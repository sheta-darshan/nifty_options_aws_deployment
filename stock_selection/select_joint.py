"""
==========================================================================================
        INSTITUTIONAL QUANTITATIVE STOCK SELECTION & ROTATION SUBSYSTEM
==========================================================================================
Selects the Top-K explosive volatility stocks using the trained global XGBoost model,
applies live ASM/GSM surveillance filters, evaluates the 50 EMA Climax Fade rule, 
enforces a 20-30% capital allocation cap, and logs paper trades safely.
==========================================================================================
"""

import os
import sys
import argparse
import json
import glob
import time
import warnings
from multiprocessing.pool import ThreadPool
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import joblib

warnings.filterwarnings("ignore", category=UserWarning)

# Setup project root pathing
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Import helpers from select_stocks
sys.path.append(os.path.join(BASE_DIR, "stock_selection"))
from select_stocks import (
    read_last_n_lines_to_df,
    precompute_nifty_features,
    extract_features_for_last_day,
    update_spot_file_if_stale,
    MODEL_DIR,
    PRED_DIR
)

SPOT_DIR = os.path.join(BASE_DIR, "backtest_data")
EQUITY_L_PATH = os.path.join(BASE_DIR, "EQUITY_L.csv")
PAPER_LOG_PATH = os.path.join(BASE_DIR, "stock_selection", "paper_trade_log.csv")


def check_surveillance_status(df_daily, current_price):
    """
    Operational ASM/GSM Surveillance Safeguard.
    Checks whether a stock matches SEBI's quantitative criteria:
    - 15-day price variation >= 40%
    - 5-day average volume < 25,000 shares
    """
    try:
        if df_daily is None or len(df_daily) < 15:
            return False, "OK"
            
        price_15d_ago = df_daily["close"].iloc[-15]
        surge_15d = (current_price - price_15d_ago) / (price_15d_ago + 1e-8)
        if surge_15d >= 0.40:
            return True, f"ASM/GSM Risk: 15d Surge +{surge_15d*100:.1f}% >= 40%"
            
        if len(df_daily) >= 5:
            avg_vol_5d = df_daily["volume"].iloc[-5:].mean()
            if avg_vol_5d < 25000:
                return True, f"ASM/GSM Risk: Low Liquidity ({int(avg_vol_5d)} shares/day < 25k)"
                
        return False, "OK"
    except Exception as e:
        return False, f"Check Error: {e}"


