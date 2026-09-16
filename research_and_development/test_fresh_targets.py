import os
import sys
import copy
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from strategies import BacktestConfig
from backtest_engine import SimulationEngine

def test_fresh(tp, be=0.0):
    config = BacktestConfig()
    config.LEG_MODE = "SELL"
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    config.ENABLE_STRATEGY_22 = True
    config.apply_strategy_defaults("Strategy_22")

    engine = SimulationEngine(config, instrument_name="NIFTY", offline_mode=False, backtest_days=180)
    engine.load_data()
    engine.inst_config['points_target_sell'] = float(tp)
    engine.inst_config['points_be_sell'] = float(be)
    df = engine.run(write_to_csv=False)
    
    if not df.empty:
        wr = (len(df[df['PnL'] > 0]) / len(df)) * 100
        net = df['PnL'].sum()
        avg = net / len(df)
        w = df[df['Gross_PnL'] > 0]['Gross_PnL'].sum()
        l = abs(df[df['Gross_PnL'] < 0]['Gross_PnL'].sum())
        pf = round(w / l, 2) if l > 0 else 99.99
        return len(df), wr, pf, net, avg
    return 0, 0, 0, 0, 0

print("Target | BE_Mult | Trades | Win Rate | Profit Factor | Net PnL (Rs.) | Avg/Trade")
print("-" * 75)
for tp in [20.0, 25.0, 30.0, 35.0]:
    trades, wr, pf, net, avg = test_fresh(tp, 0.0)
    print(f"{tp:>6.1f} | {0.0:>7.2f} | {trades:>6} | {wr:>7.1f}% | {pf:>13.2f} | Rs.{net:>11,.2f} | Rs.{avg:>8,.2f}")
