"""
research_and_development/benchmark_universal_stocks.py

Institutional Universal Stock Strategy Benchmark Harness
=========================================================
Benchmarks 4 candidate strategies across a diversified 50-stock NSE universe
over 2 years of 1-minute OHLCV historical data.

Target Criteria:
  1. Win Rate: 70% to 80%+
  2. Low Trade Frequency: 0.5 to 2.0 trades / week / stock
  3. Universal Consistency: Robust positive expectancy across >= 80% of stocks
  4. Profit Factor: >= 1.80

Candidates:
  - Strategy 17: Meta Adaptive Multi-Regime Engine (5m WMA Breakout / RSI Reversion)
  - Strategy 21: Institutional Multi-Pivot Reversal Engine (CPR + Camarilla + Wick Rejection)
  - Strategy 22: Triple Momentum Enhanced TM-Pro (5m Triple EMA + Supertrend + ADX + Chop Filter)
  - Strategy 23: Stealth Absorption Multi-Day Swing Engine (10m Opening Box + RVOL >= 1.5x)
"""

import os
import sys
import time
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, time as dt_time
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
sys.path.insert(0, BASE_DIR)

from strategies.strategy_17 import Strategy17
from strategies.strategy_21 import Strategy21
from strategies.strategy_22 import Strategy22
from strategies.strategy_23 import Strategy23

# Diversified 50-Stock Benchmark Universe
BENCHMARK_STOCKS = [
    # Banking & Financials (10)
    'HDFCBANK', 'ICICIBANK', 'SBIN', 'AXISBANK', 'KOTAKBANK',
    'BAJFINANCE', 'BAJAJFINSV', 'INDUSINDBK', 'CHOLAFIN', 'FEDERALBNK',
    # IT & Tech (8)
    'TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM',
    'PERSISTENT', 'COFORGE', 'LTIM',
    # Auto & Mobility (6)
    'TATAMOTORS', 'MARUTI', 'M&M', 'BAJAJ-AUTO', 'HEROMOTOCO', 'BHARATFORG',
    # Metals, Energy & Infra (10)
    'RELIANCE', 'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'COALINDIA',
    'ONGC', 'NTPC', 'POWERGRID', 'LT', 'ADANIENT',
    # Pharma & Healthcare (6)
    'SUNPHARMA', 'DRREDDY', 'CIPLA', 'APOLLOHOSP', 'DIVISLAB', 'LUPIN',
    # Consumer, FMCG & Retail (6)
    'ITC', 'HINDUNILVR', 'TITAN', 'ASIANPAINT', 'TRENT', 'TATACONSUM',
    # High Beta & Industrials (4)
    'DIXON', 'HAL', 'BEL', 'POLYCAB'
]

def load_stock_data(symbol: str, years: int = 2) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
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
        df = df[(df['time'] >= dt_time(9, 15)) & (df['time'] <= dt_time(15, 29))].copy()
        return df
    except Exception as e:
        return None

def calc_equity_costs(buy_val: float, sell_val: float, is_delivery: bool = False) -> float:
    brokerage = 0.0  # Zero delivery brokerage on Dhan, Rs 20 intraday max
    if is_delivery:
        stt = (buy_val + sell_val) * 0.0010  # 0.10% buy + 0.10% sell STT
    else:
        brokerage = min(40.0, 0.0003 * (buy_val + sell_val))
        stt = sell_val * 0.00025  # 0.025% on sell for intraday equity
    exch = (buy_val + sell_val) * 0.0000322
    stamp = buy_val * 0.00015
    sebi = (buy_val + sell_val) * 0.000001
    gst = 0.18 * (brokerage + exch)
    return brokerage + stt + exch + stamp + sebi + gst

