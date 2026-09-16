import os
import sys
import argparse
import csv
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time
from multiprocessing import Pool, cpu_count

# Setup project root pathing
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Import trading engine components
try:
    from backtest_engine import SimulationEngine
    from strategies import BacktestConfig
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False

DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "stock_selection", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
        df = pd.read_csv(nifty_path)
        col_name = 'timestamp' if 'timestamp' in df.columns else ('start_time' if 'start_time' in df.columns else df.columns[0])
        df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
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

def process_single_stock(symbol, nifty_features=None):
    print(f"[PROCESS] Processing {symbol}...")
    spot_path = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
    if not os.path.exists(spot_path):
        if ENGINE_AVAILABLE:
            try:
                print(f"[DOWNLOAD] Spot file missing for {symbol}. Triggering Dhan API download...")
                config = BacktestConfig()
                engine = SimulationEngine(config, instrument_name=symbol)
                engine.backtest_days = 1825  # Look back 5 years
                engine.load_data()  # Will automatically download the spot file if not found
                print(f"[DOWNLOAD SUCCESS] Downloaded spot candles for {symbol} -> {spot_path}")
            except Exception as e:
                return f"Spot file not found and failed to download for {symbol}: {e}"
        else:
            return f"File not found: {spot_path} (API engine unavailable to download)"

    try:
        # 1. Read and clean spot data
        df = pd.read_csv(spot_path)
        col_name = 'timestamp' if 'timestamp' in df.columns else ('start_time' if 'start_time' in df.columns else df.columns[0])
        df[col_name] = pd.to_datetime(df[col_name], errors='coerce')
        df.set_index(col_name, inplace=True)
        df = df[df.index.notna()].sort_index()
        df.index = pd.DatetimeIndex(df.index)
        
        # Isolate regular market session and filter out zero/negative placeholder prices
        df = df.between_time('09:15', '15:30')
        df = df[(df['close'] > 0) & (df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0)]
        if df.empty or len(df) < 50:
            return f"{symbol}: No valid regular session candles found."

        # 2. Pre-calculate technical indicators on the full dataset
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

        # Fill NaNs
        df.ffill(inplace=True)
        df.dropna(subset=['rsi', 'ema_diff', 'atr'], inplace=True)

        # 3. Group by trading day and extract features + outcomes
        df_by_date = {d: grp for d, grp in df.groupby(df.index.date)}
        dates = sorted(list(df_by_date.keys()))
        
        # Calculate daily ranges and rolling daily ATR
        daily_highs = [df_by_date[d]['high'].max() for d in dates]
        daily_lows = [df_by_date[d]['low'].min() for d in dates]
        daily_closes = [df_by_date[d]['close'].iloc[-1] for d in dates]
        
        daily_tr = []
        for i, d in enumerate(dates):
            high_low = daily_highs[i] - daily_lows[i]
            if i == 0:
                daily_tr.append(high_low)
            else:
                prev_close = daily_closes[i - 1]
                high_pc = abs(daily_highs[i] - prev_close)
                low_pc = abs(daily_lows[i] - prev_close)
                daily_tr.append(max(high_low, high_pc, low_pc))
                
        daily_atr_series = pd.Series(daily_tr).rolling(14, min_periods=1).mean()
        daily_atr_dict = {dates[i]: daily_atr_series.iloc[i] for i in range(len(dates))}
        
        records = []

        for idx, d in enumerate(dates):
            # Check for next day validation outcomes
            if idx == len(dates) - 1:
                break
                
            day_df = df_by_date[d]
            next_day_df = df_by_date[dates[idx + 1]]

            # Extract the last 30 minutes of day T dynamically using centralized timing helper
            last_30_df = get_last_30m_window(day_df, d)
            if len(last_30_df) < MIN_WINDOW_CANDLES:
                continue  # Skip days with incomplete close data

            # Target variables on T+1
            curr_close = day_df['close'].iloc[-1]
            next_open = next_day_df['open'].iloc[0]
            next_high = next_day_df['high'].max()
            next_low = next_day_df['low'].min()
            next_close = next_day_df['close'].iloc[-1]

            # Label calculations
            target_direction = 1 if next_close > curr_close else 0
            target_gap = 1 if (abs(next_open - curr_close) / curr_close) > 0.008 else 0
            # Adaptive volatility: next day high-to-low range > 1.3 * current daily ATR
            current_atr = daily_atr_dict[d]
            target_volatility = 1 if (next_high - next_low) > (1.3 * current_atr) else 0
            # Strategy Target: Next-day intraday short fade profitability (Open T+1 - Close T+1 > +1.0%)
            target_strategy = 1 if ((next_open - next_close) / (next_open + 1e-8)) > 0.010 else 0

            # Last 30-min price slices
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
            
            # Daily return up to 15:00
            day_open_val = day_df['open'].iloc[0]
            ret_day = (l30_opens[0] - day_open_val) / (day_open_val + 1e-8)

            # Volatility
            vol_30m = np.std([np.log(l30_closes[i]/l30_closes[i-1]) for i in range(1, len(l30_closes))]) if len(l30_closes) > 1 else 0.0
            range_30m = (np.max(l30_highs) - np.min(l30_lows)) / (l30_closes[-1] + 1e-8)

            # Volume Metrics
            mean_vol_day = day_df['volume'].mean() + 1e-8
            mean_vol_30m = last_30_df['volume'].mean()
            vol_ratio = mean_vol_30m / mean_vol_day
            vol_ratio_5m = last_30_df['volume'].iloc[-5:].mean() / (mean_vol_30m + 1e-8)

            # Candle body counts
            green_count = sum(l30_closes > l30_opens)
            red_count = sum(l30_closes < l30_opens)

            # Close Location Value (CLV)
            clv_vals = ((last_30_df['close'] - last_30_df['low']) - (last_30_df['high'] - last_30_df['close'])) / (last_30_df['high'] - last_30_df['low'] + 1e-8)
            clv_mean = clv_vals.mean()
            clv_last = clv_vals.iloc[-1]

            # Wick ratios normalized by total candle height instead of body size
            candle_heights = l30_highs - l30_lows
            upper_wicks = np.where(l30_closes > l30_opens, l30_highs - l30_closes, l30_highs - l30_opens)
            lower_wicks = np.where(l30_closes > l30_opens, l30_opens - l30_lows, l30_closes - l30_lows)
            
            upper_wick_mean = np.mean(upper_wicks / (candle_heights + 1e-8))
            lower_wick_mean = np.mean(lower_wicks / (candle_heights + 1e-8))

            # Technical indicators at 15:29
            rsi_val = last_30_df['rsi'].iloc[-1]
            ema_diff_val = last_30_df['ema_diff'].iloc[-1]
            atr_val = last_30_df['atr'].iloc[-1] / (l30_closes[-1] + 1e-8)

            # Broader index context lookup
            nifty_ret_30m = 0.0
            nifty_rsi = 50.0
            if nifty_features and d in nifty_features:
                nifty_ret_30m = nifty_features[d]["nifty_ret_30m"]
                nifty_rsi = nifty_features[d]["nifty_rsi"]

            # Multi-day range compression calculations
            range_ratio_T = (daily_highs[idx] - daily_lows[idx]) / (current_atr + 1e-8)
            
            if idx >= 1:
                prev_atr_1 = daily_atr_dict[dates[idx - 1]]
                range_ratio_T_1 = (daily_highs[idx - 1] - daily_lows[idx - 1]) / (prev_atr_1 + 1e-8)
            else:
                range_ratio_T_1 = 1.0
                
            if idx >= 2:
                prev_atr_2 = daily_atr_dict[dates[idx - 2]]
                range_ratio_T_2 = (daily_highs[idx - 2] - daily_lows[idx - 2]) / (prev_atr_2 + 1e-8)
            else:
                range_ratio_T_2 = 1.0

            # Weekday and Overnight Gap Features
            weekday = float(d.weekday())
            curr_open = day_df['open'].iloc[0]
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

            rec = {
                "date": d.strftime("%Y-%m-%d"),
                "ret_30m": ret_30m,
                "ret_15m": ret_15m,
                "ret_10m": ret_10m,
                "ret_5m": ret_5m,
                "ret_day": ret_day,
                "vol_30m": vol_30m,
                "range_30m": range_30m,
                "vol_ratio": vol_ratio,
                "vol_ratio_5m": vol_ratio_5m,
                "green_count": green_count,
                "red_count": red_count,
                "clv_mean": clv_mean,
                "clv_last": clv_last,
                "upper_wick_mean": upper_wick_mean,
                "lower_wick_mean": lower_wick_mean,
                "rsi": rsi_val,
                "ema_diff": ema_diff_val,
                "atr": atr_val,
                "nifty_ret_30m": nifty_ret_30m,
                "nifty_rsi": nifty_rsi,
                "range_ratio_T": range_ratio_T,
                "range_ratio_T_1": range_ratio_T_1,
                "range_ratio_T_2": range_ratio_T_2,
                "weekday": weekday,
                "previous_gap": previous_gap
            }
            rec.update(seq_features)
            rec.update({
                "target_direction": target_direction,
                "target_gap": target_gap,
                "target_volatility": target_volatility,
                "target_strategy": target_strategy
            })
            records.append(rec)

        if not records:
            return f"{symbol}: No valid days processed."

        # Save output feature matrix
        out_df = pd.DataFrame(records)
        out_path = os.path.join(OUTPUT_DIR, f"{symbol.lower()}_features.csv")
        out_df.to_csv(out_path, index=False)
        return f"[SUCCESS] Processed {symbol} -> {len(out_df)} days saved."

    except Exception as e:
        import traceback
        return f"Error processing {symbol}: {e}\n{traceback.format_exc()}"

