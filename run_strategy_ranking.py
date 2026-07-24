import os
import pandas as pd
import numpy as np
from backtest_engine import SimulationEngine
from strategies import BacktestConfig

def main():
    print("=" * 70)
    print("      UPGRADED HIGH-PARITY STRATEGY PERFORMANCE RANKING REPORT      ")
    print("=" * 70)
    
    strat_names = {
        1: "Strategy 1 (Trend Supertrend)",
        2: "Strategy 2 (Pullback Momentum)",
        3: "Strategy 3 (Triple Momentum)",
        4: "Strategy 4 (WMA/SMA Cross)",
        5: "Strategy 5 (RSI/EMA/Compression)",
        6: "Strategy 6 (New Strategy)",
        7: "Strategy 7 (Range-Bound Volatility)",
        8: "Strategy 8 (Daily 9:30 AM Entry)",
        9: "Strategy 9 (Reverse Engineered Decision Tree)",
        10: "Strategy 10 (Hilega Milega)"
    }
    
    rank_results = []
    
    for i, name in strat_names.items():
        print(f"\n[RUNNING] Simulating {name}...")
        
        # Set clean config enabling ONLY the current target strategy
        cfg = BacktestConfig()
        cfg.ENABLE_STRATEGY_1 = (i == 1)
        cfg.ENABLE_STRATEGY_2 = (i == 2)
        cfg.ENABLE_STRATEGY_3 = (i == 3)
        cfg.ENABLE_STRATEGY_4 = (i == 4)
        cfg.ENABLE_STRATEGY_5 = (i == 5)
        cfg.ENABLE_STRATEGY_6 = (i == 6)
        cfg.ENABLE_STRATEGY_7 = (i == 7)
        cfg.ENABLE_STRATEGY_8 = (i == 8)
        cfg.ENABLE_STRATEGY_9 = (i == 9)
        cfg.ENABLE_STRATEGY_10 = (i == 10)
        cfg.apply_strategy_defaults(f"Strategy_{i}")
        
        # Run upgraded high-parity simulation engine
        sim = SimulationEngine(cfg)
        sim.load_data() # Will load spot and generate correct signals for this strategy
        results = sim.run()
        
        if not results.empty:
            total_trades = len(results)
            win_rate = (len(results[results['PnL'] > 0]) / total_trades) * 100
            gross_pnl = results['Gross_PnL'].sum()
            charges = results['Charges'].sum()
            net_pnl = results['PnL'].sum()
            
            gross_profit = results[results['PnL'] > 0]['PnL'].sum()
            gross_loss = abs(results[results['PnL'] < 0]['PnL'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
            
            avg_pnl = net_pnl / total_trades
            max_pnl = results['PnL'].max()
            min_pnl = results['PnL'].min()
            
            rank_results.append({
                "Strategy": name,
                "Trades": total_trades,
                "Win Rate (%)": round(win_rate, 1),
                "Profit Factor": round(profit_factor, 2),
                "Gross PnL (Rs.)": round(gross_pnl, 2),
                "Charges (Rs.)": round(charges, 2),
                "Net PnL (Rs.)": round(net_pnl, 2),
                "Avg PnL/Trade": round(avg_pnl, 2),
                "Max Win": round(max_pnl, 2),
                "Max Loss": round(min_pnl, 2)
            })
            
            print(f"  -> Total Trades: {total_trades}")
            print(f"  -> Win Rate:    {win_rate:.1f}%")
            print(f"  -> Net PnL:     Rs.{net_pnl:.2f}")
        else:
            print("  -> No trades executed.")
            rank_results.append({
                "Strategy": name,
                "Trades": 0,
                "Win Rate (%)": 0.0,
                "Profit Factor": 0.0,
                "Gross PnL (Rs.)": 0.0,
                "Charges (Rs.)": 0.0,
                "Net PnL (Rs.)": 0.0,
                "Avg PnL/Trade": 0.0,
                "Max Win": 0.0,
                "Max Loss": 0.0
            })
            
    # Compile and Sort rankings
    df_ranks = pd.DataFrame(rank_results)
    df_ranks = df_ranks.sort_values(by="Net PnL (Rs.)", ascending=False)
    
    print("\n" + "="*95)
    print("                       FINAL STRATEGY RANKINGS (BY NET PNL)            ")
    print("="*95)
    
    # Print a beautiful ASCII Table
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(df_ranks.to_string(index=False))
    print("="*95)
    
    # Save results to CSV
    ranks_path = os.path.join(os.path.dirname(__file__), "strategy_rankings.csv")
    df_ranks.to_csv(ranks_path, index=False)
    print(f"[SUCCESS] Rankings saved to strategy_rankings.csv\n")

if __name__ == "__main__":
    main()
