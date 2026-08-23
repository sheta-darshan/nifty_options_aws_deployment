"""
Conflict metrics tracker for multi-strategy live trading.

Tracks every blocking event that prevents a strategy from placing an order.
This is critical for diagnosing "why didn't my strategy trade?" in production.

Two types of conflicts:
- ISOLATED: The block only affects the strategy itself (latency lock, allowed_actions)
- CROSS-STRATEGY: One strategy consumes a shared resource that blocks another
  (daily limit, max active on account, etc.)
"""
import json
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class BlockingEvent:
    """A single record of a signal that was blocked."""
    timestamp: float
    instrument: str
    strategy: str
    signal: str
    gate: str  # e.g., "daily_limit", "max_active", "latency_lock"
    reason: str
    is_cross_strategy: bool  # True if another strategy caused this block
    blocking_strategy: Optional[str] = None  # Which strategy caused the cross-strategy block

    def to_dict(self):
        return asdict(self)


class ConflictMetrics:
    """
    Singleton-style tracker for blocking events across the live trading bot.

    Usage:
        metrics = ConflictMetrics.get_instance()
        metrics.record_block(instrument="NIFTY", strategy="Strategy_10",
                            signal="BUY", gate="daily_limit",
                            reason="Account X reached daily limit (3/3)",
                            is_cross_strategy=True,
                            blocking_strategy="Strategy_3")

        # Periodically (or on shutdown) dump to disk for analysis
        metrics.dump_to_file("conflict_report.json")
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._events: List[BlockingEvent] = []
        self._counter_lock = threading.Lock()
        # gate -> count (e.g. "daily_limit": 5)
        self._gate_counts: Dict[str, int] = defaultdict(int)
        # (strategy, gate) -> count
        self._strategy_gate_counts: Dict[tuple, int] = defaultdict(int)
        # (strategy_A, strategy_B) -> count of A blocked by B
        self._cross_strategy_conflicts: Dict[tuple, int] = defaultdict(int)
        # strategy -> count of executed signals (for ratio)
        self._executed_count: Dict[str, int] = defaultdict(int)
        self._attempted_count: Dict[str, int] = defaultdict(int)

    @classmethod
    def get_instance(cls):
        """Get the shared singleton instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton (used by tests)."""
        with cls._lock:
            cls._instance = None

    def record_attempt(self, strategy: str):
        """Record that a signal was attempted by a strategy."""
        with self._counter_lock:
            self._attempted_count[strategy] += 1

    def record_executed(self, strategy: str):
        """Record that a signal resulted in an order being placed."""
        with self._counter_lock:
            self._executed_count[strategy] += 1

    def record_block(self, instrument: str, strategy: str, signal: str,
                     gate: str, reason: str,
                     is_cross_strategy: bool = False,
                     blocking_strategy: Optional[str] = None):
        """Record a blocking event."""
        event = BlockingEvent(
            timestamp=time.time(),
            instrument=instrument,
            strategy=strategy,
            signal=signal,
            gate=gate,
            reason=reason,
            is_cross_strategy=is_cross_strategy,
            blocking_strategy=blocking_strategy,
        )
        with self._counter_lock:
            self._events.append(event)
            self._gate_counts[gate] += 1
            self._strategy_gate_counts[(strategy, gate)] += 1
            if is_cross_strategy and blocking_strategy and blocking_strategy != strategy:
                self._cross_strategy_conflicts[(strategy, blocking_strategy)] += 1

    def get_summary(self) -> Dict:
        """Return a summary dict suitable for logging or dashboard."""
        with self._counter_lock:
            return self._summary_snapshot()

    def get_cross_strategy_conflicts(self) -> List[Dict]:
        """Return list of cross-strategy conflicts sorted by severity."""
        with self._counter_lock:
            return sorted(
                [{"blocked": a, "by": b, "count": c}
                 for (a, b), c in self._cross_strategy_conflicts.items()],
                key=lambda x: x["count"], reverse=True
            )

    def dump_to_file(self, filepath: str):
        """Dump all events + summary to a JSON file for post-mortem analysis."""
        with self._counter_lock:
            # Snapshot inside the lock to avoid deadlock with get_summary()
            payload = {
                "summary": self._summary_snapshot(),
                "events": [e.to_dict() for e in self._events],
            }
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(payload, f, indent=2)

    def _summary_snapshot(self) -> Dict:
        """Compute summary without re-acquiring the lock. Caller must hold _counter_lock."""
        block_rates = {}
        for strat, attempted in self._attempted_count.items():
            executed = self._executed_count.get(strat, 0)
            blocked = attempted - executed
            block_rates[strat] = {
                "attempted": attempted,
                "executed": executed,
                "blocked": blocked,
                "block_rate": round(blocked / attempted, 3) if attempted > 0 else 0.0,
            }
        return {
            "total_events": len(self._events),
            "gate_counts": dict(self._gate_counts),
            "strategy_block_rates": block_rates,
            "cross_strategy_conflicts": [
                {"blocked": a, "by": b, "count": c}
                for (a, b), c in self._cross_strategy_conflicts.items()
            ],
        }


# Convenience function for module-level access
_default_instance: Optional[ConflictMetrics] = None


def get_metrics() -> ConflictMetrics:
    """Get the default metrics instance."""
    global _default_instance
    if _default_instance is None:
        _default_instance = ConflictMetrics.get_instance()
    return _default_instance


def reset_metrics():
    """Reset metrics (for tests)."""
    global _default_instance
    ConflictMetrics.reset_instance()
    _default_instance = None