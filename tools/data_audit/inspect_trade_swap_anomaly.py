"""
Deep Investigation of Trades 7, 8, 9, 10 on 2024-01-16 and 2024-01-18.
Compares exact trade records (strike, option_type, entry_time, exit_time, entry_price, exit_price).
"""
import os
import sys
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

import backtest_engine
from backtest_engine import SimulationEngine, BacktestConfig

def main():
    print("=" * 95)
    print(" INVESTIGATING TRADES 7, 8, 9, 10 FOR OLD vs NEW PATHS")
    print("=" * 95)

    config = BacktestConfig()
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    setattr(config, "ENABLE_STRATEGY_22", True)
    config.apply_strategy_defaults("Strategy_22")
    config.LEG_MODE = "SELL"

    # --- RUN 1: OLD PATH ---
    os.environ["DISABLE_OFFLINE_DATASET"] = "True"
    backtest_engine._OPT_DF_CACHE.clear()
    backtest_engine._OPT_DICT_CACHE.clear()
    backtest_engine._OFFLINE_OPT_DAY_CACHE.clear()

    engine_old = SimulationEngine(config, instrument_name="NIFTY", backtest_days=1800)
    engine_old.load_data()
    engine_old.df_spot = engine_old.df_spot[(engine_old.df_spot.index >= '2024-01-01') & (engine_old.df_spot.index <= '2024-03-31')]
    res_old = engine_old.run(write_to_csv=False)

    # --- RUN 2: NEW PATH ---
    os.environ["DISABLE_OFFLINE_DATASET"] = "False"
    backtest_engine._OPT_DF_CACHE.clear()
    backtest_engine._OPT_DICT_CACHE.clear()
    backtest_engine._OFFLINE_OPT_DAY_CACHE.clear()

    engine_new = SimulationEngine(config, instrument_name="NIFTY", backtest_days=1800)
    engine_new.load_data()
    engine_new.df_spot = engine_new.df_spot[(engine_new.df_spot.index >= '2024-01-01') & (engine_new.df_spot.index <= '2024-03-31')]
    res_new = engine_new.run(write_to_csv=False)

    print("\nOLD RUN TRADES (Indices 6 to 11):")
    cols = ['Entry_Time', 'Exit_Time', 'Strike', 'Option_Type', 'Entry_Price', 'Exit_Price', 'PnL', 'Exit_Reason']
    avail_cols_old = [c for c in cols if c in res_old.columns]
    print(res_old[avail_cols_old].iloc[5:12].to_string())

    print("\nNEW RUN TRADES (Indices 6 to 11):")
    avail_cols_new = [c for c in cols if c in res_new.columns]
    print(res_new[avail_cols_new].iloc[5:12].to_string())

if __name__ == "__main__":
    main()
