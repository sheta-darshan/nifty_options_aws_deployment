import unittest
from unittest.mock import patch, MagicMock
import os
import json
from trading_bot.config import Config

class TestStrategyOverrides(unittest.TestCase):
    def test_apply_strategy_instrument_overrides(self):
        # 1. Setup a mock Config instance
        config = MagicMock(spec=Config)
        config.INSTRUMENTS = {
            "NIFTY": {
                "lot_size": 25,
                "points_sl_buy": 36,
                "points_target_buy": 72,
                "strategy_overrides": {
                    "Strategy_13": {
                        "points_sl_buy": 35,
                        "points_target_buy": 30
                    }
                }
            },
            "BANKNIFTY": {
                "lot_size": 15,
                "points_sl_buy": 50,
                "points_target_buy": 100
                # No overrides
            }
        }
        
        # Call the helper method on our mock
        Config.apply_strategy_instrument_overrides(config, "Strategy_13")
        
        # Verify NIFTY is overridden
        self.assertEqual(config.INSTRUMENTS["NIFTY"]["points_sl_buy"], 35)
        self.assertEqual(config.INSTRUMENTS["NIFTY"]["points_target_buy"], 30)
        self.assertEqual(config.INSTRUMENTS["NIFTY"]["lot_size"], 25) # base key unchanged
        
        # Verify BANKNIFTY is untouched
        self.assertEqual(config.INSTRUMENTS["BANKNIFTY"]["points_sl_buy"], 50)
        self.assertEqual(config.INSTRUMENTS["BANKNIFTY"]["points_target_buy"], 100)
        
    def test_apply_strategy_instrument_overrides_no_match(self):
        # Setup mock
        config = MagicMock(spec=Config)
        config.INSTRUMENTS = {
            "NIFTY": {
                "points_sl_buy": 36,
                "strategy_overrides": {
                    "Strategy_13": {
                        "points_sl_buy": 35
                    }
                }
            }
        }
        
        # Call with non-matching strategy
        Config.apply_strategy_instrument_overrides(config, "Strategy_12")
        
        # Verify NIFTY is not overridden (remains at default)
        self.assertEqual(config.INSTRUMENTS["NIFTY"]["points_sl_buy"], 36)

    @patch('backtest_engine.os.path.exists')
    @patch('backtest_engine.open')
    @patch('backtest_engine.json.load')
    def test_backtest_engine_overrides(self, mock_json_load, mock_open, mock_exists):
        # Mock file read of instruments.json
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "NIFTY": {
                "lot_size": 25,
                "points_sl_buy": 36,
                "points_target_buy": 72,
                "strategy_overrides": {
                    "Strategy_13": {
                        "points_sl_buy": 35,
                        "points_target_buy": 30
                    }
                }
            }
        }
        
        from backtest_engine import SimulationEngine
        
        # Mock BacktestConfig
        class MockConfig:
            ENABLE_STRATEGY_13 = True
            ENABLE_STRATEGY_1 = False
            ENABLE_STRATEGY_2 = False
            ENABLE_STRATEGY_3 = False
            ENABLE_STRATEGY_4 = False
            ENABLE_STRATEGY_5 = False
            ENABLE_STRATEGY_6 = False
            ENABLE_STRATEGY_7 = False
            ENABLE_STRATEGY_8 = False
            ENABLE_STRATEGY_9 = False
            ENABLE_STRATEGY_10 = False
            ENABLE_STRATEGY_11 = False
            ENABLE_STRATEGY_12 = False
            ENABLE_STRATEGY_14 = False
            ENABLE_STRATEGY_15 = False
            ENABLE_STRATEGY_16 = False
            ENABLE_STRATEGY_17 = False
            ENABLE_STRATEGY_18 = False
            ENABLE_STRATEGY_19 = False
            DATA_INTERVAL = 1
            TIMEZONE = None
        
        # Instantiate SimulationEngine
        bt = SimulationEngine(config=MockConfig(), instrument_name="NIFTY", df_spot=None)
        
        # Check overrides applied in inst_config
        self.assertEqual(bt.inst_config["points_sl_buy"], 35)
        self.assertEqual(bt.inst_config["points_target_buy"], 30)

    @patch('trading_bot.config.os.path.exists')
    @patch('trading_bot.config.open')
    @patch('trading_bot.config.json.load')
    def test_reload_instruments_reapplies_overrides(self, mock_json_load, mock_open, mock_exists):
        # 1. Instantiate configuration
        # Mock file system checks for first constructor load
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "NIFTY": {
                "security_id": 13,
                "points_sl_buy": 36,
                "strategy_overrides": {
                    "Strategy_13": {
                        "points_sl_buy": 35
                    }
                }
            }
        }
        
        config = Config()
        config.active_strategy = "Strategy_13"
        config.INSTRUMENTS_FILE = "instruments.json"
        config.last_instruments_mtime = 0.0
        
        # 2. Trigger reload (simulate config file modification time change on disk)
        with patch('trading_bot.config.os.path.getmtime') as mock_mtime:
            mock_mtime.return_value = 12345.67
            config.reload_instruments()
            
        # Verify that Strategy 13 overrides are successfully re-applied after disk load
        self.assertEqual(config.INSTRUMENTS["NIFTY"]["points_sl_buy"], 35)

if __name__ == '__main__':
    unittest.main()
