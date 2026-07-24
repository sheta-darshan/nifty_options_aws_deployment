import os
import json
import numpy as np
import pandas as pd
import pandas_ta as ta
from backtest_engine import SimulationEngine, BacktestConfig

def snap_tick(val):
    return round(float(val) * 20.0) / 20.0

def main():
    # 1. Load instruments.json
    config_path = "instruments.json"
    with open(config_path, "r") as f:
        instruments = json.load(f)
        
    print(f"[INFO] Loaded {len(instruments)} instruments from instruments.json.")
    
    # 2. Iterate through and identify stocks
    updated_count = 0
    
    for symbol, inst_config in instruments.items():
        inst_type = inst_config.get("type", "")
        exec_mode = inst_config.get("execution_mode", "")
        
        # We only apply point-based statistical grids to stocks
        if inst_type == "STOCK" or exec_mode == "STOCK":
            print(f"\nProcessing statistical ATR for {symbol}...")
            
            # Setup SimulationEngine to fetch 1 year of spot data
            config = BacktestConfig()
            config.apply_strategy_defaults("Strategy_3")
            
            try:
                engine = SimulationEngine(config, instrument_name=symbol, offline_mode=False, backtest_days=365)
                engine.load_data()
                df_spot = engine.df_spot
            except Exception as e:
                print(f"[WARNING] Failed to load spot data for {symbol}: {e}. Skipping.")
                continue
                
            if df_spot.empty:
                print(f"[WARNING] Spot dataset for {symbol} is empty. Skipping.")
                continue
                
            # Compute Average Spot ATR from 5-minute resampled wicks
            df_5min = df_spot.resample('5min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            if len(df_5min) < 14:
                print(f"[WARNING] Insufficient 5-min candles to compute ATR for {symbol}. Skipping.")
                continue
                
            df_5min['ATR'] = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=14)
            avg_atr = df_5min['ATR'].mean()
            avg_close = df_spot['close'].mean()
            
            if pd.isna(avg_atr) or avg_atr <= 0:
                avg_atr = avg_close * 0.005 # Fallback to 0.5% of average spot price
                print(f"  Using fallback ATR: {avg_atr:.2f}")
            else:
                print(f"  1-Year Average 5-Min Spot ATR: {avg_atr:.2f} (avg close: {avg_close:.2f})")
                
            # Calculate option premium equivalency
            is_option = (exec_mode == "OPTION")
            opt_delta = 0.5 if is_option else 1.0
            premium_atr = avg_atr * opt_delta
            
            # Asymmetric Buy / Sell boundaries centered around premium ATR
            sl_base = premium_atr
            
            # BUY mode parameters
            sl_buy_1 = max(0.05, snap_tick(sl_base * 0.8))
            sl_buy_2 = max(0.05, snap_tick(sl_base * 1.2))
            tp_buy_1 = max(0.05, snap_tick(sl_base * 1.5))
            tp_buy_2 = max(0.05, snap_tick(sl_base * 3.0))
            trail_buy = max(0.05, snap_tick(sl_base * 0.33))
            
            # SELL mode parameters
            sl_sell_1 = max(0.05, snap_tick(sl_base * 0.8))
            sl_sell_2 = max(0.05, snap_tick(sl_base * 1.2))
            tp_sell_1 = max(0.05, snap_tick(sl_base * 0.8))
            tp_sell_2 = max(0.05, snap_tick(sl_base * 1.5))
            trail_sell = max(0.05, snap_tick(sl_base * 0.33))
            
            inst_config["optimization_grid"] = {
                "points_sl_buy": [sl_buy_1, sl_buy_2],
                "points_target_buy": [tp_buy_1, tp_buy_2],
                "points_trail_buy": [0.0, trail_buy],
                "points_be_buy": [0.0],
                "points_sl_sell": [sl_sell_1, sl_sell_2],
                "points_target_sell": [tp_sell_1, tp_sell_2],
                "points_trail_sell": [0.0, trail_sell],
                "points_be_sell": [0.0]
            }
            
            print(f"  Configured grid:")
            print(f"    points_sl_buy: {inst_config['optimization_grid']['points_sl_buy']}")
            print(f"    points_target_buy: {inst_config['optimization_grid']['points_target_buy']}")
            print(f"    points_sl_sell: {inst_config['optimization_grid']['points_sl_sell']}")
            print(f"    points_target_sell: {inst_config['optimization_grid']['points_target_sell']}")
            updated_count += 1
            
    # 3. Write back to instruments.json
    with open(config_path, "w") as f:
        json.dump(instruments, f, indent=4)
        
    print(f"\n[SUCCESS] Custom optimization grids updated for {updated_count} stocks in instruments.json.")

if __name__ == "__main__":
    main()
