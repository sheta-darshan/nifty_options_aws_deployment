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

def run_split_tranche_simulation():
    config = BacktestConfig()
    config.LEG_MODE = "SELL"
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    config.ENABLE_STRATEGY_22 = True
    config.apply_strategy_defaults("Strategy_22")

    # Baseline 180-day run
    engine = SimulationEngine(config, instrument_name="NIFTY", offline_mode=False, backtest_days=180)
    engine.load_data()
    engine.inst_config['points_target_sell'] = 25.0
    engine.inst_config['points_sl_sell'] = 74.0
    df_base = engine.run(write_to_csv=False)
    
    print("================================================================================")
    print(" EXPERIMENT 3: SPLIT-TARGET & PROTECTED RUNNER LOT SIMULATION (NIFTY 180D) ")
    print("================================================================================")
    print(f"Baseline (All 5 lots @ 25 pts):")
    print(f"  Trades: {len(df_base)} | Win Rate: {(len(df_base[df_base['PnL']>0])/len(df_base))*100:.1f}% | Net PnL: Rs.{df_base['PnL'].sum():,.2f} | PF: {round(df_base[df_base['Gross_PnL']>0]['Gross_PnL'].sum()/abs(df_base[df_base['Gross_PnL']<0]['Gross_PnL'].sum()), 2)}")
    print("-" * 80)

    # Now let's test Split Tranches:
    # Tranche 1: 3 lots (60% qty = 195 qty) with Target 25, SL 74
    # Tranche 2 (Runner): 2 lots (40% qty = 130 qty) with Target T2, SL 74.
    # When Target 25 is hit, Tranche 2 SL is immediately locked at Breakeven (Cost).
    
    runner_targets = [30.0, 35.0, 40.0, 45.0, 50.0]
    
    print(f"{'Setup':<30} | {'Trades':>6} | {'Win Rate':>8} | {'Net PnL (Rs.)':>16} | {'PnL vs Baseline':>18}")
    print("-" * 85)

    # For each trade in df_base, examine the option price series after entry
    for t2_target in runner_targets:
        split_pnls = []
        wins_count = 0
        
        for idx, trade in df_base.iterrows():
            entry_price = trade['Entry_Price']
            exit_reason = trade['Exit_Reason']
            actual_pnl_pts = (entry_price - trade['Exit_Price'])  # positive = profit for SELL
            
            # 1. Tranche 1 (3 lots = 195 qty)
            # Exactly follows the baseline trade
            pnl_t1 = (entry_price - trade['Exit_Price']) * 195 - (trade['Charges'] * 0.6)
            
            # 2. Tranche 2 (2 lots = 130 qty)
            # If baseline trade was a Stop Loss (-74 pts), runner also stopped out at -74 pts
            if exit_reason in ['StopLoss', 'GapUp_SL']:
                pnl_t2 = (entry_price - trade['Exit_Price']) * 130 - (trade['Charges'] * 0.4)
            elif exit_reason in ['Target', 'GapDown_Target']:
                # The option hit 25 points!
                # Now Tranche 2 has SL at Entry (Breakeven).
                # Check option df to see if it reached t2_target or hit Breakeven first!
                opt_symbol = trade['Option_Symbol']
                opt_df = None
                
                # Fetch option candle stream from engine caches
                if opt_symbol in engine.option_cache:
                    opt_df = engine.option_cache[opt_symbol]
                
                reached_runner_target = False
                hit_breakeven = False
                runner_exit_pts = 25.0  # fallback
                
                if opt_df is not None and not opt_df.empty:
                    entry_time = pd.to_datetime(trade['Entry_Time'])
                    exit_time = pd.to_datetime(trade['Exit_Time'])
                    
                    # Candles from entry onwards
                    post_entry = opt_df[opt_df.index >= entry_time]
                    
                    # Find when 25 pt target was hit
                    t1_hit_time = None
                    target_price_25 = entry_price - 25.0
                    for c_time, c_row in post_entry.iterrows():
                        if c_row['low'] <= target_price_25:
                            t1_hit_time = c_time
                            break
                    
                    if t1_hit_time is not None:
                        # From t1_hit_time onwards, Tranche 2 SL is entry_price, Target is entry_price - t2_target
                        runner_tp_price = entry_price - t2_target
                        runner_sl_price = entry_price  # Breakeven
                        
                        after_t1 = post_entry[post_entry.index > t1_hit_time]
                        for r_time, r_row in after_t1.iterrows():
                            # Check if target hit
                            if r_row['low'] <= runner_tp_price:
                                reached_runner_target = True
                                runner_exit_pts = t2_target
                                break
                            # Check if SL (breakeven) hit
                            if r_row['high'] >= runner_sl_price:
                                hit_breakeven = True
                                runner_exit_pts = 0.0  # exited at cost
                                break
                        else:
                            # Ended day without hitting TP or BE
                            runner_exit_pts = max(0.0, entry_price - after_t1.iloc[-1]['close']) if not after_t1.empty else 25.0
                
                if reached_runner_target:
                    runner_pts = t2_target
                elif hit_breakeven:
                    runner_pts = 0.0
                else:
                    runner_pts = runner_exit_pts
                    
                pnl_t2 = (runner_pts * 130) - (trade['Charges'] * 0.4)
            else:
                pnl_t2 = (entry_price - trade['Exit_Price']) * 130 - (trade['Charges'] * 0.4)

            total_split_pnl = pnl_t1 + pnl_t2
            split_pnls.append(total_split_pnl)
            if total_split_pnl > 0:
                wins_count += 1

        total_net = sum(split_pnls)
        wr = (wins_count / len(split_pnls)) * 100
        diff = total_net - df_base['PnL'].sum()
        diff_str = f"+Rs.{diff:,.2f}" if diff >= 0 else f"-Rs.{abs(diff):,.2f}"
        setup_name = f"3L @ 25 pts + 2L @ {int(t2_target)} pts (BE Protected)"
        print(f"{setup_name:<30} | {len(split_pnls):>6} | {wr:>7.1f}% | Rs.{total_net:>13,.2f} | {diff_str:>18}")

if __name__ == "__main__":
    run_split_tranche_simulation()
