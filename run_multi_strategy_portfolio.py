import os
import sys
import argparse
import pandas as pd
import numpy as np
from strategies.config import BacktestConfig
from strategies.registry import get_strategy
from backtest_engine import SimulationEngine

print("================================================================================")
print("       MULTI-STRATEGY COMBINED PORTFOLIO BACKTESTING ENGINE LOG                 ")
print("================================================================================")

parser = argparse.ArgumentParser(description="Multi-Strategy Combined Portfolio Backtest Runner")
parser.add_argument("symbols", nargs="*", default=["NIFTY"], help="Instruments to backtest (e.g., NIFTY)")
parser.add_argument("--strategies", "-s", type=int, nargs="+", default=[14, 19, 20], help="Strategy indices to run simultaneously (e.g., --strategies 14 19 20)")
parser.add_argument("--leg-mode", "-l", choices=["AUTO", "BUY", "SELL", "BOTH"], default="AUTO", help="Option leg execution mode (AUTO automatically sets BUY for 14/19 and SELL for 20)")
parser.add_argument("--days", "-d", type=int, default=100, help="Number of days of history to backtest (default: 100)")

args = parser.parse_args()

symbol = args.symbols[0].upper()
strategy_ids = args.strategies
print(f"[CONFIG] Active Instrument: {symbol}")
print(f"[CONFIG] Active Strategies: {['Strategy_' + str(s) for s in strategy_ids]}")
print(f"[CONFIG] Execution Mode:   {args.leg_mode}")
print(f"[CONFIG] Backtest Days:    {args.days}\n")

# Run each strategy and merge results into a consolidated multi-strategy portfolio
all_strategy_trades = []

for s_id in strategy_ids:
    config = BacktestConfig()
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
        
    setattr(config, f"ENABLE_STRATEGY_{s_id}", True)
    config.apply_strategy_defaults(f"Strategy_{s_id}")
    
    # Auto Leg Mode Routing
    if args.leg_mode == "AUTO":
        if s_id in [14, 19]:
            config.LEG_MODE = "BUY"
        else:
            config.LEG_MODE = "BOTH"
    else:
        config.LEG_MODE = args.leg_mode
        
    print(f"[RUNNING] Backtesting Strategy_{s_id} (Leg Mode: {config.LEG_MODE}) on {symbol}...")
    engine = SimulationEngine(config=config, instrument_name=symbol, backtest_days=args.days)
    engine.load_data()
    res = engine.run(write_to_csv=False)
    
    if not res.empty:
        res['Active_Strategy'] = f"Strategy_{s_id}"
        all_strategy_trades.append(res)

if all_strategy_trades:
    df_combined = pd.concat(all_strategy_trades, ignore_index=True)
    df_combined['Entry_Time_DT'] = pd.to_datetime(df_combined['Entry_Time'])
    df_combined.sort_values(by='Entry_Time_DT', inplace=True)
    
    total_trades = len(df_combined)
    wins = len(df_combined[df_combined['PnL'] > 0])
    win_rate = (wins / total_trades) * 100
    gross_pnl = df_combined['Gross_PnL'].sum()
    charges = df_combined['Charges'].sum()
    net_pnl = df_combined['PnL'].sum()
    
    gross_profit = df_combined[df_combined['PnL'] > 0]['PnL'].sum()
    gross_loss = abs(df_combined[df_combined['PnL'] < 0]['PnL'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    avg_pnl = net_pnl / total_trades
    
    try:
        df_combined.to_csv("multi_strategy_portfolio_trades.csv", index=False)
        out_file = "multi_strategy_portfolio_trades.csv"
    except PermissionError:
        out_file = "multi_strategy_portfolio_trades_latest.csv"
        df_combined.to_csv(out_file, index=False)
        print(f"[WARNING] 'multi_strategy_portfolio_trades.csv' is currently open in Excel. Saved results to '{out_file}' instead.")
    
    print("\n" + "="*95)
    print("                    CONSOLIDATED MULTI-STRATEGY PORTFOLIO REPORT                 ")
    print("="*95)
    print(f"Total Portfolio Trades:       {total_trades}")
    print(f"Combined Win Rate (%):        {win_rate:.1f}%")
    print(f"Combined Profit Factor:       {profit_factor:.2f}")
    print(f"Combined Gross PnL (Rs.):     Rs.{gross_pnl:,.2f}")
    print(f"Total Transaction Charges:    Rs.{charges:,.2f}")
    print(f"COMBINED NET PNL (Rs.):       Rs.{net_pnl:,.2f}")
    print(f"Average PnL per Trade:        Rs.{avg_pnl:,.2f}")
    print("="*95)
    
    # Breakdown by Strategy
    print("\n--- BREAKDOWN BY STRATEGY ---")
    summary = []
    for s_id in strategy_ids:
        s_name = f"Strategy_{s_id}"
        sub = df_combined[df_combined['Active_Strategy'] == s_name]
        if not sub.empty:
            s_trades = len(sub)
            s_wins = len(sub[sub['PnL'] > 0])
            s_wr = (s_wins / s_trades) * 100
            s_net = sub['PnL'].sum()
            summary.append({
                "Strategy": s_name,
                "Trades": s_trades,
                "Win Rate (%)": round(s_wr, 1),
                "Net PnL (Rs.)": round(s_net, 2),
                "Avg PnL/Trade": round(s_net / s_trades, 2)
            })
    print(pd.DataFrame(summary).to_string(index=False))
    print("="*95)
    print("[SUCCESS] Multi-strategy detailed trades saved to multi_strategy_portfolio_trades.csv")
else:
    print("[INFO] No trades generated for the selected strategy combination.")
