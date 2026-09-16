"""
Phase 1: Volume Distribution Analysis for NIFTY ATM+-3 (14 series total: 7 CE + 7 PE)
Analyzes 1-minute historical option candles across 2021-2026.
"""
import os
import glob
import pandas as pd
import numpy as np
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_HIST_DIR = os.path.join(BASE_DIR, "backtest_data", "Nifty_option_historical", "Week_1min")

TARGET_LABELS = ['ATM-3', 'ATM-2', 'ATM-1', 'ATM', 'ATM+1', 'ATM+2', 'ATM+3']

def main():
    print("=" * 90)
    print(" PHASE 1: NIFTY ATM+-3 1-MINUTE OPTION VOLUME DISTRIBUTION AUDIT (2021-2026)")
    print("=" * 90)

    csv_files = sorted(glob.glob(os.path.join(OPT_HIST_DIR, "*", "*.csv")))
    print(f"Found {len(csv_files)} daily session CSVs across all years.")

    volumes_all = []
    volumes_ce = []
    volumes_pe = []
    
    # Event tracking for 1,000,000 threshold
    events_1m = []
    
    # Count total candles per group
    total_candles = 0
    yearly_counts = defaultdict(int)
    yearly_1m_events = defaultdict(int)
    label_1m_events = defaultdict(lambda: defaultdict(int)) # label -> opt_type -> count
    label_total_counts = defaultdict(int)

    # Process in batches or file by file
    for idx, fpath in enumerate(csv_files):
        if (idx + 1) % 250 == 0 or idx == len(csv_files) - 1:
            print(f"  Processed {idx + 1}/{len(csv_files)} files...")
            
        fname = os.path.basename(fpath)
        date_str = fname.replace("NIFTY_", "").replace("_1m.csv", "")
        year = date_str.split("-")[0]
        
        try:
            df = pd.read_csv(fpath)
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            continue
            
        df.drop_duplicates(subset=['datetime', 'strike_label', 'option_type'], inplace=True)
        
        # Filter to ATM+-3
        mask = df['strike_label'].isin(TARGET_LABELS)
        df_sub = df[mask].copy()
        if df_sub.empty:
            continue
            
        # Normalize option_type to CE / PE
        df_sub['opt_type'] = df_sub['option_type'].map({'CALL': 'CE', 'PUT': 'PE'}).fillna(df_sub['option_type'])
        
        vols = df_sub['volume'].to_numpy()
        volumes_all.extend(vols)
        
        ce_vols = df_sub[df_sub['opt_type'] == 'CE']['volume'].to_numpy()
        pe_vols = df_sub[df_sub['opt_type'] == 'PE']['volume'].to_numpy()
        volumes_ce.extend(ce_vols)
        volumes_pe.extend(pe_vols)
        
        total_candles += len(df_sub)
        yearly_counts[year] += len(df_sub)
        
        for lbl in TARGET_LABELS:
            cnt = (df_sub['strike_label'] == lbl).sum()
            label_total_counts[lbl] += cnt
            
        # Check > 1,000,000 volume events
        spikes = df_sub[df_sub['volume'] >= 1_000_000]
        if not spikes.empty:
            for _, r in spikes.iterrows():
                yearly_1m_events[year] += 1
                label_1m_events[r['strike_label']][r['opt_type']] += 1
                events_1m.append({
                    'datetime': r['datetime'],
                    'strike_label': r['strike_label'],
                    'opt_type': r['opt_type'],
                    'strike_price': r['strike_price'],
                    'spot': r['spot'],
                    'open': r['open'],
                    'high': r['high'],
                    'low': r['low'],
                    'close': r['close'],
                    'volume': r['volume'],
                    'oi': r.get('oi', 0)
                })

    v_all = np.array(volumes_all, dtype=np.float64)
    v_ce = np.array(volumes_ce, dtype=np.float64)
    v_pe = np.array(volumes_pe, dtype=np.float64)

    print("\n" + "=" * 90)
    print("                       1. OVERALL VOLUME PERCENTILES")
    print("=" * 90)
    
    percentiles = [50, 90, 95, 99, 99.5, 99.9, 99.99, 100]
    p_all = np.percentile(v_all, percentiles)
    p_ce = np.percentile(v_ce, percentiles)
    p_pe = np.percentile(v_pe, percentiles)
    
    df_pct = pd.DataFrame({
        'Percentile': ['50th (Median)', '90th', '95th', '99th', '99.5th', '99.9th', '99.99th', 'Max (100th)'],
        'Combined (ATM+-3)': [f"{int(x):,}" for x in p_all],
        'CE (Calls)': [f"{int(x):,}" for x in p_ce],
        'PE (Puts)': [f"{int(x):,}" for x in p_pe]
    })
    print(df_pct.to_string(index=False))

    print("\n" + "=" * 90)
    print("            2. VOLUME >= 1,000,000 CANDLE EVENTS SUMMARY")
    print("=" * 90)
    total_1m = len(events_1m)
    pct_1m = (total_1m / total_candles) * 100.0 if total_candles > 0 else 0
    print(f"Total ATM+-3 1-Min Candles Audited: {total_candles:,}")
    print(f"Total Candles with Volume >= 1,000,000: {total_1m:,} ({pct_1m:.4f}% of all candles, ~1 in every {int(total_candles/max(1, total_1m)):,} candles)")

    print("\n--- Breakdown by Year ---")
    df_year = pd.DataFrame([
        {
            'Year': y,
            'Total Candles': f"{yearly_counts[y]:,}",
            'Events >= 1M': yearly_1m_events[y],
            '% of Year Candles': f"{(yearly_1m_events[y]/max(1, yearly_counts[y]))*100:.4f}%"
        }
        for y in sorted(yearly_counts.keys())
    ])
    print(df_year.to_string(index=False))

    print("\n--- Breakdown by Relative Strike & Option Type (>= 1M Volume) ---")
    strike_order = ['ATM-3', 'ATM-2', 'ATM-1', 'ATM', 'ATM+1', 'ATM+2', 'ATM+3']
    strike_records = []
    for lbl in strike_order:
        ce_cnt = label_1m_events[lbl]['CE']
        pe_cnt = label_1m_events[lbl]['PE']
        tot = ce_cnt + pe_cnt
        strike_records.append({
            'Strike Label': lbl,
            'CE Spikes': ce_cnt,
            'PE Spikes': pe_cnt,
            'Total Spikes': tot,
            '% of 1M Spikes': f"{(tot/max(1, total_1m))*100:.2f}%"
        })
    df_strikes = pd.DataFrame(strike_records)
    print(df_strikes.to_string(index=False))

    print("\n" + "=" * 90)
    print("          3. ALTERNATIVE CANDIDATE THRESHOLDS & EVENT COUNTS")
    print("=" * 90)
    
    # Test candidate thresholds: 95th, 99th, 99.5th, 99.9th, 100k, 250k, 500k, 1M
    threshold_candidates = [
        ("95.0th Percentile", float(np.percentile(v_all, 95.0))),
        ("99.0th Percentile", float(np.percentile(v_all, 99.0))),
        ("99.5th Percentile", float(np.percentile(v_all, 99.5))),
        ("99.9th Percentile", float(np.percentile(v_all, 99.9))),
        ("Fixed 100,000", 100_000.0),
        ("Fixed 250,000", 250_000.0),
        ("Fixed 500,000", 500_000.0),
        ("Fixed 1,000,000", 1_000_000.0)
    ]
    
    alt_records = []
    for name, th in threshold_candidates:
        cnt = int((v_all >= th).sum())
        pct = (cnt / total_candles) * 100.0
        avg_per_day = cnt / max(1, len(csv_files))
        alt_records.append({
            'Threshold Name': name,
            'Volume Cutoff': f"{int(th):,}",
            'Total Events': f"{cnt:,}",
            '% of Total Candles': f"{pct:.4f}%",
            'Avg Events / Trading Day': f"{avg_per_day:.2f}"
        })
    df_alt = pd.DataFrame(alt_records)
    print(df_alt.to_string(index=False))

if __name__ == "__main__":
    main()
