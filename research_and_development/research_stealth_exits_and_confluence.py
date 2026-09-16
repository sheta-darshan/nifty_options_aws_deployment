"""
research_and_development/research_stealth_exits_and_confluence.py

Empirical Study for Option A:
  1. Target & Exit Optimization (1.5R vs 2.0R vs 2.5R vs Trailing Stop vs EOD)
  2. Long (Absorption Breakout) vs Short (Distribution Breakdown) Asymmetry
  3. Market Regime Confluence (NIFTY 50 Alignment at Entry Time)

Tested across 100 High-Liquidity Stocks over 3 Years (2023 - 2026).
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")

# 100 Liquid Stocks: Nifty 50 + Top F&O Momentum & Midcap Leaders
POPULAR_STOCKS = [
    'reliance', 'tcs', 'infy', 'hdfcbank', 'icicibank', 'tatamotors', 'sbin', 'bhartiartl', 'lt', 'itc',
    'axisbank', 'bajfinance', 'maruti', 'titan', 'sunpharma', 'kotakbank', 'wipro', 'hcltech', 'ntpc', 'ongc',
    'powergrid', 'ultracemco', 'adanient', 'tatasteel', 'hindunilvr', 'tataelxsi', 'polycab', 'persistent', 'coforge', 'm&m',
    'canbk', 'federalbnk', 'pfc', 'hal', 'bel', 'bhel', 'dlf', 'godrejprop', 'trent', 'vedl',
    'jswsteel', 'hindalco', 'coalindia', 'chamblfert', 'indiamart', 'apollotyre', 'escorst', 'jublfood', 'mrf', 'voltas',
    'irb', 'abfrl', 'cgcl', 'unominda', 'ipcalab', 'srf', 'whirlpool', 'ioc', 'cesc', 'pcbl',
    'vtl', 'aplapollo', 'schaeffler', 'gpil', 'motilaloys', 'bsoft', 'lupin', 'cipla', 'drreddy', 'apollohosp',
    'havells', 'pidilitind', 'siemens', 'abb', 'cumminsind', 'techm', 'ashokley', 'eichermot', 'heromotoco', 'tvs_motor',
    'sail', 'jindalstel', 'nmdc', 'nationalum', 'hindcopper', 'gnfc', 'deepakntr', 'upl', 'atgl', 'adaniports',
    'grasim', 'ambujacem', 'acc', 'dalbharat', 'divislab', 'biocon', 'syngene', 'alkem', 'torrentpha', 'glenmark'
]

def load_nifty_data(years: int = 3):
    csv_path = os.path.join(DATA_DIR, "nifty_spot.csv")
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

def load_stock_df(symbol: str, years: int = 3):
    csv_path = os.path.join(DATA_DIR, f"{symbol}_spot.csv")
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path)
        if len(df) < 5000:
            return None
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
    except Exception:
        return None

def run_study():
    print("=" * 105, flush=True)
    print("   DEEP DIVE RESEARCH: EXITS (1.5R vs 2.0R vs TRAILING) & NIFTY REGIME CONFLUENCE", flush=True)
    print("=" * 105, flush=True)

    print("Loading NIFTY spot benchmark for market confluence...", flush=True)
    nifty_df = load_nifty_data(years=3)
    if nifty_df is None:
        print("Error: nifty_spot.csv not found!", flush=True)
        return

    nifty_days = nifty_df.groupby('date')
    nifty_open_map = {}
    for d, grp in nifty_days:
        first_bar = grp[grp['time'] == time(9, 15)]
        if not first_bar.empty:
            nifty_open_map[d] = first_bar['open'].iloc[0]

    # Pre-index Nifty by timestamp for O(1) confluence lookup
    nifty_price_map = nifty_df['close'].to_dict()

    print(f"Loading {len(POPULAR_STOCKS)} candidate stocks...", flush=True)
    loaded_stocks = {}
    for sym in POPULAR_STOCKS:
        df = load_stock_df(sym, years=3)
        if df is not None:
            loaded_stocks[sym] = df
    print(f"Loaded {len(loaded_stocks)} valid stocks with full 3-year historical 1m data.\n", flush=True)

    # Setups to collect
    # Long Trades and Short Trades separately
    raw_signals = []

    trigger_cutoff = time(11, 0)
    eod_time = time(15, 14)

    for sym_idx, (sym, df) in enumerate(loaded_stocks.items(), 1):
        grouped = df.groupby('date')
        dates = list(grouped.groups.keys())

        # 1. 10m Opening Box Stats
        stats = []
        for d in dates:
            day_df = grouped.get_group(d)
            open_box = day_df[(day_df['time'] >= time(9, 15)) & (day_df['time'] <= time(9, 24))]
            if len(open_box) >= 8:
                stats.append({
                    'date': d,
                    'open_vol': open_box['volume'].sum(),
                    'open_px': open_box['open'].iloc[0],
                    'high_10': open_box['high'].max(),
                    'low_10': open_box['low'].min(),
                    'close_10': open_box['close'].iloc[-1]
                })

        if len(stats) < 30:
            continue

        df_stats = pd.DataFrame(stats).set_index('date')
        df_stats['vol_20_avg'] = df_stats['open_vol'].rolling(20, min_periods=10).mean().shift(1)
        df_stats['rvol'] = df_stats['open_vol'] / df_stats['vol_20_avg']
        df_stats['range_pct'] = ((df_stats['high_10'] - df_stats['low_10']) / df_stats['open_px']) * 100.0

        for d in dates[25:]:
            if d not in df_stats.index:
                continue
            meta = df_stats.loc[d]
            rvol = meta['rvol']
            range_pct = meta['range_pct']
            high_10 = meta['high_10']
            low_10 = meta['low_10']
            open_px = meta['open_px']

            # Stealth Absorption Criteria: RVOL >= 1.5 and Range <= 0.8%
            if pd.isna(rvol) or rvol < 1.5 or range_pct > 0.8:
                continue

            risk = high_10 - low_10
            if risk <= 0 or (risk / open_px) < 0.001:
                continue

            day_df = grouped.get_group(d)
            post = day_df[(day_df['time'] >= time(9, 25)) & (day_df['time'] <= time(15, 15))]
            if post.empty:
                continue

            times = post['time'].values
            opens = post['open'].values
            highs = post['high'].values
            lows = post['low'].values
            closes = post['close'].values
            idx_timestamps = post.index
            n_bars = len(post)

            # Check if Long or Short triggers first
            first_trigger = None  # ('LONG', bar_idx) or ('SHORT', bar_idx)

            for i in range(n_bars):
                t = times[i]
                h = highs[i]
                l = lows[i]
                if t > trigger_cutoff:
                    break

                hit_long = (h > high_10)
                hit_short = (l < low_10)

                if hit_long and not hit_short:
                    first_trigger = ('LONG', i)
                    break
                elif hit_short and not hit_long:
                    first_trigger = ('SHORT', i)
                    break
                elif hit_long and hit_short:
                    # Inside same bar, skip ambiguous chop
                    break

            if first_trigger is None:
                continue

            direction, entry_bar_idx = first_trigger
            entry_ts = idx_timestamps[entry_bar_idx]
            nifty_open_d = nifty_open_map.get(d)
            nifty_curr = nifty_price_map.get(entry_ts)

            nifty_bullish = False
            nifty_bearish = False
            if nifty_open_d is not None and nifty_curr is not None:
                nifty_bullish = (nifty_curr >= nifty_open_d)
                nifty_bearish = (nifty_curr < nifty_open_d)

            # Simulate performance under multiple exit regimes
            if direction == 'LONG':
                entry_px = max(high_10, opens[entry_bar_idx])
                stop_loss = entry_px - risk

                # Exit regimes to evaluate
                # 1. Fixed 1.5R
                # 2. Fixed 2.0R
                # 3. Fixed 2.5R
                # 4. Trailing (Lock +1R after hitting +1R, trail 0.5R behind peak)
                # 5. EOD

                pnl_15r = None
                pnl_20r = None
                pnl_25r = None
                pnl_trail = None
                pnl_eod = None

                max_favorable_r = 0.0
                trailing_sl = stop_loss

                for i in range(entry_bar_idx, n_bars):
                    t = times[i]
                    h = highs[i]
                    l = lows[i]
                    c = closes[i]
                    is_eod = (t >= eod_time) or (i == n_bars - 1)

                    # Update favorable excursion
                    fav_r = (h - entry_px) / risk
                    if fav_r > max_favorable_r:
                        max_favorable_r = fav_r
                        # If reached 1.0R, move SL to breakeven + trail 0.5R
                        if max_favorable_r >= 1.0:
                            new_sl = entry_px + ((max_favorable_r - 0.75) * risk)
                            trailing_sl = max(trailing_sl, new_sl)

                    # Check 1.5R
                    if pnl_15r is None:
                        if h >= entry_px + (1.5 * risk):
                            pnl_15r = 1.5
                        elif l <= stop_loss:
                            pnl_15r = -1.0
                        elif is_eod:
                            pnl_15r = (c - entry_px) / risk

                    # Check 2.0R
                    if pnl_20r is None:
                        if h >= entry_px + (2.0 * risk):
                            pnl_20r = 2.0
                        elif l <= stop_loss:
                            pnl_20r = -1.0
                        elif is_eod:
                            pnl_20r = (c - entry_px) / risk

                    # Check 2.5R
                    if pnl_25r is None:
                        if h >= entry_px + (2.5 * risk):
                            pnl_25r = 2.5
                        elif l <= stop_loss:
                            pnl_25r = -1.0
                        elif is_eod:
                            pnl_25r = (c - entry_px) / risk

                    # Check Trailing Stop
                    if pnl_trail is None:
                        if l <= trailing_sl:
                            pnl_trail = (trailing_sl - entry_px) / risk
                        elif is_eod:
                            pnl_trail = (c - entry_px) / risk

                    # Check pure EOD
                    if is_eod and pnl_eod is None:
                        pnl_eod = (c - entry_px) / risk

                raw_signals.append({
                    'symbol': sym,
                    'date': d,
                    'direction': 'LONG',
                    'nifty_confluent': nifty_bullish,
                    'r_15': pnl_15r,
                    'r_20': pnl_20r,
                    'r_25': pnl_25r,
                    'r_trail': pnl_trail,
                    'r_eod': pnl_eod
                })

            elif direction == 'SHORT':
                entry_px = min(low_10, opens[entry_bar_idx])
                stop_loss = entry_px + risk

                pnl_15r = None
                pnl_20r = None
                pnl_25r = None
                pnl_trail = None
                pnl_eod = None

                max_favorable_r = 0.0
                trailing_sl = stop_loss

                for i in range(entry_bar_idx, n_bars):
                    t = times[i]
                    h = highs[i]
                    l = lows[i]
                    c = closes[i]
                    is_eod = (t >= eod_time) or (i == n_bars - 1)

                    fav_r = (entry_px - l) / risk
                    if fav_r > max_favorable_r:
                        max_favorable_r = fav_r
                        if max_favorable_r >= 1.0:
                            new_sl = entry_px - ((max_favorable_r - 0.75) * risk)
                            trailing_sl = min(trailing_sl, new_sl)

                    if pnl_15r is None:
                        if l <= entry_px - (1.5 * risk):
                            pnl_15r = 1.5
                        elif h >= stop_loss:
                            pnl_15r = -1.0
                        elif is_eod:
                            pnl_15r = (entry_px - c) / risk

                    if pnl_20r is None:
                        if l <= entry_px - (2.0 * risk):
                            pnl_20r = 2.0
                        elif h >= stop_loss:
                            pnl_20r = -1.0
                        elif is_eod:
                            pnl_20r = (entry_px - c) / risk

                    if pnl_25r is None:
                        if l <= entry_px - (2.5 * risk):
                            pnl_25r = 2.5
                        elif h >= stop_loss:
                            pnl_25r = -1.0
                        elif is_eod:
                            pnl_25r = (entry_px - c) / risk

                    if pnl_trail is None:
                        if h >= trailing_sl:
                            pnl_trail = (entry_px - trailing_sl) / risk
                        elif is_eod:
                            pnl_trail = (entry_px - c) / risk

                    if is_eod and pnl_eod is None:
                        pnl_eod = (entry_px - c) / risk

                raw_signals.append({
                    'symbol': sym,
                    'date': d,
                    'direction': 'SHORT',
                    'nifty_confluent': nifty_bearish,
                    'r_15': pnl_15r,
                    'r_20': pnl_20r,
                    'r_25': pnl_25r,
                    'r_trail': pnl_trail,
                    'r_eod': pnl_eod
                })

    df_res = pd.DataFrame(raw_signals)
    print(f"\nCaptured a total of {len(df_res)} Stealth Absorption triggers across 3 years.\n", flush=True)

    def print_breakdown(sub_df, title):
        print("=" * 95, flush=True)
        print(f" {title.upper()} (N = {len(sub_df)})", flush=True)
        print("=" * 95, flush=True)
        if sub_df.empty:
            print("No trades found.", flush=True)
            return

        rows = []
        for col, col_name in [('r_15', 'Target 1.5R (SL 1.0R)'),
                              ('r_20', 'Target 2.0R (SL 1.0R)'),
                              ('r_25', 'Target 2.5R (SL 1.0R)'),
                              ('r_trail', 'Trailing Stop (0.75R trail after 1R)'),
                              ('r_eod', 'Pure Intraday Hold (Exit 15:15)')]:
            vals = sub_df[col].dropna()
            n = len(vals)
            wins = (vals > 0).sum()
            wr = (wins / n) * 100.0 if n > 0 else 0
            tot_r = vals.sum()
            avg_r = vals.mean() if n > 0 else 0
            w_sum = vals[vals > 0].sum()
            l_sum = abs(vals[vals < 0].sum())
            pf = (w_sum / l_sum) if l_sum > 0 else np.nan

            rows.append({
                'Exit Mechanism': col_name,
                'Win Rate %': f"{wr:.1f}%",
                'Total Profit (R)': f"{tot_r:+.1f} R",
                'Avg R / Trade': f"{avg_r:+.2f} R",
                'Profit Factor': f"{pf:.2f}"
            })

        print(pd.DataFrame(rows).to_string(index=False), flush=True)
        print("-" * 95, flush=True)

    # 1. Long vs Short Asymmetry
    df_long = df_res[df_res['direction'] == 'LONG']
    df_short = df_res[df_res['direction'] == 'SHORT']
    print_breakdown(df_long, "1. LONG (Bullish Absorption Breakout)")
    print_breakdown(df_short, "2. SHORT (Bearish Distribution Breakdown)")

    # 2. Confluence with NIFTY Filter
    df_long_nifty = df_long[df_long['nifty_confluent'] == True]
    df_long_no_nifty = df_long[df_long['nifty_confluent'] == False]
    print_breakdown(df_long_nifty, "3. LONG + NIFTY Bullish Confluence (Nifty > Open)")
    print_breakdown(df_long_no_nifty, "4. LONG WITHOUT NIFTY Confluence (Nifty < Open)")

if __name__ == '__main__':
    run_study()
