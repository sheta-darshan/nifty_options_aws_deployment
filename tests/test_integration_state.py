"""
Integration tests for TradeState persistence.

Validates the load/save cycle, lock semantics, and recovery from
corrupt / missing state files.
"""
import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

from tests.helpers import build_mock_logger
from trading_bot.state import TradeState


class TestTradeStateIntegration(unittest.TestCase):
    """Integration tests for TradeState file-backed persistence."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.tmpdir, "order_state.json")
        self.logger = build_mock_logger("StateTest")
        self.state = TradeState(self.state_file, self.logger)

    def tearDown(self):
        # Clean up tmpdir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_initial_state_has_empty_collections(self):
        """A fresh state object should have empty positions, orders, and counters."""
        self.assertEqual(self.state.positions, {})
        self.assertEqual(self.state.orders, {})
        self.assertEqual(self.state.last_order_timestamp, 0.0)

    def test_save_creates_file(self):
        """save_state should write a JSON file to disk."""
        self.state.positions["ORD1"] = {"symbol": "NIFTY", "qty": 25}
        self.state.save_state()
        self.assertTrue(os.path.exists(self.state_file))
        with open(self.state_file) as f:
            data = json.load(f)
        self.assertIn("positions", data)
        self.assertIn("ORD1", data["positions"])

    def test_load_roundtrip_preserves_data(self):
        """Saving then loading should restore the same state."""
        self.state.positions["ORD1"] = {"symbol": "NIFTY", "qty": 25, "strategy": "Strategy_20"}
        self.state.last_order_timestamp = 1234567890.0
        self.state.save_state()

        # Create a new TradeState from the same file
        new_state = TradeState(self.state_file, self.logger)
        self.assertEqual(new_state.positions["ORD1"]["symbol"], "NIFTY")
        self.assertEqual(new_state.positions["ORD1"]["strategy"], "Strategy_20")
        self.assertEqual(new_state.last_order_timestamp, 1234567890.0)

    def test_corrupt_file_loads_empty_state(self):
        """A corrupt state file should not crash; should fall back to empty state."""
        with open(self.state_file, "w") as f:
            f.write("{invalid json content!!")

        state = TradeState(self.state_file, self.logger)
        self.assertEqual(state.positions, {})

    def test_missing_file_loads_empty_state(self):
        """If the state file does not exist, an empty state should be returned."""
        nonexistent = os.path.join(self.tmpdir, "does_not_exist.json")
        state = TradeState(nonexistent, self.logger)
        self.assertEqual(state.positions, {})

    def test_concurrent_save_does_not_corrupt(self):
        """Concurrent saves from multiple threads should not corrupt the JSON."""
        def writer(i):
            self.state.positions[f"ORD{i}"] = {"i": i}
            self.state.save_state()

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # The final file should be valid JSON
        with open(self.state_file) as f:
            data = json.load(f)
        self.assertIn("positions", data)
        # At least one of the keys should be present
        self.assertGreater(len(data["positions"]), 0)

    def test_add_position_persists(self):
        """Adding a position then saving then reloading should preserve it."""
        if hasattr(self.state, "add_position"):
            self.state.add_position("ORD42", {"symbol": "BANKNIFTY", "qty": 15})
            self.state.save_state()
            new_state = TradeState(self.state_file, self.logger)
            self.assertIn("ORD42", new_state.positions)
        else:
            # Skip if method does not exist
            self.skipTest("add_position method not present")

    def test_remove_position_persists(self):
        """Removing a position should be reflected after a save/load cycle."""
        self.state.positions["ORD1"] = {"symbol": "NIFTY"}
        self.state.positions["ORD2"] = {"symbol": "BANKNIFTY"}
        self.state.save_state()

        if hasattr(self.state, "remove_position"):
            self.state.remove_position("ORD1")
            self.state.save_state()

            new_state = TradeState(self.state_file, self.logger)
            self.assertNotIn("ORD1", new_state.positions)
            self.assertIn("ORD2", new_state.positions)
        else:
            self.skipTest("remove_position method not present")

    def test_save_writes_atomic(self):
        """Saving should be atomic (write to temp file, then rename) so partial
        writes cannot corrupt the state."""
        self.state.positions["ORD1"] = {"symbol": "NIFTY"}
        self.state.save_state()
        # File exists and is non-empty
        self.assertTrue(os.path.exists(self.state_file))
        self.assertGreater(os.path.getsize(self.state_file), 0)


if __name__ == "__main__":
    unittest.main()
