"""
Script 3: Deep Scan for Anomalies across All 1,255 Daily Files.
Scans for duplicate rows, zero prices, spot price parity vs nifty_spot.csv,
and ATM strike calculations across the entire 5.4-year dataset.
"""
import os
import glob
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")
SPOT_FILE = os.path.join(BASE_DIR, "backtest_data", "nifty_spot.csv")

def main():
    print("=" * 90)
    print(" 3. DEEP ANOMALY SCAN ACROSS ALL 1,255 FILES")
    print("=" * 90)

    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    print(f"Scanning all {len(all_csvs):,} files...")

    # Load spot data
    df_spot = pd.read_csv(SPOT_FILE)
    col = 'timestamp' if 'timestamp' in df_spot.columns else df_spot.columns[0]
    df_spot['dt'] = pd.to_datetime(df_spot[col])
    df_spot.set_index('dt', inplace=True)
    df_spot_close = df_spot['close']

    duplicate_files = []
    spot_discrepancies = []
    strike_mismatches = []
    zero_prices = []
    total_rows = 0

    for fpath in all_csvs:
        fname = os.path.basename(fpath)
        df = pd.read_csv(fpath)
        total_rows += len(df)

        if df.duplicated(subset=['datetime', 'strike_label', 'option_type']).any():
            duplicate_files.append((fname, len(df)))

        if (df['close'] <= 0).any() or (df['open'] <= 0).any() or (df['high'] <= 0).any() or (df['low'] <= 0).any():
            zero_prices.append(fname)

        # Check spot parity on sample bars
        atm_sample = df[df['strike_label'] == 'ATM'].iloc[::30]
        for _, row in atm_sample.iterrows():
            ts = pd.to_datetime(row['datetime'])
            if ts in df_spot_close.index:
                actual_spot = df_spot_close.loc[ts]
                file_spot = row['spot']
                if abs(actual_spot - file_spot) > 10.0:
                    spot_discrepancies.append((fname, str(ts), file_spot, actual_spot, abs(actual_spot - file_spot)))
                    break

        # Check ATM strike = round(spot / 50) * 50
        atm_rows = df[df['strike_label'] == 'ATM']
        expected_atm = np.round(atm_rows['spot'] / 50.0) * 50.0
        mismatch = (atm_rows['strike_price'] != expected_atm).sum()
        if mismatch > 0:
            strike_mismatches.append((fname, mismatch, len(atm_rows)))

    print(f"Total Files Scanned:          {len(all_csvs):,}")
    print(f"Total Rows Scanned:          {total_rows:,}")
    print(f"Files with Duplicates:       {len(duplicate_files)}")
    print(f"Files with Zero/Neg Prices:  {len(zero_prices)}")
    print(f"Spot Parity Discrepancies (>10 pts): {len(spot_discrepancies)}")
    print(f"Files with Tie-break ATM Diff:       {len(strike_mismatches)}")

if __name__ == "__main__":
    main()
