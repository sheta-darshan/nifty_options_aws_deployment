"""
research_and_development/research_cnc_portfolio_simulation.py

Rigorous Portfolio Simulation: Pure Cash Delivery (CNC - No Borrowing)
Simulates a dedicated cash account trading Multi-Day Swing on Opening Stealth Absorption.

Portfolio Rules:
  - Account Initial Capital: ₹15,00,000 (15 Lakhs Cash)
  - Max Concurrent Positions: 4 Active Slots (Allocating ~₹3,50,000 - ₹3,75,000 per trade)
  - Slot Discipline: If 4 slots are full, new breakout signals are queued/skipped until cash is freed.
  - Sizing: Fixed Risk = ₹2,500 / trade based on 10m box stop loss, capped at available slot cash.
  - Target: +5.0% price move (with breakeven stop move at +2.5%) or Trailing Runner.
  - Zero Leverage / No Borrowing: 100% paid in cash, zero interest, zero margin call risk.
  - Exact Delivery Taxes: 0.1% buy STT + 0.1% sell STT, stamp duty, exchange fees, GST (Zero brokerage on Dhan).

Dataset: 78 High-Liquidity Stocks over 3 Years (2023 - 2026).
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")

sys.path.insert(0, BASE_DIR)
from research_and_development.research_choice2_deep_dive import STOCKS_UNIVERSE, load_stock_df, calc_delivery_charges

def run_cnc_portfolio():
    print("=" * 105, flush=True)
    print("      PORTFOLIO BACKTEST: PURE CASH DELIVERY (CNC - ZERO BORROWING)", flush=True)
    print("=" * 105, flush=True)
    print("Starting Capital : Rs. 15,00,000 (15 Lakhs)")
    print("Max Active Slots : 4 Stocks Concurrent (Max ~Rs. 3.75L per stock)")
    print("Sizing Model     : Risk Rs. 2,500 per trade on 10m Box SL, max slot cap")
    print("Duration         : 3 Years (2023 - 2026)\n", flush=True)

    loaded = {}
    for sym in STOCKS_UNIVERSE:
        df = load_stock_df(sym, years=3)
        if df is not None:
            loaded[sym] = df

    print(f"Loaded {len(loaded)} liquid stocks for portfolio simulation.", flush=True)

    trigger_cutoff = time(11, 0)
    MAX_SLOTS = 4
    START_CAPITAL = 1500000.0
    RISK_PER_TRADE = 2500.0
    SLOT_CAP = START_CAPITAL / MAX_SLOTS  # ~3.75 Lakhs per trade

    # 1. Collect all valid breakout signals chronologically
    all_signals = []

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

        for d_idx, d in enumerate(dates[25:-10]):
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
            idx_ts = post.index

            triggered = False
            entry_spot = 0.0
            entry_ts = None

            for bi in range(len(post)):
                if times[bi] > trigger_cutoff:
                    break
                if highs[bi] > high_10:
                    triggered = True
                    entry_spot = max(high_10, opens[bi])
                    entry_ts = idx_ts[bi]
                    break

            if not triggered:
                continue

            # Calculate trade evolution over next 5 trading days (+5% target, Breakeven at +2.5%)
            tp_px = entry_spot * 1.050
            be_px = entry_spot * 1.025
            current_sl = entry_spot - risk_per_share
            is_be = False

            future_dates = dates[d_idx: d_idx + 6]
            exit_px = 0.0
            exit_ts = None

            for fd in future_dates:
                if exit_px > 0:
                    break
                f_day = grouped.get_group(fd)
                f_highs = f_day['high'].values
                f_lows = f_day['low'].values
                f_ts = f_day.index

                for bi in range(len(f_day)):
                    if fd == d and f_ts[bi] <= entry_ts:
                        continue
                    bh = f_highs[bi]
                    bl = f_lows[bi]

                    if not is_be and bh >= be_px:
                        current_sl = entry_spot
                        is_be = True

                    if bh >= tp_px:
                        exit_px = tp_px
                        exit_ts = f_ts[bi]
                        break
                    elif bl <= current_sl:
                        exit_px = current_sl
                        exit_ts = f_ts[bi]
                        break

            if exit_px == 0:
                last_day = grouped.get_group(future_dates[-1])
                exit_px = last_day['close'].iloc[-1]
                exit_ts = last_day.index[-1]

            all_signals.append({
                'symbol': sym,
                'entry_ts': entry_ts,
                'exit_ts': exit_ts,
                'entry_spot': entry_spot,
                'exit_spot': exit_px,
                'risk_per_share': risk_per_share,
                'date': d
            })

    # Sort all signals chronologically
    all_signals.sort(key=lambda x: x['entry_ts'])
    print(f"Total historical signals generated: {len(all_signals)}\n", flush=True)

    # 2. Portfolio Simulation with Capital Constraints
    active_positions = []  # [{symbol, exit_ts, qty, buy_val, entry_spot, exit_spot}]
    cash_balance = START_CAPITAL
    portfolio_history = []
    executed_trades = []
    skipped_signals = 0

    for sig in all_signals:
        e_time = sig['entry_ts']

        # A. Check and close expired positions before entering new ones
        retained_positions = []
        for pos in active_positions:
            if pos['exit_ts'] <= e_time:
                # Position exited! Realize cash & P&L
                sell_val = pos['exit_spot'] * pos['qty']
                real_buy = pos['buy_val'] * 1.0005
                real_sell = sell_val * 0.9995
                charges = calc_delivery_charges(real_buy, real_sell)
                net_pnl = (real_sell - real_buy) - charges
                cash_balance += (sell_val - charges)

                executed_trades.append({
                    'symbol': pos['symbol'],
                    'entry_ts': pos['entry_ts'],
                    'exit_ts': pos['exit_ts'],
                    'year': pos['entry_ts'].year,
                    'buy_val': pos['buy_val'],
                    'sell_val': sell_val,
                    'charges': charges,
                    'net_pnl': net_pnl,
                    'win': net_pnl > 0
                })
            else:
                retained_positions.append(pos)
        active_positions = retained_positions

        # B. Check if we have an available slot and cash
        if len(active_positions) >= MAX_SLOTS:
            skipped_signals += 1
            continue

        # Position Sizing
        risk_ps = sig['risk_per_share']
        desired_qty = max(1, int(RISK_PER_TRADE / risk_ps))
        desired_val = desired_qty * sig['entry_spot']

        # Cap by slot size and available cash
        max_allowed_val = min(SLOT_CAP, cash_balance)
        if desired_val > max_allowed_val:
            desired_qty = max(1, int(max_allowed_val / sig['entry_spot']))
            desired_val = desired_qty * sig['entry_spot']

        if cash_balance < desired_val or desired_val < 50000:
            skipped_signals += 1
            continue

        # Enter Trade
        cash_balance -= desired_val
        active_positions.append({
            'symbol': sig['symbol'],
            'entry_ts': sig['entry_ts'],
            'exit_ts': sig['exit_ts'],
            'entry_spot': sig['entry_spot'],
            'exit_spot': sig['exit_spot'],
            'qty': desired_qty,
            'buy_val': desired_val
        })

    # Close any remaining open positions at the end of the 3 years
    for pos in active_positions:
        sell_val = pos['exit_spot'] * pos['qty']
        real_buy = pos['buy_val'] * 1.0005
        real_sell = sell_val * 0.9995
        charges = calc_delivery_charges(real_buy, real_sell)
        net_pnl = (real_sell - real_buy) - charges
        cash_balance += (sell_val - charges)
        executed_trades.append({
            'symbol': pos['symbol'],
            'entry_ts': pos['entry_ts'],
            'exit_ts': pos['exit_ts'],
            'year': pos['entry_ts'].year,
            'buy_val': pos['buy_val'],
            'sell_val': sell_val,
            'charges': charges,
            'net_pnl': net_pnl,
            'win': net_pnl > 0
        })

    df_exec = pd.DataFrame(executed_trades)
    n_exec = len(df_exec)
    total_net = df_exec['net_pnl'].sum()
    total_charges = df_exec['charges'].sum()
    wins = df_exec['win'].sum()
    wr = (wins / n_exec) * 100.0
    gains = df_exec[df_exec['net_pnl'] > 0]['net_pnl'].sum()
    losses = abs(df_exec[df_exec['net_pnl'] < 0]['net_pnl'].sum())
    pf = (gains / losses) if losses > 0 else np.nan

    ending_capital = START_CAPITAL + total_net
    cagr = (((ending_capital / START_CAPITAL) ** (1.0 / 3.0)) - 1.0) * 100.0

    print("=" * 105, flush=True)
    print("            PORTFOLIO SUMMARY: 3-YEAR CASH DELIVERY PERFORMANCE", flush=True)
    print("=" * 105, flush=True)
    print(f" Initial Starting Cash        : Rs. {int(START_CAPITAL):,}")
    print(f" Final Ending Cash Balance     : Rs. {int(ending_capital):,}")
    print(f" Net Realized Cash Profit      : Rs. {int(total_net):,} (+{(total_net / START_CAPITAL)*100:.1f}% Total ROI)")
    print(f" Compounded Annual Growth CAGR : {cagr:.1f}% per year")
    print(f" Total Trades Executed         : {n_exec} trades (~{n_exec // 3} / year)")
    print(f" Trades Skipped (Slot Limits)  : {skipped_signals} signals")
    print(f" Win Rate                      : {wr:.1f}%")
    print(f" Net Profit Factor             : {pf:.2f}")
    print(f" Total Statutory Taxes Paid    : Rs. -{int(total_charges):,} (Dhan Brokerage: Rs. 0)")
    print("=" * 105, flush=True)

    # Year-by-year cash flow
    print("\nANNUAL CASH BREAKDOWN:")
    print("-" * 75)
    yearly_data = []
    for yr, grp in df_exec.groupby('year'):
        y_n = len(grp)
        y_net = grp['net_pnl'].sum()
        y_wr = (grp['win'].sum() / y_n) * 100
        yearly_data.append({
            'Year': yr,
            'Trades Executed': y_n,
            'Win Rate': f"{y_wr:.1f}%",
            'Net Cash Profit': f"Rs. {int(y_net):,}",
            'Annual Return on Capital': f"+{(y_net / START_CAPITAL)*100:.1f}%"
        })
    print(pd.DataFrame(yearly_data).to_string(index=False))
    print("-" * 75, flush=True)

if __name__ == '__main__':
    run_cnc_portfolio()
