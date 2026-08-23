"""
Integration tests for API wrapper resilience.

Tests the full retry, rate-limiting, and error handling pipeline
without making real API calls to DhanHQ.
"""
import unittest
from unittest.mock import patch, MagicMock
import requests
import time

from tests.helpers import build_mock_config, build_mock_logger
from trading_bot.api_wrapper import DhanAPIWrapper


class TestAPIWrapperIntegration(unittest.TestCase):
    """Integration tests for DhanAPIWrapper with mocked HTTP responses."""

    def setUp(self):
        self.config = build_mock_config()
        self.logger = build_mock_logger()
        self.wrapper = DhanAPIWrapper(
            client_id="test_client",
            api_token="test_token",
            config=self.config,
            logger=self.logger,
            account_type="primary",
            source_ip=None,
            proxy_url=None
        )
        # Reset global failure counter so tests are isolated
        DhanAPIWrapper._consecutive_failures = 0

    def _make_mock_response(self, status_code=200, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {"status": "ok"}
        return resp

    def test_successful_request_returns_json(self):
        """A 200 response with valid JSON should return the parsed payload."""
        mock_call = MagicMock(return_value={"status": "success", "data": {"price": 100}})
        with patch.object(self.wrapper, "_make_request", wraps=self.wrapper._make_request):
            result = self.wrapper._make_request(mock_call)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["price"], 100)

    def test_retry_on_429_rate_limit(self):
        """429 status triggers circuit breaker + retry path."""
        call_count = {"n": 0}
        def fake_api():
            call_count["n"] += 1
            if call_count["n"] <= 2:
                return {"status": "error", "errorMessage": "Too many requests"}
            return {"status": "success", "data": {"ok": True}}
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch.object(self.wrapper.rate_limiter, "trigger_circuit_breaker"):
                with patch("trading_bot.api_wrapper.time.sleep"):
                    with patch("trading_bot.api_wrapper.NetworkContext"):
                        result = self.wrapper._make_request(fake_api)
        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(call_count["n"], 3)

    def test_retry_on_500_server_error_then_success(self):
        """Network exceptions should be retried up to MAX_RETRIES."""
        call_count = {"n": 0}
        def fake_api():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("server down")
            return {"status": "success", "data": {"ok": True}}
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch("trading_bot.api_wrapper.time.sleep"):
                with patch("trading_bot.api_wrapper.NetworkContext"):
                    result = self.wrapper._make_request(fake_api)
        self.assertEqual(result["status"], "success")

    def test_retry_exhaustion_returns_none(self):
        """If every attempt fails, _make_request should return None without raising."""
        def fake_api():
            raise ConnectionError("permanent failure")
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch("trading_bot.api_wrapper.time.sleep"):
                with patch("trading_bot.api_wrapper.NetworkContext"):
                    result = self.wrapper._make_request(fake_api)
        self.assertIsNone(result)

    def test_4xx_non_retryable_returns_none(self):
        """input_exception (DH-905) is permanent; no retry."""
        def fake_api():
            return {"status": "error", "errorMessage": "DH-905 input_exception invalid data"}
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch("trading_bot.api_wrapper.NetworkContext"):
                result = self.wrapper._make_request(fake_api)
        self.assertIsNone(result)

    def test_auth_failure_triggers_token_reload(self):
        """Token-expired error should attempt reload then retry."""
        self.config.reload_api_token = MagicMock(return_value=False)
        def fake_api():
            return {"status": "error", "errorMessage": "Token expired"}
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch("trading_bot.api_wrapper.NetworkContext"):
                result = self.wrapper._make_request(fake_api)
        # Token reload failed, so the function should return None (no infinite loop)
        self.assertIsNone(result)

    def test_circuit_breaker_raises_after_max_consecutive_failures(self):
        """After MAX_CONSECUTIVE_FAILURES, a RuntimeError should be raised."""
        DhanAPIWrapper._consecutive_failures = DhanAPIWrapper._MAX_CONSECUTIVE_FAILURES - 1
        def fake_api():
            # Wrapper checks for "connect" or "timeout" substrings before
            # incrementing the consecutive-failure counter.
            raise ConnectionError("unable to connect to remote host")
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch("trading_bot.api_wrapper.time.sleep"):
                with patch("trading_bot.api_wrapper.NetworkContext"):
                    with self.assertRaises(RuntimeError):
                        self.wrapper._make_request(fake_api)

    def test_place_order_success(self):
        """Successful place_order should return the broker response with orderId."""
        self.wrapper.dhan.place_order = MagicMock(
            return_value={"status": "success", "orderId": "ORD123", "orderStatus": "PENDING"}
        )
        result = self.wrapper.place_order(
            security_id="12345",
            transaction_type="BUY",
            quantity=25,
            exchange_segment="NSE_FNO",
            order_type="MARKET",
            product_type="MARGIN"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["orderId"], "ORD123")
        self.assertIn("correlationId", result)
        self.assertEqual(result["retry_attempts"], 1)

    def test_place_order_non_retryable_error(self):
        """Insufficient-funds error should return None without retry."""
        self.wrapper.dhan.place_order = MagicMock(
            side_effect=Exception("insufficient funds in account")
        )
        result = self.wrapper.place_order(
            security_id="12345",
            transaction_type="BUY",
            quantity=25
        )
        self.assertIsNone(result)

    def test_place_order_retry_then_success(self):
        """Transient error followed by success should succeed on retry."""
        # Mock at the _make_request level to isolate place_order retry logic
        # from api_wrapper's internal retry logic.
        call_count = {"n": 0}
        def fake_make_request(api_call, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("network glitch")
            return {"status": "success", "orderId": "ORD456", "orderStatus": "TRADED"}

        with patch.object(self.wrapper, "_make_request", side_effect=fake_make_request):
            with patch("trading_bot.api_wrapper.time.sleep"):
                result = self.wrapper.place_order(
                    security_id="12345",
                    transaction_type="SELL",
                    quantity=25
                )
        self.assertIsNotNone(result)
        self.assertEqual(result["orderId"], "ORD456")
        # First call raised, second succeeded -> attempt index 2
        self.assertEqual(result["retry_attempts"], 2)

    def test_get_positions_returns_list(self):
        """get_positions should unwrap the data envelope."""
        self.wrapper.dhan.get_positions = MagicMock(
            return_value={"status": "success", "data": [
                {"securityId": "1", "netQty": 25},
                {"securityId": "2", "netQty": -15}
            ]}
        )
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch("trading_bot.api_wrapper.NetworkContext"):
                positions = self.wrapper.get_positions()
        self.assertEqual(len(positions), 2)

    def test_cancel_order_success(self):
        """cancel_order should return True on success."""
        self.wrapper.dhan.cancel_order = MagicMock(
            return_value={"status": "success", "orderStatus": "CANCELLED"}
        )
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch("trading_bot.api_wrapper.NetworkContext"):
                result = self.wrapper.cancel_order("ORD123")
        self.assertTrue(result)

    def test_cancel_order_failure(self):
        """cancel_order should return False on failure."""
        self.wrapper.dhan.cancel_order = MagicMock(
            return_value={"status": "error", "orderStatus": "REJECTED"}
        )
        with patch.object(self.wrapper.rate_limiter, "wait_if_needed"):
            with patch("trading_bot.api_wrapper.NetworkContext"):
                result = self.wrapper.cancel_order("ORD999")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
