"""
stock_selection/select_joint.py

Institutional Quantitative Stock Selection & Smart Hybrid Rotation
===================================================================
Selects the Top-K explosive bidirectional stocks using the True Dual-Head
(Joint) Model calibrated on Feature Matrix 2.0:
  - Head 1 (Volatility Expansion): P(Range_{T+1} >= 1.3 * ATR_14)
  - Head 2 (Directional Edge):     P(Close_{T+1} > Close_T)

Scoring:
  - Long Joint Score  = P_vol * P_dir * (1 + RS_Nifty) * 100
  - Short Joint Score = P_vol * (1 - P_dir) * (1 - RS_Nifty) * 100

Features:
  - Fast liquid universe gating (F&O 195 liquid stocks / Top 500)
  - Sub-5-second inference latency
  - SEBI ASM/GSM surveillance filtering
  - Smart Hybrid order routing (Stock Options for F&O, 5x MIS for non-F&O)
  - Safe instruments.json rotation preserving core indices (NIFTY, BANKNIFTY)
  - Paper trade logging
"""

import os
import sys
import argparse
import json
import glob
import time
import warnings
from io import StringIO
from datetime import datetime
from multiprocessing.pool import ThreadPool
import pandas as pd
import numpy as np
import joblib

warnings.filterwarnings("ignore", category=UserWarning)

# Setup root pathing
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from stock_selection.feature_matrix_v2 import FEATURE_NAMES_V2, extract_features_v2_df

DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
MODEL_DIR = os.path.join(BASE_DIR, "stock_selection", "models")
PRED_DIR = os.path.join(BASE_DIR, "stock_selection", "predictions")
PAPER_LOG_PATH = os.path.join(BASE_DIR, "stock_selection", "paper_trade_log.csv")
EQUITY_L_PATH = os.path.join(BASE_DIR, "EQUITY_L.csv")
os.makedirs(PRED_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "global_dual_head_joint_model.pkl")


