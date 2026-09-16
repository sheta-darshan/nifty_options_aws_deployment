"""
Script 2: Inspection of Large Files & Duplicate Blocks.
Identifies files with size > 2MB, compares row counts against expected 15,750 rows
(375 bars * 21 strikes * 2 types), and checks row-level duplicate structure.
"""
import os
import glob
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def main():
    print("=" * 90)
    print(" 2. INSPECTION OF LARGE FILES & CONCATENATED BLOCKS")
    print("=" * 90)

    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    large_files = [f for f in all_csvs if os.path.getsize(f) > 2.0 * 1024 * 1024]
    print(f"Total Large Files (> 2 MB): {len(large_files)}")

    for idx, fpath in enumerate(large_files[:5]):
        fname = os.path.basename(fpath)
        df = pd.read_csv(fpath)
        dups = df.duplicated(subset=['datetime', 'strike_label', 'option_type']).sum()
        print(f"  [{idx+1}] {fname:<30s} Rows: {len(df):>6d} | Duplicates: {dups:>6d} | Deduped: {len(df)-dups:>6d}")

    # Verify if deduplication yields exact standard 15,750 (or session bar count * 42)
    all_exact_match = True
    for fpath in large_files:
        df = pd.read_csv(fpath)
        df_dedup = df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'])
        num_bars = df_dedup['datetime'].nunique()
        expected_rows = num_bars * 42 # 21 strikes * 2 (CALL, PUT)
        if len(df_dedup) != expected_rows:
            all_exact_match = False
            print(f"  [ANOMALY] {os.path.basename(fpath)} deduped rows {len(df_dedup)} != expected {expected_rows}")

    print(f"\nDeduplication Exactness Check: {'100% PERFECT' if all_exact_match else 'ANOMALIES DETECTED'}")

if __name__ == "__main__":
    main()
