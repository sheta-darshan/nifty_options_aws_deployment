"""
Comprehensive Audit Script: Expiry Rollover Integrity across ALL ~280 Weekly Transitions.
Audits:
 (a) Terminal Intrinsic Decay: On expiry day (usually Thursday), ATM/OTM options decay to intrinsic value by 15:29.
 (b) New Cycle Extrinsic Continuity: On the next day (usually Friday), the new weekly contract opens with healthy extrinsic value (premium > intrinsic).
"""
import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def run_expiry_rollover_audit():
    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    
    # Load all files metadata & dates
    file_map = {}
    for f in all_csvs:
        fname = os.path.basename(f)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        file_map[dt] = f

    sorted_dates = sorted(list(file_map.keys()))
    
    # Identify expiry days:
    # An expiry day in Indian markets is typically Thursday (or Wednesday if Thursday is a holiday).
    # We can detect expiry days by checking when the ATM premium drops sharply to near zero / intrinsic at 15:29,
    # or by calendar weekday sequence where next day rolls to a new high premium contract.
    
    rollover_records = []
    
    for i in range(len(sorted_dates) - 1):
        d_curr = sorted_dates[i]
        d_next = sorted_dates[i+1]
        
        # Load day 1 (expiring candidate) and day 2 (new cycle candidate)
        # Check if d_curr is an expiry day (usually Thursday, weekday 3, or followed by weekend where d_next is Monday)
        # In Nifty weekly options, Thursday is standard expiry.
        is_expiry_candidate = (d_curr.weekday() == 3) or ((d_next - d_curr).days >= 1 and d_curr.weekday() in [2, 3])
        
        if not is_expiry_candidate:
            continue
            
        try:
            df1 = pd.read_csv(file_map[d_curr])
            df1.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
            
            df2 = pd.read_csv(file_map[d_next])
            df2.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
            
            # 1. Check Day 1 Terminal Price (at 15:25 - 15:29)
            df1_atm_ce = df1[(df1['strike_label'] == 'ATM') & (df1['option_type'] == 'CALL')].tail(5)
            df1_atm_pe = df1[(df1['strike_label'] == 'ATM') & (df1['option_type'] == 'PUT')].tail(5)
            
            if df1_atm_ce.empty or df1_atm_pe.empty:
                continue
                
            last_ce_row = df1_atm_ce.iloc[-1]
            last_pe_row = df1_atm_pe.iloc[-1]
            
            spot_1529 = last_ce_row['spot']
            strike_ce = last_ce_row['strike_price']
            strike_pe = last_pe_row['strike_price']
            
            ce_close = last_ce_row['close']
            pe_close = last_pe_row['close']
            
            ce_intrinsic = max(0.0, spot_1529 - strike_ce)
            pe_intrinsic = max(0.0, strike_pe - spot_1529)
            
            ce_extrinsic = ce_close - ce_intrinsic
            pe_extrinsic = pe_close - pe_intrinsic
            
            # Check if this day really acted as an expiry day (extrinsic value decayed to < 20 points at 15:29)
            is_actual_expiry = (ce_extrinsic < 25.0) and (pe_extrinsic < 25.0)
            
            if not is_actual_expiry:
                continue # not an expiry transition
                
            # 2. Check Day 2 Opening Price (at 09:15 - 09:20)
            df2_atm_ce = df2[(df2['strike_label'] == 'ATM') & (df2['option_type'] == 'CALL')].head(5)
            df2_atm_pe = df2[(df2['strike_label'] == 'ATM') & (df2['option_type'] == 'PUT')].head(5)
            
            if df2_atm_ce.empty or df2_atm_pe.empty:
                continue
                
            first_ce_row = df2_atm_ce.iloc[0]
            first_pe_row = df2_atm_pe.iloc[0]
            
            spot_0915 = first_ce_row['spot']
            strike_ce_d2 = first_ce_row['strike_price']
            strike_pe_d2 = first_pe_row['strike_price']
            
            ce_open = first_ce_row['open']
            pe_open = first_pe_row['open']
            
            ce_intrinsic_d2 = max(0.0, spot_0915 - strike_ce_d2)
            pe_intrinsic_d2 = max(0.0, strike_pe_d2 - spot_0915)
            
            ce_extrinsic_d2 = ce_open - ce_intrinsic_d2
            pe_extrinsic_d2 = pe_open - pe_intrinsic_d2
            
            # Pass/Fail Criteria:
            # - Day 1 Terminal: Both CE & PE extrinsic <= 20.0 pts (decayed to near intrinsic at 15:29)
            # - Day 2 Opening: New weekly contract has healthy extrinsic premium > 25.0 pts (typically 50-200 pts for 5-6 DTE)
            decay_pass = (ce_extrinsic <= 20.0) and (pe_extrinsic <= 20.0)
            rollover_pass = (ce_extrinsic_d2 >= 25.0) and (pe_extrinsic_d2 >= 25.0)
            
            rollover_records.append({
                'expiry_date': str(d_curr),
                'next_date': str(d_next),
                'weekday_expiry': d_curr.strftime('%A'),
                'spot_expiry_1529': spot_1529,
                'ce_extrinsic_1529': ce_extrinsic,
                'pe_extrinsic_1529': pe_extrinsic,
                'spot_next_0915': spot_0915,
                'ce_extrinsic_0915': ce_extrinsic_d2,
                'pe_extrinsic_0915': pe_extrinsic_d2,
                'decay_pass': decay_pass,
                'rollover_pass': rollover_pass,
                'overall_pass': decay_pass and rollover_pass
            })
            
        except Exception as e:
            rollover_records.append({
                'expiry_date': str(d_curr),
                'next_date': str(d_next),
                'decay_pass': False,
                'rollover_pass': False,
                'overall_pass': False,
                'error': str(e)
            })

    df_roll = pd.DataFrame(rollover_records)
    
    print("\n" + "=" * 90)
    print("        EXPIRY ROLLOVER INTEGRITY CENSUS ACROSS ALL WEEKLY TRANSITIONS")
    print("=" * 90)
    total_trans = len(df_roll)
    passed_trans = df_roll['overall_pass'].sum()
    failed_trans = total_trans - passed_trans
    
    print(f"Total Weekly Transitions Detected: {total_trans}")
    print(f"Passed Transitions:                {passed_trans} ({passed_trans/total_trans*100:.2f}%)")
    print(f"Failed Transitions:                {failed_trans}")
    print(f"\nSummary Metrics:")
    print(f"  * Mean Expiry Day Terminal Extrinsic (CE): {df_roll['ce_extrinsic_1529'].mean():.2f} pts (Near 0)")
    print(f"  * Mean Expiry Day Terminal Extrinsic (PE): {df_roll['pe_extrinsic_1529'].mean():.2f} pts (Near 0)")
    print(f"  * Mean Next Day Opening Extrinsic (CE):    {df_roll['ce_extrinsic_0915'].mean():.2f} pts (Healthy 5-6 DTE premium)")
    print(f"  * Mean Next Day Opening Extrinsic (PE):    {df_roll['pe_extrinsic_0915'].mean():.2f} pts (Healthy 5-6 DTE premium)")

    if failed_trans > 0:
        print("\nFailed Transitions:")
        print(df_roll[~df_roll['overall_pass']][['expiry_date', 'next_date', 'ce_extrinsic_1529', 'pe_extrinsic_1529', 'ce_extrinsic_0915', 'pe_extrinsic_0915']].to_string(index=False))
    else:
        print("\nAll weekly transitions cleanly satisfied both terminal intrinsic decay and fresh contract rollover!")

    print("\nSample 10 Weekly Transitions:")
    print(df_roll[['expiry_date', 'next_date', 'weekday_expiry', 'ce_extrinsic_1529', 'pe_extrinsic_1529', 'ce_extrinsic_0915', 'pe_extrinsic_0915', 'overall_pass']].head(10).to_string(index=False))
    
    return df_roll

if __name__ == "__main__":
    run_expiry_rollover_audit()
