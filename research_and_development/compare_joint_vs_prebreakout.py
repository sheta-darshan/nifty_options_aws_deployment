"""
research_and_development/compare_joint_vs_prebreakout.py

Institutional Head-to-Head Backtest: Select_Joint vs Select_Prebreakout vs Ensemble
====================================================================================
Simulates and compares two distinct stock selection methodologies across 1 full year
(260 trading sessions) on identical market data, identical capital, and identical Strategy 24 execution:

  Engine 1 (Pre-Breakout Coiled):
    - Minervini Volatility Contraction Pattern (VCP Wave 3 / Wave 1)
    - TTM Squeeze (Bollinger Bands contracted inside Keltner Channels)
    - NR7 & Inside Day compression
    - Proximity to 20 EMA base & Volume Dry-up
    - Closing Auction Footprint (CAR & CLV)

  Engine 2 (True Dual-Head ML Joint):
    - Machine Learning Dual-Head XGBoost with Isotonic Probability Calibration
    - Head 1: P(Vol >= 1.3x ATR)
    - Head 2: P(Close > Open)
    - 26 Feature Matrix 2.0 Alpha Microstructure Features
    - Dynamic Relative Strength (RS) vs NIFTY 50

  Engine 3 (Ensemble Confluence):
    - Setups identified by BOTH Engine 1 and Engine 2

Execution Engine (Strategy 24):
  - 5-minute confirmation on Day T+1
  - Hard SL: 0.90x ATR
  - Dynamic Breakeven: Slide SL to Entry upon +0.65x ATR profit
  - Profit Target: +1.15x ATR
  - Smart Hybrid Routing: ATM Stock Options for F&O, 5x MIS Cash Equity for non-F&O
  - Full Dhan Transaction Charges (STT, Brokerage, Exchange, GST, SEBI, Stamp Duty)
"""

import os
import sys
import json
import time
import pickle
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, time as dt_time
from typing import Dict, List, Any
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from stock_selection.feature_matrix_v2 import FEATURE_NAMES_V2, extract_features_v2_df

DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
MODEL_PATH = os.path.join(BASE_DIR, "stock_selection", "models", "global_dual_head_joint_model.pkl")
FNO_REGISTRY_PATH = os.path.join(BASE_DIR, "stock_selection", "fno_registry.json")
CACHE_FILE = os.path.join(DATA_DIR, "prebreakout_cache_200_1y.pkl")
REPORT_OUTPUT_CSV = os.path.join(BASE_DIR, "research_and_development", "comparison_trades_joint_vs_prebreakout.csv")

ALLOCATION_PER_TRADE = 100000.0  # Rs. 1,00,000 capital / trade


