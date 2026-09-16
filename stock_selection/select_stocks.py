import os
import sys
import argparse
import glob
import json
import warnings
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time
from multiprocessing.pool import ThreadPool
from dotenv import load_dotenv

# Silence XGBoost and pandas datetime format inference warnings
warnings.filterwarnings("ignore", category=UserWarning)

def safe_to_datetime(series_or_scalar):
    """Safely parse dates with mixed formats and dayfirst=True support, fallback on error."""
    try:
        return pd.to_datetime(series_or_scalar, format='ISO8601')
    except Exception:
        try:
            return pd.to_datetime(series_or_scalar, format='mixed', dayfirst=True)
        except Exception:
            return pd.to_datetime(series_or_scalar, errors='coerce')


# Setup project root pathing
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
MODEL_DIR = os.path.join(BASE_DIR, "stock_selection", "models")
PRED_DIR = os.path.join(BASE_DIR, "stock_selection", "predictions")
os.makedirs(PRED_DIR, exist_ok=True)

FEATURE_NAMES = [
    "ret_30m", "ret_15m", "ret_10m", "ret_5m", "ret_day",
    "vol_30m", "range_30m", "vol_ratio", "vol_ratio_5m",
    "green_count", "red_count", "clv_mean", "clv_last",
    "upper_wick_mean", "lower_wick_mean", "rsi", "ema_diff", "atr",
    "nifty_ret_30m", "nifty_rsi", "range_ratio_T", "range_ratio_T_1", "range_ratio_T_2",
    "weekday", "previous_gap"
]
for i in range(30):
    FEATURE_NAMES.extend([f"close_ret_{i}", f"body_{i}", f"vol_ratio_{i}"])

