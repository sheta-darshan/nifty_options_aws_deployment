import os
import pandas as pd

def generate_manual_verification_sheet():
    input_file = "research_and_development/strategy20_bifurcated_trade_log.csv"
    if not os.path.exists(input_file):
        print(f"[ERROR] {input_file} not found!")
        return

    df = pd.read_csv(input_file)
    
    sheet_rows = []
    
    for idx, row in df.iterrows():
        cycle_id = row['Cycle_ID']
        leg_role = row['Leg_Role']
        entry_time = row['Entry_Time']
        exit_time = row['Exit_Time']
        opt_symbol = row['Option_Symbol']
        strike = row['Strike']
        trade_type = row['Trade_Type']
        qty = row['Qty']
        entry_px = row['Entry_Price']
        exit_px = row['Exit_Price']
        entry_spot = row['Entry_Spot']
        exit_spot = row['Exit_Spot']
        pnl_pts = row['Leg_PnL_Pts']
        pnl_rs = row['Leg_PnL_Rs']
        
        verify_instruction = (
            f"Step 1: Check Nifty Spot on {entry_time} = {entry_spot}. "
            f"Step 2: Check {opt_symbol} price on {entry_time} = {entry_px}. "
            f"Step 3: Check {opt_symbol} price on {exit_time} = {exit_px}. "
            f"Step 4: PnL = ({exit_px} - {entry_px}) * {qty} = ₹{pnl_rs}."
        )
        
        sheet_rows.append({
            'Cycle': cycle_id,
            'Leg': leg_role,
            'Entry_Timestamp': entry_time,
            'Exit_Timestamp': exit_time,
            'Action': trade_type,
            'Contract_Symbol': opt_symbol,
            'Strike': strike,
            'Qty_Traded': qty,
            'Entry_Spot_Price': entry_spot,
            'Exit_Spot_Price': exit_spot,
            'Entry_Contract_Price': entry_px,
            'Exit_Contract_Price': exit_px,
            'Leg_PnL_Points': pnl_pts,
            'Leg_PnL_Rupees': pnl_rs,
            'How_To_Cross_Verify': verify_instruction
        })
        
    df_sheet = pd.DataFrame(sheet_rows)
    out_csv = "research_and_development/strategy20_manual_verification_sheet.csv"
    df_sheet.to_csv(out_csv, index=False)
    print(f"[SUCCESS] Easy manual verification sheet saved to {out_csv} ({len(df_sheet)} rows).")

if __name__ == "__main__":
    generate_manual_verification_sheet()
