import os
import sys
import time
import logging
import threading
import requests
import pytz
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# Export modules for backward compatibility (Facade Layer)
from trading_bot.config import Config
from trading_bot.alerts import AlertManager
from trading_bot.api_wrapper import DhanAPIWrapper, safe_int
from trading_bot.account_manager import MultiAccountManager, CentralizedPositionManager
from trading_bot.state import TradeState
from trading_bot.data_pipeline import (
    process_market_data,
    get_latest_signal,
    load_security_master,
    choose_option_instruments,
    choose_strategy_instruments,
    log_trade_event,
    count_active_option_orders,
    wait_for_next_candle,
    get_trade_actions,
    fetch_candle_with_retry,
    get_today_trade_count
)
from trading_bot.instrument_bot import InstrumentBot
from trading_bot.manager import ThreadedBotManager

# Keep setup_logging here for direct calls from launch script and backtest engine
def setup_logging(config: Config):
    """Configure logging - output to stdout for systemd journalctl"""
    logger = logging.getLogger("live-dhan-bot")
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Set logger level
    logger.setLevel(config.LOG_LEVEL)
    
    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.LOG_LEVEL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger (avoids duplicate logs)
    logger.propagate = False
    
    return logger

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    try:
        config = Config()
        logger = setup_logging(config)
        
        # Register SIGTERM / SIGINT handler for clean systemd shutdowns
        import signal
        def handle_shutdown_signal(signum, frame):
            logger.warning(f"[SYSTEM] Received signal {signum}. Triggering clean shutdown...")
            raise KeyboardInterrupt
            
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        
        alert_manager = AlertManager(config.ALERT_WEBHOOK_URL, logger, source_ip=config.SOURCE_IP, proxy_url=config.PROXY_URL)
        
        # Detect active strategies dynamically on startup
        active_strats = []
        for attr in dir(config):
            if attr.startswith("ENABLE_STRATEGY_") and getattr(config, attr, False):
                strat_num = attr.split("_")[-1]
                active_strats.append(f"Strategy {strat_num}")
        active_strats_str = ", ".join(active_strats) if active_strats else "None"
        
        # Send Telegram alert on bot startup
        alert_manager.send_alert(
            message=f"Live Trading Bot has successfully started.\nActive Strategies: {active_strats_str}",
            header="Bot Startup"
        )
        
        # We need to pass alert_manager into the main manager and subsequently API Wrappers
        manager = ThreadedBotManager(config, logger, alert_manager)
        manager.start()
        
    except Exception as e:
        print(f"[CRITICAL] Startup Failed: {e}", file=sys.stderr)
