"""
Phase 2 Extension: Fade (Shorting) and Implied Volatility (IV) Dynamics Study
on Definition 1 Volume Spikes (5x and 10x Trailing 20-SMA) vs Matched Baseline.
"""
import os
import glob
import time
import pandas as pd
import numpy as np
from scipy import stats
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

TARGET_LABELS = ['ATM-3', 'ATM-2', 'ATM-1', 'ATM', 'ATM+1', 'ATM+2', 'ATM+3']

def get_time_of_day_bucket(dt_str):
    time_part = dt_str.split()[1] if " " in dt_str else dt_str
    hh_mm = time_part[:5]
    if hh_mm <= "09:45":
        return "Morning_Open (09:15-09:45)"
    elif hh_mm >= "14:45":
        return "Afternoon_Close (14:45-15:25)"
    else:
        return "Midday (09:46-14:44)"

def main():
    print("=" * 95)
    print(" PHASE 2 EXTENSION: FADE (SHORTING) & IV DYNAMICS ON DEFINITION 1 SPIKES")
    print("=" * 95)

    csv_files = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    print(f"Total Session CSV Files to Scan: {len(csv_files)}")

    def1_5x_events = []
    def1_10x_events = []
    baseline_pool = defaultdict(list)

    total_candles_processed = 0
    t0 = time.time()

    for idx, fpath in enumerate(csv_files):
        if (idx + 1) % 250 == 0 or idx == len(csv_files) - 1:
            print(f"  Processed {idx + 1}/{len(csv_files)} sessions ({time.time() - t0:.1f}s elapsed)...")

        fname = os.path.basename(fpath)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
        year = date_str.split("-")[0]

        try:
            df = pd.read_csv(fpath)
        except Exception:
            continue

        df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
        df['opt_type'] = df['option_type'].map({'CALL': 'CE', 'PUT': 'PE'}).fillna(df['option_type'])

        grouped = df.groupby(['strike_price', 'opt_type'])

        for (strike, o_type), c_df in grouped:
            c_df = c_df.sort_values('datetime').reset_index(drop=True)
            n_bars = len(c_df)
            if n_bars < 25:
                continue

            # Trailing 20-bar SMA excluding current candle (zero look-ahead)
            c_df['sma_vol_20'] = c_df['volume'].shift(1).rolling(20, min_periods=5).mean()

            for i in range(20, n_bars - 1):
                row = c_df.iloc[i]
                lbl = row['strike_label']
                if lbl not in TARGET_LABELS:
                    continue

                total_candles_processed += 1
                dt_str = row['datetime']
                t_bucket = get_time_of_day_bucket(dt_str)
                vol = row['volume']
                sma = row['sma_vol_20']

                next_row = c_df.iloc[i + 1]
                entry_price = next_row['open']
                entry_iv = next_row.get('iv', 0.0)
                if entry_price <= 0:
                    continue

                # Forward price indices
                idx_5 = min(i + 5, n_bars - 1)
                idx_15 = min(i + 15, n_bars - 1)
                idx_30 = min(i + 30, n_bars - 1)
                idx_60 = min(i + 60, n_bars - 1)
                idx_eod = n_bars - 1

                # SHORT (Fade) Returns: (Entry - Exit) / Entry * 100
                short_ret_5 = (entry_price - c_df.iloc[idx_5]['close']) / entry_price * 100.0
                short_ret_15 = (entry_price - c_df.iloc[idx_15]['close']) / entry_price * 100.0
                short_ret_30 = (entry_price - c_df.iloc[idx_30]['close']) / entry_price * 100.0
                short_ret_60 = (entry_price - c_df.iloc[idx_60]['close']) / entry_price * 100.0
                short_ret_eod = (entry_price - c_df.iloc[idx_eod]['close']) / entry_price * 100.0

                # Implied Volatility (IV) Change: IV_forward - IV_entry
                iv_5 = c_df.iloc[idx_5].get('iv', np.nan)
                iv_15 = c_df.iloc[idx_15].get('iv', np.nan)
                iv_30 = c_df.iloc[idx_30].get('iv', np.nan)
                iv_60 = c_df.iloc[idx_60].get('iv', np.nan)
                iv_eod = c_df.iloc[idx_eod].get('iv', np.nan)

                # IV difference (absolute points)
                delta_iv_5 = (iv_5 - entry_iv) if (pd.notna(iv_5) and pd.notna(entry_iv) and entry_iv > 0) else np.nan
                delta_iv_15 = (iv_15 - entry_iv) if (pd.notna(iv_15) and pd.notna(entry_iv) and entry_iv > 0) else np.nan
                delta_iv_30 = (iv_30 - entry_iv) if (pd.notna(iv_30) and pd.notna(entry_iv) and entry_iv > 0) else np.nan
                delta_iv_60 = (iv_60 - entry_iv) if (pd.notna(iv_60) and pd.notna(entry_iv) and entry_iv > 0) else np.nan
                delta_iv_eod = (iv_eod - entry_iv) if (pd.notna(iv_eod) and pd.notna(entry_iv) and entry_iv > 0) else np.nan

                # IV difference (% change)
                pct_iv_5 = (delta_iv_5 / entry_iv * 100.0) if (pd.notna(delta_iv_5) and entry_iv > 0) else np.nan
                pct_iv_15 = (delta_iv_15 / entry_iv * 100.0) if (pd.notna(delta_iv_15) and entry_iv > 0) else np.nan
                pct_iv_30 = (delta_iv_30 / entry_iv * 100.0) if (pd.notna(delta_iv_30) and entry_iv > 0) else np.nan
                pct_iv_60 = (delta_iv_60 / entry_iv * 100.0) if (pd.notna(delta_iv_60) and entry_iv > 0) else np.nan
                pct_iv_eod = (delta_iv_eod / entry_iv * 100.0) if (pd.notna(delta_iv_eod) and entry_iv > 0) else np.nan

                record = {
                    'datetime': dt_str,
                    'year': year,
                    'time_bucket': t_bucket,
                    'strike_label': lbl,
                    'opt_type': o_type,
                    'strike_price': strike,
                    'volume': vol,
                    'sma_vol': sma,
                    'entry_price': entry_price,
                    'entry_iv': entry_iv,
                    'short_ret_5': short_ret_5,
                    'short_ret_15': short_ret_15,
                    'short_ret_30': short_ret_30,
                    'short_ret_60': short_ret_60,
                    'short_ret_eod': short_ret_eod,
                    'delta_iv_5': delta_iv_5,
                    'delta_iv_15': delta_iv_15,
                    'delta_iv_30': delta_iv_30,
                    'delta_iv_60': delta_iv_60,
                    'delta_iv_eod': delta_iv_eod,
                    'pct_iv_5': pct_iv_5,
                    'pct_iv_15': pct_iv_15,
                    'pct_iv_30': pct_iv_30,
                    'pct_iv_60': pct_iv_60,
                    'pct_iv_eod': pct_iv_eod
                }

                if sma and sma > 0:
                    ratio = vol / sma
                    if ratio >= 5.0:
                        def1_5x_events.append(record)
                    if ratio >= 10.0:
                        def1_10x_events.append(record)
                    if ratio < 2.0:
                        baseline_pool[(year, t_bucket, o_type)].append(record)

    print(f"\nScanned {total_candles_processed:,} candles. Found {len(def1_5x_events):,} (5x) and {len(def1_10x_events):,} (10x) events.")

    # -------------------------------------------------------------------------
    # Evaluation Function for Short / Fade Returns & IV Dynamics
    # -------------------------------------------------------------------------
    def evaluate_fade_and_iv(spike_list, group_name):
        n_spikes = len(spike_list)
        if n_spikes == 0:
            print(f"No events for {group_name}")
            return

        np.random.seed(42)
        matched_baseline = []
        strata = defaultdict(list)
        for s in spike_list:
            strata[(s['year'], s['time_bucket'], s['opt_type'])].append(s)

        for (y, tb, ot), sub_spikes in strata.items():
            pool = baseline_pool.get((y, tb, ot), [])
            k = len(sub_spikes)
            if len(pool) >= k:
                sampled_indices = np.random.choice(len(pool), size=k, replace=False)
                for idx in sampled_indices:
                    matched_baseline.append(pool[idx])
            elif len(pool) > 0:
                sampled_indices = np.random.choice(len(pool), size=k, replace=True)
                for idx in sampled_indices:
                    matched_baseline.append(pool[idx])

        df_spk = pd.DataFrame(spike_list)
        df_base = pd.DataFrame(matched_baseline)

        horizons = ['5', '15', '30', '60', 'eod']
        h_labels = ['+5 min', '+15 min', '+30 min', '+60 min', 'Day Close (15:29)']

        # 1. Short (Fade) Performance Table
        short_stats = []
        for h, h_lbl in zip(horizons, h_labels):
            s_ret = df_spk[f'short_ret_{h}'].dropna()
            b_ret = df_base[f'short_ret_{h}'].dropna() if not df_base.empty else pd.Series()

            s_mean = s_ret.mean()
            s_median = s_ret.median()
            s_win = (s_ret > 0).mean() * 100.0

            b_mean = b_ret.mean() if not b_ret.empty else np.nan
            b_median = b_ret.median() if not b_ret.empty else np.nan
            b_win = (b_ret > 0).mean() * 100.0 if not b_ret.empty else np.nan

            if not b_ret.empty and len(s_ret) > 10 and len(b_ret) > 10:
                _, p_val_ttest = stats.ttest_ind(s_ret, b_ret, equal_var=False)
                _, p_val_mwu = stats.mannwhitneyu(s_ret, b_ret, alternative='two-sided')
            else:
                p_val_ttest, p_val_mwu = np.nan, np.nan

            edge = s_mean - b_mean if not np.isnan(b_mean) else np.nan

            short_stats.append({
                'Horizon': h_lbl,
                'Short Spike Mean': f"{s_mean:+.2f}%",
                'Short Base Mean': f"{b_mean:+.2f}%",
                'Short Edge (Spike-Base)': f"{edge:+.2f}%",
                'Spike Median': f"{s_median:+.2f}%",
                'Base Median': f"{b_median:+.2f}%",
                'Short Win%': f"{s_win:.1f}%",
                'Base Win%': f"{b_win:.1f}%",
                'MWU p-val': f"{p_val_mwu:.4e}" if not np.isnan(p_val_mwu) else "N/A",
                'Sig (p<0.01)': "***" if p_val_mwu < 0.001 else "**" if p_val_mwu < 0.01 else "*" if p_val_mwu < 0.05 else "NO"
            })

        print(f"\n" + "=" * 95)
        print(f" 1. SHORT / FADE HYPOTHESIS RESULTS: {group_name.upper()} (N = {n_spikes:,})")
        print("=" * 95)
        print(pd.DataFrame(short_stats).to_string(index=False))

        # 2. Implied Volatility (IV) Dynamics Table
        iv_stats = []
        for h, h_lbl in zip(horizons, h_labels):
            s_div = df_spk[f'delta_iv_{h}'].dropna()
            b_div = df_base[f'delta_iv_{h}'].dropna() if not df_base.empty else pd.Series()
            s_pct_iv = df_spk[f'pct_iv_{h}'].dropna()
            b_pct_iv = df_base[f'pct_iv_{h}'].dropna() if not df_base.empty else pd.Series()

            s_div_mean = s_div.mean()
            b_div_mean = b_div.mean() if not b_div.empty else np.nan
            edge_iv = s_div_mean - b_div_mean if not np.isnan(b_div_mean) else np.nan

            s_pct_mean = s_pct_iv.mean()
            b_pct_mean = b_pct_iv.mean() if not b_pct_iv.empty else np.nan

            crush_pct = (s_div < 0).mean() * 100.0

            if not b_div.empty and len(s_div) > 10 and len(b_div) > 10:
                _, p_val_ttest = stats.ttest_ind(s_div, b_div, equal_var=False)
                _, p_val_mwu = stats.mannwhitneyu(s_div, b_div, alternative='two-sided')
            else:
                p_val_ttest, p_val_mwu = np.nan, np.nan

            iv_stats.append({
                'Horizon': h_lbl,
                'Spike dIV (pts)': f"{s_div_mean:+.3f}",
                'Base dIV (pts)': f"{b_div_mean:+.3f}",
                'IV Edge (pts)': f"{edge_iv:+.3f}",
                'Spike dIV (%)': f"{s_pct_mean:+.2f}%",
                'Base dIV (%)': f"{b_pct_mean:+.2f}%",
                'IV Crush % (<0)': f"{crush_pct:.1f}%",
                'MWU p-val': f"{p_val_mwu:.4e}" if not np.isnan(p_val_mwu) else "N/A",
                'Sig (p<0.01)': "***" if p_val_mwu < 0.001 else "**" if p_val_mwu < 0.01 else "*" if p_val_mwu < 0.05 else "NO"
            })

        print(f"\n" + "=" * 95)
        print(f" 2. IMPLIED VOLATILITY (IV) DYNAMICS: {group_name.upper()} (N = {n_spikes:,})")
        print("=" * 95)
        print(pd.DataFrame(iv_stats).to_string(index=False))

    # Run for Definition 1 (5x and 10x)
    evaluate_fade_and_iv(def1_5x_events, "Definition 1 (5x 20-SMA Spikes)")
    evaluate_fade_and_iv(def1_10x_events, "Definition 1 (10x 20-SMA Spikes)")

    # Also evaluate CE vs PE for Definition 1 (10x)
    ce_10x = [e for e in def1_10x_events if e['opt_type'] == 'CE']
    pe_10x = [e for e in def1_10x_events if e['opt_type'] == 'PE']
    evaluate_fade_and_iv(ce_10x, "Definition 1 (10x SMA) - CALLs Only (CE Short & IV)")
    evaluate_fade_and_iv(pe_10x, "Definition 1 (10x SMA) - PUTs Only (PE Short & IV)")

if __name__ == "__main__":
    main()