def process_wrapper(args):
    return process_single_stock(*args)

def main():
    parser = argparse.ArgumentParser(description="Multi-Stock Preprocessing and Feature Extraction")
    parser.add_argument("--symbols", nargs="*", help="List of stock symbols. If omitted, parses all files in backtest_data/ matching instruments_config.csv")
    parser.add_argument("--all", action="store_true", help="Process all available stock spot CSVs in backtest_data/")
    parser.add_argument("--all-liquid", action="store_true", help="Process all liquid qualified stocks (>=1yr history, >=25L turnover)")
    args = parser.parse_args()

    # Load targets from config, arguments, or directory scan
    audit_csv = os.path.join(BASE_DIR, "scratch", "universe_audit_results.csv")
    target_symbols = []
    
    if args.symbols:
        target_symbols = [s.upper() for s in args.symbols]
    elif args.all:
        import glob
        spot_files = glob.glob(os.path.join(DATA_DIR, "*_spot.csv"))
        for sp in spot_files:
            sym = os.path.basename(sp).replace("_spot.csv", "").upper()
            if sym not in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]:
                target_symbols.append(sym)
        target_symbols = sorted(target_symbols)
    elif args.all_liquid and os.path.exists(audit_csv):
        df_audit = pd.read_csv(audit_csv)
        valid_audit = df_audit[
            (df_audit["years_span"] >= 1.0) &
            (df_audit["avg_turnover"] >= 2500000) &
            (~df_audit["symbol"].isin(["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]))
        ]
        target_symbols = sorted(list(valid_audit["symbol"].unique()))
    else:
        config_path = os.path.join(BASE_DIR, "instruments_config.csv")
        all_symbols = []
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sym = row.get("Instrument", "").strip()
                    if sym:
                        all_symbols.append(sym)
        for sym in all_symbols:
            spot_path = os.path.join(DATA_DIR, f"{sym.lower()}_spot.csv")
            if os.path.exists(spot_path):
                target_symbols.append(sym)

    print(f"[INFO] Found {len(target_symbols)} symbols ready to preprocess.")

    if not target_symbols:
        print("[ERROR] No target symbols found. Check backtest_data/ for stock spot CSVs.")
        return

    # Precompute NIFTY market context index features once to avoid redundant reads
    nifty_features_dict = precompute_nifty_features()

    # Multiprocessing setup
    cores = min(cpu_count(), len(target_symbols))
    print(f"[INFO] Launching extraction with {cores} parallel processes...")

    tasks = [(sym, nifty_features_dict) for sym in target_symbols]
    
    with Pool(processes=cores) as pool:
        results = pool.map(process_wrapper, tasks)

    print("\n" + "=" * 50)
    print("                EXTRACTION REPORT                 ")
    print("=" * 50)
    for res in results:
        print(res)
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
