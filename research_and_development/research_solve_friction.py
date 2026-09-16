"""
research_and_development/research_solve_friction.py

Investigating how to overcome the Turnover / Friction drag:
1. What happens if we enforce a minimum stop distance (e.g. Range >= 0.5% to avoid microscopic boxes that cause 100x turnover)?
2. What happens if we aim for larger momentum expansions (3R, 4R, or Trailing trend runners) instead of tight scalps?
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")

POPULAR_STOCKS = [
    'reliance', 'tcs', 'infy', 'hdfcbank', 'icicibank', 'tatamotors', 'sbin', 'bhartiartl', 'lt', 'itc',
    'axisbank', 'bajfinance', 'maruti', 'titan', 'sunpharma', 'kotakbank', 'wipro', 'hcltech', 'ntpc', 'ongc',
    'powergrid', 'ultracemco', 'adanient', 'tatasteel', 'hindunilvr', 'tataelxsi', 'polycab', 'persistent', 'coforge', 'm&m',
    'canbk', 'federalbnk', 'pfc', 'hal', 'bel', 'bhel', 'dlf', 'godrejprop', 'trent', 'vedl',
    'jswsteel', 'hindalco', 'coalindia', 'chamblfert', 'indiamart', 'apollotyre', 'escorst', 'jublfood', 'mrf', 'voltas'
]

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

def calc_nse_charges(buy_val: float, sell_val: float) -> float:
    buy_brokerage = min(20.0, buy_val * 0.0003)
    buy_exchange = buy_val * 0.0000322
    buy_sebi = buy_val * 0.000001
    buy_stamp = buy_val * 0.00003
    buy_gst = 0.18 * (buy_brokerage + buy_exchange + buy_sebi)
    buy_total = buy_brokerage + buy_exchange + buy_sebi + buy_stamp + buy_gst

    sell_brokerage = min(20.0, sell_val * 0.0003)
    sell_stt = sell_val * 0.00025
    sell_exchange = sell_val * 0.0000322
    sell_sebi = sell_val * 0.000001
    sell_gst = 0.18 * (sell_brokerage + sell_exchange + sell_sebi)
    sell_total = sell_brokerage + sell_stt + sell_exchange + sell_sebi + sell_gst

    return buy_total + sell_total

def test_friction_solution():
    print("=" * 105, flush=True)
    print("      QUANTITATIVE POST-MORTEM: SOLVING THE TURNOVER & FRICTION BOTTLENECK", flush=True)
    print("=" * 105, flush=True)

    loaded = {}
    for sym in POPULAR_STOCKS:
        df = load_stock_df(sym, years=3)
        if df is not None:
            loaded[sym] = df

    trigger_cutoff = time(11, 0)
    eod_time = time(15, 14)
    SLIPPAGE_PCT = 0.0005

    # Test two models:
    # Model A: Micro-box (Range <= 0.8%, no minimum) - what we just tested
    # Model B: Balanced Box (0.6% <= Range <= 1.2%) with 3.0R Target / 1.0R Trail
    # Model C: High-Beta Runners (0.8% <= Range <= 1.5%) with 3.5R Target

    models = [
        {"name": "Model A (Micro Box <= 0.8%, Trailing 0.75R)", "min_rng": 0.0, "max_rng": 0.8, "tp_r": 2.0, "trail": True},
        {"name": "Model B (Healthy Box 0.5% - 1.2%, Target 3.0R)", "min_rng": 0.5, "max_rng": 1.2, "tp_r": 3.0, "trail": False},
        {"name": "Model C (Healthy Box 0.5% - 1.2%, Trailing 1.0R after 1.5R)", "min_rng": 0.5, "max_rng": 1.2, "tp_r": 4.0, "trail": True},
    ]

    for m in models:
        trades = []
        for sym, df in loaded.items():
            grouped = df.groupby('date')
            dates = list(grouped.groups.keys())

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

                if pd.isna(rvol) or rvol < 1.5:
                    continue
                if range_pct < m['min_rng'] or range_pct > m['max_rng']:
                    continue

                risk = high_10 - low_10
                if risk <= 0:
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
                n_bars = len(post)

                triggered = False
                entry_idx = -1
                entry_px = 0.0

                for i in range(n_bars):
                    t = times[i]
                    h = highs[i]
                    o = opens[i]
                    if t > trigger_cutoff:
                        break
                    if h > high_10:
                        triggered = True
                        entry_idx = i
                        entry_px = max(high_10, o)
                        break

                if not triggered:
                    continue

                stop_loss = entry_px - risk
                target_px = entry_px + (m['tp_r'] * risk)
                trailing_sl = stop_loss
                max_fav_r = 0.0
                exit_px = 0.0

                for i in range(entry_idx, n_bars):
                    t = times[i]
                    h = highs[i]
                    l = lows[i]
                    c = closes[i]
                    is_eod = (t >= eod_time) or (i == n_bars - 1)

                    fav_r = (h - entry_px) / risk
                    if fav_r > max_fav_r:
                        max_fav_r = fav_r
                        if m['trail'] and max_fav_r >= 1.5:
                            new_sl = entry_px + ((max_fav_r - 1.0) * risk)
                            trailing_sl = max(trailing_sl, new_sl)

                    if not m['trail']:
                        if h >= target_px:
                            exit_px = target_px
                            break
                        elif l <= stop_loss:
                            exit_px = stop_loss
                            break
                        elif is_eod:
                            exit_px = c
                            break
                    else:
                        if h >= target_px:
                            exit_px = target_px
                            break
                        elif l <= trailing_sl:
                            exit_px = trailing_sl
                            break
                        elif is_eod:
                            exit_px = c
                            break

                if exit_px > 0:
                    trades.append({
                        'entry': entry_px,
                        'exit': exit_px,
                        'risk': risk,
                        'range_pct': range_pct
                    })

        # Calculate with 1R = Rs. 2,500
        TARGET_1R = 2500.0
        gross_list, net_list, charges_list, slip_list = [], [], [], []

        for tr in trades:
            qty = max(1, int(TARGET_1R / tr['risk']))
            r_ent = tr['entry'] * (1.0 + SLIPPAGE_PCT)
            r_ex = tr['exit'] * (1.0 - SLIPPAGE_PCT)
            b_val = r_ent * qty
            s_val = r_ex * qty
            chg = calc_nse_charges(b_val, s_val)
            slip = ((r_ent - tr['entry']) + (tr['exit'] - r_ex)) * qty
            gr = (tr['exit'] - tr['entry']) * qty
            nt = (r_ex - r_ent) * qty - chg

            gross_list.append(gr)
            net_list.append(nt)
            charges_list.append(chg)
            slip_list.append(slip)

        df_t = pd.DataFrame({'gr': gross_list, 'nt': net_list, 'chg': charges_list, 'slp': slip_list})
        n = len(df_t)
        if n == 0:
            continue
        gr_tot = df_t['gr'].sum()
        nt_tot = df_t['nt'].sum()
        chg_tot = df_t['chg'].sum()
        slp_tot = df_t['slp'].sum()
        nt_wins = (df_t['nt'] > 0).sum()
        nt_wr = (nt_wins / n) * 100.0
        nt_gain = df_t[df_t['nt'] > 0]['nt'].sum()
        nt_loss = abs(df_t[df_t['nt'] < 0]['nt'].sum())
        pf = (nt_gain / nt_loss) if nt_loss > 0 else np.nan

        print(f"\n--- {m['name']} (N = {n} trades) ---")
        print(f"  Gross Profit       : Rs. {int(gr_tot):,}")
        print(f"  Taxes + Brokerage  : Rs. -{int(chg_tot):,}")
        print(f"  Slippage (0.1%)    : Rs. -{int(slp_tot):,}")
        print(f"  Net Realized Profit: Rs. {int(nt_tot):,}")
        print(f"  Net Win Rate       : {nt_wr:.1f}%")
        print(f"  Net Profit Factor  : {pf:.2f}")

if __name__ == '__main__':
    test_friction_solution()
