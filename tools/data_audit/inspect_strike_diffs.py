"""
Script 4: Strike Difference & Midpoint Tie-Break Investigation.
Investigates the exact mathematical cause of ATM strike selection on boundary points
(e.g., spot at 14175.0 exactly equidistant between 14150 and 14200).
"""
import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAMPLE_FILE = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min", "2021-01-01_to_2021-12-31", "NIFTY_2021-01-05_1m.csv")

def main():
    print("=" * 90)
    print(" 4. ATM STRIKE MIDPOINT TIE-BREAK INVESTIGATION")
    print("=" * 90)

    df = pd.read_csv(SAMPLE_FILE)
    atm_rows = df[df['strike_label'] == 'ATM']
    expected_atm = np.round(atm_rows['spot'] / 50.0) * 50.0
    diffs = atm_rows[atm_rows['strike_price'] != expected_atm]

    print(f"Sample File: {os.path.basename(SAMPLE_FILE)}")
    print(f"Total ATM Rows in Session: {len(atm_rows)}")
    print(f"Total Mismatches vs round(): {len(diffs)}")
    print("\nDetailed Mismatch Rows:")
    for _, r in diffs.iterrows():
        print(f"  Datetime: {r['datetime']} | Type: {r['option_type']:<4s} | Strike in File: {r['strike_price']} | Spot: {r['spot']} | np.round(): {round(r['spot']/50)*50}")

    print("\nExplanation:")
    print("  When Spot = 14175.0, (14175 / 50) = 283.5.")
    print("  Python IEEE 754 'round to nearest even' rounds 283.5 to 284 (Strike 14200).")
    print("  Standard floor/integer rounding rounds 283.5 to 283 (Strike 14150).")
    print("  Both strikes are exactly 25.0 points from spot (perfectly valid ATM representation).")

if __name__ == "__main__":
    main()
