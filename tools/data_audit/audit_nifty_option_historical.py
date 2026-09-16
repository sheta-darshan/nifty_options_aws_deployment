"""
Script 1: Full Inventory, Schema, and Basic OHLC Sanity Audit.
Audits all 1,255 daily CSV files for schema uniformity, column types,
nulls, zero prices, and OHLC logical validity.
"""
import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def main():
    print("=" * 90)
    print(" 1. DATASET INVENTORY, SCHEMA & OHLC SANITY AUDIT")
    print("=" * 90)

    subdirs = sorted([
        d for d in os.listdir(OPT_HIST_DIR) 
        if os.path.isdir(os.path.join(OPT_HIST_DIR, d)) and not d.startswith(".") and not d.startswith("__")
    ])

    total_files = 0
    total_bytes = 0
    files_by_year = {}
    all_csv_paths = []

    for sd in subdirs:
        s_path = os.path.join(OPT_HIST_DIR, sd)
        csv_files = sorted(glob.glob(os.path.join(s_path, "*.csv")))
        files_by_year[sd] = len(csv_files)
        total_files += len(csv_files)
        all_csv_paths.extend(csv_files)
        for f in csv_files:
            total_bytes += os.path.getsize(f)

    print(f"Total Files Found: {total_files:,}")
    print(f"Total Disk Space:   {total_bytes / (1024*1024*1024):.2f} GB")
    print("\nYearly Breakdown:")
    for sd, count in files_by_year.items():
        print(f"  - {sd:<30s}: {count:>4d} daily CSV files")

    # Sample audit across files
    schema_set = set()
    null_count = 0
    ohlc_violations = 0
    zero_close_count = 0
    total_rows = 0

    for i, p in enumerate(all_csv_paths):
        df = pd.read_csv(p)
        total_rows += len(df)
        schema_set.add(tuple(df.columns.tolist()))
        null_count += df.isnull().sum().sum()
        
        v = ((df['high'] < df['low']) | 
             (df['high'] < df['open']) | 
             (df['high'] < df['close']) | 
             (df['low'] > df['open']) | 
             (df['low'] > df['close']) | 
             (df['open'] <= 0) | 
             (df['close'] <= 0)).sum()
        ohlc_violations += v
        zero_close_count += (df['close'] <= 0).sum()

    print(f"\nFull 1,255-File Scan Results:")
    print(f"  * Total Rows Scanned:        {total_rows:,}")
    print(f"  * Unique Schemas:            {len(schema_set)}")
    for sc in schema_set:
        print(f"    Columns: {list(sc)}")
    print(f"  * Total Null/NaN Values:     {null_count}")
    print(f"  * OHLC Logic Violations:     {ohlc_violations}")
    print(f"  * Zero or Negative Prices:   {zero_close_count}")

if __name__ == "__main__":
    main()
