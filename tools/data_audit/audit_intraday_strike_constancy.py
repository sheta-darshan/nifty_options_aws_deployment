"""
Audit Script: Check if strike_price is CONSTANT per strike_label across all intraday bars.
Tests 25 sample dates spread across 2021-2026.
"""
import os
import glob
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def main():
    print("=" * 95)
    print(" 1. CRITICAL AUDIT: INTRADAY STRIKE_PRICE CONSTANCY PER STRIKE_LABEL")
    print("=" * 95)

    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    sample_indices = np.linspace(0, len(all_csvs)-1, 25, dtype=int)
    sample_files = [all_csvs[i] for i in sample_indices]

    results = []
    any_dynamic = False

    for fpath in sample_files:
        fname = os.path.basename(fpath)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
        df = pd.read_csv(fpath)
        df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
        
        call_df = df[df['option_type'] == 'CALL']
        
        label_stats = {}
        max_unique_strikes = 0
        dynamic_labels = []
        
        for lbl in call_df['strike_label'].unique():
            lbl_data = call_df[call_df['strike_label'] == lbl]
            n_unique = lbl_data['strike_price'].nunique()
            unique_strikes = lbl_data['strike_price'].unique()
            label_stats[lbl] = (n_unique, unique_strikes)
            if n_unique > max_unique_strikes:
                max_unique_strikes = n_unique
            if n_unique > 1:
                dynamic_labels.append((lbl, n_unique, list(unique_strikes)))
                any_dynamic = True
                
        results.append({
            'date': date_str,
            'file': fname,
            'max_unique_strikes_per_label': max_unique_strikes,
            'is_dynamic': max_unique_strikes > 1,
            'dynamic_labels_count': len(dynamic_labels),
            'sample_dynamic': dynamic_labels[:3]
        })

    df_res = pd.DataFrame(results)
    print(f"Audited {len(sample_files)} sample dates across 2021-2026:")
    print(df_res[['date', 'max_unique_strikes_per_label', 'is_dynamic', 'dynamic_labels_count']].to_string(index=False))

    print("\n" + "=" * 95)
    if any_dynamic:
        print("🚨 CRITICAL FINDING: strike_label IS DYNAMICALLY RECOMPUTED INTRADAY!")
        print("   On intraday spot movement, 'ATM' changes strike_price (e.g. 14550 -> 14600 -> 14650).")
        print("   Filtering by `strike_label == 'ATM'` across the whole day would INCORRECTLY splice contracts!")
        print("   SOLUTION REQUIRED: Filter strictly by `strike_price == strike` across all rows in the file!")
    else:
        print("✅ STRIKE_LABEL IS STATIC: strike_price is 100% constant per label per day.")

    print("\nSample Dynamic Slicing Example from 1 Date:")
    sample_dyn_date = df_res[df_res['is_dynamic']].iloc[0]
    print(f"Date: {sample_dyn_date['date']}")
    for d in sample_dyn_date['sample_dynamic']:
        print(f"  - Label '{d[0]}': {d[1]} distinct strike prices throughout the day -> {d[2]}")

if __name__ == "__main__":
    main()
