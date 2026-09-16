"""
Script 5: Sample Expiry Rollover Verification.
Checks theta decay and contract rollover across a sample Thursday -> Friday transition.
"""
import os
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DIR_2021 = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min", "2021-01-01_to_2021-12-31")

def main():
    print("=" * 90)
    print(" 5. SAMPLE THURSDAY -> FRIDAY EXPIRY ROLLOVER CHECK")
    print("=" * 90)

    f_wed = os.path.join(DIR_2021, "NIFTY_2021-01-06_1m.csv")
    f_thu = os.path.join(DIR_2021, "NIFTY_2021-01-07_1m.csv")
    f_fri = os.path.join(DIR_2021, "NIFTY_2021-01-08_1m.csv")

    df_wed = pd.read_csv(f_wed)
    df_thu = pd.read_csv(f_thu)
    df_fri = pd.read_csv(f_fri)

    print("WEDNESDAY 2021-01-06 (Pre-Expiry) ATM CALL Prices (15:25-15:29):")
    print(df_wed[(df_wed['strike_label'] == 'ATM') & (df_wed['option_type'] == 'CALL')].tail(5)[['datetime', 'open', 'close', 'strike_price', 'spot']].to_string(index=False))

    print("\nTHURSDAY 2021-01-07 (Expiry Day) ATM CALL Prices (15:25-15:29 - Decaying to Intrinsic):")
    print(df_thu[(df_thu['strike_label'] == 'ATM') & (df_thu['option_type'] == 'CALL')].tail(5)[['datetime', 'open', 'close', 'strike_price', 'spot']].to_string(index=False))

    print("\nFRIDAY 2021-01-08 (New Expiry Cycle) ATM CALL Prices (09:15-09:19 - New Weekly Contract):")
    print(df_fri[(df_fri['strike_label'] == 'ATM') & (df_fri['option_type'] == 'CALL')].head(5)[['datetime', 'open', 'close', 'strike_price', 'spot']].to_string(index=False))

if __name__ == "__main__":
    main()
