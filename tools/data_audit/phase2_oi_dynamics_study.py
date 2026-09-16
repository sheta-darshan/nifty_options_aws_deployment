"""
Phase 2 Study: Open Interest (OI) Change Dynamics vs Price Direction.
Evaluates:
  1. Fresh Position Buildup (Delta_OI >= 5x, 10x trailing SMA |Delta_OI|)
  2. Position Unwinding (Delta_OI <= -5x, -10x trailing SMA |Delta_OI|)
  3. High Volume + High OI Buildup (Institutional Conviction)
  4. High Volume + Low/Flat OI (Day-Trader Noise / Churn)
  5. Both Momentum (Buyer) and Fade (Short) returns vs Matched Baseline
  6. Mann-Whitney U test p-values, CE vs PE split, Time-of-Day split
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
    print(" PHASE 2: OPEN INTEREST (OI) CHANGE DYNAMICS EMPIRICAL AUDIT (2021-2026)")
    print("=" * 95)

    csv_files = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    print(f"Total Session CSV Files to Scan: {len(csv_files)}")

    # Containers for event categories
    events_oi_build_5x = []
    events_oi_build_10x = []
    events_oi_unwind_5x = []
    events_oi_unwind_10x = []
    events_highvol_highoi = [] # Vol >= 5x AND Delta_OI >= 5x
    events_highvol_lowoi = []  # Vol >= 5x AND |Delta_OI| <= 1x

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

            # Ensure OI exists and is numeric
            if 'oi' not in c_df.columns:
                continue

            c_df['oi'] = pd.to_numeric(c_df['oi'], errors='coerce').fillna(0.0)
            c_df['delta_oi'] = c_df['oi'].diff().fillna(0.0)
            c_df['abs_delta_oi'] = c_df['delta_oi'].abs()

            # Trailing 20-bar SMA excluding current candle (zero look-ahead)
            c_df['sma_abs_doi_20'] = c_df['abs_delta_oi'].shift(1).rolling(20, min_periods=5).mean()
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
                sma_vol = row['sma_vol_20']
                doi = row['delta_oi']
                abs_doi = row['abs_delta_oi']
                sma_doi = row['sma_abs_doi_20']

                next_row = c_df.iloc[i + 1]
                entry_price = next_row['open']
                if entry_price <= 0:
                    continue

                idx_5 = min(i + 5, n_bars - 1)
                idx_15 = min(i + 15, n_bars - 1)
                idx_30 = min(i + 30, n_bars - 1)
                idx_60 = min(i + 60, n_bars - 1)
                idx_eod = n_bars - 1

                # Buyer (Momentum) Returns: (Exit - Entry) / Entry * 100
                fwd_5 = (c_df.iloc[idx_5]['close'] - entry_price) / entry_price * 100.0
                fwd_15 = (c_df.iloc[idx_15]['close'] - entry_price) / entry_price * 100.0
                fwd_30 = (c_df.iloc[idx_30]['close'] - entry_price) / entry_price * 100.0
                fwd_60 = (c_df.iloc[idx_60]['close'] - entry_price) / entry_price * 100.0
                fwd_eod = (c_df.iloc[idx_eod]['close'] - entry_price) / entry_price * 100.0

                record = {
                    'datetime': dt_str,
                    'year': year,
                    'time_bucket': t_bucket,
                    'strike_label': lbl,
                    'opt_type': o_type,
                    'strike_price': strike,
                    'volume': vol,
                    'delta_oi': doi,
                    'abs_delta_oi': abs_doi,
                    'entry_price': entry_price,
                    'ret_5': fwd_5,
                    'ret_15': fwd_15,
                    'ret_30': fwd_30,
                    'ret_60': fwd_60,
                    'ret_eod': fwd_eod
                }

                # Condition 1: Fresh OI Buildup (Delta OI > 0)
                if sma_doi and sma_doi > 0:
                    if doi > 0 and (doi >= 5.0 * sma_doi):
                        events_oi_build_5x.append(record)
                    if doi > 0 and (doi >= 10.0 * sma_doi):
                        events_oi_build_10x.append(record)

                    # Condition 2: Position Unwinding (Delta OI < 0)
                    if doi < 0 and (abs_doi >= 5.0 * sma_doi):
                        events_oi_unwind_5x.append(record)
                    if doi < 0 and (abs_doi >= 10.0 * sma_doi):
                        events_oi_unwind_10x.append(record)

                # Condition 3 & 4: Volume & OI Combined Interactions
                if sma_vol and sma_vol > 0 and sma_doi and sma_doi > 0:
                    vol_ratio = vol / sma_vol
                    doi_ratio = abs_doi / sma_doi
                    # High Vol + High Positive OI Buildup (Conviction)
                    if vol_ratio >= 5.0 and (doi > 0 and doi_ratio >= 5.0):
                        events_highvol_highoi.append(record)
                    # High Vol + Low / Flat OI (Churn / Scalp)
                    if vol_ratio >= 5.0 and doi_ratio <= 1.0:
                        events_highvol_lowoi.append(record)

                # Baseline pool: Normal OI & Normal Vol
                if sma_doi and abs_doi < 2.0 * sma_doi and sma_vol and vol < 2.0 * sma_vol:
                    baseline_pool[(year, t_bucket, o_type)].append(record)

    print(f"\nCompleted Scanning. Event Counts:")
    print(f"  * OI Buildup >= 5x:   {len(events_oi_build_5x):,} events ({len(events_oi_build_5x)/len(csv_files):.1f}/day)")
    print(f"  * OI Buildup >= 10x:  {len(events_oi_build_10x):,} events ({len(events_oi_build_10x)/len(csv_files):.1f}/day)")
    print(f"  * OI Unwind >= 5x:    {len(events_oi_unwind_5x):,} events ({len(events_oi_unwind_5x)/len(csv_files):.1f}/day)")
    print(f"  * OI Unwind >= 10x:   {len(events_oi_unwind_10x):,} events ({len(events_oi_unwind_10x)/len(csv_files):.1f}/day)")
    print(f"  * High Vol + High OI: {len(events_highvol_highoi):,} events ({len(events_highvol_highoi)/len(csv_files):.1f}/day)")
    print(f"  * High Vol + Low OI:  {len(events_highvol_lowoi):,} events ({len(events_highvol_lowoi)/len(csv_files):.1f}/day)")

    # -------------------------------------------------------------------------
    # Evaluation Engine for Momentum & Fade
    # -------------------------------------------------------------------------
    def evaluate_oi_event(event_list, event_name):
        n_events = len(event_list)
        if n_events == 0:
            print(f"\nNo events found for {event_name}")
            return

        np.random.seed(42)
        matched_baseline = []
        strata = defaultdict(list)
        for s in event_list:
            strata[(s['year'], s['time_bucket'], s['opt_type'])].append(s)

        for (y, tb, ot), sub_events in strata.items():
            pool = baseline_pool.get((y, tb, ot), [])
            k = len(sub_events)
            if len(pool) >= k:
                sampled_indices = np.random.choice(len(pool), size=k, replace=False)
                for idx in sampled_indices:
                    matched_baseline.append(pool[idx])
            elif len(pool) > 0:
                sampled_indices = np.random.choice(len(pool), size=k, replace=True)
                for idx in sampled_indices:
                    matched_baseline.append(pool[idx])

        df_evt = pd.DataFrame(event_list)
        df_base = pd.DataFrame(matched_baseline)

        horizons = ['5', '15', '30', '60', 'eod']
        h_labels = ['+5 min', '+15 min', '+30 min', '+60 min', 'Day Close (15:29)']

        # MOMENTUM (BUY) BATTERY
        mom_rows = []
        for h, h_lbl in zip(horizons, h_labels):
            s_ret = df_evt[f'ret_{h}'].dropna()
            b_ret = df_base[f'ret_{h}'].dropna() if not df_base.empty else pd.Series()

            s_mean = s_ret.mean()
            b_mean = b_ret.mean() if not b_ret.empty else np.nan
            edge_buy = s_mean - b_mean if not np.isnan(b_mean) else np.nan

            s_win = (s_ret > 0).mean() * 100.0
            b_win = (b_ret > 0).mean() * 100.0 if not b_ret.empty else np.nan

            if not b_ret.empty and len(s_ret) > 10 and len(b_ret) > 10:
                _, p_val_mwu = stats.mannwhitneyu(s_ret, b_ret, alternative='two-sided')
            else:
                p_val_mwu = np.nan

            mom_rows.append({
                'Horizon': h_lbl,
                'Buy Event Mean': f"{s_mean:+.2f}%",
                'Buy Base Mean': f"{b_mean:+.2f}%",
                'Buy Edge': f"{edge_buy:+.2f}%",
                'Event Win%': f"{s_win:.1f}%",
                'Base Win%': f"{b_win:.1f}%",
                'MWU p-val': f"{p_val_mwu:.4e}" if not np.isnan(p_val_mwu) else "N/A",
                'Sig (p<0.01)': "***" if p_val_mwu < 0.001 else "**" if p_val_mwu < 0.01 else "*" if p_val_mwu < 0.05 else "NO"
            })

        print(f"\n=========================================================================================")
        print(f" [MOMENTUM / BUY] RESULTS FOR: {event_name.upper()} (N = {n_events:,})")
        print("=========================================================================================")
        print(pd.DataFrame(mom_rows).to_string(index=False))

        # FADE (SHORT) BATTERY
        fade_rows = []
        for h, h_lbl in zip(horizons, h_labels):
            s_ret = -1.0 * df_evt[f'ret_{h}'].dropna()
            b_ret = -1.0 * df_base[f'ret_{h}'].dropna() if not df_base.empty else pd.Series()

            s_mean = s_ret.mean()
            b_mean = b_ret.mean() if not b_ret.empty else np.nan
            edge_short = s_mean - b_mean if not np.isnan(b_mean) else np.nan

            s_win = (s_ret > 0).mean() * 100.0
            b_win = (b_ret > 0).mean() * 100.0 if not b_ret.empty else np.nan

            if not b_ret.empty and len(s_ret) > 10 and len(b_ret) > 10:
                _, p_val_mwu = stats.mannwhitneyu(s_ret, b_ret, alternative='two-sided')
            else:
                p_val_mwu = np.nan

            fade_rows.append({
                'Horizon': h_lbl,
                'Short Event Mean': f"{s_mean:+.2f}%",
                'Short Base Mean': f"{b_mean:+.2f}%",
                'Short Edge': f"{edge_short:+.2f}%",
                'Short Win%': f"{s_win:.1f}%",
                'Base Win%': f"{b_win:.1f}%",
                'MWU p-val': f"{p_val_mwu:.4e}" if not np.isnan(p_val_mwu) else "N/A",
                'Sig (p<0.01)': "***" if p_val_mwu < 0.001 else "**" if p_val_mwu < 0.01 else "*" if p_val_mwu < 0.05 else "NO"
            })

        print(f"\n=========================================================================================")
        print(f" [FADE / SHORT] RESULTS FOR: {event_name.upper()} (N = {n_events:,})")
        print("=========================================================================================")
        print(pd.DataFrame(fade_rows).to_string(index=False))

    # Run evaluations
    evaluate_oi_event(events_oi_build_5x, "1. Fresh OI Buildup (Delta_OI >= 5x SMA)")
    evaluate_oi_event(events_oi_build_10x, "2. Fresh OI Buildup (Delta_OI >= 10x SMA)")
    evaluate_oi_event(events_oi_unwind_5x, "3. Position Unwinding (Delta_OI <= -5x SMA)")
    evaluate_oi_event(events_oi_unwind_10x, "4. Position Unwinding (Delta_OI <= -10x SMA)")
    evaluate_oi_event(events_highvol_highoi, "5. High Volume + High OI Buildup (Institutional Conviction)")
    evaluate_oi_event(events_highvol_lowoi, "6. High Volume + Low/Flat OI (Churn / Day-Trader Noise)")

    # CE vs PE Split for High Vol + High OI
    ce_hv_hoi = [e for e in events_highvol_highoi if e['opt_type'] == 'CE']
    pe_hv_hoi = [e for e in events_highvol_highoi if e['opt_type'] == 'PE']
    evaluate_oi_event(ce_hv_hoi, "5A. High Vol + High OI (CALLs Only - CE)")
    evaluate_oi_event(pe_hv_hoi, "5B. High Vol + High OI (PUTs Only - PE)")

if __name__ == "__main__":
    main()
