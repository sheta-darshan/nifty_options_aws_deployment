"""
Test filtering by absolute strike_price (e.g. strike_price == target_strike)
across a trading session to verify complete, uninterrupted contract-accurate bars.
"""
import os
import glob
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def test_absolute_strike_filtering():
    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    sample_indices = np.linspace(0, len(all_csvs)-1, 15, dtype=int)
    sample_files = [all_csvs[i] for i in sample_indices]

    print("=" * 95)
    print(" TESTING ABSOLUTE STRIKE_PRICE FILTERING ON PHYSICAL CONTRACTS")
    print("=" * 95)

    for fpath in sample_files:
        fname = os.path.basename(fpath)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
        df = pd.read_csv(fpath)
        df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
        
        # Pick opening ATM strike at 09:15
        bar_0915 = df[(df['datetime'].str.contains("09:15:00")) & (df['strike_label'] == 'ATM') & (df['option_type'] == 'CALL')]
        if bar_0915.empty:
            continue
            
        atm_strike = int(bar_0915['strike_price'].iloc[0])
        spot_0915 = bar_0915['spot'].iloc[0]
        
        # Filter strictly by absolute strike_price
        contract_df = df[(df['strike_price'] == atm_strike) & (df['option_type'] == 'CALL')].copy()
        
        # Check continuity
        total_session_bars = df['datetime'].nunique()
        contract_bars = len(contract_df)
        is_continuous = (contract_bars == total_session_bars)
        
        # Check price smoothness (no artificial leaps from switching contracts)
        contract_df['price_change'] = contract_df['close'].diff()
        max_jump = contract_df['price_change'].abs().max()
        
        print(f"Date: {date_str} | Spot @ 09:15: {spot_0915:.1f} | Physical Strike: {atm_strike} CE")
        print(f"  -> Contract Bars: {contract_bars}/{total_session_bars} | Continuous: {is_continuous} | Max 1-min change: {max_jump:.2f} pts")

if __name__ == "__main__":
    test_absolute_strike_filtering()
