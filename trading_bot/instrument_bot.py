import os
import re
import math
import time
import uuid
import logging
import threading
import pytz
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime, timedelta, time as dt_time
from typing import Optional, List, Dict, Tuple, Union, Any

from trading_bot.config import Config
from trading_bot.api_wrapper import DhanAPIWrapper, safe_int
from trading_bot.alerts import AlertManager
from trading_bot.state import TradeState
from trading_bot.account_manager import MultiAccountManager
from trading_bot.data_pipeline import (
    process_market_data,
    get_latest_signal,
    get_all_latest_signals,
    load_security_master,
    choose_option_instruments,
    choose_strategy_instruments,
    log_trade_event,
    count_active_option_orders,
    wait_for_next_candle,
    get_trade_actions,
    fetch_candle_with_retry,
    get_today_trade_count,
    get_today_sl_count,
    choose_calendar_spread_v2
)

# ========== THREADED INSTRUMENT BOT ==========
class InstrumentBot(threading.Thread):
    """
    Independent Trading Bot for a single Instrument.
    Runs in its own thread.
    """
    def __init__(self, instrument_name: str, config: Config, data_api: DhanAPIWrapper, order_manager: MultiAccountManager, state: TradeState, logger: logging.Logger, alert_manager: AlertManager):
        super().__init__()
        self.name = instrument_name
        self.instrument_name = instrument_name
        self.config = config
        # self.config.INSTRUMENTS[self.name] removed - now using self.config.INSTRUMENTS[self.name] directly for dynamic updates
        self.data_api = data_api  # Renamed for clarity: Used for Data Fetching
        self.order_manager = order_manager # Used for Order Execution
        self.api = data_api # Keep 'api' alias if needed, but prefer specific usage
        self.state = state
        self.logger = logger
        self.alert_manager = alert_manager
        self.running = True
        
        # Independent State
        self.cooldown_until: Optional[datetime] = None
        self.strategy_cooldowns = {}
        self.last_heartbeat_alert_time = None
        self.order_latency_locks = {}  # Prevent order entry burst triggers
        # H2 FIX: Per-strategy threading lock prevents two simultaneously firing strategies
        # from both passing the active-position check before either order completes.
        self.strategy_entry_locks: Dict[str, threading.Lock] = {}
        self.last_processed_candle = None
        self.df_spot = None
        # M1 FIX: Cache expiry_list API responses to avoid a live API call on every signal.
        # Entries: {security_id: {'expiry_list': [...], 'cached_at': datetime}}
        self._expiry_cache: Dict[str, dict] = {}
        
        # Restore Daily Count from Disk (Per Strategy, Per Account)
        self.daily_trade_counts = {}
        self.daily_sl_counts = {}
        for i in range(1, 24):
            strat_name = f"Strategy_{i}"
            restored = get_today_trade_count(config.TRADE_LOG_CSV, instrument_name, config.TIMEZONE, strategy_name=strat_name)
            self.daily_trade_counts[strat_name] = restored if isinstance(restored, dict) else {}
            restored_sl = get_today_sl_count(config.TRADE_LOG_CSV, instrument_name, config.TIMEZONE, strategy_name=strat_name)
            self.daily_sl_counts[strat_name] = restored_sl if isinstance(restored_sl, dict) else {}
        
        self.active_trades = 0
        self.poll_offset = 0  # Default 0s
        self.consecutive_failures = 0
        try:
            self.current_trading_day = datetime.now(config.TIMEZONE).date()
        except Exception:
            self.current_trading_day = datetime.now().date()
        
        # Determine Instrument Constraints
        self.MAX_ACTIVE = self.config.INSTRUMENTS[self.name].get('max_active', 1)
        self.DAILY_LIMIT = self.config.INSTRUMENTS[self.name].get('daily_limit', 5)
        self.TYPE = self.config.INSTRUMENTS[self.name].get('type', 'INDEX') # INDEX or STOCK
        
        self.logger.info(f"[{self.name}] Initialized. Type={self.TYPE}, MaxRunning={self.MAX_ACTIVE}, DailyLimit={self.DAILY_LIMIT}, RestoredCounts={self.daily_trade_counts}, RestoredSLCounts={self.daily_sl_counts}")

    def get_strategy_instrument_config(self, strategy_name: str) -> dict:
        """
        Dynamically get the config parameters for this instrument under a specific strategy.
        Copies the base configuration and applies strategy-specific overrides.
        """
        import copy
        clean_source = getattr(self.config, "BASE_INSTRUMENTS", self.config.INSTRUMENTS)
        base_cfg = copy.deepcopy(clean_source.get(self.name, {}))
        overrides = base_cfg.get("strategy_overrides", {})
        if isinstance(overrides, dict) and strategy_name in overrides:
            strat_cfg = overrides[strategy_name]
            if isinstance(strat_cfg, dict):
                for k, v in strat_cfg.items():
                    base_cfg[k] = v
        return base_cfg

    def should_carry_forward(self, strategy_name: str = "Strategy_3") -> bool:
        """
        Check if carry_forward is enabled for the specified strategy.
        Falls back to global config.CARRY_FORWARD if not explicitly set in instruments.json.
        """
        inst_cfg = self.get_strategy_instrument_config(strategy_name)
        if "carry_forward" in inst_cfg:
            val = inst_cfg["carry_forward"]
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, str):
                return val.strip().lower() in ("true", "1", "yes")
        return getattr(self.config, "CARRY_FORWARD", True)

    @staticmethod
    def _make_position_key(account_name: str, strategy: str, security_id: Union[str, int]) -> str:
        return f"{account_name}::{strategy}::{security_id}"

    def reconcile_positions_with_broker(self):
        """
        Reconcile local self.state.positions with active broker positions.
        Prunes local entries that are no longer open on the broker.
        """
        self.logger.info(f"[{self.name}] Reconciling local positions with broker...")
        broker_sec_ids_by_acc = {}
        try:
            accounts = self.order_manager.get_accounts()
            for acc in accounts:
                acc_name = acc['name']
                acc_api = acc['api']
                acc_set = set()
                try:
                    pos_list = acc_api.get_positions()
                    if pos_list:
                        for pos in pos_list:
                            net_qty = safe_int(pos.get('netQty', 0))
                            if net_qty != 0:
                                acc_set.add(str(pos.get('securityId')))
                except Exception as e:
                    self.logger.error(f"[{self.name}] Reconcile failed to fetch positions for {acc_name}: {e}")
                broker_sec_ids_by_acc[acc_name] = acc_set
            
            # Prune local positions that aren't on the broker
            to_remove = []
            all_broker_sec_ids = set().union(*broker_sec_ids_by_acc.values()) if broker_sec_ids_by_acc else set()
            with self.state.lock:
                for pos_key, pos in self.state.positions.items():
                    if pos.get('instrument') == self.name:
                        pos_acc = pos.get('account')
                        pos_sec_id = str(pos.get('security_id') or (pos_key.split('::')[-1] if '::' in str(pos_key) else pos_key))
                        if pos_acc and pos_acc in broker_sec_ids_by_acc:
                            is_open = pos_sec_id in broker_sec_ids_by_acc[pos_acc]
                        else:
                            is_open = pos_sec_id in all_broker_sec_ids
                        
                        if not is_open:
                            self.logger.warning(f"[{self.name}] Reconcile: Pruning stale local position {pos_key} ({pos.get('symbol')}) not found on broker account '{pos_acc}'.")
                            to_remove.append(pos_key)
                for pos_key in to_remove:
                    self.state.positions.pop(pos_key, None)
            if to_remove:
                self.state.save_state()
        except Exception as e:
            self.logger.error(f"[{self.name}] Reconcile failed: {e}")

    def _enforce_order_stagger(self):
        """
        Enforce a minimum spacing (e.g. 500ms) between consecutive order placements
        globally across all instrument bot threads.
        """
        with self.state.lock:
            last_global_order = getattr(self.state, "last_order_timestamp", 0.0)
            now = time.time()
            elapsed = now - last_global_order
            if elapsed < 0.5:
                sleep_time = 0.5 - elapsed
                self.logger.info(f"[{self.name}] [STAGGER] Spacing order placement. Sleeping for {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            self.state.last_order_timestamp = time.time()

    def _is_margin_rejection(self, reason_str: str, resp_obj: Any = None) -> bool:
        """
        Check if an order failure or rejection was caused by insufficient funds / margin shortfall.
        """
        text = str(reason_str or '').lower()
        if isinstance(resp_obj, dict):
            for v in resp_obj.values():
                if isinstance(v, (str, int, float)):
                    text += " " + str(v).lower()
                elif isinstance(v, dict):
                    text += " " + " ".join(str(sub_v).lower() for sub_v in v.values() if isinstance(sub_v, (str, int, float)))
        margin_keywords = ['margin', 'insufficient', 'funds', 'shortfall', 'rms:rule', 'balance', 'limit exceeded', 'not enough balance']
        return any(k in text for k in margin_keywords)

    def _validate_gatekeeper_live(self, target_strike, option_type_str, is_short=False) -> bool:
        """
        Validate entry using live Dhan API historical candles.
        Checks ATM, ATM-1, and ATM+1 strikes.
        """
        import os
        import re
        import time
        import pytz
        import pandas as pd
        from datetime import datetime, timedelta
        
        inst_config = self.config.INSTRUMENTS[self.name]
        
        # 1. Check if gatekeeper is enabled
        if inst_config.get("gatekeeper_enabled", 0) != 1:
            return True
            
        self.logger.info(f"[{self.name}] [GATEKEEPER] Running validation for {target_strike} {option_type_str}...")
        
        # 2. Market opening noise filter
        timezone = self.config.TIMEZONE
        now_time = datetime.now(timezone).time()
        mins_past_open = (now_time.hour * 60 + now_time.minute) - (9 * 60 + 15)
        time_filter_mins = inst_config.get("gatekeeper_time_filter_minutes", 20)
        
        if mins_past_open < time_filter_mins:
            self.logger.warning(f"[{self.name}] [GATEKEEPER] Skipped: within early morning noise filter ({time_filter_mins} mins).")
            return False
            
        # 3. Get parameters
        window = int(inst_config.get("gatekeeper_window_minutes", 5))
        oi_min_change = float(inst_config.get("gatekeeper_oi_min_change_pct", 1.0))
        vol_sma_period = int(inst_config.get("gatekeeper_volume_sma_period", 15))
        vol_mult = float(inst_config.get("gatekeeper_volume_multiplier", 1.2))
        
        # 4. Resolve expiry and strike step
        strike_step = inst_config.get("strike_step", 100)
        underlying_id = int(inst_config['security_id'])
        underlying_segment = inst_config.get('exchange_segment', 'IDX_I')
        expiry_list = []
        try:
            resp = self.data_api._make_request(self.data_api.dhan.expiry_list, under_security_id=underlying_id, under_exchange_segment=underlying_segment)
            if resp and resp.get('data'):
                raw_data = resp['data']
                if isinstance(raw_data, list):
                    expiry_list = raw_data
                elif isinstance(raw_data, dict):
                    for k, v in raw_data.items():
                        if isinstance(v, list):
                            expiry_list = v
                            break
        except Exception as e:
            self.logger.error(f"[{self.name}] [GATEKEEPER] Error fetching expiry: {e}")
            
        if not expiry_list:
            self.logger.error(f"[{self.name}] [GATEKEEPER] No expiry list found.")
            return True # Fail-safe bypass
            
        expiry_list.sort()
        target_expiry_idx = inst_config.get('expiry_index', 0)
        if len(expiry_list) > target_expiry_idx:
            nearest_expiry = expiry_list[target_expiry_idx]
        else:
            nearest_expiry = expiry_list[-1]
            
        # Today rollover check
        trading_date_str = datetime.now(timezone).strftime('%Y-%m-%d')
        if nearest_expiry == trading_date_str:
            try:
                curr_idx = expiry_list.index(nearest_expiry)
                if curr_idx + 1 < len(expiry_list):
                    nearest_expiry = expiry_list[curr_idx + 1]
            except ValueError:
                pass
                
        # Resolve strike step dynamically from master cache if available
        prefix_upper = inst_config['fno_prefix'].upper()
        detected_strikes = []
        use_gatekeeper_fallback = True
        
        if self.data_api.config.master_cache_index:
            try:
                for key, value in self.data_api.config.master_cache_index.items():
                    k_prefix, k_expiry, k_strike, k_type = key
                    if k_prefix == prefix_upper and k_expiry == nearest_expiry:
                        detected_strikes.append(k_strike)
                if len(detected_strikes) >= 2:
                    detected_strikes = sorted(list(set(detected_strikes)))
                    diffs = [detected_strikes[i+1] - detected_strikes[i] for i in range(len(detected_strikes)-1)]
                    if diffs:
                        detected_step = max(set(diffs), key=diffs.count)
                        if detected_step > 0:
                            strike_step = detected_step
                use_gatekeeper_fallback = False
            except Exception as ex:
                self.logger.warning(f"[{self.name}] [GATEKEEPER] Failed to parse dynamic strike step from memory: {ex}")
                use_gatekeeper_fallback = True
                
        if use_gatekeeper_fallback:
            cache_file = f"dhanhq_cache_{inst_config['fno_prefix']}.csv"
            if os.path.exists(cache_file):
                try:
                    df_cache = pd.read_csv(cache_file)
                    exp_date = datetime.strptime(nearest_expiry, '%Y-%m-%d')
                    exp_month_year = exp_date.strftime('%b%Y')
                    prefix_regex = inst_config['fno_prefix']
                    for idx, row in df_cache.iterrows():
                        sym = row['SEM_TRADING_SYMBOL']
                        expiry_date_str = str(row['SEM_EXPIRY_DATE']).split(' ')[0]
                        if expiry_date_str != nearest_expiry:
                            continue
                        match = re.search(rf'\b{prefix_regex}-{re.escape(exp_month_year)}-(\d+(?:\.\d+)?)-(CE|PE)', sym, re.IGNORECASE)
                        if match:
                            val = float(match.group(1))
                            detected_strikes.append(int(val) if val.is_integer() else val)
                    if len(detected_strikes) >= 2:
                        detected_strikes = sorted(list(set(detected_strikes)))
                        diffs = [detected_strikes[i+1] - detected_strikes[i] for i in range(len(detected_strikes)-1)]
                        if diffs:
                            detected_step = max(set(diffs), key=diffs.count)
                            if detected_step > 0:
                                strike_step = detected_step
                except Exception as ex:
                    self.logger.warning(f"[{self.name}] [GATEKEEPER] Failed to parse dynamic strike step: {ex}")
                
        # 5. Determine strikes to check (ATM, ATM-1, ATM+1 or Single Strike)
        if inst_config.get("gatekeeper_single_strike", 0) == 1:
            strikes_to_check = [target_strike]
        else:
            strikes_to_check = [target_strike - strike_step, target_strike, target_strike + strike_step]
        strikes_to_check = [int(s) if isinstance(s, float) and s.is_integer() else s for s in strikes_to_check]
        
        passes = 0
        valid_strikes_count = 0
        
        sec_master_df = None
        if use_gatekeeper_fallback:
            cache_file = f"dhanhq_cache_{inst_config['fno_prefix']}.csv"
            if os.path.exists(cache_file):
                try:
                    sec_master_df = pd.read_csv(cache_file, dtype={'SEM_SMST_SECURITY_ID': 'int64'})
                except Exception as e:
                    self.logger.warning(f"[{self.name}] [GATEKEEPER] Error reading cache master file: {e}")
                    
            if sec_master_df is None:
                self.logger.error(f"[{self.name}] [GATEKEEPER] No security master dataframe loaded.")
                return True # Fail-safe
            
        opt_seg = inst_config.get('option_segment', 'NSE_FNO')
        inst_type = inst_config.get('type', 'INDEX')
        opt_inst = "OPTIDX" if inst_type == "INDEX" else "OPTSTK"
        
        for strike in strikes_to_check:
            opt_sec_id = None
            if not use_gatekeeper_fallback:
                key = (prefix_upper, nearest_expiry, strike, option_type_str.upper())
                if key in self.data_api.config.master_cache_index:
                    opt_sec_id = self.data_api.config.master_cache_index[key][0]
            
            if not opt_sec_id and use_gatekeeper_fallback:
                exp_date = datetime.strptime(nearest_expiry, '%Y-%m-%d')
                exp_month_year = exp_date.strftime('%b%Y')
                prefix_regex = inst_config['fno_prefix']
                
                strike_str_formatted = str(int(strike)) if isinstance(strike, (int, float)) and strike.is_integer() else str(strike)
                match_pattern = f"{prefix_regex.upper()}-{exp_month_year.upper()}-{strike_str_formatted}-{option_type_str.upper()}"
                matching_rows = sec_master_df[sec_master_df['SEM_TRADING_SYMBOL'].str.upper() == match_pattern]
                if matching_rows.empty:
                    matching_rows = sec_master_df[
                        (sec_master_df['SEM_TRADING_SYMBOL'].str.contains(f"-{strike_str_formatted}-", case=False, na=False)) &
                        (sec_master_df['SEM_TRADING_SYMBOL'].str.endswith(option_type_str.upper(), na=False)) &
                        (sec_master_df['SEM_EXPIRY_DATE'].str.startswith(nearest_expiry, na=False))
                    ]
                    
                if not matching_rows.empty:
                    opt_sec_id = str(matching_rows.iloc[0]['SEM_SMST_SECURITY_ID'])
                
            if not opt_sec_id:
                self.logger.warning(f"[{self.name}] [GATEKEEPER] Could not resolve security ID for strike {strike} {option_type_str}")
                continue
                
            valid_strikes_count += 1
            
            try:
                df_opt = self.data_api.get_historical_data(
                    security_id=opt_sec_id,
                    interval=1,
                    exchange_segment=opt_seg,
                    instrument_type=opt_inst
                )
            except Exception as e:
                self.logger.warning(f"[{self.name}] [GATEKEEPER] Failed to fetch historical data for strike {strike}: {e}")
                continue
                
            if df_opt is None or df_opt.empty:
                self.logger.warning(f"[{self.name}] [GATEKEEPER] Empty historical data for strike {strike}")
                continue
                
            if 'timestamp' in df_opt.columns:
                last_row_time = df_opt['timestamp'].iloc[-1]
                if last_row_time.tzinfo is None:
                    last_row_time_local = last_row_time.tz_localize('UTC').tz_convert(timezone).tz_localize(None)
                else:
                    last_row_time_local = last_row_time.tz_convert(timezone).tz_localize(None)
                
                current_minute = datetime.now(timezone).replace(second=0, microsecond=0, tzinfo=None)
                
                if last_row_time_local >= current_minute:
                    self.logger.info(f"[{self.name}] [GATEKEEPER] Last candle {last_row_time_local} is incomplete (current minute {current_minute}). Dropping it to align with completed candle backtest.")
                    df_opt = df_opt.iloc[:-1]
                    
            required_len = max(window + 1, vol_sma_period + 1)
            if len(df_opt) < required_len:
                self.logger.warning(f"[{self.name}] [GATEKEEPER] Insufficient data length ({len(df_opt)} < {required_len}) for strike {strike}")
                continue
                
            current_close = float(df_opt['close'].iloc[-1])
            prev_close = float(df_opt['close'].iloc[-1 - window])
            price_change = current_close - prev_close
            
            if not is_short:
                price_direction_ok = (price_change > 0)
            else:
                price_direction_ok = (price_change < 0)
                
            if 'oi' in df_opt.columns:
                current_oi = float(df_opt['oi'].iloc[-1])
                prev_oi = float(df_opt['oi'].iloc[-1 - window])
                oi_change = current_oi - prev_oi
                oi_change_pct = (oi_change / prev_oi * 100.0) if prev_oi > 0 else 0.0
                oi_ok = (abs(oi_change_pct) >= oi_min_change)
            else:
                oi_ok = True
                
            if 'volume' in df_opt.columns:
                current_volume = float(df_opt['volume'].iloc[-1])
                volume_history = df_opt['volume'].iloc[-vol_sma_period - 1:-1].astype(float)
                volume_sma = volume_history.mean()
                volume_ok = (current_volume >= vol_mult * volume_sma) if volume_sma > 0 else True
            else:
                volume_ok = True
                
            self.logger.info(f"[{self.name}] [GATEKEEPER DETAIL] Strike: {strike} | Price: {prev_close:.2f} -> {current_close:.2f} (Ok: {price_direction_ok}) | Vol ok: {volume_ok} (Curr: {current_volume if 'volume' in df_opt.columns else 'N/A'}, SMA: {volume_sma if 'volume' in df_opt.columns else 'N/A'})")
            
            if price_direction_ok and oi_ok and volume_ok:
                passes += 1
                
        required_passes = 2 if valid_strikes_count >= 3 else 1
        if passes >= required_passes:
            self.logger.info(f"[{self.name}] [GATEKEEPER PASS] Passes: {passes}/{valid_strikes_count} (Required: {required_passes})")
            return True
            
        self.logger.warning(f"[{self.name}] [GATEKEEPER SKIP] Passes: {passes}/{valid_strikes_count} (Required: {required_passes}). validation failed.")
        return False

    def run(self):
        """Thread Main Loop"""
        self.logger.info(f"[{self.name}] Thread Started.")
        
        # Startup Alignment
        self._initial_alignment()
        
        # Reconcile local state with broker positions to clean up stale entries
        self.reconcile_positions_with_broker()

        # Start high-frequency local stop monitoring loop
        threading.Thread(target=self._local_monitoring_loop, daemon=True).start()

        while self.running:
            try:
                try:
                    now = datetime.now(self.config.TIMEZONE)
                except Exception:
                    now = datetime.now()
                today_date = now.date()
                if self.current_trading_day != today_date:
                    self.current_trading_day = today_date
                    for i in range(1, 24):
                        strat_name = f"Strategy_{i}"
                        self.daily_trade_counts[strat_name] = {}
                        self.daily_sl_counts[strat_name] = {}
                    self.logger.info(f"[{self.name}] New trading day ({today_date}). Daily trade and SL counts reset.")
                current_time_only = now.time()

                # 1. Market Hours Check
                if not (self.config.RUN_START <= current_time_only <= self.config.RUN_END):
                     # Square Off Check
                     if current_time_only >= self.config.SQ_OFF_TIME:
                         self.logger.info(f"[{self.name}] Square-Off Time reached. Stopping thread.")
                         self.running = False
                         break
                     
                     if current_time_only > self.config.RUN_END:
                         time.sleep(30)
                         continue
                         
                     if current_time_only < self.config.RUN_START:
                         self.logger.info(f"[{self.name}] Before Start Time ({self.config.RUN_START}). Waiting...")
                         time.sleep(30)
                         continue
                
                # 2. Cycle Logic
                # Check if still enabled (dynamic disable)
                if not self.config.INSTRUMENTS.get(self.name, {}).get('enabled', False):
                    self.logger.info(f"[{self.name}] Instrument disabled in config. Stopping thread.")
                    self.running = False
                    break
                    
                self.process_cycle()
                
                # 3. Wait
                wait_for_next_candle(now, self.config.POLL_INTERVAL_SECS, self.logger, offset_seconds=self.poll_offset)

            except RuntimeError as e:
                self.logger.critical(f"[{self.name}] CRITICAL: Circuit breaker / Fatal runtime error: {e}")
                if self.alert_manager:
                    self.alert_manager.send_alert(
                        f"🚨 *CRITICAL: {self.name} Bot Stopped*\nReason: {e}\nInitiating graceful shutdown.",
                        header="Critical Bot Shutdown"
                    )
                self.running = False
                break

            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                self.logger.exception(f"[{self.name}] CRASH: {e}")
                if self.alert_manager:
                    trace_lines = error_trace.strip().split('\n')
                    last_10_lines = '\n'.join(trace_lines[-10:]) if len(trace_lines) > 10 else error_trace
                    self.alert_manager.send_alert(f"Critical Error in `{self.name}` Thread!\nReason: {e}\nTraceback:\n{last_10_lines}")
                time.sleep(10) # Prevent tight loop crash
        
        self.logger.info(f"[{self.name}] Thread Stopped.")

    def _initial_alignment(self):
        """Align thread start with a random jitter to prevent API bursts"""
        # Check if Strategy 14 is enabled and history file is missing
        if getattr(self.config, "ENABLE_STRATEGY_14", False):
            hist_file = "backtest_data/daily_mci_history.csv"
            spot_backup = "backtest_data/nifty_spot.csv"
            
            if not os.path.exists(hist_file) and not os.path.exists(spot_backup):
                self.logger.info(f"[{self.name}] [Strategy_14] Missing metrics database and spot backup. Downloading 130-day history...")
                try:
                    security_id = self.config.INSTRUMENTS[self.name]['security_id']
                    exch_seg = self.config.INSTRUMENTS[self.name].get('exchange_segment', 'IDX_I')
                    inst_type = self.config.INSTRUMENTS[self.name].get('instrument_type', 'INDEX')
                    
                    df_130d = self.data_api.get_historical_data(
                        security_id, 
                        interval=self.config.DATA_INTERVAL,
                        exchange_segment=exch_seg,
                        instrument_type=inst_type,
                        days=130
                    )
                    if df_130d is not None and not df_130d.empty:
                        os.makedirs(os.path.dirname(spot_backup), exist_ok=True)
                        if df_130d.index.name == 'timestamp' or 'timestamp' not in df_130d.columns:
                            df_130d = df_130d.reset_index()
                        df_130d.to_csv(spot_backup, index=False)
                        self.logger.info(f"[{self.name}] [Strategy_14] Downloaded {len(df_130d)} index candles for the past 130 days and saved to {spot_backup}.")
                    else:
                        self.logger.warning(f"[{self.name}] [Strategy_14] Failed to fetch 130-day index history.")
                except Exception as e:
                    self.logger.error(f"[{self.name}] [Strategy_14] Error during 130-day historical download: {e}")

        import random
        startup_now = datetime.now(self.config.TIMEZONE)
        
        # 1. Base Minute Alignment
        next_min = startup_now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # 2. Add Random Jitter (0 to 4 seconds) to spread API load across instruments
        jitter = random.uniform(0.5, 4.0)
        
        wait_s = (next_min - startup_now).total_seconds() + jitter
        self.logger.info(f"[{self.name}] Aligning start. Waiting {wait_s:.1f}s (Jitter: {jitter:.1f}s)...")
        time.sleep(wait_s)

    def process_cycle(self):
        cycle_start = time.time()
        
        security_id = self.config.INSTRUMENTS[self.name]['security_id']
        prefix = self.config.INSTRUMENTS[self.name]['fno_prefix']
        
        # Determine Segment
        if self.TYPE == 'OPTION':
            exch_seg = self.config.INSTRUMENTS[self.name].get('exchange_segment', 'NSE_FNO')
            inst_type = self.config.INSTRUMENTS[self.name].get('instrument_type')
            if not inst_type:
                fno_prefix = self.config.INSTRUMENTS[self.name].get('fno_prefix', self.name).upper()
                if any(x in fno_prefix for x in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY']):
                    inst_type = 'OPTIDX'
                else:
                    inst_type = 'OPTSTK'
        elif self.TYPE == 'STOCK':
            exch_seg = 'NSE_EQ'
            inst_type = 'EQUITY'
        else:
            exch_seg = 'IDX_I'
            inst_type = 'INDEX'
        
        # 1. Fetch Data
        df = fetch_candle_with_retry(self.data_api, security_id, self.config, self.logger, 
                                     interval=self.config.DATA_INTERVAL,
                                     exchange_segment=exch_seg,
                                     instrument_type=inst_type)
        
        if df is None or df.empty:
            self.consecutive_failures += 1
            self.logger.warning(f"[{self.name}] Data fetch failed. (Consecutive Failures: {self.consecutive_failures})")
            
            if self.consecutive_failures == 3:
                if self.alert_manager:
                    self.alert_manager.send_alert(f"⚠️ Continuous Error: Bot `{self.name}` failed to fetch data for 3 consecutive cycles. Please check your Dhan API connection.")
                    
            if self.consecutive_failures >= 10 and self.consecutive_failures % 10 == 0:
                if self.alert_manager:
                     self.alert_manager.send_alert(f"🚨 Bot `{self.name}` still failing (Failed {self.consecutive_failures} times). Pausing cycle for 5 minutes.")
                time.sleep(300)
                
            return

        # Reset failures on success
        if self.consecutive_failures > 0:
            self.logger.info(f"[{self.name}] Connection restored after {self.consecutive_failures} failures.")
            self.consecutive_failures = 0

        # 2. Process Indicators
        df_1min = process_market_data(df, self.config, self.logger, instrument_name=self.name)
        if df_1min.empty: return
        self.df_spot = df_1min
        
        # 3. Get Signals across all active strategies
        active_signals = get_all_latest_signals(df_1min, self.logger, self.config)
        current_candle_time = df_1min.index[-1]
        
        # 4. New Candle Check
        if self.last_processed_candle != current_candle_time:
            # Latency Check
            candle_delay = (datetime.now(self.config.TIMEZONE) - current_candle_time).total_seconds()
            self.logger.info(f"[{self.name}] Candle: {current_candle_time.strftime('%H:%M')} | Active Signals Count: {len(active_signals)} | Delay: {candle_delay:.1f}s | Close: {df_1min['close'].iloc[-1]}")
            
            self.last_processed_candle = current_candle_time
            
            # Find active strategies
            active_strategies = []
            for i in range(1, 24):
                if getattr(self.config, f"ENABLE_STRATEGY_{i}", False):
                    active_strategies.append(f"Strategy_{i}")
            if not active_strategies:
                active_strategies = ["Strategy_3"]
            
            # A. Dynamic Exit Check per Strategy
            if getattr(self.config, "USE_DYNAMIC_EXITS", False):
                last_row = df_1min.iloc[-1]
                for s_name in active_strategies:
                    exit_long = bool(last_row.get(f'Exit_Long_{s_name}', False))
                    exit_short = bool(last_row.get(f'Exit_Short_{s_name}', False))
                    if exit_long or exit_short:
                        self._handle_dynamic_exits(exit_long, exit_short, source=s_name)
            
            # B. Process signals
            for signal, atr_val, s_name in active_signals:
                cooldown_time = self.strategy_cooldowns.get(s_name)
                if cooldown_time and datetime.now(self.config.TIMEZONE) < cooldown_time:
                    self.logger.info(f"[{self.name}] [SKIP] Signal {signal.upper()} for strategy {s_name} ignored. Strategy is on cooldown until {cooldown_time.strftime('%H:%M:%S')}.")
                    continue
                
                self.logger.info(f"!!! [{self.name}] SIGNAL: {signal.upper()} ({s_name}) !!!")
                if self.alert_manager:
                    self.alert_manager.send_alert(
                        f"📡 *Signal Detected*\n"
                        f"🔹 *Instrument:* `{self.name}`\n"
                        f"🔹 *Strategy:* `{s_name}`\n"
                        f"🔹 *Signal:* `{signal.upper()}`\n"
                        f"🔹 *Time:* `{current_candle_time.strftime('%H:%M')}` | *Close:* `{df_1min['close'].iloc[-1]:.2f}`",
                        header="Signal Alert"
                    )
                self._handle_signal(signal, atr_val, s_name)
        
        # Cycle Performance Log
        duration = time.time() - cycle_start
        if duration > 2.0:
            self.logger.warning(f"[{self.name}] Slow Cycle: {duration:.2f}s")
        else:
            self.logger.debug(f"[{self.name}] Cycle Time: {duration:.2f}s")

    def _get_nearest_expiry(self, inst_config: dict) -> Optional[str]:
        """
        Return the nearest expiry date string (YYYY-MM-DD) for this instrument.

        M1 FIX: Caches the expiry_list API response for 5 minutes so that both
        trade_expiry_day_only and block_expiry_day_trades filters share a single
        API call per candle cycle instead of firing independently.
        """
        cache_ttl_secs = 300  # 5 minutes
        security_id = str(inst_config.get('security_id', ''))
        cached = self._expiry_cache.get(security_id)
        now = datetime.now(self.config.TIMEZONE)
        if cached:
            age = (now - cached['cached_at']).total_seconds()
            if age < cache_ttl_secs:
                return cached.get('nearest_expiry')

        try:
            underlying_id = int(security_id)
            underlying_segment = inst_config.get('exchange_segment', 'IDX_I')
            resp = self.data_api._make_request(
                self.data_api.dhan.expiry_list,
                under_security_id=underlying_id,
                under_exchange_segment=underlying_segment
            )
            if resp and resp.get('data'):
                raw_data = resp['data']
                expiry_list = []
                if isinstance(raw_data, list):
                    expiry_list = raw_data
                elif isinstance(raw_data, dict):
                    for k, v in raw_data.items():
                        if isinstance(v, list):
                            expiry_list = v
                            break
                if expiry_list:
                    expiry_list = [str(x) for x in expiry_list if isinstance(x, str)]
                    expiry_list.sort()
                    nearest = expiry_list[0]
                    self._expiry_cache[security_id] = {
                        'nearest_expiry': nearest,
                        'cached_at': now
                    }
                    return nearest
        except Exception as e:
            self.logger.error(f"[{self.name}] _get_nearest_expiry failed: {e}")
        return None

    def _handle_signal(self, signal, atr_val, source):
        """Handle entry signal with early limit validation"""
        # H2 FIX: Acquire per-strategy lock so that if two strategies fire simultaneously
        # within the same cycle, the second one waits until the first has completed its
        # position-count check AND order placement, preventing double-entry.
        if source not in self.strategy_entry_locks:
            self.strategy_entry_locks[source] = threading.Lock()
        if not self.strategy_entry_locks[source].acquire(blocking=False):
            self.logger.warning(f"[{self.name}] [SKIP] Signal for '{source}' dropped — entry already in progress for this strategy.")
            return
        try:
            self._handle_signal_inner(signal, atr_val, source)
        finally:
            self.strategy_entry_locks[source].release()

    def _handle_signal_inner(self, signal, atr_val, source):
        """Inner signal handler — called exclusively while strategy_entry_locks[source] is held."""
        # Fetch the strategy-specific isolated config override
        inst_config = self.get_strategy_instrument_config(source)
        
        # Check order latency lock to prevent duplicate entry orders during API/broker delay
        last_order_time = self.order_latency_locks.get(source)
        if last_order_time:
            elapsed = (datetime.now(self.config.TIMEZONE) - last_order_time).total_seconds()
            if elapsed < 10.0:  # 10 seconds latency lock
                self.logger.warning(f"[{self.name}] [SKIP] Signal for strategy '{source}' ignored. Order latency lock active (placed {elapsed:.1f}s ago).")
                return
        allowed_actions = inst_config.get("allowed_actions")
        if allowed_actions is not None:
            signal_action = signal.upper()
            if signal_action not in allowed_actions:
                self.logger.info(f"[{self.name}] [SKIP] Signal {signal.upper()} ignored. Instrument restricts trade direction to {allowed_actions}.")
                return

        # Check Expiry Day only filter
        if inst_config.get("trade_expiry_day_only", 0) == 1:
            try:
                # M1 FIX: use cached expiry list (5-min TTL) instead of live API call per signal
                nearest_expiry = self._get_nearest_expiry(inst_config)
                if nearest_expiry:
                    trading_date_str = datetime.now(self.config.TIMEZONE).strftime('%Y-%m-%d')
                    if nearest_expiry != trading_date_str:
                        self.logger.info(f"[{self.name}] [SKIP] Signal ignored. trade_expiry_day_only is active and today ({trading_date_str}) is not the expiry day ({nearest_expiry}).")
                        return
            except Exception as e:
                self.logger.error(f"[{self.name}] Error checking expiry day only filter: {e}")

        # Check Expiry Day block filter
        if inst_config.get("block_expiry_day_trades", 0) == 1:
            # Only block if the signal translates to buying options (decay is bad for buyers, good for sellers)
            ce_action, pe_action = get_trade_actions(signal, self.config, self.logger, leg_mode_override=inst_config.get('LEG_MODE'))
            is_buying_trade = (ce_action == 'BUY' or pe_action == 'BUY')
            
            if is_buying_trade:
                try:
                    # M1 FIX: reuse cached expiry list — avoids duplicate API call when both
                    # trade_expiry_day_only and block_expiry_day_trades are both enabled.
                    nearest_expiry = self._get_nearest_expiry(inst_config)
                    if nearest_expiry:
                        trading_date_str = datetime.now(self.config.TIMEZONE).strftime('%Y-%m-%d')
                        if nearest_expiry == trading_date_str:
                            self.logger.warning(f"[{self.name}] [SKIP] Signal ignored. Expiry day trading is blocked for option BUYING trades today ({trading_date_str}).")
                            return
                except Exception as e:
                    self.logger.error(f"[{self.name}] Error checking expiry block: {e}")

        # 1. Early Daily Limit & Max Daily SL Check (Per Account, Per Strategy) - Saves API calls
        accounts = self.order_manager.get_accounts()
        strat_config = self.get_strategy_instrument_config(source)
        all_limited = True
        for acc in accounts:
            acc_name = acc['name']
            acc_config = acc.get('config', {})
            overrides = acc_config.get('instrument_overrides', {}).get(self.name, {})
            acc_daily_limit = overrides.get(
                'daily_limit_per_strategy',
                overrides.get('daily_limit', acc_config.get('daily_limit', strat_config.get('daily_limit_per_strategy', strat_config.get('daily_limit', self.DAILY_LIMIT))))
            )
            acc_max_sl = overrides.get(
                'max_daily_sl_per_strategy',
                overrides.get('max_daily_sl', acc_config.get('max_daily_sl', strat_config.get('max_daily_sl_per_strategy', strat_config.get('max_daily_sl', inst_config.get('max_daily_sl', None)))))
            )
            
            strat_counts = self.daily_trade_counts.setdefault(source, {})
            strat_sls = self.daily_sl_counts.setdefault(source, {})
            trade_count = strat_counts.get(acc_name, 0)
            sl_count = strat_sls.get(acc_name, 0)
            
            if trade_count < acc_daily_limit and (acc_max_sl is None or sl_count < acc_max_sl):
                all_limited = False
                break
        
        if all_limited:
            self.logger.warning(f"[{self.name}] [SKIP] Signal ignored. All accounts have reached daily limit or max daily SL for {source}.")
            return

        self.logger.info(f"[{self.name}] Executing {signal} from {source}...")
        
        # Check Execution Mode
        execution_mode = inst_config.get('execution_mode', 'OPTION')
        
        if execution_mode == 'STOCK':
            # --- STOCK EXECUTION PATH ---
            # 1. Determine Stock Action based on signal & LEG_MODE
            stock_action = None
            if signal.lower() == 'buy' and self.config.LEG_MODE in ['BUY', 'BOTH']:
                stock_action = 'BUY'
            elif signal.lower() == 'sell' and self.config.LEG_MODE in ['SELL', 'BOTH']:
                stock_action = 'SELL'
            
            if not stock_action:
                self.logger.info(f"[{self.name}] [SKIP] Stock action is None (Signal: {signal}, LEG_MODE: {self.config.LEG_MODE}).")
                return
                
            # 2. Filter Eligible Accounts
            eligible_accounts = []
            underlying_id = str(inst_config['security_id'])
            for acc in accounts:
                acc_name = acc['name']
                acc_api = acc['api']
                acc_config = acc.get('config', {})
                
                # Check allowed_actions
                allowed_actions = acc_config.get('allowed_actions')
                if allowed_actions is not None and stock_action not in allowed_actions:
                    self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. {stock_action} not in allowed_actions.")
                    continue
                    
            # Check allowed_instruments
                allowed_instruments = acc_config.get('allowed_instruments')
                if allowed_instruments is not None and self.name not in allowed_instruments:
                    self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. Not in allowed_instruments.")
                    continue
                    
                # Check limit overrides
                overrides = acc_config.get('instrument_overrides', {}).get(self.name, {})
                strat_config = self.get_strategy_instrument_config(source)
                acc_max_active = overrides.get(
                    'max_active_per_strategy',
                    overrides.get('max_active', acc_config.get('max_active', strat_config.get('max_active_per_strategy', strat_config.get('max_active', inst_config.get('max_active', self.MAX_ACTIVE)))))
                )
                acc_daily_limit = overrides.get(
                    'daily_limit_per_strategy',
                    overrides.get('daily_limit', acc_config.get('daily_limit', strat_config.get('daily_limit_per_strategy', strat_config.get('daily_limit', inst_config.get('daily_limit', self.DAILY_LIMIT)))))
                )
                
                strat_counts = self.daily_trade_counts.setdefault(source, {})
                if strat_counts.get(acc_name, 0) >= acc_daily_limit:
                    self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Daily Limit Reached for {source}.")
                    continue
                
                # Check Max Daily SL Circuit Breaker
                acc_max_sl = overrides.get(
                    'max_daily_sl_per_strategy',
                    overrides.get('max_daily_sl', acc_config.get('max_daily_sl', strat_config.get('max_daily_sl_per_strategy', strat_config.get('max_daily_sl', inst_config.get('max_daily_sl', None)))))
                )
                if acc_max_sl is not None:
                    strat_sls = self.daily_sl_counts.setdefault(source, {})
                    if strat_sls.get(acc_name, 0) >= acc_max_sl:
                        self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Max Daily SL Reached for {source} ({strat_sls.get(acc_name, 0)}/{acc_max_sl}). Circuit breaker active.")
                        continue
                    
                try:
                    active_trades = self._count_my_active_positions(None, "STOCK", strategy_name=source, account_name=acc_name)
                    if active_trades >= acc_max_active:
                        self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' has reached Max Active stock positions ({active_trades}/{acc_max_active}).")
                        continue
                except Exception as e:
                    self.logger.error(f"[{self.name}] Failed to check stock positions for '{acc_name}': {e}")
                    continue
                    
                eligible_accounts.append(acc)
                self.logger.info(f"[{self.name}] Account '{acc_name}' is eligible for stock trade (Active Stock Positions: {active_trades}/{acc_max_active}).")
                
            if not eligible_accounts:
                self.logger.warning(f"[{self.name}] No eligible accounts for stock execution.")
                return
                
            # 3. Form Stock Item and Place Orders
            stock_items = [{'id': inst_config['security_id'], 'symbol': self.name, 'delta': 1.0}]
            traded_accounts = self._place_batch(
                stock_items, stock_action, "STOCK", atr_val, signal, source,
                bypass_max_active_check=True, accounts=eligible_accounts
            )
            
            # 4. Update trade counts and cooldowns
            for acc in traded_accounts:
                strat_counts = self.daily_trade_counts.setdefault(source, {})
                strat_counts[acc] = strat_counts.get(acc, 0) + 1
                
            if traded_accounts:
                self.logger.info(f"[{self.name}] Stock Trade Counts Updated: {self.daily_trade_counts}")
                self.strategy_cooldowns[source] = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)
                self.order_latency_locks[source] = datetime.now(self.config.TIMEZONE)
                self.logger.info(f"[{self.name}] Strategy cooldown activated for {source}. Locked until {self.strategy_cooldowns[source].strftime('%H:%M:%S')}")
            return

        # Declarative Option Execution Routing based on instruments.json configuration
        strat_mode = str(inst_config.get('option_strategy_mode', 'DIRECT')).upper()
        strat_type = str(inst_config.get('strategy_type', '')).upper()
        leg_mode = str(inst_config.get('LEG_MODE', self.config.LEG_MODE)).upper()

        if strat_type == "CALENDAR_SPREAD" or strat_mode in ("CALENDAR_SPREAD", "10"):
            self._execute_calendar_spread_strategy(signal, atr_val, source)
            return

        if strat_mode in ("2", "OPTION_WRITING", "DIRECT_SELL"):
            if self.df_spot is None or self.df_spot.empty:
                self.logger.error(f"[{self.name}] [{source}] self.df_spot is empty/None! Cannot resolve spot price for option selling.")
                return
            spot_price = float(self.df_spot['close'].iloc[-1])
            self._execute_option_selling(signal, spot_price, source)
            return

        if strat_mode not in ('DIRECT', '1', 'NONE'):
            self._execute_multi_leg_strategy(strat_mode, signal, atr_val, source)
            return
        
        # Existing Options Logic
        ce_items, pe_items = choose_option_instruments(self.data_api, signal, inst_config, self.logger)
        
        if not ce_items or not pe_items:
            self.logger.warning(f"[{self.name}] [SKIP] Strategy '{source}' skipped: Option instruments could not be resolved (CE count: {len(ce_items)}, PE count: {len(pe_items)}). Stale or missing security master cache?")
            return
            
        ce_action, pe_action = get_trade_actions(signal, self.config, self.logger, leg_mode_override=leg_mode)
        
        # Gate Keeper Validation Check
        if inst_config.get("gatekeeper_enabled", 0) == 1:
            if ce_action and ce_items:
                ce_strike = ce_items[0]['strike']
                is_short_ce = (ce_action == 'SELL')
                if not self._validate_gatekeeper_live(ce_strike, 'CE', is_short=is_short_ce):
                    self.logger.warning(f"[{self.name}] [GATEKEEPER] Skipping trade entry for CE leg due to validation failure.")
                    ce_action = None
            if pe_action and pe_items:
                pe_strike = pe_items[0]['strike']
                is_short_pe = (pe_action == 'SELL')
                if not self._validate_gatekeeper_live(pe_strike, 'PE', is_short=is_short_pe):
                    self.logger.warning(f"[{self.name}] [GATEKEEPER] Skipping trade entry for PE leg due to validation failure.")
                    pe_action = None
                    
            if not ce_action and not pe_action:
                self.logger.warning(f"[{self.name}] [GATEKEEPER] Skipping entire trade because both legs failed validation.")
                return
        
        traded_accounts = set()
        
        if ce_items and pe_items:
             
             # Determine legs count based on configured num_strikes
             num_strikes = inst_config.get('num_strikes', self.config.NUM_STRIKES)
             num_ce_legs = num_strikes if ce_action else 0
             num_pe_legs = num_strikes if pe_action else 0
             
             # Perform strategy/signal-level eligibility check upfront
             eligible_accounts = []
             for acc in accounts:
                 acc_name = acc['name']
                 acc_api = acc['api']
                 acc_config = acc.get('config', {})
                 
                 # Check if the account allows at least one of the active actions
                 allowed_actions = acc_config.get('allowed_actions')
                 allowed_option_types = acc_config.get('allowed_option_types')
                 has_allowed_action = False
                 if ce_action and (allowed_actions is None or ce_action in allowed_actions):
                     if allowed_option_types is None or "CE" in allowed_option_types:
                         has_allowed_action = True
                 if pe_action and (allowed_actions is None or pe_action in allowed_actions):
                     if allowed_option_types is None or "PE" in allowed_option_types:
                         has_allowed_action = True
                     
                 if not has_allowed_action:
                     self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. Neither {ce_action} nor {pe_action} matches allowed_actions / allowed_option_types.")
                     continue
                     
                 allowed_instruments = acc_config.get('allowed_instruments')
                 if allowed_instruments is not None and self.name not in allowed_instruments:
                     self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. Not in allowed_instruments.")
                     continue
                     
                 overrides = acc_config.get('instrument_overrides', {}).get(self.name, {})
                 strat_config = self.get_strategy_instrument_config(source)
                 acc_max_active = overrides.get(
                     'max_active_per_strategy',
                     overrides.get('max_active', acc_config.get('max_active', strat_config.get('max_active_per_strategy', strat_config.get('max_active', inst_config.get('max_active', self.MAX_ACTIVE)))))
                 )
                 acc_daily_limit = overrides.get(
                     'daily_limit_per_strategy',
                     overrides.get('daily_limit', acc_config.get('daily_limit', strat_config.get('daily_limit_per_strategy', strat_config.get('daily_limit', inst_config.get('daily_limit', self.DAILY_LIMIT)))))
                 )
                 
                 strat_counts = self.daily_trade_counts.setdefault(source, {})
                 if strat_counts.get(acc_name, 0) >= acc_daily_limit:
                     self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Daily Limit Reached for {source}.")
                     continue
                 
                 # Check Max Daily SL Circuit Breaker
                 acc_max_sl = overrides.get(
                     'max_daily_sl_per_strategy',
                     overrides.get('max_daily_sl', acc_config.get('max_daily_sl', strat_config.get('max_daily_sl_per_strategy', strat_config.get('max_daily_sl', inst_config.get('max_daily_sl', None)))))
                 )
                 if acc_max_sl is not None:
                     strat_sls = self.daily_sl_counts.setdefault(source, {})
                     if strat_sls.get(acc_name, 0) >= acc_max_sl:
                         self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Max Daily SL Reached for {source} ({strat_sls.get(acc_name, 0)}/{acc_max_sl}). Circuit breaker active.")
                         continue
                     
                 try:
                     ce_count = self._count_my_active_positions(None, "CE", strategy_name=source, account_name=acc_name)
                     pe_count = self._count_my_active_positions(None, "PE", strategy_name=source, account_name=acc_name)
                     
                     # Check capacity independently for CE and PE option legs
                     is_eligible = True
                     if num_ce_legs > 0 and (allowed_actions is None or ce_action in allowed_actions):
                         active_ce_trades = math.ceil(ce_count / num_ce_legs)
                         if active_ce_trades >= acc_max_active:
                             self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' has reached Max Active CE strategy trades ({active_ce_trades}/{acc_max_active}).")
                             is_eligible = False
                     if is_eligible and num_pe_legs > 0 and (allowed_actions is None or pe_action in allowed_actions):
                         active_pe_trades = math.ceil(pe_count / num_pe_legs)
                         if active_pe_trades >= acc_max_active:
                             self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' has reached Max Active PE strategy trades ({active_pe_trades}/{acc_max_active}).")
                             is_eligible = False
                             
                     if not is_eligible:
                         continue
                         
                     eligible_accounts.append(acc)
                     self.logger.info(f"[{self.name}] Account '{acc_name}' is eligible for strategy trade (Active CE: {ce_count}/{acc_max_active * num_ce_legs}, PE: {pe_count}/{acc_max_active * num_pe_legs}).")
                     
                 except Exception as e:
                     self.logger.error(f"[{self.name}] Failed to check positions for '{acc_name}': {e}")
                     continue
                     
             if not eligible_accounts:
                 self.logger.warning(f"[{self.name}] No eligible accounts for strategy execution (all at Max Active limits or restricted).")
                 return
                 
             if ce_action:
                 ce_accounts = [
                     acc for acc in eligible_accounts
                     if acc.get('config', {}).get('allowed_option_types') is None or "CE" in acc.get('config', {}).get('allowed_option_types')
                 ]
                 if ce_accounts:
                     accs = self._place_batch(
                         ce_items, ce_action, "CE", atr_val, signal, source,
                         bypass_max_active_check=True, accounts=ce_accounts
                     )
                     if accs: traded_accounts.update(accs)
             if pe_action:
                 pe_accounts = [
                     acc for acc in eligible_accounts
                     if acc.get('config', {}).get('allowed_option_types') is None or "PE" in acc.get('config', {}).get('allowed_option_types')
                 ]
                 if pe_accounts:
                     accs = self._place_batch(
                         pe_items, pe_action, "PE", atr_val, signal, source,
                         bypass_max_active_check=True, accounts=pe_accounts
                     )
                     if accs: traded_accounts.update(accs)
             
             # Increment daily trade counts for successfully traded accounts
             for acc in traded_accounts:
                 strat_counts = self.daily_trade_counts.setdefault(source, {})
                 strat_counts[acc] = strat_counts.get(acc, 0) + 1
                 
             if traded_accounts:
                 self.logger.info(f"[{self.name}] Trade Counts Updated: {self.daily_trade_counts}")
                 self.strategy_cooldowns[source] = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)
                 self.order_latency_locks[source] = datetime.now(self.config.TIMEZONE)
                 self.logger.info(f"[{self.name}] Strategy cooldown activated for {source}. Locked until {self.strategy_cooldowns[source].strftime('%H:%M:%S')}")

    def _handle_dynamic_exits(self, exit_long: bool, exit_short: bool, source: str = "Strategy_3"):
        self.logger.info(f"[{self.name}] Checking dynamic exits: Exit_Long={exit_long}, Exit_Short={exit_short} | Source: {source}")
        
        inst_config = self.config.INSTRUMENTS[self.name]
        underlying_id = str(inst_config.get('security_id'))
        prefix = inst_config.get('fno_prefix', self.name)
        execution_mode = inst_config.get('execution_mode', 'OPTION')
        
        clean_source = source.split(" (")[0].replace(" ", "_")
        
        accounts = self.order_manager.get_accounts()
        for acc in accounts:
            acc_name = acc['name']
            acc_api = acc['api']
            acc_config = acc.get('config', {})
            
            # --- STRATEGY ROUTING FILTER ---
            allowed_strategies = acc_config.get('allowed_strategies')
            if allowed_strategies is not None and clean_source not in allowed_strategies:
                self.logger.debug(f"[{self.name}] [SKIP] Dynamic exit for '{acc_name}' restricted. Strategy '{clean_source}' not in allowed_strategies.")
                continue
                
            try:
                pos_list = acc_api.get_positions()
                if not pos_list:
                    continue
                
                pending_orders = None
                
                for pos in pos_list:
                    net_qty = safe_int(pos.get('netQty', 0))
                    if net_qty == 0:
                        continue
                    
                    sec_id = str(pos.get('securityId', ''))
                    sym = pos.get('tradingSymbol', '').upper()
                    
                    is_candidate = False
                    is_bullish = False
                    
                    if execution_mode == 'STOCK':
                        if sec_id == underlying_id:
                            is_candidate = True
                            is_bullish = (net_qty > 0)
                    else:  # OPTION mode
                        if sym.startswith(prefix.upper()):
                            is_candidate = True
                            if sym.endswith('CE'):
                                is_bullish = (net_qty > 0)
                            elif sym.endswith('PE'):
                                is_bullish = (net_qty < 0)
                            else:
                                is_bullish = (net_qty > 0) # Fallback
                                
                    if is_candidate:
                        should_exit = False
                        if is_bullish and exit_long:
                            should_exit = True
                            reason = "Exit_Long (Trend change)"
                        elif not is_bullish and exit_short:
                            should_exit = True
                            reason = "Exit_Short (Trend change)"
                            
                        if should_exit:
                            self.logger.warning(f"[{self.name}] [DYNAMIC EXIT] Account '{acc_name}' Position: {sym} (Qty: {net_qty}) triggers dynamic exit via {reason}")
                            
                            # 1. Fetch pending orders if not already done for this account
                            if pending_orders is None:
                                pending_orders = acc_api.get_pending_orders()
                                
                            # 2. Cancel all pending SL/TP orders matching this position's securityId
                            pos_pending = [o for o in pending_orders if str(o.get('securityId')) == sec_id]
                            for o in pos_pending:
                                oid = o.get('orderId')
                                self.logger.info(f"[{self.name}] [DYNAMIC EXIT] Cancelling pending safety order {oid} for {sym}")
                                acc_api.cancel_order(oid)
                                
                            # 3. Place MARKET close order
                            transaction_type = 'SELL' if net_qty > 0 else 'BUY'
                            abs_qty = abs(net_qty)
                            exch = pos.get('exchangeSegment', 'NSE_FNO')
                            product = pos.get('productType', 'MARGIN')
                            
                            self.logger.warning(f"[{self.name}] [DYNAMIC EXIT] Placing Market Exit Order on {acc_name}: {transaction_type} {abs_qty} {sym}")
                            
                            resp = acc_api.place_order(
                                security_id=sec_id,
                                transaction_type=transaction_type,
                                quantity=abs_qty,
                                exchange_segment=exch,
                                product_type=product,
                                order_type='MARKET',
                                price=0.0,
                                should_slice=(exch in ['NSE_FNO', 'BSE_FNO'])
                            )
                            
                            if resp:
                                order_id = resp.get('orderId', 'unknown')
                                self.logger.info(f"[{self.name}] [DYNAMIC EXIT] Exit Order ID: {order_id} placed successfully.")
                                
                                # Clear active position from state
                                with self.state.lock:
                                    keys_to_remove = [
                                        k for k, p in self.state.positions.items()
                                        if str(p.get('security_id')) == str(sec_id)
                                        and p.get('account') == acc_name
                                        and p.get('strategy') == source
                                    ]
                                    for k in keys_to_remove:
                                        self.state.positions.pop(k, None)
                                self.state.save_state()
                                
                                # Update State
                                self.state.add_order(order_id, {
                                    'order_id': order_id, 'account': acc_name, 'instrument': self.name,
                                    'type': f"{prefix}_{sym}_{transaction_type}_EXIT",
                                    'signal': "exit", 'leg': sym, 'action': transaction_type,
                                    'security_id': sec_id, 'symbol': sym,
                                    'price': 0.0, 'qty': abs_qty, 'target_points': 0.0, 'sl_points': 0.0,
                                    'status': resp.get('orderStatus', 'SUBMITTED'),
                                    'timestamp': datetime.now(self.config.TIMEZONE).isoformat()
                                })
                                
                                # Log to CSV
                                log_trade_event({
                                    'timestamp': datetime.now(self.config.TIMEZONE).isoformat(),
                                    'instrument': self.name, 'signal': "exit", 'leg': sym, 'action': transaction_type,
                                    'symbol': sym, 'security_id': sec_id,
                                    'price': 0.0, 'qty': abs_qty, 'atr': 0.0, 'delta': 0.0,
                                    'target_points': 0.0, 'sl_points': 0.0, 'order_id': order_id,
                                    'status': resp.get('orderStatus', 'SUBMITTED'), 'account': acc_name
                                }, self.config.TRADE_LOG_CSV, self.logger)
                                
                                # Send Telegram alert
                                if self.alert_manager:
                                    self.alert_manager.send_alert(
                                        f"🚨 *Dynamic Exit Triggered*\n"
                                        f"*Instrument:* `{self.name}`\n"
                                        f"*Strategy:* `{clean_source}`\n"
                                        f"*Account:* `{acc_name}`\n"
                                        f"*Position Closed:* `{sym}`\n"
                                        f"*Qty:* `{net_qty}`\n"
                                        f"*Reason:* `{reason}`\n"
                                        f"*Exit Order ID:* `{order_id}`",
                                        header="Dynamic Exit"
                                    )
                            else:
                                self.logger.error(f"[{self.name}] [DYNAMIC EXIT] Failed to place close order for {sym} on {acc_name}")
                                
            except Exception as e:
                self.logger.exception(f"[{self.name}] Error checking/executing dynamic exits for account '{acc_name}': {e}")

    def _execute_calendar_spread_strategy(self, signal: str, atr_val: float, source: str):
        """Execute Strategy 20 (3:1:1 Calendar Spread) sequentially across active accounts (BUY Long Legs first)."""
        inst_config = self.get_strategy_instrument_config(source)
        spot_close = float(self.df_spot['close'].iloc[-1]) if self.df_spot is not None and not self.df_spot.empty else 0.0
        regime_stance = getattr(self.df_spot, 'regime', ['PUT_CALENDAR'])[-1] if hasattr(self.df_spot, 'regime') else ("PUT_CALENDAR" if signal.upper() == "SELL" else "CALL_CALENDAR")
        
        self.logger.info(f"[{self.name}] Executing Strategy 20 Calendar Spread: Stance={regime_stance}, Spot={spot_close}")
        if inst_config.get("trade_both_sides", 0) == 1:
            self.logger.info(f"[{self.name}] DUAL STANCE ENABLED: Resolving BOTH Call & Put Calendar Spreads...")
            call_legs = choose_calendar_spread_v2(self.data_api, spot_close, stance="CALL_CALENDAR", instrument_config=inst_config)
            put_legs = choose_calendar_spread_v2(self.data_api, spot_close, stance="PUT_CALENDAR", instrument_config=inst_config)
            cal_legs = (call_legs or []) + (put_legs or [])
        else:
            cal_legs = choose_calendar_spread_v2(self.data_api, spot_close, stance=regime_stance, instrument_config=inst_config)
            
        if not cal_legs:
            self.logger.error(f"[{self.name}] Strategy 20 Calendar Spread leg resolution failed.")
            return

        # Pre-trade margin check via Dhan API v2
        scrip_list = [
            {
                "exchangeSegment": inst_config.get("option_segment", "NSE_FNO"),
                "transactionType": leg["action"],
                "quantity": leg["quantity"],
                "productType": "MARGIN",
                "securityId": str(leg["security_id"]),
                "price": float(leg["ltp"])
            } for leg in cal_legs
        ]
        margin_resp = self.data_api.calculate_multi_order_margin(scrip_list)
        
        # Determine for each account whether it already holds the monthly long legs
        # and execute the legs selectively per account to implement Mode B rollover.
        accounts = self.order_manager.get_accounts()
        prefix = inst_config.get('fno_prefix', self.name).upper()
        
        for acc in accounts:
            acc_name = acc['name']
            acc_api = acc['api']
            acc_config = acc.get('config', {})
            
            # --- STRATEGY ROUTING FILTER ---
            allowed_strategies = acc_config.get('allowed_strategies')
            if allowed_strategies is not None and "Strategy_20" not in allowed_strategies:
                self.logger.debug(f"[{self.name}] [SKIP] Strategy_20 for '{acc_name}' restricted. Not in allowed_strategies.")
                continue
                
            allowed_instruments = acc_config.get('allowed_instruments')
            if allowed_instruments is not None and self.name not in allowed_instruments:
                self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. Not in allowed_instruments.")
                continue
                
            try:
                positions = acc_api.get_positions()
            except Exception as e:
                self.logger.error(f"[{self.name}] Failed to fetch positions for rollover check on '{acc_name}': {e}")
                positions = []
                
            legs_to_execute = []
            for leg in cal_legs:
                if leg["action"] == "BUY" and leg["tag"] == "LONG_MONTHLY":
                    is_held = False
                    target_strike = float(leg["strike"])
                    target_expiry = leg["expiry"]
                    target_type = "CE" if leg["option_type"] == 'C' else "PE"
                    
                    for pos in positions:
                        qty = safe_int(pos.get('netQty', 0))
                        if qty > 0:
                            sym = pos.get('tradingSymbol', '').upper()
                            if sym.startswith(prefix) and sym.endswith(target_type):
                                pos_strike = float(pos.get('strikePrice', 0.0))
                                pos_expiry = str(pos.get('expiryDate', '')).split(' ')[0]
                                if abs(pos_strike - target_strike) < 1.0 and pos_expiry == target_expiry:
                                    is_held = True
                                    self.logger.info(f"[{self.name}] Monthly Long Leg {sym} (Strike {target_strike}, Expiry {target_expiry}) is ALREADY HELD in '{acc_name}'. Skipping BUY order.")
                                    break
                    if not is_held:
                        legs_to_execute.append(leg)
                else:
                    legs_to_execute.append(leg)
                    
            if not legs_to_execute:
                continue
                
            # Pre-trade margin check via Dhan API v2 for this account
            scrip_list = [
                {
                    "exchangeSegment": inst_config.get("option_segment", "NSE_FNO"),
                    "transactionType": leg["action"],
                    "quantity": leg["quantity"],
                    "productType": "MARGIN",
                    "securityId": str(leg["security_id"]),
                    "price": float(leg["ltp"])
                } for leg in legs_to_execute
            ]
            try:
                margin_resp = self.data_api.calculate_multi_order_margin(scrip_list)
            except Exception as e:
                self.logger.warning(f"[{self.name}] Pre-trade margin calculation failed for '{acc_name}': {e}")
                    # Get account multiplier (default: 1.0)
            multiplier = float(acc_config.get('global_multiplier', 1.0))
            
            # Staged Order Execution for this account: BUY legs first, then SELL legs
            buy_legs = [l for l in legs_to_execute if l["action"] == "BUY"]
            sell_legs = [l for l in legs_to_execute if l["action"] == "SELL"]
            
            # 1. Place BUY legs (if any are not already held)
            buy_success = True
            for leg in buy_legs:
                allowed_actions = acc_config.get('allowed_actions')
                if allowed_actions is not None and "BUY" not in allowed_actions:
                    self.logger.warning(f"[{self.name}] [SKIP] Stage 1 Long Leg for '{acc_name}' restricted. BUY not in allowed_actions.")
                    continue
                
                allowed_option_types = acc_config.get('allowed_option_types')
                leg_opt_type = "CE" if leg["option_type"] == 'C' else "PE"
                if allowed_option_types is not None and leg_opt_type not in allowed_option_types:
                    self.logger.warning(f"[{self.name}] [SKIP] Stage 1 Long Leg for '{acc_name}' restricted. Option type {leg_opt_type} not in allowed_option_types.")
                    continue
                
                order_qty = int(leg["quantity"] * multiplier)
                self._enforce_order_stagger()
                resp = acc_api.place_order(
                    security_id=leg["security_id"],
                    transaction_type="BUY",
                    quantity=order_qty,
                    exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                    product_type="MARGIN",
                    order_type="MARKET",
                    price=leg["ltp"]
                )
                self.logger.info(f"[{self.name}] Stage 1 Long Leg Order Executed ({acc_name}): {leg['tag']} (Qty: {order_qty}) -> {resp}")
                
                # Check status and extract orderId
                order_id = None
                order_status_val = None
                if resp and resp.get('status') == 'success':
                    data = resp.get('data', {})
                    if isinstance(data, dict):
                        order_id = data.get('orderId')
                        order_status_val = data.get('orderStatus')
                
                if order_status_val == 'REJECTED':
                    self.logger.error(f"[{self.name}] Stage 1 BUY order was REJECTED immediately by broker. Aborting spread placement.")
                    buy_success = False
                    continue

                if order_id:
                    self.logger.info(f"[{self.name}] Polling status for BUY order {order_id} to ensure execution before selling...")
                    is_filled = False
                    status = 'TRANSIT'
                    for attempt in range(12):  # Poll for up to 6 seconds
                        time.sleep(0.5)
                        status = acc_api.get_order_status(order_id)
                        self.logger.debug(f"[{self.name}] BUY order {order_id} status check {attempt+1}: {status}")
                        if status == 'TRADED':
                            is_filled = True
                            self.logger.info(f"[{self.name}] BUY order {order_id} is FILLED (TRADED). Proceeding to Stage 2.")
                            break
                        elif status in ['REJECTED', 'CANCELLED']:
                            self.logger.error(f"[{self.name}] BUY order {order_id} was {status}! Aborting SELL leg placement.")
                            break
                    
                    if not is_filled:
                        self.logger.error(f"[{self.name}] BUY order {order_id} failed to fill in time (status: {status}). Aborting SELL leg placement.")
                        buy_success = False
                        continue
                else:
                    self.logger.error(f"[{self.name}] Failed to retrieve orderId for BUY order. Aborting SELL leg placement.")
                    buy_success = False
                    continue

                sym = f"{prefix}-{leg['expiry']}-{leg['strike']}-{leg_opt_type}"
                pos_key = self._make_position_key(acc_name, "Strategy_20", leg["security_id"])
                with self.state.lock:
                    self.state.positions[pos_key] = {
                        'security_id': str(leg["security_id"]),
                        'symbol': sym,
                        'instrument': self.name,
                        'account': acc_name,
                        'strategy': "Strategy_20",
                        'leg': leg_opt_type,
                        'action': "BUY",
                        'qty': order_qty,
                        'product_type': "MARGIN",
                        'exchange_segment': inst_config.get("option_segment", "NSE_FNO"),
                        'exit_mode': "SWING",
                        'created_at': datetime.now(self.config.TIMEZONE).isoformat()
                    }
                self.state.save_state()
                
            # Wait brief extra moment for margin benefit to settle in broker risk systems
            if buy_legs and sell_legs and buy_success:
                time.sleep(0.2)
                
            # 2. Place SELL legs (weekly short legs)
            if buy_success:
                for leg in sell_legs:
                    allowed_actions = acc_config.get('allowed_actions')
                    if allowed_actions is not None and "SELL" not in allowed_actions:
                        self.logger.warning(f"[{self.name}] [SKIP] Stage 2 Short Leg for '{acc_name}' restricted. SELL not in allowed_actions.")
                        continue

                    # BUG-C1 FIX: allowed_option_types check and all per-leg processing
                    # must be indented inside the for-loop (was at account level before).
                    allowed_option_types = acc_config.get('allowed_option_types')
                    leg_opt_type = "CE" if leg["option_type"] == 'C' else "PE"
                    if allowed_option_types is not None and leg_opt_type not in allowed_option_types:
                        self.logger.warning(f"[{self.name}] [SKIP] Stage 2 Short Leg for '{acc_name}' restricted. Option type {leg_opt_type} not in allowed_option_types.")
                        continue

                    order_qty = int(leg["quantity"] * multiplier)
                    self._enforce_order_stagger()
                    resp = acc_api.place_order(
                        security_id=leg["security_id"],
                        transaction_type="SELL",
                        quantity=order_qty,
                        exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                        product_type="MARGIN",
                        order_type="MARKET",
                        price=leg["ltp"]
                    )
                    # Check status and extract orderStatus
                    order_status_val = None
                    if resp and resp.get('status') == 'success':
                        data = resp.get('data', {})
                        if isinstance(data, dict):
                            order_status_val = data.get('orderStatus')

                    if resp and order_status_val != 'REJECTED':
                        sym = f"{prefix}-{leg['expiry']}-{leg['strike']}-{leg_opt_type}"
                        pos_key = self._make_position_key(acc_name, "Strategy_20", leg["security_id"])
                        with self.state.lock:
                            self.state.positions[pos_key] = {
                                'security_id': str(leg["security_id"]),
                                'symbol': sym,
                                'instrument': self.name,
                                'account': acc_name,
                                'strategy': "Strategy_20",
                                'leg': leg_opt_type,
                                'action': "SELL",
                                'qty': order_qty,
                                'product_type': "MARGIN",
                                'exchange_segment': inst_config.get("option_segment", "NSE_FNO"),
                                'exit_mode': "SWING",
                                'created_at': datetime.now(self.config.TIMEZONE).isoformat()
                            }
                        self.state.save_state()
                    else:
                        self.logger.error(f"[{self.name}] Stage 2 SELL order REJECTED or failed for leg {leg.get('strike')} {leg_opt_type} on '{acc_name}'. Resp: {resp}")
                    
        self.strategy_cooldowns["Strategy_20"] = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)

    def _execute_multi_leg_strategy(self, strategy_mode: str, signal: str, atr_val: float, source: str):
        """Execute a multi-leg option strategy in a margin-safe sequential manner (BUY legs first)."""
        self.logger.info(f"[{self.name}] Resolving option strategy legs for mode: {strategy_mode}")
        legs = choose_strategy_instruments(
            self.data_api, signal, strategy_mode, self.config.INSTRUMENTS[self.name], self.logger
        )
        
        if not legs:
            self.logger.error(f"[{self.name}] Option strategy leg resolution failed.")
            return

        # Gate Keeper Validation Check
        inst_config = self.config.INSTRUMENTS[self.name]
        if inst_config.get("gatekeeper_enabled", 0) == 1:
            for leg in legs:
                strike = leg['item']['strike']
                type_str = leg['item']['type']
                is_short = (leg['action'] == 'SELL')
                if not self._validate_gatekeeper_live(strike, type_str, is_short=is_short):
                    self.logger.warning(f"[{self.name}] [GATEKEEPER] Skipping multi-leg strategy strategy_mode={strategy_mode} entry due to validation failure on leg {strike} {type_str}.")
                    return

        # 1. Max Active check at the strategy level (respecting independent CE/PE limits rule)
        eligible_accounts = []
        all_accounts = self.order_manager.get_accounts()
        
        # Count CE and PE legs in the strategy
        num_ce_legs = len([l for l in legs if l['item']['type'] == 'CE'])
        num_pe_legs = len([l for l in legs if l['item']['type'] == 'PE'])
        
        for acc in all_accounts:
            acc_name = acc['name']
            acc_api = acc['api']
            acc_config = acc.get('config', {})
            
            allowed_instruments = acc_config.get('allowed_instruments')
            if allowed_instruments is not None and self.name not in allowed_instruments:
                self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. Not in allowed_instruments.")
                continue
                
            overrides = acc_config.get('instrument_overrides', {}).get(self.name, {})
            strat_config = self.get_strategy_instrument_config(source)
            acc_max_active = overrides.get(
                'max_active_per_strategy',
                overrides.get('max_active', acc_config.get('max_active', strat_config.get('max_active_per_strategy', strat_config.get('max_active', inst_config.get('max_active', self.MAX_ACTIVE)))))
            )
            acc_daily_limit = overrides.get(
                'daily_limit_per_strategy',
                overrides.get('daily_limit', acc_config.get('daily_limit', strat_config.get('daily_limit_per_strategy', strat_config.get('daily_limit', self.DAILY_LIMIT)))))
            
            strat_counts = self.daily_trade_counts.setdefault(source, {})
            if strat_counts.get(acc_name, 0) >= acc_daily_limit:
                self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Daily Limit Reached for {source}.")
                continue
            
            # Check Max Daily SL Circuit Breaker
            acc_max_sl = overrides.get(
                'max_daily_sl_per_strategy',
                overrides.get('max_daily_sl', acc_config.get('max_daily_sl', strat_config.get('max_daily_sl_per_strategy', strat_config.get('max_daily_sl', inst_config.get('max_daily_sl', None)))))
            )
            if acc_max_sl is not None:
                strat_sls = self.daily_sl_counts.setdefault(source, {})
                if strat_sls.get(acc_name, 0) >= acc_max_sl:
                    self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Max Daily SL Reached for {source} ({strat_sls.get(acc_name, 0)}/{acc_max_sl}). Circuit breaker active.")
                    continue
                
            try:
                ce_count = self._count_my_active_positions(None, "CE", strategy_name=source, account_name=acc_name)
                pe_count = self._count_my_active_positions(None, "PE", strategy_name=source, account_name=acc_name)
                
                # CE and PE limits are tracked independently
                is_eligible = True
                if num_ce_legs > 0:
                    active_ce_trades = math.ceil(ce_count / num_ce_legs)
                    if active_ce_trades >= acc_max_active:
                        self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' has reached Max Active CE strategy trades ({active_ce_trades}/{acc_max_active}).")
                        is_eligible = False
                if is_eligible and num_pe_legs > 0:
                    active_pe_trades = math.ceil(pe_count / num_pe_legs)
                    if active_pe_trades >= acc_max_active:
                        self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' has reached Max Active PE strategy trades ({active_pe_trades}/{acc_max_active}).")
                        is_eligible = False
                        
                if not is_eligible:
                    continue
                    
                eligible_accounts.append(acc)
                self.logger.info(f"[{self.name}] Account '{acc_name}' is eligible for strategy trade (Active CE: {ce_count}/{acc_max_active * num_ce_legs}, PE: {pe_count}/{acc_max_active * num_pe_legs}).")
                
            except Exception as e:
                self.logger.error(f"[{self.name}] Failed to check positions for '{acc_name}' in multi-leg strategy: {e}")
                continue
                
        if not eligible_accounts:
            self.logger.warning(f"[{self.name}] No eligible accounts for multi-leg strategy execution (all at Max Active limits or restricted).")
            return
            
        buy_legs = [l for l in legs if l['action'] == 'BUY']
        sell_legs = [l for l in legs if l['action'] == 'SELL']
        
        # Track active execution set of accounts
        active_strategy_accounts = list(eligible_accounts)
        traded_accounts = set()
        
        # 1. Place BUY legs first (long legs establish margin hedging)
        if buy_legs:
            self.logger.info(f"[{self.name}] Placing BUY legs first (establishing hedge)...")
            for leg in buy_legs:
                if not active_strategy_accounts:
                    break
                leg_accounts = [
                    a for a in active_strategy_accounts
                    if a.get('config', {}).get('allowed_option_types') is None or leg['leg_type'] in a.get('config', {}).get('allowed_option_types')
                ]
                if not leg_accounts:
                    continue
                accs = self._place_batch(
                    [leg['item']], leg['action'], leg['leg_type'], atr_val, signal, source,
                    bypass_max_active_check=True, accounts=leg_accounts
                )
                failed_eligible = [a['name'] for a in leg_accounts if a['name'] not in accs]
                active_strategy_accounts = [a for a in active_strategy_accounts if a['name'] not in failed_eligible]
                if accs:
                    traded_accounts.update(accs)
                    
        # 2. Wait for order registration / margin benefit to apply
        if buy_legs and sell_legs and active_strategy_accounts:
            self.logger.info(f"[{self.name}] Pausing 500ms to allow margin benefit to register...")
            time.sleep(0.5)
            
        # 3. Place SELL legs next (short legs benefit from hedge margin)
        if sell_legs and active_strategy_accounts:
            self.logger.info(f"[{self.name}] Placing SELL legs next...")
            for leg in sell_legs:
                if not active_strategy_accounts:
                    break
                leg_accounts = [
                    a for a in active_strategy_accounts
                    if a.get('config', {}).get('allowed_option_types') is None or leg['leg_type'] in a.get('config', {}).get('allowed_option_types')
                ]
                if not leg_accounts:
                    continue
                accs = self._place_batch(
                    [leg['item']], leg['action'], leg['leg_type'], atr_val, signal, source,
                    bypass_max_active_check=True, accounts=leg_accounts
                )
                failed_eligible = [a['name'] for a in leg_accounts if a['name'] not in accs]
                active_strategy_accounts = [a for a in active_strategy_accounts if a['name'] not in failed_eligible]
                if accs:
                    traded_accounts.update(accs)
                    
        # 4. Update trade counts and cooldowns
        for acc in traded_accounts:
            strat_counts = self.daily_trade_counts.setdefault(source, {})
            strat_counts[acc] = strat_counts.get(acc, 0) + 1
            
        if traded_accounts:
            self.logger.info(f"[{self.name}] Trade Counts Updated: {self.daily_trade_counts}")
            self.strategy_cooldowns[source] = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)
            self.logger.info(f"[{self.name}] Strategy cooldown activated for {source}. Locked until {self.strategy_cooldowns[source].strftime('%H:%M:%S')}")

    def _count_my_active_positions(self, positions, leg_type=None, strategy_name: Optional[str] = None, account_name: Optional[str] = None):
        inst_config = self.config.INSTRUMENTS[self.name]
        execution_mode = inst_config.get('execution_mode', 'OPTION')
        
        if strategy_name:
            # Query local state positions filtered by strategy
            ce_count = 0
            pe_count = 0
            stock_count = 0
            with self.state.lock:
                for p in self.state.positions.values():
                    if p.get('instrument') == self.name and p.get('strategy') == strategy_name:
                        if account_name and p.get('account') != account_name:
                            continue
                        p_leg = p.get('leg')
                        if not p_leg:
                            sym = p.get('symbol', '').upper()
                            if sym.endswith('CE'):
                                p_leg = 'CE'
                            elif sym.endswith('PE'):
                                p_leg = 'PE'
                        if p_leg == 'CE':
                            ce_count += 1
                        elif p_leg == 'PE':
                            pe_count += 1
                        elif p_leg == 'STOCK':
                            stock_count += 1
                        else:
                            ce_count += 1
                            pe_count += 1
            if leg_type == "CE":
                return ce_count
            elif leg_type == "PE":
                return pe_count
            elif leg_type == "STOCK":
                return stock_count
            else:
                return max(ce_count, pe_count, stock_count)
                
        if execution_mode == 'STOCK':
            underlying_id = str(inst_config['security_id'])
            stock_count = 0
            if positions:
                for pos in positions:
                    qty = safe_int(pos.get('netQty', 0))
                    if qty != 0:
                        pos_sec_id = str(pos.get('securityId', ''))
                        if pos_sec_id == underlying_id:
                            stock_count += 1
            return stock_count

        ce_count = 0
        pe_count = 0
        prefix = inst_config['fno_prefix']
        if positions:
            for pos in positions:
                 qty = safe_int(pos.get('netQty', 0))
                 if qty != 0:
                     sym = pos.get('tradingSymbol', '').upper()
                     if sym.startswith(prefix.upper()):
                         if sym.endswith('CE'):
                             ce_count += 1
                         elif sym.endswith('PE'):
                             pe_count += 1
                         else:
                             ce_count += 1
                             
        if leg_type == "CE":
            return ce_count
        elif leg_type == "PE":
            return pe_count
        else:
            return max(ce_count, pe_count)


    def _place_batch(self, items, action, leg_type, atr_val, signal, source, bypass_max_active_check: bool = False, accounts: Optional[List[Dict]] = None):
        success_accounts = set()
        successful_trades = [] # List of {symbol, ltp, total_qty, sl, tp}
        
        for i, item in enumerate(items):
            sec_id = item['id']
            delta = item.get('delta', self.config.OPTION_DELTA)
            if delta is None: delta = self.config.OPTION_DELTA
            delta = abs(delta)
            
            inst_config = self.get_strategy_instrument_config(source)
            
            # --- Get LTP First ---
            execution_mode = inst_config.get('execution_mode', 'OPTION')
            if execution_mode == 'STOCK':
                opt_seg = inst_config.get('exchange_segment', 'NSE_EQ')
                delta = 1.0
            else:
                opt_seg = inst_config.get('option_segment', 'NSE_FNO')
                
            ltp = 0.0
            # Quick LTP
            try:
                resp = self.data_api._make_request(self.data_api.dhan.ohlc_data, securities={opt_seg: [int(sec_id)]})
                if resp:
                    d = resp.get('data', {}).get(opt_seg, {}).get(str(sec_id), {})
                    ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
            except Exception as e:
                self.logger.debug(f"[{self.name}] Quick LTP fetch failed for {sec_id}: {e}")
            
            # Fallback
            if ltp <= 0:
                if self.TYPE == 'OPTION':
                    hist_inst_type = inst_config.get('instrument_type')
                    if not hist_inst_type:
                        fno_prefix = inst_config.get('fno_prefix', self.name).upper()
                        if any(x in fno_prefix for x in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY']):
                            hist_inst_type = 'OPTIDX'
                        else:
                            hist_inst_type = 'OPTSTK'
                else:
                    hist_inst_type = 'EQUITY' if execution_mode == 'STOCK' else 'OPTIDX'
                df = self.data_api.get_historical_data(sec_id, 1, opt_seg, hist_inst_type)
                if df is not None and not df.empty: ltp = float(df.iloc[-1]['close'])
            
            if ltp <= 0:
                 self.logger.error(f"[{self.name}] No Price for {sec_id}. Skipping.")
                 continue
            
            # Dynamic SL, Trailing, and Target Multipliers based on Action
            if action == 'BUY':
                sl_mult = inst_config.get('sl_mult_buy', self.config.ATR_SL_MULTIPLIER)
                trail_mult = inst_config.get('trailing_mult_buy', self.config.ATR_TRAIL_MULTIPLIER_BUY)
                tp_mult = inst_config.get('tp_mult_buy', self.config.ATR_TP_MULTIPLIER)
            else: # SELL
                sl_mult = inst_config.get('sl_mult_sell', self.config.ATR_SL_MULTIPLIER)
                trail_mult = inst_config.get('trailing_mult_sell', self.config.ATR_TRAIL_MULTIPLIER_SELL)
                tp_mult = inst_config.get('tp_mult_sell', self.config.ATR_TP_MULTIPLIER)

            # Points Calculation
            spot_sl = atr_val * sl_mult
            spot_tp = atr_val * tp_mult
            spot_trail = atr_val * trail_mult
            
            opt_sl = round(spot_sl * delta, 1)
            opt_trail = round(spot_trail * delta, 1)
            
            exit_mode = inst_config.get("exit_mode", "ATR")
            local_exit_monitoring = inst_config.get("local_exit_monitoring")
            if local_exit_monitoring is None:
                if exit_mode in ["SWING", "SWING_CONTRACT", "POINTS"]:
                    local_exit_monitoring = True
                else:
                    local_exit_monitoring = False

            spot_sl_price = 0.0
            spot_target_price = 0.0
            opt_sl_price = 0.0
            opt_target_price = 0.0
            contract_atr_val = 0.0
            
            if exit_mode == "SWING":
                if self.df_spot is not None and not self.df_spot.empty:
                    swing_window = inst_config.get("swing_window_size", 10)
                    recent_df = self.df_spot.tail(swing_window)
                    spot_lows = recent_df['low']
                    spot_highs = recent_df['high']
                    spot_close_val = recent_df['close'].iloc[-1]
                    
                    sl_buffer = atr_val * inst_config.get("sl_buffer_atr_mult", 0.2)
                    spot_is_bearish = (leg_type == "PE" and action == "BUY") or (leg_type == "CE" and action == "SELL") or (leg_type == "STOCK" and action == "SELL")
                    
                    if not spot_is_bearish:
                        spot_sl_price = float(spot_lows.min() - sl_buffer)
                        spot_target_price = float(spot_close_val + (atr_val * tp_mult))
                    else:
                        spot_sl_price = float(spot_highs.max() + sl_buffer)
                        spot_target_price = float(spot_close_val - (atr_val * tp_mult))
                    
                    self.logger.info(f"[{self.name}] SWING exit calculations: spot_is_bearish={spot_is_bearish}, spot_sl_price={spot_sl_price:.2f}, spot_target_price={spot_target_price:.2f}")
                else:
                    self.logger.warning(f"[{self.name}] self.df_spot is empty or None! Falling back to ATR exit mode.")
                    exit_mode = "ATR"
            elif exit_mode == "SWING_CONTRACT":
                swing_window = inst_config.get("swing_window_size", 10)
                sl_buffer_atr_mult = inst_config.get("sl_buffer_atr_mult", 0.2)
                
                if execution_mode == "STOCK":
                    if self.df_spot is not None and not self.df_spot.empty:
                        recent_df = self.df_spot.tail(swing_window)
                        contract_lows = recent_df['low']
                        contract_highs = recent_df['high']
                        contract_atr_val = atr_val
                    else:
                        self.logger.warning(f"[{self.name}] self.df_spot is empty/None for STOCK SWING_CONTRACT! Falling back to entry LTP.")
                        contract_atr_val = atr_val
                        contract_lows = pd.Series([ltp])
                        contract_highs = pd.Series([ltp])
                else:
                    hist_inst_type = 'OPTIDX' if self.TYPE == 'INDEX' else 'OPTSTK'
                    opt_df = self.data_api.get_historical_data(
                        security_id=sec_id,
                        interval=1,
                        exchange_segment=opt_seg,
                        instrument_type=hist_inst_type
                    )
                    if opt_df is not None and not opt_df.empty:
                        if ta is not None:
                            opt_atr_series = ta.atr(opt_df['high'], opt_df['low'], opt_df['close'], length=self.config.ATR_PERIOD)
                        else:
                            high_low = opt_df['high'] - opt_df['low']
                            high_cp = (opt_df['high'] - opt_df['close'].shift(1)).abs()
                            low_cp = (opt_df['low'] - opt_df['close'].shift(1)).abs()
                            tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
                            opt_atr_series = tr.rolling(window=14).mean()
                            
                        if not opt_atr_series.empty:
                            contract_atr_val = opt_atr_series.ffill().bfill().iloc[-1]
                        else:
                            contract_atr_val = atr_val * delta
                            
                        if pd.isna(contract_atr_val) or np.isnan(contract_atr_val) or contract_atr_val <= 0:
                            contract_atr_val = atr_val * delta
                            
                        recent_opt = opt_df.tail(swing_window)
                        contract_lows = recent_opt['low']
                        contract_highs = recent_opt['high']
                    else:
                        self.logger.warning(f"[{self.name}] Option hist df empty/None for {sec_id}. Falling back to default ATR/LTP.")
                        contract_atr_val = atr_val * delta
                        contract_lows = pd.Series([ltp])
                        contract_highs = pd.Series([ltp])
                        
                sl_buffer = contract_atr_val * sl_buffer_atr_mult
                min_low = contract_lows.min()
                if pd.isna(min_low) or np.isnan(min_low):
                    min_low = ltp
                max_high = contract_highs.max()
                if pd.isna(max_high) or np.isnan(max_high):
                    max_high = ltp
                    
                if action == 'BUY':
                    opt_sl_price = float(min_low - sl_buffer)
                    target_inr = inst_config.get('profit_target_buy', 0)
                    if target_inr > 0:
                        lot_size = inst_config.get('lot_size', 1) or 1
                        opt_tp_pts = target_inr / lot_size
                        opt_target_price = float(ltp + opt_tp_pts)
                    else:
                        opt_target_price = float(ltp + (contract_atr_val * tp_mult))
                else: # SELL
                    opt_sl_price = float(max_high + sl_buffer)
                    target_inr = inst_config.get('profit_target_sell', 0)
                    if target_inr > 0:
                        lot_size = inst_config.get('lot_size', 1) or 1
                        opt_tp_pts = target_inr / lot_size
                        opt_target_price = float(ltp - opt_tp_pts)
                    else:
                        opt_target_price = float(ltp - (contract_atr_val * tp_mult))
                    
                if opt_sl_price <= 0 and action == 'BUY':
                    opt_sl_price = 0.05
                if opt_target_price <= 0 and action == 'SELL':
                    opt_target_price = 0.05
                    
                self.logger.info(f"[{self.name}] SWING_CONTRACT exit calculations: action={action}, opt_sl_price={opt_sl_price:.2f}, opt_target_price={opt_target_price:.2f}, contract_atr={contract_atr_val:.2f}")
            elif exit_mode == "POINTS":
                points_sl_buy = float(inst_config.get("points_sl_buy", 0))
                points_target_buy = float(inst_config.get("points_target_buy", 0))
                points_trail_buy = float(inst_config.get("points_trail_buy", 0))
                points_sl_sell = float(inst_config.get("points_sl_sell", 0))
                points_target_sell = float(inst_config.get("points_target_sell", 0))
                points_trail_sell = float(inst_config.get("points_trail_sell", 0))
                
                # Dynamic High Conviction Target Override
                if inst_config.get('enable_dynamic_conviction', False) and self.df_spot is not None and not self.df_spot.empty:
                    clean_source = source.split(" (")[0].replace(" ", "_")
                    conv_col = f'Conviction_{clean_source}' if f'Conviction_{clean_source}' in self.df_spot.columns else (
                        f'Conviction_{source}' if f'Conviction_{source}' in self.df_spot.columns else (
                            'Conviction' if 'Conviction' in self.df_spot.columns else None
                        )
                    )
                    conv_score = 1.0
                    if conv_col:
                        c_val = self.df_spot[conv_col].iloc[-1]
                        if pd.notna(c_val) and float(c_val) >= 1.5:
                            conv_score = float(c_val)
                        elif len(self.df_spot) >= 2:
                            prev_c_val = self.df_spot[conv_col].iloc[-2]
                            if pd.notna(prev_c_val) and float(prev_c_val) >= 1.5:
                                conv_score = float(prev_c_val)
                                
                    if conv_score >= 1.5:
                        target_high = inst_config.get("points_target_high_conviction", inst_config.get("points_target_sell_high_conviction" if action == "SELL" else "points_target_buy_high_conviction"))
                        if target_high is not None:
                            if action == "SELL":
                                points_target_sell = float(target_high)
                                self.logger.info(f"[{self.name}] [{source}] High Conviction: Dynamic Target expanded to {points_target_sell} pts!")
                            else:
                                points_target_buy = float(target_high)
                                self.logger.info(f"[{self.name}] [{source}] High Conviction: Dynamic Target expanded to {points_target_buy} pts!")
                
                if action == 'BUY':
                    opt_sl_price = float(ltp - points_sl_buy) if points_sl_buy > 0 else 0.0
                    opt_target_price = float(ltp + points_target_buy) if points_target_buy > 0 else 999999.0
                    contract_atr_val = float(points_trail_buy)
                    opt_sl = points_sl_buy
                    opt_trail = points_trail_buy
                else: # SELL
                    opt_sl_price = float(ltp + points_sl_sell) if points_sl_sell > 0 else 999999.0
                    opt_target_price = float(ltp - points_target_sell) if points_target_sell > 0 else 0.05
                    contract_atr_val = float(points_trail_sell)
                    opt_sl = points_sl_sell
                    opt_trail = points_trail_sell
                    
                if opt_sl_price <= 0 and action == 'BUY':
                    opt_sl_price = 0.05
                if opt_target_price <= 0 and action == 'SELL':
                    opt_target_price = 0.05
                    
                self.logger.info(f"[{self.name}] POINTS exit calculations: action={action}, opt_sl_price={opt_sl_price:.2f}, opt_target_price={opt_target_price:.2f}, trail_points={contract_atr_val:.2f}")
            else: # ATR mode
                if local_exit_monitoring:
                    if action == 'BUY':
                        opt_sl_price = max(0.05, ltp - opt_sl)
                        opt_target_price = ltp + opt_tp
                    else: # SELL
                        opt_sl_price = ltp + opt_sl
                        opt_target_price = max(0.05, ltp - opt_tp)
                    contract_atr_val = opt_trail
                    self.logger.info(f"[{self.name}] ATR local exit calculations: action={action}, opt_sl_price={opt_sl_price:.2f}, opt_target_price={opt_target_price:.2f}, trail_points={contract_atr_val:.2f}")
            
            # Determine breakeven multiplier and initial SL points
            if exit_mode == "POINTS":
                breakeven_mult = float(inst_config.get("points_be_buy" if action == "BUY" else "points_be_sell", 0.0))
            else:
                breakeven_mult = float(inst_config.get("atr_be_buy" if action == "BUY" else "atr_be_sell", 0.0))
            
            if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"]:
                initial_sl_points = abs(ltp - opt_sl_price) if (opt_sl_price > 0 and opt_sl_price != 999999.0) else 0.0
            else:
                initial_sl_points = abs(self.df_spot['close'].iloc[-1] - spot_sl_price) if self.df_spot is not None and spot_sl_price > 0 else 0.0

            # (LTP already fetched and validated at start of loop)

            # --- Target Calculation (Hybrid: Fixed vs ATR vs Max Premium) ---
            target_inr = 0.0
            
            if exit_mode == "POINTS":
                opt_tp = points_target_buy if action == 'BUY' else points_target_sell
            else:
                opt_tp = 0.0
                if action == 'BUY':
                    target_inr = self.config.INSTRUMENTS[self.name].get('profit_target_buy', 0)
                    if target_inr > 0:
                         lot_size = self.config.INSTRUMENTS[self.name].get('lot_size', 1)
                         opt_tp = round(target_inr / lot_size, 1)
                         self.logger.info(f"[{self.name}] BUY Using Fixed Target: {target_inr} INR / {lot_size} Qty = {opt_tp} pts")
                    else:
                         opt_tp = round(spot_tp * delta, 1)
                         self.logger.info(f"[{self.name}] BUY Using ATR Target (Config=0): {opt_tp} pts")
                
                else: # SELL Order
                    target_inr = self.config.INSTRUMENTS[self.name].get('profit_target_sell', 0)
                    if target_inr > 0:
                         lot_size = self.config.INSTRUMENTS[self.name].get('lot_size', 1)
                         opt_tp = round(target_inr / lot_size, 1)
                         self.logger.info(f"[{self.name}] SELL Using Fixed Target: {target_inr} INR / {lot_size} Qty = {opt_tp} pts")
                    else:
                         target_type = inst_config.get("short_option_target_type")
                         if not target_type:
                             target_type = "ATR" if execution_mode == 'STOCK' else "MAX_PROFIT"
                             
                         decay_val = float(inst_config.get("short_option_decay_value", 0.05))
                         if target_type == "ATR":
                             opt_tp = round(spot_tp * delta, 1)
                             self.logger.info(f"[{self.name}] SELL Using ATR Target: {opt_tp} pts")
                         else:  # MAX_PROFIT
                             opt_tp = round(ltp - decay_val, 1)
                             if opt_tp <= 0:
                                 opt_tp = round(spot_tp * delta, 1)
                             self.logger.info(f"[{self.name}] SELL Using Max Target (LTP-{decay_val}): {opt_tp} pts")

                         # Floor Protection: Cap target points to prevent negative cover price for options
                         if self.TYPE == 'OPTION' or inst_config.get('type') == 'OPTION':
                             max_tp_pts = round(ltp - decay_val, 1)
                             if opt_tp > max_tp_pts:
                                 opt_tp = max(max_tp_pts, 0.0)
                                 self.logger.info(f"[{self.name}] SELL Target points capped to {opt_tp} to prevent negative cover price (Floor: {decay_val} Rs)")

            # Base Quantity
            if execution_mode == 'STOCK':
                stock_qty_override = inst_config.get('stock_qty_override')
                if stock_qty_override is not None:
                    base_qty = int(stock_qty_override)
                    unscaled_qty = base_qty
                    unit_lot_size = 1
                else:
                    lots = inst_config.get(f'num_lots_{action.lower()}', 1)
                    unit_lot_size = inst_config.get('lot_size', 1)
                    base_qty = unit_lot_size * lots
                    unscaled_qty = base_qty
            else:
                base_lots = inst_config.get(f'num_lots_{action.lower()}', 1)
                lots = base_lots
                # Dynamic Conviction Sizing for Option Strategies (e.g. Strategy 22 / Strategy 3)
                if inst_config.get('enable_dynamic_conviction', False) and action == 'SELL' and self.df_spot is not None and not self.df_spot.empty:
                    conv_score = 1.0
                    clean_source = source.split(" (")[0].replace(" ", "_")
                    conv_col = f'Conviction_{clean_source}' if f'Conviction_{clean_source}' in self.df_spot.columns else (
                        f'Conviction_{source}' if f'Conviction_{source}' in self.df_spot.columns else (
                            'Conviction' if 'Conviction' in self.df_spot.columns else None
                        )
                    )
                    if conv_col:
                        c_val = self.df_spot[conv_col].iloc[-1]
                        if pd.notna(c_val) and float(c_val) >= 1.5:
                            conv_score = float(c_val)
                        elif len(self.df_spot) >= 2:
                            prev_c_val = self.df_spot[conv_col].iloc[-2]
                            if pd.notna(prev_c_val) and float(prev_c_val) >= 1.5:
                                conv_score = float(prev_c_val)
                                
                    if conv_score >= 1.5:
                        lots = inst_config.get('num_lots_high_conviction', lots)
                        self.logger.info(f"[{self.name}] [{source}] High Conviction Detected ({conv_col}={conv_score:.1f})! Sizing scaled from {inst_config.get('num_lots_sell', 1)} to {lots} lots.")

                unit_lot_size = inst_config.get('lot_size', 1)
                unscaled_qty = unit_lot_size * base_lots
                base_qty = unit_lot_size * lots
            
            # Get List of Accounts
            if accounts is None:
                accounts = self.order_manager.get_accounts()
            item_total_qty = 0
            item_success = False
            
            # 1. Filter and resolve parameters for eligible accounts
            eligible_dispatches = []
            for acc in accounts:
                acc_name = acc['name']
                acc_api = acc['api']
                acc_config = acc.get('config', {})
                
                # --- MASTER/SECONDARY ENFORCEMENT ---
                allowed_strategies = acc_config.get('allowed_strategies')
                clean_source = source.split(" (")[0].replace(" ", "_")
                if allowed_strategies is not None and clean_source not in allowed_strategies:
                    self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. Strategy '{clean_source}' not in allowed_strategies.")
                    continue

                allowed_actions = acc_config.get('allowed_actions')
                if allowed_actions is not None and action not in allowed_actions:
                    self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. {action} not in allowed_actions.")
                    continue
                    
                allowed_option_types = acc_config.get('allowed_option_types')
                if allowed_option_types is not None and leg_type in ['CE', 'PE'] and leg_type not in allowed_option_types:
                    self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. Option type {leg_type} not in allowed_option_types.")
                    continue
                    
                allowed_instruments = acc_config.get('allowed_instruments')
                if allowed_instruments is not None and self.name not in allowed_instruments:
                    self.logger.debug(f"[{self.name}] [SKIP] '{acc_name}' restricted. Not in allowed_instruments.")
                    continue

                # --- LIMIT OVERRIDES ---
                overrides = acc_config.get('instrument_overrides', {}).get(self.name, {})
                strat_config = self.get_strategy_instrument_config(source)
                acc_max_active = overrides.get(
                    'max_active_per_strategy',
                    overrides.get('max_active', acc_config.get('max_active', strat_config.get('max_active_per_strategy', strat_config.get('max_active', inst_config.get('max_active', self.MAX_ACTIVE)))))
                )
                acc_daily_limit = overrides.get(
                    'daily_limit_per_strategy',
                    overrides.get('daily_limit', acc_config.get('daily_limit', strat_config.get('daily_limit_per_strategy', strat_config.get('daily_limit', self.DAILY_LIMIT)))))
                
                strat_counts = self.daily_trade_counts.setdefault(source, {})
                if strat_counts.get(acc_name, 0) >= acc_daily_limit:
                    self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Daily Limit Reached for {source}.")
                    continue
                
                # --- PER-ACCOUNT SAFETY CHECK ---
                if not bypass_max_active_check:
                    try:
                        pos_list = self.order_manager.position_manager.get_cached_positions(acc_name)
                        active_qty = self._count_my_active_positions(pos_list, leg_type, strategy_name=source, account_name=acc_name)
                        if active_qty >= acc_max_active:
                            self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Max Active Reached for strategy '{source}'.")
                            continue
                    except Exception as e:
                        self.logger.error(f"[{self.name}] Failed to check positions for '{acc_name}': {e}")
                        continue
                
                # --- QUANTITY OVERRIDES ---
                override_lots = overrides.get(f'num_lots_{action.lower()}')
                if override_lots is not None:
                    if execution_mode == 'STOCK' and inst_config.get('stock_qty_override') is not None:
                        qty_unit = inst_config.get('stock_qty_override', inst_config.get('lot_size', 1))
                        acc_qty = int(qty_unit * override_lots)
                        acc_base_qty = acc_qty
                    else:
                        acc_qty = int(self.config.INSTRUMENTS[self.name]['lot_size'] * override_lots)
                        acc_base_qty = acc_qty
                else:
                    multiplier = float(acc_config.get('global_multiplier', 1.0))
                    acc_qty = max(1, int(base_qty * multiplier)) if base_qty > 0 else 0
                    acc_base_qty = max(1, int(unscaled_qty * multiplier)) if unscaled_qty > 0 else acc_qty
                
                if acc_qty == 0:
                    continue
                
                # --- PRODUCT TYPE DETERMINATION ---
                if execution_mode == 'STOCK':
                    inst_product_type = overrides.get('product_type') or inst_config.get('product_type', 'INTRADAY')
                else:
                    inst_product_type = overrides.get('product_type') or inst_config.get('product_type', self.config.PRODUCT_TYPE)

                # --- PLACE LIMIT ORDER (MARKET GUARD) ---
                buffer_points = max(1.0, ltp * 0.01)
                raw_limit = (ltp + buffer_points) if action == 'BUY' else (ltp - buffer_points)
                limit_price = round(raw_limit * 20) / 20.0 # Snap to Indian market 0.05 tick size
                
                broker_safety_sl = inst_config.get("broker_safety_sl", True)
                if local_exit_monitoring and broker_safety_sl:
                    # Option 3 (Crash-Proof Hybrid): Place Dhan Super Order with exchange-held Hard SL
                    api_opt_tp = opt_tp
                    api_opt_sl = opt_sl
                    api_opt_trail = 0.0 # Local monitor dynamically moves SL to breakeven
                elif local_exit_monitoring and not broker_safety_sl:
                    api_opt_tp = 0.0
                    api_opt_sl = 0.0
                    api_opt_trail = 0.0
                else:
                    api_opt_tp = opt_tp
                    api_opt_sl = opt_sl
                    api_opt_trail = opt_trail
                
                eligible_dispatches.append({
                    'acc_name': acc_name,
                    'acc_api': acc_api,
                    'acc_qty': acc_qty,
                    'base_qty': acc_base_qty,
                    'lot_size': unit_lot_size,
                    'limit_price': limit_price,
                    'api_opt_tp': api_opt_tp,
                    'api_opt_sl': api_opt_sl,
                    'api_opt_trail': api_opt_trail,
                    'inst_product_type': inst_product_type
                })

            # 2. Concurrently Dispatch Order Placement
            if eligible_dispatches:
                futures = {}
                for dispatch in eligible_dispatches:
                    acc_name = dispatch['acc_name']
                    self.logger.info(f"[{self.name}] [EXEC] Placing {action} concurrently for '{acc_name}' (x{dispatch['acc_qty']}) | Type: LIMIT | Limit: {dispatch['limit_price']} (LTP: {ltp})")
                    
                    # Wrap the SDK call in a stagger lambda so it blocks globally in worker thread
                    def make_call(d=dispatch):
                        self._enforce_order_stagger()
                        return d['acc_api'].place_entry_order(
                            security_id=sec_id,
                            transaction_type=action,
                            quantity=d['acc_qty'],
                            order_type="LIMIT",
                            price=d['limit_price'],
                            target_points=d['api_opt_tp'],
                            sl_points=d['api_opt_sl'],
                            trailing_jump=d['api_opt_trail'],
                            exchange_segment=opt_seg,
                            product_type=d['inst_product_type'],
                            ref_price=ltp
                        )
                        
                    futures[acc_name] = self.order_manager.executor.submit(make_call)

                # 3. Gather Results and Update State
                for dispatch in eligible_dispatches:
                    acc_name = dispatch['acc_name']
                    future = futures.get(acc_name)
                    if future:
                        try:
                            resp = future.result(timeout=15)
                            is_success = resp and not resp.get('failed', False) and resp.get('orderStatus') in ['PENDING', 'TRANSIT', 'TRADED', 'SUBMITTED', 'SUCCESS']
                            
                            if not is_success:
                                reject_reason = "Order returned empty or rejected by broker"
                                if isinstance(resp, dict):
                                    reject_reason = (
                                        resp.get('omsErrorDescription') or 
                                        resp.get('remarks') or 
                                        (resp.get('data', {}).get('omsErrorDescription') if isinstance(resp.get('data'), dict) else '') or 
                                        resp.get('message') or
                                        f"Status: {resp.get('orderStatus', 'FAILED')}"
                                    )
                                
                                # Check for Graceful Margin Downsizing Fallback (Option 1)
                                if self._is_margin_rejection(reject_reason, resp):
                                    lot_unit = dispatch.get('lot_size', 1)
                                    fallback_candidates = []
                                    # Candidate 1: Base unscaled lots
                                    if dispatch['acc_qty'] > dispatch.get('base_qty', 0) and dispatch.get('base_qty', 0) > 0:
                                        fallback_candidates.append(dispatch['base_qty'])
                                    # Candidate 2: 1 lot minimum viable position
                                    if dispatch.get('base_qty', 0) > lot_unit and lot_unit not in fallback_candidates:
                                        fallback_candidates.append(lot_unit)
                                    elif dispatch['acc_qty'] > lot_unit and lot_unit not in fallback_candidates:
                                        fallback_candidates.append(lot_unit)
                                    
                                    for fallback_qty in fallback_candidates:
                                        orig_lots = max(1, dispatch['acc_qty'] // lot_unit)
                                        fb_lots = max(1, fallback_qty // lot_unit)
                                        self.logger.warning(
                                            f"[{self.name}] [{clean_source}] [MARGIN FALLBACK] Order of {orig_lots} lots ({dispatch['acc_qty']} qty) "
                                            f"rejected for '{acc_name}' due to margin shortfall ({reject_reason}). "
                                            f"Immediately retrying at {fb_lots} lots ({fallback_qty} qty)..."
                                        )
                                        self._enforce_order_stagger()
                                        fb_resp = dispatch['acc_api'].place_entry_order(
                                            security_id=sec_id,
                                            transaction_type=action,
                                            quantity=fallback_qty,
                                            order_type="LIMIT",
                                            price=dispatch['limit_price'],
                                            target_points=dispatch['api_opt_tp'],
                                            sl_points=dispatch['api_opt_sl'],
                                            trailing_jump=dispatch['api_opt_trail'],
                                            exchange_segment=opt_seg,
                                            product_type=dispatch['inst_product_type'],
                                            ref_price=ltp
                                        )
                                        if fb_resp and not fb_resp.get('failed', False) and fb_resp.get('orderStatus') in ['PENDING', 'TRANSIT', 'TRADED', 'SUBMITTED', 'SUCCESS']:
                                            self.logger.info(
                                                f"[{self.name}] [{clean_source}] [MARGIN FALLBACK SUCCESS] Resized order filled at {fb_lots} lots ({fallback_qty} qty) for '{acc_name}'!"
                                            )
                                            resp = fb_resp
                                            dispatch['acc_qty'] = fallback_qty
                                            is_success = True
                                            if self.alert_manager:
                                                self.alert_manager.send_alert(
                                                    f"⚠️ *[MARGIN DOWNSIZED]* High Conviction Order Resized\n"
                                                    f"🔹 *Instrument:* `{self.name}`\n"
                                                    f"🔹 *Strategy:* `{clean_source}`\n"
                                                    f"🔹 *Account:* `{acc_name}`\n"
                                                    f"🔹 *Original Request:* `{orig_lots} lots` ({orig_lots * lot_unit} qty)\n"
                                                    f"🔹 *Downsized Fill:* `{fb_lots} lots` ({fallback_qty} qty)\n"
                                                    f"⚠️ *Broker Shortfall:* `{reject_reason}`\n"
                                                    f"✅ *Position active at {fb_lots} lots!*",
                                                    header="Margin Fallback Filled"
                                                )
                                            break
                                        else:
                                            if isinstance(fb_resp, dict):
                                                reject_reason = fb_resp.get('omsErrorDescription') or fb_resp.get('remarks') or fb_resp.get('message') or reject_reason

                            if is_success:
                                success_accounts.add(acc_name)
                                item_total_qty += dispatch['acc_qty']
                                item_success = True
                                order_id = str(resp.get('orderId') or (resp.get('data', {}).get('orderId') if isinstance(resp.get('data'), dict) else 'unknown'))
                                
                                self.state.add_order(order_id, {
                                    'order_id': order_id, 'account': acc_name, 'instrument': self.name,
                                    'type': f"{self.config.INSTRUMENTS[self.name]['fno_prefix']}_{leg_type}_{action}", 
                                    'signal': signal, 'leg': leg_type, 'action': action,
                                    'security_id': sec_id, 'symbol': item.get('symbol', sec_id),
                                    'price': ltp, 'qty': dispatch['acc_qty'], 'target_points': opt_tp, 'sl_points': opt_sl,
                                    'status': resp.get('orderStatus', 'SUBMITTED'),
                                    'timestamp': datetime.now(self.config.TIMEZONE).isoformat(),
                                    'exit_mode': exit_mode,
                                    'spot_sl_price': spot_sl_price,
                                    'spot_target_price': spot_target_price,
                                    'opt_sl_price': opt_sl_price if local_exit_monitoring and exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else 0.0,
                                    'opt_target_price': opt_target_price if local_exit_monitoring and exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else 0.0,
                                    'Breakeven_Mult': breakeven_mult,
                                    'Initial_SL_Points': initial_sl_points,
                                    'Breakeven_Triggered': False
                                })

                                # For SWING exit mode, track the position in state
                                if local_exit_monitoring:
                                    pos_key = self._make_position_key(acc_name, clean_source, sec_id)
                                    with self.state.lock:
                                        self.state.positions[pos_key] = {
                                            'security_id': str(sec_id),
                                            'symbol': item.get('symbol', sec_id),
                                            'instrument': self.name,
                                            'account': acc_name,
                                            'strategy': clean_source,
                                            'leg': leg_type,
                                            'action': action,
                                            'qty': dispatch['acc_qty'],
                                            'product_type': dispatch['inst_product_type'],
                                            'exchange_segment': opt_seg,
                                            'exit_mode': exit_mode,
                                            'spot_sl_price': spot_sl_price,
                                            'spot_target_price': spot_target_price,
                                            'spot_initial_sl': spot_sl_price,
                                            'spot_mfe': self.df_spot['close'].iloc[-1] if self.df_spot is not None else ltp,
                                            'spot_atr': atr_val,
                                            'Entry_Spot': self.df_spot['close'].iloc[-1] if self.df_spot is not None else ltp,
                                            'Entry_Price': ltp,
                                            'order_id': order_id,
                                            'created_at': datetime.now(self.config.TIMEZONE).isoformat(),
                                            'opt_sl_price': opt_sl_price,
                                            'opt_target_price': opt_target_price,
                                            'opt_initial_sl': opt_sl_price,
                                            'opt_mfe': ltp,
                                            'opt_atr': contract_atr_val,
                                            'Breakeven_Mult': breakeven_mult,
                                            'Initial_SL_Points': initial_sl_points,
                                            'Breakeven_Triggered': False
                                        }
                                    self.state.save_state()

                                log_trade_event({
                                    'timestamp': datetime.now(self.config.TIMEZONE).isoformat(),
                                    'instrument': self.name, 'signal': signal, 'leg': leg_type, 'action': action,
                                    'symbol': item.get('symbol', sec_id), 'security_id': sec_id,
                                    'price': ltp, 'qty': dispatch['acc_qty'], 'atr': atr_val, 'delta': delta,
                                    'target_points': opt_tp, 'sl_points': opt_sl, 'order_id': order_id,
                                    'status': resp.get('orderStatus', 'SUBMITTED'), 'account': acc_name
                                }, self.config.TRADE_LOG_CSV, self.logger)
                            else:
                                self.logger.error(f"[{self.name}] [{clean_source}] Order placement failed/rejected for '{acc_name}' on {sec_id}. Reason: {reject_reason}")
                                if self.alert_manager:
                                    self.alert_manager.send_alert(
                                        f"❌ *Order Placement Failed / Rejected*\n"
                                        f"🔹 *Instrument:* `{self.name}`\n"
                                        f"🔹 *Strategy:* `{clean_source}`\n"
                                        f"🔹 *Account:* `{acc_name}`\n"
                                        f"🔹 *Leg:* `{leg_type} {action}`\n"
                                        f"⚠️ *Reason:* `{reject_reason}`",
                                        header="Order Rejected"
                                    )
                        except Exception as e:
                            self.logger.error(f"[{self.name}] Async dispatch result error for '{acc_name}': {e}")
                            if self.alert_manager:
                                self.alert_manager.send_alert(
                                    f"❌ *Order Placement Exception*\n"
                                    f"🔹 *Instrument:* `{self.name}`\n"
                                    f"🔹 *Strategy:* `{clean_source}`\n"
                                    f"🔹 *Account:* `{acc_name}`\n"
                                    f"⚠️ *Error:* `{e}`",
                                    header="Order Error"
                                )
                
            if item_success:
                if local_exit_monitoring:
                    abs_tp = opt_target_price if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else spot_target_price
                    abs_sl = opt_sl_price if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else spot_sl_price
                    successful_trades.append({
                        'symbol': item.get('symbol', sec_id),
                        'price': ltp,
                        'qty': item_total_qty,
                        'sl_pts': abs(opt_sl_price - ltp) if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else (abs(spot_sl_price - self.df_spot['close'].iloc[-1]) if self.df_spot is not None else 0.0),
                        'tp_pts': abs(opt_target_price - ltp) if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else (abs(spot_target_price - self.df_spot['close'].iloc[-1]) if self.df_spot is not None else 0.0),
                        'tr_pts': 0.0,
                        'abs_sl': abs_sl,
                        'abs_tp': abs_tp,
                        'is_swing': True,
                        'exit_mode': exit_mode
                    })
                else:
                    # Calculate absolute target prices natively used by Dhan API for Super Orders
                    if action == 'BUY':
                        abs_tp = ltp + opt_tp
                        abs_sl = max(0.05, ltp - opt_sl)
                    else: # SELL
                        abs_tp = max(0.05, ltp - opt_tp)
                        abs_sl = ltp + opt_sl

                    successful_trades.append({
                        'symbol': item.get('symbol', sec_id),
                        'price': ltp,
                        'qty': item_total_qty,
                        'sl_pts': opt_sl,
                        'tp_pts': opt_tp,
                        'tr_pts': opt_trail,
                        'abs_sl': abs_sl,
                        'abs_tp': abs_tp,
                        'is_swing': False,
                        'exit_mode': exit_mode
                    })
                
            time.sleep(0.2)
        
        # --- SEND TELEGRAM NOTIFICATION ---
        if successful_trades and self.alert_manager:
            acc_list = sorted(list(success_accounts))
            acc_str = f"{acc_list[0]} (+{len(acc_list)-1} others)" if len(acc_list) > 1 else acc_list[0]
            
            # Create a combined message for all successful items in this batch
            trade_reports = []
            for trade in successful_trades:
                if trade.get('is_swing'):
                    mode_label = trade.get('exit_mode', 'SWING')
                    report = (
                        f"📎 *Symbol:* `{trade['symbol']}`\n"
                        f"💰 *Entry Price:* {trade['price']:.2f} (Ref) | *Total Qty:* {trade['qty']}\n"
                        f"🛡️ *SL:* {trade['abs_sl']:.2f} | *TP:* {trade['abs_tp']:.2f} ({mode_label} mode)"
                    )
                else:
                    report = (
                        f"📎 *Symbol:* `{trade['symbol']}`\n"
                        f"💰 *Entry Price:* {trade['price']:.2f} (Ref) | *Total Qty:* {trade['qty']}\n"
                        f"🛡️ *SL:* {trade['abs_sl']:.2f} ({trade['sl_pts']:.1f} pts) | *TP:* {trade['abs_tp']:.2f} ({trade['tp_pts']:.1f} pts)\n"
                        f"📈 *Trailing Jump:* {trade['tr_pts']:.1f} pts"
                    )
                trade_reports.append(report)
            
            trades_msg = "\n\n".join(trade_reports)
            full_msg = (
                f"{trades_msg}\n\n"
                f"📡 *Signal:* {signal.upper()} → 📂 *Action:* {action} | *Leg:* {leg_type}\n"
                f"👤 *Accounts:* {acc_str}\n"
                f"📊 *Source:* {source}"
            )
            self.alert_manager.send_alert(full_msg, header="Trade Executed")
            
        return success_accounts

    def _local_monitoring_loop(self):
        """High-frequency python-side monitoring loop for Spot-based exits."""
        self.logger.info(f"[{self.name}] Starting local stop monitoring loop...")
        while self.running:
            try:
                # 1. Check if we have active positions in self.state.positions
                # Filter to positions of this instrument that have exit_mode == "SWING" or "SWING_CONTRACT"
                with self.state.lock:
                    swing_positions = {
                        pos_key: pos for pos_key, pos in self.state.positions.items()
                        if pos.get('instrument') == self.name
                    }
                
                if not swing_positions:
                    time.sleep(5)
                    continue
                
                # 2. Verify against broker actual positions to prevent double execution or sync issues
                accounts = self.order_manager.get_accounts()
                for acc in accounts:
                    acc_name = acc['name']
                    acc_api = acc['api']
                    
                    try:
                        pos_list = self.order_manager.position_manager.get_cached_positions(acc_name)
                        if not pos_list:
                            continue
                        
                        # Find open positions for this instrument in this account
                        open_broker_positions = {}
                        for pos in pos_list:
                            net_qty = safe_int(pos.get('netQty', 0))
                            if net_qty != 0:
                                open_broker_positions[str(pos.get('securityId'))] = pos
                        
                        # Check each swing position
                        for pos_key, position in list(swing_positions.items()):
                            if position.get('account') != acc_name:
                                continue
                                
                            sec_id = str(position.get('security_id', ''))
                            if sec_id not in open_broker_positions:
                                # Position already closed on broker or not open yet. Clean up local state if created > 2 mins ago to avoid race conditions on entry
                                created_str = position.get('created_at', position.get('timestamp'))
                                if created_str:
                                    created_dt = datetime.fromisoformat(created_str)
                                    if (datetime.now(self.config.TIMEZONE) - created_dt).total_seconds() > 120:
                                        strat_name = position.get('strategy', 'Unknown')
                                        closed_broker_pos = [p for p in pos_list if str(p.get('securityId')) == sec_id and safe_int(p.get('netQty', 0)) == 0]
                                        if closed_broker_pos:
                                            realized_pnl = float(closed_broker_pos[0].get('realizedProfit', 0.0))
                                            if realized_pnl < 0:
                                                strat_sls = self.daily_sl_counts.setdefault(strat_name, {})
                                                strat_sls[acc_name] = strat_sls.get(acc_name, 0) + 1
                                                self.logger.warning(f"[{self.name}] Broker closed position with loss ({realized_pnl:.2f}). Recorded Daily SL for {strat_name} on {acc_name} ({strat_sls[acc_name]}).")
                                                log_trade_event({
                                                    'timestamp': datetime.now(self.config.TIMEZONE).isoformat(),
                                                    'instrument': self.name, 'signal': "StopLoss", 'leg': position.get('symbol', sec_id),
                                                    'action': "CLOSE", 'symbol': position.get('symbol', sec_id), 'security_id': sec_id,
                                                    'price': 0.0, 'qty': position.get('qty', 0), 'atr': 0.0, 'delta': 0.0,
                                                    'target_points': 0.0, 'sl_points': 0.0, 'order_id': position.get('order_id', ''),
                                                    'status': "CLOSED_SL", 'account': acc_name, 'strategy': strat_name, 'exit_reason': "StopLoss_Broker"
                                                }, self.config.TRADE_LOG_CSV, self.logger)
                                        self.logger.info(f"[{self.name}] Cleaning up stale local position state for {pos_key} ({sec_id})")
                                        with self.state.lock:
                                            self.state.positions.pop(pos_key, None)
                                        self.state.save_state()
                                continue
                                
                            # EOD Auto Square-off check if carry_forward is False for this strategy
                            now_time = datetime.now(self.config.TIMEZONE).time()
                            strat_name = position.get('strategy', 'Strategy_3')
                            if now_time >= self.config.SQ_OFF_TIME and not self.should_carry_forward(strat_name):
                                sym = open_broker_positions[sec_id].get('tradingSymbol', sec_id)
                                net_qty = safe_int(open_broker_positions[sec_id].get('netQty', 0))
                                abs_qty = abs(net_qty)
                                self.logger.warning(f"[{self.name}] [EOD SQUAREOFF] Closing position {sym} (x{abs_qty}) on {acc_name}: strategy {strat_name} carry_forward is False.")
                                
                                # Cancel pending orders for this contract
                                try:
                                    pending = acc_api.get_pending_orders()
                                    pos_pending = [o for o in pending if str(o.get('securityId')) == sec_id]
                                    for o in pos_pending:
                                        acc_api.cancel_order(o.get('orderId'))
                                except Exception as e:
                                    self.logger.error(f"[{self.name}] Error cancelling pending orders on exit: {e}")
                                    
                                # Place EOD Cover Order
                                close_action = 'SELL' if net_qty > 0 else 'BUY'
                                exch = open_broker_positions[sec_id].get('exchangeSegment', 'NSE_FNO')
                                product = open_broker_positions[sec_id].get('productType', 'MARGIN')
                                
                                resp = acc_api.place_order(
                                    security_id=sec_id,
                                    transaction_type=close_action,
                                    quantity=abs_qty,
                                    exchange_segment=exch,
                                    product_type=product,
                                    order_type="MARKET",
                                    price=0.0,
                                    should_slice=(exch in ['NSE_FNO', 'BSE_FNO'])
                                )
                                if resp:
                                    self.logger.warning(f"[{self.name}] [EOD SQUAREOFF] Position closed successfully: {resp}")
                                    with self.state.lock:
                                        self.state.positions.pop(pos_key, None)
                                    self.state.save_state()
                                    
                                    if self.alert_manager:
                                        msg = (
                                            f"🚨 *EOD Position Closed:* `{sym}`\n"
                                            f"📊 *Strategy:* `{strat_name}`\n"
                                            f"📊 *Reason:* carry_forward is False\n"
                                            f"👤 *Account:* {acc_name}"
                                        )
                                        self.alert_manager.send_alert(msg, header="Trade Closed")
                                continue
                                
                            # If it is open, check the exit mode logic
                            pos_exit_mode = position.get('exit_mode', 'SWING')
                            if pos_exit_mode in ['SWING_CONTRACT', 'POINTS', 'ATR']:
                                opt_seg = position.get('exchange_segment', 'NSE_FNO')
                                contract_ltp = 0.0
                                try:
                                    sec_id_lookup = int(sec_id) if str(sec_id).isdigit() else sec_id
                                    resp = self.data_api._make_request(self.data_api.dhan.ohlc_data, securities={opt_seg: [sec_id_lookup]})
                                    if resp and isinstance(resp.get('data'), dict):
                                        seg_data = resp['data'].get(opt_seg, {})
                                        d = seg_data.get(str(sec_id), {}) or seg_data.get(sec_id_lookup, {}) if isinstance(seg_data, dict) else {}
                                        contract_ltp = float(d.get('last_price', 0) or d.get('ltp', 0) or d.get('close', 0))
                                except Exception as e:
                                    self.logger.error(f"[{self.name}] Error fetching Contract LTP in monitor for {sec_id}: {e}")
                                
                                if contract_ltp <= 0:
                                    contract_ltp = float(open_broker_positions[sec_id].get('lastPrice', 0) or open_broker_positions[sec_id].get('ltp', 0))
                                    
                                if contract_ltp <= 0:
                                    continue
                                    
                                action = position.get('action')
                                if pos_exit_mode == 'POINTS':
                                    trail_jump = position.get('opt_atr', 0.0) # For POINTS mode, opt_atr stores raw trail_points
                                else:
                                    trail_mult = self.config.INSTRUMENTS[self.name].get('trailing_mult_sell' if action == 'SELL' else 'trailing_mult_buy', 1.6)
                                    opt_atr = position.get('opt_atr', 1.0)
                                    trail_jump = opt_atr * trail_mult
                                
                                # 1. Check Breakeven Trigger
                                updated = False
                                hit_sl = False
                                hit_target = False
                                with self.state.lock:
                                    be_mult = position.get("Breakeven_Mult", 0.0)
                                    if be_mult > 0.0 and not position.get("Breakeven_Triggered", False):
                                        if pos_exit_mode == 'POINTS':
                                            trigger_level = position["Entry_Price"] + be_mult if action == 'BUY' else position["Entry_Price"] - be_mult
                                        elif position.get("Initial_SL_Points", 0.0) > 0.0:
                                            trigger_level = position["Entry_Price"] + (position["Initial_SL_Points"] * be_mult) if action == 'BUY' else position["Entry_Price"] - (position["Initial_SL_Points"] * be_mult)
                                        else:
                                            trigger_level = None

                                        if trigger_level is not None:
                                            be_hit = False
                                            if action == 'BUY' and contract_ltp >= trigger_level:
                                                position["opt_sl_price"] = max(position["opt_sl_price"], position["Entry_Price"])
                                                position["Breakeven_Triggered"] = True
                                                self.logger.info(f"[{self.name}] [BREAKEVEN SL TRIGGER] Moved SL to entry: {position['opt_sl_price']:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                updated = True
                                                be_hit = True
                                            elif action == 'SELL' and contract_ltp <= trigger_level:
                                                position["opt_sl_price"] = min(position["opt_sl_price"], position["Entry_Price"])
                                                position["Breakeven_Triggered"] = True
                                                self.logger.info(f"[{self.name}] [BREAKEVEN SL TRIGGER] Moved SL to entry: {position['opt_sl_price']:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                updated = True
                                                be_hit = True

                                            if be_hit:
                                                # Option 3 (Crash-Proof Hybrid): Modify resting STOP_LOSS_LEG on Dhan directly
                                                super_oid = position.get('order_id')
                                                if super_oid and acc_api:
                                                    try:
                                                        target_sym = open_broker_positions.get(sec_id, {}).get('tradingSymbol', sec_id)
                                                        mod_ok = acc_api.modify_super_order_sl(super_oid, position["Entry_Price"])
                                                        if mod_ok:
                                                            self.logger.info(f"[{self.name}] [BREAKEVEN BROKER MODIFIED] Dhan STOP_LOSS_LEG for order {super_oid} modified to Entry Price ({position['Entry_Price']:.2f})!")
                                                            if self.alert_manager:
                                                                self.alert_manager.send_alert(
                                                                    f"🛡️ *Breakeven Protected on Dhan*\n"
                                                                    f"• *Symbol:* `{target_sym}`\n"
                                                                    f"• *Account:* `{acc_name}`\n"
                                                                    f"• *Broker SL Updated:* `₹{position['Entry_Price']:.2f}` (Entry Price)\n"
                                                                    f"• *Status:* 100% Risk-Free (Exchange Protected)",
                                                                    header="Breakeven Order Modified"
                                                                )
                                                    except Exception as e:
                                                        self.logger.error(f"[{self.name}] Failed to modify STOP_LOSS_LEG on Dhan for order {super_oid}: {e}")

                                    if action == 'BUY':
                                        if contract_ltp > position.get('opt_mfe', position.get('Entry_Price', contract_ltp)):
                                            position['opt_mfe'] = contract_ltp
                                            updated = True
                                        if trail_jump > 0 and contract_ltp > position.get('Entry_Price', contract_ltp):
                                            steps = int((contract_ltp - position.get('Entry_Price', contract_ltp)) / trail_jump)
                                            if steps >= 1:
                                                new_sl = position.get('opt_initial_sl', position.get('opt_sl_price')) + (steps * trail_jump)
                                                if new_sl > position.get('opt_sl_price'):
                                                    position['opt_sl_price'] = new_sl
                                                    self.logger.info(f"[{self.name}] [TRAILING SL UPDATE] New Contract SL: {new_sl:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                    updated = True
                                                    
                                        hit_sl = (contract_ltp <= position.get('opt_sl_price'))
                                        hit_target = (contract_ltp >= position.get('opt_target_price'))
                                    else: # SELL
                                        if contract_ltp < position.get('opt_mfe', position.get('Entry_Price', contract_ltp)):
                                            position['opt_mfe'] = contract_ltp
                                            updated = True
                                        if trail_jump > 0 and contract_ltp < position.get('Entry_Price', contract_ltp):
                                            steps = int((position.get('Entry_Price', contract_ltp) - contract_ltp) / trail_jump)
                                            if steps >= 1:
                                                new_sl = position.get('opt_initial_sl', position.get('opt_sl_price')) - (steps * trail_jump)
                                                if new_sl < position.get('opt_sl_price'):
                                                    position['opt_sl_price'] = new_sl
                                                    self.logger.info(f"[{self.name}] [TRAILING SL UPDATE] New Contract SL: {new_sl:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                    updated = True
                                                    
                                        hit_sl = (contract_ltp >= position.get('opt_sl_price'))
                                        hit_target = (contract_ltp <= position.get('opt_target_price'))
                                
                                if updated:
                                    self.state.save_state()
                                    
                                current_ltp_ref = contract_ltp
                                sl_price_ref = position.get('opt_sl_price')
                                target_price_ref = position.get('opt_target_price')
                                mode_label = "CONTRACT"
                                
                            else: # SWING (Spot-based)
                                spot_sec_id = self.config.INSTRUMENTS[self.name]['security_id']
                                spot_seg = 'IDX_I' if self.TYPE != 'STOCK' else 'NSE_EQ'
                                spot_ltp = 0.0
                                try:
                                    resp = self.data_api._make_request(self.data_api.dhan.ohlc_data, securities={spot_seg: [int(spot_sec_id)]})
                                    if resp:
                                        d = resp.get('data', {}).get(spot_seg, {}).get(str(spot_sec_id), {})
                                        spot_ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
                                except Exception as e:
                                    self.logger.error(f"[{self.name}] Error fetching Spot LTP in monitor: {e}")
                                    
                                if spot_ltp <= 0:
                                    continue
                                    
                                # Determine Spot Direction
                                leg_type = position.get('leg')
                                action = position.get('action')
                                spot_is_bearish = (leg_type == "PE" and action == "BUY") or (leg_type == "CE" and action == "SELL") or (leg_type == "STOCK" and action == "SELL")
                                
                                # Trailing SL update logic
                                trail_mult = self.config.INSTRUMENTS[self.name].get('trailing_mult_sell' if action == 'SELL' else 'trailing_mult_buy', 1.6)
                                spot_atr = position.get('spot_atr', 10.0)
                                trail_jump = spot_atr * trail_mult
                                
                                updated = False
                                hit_sl = False
                                hit_target = False
                                with self.state.lock:
                                    if not spot_is_bearish:
                                        # Trailing check
                                        if spot_ltp > position['spot_mfe']:
                                            position['spot_mfe'] = spot_ltp
                                            updated = True
                                        if trail_jump > 0 and spot_ltp > position['Entry_Spot']:
                                            steps = int((spot_ltp - position['Entry_Spot']) / trail_jump)
                                            if steps >= 1:
                                                new_sl = position['spot_initial_sl'] + (steps * trail_jump)
                                                if new_sl > position['spot_sl_price']:
                                                    position['spot_sl_price'] = new_sl
                                                    self.logger.info(f"[{self.name}] [TRAILING SL UPDATE] New SL: {new_sl:.2f} (Spot LTP: {spot_ltp:.2f})")
                                                    updated = True
                                                    
                                        # Check exit conditions
                                        hit_sl = (spot_ltp <= position['spot_sl_price'])
                                        hit_target = (spot_ltp >= position['spot_target_price'])
                                    else:
                                        # Trailing check
                                        if spot_ltp < position['spot_mfe']:
                                            position['spot_mfe'] = spot_ltp
                                            updated = True
                                        if trail_jump > 0 and spot_ltp < position['Entry_Spot']:
                                            steps = int((position['Entry_Spot'] - spot_ltp) / trail_jump)
                                            if steps >= 1:
                                                new_sl = position['spot_initial_sl'] - (steps * trail_jump)
                                                if new_sl < position['spot_sl_price']:
                                                    position['spot_sl_price'] = new_sl
                                                    self.logger.info(f"[{self.name}] [TRAILING SL UPDATE] New SL: {new_sl:.2f} (Spot LTP: {spot_ltp:.2f})")
                                                    updated = True
                                                    
                                        # Check exit conditions
                                        hit_sl = (spot_ltp >= position['spot_sl_price'])
                                        hit_target = (spot_ltp <= position['spot_target_price'])
                                    
                                    sl_price_ref = position['spot_sl_price']
                                    target_price_ref = position['spot_target_price']
                                
                                if updated:
                                    self.state.save_state()
                                    
                                current_ltp_ref = spot_ltp
                                mode_label = "SPOT"
                                
                            if hit_sl or hit_target:
                                reason = "StopLoss" if hit_sl else "Target"
                                sym = open_broker_positions[sec_id].get('tradingSymbol', sec_id)
                                net_qty = safe_int(open_broker_positions[sec_id].get('netQty', 0))
                                abs_qty = abs(net_qty)
                                
                                self.logger.warning(f"[{self.name}] [{mode_label} EXIT TRIGGER] {sym} triggers {reason} ({mode_label} LTP: {current_ltp_ref:.2f}, SL: {sl_price_ref:.2f}, Target: {target_price_ref:.2f})")
                                
                                # Cancel pending orders for this contract
                                try:
                                    pending = acc_api.get_pending_orders()
                                    pos_pending = [o for o in pending if str(o.get('securityId')) == sec_id]
                                    for o in pos_pending:
                                        acc_api.cancel_order(o.get('orderId'))
                                except Exception as e:
                                    self.logger.error(f"[{self.name}] Error cancelling pending orders on exit: {e}")
                                    
                                # Close position with Market order
                                close_action = 'SELL' if net_qty > 0 else 'BUY'
                                exch = open_broker_positions[sec_id].get('exchangeSegment', 'NSE_FNO')
                                product = open_broker_positions[sec_id].get('productType', 'MARGIN')
                                
                                resp = acc_api.place_order(
                                    security_id=sec_id,
                                    transaction_type=close_action,
                                    quantity=abs_qty,
                                    exchange_segment=exch,
                                    product_type=product,
                                    order_type="MARKET",
                                    price=0.0,
                                    should_slice=(exch in ['NSE_FNO', 'BSE_FNO'])
                                )
                                
                                if resp:
                                    self.logger.warning(f"[{self.name}] Position closed successfully: {resp}")
                                    strat_name = position.get('strategy', 'Unknown')
                                    if hit_sl or "StopLoss" in reason or "SL" in reason:
                                        strat_sls = self.daily_sl_counts.setdefault(strat_name, {})
                                        strat_sls[acc_name] = strat_sls.get(acc_name, 0) + 1
                                        self.logger.warning(f"[{self.name}] Daily SL recorded for {strat_name} on {acc_name} (Current: {strat_sls[acc_name]}).")
                                        
                                    log_trade_event({
                                        'timestamp': datetime.now(self.config.TIMEZONE).isoformat(),
                                        'instrument': self.name, 'signal': reason, 'leg': sym, 'action': close_action,
                                        'symbol': sym, 'security_id': sec_id,
                                        'price': current_ltp_ref, 'qty': abs_qty, 'atr': 0.0, 'delta': 0.0,
                                        'target_points': 0.0, 'sl_points': 0.0, 'order_id': resp.get('orderId', ''),
                                        'status': resp.get('orderStatus', 'SUBMITTED'), 'account': acc_name,
                                        'strategy': strat_name, 'exit_reason': reason
                                    }, self.config.TRADE_LOG_CSV, self.logger)

                                    with self.state.lock:
                                        self.state.positions.pop(pos_key, None)
                                    self.state.save_state()
                                    
                                    if self.alert_manager:
                                        strat_name = position.get('strategy', 'Unknown')
                                        msg = (
                                            f"🚨 *Position Closed:* `{sym}`\n"
                                            f"📊 *Strategy:* `{strat_name}`\n"
                                            f"📊 *Reason:* {reason} ({mode_label} LTP: {current_ltp_ref:.2f})\n"
                                            f"🛡️ *Levels:* SL: {sl_price_ref:.2f} | Target: {target_price_ref:.2f}\n"
                                            f"👤 *Account:* {acc_name}"
                                        )
                                        self.alert_manager.send_alert(msg, header="Trade Closed")
                                        
                    except Exception as acc_err:
                        self.logger.error(f"[{self.name}] Error checking positions for {acc_name} in loop: {acc_err}")
                        
                # Check Strategy 20 Intraday Exits (35% SL / Target / EOD)
                try:
                    self._monitor_strategy20_exits()
                except Exception as e:
                    self.logger.error(f"[{self.name}] Error in Strategy 20 exit monitor: {e}")
                        
            except Exception as loop_err:
                self.logger.error(f"[{self.name}] Error in local stop monitor loop: {loop_err}")
                
            time.sleep(5)

    def _execute_option_selling(self, signal: str, spot_price: float, source: str):
        """Execute Option Writer live order placement on Dhan API."""
        if source in self.strategy_cooldowns:
            if datetime.now(self.config.TIMEZONE) < self.strategy_cooldowns[source]:
                self.logger.debug(f"[{self.name}] [SKIP] {source} is on cooldown until {self.strategy_cooldowns[source].strftime('%H:%M:%S')}")
                return

        strat_config = self.get_strategy_instrument_config(source)
        otm_offset = int(strat_config.get("otm_offset", 0))
        leg_sl_pct = float(strat_config.get("leg_sl_pct", 0.35))
        base_num_lots = int(strat_config.get("num_lots_sell", strat_config.get("num_lots", 1)))
        
        # Dynamic Conviction Sizing for Option Writing
        if strat_config.get('enable_dynamic_conviction', False) and self.df_spot is not None and not self.df_spot.empty:
            conv_score = 1.0
            clean_source = source.split(" (")[0].replace(" ", "_")
            conv_col = f'Conviction_{clean_source}' if f'Conviction_{clean_source}' in self.df_spot.columns else (
                f'Conviction_{source}' if f'Conviction_{source}' in self.df_spot.columns else (
                    'Conviction' if 'Conviction' in self.df_spot.columns else None
                )
            )
            if conv_col:
                c_val = self.df_spot[conv_col].iloc[-1]
                if pd.notna(c_val) and float(c_val) >= 1.5:
                    conv_score = float(c_val)
                elif len(self.df_spot) >= 2:
                    prev_c_val = self.df_spot[conv_col].iloc[-2]
                    if pd.notna(prev_c_val) and float(prev_c_val) >= 1.5:
                        conv_score = float(prev_c_val)
                        
            if conv_score >= 1.5:
                base_num_lots = int(strat_config.get('num_lots_high_conviction', base_num_lots))
                self.logger.info(f"[{self.name}] [{source}] High Conviction Detected ({conv_col}={conv_score:.1f})! Sizing scaled to {base_num_lots} lots.")
        
        inst_config = self.config.INSTRUMENTS[self.name]
        strike_step = int(inst_config.get("strike_step", 50))
        lot_size = int(inst_config.get("lot_size", 65))
        prefix = inst_config.get("fno_prefix", self.name).upper()
        
        atm_strike = int(round(spot_price / strike_step) * strike_step)
        
        sig_str = str(signal).upper()
        if sig_str in ("CALL", "BUY", "1", "+1"):  # Bullish trend -> Sell PE
            action_type = "PE"
            strike = atm_strike - otm_offset
        elif sig_str in ("PUT", "SELL", "-1"): # Bearish trend -> Sell CE
            action_type = "CE"
            strike = atm_strike + otm_offset
        else:
            return

        nearest_expiry = self._get_nearest_expiry(inst_config)

        try:
            sec_id = self.data_api.resolve_option_security_id(
                prefix=prefix,
                strike=strike,
                option_type=action_type,
                expiry_date=nearest_expiry,
                expiry_index=0
            )
        except Exception as e:
            self.logger.error(f"[{self.name}] [{source}] Failed to resolve option contract security ID: {e}")
            return

        if not sec_id:
            self.logger.error(f"[{self.name}] [{source}] Security ID for {strike} {action_type} not found.")
            return

        accounts = self.order_manager.get_accounts()
        for acc in accounts:
            acc_name = acc['name']
            acc_api = acc['api']
            acc_config = acc.get('config', {})
            
            allowed_strategies = acc_config.get('allowed_strategies')
            if allowed_strategies is not None and source not in allowed_strategies:
                continue
                
            # Check Max Active Limit for this account
            active_count = self._count_my_active_positions(None, strategy_name=source, account_name=acc_name)
            overrides = acc_config.get('instrument_overrides', {}).get(self.name, {})
            acc_max_active = overrides.get(
                'max_active_per_strategy',
                overrides.get('max_active', acc_config.get('max_active', strat_config.get('max_active_per_strategy', strat_config.get('max_active', inst_config.get('max_active', self.MAX_ACTIVE)))))
            )
            if active_count >= acc_max_active:
                self.logger.warning(f"[{self.name}] [{source}] [SKIP] Account '{acc_name}' has reached Max Active {source} trades ({active_count}/{acc_max_active}).")
                continue
                
            # Check Daily Limit for this account
            strat_counts = self.daily_trade_counts.setdefault(source, {})
            acc_daily_limit = overrides.get(
                'daily_limit_per_strategy',
                overrides.get('daily_limit', acc_config.get('daily_limit', strat_config.get('daily_limit_per_strategy', strat_config.get('daily_limit', self.DAILY_LIMIT)))))
            if strat_counts.get(acc_name, 0) >= acc_daily_limit:
                self.logger.warning(f"[{self.name}] [{source}] [SKIP] Account '{acc_name}' has reached Daily Limit for {source} ({strat_counts.get(acc_name, 0)}/{acc_daily_limit}).")
                continue
            
            # Check Max Daily SL Circuit Breaker
            acc_max_sl = overrides.get(
                'max_daily_sl_per_strategy',
                overrides.get('max_daily_sl', acc_config.get('max_daily_sl', strat_config.get('max_daily_sl_per_strategy', strat_config.get('max_daily_sl', inst_config.get('max_daily_sl', None)))))
            )
            if acc_max_sl is not None:
                strat_sls = self.daily_sl_counts.setdefault(source, {})
                if strat_sls.get(acc_name, 0) >= acc_max_sl:
                    self.logger.warning(f"[{self.name}] [{source}] [SKIP] Account '{acc_name}' has reached Max Daily SL for {source} ({strat_sls.get(acc_name, 0)}/{acc_max_sl}). Circuit breaker active.")
                    continue
                
            # Resolve Lots per Account (honoring account-level overrides and multipliers)
            override_lots = overrides.get('num_lots_sell', overrides.get('num_lots'))
            if override_lots is not None:
                acc_num_lots = int(override_lots)
            else:
                multiplier = float(acc_config.get('global_multiplier', 1.0))
                acc_num_lots = max(1, int(base_num_lots * multiplier)) if base_num_lots > 0 else 0
                
            if acc_num_lots <= 0:
                continue
                
            order_qty = acc_num_lots * lot_size
            
            self.logger.info(f"[{self.name}] [{source}] Placing LIVE SELL Market Order for '{acc_name}': {order_qty} qty of {prefix} {strike} {action_type} (sec_id: {sec_id})")
            
            resp = acc_api.place_order(
                security_id=sec_id,
                transaction_type="SELL",
                quantity=order_qty,
                exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                product_type="MARGIN",
                order_type="MARKET",
                price=0.0
            )
            
            order_status_val = None
            order_id = None
            if resp:
                order_id = str(resp.get('orderId') or (resp.get('data', {}).get('orderId') if isinstance(resp.get('data'), dict) else ''))
                order_status_val = str(resp.get('orderStatus') or (resp.get('data', {}).get('orderStatus') if isinstance(resp.get('data'), dict) else ''))

            is_sell_failed = not resp or resp.get('failed', False) or order_status_val in ['REJECTED', 'FAILED']
            if is_sell_failed:
                reject_reason = 'Submission failed / Rejected by Dhan'
                if isinstance(resp, dict):
                    reject_reason = (
                        resp.get('omsErrorDescription') or 
                        resp.get('remarks') or 
                        (resp.get('data', {}).get('omsErrorDescription') if isinstance(resp.get('data'), dict) else '') or 
                        resp.get('message') or
                        resp.get('status') or 
                        'Submission failed / Rejected by Dhan'
                    )
                
                # Check for Margin Downsizing in direct option selling
                if self._is_margin_rejection(reject_reason, resp) and order_qty > lot_size:
                    fallback_qty = lot_size
                    self.logger.warning(
                        f"[{self.name}] [{source}] [MARGIN FALLBACK] Direct option sell of {order_qty} qty rejected for '{acc_name}' "
                        f"due to broker margin shortfall ({reject_reason}). Retrying at 1 lot ({fallback_qty} qty)..."
                    )
                    self._enforce_order_stagger()
                    fb_resp = acc_api.place_order(
                        security_id=sec_id,
                        transaction_type="SELL",
                        quantity=fallback_qty,
                        exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                        product_type="MARGIN",
                        order_type="MARKET",
                        price=0.0
                    )
                    if fb_resp and not fb_resp.get('failed', False) and str(fb_resp.get('orderStatus', '')).upper() not in ['REJECTED', 'FAILED']:
                        resp = fb_resp
                        order_qty = fallback_qty
                        is_sell_failed = False
                        order_id = str(resp.get('orderId') or (resp.get('data', {}).get('orderId') if isinstance(resp.get('data'), dict) else ''))
                        order_status_val = str(resp.get('orderStatus') or (resp.get('data', {}).get('orderStatus') if isinstance(resp.get('data'), dict) else 'SUBMITTED'))
                        self.logger.info(f"[{self.name}] [{source}] [MARGIN FALLBACK SUCCESS] Direct option sell filled at {fallback_qty} qty for '{acc_name}'!")
                        if self.alert_manager:
                            self.alert_manager.send_alert(
                                f"⚠️ *[MARGIN DOWNSIZED]* Direct Option Sell Resized\n"
                                f"🔹 *Instrument:* `{prefix} {strike} {action_type}`\n"
                                f"🔹 *Strategy:* `{source}`\n"
                                f"🔹 *Account:* `{acc_name}`\n"
                                f"🔹 *Downsized Qty:* `{fallback_qty}`\n"
                                f"⚠️ *Broker Shortfall:* `{reject_reason}`\n"
                                f"✅ *Order successfully filled at 1 lot!*",
                                header="Margin Fallback Filled"
                            )

            if is_sell_failed:
                self.logger.error(f"[{self.name}] [{source}] Order placement failed/rejected for '{acc_name}'. Reason: {reject_reason}")
                if self.alert_manager:
                    self.alert_manager.send_alert(
                        f"❌ *Order Placement Rejected / Failed*\n"
                        f"🔹 *Instrument:* `{prefix} {strike} {action_type}`\n"
                        f"🔹 *Strategy:* `{source}`\n"
                        f"🔹 *Account:* `{acc_name}`\n"
                        f"🔹 *Qty:* `{order_qty}`\n"
                        f"⚠️ *Reason:* `{reject_reason}`",
                        header="Order Rejected"
                    )
                continue

            if resp and not is_sell_failed:
                # BUG-C2 FIX: MARKET orders return price=0.0 at submission time.
                # Poll order status to get the actual fill price before computing SL.
                fill_px = 0.0
                if order_id:
                    self.logger.info(f"[{self.name}] [{source}] Polling fill price for order {order_id} on '{acc_name}'...")
                    for attempt in range(10):  # Poll up to 5 seconds
                        time.sleep(0.5)
                        try:
                            status_resp = acc_api._make_request(
                                acc_api.dhan.get_order_by_id, order_id=order_id
                            )
                            if status_resp:
                                if isinstance(status_resp, dict) and status_resp.get('status') == 'success':
                                    order_data = status_resp.get('data', {})
                                    if isinstance(order_data, list) and order_data:
                                        order_data = order_data[0]
                                elif isinstance(status_resp, list) and len(status_resp) > 0:
                                    order_data = status_resp[0] if isinstance(status_resp[0], dict) else {}
                                else:
                                    order_data = {}
                                
                                if order_data:
                                    actual_status = str(order_data.get('orderStatus', '')).upper()
                                    if actual_status == 'TRADED':
                                        fill_px = float(order_data.get('averageTradedPrice', 0.0) or
                                                        order_data.get('price', 0.0) or 0.0)
                                        self.logger.info(f"[{self.name}] [{source}] Fill price confirmed: ₹{fill_px:.2f}")
                                        break
                                    elif actual_status in ['REJECTED', 'CANCELLED']:
                                        reject_reason = (
                                            order_data.get('omsErrorDescription') or 
                                            order_data.get('remarks') or 
                                            order_data.get('failureRemarks') or 
                                            'Unknown reason'
                                        )
                                        self.logger.error(f"[{self.name}] [{source}] Order {order_id} was {actual_status} on '{acc_name}'. Reason: {reject_reason}")
                                        order_status_val = actual_status
                                        if self.alert_manager:
                                            self.alert_manager.send_alert(
                                                f"❌ *Order {actual_status} by Broker*\n"
                                                f"🔹 *Instrument:* `{prefix} {strike} {action_type}`\n"
                                                f"🔹 *Strategy:* `{source}`\n"
                                                f"🔹 *Account:* `{acc_name}`\n"
                                                f"🔹 *Qty:* `{order_qty}`\n"
                                                f"🔹 *Order ID:* `{order_id}`\n"
                                                f"⚠️ *Reason:* `{reject_reason}`",
                                                header="Order Rejected"
                                            )
                                        break
                        except Exception as poll_e:
                            self.logger.warning(f"[{self.name}] [{source}] Fill price poll attempt {attempt+1} failed: {poll_e}")

                if order_status_val in ['REJECTED', 'CANCELLED']:
                    continue

                # Fallback: if fill_px still 0, use LTP from OHLC as proxy
                if fill_px <= 0:
                    try:
                        opt_seg = inst_config.get("option_segment", "NSE_FNO")
                        ltp_resp = self.data_api._make_request(
                            self.data_api.dhan.ohlc_data, securities={opt_seg: [int(sec_id)]}
                        )
                        if isinstance(ltp_resp, dict) and 'data' in ltp_resp:
                            d = ltp_resp['data'].get(opt_seg, {}).get(str(sec_id), {})
                            fill_px = float(d.get('last_price', 0.0))
                    except Exception as e:
                        self.logger.error(f"[{self.name}] [{source}] Error fetching LTP fallback for {sec_id}: {e}")
                        
                if fill_px <= 0:
                    self.logger.error(f"[{self.name}] [{source}] CRITICAL: Could not confirm fill price. Abandoning state update to prevent 0.00 SL.")
                    continue

                sl_price = round(fill_px * (1.0 + leg_sl_pct), 2) if fill_px > 0 else 0.0
                self.logger.info(f"[{self.name}] [{source}] Entry=₹{fill_px:.2f}, SL=₹{sl_price:.2f} ({leg_sl_pct*100:.0f}%)")
                
                pos_key = self._make_position_key(acc_name, source, sec_id)
                with self.state.lock:
                    self.state.positions[pos_key] = {
                        "security_id": str(sec_id),
                        "instrument": self.name,
                        "strategy": source,
                        "account": acc_name,
                        "leg": action_type,
                        "qty": order_qty,
                        "entry_price": fill_px,
                        "sl_price": sl_price,
                        "timestamp": datetime.now(self.config.TIMEZONE).isoformat(),
                        "symbol": f"{prefix} {strike} {action_type}",
                        "exchange_segment": inst_config.get("option_segment", "NSE_FNO")
                    }
                self.state.save_state()
                
                if self.alert_manager:
                    self.alert_manager.send_alert(
                        f"🚨 *Live Option Short Executed:*\n"
                        f"🔹 *Strategy:* `{source}`\n"
                        f"🔹 *Account:* `{acc_name}`\n"
                        f"🔹 *Instrument:* `{prefix} {strike} {action_type}`\n"
                        f"🔹 *Quantity:* `{order_qty}` (SL: {sl_price:.2f})\n"
                        f"🔹 *Entry Price:* `{fill_px:.2f}`",
                        header="Live Order Executed"
                    )
                    
                # Increment daily trade count for Strategy
                strat_counts = self.daily_trade_counts.setdefault(source, {})
                strat_counts[acc_name] = strat_counts.get(acc_name, 0) + 1

        self.strategy_cooldowns[source] = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)

    def _monitor_strategy20_exits(self):
        """Monitor active Strategy 20 option writing positions for 35% SL, target profit, or EOD exit."""
        strat_config = self.get_strategy_instrument_config("Strategy_20")
        target_pnl_per_lot = float(strat_config.get("target_profit", 2000.0))
        max_loss_pnl_per_lot = float(strat_config.get("stop_loss", -2500.0))
        if max_loss_pnl_per_lot > 0: max_loss_pnl_per_lot = -max_loss_pnl_per_lot
        
        inst_config = self.config.INSTRUMENTS[self.name]
        lot_size = int(inst_config.get("lot_size", 65))
        
        accounts = self.order_manager.get_accounts()
        for acc in accounts:
            acc_name = acc['name']
            acc_api = acc['api']
            
            with self.state.lock:
                s20_positions = [
                    pos for pos in self.state.positions.values()
                    if pos.get('strategy') == "Strategy_20" and pos.get('account') == acc_name
                ]
                
            if not s20_positions:
                continue
                
            for pos in s20_positions:
                sec_id = pos['security_id']
                qty = pos['qty']
                entry_px = pos.get('entry_price', 0.0)
                sl_price = pos.get('sl_price', 0.0)
                
                pos_lots = max(1, qty // lot_size)
                effective_target_pnl = target_pnl_per_lot * pos_lots
                effective_max_loss_pnl = max_loss_pnl_per_lot * pos_lots
                
                opt_segment = pos.get('exchange_segment', 'NSE_FNO')
                sec_id_lookup = int(sec_id) if str(sec_id).isdigit() else sec_id
                ltp_resp = self.data_api._make_request(self.data_api.dhan.ohlc_data, securities={opt_segment: [sec_id_lookup]})
                ltp = 0.0
                if ltp_resp and isinstance(ltp_resp.get('data'), dict):
                    try:
                        d = ltp_resp['data']
                        if opt_segment in d and isinstance(d[opt_segment], dict):
                            d = d[opt_segment]
                        if str(sec_id) in d:
                            d = d[str(sec_id)]
                        elif sec_id_lookup in d:
                            d = d[sec_id_lookup]
                        ltp = float(d.get('last_price', 0) or d.get('ltp', 0) or d.get('close', 0))
                    except Exception:
                        pass
                        
                if ltp <= 0:
                    continue
                    
                running_pnl = (entry_px - ltp) * qty
                now_time = datetime.now(self.config.TIMEZONE).time()
                
                trigger_exit = False
                reason = ""
                
                if sl_price > 0 and ltp >= sl_price:
                    trigger_exit = True
                    reason = f"35% Premium Stop Loss Hit (LTP: {ltp:.2f} >= SL: {sl_price:.2f})"
                elif running_pnl <= effective_max_loss_pnl:
                    trigger_exit = True
                    reason = f"Max Loss Cap Triggered (PnL: Rs. {running_pnl:.2f} <= Limit: Rs. {effective_max_loss_pnl:.2f})"
                elif running_pnl >= effective_target_pnl:
                    trigger_exit = True
                    reason = f"Target Profit Reached (PnL: Rs. {running_pnl:.2f} >= Target: Rs. {effective_target_pnl:.2f})"
                elif now_time >= dt_time(15, 15):
                    trigger_exit = True
                    reason = "15:15 PM EOD Squareoff"
                    
                if trigger_exit:
                    self.logger.warning(f"[{self.name}] [STRATEGY 20 EXIT] Closing short leg {pos['symbol']} on {acc_name}: {reason}")
                    resp = acc_api.place_order(
                        security_id=sec_id,
                        transaction_type="BUY",
                        quantity=qty,
                        exchange_segment=pos.get('exchange_segment', 'NSE_FNO'),
                        product_type="MARGIN",
                        order_type="MARKET",
                        price=0.0
                    )
                    if "Stop Loss" in reason or "Max Loss" in reason or "SL" in reason:
                        strat_sls = self.daily_sl_counts.setdefault("Strategy_20", {})
                        strat_sls[acc_name] = strat_sls.get(acc_name, 0) + 1
                        self.logger.warning(f"[{self.name}] Daily SL recorded for Strategy_20 on {acc_name} (Current: {strat_sls[acc_name]}).")
                        
                    log_trade_event({
                        'timestamp': datetime.now(self.config.TIMEZONE).isoformat(),
                        'instrument': self.name, 'signal': "StopLoss" if ("Stop Loss" in reason or "Max Loss" in reason) else "Target",
                        'leg': pos.get('symbol', sec_id),
                        'action': "BUY", 'symbol': pos.get('symbol', sec_id), 'security_id': sec_id,
                        'price': ltp, 'qty': qty, 'atr': 0.0, 'delta': 0.0,
                        'target_points': 0.0, 'sl_points': 0.0, 'order_id': resp.get('orderId', '') if resp else '',
                        'status': "SUBMITTED", 'account': acc_name,
                        'strategy': "Strategy_20", 'exit_reason': reason
                    }, self.config.TRADE_LOG_CSV, self.logger)

                    with self.state.lock:
                        keys_to_remove = [
                            k for k, p in self.state.positions.items()
                            if str(p.get('security_id')) == str(sec_id)
                            and p.get('account') == acc_name
                            and p.get('strategy') == "Strategy_20"
                        ]
                        for k in keys_to_remove:
                            self.state.positions.pop(k, None)
                    self.state.save_state()



# ========== MAIN TRADING LOOP ==========
# LEGACY LOOP (UNUSED - KEPT FOR REFERENCE)
'''
def main_loop(config: Config, logger):
    """Main trading loop for 5-minute Strategy"""
    logger.info("=" * 60)
    logger.info("Starting NIFTY 50 Options Bot (Supertrend + ADX + StochRSI)")
    logger.info(f"Timezone: {config.TIMEZONE.zone}")
    logger.info(f"Trading Hours: {config.RUN_START} - {config.RUN_END}")
    logger.info(f"Timeframe: {config.TIMEFRAME} (Direct Fetch {config.DATA_INTERVAL}min)")
    logger.info("=" * 60)
    
    # Log LEG_MODE configuration
    logger.info("=" * 60)
    logger.info("TRADING DIRECTION MODE CONFIGURATION")
    logger.info(f"  Active Mode: {config.LEG_MODE}")
    logger.info("=" * 60)
    flush_logs(logger)
    
    # Initialize API wrapper
    api = DhanAPIWrapper(config.CLIENT_ID, config.API_TOKEN, config, logger)
    
    # Initialize state management
    state = TradeState(config.ORDER_STATE_FILE, logger)
    
    # Trading state
    last_processed_candle_time = None
    trades_today_count = 0
    last_data_fetch = None
    
    # Initial Alignment (Wait for next minute start)
    startup_now = datetime.now(config.TIMEZONE)
    if startup_now.second > 10:
        logger.info(f"Started at {startup_now.strftime('%H:%M:%S')}. Aligning...")
        wait_for_next_candle(startup_now, config.POLL_INTERVAL_SECS, logger, offset_seconds=2)

    while True:
        try:
            now = datetime.now(config.TIMEZONE)
            current_time_only = now.time()
            
            # Check market hours
            if not (config.RUN_START <= current_time_only <= config.RUN_END):
                # Square Off Time Check
                if current_time_only >= config.SQ_OFF_TIME:
                    logger.info("Square Off Time Reached. Exiting trading session.")
                    logger.warning("[SQ_OFF] Triggering Auto Square-off...")
                    # api.close_all_intraday_positions() # temprory not closing open positions
                    break
                    
                if current_time_only > config.RUN_END:
                    logger.info("Market entry window closed. Waiting...")
                    time.sleep(60)
                    continue
                
                logger.debug(f"Outside trading hours. Waiting... ({current_time_only})")
                time.sleep(30)
                continue
            
            # =========================================================
            # MULTI-INDEX LOOP
            # =========================================================
            logger.info(f"--- Processing Candle {now.strftime('%H:%M')} ---")
            
            for inst_name, inst_config in config.INSTRUMENTS.items():
                if not inst_config.get('enabled', False):
                    continue
                    
                security_id = inst_config['security_id']
                prefix = inst_config['fno_prefix']
                
                # logger.info(f"[{prefix}] Fetching data...")
                
                # ===== FETCH MARKET DATA =====
                # Fetch 5-min data directly
                df = fetch_candle_with_retry(api, security_id, config, logger, interval=config.DATA_INTERVAL)
                
                if df is None or df.empty:
                    logger.warning(f"[{prefix}] Failed to fetch market data.")
                    continue
                
                # ===== PROCESS & GENERATE SIGNALS =====
                df_5min = process_market_data(df, config, logger, instrument_name=inst_name)
                
                if df_5min.empty:
                    # logger.info(f"[{prefix}] Waiting for more data...")
                    continue
                    
                # Get latest complete candle signal
                signal, atr_val = get_latest_signal(df_5min, logger)
                current_candle_time = df_5min.index[-1]
                
                logger.info(f"[{prefix}] Time: {current_candle_time.strftime('%H:%M')} | Signal: {signal} | Close: {df_5min['close'].iloc[-1]}")
                
                 # Check if this candle is new and hasn't been processed
                 # We need a tracker per instrument now. 
                 # Since 'last_processed_candle_time' was single variable, we need a dict.
                 # Initializing it dynamically if not present in state
                
                # Hack: Store last processed time in a local dict in main_loop scope
                # But 'state' object is persistent. Let's rely on transient dict for runtime loop
                if not hasattr(main_loop, 'processed_candles'):
                     main_loop.processed_candles = {}
                
                last_time = main_loop.processed_candles.get(prefix)
                is_new_candle = (last_time != current_candle_time)
                
                if is_new_candle:
                    # Update tracker
                    main_loop.processed_candles[prefix] = current_candle_time
                    
                    if signal:
                        logger.info(f"!!! [{prefix}] SIGNAL DETECTED: {signal.upper()} !!!")
                        
                        # Validate Trade Constraints
                        if trades_today_count >= config.MAX_TRADES_PER_DAY:
                            logger.warning("Max trades reached. Ignoring signal.")
                        else:
                            active_orders = count_active_option_orders(api.get_positions(), logger)
                            if active_orders >= config.MAX_ACTIVE_ORDERS:
                                logger.warning("Max active orders reached. Ignoring signal.")
                            else:
                                # ===== EXECUTE TRADE =====
                                logger.info(f"Executing {signal.upper()} trade for {prefix}...")
                                
                                # Check for Strategy 20 (Math Calendar Spread)
                                if inst_config.get("strategy_type") == "CALENDAR_SPREAD" or getattr(config, "ENABLE_STRATEGY_20", False):
                                    spot_close = float(df_5min['close'].iloc[-1])
                                    regime_stance = getattr(df_5min, 'regime', ['PUT_CALENDAR'])[-1] if hasattr(df_5min, 'regime') else ("PUT_CALENDAR" if signal == "SELL" else "CALL_CALENDAR")
                                    
                                    logger.info(f"[{prefix}] Executing Strategy 20 Calendar Spread: Stance={regime_stance}, Spot={spot_close}")
                                    if inst_config.get("trade_both_sides", 0) == 1:
                                        logger.info(f"[{prefix}] DUAL STANCE ENABLED: Resolving BOTH Call & Put Calendar Spreads...")
                                        call_legs = choose_calendar_spread_v2(api, spot_close, stance="CALL_CALENDAR", instrument_config=inst_config)
                                        put_legs = choose_calendar_spread_v2(api, spot_close, stance="PUT_CALENDAR", instrument_config=inst_config)
                                        cal_legs = (call_legs or []) + (put_legs or [])
                                    else:
                                        cal_legs = choose_calendar_spread_v2(api, spot_close, stance=regime_stance, instrument_config=inst_config)
                                    
                                    if cal_legs:
                                        # Pre-trade margin check via Dhan API v2
                                        scrip_list = [
                                            {
                                                "exchangeSegment": inst_config.get("option_segment", "NSE_FNO"),
                                                "transactionType": leg["action"],
                                                "quantity": leg["quantity"],
                                                "productType": "MARGIN",
                                                "securityId": str(leg["security_id"]),
                                                "price": float(leg["ltp"])
                                            } for leg in cal_legs
                                        ]
                                        margin_resp = api.calculate_multi_order_margin(scrip_list)
                                        
                                        # Staged Order Execution: Stage 1 = Long Monthly FIRST, Stage 2 = Short Weekly SECOND
                                        long_legs = [l for l in cal_legs if l["action"] == "BUY"]
                                        short_legs = [l for l in cal_legs if l["action"] == "SELL"]
                                        
                                        # Execute Long Legs First
                                        for leg in long_legs:
                                            resp = api.place_order(
                                                security_id=leg["security_id"],
                                                transaction_type="BUY",
                                                quantity=leg["quantity"],
                                                exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                                                product_type="MARGIN",
                                                order_type="MARKET",
                                                price=leg["ltp"]
                                            )
                                            logger.info(f"[{prefix}] Stage 1 Long Leg Order Executed: {leg['tag']} -> {resp}")
                                            
                                        # Execute Short Legs Second
                                        for leg in short_legs:
                                            resp = api.place_order(
                                                security_id=leg["security_id"],
                                                transaction_type="SELL",
                                                quantity=leg["quantity"],
                                                exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                                                product_type="MARGIN",
                                                order_type="MARKET",
                                                price=leg["ltp"]
                                            )
                                            logger.info(f"[{prefix}] Stage 2 Short Leg Order Executed: {leg['tag']} -> {resp}")
                                            
                                        continue

                                # 1. Select Options (Pass instrument config)
                                ce_items, pe_items = choose_option_instruments(api, signal, inst_config, logger)
                                
                                if ce_items and pe_items:
                                    # 2. Determine Action
                                    ce_action, pe_action = get_trade_actions(signal, config, logger)
                                    
                                    # Helper to Place BO (Updated for dynamic delta)
                                    def place_leg_with_delta(item, action, leg_tag):
                                        if not action: return None
                                        
                                        sec_id = item['id']
                                        leg_delta = item.get('delta')
                                        
                                        # Fallback to default check
                                        used_delta = abs(leg_delta) if leg_delta is not None and leg_delta != 0 else config.OPTION_DELTA
                                            
                                        # Calculate Dynamic Points
                                        # Spot Points
                                        spot_sl = atr_val * config.ATR_SL_MULTIPLIER
                                        spot_tp = atr_val * config.ATR_TP_MULTIPLIER
                                        spot_trail = atr_val * config.ATR_TRAIL_MULTIPLIER
                                        
                                        # Option Points (Refined)
                                        opt_sl_points = round(spot_sl * used_delta, 1)
                                        
                                        # BUY: Fixed Profit Target Logic
                                        if action == "BUY":
                                            lot_size = inst_config.get('lot_size', 1)
                                            target_per_lot = inst_config.get('profit_target_per_lot', config.PROFIT_TARGET_PER_LOT)
                                            opt_tp_points = round(target_per_lot / lot_size, 1)
                                            # Keep jump consistent with new lower TP? Or keep purely ATR?
                                            # Using original logic for Jump:
                                            opt_jump_points = round(spot_trail * used_delta, 1)
                                            logger.info(f"[{leg_tag}] BUY Target: {target_per_lot} INR / {lot_size} Qty = {opt_tp_points} pts")
                                        else:
                                            # SELL: Original ATR Logic
                                            opt_tp_points = round(spot_tp * used_delta, 1)
                                            opt_jump_points = round(spot_trail * used_delta, 1)

                                        logger.info(f"[{leg_tag}] Delta: {used_delta:.2f} | SL: {opt_sl_points} | TP: {opt_tp_points} | Trail: {opt_jump_points}")
    
                                        # Quick LTP fetch for Reference
                                        # Use generic fetch with dynamic segment
                                        opt_segment = inst_config.get('option_segment', 'NSE_FNO')
                                        ltp_resp = api._make_request(api.dhan.ohlc_data, securities={opt_segment: [int(sec_id)]})
                                        ltp = 0.0
                                        if ltp_resp and 'data' in ltp_resp:
                                            # ... parsing ...
                                            try:
                                                d = ltp_resp['data']
                                                if opt_segment in d: d = d[opt_segment]
                                                if str(sec_id) in d: d = d[str(sec_id)]
                                                ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
                                            except: pass
                                        
                                        if ltp <= 0:
                                            # Emergency fallback: Historical
                                            h_df = api.get_historical_data(sec_id, 1, opt_segment, 'OPTIDX')
                                            if h_df is not None and not h_df.empty:
                                                ltp = float(h_df.iloc[-1]['close'])
                                        
                                        if ltp <= 0:
                                            logger.error(f"[{leg_tag}] Could not get Price for {sec_id}. Skipping this leg.")
                                            return None
                                            
                                        # Recalculate Quantity based on Split Lots
                                        base_lot_size = inst_config.get('lot_size', 1)
                                        if action == 'BUY':
                                            num_lots = inst_config.get('num_lots_buy', 1)
                                        else:
                                            num_lots = inst_config.get('num_lots_sell', 1)
                                            if inst_config.get('enable_dynamic_conviction', False) and 'Conviction' in df_5min.columns:
                                                conv_val = df_5min['Conviction'].iloc[-1]
                                                if pd.notna(conv_val) and float(conv_val) >= 1.5:
                                                    num_lots = inst_config.get('num_lots_high_conviction', num_lots)
                                                    logger.info(f"[{leg_tag}] High Conviction Detected (15m Aligned)! Sizing scaled up to {num_lots} lots.")
                                            
                                        # Recalculate Quantity based on Split Lots Logic
                                        trade_quantity = base_lot_size * num_lots
                                        
                                        resp = api.place_entry_order(
                                            security_id=sec_id,
                                            transaction_type=action,
                                            quantity=trade_quantity, # Use Calculated Total Quantity
                                            order_type="MARKET",
                                            price=ltp, # Reference for BO calc
                                            target_points=opt_tp_points,
                                            sl_points=opt_sl_points,
                                            trailing_jump=opt_jump_points,
                                            product_type="MARGIN",
                                            exchange_segment=opt_segment
                                        )
                                        
                                        # LOGGING RESTORED
                                        if resp:
                                            # 1. Update State
                                            order_id = resp.get('orderId', 'unknown')
                                            state.add_order(order_id, {
                                                'type': f"{prefix}_{leg_tag}_{action}", # Prefix with Instrument
                                                'security_id': sec_id,
                                                'symbol': item.get('symbol', 'unknown'),
                                                'price': ltp,
                                                'status': resp.get('orderStatus', 'SUBMITTED'),
                                                'target_points': opt_tp_points,
                                                'sl_points': opt_sl_points,
                                                'timestamp': datetime.now(config.TIMEZONE).isoformat()
                                            })
                                            
                                            # 2. Log to CSV
                                            log_trade_event({
                                                'timestamp': datetime.now(config.TIMEZONE).isoformat(),
                                                'instrument': prefix, # Add Instrument column
                                                'signal': signal,
                                                'leg': leg_tag,
                                                'action': action,
                                                'symbol': item.get('symbol', sec_id),
                                                'security_id': sec_id,
                                                'price': ltp,
                                                'order_id': order_id,
                                                'status': resp.get('orderStatus', 'SUBMITTED')
                                            }, config.TRADE_LOG_CSV, logger)
    
                                        return resp
    
                                    # Execute CE Orders
                                    if ce_action:
                                        logger.info(f"[EXECUTION] Processing {len(ce_items)} CE Orders for {prefix}...")
                                        for i, item in enumerate(ce_items):
                                            logger.info(f"  >> Order {i+1}/{len(ce_items)}: {item.get('symbol', item['id'])}")
                                            place_leg_with_delta(item, ce_action, f"CE_{i+1}")
                                            time.sleep(0.5)
                                        
                                    # Execute PE Orders
                                    if pe_action:
                                        logger.info(f"[EXECUTION] Processing {len(pe_items)} PE Orders for {prefix}...")
                                        for i, item in enumerate(pe_items):
                                            logger.info(f"  >> Order {i+1}/{len(pe_items)}: {item.get('symbol', item['id'])}")
                                            place_leg_with_delta(item, pe_action, f"PE_{i+1}")
                                            time.sleep(0.5)
                                        
                                    trades_today_count += 1
                                    logger.info(f"Trades Today: {trades_today_count}")

            # ===== WAIT ======
            # Wait for next minute to check again (we resample 1-min data, so we check every minute)
            # This aligns the global cycle
            wait_for_next_candle(now, config.POLL_INTERVAL_SECS, logger)
        
        except KeyboardInterrupt:
            logger.info("Exiting...")
            break
        
        except Exception as e:
            logger.exception(f"Loop Error: {e}")
            time.sleep(10)
'''