def read_last_n_lines_to_df(filepath, n=2000):
    """Reads the last N lines of a CSV file very quickly using binary seek, prepending the actual header dynamically."""
    try:
        # 1. Read the actual header from the first line of the file
        with open(filepath, 'r', encoding='utf-8') as f:
            header_line = f.readline()
        if not header_line:
            raise ValueError(f"File {filepath} is empty.")
            
        header_cols = [c.strip().lower() for c in header_line.split(',')]
        
        # 2. Seek and read the last N lines binary
        with open(filepath, 'rb') as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            chunk_size = max(100, n * 80)
            pos = max(0, pos - chunk_size)
            f.seek(pos)
            chunk = f.read()
            lines = chunk.split(b'\n')
            non_empty_lines = [l for l in lines if l.strip()]
            last_lines = non_empty_lines[-n:]
            
            from io import StringIO
            data_str = header_line.strip() + "\n" + b'\n'.join(last_lines).decode('utf-8')
            df = pd.read_csv(StringIO(data_str))
            
            # 3. Standardize columns
            # Convert column names to lowercase and strip whitespace
            df.columns = [c.strip().lower() for c in df.columns]
            
            # Map start_time to timestamp
            if "start_time" in df.columns:
                df.rename(columns={"start_time": "timestamp"}, inplace=True)
                
            required = ["timestamp", "open", "high", "low", "close", "volume"]
            missing = [col for col in required if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns {missing} in file {filepath}. Found: {list(df.columns)}")
                
            # Filter and order standard columns
            return df[required]
    except Exception as e:
        print(f"[WARNING] Fast-path reader failed for {filepath}: {e}. Falling back to full read.")
        # Fallback to slow path but enforce standardization and validation
        df = pd.read_csv(filepath)
        df.columns = [c.strip().lower() for c in df.columns]
        if "start_time" in df.columns:
            df.rename(columns={"start_time": "timestamp"}, inplace=True)
        required = ["timestamp", "open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns {missing} in file {filepath} on fallback path.")
        return df[required]

# Import centralized feature timing constants
sys.path.append(os.path.join(BASE_DIR, "stock_selection"))
from constants import get_last_30m_window, MIN_WINDOW_CANDLES

def precompute_nifty_features():
    print("[NIFTY] Precomputing market index features from nifty_spot.csv...")
    nifty_path = os.path.join(DATA_DIR, "nifty_spot.csv")
    if not os.path.exists(nifty_path):
        print("[WARNING] nifty_spot.csv not found for index context precomputation.")
        return {}
    try:
        df = read_last_n_lines_to_df(nifty_path, 15000)
        col_name = 'timestamp' if 'timestamp' in df.columns else ('start_time' if 'start_time' in df.columns else df.columns[0])
        df[col_name] = safe_to_datetime(df[col_name])
        df.set_index(col_name, inplace=True)
        df = df[df.index.notna()].sort_index()
        df.index = pd.DatetimeIndex(df.index)
        df = df.between_time('09:15', '15:30')
        
        try:
            import pandas_ta as ta
            df['rsi'] = ta.rsi(df['close'], length=14)
        except Exception:
            df['rsi'] = 50.0
            
        df.ffill(inplace=True)
        df.dropna(subset=['rsi'], inplace=True)
        
        df_by_date = {d: grp for d, grp in df.groupby(df.index.date)}
        nifty_features = {}
        for d, day_df in df_by_date.items():
            last_30_df = get_last_30m_window(day_df, d)
            if len(last_30_df) < MIN_WINDOW_CANDLES:
                continue
            ret_30m = (last_30_df['close'].iloc[-1] - last_30_df['open'].iloc[0]) / (last_30_df['open'].iloc[0] + 1e-8)
            rsi_val = last_30_df['rsi'].iloc[-1]
            nifty_features[d] = {
                "nifty_ret_30m": float(ret_30m),
                "nifty_rsi": float(rsi_val)
            }
        print(f"[NIFTY SUCCESS] Precomputed {len(nifty_features)} trading days of index context.")
        return nifty_features
    except Exception as e:
        print(f"[WARNING] Failed to precompute NIFTY features: {e}")
        return {}

def extract_features_for_last_day(symbol, nifty_features=None):
    spot_path = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
    if not os.path.exists(spot_path):
        return None, "Spot file not found"

    try:
        # 1. Read spot data (fast tail loading with 8000 lines to ensure enough history for ATR and compression)
        df = read_last_n_lines_to_df(spot_path, 8000)
        col_name = 'timestamp' if 'timestamp' in df.columns else ('start_time' if 'start_time' in df.columns else df.columns[0])
        df[col_name] = safe_to_datetime(df[col_name])
        df.set_index(col_name, inplace=True)
        df = df[df.index.notna()].sort_index()
        df.index = pd.DatetimeIndex(df.index)
        
        # Isolate session
        df = df.between_time('09:15', '15:30')
        if df.empty:
            return None, "No session candles"

        # 2. Add indicators
        try:
            import pandas_ta as ta
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema_9'] = ta.ema(df['close'], length=9)
            df['ema_21'] = ta.ema(df['close'], length=21)
            df['ema_diff'] = (df['ema_9'] - df['ema_21']) / (df['ema_21'] + 1e-8)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        except Exception as e:
            df['rsi'] = 50.0
            df['ema_diff'] = 0.0
            df['atr'] = df['high'] - df['low']

        df.ffill(inplace=True)
        df.dropna(subset=['rsi', 'ema_diff', 'atr'], inplace=True)

        # 3. Find the most recent day with complete afternoon candles
        df_by_date = {d: grp for d, grp in df.groupby(df.index.date)}
        chronological_dates = sorted(list(df_by_date.keys()))
        
        features_found = False
        day_df = None
        last_30_df = None
        last_date = None
        
        for d in reversed(chronological_dates):
            day_df = df_by_date[d]
            last_30_df = get_last_30m_window(day_df, d)
            if len(last_30_df) >= MIN_WINDOW_CANDLES:
                last_date = d
                features_found = True
                break
                
        if not features_found:
            return None, "No recent day with sufficient afternoon candles found"

        # Price slices
        l30_closes = last_30_df['close'].values
        l30_opens = last_30_df['open'].values
        l30_highs = last_30_df['high'].values
        l30_lows = last_30_df['low'].values
        l30_vols = last_30_df['volume'].values

        # Feature calculations
        ret_30m = (l30_closes[-1] - l30_opens[0]) / (l30_opens[0] + 1e-8)
        ret_15m = (l30_closes[-1] - l30_opens[15]) / (l30_opens[15] + 1e-8) if len(l30_opens) > 15 else ret_30m
        ret_10m = (l30_closes[-1] - l30_opens[20]) / (l30_opens[20] + 1e-8) if len(l30_opens) > 20 else ret_30m
        ret_5m = (l30_closes[-1] - l30_opens[-5]) / (l30_opens[-5] + 1e-8) if len(l30_opens) > 5 else ret_30m
        
        day_open_val = day_df['open'].iloc[0]
        ret_day = (l30_opens[0] - day_open_val) / (day_open_val + 1e-8)

        vol_30m = np.std([np.log(l30_closes[i]/l30_closes[i-1]) for i in range(1, len(l30_closes))]) if len(l30_closes) > 1 else 0.0
        range_30m = (np.max(l30_highs) - np.min(l30_lows)) / (l30_closes[-1] + 1e-8)

        mean_vol_day = day_df['volume'].mean() + 1e-8
        mean_vol_30m = last_30_df['volume'].mean()
        vol_ratio = mean_vol_30m / mean_vol_day
        vol_ratio_5m = last_30_df['volume'].iloc[-5:].mean() / (mean_vol_30m + 1e-8)

        green_count = sum(l30_closes > l30_opens)
        red_count = sum(l30_closes < l30_opens)

        clv_vals = ((last_30_df['close'] - last_30_df['low']) - (last_30_df['high'] - last_30_df['close'])) / (last_30_df['high'] - last_30_df['low'] + 1e-8)
        clv_mean = clv_vals.mean()
        clv_last = clv_vals.iloc[-1]

        candle_heights = l30_highs - l30_lows
        upper_wicks = np.where(l30_closes > l30_opens, l30_highs - l30_closes, l30_highs - l30_opens)
        lower_wicks = np.where(l30_closes > l30_opens, l30_opens - l30_lows, l30_closes - l30_lows)
        upper_wick_mean = np.mean(upper_wicks / (candle_heights + 1e-8))
        lower_wick_mean = np.mean(lower_wicks / (candle_heights + 1e-8))

        rsi_val = last_30_df['rsi'].iloc[-1]
        ema_diff_val = last_30_df['ema_diff'].iloc[-1]
        atr_val = last_30_df['atr'].iloc[-1] / (l30_closes[-1] + 1e-8)

        # Calculate daily ranges and rolling daily ATR
        daily_highs = [df_by_date[d]['high'].max() for d in chronological_dates]
        daily_lows = [df_by_date[d]['low'].min() for d in chronological_dates]
        daily_closes = [df_by_date[d]['close'].iloc[-1] for d in chronological_dates]
        
        daily_tr = []
        for i, d in enumerate(chronological_dates):
            high_low = daily_highs[i] - daily_lows[i]
            if i == 0:
                daily_tr.append(high_low)
            else:
                prev_close = daily_closes[i - 1]
                high_pc = abs(daily_highs[i] - prev_close)
                low_pc = abs(daily_lows[i] - prev_close)
                daily_tr.append(max(high_low, high_pc, low_pc))
                
        daily_atr_series = pd.Series(daily_tr).rolling(14, min_periods=1).mean()
        daily_atr_dict = {chronological_dates[i]: daily_atr_series.iloc[i] for i in range(len(chronological_dates))}

        idx = chronological_dates.index(last_date)
        current_atr = daily_atr_dict[last_date]
        range_ratio_T = (daily_highs[idx] - daily_lows[idx]) / (current_atr + 1e-8)
        
        if idx >= 1:
            prev_atr_1 = daily_atr_dict[chronological_dates[idx - 1]]
            range_ratio_T_1 = (daily_highs[idx - 1] - daily_lows[idx - 1]) / (prev_atr_1 + 1e-8)
        else:
            range_ratio_T_1 = 1.0
            
        if idx >= 2:
            prev_atr_2 = daily_atr_dict[chronological_dates[idx - 2]]
            range_ratio_T_2 = (daily_highs[idx - 2] - daily_lows[idx - 2]) / (prev_atr_2 + 1e-8)
        else:
            range_ratio_T_2 = 1.0

        nifty_ret_30m = 0.0
        nifty_rsi = 50.0
        if nifty_features and last_date in nifty_features:
            nifty_ret_30m = nifty_features[last_date]["nifty_ret_30m"]
            nifty_rsi = nifty_features[last_date]["nifty_rsi"]

        # Weekday and Overnight Gap Features
        day_df = df_by_date[last_date]
        curr_open = day_df['open'].iloc[0]
        weekday = float(last_date.weekday())
        if idx >= 1:
            prev_close = daily_closes[idx - 1]
            previous_gap = (curr_open - prev_close) / (prev_close + 1e-8)
        else:
            previous_gap = 0.0

        # 30-Candle Sequence Shape Features
        closes_30 = l30_closes
        opens_30 = l30_opens
        vols_30 = l30_vols
        if len(closes_30) < 30:
            pad_width = 30 - len(closes_30)
            closes_30 = np.pad(closes_30, (0, pad_width), mode='edge')
            opens_30 = np.pad(opens_30, (0, pad_width), mode='edge')
            vols_30 = np.pad(vols_30, (0, pad_width), mode='edge')

        seq_features = {}
        for i in range(30):
            seq_features[f"close_ret_{i}"] = float((closes_30[i] - opens_30[i]) / (opens_30[i] + 1e-8))
            seq_features[f"body_{i}"] = float(abs(closes_30[i] - opens_30[i]) / (opens_30[i] + 1e-8))
            seq_features[f"vol_ratio_{i}"] = float(vols_30[i] / (mean_vol_day + 1e-8))

        features = {
            "ret_30m": ret_30m, "ret_15m": ret_15m, "ret_10m": ret_10m, "ret_5m": ret_5m, "ret_day": ret_day,
            "vol_30m": vol_30m, "range_30m": range_30m, "vol_ratio": vol_ratio, "vol_ratio_5m": vol_ratio_5m,
            "green_count": green_count, "red_count": red_count, "clv_mean": clv_mean, "clv_last": clv_last,
            "upper_wick_mean": upper_wick_mean, "lower_wick_mean": lower_wick_mean,
            "rsi": rsi_val, "ema_diff": ema_diff_val, "atr": atr_val,
            "nifty_ret_30m": nifty_ret_30m, "nifty_rsi": nifty_rsi,
            "range_ratio_T": range_ratio_T, "range_ratio_T_1": range_ratio_T_1, "range_ratio_T_2": range_ratio_T_2,
            "weekday": weekday, "previous_gap": previous_gap
        }
        features.update(seq_features)
        return features, last_date

    except Exception as e:
        return None, str(e)

def update_spot_file_if_stale(symbol, client_id, api_token):
    """Fetches the latest candles from Dhan API and appends them to the spot CSV file if stale."""
    if not client_id or not api_token:
        return
        
    spot_path = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
    if not os.path.exists(spot_path):
        return

    try:
        # Load instruments.json to get security_id and segment
        inst_file = os.path.join(BASE_DIR, "instruments.json")
        if not os.path.exists(inst_file):
            return
        with open(inst_file, "r") as f:
            instruments = json.load(f)
        inst_config = instruments.get(symbol.upper())
        if not inst_config:
            return

        # 1. Read last timestamp in file using seek (super fast and loop-free)
        last_ts = None
        try:
            with open(spot_path, 'rb') as f:
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                pos = max(0, pos - 200)
                f.seek(pos)
                chunk = f.read().decode('utf-8', errors='ignore')
                lines = [l for l in chunk.split('\n') if l.strip()]
                if lines:
                    last_line = lines[-1]
                    parts = last_line.split(',')
                    last_ts = safe_to_datetime(parts[0])
        except Exception:
            pass

        # Fallback to pandas if seek failed
        if last_ts is None:
            df_tail = pd.read_csv(spot_path).tail(5)
            if df_tail.empty:
                return
            col_name = 'timestamp' if 'timestamp' in df_tail.columns else ('start_time' if 'start_time' in df_tail.columns else df_tail.columns[0])
            last_ts = safe_to_datetime(df_tail[col_name].iloc[-1])
        
        # Check if the file is already up to date
        now_ist = datetime.now()
        
        try:
            from backtest_engine import NSE_HOLIDAYS
        except ImportError:
            NSE_HOLIDAYS = set()

        def get_last_trading_date(ref_date, nse_holidays):
            check_date = ref_date
            while True:
                if check_date.weekday() < 5 and check_date.strftime("%Y-%m-%d") not in nse_holidays:
                    return check_date
                check_date -= timedelta(days=1)

        is_up_to_date = False
        if now_ist - last_ts < timedelta(minutes=10):
            is_up_to_date = True
        else:
            is_weekday = now_ist.weekday() < 5
            is_holiday = now_ist.strftime("%Y-%m-%d") in NSE_HOLIDAYS
            is_trading_day = is_weekday and not is_holiday
            
            # Closing time is 15:15 starting August 3, 2026
            closing_time_str = "15:15" if now_ist.date() >= datetime.strptime("2026-08-03", "%Y-%m-%d").date() else "15:30"
            if is_trading_day and now_ist.time() >= datetime.strptime(closing_time_str, "%H:%M").time():
                # Market closed today. We need today's close.
                target_date = now_ist.date()
            else:
                # Weekend, holiday, or before market close today. We need the previous trading day's close.
                target_date = get_last_trading_date(now_ist.date() - timedelta(days=1), NSE_HOLIDAYS)
                
            # If target_date is on/after August 3, 2026, session ends at 15:15 (last candle 15:14).
            # Otherwise, session ends at 15:30 (last candle 15:29).
            if target_date >= datetime.strptime("2026-08-03", "%Y-%m-%d").date():
                has_enough_candles = (last_ts.hour == 15 and last_ts.minute >= 14) or (last_ts.hour > 15)
            else:
                has_enough_candles = (last_ts.hour == 15 and last_ts.minute >= 29)
                
            if last_ts.date() == target_date and has_enough_candles:
                is_up_to_date = True

        if is_up_to_date:
            return  # Already up to date

        start_date = last_ts.replace(hour=9, minute=15, second=0)
        end_date = now_ist
        
        if start_date >= end_date:
            return

        sec_id = str(inst_config['security_id'])
        inst_type = inst_config.get('type', 'INDEX')
        exch_seg = inst_config.get('exchange_segment', 'IDX_I')
        
        if inst_type == "OPTION":
            hist_inst = 'OPTIDX' if symbol.upper() in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY'] else 'OPTSTK'
        else:
            hist_inst = "INDEX" if inst_type == "INDEX" else "EQUITY"
            
        headers = {
            "access-token": api_token,
            "client-id": client_id,
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
            
            for attempt in range(3):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
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
                                df['timestamp'] = safe_to_datetime(df['start_time'])
                                df.set_index('timestamp', inplace=True)
                                
                            cols = ['open', 'high', 'low', 'close', 'volume']
                            cols = [c for c in cols if c in df.columns]
                            all_dfs.append(df[cols])
                        break
                    elif response.status_code == 429:
                        import random
                        time.sleep(2 + random.random() * 2)
                except:
                    pass
                time.sleep(0.5)
            current = next_m
            
        if all_dfs:
            df_new = pd.concat(all_dfs)
            df_new = df_new[~df_new.index.duplicated(keep='first')]
            
            df_existing = pd.read_csv(spot_path)
            col_name = 'timestamp' if 'timestamp' in df_existing.columns else ('start_time' if 'start_time' in df_existing.columns else df_existing.columns[0])
            df_existing[col_name] = safe_to_datetime(df_existing[col_name])
            df_existing.set_index(col_name, inplace=True)
            
            df_combined = pd.concat([df_existing, df_new])
            df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
            df_combined = df_combined.sort_index()
            
            df_combined.reset_index(inplace=True)
            df_combined.rename(columns={col_name: 'timestamp'}, inplace=True)
            df_combined.to_csv(spot_path, index=False)
            print(f"[AUTO-UPDATE] Updated {symbol} spot data to latest. Total candles: {len(df_combined)}")
    except Exception as e:
        print(f"[WARNING] Failed to auto-update spot data for {symbol}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate Stock Selection Recommendations for Tomorrow")
    parser.add_argument("--target", "-t", choices=["direction", "gap", "volatility", "strategy"], default="volatility", help="Target variable models to evaluate")
    parser.add_argument("--no-update", action="store_true", help="Bypass updating spot files from Dhan API")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of top stocks to recommend for selection")
    parser.add_argument("--rotate", action="store_true", help="Automatically rotate and enable the top-K selections inside instruments.json")
    args = parser.parse_args()

    # 1. Load scorecard details
    scorecard_path = os.path.join(BASE_DIR, "stock_selection", f"scorecard_{args.target}.json")
    if not os.path.exists(scorecard_path):
        print(f"[ERROR] Scorecard scorecard_{args.target}.json not found. Run train.py first.")
        return

    with open(scorecard_path, "r", encoding="utf-8") as f:
        scorecard = json.load(f)

    # 2. Check for Global Pooled Model first
    global_model_path = os.path.join(MODEL_DIR, f"global_pooled_model_{args.target}.pkl")
    use_pooled = os.path.exists(global_model_path)
    
    import joblib
    
    if use_pooled:
        print("[INFO] Global Pooled Model found. Using pooled inference for all symbols.")
        global_model_pkg = joblib.load(global_model_path)
        active_symbols = [sym for sym in scorecard if sym != "GLOBAL_POOLED" and scorecard[sym].get("status") == "trained"]
        if not active_symbols:
            # Fallback: get all symbols in data/
            feature_files = glob.glob(os.path.join(BASE_DIR, "stock_selection", "data", "*_features.csv"))
            active_symbols = [os.path.basename(f).replace("_features.csv", "").upper() for f in feature_files]
    else:
        model_pattern = os.path.join(MODEL_DIR, f"*_best_model_{args.target}.pkl")
        model_files = glob.glob(model_pattern)
        if not model_files:
            print(f"[ERROR] No trained models found in: {MODEL_DIR} for target {args.target}. Run train.py first.")
            return
        active_symbols = []
        for mf in model_files:
            symbol = os.path.basename(mf).replace(f"_best_model_{args.target}.pkl", "").upper()
            if symbol in scorecard and scorecard[symbol].get("status") == "trained":
                active_symbols.append(symbol)

    # Load API credentials from .env to auto-update files if stale
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
    client_id = os.getenv("DHAN_CLIENT_ID", "").strip().strip("'").strip('"')
    api_token = os.getenv("DHAN_API_TOKEN", "").strip().strip("'").strip('"')
    
    if client_id and api_token and not args.no_update:
        # Always update NIFTY first synchronously to prevent read/write conflicts
        print("[INFO] Dhan API credentials found. Checking and updating NIFTY spot file first...")
        update_spot_file_if_stale("NIFTY", client_id, api_token)

        if active_symbols:
            print(f"[INFO] Checking and updating spot files for {len(active_symbols)} symbols in parallel...")
            pool = ThreadPool(10)
            pool.map(lambda sym: update_spot_file_if_stale(sym, client_id, api_token), active_symbols)
            pool.close()
            pool.join()
            print("[INFO] Spot files check and update complete.\n")

    # Precompute NIFTY features from nifty_spot.csv
    nifty_features = precompute_nifty_features()

    predictions = []
    run_date = None

    for symbol in active_symbols:
        # Extract features for the latest date
        features, last_date_obj = extract_features_for_last_day(symbol, nifty_features)
        if features is None:
            # Skip with warning if last day features couldn't be derived
            continue

        last_date_str = last_date_obj.strftime("%Y-%m-%d")
        if run_date is None:
            run_date = last_date_str
            
        try:
            if use_pooled:
                selected_features = global_model_pkg["features"]
                X_pred = pd.DataFrame([features])[selected_features]
                probs = global_model_pkg["model"].predict_proba(X_pred)[0]
                prob_positive = probs[1] if len(probs) > 1 else probs[0]
                
                best_model_type = global_model_pkg.get("best_model_type", "xgboost")
                opt_thresh = global_model_pkg.get("opt_threshold", 0.5)
                test_precision = global_model_pkg.get("test_precision", 0.5)
                # Selection score is just the raw probability percentage since it's a single global model
                selection_score = prob_positive * 100
            else:
                mf = os.path.join(MODEL_DIR, f"{symbol.lower()}_best_model_{args.target}.pkl")
                model_pkg = joblib.load(mf)
                
                if isinstance(model_pkg, dict):
                    selected_features = model_pkg["features"]
                    X_pred = pd.DataFrame([features])[selected_features]
                    
                    # Check if this is the updated single final model package
                    if "model" in model_pkg:
                        probs = model_pkg["model"].predict_proba(X_pred)[0]
                        prob_positive = probs[1] if len(probs) > 1 else probs[0]
                    else: # Legacy ensemble fallback
                        prob_list = []
                        for m in model_pkg["models"]:
                            probs = m.predict_proba(X_pred)[0]
                            p_pos = probs[1] if len(probs) > 1 else probs[0]
                            prob_list.append(p_pos)
                        prob_positive = np.mean(prob_list)
                    
                    best_model_type = model_pkg.get("best_model_type", scorecard[symbol]["best_model"])
                    opt_thresh = model_pkg.get("opt_threshold", 0.5)
                    test_precision = model_pkg.get("test_precision", scorecard[symbol]["metrics"]["precision"])
                else:
                    # Legacy model instance fallback
                    X_pred = pd.DataFrame([features])[FEATURE_NAMES]
                    probs = model_pkg.predict_proba(X_pred)[0]
                    prob_positive = probs[1] if len(probs) > 1 else probs[0]
                    best_model_type = scorecard[symbol]["best_model"]
                    opt_thresh = scorecard[symbol].get("opt_threshold", 0.5)
                    test_precision = scorecard[symbol]["metrics"]["precision"]
                
                # Selection score is probability relative to threshold
                selection_score = (prob_positive - opt_thresh) * 100

            predictions.append({
                "Symbol": symbol,
                "Probability (%)": round(prob_positive * 100, 1),
                "Selection Score (%)": round(selection_score, 1),
                "Model Type": best_model_type,
                "Test Precision": test_precision,
                "Verdict": "AVOID"
            })
        except Exception as e:
            print(f"[WARNING] Failed to run prediction model for {symbol}: {e}")

    if not predictions:
        print("[ERROR] No predictions could be generated. Check model serializations and spot files.")
        return

    # Sort predictions by selection score descending
    df_preds = pd.DataFrame(predictions)
    df_preds = df_preds.sort_values(by="Selection Score (%)", ascending=False).reset_index(drop=True)
    
    # Apply Top-K ranking verdict
    top_k = int(args.top_k)
    for idx in range(len(df_preds)):
        prob = df_preds.loc[idx, "Probability (%)"]
        score = df_preds.loc[idx, "Selection Score (%)"]
        
        # Safe selection condition: must be in top_k AND (prob >= 35.0 or selection score >= 0.0)
        if idx < top_k and (prob >= 35.0 or (not use_pooled and score >= 0.0)):
            df_preds.loc[idx, "Verdict"] = "SELECT (TOP K)"
        else:
            df_preds.loc[idx, "Verdict"] = "AVOID"

    print("\n" + "=" * 110)
    print(f"               DAILY STOCK SELECTION RECOMMENDATIONS FOR TOMORROW              ")
    print(f"               Reference Trading Date: {run_date} | Target: {args.target.upper()}")
    print("=" * 110)
    print(f"  {'Rank':<5} | {'Symbol':<12} | {'Probability':<12} | {'Selection Score':<16} | {'Test Precision':<15} | {'Model Type':<14} | {'Verdict':<18}")
    print("-" * 110)
    
    for idx, row in df_preds.iterrows():
        rank = idx + 1
        prob_str = f"{float(row['Probability (%)']):.1f}%"
        score_val = float(row['Selection Score (%)'])
        score_str = f"{score_val:+.1f}%" if not use_pooled else f"{score_val:.1f}% (Pooled)"
        prec_str = f"{row['Test Precision']:.3f}"
        print(f"  {rank:<5} | {row['Symbol']:<12} | {prob_str:<12} | {score_str:<16} | {prec_str:<15} | {row['Model Type']:<14} | {row['Verdict']:<18}")

    print("=" * 110)
    
    # Save predictions to CSV
    save_filename = f"predictions_{args.target}_{run_date}.csv"
    save_path = os.path.join(PRED_DIR, save_filename)
    df_preds.to_csv(save_path, index=False)
    print(f"[SUCCESS] Selection recommendations saved to: {save_path}\n")
    
    # 4. Automate Stock Rotation if requested
    rotation_status = "Rotation not requested (run with --rotate to update instruments.json)"
    activated = []
    deactivated = []
    
    if args.rotate:
        print("[ROTATE] Automating stock rotation based on Top-K predicted selections...")
        
        # Identify top selections
        top_selections = set(df_preds[df_preds["Verdict"] == "SELECT (TOP K)"]["Symbol"].tolist())
        evaluated_symbols = set(active_symbols)
        
        instruments_path = os.path.join(BASE_DIR, "instruments.json")
        if os.path.exists(instruments_path):
            try:
                with open(instruments_path, "r", encoding="utf-8") as f:
                    instruments = json.load(f)
                
                activated = []
                deactivated = []
                
                for symbol in instruments:
                    if symbol in evaluated_symbols:
                        if symbol in top_selections:
                            if instruments[symbol].get("enabled", 0) != 1:
                                instruments[symbol]["enabled"] = 1
                                activated.append(symbol)
                        else:
                            if instruments[symbol].get("enabled", 0) != 0:
                                instruments[symbol]["enabled"] = 0
                                deactivated.append(symbol)
                
                # Write back to instruments.json
                with open(instruments_path, "w", encoding="utf-8") as f:
                    json.dump(instruments, f, indent=4)
                    
                print(f"[SUCCESS] instruments.json updated successfully!")
                print(f"  * Activated:   {activated if activated else 'None'}")
                print(f"  * Deactivated: {deactivated if deactivated else 'None'}")
                rotation_status = f"Successfully rotated instruments.json!\n• Activated: {', '.join(activated) if activated else 'None'}\n• Deactivated: {len(deactivated)} symbols"
            except Exception as e:
                print(f"[ERROR] Failed to update instruments.json: {e}")
                rotation_status = f"Rotation failed: {e}"
        else:
            print(f"[ERROR] instruments.json not found at {instruments_path}")
            rotation_status = "Rotation failed: instruments.json not found"

    # 5. Send Telegram/Slack Alert Notification
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        print("[ALERT] Sending daily recommendations alert...")
        try:
            import logging
            from trading_bot.alerts import AlertManager
            
            # Setup localized logging
            logger = logging.getLogger("StockSelector")
            
            source_ip = os.getenv("DHAN_SOURCE_IP")
            if not source_ip or source_ip.strip() == "" or source_ip.strip().startswith("#"):
                source_ip = None
                
            alert_mgr = AlertManager(webhook_url=webhook_url, logger=logger, source_ip=source_ip)
            
            # Construct message
            top_k_rows = df_preds[df_preds["Verdict"] == "SELECT (TOP K)"]
            rec_lines = []
            for rank_idx, (_, row) in enumerate(top_k_rows.iterrows()):
                rec_lines.append(f"{rank_idx+1}. {row['Symbol']} - {row['Probability (%)']:.1f}%")
                
            message = (
                f"Reference Date: {run_date}\n"
                f"Target: {args.target.upper()}\n\n"
                f"🎯 *Top Recommendations:*\n"
                + "\n".join(rec_lines) + "\n\n"
                f"🔄 *Rotation Status:*\n"
                f"{rotation_status}"
            )
            
            alert_mgr.send_alert(message=message, header="ML Stock Selection Complete")
            print("[SUCCESS] Alert notification sent via AlertManager!")
        except Exception as e:
            print(f"[WARNING] Failed to send alert notification: {e}")
    else:
        print("[ALERT] ALERT_WEBHOOK_URL not configured. Skipping alert notification.")

if __name__ == "__main__":
    main()
