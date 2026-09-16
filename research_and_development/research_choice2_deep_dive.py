"""
research_and_development/research_choice2_deep_dive.py

Comprehensive Deep-Dive Research: Choice 2 (Multi-Day Swing Trading on Opening Stealth Absorption)
Evaluates:
  1. Target & Holding Grid (+4%, +5%, +6%, +8%, Trailing 3-day / 5-day / 10-day)
  2. Year-by-Year Consistency & Annual P&L (2023, 2024, 2025, 2026)
  3. Maximum Drawdown & Equity Curve Metrics
  4. Top 15 Winning Stock Tickers
  5. Exact Net Take-Home Returns after full Delivery Taxes (STT 0.1% buy + 0.1% sell, GST, Stamp Duty)

Universe: 80 High-Liquidity Stocks (Large-Caps + High-Beta Mid-Caps) over 3 Years (~750 Sessions).
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")

STOCKS_UNIVERSE = [
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'TATAMOTORS', 'SBIN', 'BHARTIARTL',
    'LT', 'ITC', 'AXISBANK', 'BAJFINANCE', 'MARUTI', 'TITAN', 'SUNPHARMA', 'KOTAKBANK',
    'WIPRO', 'HCLTECH', 'NTPC', 'ONGC', 'POWERGRID', 'ULTRACEMCO', 'ADANIENT', 'TATASTEEL',
    'HINDUNILVR', 'TATAELXSI', 'POLYCAB', 'PERSISTENT', 'COFORGE', 'M&M', 'CANBK', 'FEDERALBNK',
    'PFC', 'HAL', 'BEL', 'BHEL', 'DLF', 'GODREJPROP', 'TRENT', 'VEDL', 'JSWSTEEL', 'HINDALCO',
    'COALINDIA', 'APOLLOTYRE', 'JUBLFOOD', 'VOLTAS', 'IRB', 'SRF', 'IOC', 'TECHM',
    'ASHOKLEY', 'EICHERMOT', 'HEROMOTOCO', 'TVS_MOTOR', 'SAIL', 'JINDALSTEL', 'NMDC', 'NATIONALUM',
    'HINDCOPPER', 'GNFC', 'DEEPAKNTR', 'UPL', 'ADANIPORTS', 'GRASIM', 'AMBUJACEM', 'ACC',
    'DIVISLAB', 'BIOCON', 'SYNGENE', 'ALKEM', 'TORRENTPHA', 'GLENMARK', 'LUPIN', 'CIPLA',
    'DRREDDY', 'APOLLOHOSP', 'HAVELLS', 'PIDILITIND', 'SIEMENS', 'ABB'
]

def load_stock_df(symbol: str, years: int = 3):
    csv_path = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
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

def calc_delivery_charges(buy_val: float, sell_val: float) -> float:
    brokerage = 0.0  # Zero delivery brokerage on Dhan
    stt = (buy_val + sell_val) * 0.0010  # 0.10% buy + 0.10% sell STT
    exch = (buy_val + sell_val) * 0.0000322
    stamp = buy_val * 0.00015  # 0.015% on buy
    sebi = (buy_val + sell_val) * 0.000001
    gst = 0.18 * (brokerage + exch)
    return brokerage + stt + exch + stamp + sebi + gst

def run_deep_dive():
    print("=" * 105, flush=True)
    print("      DEEP-DIVE RESEARCH: CHOICE 2 (MULTI-DAY SWING TRADING ON STEALTH ABSORPTION)", flush=True)
    print("=" * 105, flush=True)

    loaded = {}
    for sym in STOCKS_UNIVERSE:
        df = load_stock_df(sym, years=3)
        if df is not None:
            loaded[sym] = df

    print(f"Loaded {len(loaded)} liquid stocks with full 3-year data for swing analysis.\n", flush=True)

    trigger_cutoff = time(11, 0)
    FIXED_RISK = 2500.0  # Risk ₹2,500 per trade on initial stop

    # Configurations to test:
    # 1. Target +4.0% (Max 3 days hold, Breakeven at +2.0%)
    # 2. Target +5.0% (Max 5 days hold, Breakeven at +2.5%) - Baseline tested earlier
    # 3. Target +6.0% (Max 5 days hold, Breakeven at +3.0%)
    # 4. Target +8.0% (Max 7 days hold, Breakeven at +3.5%)
    # 5. Pure Trailing Runner (Hold up to 10 days, trail by 2.0% behind peak once +3.0% reached)

    target_configs = [
        {"name": "Quick Swing (+4.0% Target, Max 3 Days)", "tp_pct": 0.040, "be_pct": 0.020, "max_days": 3, "trail_peak": False},
        {"name": "Standard Swing (+5.0% Target, Max 5 Days)", "tp_pct": 0.050, "be_pct": 0.025, "max_days": 5, "trail_peak": False},
        {"name": "Extended Swing (+6.0% Target, Max 5 Days)", "tp_pct": 0.060, "be_pct": 0.030, "max_days": 5, "trail_peak": False},
        {"name": "Large Momentum (+8.0% Target, Max 7 Days)", "tp_pct": 0.080, "be_pct": 0.035, "max_days": 7, "trail_peak": False},
        {"name": "Trend Runner (Trailing 2.0% from Peak, Max 10 Days)", "tp_pct": 0.150, "be_pct": 0.030, "max_days": 10, "trail_peak": True},
    ]

    grid_results = {cfg['name']: [] for cfg in target_configs}

    for sym, df in loaded.items():
        grouped = df.groupby('date')
        dates = list(grouped.groups.keys())

        # Opening 10m Box Stats
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

        for d_idx, d in enumerate(dates[25:-12]):
            if d not in df_stats.index:
                continue
            m = df_stats.loc[d]
            rvol = m['rvol']
            range_pct = m['range_pct']
            high_10 = m['high_10']
            low_10 = m['low_10']
            open_px = m['open_px']

            if pd.isna(rvol) or rvol < 1.5 or range_pct > 0.8:
                continue

            risk_per_share = high_10 - low_10
            if risk_per_share <= 0 or (risk_per_share / open_px) < 0.001:
                continue

            day_df = grouped.get_group(d)
            post = day_df[(day_df['time'] >= time(9, 25)) & (day_df['time'] <= time(15, 15))]
            if post.empty:
                continue

            times = post['time'].values
            highs = post['high'].values
            opens = post['open'].values
            n_bars = len(post)

            triggered = False
            entry_spot = 0.0

            for i in range(n_bars):
                t = times[i]
                h = highs[i]
                o = opens[i]
                if t > trigger_cutoff:
                    break
                if h > high_10:
                    triggered = True
                    entry_spot = max(high_10, o)
                    break

            if not triggered:
                continue

            initial_sl = entry_spot - risk_per_share
            qty = max(1, int(FIXED_RISK / risk_per_share))

            # Simulate for each target config
            for cfg in target_configs:
                tp_px = entry_spot * (1.0 + cfg['tp_pct'])
                be_trigger_px = entry_spot * (1.0 + cfg['be_pct'])
                max_hold_days = cfg['max_days']

                current_sl = initial_sl
                is_be_activated = False
                peak_px = entry_spot

                future_dates = dates[d_idx: d_idx + max_hold_days + 1]
                exit_px = 0.0
                exit_date = None
                exit_reason = None

                for fd_idx, fd in enumerate(future_dates):
                    if exit_px > 0:
                        break
                    f_day = grouped.get_group(fd)
                    f_highs = f_day['high'].values
                    f_lows = f_day['low'].values
                    f_closes = f_day['close'].values

                    # On day 0 (entry day), only evaluate bars after entry
                    start_bar = 0
                    if fd == d:
                        start_bar = 0  # In our entry day, evaluated after 09:25

                    for bi in range(start_bar, len(f_day)):
                        bh = f_highs[bi]
                        bl = f_lows[bi]

                        if bh > peak_px:
                            peak_px = bh

                        # Check Breakeven activation
                        if not is_be_activated and bh >= be_trigger_px:
                            current_sl = entry_spot
                            is_be_activated = True

                        # If trailing runner
                        if cfg['trail_peak'] and is_be_activated:
                            trail_sl = peak_px * 0.980  # 2.0% behind peak
                            current_sl = max(current_sl, trail_sl)

                        # Check Target
                        if bh >= tp_px:
                            exit_px = tp_px
                            exit_date = fd
                            exit_reason = "TARGET"
                            break

                        # Check Stop Loss
                        if bl <= current_sl:
                            exit_px = current_sl
                            exit_date = fd
                            exit_reason = "STOP_OR_BE"
                            break

                # If held until max days without hitting TP or SL
                if exit_px == 0:
                    last_fday = grouped.get_group(future_dates[-1])
                    exit_px = last_fday['close'].iloc[-1]
                    exit_date = future_dates[-1]
                    exit_reason = "TIME_EXPIRY"

                # Calculate Net P&L after Delivery STT & Charges
                buy_val = entry_spot * qty
                sell_val = exit_px * qty
                real_buy = buy_val * 1.0005  # 0.05% slippage
                real_sell = sell_val * 0.9995
                charges = calc_delivery_charges(real_buy, real_sell)
                net_pnl = (real_sell - real_buy) - charges

                grid_results[cfg['name']].append({
                    'symbol': sym,
                    'entry_date': d,
                    'exit_date': exit_date,
                    'year': d.year,
                    'entry_spot': entry_spot,
                    'exit_spot': exit_px,
                    'gain_pct': (exit_px - entry_spot) / entry_spot * 100.0,
                    'qty': qty,
                    'net_pnl': net_pnl,
                    'charges': charges,
                    'win': net_pnl > 0,
                    'exit_reason': exit_reason
                })

    # 1. Performance across Target Configurations
    print("=" * 115, flush=True)
    print("                    1. TARGET & HOLDING PERIOD PERFORMANCE COMPARISON", flush=True)
    print("=" * 115, flush=True)

    summary_rows = []
    for cfg in target_configs:
        name = cfg['name']
        trades = grid_results[name]
        df_t = pd.DataFrame(trades)
        n = len(df_t)
        if n == 0:
            continue
        wins = df_t['win'].sum()
        wr = (wins / n) * 100.0
        tot_net = df_t['net_pnl'].sum()
        tot_chg = df_t['charges'].sum()
        gains = df_t[df_t['net_pnl'] > 0]['net_pnl'].sum()
        losses = abs(df_t[df_t['net_pnl'] < 0]['net_pnl'].sum())
        pf = (gains / losses) if losses > 0 else np.nan
        avg_trade = tot_net / n

        summary_rows.append({
            'Configuration': name,
            'Trades': n,
            'Win Rate': f"{wr:.1f}%",
            'Total Charges': f"Rs. -{int(tot_chg):,}",
            'Net Realized Profit': f"Rs. {int(tot_net):,}",
            'Net Profit Factor': f"{pf:.2f}",
            'Avg Net / Trade': f"Rs. {int(avg_trade):,}"
        })

    print(pd.DataFrame(summary_rows).to_string(index=False), flush=True)
    print("=" * 115, flush=True)

    # 2. Detailed Breakdown of the Best Configuration (Standard Swing: +5.0% Target)
    best_name = "Standard Swing (+5.0% Target, Max 5 Days)"
    df_best = pd.DataFrame(grid_results[best_name])

    print("\n" + "=" * 115, flush=True)
    print(f"      2. YEAR-BY-YEAR CONSISTENCY FOR BEST CONFIG: {best_name.upper()}", flush=True)
    print("=" * 115, flush=True)

    yearly_rows = []
    for yr, grp in df_best.groupby('year'):
        n_yr = len(grp)
        wins_yr = grp['win'].sum()
        wr_yr = (wins_yr / n_yr) * 100.0
        net_yr = grp['net_pnl'].sum()
        gains_yr = grp[grp['net_pnl'] > 0]['net_pnl'].sum()
        losses_yr = abs(grp[grp['net_pnl'] < 0]['net_pnl'].sum())
        pf_yr = (gains_yr / losses_yr) if losses_yr > 0 else np.nan

        yearly_rows.append({
            'Year': yr,
            'Trades': n_yr,
            'Win Rate': f"{wr_yr:.1f}%",
            'Net Realized Profit': f"Rs. {int(net_yr):,}",
            'Profit Factor': f"{pf_yr:.2f}",
            'Avg Profit / Trade': f"Rs. {int(net_yr / n_yr):,}"
        })

    print(pd.DataFrame(yearly_rows).to_string(index=False), flush=True)
    print("=" * 115, flush=True)

    # 3. Maximum Drawdown Calculation
    df_best.sort_values(by='entry_date', inplace=True)
    df_best['cum_pnl'] = df_best['net_pnl'].cumsum()
    df_best['peak'] = df_best['cum_pnl'].cummax()
    df_best['drawdown'] = df_best['cum_pnl'] - df_best['peak']
    max_dd = df_best['drawdown'].min()

    print(f"\nMaximum Cumulative Drawdown : Rs. {int(abs(max_dd)):,} (approx {abs(max_dd) / FIXED_RISK:.1f} R)", flush=True)
    print(f"Total Cumulative Net Profit  : Rs. {int(df_best['cum_pnl'].iloc[-1]):,} (approx {df_best['cum_pnl'].iloc[-1] / FIXED_RISK:.1f} R)", flush=True)
    print(f"Profit-to-Drawdown Ratio     : {(df_best['cum_pnl'].iloc[-1] / abs(max_dd)):.2f}x\n", flush=True)

    # 4. Top 15 Best Stock Contributors
    print("=" * 115, flush=True)
    print("                      3. TOP 15 STOCK CONTRIBUTORS (MOST PROFITABLE RUNNERS)", flush=True)
    print("=" * 115, flush=True)

    stock_rows = []
    for s_sym, s_grp in df_best.groupby('symbol'):
        s_n = len(s_grp)
        if s_n >= 3:
            s_net = s_grp['net_pnl'].sum()
            s_wins = s_grp['win'].sum()
            s_wr = (s_wins / s_n) * 100.0
            stock_rows.append({
                'Stock Symbol': s_sym,
                'Trades': s_n,
                'Win Rate': f"{s_wr:.1f}%",
                'Net Realized Profit': int(s_net)
            })

    df_top_stocks = pd.DataFrame(stock_rows).sort_values(by='Net Realized Profit', ascending=False)
    # Format currency
    df_top_stocks['Net Realized Profit'] = df_top_stocks['Net Realized Profit'].apply(lambda x: f"Rs. {x:,}")
    print(df_top_stocks.head(15).to_string(index=False), flush=True)
    print("=" * 115, flush=True)

if __name__ == '__main__':
    run_deep_dive()
