import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from live_trade_fixed import process_market_data

class TestSignalMerging(unittest.TestCase):
    @patch('strategies.get_strategy')
    def test_concurrent_strategy_merging(self, mock_get_strategy):
        # Setup config enabling both Strategy 3 and Strategy 10
        class MockConfig:
            ENABLE_STRATEGY_3 = True
            ENABLE_STRATEGY_10 = True
            ENABLE_STRATEGY_1 = ENABLE_STRATEGY_2 = ENABLE_STRATEGY_4 = ENABLE_STRATEGY_5 = False
            ENABLE_STRATEGY_6 = ENABLE_STRATEGY_7 = ENABLE_STRATEGY_8 = ENABLE_STRATEGY_9 = False
            DATA_INTERVAL = '1m'
            TIMEZONE = None

        spot_df = pd.DataFrame({
            'open': [23000.0, 23050.0],
            'high': [23060.0, 23110.0],
            'low': [22990.0, 23040.0],
            'close': [23050.0, 23100.0],
            'volume': [1000, 1500]
        }, index=pd.to_datetime(['2026-07-08 09:15:00', '2026-07-08 09:16:00']))

        # Return different signals depending on the strategy name
        def mock_get_strategy_side_effect(s_name, params=None):
            mock_inst = MagicMock()
            res_df = spot_df.copy()
            res_df['Signal'] = 0
            res_df['Signal_Source'] = "None"
            
            if s_name == 'Strategy_3':
                # Strategy 3 triggers a BUY signal on index 0
                res_df.loc[res_df.index[0], 'Signal'] = 1
                res_df.loc[res_df.index[0], 'Signal_Source'] = 'Strategy_3'
            elif s_name == 'Strategy_10':
                # Strategy 10 triggers a SELL signal on index 1
                res_df.loc[res_df.index[1], 'Signal'] = -1
                res_df.loc[res_df.index[1], 'Signal_Source'] = 'Strategy_10'
                
            mock_inst.generate_signals.return_value = res_df
            return mock_inst

        mock_get_strategy.side_effect = mock_get_strategy_side_effect

        import logging
        logger = logging.getLogger("Test")

        # Execute
        merged_df = process_market_data(spot_df.copy(), MockConfig(), logger, instrument_name='NIFTY')

        # Verify signals were merged successfully without overwriting each other
        self.assertEqual(merged_df.loc[spot_df.index[0], 'Signal'], 1)
        self.assertEqual(merged_df.loc[spot_df.index[0], 'Signal_Source'], 'Strategy_3')
        
        self.assertEqual(merged_df.loc[spot_df.index[1], 'Signal'], -1)
        self.assertEqual(merged_df.loc[spot_df.index[1], 'Signal_Source'], 'Strategy_10')

if __name__ == '__main__':
    unittest.main()
