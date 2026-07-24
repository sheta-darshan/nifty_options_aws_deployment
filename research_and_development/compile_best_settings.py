"""
compile_best_settings.py - Compile Optimized Risk Parameters
============================================================
Parses the output of optimize_buy_sell_modes.py (best parameters for buying and selling per instrument),
updates instruments_config.csv with the optimized parameters, ranks them by Combined Robustness,
and writes them back so they can be immediately synced to instruments.json using update_instruments_from_csv.py.
"""
import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "optimization_results")
CSV_PATH = os.path.join(BASE_DIR, "instruments_config.csv")

def main():
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] Could not find baseline config at {CSV_PATH}!")
        return

    print(f"[INFO] Loading baseline instruments config from {CSV_PATH}...")
    df_config = pd.read_csv(CSV_PATH)

    # Initialize diagnostic tracking columns
    metrics = {
        'Buy_PnL': 0.0, 'Buy_WinRate': 0.0, 'Buy_PF': 0.0, 'Buy_Robustness': 0.0,
        'Sell_PnL': 0.0, 'Sell_WinRate': 0.0, 'Sell_PF': 0.0, 'Sell_Robustness': 0.0,
        'Combined_Robustness': 0.0
    }
    for m in metrics:
        df_config[m] = 0.0

    updated_buy_count = 0
    updated_sell_count = 0

    print("[INFO] Scanning optimization results and matching with config...")
    for idx, row in df_config.iterrows():
        inst_name = str(row['Instrument']).strip().upper()
        inst_lower = inst_name.lower()

        # Files to check
        buy_file = os.path.join(RESULTS_DIR, f"optimized_buying_{inst_lower}.csv")
        sell_file = os.path.join(RESULTS_DIR, f"optimized_selling_{inst_lower}.csv")

        # 1. Update Option Buying Params
        if os.path.exists(buy_file):
            try:
                df_buy = pd.read_csv(buy_file)
                if not df_buy.empty:
                    best_buy = df_buy.iloc[0]
                    # Update config columns
                    df_config.at[idx, 'sl_mult_buy'] = float(best_buy['SL_Mult'])
                    df_config.at[idx, 'trailing_mult_buy'] = float(best_buy['Trail_Mult'])
                    df_config.at[idx, 'tp_mult_buy'] = float(best_buy['ATR_TP_Mult'])

                    # Set diagnostic metrics
                    df_config.at[idx, 'Buy_PnL'] = float(best_buy['Net_PnL'])
                    df_config.at[idx, 'Buy_WinRate'] = float(best_buy['Win_Rate'])
                    df_config.at[idx, 'Buy_PF'] = float(best_buy['Profit_Factor'])
                    df_config.at[idx, 'Buy_Robustness'] = float(best_buy['Robustness_Score'])
                    updated_buy_count += 1
            except Exception as e:
                print(f"  [WARNING] Error reading {buy_file}: {e}")

        # 2. Update Option Selling Params
        if os.path.exists(sell_file):
            try:
                df_sell = pd.read_csv(sell_file)
                if not df_sell.empty:
                    best_sell = df_sell.iloc[0]
                    # Update config columns
                    df_config.at[idx, 'sl_mult_sell'] = float(best_sell['SL_Mult'])
                    df_config.at[idx, 'trailing_mult_sell'] = float(best_sell['Trail_Mult'])
                    df_config.at[idx, 'tp_mult_sell'] = float(best_sell['ATR_TP_Mult'])

                    # Set diagnostic metrics
                    df_config.at[idx, 'Sell_PnL'] = float(best_sell['Net_PnL'])
                    df_config.at[idx, 'Sell_WinRate'] = float(best_sell['Win_Rate'])
                    df_config.at[idx, 'Sell_PF'] = float(best_sell['Profit_Factor'])
                    df_config.at[idx, 'Sell_Robustness'] = float(best_sell['Robustness_Score'])
                    updated_sell_count += 1
            except Exception as e:
                print(f"  [WARNING] Error reading {sell_file}: {e}")

        # Compute Combined Robustness
        df_config.at[idx, 'Combined_Robustness'] = (
            df_config.at[idx, 'Buy_Robustness'] + df_config.at[idx, 'Sell_Robustness']
        )

    # Sort from best to worst by Combined Robustness
    df_sorted = df_config.sort_values(by='Combined_Robustness', ascending=False)

    # Save sorted updated CSV back to workspace
    df_sorted.to_csv(CSV_PATH, index=False)
    print(f"\n[SUCCESS] Compiled configurations saved back to {CSV_PATH}!")
    print(f"  - Updated Buying parameters for {updated_buy_count} instruments")
    print(f"  - Updated Selling parameters for {updated_sell_count} instruments")

    # Display Top 15 Instruments Report
    print("\n" + "=" * 115)
    print(f"  TOP 15 INSTRUMENTS BY COMBINED ROBUSTNESS SCORE")
    print("=" * 115)
    print(f"  {'Instrument':<12} | {'Buy SL/Tr/TP':<12} | {'Buy PnL':<10} | {'Buy Score':<9} | "
          f"{'Sell SL/Tr/TP':<12} | {'Sell PnL':<10} | {'Sell Score':<10} | {'Comb Score':<10}")
    print("-" * 115)

    for _, r in df_sorted.head(15).iterrows():
        buy_str = f"{r['sl_mult_buy']:.1f}/{r['trailing_mult_buy']:.1f}/{r['tp_mult_buy']:.1f}"
        sell_str = f"{r['sl_mult_sell']:.1f}/{r['trailing_mult_sell']:.1f}/{r['tp_mult_sell']:.1f}"
        print(f"  {r['Instrument']:<12} | {buy_str:<12} | Rs.{r['Buy_PnL']:<7.0f} | {r['Buy_Robustness']:<9.1f} | "
              f"{sell_str:<12} | Rs.{r['Sell_PnL']:<7.0f} | {r['Sell_Robustness']:<10.1f} | {r['Combined_Robustness']:<10.1f}")
    print("=" * 115)
    print(f"\n[INFO] You can now update instruments.json by running:")
    print(f"    ..\\.venv\\Scripts\\python.exe update_instruments_from_csv.py instruments_config.csv\n")

if __name__ == "__main__":
    main()
