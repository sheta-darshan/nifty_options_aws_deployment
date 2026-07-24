"""
set_starting_settings.py
=========================
Programmatically sets mathematically sound starting point-based exit parameters
for stock options in instruments.json based on their spot close prices.

ATM premium is estimated as 3.0% of the underlying stock price.
- Stop Loss: 30% of ATM premium (~0.9% of stock price)
- Target: 60% of ATM premium (~1.8% of stock price)
- Trailing Stop: 0.0 (disabled by default for stock options to prevent noise exits)
"""
import os
import json
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "instruments.json")
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")

def get_recent_close(symbol):
    spot_file = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
    if not os.path.exists(spot_file):
        return None
    try:
        # Load only the close column (or fallback to column 4 if close doesn't exist)
        # to remain extremely fast and memory efficient
        df_temp = pd.read_csv(spot_file, nrows=5)
        col_close = 'close' if 'close' in df_temp.columns else ('close' if 'CLOSE' in [c.upper() for c in df_temp.columns] else df_temp.columns[4])
        
        df_all = pd.read_csv(spot_file, usecols=[col_close])
        return float(df_all[col_close].iloc[-1])
    except Exception as e:
        print(f"[WARNING] Could not read close price for {symbol}: {e}")
        return None

def snap_tick(val):
    # Round to nearest 0.5 for small numbers (< 10), otherwise nearest integer
    if val < 10:
        return round(float(val) * 2.0) / 2.0
    else:
        return float(round(val))

def main():
    if not os.path.exists(JSON_PATH):
        print(f"[ERROR] instruments.json not found at {JSON_PATH}!")
        return

    with open(JSON_PATH, "r") as f:
        instruments = json.load(f)

    updated_count = 0
    print("\n[INFO] Auto-calculating starting POINTS settings based on underlying spot prices:")
    print("=" * 90)
    print(f"  {'Symbol':<12} | {'Spot Close':<10} | {'ATM Premium':<12} | {'SL (Points)':<12} | {'Target (Points)':<15}")
    print("-" * 90)

    for sym, config in instruments.items():
        # Only process STOCKS or OPTIONS with STOCK underlyings
        is_stock = config.get("type") == "STOCK"
        is_index = config.get("type") == "INDEX"
        
        if is_index:
            # Set index standard defaults
            if sym == "NIFTY":
                config["exit_mode"] = "POINTS"
                config["points_sl_buy"] = 30
                config["points_target_buy"] = 40
                config["points_trail_buy"] = 0
                config["points_sl_sell"] = 30
                config["points_target_sell"] = 100
                config["points_trail_sell"] = 10
            elif sym == "BANKNIFTY":
                config["exit_mode"] = "POINTS"
                config["points_sl_buy"] = 60
                config["points_target_buy"] = 90
                config["points_trail_buy"] = 0
                config["points_sl_sell"] = 60
                config["points_target_sell"] = 180
                config["points_trail_sell"] = 20
            updated_count += 1
            continue

        if not is_stock:
            continue

        close_price = get_recent_close(sym)
        if close_price is None:
            # Fallback estimation if spot file is missing
            close_price = 500.0 # moderate default close price
            print(f"  {sym:<12} | Missing Spot File! Using fallback Rs.{close_price:.0f}")

        # ATM Option premium estimation: ~3.0% of stock price
        atm_premium = close_price * 0.03
        
        # Stop loss: 30% of ATM premium (~0.9% of spot close)
        sl_points = snap_tick(atm_premium * 0.3)
        # Target: 60% of ATM premium (~1.8% of spot close) - 1:2 Risk Reward ratio
        tp_points = snap_tick(atm_premium * 0.6)
        
        # Ensure a minimum floor for points settings
        sl_points = max(0.5, sl_points)
        tp_points = max(1.0, tp_points)

        # Update JSON configuration
        config["exit_mode"] = "POINTS"
        config["points_sl_buy"] = sl_points
        config["points_target_buy"] = tp_points
        config["points_trail_buy"] = 0.0  # Keep trailing stop off by default to avoid whipsaw losses
        
        config["points_sl_sell"] = sl_points
        config["points_target_sell"] = tp_points
        config["points_trail_sell"] = 0.0
        
        print(f"  {sym:<12} | Rs.{close_price:<7.2f} | Rs.{atm_premium:<9.2f} | {sl_points:<12.1f} | {tp_points:<15.1f}")
        updated_count += 1

    print("=" * 90)
    
    # Save the updated configurations back to instruments.json
    with open(JSON_PATH, "w") as f:
        json.dump(instruments, f, indent=4)
        
    print(f"\n[SUCCESS] Updated {updated_count} instruments with starting exit settings in instruments.json!\n")

if __name__ == "__main__":
    main()
