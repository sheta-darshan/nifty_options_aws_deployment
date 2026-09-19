"""
research_and_development/backtest_prebreakout_selection.py

Institutional Historical Backtesting Harness for Pre-Breakout Coiled Stock Selection
=====================================================================================
Walk-forward simulation over 1-2 years:
  1. At each Day T close, evaluate compression metrics across a diversified universe.
  2. Select Top K Coiled Stocks (Score >= 75: TTM Squeeze, NR7/Inside Day, Volume Dry-up, 20 EMA).
  3. On Day T+1, monitor 1-minute intraday bars:
     - If price crosses Trigger Price (Day T High + 0.05), enter LONG.
     - Hard SL: Day T Low or Entry - 1.2x ATR (max 1.5%).
     - Dynamic Breakeven: Slide SL to Entry + 0.05% when profit reaches +0.8x ATR.
     - Target: Entry + 2.0x ATR.
     - Enforce exact Dhan transaction costs (STT, turnover, GST, SEBI, stamp duty).
"""

import os
import sys
import glob
import json
import time
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, time as dt_time
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
sys.path.insert(0, BASE_DIR)

def load_universe_stocks(universe: str = "500") -> List[str]:
    """Loads universe stock list based on universe name or path."""
    if universe in ["500", "top500"]:
        u_file = os.path.join(BASE_DIR, "universe_500.json")
    elif universe in ["200", "top200"]:
        u_file = os.path.join(BASE_DIR, "universe_200.json")
    elif os.path.exists(universe):
        u_file = universe
    else:
        u_file = os.path.join(BASE_DIR, "universe_500.json")

    if os.path.exists(u_file):
        with open(u_file, "r") as f:
            return [s.upper() for s in json.load(f)]
    # Fallback to standard 50 stocks
    return [
        'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
        'TATAMOTORS', 'SBIN', 'BHARTIARTL', 'LT', 'ITC',
        'AXISBANK', 'BAJFINANCE', 'MARUTI', 'TITAN', 'SUNPHARMA',
        'KOTAKBANK', 'WIPRO', 'HCLTECH', 'NTPC', 'ONGC',
        'POWERGRID', 'ULTRACEMCO', 'ADANIENT', 'TATASTEEL', 'HINDUNILVR',
        'COFORGE', 'PERSISTENT', 'LTIM', 'TECHM', 'CHOLAFIN',
        'FEDERALBNK', 'BAJAJFINSV', 'BAJAJ-AUTO', 'HEROMOTOCO', 'BHARATFORG',
        'JSWSTEEL', 'HINDALCO', 'COALINDIA', 'DRREDDY', 'CIPLA',
        'APOLLOHOSP', 'DIVISLAB', 'LUPIN', 'ASIANPAINT', 'TRENT',
        'TATACONSUM', 'DIXON', 'HAL', 'BEL', 'POLYCAB'
    ]


def calc_equity_costs(buy_val: float, sell_val: float, is_delivery: bool = False) -> float:
    """Exact Dhan transaction costs for equity."""
    if is_delivery:
        stt = (buy_val + sell_val) * 0.0010
        brokerage = 0.0
    else:
        brokerage = min(40.0, 0.0003 * (buy_val + sell_val))
        stt = sell_val * 0.00025
    exch = (buy_val + sell_val) * 0.0000322
    stamp = buy_val * 0.00015
    sebi = (buy_val + sell_val) * 0.000001
    gst = 0.18 * (brokerage + exch)
    return brokerage + stt + exch + stamp + sebi + gst


