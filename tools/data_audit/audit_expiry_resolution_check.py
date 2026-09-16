"""
Audit Script: Spot-check 5 Dates for _get_actual_expiry_date() Alignment.
Verifies that engine's expiry calculation matches the offline dataset's contract expiry.
"""
import os
import sys
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)
from backtest_engine import SimulationEngine, BacktestConfig

OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def main():
    print("=" * 95)
    print(" 5. SPOT-CHECK: _get_actual_expiry_date() vs OFFLINE CONTRACT IMPLIED EXPIRY")
    print("=" * 95)

    config = BacktestConfig()
    engine = SimulationEngine(config, instrument_name="NIFTY")

    test_dates = [
        "2021-04-15", # Thursday standard expiry
        "2022-08-18", # Thursday standard expiry
        "2023-01-25", # Wednesday holiday-adjusted expiry (Jan 26 Republic Day)
        "2024-03-07", # Thursday standard expiry
        "2025-10-09", # Thursday standard expiry
    ]

    for d_str in test_dates:
        t_date = datetime.strptime(d_str, "%Y-%m-%d").date()
        engine_expiry = engine._get_actual_expiry_date(t_date, expiry_index=0)
        
        # Locate offline file
        pattern = os.path.join(OPT_HIST_DIR, "*", f"NIFTY_{d_str}_1m.csv")
        import glob
        matches = glob.glob(pattern)
        
        if matches:
            df = pd.read_csv(matches[0])
            df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
            
            # Check decay at 15:29 on expiry day vs regular day
            atm_1529 = df[(df['strike_label'] == 'ATM') & (df['option_type'] == 'CALL')].tail(1)
            spot_1529 = atm_1529['spot'].iloc[0]
            strike_1529 = atm_1529['strike_price'].iloc[0]
            close_1529 = atm_1529['close'].iloc[0]
            extrinsic_1529 = close_1529 - max(0.0, spot_1529 - strike_1529)
            
            is_expiry_day = (d_str == engine_expiry)
            decayed_to_intrinsic = (extrinsic_1529 < 20.0) if is_expiry_day else (extrinsic_1529 >= 20.0)
            
            print(f"\nDate: {d_str} ({t_date.strftime('%A')})")
            print(f"  * Engine _get_actual_expiry_date: {engine_expiry}")
            print(f"  * Is Expiry Day:                   {is_expiry_day}")
            print(f"  * 15:29 Spot: {spot_1529:.1f} | Strike: {strike_1529} | Close: {close_1529:.2f} | Extrinsic: {extrinsic_1529:.2f} pts")
            print(f"  * Terminal Behavior Consistent:    {decayed_to_intrinsic}")

if __name__ == "__main__":
    main()
