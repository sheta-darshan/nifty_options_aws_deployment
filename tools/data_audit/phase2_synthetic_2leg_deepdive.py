"""
Phase 2 Deep Dive: 2-Leg Options-Only Conversion (Long CE + Short PE) on Synthetic Cheap Events.
Evaluates:
  1. 2-Leg Gross & Net Points (Long ATM Call + Short ATM Put) at +5m, +15m, +30m, +60m, Day Close (15:29), and Next-Day Open (09:15-09:45)
  2. Exact 2-Leg Round-Trip Friction (Statutory Taxes + 0.5% Slippage per leg)
  3. Individual Trade Net Win Rate (% of trades > 0 after friction)
  4. Multi-Year Regime Trend (2021 to 2026) - Is the edge shrinking?
  5. Directional Spot Risk Exposure (Delta = 1.0) on Naked 2-Leg Conversion
"""
import os
import glob
import time
import pandas as pd
import numpy as np
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

def compute_2leg_friction_pts(call_entry, put_entry, call_exit, put_exit, lot_size=50):
    if any(pd.isna([call_entry, put_entry, call_exit, put_exit])):
        return np.nan
    # Leg 1: Long Call (Buy entry, Sell exit)
    # Leg 2: Short Put (Sell entry, Buy exit)
    # Slippage (0.5% each leg entry + exit, min 0.05 pt floor)
    slip_call = max(call_entry * 0.005, 0.05) + max(call_exit * 0.005, 0.05)
    slip_put = max(put_entry * 0.005, 0.05) + max(put_exit * 0.005, 0.05)
    total_slippage_pts = slip_call + slip_put

    # Statutory Taxes & Brokerage (in INR per lot)
    brokerage = 80.0
    
    # Turnover (INR)
    buy_turnover = (call_entry + put_exit) * lot_size
    sell_turnover = (call_exit + put_entry) * lot_size
    round_trip_turnover = buy_turnover + sell_turnover

    # STT (0.15% on Sell side)
    stt = sell_turnover * 0.0015
    # Exchange turnover (0.03553%)
    exch = round_trip_turnover * 0.0003553
    # GST (18% on Brokerage + Exchange)
    gst = 0.18 * (brokerage + exch)
    # Stamp duty (0.003% on Buy side)
    stamp = max(round(buy_turnover * 0.00003), 1.0) if pd.notna(buy_turnover) else 1.0
    # SEBI
    sebi = round_trip_turnover * 0.000001

    total_taxes_inr = brokerage + stt + exch + gst + stamp + sebi
    taxes_pts = total_taxes_inr / lot_size

    total_friction_pts = total_slippage_pts + taxes_pts
    return total_friction_pts

def is_expiry_day(dt_str):
    d = pd.to_datetime(dt_str.split()[0])
    return d.weekday() == 3

