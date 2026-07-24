import os
import time
import requests
import json
import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    ta = None
import numpy as np
from datetime import time as dt_time, datetime, timedelta
from dotenv import load_dotenv
from strategies import BacktestConfig, get_strategy, STRATEGY_REGISTRY

_OPT_DF_CACHE = {}
_OPT_DICT_CACHE = {}
_EXPIRY_CACHE = {}
_MASTER_DF = None
_FALLBACK_CE_CACHE = {}
_FALLBACK_PE_CACHE = {}
_FALLBACK_CE_DICT_CACHE = {}
_FALLBACK_PE_DICT_CACHE = {}

NSE_HOLIDAYS = {
    # 2021
    "2021-01-26", "2021-03-11", "2021-03-29", "2021-04-02", "2021-04-14",
    "2021-04-21", "2021-05-13", "2021-07-21", "2021-08-19", "2021-09-10",
    "2021-10-15", "2021-11-05", "2021-11-19",
    # 2022
    "2022-01-26", "2022-03-01", "2022-03-18", "2022-04-14", "2022-04-15",
    "2022-05-03", "2022-08-09", "2022-08-15", "2022-08-31", "2022-10-05",
    "2022-10-26", "2022-11-08",
    # 2023
    "2023-01-26", "2023-03-07", "2023-03-30", "2023-04-04", "2023-04-07",
    "2023-04-14", "2023-05-01", "2023-06-28", "2023-08-15", "2023-09-19",
    "2023-10-02", "2023-10-24", "2023-11-14", "2023-11-27", "2023-12-25",
    # 2024
    "2024-01-26", "2024-03-08", "2024-03-25", "2024-03-29", "2024-04-11",
    "2024-04-17", "2024-05-01", "2024-06-17", "2024-07-17", "2024-08-15",
    "2024-10-02", "2024-11-15", "2024-12-25",
    # 2025
    "2025-02-26", "2025-03-14", "2025-03-31", "2025-04-10", "2025-04-14",
    "2025-04-18", "2025-05-01", "2025-08-15", "2025-08-27", "2025-10-02",
    "2025-10-22", "2025-11-05", "2025-12-25",
    # 2026
    "2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31",
    "2026-04-03", "2026-04-14", "2026-05-01", "2026-05-28", "2026-06-26",
    "2026-09-14", "2026-10-02", "2026-10-20", "2026-11-10", "2026-11-24",
    "2026-12-25"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
os.makedirs(DATA_DIR, exist_ok=True)

# Load F&O Inception Cache
FNO_INCEPTION_CACHE = {}
inception_path = os.path.join(BASE_DIR, "fno_inception_cache.json")
if os.path.exists(inception_path):
    try:
        with open(inception_path, "r") as f:
            FNO_INCEPTION_CACHE = json.load(f)
    except Exception as e:
        print(f"[WARNING] Failed to load fno_inception_cache.json: {e}")

class SimulationEngine:
    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, new_config):
        self._config = new_config
        if new_config is not None:
            strategy_name = "Strategy_1"
            for s in STRATEGY_REGISTRY.keys():
                if getattr(new_config, f"ENABLE_{s.upper()}", False):
                    strategy_name = s
                    break
            params = {}
            for k in dir(new_config):
                if not k.startswith("__") and not callable(getattr(new_config, k)):
                    params[k] = getattr(new_config, k)
            self.strategy = get_strategy(strategy_name, params)

    def __init__(self, config: BacktestConfig, instrument_name="NIFTY", df_spot=None,
                 override_sl=None, override_trail=None, offline_mode=False, backtest_days=730):
        self._config = None
        self.strategy = None
        self.config = config
        self.offline_mode = offline_mode
        self.instrument_name = instrument_name
        self.backtest_days = backtest_days
        self.trades = []
        self.active_trades = []
        
        # Ingest API settings from .env (for dynamic contract fetching)
        load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
        self.client_id = os.getenv("DHAN_CLIENT_ID", "").strip().strip("'").strip('"')
        self.api_token = os.getenv("DHAN_API_TOKEN", "").strip().strip("'").strip('"')
        
        # Local Contract Cache Directory
        self.cache_dir = os.path.join(DATA_DIR, "contract_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Advanced Simulation Settings
        self.SLIPPAGE_PCT = 0.005  # 0.5% Slippage to mimic real-world execution
        self.cooldown_until = None  # Live bot 280s cooldown simulation
        self.enable_early_rejection = False
        self._opt_df_cache = _OPT_DF_CACHE
        self._opt_dict_cache = _OPT_DICT_CACHE
        
        # Fallback offline datasets
        self.fallback_ce = None
        self.fallback_pe = None
        self.fallback_ce_dict = None
        self.fallback_pe_dict = None
        self.master_df = None
        
        # Gatekeeper Data Audit Counters
        self.gk_total_checks = 0
        self.gk_oi_calculated_pass = 0
        self.gk_oi_missing_bypass = 0
        self.gk_oi_failed = 0
        self.gk_vol_calculated_pass = 0
        self.gk_vol_missing_bypass = 0
        self.gk_vol_failed = 0
        
        # Load per-instrument config dynamically
        self.inst_config = self._load_instrument_config(instrument_name)
        if override_sl is not None:
            self.inst_config['sl_mult_buy'] = override_sl
            self.inst_config['sl_mult_sell'] = override_sl
        if override_trail is not None:
            self.inst_config['trailing_mult_buy'] = override_trail
            self.inst_config['trailing_mult_sell'] = override_trail
            
        self.LOT_SIZE = self.inst_config.get('lot_size', 1) or 1
        self.df_spot = df_spot
        
        # Apply instrument config overrides directly to strategy params
        if self.strategy and hasattr(self, 'inst_config'):
            for k, v in self.inst_config.items():
                self.strategy.params[k] = v
        
    def _load_instrument_config(self, instrument_name):
        inst_file = os.path.join(BASE_DIR, "instruments.json")
        defaults = {
            "lot_size": 25,
            "num_lots_buy": 1,
            "num_lots_sell": 1,
            "sl_mult_buy": 1.4,
            "sl_mult_sell": 1.4,
            "trailing_mult_buy": 1.6,
            "trailing_mult_sell": 1.6,
            "strike_offset": 0,
            "strike_offset_buy": 0,
            "strike_offset_sell": 0,
            "strike_step": 100,
            "profit_target_buy": 0,
            "profit_target_sell": 0,
            "option_delta": 0.5,
            "option_strategy_mode": "DIRECT",
            "strategy_leg_width": 1,
            "execution_mode": "OPTION",
            "stock_qty_override": None,
            "points_sl_buy": 0,
            "points_target_buy": 0,
            "points_trail_buy": 0,
            "points_sl_sell": 0,
            "points_target_sell": 0,
            "points_trail_sell": 0,
            "local_exit_monitoring": None,
            "gatekeeper_enabled": 0,
            "gatekeeper_time_filter_minutes": 20,
            "gatekeeper_window_minutes": 5,
            "gatekeeper_oi_min_change_pct": 1.0,
            "gatekeeper_volume_sma_period": 15,
            "gatekeeper_volume_multiplier": 1.2
        }
        try:
            with open(inst_file, "r") as f:
                instruments = json.load(f)
            inst = instruments.get(instrument_name, {})
            
            # Apply strategy-specific overrides if active
            if self.strategy:
                overrides = inst.get("strategy_overrides", {}).get(self.strategy.name, {})
                if isinstance(overrides, dict) and overrides:
                    for k, v in overrides.items():
                        inst[k] = v
            
            # First ensure strike_offset is loaded
            if "strike_offset" not in inst:
                inst["strike_offset"] = defaults["strike_offset"]
                
            # Set dynamic defaults for buy/sell specific offsets based on strike_offset
            defaults["strike_offset_buy"] = inst["strike_offset"]
            defaults["strike_offset_sell"] = inst["strike_offset"]
            
            for key, val in defaults.items():
                if key not in inst:
                    inst[key] = val
            return inst
        except Exception as e:
            print(f"[WARNING] Could not load instruments.json in backtest_engine: {e}. Using defaults.")
            return defaults
        
    def _apply_fno_inception_filter(self):
        if self.df_spot is None or self.df_spot.empty:
            return
            
        if self.inst_config.get("execution_mode", "OPTION") == "STOCK":
            return
            
        fno_inception_date = None
        spot_sym = self.instrument_name.upper()
        fno_pref = self.inst_config.get('fno_prefix', self.instrument_name).strip().upper()
        
        spot_inc = FNO_INCEPTION_CACHE.get(spot_sym, "9999-12-31")
        pref_inc = FNO_INCEPTION_CACHE.get(fno_pref, "9999-12-31")
        
        if spot_inc is None or pref_inc is None:
            fno_inception_date = None
        else:
            valid_dates = [d for d in [spot_inc, pref_inc] if d != "9999-12-31"]
            if valid_dates:
                fno_inception_date = min(valid_dates)
                
        if fno_inception_date:
            print(f"[INFO] Filtering spot data for {self.instrument_name} to on/after F&O inception date: {fno_inception_date}")
            self.df_spot = self.df_spot[self.df_spot.index >= pd.Timestamp(fno_inception_date)]

    def _compute_median_atr_pct(self):
        if self.df_spot is not None and 'ATR' in self.df_spot.columns and not self.df_spot.empty:
            non_zero_spot = self.df_spot[self.df_spot['close'] > 0]
            if not non_zero_spot.empty:
                atr_pct = (non_zero_spot['ATR'] / non_zero_spot['close']) * 100
                self.median_atr_pct = float(atr_pct.median())
            else:
                self.median_atr_pct = 0.0
        else:
            self.median_atr_pct = 0.0

    def load_data(self):
        prefix = self.instrument_name.lower()
        
        global _FALLBACK_CE_CACHE, _FALLBACK_PE_CACHE, _FALLBACK_CE_DICT_CACHE, _FALLBACK_PE_DICT_CACHE
        
        # Check if fallbacks are disabled via environment variable
        disable_fallbacks = os.getenv("DISABLE_FALLBACKS", "False").lower() in ("true", "1", "yes")
        
        if disable_fallbacks:
            print("[INFO] DISABLE_FALLBACKS is True. Bypassing offline ATM option fallback files.")
            self.fallback_ce = None
            self.fallback_pe = None
            self.fallback_ce_dict = None
            self.fallback_pe_dict = None
        else:
            # Pre-load offline ATM fallbacks if not already loaded
            ce_path = os.path.join(DATA_DIR, f"{prefix}_atm_ce.csv")
            pe_path = os.path.join(DATA_DIR, f"{prefix}_atm_pe.csv")
            
            if prefix not in _FALLBACK_CE_CACHE and os.path.exists(ce_path):
                print(f"[INFO] Pre-loading offline ATM options CE fallback file for {self.instrument_name}...")
                df_ce = pd.read_csv(ce_path, index_col='timestamp', parse_dates=True)
                _FALLBACK_CE_CACHE[prefix] = df_ce
                print(f"[SUCCESS] Loaded CE Fallback File for {self.instrument_name}: {len(df_ce)} rows.")
                print(f"[INFO] Grouping CE fallback for {self.instrument_name} by date...")
                _FALLBACK_CE_DICT_CACHE[prefix] = {str(d): grp for d, grp in df_ce.groupby(df_ce.index.date)}
                print(f"[SUCCESS] Grouped CE fallback for {self.instrument_name} by date.")
                
            if prefix not in _FALLBACK_PE_CACHE and os.path.exists(pe_path):
                print(f"[INFO] Pre-loading offline ATM options PE fallback file for {self.instrument_name}...")
                df_pe = pd.read_csv(pe_path, index_col='timestamp', parse_dates=True)
                _FALLBACK_PE_CACHE[prefix] = df_pe
                print(f"[SUCCESS] Loaded PE Fallback File for {self.instrument_name}: {len(df_pe)} rows.")
                print(f"[INFO] Grouping PE fallback for {self.instrument_name} by date...")
                _FALLBACK_PE_DICT_CACHE[prefix] = {str(d): grp for d, grp in df_pe.groupby(df_pe.index.date)}
                print(f"[SUCCESS] Grouped PE fallback for {self.instrument_name} by date.")
                
            self.fallback_ce = _FALLBACK_CE_CACHE.get(prefix)
            self.fallback_pe = _FALLBACK_PE_CACHE.get(prefix)
            self.fallback_ce_dict = _FALLBACK_CE_DICT_CACHE.get(prefix)
            self.fallback_pe_dict = _FALLBACK_PE_DICT_CACHE.get(prefix)

        if self.df_spot is not None:
            # Ensure it is a DatetimeIndex
            if not isinstance(self.df_spot.index, pd.DatetimeIndex):
                self.df_spot.index = pd.to_datetime(self.df_spot.index, errors='coerce')
                self.df_spot = self.df_spot[self.df_spot.index.notna()]
                self.df_spot.index = pd.DatetimeIndex(self.df_spot.index)
            # Data already loaded (e.g. from optimizer)
            self.df_spot = self.df_spot.between_time('09:15', '15:30')
            self._apply_fno_inception_filter()
            self._compute_median_atr_pct()
            return
            
        print(f"[INFO] Loading Spot data for {self.instrument_name}...")
        spot_path = os.path.join(DATA_DIR, f"{prefix}_spot.csv")
        
        need_download = False
        if not os.path.exists(spot_path):
            need_download = True
        else:
            try:
                # Cooldown check: if the spot file was modified within the last hour, skip re-download checks
                file_age_seconds = time.time() - os.path.getmtime(spot_path)
                if file_age_seconds > 3600:
                    # Check if enough history is present in the file
                    df_temp = pd.read_csv(spot_path, nrows=5)
                    if not df_temp.empty:
                        col_name = 'timestamp' if 'timestamp' in df_temp.columns else ('start_time' if 'start_time' in df_temp.columns else df_temp.columns[0])
                        first_ts = pd.to_datetime(df_temp[col_name].iloc[0])
                        required_start = datetime.now() - timedelta(days=self.backtest_days)
                        if first_ts > required_start:
                            print(f"[INFO] Spot file starts at {first_ts.date()}, but {self.backtest_days} days of history requested (needs to start by {required_start.date()}). Re-downloading...")
                            need_download = True
            except Exception as e:
                need_download = True
                
        if need_download:
            self._auto_download_spot_candles(spot_path)
            
        self.df_spot = pd.read_csv(spot_path)
        # Standardize and explicitly parse the index to DatetimeIndex to handle different CSV date formats (e.g. DD/MM/YYYY vs YYYY-MM-DD)
        if 'timestamp' in self.df_spot.columns:
            self.df_spot['timestamp'] = pd.to_datetime(self.df_spot['timestamp'], errors='coerce')
            self.df_spot.set_index('timestamp', inplace=True)
        elif 'start_time' in self.df_spot.columns:
            self.df_spot['timestamp'] = pd.to_datetime(self.df_spot['start_time'], errors='coerce')
            self.df_spot.set_index('timestamp', inplace=True)
            
        # Ensure the index is a DatetimeIndex
        self.df_spot = self.df_spot[self.df_spot.index.notna()]
        self.df_spot.index = pd.DatetimeIndex(self.df_spot.index)
        
        self.df_spot = self.df_spot.between_time('09:15', '15:30')
        
        import logging
        from live_trade_fixed import process_market_data
        bt_logger = logging.getLogger("Backtest")
        self.df_spot = process_market_data(self.df_spot, self.config, bt_logger, instrument_name=self.instrument_name)
        self._apply_fno_inception_filter()
        
        # Filter spot data to the requested backtest days to prevent backtesting 5 years of data
        if self.backtest_days and not self.df_spot.empty:
            print(f"[DEBUG] self.backtest_days = {self.backtest_days}")
            print(f"[DEBUG] df_spot shape before slice: {self.df_spot.shape}")
            print(f"[DEBUG] df_spot index max: {self.df_spot.index.max()}")
            cutoff_date = self.df_spot.index.max() - pd.Timedelta(days=self.backtest_days)
            print(f"[DEBUG] calculated cutoff_date: {cutoff_date}")
            self.df_spot = self.df_spot[self.df_spot.index >= cutoff_date]
            print(f"[DEBUG] df_spot shape after slice: {self.df_spot.shape}")
        self._compute_median_atr_pct()
        
    def _auto_download_spot_candles(self, spot_path):
        """Automatically downloads the requested range of 1-minute spot candles from Dhan API."""
        if not self.client_id or not self.api_token:
            raise FileNotFoundError(
                f"Missing required Spot index file: {spot_path}. Run data_fetcher.py first or add Dhan API credentials to .env."
            )
            
        print(f"[INFO] Downloading last {self.backtest_days} days of spot data from Dhan API...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.backtest_days)
        
        sec_id = str(self.inst_config['security_id'])
        inst_type = self.inst_config.get('type', 'INDEX')
        exch_seg = self.inst_config.get('exchange_segment', 'IDX_I')
        if inst_type == "OPTION":
            hist_inst = self.inst_config.get('instrument_type')
            if not hist_inst:
                fno_prefix = self.inst_config.get('fno_prefix', self.instrument_name).upper()
                if any(x in fno_prefix for x in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY']):
                    hist_inst = 'OPTIDX'
                else:
                    hist_inst = 'OPTSTK'
        else:
            hist_inst = "INDEX" if inst_type == "INDEX" else "EQUITY"
        
        headers = {
            "access-token": self.api_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        url = "https://api.dhan.co/v2/charts/intraday"
        
        all_dfs = []
        current = start_date
        while current < end_date:
            next_m = current + timedelta(days=30)
            chunk_end = min(next_m, end_date)
            
            payload = {
                "securityId": sec_id,
                "exchangeSegment": exch_seg,
                "instrument": hist_inst,
                "interval": "1",
                "fromDate": current.strftime("%Y-%m-%d 09:15:00"),
                "toDate": chunk_end.strftime("%Y-%m-%d 15:30:00")
            }
            
            print(f"  Fetching spot chunk from {current.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}...")
            
            for attempt in range(3):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=15)
                    if response.status_code == 200:
                        resp_json = response.json()
                        raw_data = resp_json.get("data", resp_json)
                        
                        df = pd.DataFrame()
                        if raw_data and isinstance(raw_data, list):
                            df = pd.DataFrame(raw_data)
                        elif raw_data and isinstance(raw_data, dict) and "close" in raw_data:
                            df = pd.DataFrame(raw_data)
                            
                        if not df.empty:
                            df.columns = df.columns.str.lower()
                            if 'timestamp' in df.columns:
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                                df.set_index('timestamp', inplace=True)
                            elif 'start_time' in df.columns:
                                df['timestamp'] = pd.to_datetime(df['start_time'])
                                df.set_index('timestamp', inplace=True)
                                
                            cols = ['open', 'high', 'low', 'close', 'volume']
                            cols = [c for c in cols if c in df.columns]
                            all_dfs.append(df[cols])
                        break
                    elif response.status_code == 429:
                        time.sleep(10)
                except Exception as e:
                    print(f"  [WARNING] Chunk download failed: {e}")
                time.sleep(1)
            current = next_m
            
        if all_dfs:
            final_df = pd.concat(all_dfs).sort_index()
            final_df = final_df[~final_df.index.duplicated(keep='first')]
            os.makedirs(os.path.dirname(spot_path), exist_ok=True)
            final_df.to_csv(spot_path)
            print(f"[SUCCESS] Downloaded and cached {len(final_df)} spot rows -> {spot_path}")
        else:
            raise FileNotFoundError(f"[ERROR] Failed to fetch spot index data for {self.instrument_name} from Dhan API.")
        
    def _get_expiry_date(self, trade_date, expiry_index: int = None) -> str:
        """Programmatically estimate the weekly/monthly expiry date based on standard contract calendars, transition rules, and holidays."""
        from datetime import date
        
        if expiry_index is None:
            expiry_index = self.inst_config.get("expiry_index", 0)
            
        symbol = self.instrument_name.upper()
        
        # Normalize trade_date to a datetime.date object
        if isinstance(trade_date, str):
            t_date = datetime.strptime(trade_date, "%Y-%m-%d").date()
        elif hasattr(trade_date, 'date'):
            t_date = trade_date.date()
        elif isinstance(trade_date, date):
            t_date = trade_date
        else:
            t_date = trade_date
            
        # Helper to check if a day is a weekend or NSE trading holiday
        def is_holiday(check_date: date) -> bool:
            if check_date.weekday() >= 5:
                return True
            date_str = check_date.strftime("%Y-%m-%d")
            return date_str in NSE_HOLIDAYS
            
        # Check if it is a stock option (monthly only)
        # Helper to get base weekly/monthly expiry weekday (for indices/stocks)
        def get_base_weekday(curr_date: date) -> int:
            if symbol == "FINNIFTY":
                return 1  # Tuesday
            elif symbol == "MIDCPNIFTY":
                return 0  # Monday
            elif symbol == "SENSEX":
                # Shifted to Tuesday in Jan 2025, and to Thursday on Sep 1, 2025
                if curr_date >= date(2025, 9, 1):
                    return 3  # Thursday
                elif curr_date >= date(2025, 1, 1):
                    return 1  # Tuesday
                else:
                    return 4  # Friday
            elif symbol == "BANKNIFTY":
                # Shifted to Wednesday starting Sept 4, 2023
                if curr_date >= date(2023, 9, 4):
                    return 2  # Wednesday
                else:
                    return 3  # Thursday
            elif symbol == "NIFTY":
                # Shifted to Tuesday starting Sept 2, 2025
                if curr_date >= date(2025, 9, 2):
                    return 1  # Tuesday
                else:
                    return 3  # Thursday
            else:
                # Stock options monthly expiry shifted to Tuesday starting Sept 2, 2025
                if curr_date >= date(2025, 9, 2):
                    return 1  # Tuesday
                else:
                    return 3  # Thursday (default)

        # Check if the instrument is a weekly index (indices have weekly expiries, stock options only monthly)
        is_weekly_index = (symbol in ["NIFTY", "SENSEX"])
        is_monthly_only = not is_weekly_index

        
        if is_monthly_only:
            def get_monthly_expiry(check_date: date, idx: int) -> date:
                y, m = check_date.year, check_date.month
                
                def get_symbol_last_weekday_of_month(year: int, month: int) -> date:
                    if month == 12:
                        next_month = date(year + 1, 1, 1)
                    else:
                        next_month = date(year, month + 1, 1)
                    last_day = next_month - timedelta(days=1)
                    curr = last_day
                    while True:
                        target_wd = get_base_weekday(curr)
                        if curr.weekday() == target_wd:
                            return curr
                        curr -= timedelta(days=1)

                found_months = []
                curr_y, curr_m = y, m
                
                for _ in range(idx + 3):
                    raw_exp = get_symbol_last_weekday_of_month(curr_y, curr_m)
                        
                    adj_exp = raw_exp
                    while is_holiday(adj_exp):
                        adj_exp -= timedelta(days=1)
                        
                    if adj_exp >= t_date:
                        found_months.append(adj_exp)
                        
                    if curr_m == 12:
                        curr_y += 1
                        curr_m = 1
                    else:
                        curr_m += 1
                        
                if len(found_months) > idx:
                    return found_months[idx]
                return t_date
                
            monthly_expiry_date = get_monthly_expiry(t_date, expiry_index)
            return monthly_expiry_date.strftime("%Y-%m-%d")

        # Iterate day-by-day starting from t_date to find weekly expiries (indices)
        curr_date = t_date
        found_expiries = []
        
        # Search up to 45 days in the future to find expiries
        limit_date = t_date + timedelta(days=45)
        
        while curr_date <= limit_date:
            target_weekday = get_base_weekday(curr_date)
            if curr_date.weekday() == target_weekday:
                # We found a raw weekly expiry candidate!
                # Adjust for holidays by shifting to the preceding trading day
                exp_date = curr_date
                while is_holiday(exp_date):
                    exp_date -= timedelta(days=1)
                
                # Check if this holiday-adjusted date is already found (to avoid duplicates due to shifts)
                if exp_date not in found_expiries:
                    # Make sure the expiry date is on or after the trade_date
                    if exp_date >= t_date:
                        found_expiries.append(exp_date)
                        if len(found_expiries) > expiry_index + 1:
                            break
            curr_date += timedelta(days=1)
            
        if len(found_expiries) > expiry_index:
            return found_expiries[expiry_index].strftime("%Y-%m-%d")
            
        # Fallback to simple calculation if loop fails
        expiry_weekday = 3
        if symbol == "FINNIFTY":
            expiry_weekday = 1
        elif symbol == "MIDCPNIFTY":
            expiry_weekday = 0
        elif symbol == "SENSEX":
            if t_date >= date(2025, 9, 1):
                expiry_weekday = 3
            elif t_date >= date(2025, 1, 1):
                expiry_weekday = 1
            else:
                expiry_weekday = 4
        elif symbol == "BANKNIFTY":
            if t_date >= date(2023, 9, 4):
                expiry_weekday = 2
            else:
                expiry_weekday = 3
        elif symbol == "NIFTY":
            if t_date >= date(2025, 9, 2):
                expiry_weekday = 1
            else:
                expiry_weekday = 3
                
        days_ahead = (expiry_weekday - t_date.weekday() + 7) % 7
        est_date = t_date + timedelta(days=days_ahead + (expiry_index * 7))
        while is_holiday(est_date):
            est_date -= timedelta(days=1)
        return est_date.strftime("%Y-%m-%d")

    def apply_slippage(self, price: float, side: str, is_stock: bool = False) -> float:
        """Apply slippage and round to nearest 0.05 if stock or apply slippage floor if option."""
        pct = 0.0005 if is_stock else self.SLIPPAGE_PCT
        if is_stock:
            if side == 'BUY':
                res_price = price * (1 + pct)
            else:
                res_price = price * (1 - pct)
            res_price = round(res_price / 0.05) * 0.05
        else:
            # Option slippage: minimum of 1 tick (0.05)
            slip_amt = max(price * pct, 0.05)
            if side == 'BUY':
                res_price = price + slip_amt
            else:
                res_price = price - slip_amt
            res_price = max(res_price, 0.05)
        return round(res_price, 2)
            
    def _get_option_candles(self, strike: int, option_type: str, trade_date, relative_strike: str = "ATM", expiry_date_str: str = None) -> pd.DataFrame:
        prefix = self.instrument_name.lower()
        date_str = trade_date.strftime("%Y-%m-%d") if hasattr(trade_date, 'strftime') else str(trade_date)
        if expiry_date_str is None:
            expiry_index = self.inst_config.get("expiry_index", 0)
            expiry_date_str = self._get_actual_expiry_date(trade_date, expiry_index)
        cache_key = (prefix, strike, option_type.upper(), expiry_date_str, date_str)
        
        if cache_key in self._opt_df_cache:
            return self._opt_df_cache[cache_key]
            
        df = self._get_option_candles_uncached(strike, option_type, trade_date, relative_strike, expiry_date_str)
        self._opt_df_cache[cache_key] = df
        return df

    def _get_option_candle_dict(self, strike: int, option_type: str, trade_date, expiry_date_str: str = None) -> dict:
        """Returns a fast lookup dictionary mapping Timestamp -> {open, high, low, close}"""
        prefix = self.instrument_name.lower()
        date_str = trade_date.strftime("%Y-%m-%d") if hasattr(trade_date, 'strftime') else str(trade_date)
        if expiry_date_str is None:
            expiry_index = self.inst_config.get("expiry_index", 0)
            expiry_date_str = self._get_actual_expiry_date(trade_date, expiry_index)
        cache_key = (prefix, strike, option_type.upper(), expiry_date_str, date_str)
        
        if cache_key in self._opt_dict_cache:
            return self._opt_dict_cache[cache_key]
            
        df = self._get_option_candles(strike, option_type, trade_date, expiry_date_str=expiry_date_str)
        if df is not None and not df.empty:
            cols = [c for c in ['open', 'high', 'low', 'close', 'volume', 'oi'] if c in df.columns]
            dict_data = df[cols].to_dict(orient='index')
            self._opt_dict_cache[cache_key] = dict_data
            return dict_data
        else:
            self._opt_dict_cache[cache_key] = {}
            return {}

    def _load_master_cache(self):
        """Lazily load the master cache file to map option details to security IDs."""
        global _MASTER_DF
        if _MASTER_DF is not None:
            self.master_df = _MASTER_DF
            return _MASTER_DF
            
        cache_path = os.path.join(BASE_DIR, "dhanhq_master_cache.csv")
        if not os.path.exists(cache_path):
            print(f"[WARNING] Master cache file not found at: {cache_path}")
            self.master_df = pd.DataFrame()
            _MASTER_DF = self.master_df
            return self.master_df
            
        try:
            print("[INFO] Lazily loading master cache...")
            df = pd.read_csv(
                cache_path,
                dtype={
                    'SECURITY_ID': str,
                    'UNDERLYING_SYMBOL': str,
                    'OPTION_TYPE': str,
                    'STRIKE_PRICE': float,
                    'SM_EXPIRY_DATE': str,
                    'SEGMENT': str,
                    'EXCH_ID': str
                },
                low_memory=False
            )
            df['UNDERLYING_SYMBOL'] = df['UNDERLYING_SYMBOL'].astype(str).str.strip().str.upper()
            df['OPTION_TYPE'] = df['OPTION_TYPE'].astype(str).str.strip().str.upper()
            df['SM_EXPIRY_DATE'] = df['SM_EXPIRY_DATE'].astype(str).str.strip()
            df['SEGMENT'] = df['SEGMENT'].astype(str).str.strip().str.upper()
            df['EXCH_ID'] = df['EXCH_ID'].astype(str).str.strip().str.upper()
            print(f"[SUCCESS] Master cache loaded: {len(df)} rows.")
            _MASTER_DF = df
            self.master_df = df
        except Exception as e:
            print(f"[ERROR] Failed to load master cache: {e}")
            self.master_df = pd.DataFrame()
            _MASTER_DF = self.master_df
            
        return self.master_df

    def _lookup_option_security_id(self, strike: float, option_type: str, expiry_date_str: str) -> str:
        """Lookup option contract security ID from master cache."""
        df = self._load_master_cache()
        if df.empty:
            return None
            
        underlying = self.inst_config.get('fno_prefix', self.instrument_name).strip().upper()
        opt_type = option_type.strip().upper()
        if opt_type == 'CALL':
            opt_type = 'CE'
        elif opt_type == 'PUT':
            opt_type = 'PE'
            
        matches = df[
            (df['UNDERLYING_SYMBOL'] == underlying) &
            (df['EXCH_ID'] == 'NSE') &
            (df['OPTION_TYPE'] == opt_type) &
            (df['STRIKE_PRICE'] == float(strike)) &
            (df['SM_EXPIRY_DATE'] == expiry_date_str)
        ]
        
        if not matches.empty:
            sec_id = matches.iloc[0]['SECURITY_ID']
            if pd.notna(sec_id):
                return str(sec_id).strip()
                
        return None

    def _get_actual_expiry_date(self, trade_date, expiry_index: int = 0) -> str:
        """Resolve the actual expiry date from the master cache that is on or after trade_date."""
        underlying = self.inst_config.get('fno_prefix', self.instrument_name).strip().upper()
        # Ensure trade_date is a datetime.date object for comparison
        from datetime import date
        if isinstance(trade_date, str):
            t_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()
        elif hasattr(trade_date, 'date'):
            t_date_obj = trade_date.date()
        else:
            t_date_obj = trade_date

        date_str = t_date_obj.strftime("%Y-%m-%d")
        cache_key = (underlying, date_str, expiry_index)
        
        global _EXPIRY_CACHE
        if cache_key in _EXPIRY_CACHE:
            return _EXPIRY_CACHE[cache_key]
            
        # Bypass master cache for weekly indices to avoid incorrect monthly fallback due to incomplete cache
        is_weekly_index = (underlying in ["NIFTY", "SENSEX"])
        
        # Determine if we should roll over to next expiry on expiry day
        # We roll over for weekly/index options, but NOT for stock options due to Dhan's historical next-month data gap
        should_rollover = (self.inst_config.get('type', 'INDEX').upper() == 'INDEX')
        
        if is_weekly_index:
            res = self._get_expiry_date(t_date_obj, expiry_index)
            if res == date_str and should_rollover:
                res = self._get_expiry_date(t_date_obj, expiry_index + 1)
            _EXPIRY_CACHE[cache_key] = res
            return res

        df = self._load_master_cache()
        if df.empty:
            res = self._get_expiry_date(t_date_obj, expiry_index)
            if res == date_str and should_rollover:
                res = self._get_expiry_date(t_date_obj, expiry_index + 1)
            _EXPIRY_CACHE[cache_key] = res
            return res
            
        matching_expiries = df[
            (df['UNDERLYING_SYMBOL'] == underlying) &
            (df['EXCH_ID'] == 'NSE') &
            (df['SM_EXPIRY_DATE'] >= date_str)
        ]['SM_EXPIRY_DATE'].unique()
        
        if len(matching_expiries) > 0:
            sorted_expiries = sorted(matching_expiries)
            if expiry_index < len(sorted_expiries):
                res = sorted_expiries[expiry_index]
                if res == date_str and should_rollover:
                    res = sorted_expiries[expiry_index + 1] if (expiry_index + 1) < len(sorted_expiries) else res
                
                # If the matched expiry is too far in the future compared to trade_date, it's likely a master cache leak
                try:
                    res_date = datetime.strptime(res, "%Y-%m-%d").date()
                    if (res_date - t_date_obj).days <= 35:
                        _EXPIRY_CACHE[cache_key] = res
                        return res
                except:
                    pass
                
        res = self._get_expiry_date(t_date_obj, expiry_index)
        if res == date_str and should_rollover:
            res = self._get_expiry_date(t_date_obj, expiry_index + 1)
        _EXPIRY_CACHE[cache_key] = res
        return res

    def _get_strike_step(self, trade_date, expiry_date_str=None) -> float:
        # 1. Resolve expiry date
        if expiry_date_str is None:
            expiry_index = self.inst_config.get("expiry_index", 0)
            expiry_date_str = self._get_actual_expiry_date(trade_date, expiry_index)
            
        # 2. Check if we have historical registry loaded
        if not hasattr(self, '_strike_step_registry'):
            self._strike_step_registry = {}
            registry_path = os.path.join(BASE_DIR, "strike_step_history.json")
            if os.path.exists(registry_path):
                try:
                    with open(registry_path, 'r') as f:
                        self._strike_step_registry = json.load(f)
                    print(f"[INFO] Loaded historical strike step registry from {registry_path} with {len(self._strike_step_registry)} symbols.")
                except Exception as e:
                    print(f"[WARNING] Failed to load strike step registry: {e}")
                    
        symbol = self.instrument_name.upper()
        
        # 3. Check registry for symbol and expiry
        if symbol in self._strike_step_registry:
            sym_history = self._strike_step_registry[symbol]
            if expiry_date_str in sym_history:
                detected_step = sym_history[expiry_date_str]
                return float(detected_step)
                
        # 4. Fallback to weekly index overrides
        if symbol == "NIFTY":
            return 50.0
        elif symbol == "FINNIFTY":
            return 50.0
        elif symbol == "MIDCPNIFTY":
            return 25.0
            
        # 5. Fallback to configured static strike_step
        return float(self.inst_config.get('strike_step', 100.0))

    def _get_lot_size(self, trade_date, expiry_date_str=None) -> int:
        # 1. Resolve expiry date
        if expiry_date_str is None:
            expiry_index = self.inst_config.get("expiry_index", 0)
            expiry_date_str = self._get_actual_expiry_date(trade_date, expiry_index)
            
        # 2. Check if we have historical registry loaded
        if not hasattr(self, '_lot_size_registry'):
            self._lot_size_registry = {}
            registry_path = os.path.join(BASE_DIR, "lot_size_history.json")
            if os.path.exists(registry_path):
                try:
                    with open(registry_path, 'r') as f:
                        self._lot_size_registry = json.load(f)
                    print(f"[INFO] Loaded historical lot size registry from {registry_path} with {len(self._lot_size_registry)} symbols.")
                except Exception as e:
                    print(f"[WARNING] Failed to load lot size registry: {e}")
                    
        symbol = self.instrument_name.upper()
        
        # 3. Check registry for symbol and expiry
        if symbol in self._lot_size_registry:
            sym_history = self._lot_size_registry[symbol]
            if expiry_date_str in sym_history:
                detected_lot = sym_history[expiry_date_str]
                return int(detected_lot)
                
        # 4. Fallback to configured static lot_size
        return int(self.inst_config.get('lot_size', 1))

    def _validate_gatekeeper(self, target_strike, option_type_str, trade_date, entry_timestamp, is_short=False) -> bool:
        # 1. Market opening noise filter
        dt_time_obj = entry_timestamp.time() if hasattr(entry_timestamp, 'time') else entry_timestamp
        # Convert trigger time to minutes past 09:15
        mins_past_open = (dt_time_obj.hour * 60 + dt_time_obj.minute) - (9 * 60 + 15)
        time_filter_mins = self.inst_config.get("gatekeeper_time_filter_minutes", 20)
        if mins_past_open < time_filter_mins:
            print(f"  [GATEKEEPER] Skipped: {entry_timestamp} is within early morning noise filter ({time_filter_mins} mins).")
            return False
            
        # 2. Get parameters
        window = int(self.inst_config.get("gatekeeper_window_minutes", 5))
        oi_min_change = float(self.inst_config.get("gatekeeper_oi_min_change_pct", 1.0))
        vol_sma_period = int(self.inst_config.get("gatekeeper_volume_sma_period", 15))
        vol_mult = float(self.inst_config.get("gatekeeper_volume_multiplier", 1.2))
        
        # 3. Determine strikes to check (ATM, ATM-1, ATM+1 or Single Strike)
        if self.inst_config.get("gatekeeper_single_strike", 0) == 1:
            strikes_to_check = [target_strike]
        else:
            strike_step = self._get_strike_step(trade_date)
            strikes_to_check = [target_strike - strike_step, target_strike, target_strike + strike_step]
        
        # Ensure strikes are integers if applicable
        strikes_to_check = [int(s) if isinstance(s, float) and s.is_integer() else s for s in strikes_to_check]
        
        expiry_index = self.inst_config.get("expiry_index", 0)
        expiry_date_str = self._get_actual_expiry_date(trade_date, expiry_index)
        
        passes = 0
        valid_strikes_count = 0
        
        for strike in strikes_to_check:
            self.gk_total_checks += 1
            df = self._get_option_candles(strike, option_type_str, trade_date, expiry_date_str=expiry_date_str)
            if df is None or df.empty:
                self.gk_oi_missing_bypass += 1
                self.gk_vol_missing_bypass += 1
                continue
                
            valid_strikes_count += 1
            
            # Filter up to entry_timestamp (excluding the entry candle itself which has just started and is incomplete)
            try:
                sub_df = df.loc[:entry_timestamp]
                if not sub_df.empty and sub_df.index[-1] == entry_timestamp:
                    sub_df = sub_df.iloc[:-1]
            except Exception:
                self.gk_oi_missing_bypass += 1
                self.gk_vol_missing_bypass += 1
                continue
                
            if len(sub_df) < max(window + 1, vol_sma_period + 1):
                self.gk_oi_missing_bypass += 1
                self.gk_vol_missing_bypass += 1
                continue
                
            # Extract historical values
            current_close = sub_df['close'].iloc[-1]
            prev_close = sub_df['close'].iloc[-1 - window]
            
            # Buildup check
            price_change = current_close - prev_close
            
            # Check price direction matches trade intention
            if not is_short:
                # Option Buying: we want option price to increase
                price_direction_ok = (price_change > 0)
            else:
                # Option Selling: we want option price to decrease
                price_direction_ok = (price_change < 0)
                
            # OI change verification (Velocity)
            if 'oi' in sub_df.columns:
                current_oi = sub_df['oi'].iloc[-1]
                prev_oi = sub_df['oi'].iloc[-1 - window]
                oi_change = current_oi - prev_oi
                oi_change_pct = (oi_change / prev_oi * 100.0) if prev_oi > 0 else 0.0
                oi_ok = (abs(oi_change_pct) >= oi_min_change)
                if oi_ok:
                    self.gk_oi_calculated_pass += 1
                else:
                    self.gk_oi_failed += 1
            else:
                oi_ok = True
                self.gk_oi_missing_bypass += 1
                
            # Volume verification
            if 'volume' in sub_df.columns:
                current_volume = sub_df['volume'].iloc[-1]
                # Volume SMA of the preceding vol_sma_period minutes (excluding current minute)
                volume_history = sub_df['volume'].iloc[-vol_sma_period - 1:-1]
                volume_sma = volume_history.mean()
                volume_ok = (current_volume >= vol_mult * volume_sma) if volume_sma > 0 else True
                if volume_ok:
                    self.gk_vol_calculated_pass += 1
                else:
                    self.gk_vol_failed += 1
            else:
                volume_ok = True
                self.gk_vol_missing_bypass += 1
            
            if price_direction_ok and oi_ok and volume_ok:
                passes += 1
                
        # If at least 2 of the 3 strikes pass (or 1 if only 1 valid strike was successfully loaded)
        required_passes = 2 if valid_strikes_count >= 3 else 1
        if passes >= required_passes:
            print(f"  [GATEKEEPER PASS] {entry_timestamp} | Passes: {passes}/{valid_strikes_count} (Required: {required_passes})")
            return True
            
        print(f"  [GATEKEEPER SKIP] {entry_timestamp} | Passes: {passes}/{valid_strikes_count} (Required: {required_passes})")
        return False

    def _get_option_candles_via_stitching(self, strike: int, option_type: str, trade_date, date_str: str, expiry_index: int, headers: dict, expiry_date_str: str = None) -> pd.DataFrame:
        """Fetch relative strikes from Dhan rolling option API and stitch them using a price-continuity tracker to avoid jumps."""
        print(f"[STITCHER] Initiating price-continuity stitching for {self.instrument_name} {strike} {option_type} on {date_str}...")
        
        # 1. Get spot data for the specific day to determine range of spot prices
        if self.df_spot is None:
            print("[STITCHER ERROR] Spot data is required for stitching.")
            return pd.DataFrame()
            
        try:
            spot_day = self.df_spot.loc[date_str]
        except KeyError:
            print(f"[STITCHER ERROR] Spot data not found for date {date_str}.")
            return pd.DataFrame()
            
        if spot_day.empty:
            print(f"[STITCHER ERROR] Spot data empty for date {date_str}.")
            return pd.DataFrame()
            
        # Calculate dynamic offsets
        spot_low = spot_day['close'].min()
        spot_high = spot_day['close'].max()
        # Determine actual market option strike step (broker relative offset resolution)
        strike_step = self._get_strike_step(trade_date, expiry_date_str)
        print(f"  [STITCHER] Using market strike step {strike_step} for symbol {self.instrument_name.upper()} (configured: {self.inst_config.get('strike_step', 100)})")
        atm_min = int(round(spot_low / strike_step) * strike_step)
        atm_max = int(round(spot_high / strike_step) * strike_step)
        
        offset_min = int((strike - atm_max) / strike_step) - 1
        offset_max = int((strike - atm_min) / strike_step) + 1
        
        offsets = list(range(offset_min, offset_max + 1))
        
        # Limit offsets to prevent extreme errors, but map them to the Dhan API's allowed [-10, 10] range
        offsets = [o for o in offsets if -40 <= o <= 40]
        if not offsets:
            print("[STITCHER ERROR] Calculated offsets are out of bounds.")
            return pd.DataFrame()
            
        # Determine which offsets we actually need to fetch (clipped to API bounds [-10, 10])
        # This significantly reduces API calls and avoids "out of bounds" errors for deep ITM/OTM options.
        fetch_offsets = sorted(list(set(max(-10, min(10, o)) for o in offsets)))
        
        print(f"[STITCHER] Spot Range: {spot_low:.2f} - {spot_high:.2f}. ATM Range: {atm_min} - {atm_max}.")
        print(f"  Required offsets: {offsets}")
        print(f"  Offsets to fetch (clipped to Dhan limits): {fetch_offsets}")
        
        # Fetch rolling options data for each clipped offset
        fetched_dfs = {}
        opt_seg = self.inst_config.get('option_segment', 'NSE_FNO')
        inst_type = self.inst_config.get('type', 'INDEX')
        opt_inst = "OPTIDX" if inst_type == "INDEX" else "OPTSTK"
        sec_id = str(self.inst_config['security_id'])
        symbol = self.instrument_name.upper()
        expiry_flag = "WEEK" if symbol in ["NIFTY", "SENSEX"] else "MONTH"
        url = "https://api.dhan.co/v2/charts/rollingoption"
        
        # Determine correct expiry code for monthly contracts to handle broker rollover delay
        from datetime import date
        if isinstance(trade_date, str):
            t_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()
        elif hasattr(trade_date, 'date'):
            t_date_obj = trade_date.date()
        else:
            t_date_obj = trade_date

        is_monthly_only = (symbol not in ["NIFTY", "SENSEX"])
        
        if is_monthly_only:
            target_expiry_str = self._get_actual_expiry_date(trade_date, expiry_index)
            first_of_month = date(t_date_obj.year, t_date_obj.month, 1)
            monthly_expiries = []
            for idx in range(5):
                monthly_expiries.append(self._get_actual_expiry_date(first_of_month, idx))
                
            # Rollover occurs starting the day after the current month's monthly FNO expiry date
            curr_month_expiry_str = monthly_expiries[0]
            curr_month_expiry = datetime.strptime(curr_month_expiry_str, "%Y-%m-%d").date()
            rolled_over = (t_date_obj > curr_month_expiry)
            
            api_expiry_code = 1
            for idx, exp in enumerate(monthly_expiries):
                if exp == target_expiry_str:
                    if rolled_over:
                        api_expiry_code = idx
                    else:
                        api_expiry_code = idx + 1
                    break
            api_expiry_code = max(api_expiry_code, 1)
        else:
            # For weekly options
            if expiry_date_str is not None:
                nearest_est = self._get_expiry_date(t_date_obj, 0)
                next_est = self._get_expiry_date(t_date_obj, 1)
                if expiry_date_str == nearest_est:
                    api_expiry_code = 1
                elif expiry_date_str == next_est:
                    api_expiry_code = 2
                else:
                    api_expiry_code = expiry_index + 1
            else:
                est_expiry_str = self._get_expiry_date(t_date_obj, expiry_index)
                today_str = t_date_obj.strftime("%Y-%m-%d")
                if est_expiry_str == today_str:
                    api_expiry_code = expiry_index + 2
                else:
                    api_expiry_code = expiry_index + 1
            
        for f_offset in fetch_offsets:
            if f_offset == 0:
                rel_strike = "ATM"
            elif f_offset > 0:
                rel_strike = f"ATM+{f_offset}"
            else:
                rel_strike = f"ATM{f_offset}"
                
            payload = {
                "exchangeSegment": opt_seg,
                "interval": "1",
                "securityId": sec_id,
                "instrument": opt_inst,
                "expiryFlag": expiry_flag,
                "expiryCode": api_expiry_code,
                "strike": rel_strike,
                "drvOptionType": "CALL" if option_type.upper() == "CE" else "PUT",
                "requiredData": ["open", "high", "low", "close", "volume", "oi"],
                "fromDate": date_str,
                "toDate": date_str
            }
            
            for attempt in range(3):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=15)
                    if response.status_code == 200:
                        resp_json = response.json()
                        raw_data = resp_json.get("data", resp_json)
                        
                        if isinstance(raw_data, dict) and ('ce' in raw_data or 'pe' in raw_data):
                            if 'ce' in raw_data and raw_data['ce'] is not None and 'close' in raw_data['ce']:
                                raw_data = raw_data['ce']
                            elif 'pe' in raw_data and raw_data['pe'] is not None and 'close' in raw_data['pe']:
                                raw_data = raw_data['pe']
                                
                        df_rel = pd.DataFrame()
                        if isinstance(raw_data, dict):
                            raw_data = {k: v for k, v in raw_data.items() if isinstance(v, list) and len(v) > 0}
                            if 'close' in raw_data:
                                df_rel = pd.DataFrame(raw_data)
                        elif isinstance(raw_data, list) and len(raw_data) > 0:
                            df_rel = pd.DataFrame(raw_data)
                            
                        if not df_rel.empty:
                            df_rel.columns = df_rel.columns.str.lower()
                            if 'timestamp' in df_rel.columns:
                                try:
                                    df_rel['timestamp'] = pd.to_datetime(df_rel['timestamp'], unit='s')
                                except:
                                    df_rel['timestamp'] = pd.to_datetime(df_rel['timestamp'])
                                df_rel['timestamp'] = df_rel['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                                df_rel.set_index('timestamp', inplace=True)
                            
                            df_rel = df_rel[~df_rel.index.duplicated(keep='first')]
                            cols = [c for c in ['open', 'high', 'low', 'close', 'volume', 'oi'] if c in df_rel.columns]
                            fetched_dfs[f_offset] = df_rel[cols]
                            print(f"  [STITCHER] Successfully fetched {rel_strike} ({len(df_rel)} candles)")
                            break
                    elif response.status_code == 429:
                        time.sleep(10)
                    else:
                        print(f"  [STITCHER API ERROR] {rel_strike} attempt {attempt+1} HTTP {response.status_code}: {response.text}")
                except Exception as e:
                    print(f"  [STITCHER WARNING] {rel_strike} attempt {attempt+1} failed: {e}")
                time.sleep(2 ** attempt)
            time.sleep(0.1) # be gentle on rate limit
            
        if not fetched_dfs:
            print("[STITCHER ERROR] No relative strike data could be fetched.")
            return pd.DataFrame()
            
        # Reconstruct rolling_dfs for all required offsets by applying intrinsic value adjustment to fetched_dfs
        rolling_dfs = {}
        for offset in offsets:
            clipped_offset = max(-10, min(10, offset))
            if clipped_offset not in fetched_dfs:
                continue
                
            df_base = fetched_dfs[clipped_offset].copy()
            if offset == clipped_offset:
                # No adjustment needed if offset is within API limits
                rolling_dfs[offset] = df_base
                continue
                
            # Perform intrinsic value adjustment for out-of-bounds offset
            # Target strike corresponds to ATM + offset * strike_step
            # Fetched strike corresponds to ATM + clipped_offset * strike_step
            try:
                # Align spot close with the option index
                spot_aligned = spot_day['close'].reindex(df_base.index).ffill()
                atm_aligned = (spot_aligned / strike_step).round() * strike_step
                
                target_strike = atm_aligned + (offset * strike_step)
                fetched_strike = atm_aligned + (clipped_offset * strike_step)
                
                if option_type.upper() == "CE":
                    target_intrinsic = (spot_aligned - target_strike).clip(lower=0)
                    fetched_intrinsic = (spot_aligned - fetched_strike).clip(lower=0)
                else:
                    target_intrinsic = (target_strike - spot_aligned).clip(lower=0)
                    fetched_intrinsic = (fetched_strike - spot_aligned).clip(lower=0)
                    
                intrinsic_diff = target_intrinsic - fetched_intrinsic
                
                # Apply the difference to open, high, low, close and clip at 0.05 (min option tick)
                for col in ['open', 'high', 'low', 'close']:
                    if col in df_base.columns:
                        df_base[col] = (df_base[col] + intrinsic_diff).clip(lower=0.05)
                        
                rolling_dfs[offset] = df_base
                print(f"  [STITCHER] Derived offset {offset} from fetched {clipped_offset} via intrinsic adjustment.")
            except Exception as adj_err:
                print(f"  [STITCHER WARNING] Adjustment failed for offset {offset}: {adj_err}")
                rolling_dfs[offset] = df_base
            
        # Stitch them using exact mathematical relative strike mapping aligned to spot day minutes
        all_timestamps = spot_day.index
        stitched_records = []
        avail_offsets = list(rolling_dfs.keys())
        missing_count = 0
        
        for t in all_timestamps:
            spot_close_t = spot_day.loc[t, 'close']
            if isinstance(spot_close_t, pd.Series):
                spot_close_t = spot_close_t.iloc[0]
                
            atm_calc_t = round(spot_close_t / strike_step) * strike_step
            correct_offset = int(round((strike - atm_calc_t) / strike_step))
            
            prev_row = None
            if not avail_offsets:
                prev_row = pd.Series({'open': 0.0, 'high': 0.0, 'low': 0.0, 'close': 0.0, 'volume': 0, 'oi': 0})
            else:
                # Find the best offset matching the correct offset
                best_offset = correct_offset
                if best_offset not in avail_offsets:
                    best_offset = min(avail_offsets, key=lambda x: abs(x - best_offset))
                    
                if t in rolling_dfs[best_offset].index:
                    prev_row = rolling_dfs[best_offset].loc[t]
                else:
                    # Try other offsets for this timestamp before giving up
                    found = False
                    for off in sorted(avail_offsets, key=lambda x: abs(x - correct_offset)):
                        if t in rolling_dfs[off].index:
                            prev_row = rolling_dfs[off].loc[t]
                            found = True
                            break
                    if not found:
                        missing_count += 1
                        prev_close = stitched_records[-1]['close'] if stitched_records else 0.0
                        prev_oi = stitched_records[-1]['oi'] if stitched_records else 0
                        prev_row = pd.Series({
                            'open': prev_close,
                            'high': prev_close,
                            'low': prev_close,
                            'close': prev_close,
                            'volume': 0,
                            'oi': prev_oi
                        })
            
            stitched_records.append({
                'timestamp': t,
                'open': prev_row['open'],
                'high': prev_row['high'],
                'low': prev_row['low'],
                'close': prev_row['close'],
                'volume': prev_row.get('volume', 0),
                'oi': prev_row.get('oi', 0)
            })
            
        stitched_df = pd.DataFrame(stitched_records)
        stitched_df.set_index('timestamp', inplace=True)
        print(f"[STITCHER SUCCESS] Stitched {len(stitched_df)} candles for {strike} {option_type}. Forward-filled: {missing_count} mins.")
        return stitched_df

    def _get_option_candles_uncached(self, strike: int, option_type: str, trade_date, relative_strike: str = "ATM", expiry_date_str: str = None) -> pd.DataFrame:
        """Fetch 1-minute historical candles for a specific option strike, using local CSV cache."""
        prefix = self.instrument_name.lower()
        date_str = trade_date.strftime("%Y-%m-%d")
        
        # Resolve expiry date
        expiry_index = self.inst_config.get("expiry_index", 0)
        expiry_str = expiry_date_str or self._get_actual_expiry_date(trade_date, expiry_index)
        
        # In offline mode, completely bypass disk checks and writes, slicing directly from in-memory fallback dict
        if self.offline_mode:
            fallback_dict = getattr(self, 'fallback_ce_dict', None) if option_type.upper() == "CE" else getattr(self, 'fallback_pe_dict', None)
            if fallback_dict is not None and date_str in fallback_dict:
                df_fallback = fallback_dict[date_str].copy()
                if not df_fallback.empty and self.df_spot is not None:
                    try:
                        spot_day = self.df_spot.loc[date_str]
                        if not spot_day.empty:
                            # Align fallback with spot timestamps
                            merged = pd.merge(spot_day[['close']], df_fallback, left_index=True, right_index=True, suffixes=('_spot', '_opt'))
                            if not merged.empty:
                                strike_step = self._get_strike_step(trade_date, expiry_str)
                                if option_type.upper() == "CE":
                                    intrinsic_atm = (merged['close_spot'] - (merged['close_spot'] / strike_step).round() * strike_step).clip(lower=0)
                                    intrinsic_target = (merged['close_spot'] - strike).clip(lower=0)
                                else:
                                    intrinsic_atm = (((merged['close_spot'] / strike_step).round() * strike_step) - merged['close_spot']).clip(lower=0)
                                    intrinsic_target = (strike - merged['close_spot']).clip(lower=0)
                                    
                                diff = intrinsic_target - intrinsic_atm
                                for col in ['open', 'high', 'low', 'close']:
                                    if col in merged.columns:
                                        merged[col] = merged[col] + diff
                                        
                                # Drop the spot close column and return the modified df
                                return merged.drop(columns=['close_spot'])
                    except Exception as e:
                        print(f"[WARNING] Offline strike adjustment failed for {date_str}: {e}")
                return df_fallback
            return pd.DataFrame()
            
        expiry_index = self.inst_config.get("expiry_index", 0)
        expiry_str = expiry_date_str or self._get_actual_expiry_date(trade_date, expiry_index)
        cache_filename = f"{prefix}_{strike}_{option_type.upper()}_exp{expiry_index}_expiry{expiry_str}_{date_str}.csv"
        cache_path = os.path.join(self.cache_dir, cache_filename)
        
        # 1. Check Local Disk Cache
        if os.path.exists(cache_path):
            try:
                if os.path.getsize(cache_path) < 100:
                    return pd.DataFrame()
                df = pd.read_csv(cache_path, index_col='timestamp', parse_dates=True)
                
                # Check if this cached file is complete relative to our spot data
                if self.df_spot is not None and not df.empty:
                    try:
                        spot_day = self.df_spot.loc[date_str]
                        if not spot_day.empty:
                            spot_max = spot_day.index.max()
                            df_max = df.index.max()
                            if pd.notna(spot_max) and pd.notna(df_max):
                                spot_max_naive = spot_max.tz_localize(None) if spot_max.tzinfo is not None else spot_max
                                df_max_naive = df_max.tz_localize(None) if df_max.tzinfo is not None else df_max
                                if df_max_naive < spot_max_naive:
                                    print(f"[INFO] Cached option data for {date_str} is incomplete (cache ends at {df_max}, spot ends at {spot_max}). Re-fetching...")
                                    df = pd.DataFrame()
                    except KeyError:
                        pass
                
                if not df.empty:
                    return df
            except Exception as e:
                print(f"[WARNING] Failed to read cached file {cache_path}: {e}")

        # 3. Cache Miss -> Try dynamic query DhanHQ charts API
        df = pd.DataFrame()
        
        # Check if trade_date is a weekend or NSE trading holiday
        t_date_obj = trade_date
        if isinstance(trade_date, str):
            t_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()
        elif hasattr(trade_date, 'date'):
            t_date_obj = trade_date.date()
            
        if t_date_obj.weekday() >= 5 or date_str in NSE_HOLIDAYS:
            # Silently return empty DataFrame to completely bypass live API calls & stitching for non-trading days
            return pd.DataFrame()
            
        only_use_cache = os.getenv("ONLY_USE_CACHE", "False").lower() in ("true", "1", "yes")
        if self.client_id and self.api_token and not only_use_cache:
            expiry_str = expiry_date_str or self._get_actual_expiry_date(trade_date, expiry_index)
            print(f"[CACHE MISS] Fetching dynamic option {self.instrument_name} {strike} ({relative_strike}) {option_type} (Expiry: {expiry_str}) for {date_str} from Dhan API...")
            
            headers = {
                "access-token": self.api_token,
                "client-id": self.client_id,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Check if the contract has already expired relative to today
            today_str = datetime.now().strftime("%Y-%m-%d")
            is_expired = expiry_str < today_str
            
            if is_expired:
                print(f"[INFO] Contract expiring {expiry_str} has already expired. Skipping standard intraday API and using stitching.")
                df = self._get_option_candles_via_stitching(strike, option_type, trade_date, date_str, expiry_index, headers, expiry_date_str=expiry_str)
            else:
                opt_sec_id = self._lookup_option_security_id(strike, option_type, expiry_str)
                opt_seg = self.inst_config.get('option_segment', 'NSE_FNO')
                inst_type = self.inst_config.get('type', 'INDEX')
                opt_inst = "OPTIDX" if inst_type == "INDEX" else "OPTSTK"
                
                # Try specific contract lookup and standard intraday chart API first (for active contracts)
                if opt_sec_id:
                    print(f"[INFO] Resolved security ID {opt_sec_id} for contract {self.instrument_name} {strike} {option_type} expiring {expiry_str}")
                    intraday_url = "https://api.dhan.co/v2/charts/intraday"
                    intraday_payload = {
                        "securityId": str(opt_sec_id),
                        "exchangeSegment": opt_seg,
                        "instrument": opt_inst,
                        "interval": "1",
                        "fromDate": f"{date_str} 09:15:00",
                        "toDate": f"{date_str} 15:30:00"
                    }
                    
                    for attempt in range(3):
                        try:
                            print(f"  Attempting to fetch standard intraday chart for contract ID {opt_sec_id} (Attempt {attempt+1})...")
                            response = requests.post(intraday_url, headers=headers, json=intraday_payload, timeout=15)
                            if response.status_code == 200:
                                resp_json = response.json()
                                raw_data = resp_json.get("data", resp_json)
                                
                                temp_df = pd.DataFrame()
                                if raw_data and isinstance(raw_data, list):
                                    temp_df = pd.DataFrame(raw_data)
                                elif raw_data and isinstance(raw_data, dict) and "close" in raw_data:
                                    temp_df = pd.DataFrame(raw_data)
                                    
                                if not temp_df.empty:
                                    temp_df.columns = temp_df.columns.str.lower()
                                    if 'timestamp' in temp_df.columns:
                                        try:
                                            temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'], unit='s')
                                        except:
                                            temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
                                        temp_df['timestamp'] = temp_df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                                        temp_df.set_index('timestamp', inplace=True)
                                        
                                    cols = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c in temp_df.columns]
                                    df = temp_df[cols]
                                    print(f"[SUCCESS] Fetched {len(df)} candles via standard intraday charts API for contract ID {opt_sec_id}")
                                    break
                                else:
                                    print(f"  [INFO] Standard intraday API returned empty/no data for contract ID {opt_sec_id}")
                            elif response.status_code == 429:
                                time.sleep(10)
                            else:
                                print(f"  [INFO] Standard intraday API returned HTTP {response.status_code}: {response.text}")
                        except Exception as e:
                            print(f"  [WARNING] Standard intraday API attempt {attempt+1} failed: {e}")
                        time.sleep(2 ** attempt)
                else:
                    print(f"[WARNING] Could not resolve security ID in master cache for contract {self.instrument_name} {strike} {option_type} expiring {expiry_str}")
                    
                # If standard intraday chart API failed or wasn't tried, use our price-continuity stitching algorithm
                if df.empty:
                    df = self._get_option_candles_via_stitching(strike, option_type, trade_date, date_str, expiry_index, headers, expiry_date_str=expiry_str)

        # 3. Graceful Fallback if API failed or no credentials
        if df.empty:
            fallback_df = self.fallback_ce if option_type.upper() == "CE" else self.fallback_pe
            if fallback_df is not None:
                print(f"[WARNING] Dhan API fetch unavailable for {date_str}. Slicing pre-loaded ATM files...")
                try:
                    # Slice fallback dataset for trade_date
                    sliced = fallback_df.loc[date_str]
                    if not sliced.empty:
                        df = sliced.copy()
                        if isinstance(df, pd.Series):
                            df = df.to_frame().T
                        print(f"[FALLBACK SUCCESS] Sliced {len(df)} candles from offline ATM dataset for {date_str}.")
                except KeyError:
                    print(f"[FALLBACK ERROR] Date {date_str} not found in pre-loaded ATM dataset.")
                    
        if not df.empty:
            try:
                df.to_csv(cache_path)
            except Exception as e:
                print(f"[WARNING] Failed to write CSV cache: {e}")
            return df
        else:
            print(f"[CRITICAL WARNING] No option data available for {self.instrument_name} {strike} {option_type} on {date_str}")
            try:
                pd.DataFrame().to_csv(cache_path)
            except Exception as e:
                print(f"[WARNING] Failed to write empty cache marker: {e}")
            return pd.DataFrame()
  
    def run(self, write_to_csv=True):
        print(f"[INFO] Running dynamic strike simulation engine for {self.instrument_name}...")
        if not any(col in self.df_spot.columns for col in ['TM_ADX', 'ADX', 'ADX_14']):
            print("[INFO] 'ADX' column not found in spot data. Calculating fallback 5-minute ADX...")
            try:
                import pandas_ta as ta
                # 1. Resample to 5-min
                df_5min = self.df_spot.resample('5min').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last'
                }).dropna()
                # 2. Compute ADX
                adx_df = ta.adx(df_5min['high'], df_5min['low'], df_5min['close'], length=14)
                if adx_df is not None:
                    # 3. Shift to avoid lookahead and join
                    df_5min['ADX_14'] = adx_df['ADX_14'].shift(1)
                    self.df_spot = self.df_spot.join(df_5min[['ADX_14']], how='left')
                    self.df_spot['ADX_14'] = self.df_spot['ADX_14'].ffill().fillna(20.0)
            except Exception as e:
                print(f"[WARNING] Failed to calculate fallback ADX: {e}")

        if 'ATR' not in self.df_spot.columns:
            print("[INFO] 'ATR' column not found in spot data. Calculating fallback 5-minute ATR...")
            try:
                import pandas_ta as ta
                # 1. Resample to 5-min
                df_5min = self.df_spot.resample('5min').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last'
                }).dropna()
                
                # 2. Compute ATR on 5-min
                df_5min['ATR'] = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=14)
                
                # 3. Shift to prevent lookahead
                df_5min['ATR'] = df_5min['ATR'].shift(1)
                
                # 4. Join back to df_spot and ffill
                self.df_spot = self.df_spot.join(df_5min[['ATR']], how='left')
                self.df_spot['ATR'] = self.df_spot['ATR'].ffill()
                
                # If there are still NaNs at the beginning, backfill or fill with 0
                self.df_spot['ATR'] = self.df_spot['ATR'].bfill().fillna(0.0)
            except Exception as e:
                print(f"[WARNING] Failed to calculate 5-minute ATR: {e}. Calculating 1-minute fallback ATR...")
                try:
                    import pandas_ta as ta
                    self.df_spot['ATR'] = ta.atr(self.df_spot['high'], self.df_spot['low'], self.df_spot['close'], length=14)
                    self.df_spot['ATR'] = self.df_spot['ATR'].fillna(0.0)
                except Exception as e2:
                    print(f"[ERROR] Failed to calculate 1-minute ATR: {e2}. Using static ATR of 10.0.")
                    self.df_spot['ATR'] = 10.0

        # Re-compute median ATR% now that ATR column has been populated
        self._compute_median_atr_pct()

        spot_high = self.df_spot['high'].values
        spot_low = self.df_spot['low'].values
        spot_close = self.df_spot['close'].values
        
        spot_atr = self.df_spot['ATR'].values
        spot_signals = self.df_spot['Signal'].values
        spot_source = self.df_spot['Signal_Source'].values
        timestamps = self.df_spot.index
        times = [t.time() for t in timestamps]
        
        n = len(self.df_spot)
        time_1500 = dt_time(15, 00)
        
        current_date = None
        daily_trade_count = 0
        daily_limit = self.inst_config.get('daily_limit', 5)
        
        strike_step = self.inst_config.get('strike_step', 100)
        strike_offset = self.inst_config.get('strike_offset', 0)
        strike_offset_buy = self.inst_config.get('strike_offset_buy', strike_offset)
        strike_offset_sell = self.inst_config.get('strike_offset_sell', strike_offset)
        
        # Track the active option contract dataframe
        active_opt_df = None
        
        for i in range(n):
            timestamp = timestamps[i]
            # Skip weekends and NSE trading holidays
            if timestamp.weekday() >= 5 or timestamp.strftime('%Y-%m-%d') in NSE_HOLIDAYS:
                continue
                
            current_time = times[i]
            trade_date = timestamp.date()
            
            # Reset daily trade count on date change
            if trade_date != current_date:
                current_date = trade_date
                daily_trade_count = 0
                
            # 1. Manage Active Trades (Check SL / TP / Trailing)
            if self.active_trades:
                still_active = []
                for trade in self.active_trades:
                    if trade.get("Type") == "STOCK":
                        opt_open = self.df_spot['open'].values[i]
                        opt_high = spot_high[i]
                        opt_low = spot_low[i]
                        opt_close = spot_close[i]
                    else:
                        opt_low = np.nan
                        opt_high = np.nan
                        opt_open = np.nan
                        opt_close = np.nan
                        
                        # Dynamically retrieve contract candles for the current trade date (vital for carry forward)
                        opt_candles = self._get_option_candle_dict(trade["Strike"], trade["Type"], trade_date, expiry_date_str=trade.get("Expiry"))
                        candle = opt_candles.get(timestamp)
                        
                        if candle is not None:
                            o = candle.get('open', np.nan)
                            l = candle.get('low', np.nan)
                            h = candle.get('high', np.nan)
                            c = candle.get('close', np.nan)
                            if (not np.isnan(o) and o > 0 and
                                not np.isnan(l) and l > 0 and
                                not np.isnan(h) and h > 0 and
                                not np.isnan(c) and c > 0):
                                opt_open = o
                                opt_low = l
                                opt_high = h
                                opt_close = c
                            
                        if np.isnan(opt_low) or np.isnan(opt_high) or np.isnan(opt_open):
                            # Fallback to spot delta proxy if dynamic contract data point is missing
                            entry_spot = trade["Entry_Spot"]
                            entry_price = trade["Entry_Price"]
                            
                            delta = self.config.OPTION_DELTA
                            
                            spot_open_val = self.df_spot['open'].values[i]
                            spot_high_val = spot_high[i]
                            spot_low_val = spot_low[i]
                            spot_close_val = spot_close[i]
                            
                            if trade["Type"] == "CE":
                                opt_open = max(entry_price + (spot_open_val - entry_spot) * delta, 0.05)
                                opt_high = max(entry_price + (spot_high_val - entry_spot) * delta, 0.05)
                                opt_low = max(entry_price + (spot_low_val - entry_spot) * delta, 0.05)
                                opt_close = max(entry_price + (spot_close_val - entry_spot) * delta, 0.05)
                            else:
                                opt_open = max(entry_price - (spot_open_val - entry_spot) * delta, 0.05)
                                opt_high = max(entry_price - (spot_low_val - entry_spot) * delta, 0.05)
                                opt_low = max(entry_price - (spot_high_val - entry_spot) * delta, 0.05)
                                opt_close = max(entry_price - (spot_close_val - entry_spot) * delta, 0.05)
                    
                    is_opening_candle = (i == 0 or timestamps[i].date() != timestamps[i-1].date())
                    closed = self._manage_trade_fast(timestamp, trade, opt_open, opt_high, opt_low, opt_close, is_opening_candle=is_opening_candle)
                    if not closed:
                        still_active.append(trade)
                self.active_trades = still_active
                
            # 2. 15:15 Force Close / Expiry Day Close Logic
            carry_forward = getattr(self.config, "CARRY_FORWARD", False)
            if self.active_trades and current_time >= time_1500:
                still_active = []
                for trade in self.active_trades:
                    is_expiry_day = (trade.get("Expiry") == trade_date.strftime("%Y-%m-%d"))
                    if not carry_forward or (trade.get("Type") != "STOCK" and is_expiry_day):
                        # Force square-off at 15:15 for intraday mode, or options on their expiry day
                        if trade.get("Type") == "STOCK":
                            opt_open_val = self.df_spot['open'].values[i]
                        else:
                            opt_open_val = np.nan
                            opt_candles = self._get_option_candle_dict(trade["Strike"], trade["Type"], trade_date, expiry_date_str=trade.get("Expiry"))
                            candle = opt_candles.get(timestamp)
                            if candle is not None:
                                val = candle.get('open', np.nan)
                                if not np.isnan(val) and val > 0:
                                    opt_open_val = val
                        self._close_trade_fast_direct(timestamp, trade, "Time_SquareOff", opt_open_val, spot_close_val=spot_close[i])
                    else:
                        still_active.append(trade)
                self.active_trades = still_active
                
            # If we still have active trades, capacity limits are now checked dynamically at the time of entry.
                
            # Stop taking new entries after 15:15
            if current_time >= time_1500:
                continue
                
            # 3. Look for new entries (Respect daily limits and Cooldown Lockout)
            if self.cooldown_until and timestamp < self.cooldown_until:
                continue
                
            signal = spot_signals[i]
            if signal != 0:
                # Expiry Day Only Filter
                if self.inst_config.get("trade_expiry_day_only", 0) == 1:
                    nearest_expiry = self._get_expiry_date(trade_date, 0)
                    current_date_str = trade_date.strftime('%Y-%m-%d') if hasattr(trade_date, 'strftime') else str(trade_date)
                    if current_date_str != nearest_expiry:
                        continue

                # Expiry Day Block Filter
                if self.inst_config.get("block_expiry_day_trades", 0) == 1:
                    leg_mode = getattr(self.config, "LEG_MODE", "BUY").upper()
                    strat_mode = self.inst_config.get('option_strategy_mode', 'DIRECT')
                    is_buying_trade = False
                    if strat_mode == "DIRECT":
                        if leg_mode in ["BUY", "BOTH"]:
                            is_buying_trade = True
                    elif strat_mode in ["LONG_STRADDLE", "LONG_STRANGLE", "DEBIT_SPREAD"]:
                        is_buying_trade = True
                        
                    if is_buying_trade:
                        nearest_expiry = self._get_expiry_date(trade_date, 0)
                        current_date_str = trade_date.strftime('%Y-%m-%d') if hasattr(trade_date, 'strftime') else str(trade_date)
                        if current_date_str == nearest_expiry:
                            continue
                            
                # The signal candle is confirmed at index i. Actual execution happens at the open of index i+1.
                entry_idx = i + 1
                if entry_idx >= n:
                    continue
                
                entry_timestamp = timestamps[entry_idx]
                entry_time = times[entry_idx]
                
                # Sanity check: close-based signal vs open-based entry
                if 'TM_Sig_High' in self.df_spot.columns and 'TM_Sig_Low' in self.df_spot.columns:
                    spot_open_val = self.df_spot['open'].values[entry_idx]
                    if signal == 1:
                        sig_level = self.df_spot['TM_Sig_High'].values[i]
                        if pd.notna(sig_level) and spot_open_val > sig_level * 1.002:
                            continue
                    elif signal == -1:
                        sig_level = self.df_spot['TM_Sig_Low'].values[i]
                        if pd.notna(sig_level) and spot_open_val < sig_level * 0.998:
                            continue
                
                # Cooldown Lockout check at the time of entry execution
                if self.cooldown_until and entry_timestamp < self.cooldown_until:
                    continue
                
                if entry_time >= self.config.RUN_START:
                    if daily_trade_count < daily_limit:
                        # Check execution mode
                        execution_mode = self.inst_config.get("execution_mode", "OPTION")
                        if execution_mode == "STOCK":
                            stock_action = None
                            if signal == 1 and self.config.LEG_MODE in ["BUY", "BOTH"]:
                                stock_action = "BUY"
                            elif signal == -1 and self.config.LEG_MODE in ["SELL", "BOTH"]:
                                stock_action = "SELL"
                                
                            if stock_action:
                                # Check max active trades limit
                                max_active = self.inst_config.get("max_active", 1) or 1
                                active_stock_count = sum(1 for t in self.active_trades if t.get("Type") == "STOCK")
                                if active_stock_count >= max_active:
                                    continue
                                # Determine Qty
                                stock_qty_override = self.inst_config.get("stock_qty_override")
                                if stock_qty_override is not None:
                                    qty = int(stock_qty_override)
                                else:
                                    lots = self.inst_config.get(f"num_lots_{stock_action.lower()}", 1)
                                    lot_size = self.inst_config.get("lot_size", 1) or 1
                                    qty = lot_size * lots
                                    
                                spot_open_val = self.df_spot['open'].values[entry_idx]
                                if spot_open_val > 0:
                                    trade_dict = self._enter_trade_fast_direct(
                                        entry_timestamp,
                                        signal,
                                        spot_atr[entry_idx],
                                        spot_source[i],
                                        spot_open_val,
                                        spot_close[i],
                                        "STOCK",
                                        stock_action == "SELL",
                                        None,
                                        0,
                                        None,
                                        qty
                                    )
                                    if trade_dict:
                                        self.active_trades.append(trade_dict)
                                        daily_trade_count += 1
                                        self.cooldown_until = entry_timestamp + timedelta(seconds=280)
                            continue
                        
                        # DYNAMIC STRIKE ROUTING
                        spot_val = spot_close[i]
                        strike_step = self._get_strike_step(trade_date)
                        atm_strike = round(spot_val / strike_step) * strike_step
                        if isinstance(atm_strike, float) and atm_strike.is_integer():
                            atm_strike = int(atm_strike)
                        
                        strat_mode = self.inst_config.get("option_strategy_mode", "DIRECT")
                        width = self.inst_config.get("strategy_leg_width", 1)
                        
                        # Determine legs to enter based on strategy_mode, signal & leg_mode
                        base_legs = [] # List of (type, is_short, offset)
                        
                        if strat_mode == "DIRECT":
                            leg_mode = getattr(self.config, "LEG_MODE", "BUY").upper()
                            if leg_mode == "BUY":
                                if signal == 1:
                                    base_legs.append(("CE", False, strike_offset_buy))
                                elif signal == -1:
                                    base_legs.append(("PE", False, strike_offset_buy))
                            elif leg_mode == "SELL":
                                if signal == 1:
                                    base_legs.append(("PE", True, strike_offset_sell))
                                elif signal == -1:
                                    base_legs.append(("CE", True, strike_offset_sell))
                            elif leg_mode == "BOTH":
                                if signal == 1:
                                    base_legs.append(("CE", False, strike_offset_buy)) # Buy CE
                                    base_legs.append(("PE", True, strike_offset_sell))  # Sell PE
                                elif signal == -1:
                                    base_legs.append(("PE", False, strike_offset_buy)) # Buy PE
                                    base_legs.append(("CE", True, strike_offset_sell))  # Sell CE
                        elif strat_mode == "DEBIT_SPREAD":
                            if signal == 1:
                                base_legs.append(("CE", False, strike_offset_buy)) # Buy CE ATM
                                base_legs.append(("CE", True, strike_offset_buy + width)) # Sell CE OTM
                            elif signal == -1:
                                base_legs.append(("PE", False, strike_offset_buy)) # Buy PE ATM
                                base_legs.append(("PE", True, strike_offset_buy + width)) # Sell PE OTM
                        elif strat_mode == "CREDIT_SPREAD":
                            if signal == 1:
                                base_legs.append(("PE", False, strike_offset_sell + width)) # Buy PE OTM (hedge)
                                base_legs.append(("PE", True, strike_offset_sell)) # Sell PE ATM
                            elif signal == -1:
                                base_legs.append(("CE", False, strike_offset_sell + width)) # Buy CE OTM (hedge)
                                base_legs.append(("CE", True, strike_offset_sell)) # Sell CE ATM
                        elif strat_mode == "SHORT_STRADDLE":
                            base_legs.append(("CE", True, strike_offset_sell))
                            base_legs.append(("PE", True, strike_offset_sell))
                        elif strat_mode == "LONG_STRADDLE":
                            base_legs.append(("CE", False, strike_offset_buy))
                            base_legs.append(("PE", False, strike_offset_buy))
                        elif strat_mode == "SHORT_STRANGLE":
                            base_legs.append(("CE", True, strike_offset_sell + width))
                            base_legs.append(("PE", True, strike_offset_sell + width))
                        elif strat_mode == "LONG_STRANGLE":
                            base_legs.append(("CE", False, strike_offset_buy + width))
                            base_legs.append(("PE", False, strike_offset_buy + width))
                        elif strat_mode == "IRON_CONDOR":
                            base_legs.append(("PE", False, strike_offset_sell + width))  # Hedge Put (further OTM)
                            base_legs.append(("PE", True, strike_offset_sell + width))    # Short Put (OTM)
                            base_legs.append(("CE", True, strike_offset_sell + width))    # Short Call (OTM)
                            base_legs.append(("CE", False, strike_offset_sell + width))  # Hedge Call (further OTM)
                        elif strat_mode == "IRON_FLY":
                            base_legs.append(("PE", False, strike_offset_sell + width))      # Hedge Put (OTM)
                            base_legs.append(("PE", True, strike_offset_sell))            # Short Put (ATM)
                            base_legs.append(("CE", True, strike_offset_sell))            # Short Call (ATM)
                            base_legs.append(("CE", False, strike_offset_sell + width))       # Hedge Call (OTM)
                                
                        # Expand base legs by num_strikes if in DIRECT mode
                        legs_to_enter = []
                        num_strikes = self.inst_config.get('num_strikes', 1)
                        direction = 1 if signal == 1 else -1
                        
                        for option_type_str, is_short, active_offset in base_legs:
                            if strat_mode == "DIRECT":
                                for strike_idx in range(num_strikes):
                                    if option_type_str == "CE":
                                        offset = active_offset + (strike_idx * direction)
                                    else:
                                        offset = active_offset - (strike_idx * direction)
                                    legs_to_enter.append((option_type_str, is_short, offset))
                            else:
                                legs_to_enter.append((option_type_str, is_short, active_offset))
                                
                        # Check capacity limits for options
                        max_active = self.inst_config.get("max_active", 1) or 1
                        active_ce_count = sum(1 for t in self.active_trades if t.get("Type") == "CE")
                        active_pe_count = sum(1 for t in self.active_trades if t.get("Type") == "PE")
                        
                        num_ce_legs = sum(1 for type_str, _, _ in legs_to_enter if type_str == "CE")
                        num_pe_legs = sum(1 for type_str, _, _ in legs_to_enter if type_str == "PE")
                        
                        is_eligible = True
                        if num_ce_legs > 0:
                            active_ce_trades = (active_ce_count + num_ce_legs - 1) // num_ce_legs
                            if active_ce_trades >= max_active:
                                is_eligible = False
                        if is_eligible and num_pe_legs > 0:
                            active_pe_trades = (active_pe_count + num_pe_legs - 1) // num_pe_legs
                            if active_pe_trades >= max_active:
                                is_eligible = False
                        if not is_eligible:
                            continue
                                
                        entered_any = False
                        for option_type_str, is_short, active_offset in legs_to_enter:
                            # Apply active strike offset
                            if option_type_str == "CE":
                                target_strike = atm_strike + (active_offset * strike_step)
                            else:
                                target_strike = atm_strike - (active_offset * strike_step)
                                
                            if isinstance(target_strike, float) and target_strike.is_integer():
                                target_strike = int(target_strike)
                                
                            if active_offset == 0:
                                relative_strike = "ATM"
                            else:
                                prefix_sign = "+" if option_type_str == "CE" else "-"
                                relative_strike = f"ATM{prefix_sign}{active_offset}"
                            
                            # Gate Keeper Validation Check
                            if self.inst_config.get("gatekeeper_enabled", 0) == 1:
                                if not self._validate_gatekeeper(target_strike, option_type_str, trade_date, entry_timestamp, is_short=is_short):
                                    continue

                            # Dynamic fetch contract candles for entry_timestamp
                            opt_candles = self._get_option_candle_dict(target_strike, option_type_str, trade_date)
                            candle = opt_candles.get(entry_timestamp)
                            
                            if candle is not None:
                                opt_entry_price = candle.get('open', np.nan)
                                
                                if not np.isnan(opt_entry_price) and opt_entry_price > 0:
                                    opt_df = self._get_option_candles(target_strike, option_type_str, trade_date, relative_strike=relative_strike)
                                    expiry_index = self.inst_config.get("expiry_index", 0)
                                    expiry_str = self._get_actual_expiry_date(trade_date, expiry_index)
                                    trade_dict = self._enter_trade_fast_direct(
                                        entry_timestamp,
                                        signal,
                                        spot_atr[entry_idx],
                                        spot_source[i],
                                        opt_entry_price,
                                        spot_close[i],
                                        option_type_str,
                                        is_short,
                                        opt_df,
                                        target_strike,
                                        expiry_str
                                    )
                                    if trade_dict:
                                        self.active_trades.append(trade_dict)
                                        entered_any = True
                                        
                        if entered_any:
                            daily_trade_count += 1
                            self.cooldown_until = entry_timestamp + timedelta(seconds=280)
                            
            # Early Rejection Engine Check (Priority 8)
            if self.enable_early_rejection and len(self.trades) >= 30:
                if len(self.trades) % 5 == 0:
                    pnls = [t["PnL"] for t in self.trades]
                    gross_profit = sum(p for p in pnls if p > 0)
                    gross_loss = abs(sum(p for p in pnls if p < 0))
                    pf = gross_profit / gross_loss if gross_loss > 0 else np.inf
                    win_rate = (sum(1 for p in pnls if p > 0) / len(pnls)) * 100
                    net_pnl = sum(pnls)
                    
                    avg_sl = np.mean([
                        t.get("Initial_SL_Points", 0.0) or t.get("Spot_ATR", 1.0)
                        for t in self.trades
                    ])
                    lot_size = self._get_lot_size(trade_date)
                    net_r = net_pnl / (avg_sl * lot_size) if avg_sl > 0 else -10.0
                    
                    if (pf < 0.7 and win_rate < 30.0) or net_r < -5.0:
                        break
                                    
        # Close any lingering trades at the end of the simulation
        if self.active_trades:
            for trade in self.active_trades:
                last_time = timestamps[-1]
                last_opt_val = np.nan
                if trade.get("Type") == "STOCK":
                    last_opt_val = self.df_spot['open'].values[-1]
                else:
                    last_date = last_time.date()
                    opt_candles = self._get_option_candle_dict(trade["Strike"], trade["Type"], last_date, expiry_date_str=trade.get("Expiry"))
                    candle = opt_candles.get(last_time)
                    if candle is not None:
                        val = candle.get('open', np.nan)
                        if not np.isnan(val) and val > 0:
                            last_opt_val = val
                self._close_trade_fast_direct(last_time, trade, "End_Of_Simulation", last_opt_val, spot_close_val=spot_close[-1])
            self.active_trades = []
            
        df_results = pd.DataFrame(self.trades)
        
        # Print Gatekeeper Data Audit Report if gatekeeper was enabled
        if self.inst_config.get("gatekeeper_enabled", 0) == 1 and self.gk_total_checks > 0:
            print("\n" + "=" * 50)
            print("            GATEKEEPER DATA AUDIT REPORT            ")
            print("=" * 50)
            print(f"Total Strike checks:          {self.gk_total_checks}")
            print(f"[Open Interest (OI) Filter]")
            print(f"  -> Calculated & Passed:     {self.gk_oi_calculated_pass}")
            print(f"  -> Calculated & Failed:     {self.gk_oi_failed}")
            print(f"  -> Missing-Data Bypassed:   {self.gk_oi_missing_bypass}")
            print(f"[Volume SMA Filter]")
            print(f"  -> Calculated & Passed:     {self.gk_vol_calculated_pass}")
            print(f"  -> Calculated & Failed:     {self.gk_vol_failed}")
            print(f"  -> Missing-Data Bypassed:   {self.gk_vol_missing_bypass}")
            print("=" * 50 + "\n")
            
        if write_to_csv and not df_results.empty:
            filepath = os.path.join(BASE_DIR, "backtest_results.csv")
            try:
                df_results.to_csv(filepath, index=False)
            except PermissionError:
                temp_filepath = os.path.join(BASE_DIR, "backtest_results_temp.csv")
                print(f"[WARNING] Permission denied to write to '{filepath}'. Saving to '{temp_filepath}' instead.")
                df_results.to_csv(temp_filepath, index=False)
        return df_results
  
    def _enter_trade_fast_direct(self, timestamp, signal, spot_atr_val, signal_source, opt_entry_val, spot_close_val, option_type_str, is_short, opt_df, target_strike, expiry_str, qty=None) -> dict:
        is_stock = (option_type_str == "STOCK")
        # Resolve dynamic lot size
        if is_stock:
            lot_size = int(self.inst_config.get('lot_size', 1) or 1)
        else:
            lot_size = self._get_lot_size(timestamp.date(), expiry_str)
        if not is_short:
            actual_entry = self.apply_slippage(opt_entry_val, 'BUY', is_stock=is_stock)
        else:
            actual_entry = self.apply_slippage(opt_entry_val, 'SELL', is_stock=is_stock)
        
        # Load multipliers dynamically based on trade direction (long vs short)
        if not is_short:
            sl_mult = self.inst_config['sl_mult_buy']
            trail_mult = self.inst_config['trailing_mult_buy']
            tp_mult = self.inst_config.get('tp_mult_buy', self.config.ATR_TP_MULTIPLIER)
        else:
            sl_mult = self.inst_config['sl_mult_sell']
            trail_mult = self.inst_config['trailing_mult_sell']
            tp_mult = self.inst_config.get('tp_mult_sell', self.config.ATR_TP_MULTIPLIER)
            
        # Get instrument-specific options delta (defaulting to config.OPTION_DELTA)
        if option_type_str == "STOCK":
            opt_delta = 1.0
        else:
            opt_delta = self.inst_config.get('option_delta', self.config.OPTION_DELTA)

        exit_mode = self.inst_config.get("exit_mode", "ATR")
        
        if exit_mode == "SWING":
            # SWING Stop Loss & Spot Exit mode calculations
            entry_idx = self.df_spot.index.get_loc(timestamp)
            signal_idx = entry_idx - 1
            swing_window = self.inst_config.get("swing_window_size", 10)
            start_idx = max(0, signal_idx - swing_window + 1)
            end_idx = signal_idx + 1
            
            spot_lows = self.df_spot['low'].iloc[start_idx:end_idx]
            spot_highs = self.df_spot['high'].iloc[start_idx:end_idx]
            
            sl_buffer = spot_atr_val * self.inst_config.get("sl_buffer_atr_mult", 0.2)
            
            spot_is_bearish = (option_type_str == "PE" and not is_short) or (option_type_str == "CE" and is_short) or (option_type_str == "STOCK" and is_short)
            if not spot_is_bearish:
                spot_sl_price = spot_lows.min() - sl_buffer
                spot_target_price = spot_close_val + (spot_atr_val * tp_mult)
            else:
                spot_sl_price = spot_highs.max() + sl_buffer
                spot_target_price = spot_close_val - (spot_atr_val * tp_mult)
                
            sl_price = 0.0 if not spot_is_bearish else 999999.0
            tp_price = 999999.0 if not spot_is_bearish else 0.0
            opt_trail_jump = 0.0
        elif exit_mode == "SWING_CONTRACT":
            # SWING Stop Loss & Target calculated on the traded contract (option or stock) itself
            swing_window = self.inst_config.get("swing_window_size", 10)
            sl_buffer_atr_mult = self.inst_config.get("sl_buffer_atr_mult", 0.2)
            
            if option_type_str == "STOCK":
                # For STOCK mode, the traded contract is self.df_spot (the stock spot)
                entry_idx = self.df_spot.index.get_loc(timestamp)
                signal_idx = entry_idx - 1
                start_idx = max(0, signal_idx - swing_window + 1)
                end_idx = signal_idx + 1
                
                lows_series = self.df_spot['low'].iloc[start_idx:end_idx]
                highs_series = self.df_spot['high'].iloc[start_idx:end_idx]
                contract_atr_val = spot_atr_val
            else:
                # For OPTION mode, the traded contract is opt_df
                if opt_df is not None and not opt_df.empty:
                    # Calculate 14-period ATR on opt_df if not already calculated
                    if 'ATR' not in opt_df.columns:
                        if ta is not None:
                            opt_df['ATR'] = ta.atr(opt_df['high'], opt_df['low'], opt_df['close'], length=self.config.ATR_PERIOD)
                        else:
                            high_low = opt_df['high'] - opt_df['low']
                            high_cp = (opt_df['high'] - opt_df['close'].shift(1)).abs()
                            low_cp = (opt_df['low'] - opt_df['close'].shift(1)).abs()
                            tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
                            opt_df['ATR'] = tr.rolling(window=14).mean()
                    
                    try:
                        entry_idx = opt_df.index.get_loc(timestamp)
                        signal_idx = entry_idx - 1
                        start_idx = max(0, signal_idx - swing_window + 1)
                        end_idx = signal_idx + 1
                        
                        lows_series = opt_df['low'].iloc[start_idx:end_idx]
                        highs_series = opt_df['high'].iloc[start_idx:end_idx]
                        
                        # Find non-NaN ATR value
                        contract_atr_val = opt_df['ATR'].iloc[entry_idx]
                        if np.isnan(contract_atr_val):
                            # Try forward fill or backward fill
                            contract_atr_val = opt_df['ATR'].ffill().bfill().iloc[entry_idx]
                        if np.isnan(contract_atr_val) or pd.isna(contract_atr_val):
                            contract_atr_val = spot_atr_val * opt_delta
                    except Exception:
                        lows_series = pd.Series([opt_entry_val])
                        highs_series = pd.Series([opt_entry_val])
                        contract_atr_val = spot_atr_val * opt_delta
                else:
                    lows_series = pd.Series([opt_entry_val])
                    highs_series = pd.Series([opt_entry_val])
                    contract_atr_val = spot_atr_val * opt_delta

            sl_buffer = contract_atr_val * sl_buffer_atr_mult
            min_low = lows_series.min()
            if pd.isna(min_low) or np.isnan(min_low):
                min_low = opt_entry_val
                
            max_high = highs_series.max()
            if pd.isna(max_high) or np.isnan(max_high):
                max_high = opt_entry_val
                
            if not is_short:
                sl_price = float(min_low - sl_buffer)
                fixed_target_buy = self.inst_config.get('profit_target_buy', 0)
                if fixed_target_buy > 0:
                    opt_tp_points = fixed_target_buy / lot_size
                    tp_price = float(actual_entry + opt_tp_points)
                else:
                    tp_price = float(actual_entry + (contract_atr_val * tp_mult))
                opt_trail_jump = float(contract_atr_val * trail_mult)
            else:
                sl_price = float(max_high + sl_buffer)
                fixed_target_sell = self.inst_config.get('profit_target_sell', 0)
                if fixed_target_sell > 0:
                    opt_tp_points = fixed_target_sell / lot_size
                    tp_price = float(actual_entry - opt_tp_points)
                else:
                    tp_price = float(actual_entry - (contract_atr_val * tp_mult))
                opt_trail_jump = float(contract_atr_val * trail_mult)
                
            # Prevent stop loss or target price from crossing invalid levels
            if sl_price <= 0 and not is_short:
                sl_price = 0.05
            if tp_price <= 0 and is_short:
                tp_price = 0.05
                
            spot_sl_price = 0.0
            spot_target_price = 0.0
        elif exit_mode == "POINTS":
            # Fixed points-based Stop Loss, Target, and Trailing stops calculated on traded contract
            points_sl_buy = self.inst_config.get('points_sl_buy', 0)
            points_target_buy = self.inst_config.get('points_target_buy', 0)
            points_trail_buy = self.inst_config.get('points_trail_buy', 0)
            points_sl_sell = self.inst_config.get('points_sl_sell', 0)
            points_target_sell = self.inst_config.get('points_target_sell', 0)
            points_trail_sell = self.inst_config.get('points_trail_sell', 0)
            
            if not is_short:
                sl_price = float(actual_entry - points_sl_buy) if points_sl_buy > 0 else 0.0
                tp_price = float(actual_entry + points_target_buy) if points_target_buy > 0 else 999999.0
                opt_trail_jump = float(points_trail_buy)
            else:
                sl_price = float(actual_entry + points_sl_sell) if points_sl_sell > 0 else 999999.0
                tp_price = float(actual_entry - points_target_sell) if points_target_sell > 0 else 0.05
                opt_trail_jump = float(points_trail_sell)
                
            # Prevent stop loss or target price from crossing invalid levels
            if sl_price <= 0 and not is_short:
                sl_price = 0.05
            if tp_price <= 0 and is_short:
                tp_price = 0.05
                
            spot_sl_price = 0.0
            spot_target_price = 0.0
        else:
            # Legacy ATR-based option stop/target logic
            spot_sl_price = 0.0
            spot_target_price = 0.0
            opt_sl_points = round(spot_atr_val * sl_mult * opt_delta, 1)
            opt_trail_jump = round(spot_atr_val * trail_mult * opt_delta, 1)
            
            if not is_short:
                sl_price = actual_entry - opt_sl_points if opt_sl_points > 0 else 0.0
                
                fixed_target_buy = self.inst_config.get('profit_target_buy', 0)
                if fixed_target_buy > 0:
                    opt_tp_points = round(fixed_target_buy / lot_size, 1)
                    tp_price = actual_entry + opt_tp_points
                else:
                    opt_tp_points = round(spot_atr_val * tp_mult * opt_delta, 1)
                    tp_price = actual_entry + opt_tp_points if opt_tp_points > 0 else 999999.0
            else:
                sl_price = actual_entry + opt_sl_points if opt_sl_points > 0 else 999999.0
                
                fixed_target_sell = self.inst_config.get('profit_target_sell', 0)
                if fixed_target_sell > 0:
                    opt_tp_points = round(fixed_target_sell / lot_size, 1)
                    tp_price = max(actual_entry - opt_tp_points, 0.05)
                else:
                    target_type = self.inst_config.get("short_option_target_type")
                    if not target_type:
                        target_type = "ATR" if option_type_str == "STOCK" else "MAX_PROFIT"
                        
                    decay_val = float(self.inst_config.get("short_option_decay_value", 0.05))
                    if target_type == "ATR":
                        opt_tp_points = round(spot_atr_val * tp_mult * opt_delta, 1)
                    else: # MAX_PROFIT
                        opt_tp_points = round(actual_entry - decay_val, 1)
                        if opt_tp_points <= 0:
                            opt_tp_points = round(spot_atr_val * tp_mult * opt_delta, 1)
                    
                    # Floor Protection: Cap target points so target price never goes below decay_val
                    max_tp_pts = round(actual_entry - decay_val, 1)
                    if opt_tp_points > max_tp_pts:
                        opt_tp_points = max(max_tp_pts, 0.0)
                    tp_price = max(actual_entry - opt_tp_points, decay_val) if opt_tp_points > 0 else 0.0
            
        # Determine breakeven multiplier
        if exit_mode == "POINTS":
            breakeven_mult = float(self.inst_config.get("points_be_buy" if not is_short else "points_be_sell", 0.0))
        else:
            breakeven_mult = float(self.inst_config.get("atr_be_buy" if not is_short else "atr_be_sell", 0.0))

        if qty is None:
            qty = lot_size * (self.inst_config.get('num_lots_sell', 1) if is_short else self.inst_config.get('num_lots_buy', 1))

        # Determine market regime at entry
        adx_col = None
        for col in ['TM_ADX', 'ADX', 'ADX_14']:
            if self.df_spot is not None and col in self.df_spot.columns:
                adx_col = col
                break
                
        adx_val = 20.0
        if adx_col and self.df_spot is not None and timestamp in self.df_spot.index:
            val = self.df_spot.loc[timestamp, adx_col]
            if isinstance(val, pd.Series):
                val = val.iloc[0]
            adx_val = float(val) if pd.notna(val) else 20.0
            
        regime_trend = "TREND" if adx_val > 25.0 else ("RANGE" if adx_val < 20.0 else "NEUTRAL")
        
        atr_pct_val = (spot_atr_val / spot_close_val) * 100 if spot_close_val > 0 else 0.0
        regime_vol = "HIGH_VIX" if atr_pct_val > getattr(self, "median_atr_pct", 0.0) else "LOW_VIX"

        return {
            "Entry_Time": timestamp,
            "Type": option_type_str,
            "Is_Short": is_short,
            "Trade_Type": "SELL" if is_short else "BUY",
            "Option_Symbol": f"{self.instrument_name}" if option_type_str == "STOCK" else f"{self.instrument_name} {target_strike} {option_type_str}",
            "Strike": target_strike,
            "Expiry": expiry_str,
            "Strategy": signal_source,
            "Entry_Price": actual_entry,
            "Qty": qty,
            "Target_Price": tp_price,
            "SL_Price": sl_price,
            "Initial_SL": sl_price,
            "Spot_ATR": spot_atr_val,
            "Entry_Spot": spot_close_val,
            "Max_Favorable_Excursion": actual_entry,
            "Trailing_Trigger_Points": round(spot_atr_val * self.config.TRAIL_TRIGGER_ATR * opt_delta, 1) if exit_mode != "SWING" else 0.0,
            "Trailing_Jump_Points": opt_trail_jump,
            "exit_mode": exit_mode,
            "spot_sl_price": spot_sl_price,
            "spot_target_price": spot_target_price,
            "spot_initial_sl": spot_sl_price,
            "spot_mfe": spot_close_val,
            "spot_atr": spot_atr_val,
            "Breakeven_Mult": breakeven_mult,
            "Initial_SL_Points": abs(actual_entry - sl_price) if (sl_price > 0 and sl_price != 999999.0) else 0.0,
            "Breakeven_Triggered": False,
            "opt_df": opt_df,
            "Regime_Trend": regime_trend,
            "Regime_Vol": regime_vol
        }
        
    def _manage_trade_fast(self, timestamp, trade, open_val, high, low, close, is_opening_candle=False) -> bool:
        """Returns True if the trade was closed, False otherwise."""
        if np.isnan(low) or np.isnan(high) or np.isnan(open_val):
            return False
            
        if open_val <= 0 or low <= 0 or high <= 0 or (not np.isnan(close) and close <= 0):
            return False
            
        is_short = trade.get("Is_Short", False)
        is_stock = (trade.get("Type") == "STOCK")
        
        # Check for dynamic strategy-based exits
        if getattr(self.config, "USE_DYNAMIC_EXITS", False) and timestamp != trade.get("Entry_Time"):
            if self.df_spot is not None and timestamp in self.df_spot.index:
                if not is_short:
                    if 'Exit_Long' in self.df_spot.columns:
                        val = self.df_spot.loc[timestamp, 'Exit_Long']
                        if isinstance(val, pd.Series):
                            val = val.iloc[0]
                        if bool(val):
                            exit_price = self.apply_slippage(open_val, 'SELL', is_stock=is_stock)
                            self._close_trade_fast_exit(timestamp, trade, "Strategy_Exit", exit_price)
                            return True
                else:
                    if 'Exit_Short' in self.df_spot.columns:
                        val = self.df_spot.loc[timestamp, 'Exit_Short']
                        if isinstance(val, pd.Series):
                            val = val.iloc[0]
                        if bool(val):
                            exit_price = self.apply_slippage(open_val, 'BUY', is_stock=is_stock)
                            self._close_trade_fast_exit(timestamp, trade, "Strategy_Exit", exit_price)
                            return True

        if trade.get("exit_mode") == "SWING":
            if self.df_spot is not None and timestamp in self.df_spot.index:
                spot_row = self.df_spot.loc[timestamp]
                if isinstance(spot_row, pd.DataFrame):
                    spot_row = spot_row.iloc[0]
                spot_high = spot_row['high']
                spot_low = spot_row['low']
                spot_close = spot_row['close']
                
                # Dynamic SL, Trailing, and TP Multipliers from config
                if not is_short:
                    trail_mult = self.inst_config['trailing_mult_buy']
                else:
                    trail_mult = self.inst_config['trailing_mult_sell']
                
                spot_atr = trade['spot_atr']
                trail_jump = spot_atr * trail_mult
                
                spot_is_bearish = (trade.get("Type") == "PE" and not is_short) or (trade.get("Type") == "CE" and is_short) or (trade.get("Type") == "STOCK" and is_short)
                if not spot_is_bearish:
                    # BUY Trade Spot Exit Checks
                    # 1. Stop Loss Hit
                    if is_opening_candle and spot_row['open'] <= trade['spot_sl_price']:
                        exit_price = self.apply_slippage(open_val, 'SELL', is_stock=is_stock)
                        self._close_trade_fast_exit(timestamp, trade, "GapDown_SL", exit_price)
                        return True
                    elif spot_low <= trade['spot_sl_price']:
                        exit_price = self.apply_slippage(open_val, 'SELL', is_stock=is_stock)
                        self._close_trade_fast_exit(timestamp, trade, "StopLoss", exit_price)
                        return True
                    # 2. Target Hit
                    if is_opening_candle and spot_row['open'] >= trade['spot_target_price']:
                        exit_price = self.apply_slippage(open_val, 'SELL', is_stock=is_stock)
                        self._close_trade_fast_exit(timestamp, trade, "GapUp_Target", exit_price)
                        return True
                    elif spot_high >= trade['spot_target_price']:
                        exit_price = self.apply_slippage(open_val, 'SELL', is_stock=is_stock)
                        self._close_trade_fast_exit(timestamp, trade, "Target", exit_price)
                        return True
                    # 3. Trailing Stop Loss on Spot
                    if spot_high > trade['spot_mfe']:
                        trade['spot_mfe'] = spot_high
                    
                    if trail_jump > 0 and spot_high > trade['Entry_Spot']:
                        steps = int((spot_high - trade['Entry_Spot']) / trail_jump)
                        if steps >= 1:
                            new_sl = trade['spot_initial_sl'] + (steps * trail_jump)
                            if new_sl > trade['spot_sl_price']:
                                trade['spot_sl_price'] = new_sl
                else:
                    # SELL Trade Spot Exit Checks
                    # 1. Stop Loss Hit
                    if is_opening_candle and spot_row['open'] >= trade['spot_sl_price']:
                        exit_price = self.apply_slippage(open_val, 'BUY', is_stock=is_stock)
                        self._close_trade_fast_exit(timestamp, trade, "GapUp_SL", exit_price)
                        return True
                    elif spot_high >= trade['spot_sl_price']:
                        exit_price = self.apply_slippage(open_val, 'BUY', is_stock=is_stock)
                        self._close_trade_fast_exit(timestamp, trade, "StopLoss", exit_price)
                        return True
                    # 2. Target Hit
                    if is_opening_candle and spot_row['open'] <= trade['spot_target_price']:
                        exit_price = self.apply_slippage(open_val, 'BUY', is_stock=is_stock)
                        self._close_trade_fast_exit(timestamp, trade, "GapDown_Target", exit_price)
                        return True
                    elif spot_low <= trade['spot_target_price']:
                        exit_price = self.apply_slippage(open_val, 'BUY', is_stock=is_stock)
                        self._close_trade_fast_exit(timestamp, trade, "Target", exit_price)
                        return True
                    # 3. Trailing Stop Loss on Spot
                    if spot_low < trade['spot_mfe']:
                        trade['spot_mfe'] = spot_low
                    
                    if trail_jump > 0 and spot_low < trade['Entry_Spot']:
                        steps = int((trade['Entry_Spot'] - spot_low) / trail_jump)
                        if steps >= 1:
                            new_sl = trade['spot_initial_sl'] - (steps * trail_jump)
                            if new_sl < trade['spot_sl_price']:
                                trade['spot_sl_price'] = new_sl
            return False

        # Legacy ATR-based option premium exit logic
        if not is_short:
            # 1. Check if SL was hit first at open (using the current SL_Price)
            if is_opening_candle and open_val <= trade['SL_Price']:
                exit_price = self.apply_slippage(open_val, 'SELL', is_stock=is_stock)
                self._close_trade_fast_exit(timestamp, trade, "GapDown_SL", exit_price)
                return True
            # 2. Check if Target was hit at open
            if is_opening_candle and open_val >= trade['Target_Price']:
                exit_price = self.apply_slippage(open_val, 'SELL', is_stock=is_stock)
                self._close_trade_fast_exit(timestamp, trade, "GapUp_Target", exit_price)
                return True

            # 3. Check Breakeven Trigger
            be_mult = trade.get("Breakeven_Mult", 0.0)
            if be_mult > 0.0 and not trade.get("Breakeven_Triggered", False) and trade.get("Initial_SL_Points", 0.0) > 0.0:
                trigger_level = trade["Entry_Price"] + (trade["Initial_SL_Points"] * be_mult)
                if high >= trigger_level:
                    trade["SL_Price"] = max(trade["SL_Price"], trade["Entry_Price"])
                    trade["Breakeven_Triggered"] = True

            # 4. Check if SL is hit during the candle
            if low <= trade['SL_Price']:
                exit_price = self.apply_slippage(trade['SL_Price'], 'SELL', is_stock=is_stock)
                self._close_trade_fast_exit(timestamp, trade, "StopLoss", exit_price)
                return True
                
            # 5. Check if Target is hit during the candle
            if high >= trade['Target_Price']:
                exit_price = self.apply_slippage(trade['Target_Price'], 'SELL', is_stock=is_stock)
                self._close_trade_fast_exit(timestamp, trade, "Target", exit_price)
                return True
                
            # 6. Update trailing SL based on high of current candle
            if high > trade['Max_Favorable_Excursion']:
                trade['Max_Favorable_Excursion'] = high
                
            trail_jump = trade['Trailing_Jump_Points']
            if trail_jump > 0 and high > trade['Entry_Price']:
                steps = int((high - trade['Entry_Price']) / trail_jump)
                if steps >= 1:
                    new_sl = trade['Initial_SL'] + steps * trail_jump
                    if new_sl > trade['SL_Price']:
                        trade['SL_Price'] = new_sl
        else:
            # 1. Check if SL was hit first at open (using the current SL_Price)
            if is_opening_candle and open_val >= trade['SL_Price']:
                exit_price = self.apply_slippage(open_val, 'BUY', is_stock=is_stock)
                self._close_trade_fast_exit(timestamp, trade, "GapUp_SL", exit_price)
                return True
            # 2. Check if Target was hit at open
            if is_opening_candle and open_val <= trade['Target_Price']:
                exit_price = self.apply_slippage(open_val, 'BUY', is_stock=is_stock)
                self._close_trade_fast_exit(timestamp, trade, "GapDown_Target", exit_price)
                return True

            # 3. Check Breakeven Trigger
            be_mult = trade.get("Breakeven_Mult", 0.0)
            if be_mult > 0.0 and not trade.get("Breakeven_Triggered", False) and trade.get("Initial_SL_Points", 0.0) > 0.0:
                trigger_level = trade["Entry_Price"] - (trade["Initial_SL_Points"] * be_mult)
                if low <= trigger_level:
                    trade["SL_Price"] = min(trade["SL_Price"], trade["Entry_Price"])
                    trade["Breakeven_Triggered"] = True

            # 4. Check if SL is hit during the candle
            if high >= trade['SL_Price']:
                exit_price = self.apply_slippage(trade['SL_Price'], 'BUY', is_stock=is_stock)
                self._close_trade_fast_exit(timestamp, trade, "StopLoss", exit_price)
                return True
                
            # 5. Check if Target is hit during the candle
            if low <= trade['Target_Price']:
                exit_price = self.apply_slippage(trade['Target_Price'], 'BUY', is_stock=is_stock)
                self._close_trade_fast_exit(timestamp, trade, "Target", exit_price)
                return True
                
            # 6. Update trailing SL based on low of current candle
            if low < trade['Max_Favorable_Excursion']:
                trade['Max_Favorable_Excursion'] = low
                
            trail_jump = trade['Trailing_Jump_Points']
            if trail_jump > 0 and low < trade['Entry_Price']:
                steps = int((trade['Entry_Price'] - low) / trail_jump)
                if steps >= 1:
                    new_sl = trade['Initial_SL'] - steps * trail_jump
                    if new_sl < trade['SL_Price']:
                        trade['SL_Price'] = new_sl
        return False
        return False
  
    def _close_trade_fast_direct(self, timestamp, trade, exit_reason, opt_open_val, spot_close_val=None):
        is_short = trade.get("Is_Short", False)
        is_stock = (trade.get("Type") == "STOCK")
        
        if trade.get("Type") == "STOCK":
            exit_val = opt_open_val if (not np.isnan(opt_open_val) and opt_open_val > 0) else spot_close_val
            if exit_val is None or np.isnan(exit_val):
                exit_val = trade['Entry_Price']
            if not is_short:
                exit_price = self.apply_slippage(exit_val, 'SELL', is_stock=is_stock)
            else:
                exit_price = self.apply_slippage(exit_val, 'BUY', is_stock=is_stock)
        else:
            if not np.isnan(opt_open_val) and opt_open_val > 0:
                if not is_short:
                    exit_price = self.apply_slippage(opt_open_val, 'SELL', is_stock=is_stock)
                else:
                    exit_price = self.apply_slippage(opt_open_val, 'BUY', is_stock=is_stock)
            else:
                # Fallback when option price is missing or zero
                is_expiry = (trade.get("Expiry") == timestamp.strftime("%Y-%m-%d"))
                if is_expiry and spot_close_val is not None:
                    # Expired: calculate exact intrinsic value
                    strike = trade["Strike"]
                    if trade["Type"] == "CE":
                        intrinsic = max(0.0, spot_close_val - strike)
                    else:
                        intrinsic = max(0.0, strike - spot_close_val)
                    exit_price = max(intrinsic, 0.05)
                elif spot_close_val is not None:
                    # Non-expiry day: estimate change using delta proxy
                    delta = self.config.OPTION_DELTA
                    entry_spot = trade["Entry_Spot"]
                    entry_price = trade["Entry_Price"]
                    if trade["Type"] == "CE":
                        val = entry_price + (spot_close_val - entry_spot) * delta
                    else:
                        val = entry_price - (spot_close_val - entry_spot) * delta
                    exit_price = max(val, 0.05)
                else:
                    exit_price = trade['Entry_Price']
            
        self._close_trade_fast_exit(timestamp, trade, exit_reason, exit_price)
  
    def calculate_charges(self, buy_price: float, sell_price: float, qty: int, is_stock: bool = False) -> float:
        """Calculate precise Dhan Equity Options or Intraday Equity charges (India) per round-trip trade."""
        buy_val = buy_price * qty
        sell_val = sell_price * qty

        if is_stock:
            # 1. Buy side charges
            buy_brokerage = min(20.0, buy_val * 0.0003)
            buy_exchange = buy_val * 0.0000322
            buy_sebi = buy_val * 0.000001
            buy_stamp = buy_val * 0.00003
            buy_gst = 0.18 * (buy_brokerage + buy_exchange + buy_sebi)
            buy_total = buy_brokerage + buy_exchange + buy_sebi + buy_stamp + buy_gst

            # 2. Sell side charges
            sell_brokerage = min(20.0, sell_val * 0.0003)
            sell_stt = sell_val * 0.00025
            sell_exchange = sell_val * 0.0000322
            sell_sebi = sell_val * 0.000001
            sell_gst = 0.18 * (sell_brokerage + sell_exchange + sell_sebi)
            sell_total = sell_brokerage + sell_stt + sell_exchange + sell_sebi + sell_gst

            return round(buy_total + sell_total, 2)
        else:
            # 1. Buy side charges
            buy_brokerage = 20.0
            is_bse = any(x in self.instrument_name.upper() for x in ["SENSEX", "BANKEX"])
            exch_rate = 0.000325 if is_bse else 0.0003553
            buy_exchange = buy_val * exch_rate
            buy_sebi = buy_val * 0.000001
            # Stamp duty is 0.003% of premium value, rounded to nearest rupee (min ₹1 if buy_val > 0)
            buy_stamp = float(max(round(buy_val * 0.00003), 1)) if buy_val > 0 else 0.0
            buy_gst = 0.18 * (buy_brokerage + buy_exchange)
            buy_total = buy_brokerage + buy_exchange + buy_sebi + buy_stamp + buy_gst

            # 2. Sell side charges
            sell_brokerage = 20.0
            # STT is 0.15% of premium value on sell side, rounded to nearest rupee (effective April 1, 2026)
            sell_stt = float(round(sell_val * 0.0015))
            sell_exchange = sell_val * exch_rate
            sell_sebi = sell_val * 0.000001
            sell_gst = 0.18 * (sell_brokerage + sell_exchange)
            sell_total = sell_brokerage + sell_stt + sell_exchange + sell_sebi + sell_gst

            return round(buy_total + sell_total, 2)
  
    def _close_trade_fast_exit(self, timestamp, trade, exit_reason, exit_price):
        is_short = trade.get("Is_Short", False)
        is_stock = (trade.get("Type") == "STOCK")
        
        if not is_short:
            gross_pnl = (exit_price - trade['Entry_Price']) * trade['Qty']
            charges = self.calculate_charges(trade['Entry_Price'], exit_price, trade['Qty'], is_stock=is_stock)
            excursion = round(trade['Max_Favorable_Excursion'] - trade['Entry_Price'], 2)
        else:
            gross_pnl = (trade['Entry_Price'] - exit_price) * trade['Qty']
            charges = self.calculate_charges(exit_price, trade['Entry_Price'], trade['Qty'], is_stock=is_stock)
            excursion = round(trade['Entry_Price'] - trade['Max_Favorable_Excursion'], 2)
            
        net_pnl = gross_pnl - charges
        
        exit_spot = np.nan
        if self.df_spot is not None and timestamp in self.df_spot.index:
            spot_val = self.df_spot.loc[timestamp, 'close']
            if isinstance(spot_val, pd.Series):
                spot_val = spot_val.iloc[0]
            exit_spot = round(float(spot_val), 2)
            
        trade_log = {k: v for k, v in trade.items() if k != "opt_df"}
        trade_log.update({
            "Exit_Time": timestamp,
            "Exit_Price": round(exit_price, 2),
            "Exit_Spot": exit_spot,
            "Gross_PnL": round(gross_pnl, 2),
            "Charges": round(charges, 2),
            "PnL": round(net_pnl, 2),
            "Exit_Reason": exit_reason,
            "Max_Excursion_Pts": excursion
        })
        self.trades.append(trade_log)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SATP Backtesting Engine")
    parser.add_argument("-s", "--strategy", type=str, default=None, help="Strategy name to run (e.g. Strategy_15)")
    parser.add_argument("-d", "--days", type=int, default=730, help="Number of days to backtest")
    parser.add_argument("--symbol", type=str, default="NIFTY", help="Symbol to backtest")
    parser.add_argument("--leg", type=str, choices=["BUY", "SELL", "BOTH"], default=None, help="Leg execution mode")
    args = parser.parse_args()
    
    # Load .env file and align config LEG_MODE
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
    
    config = BacktestConfig()
    
    # Override strategy toggles if specified
    if args.strategy:
        strategy_name = args.strategy
        for name in STRATEGY_REGISTRY.keys():
            toggle_name = f"ENABLE_{name.upper()}"
            setattr(config, toggle_name, (name == strategy_name))
        config.apply_strategy_defaults(strategy_name)
    else:
        # Resolve active strategy name from config defaults
        strategy_name = "Strategy_13"
        for s in STRATEGY_REGISTRY.keys():
            if getattr(config, f"ENABLE_{s.upper()}", False):
                strategy_name = s
                break
                
    if args.leg:
        config.LEG_MODE = args.leg
    else:
        env_leg_mode = os.getenv("LEG_MODE", "BOTH").upper()
        if env_leg_mode in ["BUY", "SELL", "BOTH"]:
            config.LEG_MODE = env_leg_mode
            
    print(f"[INFO] Aligned backtest engine with LEG_MODE = {config.LEG_MODE}")
    print(f"[INFO] Active Strategy: {strategy_name}")
    print(f"[INFO] Backtest Days: {args.days}")
    print(f"[INFO] Running backtest with DEFAULT parameters...")
    
    engine = SimulationEngine(config, instrument_name=args.symbol, backtest_days=args.days)
    engine.load_data()
    results = engine.run()
    
    if not results.empty:
        total_net_pnl = results['PnL'].sum()
        total_gross_pnl = results['Gross_PnL'].sum()
        total_charges = results['Charges'].sum()
        win_rate = (len(results[results['PnL'] > 0]) / len(results)) * 100
        total_trades = len(results)
        profit_factor = 0
        
        gross_profit = results[results['PnL'] > 0]['PnL'].sum()
        gross_loss = abs(results[results['PnL'] < 0]['PnL'].sum())
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        
        print("\n" + "="*30)
        print("    BACKTEST RESULTS    ")
        print("="*30)
        print(f"Total Trades:    {total_trades}")
        print(f"Win Rate:        {win_rate:.1f}%")
        print(f"Profit Factor:   {profit_factor:.2f}")
        print(f"Gross PnL:       Rs.{total_gross_pnl:.2f}")
        print(f"Total Charges:   Rs.{total_charges:.2f}")
        print(f"Net PnL:         Rs.{total_net_pnl:.2f}")
        print("="*30)
        print("[SUCCESS] Full results saved to backtest_results.csv")
    else:
        print("[WARNING] No trades executed.")