def run_prebreakout_backtest(years: int = 1, top_k: int = 3, max_hold_days: int = 2, universe: str = "500"):
    universe_stocks = load_universe_stocks(universe)
    print("=" * 115, flush=True)
    print(f"   HISTORICAL BACKTEST: PRE-BREAKOUT COILED SELECTION ({years} YEARS, {len(universe_stocks)} STOCKS)", flush=True)
    print("=" * 115, flush=True)
    print(f"Parameters: Top-{top_k} Daily Coiled Picks | Trigger: Day T High | Dynamic Breakeven: +0.8x ATR | Target: +2.0x ATR\n", flush=True)

    cache_file = os.path.join(DATA_DIR, f"prebreakout_cache_{len(universe_stocks)}_{years}y.pkl")
    if os.path.exists(cache_file):
        print(f"Loading pre-computed {len(universe_stocks)} stock dataset from binary cache: {cache_file}...", flush=True)
        import pickle
        with open(cache_file, 'rb') as f:
            stock_1m, stock_daily = pickle.load(f)
    else:
        print(f"Pre-loading historical datasets for {len(universe_stocks)} stocks in parallel...", flush=True)
        from multiprocessing.pool import ThreadPool

        def load_stock_worker(sym):
            p = os.path.join(DATA_DIR, f"{sym}_spot.csv")
            if not os.path.exists(p):
                p = os.path.join(DATA_DIR, f"{sym.lower()}_spot.csv")
            if not os.path.exists(p):
                return None
            try:
                df = pd.read_csv(p)
                col = 'timestamp' if 'timestamp' in df.columns else df.columns[0]
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df.set_index(col, inplace=True)
                df.sort_index(inplace=True)
                
                # Slice requested lookback
                max_dt = df.index.max()
                cutoff_dt = max_dt - pd.Timedelta(days=years * 365 + 60) # buffer for 50 EMA
                df = df.loc[cutoff_dt:max_dt].copy()
                df['time'] = df.index.time
                df['date'] = df.index.date
                df = df[(df['time'] >= dt_time(9, 15)) & (df['time'] <= dt_time(15, 29))].copy()

                if len(df) < 5000:
                    return None

                # Daily bars
                daily = df.groupby('date').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

                if len(daily) < 30:
                    return None

                # Precalculate indicators on daily
                closes = daily['close']
                highs = daily['high']
                lows = daily['low']
                vols = daily['volume']

                tr = np.maximum(
                    highs - lows,
                    np.maximum(abs(highs - closes.shift(1)), abs(lows - closes.shift(1)))
                )
                daily['atr14'] = tr.rolling(14).mean()
                daily['ema20'] = closes.ewm(span=20).mean()
                daily['ema50'] = closes.ewm(span=50).mean()
                daily['vol_sma20'] = vols.rolling(20).mean()

                basis = closes.rolling(20).mean()
                dev = closes.rolling(20).std()
                daily['bb_upper'] = basis + 2.0 * dev
                daily['bb_lower'] = basis - 2.0 * dev
                daily['bb_width'] = (daily['bb_upper'] - daily['bb_lower']) / (basis + 1e-9)
                daily['kc_upper'] = basis + 1.5 * daily['atr14']
                daily['kc_lower'] = basis - 1.5 * daily['atr14']
                daily['high_200'] = highs.rolling(200, min_periods=50).max()

                return sym, df, daily
            except Exception:
                return None

        pool = ThreadPool(16)
        results = pool.map(load_stock_worker, universe_stocks)
        pool.close()
        pool.join()

        stock_1m = {}
        stock_daily = {}
        for res in results:
            if res is not None:
                s, df, daily = res
                stock_1m[s] = df
                stock_daily[s] = daily

        try:
            import pickle
            with open(cache_file, 'wb') as f:
                pickle.dump((stock_1m, stock_daily), f)
            print(f"Cached {len(stock_1m)} stocks to {cache_file} for instant future runs.", flush=True)
        except Exception:
            pass

    print(f"Successfully pre-loaded {len(stock_1m)}/{len(universe_stocks)} stocks with clean OHLCV data.\n", flush=True)

    # 2. Extract shared dates across the universe
    date_counts = pd.Series([d for df in stock_daily.values() for d in df.index]).value_counts()
    all_dates = sorted(date_counts[date_counts >= 25].index.tolist())
    # Trim warmup
    test_dates = all_dates[40:] if len(all_dates) > 40 else all_dates
    print(f"Simulating walk-forward trading across {len(test_dates)} sessions...\n", flush=True)

    trades = []
    daily_logs = []
    ALLOCATION = 100000.0  # Rs. 1,00,000 capital per trade

    for day_idx in range(len(test_dates) - 1):
        date_t = test_dates[day_idx]
        date_t1 = test_dates[day_idx + 1]

        # Scan universe at Day T Close for Pre-Breakout Coiling
        candidate_scores = []

        for sym, d_df in stock_daily.items():
            if date_t not in d_df.index:
                continue
            idx_loc = d_df.index.get_loc(date_t)
            if idx_loc < 25:
                continue

            sub = d_df.iloc[:idx_loc + 1]
            c = sub['close'].iloc[-1]
            h = sub['high'].iloc[-1]
            l = sub['low'].iloc[-1]
            v = sub['volume'].iloc[-1]
            e20 = sub['ema20'].iloc[-1]
            e50 = sub['ema50'].iloc[-1]
            atr = sub['atr14'].iloc[-1]
            v_sma = sub['vol_sma20'].iloc[-1]
            bbl = sub['bb_lower'].iloc[-1]
            bbu = sub['bb_upper'].iloc[-1]
            kcl = sub['kc_lower'].iloc[-1]
            kcu = sub['kc_upper'].iloc[-1]
            rng = h - l

            # Trend & Anti-Climax Gates
            if c < e50 or v_sma < 20000:
                continue
            # Overhead Supply Gate (Minervini Stage 2: Within 18% of 200-day high)
            h200 = sub['high_200'].iloc[-1]
            if c < 0.82 * h200:
                continue
            # Relative Momentum (positive 20-day return)
            if len(sub) >= 21 and c < sub['close'].iloc[-21]:
                continue
            today_ret = (c - sub['open'].iloc[-1]) / sub['open'].iloc[-1] * 100.0
            if today_ret >= 4.0:
                continue  # Skip stocks that already exploded today

            score = 0.0

            # 1. TTM Squeeze
            if (bbl >= kcl) and (bbu <= kcu):
                score += 25.0
            elif sub['bb_width'].iloc[-1] <= sub['bb_width'].iloc[-20:].min() * 1.15:
                score += 15.0

            # 2. NR7 / Inside Day
            ranges_7 = (sub['high'] - sub['low']).iloc[-7:]
            is_nr7 = rng <= ranges_7.min() + 1e-6
            prev_h = sub['high'].iloc[-2]
            prev_l = sub['low'].iloc[-2]
            is_inside_day = (h <= prev_h) and (l >= prev_l)

            if is_nr7 and is_inside_day:
                score += 25.0
            elif is_nr7:
                score += 20.0
            elif is_inside_day:
                score += 18.0
            elif rng < 0.8 * atr:
                score += 12.0

            # 3. Base Proximity (0% - 2.5% of 20 EMA)
            dist_20 = (c - e20) / e20 * 100.0
            if 0.0 <= dist_20 <= 1.8:
                score += 25.0
            elif 1.8 < dist_20 <= 3.0:
                score += 18.0
            elif -1.5 <= dist_20 < 0.0:
                score += 12.0

            # 4. Volume Dry-Up
            vol_ratio = v / (v_sma + 1e-9)
            if vol_ratio <= 0.65:
                score += 15.0
            elif vol_ratio <= 0.85:
                score += 10.0
            elif vol_ratio <= 1.10:
                score += 5.0

            # 5. Momentum slope
            if len(sub) >= 6:
                ret_5d = (c - sub['close'].iloc[-6]) / sub['close'].iloc[-6] * 100.0
                if ret_5d > 0:
                    score += 10.0

            if score >= 65.0:
                candidate_scores.append({
                    'sym': sym,
                    'score': score,
                    'trigger_px': round(h + 0.05, 2),
                    'day_low': l,
                    'atr': atr
                })

        if not candidate_scores:
            continue

        # Sort and select Top K coiled stocks for Day T+1
        candidate_scores.sort(key=lambda x: x['score'], reverse=True)
        top_picks = candidate_scores[:top_k]

        # Simulate execution on Day T+1
        for pick in top_picks:
            sym = pick['sym']
            trig_px = pick['trigger_px']
            atr = pick['atr']
            day_t_low = pick['day_low']

            # Check 1-minute bars on Day T+1
            m1_df = stock_1m[sym]
            t1_bars = m1_df[m1_df['date'] == date_t1]
            if t1_bars.empty:
                continue

            # Resample Day T+1 to 5-minute bars for robust institutional confirmation
            m5_df = t1_bars.resample('5min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            m5_morning = m5_df[(m5_df.index.time >= dt_time(9, 20)) & (m5_df.index.time <= dt_time(11, 30))]
            breakout_5m = m5_morning[(m5_morning['high'] >= trig_px) & (m5_morning['close'] >= trig_px) & (m5_morning['close'] >= m5_morning['open'])]
            if breakout_5m.empty:
                continue

            entry_bar_idx = breakout_5m.index[0]
            entry_bar = breakout_5m.loc[entry_bar_idx]

            # Volume Surge on 5-min bar
            # Volume Surge on 5-min bar (Opening RVOL check & subsequent volume check)
            pos_5m = m5_df.index.get_loc(entry_bar_idx)
            if isinstance(pos_5m, int):
                if pos_5m >= 3:
                    avg_vol = m5_df['volume'].iloc[max(0, pos_5m-5):pos_5m].mean()
                    if avg_vol > 0 and entry_bar['volume'] < 1.25 * avg_vol:
                        continue  # Low volume fakeout
                else:
                    # Opening 15-min bar: Must have solid participation (volume > 2000 shares)
                    if entry_bar['volume'] < 2500:
                        continue

            entry_price = trig_px
            shares = int(ALLOCATION / entry_price)
            if shares <= 0:
                continue

            # Stop Loss & Dynamic Breakeven Rules
            sl_price = round(entry_price - 0.9 * atr, 2)
            be_trigger = round(entry_price + 0.65 * atr, 2)
            tp_price = round(entry_price + 1.15 * atr, 2)
            fail_exit_price = round(entry_price - 0.50 * atr, 2)

            be_active = False
            exit_price = None
            exit_reason = None

            # Track post-entry 1-minute bars
            post_bars = t1_bars[t1_bars.index >= entry_bar_idx]

            for _, bar in post_bars.iterrows():
                h_b = bar['high']
                l_b = bar['low']
                c_b = bar['close']

                # Dynamic Breakeven Shift
                if not be_active and h_b >= be_trigger:
                    sl_price = round(entry_price * 1.001, 2)
                    be_active = True

                # Check Stop Loss / Breakeven
                if l_b <= sl_price:
                    exit_price = sl_price
                    exit_reason = "BREAKEVEN" if be_active else "STOP_LOSS"
                    break

                # Check Profit Target
                if h_b >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TARGET"
                    break

                # Failed Breakout Scratch Exit (if price drops below fail_exit_price before breakeven)
                if not be_active and c_b <= fail_exit_price:
                    exit_price = fail_exit_price
                    exit_reason = "FAILED_BREAKOUT"
                    break

            # If not exited by 15:15 PM on Day T+1:
            if exit_price is None:
                eod_close = post_bars['close'].iloc[-1]
                if eod_close <= entry_price or max_hold_days <= 1:
                    exit_price = eod_close
                    exit_reason = "EOD"
                    is_delivery = False
                else:
                    # Position is winning! Carry forward to Day T+2
                    t2_date = test_dates[min(day_idx + 2, len(test_dates) - 1)]
                    t2_bars = m1_df[m1_df['date'] == t2_date]
                    if not t2_bars.empty:
                        for _, bar2 in t2_bars.iterrows():
                            h2, l2 = bar2['high'], bar2['low']
                            if not be_active and h2 >= be_trigger:
                                sl_price = round(entry_price * 1.0005, 2)
                                be_active = True
                            if l2 <= sl_price:
                                exit_price = sl_price
                                exit_reason = "BREAKEVEN" if be_active else "STOP_LOSS"
                                break
                            if h2 >= tp_price:
                                exit_price = tp_price
                                exit_reason = "TARGET"
                                break
                        if exit_price is None:
                            exit_price = t2_bars['close'].iloc[-1]
                            exit_reason = "SWING_EXIT"
                        is_delivery = True
                    else:
                        exit_price = eod_close
                        exit_reason = "EOD"
                        is_delivery = False
            else:
                is_delivery = False

            # Calculate PnL and exact Dhan costs
            gross_pnl = (exit_price - entry_price) * shares
            pct_ret = (exit_price - entry_price) / entry_price * 100.0
            buy_val = entry_price * shares
            sell_val = exit_price * shares
            costs = calc_equity_costs(buy_val, sell_val, is_delivery=is_delivery)
            net_pnl = gross_pnl - costs
            is_win = net_pnl > 0

            trades.append({
                'date': date_t1,
                'year': date_t1.year if hasattr(date_t1, 'year') else str(date_t1)[:4],
                'symbol': sym,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pct_ret': pct_ret,
                'net_pnl': net_pnl,
                'costs': costs,
                'exit_reason': exit_reason,
                'is_win': is_win
            })

    # 3. Analyze Performance Results
    if not trades:
        print("[ERROR] No trades were triggered during the backtest.")
        return

    df_t = pd.DataFrame(trades)
    total_trades = len(df_t)
    wins = df_t['is_win'].sum()
    win_rate = (wins / total_trades) * 100.0

    target_hits = (df_t['exit_reason'] == 'TARGET').sum()
    be_hits = (df_t['exit_reason'] == 'BREAKEVEN').sum()
    sl_hits = (df_t['exit_reason'] == 'STOP_LOSS').sum()
    eod_exits = (df_t['exit_reason'].isin(['EOD', 'SWING_EXIT'])).sum()

    gross_gains = df_t.loc[df_t['net_pnl'] > 0, 'net_pnl'].sum()
    gross_losses = abs(df_t.loc[df_t['net_pnl'] < 0, 'net_pnl'].sum())
    profit_factor = (gross_gains / gross_losses) if gross_losses > 0 else 9.99
    total_pnl = df_t['net_pnl'].sum()
    total_costs = df_t['costs'].sum()
    trading_weeks = len(test_dates) / 5.0
    trades_per_week = total_trades / max(1.0, trading_weeks)

    # Capital & Utilization Analytics
    active_days = df_t['date'].nunique()
    idle_days = len(test_dates) - active_days
    idle_pct = (idle_days / len(test_dates)) * 100.0
    peak_capital = top_k * ALLOCATION
    roi_cash = (total_pnl / peak_capital) * 100.0
    years_elapsed = max(1.0, len(test_dates) / 250.0)
    cagr_cash = ((1.0 + total_pnl / peak_capital) ** (1.0 / years_elapsed) - 1.0) * 100.0 if total_pnl > 0 else 0.0

    df_t_sorted = df_t.sort_values(by='date').copy()
    df_t_sorted['cum_pnl'] = df_t_sorted['net_pnl'].cumsum()
    cum_max = df_t_sorted['cum_pnl'].cummax()
    max_dd = (df_t_sorted['cum_pnl'] - cum_max).min()
    max_dd_pct = (abs(max_dd) / peak_capital) * 100.0

    # Intraday MIS 5x leverage projection
    mis_pnl = total_pnl * 5.0
    mis_roi = (mis_pnl / peak_capital) * 100.0

    print("=" * 115)
    print("                 HISTORICAL BACKTEST RESULTS: PRE-BREAKOUT COILED SELECTION (TOP 200 STOCKS)")
    print("=" * 115)
    print(f"Total Trading Days:         {len(test_dates):,} days ({trading_weeks:.1f} trading weeks)")
    print(f"Active Trading Days:        {active_days:,} days ({100.0 - idle_pct:.1f}% active | ONLY {idle_pct:.1f}% idle days)")
    print(f"Total Completed Trades:     {total_trades:,} trades (~{trades_per_week:.2f} trades / week total)")
    print(f"Overall Net Win Rate:       {win_rate:.1f}%")
    print(f"Profit Factor:              {profit_factor:.2f}")
    print("-" * 115)
    print("CAPITAL & RETURN ON INVESTMENT (ROI):")
    print(f"  * Allocation per Trade:      Rs. {ALLOCATION:,.2f}")
    print(f"  * Peak Capital Required:     Rs. {peak_capital:,.2f} (Top-{top_k} picks)")
    print(f"  * Max Portfolio Drawdown:    Rs. {max_dd:,.2f} (-{max_dd_pct:.1f}% max risk)")
    print(f"  * 1x Cash Equity Net PnL:    Rs. {total_pnl:,.2f}  --> +{roi_cash:.1f}% Net Return (+{cagr_cash:.1f}% CAGR)")
    print(f"  * 5x Intraday MIS Net PnL:   Rs. {mis_pnl:,.2f}  --> +{mis_roi:.1f}% Net Return on Capital")
    print(f"  * Total Transaction Costs:   Rs. {total_costs:,.2f} (Dhan STT, Brokerage, Exchange, GST)")
    print("-" * 115)
    print("Trade Outcome Distribution:")
    print(f"  * Profit Target Reached (+1.2x ATR):  {target_hits:>4} trades ({target_hits/total_trades*100:5.1f}%)")
    print(f"  * Dynamic Breakeven Protected:        {be_hits:>4} trades ({be_hits/total_trades*100:5.1f}%)")
    print(f"  * Stopped Out (Initial SL Hit):       {sl_hits:>4} trades ({sl_hits/total_trades*100:5.1f}%)")
    print(f"  * EOD / Swing Flat Exits:             {eod_exits:>4} trades ({eod_exits/total_trades*100:5.1f}%)")
    print("=" * 115)

    # Year-by-Year Performance Breakdown
    print("\n" + "=" * 135)
    print("                                            YEAR-BY-YEAR PERFORMANCE BREAKDOWN")
    print("=" * 135)
    print(f"{'Year':<6} | {'Trades':<7} | {'Win Rate':<9} | {'PF':<6} | {'Net PnL (Rs.)':<14} | {'Target':<7} | {'Breakeven':<9} | {'EOD Win':<8} | {'EOD Loss':<9} | {'Scratch':<8} | {'Hard SL':<8}")
    print("-" * 135)

    for yr, y_df in df_t.groupby('year'):
        y_trades = len(y_df)
        y_wins = y_df['is_win'].sum()
        y_wr = (y_wins / y_trades) * 100.0
        y_gains = y_df.loc[y_df['net_pnl'] > 0, 'net_pnl'].sum()
        y_losses = abs(y_df.loc[y_df['net_pnl'] < 0, 'net_pnl'].sum())
        y_pf = (y_gains / y_losses) if y_losses > 0 else 9.99
        y_pnl = y_df['net_pnl'].sum()
        y_tp = (y_df['exit_reason'] == 'TARGET').sum()
        y_be = (y_df['exit_reason'] == 'BREAKEVEN').sum()
        y_eod_win = ((y_df['exit_reason'] == 'EOD') & (y_df['is_win'] == True)).sum()
        y_eod_loss = ((y_df['exit_reason'] == 'EOD') & (y_df['is_win'] == False)).sum()
        y_scratch = (y_df['exit_reason'] == 'FAILED_BREAKOUT').sum()
        y_sl = (y_df['exit_reason'] == 'STOP_LOSS').sum()

        print(f"{yr:<6} | {y_trades:<7} | {y_wr:<8.1f}% | {y_pf:<6.2f} | Rs.{y_pnl:<10,.2f} | {y_tp:<7} | {y_be:<9} | {y_eod_win:<8} | {y_eod_loss:<9} | {y_scratch:<8} | {y_sl:<8}")

    print("=" * 135)

    # Export trade log
    out_csv = os.path.join(BASE_DIR, "research_and_development", "prebreakout_backtest_trades.csv")
    df_t.to_csv(out_csv, index=False)
    print(f"\n[EXPORT] Detailed trade logs successfully exported to: {out_csv}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest Pre-Breakout Coiled Selection")
    parser.add_argument("--years", type=int, default=1, help="Years of backtest lookback")
    parser.add_argument("--top-k", type=int, default=3, help="Top K coiled picks per day")
    parser.add_argument("--hold-days", type=int, default=1, help="Max holding days (1 for pure intraday, 2 for swing carry)")
    parser.add_argument("--universe", type=str, default="500", help="Universe: 500, 200, or json path")
    args = parser.parse_args()

    run_prebreakout_backtest(years=args.years, top_k=args.top_k, max_hold_days=args.hold_days, universe=args.universe)

