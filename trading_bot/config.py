import os
import json
import time
import logging
import pytz
import pandas as pd
from datetime import time as dt_time, datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dotenv import load_dotenv, find_dotenv

class Config:
    """Centralized configuration management"""
    def __init__(self, dotenv_path: Optional[str] = None, client_id: Optional[str] = None, api_token: Optional[str] = None):
        # 0. Set Base Directory for absolute paths
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 1. Try to explicitly load .env file
        if dotenv_path:
            self.env_path = dotenv_path
            load_dotenv(dotenv_path, override=True)
        else:
            # First check script directory
            local_env = os.path.join(self.BASE_DIR, ".env")
            if os.path.exists(local_env):
                self.env_path = local_env
                load_dotenv(local_env, override=True)
            else:
                # Fallback to searching (find_dotenv)
                self.env_path = find_dotenv()
                if self.env_path:
                    load_dotenv(self.env_path, override=True)
                else:
                    self.env_path = None

        # Allow direct overrides via constructor
        self.refresh_env_vars(client_id, api_token)
            
        # File Paths (Absolute)
        self.INSTRUMENTS_FILE = os.path.join(self.BASE_DIR, "instruments.json")
        self.ACCOUNTS_FILE = os.path.join(self.BASE_DIR, "accounts.json")
        self.TRADE_LOG_CSV = os.path.join(self.BASE_DIR, "live_trades_multi_index.csv")
        self.FAILED_TRADE_LOG_CSV = os.path.join(self.BASE_DIR, "failed_trades.csv")
        self.ORDER_STATE_FILE = os.path.join(self.BASE_DIR, "order_state.json")

        # Instrument Configuration
        self.last_instruments_mtime = 0.0
        self.reload_instruments()

        # Memory-resident Security ID lookup map
        self.master_cache_index = {}

        # Strategy Configuration
        self.TIMEFRAME = '5min'
        self.DATA_INTERVAL = 1  # 1-min for Breakouts
        
        # Master Strategy Toggles
        self.ENABLE_STRATEGY_1 = False # Standard Trend
        self.ENABLE_STRATEGY_2 = False # High-Conviction Pullback
        self.ENABLE_STRATEGY_3 = True   # Triple Momentum Breakout
        self.ENABLE_STRATEGY_4 = False # WMA/SMA Trend Breakout
        self.ENABLE_STRATEGY_5 = False  # Added for Strategy 5  
        self.ENABLE_STRATEGY_6 = False  # Added for Strategy 6
        self.ENABLE_STRATEGY_7 = False  # Added for Strategy 7
        self.ENABLE_STRATEGY_8 = False  # Added for Strategy 8 (Daily 9:30 AM Entry)
        self.ENABLE_STRATEGY_9 = False  # Added for Strategy 9 (Reverse Engineered)
        self.ENABLE_STRATEGY_10 = False # Hilega milega
        self.ENABLE_STRATEGY_11 = False
        self.ENABLE_STRATEGY_12 = False
        self.ENABLE_STRATEGY_13 = False
        self.ENABLE_STRATEGY_14 = False
        self.ENABLE_STRATEGY_15 = False
        self.ENABLE_STRATEGY_16 = False
        self.ENABLE_STRATEGY_17 = False
        self.ENABLE_STRATEGY_18 = False
        self.ENABLE_STRATEGY_19 = False
        self.ENABLE_STRATEGY_20 = False
        
        # Strategy 1
        self.SUPERTREND_LEN = 12
        self.SUPERTREND_MUL = 3
        self.ADX_THRESHOLD = 18
        self.EMA_FILTER_LEN = 21

        # Strategy 2 Configuration (High-Conviction Pullback)
        self.S2_ST15_LEN = 10
        self.S2_ST15_MUL = 3.0
        self.S2_ST5_MUL = 4.0
        self.S2_RSI_OVERSOLD = 25
        self.S2_RSI_OVERBOUGHT = 75

        # Strategy 3 Configuration (Triple Momentum) - Institutional Upgrade
        self.TM_EMA_LONG = 30
        self.TM_EMA_SHORT = 11
        self.TM_EMA_BASE = 21
        self.TM_ST_LEN = 10
        self.TM_ST_MUL = 2.5
        self.TM_ADX_THRESHOLD = 10
        self.TM_MAX_STRETCH = 0.003

        # Strategy 4 Configuration (WMA/VWAP Breakout)
        self.S4_WMA_87 = 87
        self.S4_WMA_200 = 200

        # Entry Trigger
        self.STOCH_LEN = 14
        self.RSI_OVERSOLD = 30
        self.RSI_OVERBOUGHT = 70

        # Risk Management
        self.ATR_PERIOD = 14
        self.ATR_SL_MULTIPLIER = 1.4
        self.ATR_TP_MULTIPLIER = 4.0
        self.OPTION_DELTA = 0.5
        self.PROFIT_TARGET_PER_LOT = 1250
        self.TRAIL_TRIGGER_ATR = 2.5
        self.ATR_TRAIL_MULTIPLIER_BUY = 1.6
        self.ATR_TRAIL_MULTIPLIER_SELL = 1.6
        self.TRAILING_JUMP = 0
        self.USE_DYNAMIC_EXITS = False
        
        # Time Settings
        self.RUN_START = dt_time(9, 20)
        self.RUN_END = dt_time(15, 15)
        self.SQ_OFF_TIME = dt_time(15, 16)
        self.TIMEZONE = pytz.timezone("Asia/Kolkata")
        self.POLL_INTERVAL_SECS = 30
        
        # API & Rate Limiting
        self.REQUEST_TIMEOUT = 10
        self.MAX_RETRIES = 3
        self.RETRY_BACKOFF = 2
        self.MAX_REQUESTS_PER_SEC = 5
        self.MAX_REQUESTS_PER_MIN = 250
        self.NUM_STRIKES = 1
        
        self.LOG_LEVEL = logging.INFO
        
        # Network Settings (Primary Account)
        self.SOURCE_IP = os.getenv("DHAN_SOURCE_IP", "").strip()
        self.PROXY_URL = os.getenv("DHAN_PROXY_URL", "").strip()

        # Parse Strategy Enable Flags from .env
        for i in range(1, 24):
            env_val = os.getenv(f"ENABLE_STRATEGY_{i}", None)
            if env_val is not None:
                setattr(self, f"ENABLE_STRATEGY_{i}", env_val.strip().upper() == "TRUE")

        self.active_strategy = "Strategy_3"
        for i in range(1, 24):
            if getattr(self, f"ENABLE_STRATEGY_{i}", False):
                self.active_strategy = f"Strategy_{i}"
                break
        self.apply_strategy_defaults(self.active_strategy)
        self.apply_strategy_instrument_overrides(self.active_strategy)
        # Ensure RUN_START is 09:15 if any active or enabled strategy requires early 09:15 AM entry
        early_strategies = {"Strategy_14", "Strategy_20"}
        enabled_any_early = any(getattr(self, f"ENABLE_STRATEGY_{s.split('_')[-1]}", False) for s in early_strategies)
        if self.active_strategy in early_strategies or enabled_any_early:
            self.RUN_START = dt_time(9, 15)

    def apply_strategy_defaults(self, strategy_name: str):
        """Apply default parameters for the specified strategy to prevent collision."""
        import strategies as strat
        try:
            strat_cls = strat.get_strategy_class(strategy_name)
            defaults = strat_cls().get_default_params()
            for k, v in defaults.items():
                setattr(self, k, v)
        except Exception:
            pass
            
        if strategy_name == "Strategy_12":
            self.USE_DYNAMIC_EXITS = True

    def apply_strategy_instrument_overrides(self, strategy_name: str):
        """Merge strategy-specific overrides into the active instruments configurations."""
        if not hasattr(self, "INSTRUMENTS") or not self.INSTRUMENTS:
            return
        
        for name, item in self.INSTRUMENTS.items():
            if not isinstance(item, dict):
                continue
            
            overrides = item.get("strategy_overrides", {})
            if isinstance(overrides, dict) and strategy_name in overrides:
                strategy_cfg = overrides[strategy_name]
                if isinstance(strategy_cfg, dict):
                    # Merge strategy overrides into the main instrument parameters
                    for k, v in strategy_cfg.items():
                        item[k] = v

    def refresh_env_vars(self, client_id: Optional[str] = None, api_token: Optional[str] = None):
        """Refresh environment variables into class attributes"""
        self.API_TOKEN = (api_token or os.getenv("DHAN_API_TOKEN", "")).strip()
        self.CLIENT_ID = (client_id or os.getenv("DHAN_CLIENT_ID", "")).strip()
        
        self.ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "").strip()
        self.LEG_MODE = os.getenv("LEG_MODE", "BOTH").upper()
        self.PRODUCT_TYPE = os.getenv("PRODUCT_TYPE", "MARGIN").upper()
        
        # Refresh Network Settings
        self.SOURCE_IP = os.getenv("DHAN_SOURCE_IP", "").strip()
        self.PROXY_URL = os.getenv("DHAN_PROXY_URL", "").strip()
        self.USE_DYNAMIC_EXITS = os.getenv("USE_DYNAMIC_EXITS", "False").strip().upper() == "TRUE"
        self.CARRY_FORWARD = os.getenv("CARRY_FORWARD", "True").strip().upper() == "TRUE"
        
        if self.LEG_MODE not in ["BOTH", "BUY", "SELL"]:
            self.LEG_MODE = "BOTH"

    def reload_instruments(self) -> bool:
        """Reload the instruments configuration from JSON file only if it changed on disk"""
        try:
            if os.path.exists(self.INSTRUMENTS_FILE):
                mtime = os.path.getmtime(self.INSTRUMENTS_FILE)
                if mtime == self.last_instruments_mtime:
                    return False  # No change on disk, skip reload
                
                with open(self.INSTRUMENTS_FILE, "r") as f:
                    self.INSTRUMENTS = json.load(f)
                self.validate_and_scrub_instruments()
                
                # Store a clean copy of base configurations for multi-strategy dynamic overrides
                import copy
                self.BASE_INSTRUMENTS = copy.deepcopy(self.INSTRUMENTS)
                
                # Re-apply strategy-specific overrides after reloading from disk
                if hasattr(self, "active_strategy"):
                    self.apply_strategy_instrument_overrides(self.active_strategy)
                    
                self.last_instruments_mtime = mtime
                return True
            else:
                return False
        except Exception as e:
            # H4 FIX: Previously all exceptions were swallowed silently (except Exception: return False),
            # leaving operators with no visibility when instruments.json is corrupt or unreadable.
            # Now logs the error and optionally fires a Telegram alert.
            import traceback
            err_detail = traceback.format_exc()
            try:
                import logging
                _logger = logging.getLogger("live-dhan-bot")
                _logger.error(
                    f"[CONFIG] CRITICAL: Failed to reload instruments.json. "
                    f"Bot is running on stale config. Error: {e}\n{err_detail}"
                )
            except Exception:
                pass
            return None

    def validate_and_scrub_instruments(self):
        """Validate all instrument configurations and inject defaults for missing keys to prevent crashes."""
        DEFAULTS = {
            "lot_size": 1,
            "num_lots_buy": 1,
            "num_lots_sell": 1,
            "strike_step": 100.0,
            "strike_offset": 0,
            "strike_offset_buy": 0,
            "strike_offset_sell": 0,
            "enabled": 0,
            "max_active": 1,
            "daily_limit": 2,
            "profit_target_buy": 0.0,
            "profit_target_sell": 0.0,
            "expiry_index": 1,
            "num_strikes": 1,
            "trailing_mult_buy": 0.5,
            "trailing_mult_sell": 0.5,
            "sl_mult_buy": 1.0,
            "sl_mult_sell": 1.0,
            "option_strategy_mode": "DIRECT",
            "strategy_leg_width": 1,
            "execution_mode": "OPTION",
            "points_sl_buy": 0.0,
            "points_target_buy": 0.0,
            "points_trail_buy": 0.0,
            "points_sl_sell": 0.0,
            "points_target_sell": 0.0,
            "points_trail_sell": 0.0,
            "local_exit_monitoring": None,
            "allowed_actions": None,
            "gatekeeper_enabled": 0,
            "gatekeeper_time_filter_minutes": 20,
            "gatekeeper_window_minutes": 5,
            "gatekeeper_oi_min_change_pct": 1.0,
            "gatekeeper_volume_sma_period": 15,
            "gatekeeper_volume_multiplier": 1.2
        }
        
        if not isinstance(self.INSTRUMENTS, dict):
            self.INSTRUMENTS = {}
            return
            
        clean_instruments = {}
        for name, item in self.INSTRUMENTS.items():
            if not isinstance(item, dict):
                continue
                
            if 'security_id' not in item:
                # Can't trade without security ID
                continue
                
            if 'fno_prefix' not in item:
                item['fno_prefix'] = name
                
            # If type is OPTION, default exchange_segment to NSE_FNO if missing
            if item.get('type') == 'OPTION' and 'exchange_segment' not in item:
                item['exchange_segment'] = "NSE_FNO"
                
            if 'option_segment' not in item:
                item['option_segment'] = "BSE_FNO" if "BSE" in item.get('exchange_segment', '') else "NSE_FNO"
                
            for key, val in DEFAULTS.items():
                if key not in item:
                    if key in ["strike_offset_buy", "strike_offset_sell"]:
                        item[key] = item.get("strike_offset", 0)
                    else:
                        item[key] = val
                    
            clean_instruments[name] = item
            
        self.INSTRUMENTS = clean_instruments

    def reload_api_token(self) -> bool:
        """Reload the API token and other env vars from the .env file"""
        try:
            if not self.env_path or not os.path.exists(self.env_path):
                return False
                
            load_dotenv(self.env_path, override=True)
            old_token = self.API_TOKEN
            self.refresh_env_vars()
            
            return self.API_TOKEN != old_token
        except Exception:
            return False

    def get_holiday_set(self) -> set:
        """Fetch holiday dates from local cache or fallback list"""
        holiday_set = set()
        cache_file = os.path.join(self.BASE_DIR, "holidays_cache.json")
        
        # 1. Try to load from cache (created by is_market_open.py)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    holidays = data.get("holidays", [])
                    for item in holidays:
                        # Standard Upstox API format
                        exchanges = item.get("closed_exchanges", [])
                        if "NSE" in exchanges or "BSE" in exchanges:
                            date_str = item.get("date")
                            if date_str: holiday_set.add(date_str)
            except Exception:
                pass

        # 2. Add Fallback (Emergency only)
        fallbacks = [
            "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31", 
            "2026-04-03", "2026-04-14", "2026-05-01", "2026-05-28",
            "2026-06-26", "2026-09-14", "2026-10-02", "2026-10-20",
            "2026-11-10", "2026-11-24", "2026-12-25"
        ]
        for d in fallbacks:
            holiday_set.add(d)
                
        return holiday_set

    def is_market_day(self) -> bool:
        """Check if today is a trading day (Monday-Friday and NOT a holiday)"""
        now = datetime.now(self.TIMEZONE)
        
        # 1. Weekend Check
        if now.weekday() >= 5:
            return False
            
        # 2. Holiday Check
        current_date_str = now.strftime("%Y-%m-%d")
        holidays = self.get_holiday_set()
        
        if current_date_str in holidays:
            return False
            
        return True

    def build_master_index(self, logger):
        """
        Scan and index all F&O cache CSV files into an in-memory dictionary.
        Format: (prefix, expiry_date, strike, option_type) -> (security_id, lot_size, symbol)
        """
        import time
        import re
        import os
        from datetime import datetime as dt
        logger.info("[INDEXER] Starting in-memory security master index build...")
        t0 = time.time()
        self.master_cache_index = {}
        
        # 1. Download fresh scrip master if missing or stale (older than today)
        master_csv = os.path.join(self.BASE_DIR, 'dhanhq_securities_compact.csv')
        downloaded_fresh_master = False
        need_download_master = True
        
        if os.path.exists(master_csv):
            mtime_date = dt.fromtimestamp(os.path.getmtime(master_csv)).date()
            if mtime_date == dt.now().date():
                need_download_master = False
                
        if need_download_master:
            logger.info("[INDEXER] Compact scrip master is stale or missing. Downloading latest from Dhan...")
            try:
                import requests
                master_csv_url = "https://images.dhan.co/api-data/api-scrip-master.csv"
                response = requests.get(master_csv_url, timeout=60)
                if response.status_code == 200:
                    with open(master_csv, "wb") as f:
                        f.write(response.content)
                    logger.info("[INDEXER] Successfully downloaded compact scrip master.")
                    downloaded_fresh_master = True
                else:
                    logger.warning(f"[INDEXER] Failed to download scrip master. Status code: {response.status_code}")
            except Exception as e:
                logger.error(f"[INDEXER] Failed to download scrip master: {e}")
                
        # Scan each enabled instrument
        for name, inst in self.INSTRUMENTS.items():
            if not inst.get('enabled', False):
                continue
            prefix = inst.get('fno_prefix')
            if not prefix:
                continue
            
            cache_file = os.path.join(self.BASE_DIR, f"dhanhq_cache_{prefix}.csv")
            is_cache_stale = downloaded_fresh_master
            
            if not is_cache_stale and os.path.exists(cache_file):
                mtime_date = dt.fromtimestamp(os.path.getmtime(cache_file)).date()
                if mtime_date < dt.now().date():
                    is_cache_stale = True
                    
            if not os.path.exists(cache_file) or is_cache_stale:
                if os.path.exists(master_csv):
                    logger.info(f"[INDEXER] Regenerating cache file {cache_file} for prefix {prefix}...")
                    try:
                        import pandas as pd
                        full_df = pd.read_csv(master_csv, low_memory=False)
                        nifty_mask = full_df['SEM_TRADING_SYMBOL'].str.contains(f'{prefix}-', case=False, na=False)
                        option_mask = full_df['SEM_INSTRUMENT_NAME'].str.contains('OPT', case=False, na=False)
                        target_exch = 'BSE' if 'BSE' in inst.get('option_segment', 'NSE') else 'NSE'
                        exch_mask = full_df['SEM_EXM_EXCH_ID'].str.contains(target_exch, case=False, na=False)
                        prefix_df = full_df[nifty_mask & option_mask & exch_mask].copy()
                        if not prefix_df.empty:
                            prefix_df.to_csv(cache_file, index=False)
                            logger.info(f"[INDEXER] Successfully generated cache file {cache_file} with {len(prefix_df)} option contracts.")
                        else:
                            logger.warning(f"[INDEXER] Compact master has no option rows matching prefix {prefix} on exchange {target_exch}.")
                    except Exception as ex:
                        logger.error(f"[INDEXER] Failed to dynamically generate cache for {prefix}: {ex}")
            
            if not os.path.exists(cache_file):
                logger.warning(f"[INDEXER] F&O cache file for {prefix} not found on disk at {cache_file}")
                continue
            
            try:
                import pandas as pd
                df = pd.read_csv(cache_file)
                if df.empty:
                    continue
                
                count = 0
                for _, row in df.iterrows():
                    try:
                        sym = row.get('SEM_TRADING_SYMBOL')
                        if pd.isna(sym) or not sym:
                            continue
                        raw_sec_id = row.get('SEM_SMST_SECURITY_ID')
                        if pd.isna(raw_sec_id):
                            continue
                        sec_id = str(int(raw_sec_id))
                        expiry_val = row.get('SEM_EXPIRY_DATE')
                        if pd.isna(expiry_val) or not expiry_val:
                            continue
                        expiry_date_str = str(expiry_val).split(' ')[0]
                        lot_size = int(row.get('LOT_SIZE', row.get('lot_size', inst.get('lot_size', 1))))
                        
                        # Parse strike and type using regex (matches e.g., RECLTD-JUN2026-382.5-CE)
                        match = re.search(rf'\b{re.escape(prefix)}-(\w+)-(\d+(?:\.\d+)?)-(CE|PE)', sym, re.IGNORECASE)
                        if match:
                            val = float(match.group(2))
                            strike = int(val) if val.is_integer() else val
                            opt_type = match.group(3).upper()
                            
                            # Store in index mapping: key is (prefix, expiry_date, strike, opt_type)
                            self.master_cache_index[(prefix.upper(), expiry_date_str, strike, opt_type)] = (sec_id, lot_size, sym)
                            count += 1
                    except Exception:
                        continue
                        
                logger.info(f"[INDEXER] Indexed {count} contracts from {cache_file}")
            except Exception as e:
                logger.error(f"[INDEXER] Failed to index {cache_file}: {e}")
                
        logger.info(f"[INDEXER] Finished master index build in {time.time() - t0:.3f}s. Total indexed: {len(self.master_cache_index)}")