def load_fno_registry() -> dict:
    if os.path.exists(FNO_REGISTRY_PATH):
        with open(FNO_REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def calc_transaction_costs(buy_val: float, sell_val: float, is_option: bool = False) -> float:
    """Computes exact Dhan transaction charges."""
    if is_option:
        brokerage = 40.0  # Rs. 20 buy + Rs. 20 sell
        stt = sell_val * 0.00125  # 0.125% on option premium turnover (sell leg)
        exch = (buy_val + sell_val) * 0.00050
        sebi = (buy_val + sell_val) * 0.000001
        stamp = buy_val * 0.00003
        gst = 0.18 * (brokerage + exch)
        return brokerage + stt + exch + sebi + stamp + gst
    else:
        brokerage = min(40.0, 0.0003 * (buy_val + sell_val))
        stt = sell_val * 0.00025  # 0.025% on intraday equity turnover
        exch = (buy_val + sell_val) * 0.0000322
        stamp = buy_val * 0.00015
        sebi = (buy_val + sell_val) * 0.000001
        gst = 0.18 * (brokerage + exch)
        return brokerage + stt + exch + stamp + sebi + gst


def evaluate_prebreakout_picks(sym: str, d_df: pd.DataFrame, idx_loc: int) -> dict:
    """Evaluates rule-based Pre-Breakout compression score on Day T."""
    if idx_loc < 25:
        return None

    sub = d_df.iloc[:idx_loc + 1]
    c = sub['close'].iloc[-1]
    h = sub['high'].iloc[-1]
    l = sub['low'].iloc[-1]
    v = sub['volume'].iloc[-1]
    e20 = sub['ema20'].iloc[-1] if 'ema20' in sub.columns else sub['close'].ewm(span=20).mean().iloc[-1]
    e50 = sub['ema50'].iloc[-1] if 'ema50' in sub.columns else sub['close'].ewm(span=50).mean().iloc[-1]
    atr = sub['atr14'].iloc[-1] if 'atr14' in sub.columns else (h - l)
    v_sma = sub['vol_sma20'].iloc[-1] if 'vol_sma20' in sub.columns else sub['volume'].rolling(20).mean().iloc[-1]
    rng = h - l

    # Liquidity gate
    if v_sma < 15000:
        return None

    # Trend & Proximity
    dist_20 = (c - e20) / (e20 + 1e-9) * 100.0

    # 1. TTM Squeeze
    sma20 = sub['close'].rolling(20).mean().iloc[-1]
    std20 = sub['close'].rolling(20).std().iloc[-1]
    bbl = sma20 - 2.0 * std20
    bbu = sma20 + 2.0 * std20
    kcl = e20 - 1.5 * atr
    kcu = e20 + 1.5 * atr
    is_squeeze = (bbl >= kcl) and (bbu <= kcu)

    # 2. NR7 / Inside Day
    ranges_7 = (sub['high'] - sub['low']).iloc[-7:]
    is_nr7 = rng <= ranges_7.min() + 1e-6
    prev_h = sub['high'].iloc[-2] if len(sub) >= 2 else h
    prev_l = sub['low'].iloc[-2] if len(sub) >= 2 else l
    is_inside_day = (h <= prev_h) and (l >= prev_l)

    # 3. Volume dryup
    vol_ratio = v / (v_sma + 1e-9)

    score_buy = 0.0
    score_sell = 0.0

    # Base Squeeze score
    if is_squeeze:
        score_buy += 25.0
        score_sell += 25.0

    if is_nr7 and is_inside_day:
        score_buy += 25.0
        score_sell += 25.0
    elif is_nr7:
        score_buy += 20.0
        score_sell += 20.0
    elif is_inside_day:
        score_buy += 18.0
        score_sell += 18.0

    if vol_ratio <= 0.70:
        score_buy += 15.0
        score_sell += 15.0
    elif vol_ratio <= 0.90:
        score_buy += 10.0
        score_sell += 10.0

    # Directional differentiation
    if c >= e50 and 0.0 <= dist_20 <= 2.5:
        score_buy += 25.0
    elif c < e50 and -2.5 <= dist_20 <= 0.0:
        score_sell += 25.0

    # 5d trend slope
    if len(sub) >= 6:
        ret_5d = (c - sub['close'].iloc[-6]) / (sub['close'].iloc[-6] + 1e-9) * 100.0
        if ret_5d > 0:
            score_buy += 10.0
        else:
            score_sell += 10.0

    best_dir = "BUY" if score_buy >= score_sell else "SELL"
    best_score = score_buy if best_dir == "BUY" else score_sell

    return {
        'sym': sym,
        'direction': best_dir,
        'score': best_score,
        'trigger_px': round(h + 0.05, 2) if best_dir == "BUY" else round(l - 0.05, 2),
        'atr': atr,
        'close': c,
        'high': h,
        'low': l
    }


def evaluate_joint_picks(sym: str, df_feat: pd.DataFrame, date_t) -> dict:
    """Evaluates ML True Dual-Head Joint scores on Day T using batch pre-computed predictions."""
    if df_feat is None or df_feat.empty or date_t not in df_feat.index:
        return None

    row = df_feat.loc[date_t]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[-1]

    p_vol = float(row.get('p_vol', 0.0))
    p_dir = float(row.get('p_dir', 0.50))
    joint_score_long = float(row.get('joint_score_long', 0.0))
    joint_score_short = float(row.get('joint_score_short', 0.0))

    c = float(row.get('close', 0.0))
    h = float(row.get('high', 0.0))
    l = float(row.get('low', 0.0))
    atr = float(row.get('atr14', 0.0))
    if atr <= 0:
        atr = (h - l) if (h > l) else max(1.0, c * 0.015)

    # Determine primary direction
    if p_dir >= 0.50:
        best_dir = "BUY"
        best_score = joint_score_long
        trig = round(h + 0.05, 2)
    else:
        best_dir = "SELL"
        best_score = joint_score_short
        trig = round(l - 0.05, 2)

    return {
        'sym': sym,
        'direction': best_dir,
        'score': best_score,
        'p_vol': p_vol,
        'p_dir': p_dir,
        'trigger_px': trig,
        'atr': atr,
        'close': c,
        'high': h,
        'low': l
    }


def simulate_trade_day_t1(pick: dict, t1_bars: pd.DataFrame, is_fno: bool, fno_info: dict) -> dict:
    """Simulates Strategy 24 execution on Day T+1 with Smart Hybrid routing."""
    sym = pick['sym']
    direction = pick['direction']
    trig_px = pick['trigger_px']
    atr = pick['atr']

    if t1_bars.empty or len(t1_bars) < 30:
        return None

    # Resample Day T+1 to 5-min bars for confirmation
    m5_df = t1_bars.resample('5min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()

    m5_morning = m5_df[(m5_df.index.time >= dt_time(9, 20)) & (m5_df.index.time <= dt_time(11, 30))]

    if direction == "BUY":
        breakout = m5_morning[(m5_morning['high'] >= trig_px) & (m5_morning['close'] >= trig_px) & (m5_morning['close'] >= m5_morning['open'])]
    else:
        breakout = m5_morning[(m5_morning['low'] <= trig_px) & (m5_morning['close'] <= trig_px) & (m5_morning['close'] <= m5_morning['open'])]

    if breakout.empty:
        return None

    entry_bar_idx = breakout.index[0]
    entry_bar = breakout.loc[entry_bar_idx]

    # Volume participation filter
    pos_5m = m5_df.index.get_loc(entry_bar_idx)
    if isinstance(pos_5m, int) and pos_5m >= 3:
        avg_v = m5_df['volume'].iloc[max(0, pos_5m - 5):pos_5m].mean()
        if avg_v > 0 and entry_bar['volume'] < 1.15 * avg_v:
            return None

    entry_price = trig_px

    # Smart Hybrid Option Sizing
    if is_fno and fno_info:
        is_option = True
        lot_size = fno_info['lot_size']
        est_option_premium = entry_price * 0.025  # ~2.5% ATM option premium
        contracts = max(1, int(ALLOCATION_PER_TRADE / (est_option_premium * lot_size + 1e-9)))
        effective_shares = contracts * lot_size
        delta = 0.50  # ATM Delta
    else:
        is_option = False
        effective_shares = max(1, int((ALLOCATION_PER_TRADE * 5.0) / entry_price))  # 5x MIS Cash
        delta = 1.0

    # Strategy 24 Risk Parameters
    sl_distance = 0.90 * atr
    be_distance = 0.65 * atr
    tp_distance = 1.15 * atr

    if direction == "BUY":
        sl_price = round(entry_price - sl_distance, 2)
        be_trigger = round(entry_price + be_distance, 2)
        tp_price = round(entry_price + tp_distance, 2)
    else:
        sl_price = round(entry_price + sl_distance, 2)
        be_trigger = round(entry_price - be_distance, 2)
        tp_price = round(entry_price - tp_distance, 2)

    # Intraday 1-min simulation from entry bar onwards
    remaining_bars = t1_bars.loc[entry_bar_idx:]
    if len(remaining_bars) <= 1:
        return None

    be_active = False
    exit_price = None
    exit_reason = None

    for _, bar in remaining_bars.iloc[1:].iterrows():
        b_h = bar['high']
        b_l = bar['low']

        if direction == "BUY":
            if not be_active and b_h >= be_trigger:
                sl_price = round(entry_price * 1.0005, 2)  # Shift SL to breakeven
                be_active = True
            if b_l <= sl_price:
                exit_price = sl_price
                exit_reason = "BREAKEVEN" if be_active else "STOP_LOSS"
                break
            if b_h >= tp_price:
                exit_price = tp_price
                exit_reason = "TARGET"
                break
        else:
            if not be_active and b_l <= be_trigger:
                sl_price = round(entry_price * 0.9995, 2)  # Shift SL to breakeven
                be_active = True
            if b_h >= sl_price:
                exit_price = sl_price
                exit_reason = "BREAKEVEN" if be_active else "STOP_LOSS"
                break
            if b_l <= tp_price:
                exit_price = tp_price
                exit_reason = "TARGET"
                break

    if exit_price is None:
        exit_price = remaining_bars['close'].iloc[-1]
        exit_reason = "EOD"

    # Compute PnL
    if direction == "BUY":
        price_diff = exit_price - entry_price
    else:
        price_diff = entry_price - exit_price

    if is_option:
        # Option PnL with ~0.50 delta
        option_pnl_pts = price_diff * delta
        gross_pnl = option_pnl_pts * effective_shares
        buy_val = est_option_premium * effective_shares
        sell_val = max(1.0, est_option_premium + option_pnl_pts) * effective_shares
        costs = calc_transaction_costs(buy_val, sell_val, is_option=True)
    else:
        gross_pnl = price_diff * effective_shares
        buy_val = entry_price * effective_shares
        sell_val = exit_price * effective_shares
        costs = calc_transaction_costs(buy_val, sell_val, is_option=False)

    net_pnl = gross_pnl - costs
    pct_ret = (net_pnl / ALLOCATION_PER_TRADE) * 100.0

    return {
        'symbol': sym,
        'direction': direction,
        'execution_mode': 'OPTION' if is_option else 'STOCK_MIS',
        'entry_price': entry_price,
        'exit_price': exit_price,
        'exit_reason': exit_reason,
        'gross_pnl': round(gross_pnl, 2),
        'costs': round(costs, 2),
        'net_pnl': round(net_pnl, 2),
        'pct_ret': round(pct_ret, 2),
        'is_win': net_pnl > 0
    }


def run_comparative_backtest():
    print("=" * 125, flush=True)
    print("      HEAD-TO-HEAD COMPARATIVE BACKTEST: SELECT_JOINT vs SELECT_PREBREAKOUT vs ENSEMBLE", flush=True)
    print("=" * 125, flush=True)
    print(f"Loading datasets from binary cache: {CACHE_FILE}...", flush=True)

    if not os.path.exists(CACHE_FILE):
        print(f"[ERROR] Cache file not found at {CACHE_FILE}")
        return

    with open(CACHE_FILE, 'rb') as f:
        stock_1m, stock_daily = pickle.load(f)

    symbols = list(stock_daily.keys())
    print(f"[INFO] Loaded {len(symbols)} liquid stocks from cache.", flush=True)

    # Load Dual-Head Model
    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] Model file not found at {MODEL_PATH}")
        return
    model_bundle = joblib.load(MODEL_PATH)
    print("[INFO] Loaded True Dual-Head (Joint) Model with Feature Matrix 2.0.", flush=True)

    # Load F&O Registry
    fno_registry = load_fno_registry()
    print(f"[INFO] Loaded {len(fno_registry)} verified live option underlyings.", flush=True)

    # Pre-extract Feature Matrix 2.0 for all stocks
    # Pre-extract Feature Matrix 2.0 and compute batch predictions for all stocks
    print("[INFO] Pre-computing Feature Matrix 2.0 and running batch Dual-Head predictions for all stocks...", flush=True)
    t0 = time.time()
    stock_feat_v2 = {}
    vol_model = model_bundle["volatility_model"]
    dir_model = model_bundle["direction_model"]

    for sym in symbols:
        try:
            m1 = stock_1m[sym]
            f_df = extract_features_v2_df(m1, nifty_daily=None, is_training=False)
            if f_df is not None and not f_df.empty:
                # Batch prediction across all rows at once (instantaneous)
                X_all = f_df[FEATURE_NAMES_V2]
                f_df['p_vol'] = vol_model.predict_proba(X_all)[:, 1]
                f_df['p_dir'] = dir_model.predict_proba(X_all)[:, 1]

                rs_norm = (f_df['rs_nifty_5d'] / 100.0).clip(-0.5, 0.5)
                f_df['joint_score_long'] = f_df['p_vol'] * f_df['p_dir'] * (1.0 + rs_norm) * 100.0
                f_df['joint_score_short'] = f_df['p_vol'] * (1.0 - f_df['p_dir']) * (1.0 - rs_norm) * 100.0

                stock_feat_v2[sym] = f_df
        except Exception:
            pass
    print(f"[INFO] Feature Matrix 2.0 & Batch Predictions ready for {len(stock_feat_v2)} stocks in {time.time() - t0:.1f}s.", flush=True)

    # Discover common trading sessions
    ref_sym = 'RELIANCE' if 'RELIANCE' in stock_daily else symbols[0]
    all_dates = sorted(stock_daily[ref_sym].index)
    test_dates = [d for d in all_dates if d >= pd.to_datetime('2025-09-01').date()]
    print(f"[INFO] Backtesting across {len(test_dates)} historical sessions (Sept 2025 – Sept 2026)...\n", flush=True)

    trades_prebreakout = []
    trades_joint = []
    trades_ensemble = []

    t_start = time.time()

    for idx in range(len(test_dates) - 1):
        date_t = test_dates[idx]
        date_t1 = test_dates[idx + 1]

        if idx % 30 == 0 or idx == len(test_dates) - 2:
            print(f"  Processing session {idx+1}/{len(test_dates)-1} ({date_t} -> {date_t1})...", flush=True)

        candidates_prebreakout = []
        candidates_joint = []

        for sym in symbols:
            # 1. Evaluate Pre-Breakout Coiling
            d_df = stock_daily[sym]
            if date_t in d_df.index:
                loc = d_df.index.get_loc(date_t)
                pb_pick = evaluate_prebreakout_picks(sym, d_df, loc)
                if pb_pick and pb_pick['score'] >= 65.0:
                    candidates_prebreakout.append(pb_pick)

            # 2. Evaluate Dual-Head Joint Model
            if sym in stock_feat_v2:
                f_df = stock_feat_v2[sym]
                jt_pick = evaluate_joint_picks(sym, f_df, date_t)
                if jt_pick and jt_pick['score'] >= 11.0:
                    candidates_joint.append(jt_pick)

        # Select Top 3 picks per engine
        candidates_prebreakout.sort(key=lambda x: x['score'], reverse=True)
        top_pb = candidates_prebreakout[:3]

        candidates_joint.sort(key=lambda x: x['score'], reverse=True)
        top_jt = candidates_joint[:3]

        # Ensemble: picks present in top 8 of both with matching direction
        pb_map = {p['sym']: p for p in candidates_prebreakout[:8]}
        jt_map = {p['sym']: p for p in candidates_joint[:8]}
        ensemble_picks = []
        for sym, p_pb in pb_map.items():
            if sym in jt_map and jt_map[sym]['direction'] == p_pb['direction']:
                ensemble_picks.append(p_pb)
        top_ensemble = ensemble_picks[:3]

        # Simulate Day T+1 execution
        # Engine 1: Pre-Breakout
        for pick in top_pb:
            sym = pick['sym']
            t1_bars = stock_1m[sym][stock_1m[sym]['date'] == date_t1]
            is_fno = sym in fno_registry
            fno_info = fno_registry.get(sym)
            res = simulate_trade_day_t1(pick, t1_bars, is_fno, fno_info)
            if res:
                res['date'] = date_t1
                res['engine'] = 'PREBREAKOUT'
                trades_prebreakout.append(res)

        # Engine 2: Joint Model
        for pick in top_jt:
            sym = pick['sym']
            t1_bars = stock_1m[sym][stock_1m[sym]['date'] == date_t1]
            is_fno = sym in fno_registry
            fno_info = fno_registry.get(sym)
            res = simulate_trade_day_t1(pick, t1_bars, is_fno, fno_info)
            if res:
                res['date'] = date_t1
                res['engine'] = 'JOINT_MODEL'
                trades_joint.append(res)

        # Engine 3: Ensemble
        for pick in top_ensemble:
            sym = pick['sym']
            t1_bars = stock_1m[sym][stock_1m[sym]['date'] == date_t1]
            is_fno = sym in fno_registry
            fno_info = fno_registry.get(sym)
            res = simulate_trade_day_t1(pick, t1_bars, is_fno, fno_info)
            if res:
                res['date'] = date_t1
                res['engine'] = 'ENSEMBLE_CONFLUENCE'
                trades_ensemble.append(res)

    print(f"[SUCCESS] Simulation completed across {len(test_dates)} sessions in {time.time() - t_start:.1f}s.")

    # Compute Comparative Statistics
    def compute_stats(trades: list, name: str) -> dict:
        if not trades:
            return {
                "name": name, "trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
                "net_pnl": 0.0, "max_dd": 0.0, "costs": 0.0,
                "target_hits": 0, "be_hits": 0, "sl_hits": 0,
                "prof_months": "0/0 (0%)"
            }
        df = pd.DataFrame(trades)
        total = len(df)
        wins = df['is_win'].sum()
        wr = (wins / total) * 100.0
        gains = df.loc[df['net_pnl'] > 0, 'net_pnl'].sum()
        losses = abs(df.loc[df['net_pnl'] < 0, 'net_pnl'].sum())
        pf = (gains / losses) if losses > 0 else 9.99
        net_pnl = df['net_pnl'].sum()
        costs = df['costs'].sum()

        df_sorted = df.sort_values(by='date').copy()
        df_sorted['cum'] = df_sorted['net_pnl'].cumsum()
        max_dd = (df_sorted['cum'] - df_sorted['cum'].cummax()).min()

        t_hits = (df['exit_reason'] == 'TARGET').sum()
        be_hits = (df['exit_reason'] == 'BREAKEVEN').sum()
        sl_hits = (df['exit_reason'] == 'STOP_LOSS').sum()

        # Monthly breakdown
        df['month'] = df['date'].apply(lambda d: str(d)[:7])
        monthly = df.groupby('month')['net_pnl'].sum()
        prof_months = (monthly > 0).sum()
        tot_months = len(monthly)
        mo_win_rate = (prof_months / tot_months * 100.0) if tot_months > 0 else 0.0

        return {
            "name": name,
            "trades": total,
            "win_rate": round(wr, 1),
            "profit_factor": round(pf, 2),
            "net_pnl": round(net_pnl, 2),
            "max_dd": round(max_dd, 2),
            "costs": round(costs, 2),
            "target_hits": t_hits,
            "be_hits": be_hits,
            "sl_hits": sl_hits,
            "prof_months": f"{prof_months}/{tot_months} ({mo_win_rate:.0f}%)"
        }

    s_pb = compute_stats(trades_prebreakout, "Select_Prebreakout (Rule-Based)")
    s_jt = compute_stats(trades_joint, "Select_Joint (Dual-Head ML)")
    s_ens = compute_stats(trades_ensemble, "Ensemble Confluence (Both Agree)")

    # Display Side-by-Side Comparison
    print("\n" + "=" * 135)
    print("                           HEAD-TO-HEAD QUANTITATIVE PERFORMANCE AUDIT")
    print("=" * 135)
    print(f"{'Metric':<32} | {'Select_Prebreakout':<26} | {'Select_Joint (ML)':<26} | {'Ensemble Confluence':<26}")
    print("-" * 135)
    print(f"{'Total Trades Executed':<32} | {s_pb['trades']:<26} | {s_jt['trades']:<26} | {s_ens['trades']:<26}")
    print(f"{'Win Rate (%)':<32} | {s_pb['win_rate']:<25}% | {s_jt['win_rate']:<25}% | {s_ens['win_rate']:<25}%")
    print(f"{'Profit Factor':<32} | {s_pb['profit_factor']:<26} | {s_jt['profit_factor']:<26} | {s_ens['profit_factor']:<26}")
    print(f"{'Net Realized Profit (Rs.)':<32} | Rs. {s_pb['net_pnl']:<22,.2f} | Rs. {s_jt['net_pnl']:<22,.2f} | Rs. {s_ens['net_pnl']:<22,.2f}")
    print(f"{'Max Peak-to-Trough DD (Rs.)':<32} | Rs. {s_pb['max_dd']:<22,.2f} | Rs. {s_jt['max_dd']:<22,.2f} | Rs. {s_ens['max_dd']:<22,.2f}")
    print(f"{'Total Transaction Costs':<32} | Rs. {s_pb['costs']:<22,.2f} | Rs. {s_jt['costs']:<22,.2f} | Rs. {s_ens['costs']:<22,.2f}")
    print(f"{'Profitable Months (%)':<32} | {s_pb['prof_months']:<26} | {s_jt['prof_months']:<26} | {s_ens['prof_months']:<26}")
    print(f"{'Target Hit Rate':<32} | {s_pb['target_hits']} trades ({s_pb['target_hits']/max(1, s_pb['trades'])*100:.1f}%) | {s_jt['target_hits']} trades ({s_jt['target_hits']/max(1, s_jt['trades'])*100:.1f}%) | {s_ens['target_hits']} trades ({s_ens['target_hits']/max(1, s_ens['trades'])*100:.1f}%)")
    print(f"{'Breakeven Protect Rate':<32} | {s_pb['be_hits']} trades ({s_pb['be_hits']/max(1, s_pb['trades'])*100:.1f}%) | {s_jt['be_hits']} trades ({s_jt['be_hits']/max(1, s_jt['trades'])*100:.1f}%) | {s_ens['be_hits']} trades ({s_ens['be_hits']/max(1, s_ens['trades'])*100:.1f}%)")
    print(f"{'Hard Stop Loss Hit Rate':<32} | {s_pb['sl_hits']} trades ({s_pb['sl_hits']/max(1, s_pb['trades'])*100:.1f}%) | {s_jt['sl_hits']} trades ({s_jt['sl_hits']/max(1, s_jt['trades'])*100:.1f}%) | {s_ens['sl_hits']} trades ({s_ens['sl_hits']/max(1, s_ens['trades'])*100:.1f}%)")
    print("=" * 135)

    # Save detailed trade logs
    all_trades = trades_prebreakout + trades_joint + trades_ensemble
    if all_trades:
        df_all = pd.DataFrame(all_trades)
        df_all.to_csv(REPORT_OUTPUT_CSV, index=False)
        print(f"\n[SUCCESS] Detailed trade logs saved to:\n  -> {REPORT_OUTPUT_CSV}")


if __name__ == "__main__":
    run_comparative_backtest()