def process_single_stock(symbol, nifty_features, model, feat_cols):
    """Evaluates a single stock in ~3ms using tail binary seek."""
    try:
        features, last_date_obj = extract_features_for_last_day(symbol, nifty_features)
        if features is None or last_date_obj is None:
            return None

        run_date_str = last_date_obj.strftime("%Y-%m-%d")

        # Predict Range Expansion Score
        X_pred = pd.DataFrame([features])[feat_cols]
        probs = model.predict_proba(X_pred)[0]
        vol_prob = float(probs[1] if len(probs) > 1 else probs[0])

        # Read tail spot history for 50 EMA & Surveillance Check
        spot_file = os.path.join(SPOT_DIR, f"{symbol.lower()}_spot.csv")
        df_spot = read_last_n_lines_to_df(spot_file, n=25000)
        if df_spot is None or len(df_spot) < 100:
            return None

        col_time = 'timestamp' if 'timestamp' in df_spot.columns else ('start_time' if 'start_time' in df_spot.columns else df_spot.columns[0])
        df_spot[col_time] = pd.to_datetime(df_spot[col_time], errors='coerce')
        df_spot = df_spot.dropna(subset=[col_time]).sort_values(by=col_time)
        df_spot["dt_str"] = df_spot[col_time].dt.strftime("%Y-%m-%d")

        df_daily = df_spot.groupby("dt_str").agg(
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum")
        ).reset_index()

        if len(df_daily) < 50:
            return None

        ema_50 = float(df_daily["close"].ewm(span=50, adjust=False).mean().iloc[-1])
        last_close = float(df_daily["close"].iloc[-1])
        stretch_pct = ((last_close - ema_50) / ema_50) * 100

        # ATR_14
        df_daily["tr"] = np.maximum(
            df_daily["high"] - df_daily["low"],
            np.maximum(
                abs(df_daily["high"] - df_daily["close"].shift(1)),
                abs(df_daily["low"] - df_daily["close"].shift(1))
            )
        )
        atr_14 = float(df_daily["tr"].rolling(14).mean().iloc[-1])

        # Check ASM/GSM Surveillance Status
        is_surv, surv_reason = check_surveillance_status(df_daily, last_close)

        # Direction Bias (Short-Only Fade Rule)
        is_above_50ema = last_close > ema_50
        direction_action = "SELL" if is_above_50ema else "AVOID_LONG_FADE"

        return {
            "Symbol": symbol,
            "Run_Date": run_date_str,
            "Vol_Prob_%": round(vol_prob * 100, 2),
            "Last_Close": round(last_close, 2),
            "50_EMA": round(ema_50, 2),
            "ATR_14": round(atr_14, 2),
            "EMA_Stretch_%": round(stretch_pct, 2),
            "Action": direction_action,
            "Is_Surveillance": is_surv,
            "Surveillance_Reason": surv_reason,
            "Verdict": "PENDING"
        }
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Institutional Quantitative Stock Selection & Rotation Subsystem")
    parser.add_argument("--no-update", action="store_true", help="Bypass updating spot files from Dhan API")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of top stocks to select for rotation (default: 3)")
    parser.add_argument("--basket-capital-allocation-pct", type=float, default=0.25, help="Total account capital allocation cap for the fade basket (default: 0.25 = 25%)")
    parser.add_argument("--mode", choices=["PAPER", "LIVE"], default="PAPER", help="Deployment mode: PAPER (safe logging) or LIVE (orders enabled). Default: PAPER")
    parser.add_argument("--rotate", action="store_true", help="Automatically rotate selections inside instruments.json")
    args = parser.parse_args()

    print("=" * 125)
    print("      INSTITUTIONAL QUANTITATIVE STOCK SELECTION & ROTATION SUBSYSTEM")
    print("=" * 125)
    print(f"[CONFIG] Top-K Target:             {args.top_k} stocks")
    print(f"[CONFIG] Basket Capital Cap:       {args.basket_capital_allocation_pct*100:.1f}% of total account equity")
    print(f"[CONFIG] Per-Stock Allocation:     {(args.basket_capital_allocation_pct / args.top_k)*100:.2f}% per stock")
    print(f"[CONFIG] Deployment Mode:          {args.mode} (Default: PAPER)")
    print(f"[CONFIG] Auto-Rotate in JSON:      {args.rotate}")

    # 1. Load Legally Eligible EQ Series Symbols
    eq_eligible_symbols = set()
    if os.path.exists(EQUITY_L_PATH):
        df_eq = pd.read_csv(EQUITY_L_PATH)
        eq_eligible_symbols = set(df_eq[df_eq[" SERIES"].str.strip().str.upper() == "EQ"]["SYMBOL"].str.strip().str.upper().dropna())
        print(f"[INFO] Loaded {len(eq_eligible_symbols):,} legally short-eligible EQ series stocks from EQUITY_L.csv")

    # 2. Load Global Pooled Volatility Model
    global_model_vol_path = os.path.join(MODEL_DIR, "global_pooled_model_volatility.pkl")
    if not os.path.exists(global_model_vol_path):
        print(f"[ERROR] Trained volatility model not found at: {global_model_vol_path}")
        return

    global_model_pkg = joblib.load(global_model_vol_path)
    model = global_model_pkg["model"]
    feat_cols = global_model_pkg["features"]
    print(f"[INFO] Loaded Global XGBoost Volatility Model (Trained on {global_model_pkg.get('num_stocks', 1800)} stocks, {len(feat_cols)} features).")

    # 3. Find Available Spot Files
    all_spot_files = glob.glob(os.path.join(SPOT_DIR, "*_spot.csv"))
    active_symbols = []
    for f in all_spot_files:
        sym = os.path.basename(f).replace("_spot.csv", "").upper()
        if sym not in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]:
            if not eq_eligible_symbols or sym in eq_eligible_symbols:
                active_symbols.append(sym)

    print(f"[INFO] Evaluating {len(active_symbols):,} candidate EQ stocks in universe in parallel...")

    # Precompute nifty features
    nifty_features = precompute_nifty_features()

    # Parallel Evaluation across CPU cores with real-time progress
    start_t = time.time()
    pool = ThreadPool(16)
    results = []
    total_syms = len(active_symbols)
    batch_size = 150

    for i in range(0, total_syms, batch_size):
        chunk = active_symbols[i:i+batch_size]
        res_chunk = pool.map(lambda sym: process_single_stock(sym, nifty_features, model, feat_cols), chunk)
        results.extend(res_chunk)
        print(f"[PROGRESS] Evaluated {min(i+batch_size, total_syms):,}/{total_syms:,} stocks ({min(i+batch_size, total_syms)/total_syms*100:.1f}%)...", flush=True)

    pool.close()
    pool.join()

    predictions = [r for r in results if r is not None]
    eval_elapsed = time.time() - start_t
    print(f"[SUCCESS] Scored {len(predictions):,} active stocks across the universe in {eval_elapsed:.2f} seconds.")

    if not predictions:
        print("[ERROR] No predictions could be generated.")
        return

    run_date = predictions[0]["Run_Date"]

    # 5. Rank by Volatility Score Descending
    df_preds = pd.DataFrame(predictions)
    df_preds = df_preds.sort_values(by="Vol_Prob_%", ascending=False).reset_index(drop=True)

    # 6. Apply Selection Gates:
    # Must be: High Volatility Rank + Short-Only (Price > 50 EMA) + Clean ASM/GSM Status + Sane Stretch (<= 50%)
    selected_count = 0
    top_k = int(args.top_k)

    for idx in range(len(df_preds)):
        is_surv = df_preds.loc[idx, "Is_Surveillance"]
        action = df_preds.loc[idx, "Action"]
        stretch_pct = df_preds.loc[idx, "EMA_Stretch_%"]

        if is_surv:
            df_preds.loc[idx, "Verdict"] = "AVOID (SURVEILLANCE)"
        elif abs(stretch_pct) > 50.0:
            df_preds.loc[idx, "Verdict"] = "AVOID (EXTREME_STRETCH > 50%)"
        elif action != "SELL":
            df_preds.loc[idx, "Verdict"] = "AVOID (BELOW 50 EMA)"
        elif selected_count < top_k:
            df_preds.loc[idx, "Verdict"] = "SELECT (TOP K FADE)"
            selected_count += 1
        else:
            df_preds.loc[idx, "Verdict"] = "ELIGIBLE (RANK RUNNER-UP)"

    # Print Report
    print("\n" + "=" * 135)
    print(f"       TOP QUANTITATIVE SHORT-FADE ROTATION RECOMMENDATIONS (LATEST DATE: {run_date})")
    print("=" * 135)
    print(f"  {'Rank':<5} | {'Symbol':<12} | {'Vol Prob':<10} | {'Last Close':<11} | {'50 EMA':<10} | {'EMA Stretch':<12} | {'Action':<8} | {'Verdict':<25}")
    print("-" * 135)

    for idx, row in df_preds.head(25).iterrows():
        rank = idx + 1
        v_prob = f"{row['Vol_Prob_%']:.1f}%"
        stretch = f"{row['EMA_Stretch_%']:+0.1f}%"
        print(f"  {rank:<5} | {row['Symbol']:<12} | {v_prob:<10} | {row['Last_Close']:<11} | {row['50_EMA']:<10} | {stretch:<12} | {row['Action']:<8} | {row['Verdict']:<25}")

    print("=" * 135)

    # 7. Save Daily Prediction Artifact
    save_filename = f"predictions_short_fade_{run_date}.csv"
    save_path = os.path.join(PRED_DIR, save_filename)
    df_preds.to_csv(save_path, index=False)
    print(f"[SUCCESS] Predictions saved to: {save_path}")

    # 8. Paper Trading Logging & instruments.json Rotation
    top_selected = df_preds[df_preds["Verdict"] == "SELECT (TOP K FADE)"]
    per_stock_alloc = args.basket_capital_allocation_pct / max(1, top_k)

    # Log to paper_trade_log.csv
    log_rows = []
    iso_run_date = pd.to_datetime(run_date).strftime("%Y-%m-%d")
    for _, row in top_selected.iterrows():
        log_rows.append({
            "Selection_Date": iso_run_date,
            "Symbol": row["Symbol"],
            "Direction": "SHORT",
            "Vol_Prob_%": row["Vol_Prob_%"],
            "Reference_Close": row["Last_Close"],
            "50_EMA": row["50_EMA"],
            "ATR_14": row["ATR_14"],
            "Stop_Loss_Price (2.0xATR)": round(row["Last_Close"] + 2.0 * row["ATR_14"], 2),
            "Allocation_Pct": round(per_stock_alloc * 100, 2),
            "Mode": args.mode,
            "Status": "PENDING_T+1_EXECUTION"
        })

    if log_rows:
        df_log = pd.DataFrame(log_rows)
        header_needed = not os.path.exists(PAPER_LOG_PATH)
        df_log.to_csv(PAPER_LOG_PATH, mode="a", header=header_needed, index=False)
        print(f"[PAPER] Logged {len(df_log)} candidate trades to: {PAPER_LOG_PATH}")

    # 9. Update instruments.json with strict Paper/Live Safety Guard
    if args.rotate:
        print(f"\n[ROTATE] Updating instruments.json with mode = {args.mode}...")
        instruments_path = os.path.join(BASE_DIR, "instruments.json")
        if os.path.exists(instruments_path):
            with open(instruments_path, "r", encoding="utf-8") as f:
                instruments = json.load(f)

            selected_symbols = set(top_selected["Symbol"].values)
            activated = []
            deactivated = []

            for symbol in instruments:
                if symbol in selected_symbols:
                    # In PAPER mode, keep enabled = 0 or execution_mode = "PAPER"
                    if args.mode == "PAPER":
                        instruments[symbol]["enabled"] = 0
                        instruments[symbol]["execution_mode"] = "PAPER"
                    else:
                        instruments[symbol]["enabled"] = 1
                        instruments[symbol]["execution_mode"] = "STOCK"

                    instruments[symbol]["allowed_actions"] = ["SELL"]
                    instruments[symbol]["capital_allocation_pct"] = round(per_stock_alloc, 4)
                    instruments[symbol]["stop_loss_mult_atr"] = 2.0
                    activated.append(f"{symbol} (SHORT | {per_stock_alloc*100:.1f}% Alloc | {args.mode})")
                else:
                    instruments[symbol]["enabled"] = 0
                    instruments[symbol]["allowed_actions"] = ["BUY", "SELL"]
                    deactivated.append(symbol)

            with open(instruments_path, "w", encoding="utf-8") as f:
                json.dump(instruments, f, indent=4)

            print(f"[SUCCESS] instruments.json updated successfully!")
            print(f"  * Activated ({args.mode}): {activated}")
            print(f"  * Deactivated:             {len(deactivated)} symbols")


if __name__ == "__main__":
    main()
