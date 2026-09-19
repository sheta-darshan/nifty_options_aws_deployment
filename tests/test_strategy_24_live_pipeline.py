import os
import json
import unittest
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, time as dt_time

from trading_bot.config import Config
from trading_bot.data_pipeline import process_market_data, get_all_latest_signals
from stock_selection.select_prebreakout import get_security_id_map


class TestStrategy24LivePipeline(unittest.TestCase):
    """
    Validates end-to-end live bot readiness for Strategy 24 and Pre-Breakout rotated stocks.
    """

    def test_security_id_cache_lookup(self):
        """Asserts that all rotated candidate stocks resolve to valid Dhan security IDs."""
        sec_map = get_security_id_map()
        self.assertTrue(len(sec_map) > 1000, "Security ID cache should contain thousands of NSE stocks.")
        
        # Test known symbols
        self.assertIn("SHINDL", sec_map)
        self.assertIn("SAFARI", sec_map)
        self.assertIn("OIL", sec_map)
        self.assertEqual(sec_map["SHINDL"], "762904")
        self.assertEqual(sec_map["SAFARI"], "13035")
        self.assertEqual(sec_map["OIL"], "17438")

    def test_instruments_json_integrity(self):
        """Asserts that instruments.json contains valid security_id, lot_size, and Strategy_24 configs."""
        config = Config()
        rotated = [k for k, v in config.INSTRUMENTS.items() if v.get("rotated_prebreakout")]
        self.assertTrue(len(rotated) > 0, "At least one pre-breakout stock should be rotated into INSTRUMENTS")
        for sym in rotated:
            instr = config.INSTRUMENTS[sym]
            self.assertIn("security_id", instr, f"{sym} must have security_id")
            self.assertIsInstance(instr["security_id"], (int, str))
            self.assertTrue(int(instr["security_id"]) > 0, f"{sym} security_id must be positive")
            self.assertEqual(instr.get("strategy"), "Strategy_24")
            self.assertEqual(instr.get("exit_mode"), "POINTS")
            self.assertIn(instr.get("execution_mode"), ["STOCK", "OPTION"], f"{sym} execution_mode must be STOCK or OPTION")
            
            if instr.get("execution_mode") == "OPTION":
                self.assertTrue(instr.get("lot_size", 0) > 1, f"{sym} option lot_size must be > 1")
                self.assertEqual(instr.get("exchange_segment"), "NSE_FNO")
                self.assertTrue(instr.get("points_sl_buy", 0) > 0)
                self.assertTrue(instr.get("points_target_buy", 0) > 0)
            else:
                self.assertTrue(instr.get("stock_qty_override", 0) > 0)
                self.assertEqual(instr.get("exchange_segment"), "NSE_EQ")
                if instr.get("direction") == "SELL":
                    self.assertTrue(instr.get("points_sl_sell", 0) > 0)
                    self.assertTrue(instr.get("points_target_sell", 0) > 0)
                else:
                    self.assertTrue(instr.get("points_sl_buy", 0) > 0)
                    self.assertTrue(instr.get("points_target_buy", 0) > 0)

    def test_early_run_start_for_strategy_24(self):
        """Asserts that RUN_START is set to 09:15 AM so opening breakouts are not missed."""
        config = Config()
        self.assertEqual(config.RUN_START, dt_time(9, 15), "RUN_START must be 09:15:00 for Strategy 24")

    def test_data_pipeline_strategy_24_execution(self):
        """Asserts that process_market_data generates Signal_Strategy_24 when trigger price is breached."""
        import logging
        logger = logging.getLogger("test_pipeline")
        config = Config()

        # Find an active rotated BUY stock from instruments.json
        rotated_buys = [k for k, v in config.INSTRUMENTS.items() if v.get("rotated_prebreakout") and v.get("direction") == "BUY"]
        test_sym = rotated_buys[0] if rotated_buys else "TEST_BUY"
        trig = float(config.INSTRUMENTS.get(test_sym, {}).get("trigger_price", 100.0))

        tz = pytz.timezone("Asia/Kolkata")
        # Provide 2 days of data so daily indicators and trigger levels resolve properly
        dates_d1 = pd.date_range("2026-09-17 09:15", "2026-09-17 15:30", freq="1min", tz=tz)
        dates_d2 = pd.date_range("2026-09-18 09:15", "2026-09-18 09:45", freq="1min", tz=tz)
        dates = dates_d1.append(dates_d2)

        base_px = trig - 5.0
        df = pd.DataFrame({
            'open': [base_px] * len(dates),
            'high': [base_px + 1.0] * len(dates),
            'low': [base_px - 1.0] * len(dates),
            'close': [base_px] * len(dates),
            'volume': [5000.0] * len(dates)
        }, index=dates)

        # On Day 2 (bar indices 10 to 14, i.e. 09:25-09:29), simulate sustained breakout above trigger with strong close
        for m in range(10, 15):
            b_idx = dates[len(dates_d1) + m]
            df.loc[b_idx, 'open'] = trig + 0.5
            df.loc[b_idx, 'high'] = trig + 2.0
            df.loc[b_idx, 'close'] = trig + 1.8
            df.loc[b_idx, 'volume'] = 10000.0

        processed = process_market_data(df, config, logger, instrument_name=test_sym)
        self.assertIn("Signal_Strategy_24", processed.columns)
        self.assertEqual(processed['Signal_Strategy_24'].sum(), 1, "Strategy 24 must generate exactly 1 breakout signal")


if __name__ == '__main__':
    unittest.main()
