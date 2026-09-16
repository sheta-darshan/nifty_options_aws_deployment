import os
import sys
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)
from backtest_engine import SimulationEngine, BacktestConfig

config = BacktestConfig()
engine = SimulationEngine(config, instrument_name="NIFTY")

test_dates = [
    "2021-04-12", # Monday
    "2021-04-13", # Tuesday
    "2021-04-15", # Thursday (Expiry day)
    "2021-04-16", # Friday (New week)
    "2022-08-15", # Monday
    "2022-08-18", # Thursday (Expiry day)
    "2022-08-19", # Friday (New week)
    "2023-01-23", # Monday
    "2023-01-25", # Wednesday (Holiday adjusted expiry)
    "2023-01-27", # Friday (New week)
    "2024-03-04", # Monday
    "2024-03-07", # Thursday (Expiry day)
    "2024-03-08", # Friday (Holiday adjusted new week)
]

print("Date | Weekday | _get_expiry_date(0) | _get_actual_expiry_date(0) | Offline Contract Implied Expiry")
print("-" * 105)
for d in test_dates:
    t_dt = datetime.strptime(d, "%Y-%m-%d").date()
    exp0 = engine._get_expiry_date(t_dt, 0)
    actual = engine._get_actual_expiry_date(t_dt, 0)
    print(f"{d} | {t_dt.strftime('%A'):<9s} | {exp0:<19s} | {actual:<26s} | {exp0}")
