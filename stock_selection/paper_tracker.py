"""
==========================================================================================
        AUTOMATED PAPER-TRADING TRACKER & AUDIT ENGINE
==========================================================================================
Audits daily paper trades from paper_trade_log.csv against actual 1-minute spot candles,
computes net PnL (net of 15 bps friction), tracks stop-loss hits, and compares live paper
performance against the expected backtest distribution.
==========================================================================================
"""

import os
import sys
import glob
import re
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPOT_DIR = os.path.join(BASE_DIR, "backtest_data")
LOG_PATH = os.path.join(BASE_DIR, "stock_selection", "paper_trade_log.csv")
REPORT_PATH = os.path.join(BASE_DIR, "stock_selection", "paper_performance_summary.csv")
ROUND_TRIP_COST = 0.0015  # 15 bps friction

ISO_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date_to_iso(date_val):
    """
    Parses date string or timestamp to ISO %Y-%m-%d string.
    Tries ISO format first; falls back to dayfirst=True only if ISO parse fails.
    """
    if pd.isna(date_val) or str(date_val).strip() == "" or str(date_val).strip().lower() == "nan":
        return None
    s = str(date_val).strip()
    # Try ISO %Y-%m-%d first
    try:
        dt = pd.to_datetime(s, format="%Y-%m-%d", errors="raise")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    # Try ISO8601
    try:
        dt = pd.to_datetime(s, format="ISO8601", errors="raise")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    # Fallback with dayfirst=True for legacy DD/MM/YYYY
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="raise")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    # General fallback
    try:
        dt = pd.to_datetime(s, errors="raise")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        raise ValueError(f"Unable to parse date string into ISO format: '{s}'")


def migrate_log_file(filepath=LOG_PATH):
    """
    One-time migration step that normalizes all date columns in paper_trade_log.csv to ISO %Y-%m-%d format.
    """
    if not os.path.exists(filepath):
        return
    df = pd.read_csv(filepath)
    if df.empty:
        return

    modified = False
    for col in ["Selection_Date", "Execution_Date"]:
        if col in df.columns:
            for idx in range(len(df)):
                val = df.loc[idx, col]
                if pd.notna(val) and str(val).strip() != "" and str(val).strip().lower() != "nan":
                    iso_val = parse_date_to_iso(val)
                    if iso_val != str(val).strip():
                        df.loc[idx, col] = iso_val
                        modified = True
    if modified:
        df.to_csv(filepath, index=False)
        print(f"[MIGRATION] Migrated legacy dates in {filepath} to standard ISO %Y-%m-%d format.")


def validate_date_formats(df):
    """
    Lightweight assertion helper that fails loudly if any row's Selection_Date doesn't match YYYY-MM-DD.
    """
    for idx, row in df.iterrows():
        sel_date = str(row.get("Selection_Date", "")).strip()
        if sel_date and sel_date.lower() != "nan":
            if not ISO_DATE_REGEX.match(sel_date):
                raise AssertionError(
                    f"Date validation error: Row {idx} has invalid non-ISO Selection_Date: '{sel_date}'. Expected format: YYYY-MM-DD."
                )
        exec_date = str(row.get("Execution_Date", "")).strip()
        if exec_date and exec_date.lower() != "nan":
            if not ISO_DATE_REGEX.match(exec_date):
                raise AssertionError(
                    f"Date validation error: Row {idx} has invalid non-ISO Execution_Date: '{exec_date}'. Expected format: YYYY-MM-DD."
                )


