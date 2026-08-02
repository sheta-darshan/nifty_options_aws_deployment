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
from typing import Optional, List, Dict, Tuple

from trading_bot.config import Config
from trading_bot.api_wrapper import DhanAPIWrapper, safe_int
from trading_bot.alerts import AlertManager
from trading_bot.state import TradeState
from trading_bot.account_manager import MultiAccountManager
from trading_bot.data_pipeline import (
    process_market_data,
    get_latest_signal,
    load_security_master,
    choose_option_instruments,
    choose_strategy_instruments,
    log_trade_event,
    count_active_option_orders,
    wait_for_next_candle,
    get_trade_actions,
    fetch_candle_with_retry,
    get_today_trade_count,
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
        self.last_processed_candle = None
        self.df_spot = None
        
        # Restore Daily Count from Disk (Per Account)
        restored_counts = get_today_trade_count(config.TRADE_LOG_CSV, instrument_name, config.TIMEZONE)
        self.daily_trade_counts = restored_counts if isinstance(restored_counts, dict) else {}
        
        self.active_trades = 0
        self.poll_offset = 0  # Default 0s
        self.consecutive_failures = 0
        
        # Determine Instrument Constraints
        self.MAX_ACTIVE = self.config.INSTRUMENTS[self.name].get('max_active', 1)
        self.DAILY_LIMIT = self.config.INSTRUMENTS[self.name].get('daily_limit', 5)
        self.TYPE = self.config.INSTRUMENTS[self.name].get('type', 'INDEX') # INDEX or STOCK
        
        self.logger.info(f"[{self.name}] Initialized. Type={self.TYPE}, MaxRunning={self.MAX_ACTIVE}, DailyLimit={self.DAILY_LIMIT}, RestoredCounts={self.daily_trade_counts}")

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
        target_expiry_idx = inst_config.get('expiry_index', 1)
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

        # Start high-frequency local stop monitoring loop
        threading.Thread(target=self._local_monitoring_loop, daemon=True).start()

        while self.running:
            try:
                now = datetime.now(self.config.TIMEZONE)
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
        
        if self.cooldown_until and datetime.now(self.config.TIMEZONE) < self.cooldown_until:
             return

        
        security_id = self.config.INSTRUMENTS[self.name]['security_id']
        prefix = self.config.INSTRUMENTS[self.name]['fno_prefix']
        
        # Determine Segment
        if self.TYPE == 'OPTION':
            exch_seg = self.config.INSTRUMENTS[self.name].get('exchange_segment', 'NSE_FNO')
            # Check for custom instrument_type, else infer OPTIDX vs OPTSTK
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
                time.sleep(300) # Cooldown to avoid completely spamming API/Logs
                
            return

        # Reset failures on success
        if self.consecutive_failures > 0:
            self.logger.info(f"[{self.name}] Connection restored after {self.consecutive_failures} failures.")
            self.consecutive_failures = 0

        # 2. Process Indicators
        df_1min = process_market_data(df, self.config, self.logger, instrument_name=self.name)
        if df_1min.empty: return
        self.df_spot = df_1min
        
        # 3. Get Signal
        signal, atr_val, source = get_latest_signal(df_1min, self.logger, self.config)
        current_candle_time = df_1min.index[-1]
        
        # 4. New Candle Check
        if self.last_processed_candle != current_candle_time:
            # Latency Check
            candle_delay = (datetime.now(self.config.TIMEZONE) - current_candle_time).total_seconds()
            self.logger.info(f"[{self.name}] Candle: {current_candle_time.strftime('%H:%M')} | Signal: {signal} | Delay: {candle_delay:.1f}s | Close: {df_1min['close'].iloc[-1]}")
            
            self.last_processed_candle = current_candle_time
            
            # Dynamic Exit Check
            if getattr(self.config, "USE_DYNAMIC_EXITS", False):
                last_row = df_1min.iloc[-1]
                exit_long = bool(last_row.get('Exit_Long', False))
                exit_short = bool(last_row.get('Exit_Short', False))
                if exit_long or exit_short:
                    self._handle_dynamic_exits(exit_long, exit_short, source=source)
            
            if signal:
                self.logger.info(f"!!! [{self.name}] SIGNAL: {signal.upper()} ({source}) !!!")
                self._handle_signal(signal, atr_val, source)
        
        # Cycle Performance Log
        duration = time.time() - cycle_start
        if duration > 2.0:
            self.logger.warning(f"[{self.name}] Slow Cycle: {duration:.2f}s")
        else:
            self.logger.debug(f"[{self.name}] Cycle Time: {duration:.2f}s")

    def _handle_signal(self, signal, atr_val, source):
        """Handle entry signal with early limit validation"""
        # Check instrument-level allowed actions (trade direction lock)
        inst_config = self.config.INSTRUMENTS.get(self.name, {})
        allowed_actions = inst_config.get("allowed_actions")
        if allowed_actions is not None:
            signal_action = signal.upper()
            if signal_action not in allowed_actions:
                self.logger.info(f"[{self.name}] [SKIP] Signal {signal.upper()} ignored. Instrument restricts trade direction to {allowed_actions}.")
                return

        # Check Expiry Day only filter
        if inst_config.get("trade_expiry_day_only", 0) == 1:
            try:
                underlying_id = int(inst_config['security_id'])
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
                        nearest_expiry = expiry_list[0]
                        trading_date_str = datetime.now(self.config.TIMEZONE).strftime('%Y-%m-%d')
                        if nearest_expiry != trading_date_str:
                            self.logger.info(f"[{self.name}] [SKIP] Signal ignored. trade_expiry_day_only is active and today ({trading_date_str}) is not the expiry day ({nearest_expiry}).")
                            return
            except Exception as e:
                self.logger.error(f"[{self.name}] Error checking expiry day only filter: {e}")

        # Check Expiry Day block filter
        if inst_config.get("block_expiry_day_trades", 0) == 1:
            # Only block if the signal translates to buying options (decay is bad for buyers, good for sellers)
            ce_action, pe_action = get_trade_actions(signal, self.config, self.logger)
            is_buying_trade = (ce_action == 'BUY' or pe_action == 'BUY')
            
            if is_buying_trade:
                try:
                    underlying_id = int(inst_config['security_id'])
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
                            nearest_expiry = expiry_list[0]
                            trading_date_str = datetime.now(self.config.TIMEZONE).strftime('%Y-%m-%d')
                            if nearest_expiry == trading_date_str:
                                self.logger.warning(f"[{self.name}] [SKIP] Signal ignored. Expiry day trading is blocked for option BUYING trades today ({trading_date_str}).")
                                return
                except Exception as e:
                    self.logger.error(f"[{self.name}] Error checking expiry block: {e}")

        # 1. Early Daily Limit Check (Per Account) - Saves API calls
        accounts = self.order_manager.get_accounts()
        all_limited = True
        for acc in accounts:
            acc_name = acc['name']
            acc_config = acc.get('config', {})
            overrides = acc_config.get('instrument_overrides', {}).get(self.name, {})
            acc_daily_limit = overrides.get('daily_limit', acc_config.get('daily_limit', self.DAILY_LIMIT))
            
            if self.daily_trade_counts.get(acc_name, 0) < acc_daily_limit:
                all_limited = False
                break
        
        if all_limited:
            self.logger.warning(f"[{self.name}] [SKIP] Signal ignored. All accounts have reached daily limit.")
            return

        self.logger.info(f"[{self.name}] Executing {signal} from {source}...")
        
        # Check Execution Mode
        inst_config = self.config.INSTRUMENTS[self.name]
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
                acc_max_active = overrides.get('max_active', acc_config.get('max_active', self.MAX_ACTIVE))
                acc_daily_limit = overrides.get('daily_limit', acc_config.get('daily_limit', self.DAILY_LIMIT))
                
                if self.daily_trade_counts.get(acc_name, 0) >= acc_daily_limit:
                    self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Daily Limit Reached.")
                    continue
                    
                # Check capacity of active positions for the underlying stock
                try:
                    pos_list = acc_api.get_positions()
                    active_trades = sum(1 for pos in pos_list if safe_int(pos.get('netQty', 0)) != 0 and str(pos.get('securityId', '')) == underlying_id)
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
                self.daily_trade_counts[acc] = self.daily_trade_counts.get(acc, 0) + 1
                
            if traded_accounts:
                self.logger.info(f"[{self.name}] Stock Trade Counts Updated: {self.daily_trade_counts}")
                self.cooldown_until = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)
                self.logger.info(f"[{self.name}] Cooldown activated. Locked until {self.cooldown_until.strftime('%H:%M:%S')}")
            return

        # Check Strategy 20 (Math Calendar Spread)
        if inst_config.get("strategy_type") == "CALENDAR_SPREAD" or getattr(self.config, "ENABLE_STRATEGY_20", False):
            self._execute_calendar_spread_strategy(signal, atr_val, source)
            return

        # Check Option Strategy Mode
        strat_mode = inst_config.get('option_strategy_mode', 'DIRECT')
        if strat_mode != 'DIRECT':
            self._execute_multi_leg_strategy(strat_mode, signal, atr_val, source)
            return
        
        # Existing Options Logic
        ce_items, pe_items = choose_option_instruments(self.data_api, signal, self.config.INSTRUMENTS[self.name], self.logger)
        
        ce_action, pe_action = get_trade_actions(signal, self.config, self.logger)
        
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
                 acc_max_active = overrides.get('max_active', acc_config.get('max_active', self.MAX_ACTIVE))
                 acc_daily_limit = overrides.get('daily_limit', acc_config.get('daily_limit', self.DAILY_LIMIT))
                 
                 if self.daily_trade_counts.get(acc_name, 0) >= acc_daily_limit:
                     self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Daily Limit Reached.")
                     continue
                     
                 try:
                     pos_list = acc_api.get_positions()
                     
                     ce_count = 0
                     pe_count = 0
                     prefix = inst_config['fno_prefix']
                     for pos in pos_list:
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
                 self.daily_trade_counts[acc] = self.daily_trade_counts.get(acc, 0) + 1
                 
             if traded_accounts:
                 self.logger.info(f"[{self.name}] Trade Counts Updated: {self.daily_trade_counts}")
                 self.cooldown_until = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)
                 self.logger.info(f"[{self.name}] Cooldown activated. Locked until {self.cooldown_until.strftime('%H:%M:%S')}")

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
                                    self.state.positions.pop(sec_id, None)
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
        inst_config = self.config.INSTRUMENTS[self.name]
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
                
            # Staged Order Execution for this account: BUY legs first, then SELL legs
            buy_legs = [l for l in legs_to_execute if l["action"] == "BUY"]
            sell_legs = [l for l in legs_to_execute if l["action"] == "SELL"]
            
            # 1. Place BUY legs (if any are not already held)
            for leg in buy_legs:
                resp = acc_api.place_order(
                    security_id=leg["security_id"],
                    transaction_type="BUY",
                    quantity=leg["quantity"],
                    exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                    product_type="MARGIN",
                    order_type="MARKET",
                    price=leg["ltp"]
                )
                self.logger.info(f"[{self.name}] Stage 1 Long Leg Order Executed ({acc_name}): {leg['tag']} -> {resp}")
                
            # Wait 500ms for margin benefit to apply if we placed a new BUY leg
            if buy_legs and sell_legs:
                time.sleep(0.5)
                
            # 2. Place SELL legs (weekly short legs)
            for leg in sell_legs:
                resp = acc_api.place_order(
                    security_id=leg["security_id"],
                    transaction_type="SELL",
                    quantity=leg["quantity"],
                    exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                    product_type="MARGIN",
                    order_type="MARKET",
                    price=leg["ltp"]
                )
                self.logger.info(f"[{self.name}] Stage 2 Short Leg Order Executed ({acc_name}): {leg['tag']} -> {resp}")
                
        self.cooldown_until = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)

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
            acc_max_active = overrides.get('max_active', acc_config.get('max_active', self.MAX_ACTIVE))
            acc_daily_limit = overrides.get('daily_limit', acc_config.get('daily_limit', self.DAILY_LIMIT))
            
            if self.daily_trade_counts.get(acc_name, 0) >= acc_daily_limit:
                self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Daily Limit Reached.")
                continue
                
            try:
                pos_list = acc_api.get_positions()
                
                ce_count = 0
                pe_count = 0
                prefix = self.config.INSTRUMENTS[self.name]['fno_prefix']
                for pos in pos_list:
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
            self.daily_trade_counts[acc] = self.daily_trade_counts.get(acc, 0) + 1
            
        if traded_accounts:
            self.logger.info(f"[{self.name}] Trade Counts Updated: {self.daily_trade_counts}")
            self.cooldown_until = datetime.now(self.config.TIMEZONE) + timedelta(seconds=280)
            self.logger.info(f"[{self.name}] Cooldown activated. Locked until {self.cooldown_until.strftime('%H:%M:%S')}")

    def _count_my_active_positions(self, positions, leg_type=None):
        inst_config = self.config.INSTRUMENTS[self.name]
        execution_mode = inst_config.get('execution_mode', 'OPTION')
        
        if execution_mode == 'STOCK':
            underlying_id = str(inst_config['security_id'])
            stock_count = 0
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
            
            inst_config = self.config.INSTRUMENTS[self.name]
            
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
                else:
                    lots = inst_config.get(f'num_lots_{action.lower()}', 1)
                    base_qty = inst_config.get('lot_size', 1) * lots
            else:
                lots = inst_config.get(f'num_lots_{action.lower()}', 1)
                base_qty = inst_config['lot_size'] * lots
            
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
                acc_max_active = overrides.get('max_active', acc_config.get('max_active', self.MAX_ACTIVE))
                acc_daily_limit = overrides.get('daily_limit', acc_config.get('daily_limit', self.DAILY_LIMIT))
                
                if self.daily_trade_counts.get(acc_name, 0) >= acc_daily_limit:
                    self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Daily Limit Reached.")
                    continue
                
                # --- PER-ACCOUNT SAFETY CHECK ---
                if not bypass_max_active_check:
                    try:
                        pos_list = self.order_manager.position_manager.get_cached_positions(acc_name)
                        active_qty = self._count_my_active_positions(pos_list, leg_type)
                        if active_qty >= acc_max_active:
                            self.logger.warning(f"[{self.name}] [SKIP] Account '{acc_name}' Max Active Reached.")
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
                    else:
                        acc_qty = int(self.config.INSTRUMENTS[self.name]['lot_size'] * override_lots)
                else:
                    multiplier = float(acc_config.get('global_multiplier', 1.0))
                    acc_qty = max(1, int(base_qty * multiplier)) if base_qty > 0 else 0
                
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
                
                api_opt_tp = 0.0 if local_exit_monitoring else opt_tp
                api_opt_sl = 0.0 if local_exit_monitoring else opt_sl
                api_opt_trail = 0.0 if local_exit_monitoring else opt_trail
                
                eligible_dispatches.append({
                    'acc_name': acc_name,
                    'acc_api': acc_api,
                    'acc_qty': acc_qty,
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
                    futures[acc_name] = self.order_manager.executor.submit(
                        dispatch['acc_api'].place_entry_order,
                        security_id=sec_id,
                        transaction_type=action,
                        quantity=dispatch['acc_qty'],
                        order_type="LIMIT",
                        price=dispatch['limit_price'],
                        target_points=dispatch['api_opt_tp'],
                        sl_points=dispatch['api_opt_sl'],
                        trailing_jump=dispatch['api_opt_trail'],
                        exchange_segment=opt_seg,
                        product_type=dispatch['inst_product_type'],
                        ref_price=ltp
                    )

                # 3. Gather Results and Update State
                for dispatch in eligible_dispatches:
                    acc_name = dispatch['acc_name']
                    future = futures.get(acc_name)
                    if future:
                        try:
                            resp = future.result(timeout=15)
                            if resp:
                                success_accounts.add(acc_name)
                                item_total_qty += dispatch['acc_qty']
                                item_success = True
                                order_id = resp.get('orderId', 'unknown')
                                
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
                                    with self.state.lock:
                                        self.state.positions[str(sec_id)] = {
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
                        except Exception as e:
                            self.logger.error(f"[{self.name}] Async dispatch result error for '{acc_name}': {e}")
                
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
                        sec_id: pos for sec_id, pos in self.state.positions.items()
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
                        for sec_id, position in list(swing_positions.items()):
                            if position.get('account') != acc_name:
                                continue
                                
                            if sec_id not in open_broker_positions:
                                # Position already closed on broker or not open yet. Clean up local state if created > 2 mins ago to avoid race conditions on entry
                                created_str = position.get('created_at', position.get('timestamp'))
                                if created_str:
                                    created_dt = datetime.fromisoformat(created_str)
                                    if (datetime.now(self.config.TIMEZONE) - created_dt).total_seconds() > 120:
                                        self.logger.info(f"[{self.name}] Cleaning up stale local position state for {sec_id}")
                                        with self.state.lock:
                                            self.state.positions.pop(sec_id, None)
                                        self.state.save_state()
                                continue
                                
                            # If it is open, check the exit mode logic
                            pos_exit_mode = position.get('exit_mode', 'SWING')
                            if pos_exit_mode in ['SWING_CONTRACT', 'POINTS', 'ATR']:
                                opt_seg = position.get('exchange_segment', 'NSE_FNO')
                                contract_ltp = 0.0
                                try:
                                    resp = self.data_api._make_request(self.data_api.dhan.ohlc_data, securities={opt_seg: [int(sec_id)]})
                                    if resp:
                                        d = resp.get('data', {}).get(opt_seg, {}).get(str(sec_id), {})
                                        contract_ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
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
                                    if be_mult > 0.0 and not position.get("Breakeven_Triggered", False) and position.get("Initial_SL_Points", 0.0) > 0.0:
                                        if action == 'BUY':
                                            trigger_level = position["Entry_Price"] + (position["Initial_SL_Points"] * be_mult)
                                            if contract_ltp >= trigger_level:
                                                position["opt_sl_price"] = max(position["opt_sl_price"], position["Entry_Price"])
                                                position["Breakeven_Triggered"] = True
                                                self.logger.info(f"[{self.name}] [BREAKEVEN SL TRIGGER] Moved SL to entry: {position['opt_sl_price']:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                updated = True
                                        else: # SELL
                                            trigger_level = position["Entry_Price"] - (position["Initial_SL_Points"] * be_mult)
                                            if contract_ltp <= trigger_level:
                                                position["opt_sl_price"] = min(position["opt_sl_price"], position["Entry_Price"])
                                                position["Breakeven_Triggered"] = True
                                                self.logger.info(f"[{self.name}] [BREAKEVEN SL TRIGGER] Moved SL to entry: {position['opt_sl_price']:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                updated = True

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
                                    with self.state.lock:
                                        self.state.positions.pop(sec_id, None)
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
                        
                # Check Strategy 20 Intraday Exits (> Rs. 5000)
                try:
                    self._monitor_calendar_spread_exits()
                except Exception as e:
                    self.logger.error(f"[{self.name}] Error in calendar spread monitor: {e}")
                        
            except Exception as loop_err:
                self.logger.error(f"[{self.name}] Error in local stop monitor loop: {loop_err}")
                
            time.sleep(5)

    def _monitor_calendar_spread_exits(self):
        """Monitor active calendar spreads (Strategy 20) for intraday profit target > Rs. 5000."""
        inst_config = self.config.INSTRUMENTS[self.name]
        prefix = inst_config.get('fno_prefix', self.name).upper()
        
        accounts = self.order_manager.get_accounts()
        for acc in accounts:
            acc_name = acc['name']
            acc_api = acc['api']
            
            try:
                positions = acc_api.get_positions()
                if not positions:
                    continue
                
                stance_positions = {"CALL": [], "PUT": []}
                for pos in positions:
                    qty = safe_int(pos.get('netQty', 0))
                    if qty == 0:
                        continue
                        
                    sym = pos.get('tradingSymbol', '').upper()
                    if sym.startswith(prefix):
                        if sym.endswith('CE'):
                            stance_positions["CALL"].append(pos)
                        elif sym.endswith('PE'):
                            stance_positions["PUT"].append(pos)
                            
                for stance, legs in stance_positions.items():
                    if not legs:
                        continue
                        
                    combined_pnl = 0.0
                    for leg in legs:
                        qty = safe_int(leg.get('netQty', 0))
                        ltp = float(leg.get('lastPrice', 0.0))
                        avg_px = float(leg.get('averagePrice', 0.0))
                        if qty != 0:
                            combined_pnl += qty * (ltp - avg_px)
                            
                    trigger_exit = False
                    reason = ""
                    header_label = ""
                    if combined_pnl >= 5000.0:
                        trigger_exit = True
                        reason = f"Profit Target Reached (Target: Rs. 5000)"
                        header_label = "Strategy 20 Profit Target"
                    elif combined_pnl <= -4000.0:
                        trigger_exit = True
                        reason = f"Stop Loss Triggered (Limit: -Rs. 4000)"
                        header_label = "Strategy 20 Stop Loss"
                        
                    if trigger_exit:
                        self.logger.warning(f"[{self.name}] [STRATEGY 20 EXIT] Combined PnL for {stance} Calendar on {acc_name} reached Rs. {combined_pnl:.2f}. Triggering exit via {reason}.")
                        
                        for leg in legs:
                            sec_id = str(leg.get('securityId'))
                            sym = leg.get('tradingSymbol')
                            qty = safe_int(leg.get('netQty', 0))
                            abs_qty = abs(qty)
                            close_action = 'SELL' if qty > 0 else 'BUY'
                            exch = leg.get('exchangeSegment', 'NSE_FNO')
                            product = leg.get('productType', 'MARGIN')
                            
                            try:
                                resp = acc_api.place_order(
                                    security_id=sec_id,
                                    transaction_type=close_action,
                                    quantity=abs_qty,
                                    exchange_segment=exch,
                                    product_type=product,
                                    order_type='MARKET',
                                    price=0.0,
                                    should_slice=(exch in ['NSE_FNO', 'BSE_FNO'])
                                )
                                self.logger.info(f"[{self.name}] [STRATEGY 20 EXIT] Placed exit order for {sym}: {close_action} {abs_qty} -> {resp}")
                            except Exception as e:
                                self.logger.error(f"[{self.name}] [STRATEGY 20 EXIT] Failed to close {sym} for {acc_name}: {e}")
                                
                        if self.alert_manager:
                            self.alert_manager.send_alert(
                                f"🎯 *{header_label}*\n"
                                f"*Instrument:* `{self.name}`\n"
                                f"*Stance:* `{stance} Calendar`\n"
                                f"*Account:* `{acc_name}`\n"
                                f"*Combined PnL:* `Rs. {combined_pnl:,.2f}`\n"
                                f"*Action:* Exited all legs at market due to {reason}.",
                                header=header_label
                            )
            except Exception as e:
                self.logger.error(f"[{self.name}] Error in calendar spread monitor for '{acc_name}': {e}")



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

