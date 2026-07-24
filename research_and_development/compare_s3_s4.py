import os
import pandas as pd
import numpy as np
from datetime import datetime
from backtest_engine import SimulationEngine
from strategies import BacktestConfig

def analyze_trades(trades_df):
    if trades_df.empty:
        return {
            "Net PnL": 0.0, "Gross PnL": 0.0, "Charges": 0.0, "Trades": 0,
            "Win Rate": 0.0, "Profit Factor": 0.0, "Max Win": 0.0, "Max Loss": 0.0,
            "Avg Win": 0.0, "Avg Loss": 0.0, "Max Drawdown": 0.0,
            "CE Net PnL": 0.0, "PE Net PnL": 0.0, "CE Trades": 0, "PE Trades": 0
        }
    
    # Basic metrics
    net_pnl = trades_df['PnL'].sum()
    gross_pnl = trades_df['Gross_PnL'].sum()
    charges = trades_df['Charges'].sum()
    total_trades = len(trades_df)
    
    winning_trades = trades_df[trades_df['PnL'] > 0]
    losing_trades = trades_df[trades_df['PnL'] <= 0]
    
    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0.0
    
    gross_profit = winning_trades['PnL'].sum()
    gross_loss = abs(losing_trades['PnL'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    
    max_win = trades_df['PnL'].max()
    max_loss = trades_df['PnL'].min()
    
    avg_win = winning_trades['PnL'].mean() if len(winning_trades) > 0 else 0.0
    avg_loss = losing_trades['PnL'].mean() if len(losing_trades) > 0 else 0.0
    
    # Calculate Max Drawdown based on cumulative net PnL equity curve
    trades_df = trades_df.sort_values(by="Entry_Time").copy()
    trades_df['Cum_PnL'] = trades_df['PnL'].cumsum()
    cum_max = trades_df['Cum_PnL'].cummax()
    drawdowns = cum_max - trades_df['Cum_PnL']
    max_dd = drawdowns.max()
    
    # CE vs PE breakdown
    ce_trades = trades_df[trades_df['Type'] == 'CE']
    pe_trades = trades_df[trades_df['Type'] == 'PE']
    
    ce_net_pnl = ce_trades['PnL'].sum() if not ce_trades.empty else 0.0
    pe_net_pnl = pe_trades['PnL'].sum() if not pe_trades.empty else 0.0
    
    # Year-by-year consistency
    trades_df['Entry_Time'] = pd.to_datetime(trades_df['Entry_Time'])
    trades_df['Year'] = trades_df['Entry_Time'].dt.year
    yearly_pnl = trades_df.groupby('Year')['PnL'].sum().to_dict()
    
    return {
        "Net PnL": net_pnl,
        "Gross PnL": gross_pnl,
        "Charges": charges,
        "Trades": total_trades,
        "Win Rate": win_rate,
        "Profit Factor": profit_factor,
        "Max Win": max_win,
        "Max Loss": max_loss,
        "Avg Win": avg_win,
        "Avg Loss": avg_loss,
        "Max Drawdown": max_dd,
        "CE Net PnL": ce_net_pnl,
        "PE Net PnL": pe_net_pnl,
        "CE Trades": len(ce_trades),
        "PE Trades": len(pe_trades),
        "Yearly PnL": yearly_pnl
    }

def run_simulation_run(strategy_num, leg_mode):
    cfg = BacktestConfig()
    cfg.ENABLE_STRATEGY_1 = False
    cfg.ENABLE_STRATEGY_2 = False
    cfg.ENABLE_STRATEGY_3 = (strategy_num == 3)
    cfg.ENABLE_STRATEGY_4 = (strategy_num == 4)
    cfg.LEG_MODE = leg_mode  # BUY or SELL
    
    # Apply optimized parameter sets
    if strategy_num == 3:
        cfg.TM_EMA_LONG = 30
        cfg.TM_EMA_SHORT = 8
        cfg.TM_ST_MUL = 1.5
        cfg.TM_ADX_THRESHOLD = 10
        cfg.ATR_TP_MULTIPLIER = 4.0
    else:
        cfg.S4_WMA_87 = 87
        cfg.S4_WMA_200 = 200
        cfg.ATR_TP_MULTIPLIER = 4.0
        
    engine = SimulationEngine(cfg, override_sl=0.8, override_trail=0.5)
    engine.load_data()
    trades = engine.run()
    return analyze_trades(trades)

def main():
    print("=" * 100)
    print("       STRATEGY 3 VS STRATEGY 4: DECOUPLED BUYING VS SELLING (2021-2026)      ")
    print("=" * 100)
    
    # Run Strategy 3
    print("\n[RUNNING] Strategy 3 (Triple Momentum) in Option BUYING mode...")
    s3_buy = run_simulation_run(3, "BUY")
    print("[RUNNING] Strategy 3 (Triple Momentum) in Option SELLING mode...")
    s3_sell = run_simulation_run(3, "SELL")
    
    # Run Strategy 4
    print("\n[RUNNING] Strategy 4 (WMA/SMA Cross) in Option BUYING mode...")
    s4_buy = run_simulation_run(4, "BUY")
    print("[RUNNING] Strategy 4 (WMA/SMA Cross) in Option SELLING mode...")
    s4_sell = run_simulation_run(4, "SELL")
    
    # Print Comparative Table
    print("\n" + "="*120)
    print("                                      FINAL DECISION MATRIX: BUY VS SELL MODE                                  ")
    print("="*120)
    print(f"{'Metric':<25} | {'S3 BUY (Long)':<20} | {'S3 SELL (Short)':<20} | {'S4 BUY (Long)':<20} | {'S4 SELL (Short)':<20}")
    print("-" * 120)
    
    print(f"{'Net PnL (Rs.)':<25} | {s3_buy['Net PnL']:+18,.2f} | {s3_sell['Net PnL']:+18,.2f} | {s4_buy['Net PnL']:+18,.2f} | {s4_sell['Net PnL']:+18,.2f}")
    print(f"{'Gross PnL (Rs.)':<25} | {s3_buy['Gross PnL']:+18,.2f} | {s3_sell['Gross PnL']:+18,.2f} | {s4_buy['Gross PnL']:+18,.2f} | {s4_sell['Gross PnL']:+18,.2f}")
    print(f"{'Trading Charges (Rs.)':<25} | {s3_buy['Charges']:18,.2f} | {s3_sell['Charges']:18,.2f} | {s4_buy['Charges']:18,.2f} | {s4_sell['Charges']:18,.2f}")
    print(f"{'Total Trades':<25} | {s3_buy['Trades']:18} | {s3_sell['Trades']:18} | {s4_buy['Trades']:18} | {s4_sell['Trades']:18}")
    print(f"{'Win Rate (%)':<25} | {s3_buy['Win Rate']:17.1f}% | {s3_sell['Win Rate']:17.1f}% | {s4_buy['Win Rate']:17.1f}% | {s4_sell['Win Rate']:17.1f}%")
    print(f"{'Profit Factor':<25} | {s3_buy['Profit Factor']:18.2f} | {s3_sell['Profit Factor']:18.2f} | {s4_buy['Profit Factor']:18.2f} | {s4_sell['Profit Factor']:18.2f}")
    print(f"{'Max Drawdown (Rs.)':<25} | {s3_buy['Max Drawdown']:18,.2f} | {s3_sell['Max Drawdown']:18,.2f} | {s4_buy['Max Drawdown']:18,.2f} | {s4_sell['Max Drawdown']:18,.2f}")
    print(f"{'Avg Win / Loss (Rs.)':<25} | {s3_buy['Avg Win']:,.0f} / {s3_buy['Avg Loss']:,.0f} | {s3_sell['Avg Win']:,.0f} / {s3_sell['Avg Loss']:,.0f} | {s4_buy['Avg Win']:,.0f} / {s4_buy['Avg Loss']:,.0f} | {s4_sell['Avg Win']:,.0f} / {s4_sell['Avg Loss']:,.0f}")
    
    print("-" * 120)
    print("Year-by-Year Net PnL (Rs.):")
    all_years = sorted(list(set(s3_buy["Yearly PnL"].keys()) | set(s3_sell["Yearly PnL"].keys())))
    for y in all_years:
        y3b = s3_buy["Yearly PnL"].get(y, 0.0)
        y3s = s3_sell["Yearly PnL"].get(y, 0.0)
        y4b = s4_buy["Yearly PnL"].get(y, 0.0)
        y4s = s4_sell["Yearly PnL"].get(y, 0.0)
        print(f"Year {y} Net PnL | {y3b:+18,.2f} | {y3s:+18,.2f} | {y4b:+18,.2f} | {y4s:+18,.2f}")
    print("="*120)

if __name__ == "__main__":
    main()
