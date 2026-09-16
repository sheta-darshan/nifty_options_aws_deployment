"""
research_and_development/research_opening_absorption_alpha.py

Ultra-Fast Vectorized Empirical Research: Opening Stealth Absorption & Momentum Breakout
Tests across top 25 high-liquidity NSE stocks over 3 years (2023 - 2026).
Compares:
  - Stealth Momentum Filter (RVOL > 2.0 + Range <= 0.6% + Breakout)
  - Control Group (Raw 10-minute breakout without volume/range filter)
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")

SYMBOLS = [
    'reliance', 'tcs', 'infy', 'hdfcbank', 'icicibank',
    'tatamotors', 'sbin', 'bhartiartl', 'lt', 'itc',
    'axisbank', 'bajfinance', 'maruti', 'titan', 'sunpharma',
    'kotakbank', 'wipro', 'hcltech', 'ntpc', 'ongc',
    'powergrid', 'ultracemco', 'adanient', 'tatasteel', 'hindunilvr'
]

def load_stock_data(symbol: str, years: int = 3):
    csv_path = os.path.join(DATA_DIR, f"{symbol}_spot.csv")
    if not os.path.exists(csv_path):
        return None

    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    max_dt = df.index.max()
    cutoff_dt = max_dt - pd.Timedelta(days=years * 365)
    df = df.loc[cutoff_dt:max_dt].copy()

    df['time'] = df.index.time
    df['date'] = df.index.date
    df = df[(df['time'] >= time(9, 15)) & (df['time'] <= time(15, 29))].copy()
    return df

def analyze_symbol(symbol: str, years: int = 3):
    df = load_stock_data(symbol, years=years)
    if df is None or len(df) < 5000:
        return [], []

    grouped = df.groupby('date')
    dates = list(grouped.groups.keys())

    opening_stats = []
    for d in dates:
        day_df = grouped.get_group(d)
        open_box = day_df[(day_df['time'] >= time(9, 15)) & (day_df['time'] <= time(9, 24))]
        if len(open_box) >= 8:
            opening_stats.append({
                'date': d,
                'open_vol': open_box['volume'].sum(),
                'open_price': open_box['open'].iloc[0],
                'high_10': open_box['high'].max(),
                'low_10': open_box['low'].min(),
                'close_10': open_box['close'].iloc[-1]
            })

    if len(opening_stats) < 30:
        return [], []

    df_open = pd.DataFrame(opening_stats)
    df_open.set_index('date', inplace=True)
    df_open['vol_20_avg'] = df_open['open_vol'].rolling(20, min_periods=10).mean().shift(1)
    df_open['rvol'] = df_open['open_vol'] / df_open['vol_20_avg']
    df_open['box_range_pct'] = ((df_open['high_10'] - df_open['low_10']) / df_open['open_price']) * 100.0

    trades_absorption = []
    trades_control = []

    trigger_cutoff_time = time(11, 0)
    eod_time = time(15, 14)

    for d in dates[25:]:
        if d not in df_open.index:
            continue

        meta = df_open.loc[d]
        rvol = meta['rvol']
        if pd.isna(rvol) or rvol <= 0:
            continue

        box_range_pct = meta['box_range_pct']
        high_10 = meta['high_10']
        low_10 = meta['low_10']
        open_px = meta['open_price']

        is_stealth_absorption = (rvol >= 2.0) and (box_range_pct <= 0.60)
        risk = high_10 - low_10
        if risk <= 0 or (risk / open_px) < 0.001:
            continue

        day_df = grouped.get_group(d)
        post_open = day_df[(day_df['time'] >= time(9, 25)) & (day_df['time'] <= time(15, 15))]
        if post_open.empty:
            continue

        times_arr = post_open['time'].values
        opens_arr = post_open['open'].values
        highs_arr = post_open['high'].values
        lows_arr = post_open['low'].values
        closes_arr = post_open['close'].values

        n_bars = len(post_open)
        triggered = False
        target_2r = 0.0
        stop_loss = 0.0
        entry_px = 0.0

        trade_result = None

        for idx in range(n_bars):
            c_time = times_arr[idx]
            c_high = highs_arr[idx]
            c_low = lows_arr[idx]
            c_open = opens_arr[idx]
            c_close = closes_arr[idx]

            if not triggered:
                if c_time <= trigger_cutoff_time and c_high > high_10:
                    triggered = True
                    entry_px = max(high_10, c_open)
                    target_2r = entry_px + (2.0 * risk)
                    stop_loss = entry_px - risk
                    continue

            if triggered:
                hit_tp = (c_high >= target_2r)
                hit_sl = (c_low <= stop_loss)
                is_eod = (c_time >= eod_time) or (idx == n_bars - 1)

                if hit_tp and not hit_sl:
                    trade_result = {'symbol': symbol, 'date': d, 'win': True, 'r_pnl': 2.0, 'type': 'TP'}
                    break
                elif hit_sl and not hit_tp:
                    trade_result = {'symbol': symbol, 'date': d, 'win': False, 'r_pnl': -1.0, 'type': 'SL'}
                    break
                elif hit_tp and hit_sl:
                    trade_result = {'symbol': symbol, 'date': d, 'win': False, 'r_pnl': -1.0, 'type': 'SL'}
                    break
                elif is_eod:
                    r_pnl = (c_close - entry_px) / risk
                    trade_result = {'symbol': symbol, 'date': d, 'win': r_pnl > 0, 'r_pnl': r_pnl, 'type': 'EOD'}
                    break

        if trade_result:
            if is_stealth_absorption:
                trades_absorption.append(trade_result)
            trades_control.append(trade_result)

    return trades_absorption, trades_control

def main():
    print("="*95, flush=True)
    print("   EMPIRICAL RESEARCH: HISTORICAL TESTING OF OPENING STEALTH ABSORPTION ALPHA", flush=True)
    print("="*95, flush=True)
    print("Testing 25 Large-Cap NSE Stocks over 3 Years (~750 Trading Sessions/Stock)...", flush=True)

    all_absorption = []
    all_control = []

    for i, sym in enumerate(SYMBOLS, 1):
        print(f"[{i:02d}/{len(SYMBOLS)}] Processing {sym.upper()}...", flush=True)
        abs_t, ctrl_t = analyze_symbol(sym, years=3)
        all_absorption.extend(abs_t)
        all_control.extend(ctrl_t)

    print("\n" + "="*95, flush=True)
    print("                  AGGREGATED 3-YEAR PERFORMANCE COMPARISON", flush=True)
    print("="*95, flush=True)

    df_abs = pd.DataFrame(all_absorption)
    df_ctrl = pd.DataFrame(all_control)

    def calc_metrics(df_t, name):
        if df_t.empty:
            return {'Strategy': name, 'Total Trades': 0, 'Wins': 0, 'Losses': 0, 'Win Rate %': 0, 'Total R-Profit': 0, 'Avg R / Trade': 0, 'Profit Factor': 0}
        n = len(df_t)
        wins = df_t['win'].sum()
        wr = (wins / n) * 100.0
        total_r = df_t['r_pnl'].sum()
        avg_r = df_t['r_pnl'].mean()
        win_r = df_t[df_t['r_pnl'] > 0]['r_pnl'].sum()
        loss_r = abs(df_t[df_t['r_pnl'] < 0]['r_pnl'].sum())
        pf = (win_r / loss_r) if loss_r > 0 else np.nan
        return {
            'Strategy': name,
            'Total Trades': n,
            'Wins': wins,
            'Losses': n - wins,
            'Win Rate %': round(wr, 1),
            'Total R-Profit': round(total_r, 1),
            'Avg R / Trade': round(avg_r, 2),
            'Profit Factor': round(pf, 2)
        }

    m_abs = calc_metrics(df_abs, "1. Stealth Absorption (RVOL >= 2.0 + Range <= 0.6%)")
    m_ctrl = calc_metrics(df_ctrl, "2. Baseline Control (Raw 10m Breakout - No Filter)")

    summary_df = pd.DataFrame([m_abs, m_ctrl])
    print(summary_df.to_string(index=False), flush=True)
    print("="*95, flush=True)

    if not df_abs.empty:
        print("\nTOP 10 INDIVIDUAL STOCK PERFORMANCE UNDER STEALTH ABSORPTION:", flush=True)
        print("-"*85, flush=True)
        stock_perf = []
        for sym, grp in df_abs.groupby('symbol'):
            n = len(grp)
            if n >= 5:
                wr = (grp['win'].sum() / n) * 100
                tot_r = grp['r_pnl'].sum()
                avg_r = grp['r_pnl'].mean()
                stock_perf.append({'Stock': sym.upper(), 'Trades': n, 'Win Rate %': round(wr, 1), 'Total R': round(tot_r, 1), 'Avg R': round(avg_r, 2)})

        df_sp = pd.DataFrame(stock_perf).sort_values(by='Total R', ascending=False)
        print(df_sp.head(10).to_string(index=False), flush=True)
        print("-"*85, flush=True)

if __name__ == '__main__':
    main()
