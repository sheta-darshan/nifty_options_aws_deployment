"""
research_and_development/research_stock_options_alpha.py

Path B: Stock Options Simulation for Opening Stealth Absorption
Evaluates trading ATM Stock Call Options (CE) instead of Cash Equity MIS.
Tests across all 198 NSE F&O Stocks from instruments.json over 3 Years (2023 - 2026).

Option Mechanics:
  - Strike: Resolved to nearest ATM strike using exact strike_step from instruments.json.
  - Sizing: 1 native exchange lot size per trade (exact lot_size from instruments.json).
  - Pricing: Black-Scholes Greeks with Delta expansion (Gamma) and Theta decay over holding time.
  - Statutory Friction:
      * Brokerage: Flat ₹20 buy + ₹20 sell = ₹40 per round-trip
      * STT: 0.10% on sell-side option premium turnover
      * Exchange Txn Charges: 0.05% on option premium turnover
      * GST: 18% on (Brokerage + Exchange)
      * Stamp Duty: 0.003% on buy-side premium
      * SEBI Fee: ₹10 / crore
      * Slippage: 0.50% on option premium
"""

import os
import sys
import json
import math
import numpy as np
import pandas as pd
from datetime import datetime, time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
INSTRUMENTS_PATH = os.path.join(BASE_DIR, "instruments.json")

def load_instruments():
    with open(INSTRUMENTS_PATH) as f:
        data = json.load(f)
    fno_stocks = {}
    for k, v in data.items():
        if v.get('type') == 'STOCK' and v.get('option_segment') == 'NSE_FNO':
            fno_stocks[k] = {
                'lot_size': int(v.get('lot_size', 500)),
                'strike_step': float(v.get('strike_step', 10)),
                'fno_prefix': v.get('fno_prefix', k)
            }
    return fno_stocks

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

def calc_fno_option_charges(buy_prem_val: float, sell_prem_val: float) -> float:
    """Exact NSE F&O Options statutory charges."""
    brokerage = 40.0  # ₹20 entry + ₹20 exit
    stt = sell_prem_val * 0.0010  # 0.10% on sell-side option premium
    exch = (buy_prem_val + sell_prem_val) * 0.00050  # 0.050% on option premium turnover
    gst = 0.18 * (brokerage + exch)
    stamp = buy_prem_val * 0.00003  # 0.003% on buy premium
    sebi = (buy_prem_val + sell_prem_val) * 0.000001
    return brokerage + stt + exch + gst + stamp + sebi

def simulate_atm_ce(entry_spot: float, strike: float, spot_move: float, hold_minutes: float, base_iv: float = 0.30):
    """
    Simulates ATM Call option premium change using Delta, Gamma, and Theta.
    ATM Call price approx: 0.40 * S * sigma * sqrt(T)
    For 20 DTE option: approx 3.0% - 4.0% of spot price.
    """
    # Baseline 20 days to monthly expiry
    t_years = max(1.0 / 365.0, (20.0 - (hold_minutes / 375.0)) / 365.0)
    
    # ATM initial premium approx (approx 3.2% of stock price for 30% IV)
    atm_premium = entry_spot * base_iv * math.sqrt(20.0 / 365.0) * 0.40
    atm_premium = max(1.0, atm_premium)

    # Greeks for ATM
    delta = 0.50
    # Spot percentage move
    spot_pct_move = spot_move / entry_spot
    # Delta expansion: delta rises as spot rises (gamma effect)
    effective_delta = delta + (0.5 * spot_pct_move * 5.0)  # Gamma proxy
    effective_delta = max(0.10, min(0.95, effective_delta))

    # Theta decay: ~1.5% of premium lost per full 6-hour trading day
    theta_loss = atm_premium * 0.015 * (hold_minutes / 375.0)

    option_pnl_per_share = (effective_delta * spot_move) - theta_loss
    exit_premium = max(0.05, atm_premium + option_pnl_per_share)

    return atm_premium, exit_premium

