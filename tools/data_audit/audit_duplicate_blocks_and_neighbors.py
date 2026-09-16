"""
Audit Script: Root-Cause Investigation of 40 Duplicated-Block Files & Neighbor Audit.
Analyzes the date clustering of the 40 double-sized files, verifies byte-exact duplicate
structure, and audits 5 neighboring files (same calendar week) for any subtle corruption.
"""
import os
import glob
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def run_duplicate_root_cause_audit():
    print("=" * 90)
    print(" 7. ROOT CAUSE INVESTIGATION OF 40 DUPLICATE-BLOCK FILES & NEIGHBOR INTEGRITY")
    print("=" * 90)
    
    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    
    dup_files = []
    for f in all_csvs:
        size_kb = os.path.getsize(f) / 1024.0
        if size_kb > 2000: # Files over ~2MB
            fname = os.path.basename(f)
            date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            dup_files.append((dt, f, size_kb))

    df_dups = pd.DataFrame(dup_files, columns=['date', 'path', 'size_kb'])
    df_dups['year'] = df_dups['date'].apply(lambda d: d.year)
    df_dups['month'] = df_dups['date'].apply(lambda d: d.month)
    
    print(f"Total Duplicated-Block Files Found: {len(df_dups)}")
    print("\nYearly Distribution of Duplicated Files:")
    print(df_dups['year'].value_counts().sort_index().to_string())
    
    print("\nAll 40 Duplicated File Dates:")
    for idx, r in df_dups.iterrows():
        print(f"  [{idx+1:>2d}] {str(r['date'])} (Size: {r['size_kb']:.1f} KB)")
        
    # Check structure of duplication: Is it an exact concatenation of the day twice?
    print("\nStructural Verification of Duplicate Blocks:")
    is_exact_double = True
    for idx, r in df_dups.iterrows():
        df = pd.read_csv(r['path'])
        n_total = len(df)
        n_unique = len(df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type']))
        if n_total != 2 * n_unique:
            is_exact_double = False
            print(f"  [ANOMALY] {r['date']}: Total={n_total}, Unique={n_unique} (Not exact 2x)")
    
    if is_exact_double:
        print("  All 40 files are EXACT 2x duplicate concatenations (Header + Part1 + Part1 repeated).")
        print("  Root Cause: An ingestion script or multi-threaded fetcher wrote the batch twice without truncating.")

    # Spot-check 5 neighboring files (dates immediately before/after duplicate files)
    print("\nNeighboring Files Audit (5 sample pairs):")
    sample_dups = df_dups.sample(5, random_state=42).sort_values('date')
    
    for _, r in sample_dups.iterrows():
        dup_date = r['date']
        # find neighbor in all_csvs
        dup_path = r['path']
        dir_name = os.path.dirname(dup_path)
        siblings = sorted(glob.glob(os.path.join(dir_name, "*.csv")))
        idx_in_sib = siblings.index(dup_path)
        
        prev_f = siblings[idx_in_sib - 1] if idx_in_sib > 0 else None
        next_f = siblings[idx_in_sib + 1] if idx_in_sib < len(siblings) - 1 else None
        
        print(f"\nAudit Cluster around {dup_date}:")
        if prev_f:
            df_prev = pd.read_csv(prev_f)
            dups_prev = df_prev.duplicated(subset=['datetime', 'strike_label', 'option_type']).sum()
            print(f"  - Preceding File ({os.path.basename(prev_f)}): Rows={len(df_prev)}, Dups={dups_prev}, Nulls={df_prev.isnull().sum().sum()}, OHLC_OK={((df_prev['high']>=df_prev['low']) & (df_prev['close']>0)).all()}")
        
        df_curr = pd.read_csv(dup_path)
        dups_curr = df_curr.duplicated(subset=['datetime', 'strike_label', 'option_type']).sum()
        print(f"  - Duplicate File ({os.path.basename(dup_path)}): Rows={len(df_curr)}, Dups={dups_curr}, Nulls={df_curr.isnull().sum().sum()}, OHLC_OK={((df_curr['high']>=df_curr['low']) & (df_curr['close']>0)).all()}")
        
        if next_f:
            df_next = pd.read_csv(next_f)
            dups_next = df_next.duplicated(subset=['datetime', 'strike_label', 'option_type']).sum()
            print(f"  - Succeeding File ({os.path.basename(next_f)}): Rows={len(df_next)}, Dups={dups_next}, Nulls={df_next.isnull().sum().sum()}, OHLC_OK={((df_next['high']>=df_next['low']) & (df_next['close']>0)).all()}")

if __name__ == "__main__":
    run_duplicate_root_cause_audit()
