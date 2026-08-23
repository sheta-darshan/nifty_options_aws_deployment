import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import time

from trading_bot.config import Config
from trading_bot.state import TradeState
from trading_bot.instrument_bot import InstrumentBot

class TestConcurrencyFixes(unittest.TestCase):
    def setUp(self):
        self.config_mock = MagicMock(spec=Config)
        self.config_mock.TIMEZONE = None
        self.config_mock.TRADE_LOG_CSV = "dummy.csv"
        self.config_mock.PRODUCT_TYPE = "MARGIN"
        self.config_mock.INSTRUMENTS = {
            "NIFTY": {
                "lot_size": 25,
                "fno_prefix": "NIFTY",
                "max_active": 1,
                "daily_limit": 5,
                "strategy_overrides": {
                    "Strategy_14": {
                        "max_active": 2,
                        "points_sl_buy": 10
                    }
                }
            }
        }
        self.state_mock = MagicMock(spec=TradeState)
        self.state_mock.lock = MagicMock()
        self.state_mock.positions = {}
        
        self.logger_mock = MagicMock()
        self.alert_mock = MagicMock()
        self.order_manager_mock = MagicMock()
        
        # Setup mock accounts
        self.acc_api_mock = MagicMock()
        self.order_manager_mock.get_accounts.return_value = [
            {"name": "Mansi", "api": self.acc_api_mock, "config": {}}
        ]
        
        # Instantiate InstrumentBot with mocked dependencies
        with patch('trading_bot.instrument_bot.get_today_trade_count', return_value={}):
            self.bot = InstrumentBot(
                instrument_name="NIFTY",
                config=self.config_mock,
                state=self.state_mock,
                data_api=MagicMock(),
                order_manager=self.order_manager_mock,
                logger=self.logger_mock,
                alert_manager=self.alert_mock
            )

    def test_get_strategy_instrument_config_overrides(self):
        # Test default config when strategy name is unknown or has no overrides
        cfg_default = self.bot.get_strategy_instrument_config("Strategy_19")
        self.assertEqual(cfg_default["max_active"], 1)
        self.assertEqual(cfg_default["lot_size"], 25)
        
        # Test overrides applied for Strategy_14
        cfg_s14 = self.bot.get_strategy_instrument_config("Strategy_14")
        self.assertEqual(cfg_s14["max_active"], 2)
        self.assertEqual(cfg_s14["points_sl_buy"], 10)
        self.assertEqual(cfg_s14["lot_size"], 25)

    def test_count_my_active_positions_isolated(self):
        # Setup self.state.positions with mixed strategy/instrument positions
        self.state_mock.positions = {
            "123": {"instrument": "NIFTY", "strategy": "Strategy_14", "leg": "CE"},
            "456": {"instrument": "NIFTY", "strategy": "Strategy_14", "leg": "PE"},
            "789": {"instrument": "NIFTY", "strategy": "Strategy_19", "leg": "CE"},
            "999": {"instrument": "BANKNIFTY", "strategy": "Strategy_14", "leg": "CE"}
        }
        
        # Verify counts isolated by strategy name
        s14_ce = self.bot._count_my_active_positions(None, leg_type="CE", strategy_name="Strategy_14")
        s14_pe = self.bot._count_my_active_positions(None, leg_type="PE", strategy_name="Strategy_14")
        s19_ce = self.bot._count_my_active_positions(None, leg_type="CE", strategy_name="Strategy_19")
        
        self.assertEqual(s14_ce, 1)
        self.assertEqual(s14_pe, 1)
        self.assertEqual(s19_ce, 1)
        
        # Verify total strategy counts
        s14_total = self.bot._count_my_active_positions(None, strategy_name="Strategy_14")
        self.assertEqual(s14_total, 1) # max of CE, PE, STOCK

    def test_reconcile_positions_with_broker(self):
        # Setup local state with positions
        self.state_mock.positions = {
            "123": {"instrument": "NIFTY", "symbol": "NIFTY26AUGCE", "strategy": "Strategy_14"},
            "456": {"instrument": "NIFTY", "symbol": "NIFTY26AUGPE", "strategy": "Strategy_19"},
            "789": {"instrument": "BANKNIFTY", "symbol": "BANKNIFTY26AUGCE", "strategy": "Strategy_14"}
        }
        
        # Mock broker positions (missing NIFTY26AUGPE)
        self.acc_api_mock.get_positions.return_value = [
            {"securityId": "123", "tradingSymbol": "NIFTY26AUGCE", "netQty": 25},
            {"securityId": "789", "tradingSymbol": "BANKNIFTY26AUGCE", "netQty": 15}
        ]
        
        self.bot.reconcile_positions_with_broker()
        
        # Verify NIFTY26AUGPE is pruned (since it's not on broker) but other positions remain
        self.assertIn("123", self.state_mock.positions)
        self.assertNotIn("456", self.state_mock.positions)
        self.assertIn("789", self.state_mock.positions)
        self.state_mock.save_state.assert_called_once()

    def test_enforce_order_stagger(self):
        # Setup shared state last_order_timestamp to simulate a very recent order
        self.state_mock.last_order_timestamp = time.time()
        
        start_time = time.time()
        self.bot._enforce_order_stagger()
        end_time = time.time()
        
        # Stagger should have slept to enforce the 0.5s separation
        self.assertTrue((end_time - start_time) >= 0.45) # Tolerant sleep check

    def test_order_latency_locks(self):
        # Initially, no latency lock should be active
        self.assertNotIn("Strategy_14", self.bot.order_latency_locks)
        
        # Trigger an order mock placement, which sets the latency lock
        self.bot.order_latency_locks["Strategy_14"] = datetime.now()
        
        # Verify a signal handled within the lock period is skipped
        with patch.object(self.bot, 'get_strategy_instrument_config') as mock_get_cfg:
            self.bot._handle_signal("BUY", 10.0, "Strategy_14")
            # Should call config override method once, but skip actual placement/validation
            mock_get_cfg.assert_called_once_with("Strategy_14")

if __name__ == '__main__':
    unittest.main()
