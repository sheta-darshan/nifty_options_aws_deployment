#!/usr/bin/env python3
"""
send_daily_digest.py
Standalone tool to generate and send the Daily 3:35 PM PnL & Risk Digest via Telegram/Slack.
Can be run manually, via Windows Task Scheduler, or cron.

Usage:
    ..\\venv\\Scripts\\python.exe send_daily_digest.py [--preview]
"""

import sys
import argparse
import logging
from trading_bot.config import Config
from trading_bot.alerts import AlertManager
from trading_bot.manager import ThreadedBotManager

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Generate and send Daily PnL & Risk Digest.")
    parser.add_argument("--preview", action="store_true", help="Print digest to terminal without sending webhook alert.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("DailyDigestCLI")

    config = Config()
    alert_mgr = AlertManager(config.ALERT_WEBHOOK_URL, logger, source_ip=config.SOURCE_IP, proxy_url=config.PROXY_URL)
    
    manager = ThreadedBotManager(config, logger, alert_mgr)

    logger.info("Generating Daily PnL & Risk Digest...")
    digest_text = manager.generate_daily_digest()

    print("\n" + "=" * 50)
    print("DAILY PnL & RISK DIGEST PREVIEW")
    print("=" * 50)
    print(digest_text)
    print("=" * 50 + "\n")

    if args.preview:
        logger.info("[PREVIEW MODE] Alert was not dispatched to webhook.")
    else:
        logger.info("Dispatching digest to Webhook / Telegram...")
        manager.send_daily_digest()
        logger.info("Done.")

if __name__ == "__main__":
    main()
