import os
import sys
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

import backtest_engine
from backtest_engine import SimulationEngine, BacktestConfig

config = BacktestConfig()
for i in range(1, 23):
    setattr(config, f"ENABLE_STRATEGY_{i}", False)
setattr(config, "ENABLE_STRATEGY_22", True)
config.apply_strategy_defaults("Strategy_22")
config.LEG_MODE = "SELL"

# Run with New Offline Dataset
os.environ["DISABLE_OFFLINE_DATASET"] = "False"
engine_new = SimulationEngine(config, instrument_name="NIFTY", backtest_days=1800)
engine_new.load_data()
engine_new.df_spot = engine_new.df_spot[(engine_new.df_spot.index >= '2024-01-01') & (engine_new.df_spot.index <= '2024-03-31')]
res_new = engine_new.run(write_to_csv=False)

print("TRADE 34 ON 2024-03-06:")
t34 = res_new[res_new['Entry_Time'].astype(str).str.contains("2024-03-06")]
print(t34[['Entry_Time', 'Exit_Time', 'Strike', 'Entry_Price', 'Exit_Price', 'PnL', 'Exit_Reason']].to_string())
