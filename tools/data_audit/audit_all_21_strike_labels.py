"""
Audit Script: Comprehensive Verification of ALL 21 Strike Labels (ATM-10 to ATM+10).
Verifies that Strike(ATM+k) - Strike(ATM) == k * 50 across sample sessions for all years.
"""
import os
import glob
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def main():
    print("=" * 95)
    print("     ALL 21 STRIKE LABELS SPACING AUDIT (ATM-10 to ATM+10) ACROSS 2021-2026")
    print("=" * 95)

    subdirs = sorted([d for d in os.listdir(OPT_HIST_DIR) if os.path.isdir(os.path.join(OPT_HIST_DIR, d)) and not d.startswith(".") and not d.startswith("__")])

    sample_sessions = []
    for sd in subdirs:
        csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, sd, "*.csv")))
        if csvs:
            # pick middle file of the year
            sample_sessions.append(csvs[len(csvs)//2])

    expected_offsets = {
        'ATM-10': -10, 'ATM-9': -9, 'ATM-8': -8, 'ATM-7': -7, 'ATM-6': -6,
        'ATM-5': -5,   'ATM-4': -4, 'ATM-3': -3, 'ATM-2': -2, 'ATM-1': -1,
        'ATM': 0,
        'ATM+1': 1,    'ATM+2': 2,  'ATM+3': 3,  'ATM+4': 4,  'ATM+5': 5,
        'ATM+6': 6,    'ATM+7': 7,  'ATM+8': 8,  'ATM+9': 9,  'ATM+10': 10
    }

    all_labels_order = [
        'ATM-10', 'ATM-9', 'ATM-8', 'ATM-7', 'ATM-6', 'ATM-5', 'ATM-4', 'ATM-3', 'ATM-2', 'ATM-1',
        'ATM',
        'ATM+1', 'ATM+2', 'ATM+3', 'ATM+4', 'ATM+5', 'ATM+6', 'ATM+7', 'ATM+8', 'ATM+9', 'ATM+10'
    ]

    for s_path in sample_sessions:
        fname = os.path.basename(s_path)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
        df = pd.read_csv(s_path)
        df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
        
        # Pick 09:15 bar CALL options
        bar = df[(df['datetime'].str.contains("09:15:00")) & (df['option_type'] == 'CALL')]
        if bar.empty:
            bar = df[df['option_type'] == 'CALL'].iloc[:21]
            
        atm_row = bar[bar['strike_label'] == 'ATM']
        if atm_row.empty:
            print(f"[ERROR] No ATM strike in {fname}")
            continue
            
        atm_strike = atm_row['strike_price'].iloc[0]
        spot_val = atm_row['spot'].iloc[0]
        
        print(f"\n--- Session: {date_str} (Spot @ 09:15: {spot_val}, ATM Strike: {atm_strike}) ---")
        
        label_table = []
        deviations = 0
        for lbl in all_labels_order:
            row = bar[bar['strike_label'] == lbl]
            if not row.empty:
                strike_k = row['strike_price'].iloc[0]
                k = expected_offsets[lbl]
                expected_strike = atm_strike + k * 50
                diff = strike_k - expected_strike
                is_ok = (diff == 0)
                if not is_ok:
                    deviations += 1
                label_table.append({
                    'label': lbl,
                    'offset_k': k,
                    'strike': strike_k,
                    'expected': expected_strike,
                    'diff': diff,
                    'status': 'OK' if is_ok else 'FAIL'
                })
            else:
                label_table.append({
                    'label': lbl,
                    'offset_k': expected_offsets[lbl],
                    'strike': 'MISSING',
                    'expected': atm_strike + expected_offsets[lbl] * 50,
                    'diff': 'N/A',
                    'status': 'MISSING'
                })
                deviations += 1
                
        df_lbl = pd.DataFrame(label_table)
        print(df_lbl.to_string(index=False))
        print(f"Result for {date_str}: {'100% PERFECT (0 Deviations)' if deviations == 0 else f'{deviations} DEVIATIONS'}")

if __name__ == "__main__":
    main()
