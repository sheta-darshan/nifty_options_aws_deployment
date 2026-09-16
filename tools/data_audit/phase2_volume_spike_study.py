"""
Phase 2: Comprehensive Forward Return Study on Abnormal Option Volume Spikes.
Evaluates:
  - Definition 1: Relative Trailing 20-bar SMA Spikes (5x, 8x, 10x, 15x)
  - Definition 2: Year-Stratified 99th Percentile Volume Spikes
  - Matched Baseline (Same Time-of-Day & Same Year Distribution)
  - Next-candle-open entry price (Zero Look-Ahead Bias)
  - Forward horizons: +5m, +15m, +30m, +60m, EOD Close (15:29)
  - Statistical Significance Tests (Student's t-test and Mann-Whitney U)
  - Segmented by Option Type (CE vs PE) and Time-of-Day (Open / Midday / Close)
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
    # dt_str format: 'YYYY-MM-DD HH:MM:SS'
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
    print(" PHASE 2: FORWARD RETURN STUDY ON ABNORMAL OPTION VOLUME SPIKES (2021-2026)")
    print("=" * 95)

    csv_files = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    print(f"Total Session CSV Files to Scan: {len(csv_files)}")

    # Step 1: First pass to compute exact Year-Stratified 99th percentiles
    print("\n>>> [STEP 1] Computing Year-Stratified 99th Percentiles for Definition 2...")
    yearly_vols = defaultdict(list)
    for idx, fpath in enumerate(csv_files):
        fname = os.path.basename(fpath)
        year = fname.replace("NIFTY_", "").split("-")[0]
        try:
            df = pd.read_csv(fpath)
            df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
            df_sub = df[df['strike_label'].isin(TARGET_LABELS)]
            if not df_sub.empty:
                yearly_vols[year].extend(df_sub['volume'].to_numpy())
        except Exception:
            pass

    year_p99 = {}
    print("\nYear-Stratified 99th Percentile Volume Thresholds (Definition 2):")
    for y in sorted(yearly_vols.keys()):
        arr = np.array(yearly_vols[y], dtype=np.float64)
        p99_val = float(np.percentile(arr, 99.0))
        year_p99[y] = p99_val
        print(f"  * Year {y}: 99th Percentile = {int(p99_val):,} volume ({len(arr):,} candles audited)")

    # Step 2: Main scan across all sessions
    print("\n>>> [STEP 2] Scanning all sessions for Spikes, Forward Returns, and Baseline Pool...")
    
    # Store records for Definition 1 (at 5x, 8x, 10x, 15x) and Definition 2
    def1_5x_events = []
    def1_8x_events = []
    def1_10x_events = []
    def1_15x_events = []
    def2_p99_events = []
    
    # Non-spike candidate pool for baseline matching: key = (year, time_bucket) -> list of candle dicts
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

        # Build spot price map for forward spot return lookup
        spot_df = df[['datetime', 'spot']].drop_duplicates(subset=['datetime']).sort_values('datetime').reset_index(drop=True)
        spot_map = dict(zip(spot_df['datetime'], spot_df['spot']))
        all_timestamps = spot_df['datetime'].tolist()
        ts_to_idx = {ts: i for i, ts in enumerate(all_timestamps)}
        n_timestamps = len(all_timestamps)

        # Process each physical contract (strike_price, opt_type)
        grouped = df.groupby(['strike_price', 'opt_type'])

        for (strike, o_type), c_df in grouped:
            c_df = c_df.sort_values('datetime').reset_index(drop=True)
            n_bars = len(c_df)
            if n_bars < 25:
                continue

            # Trailing 20-bar SMA excluding current candle (zero look-ahead)
            c_df['sma_vol_20'] = c_df['volume'].shift(1).rolling(20, min_periods=5).mean()
            
            # Map index by datetime for fast forward lookup
            c_ts_to_idx = {row['datetime']: i for i, row in c_df.iterrows()}

            for i in range(20, n_bars - 1): # Must have at least 1 future candle for next-open entry
                row = c_df.iloc[i]
                lbl = row['strike_label']
                
                # Only analyze near-the-money universe (ATM+-3)
                if lbl not in TARGET_LABELS:
                    continue

                total_candles_processed += 1
                dt_str = row['datetime']
                t_bucket = get_time_of_day_bucket(dt_str)
                vol = row['volume']
                sma = row['sma_vol_20']

                # Next-candle-open entry price (strictly no look-ahead)
                next_row = c_df.iloc[i + 1]
                entry_price = next_row['open']
                if entry_price <= 0:
                    continue

                # Forward option returns
                # +5m (index i+5), +15m (i+15), +30m (i+30), +60m (i+60), EOD (last bar)
                idx_5 = min(i + 5, n_bars - 1)
                idx_15 = min(i + 15, n_bars - 1)
                idx_30 = min(i + 30, n_bars - 1)
                idx_60 = min(i + 60, n_bars - 1)
                idx_eod = n_bars - 1

                fwd_opt_5 = (c_df.iloc[idx_5]['close'] - entry_price) / entry_price * 100.0
                fwd_opt_15 = (c_df.iloc[idx_15]['close'] - entry_price) / entry_price * 100.0
                fwd_opt_30 = (c_df.iloc[idx_30]['close'] - entry_price) / entry_price * 100.0
                fwd_opt_60 = (c_df.iloc[idx_60]['close'] - entry_price) / entry_price * 100.0
                fwd_opt_eod = (c_df.iloc[idx_eod]['close'] - entry_price) / entry_price * 100.0

                # Forward spot returns
                spot_cur_idx = ts_to_idx.get(dt_str, 0)
                next_ts = next_row['datetime']
                spot_entry_ts = all_timestamps[min(spot_cur_idx + 1, n_timestamps - 1)]
                spot_entry = spot_map.get(spot_entry_ts, row['spot'])

                spot_ts_5 = all_timestamps[min(spot_cur_idx + 5, n_timestamps - 1)]
                spot_ts_15 = all_timestamps[min(spot_cur_idx + 15, n_timestamps - 1)]
                spot_ts_30 = all_timestamps[min(spot_cur_idx + 30, n_timestamps - 1)]
                spot_ts_60 = all_timestamps[min(spot_cur_idx + 60, n_timestamps - 1)]
                spot_ts_eod = all_timestamps[-1]

                fwd_spot_5 = (spot_map[spot_ts_5] - spot_entry) / spot_entry * 100.0 if spot_entry > 0 else 0.0
                fwd_spot_15 = (spot_map[spot_ts_15] - spot_entry) / spot_entry * 100.0 if spot_entry > 0 else 0.0
                fwd_spot_30 = (spot_map[spot_ts_30] - spot_entry) / spot_entry * 100.0 if spot_entry > 0 else 0.0
                fwd_spot_60 = (spot_map[spot_ts_60] - spot_entry) / spot_entry * 100.0 if spot_entry > 0 else 0.0
                fwd_spot_eod = (spot_map[spot_ts_eod] - spot_entry) / spot_entry * 100.0 if spot_entry > 0 else 0.0

                record = {
                    'datetime': dt_str,
                    'year': year,
                    'time_bucket': t_bucket,
                    'strike_label': lbl,
                    'opt_type': o_type,
                    'strike_price': strike,
                    'volume': vol,
                    'sma_vol': sma,
                    'vol_ratio': vol / max(1.0, sma) if sma and sma > 0 else 1.0,
                    'entry_price': entry_price,
                    'ret_opt_5': fwd_opt_5,
                    'ret_opt_15': fwd_opt_15,
                    'ret_opt_30': fwd_opt_30,
                    'ret_opt_60': fwd_opt_60,
                    'ret_opt_eod': fwd_opt_eod,
                    'ret_spot_5': fwd_spot_5,
                    'ret_spot_15': fwd_spot_15,
                    'ret_spot_30': fwd_spot_30,
                    'ret_spot_60': fwd_spot_60,
                    'ret_spot_eod': fwd_spot_eod
                }

                # Check Definition 1 thresholds (SMA Multiplier)
                if sma and sma > 0:
                    ratio = vol / sma
                    if ratio >= 5.0:
                        def1_5x_events.append(record)
                    if ratio >= 8.0:
                        def1_8x_events.append(record)
                    if ratio >= 10.0:
                        def1_10x_events.append(record)
                    if ratio >= 15.0:
                        def1_15x_events.append(record)

                # Check Definition 2 threshold (Year-Stratified 99th Percentile)
                if vol >= year_p99.get(year, 1e9):
                    def2_p99_events.append(record)

                # Collect non-spike candidates for baseline (ratio < 2.0 and vol < p90)
                if sma and (vol / max(1.0, sma) < 2.0) and vol < year_p99.get(year, 1e9) * 0.5:
                    baseline_pool[(year, t_bucket, o_type)].append(record)

    print(f"\nCompleted Scanning {total_candles_processed:,} near-the-money candles in {time.time() - t0:.1f}s.")

    # -------------------------------------------------------------------------
    # Helper for Matched Baseline Sampling & Statistical Evaluation
    # -------------------------------------------------------------------------
    def evaluate_group(spike_list, group_name):
        n_spikes = len(spike_list)
        if n_spikes == 0:
            print(f"\n[WARNING] No events found for {group_name}.")
            return None

        # Sample matched baseline: exactly matching (year, time_bucket, opt_type)
        np.random.seed(42)
        matched_baseline = []
        
        # Group spikes by (year, time_bucket, opt_type)
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

        stats_table = []
        for h, h_lbl in zip(horizons, h_labels):
            s_ret = df_spk[f'ret_opt_{h}'].dropna()
            b_ret = df_base[f'ret_opt_{h}'].dropna() if not df_base.empty else pd.Series()
            s_spot = df_spk[f'ret_spot_{h}'].dropna()

            s_mean = s_ret.mean()
            s_median = s_ret.median()
            s_win = (s_ret > 0).mean() * 100.0

            b_mean = b_ret.mean() if not b_ret.empty else np.nan
            b_median = b_ret.median() if not b_ret.empty else np.nan
            b_win = (b_ret > 0).mean() * 100.0 if not b_ret.empty else np.nan

            # T-test & Mann-Whitney U test
            if not b_ret.empty and len(s_ret) > 10 and len(b_ret) > 10:
                t_stat, p_val_ttest = stats.ttest_ind(s_ret, b_ret, equal_var=False)
                u_stat, p_val_mwu = stats.mannwhitneyu(s_ret, b_ret, alternative='two-sided')
            else:
                p_val_ttest, p_val_mwu = np.nan, np.nan

            diff_mean = s_mean - b_mean if not np.isnan(b_mean) else np.nan

            stats_table.append({
                'Horizon': h_lbl,
                'Spike Mean': f"{s_mean:+.2f}%",
                'Base Mean': f"{b_mean:+.2f}%",
                'Edge (Spike-Base)': f"{diff_mean:+.2f}%",
                'Spike Median': f"{s_median:+.2f}%",
                'Base Median': f"{b_median:+.2f}%",
                'Spike Win%': f"{s_win:.1f}%",
                'Base Win%': f"{b_win:.1f}%",
                'Spot Mean': f"{s_spot.mean():+.3f}%",
                't-test p-val': f"{p_val_ttest:.4e}" if not np.isnan(p_val_ttest) else "N/A",
                'MWU p-val': f"{p_val_mwu:.4e}" if not np.isnan(p_val_mwu) else "N/A",
                'Sig (p<0.01)': "***" if p_val_mwu < 0.001 else "**" if p_val_mwu < 0.01 else "*" if p_val_mwu < 0.05 else "NO"
            })

        print(f"\n=========================================================================================")
        print(f" RESULTS FOR: {group_name.upper()} (N = {n_spikes:,} spike events | Baseline N = {len(matched_baseline):,})")
        print(f"=========================================================================================")
        df_out = pd.DataFrame(stats_table)
        print(df_out[['Horizon', 'Spike Mean', 'Base Mean', 'Edge (Spike-Base)', 'Spike Median', 'Base Median', 'Spike Win%', 'Base Win%', 'MWU p-val', 'Sig (p<0.01)']].to_string(index=False))

        return df_spk, df_base

    # -------------------------------------------------------------------------
    # 1. Summary of Event Counts across Definitions
    # -------------------------------------------------------------------------
    print("\n" + "=" * 95)
    print("                    EVENT FREQUENCY & TRADEABILITY COMPARISON")
    print("=" * 95)
    n_days = len(csv_files)
    freq_summary = [
        {"Definition": "Definition 1 (5x 20-SMA)", "Total Events": f"{len(def1_5x_events):,}", "Avg / Day": f"{len(def1_5x_events)/n_days:.1f}", "Avg / Strike/Day": f"{len(def1_5x_events)/(n_days*14):.2f}"},
        {"Definition": "Definition 1 (8x 20-SMA)", "Total Events": f"{len(def1_8x_events):,}", "Avg / Day": f"{len(def1_8x_events)/n_days:.1f}", "Avg / Strike/Day": f"{len(def1_8x_events)/(n_days*14):.2f}"},
        {"Definition": "Definition 1 (10x 20-SMA)", "Total Events": f"{len(def1_10x_events):,}", "Avg / Day": f"{len(def1_10x_events)/n_days:.1f}", "Avg / Strike/Day": f"{len(def1_10x_events)/(n_days*14):.2f}"},
        {"Definition": "Definition 1 (15x 20-SMA)", "Total Events": f"{len(def1_15x_events):,}", "Avg / Day": f"{len(def1_15x_events)/n_days:.1f}", "Avg / Strike/Day": f"{len(def1_15x_events)/(n_days*14):.2f}"},
        {"Definition": "Definition 2 (Yearly 99th Pct)", "Total Events": f"{len(def2_p99_events):,}", "Avg / Day": f"{len(def2_p99_events)/n_days:.1f}", "Avg / Strike/Day": f"{len(def2_p99_events)/(n_days*14):.2f}"},
    ]
    print(pd.DataFrame(freq_summary).to_string(index=False))

    # -------------------------------------------------------------------------
    # 2. Main Comparative Runs
    # -------------------------------------------------------------------------
    df_def1_5x, _ = evaluate_group(def1_5x_events, "Definition 1: Relative Volume Spike (>= 5x Trailing 20-SMA)")
    df_def1_10x, _ = evaluate_group(def1_10x_events, "Definition 1 Sensitivity: Relative Volume Spike (>= 10x Trailing 20-SMA)")
    df_def2_p99, _ = evaluate_group(def2_p99_events, "Definition 2: Year-Stratified 99th Percentile Volume Spike")

    # -------------------------------------------------------------------------
    # 3. Segmentation by Option Type (CE vs PE) for Definition 1 (10x) and Def 2
    # -------------------------------------------------------------------------
    print("\n" + "=" * 95)
    print("                      CE vs PE SUB-SEGMENT ANALYSIS")
    print("=" * 95)
    
    # Def 1 (10x) CE vs PE
    ce_def1_10x = [e for e in def1_10x_events if e['opt_type'] == 'CE']
    pe_def1_10x = [e for e in def1_10x_events if e['opt_type'] == 'PE']
    evaluate_group(ce_def1_10x, "Definition 1 (10x SMA) - CALL Options Only (CE)")
    evaluate_group(pe_def1_10x, "Definition 1 (10x SMA) - PUT Options Only (PE)")

    # Def 2 (Yearly 99th) CE vs PE
    ce_def2 = [e for e in def2_p99_events if e['opt_type'] == 'CE']
    pe_def2 = [e for e in def2_p99_events if e['opt_type'] == 'PE']
    evaluate_group(ce_def2, "Definition 2 (Yearly 99th) - CALL Options Only (CE)")
    evaluate_group(pe_def2, "Definition 2 (Yearly 99th) - PUT Options Only (PE)")

    # -------------------------------------------------------------------------
    # 4. Segmentation by Time-of-Day (Morning Open vs Midday vs Afternoon Close)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 95)
    print("                    TIME-OF-DAY SUB-SEGMENT ANALYSIS")
    print("=" * 95)
    
    # Time-of-day for Def 1 (10x)
    for tb in ["Morning_Open (09:15-09:45)", "Midday (09:46-14:44)", "Afternoon_Close (14:45-15:25)"]:
        sub_events = [e for e in def1_10x_events if e['time_bucket'] == tb]
        evaluate_group(sub_events, f"Definition 1 (10x SMA) - Time: {tb}")

    # Time-of-day for Def 2 (Yearly 99th)
    for tb in ["Morning_Open (09:15-09:45)", "Midday (09:46-14:44)", "Afternoon_Close (14:45-15:25)"]:
        sub_events = [e for e in def2_p99_events if e['time_bucket'] == tb]
        evaluate_group(sub_events, f"Definition 2 (Yearly 99th) - Time: {tb}")

if __name__ == "__main__":
    main()
