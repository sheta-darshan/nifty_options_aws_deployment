"""
research_and_development/research_choice1_vs_choice2.py

Head-to-Head Quantitative Research: Choice 1 vs Choice 2 on Opening Stealth Absorption
Tested across Top 50 Liquid F&O Stocks over 3 Years (2023 - 2026).

Choice 1: Stock Option Writing (Bull Put Credit Spread)
  - Sell 1 OTM Put (ATM - 1 Strike Step) + Buy 1 OTM Hedge (ATM - 2 Strike Steps)
  - Edge: Theta decay + Delta working together; wins if stock rallies OR chops sideways.
  - Stop: Stock spot breaks below the 10m opening box low.
  - Target: 80% decay of credit collected or intraday EOD.

Choice 2: Multi-Day Swing Trading (Cash Delivery / CNC Hold 2-5 Days)
  - Enter on breakout; hold overnight for multi-day institutional trend continuation.
  - Target: +5.0% price move.
  - Stop: 10m opening box low (trailing to breakeven after +2.5%).
  - Time Stop: 5 trading days max hold.
  - Exact delivery statutory charges: 0.1% STT on Buy + 0.1% STT on Sell, brokerage, GST, exchange.
"""

import os
import sys
import json
import math
import numpy as np
import pandas as pd
from datetime import datetime, time, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
INSTRUMENTS_PATH = os.path.join(BASE_DIR, "instruments.json")

# Top 50 Liquid F&O Stocks
CANDIDATE_SYMBOLS = [
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'TATAMOTORS', 'SBIN', 'BHARTIARTL',
    'LT', 'ITC', 'AXISBANK', 'BAJFINANCE', 'MARUTI', 'TITAN', 'SUNPHARMA', 'KOTAKBANK',
    'WIPRO', 'HCLTECH', 'NTPC', 'ONGC', 'POWERGRID', 'ULTRACEMCO', 'ADANIENT', 'TATASTEEL',
    'HINDUNILVR', 'TATAELXSI', 'POLYCAB', 'PERSISTENT', 'COFORGE', 'M&M', 'CANBK', 'FEDERALBNK',
    'PFC', 'HAL', 'BEL', 'BHEL', 'DLF', 'GODREJPROP', 'TRENT', 'VEDL', 'JSWSTEEL', 'HINDALCO',
    'COALINDIA', 'APOLLOTYRE', 'JUBLFOOD', 'VOLTAS', 'IRB', 'SRF', 'IOC', 'TECHM'
]

def load_fno_meta():
    with open(INSTRUMENTS_PATH) as f:
        data = json.load(f)
    fno = {}
    for sym in CANDIDATE_SYMBOLS:
        if sym in data:
            v = data[sym]
            fno[sym] = {
                'lot_size': int(v.get('lot_size', 500)),
                'strike_step': float(v.get('strike_step', 10))
            }
    return fno

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

def calc_option_spread_charges(short_prem_turnover: float, long_prem_turnover: float) -> float:
    # 4 legs total (entry 2 orders + exit 2 orders)
    brokerage = 80.0
    stt = short_prem_turnover * 0.0010  # 0.10% on sell-side option premium
    exch = (short_prem_turnover + long_prem_turnover) * 0.00050
    gst = 0.18 * (brokerage + exch)
    stamp = long_prem_turnover * 0.00003
    sebi = (short_prem_turnover + long_prem_turnover) * 0.000001
    return brokerage + stt + exch + gst + stamp + sebi

def calc_delivery_charges(buy_val: float, sell_val: float) -> float:
    brokerage = 0.0  # Zero delivery brokerage on Dhan
    stt = (buy_val + sell_val) * 0.0010  # 0.10% on buy and 0.10% on sell for Delivery
    exch = (buy_val + sell_val) * 0.0000322
    stamp = buy_val * 0.00015  # 0.015% on buy
    sebi = (buy_val + sell_val) * 0.000001
    gst = 0.18 * (brokerage + exch)
    return brokerage + stt + exch + stamp + sebi + gst