def simulate_strategy_trades(df: pd.DataFrame, strat_name: str, signals_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Simulates trades with zero lookahead bias:
    Signal detected at index i (candle close) -> Entry executed at index i+1 (candle open).
    Normalized percentage risk/reward with dynamic breakeven.
    """
    trades = []
    if signals_df is None or len(signals_df) == 0:
        return trades

    sig_col = 'Signal' if 'Signal' in signals_df.columns else 'signal'
    if sig_col not in signals_df.columns:
        return trades

    times = df['time'].values
    dates = df['date'].values
    opens = df['open'].values
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    signals = signals_df[sig_col].values
    n = len(df)

    in_pos = False
    entry_idx = 0
    entry_price = 0.0
    entry_date = None
    pos_type = 0  # 1 = Long, -1 = Short
    sl_price = 0.0
    tp_price = 0.0
    be_price = 0.0
    be_active = False
    highest_price = 0.0
    lowest_price = 999999.0
    max_hold_days = 1 if strat_name != "Strategy_23" else 5

    # Strategy-specific normalized exit rules
    if strat_name == "Strategy_23":
        # S-AMS Multi-Day Swing
        sl_pct = 0.012  # Box low proxy ~1.2%
        be_threshold_pct = 0.020  # +2.0% triggers Breakeven
        tp_pct = 0.045  # +4.5% target
        is_delivery = True
    elif strat_name == "Strategy_22":
        # TM-Pro 5m Trend Breakout
        sl_pct = 0.008  # 0.8% Stop Loss
        be_threshold_pct = 0.006  # +0.6% triggers Breakeven
        tp_pct = 0.016  # +1.6% target (2:1 R:R)
        is_delivery = False
    elif strat_name == "Strategy_21":
        # Institutional Pivot Reversals
        sl_pct = 0.009  # 0.9% Stop Loss
        be_threshold_pct = 0.007  # +0.7% triggers Breakeven
        tp_pct = 0.018  # +1.8% target (2:1 R:R)
        is_delivery = False
    else: # Strategy_17
        # Meta Adaptive
        sl_pct = 0.008
        be_threshold_pct = 0.006
        tp_pct = 0.016
        is_delivery = False

    ALLOCATION = 100000.0  # Normalized ₹1,00,000 position capital

    i = 0
    while i < n - 1:
        if not in_pos:
            sig = signals[i]
            # Long entries supported on all; Short only intraday
            if sig == 1 or (sig == -1 and not is_delivery):
                # Entry at open of next bar i+1
                entry_idx = i + 1
                entry_price = opens[entry_idx]
                entry_date = dates[entry_idx]
                pos_type = sig
                in_pos = True
                be_active = False
                highest_price = entry_price
                lowest_price = entry_price

                if pos_type == 1:
                    sl_price = entry_price * (1.0 - sl_pct)
                    tp_price = entry_price * (1.0 + tp_pct)
                    be_trigger = entry_price * (1.0 + be_threshold_pct)
                else:
                    sl_price = entry_price * (1.0 + sl_pct)
                    tp_price = entry_price * (1.0 - tp_pct)
                    be_trigger = entry_price * (1.0 - be_threshold_pct)

                i += 1
                continue
        else:
            cur_time = times[i]
            cur_date = dates[i]
            cur_high = highs[i]
            cur_low = lows[i]
            cur_close = closes[i]

            days_held = (cur_date - entry_date).days if hasattr(cur_date - entry_date, 'days') else 0
            exit_price = None
            exit_reason = None

            # Track peak prices
            if cur_high > highest_price:
                highest_price = cur_high
            if cur_low < lowest_price:
                lowest_price = cur_low

            # Check Breakeven trigger
            if not be_active:
                if pos_type == 1 and cur_high >= be_trigger:
                    sl_price = entry_price  # Slide SL to Entry (Zero Risk)
                    be_active = True
                elif pos_type == -1 and cur_low <= be_trigger:
                    sl_price = entry_price
                    be_active = True

            # 1. Stop Loss Hit
            if pos_type == 1 and cur_low <= sl_price:
                exit_price = min(opens[i], sl_price)
                exit_reason = "BREAKEVEN" if be_active and sl_price == entry_price else "STOP_LOSS"
            elif pos_type == -1 and cur_high >= sl_price:
                exit_price = max(opens[i], sl_price)
                exit_reason = "BREAKEVEN" if be_active and sl_price == entry_price else "STOP_LOSS"

            # 2. Target Hit
            elif pos_type == 1 and cur_high >= tp_price:
                exit_price = max(opens[i], tp_price)
                exit_reason = "TARGET"
            elif pos_type == -1 and cur_low <= tp_price:
                exit_price = min(opens[i], tp_price)
                exit_reason = "TARGET"

            # 3. Time Stop (Intraday EOD or Swing Max Hold)
            elif not is_delivery and cur_time >= dt_time(15, 15):
                exit_price = cur_close
                exit_reason = "EOD_EXIT"
            elif is_delivery and days_held >= max_hold_days and cur_time >= dt_time(15, 15):
                exit_price = cur_close
                exit_reason = "TIME_EXPIRE"

            if exit_price is not None:
                # Trade complete
                shares = int(ALLOCATION / entry_price) if entry_price > 0 else 0
                if shares > 0:
                    if pos_type == 1:
                        gross_pnl = (exit_price - entry_price) * shares
                        pct_ret = (exit_price - entry_price) / entry_price
                    else:
                        gross_pnl = (entry_price - exit_price) * shares
                        pct_ret = (entry_price - exit_price) / entry_price

                    buy_val = entry_price * shares
                    sell_val = exit_price * shares
                    charges = calc_equity_costs(buy_val, sell_val, is_delivery=is_delivery)
                    net_pnl = gross_pnl - charges

                    trades.append({
                        'entry_time': df.index[entry_idx],
                        'exit_time': df.index[i],
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pos_type': 'LONG' if pos_type == 1 else 'SHORT',
                        'gross_pnl': gross_pnl,
                        'net_pnl': net_pnl,
                        'pct_ret': pct_ret * 100.0,
                        'exit_reason': exit_reason,
                        'is_win': net_pnl > 0
                    })

                in_pos = False
                be_active = False

        i += 1

    return trades

def run_benchmark(stocks: List[str] = None, max_stocks: int = 50, years: int = 2):
    target_stocks = (stocks if stocks else BENCHMARK_STOCKS)[:max_stocks]
    print("=" * 115, flush=True)
    print(f"   INSTITUTIONAL BENCHMARK: 4 STRATEGY CANDIDATES ON {len(target_stocks)} NSE EQUITIES ({years} YEARS)", flush=True)
    print("=" * 115, flush=True)
    print("Target Hurdles: Win Rate >= 70%, Trade Frequency 0.5 - 2.0 / week, Universality >= 80%\n", flush=True)

    strategies = [
        ("Strategy_23", Strategy23()),
        ("Strategy_22", Strategy22()),
        ("Strategy_21", Strategy21()),
        ("Strategy_17", Strategy17())
    ]

    # Preload stock datasets
    print("Pre-loading historical stock data...", flush=True)
    stock_dfs = {}
    for sym in target_stocks:
        df = load_stock_data(sym, years=years)
        if df is not None:
            stock_dfs[sym] = df

    print(f"Successfully loaded {len(stock_dfs)}/{len(target_stocks)} stocks with full 1-min data.\n", flush=True)

    summary_rows = []
    all_trade_results = {s_name: [] for s_name, _ in strategies}

    for s_name, strat_obj in strategies:
        print(f"--> Simulating {s_name} across {len(stock_dfs)} stocks...", flush=True)
        strat_trades = []
        stock_win_rates = []
        stock_pfs = []
        stock_pnls = []

        for sym, df in stock_dfs.items():
            try:
                sig_df = strat_obj.generate_signals(df)
                trades = simulate_strategy_trades(df, s_name, sig_df)
                strat_trades.extend(trades)

                if len(trades) >= 5:
                    wins = sum(1 for t in trades if t['is_win'])
                    wr = (wins / len(trades)) * 100.0
                    gp = sum(t['net_pnl'] for t in trades if t['net_pnl'] > 0)
                    gl = abs(sum(t['net_pnl'] for t in trades if t['net_pnl'] < 0))
                    pf = (gp / gl) if gl > 0 else (2.0 if gp > 0 else 0.0)
                    total_pnl = sum(t['net_pnl'] for t in trades)

                    stock_win_rates.append(wr)
                    stock_pfs.append(pf)
                    stock_pnls.append(total_pnl)
            except Exception as e:
                continue

        all_trade_results[s_name] = strat_trades

        total_trades = len(strat_trades)
        total_wins = sum(1 for t in strat_trades if t['is_win'])
        overall_wr = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_win_val = sum(t['net_pnl'] for t in strat_trades if t['net_pnl'] > 0)
        gross_loss_val = abs(sum(t['net_pnl'] for t in strat_trades if t['net_pnl'] < 0))
        overall_pf = (gross_win_val / gross_loss_val) if gross_loss_val > 0 else 0.0
        total_net_pnl = sum(t['net_pnl'] for t in strat_trades)

        # Estimate average trades per week per stock
        trading_weeks = (years * 50)
        trades_per_wk_per_stock = (total_trades / (len(stock_dfs) * trading_weeks)) if len(stock_dfs) > 0 else 0.0

        # Universality: % of stocks with positive expectancy
        profitable_stocks = sum(1 for pnl in stock_pnls if pnl > 0)
        stocks_above_70_wr = sum(1 for wr in stock_win_rates if wr >= 70.0)
        universality_pct = (profitable_stocks / len(stock_pnls) * 100.0) if stock_pnls else 0.0

        summary_rows.append({
            'Strategy': s_name,
            'Total_Trades': total_trades,
            'Trades_Per_Wk_Stock': round(trades_per_wk_per_stock, 2),
            'Win_Rate_Pct': round(overall_wr, 1),
            'Profit_Factor': round(overall_pf, 2),
            'Total_Net_PnL': round(total_net_pnl, 2),
            'Universality_Profitable': f"{profitable_stocks}/{len(stock_pnls)} ({round(universality_pct, 1)}%)",
            'Stocks_Above_70_WR': f"{stocks_above_70_wr}/{len(stock_win_rates)}"
        })

    print("\n" + "=" * 115, flush=True)
    print("                     OVERALL 50-STOCK BENCHMARK SCORECARD SUMMARY", flush=True)
    print("=" * 115, flush=True)
    res_df = pd.DataFrame(summary_rows)
    print(res_df.to_string(index=False), flush=True)
    print("=" * 115 + "\n", flush=True)

    # Save to CSV
    csv_out = os.path.join(BASE_DIR, "stock_benchmark_scorecard.csv")
    res_df.to_csv(csv_out, index=False)
    print(f"Benchmark scorecard successfully exported to: {csv_out}", flush=True)
    return res_df, all_trade_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Institutional Universal Stock Strategy Benchmark")
    parser.add_argument("--stocks", type=int, default=50, help="Number of benchmark stocks to test (default: 50)")
    parser.add_argument("--years", type=int, default=2, help="Years of historical 1-minute data (default: 2)")
    args = parser.parse_args()

    run_benchmark(max_stocks=args.stocks, years=args.years)
