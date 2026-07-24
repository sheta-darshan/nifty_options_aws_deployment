"""
verify_data.py - Quick data verification tool
==============================================
Cross-checks your downloaded backtest data for consistency.

Usage:
    python verify_data.py                   -> Verify NIFTY (5 random dates)
    python verify_data.py 2024-01-15        -> Verify specific date
    python verify_data.py SENSEX            -> Verify SENSEX data
"""
import os
import sys
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")


def verify_instrument(instrument="nifty", specific_date=None):
    prefix = instrument.lower()
    spot_file = os.path.join(DATA_DIR, f"{prefix}_spot.csv")
    ce_file = os.path.join(DATA_DIR, f"{prefix}_atm_ce.csv")
    pe_file = os.path.join(DATA_DIR, f"{prefix}_atm_pe.csv")

    for f, label in [(spot_file, "Spot"), (ce_file, "CE"), (pe_file, "PE")]:
        if not os.path.exists(f):
            print(f"[ERROR] {label} file not found: {f}")
            return

    print(f"\n{'='*60}")
    print(f"  DATA VERIFICATION: {instrument.upper()}")
    print(f"{'='*60}")

    spot = pd.read_csv(spot_file, index_col='timestamp', parse_dates=True)
    ce = pd.read_csv(ce_file, index_col='timestamp', parse_dates=True)
    pe = pd.read_csv(pe_file, index_col='timestamp', parse_dates=True)

    print(f"\n  OVERALL STATS:")
    print(f"  {'File':<15} {'Rows':>10} {'Start':>12} {'End':>12} {'NaN%':>6}")
    print(f"  {'-'*55}")
    for name, df in [("Spot", spot), ("ATM CE", ce), ("ATM PE", pe)]:
        nan_pct = df.isnull().any(axis=1).mean() * 100
        print(f"  {name:<15} {len(df):>10,} {str(df.index.min().date()):>12} {str(df.index.max().date()):>12} {nan_pct:>5.1f}%")

    # Pick dates to verify
    all_dates = sorted(np.unique(spot.index.date.astype(str)))
    if specific_date:
        dates_to_check = [specific_date]
    else:
        # Pick 5 evenly spaced dates
        indices = np.linspace(0, len(all_dates) - 1, 5, dtype=int)
        dates_to_check = [all_dates[i] for i in indices]

    print(f"\n  DETAILED CHECK ({len(dates_to_check)} dates):")
    print(f"  {'Date':<12} {'Spot Candles':>12} {'CE Candles':>10} {'PE Candles':>10} {'Aligned':>8} {'Spot Range':>20} {'CE Range':>16} {'PE Range':>16}")
    print(f"  {'-'*110}")

    issues = []
    for d in dates_to_check:
        s = spot[spot.index.date.astype(str) == d]
        c = ce[ce.index.date.astype(str) == d]
        p = pe[pe.index.date.astype(str) == d]

        common = s.index.intersection(c.index).intersection(p.index)

        spot_range = f"{s['close'].min():.1f}-{s['close'].max():.1f}" if not s.empty else "N/A"
        ce_range = f"{c['close'].min():.1f}-{c['close'].max():.1f}" if not c.empty else "N/A"
        pe_range = f"{p['close'].min():.1f}-{p['close'].max():.1f}" if not p.empty else "N/A"

        align_pct = f"{len(common)/max(len(s),1)*100:.0f}%" if not s.empty else "N/A"

        print(f"  {d:<12} {len(s):>12} {len(c):>10} {len(p):>10} {align_pct:>8} {spot_range:>20} {ce_range:>16} {pe_range:>16}")

        # Flag issues
        if len(s) < 300 and len(s) > 0:
            issues.append(f"  {d}: Only {len(s)} spot candles (expected ~375)")
        if not s.empty and not c.empty and len(common) / len(s) < 0.8:
            issues.append(f"  {d}: Low alignment ({align_pct}) between spot and options")
        if not c.empty and c['close'].min() <= 0:
            issues.append(f"  {d}: CE has zero/negative prices!")
        if not p.empty and p['close'].min() <= 0:
            issues.append(f"  {d}: PE has zero/negative prices!")

    if issues:
        print(f"\n  [!] ISSUES FOUND:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print(f"\n  [OK] All checks passed!")

    # Price sanity check
    print(f"\n  PRICE SANITY CHECK:")
    print(f"  Spot Close Range: {spot['close'].min():.2f} - {spot['close'].max():.2f}")
    if not ce.empty:
        print(f"  CE Close Range:   {ce['close'].min():.2f} - {ce['close'].max():.2f}")
    if not pe.empty:
        print(f"  PE Close Range:   {pe['close'].min():.2f} - {pe['close'].max():.2f}")

    # Check for gaps (missing trading days)
    trading_days = sorted(set(spot.index.date))
    gaps = []
    for i in range(1, len(trading_days)):
        diff = (trading_days[i] - trading_days[i-1]).days
        if diff > 4:  # More than a long weekend
            gaps.append(f"{trading_days[i-1]} -> {trading_days[i]} ({diff} days)")

    if gaps:
        print(f"\n  [!] DATA GAPS (>4 days between trading days):")
        for g in gaps[:10]:
            print(f"    {g}")
    else:
        print(f"\n  [OK] No significant data gaps found")

    print(f"\n  Total trading days: {len(trading_days)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    args = sys.argv[1:]

    instrument = "nifty"
    specific_date = None

    for arg in args:
        if '-' in arg and len(arg) == 10:  # Looks like a date
            specific_date = arg
        else:
            instrument = arg

    verify_instrument(instrument, specific_date)