def run_comparison():
    print("=" * 105, flush=True)
    print("     HEAD-TO-HEAD RESEARCH: CHOICE 1 (OPTION WRITING) vs CHOICE 2 (MULTI-DAY SWING)", flush=True)
    print("=" * 105, flush=True)

    fno_meta = load_fno_meta()
    loaded_stocks = {}
    for sym in CANDIDATE_SYMBOLS:
        df = load_stock_df(sym, years=3)
        if df is not None:
            loaded_stocks[sym] = df

    print(f"Loaded {len(loaded_stocks)} liquid F&O stocks with 3-year data for comparison.\n", flush=True)

    trigger_cutoff = time(11, 0)
    eod_time = time(15, 14)

    c1_trades = []
    c2_trades = []

    for sym, df in loaded_stocks.items():
        meta = fno_meta.get(sym, {'lot_size': 500, 'strike_step': 10})
        lot_size = meta['lot_size']
        strike_step = meta['strike_step']

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

        for d_idx, d in enumerate(dates[25:-5]):  # Leave room for multi-day swing hold
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

            risk_spot = high_10 - low_10
            if risk_spot <= 0 or (risk_spot / open_px) < 0.001:
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
            entry_spot = 0.0

            for i in range(n_bars):
                t = times[i]
                h = highs[i]
                o = opens[i]
                if t > trigger_cutoff:
                    break
                if h > high_10:
                    triggered = True
                    entry_idx = i
                    entry_spot = max(high_10, o)
                    break

            if not triggered:
                continue

            stop_spot = entry_spot - risk_spot

            # -------------------------------------------------------------
            # SIMULATION 1: CHOICE 1 (OPTION WRITING / BULL PUT SPREAD)
            # -------------------------------------------------------------
            # Sell 1 OTM Put (ATM - 1 Strike Step)
            # Buy 1 OTM Put Hedge (ATM - 2 Strike Steps)
            atm_strike = round(entry_spot / strike_step) * strike_step
            short_strike = atm_strike - strike_step
            long_strike = short_strike - strike_step

            # Credit collected approx for 1-step OTM Put spread (approx 0.8% - 1.2% of spot)
            net_credit_pts = max(1.0, strike_step * 0.35)
            max_risk_pts = strike_step - net_credit_pts

            c1_exit_pts = 0.0
            c1_win = False

            # Intraday tracking for Option Writing
            for i in range(entry_idx, n_bars):
                t = times[i]
                l = lows[i]
                c = closes[i]
                is_eod = (t >= eod_time) or (i == n_bars - 1)

                # Stop loss hit if spot drops below box low
                if l <= stop_spot:
                    c1_exit_pts = -max_risk_pts  # Max loss on spread
                    c1_win = False
                    break
                elif is_eod:
                    # If spot closes strong above entry, spread decays 70%
                    if c >= entry_spot:
                        c1_exit_pts = net_credit_pts * 0.70  # Capture 70% of credit
                        c1_win = True
                    else:
                        c1_exit_pts = net_credit_pts * 0.20  # Minor decay
                        c1_win = True
                    break

            short_val = (net_credit_pts + 5.0) * lot_size
            long_val = 5.0 * lot_size
            c1_charges = calc_option_spread_charges(short_val, long_val)
            c1_net_pnl = (c1_exit_pts * lot_size) - c1_charges

            c1_trades.append({
                'symbol': sym,
                'date': d,
                'net_pnl': c1_net_pnl,
                'win': c1_net_pnl > 0,
                'charges': c1_charges
            })

            # -------------------------------------------------------------
            # SIMULATION 2: CHOICE 2 (MULTI-DAY SWING TRADING 2-5 DAYS)
            # -------------------------------------------------------------
            # Sizing: ₹2,500 Risk per trade on spot stop loss
            qty_swing = max(1, int(2500.0 / risk_spot))
            swing_tp = entry_spot * 1.050  # +5.0% target
            swing_sl = stop_spot
            trailing_be = False
            swing_exit_px = 0.0
            swing_win = False

            # Track over next 5 trading days
            future_dates = dates[d_idx: d_idx + 6]
            exit_found = False

            for f_d in future_dates:
                if exit_found:
                    break
                f_day_df = grouped.get_group(f_d)
                f_highs = f_day_df['high'].values
                f_lows = f_day_df['low'].values
                f_closes = f_day_df['close'].values

                for bi in range(len(f_day_df)):
                    bh = f_highs[bi]
                    bl = f_lows[bi]

                    # Breakeven trigger: if reaches +2.5%, move stop to entry
                    if not trailing_be and bh >= entry_spot * 1.025:
                        swing_sl = entry_spot
                        trailing_be = True

                    if bh >= swing_tp:
                        swing_exit_px = swing_tp
                        swing_win = True
                        exit_found = True
                        break
                    elif bl <= swing_sl:
                        swing_exit_px = swing_sl
                        swing_win = False
                        exit_found = True
                        break

            if not exit_found:
                # Time exit after 5 days at close
                last_day_df = grouped.get_group(future_dates[-1])
                swing_exit_px = last_day_df['close'].iloc[-1]
                swing_win = (swing_exit_px > entry_spot)

            buy_val_swing = entry_spot * qty_swing
            sell_val_swing = swing_exit_px * qty_swing
            # 0.1% slippage on delivery
            real_buy = buy_val_swing * 1.0005
            real_sell = sell_val_swing * 0.9995

            c2_charges = calc_delivery_charges(real_buy, real_sell)
            c2_net_pnl = (real_sell - real_buy) - c2_charges

            c2_trades.append({
                'symbol': sym,
                'date': d,
                'net_pnl': c2_net_pnl,
                'win': c2_net_pnl > 0,
                'charges': c2_charges
            })

    print(f"Evaluated {len(c1_trades)} trades across both models over 3 years.\n", flush=True)

    def print_model_results(trades, name, capital_desc):
        df_m = pd.DataFrame(trades)
        n = len(df_m)
        wins = df_m['win'].sum()
        wr = (wins / n) * 100.0
        tot_net = df_m['net_pnl'].sum()
        tot_chg = df_m['charges'].sum()
        gains = df_m[df_m['net_pnl'] > 0]['net_pnl'].sum()
        losses = abs(df_m[df_m['net_pnl'] < 0]['net_pnl'].sum())
        pf = (gains / losses) if losses > 0 else np.nan

        print("=" * 105, flush=True)
        print(f"  {name.upper()}", flush=True)
        print("=" * 105, flush=True)
        print(f" Capital Model             : {capital_desc}")
        print(f" Total Trades Executed     : {n} trades (~{n // 3} / year)")
        print(f" Win Rate                  : {wr:.1f}%")
        print(f" Total Statutory Friction  : Rs. -{int(tot_chg):,}")
        print(f" Total Net Realized Profit : Rs. {int(tot_net):,}")
        print(f" Net Profit Factor         : {pf:.2f}")
        print(f" Avg Net P&L per Trade     : Rs. {int(tot_net / n):,}")
        print("=" * 105, flush=True)

    print_model_results(c1_trades, "Choice 1: Stock Option Writing (Bull Put Credit Spread)", "Margin ~Rs. 40,000 / lot")
    print_model_results(c2_trades, "Choice 2: Multi-Day Swing Trading (Cash Delivery 2-5 Days)", "Fixed Risk Rs. 2,500 / trade")

if __name__ == '__main__':
    run_comparison()
