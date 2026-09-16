"""
==========================================================================================
        INSTITUTIONAL 10-YEAR HISTORICAL DATA MERGE & STITCHING ENGINE
==========================================================================================
Stitches older 10-year 1-minute historical equity data (from G:\\stockdata) into
backtest_data/{symbol}_spot.csv, prepending missing 2015-2021 historical bars while 
preserving 100% of authoritative recent Dhan API data without duplicate timestamps.
==========================================================================================
"""

import os
import sys
import glob
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np

# Project Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCE_DIR = r"G:\stockdata"
DEFAULT_TARGET_DIR = os.path.join(BASE_DIR, "backtest_data")
STANDARD_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def process_stock_file(src_path, target_dir, dry_run=False):
    """
    Processes a single stock file from G:\\stockdata and merges it into backtest_data.
    """
    filename = os.path.basename(src_path)
    symbol = filename.replace("_minute.csv", "").upper()
    target_filename = f"{symbol.lower()}_spot.csv"
    target_path = os.path.join(target_dir, target_filename)

    try:
        # Read source data
        df_src = pd.read_csv(src_path)
        if df_src.empty:
            return {"symbol": symbol, "status": "EMPTY_SOURCE", "prepended_rows": 0, "total_rows": 0}

        # Normalize source columns
        col_map = {}
        for col in df_src.columns:
            c_low = col.lower().strip()
            if c_low in ["date", "timestamp", "datetime", "time"]:
                col_map[col] = "timestamp"
            elif c_low in ["open", "high", "low", "close", "volume"]:
                col_map[col] = c_low
        df_src.rename(columns=col_map, inplace=True)

        # Check required columns
        for col in STANDARD_COLUMNS:
            if col not in df_src.columns:
                return {"symbol": symbol, "status": f"MISSING_COL_{col.upper()}", "prepended_rows": 0, "total_rows": 0}

        df_src = df_src[STANDARD_COLUMNS].copy()
        df_src["timestamp"] = pd.to_datetime(df_src["timestamp"], errors="coerce")
        df_src.dropna(subset=["timestamp", "open", "high", "low", "close"], inplace=True)
        df_src.sort_values(by="timestamp", inplace=True)

        if os.path.exists(target_path):
            # Read existing target
            df_tgt = pd.read_csv(target_path)
            col_tgt_map = {}
            for col in df_tgt.columns:
                c_low = col.lower().strip()
                if c_low in ["date", "timestamp", "datetime", "time"]:
                    col_tgt_map[col] = "timestamp"
                elif c_low in ["open", "high", "low", "close", "volume"]:
                    col_tgt_map[col] = c_low
            df_tgt.rename(columns=col_tgt_map, inplace=True)

            if "timestamp" not in df_tgt.columns or df_tgt.empty:
                # Replace corrupted target
                df_merged = df_src
                prepended_count = len(df_merged)
            else:
                df_tgt["timestamp"] = pd.to_datetime(df_tgt["timestamp"], errors="coerce")
                df_tgt.dropna(subset=["timestamp"], inplace=True)
                earliest_tgt_ts = df_tgt["timestamp"].min()

                # Slice strictly older rows from source
                df_src_older = df_src[df_src["timestamp"] < earliest_tgt_ts]
                prepended_count = len(df_src_older)

                if prepended_count > 0:
                    # Concat [older source + full target]
                    # Keep existing target columns (which might have indicators) or align to standard
                    extra_cols = [c for c in df_tgt.columns if c not in STANDARD_COLUMNS]
                    if extra_cols:
                        for ec in extra_cols:
                            df_src_older[ec] = np.nan

                    df_merged = pd.concat([df_src_older, df_tgt], ignore_index=True)
                else:
                    return {
                        "symbol": symbol,
                        "status": "ALREADY_COMPLETE",
                        "prepended_rows": 0,
                        "total_rows": len(df_tgt),
                        "start_ts": str(earliest_tgt_ts),
                        "end_ts": str(df_tgt["timestamp"].max())
                    }
        else:
            # New stock creation
            df_merged = df_src
            prepended_count = len(df_merged)

        # Clean, sort, and deduplicate
        df_merged.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
        df_merged.sort_values(by="timestamp", inplace=True)

        # Standard string format for timestamp: YYYY-MM-DD HH:MM:SS
        df_merged["timestamp"] = df_merged["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        start_ts = df_merged["timestamp"].iloc[0]
        end_ts = df_merged["timestamp"].iloc[-1]
        total_rows = len(df_merged)

        if not dry_run:
            df_merged.to_csv(target_path, index=False)

        return {
            "symbol": symbol,
            "status": "MERGED",
            "prepended_rows": prepended_count,
            "total_rows": total_rows,
            "start_ts": str(start_ts),
            "end_ts": str(end_ts)
        }

    except Exception as e:
        return {"symbol": symbol, "status": f"ERROR: {e}", "prepended_rows": 0, "total_rows": 0}


def main():
    parser = argparse.ArgumentParser(description="Institutional 10-Year Historical Data Merge & Stitching Engine")
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR, help="Path to 10-year source CSV directory")
    parser.add_argument("--target-dir", default=DEFAULT_TARGET_DIR, help="Path to backtest_data destination directory")
    parser.add_argument("--symbols", nargs="*", help="Filter to specific symbols (e.g. --symbols RELIANCE INFY TCS)")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel worker threads (default: 8)")
    parser.add_argument("--dry-run", action="store_true", help="Preview merge operations without writing to disk")
    args = parser.parse_args()

    print("=" * 90)
    print("      INSTITUTIONAL 10-YEAR HISTORICAL DATA MERGE & STITCHING ENGINE")
    print("=" * 90)
    print(f"[CONFIG] Source Directory:  {args.source_dir}")
    print(f"[CONFIG] Target Directory:  {args.target_dir}")
    print(f"[CONFIG] Parallel Workers:  {args.workers}")
    print(f"[CONFIG] Dry-Run Mode:      {args.dry_run}")

    if not os.path.exists(args.source_dir):
        print(f"[ERROR] Source directory does not exist: {args.source_dir}")
        sys.exit(1)

    os.makedirs(args.target_dir, exist_ok=True)

    # Find all source files
    all_src_files = glob.glob(os.path.join(args.source_dir, "*_minute.csv"))
    print(f"\n[STEP 1] Found {len(all_src_files)} total stock files in source directory.")

    if args.symbols:
        filtered_syms = set([s.upper() for s in args.symbols])
        all_src_files = [f for f in all_src_files if os.path.basename(f).replace("_minute.csv", "").upper() in filtered_syms]
        print(f"[FILTER] Sliced to {len(all_src_files)} requested symbols: {args.symbols}")

    if not all_src_files:
        print("[ERROR] No matching source files found to process.")
        sys.exit(1)

    start_time = time.time()
    results = []

    print(f"\n[STEP 2] Processing {len(all_src_files)} stocks with {args.workers} concurrent workers...")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {
            executor.submit(process_stock_file, f, args.target_dir, args.dry_run): f
            for f in all_src_files
        }

        completed = 0
        for future in as_completed(future_map):
            completed += 1
            res = future.result()
            results.append(res)
            sym = res["symbol"]
            status = res["status"]
            prepended = res["prepended_rows"]
            total = res["total_rows"]
            
            if status == "MERGED":
                print(f"[{completed}/{len(all_src_files)}] {sym:<12} -> [MERGED] +{prepended:,} older rows | Total: {total:,} rows ({res['start_ts'][:10]} to {res['end_ts'][:10]})")
            elif status == "ALREADY_COMPLETE":
                print(f"[{completed}/{len(all_src_files)}] {sym:<12} -> [UP TO DATE] Total: {total:,} rows ({res.get('start_ts', '')[:10]} to {res.get('end_ts', '')[:10]})")
            else:
                print(f"[{completed}/{len(all_src_files)}] {sym:<12} -> [{status}]")

    elapsed = time.time() - start_time

    # Summary Metrics
    merged_count = sum(1 for r in results if r["status"] == "MERGED")
    complete_count = sum(1 for r in results if r["status"] == "ALREADY_COMPLETE")
    error_count = sum(1 for r in results if "ERROR" in r["status"])
    total_prepended_rows = sum(r["prepended_rows"] for r in results)

    print("\n" + "=" * 90)
    print("                         DATA MERGE SUMMARY REPORT")
    print("=" * 90)
    print(f"Total Source Stocks Processed: {len(results)}")
    print(f"Successfully Merged / Updated: {merged_count}")
    print(f"Already Up-To-Date (Skipped):  {complete_count}")
    print(f"Errors Encountered:            {error_count}")
    print(f"Total Historical Rows Added:   {total_prepended_rows:,} 1-minute bars")
    print(f"Total Execution Time:          {elapsed:.2f}s ({elapsed/60:.2f} mins)")
    print(f"Output Directory:              {args.target_dir}")
    print("=" * 90)


if __name__ == "__main__":
    main()
