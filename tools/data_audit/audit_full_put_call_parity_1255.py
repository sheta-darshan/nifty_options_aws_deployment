"""
Comprehensive Audit Script: Put-Call Parity across ALL 1,255 Trading Days.
Calculates Synthetic Future Basis: Spread = (C_atm - P_atm + K_atm) - Spot
for all 1,255 daily CSV files.
"""
import os
import glob
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def run_full_parity_audit():
    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    print(f"Auditing Put-Call Parity across ALL {len(all_csvs):,} trading days...")

    results = []

    for fpath in all_csvs:
        fname = os.path.basename(fpath)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
        try:
            df = pd.read_csv(fpath)
            df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
            
            atm_df = df[df['strike_label'] == 'ATM']
            if atm_df.empty:
                results.append({'date': date_str, 'file': fname, 'status': 'FAIL_NO_ATM', 'mean_spread': np.nan, 'std_spread': np.nan, 'bars': 0})
                continue
                
            piv = atm_df.pivot(index='datetime', columns='option_type', values=['close', 'strike_price', 'spot'])
            piv.dropna(inplace=True)
            
            if piv.empty:
                results.append({'date': date_str, 'file': fname, 'status': 'FAIL_EMPTY_PIVOT', 'mean_spread': np.nan, 'std_spread': np.nan, 'bars': 0})
                continue
                
            call_close = piv[('close', 'CALL')]
            put_close = piv[('close', 'PUT')]
            strike = piv[('strike_price', 'CALL')]
            spot = piv[('spot', 'CALL')]
            
            synth_fut = call_close - put_close + strike
            spread = synth_fut - spot # Synthetic future basis vs spot
            
            mean_s = spread.mean()
            std_s = spread.std()
            min_s = spread.min()
            max_s = spread.max()
            bars = len(spread)
            
            # Pass/Fail Criteria:
            # - Mean spread must be within [-50.0, +80.0] points (realistic range for weekly options at 14k-25k index)
            # - Intraday std dev of spread <= 25.0 points
            # - Minimum bars >= 100 (half day / full session)
            passed = (-50.0 <= mean_s <= 80.0) and (std_s <= 25.0) and (bars >= 100)
            
            results.append({
                'date': date_str,
                'file': fname,
                'status': 'PASS' if passed else 'FAIL',
                'mean_spread': mean_s,
                'std_spread': std_s,
                'min_spread': min_s,
                'max_spread': max_s,
                'bars': bars,
                'mean_spot': spot.mean()
            })
        except Exception as e:
            results.append({'date': date_str, 'file': fname, 'status': f'ERROR_{e}', 'mean_spread': np.nan, 'std_spread': np.nan, 'bars': 0})

    df_res = pd.DataFrame(results)
    
    total = len(df_res)
    passed_count = (df_res['status'] == 'PASS').sum()
    failed_count = total - passed_count
    
    print("\n" + "=" * 90)
    print("                PUT-CALL PARITY FULL CENSUS RESULTS (1,255 SESSIONS)")
    print("=" * 90)
    print(f"Total Sessions Evaluated:  {total:,}")
    print(f"Passed Sessions:           {passed_count:,} ({passed_count/total*100:.2f}%)")
    print(f"Failed Sessions:           {failed_count:,} ({failed_count/total*100:.2f}%)")
    print(f"Pass/Fail Criteria:        -50.0 <= Mean Spread <= +80.0 pts AND StdDev <= 25.0 pts")
    
    print(f"\nOverall Spread Statistics across all 1,255 sessions:")
    print(f"  * Grand Mean Spread:       {df_res['mean_spread'].mean():.2f} pts")
    print(f"  * Grand Median Spread:     {df_res['mean_spread'].median():.2f} pts")
    print(f"  * 5th Percentile Spread:   {df_res['mean_spread'].quantile(0.05):.2f} pts")
    print(f"  * 95th Percentile Spread:  {df_res['mean_spread'].quantile(0.95):.2f} pts")
    print(f"  * Mean Intraday Std Dev:   {df_res['std_spread'].mean():.2f} pts")
    
    # Worst 10 offending dates by absolute spread deviation from grand median
    df_res['abs_dev'] = (df_res['mean_spread'] - df_res['mean_spread'].median()).abs()
    worst_10 = df_res.sort_values(by='abs_dev', ascending=False).head(10)
    
    print("\nTop 10 Worst Outlier / Offending Sessions (sorted by absolute deviation from median):")
    print(worst_10[['date', 'status', 'mean_spread', 'std_spread', 'min_spread', 'max_spread', 'mean_spot', 'bars']].to_string(index=False))
    
    return df_res

if __name__ == "__main__":
    run_full_parity_audit()