def evaluate_paper_trades():
    print("=" * 120)
    print("          AUTOMATED PAPER-TRADING PERFORMANCE TRACKER & AUDIT")
    print("=" * 120)

    if not os.path.exists(LOG_PATH):
        print(f"[INFO] No paper trade log found at {LOG_PATH}. Run select_joint.py first.")
        return

    # Run migration on raw log file
    migrate_log_file(LOG_PATH)

    df_log = pd.read_csv(LOG_PATH)
    if df_log.empty:
        print("[INFO] Paper trade log is empty.")
        return

    print(f"[INFO] Found {len(df_log)} total logged paper recommendations.")

    updated_rows = []

    for idx, row in df_log.iterrows():
        sym = str(row["Symbol"]).strip().upper()
        sel_date_raw = row["Selection_Date"]
        sel_date_iso = parse_date_to_iso(sel_date_raw)
        direction = str(row["Direction"]).strip().upper()
        alloc = float(row["Allocation_Pct"])
        
        spot_file = os.path.join(SPOT_DIR, f"{sym.lower()}_spot.csv")
        if not os.path.exists(spot_file):
            r_dict = row.to_dict()
            r_dict["Selection_Date"] = sel_date_iso
            updated_rows.append(r_dict)
            continue

        try:
            df_spot = pd.read_csv(spot_file)
            col_name = 'timestamp' if 'timestamp' in df_spot.columns else ('start_time' if 'start_time' in df_spot.columns else df_spot.columns[0])
            df_spot['dt'] = pd.to_datetime(df_spot[col_name], errors='coerce')
            df_spot = df_spot.dropna(subset=['dt']).sort_values(by='dt')
            df_spot['date_only'] = df_spot['dt'].dt.normalize()

            sel_dt = pd.to_datetime(sel_date_iso).normalize()

            # Find next trading date after selection date using datetime objects
            available_dates = sorted(df_spot[df_spot['date_only'] > sel_dt]['date_only'].unique())
            if not available_dates:
                # Trading session hasn't occurred yet
                r_dict = row.to_dict()
                r_dict["Selection_Date"] = sel_date_iso
                status = row.get("Status", "PENDING_EXECUTION")
                r_dict["Status"] = status if "PENDING" in str(status) else "PENDING_EXECUTION"
                updated_rows.append(r_dict)
                continue

            exec_date_dt = available_dates[0]
            exec_date_str = pd.to_datetime(exec_date_dt).strftime("%Y-%m-%d")
            day_candles = df_spot[df_spot['date_only'] == exec_date_dt].sort_values(by='dt')

            if len(day_candles) < 30:
                r_dict = row.to_dict()
                r_dict["Selection_Date"] = sel_date_iso
                r_dict["Status"] = "INCOMPLETE_DATA"
                updated_rows.append(r_dict)
                continue

            entry_open = float(day_candles["open"].iloc[0])
            exit_close = float(day_candles["close"].iloc[-1])
            day_high = float(day_candles["high"].max())
            atr = float(row.get("ATR_14", entry_open * 0.03))
            sl_price = entry_open + 2.0 * atr if direction == "SHORT" else entry_open - 2.0 * atr

            # Check if 2.0xATR stop was triggered intraday
            stopped_out = False
            actual_exit = exit_close

            for _, c in day_candles.iterrows():
                if direction == "SHORT" and c["high"] >= sl_price:
                    actual_exit = sl_price
                    stopped_out = True
                    break
                elif direction == "LONG" and c["low"] <= sl_price:
                    actual_exit = sl_price
                    stopped_out = True
                    break

            raw_pnl = ((entry_open - actual_exit) / entry_open) if direction == "SHORT" else ((actual_exit - entry_open) / entry_open)
            net_pnl = raw_pnl - ROUND_TRIP_COST

            r_dict = row.to_dict()
            r_dict["Selection_Date"] = sel_date_iso
            r_dict["Execution_Date"] = exec_date_str
            r_dict["Entry_Price"] = round(entry_open, 2)
            r_dict["Exit_Price"] = round(actual_exit, 2)
            r_dict["Stopped_Out"] = stopped_out
            r_dict["Net_PnL_%"] = round(net_pnl * 100, 2)
            r_dict["Weighted_PnL_%"] = round(net_pnl * (alloc / 100.0) * 100, 3)
            r_dict["Status"] = "EXECUTED"
            updated_rows.append(r_dict)

        except Exception as e:
            r_dict = row.to_dict()
            r_dict["Selection_Date"] = sel_date_iso
            r_dict["Status"] = f"ERROR: {e}"
            updated_rows.append(r_dict)

    df_updated = pd.DataFrame(updated_rows)

    # Validate all date formats strictly before saving
    validate_date_formats(df_updated)

    df_updated.to_csv(LOG_PATH, index=False)

    # Summary Report
    executed = df_updated[df_updated["Status"] == "EXECUTED"]
    if not executed.empty:
        pnl_vals = executed["Net_PnL_%"].values
        win_rate = (pnl_vals > 0).mean() * 100
        mean_pnl = np.mean(pnl_vals)
        mean_weighted = np.mean(executed["Weighted_PnL_%"].values)
        
        print("\n" + "=" * 120)
        print("                  PAPER TRADING PERFORMANCE SUMMARY REPORT")
        print("=" * 120)
        print(f"Total Executed Paper Trades:   {len(executed)}")
        print(f"Trade Win Rate:                {win_rate:.1f}%  (Backtest Target: ~61.5%)")
        print(f"Mean Trade Net Return:         {mean_pnl:+0.2f}%  (Backtest Target: ~+0.70%)")
        print(f"Mean Portfolio Daily Return:   {mean_weighted:+0.3f}%  (at {executed['Allocation_Pct'].iloc[0]}% per stock)")
        print(f"Total Stop-Loss Hits:          {executed['Stopped_Out'].sum()} out of {len(executed)} ({executed['Stopped_Out'].mean()*100:.1f}%)")
        print("=" * 120)
        print(executed[["Selection_Date", "Execution_Date", "Symbol", "Direction", "Entry_Price", "Exit_Price", "Stopped_Out", "Net_PnL_%", "Weighted_PnL_%"]].tail(15).to_string(index=False))
        print("=" * 120 + "\n")


if __name__ == "__main__":
    evaluate_paper_trades()
