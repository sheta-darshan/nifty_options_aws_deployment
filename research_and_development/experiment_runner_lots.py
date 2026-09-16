import os
import sys
import copy
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from strategies import BacktestConfig
from backtest_engine import SimulationEngine

def run_experiment():
    print("================================================================================")
    print(" EXPERIMENT 3: RUNNER LOTS & SPLIT-TARGET SCALING ON NIFTY (STRATEGY 22 / 3) ")
    print("================================================================================")
    
    config = BacktestConfig()
    config.LEG_MODE = "SELL"
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    config.ENABLE_STRATEGY_22 = True
    config.apply_strategy_defaults("Strategy_22")
    
    # 1. Base Engine Setup
    engine = SimulationEngine(config, instrument_name="NIFTY", offline_mode=True, backtest_days=180)
    engine.load_data()
    
    base_inst_config = copy.deepcopy(engine.inst_config)
    
    # Part A: Sweep Single Targets [20, 25, 30, 35, 40, 45, 50] to see raw decay depth
    target_sweep = [20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    sweep_results = {}
    
    print("\n--- PHASE 1: Single Target Horizon Sweep (325 qty / 5 lots) ---")
    print(f"{'Target Pts':>10} | {'Trades':>6} | {'Win Rate':>8} | {'PF':>6} | {'Net PnL (Rs.)':>14} | {'Avg/Trade':>10} | {'Max Win':>10} | {'Max Loss':>10}")
    print("-" * 88)
    
    for tp in target_sweep:
        engine.inst_config = copy.deepcopy(base_inst_config)
        engine.inst_config['points_target_sell'] = float(tp)
        engine.inst_config['points_trail_sell'] = 0.0
        
        # Reset trade logs
        engine.trade_log = []
        df_res = engine.run(write_to_csv=False)
        
        if not df_res.empty:
            total_trades = len(df_res)
            win_rate = (len(df_res[df_res['PnL'] > 0]) / total_trades) * 100
            net_pnl = df_res['PnL'].sum()
            avg_pnl = net_pnl / total_trades
            wins = df_res[df_res['Gross_PnL'] > 0]['Gross_PnL'].sum()
            losses = abs(df_res[df_res['Gross_PnL'] < 0]['Gross_PnL'].sum())
            pf = round(wins / losses, 2) if losses > 0 else 99.99
            max_win = df_res['PnL'].max()
            max_loss = df_res['PnL'].min()
            
            sweep_results[tp] = df_res.copy()
            print(f"{tp:>10.1f} | {total_trades:>6} | {win_rate:>7.1f}% | {pf:>6.2f} | {net_pnl:>14.2f} | {avg_pnl:>10.2f} | {max_win:>10.2f} | {max_loss:>10.2f}")

    # Part B: Trailing Stop Evaluation on Wide Targets
    print("\n--- PHASE 2: Wide Target (45 pts) with Trailing Ratchet ---")
    print(f"{'Target':>8} | {'Trail Jump':>10} | {'Trades':>6} | {'Win Rate':>8} | {'PF':>6} | {'Net PnL (Rs.)':>14} | {'Avg/Trade':>10}")
    print("-" * 75)
    for trail in [10.0, 15.0, 20.0, 25.0]:
        engine.inst_config = copy.deepcopy(base_inst_config)
        engine.inst_config['points_target_sell'] = 45.0
        engine.inst_config['points_trail_sell'] = float(trail)
        engine.trade_log = []
        df_res = engine.run(write_to_csv=False)
        if not df_res.empty:
            total_trades = len(df_res)
            win_rate = (len(df_res[df_res['PnL'] > 0]) / total_trades) * 100
            net_pnl = df_res['PnL'].sum()
            avg_pnl = net_pnl / total_trades
            wins = df_res[df_res['Gross_PnL'] > 0]['Gross_PnL'].sum()
            losses = abs(df_res[df_res['Gross_PnL'] < 0]['Gross_PnL'].sum())
            pf = round(wins / losses, 2) if losses > 0 else 99.99
            print(f"{45.0:>8.1f} | {trail:>10.1f} | {total_trades:>6} | {win_rate:>7.1f}% | {pf:>6.2f} | {net_pnl:>14.2f} | {avg_pnl:>10.2f}")

    # Part C: Exact Split-Target Portfolio (Tranche 1: 3 lots @ 25 pts, Tranche 2: 2 lots @ runner targets)
    print("\n--- PHASE 3: Composite Split Tranche (3 Lots @ 25 pts + 2 Lots @ Runner Target) ---")
    print(f"{'Tranche 1':>10} | {'Tranche 2':>10} | {'Blended Trades':>14} | {'Blended Net PnL (Rs.)':>22} | {'Net PnL vs Baseline':>20}")
    print("-" * 85)
    
    baseline_pnl = sweep_results[25.0]['PnL'].sum()
    df_t1 = sweep_results[25.0]
    
    for t2_tp in [30.0, 35.0, 40.0, 45.0, 50.0]:
        df_t2 = sweep_results[t2_tp]
        # Align trades by Entry_Time
        # Tranche 1 has 3 lots = 3/5 = 60% of total size
        # Tranche 2 has 2 lots = 2/5 = 40% of total size
        merged = pd.merge(df_t1[['Entry_Time', 'PnL']], df_t2[['Entry_Time', 'PnL']], on='Entry_Time', suffixes=('_t1', '_t2'))
        if not merged.empty:
            merged['Split_PnL'] = (merged['PnL_t1'] * 0.6) + (merged['PnL_t2'] * 0.4)
            split_pnl = merged['Split_PnL'].sum()
            diff = split_pnl - baseline_pnl
            diff_str = f"+Rs.{diff:,.2f}" if diff >= 0 else f"-Rs.{abs(diff):,.2f}"
            print(f"{'3 Lots @ 25':>10} | {f'2 Lots @ {int(t2_tp)}':>10} | {len(merged):>14} | Rs.{split_pnl:>17,.2f} | {diff_str:>20}")

if __name__ == "__main__":
    run_experiment()
