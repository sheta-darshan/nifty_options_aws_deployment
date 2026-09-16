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

def run_conditioned_early_exit_experiment():
    print("================================================================================")
    print(" EXPERIMENT 2B: CONDITIONED EARLY CUT (LOSS THRESHOLD + INDICATOR FLIP) ")
    print("================================================================================")

    config = BacktestConfig()
    config.LEG_MODE = "SELL"
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    config.ENABLE_STRATEGY_22 = True
    config.apply_strategy_defaults("Strategy_22")

    engine = SimulationEngine(config, instrument_name="NIFTY", offline_mode=False, backtest_days=180)
    engine.load_data()
    engine.inst_config['points_target_sell'] = 25.0
    engine.inst_config['points_sl_sell'] = 74.0
    df_baseline = engine.run(write_to_csv=False)

    total_baseline_trades = len(df_baseline)
    base_wins = df_baseline[df_baseline['PnL'] > 0]
    base_losses = df_baseline[df_baseline['PnL'] < 0]
    base_wr = (len(base_wins) / total_baseline_trades) * 100
    base_net = df_baseline['PnL'].sum()
    base_pf = round(base_wins['Gross_PnL'].sum() / abs(base_losses['Gross_PnL'].sum()), 2)
    base_avg_loss = base_losses['PnL'].mean()

    print(f"Baseline: Trades {total_baseline_trades} | WR: {base_wr:.1f}% | Net PnL: Rs.{base_net:,.2f} | PF: {base_pf} | Avg Loss: Rs.{base_avg_loss:,.2f}")
    print("-" * 85)

    df_spot = engine.df_spot
    import pandas_ta as ta
    df_5m = df_spot.resample('5min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    df_5m['EMA_8'] = ta.ema(df_5m['close'], length=8)
    df_5m['EMA_18'] = ta.ema(df_5m['close'], length=18)
    st = ta.supertrend(df_5m['high'], df_5m['low'], df_5m['close'], length=10, multiplier=2.5)
    st_col = [c for c in st.columns if c.startswith('SUPERT_')][0]
    df_5m['ST_Line'] = st[st_col]
    df_5m['ST_Trend'] = st[[c for c in st.columns if c.startswith('SUPERTd_')][0]]
    
    df_5m_shifted = df_5m[['EMA_8', 'EMA_18', 'ST_Line', 'ST_Trend']].shift(1)
    df_spot_ind = df_spot.join(df_5m_shifted, how='left').ffill()

    print(f"{'Condition (Min Loss)':<25} | {'Trades':>6} | {'Win Rate':>8} | {'PF':>6} | {'Net PnL (Rs.)':>16} | {'Avg Loss':>12} | {'Net vs Base':>14}")
    print("-" * 95)

    # Test varying loss filters before allowing early cut
    for min_loss_pts in [25.0, 30.0, 35.0, 40.0, 45.0, 50.0]:
        sim_pnls = []
        wins = 0
        loss_pnls = []
        win_pnls = []

        for idx, trade in df_baseline.iterrows():
            entry_time = pd.to_datetime(trade['Entry_Time'])
            exit_time = pd.to_datetime(trade['Exit_Time'])
            entry_price = trade['Entry_Price']
            exit_reason = trade['Exit_Reason']
            trade_type = trade['Type']
            qty = trade['Qty']
            
            trade_spot = df_spot_ind[(df_spot_ind.index >= entry_time) & (df_spot_ind.index <= exit_time)]
            
            early_cut_time = None
            early_cut_spot = None
            
            for t_stamp, s_row in trade_spot.iterrows():
                if t_stamp == entry_time:
                    continue
                
                spot_entry = trade['Entry_Spot']
                delta = 0.50
                spot_diff = s_row['open'] - spot_entry
                
                # Estimated option points loss
                if trade_type == "PE":
                    opt_est_pts_loss = spot_diff * (-delta)  # spot dropped -> loss
                else:
                    opt_est_pts_loss = spot_diff * delta   # spot rose -> loss
                    
                # Only consider cutting if option is in paper loss >= min_loss_pts
                if opt_est_pts_loss >= min_loss_pts:
                    # Check indicator breakdown
                    if trade_type == "PE":
                        st_broken = (s_row['ST_Trend'] == -1) or (s_row['close'] < s_row['ST_Line'])
                    else:
                        st_broken = (s_row['ST_Trend'] == 1) or (s_row['close'] > s_row['ST_Line'])
                        
                    if st_broken:
                        early_cut_time = t_stamp
                        early_cut_spot = s_row['open']
                        break
            
            if early_cut_time is not None and early_cut_time < exit_time:
                spot_entry = trade['Entry_Spot']
                delta = 0.50
                spot_diff = early_cut_spot - spot_entry
                if trade_type == "PE":
                    opt_est_exit = entry_price + (-spot_diff * delta)
                else:
                    opt_est_exit = entry_price + (spot_diff * delta)
                opt_est_exit = max(0.05, opt_est_exit)
                pnl = (entry_price - opt_est_exit) * qty - trade['Charges']
            else:
                pnl = trade['PnL']
                
            sim_pnls.append(pnl)
            if pnl > 0:
                wins += 1
                win_pnls.append(pnl)
            else:
                loss_pnls.append(pnl)

        total_net = sum(sim_pnls)
        wr = (wins / len(sim_pnls)) * 100
        total_w = sum(win_pnls) if win_pnls else 0
        total_l = abs(sum(loss_pnls)) if loss_pnls else 1.0
        pf = round(total_w / total_l, 2)
        avg_loss = (sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0
        diff = total_net - base_net
        diff_str = f"+Rs.{diff:,.2f}" if diff >= 0 else f"-Rs.{abs(diff):,.2f}"
        cond_label = f"Loss >= {int(min_loss_pts)} pts + ST Flip"
        print(f"{cond_label:<25} | {len(sim_pnls):>6} | {wr:>7.1f}% | {pf:>6.2f} | Rs.{total_net:>13,.2f} | Rs.{avg_loss:>10,.2f} | {diff_str:>14}")

if __name__ == "__main__":
    run_conditioned_early_exit_experiment()
