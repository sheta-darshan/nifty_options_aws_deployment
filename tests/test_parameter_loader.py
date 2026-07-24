import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from live_trade_fixed import process_market_data

class TestParameterLoader(unittest.TestCase):
    @patch('strategies.get_strategy')
    def test_parameter_loader_overrides(self, mock_get_strategy):
        # Create mock config setting only Strategy 3 active
        class MockConfig:
            ENABLE_STRATEGY_3 = True
            ENABLE_STRATEGY_1 = False
            ENABLE_STRATEGY_2 = False
            ENABLE_STRATEGY_4 = False
            ENABLE_STRATEGY_5 = False
            ENABLE_STRATEGY_6 = False
            ENABLE_STRATEGY_7 = False
            ENABLE_STRATEGY_8 = False
            ENABLE_STRATEGY_9 = False
            ENABLE_STRATEGY_10 = False
            DATA_INTERVAL = '1m'
            TIMEZONE = None

        spot_df = pd.DataFrame({
            'open': [23000.0, 23050.0],
            'high': [23060.0, 23110.0],
            'low': [22990.0, 23040.0],
            'close': [23050.0, 23100.0],
            'volume': [1000, 1500]
        }, index=pd.to_datetime(['2026-07-08 09:15:00', '2026-07-08 09:16:00']))

        import logging
        logger = logging.getLogger("Test")
        
        # Mock strategy instance to return empty df
        mock_strategy_instance = MagicMock()
        mock_strategy_instance.generate_signals.return_value = pd.DataFrame()
        mock_get_strategy.return_value = mock_strategy_instance

        # Execute
        process_market_data(spot_df, MockConfig(), logger, instrument_name='NIFTY')

        # Assert get_strategy was called
        mock_get_strategy.assert_called()
        
        # Extract params passed to get_strategy
        called_args, called_kwargs = mock_get_strategy.call_args
        strategy_name = called_args[0]
        params = called_args[1]
        
        self.assertEqual(strategy_name, 'Strategy_3')
        
        # Check that base parameters from instruments.json are successfully loaded
        self.assertIn('allowed_regimes_trend', params)
        self.assertIn('NEUTRAL', params['allowed_regimes_trend'])
        self.assertIn('RANGE', params['allowed_regimes_trend'])

if __name__ == '__main__':
    unittest.main()
