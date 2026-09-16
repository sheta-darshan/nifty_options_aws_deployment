import unittest
import os
import json
import tempfile
import pandas as pd
from unittest.mock import MagicMock, patch
from trading_bot.config import Config
from trading_bot.data_pipeline import get_today_sl_count
from trading_bot.instrument_bot import InstrumentBot

class TestMaxDailySLAndConviction(unittest.TestCase):
    def test_dynamic_conviction_configs_in_instruments_json(self):
        """Verify Strategy_22 dynamic conviction is enabled across NIFTY, BANKNIFTY, and SENSEX."""
        with open('instruments.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # NIFTY
        nifty_s22 = data.get('NIFTY', {}).get('strategy_overrides', {}).get('Strategy_22', {})
        self.assertTrue(nifty_s22.get('enable_dynamic_conviction'))
        self.assertGreaterEqual(nifty_s22.get('num_lots_high_conviction', 0), nifty_s22.get('num_lots_sell', 0))
        self.assertEqual(nifty_s22.get('points_target_high_conviction'), 45.0)
        
        # BANKNIFTY
        bn_s22 = data.get('BANKNIFTY', {}).get('strategy_overrides', {}).get('Strategy_22', {})
        self.assertTrue(bn_s22.get('enable_dynamic_conviction'))
        self.assertGreaterEqual(bn_s22.get('num_lots_high_conviction', 0), bn_s22.get('num_lots_sell', 0))
        self.assertEqual(bn_s22.get('points_target_high_conviction'), 75.0)
        
        # SENSEX
        sx_s22 = data.get('SENSEX', {}).get('strategy_overrides', {}).get('Strategy_22', {})
        self.assertTrue(sx_s22.get('enable_dynamic_conviction'))
        self.assertGreaterEqual(sx_s22.get('num_lots_high_conviction', 0), sx_s22.get('num_lots_sell', 0))
        self.assertEqual(sx_s22.get('points_target_high_conviction'), 90.0)

    def test_get_today_sl_count_csv(self):
        """Verify get_today_sl_count correctly parses SL exits from CSV log."""
        from datetime import datetime
        import pytz
        tz = pytz.timezone('Asia/Kolkata')
        today_str = datetime.now(tz).isoformat()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tf:
            temp_csv = tf.name
            df = pd.DataFrame([
                {
                    'timestamp': today_str,
                    'instrument': 'NIFTY',
                    'signal': 'StopLoss',
                    'strategy': 'Strategy_15',
                    'account': 'ACC_1',
                    'exit_reason': 'StopLoss'
                },
                {
                    'timestamp': today_str,
                    'instrument': 'NIFTY',
                    'signal': 'Target',
                    'strategy': 'Strategy_15',
                    'account': 'ACC_1',
                    'exit_reason': 'Target'
                },
                {
                    'timestamp': today_str,
                    'instrument': 'NIFTY',
                    'signal': 'StopLoss',
                    'strategy': 'Strategy_15',
                    'account': 'ACC_2',
                    'exit_reason': 'StopLoss'
                }
            ])
            df.to_csv(temp_csv, index=False)
            
        try:
            sl_counts = get_today_sl_count(temp_csv, 'NIFTY', tz, strategy_name='Strategy_15')
            self.assertEqual(sl_counts.get('ACC_1'), 1)
            self.assertEqual(sl_counts.get('ACC_2'), 1)
        finally:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)

    def test_max_daily_sl_blocks_entry(self):
        """Verify that InstrumentBot blocks trade entry when daily SL limit is reached."""
        config_mock = MagicMock(spec=Config)
        config_mock.INSTRUMENTS = {
            'NIFTY': {
                'security_id': 13,
                'lot_size': 65,
                'type': 'INDEX',
                'fno_prefix': 'NIFTY',
                'enabled': 1,
                'max_active': 1,
                'daily_limit': 5,
                'max_daily_sl': 1,
                'strategy_overrides': {
                    'Strategy_15': {
                        'max_daily_sl': 1,
                        'daily_limit': 2
                    }
                }
            }
        }
        config_mock.BASE_INSTRUMENTS = config_mock.INSTRUMENTS
        config_mock.TRADE_LOG_CSV = "dummy.csv"
        import pytz
        config_mock.TIMEZONE = pytz.timezone('Asia/Kolkata')
        
        data_api_mock = MagicMock()
        order_manager_mock = MagicMock()
        order_manager_mock.get_accounts.return_value = [
            {'name': 'ACC_MAIN', 'api': MagicMock(), 'config': {}}
        ]
        state_mock = MagicMock()
        state_mock.positions = {}
        logger_mock = MagicMock()
        alert_mock = MagicMock()
        
        with patch('trading_bot.instrument_bot.get_today_trade_count', return_value={}), \
             patch('trading_bot.instrument_bot.get_today_sl_count', return_value={}):
            bot = InstrumentBot('NIFTY', config_mock, data_api_mock, order_manager_mock, state_mock, logger_mock, alert_mock)
            
        config_mock.LEG_MODE = 'BUY'
        # Manually set daily SL count to 1 for Strategy_15
        bot.daily_sl_counts['Strategy_15'] = {'ACC_MAIN': 1}
        bot.daily_trade_counts['Strategy_15'] = {'ACC_MAIN': 0}
        
        # Verify that signal is blocked by circuit breaker
        bot._handle_signal_inner('BUY', 15.0, 'Strategy_15')
        
        # Ensure it was skipped at early filter
        warn_calls = [str(call) for call in logger_mock.warning.call_args_list]
        self.assertTrue(any("reached daily limit or max daily SL" in c for c in warn_calls))
        
        # Now reset daily SL count to 0
        bot.daily_sl_counts['Strategy_15'] = {'ACC_MAIN': 0}
        bot.daily_trade_counts['Strategy_15'] = {'ACC_MAIN': 0}
        logger_mock.info.reset_mock()
        
        bot._handle_signal_inner('BUY', 15.0, 'Strategy_15')
        info_calls = [str(call) for call in logger_mock.info.call_args_list]
        self.assertTrue(any("Executing BUY from Strategy_15" in c for c in info_calls))

if __name__ == '__main__':
    unittest.main()
