"""
Cross-verify backtest option Entry/Exit prices against NSE F&O bhavcopy.

UPDATED VERSION - uses the new UDiFF Common Bhavcopy Final format directly
(NSE switched formats on 8 July 2024; jugaad-data's old downloader breaks
for any date after that).

WHAT THIS DOES
--------------
For every "Time_SquareOff" trade (exits at 15:00, i.e. day's close), this script:
  1. Downloads (and caches) the NSE F&O UDiFF bhavcopy for the Exit_Time date.
  2. Looks up the row matching the option symbol/strike/expiry/type.
  3. Compares the bhavcopy CLOSE price to the backtest's Exit_Price.
  4. Flags any mismatch beyond a tolerance.

For "StopLoss" trades, exact verification needs intraday data (not available
free). The script does a rough sanity check using the day's high/low range.

REQUIREMENTS
------------
pip install requests pandas

USAGE
-----
python verify_backtest.py /path/to/backtest_results_nifty.csv

NOTES
-----
- Bhavcopy URL format: 
  https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip
- This gives end-of-day OHLC + settlement price per contract — enough to
  check Time_SquareOff exits (15:00 close) but not intraday StopLoss triggers.
- Run on a machine with normal internet (NSE blocks many cloud/datacenter IPs).
- For dates with no trading (weekends/holidays), download will fail - this
  is expected and the script will report "could not download".
"""

import csv
import io
import os
import sys
import zipfile
from datetime import datetime, date

import requests
import pandas as pd

CACHE_DIR = "bhavcopy_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

TOLERANCE = 1.0  # rupees difference allowed before flagging

UDIFF_URL = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
}


def parse_dt(s):
    for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"time data {s!r} does not match any known format")


def parse_expiry(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"expiry data {s!r} does not match any known format")


def get_bhavcopy(d: date):
    """Download (or load cached) UDiFF F&O bhavcopy for date d. Returns DataFrame or None."""
    ymd = d.strftime("%Y%m%d")
    csv_name = f"BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv"
    cache_path = os.path.join(CACHE_DIR, csv_name)

    if os.path.exists(cache_path):
        try:
            return pd.read_csv(cache_path)
        except Exception as e:
            print(f"  [WARN] Could not read cached file {cache_path}: {e}")
            return None

    url = UDIFF_URL.format(ymd=ymd)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
    except Exception as e:
        print(f"  [WARN] Request failed for {d}: {e}")
        return None

    if r.status_code != 200:
        print(f"  [WARN] HTTP {r.status_code} for {d} (likely holiday/weekend or no data)")
        return None

    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        names = z.namelist()
        with z.open(names[0]) as f:
            df = pd.read_csv(f)
        # cache it
        df.to_csv(cache_path, index=False)
        return df
    except Exception as e:
        print(f"  [WARN] Could not unzip/parse bhavcopy for {d}: {e}")
        return None


def find_option_row(df: pd.DataFrame, strike, expiry: date, opt_type):
    """
    Find the row for NIFTY option with given strike, expiry, CE/PE.
    UDiFF format columns (typical): TckrSymb, FinInstrmTp, XpryDt, StrkPric,
    OptnTp, ClsPric, OpnPric, HghPric, LwPric, SttlmPric, ...
    """
    if df is None:
        return None

    cols_lower = {c.lower(): c for c in df.columns}

    sym_col = cols_lower.get("tckrsymb") or cols_lower.get("symbol")
    instr_col = cols_lower.get("fininstrmtp") or cols_lower.get("instrument")
    strike_col = cols_lower.get("strkpric") or cols_lower.get("strike_pr")
    expiry_col = cols_lower.get("xprydt") or cols_lower.get("expiry_dt")
    optype_col = cols_lower.get("optntp") or cols_lower.get("optntype") or cols_lower.get("option_typ")

    if not all([sym_col, strike_col, expiry_col, optype_col]):
        print("  [WARN] Could not identify required columns. Columns found:")
        print("   ", list(df.columns))
        return None

    sub = df[df[sym_col].astype(str).str.strip() == "NIFTY"]

    if instr_col:
        # Index options are typically 'OPTIDX' (sometimes 'IDO' in older formats)
        instr_vals = sub[instr_col].astype(str).str.strip().str.upper()
        if (instr_vals == "OPTIDX").any():
            sub = sub[instr_vals == "OPTIDX"]
        elif (instr_vals == "IDO").any():
            sub = sub[instr_vals == "IDO"]
        # else: don't filter on instrument type, rely on strike/expiry/optype

    def expiry_matches(val):
        val = str(val).strip()
        for fmt in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(val, fmt).date() == expiry
            except ValueError:
                continue
        return False

    sub = sub[sub[expiry_col].apply(expiry_matches)]
    sub = sub[sub[optype_col].astype(str).str.strip().str.upper() == opt_type.upper()]
    sub = sub[sub[strike_col].astype(float) == float(strike)]

    if len(sub) == 0:
        return None
    return sub.iloc[0]