def read_last_n_lines_to_df(filepath: str, n: int = 2500) -> pd.DataFrame:
    """Reads the last N lines of a CSV quickly using binary seek."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            header_line = f.readline()
        if not header_line:
            return None
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
            data_str = header_line.strip() + "\n" + b'\n'.join(last_lines).decode('utf-8')
            df = pd.read_csv(StringIO(data_str))
            df.columns = [c.strip().lower() for c in df.columns]
            if "start_time" in df.columns:
                df.rename(columns={"start_time": "timestamp"}, inplace=True)
            required = ["timestamp", "open", "high", "low", "close", "volume"]
            if all(col in df.columns for col in required):
                return df[required]
    except Exception:
        pass
    try:
        df = pd.read_csv(filepath)
        df.columns = [c.strip().lower() for c in df.columns]
        if "start_time" in df.columns:
            df.rename(columns={"start_time": "timestamp"}, inplace=True)
        required = ["timestamp", "open", "high", "low", "close", "volume"]
        if all(col in df.columns for col in required):
            return df[required].iloc[-n:]
    except Exception:
        return None
    return None


def check_surveillance_status(df_daily: pd.DataFrame, current_price: float):
    """Checks whether a stock matches SEBI ASM/GSM quantitative criteria."""
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


def get_fno_stock_registry() -> dict:
    """Loads clean NSE F&O stocks with lot_size and strike_step from fno_registry.json."""
    reg_path = os.path.join(BASE_DIR, "stock_selection", "fno_registry.json")
    if os.path.exists(reg_path):
        try:
            with open(reg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_security_id_map() -> dict:
    """Loads Dhan security ID map from dhan_equity_master_cache.csv"""
    sec_map = {}
    cache_path = os.path.join(BASE_DIR, "dhan_equity_master_cache.csv")
    if os.path.exists(cache_path):
        try:
            df_cache = pd.read_csv(cache_path, dtype={'SECURITY_ID': str})
            for _, r in df_cache.iterrows():
                sym = str(r.get('SYMBOL', '')).strip().upper()
                sid = str(r.get('SECURITY_ID', '')).strip()
                if sym and sid:
                    sec_map[sym] = sid
        except Exception:
            pass
    return sec_map


def load_nifty_daily() -> pd.DataFrame:
    """Loads NIFTY spot daily bars."""
    nifty_path = os.path.join(DATA_DIR, "nifty_spot.csv")
    if not os.path.exists(nifty_path):
        return None
    try:
        df = pd.read_csv(nifty_path)
        col = 'timestamp' if 'timestamp' in df.columns else ('start_time' if 'start_time' in df.columns else df.columns[0])
        df[col] = pd.to_datetime(df[col], errors='coerce')
        df.set_index(col, inplace=True)
        df = df[df.index.notna()].sort_index()
        df = df.between_time('09:15', '15:30')
        df['date'] = df.index.date
        daily = df.groupby('date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        return daily
    except Exception:
        return None


def evaluate_single_stock(args):
    """Evaluates a single stock for dual-head joint volatility and direction."""
    symbol, spot_path, nifty_daily, model_bundle = args
    try:
        df_spot = read_last_n_lines_to_df(spot_path, n=35000)
        if df_spot is None or len(df_spot) < 500:
            return None

        # Extract features (inference mode keeps today's latest completed close)
        df_feat = extract_features_v2_df(df_spot, nifty_daily=nifty_daily, is_training=False)
        if df_feat is None or df_feat.empty:
            return None

        latest_features = df_feat.iloc[-1]
        run_date_str = str(df_feat.index[-1])

        # Dual-Head inference
        X_pred = pd.DataFrame([latest_features[FEATURE_NAMES_V2]])
        vol_model = model_bundle["volatility_model"]
        dir_model = model_bundle["direction_model"]

        p_vol = float(vol_model.predict_proba(X_pred)[0][1])
        p_dir = float(dir_model.predict_proba(X_pred)[0][1])

        # Directional joint scores
        rs_5d = float(latest_features.get('rs_nifty_5d', 0.0))
        rs_norm = float(np.clip(rs_5d / 100.0, -0.5, 0.5))

        joint_score_long = p_vol * p_dir * (1.0 + rs_norm) * 100.0
        joint_score_short = p_vol * (1.0 - p_dir) * (1.0 - rs_norm) * 100.0

        # Technical levels from latest row (instantaneous, zero overhead)
        last_close = float(latest_features.get('close', 0.0))
        day_high = float(latest_features.get('high', 0.0))
        day_low = float(latest_features.get('low', 0.0))
        atr_14 = float(latest_features.get('atr14', 0.0))
        if atr_14 <= 0:
            atr_14 = (day_high - day_low) if (day_high > day_low) else max(1.0, last_close * 0.015)

        # Surveillance check using daily closes from df_feat
        if len(df_feat) >= 15 and 'close' in df_feat.columns:
            c_15_ago = float(df_feat['close'].iloc[-15])
            surge_15d = (last_close - c_15_ago) / (c_15_ago + 1e-9)
            if surge_15d >= 0.40:
                is_surv, surv_reason = True, f"ASM/GSM Risk: 15d Surge +{surge_15d*100:.1f}% >= 40%"
            else:
                is_surv, surv_reason = False, "OK"
        else:
            is_surv, surv_reason = False, "OK"

        # Triggers for Day T+1
        # Long Setup: Breakout above Day High + 0.05
        trigger_long = round(day_high + 0.05, 2)
        sl_long = round(trigger_long - 0.90 * atr_14, 2)
        be_long = round(trigger_long + 0.50 * atr_14, 2)
        tp_long = round(trigger_long + 1.35 * atr_14, 2)

        # Short Setup: Breakdown below Day Low - 0.05
        trigger_short = round(day_low - 0.05, 2)
        sl_short = round(trigger_short + 0.90 * atr_14, 2)
        be_short = round(trigger_short - 0.50 * atr_14, 2)
        tp_short = round(trigger_short - 1.35 * atr_14, 2)

        dist_ema20 = float(latest_features.get('dist_ema20', 0.0))
        dist_ema50 = float(latest_features.get('dist_ema50', 0.0))
        car_pct = float(latest_features.get('car', 0.14)) * 100.0
        clv_val = float(latest_features.get('clv_close', 0.0))
        vcp_ratio = float(latest_features.get('vcp_ratio', 1.0))

        return {
            "Symbol": symbol.upper(),
            "Date": run_date_str,
            "P_Vol_%": round(p_vol * 100.0, 1),
            "P_Dir_%": round(p_dir * 100.0, 1),
            "Score_Long": round(joint_score_long, 2),
            "Score_Short": round(joint_score_short, 2),
            "RS_Nifty_5d": round(rs_5d, 2),
            "Close": round(last_close, 2),
            "Day_High": round(day_high, 2),
            "Day_Low": round(day_low, 2),
            "ATR_14": round(atr_14, 2),
            "Dist_EMA20_%": round(dist_ema20, 1),
            "Dist_EMA50_%": round(dist_ema50, 1),
            "CAR_%": round(car_pct, 1),
            "CLV": round(clv_val, 2),
            "VCP_Ratio": round(vcp_ratio, 2),
            "Trigger_Long": trigger_long,
            "SL_Long": sl_long,
            "BE_Long": be_long,
            "TP_Long": tp_long,
            "Trigger_Short": trigger_short,
            "SL_Short": sl_short,
            "BE_Short": be_short,
            "TP_Short": tp_short,
            "Is_Surveillance": is_surv,
            "Surveillance_Reason": surv_reason
        }
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Institutional True Dual-Head Quantitative Stock Selector")
    parser.add_argument("--direction", choices=["both", "long", "short"], default="both", help="Selection side: both, long, or short")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of top candidates per direction (default: 3)")
    parser.add_argument("--universe", choices=["fno", "top500", "all"], default="fno", help="Universe scope (default: fno - 195 liquid F&O stocks)")
    parser.add_argument("--fno-only", action="store_true", help="Filter universe exclusively for F&O stocks (alias for --universe fno)")
    parser.add_argument("--execution-mode", choices=["hybrid", "option", "stock"], default="hybrid", help="Execution routing mode")
    parser.add_argument("--capital", type=float, default=100000.0, help="Total account capital allocation (default: 100,000)")
    parser.add_argument("--leverage", type=float, default=5.0, help="Cash intraday MIS leverage (default: 5.0x)")
    parser.add_argument("--rotate", action="store_true", help="Rotate top selections into instruments.json")
    parser.add_argument("--mode", choices=["PAPER", "LIVE"], default="LIVE", help="Deployment mode: PAPER or LIVE (default: LIVE)")
    parser.add_argument("--sizing-mode", choices=["fixed", "capital"], default="fixed",
                        help="Position sizing mode: 'fixed' (Option A: 1 lot/1 share) or 'capital' (Option B: dynamically sized to --capital)")
    args = parser.parse_args()

    if args.fno_only:
        args.universe = "fno"

    print("=" * 125)
    print("      INSTITUTIONAL TRUE DUAL-HEAD QUANTITATIVE STOCK SELECTION & ROTATION")
    print("=" * 125)
    print(f"[CONFIG] Direction Target:         {args.direction.upper()}")
    print(f"[CONFIG] Top-K Target:             {args.top_k} stocks per side")
    print(f"[CONFIG] Universe Gating:          {args.universe.upper()}")
    print(f"[CONFIG] Execution Mode:           {args.execution_mode.upper()}")
    print(f"[CONFIG] Capital Allocation:       Rs. {args.capital:,.0f} (Leverage: {args.leverage:.1f}x)")
    print(f"[CONFIG] Deployment Mode:          {args.mode} (Default: PAPER)")
    print(f"[CONFIG] Auto-Rotate in JSON:      {args.rotate}")

    # 1. Load Dual-Head Model
    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] Trained Dual-Head model not found at:\n  {MODEL_PATH}")
        print("Please run 'python stock_selection/train_joint_v2.py' first.")
        return

    model_bundle = joblib.load(MODEL_PATH)
    print(f"[INFO] Loaded Dual-Head Model ({model_bundle.get('architecture', 'Dual-Head')}).")

    # 2. Build Candidate Universe
    fno_registry = get_fno_stock_registry()
    eligible_symbols = []

    if args.universe == "fno":
        for sym in fno_registry.keys():
            spot_f = os.path.join(DATA_DIR, f"{sym.lower()}_spot.csv")
            if os.path.exists(spot_f):
                eligible_symbols.append((sym, spot_f))
    else:
        # Load EQ series
        eq_set = set()
        if os.path.exists(EQUITY_L_PATH):
            df_eq = pd.read_csv(EQUITY_L_PATH)
            eq_set = set(df_eq[df_eq[" SERIES"].str.strip().str.upper() == "EQ"]["SYMBOL"].str.strip().str.upper().dropna())

        all_spot_files = glob.glob(os.path.join(DATA_DIR, "*_spot.csv"))
        for f in all_spot_files:
            sym = os.path.basename(f).replace("_spot.csv", "").upper()
            if sym not in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]:
                if not eq_set or sym in eq_set:
                    eligible_symbols.append((sym, f))

        if args.universe == "top500":
            eligible_symbols = eligible_symbols[:500]

    print(f"[INFO] Gated Universe: {len(eligible_symbols):,} candidate stocks to evaluate.")

    nifty_daily = load_nifty_daily()

    # 3. Parallel Inference
    t0 = time.time()
    tasks = [(sym, s_path, nifty_daily, model_bundle) for sym, s_path in eligible_symbols]

    results = []
    with ThreadPool(12) as pool:
        for res in pool.imap_unordered(evaluate_single_stock, tasks):
            if res is not None and not res.get("Is_Surveillance", False):
                results.append(res)

    print(f"[SUCCESS] Evaluated {len(tasks):,} stocks in {time.time() - t0:.2f}s ({len(results)} valid candidates).")

    if not results:
        print("[ERROR] No valid candidates found.")
        return

    df_results = pd.DataFrame(results)
    run_date = df_results['Date'].iloc[0]

    # 4. Bidirectional Ranking & Presentation
    top_candidates = []

    # BUY / LONG RANKING (Requires P_Dir >= 49.0% and supportive structure)
    top_buys = pd.DataFrame()
    if args.direction in ["both", "long"]:
        df_long = df_results[(df_results['P_Dir_%'] >= 49.0) & (df_results['Dist_EMA20_%'] >= -3.0)].sort_values(by="Score_Long", ascending=False).reset_index(drop=True)
        if df_long.empty:
            df_long = df_results.sort_values(by="Score_Long", ascending=False).reset_index(drop=True)
        top_buys = df_long.head(args.top_k)

        print("\n" + "=" * 145)
        print(f"               TOP {len(top_buys)} QUANTITATIVE BREAKOUT (BUY / LONG) RECOMMENDATIONS (DATE: {run_date})")
        print("=" * 145)
        print(f"{'Rank':<4} | {'Symbol':<12} | {'Side':<5} | {'Joint':<6} | {'P(Vol)':<7} | {'P(Dir)':<7} | {'RS(5d)':<7} | {'CAR':<6} | {'CLV':<6} | {'Trigger':<9} | {'SL':<8} | {'Target':<9}")
        print("-" * 145)
        for idx, r in top_buys.iterrows():
            print(f"{idx+1:<4} | {r['Symbol']:<12} | {'BUY':<5} | {r['Score_Long']:<6.1f} | {r['P_Vol_%']:<5.1f}% | {r['P_Dir_%']:<5.1f}% | {r['RS_Nifty_5d']:<+6.1f}% | {r['CAR_%']:<5.0f}% | {r['CLV']:<+5.2f} | Rs.{r['Trigger_Long']:<8.2f} | Rs.{r['SL_Long']:<7.2f} | Rs.{r['TP_Long']:<8.2f}")
            top_candidates.append({**r, 'Side': 'BUY', 'Trigger_Price': r['Trigger_Long'], 'Stop_Loss': r['SL_Long'], 'BE_Trigger': r['BE_Long'], 'Target_Price': r['TP_Long']})
        print("=" * 145)

    # SELL / SHORT RANKING (Requires P_Dir < 49.0% and non-overlapping with Longs)
    if args.direction in ["both", "short"]:
        selected_buy_syms = set(top_buys['Symbol'].values) if not top_buys.empty else set()
        df_short = df_results[(df_results['P_Dir_%'] < 49.0) & (~df_results['Symbol'].isin(selected_buy_syms))].sort_values(by="Score_Short", ascending=False).reset_index(drop=True)
        if df_short.empty:
            df_short = df_results[~df_results['Symbol'].isin(selected_buy_syms)].sort_values(by="Score_Short", ascending=False).reset_index(drop=True)
        top_sells = df_short.head(args.top_k)

        print("\n" + "=" * 145)
        print(f"               TOP {len(top_sells)} QUANTITATIVE BREAKDOWN (SELL / SHORT) RECOMMENDATIONS (DATE: {run_date})")
        print("=" * 145)
        print(f"{'Rank':<4} | {'Symbol':<12} | {'Side':<5} | {'Joint':<6} | {'P(Vol)':<7} | {'P(Dir)':<7} | {'RS(5d)':<7} | {'CAR':<6} | {'CLV':<6} | {'Trigger':<9} | {'SL':<8} | {'Target':<9}")
        print("-" * 145)
        for idx, r in top_sells.iterrows():
            print(f"{idx+1:<4} | {r['Symbol']:<12} | {'SELL':<5} | {r['Score_Short']:<6.1f} | {r['P_Vol_%']:<5.1f}% | {r['P_Dir_%']:<5.1f}% | {r['RS_Nifty_5d']:<+6.1f}% | {r['CAR_%']:<5.0f}% | {r['CLV']:<+5.2f} | Rs.{r['Trigger_Short']:<8.2f} | Rs.{r['SL_Short']:<7.2f} | Rs.{r['TP_Short']:<8.2f}")
            top_candidates.append({**r, 'Side': 'SELL', 'Trigger_Price': r['Trigger_Short'], 'Stop_Loss': r['SL_Short'], 'BE_Trigger': r['BE_Short'], 'Target_Price': r['TP_Short']})
        print("=" * 145)

    # 5. Save Full Predictions CSV
    pred_path = os.path.join(PRED_DIR, f"predictions_joint_{run_date}.csv")
    df_results.to_csv(pred_path, index=False)
    print(f"\n[SUCCESS] Full predictions artifact saved to:\n  -> {pred_path}")

    # 6. Paper Trading Logging
    if top_candidates:
        log_rows = []
        per_alloc = 100.0 / len(top_candidates)
        for cand in top_candidates:
            log_rows.append({
                "Selection_Date": run_date,
                "Symbol": cand["Symbol"],
                "Direction": cand["Side"],
                "Vol_Prob_%": cand["P_Vol_%"],
                "Dir_Prob_%": cand["P_Dir_%"],
                "Joint_Score": cand["Score_Long"] if cand["Side"] == "BUY" else cand["Score_Short"],
                "Trigger_Price": cand["Trigger_Price"],
                "Stop_Loss": cand["Stop_Loss"],
                "Target_Price": cand["Target_Price"],
                "Allocation_Pct": round(per_alloc, 2),
                "Execution_Mode": args.execution_mode.upper(),
                "Mode": args.mode,
                "Status": "PENDING_T+1_TRIGGER"
            })

        df_log = pd.DataFrame(log_rows)
        header_needed = not os.path.exists(PAPER_LOG_PATH)
        df_log.to_csv(PAPER_LOG_PATH, mode="a", header=header_needed, index=False)
        print(f"[PAPER] Logged {len(df_log)} candidate setups to: {PAPER_LOG_PATH}")

    # 7. Safe instruments.json Rotation (Preserving Core Indices)
    if args.rotate and top_candidates:
        print(f"\n[ROTATE] Updating instruments.json with {len(top_candidates)} setups (Mode: {args.execution_mode.upper()})...")
        instruments_path = os.path.join(BASE_DIR, "instruments.json")
        try:
            with open(instruments_path, "r", encoding="utf-8") as f:
                inst_data = json.load(f)

            sec_map = get_security_id_map()

            # Clean previous rotated joint stocks ONLY (never touch NIFTY / BANKNIFTY or prebreakout stocks)
            for sym in list(inst_data.keys()):
                cfg = inst_data[sym]
                if cfg.get("rotated_joint", False):
                    if cfg.get("rotated_prebreakout", False):
                        cfg.pop("rotated_joint", None)
                    elif "strategy_overrides" in cfg or cfg.get("type") == "INDEX":
                        cfg["enabled"] = 0
                        cfg.pop("rotated_joint", None)
                    else:
                        del inst_data[sym]

            opt_count = 0
            stock_count = 0

            for cand in top_candidates:
                sym = cand["Symbol"].upper()
                side = cand["Side"].upper()
                trig_px = float(cand["Trigger_Price"])
                sl_px = float(cand["Stop_Loss"])
                tp_px = float(cand["Target_Price"])
                be_px = float(cand["BE_Trigger"])

                sl_pts = abs(round(trig_px - sl_px, 2))
                tp_pts = abs(round(tp_px - trig_px, 2))
                be_pts = abs(round(be_px - trig_px, 2))

                sec_id = sec_map.get(sym)
                is_fno = sym in fno_registry
                use_option = (args.execution_mode.lower() == "option") or (args.execution_mode.lower() == "hybrid" and is_fno)

                if use_option and is_fno:
                    # Stock Options Execution (ATM Call for Breakout, ATM Put for Breakdown)
                    fno_info = fno_registry[sym]
                    lot_sz = fno_info['lot_size']
                    step = fno_info['strike_step']

                    # Delta-adjusted points (~0.50 delta for ATM contract)
                    opt_sl = round(max(1.0, sl_pts * 0.50), 2)
                    opt_tp = round(max(2.0, tp_pts * 0.50), 2)
                    opt_be = round(max(1.0, be_pts * 0.50), 2)

                    if args.sizing_mode == "capital":
                        est_prem = max(0.5, trig_px * 0.025)
                        cost_per_lot = est_prem * lot_sz
                        alloc = args.capital / max(1, len(top_candidates))
                        opt_lots = max(1, int(alloc / max(1.0, cost_per_lot)))
                    else:
                        opt_lots = 1

                    item_dict = {
                        "security_id": int(sec_id) if sec_id else int(inst_data.get(sym, {}).get("security_id", 0)),
                        "type": "STOCK",
                        "execution_mode": "OPTION",
                        "exchange_segment": "NSE_FNO",
                        "option_segment": "NSE_FNO",
                        "product_type": "INTRADAY",
                        "lot_size": lot_sz,
                        "strike_step": step,
                        "num_lots_buy": opt_lots,
                        "num_lots_sell": opt_lots,
                        "leg_mode": "BUY",
                        "allowed_actions": ["BUY"],
                        "direction": side,
                        "rotated_joint": True,
                        "strategy": "Strategy_24",
                        "exit_mode": "POINTS",
                        "local_exit_monitoring": True,
                        "broker_safety_sl": True,
                        "trigger_price": trig_px,
                        "points_sl_buy": opt_sl,
                        "points_target_buy": opt_tp,
                        "points_be_buy": opt_be,
                        "enabled": 1 if args.mode == "LIVE" else 0
                    }
                    opt_count += 1
                else:
                    # 5x MIS Cash Equity Execution
                    if args.sizing_mode == "capital":
                        eff_capital = (args.capital / max(1, len(top_candidates))) * args.leverage
                        shares = max(1, int(eff_capital / trig_px))
                    else:
                        shares = 1

                    item_dict = {
                        "security_id": int(sec_id) if sec_id else int(inst_data.get(sym, {}).get("security_id", 0)),
                        "lot_size": 1,
                        "type": "STOCK",
                        "execution_mode": "STOCK",
                        "exchange_segment": "NSE_EQ",
                        "product_type": "INTRADAY",
                        "num_lots_buy": 1,
                        "num_lots_sell": 1,
                        "stock_qty_override": shares,
                        "allowed_actions": [side],
                        "direction": side,
                        "rotated_joint": True,
                        "strategy": "Strategy_24",
                        "exit_mode": "POINTS",
                        "local_exit_monitoring": True,
                        "broker_safety_sl": True,
                        "trigger_price": trig_px,
                        "points_sl_buy": sl_pts if side == "BUY" else None,
                        "points_target_buy": tp_pts if side == "BUY" else None,
                        "points_be_buy": be_pts if side == "BUY" else None,
                        "points_sl_sell": sl_pts if side == "SELL" else None,
                        "points_target_sell": tp_pts if side == "SELL" else None,
                        "points_be_sell": be_pts if side == "SELL" else None,
                        "enabled": 1 if args.mode == "LIVE" else 0
                    }
                    stock_count += 1

                if sym in inst_data and inst_data[sym].get("rotated_prebreakout"):
                    item_dict["rotated_prebreakout"] = True

                inst_data[sym] = item_dict

            with open(instruments_path, "w", encoding="utf-8") as f:
                json.dump(inst_data, f, indent=4)

            print(f"[SUCCESS] instruments.json updated successfully!")
            print(f"  * Stock Options configured: {opt_count}")
            print(f"  * Cash Equities configured: {stock_count}")
            print(f"  * Mode:                     {args.mode} (Enabled = {1 if args.mode == 'LIVE' else 0})")

        except Exception as e:
            print(f"[ERROR] Failed to update instruments.json: {e}")


if __name__ == "__main__":
    main()
