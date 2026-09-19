import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategies.registry import get_strategy
from strategies.strategy_24 import Strategy24


class TestStrategy24(unittest.TestCase):
    def setUp(self):
        self.strat = Strategy24()

    def test_default_params(self):
        params = self.strat.get_default_params()
        self.assertEqual(params["MIN_VOLUME_SURGE"], 1.25)
        self.assertEqual(params["MIN_ABS_VOLUME"], 2500)
        self.assertEqual(params["TARGET_ATR_MULT"], 1.15)
        self.assertEqual(params["SL_ATR_MULT"], 0.90)
        self.assertEqual(params["BE_ATR_MULT"], 0.65)

    def test_breakout_signal_with_volume_surge(self):
        """Simulate Day T coiling and Day T+1 breakout with volume surge."""
        # Create 2 days of 5-min candles
        # Day 1: 09:15 to 15:25
        t1_start = pd.Timestamp("2026-09-10 09:15:00")
        times_day1 = pd.date_range(t1_start, t1_start + pd.Timedelta(hours=6), freq='5min')

        records = []
        for t in times_day1:
            records.append({
                'timestamp': t,
                'open': 100.0,
                'high': 102.0,  # Day 1 High is 102.0
                'low': 98.0,
                'close': 101.0,
                'volume': 2000.0
            })

        # Day 2: 09:15 to 15:25
        t2_start = pd.Timestamp("2026-09-11 09:15:00")
        times_day2 = pd.date_range(t2_start, t2_start + pd.Timedelta(hours=6), freq='5min')

        for i, t in enumerate(times_day2):
            if i == 2:  # 09:25 AM: Breakout past 102.0 with high volume
                records.append({
                    'timestamp': t,
                    'open': 101.5,
                    'high': 103.5,  # Crosses 102.0 Day 1 High
                    'low': 101.2,
                    'close': 103.0,
                    'volume': 6000.0  # Big volume surge
                })
            else:
                records.append({
                    'timestamp': t,
                    'open': 101.0,
                    'high': 101.8,
                    'low': 100.5,
                    'close': 101.2,
                    'volume': 1500.0
                })

        df = pd.DataFrame(records)
        df_sig = self.strat.generate_signals(df)

        signals = df_sig[df_sig['Signal'] == 1]
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals['Signal_Source'].iloc[0], "Strategy_24")
        self.assertEqual(signals.index[0], pd.Timestamp("2026-09-11 09:25:00"))

    def test_low_volume_fakeout_rejected(self):
        """Breakout candle with low volume should be rejected."""
        t1_start = pd.Timestamp("2026-09-10 09:15:00")
        times_day1 = pd.date_range(t1_start, t1_start + pd.Timedelta(hours=6), freq='5min')

        records = []
        for t in times_day1:
            records.append({
                'timestamp': t,
                'open': 100.0,
                'high': 102.0,
                'low': 98.0,
                'close': 101.0,
                'volume': 2000.0
            })

        t2_start = pd.Timestamp("2026-09-11 09:15:00")
        times_day2 = pd.date_range(t2_start, t2_start + pd.Timedelta(hours=6), freq='5min')

        for i, t in enumerate(times_day2):
            if i == 2:  # Crosses 102.0 but with tiny volume (500 shares)
                records.append({
                    'timestamp': t,
                    'open': 101.5,
                    'high': 103.5,
                    'low': 101.2,
                    'close': 103.0,
                    'volume': 500.0  # Less than min 2500
                })
            else:
                records.append({
                    'timestamp': t,
                    'open': 101.0,
                    'high': 101.8,
                    'low': 100.5,
                    'close': 101.2,
                    'volume': 1500.0
                })

        df = pd.DataFrame(records)
        df_sig = self.strat.generate_signals(df)

        signals = df_sig[df_sig['Signal'] == 1]
        self.assertEqual(len(signals), 0)

    def test_sell_breakdown_execution(self):
        """Validates that Strategy 24 generates Signal = -1 on breakdown below Day T Low with volume."""
        strat_sell = Strategy24({"DIRECTION": "SELL", "MIN_ABS_VOLUME": 2500, "MIN_VOLUME_SURGE": 1.25})

        # Day 1: Day Low = 98.0
        t1_start = pd.Timestamp("2026-09-10 09:15:00")
        times_day1 = pd.date_range(t1_start, t1_start + pd.Timedelta(hours=6), freq='5min')
        records = []
        for t in times_day1:
            records.append({
                'timestamp': t,
                'open': 100.0,
                'high': 102.0,
                'low': 98.0,
                'close': 100.5,
                'volume': 2000.0
            })

        # Day 2: Candle 2 breaks below 98.0 with volume surge (6000 shares)
        t2_start = pd.Timestamp("2026-09-11 09:15:00")
        times_day2 = pd.date_range(t2_start, t2_start + pd.Timedelta(hours=6), freq='5min')
        for i, t in enumerate(times_day2):
            if i == 2:
                records.append({
                    'timestamp': t,
                    'open': 98.5,
                    'high': 98.8,
                    'low': 96.5,  # Breaks below 98.0
                    'close': 97.0,
                    'volume': 6000.0
                })
            else:
                records.append({
                    'timestamp': t,
                    'open': 99.0,
                    'high': 99.5,
                    'low': 98.2,
                    'close': 98.8,
                    'volume': 1500.0
                })

        df = pd.DataFrame(records)
        df_sig = strat_sell.generate_signals(df)

        sell_signals = df_sig[df_sig['Signal'] == -1]
        self.assertEqual(len(sell_signals), 1)
        self.assertEqual(sell_signals['Signal_Source'].iloc[0], "Strategy_24")
        self.assertEqual(sell_signals.index[0], pd.Timestamp("2026-09-11 09:25:00"))


if __name__ == '__main__':
    unittest.main()