def main(csv_path):
    trades = list(csv.DictReader(open(csv_path)))

    print(f"Loaded {len(trades)} trades from {csv_path}\n")

    time_squareoff = [t for t in trades if t["Exit_Reason"] == "Time_SquareOff"]
    stoploss = [t for t in trades if t["Exit_Reason"] == "StopLoss"]
    other = [t for t in trades if t["Exit_Reason"] not in ("Time_SquareOff", "StopLoss")]

    print(f"  Time_SquareOff trades: {len(time_squareoff)}")
    print(f"  StopLoss trades:       {len(stoploss)}")
    print(f"  Other:                 {len(other)} -> {set(t['Exit_Reason'] for t in other)}")
    print()

    # ---- Part 1: verify Time_SquareOff exit prices against EOD close ----
    print("=" * 70)
    print("PART 1: Time_SquareOff exits vs NSE bhavcopy CLOSE price")
    print("=" * 70)

    matches, mismatches, unresolved = 0, 0, 0

    for t in time_squareoff:
        exit_dt = parse_dt(t["Exit_Time"])
        expiry = parse_expiry(t["Expiry"])
        strike = t["Strike"]
        opt_type = t["Type"]
        claimed_exit = float(t["Exit_Price"])

        df = get_bhavcopy(exit_dt.date())
        row = find_option_row(df, strike, expiry, opt_type)

        if row is None:
            unresolved += 1
            print(f"[?] {t['Entry_Time']} | {t['Option_Symbol']} exp {t['Expiry']} "
                  f"-> bhavcopy row not found for {exit_dt.date()}")
            continue

        cols_lower = {c.lower(): c for c in df.columns}
        close_col = cols_lower.get("clspric") or cols_lower.get("close") or cols_lower.get("sttlmpric")
        real_close = float(row[close_col])

        diff = abs(real_close - claimed_exit)
        flag = "OK " if diff <= TOLERANCE else "MISMATCH"
        if diff <= TOLERANCE:
            matches += 1
        else:
            mismatches += 1

        print(f"[{flag}] {t['Option_Symbol']:<20} exp {t['Expiry']} "
              f"| backtest exit={claimed_exit:>8.2f} | bhavcopy close={real_close:>8.2f} "
              f"| diff={diff:>6.2f}")

    print()
    print(f"Summary: {matches} match, {mismatches} mismatch, {unresolved} unresolved (out of {len(time_squareoff)})")

    # ---- Part 2: StopLoss trades — print day range for manual review ----
    print()
    print("=" * 70)
    print("PART 2: StopLoss trades — EOD range for manual review")
    print("(Free data only gives day OHLC, not intraday timing of the SL hit)")
    print("=" * 70)

    plausible, suspicious, unresolved2 = 0, 0, 0

    for t in stoploss:
        exit_dt = parse_dt(t["Exit_Time"])
        expiry = parse_expiry(t["Expiry"])
        strike = t["Strike"]
        opt_type = t["Type"]
        claimed_sl = float(t["SL_Price"])
        claimed_exit = float(t["Exit_Price"])

        df_exit = get_bhavcopy(exit_dt.date())
        row_exit = find_option_row(df_exit, strike, expiry, opt_type)

        if row_exit is None:
            unresolved2 += 1
            print(f"[?] {t['Option_Symbol']:<20} exp {t['Expiry']} "
                  f"-> bhavcopy row not found for {exit_dt.date()}")
            continue

        cols_lower = {c.lower(): c for c in df_exit.columns}
        high_col = cols_lower.get("hghpric") or cols_lower.get("high")
        low_col = cols_lower.get("lwpric") or cols_lower.get("low")
        close_col = cols_lower.get("clspric") or cols_lower.get("close")

        day_high = float(row_exit[high_col])
        day_low = float(row_exit[low_col])
        day_close = float(row_exit[close_col])

        sl_in_range = day_low <= claimed_sl <= day_high
        flag = "PLAUSIBLE" if sl_in_range else "SUSPICIOUS"
        if sl_in_range:
            plausible += 1
        else:
            suspicious += 1

        print(f"[{flag}] {t['Option_Symbol']:<20} exp {t['Expiry']} | "
              f"claimed SL hit at {claimed_sl:>7.2f} | "
              f"exit_date day range [{day_low:.2f} - {day_high:.2f}], close={day_close:.2f} "
              f"| backtest exit_price={claimed_exit:.2f}")

    print()
    print(f"Summary: {plausible} plausible, {suspicious} suspicious, {unresolved2} unresolved (out of {len(stoploss)})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_backtest.py /path/to/backtest_results_nifty.csv")
        sys.exit(1)
    main(sys.argv[1])
