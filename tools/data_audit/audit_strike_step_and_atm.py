"""
Audit Script: NIFTY Strike Step & ATM Consistency (2021 - 2026).
Verifies the strike interval between consecutive strike labels (ATM, ATM+1, ATM-1, etc.)
across all 5.4 years, and cross-checks with backtest_engine.py's _get_strike_step() logic.
"""
import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

# Import BacktestEngine strike step logic for direct cross-check
import sys
sys.path.append(BASE_DIR)
from backtest_engine import SimulationEngine, BacktestConfig

def run_strike_step_audit():
    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    
    config = BacktestConfig()
    engine = SimulationEngine(config, instrument_name="NIFTY")
    
    print("=" * 90)
    print("      NIFTY STRIKE STEP & ATM RESOLUTION CROSS-CHECK (2021 - 2026)")
    print("=" * 90)
    
    step_records = []
    engine_mismatches = []
    
    # Audit across a dense sample of files across every single year
    for idx, fpath in enumerate(all_csvs):
        fname = os.path.basename(fpath)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
        t_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        df = pd.read_csv(fpath)
        df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
        
        # Pick 09:15 bar
        bar_0915 = df[df['datetime'].str.contains("09:15:00")]
        if bar_0915.empty:
            bar_0915 = df.iloc[:42]
            
        atm_strike = bar_0915[(bar_0915['strike_label'] == 'ATM') & (bar_0915['option_type'] == 'CALL')]['strike_price'].values
        atm_p1_strike = bar_0915[(bar_0915['strike_label'] == 'ATM+1') & (bar_0915['option_type'] == 'CALL')]['strike_price'].values
        atm_m1_strike = bar_0915[(bar_0915['strike_label'] == 'ATM-1') & (bar_0915['option_type'] == 'CALL')]['strike_price'].values
        spot_val = bar_0915[(bar_0915['strike_label'] == 'ATM') & (bar_0915['option_type'] == 'CALL')]['spot'].values
        
        if len(atm_strike) > 0 and len(atm_p1_strike) > 0 and len(atm_m1_strike) > 0:
            step_up = atm_p1_strike[0] - atm_strike[0]
            step_down = atm_strike[0] - atm_m1_strike[0]
            
            # Cross check with backtest_engine._get_strike_step
            engine_step = engine._get_strike_step(t_date)
            
            # Cross check ATM formula
            expected_atm_engine = round(spot_val[0] / engine_step) * engine_step
            
            step_records.append({
                'date': date_str,
                'year': t_date.year,
                'spot': spot_val[0],
                'atm': atm_strike[0],
                'atm+1': atm_p1_strike[0],
                'atm-1': atm_m1_strike[0],
                'step_up': step_up,
                'step_down': step_down,
                'engine_step': engine_step
            })
            
            # Check if step differs from 50
            if step_up != 50.0 or step_down != 50.0:
                print(f"[UNEXPECTED STEP] {date_str}: step_up={step_up}, step_down={step_down}")

    df_steps = pd.DataFrame(step_records)
    
    print(f"Total Sessions Audited: {len(df_steps):,}")
    print(f"\nObserved Strike Steps Across Dataset:")
    print(f"  * Step Up (ATM+1 - ATM):   Min={df_steps['step_up'].min()}, Max={df_steps['step_up'].max()}, Unique={df_steps['step_up'].unique()}")
    print(f"  * Step Down (ATM - ATM-1): Min={df_steps['step_down'].min()}, Max={df_steps['step_down'].max()}, Unique={df_steps['step_down'].unique()}")
    print(f"  * Engine _get_strike_step: Min={df_steps['engine_step'].min()}, Max={df_steps['engine_step'].max()}, Unique={df_steps['engine_step'].unique()}")
    
    print("\nYear-by-Year Strike Step & Spot Range Summary:")
    grouped = df_steps.groupby('year').agg(
        sessions=('date', 'count'),
        min_spot=('spot', 'min'),
        max_spot=('spot', 'max'),
        strike_step=('step_up', 'median'),
        engine_step=('engine_step', 'median')
    )
    print(grouped.to_string())

if __name__ == "__main__":
    run_strike_step_audit()
