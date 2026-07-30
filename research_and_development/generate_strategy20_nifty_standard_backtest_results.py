import os
import pandas as pd
from datetime import datetime

def generate_bifurcated_backtest_csv():
    input_csv = "research_and_development/strategy20_exact_live_premium_matched_log.csv"
    if not os.path.exists(input_csv):
        print(f"[ERROR] {input_csv} not found!")
        return

    df_cycles = pd.read_csv(input_csv)
    lot_size = 65  # Current Nifty exchange lot size
    
    bifurcated_rows = []
    
    for idx, row in df_cycles.iterrows():
        cycle_num = row['Cycle']
        entry_time = row['Entry_Timestamp']
        exit_time = row['Exit_Timestamp']
        stance = row['Stance']
        entry_spot = row['Entry_Spot']
        exit_spot = row['Exit_Spot']
        
        opt_type = 'PE' if 'PUT' in str(stance).upper() else 'CE'
        
        # -------------------------------------------------------------
        # LEG 1: Long Monthly Option (BUY 3 Lots = 195 Qty @ 65 lot size)
        # -------------------------------------------------------------
        long_strike = row['Long_Strike']
        long_entry_px = row['Long_Entry_Px']
        long_exit_px = row['Long_Exit_Px']
        long_qty = 3 * lot_size
        long_pnl_pts = (long_exit_px - long_entry_px) * 3
        long_pnl_rs = (long_exit_px - long_entry_px) * long_qty
        
        bifurcated_rows.append({
            'Cycle_ID': cycle_num,
            'Leg_Role': 'MONTHLY_LONG_HEDGE',
            'Entry_Time': entry_time,
            'Exit_Time': exit_time,
            'Type': opt_type,
            'Is_Short': False,
            'Trade_Type': 'BUY',
            'Option_Symbol': f"NIFTY {opt_type} {long_strike}",
            'Strike': long_strike,
            'Strategy': 'Strategy_20',
            'Entry_Price': long_entry_px,
            'Exit_Price': long_exit_px,
            'Qty': long_qty,
            'Entry_Spot': entry_spot,
            'Exit_Spot': exit_spot,
            'Leg_PnL_Pts': round(long_pnl_pts, 2),
            'Leg_PnL_Rs': round(long_pnl_rs, 2),
            'Exit_Reason': 'Weekly_Rollover_Rebalance'
        })
        
        # -------------------------------------------------------------
        # LEG 2: Weekly Short Option 1 (SELL 1 Lot = 65 Qty @ 65 lot size)
        # -------------------------------------------------------------
        short1_strike = row['Short1_Strike']
        short1_entry_px = row['Short1_Entry_Px']
        short1_exit_px = row['Short1_Exit_Px']
        short1_qty = 1 * lot_size
        short1_pnl_pts = (short1_entry_px - short1_exit_px) * 1
        short1_pnl_rs = (short1_entry_px - short1_exit_px) * short1_qty
        
        bifurcated_rows.append({
            'Cycle_ID': cycle_num,
            'Leg_Role': 'WEEKLY_SHORT_DECAY_1',
            'Entry_Time': entry_time,
            'Exit_Time': exit_time,
            'Type': opt_type,
            'Is_Short': True,
            'Trade_Type': 'SELL',
            'Option_Symbol': f"NIFTY {opt_type} {short1_strike}",
            'Strike': short1_strike,
            'Strategy': 'Strategy_20',
            'Entry_Price': short1_entry_px,
            'Exit_Price': short1_exit_px,
            'Qty': short1_qty,
            'Entry_Spot': entry_spot,
            'Exit_Spot': exit_spot,
            'Leg_PnL_Pts': round(short1_pnl_pts, 2),
            'Leg_PnL_Rs': round(short1_pnl_rs, 2),
            'Exit_Reason': 'Weekly_Expiry_Decay'
        })
        
        # -------------------------------------------------------------
        # LEG 3: Weekly Short Option 2 (SELL 1 Lot = 65 Qty @ 65 lot size)
        # -------------------------------------------------------------
        short2_strike = row['Short2_Strike']
        short2_entry_px = row['Short2_Entry_Px']
        short2_exit_px = row['Short2_Exit_Px']
        short2_qty = 1 * lot_size
        short2_pnl_pts = (short2_entry_px - short2_exit_px) * 1
        short2_pnl_rs = (short2_entry_px - short2_exit_px) * short2_qty
        
        bifurcated_rows.append({
            'Cycle_ID': cycle_num,
            'Leg_Role': 'WEEKLY_SHORT_DECAY_2',
            'Entry_Time': entry_time,
            'Exit_Time': exit_time,
            'Type': opt_type,
            'Is_Short': True,
            'Trade_Type': 'SELL',
            'Option_Symbol': f"NIFTY {opt_type} {short2_strike}",
            'Strike': short2_strike,
            'Strategy': 'Strategy_20',
            'Entry_Price': short2_entry_px,
            'Exit_Price': short2_exit_px,
            'Qty': short2_qty,
            'Entry_Spot': entry_spot,
            'Exit_Spot': exit_spot,
            'Leg_PnL_Pts': round(short2_pnl_pts, 2),
            'Leg_PnL_Rs': round(short2_pnl_rs, 2),
            'Exit_Reason': 'Weekly_Expiry_Decay'
        })
        
    df_out = pd.DataFrame(bifurcated_rows)
    out_csv = "research_and_development/strategy20_bifurcated_trade_log.csv"
    df_out.to_csv(out_csv, index=False)
    print(f"[SUCCESS] Bifurcated trade log saved to {out_csv} ({len(df_out)} trade leg rows).")

if __name__ == "__main__":
    generate_bifurcated_backtest_csv()
