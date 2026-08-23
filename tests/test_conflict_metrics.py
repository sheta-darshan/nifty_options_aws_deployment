"""
Tests for the ConflictMetrics singleton and blocking-event tracker.
"""
import json
import os
import tempfile
import threading
import unittest

from trading_bot.conflict_metrics import (
    ConflictMetrics,
    BlockingEvent,
    get_metrics,
    reset_metrics,
)


class TestConflictMetrics(unittest.TestCase):
    def setUp(self):
        reset_metrics()
        self.metrics = ConflictMetrics.get_instance()

    def tearDown(self):
        reset_metrics()

    def test_singleton_returns_same_instance(self):
        """ConflictMetrics must be a process-wide singleton."""
        a = ConflictMetrics.get_instance()
        b = ConflictMetrics.get_instance()
        self.assertIs(a, b)

    def test_record_block_increments_counters(self):
        """Recording a block must update gate_counts and strategy_gate_counts."""
        self.metrics.record_block(
            instrument="NIFTY", strategy="Strategy_10", signal="BUY",
            gate="daily_limit", reason="Account X reached 5/5",
            is_cross_strategy=True, blocking_strategy="Strategy_3"
        )
        summary = self.metrics.get_summary()
        self.assertEqual(summary["total_events"], 1)
        self.assertEqual(summary["gate_counts"]["daily_limit"], 1)

    def test_cross_strategy_conflict_recorded(self):
        """When a strategy is blocked by another, the cross-strategy counter increments."""
        self.metrics.record_block(
            instrument="NIFTY", strategy="Strategy_10", signal="BUY",
            gate="daily_limit", reason="Account X reached 5/5",
            is_cross_strategy=True, blocking_strategy="Strategy_3"
        )
        conflicts = self.metrics.get_cross_strategy_conflicts()
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["blocked"], "Strategy_10")
        self.assertEqual(conflicts[0]["by"], "Strategy_3")
        self.assertEqual(conflicts[0]["count"], 1)

    def test_isolated_block_not_counted_as_cross_strategy(self):
        """A latency_lock block (isolated to one strategy) should not be flagged cross-strategy."""
        self.metrics.record_block(
            instrument="NIFTY", strategy="Strategy_10", signal="BUY",
            gate="latency_lock", reason="Traded 3s ago",
            is_cross_strategy=False
        )
        conflicts = self.metrics.get_cross_strategy_conflicts()
        self.assertEqual(conflicts, [])

    def test_block_rate_calculation(self):
        """Block rate = blocked / attempted."""
        # Strategy_3: 3 attempts, 1 executed -> 2 blocked (66.7%)
        for _ in range(3):
            self.metrics.record_attempt("Strategy_3")
        self.metrics.record_executed("Strategy_3")
        self.metrics.record_block(
            instrument="NIFTY", strategy="Strategy_3", signal="BUY",
            gate="latency_lock", reason="Lock active"
        )
        self.metrics.record_block(
            instrument="NIFTY", strategy="Strategy_3", signal="BUY",
            gate="allowed_actions", reason="BUY not allowed"
        )
        summary = self.metrics.get_summary()
        s3 = summary["strategy_block_rates"]["Strategy_3"]
        self.assertEqual(s3["attempted"], 3)
        self.assertEqual(s3["executed"], 1)
        self.assertEqual(s3["blocked"], 2)
        self.assertEqual(s3["block_rate"], 0.667)

    def test_concurrent_recording_is_safe(self):
        """Multiple threads recording blocks concurrently should not corrupt state."""
        def worker(i):
            for j in range(100):
                self.metrics.record_block(
                    instrument="NIFTY", strategy=f"Strategy_{i}", signal="BUY",
                    gate="test_gate", reason=f"Block {j}"
                )

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        summary = self.metrics.get_summary()
        self.assertEqual(summary["total_events"], 500)

    def test_dump_to_file_creates_valid_json(self):
        """dump_to_file should produce a parseable JSON file with events + summary."""
        self.metrics.record_block(
            instrument="NIFTY", strategy="Strategy_10", signal="BUY",
            gate="daily_limit", reason="test"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "conflict.json")
            self.metrics.dump_to_file(path)
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                data = json.load(f)
            self.assertIn("summary", data)
            self.assertIn("events", data)
            self.assertEqual(len(data["events"]), 1)

    def test_self_block_not_counted_as_cross_strategy(self):
        """A strategy blocking itself should not be flagged as a cross-strategy conflict."""
        self.metrics.record_block(
            instrument="NIFTY", strategy="Strategy_10", signal="BUY",
            gate="max_active", reason="Strategy_10 already has 1 position",
            is_cross_strategy=True, blocking_strategy="Strategy_10"
        )
        conflicts = self.metrics.get_cross_strategy_conflicts()
        # Self-conflict should be excluded
        self.assertEqual(conflicts, [])

    def test_reset_instance_creates_fresh_state(self):
        """reset_instance must discard all recorded events."""
        self.metrics.record_block(
            instrument="NIFTY", strategy="Strategy_X", signal="BUY",
            gate="x", reason="y"
        )
        self.assertEqual(self.metrics.get_summary()["total_events"], 1)
        reset_metrics()
        new_metrics = ConflictMetrics.get_instance()
        self.assertEqual(new_metrics.get_summary()["total_events"], 0)


class TestBlockingEventDataclass(unittest.TestCase):
    def test_to_dict_serializable(self):
        """BlockingEvent.to_dict should produce JSON-serializable dict."""
        from time import time
        e = BlockingEvent(
            timestamp=time(), instrument="NIFTY", strategy="S3", signal="BUY",
            gate="g", reason="r", is_cross_strategy=False
        )
        d = e.to_dict()
        # Should be JSON-serializable
        json.dumps(d)


if __name__ == "__main__":
    unittest.main()
