import os
import sys
import copy
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from strategies import BacktestConfig
from backtest_engine import SimulationEngine

def main():
    config = BacktestConfig()
    config.LEG_MODE = "SELL"
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    config.ENABLE_STRATEGY_22 = True
    config.apply_strategy_defaults("Strategy_22")

    engine = SimulationEngine(config, instrument_name="NIFTY", offline_mode=False, backtest_days=180)
    engine.load_data()
    base_cfg = copy.deepcopy(engine.inst_config)

    print("================================================================================")
    print(" TESTING BREAKEVEN MULTIPLIER + TARGET MATRIX ON NIFTY 180D (STRATEGY 22) ")
    print("================================================================================")
    print(f"{'BE_Mult':>8} | {'Target':>8} | {'Trades':>6} | {'WinRate':>8} | {'PF':>6} | {'Net PnL (INR)':>14} | {'Avg/Trade':>10}")
    print("-" * 75)

    for be in [0.0, 0.15, 0.20, 0.25, 0.30]:
        for tp in [20.0, 25.0, 30.0, 35.0]:
            engine.inst_config = copy.deepcopy(base_cfg)
            engine.inst_config['points_be_sell'] = float(be)
            engine.inst_config['points_target_sell'] = float(tp)
            engine.trade_log = []
            df = engine.run(write_to_csv=False)
            if not df.empty:
                wr = (len(df[df['PnL'] > 0]) / len(df)) * 100
                net = df['PnL'].sum()
                avg = net / len(df)
                w = df[df['Gross_PnL'] > 0]['Gross_PnL'].sum()
                l = abs(df[df['Gross_PnL'] < 0]['Gross_PnL'].sum())
                pf = round(w / l, 2) if l > 0 else 99.99
                print(f"{be:>8.2f} | {tp:>8.1f} | {len(df):>6} | {wr:>7.1f}% | {pf:>6.2f} | {net:>14.2f} | {avg:>10.2f}")

if __name__ == "__main__":
    main()
