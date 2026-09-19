import unittest
from unittest.mock import MagicMock
import logging

class TestMarginFallbackSettlement(unittest.TestCase):
    def setUp(self):
        import threading
        from trading_bot.instrument_bot import InstrumentBot
        
        self.bot = InstrumentBot.__new__(InstrumentBot)
        threading.Thread.__init__(self.bot)
        self.bot.name = "NIFTY"
        self.bot.logger = logging.getLogger("test_logger")
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_verify_order_settlement_rejected_rms(self):
        """Verify that an order in TRANSIT is identified as REJECTED when Dhan OMS rejects it."""
        mock_acc_api = MagicMock()
        mock_acc_api.dhan = MagicMock()
        mock_acc_api._make_request.return_value = {
            'status': 'success',
            'data': {
                'orderId': '32326091725371',
                'orderStatus': 'REJECTED',
                'omsErrorDescription': 'Margin shortfall: Required 260000 Available 180000',
                'remarks': 'RMS:Rule: Check margin failed'
            }
        }

        initial_resp = {
            'orderId': '32326091725371',
            'orderStatus': 'TRANSIT'
        }

        verified_resp = self.bot._verify_order_settlement(mock_acc_api, initial_resp, wait_seconds=0.0)

        self.assertEqual(verified_resp['orderStatus'], 'REJECTED')
        self.assertTrue(verified_resp.get('failed'))
        self.assertIn('Margin shortfall', verified_resp.get('omsErrorDescription', ''))
        self.assertTrue(self.bot._is_margin_rejection(verified_resp['omsErrorDescription'], verified_resp))

    def test_verify_order_settlement_confirmed_pending(self):
        """Verify that an order in TRANSIT confirmed as PENDING remains successful."""
        mock_acc_api = MagicMock()
        mock_acc_api.dhan = MagicMock()
        mock_acc_api._make_request.return_value = {
            'status': 'success',
            'data': {
                'orderId': '34326091713372',
                'orderStatus': 'PENDING'
            }
        }

        initial_resp = {
            'orderId': '34326091713372',
            'orderStatus': 'TRANSIT'
        }

        verified_resp = self.bot._verify_order_settlement(mock_acc_api, initial_resp, wait_seconds=0.0)

        self.assertEqual(verified_resp['orderStatus'], 'PENDING')
        self.assertFalse(verified_resp.get('failed', False))

    def test_verify_order_settlement_confirmed_traded(self):
        """Verify that an order in TRANSIT confirmed as TRADED remains successful."""
        mock_acc_api = MagicMock()
        mock_acc_api.dhan = MagicMock()
        mock_acc_api._make_request.return_value = {
            'status': 'success',
            'data': [{
                'orderId': '22326091725771',
                'orderStatus': 'TRADED'
            }]
        }

        initial_resp = {
            'orderId': '22326091725771',
            'orderStatus': 'TRANSIT'
        }

        verified_resp = self.bot._verify_order_settlement(mock_acc_api, initial_resp, wait_seconds=0.0)

        self.assertEqual(verified_resp['orderStatus'], 'TRADED')
        self.assertFalse(verified_resp.get('failed', False))

    def test_margin_keywords_recognition(self):
        """Verify that diverse RMS error descriptions correctly trigger margin fallback flag."""
        rejection_cases = [
            "Margin shortfall: Required 260000 Available 180000",
            "Insufficient funds in account",
            "RMS:Rule: Margin limit exceeded",
            "Not enough balance for this transaction"
        ]
        for reason in rejection_cases:
            self.assertTrue(self.bot._is_margin_rejection(reason), f"Failed to identify: {reason}")

    def test_end_to_end_margin_fallback_execution(self):
        """
        Simulate the exact Sep 17 live event:
        1. 2 lots placed -> returns TRANSIT
        2. Fast OMS verification reveals REJECTED due to margin shortfall
        3. Fallback ladder triggers -> downscales to 1 lot
        4. 1-lot order returns TRANSIT -> verifies as PENDING/TRADED -> succeeds!
        """
        mock_acc_api = MagicMock()
        mock_acc_api.dhan = MagicMock()

        # Step 1: Initial call returns TRANSIT, but get_order_by_id returns REJECTED
        def place_entry_side_effect(**kwargs):
            qty = kwargs.get('quantity')
            if qty == 130:
                return {'orderId': '32326091725371', 'orderStatus': 'TRANSIT'}
            elif qty == 65:
                return {'orderId': '32326091799999', 'orderStatus': 'TRANSIT'}
            return {'orderStatus': 'FAILED'}

        mock_acc_api.place_entry_order.side_effect = place_entry_side_effect

        def make_request_side_effect(func, **kwargs):
            oid = kwargs.get('order_id')
            if oid == '32326091725371':
                return {
                    'status': 'success',
                    'data': {
                        'orderId': oid,
                        'orderStatus': 'REJECTED',
                        'omsErrorDescription': 'Margin shortfall: Required 260000 Available 180000'
                    }
                }
            elif oid == '32326091799999':
                return {
                    'status': 'success',
                    'data': {
                        'orderId': oid,
                        'orderStatus': 'PENDING'
                    }
                }
            return None

        mock_acc_api._make_request.side_effect = make_request_side_effect

        # Simulate execution
        dispatch = {
            'acc_name': 'Primary_Account',
            'acc_api': mock_acc_api,
            'acc_qty': 130, # 2 lots
            'base_qty': 65,  # 1 lot
            'lot_size': 65,
            'limit_price': 119.0,
            'api_opt_tp': 45.0,
            'api_opt_sl': 74.0,
            'api_opt_trail': 0.0,
            'inst_product_type': 'MARGIN'
        }

        # Step 1: Place 2 lots
        resp = mock_acc_api.place_entry_order(
            security_id='56984',
            transaction_type='SELL',
            quantity=dispatch['acc_qty'],
            order_type='LIMIT',
            price=dispatch['limit_price'],
            target_points=dispatch['api_opt_tp'],
            sl_points=dispatch['api_opt_sl'],
            trailing_jump=dispatch['api_opt_trail'],
            exchange_segment='NSE_FNO',
            product_type=dispatch['inst_product_type'],
            ref_price=120.2
        )

        # Fast OMS verification
        resp = self.bot._verify_order_settlement(dispatch['acc_api'], resp, wait_seconds=0.0)
        is_success = resp and not resp.get('failed', False) and resp.get('orderStatus') in ['PENDING', 'TRANSIT', 'TRADED', 'SUBMITTED', 'SUCCESS']

        self.assertFalse(is_success)
        self.assertEqual(resp['orderStatus'], 'REJECTED')

        # Fallback ladder
        reject_reason = resp.get('omsErrorDescription')
        self.assertTrue(self.bot._is_margin_rejection(reject_reason, resp))

        lot_unit = dispatch.get('lot_size', 1)
        fallback_candidates = []
        if dispatch['acc_qty'] > dispatch.get('base_qty', 0) and dispatch.get('base_qty', 0) > 0:
            fallback_candidates.append(dispatch['base_qty'])

        self.assertEqual(fallback_candidates, [65])

        for fallback_qty in fallback_candidates:
            fb_resp = dispatch['acc_api'].place_entry_order(
                security_id='56984',
                transaction_type='SELL',
                quantity=fallback_qty,
                order_type='LIMIT',
                price=dispatch['limit_price'],
                target_points=dispatch['api_opt_tp'],
                sl_points=dispatch['api_opt_sl'],
                trailing_jump=dispatch['api_opt_trail'],
                exchange_segment='NSE_FNO',
                product_type=dispatch['inst_product_type'],
                ref_price=120.2
            )
            fb_resp = self.bot._verify_order_settlement(dispatch['acc_api'], fb_resp, wait_seconds=0.0)
            if fb_resp and not fb_resp.get('failed', False) and fb_resp.get('orderStatus') in ['PENDING', 'TRANSIT', 'TRADED', 'SUBMITTED', 'SUCCESS']:
                resp = fb_resp
                dispatch['acc_qty'] = fallback_qty
                is_success = True
                break

        self.assertTrue(is_success)
        self.assertEqual(dispatch['acc_qty'], 65)
        self.assertEqual(resp['orderStatus'], 'PENDING')
        self.assertEqual(resp['orderId'], '32326091799999')

if __name__ == '__main__':
    unittest.main()
