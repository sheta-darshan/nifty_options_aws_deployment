"""
research_and_development/research_friction_and_taxes_audit.py

Step 1: Realistic Friction Audit for Opening Stealth Momentum Strategy
Calculates:
  - Exact NSE & Dhan Cash Intraday (MIS) Statutory Charges:
      * Brokerage: min(₹20, 0.03% turnover) per leg
      * STT: 0.025% on sell side
      * Exchange Turnover Fee: 0.00322% on turnover
      * Stamp Duty: 0.003% on buy side
      * SEBI Fee: ₹10 per crore (0.0001%)
      * GST: 18% on (Brokerage + Exchange + SEBI)
  - Realistic Slippage: 0.05% on Entry + 0.05% on Exit (0.10% total friction)
  - Evaluates performance across 3 Risk Tiers:
      * 1R = ₹1,000
      * 1R = ₹2,500
      * 1R = ₹5,000
Tests on all 870 trades over 3 Years across 96 liquid stocks.
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
    'jswsteel', 'hindalco', 'coalindia', 'chamblfert', 'indiamart', 'apollotyre', 'escorst', 'jublfood', 'mrf', 'voltas',
    'irb', 'abfrl', 'cgcl', 'unominda', 'ipcalab', 'srf', 'whirlpool', 'ioc', 'cesc', 'pcbl',
    'vtl', 'aplapollo', 'schaeffler', 'gpil', 'motilaloys', 'bsoft', 'lupin', 'cipla', 'drreddy', 'apollohosp',
    'havells', 'pidilitind', 'siemens', 'abb', 'cumminsind', 'techm', 'ashokley', 'eichermot', 'heromotoco', 'tvs_motor',
    'sail', 'jindalstel', 'nmdc', 'nationalum', 'hindcopper', 'gnfc', 'deepakntr', 'upl', 'atgl', 'adaniports',
    'grasim', 'ambujacem', 'acc', 'dalbharat', 'divislab', 'biocon', 'syngene', 'alkem', 'torrentpha', 'glenmark'
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
    """Exact statutory fee structure matching backtest_engine.py."""
    # Buy side
    buy_brokerage = min(20.0, buy_val * 0.0003)
    buy_exchange = buy_val * 0.0000322
    buy_sebi = buy_val * 0.000001
    buy_stamp = buy_val * 0.00003
    buy_gst = 0.18 * (buy_brokerage + buy_exchange + buy_sebi)
    buy_total = buy_brokerage + buy_exchange + buy_sebi + buy_stamp + buy_gst

    # Sell side
    sell_brokerage = min(20.0, sell_val * 0.0003)
    sell_stt = sell_val * 0.00025  # 0.025% on sell side for intraday cash equity
    sell_exchange = sell_val * 0.0000322
    sell_sebi = sell_val * 0.000001
    sell_gst = 0.18 * (sell_brokerage + sell_exchange + sell_sebi)
    sell_total = sell_brokerage + sell_stt + sell_exchange + sell_sebi + sell_gst

    return buy_total + sell_total

def run_friction_audit():
    print("=" * 105, flush=True)
    print("      STEP 1: REALISTIC FRICTION AUDIT (TAXES, BROKERAGE & SLIPPAGE) ON 3-YEAR DATA", flush=True)
    print("=" * 105, flush=True)

    loaded_stocks = {}
    for sym in POPULAR_STOCKS:
        df = load_stock_df(sym, years=3)
        if df is not None:
            loaded_stocks[sym] = df

    print(f"Loaded {len(loaded_stocks)} liquid stocks for audit.\n", flush=True)

    trigger_cutoff = time(11, 0)
    eod_time = time(15, 14)
    SLIPPAGE_PCT = 0.0005  # 0.05% per leg

    raw_trades = []

    for sym, df in loaded_stocks.items():
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

        for d in dates[25:]:
            if d not in df_stats.index:
                continue
            meta = df_stats.loc[d]
            rvol = meta['rvol']
            range_pct = meta['range_pct']
            high_10 = meta['high_10']
            low_10 = meta['low_10']
            open_px = meta['open_px']

            # Setup filter: RVOL >= 1.5, Range <= 0.8%
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
            opens = post['open'].values
            highs = post['high'].values
            lows = post['low'].values
            closes = post['close'].values
            n_bars = len(post)

            # Long breakout trigger
            triggered = False
            entry_idx = -1
            clean_entry_px = 0.0

            for i in range(n_bars):
                t = times[i]
                h = highs[i]
                o = opens[i]
                if t > trigger_cutoff:
                    break
                if h > high_10:
                    triggered = True
                    entry_idx = i
                    clean_entry_px = max(high_10, o)
                    break

            if not triggered:
                continue

            # Trailing stop exit simulation (0.75R trailing after reaching +1.0R)
            stop_loss = clean_entry_px - risk_per_share
            trailing_sl = stop_loss
            max_fav_r = 0.0
            clean_exit_px = 0.0
            exit_reason = None

            for i in range(entry_idx, n_bars):
                t = times[i]
                h = highs[i]
                l = lows[i]
                c = closes[i]
                is_eod = (t >= eod_time) or (i == n_bars - 1)

                fav_r = (h - clean_entry_px) / risk_per_share
                if fav_r > max_fav_r:
                    max_fav_r = fav_r
                    if max_fav_r >= 1.0:
                        new_sl = clean_entry_px + ((max_fav_r - 0.75) * risk_per_share)
                        trailing_sl = max(trailing_sl, new_sl)

                if l <= trailing_sl:
                    clean_exit_px = trailing_sl
                    exit_reason = "TRAIL_OR_SL"
                    break
                elif is_eod:
                    clean_exit_px = c
                    exit_reason = "EOD"
                    break

            if clean_exit_px > 0:
                raw_trades.append({
                    'symbol': sym,
                    'date': d,
                    'clean_entry': clean_entry_px,
                    'clean_exit': clean_exit_px,
                    'risk_per_share': risk_per_share,
                    'exit_reason': exit_reason
                })

    print(f"Auditing {len(raw_trades)} Long trades through real-world execution friction...\n", flush=True)

    risk_tiers = [1000.0, 2500.0, 5000.0, 10000.0]

    tier_results = []

    for target_risk in risk_tiers:
        gross_pnl_list = []
        net_pnl_list = []
        charges_list = []
        slippage_list = []

        for tr in raw_trades:
            clean_entry = tr['clean_entry']
            clean_exit = tr['clean_exit']
            risk_ps = tr['risk_per_share']

            # Sizing: quantity based on target risk
            qty = max(1, int(target_risk / risk_ps))

            # Apply realistic slippage
            real_entry = clean_entry * (1.0 + SLIPPAGE_PCT)
            real_exit = clean_exit * (1.0 - SLIPPAGE_PCT)

            buy_val = real_entry * qty
            sell_val = real_exit * qty

            charges = calc_nse_charges(buy_val, sell_val)
            charges_list.append(charges)

            slippage_cost = ((real_entry - clean_entry) + (clean_exit - real_exit)) * qty
            slippage_list.append(slippage_cost)

            gross_pnl = (clean_exit - clean_entry) * qty
            gross_pnl_list.append(gross_pnl)

            net_pnl = (real_exit - real_entry) * qty - charges
            net_pnl_list.append(net_pnl)

        df_res = pd.DataFrame({
            'gross': gross_pnl_list,
            'net': net_pnl_list,
            'charges': charges_list,
            'slippage': slippage_list
        })

        n = len(df_res)
        gross_tot = df_res['gross'].sum()
        net_tot = df_res['net'].sum()
        charges_tot = df_res['charges'].sum()
        slip_tot = df_res['slippage'].sum()

        gross_wins = (df_res['gross'] > 0).sum()
        gross_wr = (gross_wins / n) * 100.0

        net_wins = (df_res['net'] > 0).sum()
        net_wr = (net_wins / n) * 100.0

        # Profit Factor
        net_gain = df_res[df_res['net'] > 0]['net'].sum()
        net_loss = abs(df_res[df_res['net'] < 0]['net'].sum())
        net_pf = (net_gain / net_loss) if net_loss > 0 else np.nan

        tier_results.append({
            'Risk Per Trade (1R)': f"Rs. {int(target_risk):,}",
            'Gross Profit': f"Rs. {int(gross_tot):,}",
            'Brokerage & Taxes': f"Rs. -{int(charges_tot):,}",
            'Slippage Cost (0.1%)': f"Rs. -{int(slip_tot):,}",
            'Net Realized Profit': f"Rs. {int(net_tot):,}",
            'Net Win Rate': f"{net_wr:.1f}%",
            'Net Profit Factor': f"{net_pf:.2f}",
            'Net R / Trade': f"+{(net_tot / (n * target_risk)):.2f} R"
        })

    summary_df = pd.DataFrame(tier_results)
    print(summary_df.to_string(index=False), flush=True)
    print("=" * 105, flush=True)

if __name__ == '__main__':
    run_friction_audit()
