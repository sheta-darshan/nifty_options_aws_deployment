import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import pytz

from trading_bot.config import Config
from trading_bot.manager import ThreadedBotManager
from trading_bot.alerts import AlertManager

class TestDailyDigest(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.logger = MagicMock()
        self.alert_manager = MagicMock(spec=AlertManager)
        
        with patch('trading_bot.manager.DhanAPIWrapper'), \
             patch('trading_bot.manager.MultiAccountManager'), \
             patch('trading_bot.manager.CentralizedPositionManager'), \
             patch('trading_bot.manager.TradeState'):
            self.manager = ThreadedBotManager(self.config, self.logger, self.alert_manager)

    def test_generate_daily_digest_format(self):
        # Mock accounts
        mock_acc_api = MagicMock()
        mock_acc_api.get_positions.return_value = [
            {'realizedProfit': 4500.0, 'unrealizedProfit': 0.0, 'netQty': 0, 'tradingSymbol': 'NIFTY 25000 CE'},
            {'realizedProfit': -1200.0, 'unrealizedProfit': 250.0, 'netQty': 50, 'tradingSymbol': 'BANKNIFTY 52000 PE'}
        ]
        mock_acc_api._make_request.return_value = {
            'data': {'availMargin': 250000.0, 'utilisedMargin': 45000.0}
        }
        
        mock_account = {
            'name': 'TestAccount_1',
            'api': mock_acc_api
        }
        self.manager.order_manager.get_accounts.return_value = [mock_account]
        
        # Mock carry forward position in state
        self.manager.state.positions = {
            'pos_1': {'symbol': 'NIFTY 25000 CE', 'action': 'SELL', 'qty': 50, 'Entry_Price': 120.5, 'strategy': 'Strategy_22'}
        }
        
        digest = self.manager.generate_daily_digest()
        
        self.assertIn("ACCOUNT-WISE REALIZED PnL", digest)
        self.assertIn("TestAccount_1", digest)
        self.assertIn("₹+3,300.00", digest)  # 4500 - 1200 = 3300
        self.assertIn("Avail Margin:", digest)
        self.assertIn("₹250,000.00", digest)
        self.assertIn("CARRY-FORWARD POSITIONS", digest)
        self.assertIn("NIFTY 25000 CE", digest)
        self.assertIn("Strategy_22", digest)
        self.assertIn("RISK & CIRCUIT CONTROLS", digest)

    def test_send_daily_digest_calls_alert_manager(self):
        self.manager.order_manager.get_accounts.return_value = []
        self.manager.state.positions = {}
        
        self.manager.send_daily_digest()
        self.alert_manager.send_alert.assert_called_once()
        call_args = self.alert_manager.send_alert.call_args
        self.assertEqual(call_args[1]['header'], "Daily PnL & Risk Digest")

if __name__ == '__main__':
    unittest.main()
