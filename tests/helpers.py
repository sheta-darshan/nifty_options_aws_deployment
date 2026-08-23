"""
Shared test helpers for building mock Config and Logger instances.

These keep integration tests readable and consistent with the real
Config schema without loading the full environment / .env file.
"""
import logging
from unittest.mock import MagicMock


def build_mock_logger(name="TestLogger"):
    """Return a real logger that swallows output but still records calls."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def build_mock_config(**overrides):
    """Build a Config-like object with the attributes used by the trading_bot package.

    Any attribute accessed that wasn't explicitly set will return a MagicMock.
    """
    cfg = MagicMock()
    # Retry / HTTP settings
    cfg.MAX_RETRIES = overrides.get("MAX_RETRIES", 3)
    cfg.RETRY_BACKOFF = overrides.get("RETRY_BACKOFF", 2.0)
    cfg.REQUEST_TIMEOUT = overrides.get("REQUEST_TIMEOUT", 10)
    # Token reload behavior
    cfg.reload_api_token = MagicMock(return_value=False)
    cfg.API_TOKEN = "test_token"
    # Account-related
    cfg.ACCOUNTS_FILE = "accounts.json"
    # Security-id caches (empty by default; tests that need them populate them)
    cfg.master_cache_index = overrides.get("master_cache_index", {})
    cfg.sec_master_df = overrides.get("sec_master_df", None)
    return cfg


def build_mock_instrument_config(extra=None):
    """Return a dict that resembles a single entry from instruments.json."""
    base = {
        "lot_size": 25,
        "fno_prefix": "NIFTY",
        "max_active": 1,
        "daily_limit": 5,
        "strike_step": 50,
        "execution_mode": "OPTION",
        "option_strategy_mode": "DIRECT",
        "exit_mode": "ATR",
        "allowed_actions": ["BUY", "SELL"],
        "strategy_overrides": {},
    }
    if extra:
        base.update(extra)
    return base


def make_spot_candles(rows=30, start_price=23000.0, freq="1min"):
    """Create a tiny OHLCV dataframe suitable for signal-generation tests."""
    import pandas as pd
    import numpy as np
    idx = pd.date_range("2026-07-08 09:15", periods=rows, freq=freq)
    np.random.seed(42)
    closes = start_price + np.cumsum(np.random.randn(rows) * 5)
    df = pd.DataFrame({
        "open": closes + np.random.randn(rows),
        "high": closes + abs(np.random.randn(rows)) * 3,
        "low": closes - abs(np.random.randn(rows)) * 3,
        "close": closes,
        "volume": np.random.randint(500, 5000, size=rows),
    }, index=idx)
    return df