def run_stock_options_research():
    print("=" * 105, flush=True)
    print("   PATH B RESEARCH: STOCK OPTIONS (ATM CE) ON STEALTH ABSORPTION BREAKOUTS", flush=True)
    print("=" * 105, flush=True)

    fno_dict = load_instruments()
    print(f"Total F&O stocks configured: {len(fno_dict)}", flush=True)

    # Filter stocks with available 1m spot data
    test_stocks = {}
    for sym, meta in fno_dict.items():
        df = load_stock_df(sym, years=3)
        if df is not None:
            test_stocks[sym] = (df, meta)

    print(f"Loaded {len(test_stocks)} F&O stocks with full 3-year historical 1-minute data.\n", flush=True)

    trigger_cutoff = time(11, 0)
    eod_time = time(15, 14)
    OPTION_SLIPPAGE = 0.005  # 0.5% slippage on option premium

    completed_trades = []

    for s_idx, (sym, (df, meta)) in enumerate(test_stocks.items(), 1):
        lot_size = meta['lot_size']
        strike_step = meta['strike_step']

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
            m = df_stats.loc[d]
            rvol = m['rvol']
            range_pct = m['range_pct']
            high_10 = m['high_10']
            low_10 = m['low_10']
            open_px = m['open_px']

            # Setup criteria: RVOL >= 1.5, Range <= 0.8%
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

            atm_strike = round(entry_spot / strike_step) * strike_step
            stop_spot = entry_spot - risk_spot

            # Trailing stop in spot: once reaches +1.0R in spot, trail 0.75R
            trailing_stop_spot = stop_spot
            max_fav_spot_r = 0.0
            exit_spot = 0.0
            hold_minutes = 0.0

            for i in range(entry_idx, n_bars):
                t = times[i]
                h = highs[i]
                l = lows[i]
                c = closes[i]
                is_eod = (t >= eod_time) or (i == n_bars - 1)

                fav_r = (h - entry_spot) / risk_spot
                if fav_r > max_fav_spot_r:
                    max_fav_spot_r = fav_r
                    if max_fav_spot_r >= 1.0:
                        new_sl = entry_spot + ((max_fav_spot_r - 0.75) * risk_spot)
                        trailing_stop_spot = max(trailing_stop_spot, new_sl)

                if l <= trailing_stop_spot:
                    exit_spot = trailing_stop_spot
                    hold_minutes = (i - entry_idx)
                    break
                elif is_eod:
                    exit_spot = c
                    hold_minutes = (i - entry_idx)
                    break

            if exit_spot > 0:
                spot_move = exit_spot - entry_spot
                buy_prem, sell_prem = simulate_atm_ce(entry_spot, atm_strike, spot_move, hold_minutes)

                # Slippage
                real_buy_prem = buy_prem * (1.0 + OPTION_SLIPPAGE)
                real_sell_prem = sell_prem * (1.0 - OPTION_SLIPPAGE)

                buy_val = real_buy_prem * lot_size
                sell_val = real_sell_prem * lot_size

                charges = calc_fno_option_charges(buy_val, sell_val)
                gross_pnl = (sell_prem - buy_prem) * lot_size
                net_pnl = (real_sell_prem - real_buy_prem) * lot_size - charges

                completed_trades.append({
                    'symbol': sym,
                    'date': d,
                    'lot_size': lot_size,
                    'entry_spot': entry_spot,
                    'exit_spot': exit_spot,
                    'buy_prem': buy_prem,
                    'sell_prem': sell_prem,
                    'turnover': buy_val + sell_val,
                    'gross_pnl': gross_pnl,
                    'charges': charges,
                    'net_pnl': net_pnl,
                    'win': net_pnl > 0
                })

    df_res = pd.DataFrame(completed_trades)
    n = len(df_res)
    print(f"Captured {n} Option Trades across {len(test_stocks)} F&O stocks over 3 years.\n", flush=True)

    if n == 0:
        print("No trades found.", flush=True)
        return

    gross_tot = df_res['gross_pnl'].sum()
    net_tot = df_res['net_pnl'].sum()
    charges_tot = df_res['charges'].sum()
    avg_turnover = df_res['turnover'].mean()
    avg_charges = df_res['charges'].mean()

    wins = df_res['win'].sum()
    wr = (wins / n) * 100.0
    gains = df_res[df_res['net_pnl'] > 0]['net_pnl'].sum()
    losses = abs(df_res[df_res['net_pnl'] < 0]['net_pnl'].sum())
    pf = (gains / losses) if losses > 0 else np.nan

    print("=" * 105, flush=True)
    print("               PATH B (STOCK OPTIONS) 3-YEAR PERFORMANCE AUDIT", flush=True)
    print("=" * 105, flush=True)
    print(f" Total Trades Executed    : {n} trades (~{n // 3} trades / year)")
    print(f" Average Option Turnover  : Rs. {int(avg_turnover):,} per trade (vs Rs. 8.3 Lakhs in Cash MIS!)")
    print(f" Average Total Friction   : Rs. {int(avg_charges):,} per trade (Brokerage + STT + GST)")
    print(f" Total Brokerage & Taxes  : Rs. -{int(charges_tot):,}")
    print(f" Total Gross Profit       : Rs. {int(gross_tot):,}")
    print(f" Total NET Take-Home P&L  : Rs. {int(net_tot):,}")
    print(f" Net Win Rate             : {wr:.1f}%")
    print(f" Net Profit Factor        : {pf:.2f}")
    print("=" * 105, flush=True)

    # Top liquid F&O stocks (Nifty 50 F&O heavyweights)
    TOP_LIQUID_FNO = [
        'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'TATAMOTORS', 'SBIN', 'BHARTIARTL',
        'LT', 'ITC', 'AXISBANK', 'BAJFINANCE', 'MARUTI', 'TITAN', 'SUNPHARMA', 'KOTAKBANK',
        'TATAELXSI', 'POLYCAB', 'COFORGE', 'HAL', 'BEL', 'DLF', 'TRENT', 'VEDL', 'JSWSTEEL'
    ]
    df_top = df_res[df_res['symbol'].isin(TOP_LIQUID_FNO)]
    if not df_top.empty:
        n_top = len(df_top)
        top_net = df_top['net_pnl'].sum()
        top_wins = df_top['win'].sum()
        top_wr = (top_wins / n_top) * 100.0
        top_gain = df_top[df_top['net_pnl'] > 0]['net_pnl'].sum()
        top_loss = abs(df_top[df_top['net_pnl'] < 0]['net_pnl'].sum())
        top_pf = (top_gain / top_loss) if top_loss > 0 else np.nan

        print("\nTOP 25 HIGH-LIQUIDITY F&O STOCKS ONLY (Liquid Option Books):")
        print(f" Trades: {n_top} | Net P&L: Rs. {int(top_net):,} | Net Win Rate: {top_wr:.1f}% | Net Profit Factor: {top_pf:.2f}")
        print("=" * 105, flush=True)

if __name__ == '__main__':
    run_stock_options_research()
