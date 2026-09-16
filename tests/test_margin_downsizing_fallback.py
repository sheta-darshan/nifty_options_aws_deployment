import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

from trading_bot.instrument_bot import InstrumentBot
from trading_bot.api_wrapper import DhanAPIWrapper


class TestMarginDownsizingFallback(unittest.TestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_config.INSTRUMENTS = {
            'NIFTY': {
                'lot_size': 50,
                'fno_prefix': 'NIFTY',
                'strike_step': 50,
                'num_lots_sell': 2,
                'num_lots_high_conviction': 4,
                'enable_dynamic_conviction': True,
                'points_target_sell': 25.0,
                'points_target_high_conviction': 45.0,
                'points_sl_sell': 74.0,
                'product_type': 'MARGIN',
                'option_segment': 'NSE_FNO',
                'exit_mode': 'POINTS',
                'allowed_regimes_trend': ['NEUTRAL', 'RANGE'],
                'strategy_overrides': {}
            }
        }
        import pytz
        self.mock_config.TIMEZONE = pytz.timezone('Asia/Kolkata')
        self.mock_config.TRADE_LOG_CSV = 'test_trades.csv'
        self.mock_config.PRODUCT_TYPE = 'MARGIN'
        self.mock_config.EXIT_MODE = 'POINTS'

    def test_is_margin_rejection_detection(self):
        """Test _is_margin_rejection accurately identifies various broker margin error formats."""
        with patch.object(InstrumentBot, '__init__', lambda self, *args, **kwargs: None):
            bot = InstrumentBot()
            
            # Case 1: Dhan RMS margin shortfall string
            self.assertTrue(bot._is_margin_rejection("RMS:Rule: Margin Shortfall of Rs 85000.00", None))
            
            # Case 2: Insufficient funds in response dict
            resp1 = {'status': 'failure', 'remarks': 'Insufficient funds for trade'}
            self.assertTrue(bot._is_margin_rejection("", resp1))
            
            # Case 3: Nested data omsErrorDescription
            resp2 = {'orderStatus': 'REJECTED', 'data': {'omsErrorDescription': 'RMS: Insufficient balance'}}
            self.assertTrue(bot._is_margin_rejection("Order rejected", resp2))

            # Case 4: Non-margin error (e.g. Market closed / Invalid strike)
            resp3 = {'orderStatus': 'REJECTED', 'remarks': 'Exchange not available / market closed'}
            self.assertFalse(bot._is_margin_rejection("Exchange not available", resp3))

    def test_api_wrapper_returns_rejection_details_on_super_order_failure(self):
        """Test that place_super_order returns rejection dict with failed=True rather than None."""
        wrapper = DhanAPIWrapper(client_id="test_client", api_token="test_token", config=self.mock_config, logger=MagicMock())
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'orderStatus': 'REJECTED',
            'remarks': 'RMS:Rule: Margin Shortfall of Rs 50000.00'
        }
        
        with patch('requests.post', return_value=mock_response):
            result = wrapper.place_super_order(
                security_id="12345",
                transaction_type="SELL",
                quantity=200,
                price=100.0,
                target_price=55.0,
                stop_loss_price=174.0
            )
            
            self.assertIsNotNone(result)
            self.assertTrue(result.get('failed'))
            self.assertEqual(result.get('orderStatus'), 'REJECTED')
            self.assertIn('Margin Shortfall', result.get('remarks', ''))

    def test_instrument_bot_falls_back_to_base_qty_on_margin_rejection(self):
        """
        Test that when high-conviction order for 4 lots is rejected by Dhan due to margin shortfall,
        InstrumentBot automatically falls back and executes base size of 2 lots.
        """
        import threading
        def dummy_init(self, *args, **kwargs):
            threading.Thread.__init__(self)
        with patch.object(InstrumentBot, '__init__', dummy_init):
            bot = InstrumentBot()
            bot.name = 'NIFTY'
            bot.config = self.mock_config
            bot.logger = MagicMock()
            bot.alert_manager = MagicMock()
            bot.state = MagicMock()
            bot.state.lock = MagicMock()
            bot.state.positions = {}
            bot.state.add_order = MagicMock()
            bot.state.save_state = MagicMock()
            bot.daily_trade_counts = {}
            bot.daily_sl_counts = {}
            bot.TYPE = 'OPTION'
            bot.MAX_ACTIVE = 5
            bot.DAILY_LIMIT = 10
            bot._enforce_order_stagger = MagicMock()
            bot.get_strategy_instrument_config = MagicMock(return_value=self.mock_config.INSTRUMENTS['NIFTY'])
            bot.data_api = MagicMock()
            bot.data_api.get_ltp.return_value = 100.0
            
            # Setup spot DataFrame with Conviction = 2.0 (High Conviction)
            bot.df_spot = pd.DataFrame({
                'close': [24500.0],
                'Conviction': [2.0]
            })

            # Mock Order Manager and Executor
            mock_acc_api = MagicMock()
            
            # First call (4 lots = 200 qty) returns margin rejection
            # Second call (2 lots = 100 qty fallback) returns success
            rejection_response = {
                'orderStatus': 'REJECTED',
                'failed': True,
                'remarks': 'RMS:Rule: Margin Shortfall of Rs 90000.00'
            }
            success_response = {
                'orderStatus': 'TRANSIT',
                'orderId': 'BO_998877',
                'failed': False
            }
            mock_acc_api.place_entry_order.side_effect = [rejection_response, success_response]

            bot.order_manager = MagicMock()
            bot.order_manager.get_accounts.return_value = [{
                'name': 'Account_Main',
                'api': mock_acc_api,
                'config': {'global_multiplier': 1.0}
            }]
            
            # Mock executor to immediately run the callable
            class ImmediateExecutor:
                def submit(self, fn, *args, **kwargs):
                    class FakeFuture:
                        def result(self, timeout=None):
                            return fn(*args, **kwargs)
                    return FakeFuture()
            
            bot.order_manager.executor = ImmediateExecutor()
            bot.order_manager.position_manager.get_cached_positions.return_value = []
            bot._count_my_active_positions = MagicMock(return_value=0)

            # Invoke _place_batch
            item = {'id': '54321', 'symbol': 'NIFTY 24500 PE', 'security_id': '54321'}
            with patch('trading_bot.instrument_bot.log_trade_event') as mock_log:
                traded_accounts = bot._place_batch(
                    items=[item],
                    action='SELL',
                    leg_type='PE',
                    atr_val=15.0,
                    signal='SELL',
                    source='Strategy_22'
                )

                # Verify that 2 calls were made to place_entry_order
                self.assertEqual(mock_acc_api.place_entry_order.call_count, 2)
                
                # First call attempted 4 lots = 200 qty
                first_call_qty = mock_acc_api.place_entry_order.call_args_list[0][1]['quantity']
                self.assertEqual(first_call_qty, 200)
                
                # Second call fell back to base size 2 lots = 100 qty
                second_call_qty = mock_acc_api.place_entry_order.call_args_list[1][1]['quantity']
                self.assertEqual(second_call_qty, 100)

                # Verify that Account_Main succeeded and order state recorded 100 qty
                self.assertIn('Account_Main', traded_accounts)
                self.assertTrue(bot.state.add_order.called)
                recorded_order = bot.state.add_order.call_args[0][1]
                self.assertEqual(recorded_order['qty'], 100)
                self.assertEqual(recorded_order['order_id'], 'BO_998877')

                # Verify that alert_manager sent the Downsized alert
                self.assertTrue(bot.alert_manager.send_alert.called)
                all_alerts = [c[0][0] for c in bot.alert_manager.send_alert.call_args_list]
                self.assertTrue(any('[MARGIN DOWNSIZED]' in a and '2 lots' in a for a in all_alerts))


if __name__ == '__main__':
    unittest.main()
