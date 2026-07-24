import os
import sys
import json
import csv
import pandas as pd
import numpy as np
from multiprocessing import Pool, cpu_count
from dotenv import load_dotenv

# Setup project root pathing and load environment variables first
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

from backtest_engine import SimulationEngine
from strategies import BacktestConfig

DATA_DIR = os.path.join(BASE_DIR, "backtest_data")

def run_backtest_for_stock(symbol):
    """Run 5-year offline backtest for a single stock using Strategy 3 (Triple Momentum) in STOCK mode."""
    try:
        # Setup config with Strategy 3 enabled
        config = BacktestConfig()
        for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]:
            setattr(config, f"ENABLE_STRATEGY_{i}", False)
        config.ENABLE_STRATEGY_3 = True
        config.apply_strategy_defaults("Strategy_3")
        
        # Instantiate SimulationEngine for the target symbol
        engine = SimulationEngine(
            config, 
            instrument_name=symbol, 
            offline_mode=True, 
            backtest_days=1825  # 5 years
        )
        
        # FORCE execution mode to STOCK (run on spot prices)
        engine.inst_config["execution_mode"] = "STOCK"
        
        # Load spot data and calculate indicators/signals
        engine.load_data()
        
        # Run simulation
        trades_df = engine.run(write_to_csv=False)
        
        if trades_df is not None and not trades_df.empty:
            total_trades = len(trades_df)
            win_rate = (len(trades_df[trades_df['PnL'] > 0]) / total_trades) * 100
            gross_pnl = trades_df['Gross_PnL'].sum()
            charges = trades_df['Charges'].sum()
            net_pnl = trades_df['PnL'].sum()
            
            gross_profit = trades_df[trades_df['PnL'] > 0]['PnL'].sum()
            gross_loss = abs(trades_df[trades_df['PnL'] < 0]['PnL'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
            
            avg_pnl = net_pnl / total_trades
            max_win = trades_df['PnL'].max()
            max_loss = trades_df['PnL'].min()
            
            # Calculate Drawdown
            arr_pnl = np.array(trades_df['PnL'].tolist())
            cum_pnl = np.cumsum(arr_pnl)
            peaks_pnl = np.maximum.accumulate(cum_pnl)
            drawdowns_pnl = peaks_pnl - cum_pnl
            max_dd_pnl = np.max(drawdowns_pnl) if len(drawdowns_pnl) > 0 else 0.0
            
            # Robustness Score (Option A): Net PnL / Max Drawdown, adjusted for low trade counts
            robustness_score = 0.0
            if max_dd_pnl > 0:
                robustness_score = net_pnl / max_dd_pnl
            else:
                robustness_score = net_pnl if net_pnl > 0 else 0.0
                
            # Penalize low trade count (e.g. fewer than 30 trades)
            if total_trades < 30:
                robustness_score *= (total_trades / 30.0)
                
            return {
                "Instrument": symbol,
                "Trades": total_trades,
                "Win Rate (%)": round(win_rate, 1),
                "Profit Factor": round(profit_factor, 2) if profit_factor != np.inf else 999.0,
                "Gross PnL (Rs.)": round(gross_pnl, 2),
                "Charges (Rs.)": round(charges, 2),
                "Net PnL (Rs.)": round(net_pnl, 2),
                "Avg PnL/Trade": round(avg_pnl, 2),
                "Max Win": round(max_win, 2),
                "Max Loss": round(max_loss, 2),
                "Max Drawdown (Rs.)": round(max_dd_pnl, 2),
                "Robustness Score": round(robustness_score, 3)
            }
        else:
            return {
                "Instrument": symbol,
                "Trades": 0,
                "Win Rate (%)": 0.0,
                "Profit Factor": 0.0,
                "Gross PnL (Rs.)": 0.0,
                "Charges (Rs.)": 0.0,
                "Net PnL (Rs.)": 0.0,
                "Avg PnL/Trade": 0.0,
                "Max Win": 0.0,
                "Max Loss": 0.0,
                "Max Drawdown (Rs.)": 0.0,
                "Robustness Score": 0.0
            }
    except Exception as e:
        return {
            "Instrument": symbol,
            "Trades": 0,
            "Win Rate (%)": 0.0,
            "Profit Factor": 0.0,
            "Gross PnL (Rs.)": 0.0,
            "Charges (Rs.)": 0.0,
            "Net PnL (Rs.)": 0.0,
            "Avg PnL/Trade": 0.0,
            "Max Win": 0.0,
            "Max Loss": 0.0,
            "Max Drawdown (Rs.)": 0.0,
            "Robustness Score": 0.0,
            "Error": str(e)
        }

def main():
    print("=" * 80)
    print("        STRATEGY 3 (TRIPLE MOMENTUM) STOCK PERFORMANCE RANKING ENGINE       ")
    print("=" * 80)
    
    # 1. Load instruments.json
    inst_file = os.path.join(BASE_DIR, "instruments.json")
    if not os.path.exists(inst_file):
        print(f"[ERROR] Could not find instruments.json at: {inst_file}")
        return
        
    try:
        with open(inst_file, "r") as f:
            instruments = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse instruments.json: {e}")
        return
        
    # 2. Extract Stock symbols with available historical spot data files
    stock_symbols = []
    for symbol, cfg in instruments.items():
        if cfg.get("type") == "STOCK":
            spot_path = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
            if os.path.exists(spot_path):
                stock_symbols.append(symbol)
                
    total_symbols = len(stock_symbols)
    print(f"[INFO] Found {total_symbols} stocks in instruments.json with valid spot data in backtest_data/.")
    if total_symbols == 0:
        print("[ERROR] No stock spot files found to backtest.")
        return
        
    # 3. Launch parallel backtests
    cores = min(cpu_count(), total_symbols)
    print(f"[INFO] Running parallel backtests on {cores} CPU cores...")
    
    with Pool(processes=cores) as pool:
        results = pool.map(run_backtest_for_stock, stock_symbols)
        
    # 4. Filter and process results
    valid_results = [r for r in results if "Error" not in r]
    errors = [r for r in results if "Error" in r]
    
    if errors:
        print(f"[WARNING] {len(errors)} backtests failed due to exceptions:")
        for err in errors[:5]:
            print(f"  - {err['Instrument']}: {err['Error']}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more.")
            
    if not valid_results:
        print("[ERROR] No valid backtest results generated.")
        return
        
    df_results = pd.DataFrame(valid_results)
    
    # Print configuration details
    config = BacktestConfig()
    print(f"\n[CONFIG] CARRY_FORWARD (Overnight holding): {config.CARRY_FORWARD}")
    print(f"[CONFIG] USE_DYNAMIC_EXITS: {config.USE_DYNAMIC_EXITS}")
    print(f"[CONFIG] LEG_MODE: {config.LEG_MODE}")
    
    # Rank by Robustness Score (Net PnL / Max Drawdown with trade penalty)
    df_ranks = df_results.sort_values(by="Robustness Score", ascending=False)
    
    # Filter to require at least 30 trades for the top 40 to avoid statistical anomalies
    df_filtered_ranks = df_ranks[df_ranks['Trades'] >= 30]
    top_40 = df_filtered_ranks.head(40)
    
    print("\n" + "=" * 125)
    print("                                TOP 40 STOCKS FOR STRATEGY 3 (TRIPLE MOMENTUM)                           ")
    print("=" * 125)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(top_40.to_string(index=False))
    print("=" * 125)
    
    # Save the full results and the top 40 results
    output_csv = os.path.join(BASE_DIR, "strategy_3_stock_rankings.csv")
    top_40_csv = os.path.join(BASE_DIR, "strategy_3_top_40_stocks.csv")
    
    try:
        df_ranks.to_csv(output_csv, index=False)
        top_40.to_csv(top_40_csv, index=False)
        print(f"[SUCCESS] Saved full rankings to strategy_3_stock_rankings.csv")
        print(f"[SUCCESS] Saved top 40 rankings to strategy_3_top_40_stocks.csv\n")
    except PermissionError as e:
        print(f"[ERROR] Permission denied writing results: {e}")

if __name__ == "__main__":
    main()
