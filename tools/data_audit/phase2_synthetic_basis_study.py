"""
Phase 2 Study: Synthetic Future Basis Divergence & Mean-Reversion Arbitrage Audit.
Evaluates:
  1. 1-Minute Basis Spread = (ATM_Call - ATM_Put + ATM_Strike) - Spot
  2. Daily 09:15-09:45 Opening Baseline (Mean & Std Dev of Basis)
  3. Z-Score Divergence Events (|Z| >= 2.0)
  4. Forward Basis Convergence (+5m, +15m, +30m, +60m, EOD)
  5. Spot vs Option Repricing Decomposition
  6. Matched Baseline & Statistical Significance (Mann-Whitney U)
  7. Expiry Day (0-DTE) vs Non-Expiry Segmentation
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

def get_time_of_day_bucket(dt_str):
    time_part = dt_str.split()[1] if " " in dt_str else dt_str
    hh_mm = time_part[:5]
    if hh_mm <= "11:30":
        return "Morning (09:46-11:30)"
    elif hh_mm <= "14:00":
        return "Midday (11:31-14:00)"
    else:
        return "Afternoon (14:01-15:00)"

def is_expiry_day(dt_str):
    # In India, weekly expiry is typically Thursday (weekday 3)
    d = pd.to_datetime(dt_str.split()[0])
    return d.weekday() == 3

def main():
    print("=" * 95)
    print(" PHASE 2: SYNTHETIC FUTURE BASIS DIVERGENCE & ARBITRAGE EMPIRICAL AUDIT (2021-2026)")
    print("=" * 95)

    csv_files = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    print(f"Total Session CSV Files to Scan: {len(csv_files)}")

    events_rich_synth = []  # Z >= +2.0 (Synthetic Rich / Spot Cheap)
    events_cheap_synth = [] # Z <= -2.0 (Synthetic Cheap / Spot Rich)
    baseline_pool = defaultdict(list)

    total_sessions_processed = 0
    total_bars_audited = 0
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

        # Filter to ATM strike rows
        df_atm = df[df['strike_label'] == 'ATM'].copy()
        if df_atm.empty:
            continue

        # Pivot to get CE and PE on the same row per datetime
        piv = df_atm.pivot(index='datetime', columns='opt_type', values=['open', 'close', 'strike_price', 'spot'])
        piv.columns = [f"{c[0]}_{c[1]}" for c in piv.columns]
        piv = piv.reset_index().sort_values('datetime').reset_index(drop=True)

        if len(piv) < 40 or 'close_CE' not in piv.columns or 'close_PE' not in piv.columns:
            continue

        # Calculate Synthetic Future and Basis Spread for every minute
        # Synthetic Future = Call + Strike - Put
        # Basis Spread = Synthetic Future - Spot
        piv['strike'] = piv['strike_price_CE'].fillna(piv['strike_price_PE'])
        piv['spot'] = piv['spot_CE'].fillna(piv['spot_PE'])
        piv['synth_close'] = piv['close_CE'] - piv['close_PE'] + piv['strike']
        piv['basis_close'] = piv['synth_close'] - piv['spot']

        # Next-candle-open values for realistic entry (t+1)
        piv['synth_open_next'] = (piv['open_CE'].shift(-1) - piv['open_PE'].shift(-1) + piv['strike'].shift(-1))
        piv['spot_open_next'] = piv['spot'].shift(-1) # or open_spot
        piv['basis_open_next'] = piv['synth_open_next'] - piv['spot_open_next']

        # Step 2: Extract opening 30-min baseline (09:15 to 09:45)
        piv['time_str'] = piv['datetime'].apply(lambda x: x.split()[1][:5] if ' ' in str(x) else '')
        opening_mask = (piv['time_str'] >= "09:15") & (piv['time_str'] <= "09:45")
        df_open = piv[opening_mask]

        if len(df_open) < 15:
            continue

        base_mean = df_open['basis_close'].mean()
        base_std = df_open['basis_close'].std()
        base_std = max(base_std, 1.0) # Floor at 1.0 point to prevent division blowup

        # Step 3: Scan post-opening bars (09:46 to 15:00) for Z-score divergence events
        total_sessions_processed += 1
        n_bars = len(piv)
        is_exp = is_expiry_day(date_str)

        for i in range(len(df_open), n_bars - 1):
            row = piv.iloc[i]
            t_str = row['time_str']
            if t_str > "15:00":
                continue # Don't enter trades after 15:00

            total_bars_audited += 1
            dt_str = row['datetime']
            t_bucket = get_time_of_day_bucket(dt_str)

            basis_t = row['basis_close']
            z_score = (basis_t - base_mean) / base_std

            # Next-candle-open entry (t+1)
            next_row = piv.iloc[i + 1]
            entry_basis = next_row['basis_open_next'] if pd.notna(next_row['basis_open_next']) else (next_row['synth_close'] - next_row['spot'])
            entry_synth = next_row['synth_open_next'] if pd.notna(next_row['synth_open_next']) else next_row['synth_close']
            entry_spot = next_row['spot']

            if pd.isna(entry_basis) or pd.isna(entry_synth) or pd.isna(entry_spot):
                continue

            # Forward horizons
            idx_5 = min(i + 5, n_bars - 1)
            idx_15 = min(i + 15, n_bars - 1)
            idx_30 = min(i + 30, n_bars - 1)
            idx_60 = min(i + 60, n_bars - 1)
            idx_eod = n_bars - 1

            basis_5 = piv.iloc[idx_5]['basis_close']
            basis_15 = piv.iloc[idx_15]['basis_close']
            basis_30 = piv.iloc[idx_30]['basis_close']
            basis_60 = piv.iloc[idx_60]['basis_close']
            basis_eod = piv.iloc[idx_eod]['basis_close']

            spot_5 = piv.iloc[idx_5]['spot']
            spot_15 = piv.iloc[idx_15]['spot']
            spot_30 = piv.iloc[idx_30]['spot']
            spot_60 = piv.iloc[idx_60]['spot']
            spot_eod = piv.iloc[idx_eod]['spot']

            synth_5 = piv.iloc[idx_5]['synth_close']
            synth_15 = piv.iloc[idx_15]['synth_close']
            synth_30 = piv.iloc[idx_30]['synth_close']
            synth_60 = piv.iloc[idx_60]['synth_close']
            synth_eod = piv.iloc[idx_eod]['synth_close']

            # Basis Reversion Amount (Points moved toward baseline):
            # For Rich (Z >= 2, entry_basis > base_mean): Reversion = entry_basis - basis_fwd
            # For Cheap (Z <= -2, entry_basis < base_mean): Reversion = basis_fwd - entry_basis
            # Standardized directional basis change:
            record = {
                'datetime': dt_str,
                'year': year,
                'is_expiry': is_exp,
                'time_bucket': t_bucket,
                'z_score': z_score,
                'base_mean': base_mean,
                'base_std': base_std,
                'entry_basis': entry_basis,
                'entry_synth': entry_synth,
                'entry_spot': entry_spot,
                'initial_gap': abs(entry_basis - base_mean),
                # Raw basis delta (basis_t+h - entry_basis)
                'delta_basis_5': basis_5 - entry_basis,
                'delta_basis_15': basis_15 - entry_basis,
                'delta_basis_30': basis_30 - entry_basis,
                'delta_basis_60': basis_60 - entry_basis,
                'delta_basis_eod': basis_eod - entry_basis,
                # Spot moves
                'delta_spot_5': spot_5 - entry_spot,
                'delta_spot_15': spot_15 - entry_spot,
                'delta_spot_30': spot_30 - entry_spot,
                'delta_spot_60': spot_60 - entry_spot,
                'delta_spot_eod': spot_eod - entry_spot,
                # Synth moves
                'delta_synth_5': synth_5 - entry_synth,
                'delta_synth_15': synth_15 - entry_synth,
                'delta_synth_30': synth_30 - entry_synth,
                'delta_synth_60': synth_60 - entry_synth,
                'delta_synth_eod': synth_eod - entry_synth,
            }

            if z_score >= 2.0:
                events_rich_synth.append(record)
            elif z_score <= -2.0:
                events_cheap_synth.append(record)
            elif abs(z_score) < 0.8:
                baseline_pool[(year, t_bucket, is_exp)].append(record)

    print(f"\nCompleted Scanning {total_sessions_processed:,} sessions ({total_bars_audited:,} bars).")
    print(f"  * Synthetic Rich Events (Z >= +2.0):  {len(events_rich_synth):,} events ({len(events_rich_synth)/total_sessions_processed:.1f}/day)")
    print(f"  * Synthetic Cheap Events (Z <= -2.0): {len(events_cheap_synth):,} events ({len(events_cheap_synth)/total_sessions_processed:.1f}/day)")

    # -------------------------------------------------------------------------
    # Evaluation Engine for Basis Mean-Reversion & Decomposition
    # -------------------------------------------------------------------------
    def evaluate_basis_divergence(event_list, event_name, is_rich=True):
        n_events = len(event_list)
        if n_events == 0:
            print(f"No events for {event_name}")
            return

        np.random.seed(42)
        matched_baseline = []
        strata = defaultdict(list)
        for s in event_list:
            strata[(s['year'], s['time_bucket'], s['is_expiry'])].append(s)

        for (y, tb, exp), sub_events in strata.items():
            pool = baseline_pool.get((y, tb, exp), [])
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

        # For Rich (Z >= 2): Reversion = -1 * delta_basis (basis should fall)
        # For Cheap (Z <= -2): Reversion = +1 * delta_basis (basis should rise)
        mult = -1.0 if is_rich else 1.0

        horizons = ['5', '15', '30', '60', 'eod']
        h_labels = ['+5 min', '+15 min', '+30 min', '+60 min', 'Day Close (15:29)']

        table_rows = []
        for h, h_lbl in zip(horizons, h_labels):
            # Basis Reversion (in Index Points)
            s_rev = mult * df_evt[f'delta_basis_{h}'].dropna()
            b_rev = mult * df_base[f'delta_basis_{h}'].dropna() if not df_base.empty else pd.Series()

            s_mean_rev = s_rev.mean()
            s_med_rev = s_rev.median()
            s_win = (s_rev > 0).mean() * 100.0

            b_mean_rev = b_rev.mean() if not b_rev.empty else np.nan
            b_win = (b_rev > 0).mean() * 100.0 if not b_rev.empty else np.nan

            # Gap Closed Percentage
            init_gap = df_evt['initial_gap'].mean()
            gap_closed_pct = (s_mean_rev / init_gap * 100.0) if init_gap > 0 else 0.0

            # Spot Move vs Synth Move Decomposition
            # For Rich (Synthetic too high):
            # If Spot rises -> Spot contributed to closing the gap (mult_spot = +1)
            # If Synth falls -> Option repricing closed the gap (mult_synth = -1)
            s_spot_move = df_evt[f'delta_spot_{h}'].mean()
            s_synth_move = df_evt[f'delta_synth_{h}'].mean()

            if not b_rev.empty and len(s_rev) > 10 and len(b_rev) > 10:
                _, p_val_mwu = stats.mannwhitneyu(s_rev, b_rev, alternative='two-sided')
            else:
                p_val_mwu = np.nan

            table_rows.append({
                'Horizon': h_lbl,
                'Initial Gap (pts)': f"{init_gap:.2f}",
                'Mean Reversion (pts)': f"{s_mean_rev:+.2f} pts",
                'Base Mean Rev': f"{b_mean_rev:+.2f} pts",
                'Net Edge (pts)': f"{(s_mean_rev - b_mean_rev):+.2f} pts",
                'Gap Closed %': f"{gap_closed_pct:.1f}%",
                'Reversion Win%': f"{s_win:.1f}%",
                'Base Win%': f"{b_win:.1f}%",
                'Spot Move (pts)': f"{s_spot_move:+.2f} pts",
                'Synth Move (pts)': f"{s_synth_move:+.2f} pts",
                'MWU p-val': f"{p_val_mwu:.4e}" if not np.isnan(p_val_mwu) else "N/A",
                'Sig (p<0.01)': "***" if p_val_mwu < 0.001 else "**" if p_val_mwu < 0.01 else "*" if p_val_mwu < 0.05 else "NO"
            })

        print(f"\n=========================================================================================")
        print(f" RESULTS FOR: {event_name.upper()} (N = {n_events:,})")
        print("=========================================================================================")
        df_res = pd.DataFrame(table_rows)
        print(df_res[['Horizon', 'Initial Gap (pts)', 'Mean Reversion (pts)', 'Net Edge (pts)', 'Gap Closed %', 'Reversion Win%', 'Base Win%', 'Spot Move (pts)', 'Synth Move (pts)', 'MWU p-val', 'Sig (p<0.01)']].to_string(index=False))

    # Evaluate Rich, Cheap, Combined
    evaluate_basis_divergence(events_rich_synth, "1. Synthetic Future Rich (Z >= +2.0, Overpriced vs Spot)", is_rich=True)
    evaluate_basis_divergence(events_cheap_synth, "2. Synthetic Future Cheap (Z <= -2.0, Underpriced vs Spot)", is_rich=False)

    # Expiry vs Non-Expiry Breakdown
    rich_exp = [e for e in events_rich_synth if e['is_expiry']]
    rich_non_exp = [e for e in events_rich_synth if not e['is_expiry']]
    evaluate_basis_divergence(rich_exp, "1A. Synthetic Rich - 0-DTE Expiry Days Only", is_rich=True)
    evaluate_basis_divergence(rich_non_exp, "1B. Synthetic Rich - Regular Non-Expiry Days", is_rich=True)

    # Time-of-Day Breakdown
    for tb in ["Morning (09:46-11:30)", "Midday (11:31-14:00)", "Afternoon (14:01-15:00)"]:
        sub_e = [e for e in events_rich_synth if e['time_bucket'] == tb]
        evaluate_basis_divergence(sub_e, f"1C. Synthetic Rich - Time: {tb}", is_rich=True)

if __name__ == "__main__":
    main()