def main():
    print("=" * 95)
    print(" PHASE 2 DEEP DIVE: 2-LEG OPTIONS-ONLY SYNTHETIC CONVERSION ARBITRAGE (2021-2026)")
    print("=" * 95)

    csv_files = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    print(f"Total Session CSV Files: {len(csv_files)}")

    # Load session DataFrames into memory mapping date -> pivoted df
    session_pivots = {}
    session_dates = []

    print("\n>>> [STEP 1] Pre-processing daily session ATM series...")
    t0 = time.time()
    for idx, fpath in enumerate(csv_files):
        fname = os.path.basename(fpath)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")

        try:
            df = pd.read_csv(fpath)
        except Exception:
            continue

        df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
        df['opt_type'] = df['option_type'].map({'CALL': 'CE', 'PUT': 'PE'}).fillna(df['option_type'])

        df_atm = df[df['strike_label'] == 'ATM'].copy()
        if df_atm.empty:
            continue

        piv = df_atm.pivot(index='datetime', columns='opt_type', values=['open', 'close', 'strike_price', 'spot'])
        piv.columns = [f"{c[0]}_{c[1]}" for c in piv.columns]
        piv = piv.reset_index().sort_values('datetime').reset_index(drop=True)

        if len(piv) < 40 or 'close_CE' not in piv.columns or 'close_PE' not in piv.columns:
            continue

        piv['strike'] = piv['strike_price_CE'].fillna(piv['strike_price_PE'])
        piv['spot'] = piv['spot_CE'].fillna(piv['spot_PE'])
        piv['synth_close'] = piv['close_CE'] - piv['close_PE'] + piv['strike']
        piv['basis_close'] = piv['synth_close'] - piv['spot']

        piv['time_str'] = piv['datetime'].apply(lambda x: x.split()[1][:5] if ' ' in str(x) else '')
        session_pivots[date_str] = piv
        session_dates.append(date_str)

    print(f"Preprocessed {len(session_pivots):,} valid daily sessions in {time.time() - t0:.1f}s.")

    # Step 2: Audit Synthetic Cheap Events (Z <= -2.0)
    print("\n>>> [STEP 2] Evaluating 2-Leg Synthetic Long (+CE, -PE) Payoffs & Frictions...")

    cheap_records = []
    
    for s_idx, date_str in enumerate(session_dates):
        piv = session_pivots[date_str]
        year = date_str.split("-")[0]
        is_exp = is_expiry_day(date_str)

        # Baseline: 09:15-09:45
        df_open = piv[(piv['time_str'] >= "09:15") & (piv['time_str'] <= "09:45")]
        if len(df_open) < 15:
            continue

        base_mean = df_open['basis_close'].mean()
        base_std = max(df_open['basis_close'].std(), 1.0)

        n_bars = len(piv)
        next_piv = session_pivots.get(session_dates[s_idx + 1]) if (s_idx + 1 < len(session_dates) and not is_exp) else None

        for i in range(len(df_open), n_bars - 1):
            row = piv.iloc[i]
            t_str = row['time_str']
            if t_str > "15:00":
                continue

            basis_t = row['basis_close']
            z_score = (basis_t - base_mean) / base_std

            if z_score <= -2.0: # Synthetic Cheap Event
                # Entry at next-candle-open (i+1)
                next_row = piv.iloc[i + 1]
                ce_entry = next_row['open_CE'] if pd.notna(next_row.get('open_CE')) else next_row['close_CE']
                pe_entry = next_row['open_PE'] if pd.notna(next_row.get('open_PE')) else next_row['close_PE']
                spot_entry = next_row['spot']
                strike_entry = next_row['strike']
                synth_entry = ce_entry - pe_entry + strike_entry
                basis_entry = synth_entry - spot_entry

                if ce_entry <= 0 or pe_entry <= 0:
                    continue

                # Horizons
                idx_5 = min(i + 5, n_bars - 1)
                idx_15 = min(i + 15, n_bars - 1)
                idx_30 = min(i + 30, n_bars - 1)
                idx_60 = min(i + 60, n_bars - 1)
                idx_eod = n_bars - 1

                # Forward Option Closes
                ce_5, pe_5, sp_5 = piv.iloc[idx_5]['close_CE'], piv.iloc[idx_5]['close_PE'], piv.iloc[idx_5]['spot']
                ce_15, pe_15, sp_15 = piv.iloc[idx_15]['close_CE'], piv.iloc[idx_15]['close_PE'], piv.iloc[idx_15]['spot']
                ce_30, pe_30, sp_30 = piv.iloc[idx_30]['close_CE'], piv.iloc[idx_30]['close_PE'], piv.iloc[idx_30]['spot']
                ce_60, pe_60, sp_60 = piv.iloc[idx_60]['close_CE'], piv.iloc[idx_60]['close_PE'], piv.iloc[idx_60]['spot']
                ce_eod, pe_eod, sp_eod = piv.iloc[idx_eod]['close_CE'], piv.iloc[idx_eod]['close_PE'], piv.iloc[idx_eod]['spot']

                # Gross 2-Leg Payoff: (+CE PnL) + (-PE PnL) = (ce_exit - ce_entry) + (pe_entry - pe_exit)
                # = (ce_exit - pe_exit) - (ce_entry - pe_entry) = Delta_Synth
                gross_pts_5 = (ce_5 - pe_5) - (ce_entry - pe_entry)
                gross_pts_15 = (ce_15 - pe_15) - (ce_entry - pe_entry)
                gross_pts_30 = (ce_30 - pe_30) - (ce_entry - pe_entry)
                gross_pts_60 = (ce_60 - pe_60) - (ce_entry - pe_entry)
                gross_pts_eod = (ce_eod - pe_eod) - (ce_entry - pe_entry)

                # 2-Leg Friction Costs
                fric_5 = compute_2leg_friction_pts(ce_entry, pe_entry, ce_5, pe_5)
                fric_15 = compute_2leg_friction_pts(ce_entry, pe_entry, ce_15, pe_15)
                fric_30 = compute_2leg_friction_pts(ce_entry, pe_entry, ce_30, pe_30)
                fric_60 = compute_2leg_friction_pts(ce_entry, pe_entry, ce_60, pe_60)
                fric_eod = compute_2leg_friction_pts(ce_entry, pe_entry, ce_eod, pe_eod)

                # Next Day Opening Range (09:15-09:45) Reversion (if held overnight)
                gross_pts_next_open = np.nan
                fric_next_open = np.nan
                spot_next_open_delta = np.nan

                if next_piv is not None:
                    next_open_bars = next_piv[(next_piv['time_str'] >= "09:15") & (next_piv['time_str'] <= "09:45")]
                    if not next_open_bars.empty:
                        ce_next = next_open_bars['close_CE'].mean()
                        pe_next = next_open_bars['close_PE'].mean()
                        sp_next = next_open_bars['spot'].mean()
                        gross_pts_next_open = (ce_next - pe_next) - (ce_entry - pe_entry)
                        fric_next_open = compute_2leg_friction_pts(ce_entry, pe_entry, ce_next, pe_next)
                        spot_next_open_delta = sp_next - spot_entry

                cheap_records.append({
                    'datetime': row['datetime'],
                    'year': year,
                    'is_expiry': is_exp,
                    'initial_gap': abs(basis_entry - base_mean),
                    'spot_entry': spot_entry,
                    'ce_entry': ce_entry,
                    'pe_entry': pe_entry,
                    # Gross Points
                    'gross_5': gross_pts_5,
                    'gross_15': gross_pts_15,
                    'gross_30': gross_pts_30,
                    'gross_60': gross_pts_60,
                    'gross_eod': gross_pts_eod,
                    'gross_next_open': gross_pts_next_open,
                    # Friction Points
                    'fric_5': fric_5,
                    'fric_15': fric_15,
                    'fric_30': fric_30,
                    'fric_60': fric_60,
                    'fric_eod': fric_eod,
                    'fric_next_open': fric_next_open,
                    # Net Points (Gross - Friction)
                    'net_5': gross_pts_5 - fric_5,
                    'net_15': gross_pts_15 - fric_15,
                    'net_30': gross_pts_30 - fric_30,
                    'net_60': gross_pts_60 - fric_60,
                    'net_eod': gross_pts_eod - fric_eod,
                    'net_next_open': (gross_pts_next_open - fric_next_open) if pd.notna(gross_pts_next_open) else np.nan,
                    # Spot Moves (Delta = 1.0 Naked Risk)
                    'spot_delta_30': sp_30 - spot_entry,
                    'spot_delta_eod': sp_eod - spot_entry,
                    'spot_delta_next_open': spot_next_open_delta
                })

    df_chp = pd.DataFrame(cheap_records)
    print(f"\nTotal Synthetic Cheap Events Audited: {len(df_chp):,} events across 5.4 years.")

    # -------------------------------------------------------------------------
    # 1. Performance Overview Table (2-Leg Leaner Structure)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 95)
    print(" 1. 2-LEG SYNTHETIC CONVERSION PERFORMANCE (LONG CALL + SHORT PUT, NO FUTURE)")
    print("=" * 95)

    horizons = ['5', '15', '30', '60', 'eod', 'next_open']
    h_labels = ['+5 min', '+15 min', '+30 min', '+60 min', 'Day Close (15:29)', 'Next-Day Open (09:30)']

    summary_rows = []
    for h, h_lbl in zip(horizons, h_labels):
        s_gross = df_chp[f'gross_{h}'].dropna()
        s_fric = df_chp[f'fric_{h}'].dropna()
        s_net = df_chp[f'net_{h}'].dropna()
        
        gross_mean = s_gross.mean()
        gross_med = s_gross.median()
        fric_mean = s_fric.mean()
        net_mean = s_net.mean()
        net_med = s_net.median()
        net_win_pct = (s_net > 0).mean() * 100.0
        gross_win_pct = (s_gross > 0).mean() * 100.0
        
        # Win/Loss Ratio
        avg_win = s_net[s_net > 0].mean() if (s_net > 0).sum() > 0 else 0
        avg_loss = s_net[s_net <= 0].mean() if (s_net <= 0).sum() > 0 else 0
        profit_factor = (s_net[s_net > 0].sum() / abs(s_net[s_net <= 0].sum())) if s_net[s_net <= 0].sum() != 0 else np.nan

        summary_rows.append({
            'Horizon': h_lbl,
            'Gross PnL (pts)': f"{gross_mean:+.2f} pts",
            '2-Leg Fric (pts)': f"{fric_mean:.2f} pts",
            'Net PnL (pts)': f"{net_mean:+.2f} pts",
            'Net INR / Lot': f"Rs. {net_mean * 50:+.0f}",
            'Gross Win%': f"{gross_win_pct:.1f}%",
            'Net Win% (>0)': f"{net_win_pct:.1f}%",
            'Profit Factor': f"{profit_factor:.2f}" if pd.notna(profit_factor) else "N/A"
        })

    print(pd.DataFrame(summary_rows).to_string(index=False))

    # -------------------------------------------------------------------------
    # 2. Multi-Year Regime Breakdown (Consistency Check)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 95)
    print(" 2. MULTI-YEAR REGIME BREAKDOWN: NET PNL & WIN RATE BY CALENDAR YEAR")
    print("=" * 95)

    year_rows = []
    for y in sorted(df_chp['year'].unique()):
        sub_y = df_chp[df_chp['year'] == y]
        n_y = len(sub_y)
        
        net_30 = sub_y['net_30'].mean()
        win_30 = (sub_y['net_30'] > 0).mean() * 100.0
        
        net_eod = sub_y['net_eod'].mean()
        win_eod = (sub_y['net_eod'] > 0).mean() * 100.0
        
        net_next = sub_y['net_next_open'].dropna().mean()
        win_next = (sub_y['net_next_open'].dropna() > 0).mean() * 100.0 if not sub_y['net_next_open'].dropna().empty else 0

        year_rows.append({
            'Year': y,
            'Events (N)': f"{n_y:,}",
            '+30m Net Pts': f"{net_30:+.2f} pts",
            '+30m Win%': f"{win_30:.1f}%",
            'EOD Net Pts': f"{net_eod:+.2f} pts",
            'EOD Win%': f"{win_eod:.1f}%",
            'Next-Open Net Pts': f"{net_next:+.2f} pts",
            'Next-Open Win%': f"{win_next:.1f}%"
        })

    print(pd.DataFrame(year_rows).to_string(index=False))

    # -------------------------------------------------------------------------
    # 3. Directional Spot Risk (The Naked Delta = 1.0 Reality)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 95)
    print(" 3. UNDERLYING SPOT VOLATILITY VS BASIS ALPHA EXPOSURE")
    print("=" * 95)
    
    spot_std_30 = df_chp['spot_delta_30'].std()
    spot_std_eod = df_chp['spot_delta_eod'].std()
    spot_std_next = df_chp['spot_delta_next_open'].dropna().std()
    
    net_pts_eod = df_chp['net_eod'].mean()
    net_std_eod = df_chp['net_eod'].std()

    print(f"Average Gross Basis Alpha Captured at EOD:           {df_chp['gross_eod'].mean():+.2f} pts")
    print(f"Standard Deviation of Spot Movement over Same EOD:   {spot_std_eod:.2f} pts")
    print(f"Standard Deviation of Overnight Spot Gap (Next Open): {spot_std_next:.2f} pts")
    print(f"Signal-to-Noise Ratio (Alpha / Spot Volatility):     {(df_chp['gross_eod'].mean() / max(1.0, spot_std_eod)):.2f}")

if __name__ == "__main__":
    main()
