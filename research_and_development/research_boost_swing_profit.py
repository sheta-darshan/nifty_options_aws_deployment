"""
research_and_development/research_boost_swing_profit.py

Empirical Study: How to Maximize Net Profit on Multi-Day Swing Trading (Countering 20% STCG Tax)
Tests 3 High-Impact Alpha Enhancers:
  1. Letting Winners Run: Trailing Stop (Trail 2.0% behind peak) vs Fixed 5% Target.
  2. Trend Alignment Filter: Stock must be above its 50 EMA (Stage 2 Uptrend).
  3. Dynamic Compounding: Position sizing scales as account grows (risking 0.25% of current equity).

Evaluated across the 78 Liquid Stocks over 3 Years (2023 - 2026).
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

def run_profit_boost_study():
    print("=" * 105, flush=True)
    print("      RESEARCH: MAXIMIZING NET SWING PROFIT (BEATING 20% STCG TAX DRAG)", flush=True)
    print("=" * 105, flush=True)

    loaded = {}
    for sym in STOCKS_UNIVERSE:
        df = load_stock_df(sym, years=3)
        if df is not None:
            loaded[sym] = df

    print(f"Loaded {len(loaded)} liquid stocks for optimization study.\n", flush=True)

    trigger_cutoff = time(11, 0)
    START_CAPITAL = 1500000.0  # ₹15 Lakhs
    MAX_SLOTS = 4

    # 1. Collect all valid breakout signals with 50-EMA trend metadata
    signals = []

    for sym, df in loaded.items():
        grouped = df.groupby('date')
        dates = list(grouped.groups.keys())

        # Daily closing prices for 50-EMA calculation
        daily_closes = [grouped.get_group(d)['close'].iloc[-1] for d in dates]
        df_daily = pd.DataFrame({'date': dates, 'close': daily_closes}).set_index('date')
        df_daily['ema_50'] = df_daily['close'].ewm(span=50, adjust=False).mean().shift(1)

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
            if d not in df_stats.index or d not in df_daily.index:
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

            # Stage-2 Trend Filter: Stock must be above its 50-day EMA
            ema_50_val = df_daily.loc[d, 'ema_50']
            is_above_50_ema = (open_px >= ema_50_val) if not pd.isna(ema_50_val) else True

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

            # Simulate Trailing Trend Runner exit (up to 10 trading days hold)
            # Stop starts at box low; once +2.5% reached, move SL to breakeven; once +4% reached, trail 2.0% behind peak
            current_sl = entry_spot - risk_per_share
            be_activated = False
            trail_activated = False
            peak_px = entry_spot

            future_dates = dates[d_idx: d_idx + 11]
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

                    if bh > peak_px:
                        peak_px = bh

                    if not be_activated and bh >= entry_spot * 1.025:
                        current_sl = entry_spot
                        be_activated = True

                    if bh >= entry_spot * 1.040:
                        trail_activated = True

                    if trail_activated:
                        new_trail = peak_px * 0.980  # 2.0% behind highest price reached
                        current_sl = max(current_sl, new_trail)

                    if bl <= current_sl:
                        exit_px = current_sl
                        exit_ts = f_ts[bi]
                        break

            if exit_px == 0:
                last_day = grouped.get_group(future_dates[-1])
                exit_px = last_day['close'].iloc[-1]
                exit_ts = last_day.index[-1]

            signals.append({
                'symbol': sym,
                'entry_ts': entry_ts,
                'exit_ts': exit_ts,
                'entry_spot': entry_spot,
                'exit_spot': exit_px,
                'gain_pct': (exit_px - entry_spot) / entry_spot * 100.0,
                'risk_per_share': risk_per_share,
                'is_above_50_ema': is_above_50_ema,
                'rvol': rvol,
                'date': d
            })

    signals.sort(key=lambda x: x['entry_ts'])
    print(f"Captured {len(signals)} multi-day swing breakout signals.\n", flush=True)

    # We evaluate 3 Portfolio Models:
    # Model 1: Baseline (Fixed 5% target, no trend filter, ₹15L static) -> What we ran earlier
    # Model 2: Trailing Runner (Hold up to 10 days, letting winners run, no trend filter)
    # Model 3: Enhanced Alpha Engine (Trailing Runner + 50 EMA Uptrend Filter + Compounding 0.30% Equity Risk)

    def simulate_portfolio(sig_list, model_name, use_ema_filter=False, use_compounding=False):
        cash = START_CAPITAL
        equity = START_CAPITAL
        active = []
        exec_trades = []
        skipped = 0

        for sig in sig_list:
            if use_ema_filter and not sig['is_above_50_ema']:
                continue

            e_time = sig['entry_ts']

            # Close finished trades
            retained = []
            for pos in active:
                if pos['exit_ts'] <= e_time:
                    sell_val = pos['exit_spot'] * pos['qty']
                    real_buy = pos['buy_val'] * 1.0005
                    real_sell = sell_val * 0.9995
                    chg = calc_delivery_charges(real_buy, real_sell)
                    net_pnl = (real_sell - real_buy) - chg
                    cash += (sell_val - chg)
                    equity += net_pnl

                    exec_trades.append({
                        'symbol': pos['symbol'],
                        'year': pos['entry_ts'].year,
                        'net_pnl': net_pnl,
                        'charges': chg,
                        'win': net_pnl > 0
                    })
                else:
                    retained.append(pos)
            active = retained

            if len(active) >= MAX_SLOTS:
                skipped += 1
                continue

            # Sizing
            risk_amt = (equity * 0.0030) if use_compounding else 2500.0
            slot_cap = (equity / MAX_SLOTS) if use_compounding else (START_CAPITAL / MAX_SLOTS)

            desired_qty = max(1, int(risk_amt / sig['risk_per_share']))
            desired_val = desired_qty * sig['entry_spot']

            max_val = min(slot_cap, cash)
            if desired_val > max_val:
                desired_qty = max(1, int(max_val / sig['entry_spot']))
                desired_val = desired_qty * sig['entry_spot']

            if cash < desired_val or desired_val < 50000:
                skipped += 1
                continue

            cash -= desired_val
            active.append({
                'symbol': sig['symbol'],
                'entry_ts': sig['entry_ts'],
                'exit_ts': sig['exit_ts'],
                'entry_spot': sig['entry_spot'],
                'exit_spot': sig['exit_spot'],
                'qty': desired_qty,
                'buy_val': desired_val
            })

        # Close remaining
        for pos in active:
            sell_val = pos['exit_spot'] * pos['qty']
            real_buy = pos['buy_val'] * 1.0005
            real_sell = sell_val * 0.9995
            chg = calc_delivery_charges(real_buy, real_sell)
            net_pnl = (real_sell - real_buy) - chg
            cash += (sell_val - chg)
            equity += net_pnl
            exec_trades.append({
                'symbol': pos['symbol'],
                'year': pos['entry_ts'].year,
                'net_pnl': net_pnl,
                'charges': chg,
                'win': net_pnl > 0
            })

        df_ex = pd.DataFrame(exec_trades)
        n = len(df_ex)
        tot_net = df_ex['net_pnl'].sum()
        tot_chg = df_ex['charges'].sum()
        wins = df_ex['win'].sum()
        wr = (wins / n) * 100.0 if n > 0 else 0
        gains = df_ex[df_ex['net_pnl'] > 0]['net_pnl'].sum()
        losses = abs(df_ex[df_ex['net_pnl'] < 0]['net_pnl'].sum())
        pf = (gains / losses) if losses > 0 else np.nan

        # 20% STCG Tax impact
        stcg_tax_20 = max(0.0, tot_net * 0.20)
        post_tax_inr = tot_net - stcg_tax_20
        post_tax_cagr = ((( (START_CAPITAL + post_tax_inr) / START_CAPITAL) ** (1.0 / 3.0)) - 1.0) * 100.0

        return {
            'Strategy Model': model_name,
            'Trades': n,
            'Win Rate': f"{wr:.1f}%",
            'Net Profit (Pre-Tax)': f"Rs. {int(tot_net):,}",
            '20% STCG Tax': f"Rs. -{int(stcg_tax_20):,}",
            'Pure Take-Home (Post-Tax)': f"Rs. {int(post_tax_inr):,}",
            'Post-Tax CAGR %': f"{post_tax_cagr:.1f}% / yr",
            'Profit Factor': f"{pf:.2f}"
        }

    # Run comparisons
    m1 = {
        'Strategy Model': "Baseline (Fixed 5% Target, Static Sizing)",
        'Trades': 484,
        'Win Rate': "25.4%",
        'Net Profit (Pre-Tax)': "Rs. 568,815",
        '20% STCG Tax': f"Rs. -{int(568815 * 0.20):,}",
        'Pure Take-Home (Post-Tax)': f"Rs. {int(568815 * 0.80):,}",
        'Post-Tax CAGR %': f"{((((1500000 + 568815*0.8)/1500000)**(1/3))-1)*100:.1f}% / yr",
        'Profit Factor': "1.50"
    }
    m2 = simulate_portfolio(signals, "Model 2: Trailing Runner (Hold up to 10 Days)", use_ema_filter=False, use_compounding=False)
    m3 = simulate_portfolio(signals, "Model 3: Trailing Runner + 50 EMA Trend Filter", use_ema_filter=True, use_compounding=False)
    m4 = simulate_portfolio(signals, "Model 4: Full Engine (Trailing + Trend Filter + Compounding)", use_ema_filter=True, use_compounding=True)

    df_comp = pd.DataFrame([m1, m2, m3, m4])
    print(df_comp.to_string(index=False), flush=True)
    print("=" * 115, flush=True)

if __name__ == '__main__':
    run_profit_boost_study()
