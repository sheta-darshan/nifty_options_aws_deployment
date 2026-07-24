import unittest
import pandas as pd
import numpy as np
from strategies.base import BaseStrategy

class DummyStrategy(BaseStrategy):
    def get_default_params(self) -> dict:
        return {}

class TestRegimeFiltering(unittest.TestCase):
    def test_adx_trend_filter(self):
        # Instantiate strategy with trend limits set to allow ONLY 'NEUTRAL'
        strategy = DummyStrategy({
            "allowed_regimes_trend": ["NEUTRAL"]
        })

        # Construct spot dataframe with pre-calculated ADX values
        df = pd.DataFrame({
            'open': [100.0, 100.0, 100.0],
            'high': [101.0, 101.0, 101.0],
            'low': [99.0, 99.0, 99.0],
            'close': [100.0, 100.0, 100.0],
            'ADX_14': [15.0, 22.0, 30.0], # RANGE, NEUTRAL, TREND
            'Signal': [1, 1, 1],
            'Signal_Source': ['Dummy', 'Dummy', 'Dummy']
        }, index=pd.to_datetime(['2026-07-08 09:15:00', '2026-07-08 09:16:00', '2026-07-08 09:17:00']))

        # Apply regime filter
        filtered_df = strategy.apply_regime_filter(df)

        # Assert results:
        # Row 0 (ADX = 15.0 -> RANGE) should be blocked (Signal -> 0)
        self.assertEqual(filtered_df.iloc[0]['Signal'], 0)
        self.assertEqual(filtered_df.iloc[0]['Signal_Source'], 'None')

        # Row 1 (ADX = 22.0 -> NEUTRAL) should pass through (Signal -> 1)
        self.assertEqual(filtered_df.iloc[1]['Signal'], 1)
        self.assertEqual(filtered_df.iloc[1]['Signal_Source'], 'Dummy')

        # Row 2 (ADX = 30.0 -> TREND) should be blocked (Signal -> 0)
        self.assertEqual(filtered_df.iloc[2]['Signal'], 0)
        self.assertEqual(filtered_df.iloc[2]['Signal_Source'], 'None')

if __name__ == '__main__':
    unittest.main()
