"""
Script 6: Sample Put-Call Parity Test (50-Session Sample).
Calculates Synthetic Future Basis (C - P + K - Spot) across a distributed sample of 50 sessions.
"""
import os
import glob
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def main():
    print("=" * 90)
    print(" 6. SAMPLE PUT-CALL PARITY AUDIT (50-SESSION SAMPLE)")
    print("=" * 90)

    all_csvs = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    sample_indices = np.linspace(0, len(all_csvs)-1, 50, dtype=int)
    sample_files = [all_csvs[i] for i in sample_indices]

    parity_errors = []

    for fpath in sample_files:
        df = pd.read_csv(fpath)
        df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
        
        atm_df = df[df['strike_label'] == 'ATM']
        piv = atm_df.pivot(index='datetime', columns='option_type', values=['close', 'strike_price', 'spot'])
        piv.dropna(inplace=True)
        
        call_close = piv[('close', 'CALL')]
        put_close = piv[('close', 'PUT')]
        strike = piv[('strike_price', 'CALL')]
        spot = piv[('spot', 'CALL')]
        
        synth_fut = call_close - put_close + strike
        diff = synth_fut - spot
        mean_diff = diff.mean()
        parity_errors.append((os.path.basename(fpath), mean_diff, diff.std(), len(diff)))

    df_parity = pd.DataFrame(parity_errors, columns=['file', 'mean_diff (SynthFut - Spot)', 'std_diff', 'bars'])
    print(f"Audited 50 sample trading sessions across 2021-2026:")
    print(f"  * Overall Mean (C - P + K - Spot): {df_parity['mean_diff (SynthFut - Spot)'].mean():.2f} pts")
    print(f"  * Mean Std Dev per session:        {df_parity['std_diff'].mean():.2f} pts")
    print("\nSample 10 Sessions Parity Spread:")
    print(df_parity.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
