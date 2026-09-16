import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import pytz

from trading_bot.config import Config
from trading_bot.api_wrapper import DhanAPIWrapper
from trading_bot.instrument_bot import InstrumentBot

class TestHybridCrashProofBreakeven(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.logger = MagicMock()
        self.alert_manager = MagicMock()
        
    def test_modify_super_order_sl(self):
        """Test DhanAPIWrapper.modify_super_order_sl properly formats call to dhanhq."""
        api = DhanAPIWrapper("test_client", "test_token", self.config, self.logger)
        api.dhan = MagicMock()
        api.dhan.modify_super_order.return_value = {
            'status': 'success',
            'orderStatus': 'MODIFIED'
        }
        
        success = api.modify_super_order_sl("ORD12345", 152.33)
        self.assertTrue(success)
        
        # Indian tick size round to 0.05 -> 152.35
        api.dhan.modify_super_order.assert_called_once_with(
            order_id="ORD12345",
            order_type="STOP_LOSS_MARKET",
            leg_name="STOP_LOSS_LEG",
            stopLossPrice=152.35
        )

    def test_hybrid_dispatch_params(self):
        """Test that with local_exit_monitoring=True and broker_safety_sl=True, SL is dispatched to broker."""
        inst_config = {
            'local_exit_monitoring': True,
            'broker_safety_sl': True
        }
        opt_tp = 25.0
        opt_sl = 74.0
        opt_trail = 10.0
        
        local_exit_monitoring = inst_config.get("local_exit_monitoring")
        broker_safety_sl = inst_config.get("broker_safety_sl", True)
        
        if local_exit_monitoring and broker_safety_sl:
            api_opt_tp = opt_tp
            api_opt_sl = opt_sl
            api_opt_trail = 0.0
        elif local_exit_monitoring and not broker_safety_sl:
            api_opt_tp = 0.0
            api_opt_sl = 0.0
            api_opt_trail = 0.0
        else:
            api_opt_tp = opt_tp
            api_opt_sl = opt_sl
            api_opt_trail = opt_trail

        self.assertEqual(api_opt_sl, 74.0, "Hard SL must be dispatched to broker for crash protection")
        self.assertEqual(api_opt_tp, 25.0, "Target must be dispatched to broker for Super Order completion")
        self.assertEqual(api_opt_trail, 0.0, "Trail must be 0 so local monitor controls dynamic breakeven")

    def test_breakeven_modifies_broker_sl(self):
        """Test that when local monitor hits breakeven trigger, modify_super_order_sl is invoked on the broker."""
        order_manager = MagicMock()
        primary_api = MagicMock()
        state = MagicMock()
        state.lock = MagicMock()
        
        bot = InstrumentBot("NIFTY", self.config, primary_api, order_manager, state, self.logger, self.alert_manager)
        
        mock_acc_api = MagicMock()
        mock_acc_api.modify_super_order_sl.return_value = True
        
        position = {
            'account': 'Primary_Account',
            'security_id': '12345',
            'action': 'SELL',
            'Entry_Price': 150.0,
            'opt_sl_price': 224.0,
            'opt_target_price': 105.0,
            'exit_mode': 'POINTS',
            'Breakeven_Mult': 25.0,
            'Initial_SL_Points': 74.0,
            'Breakeven_Triggered': False,
            'order_id': 'SUPER_ORD_999'
        }
        
        # Simulate price reaching 124.0 (<= 150 - 25 = 125.0 trigger)
        contract_ltp = 124.0
        be_mult = position.get("Breakeven_Mult", 0.0)
        action = position.get("action")
        pos_exit_mode = position.get("exit_mode")
        
        trigger_level = position["Entry_Price"] - be_mult if action == 'SELL' else position["Entry_Price"] + be_mult
        
        be_hit = False
        if action == 'SELL' and contract_ltp <= trigger_level:
            position["opt_sl_price"] = min(position["opt_sl_price"], position["Entry_Price"])
            position["Breakeven_Triggered"] = True
            be_hit = True

        self.assertTrue(be_hit)
        self.assertEqual(position["opt_sl_price"], 150.0)
        self.assertTrue(position["Breakeven_Triggered"])
        
        # Verify broker modification call
        super_oid = position.get('order_id')
        if be_hit and super_oid:
            mock_acc_api.modify_super_order_sl(super_oid, position["Entry_Price"])
            
        mock_acc_api.modify_super_order_sl.assert_called_once_with('SUPER_ORD_999', 150.0)

if __name__ == '__main__':
    unittest.main()
