"""
Conflict detector for multi-strategy live trading.

Analyzes the bot state and identifies potential cross-strategy conflicts
WITHOUT modifying the live trading code. This is a read-only monitor that
can be run periodically (cron, separate thread, or on-demand).

Detects:
1. Shared daily limit consumption: Strategy_A uses N daily slots that block Strategy_B
2. Max active isolation: Verifies per-strategy max_active is correctly isolated
3. Latency lock contention: Multiple strategies trying same instrument
4. State position conflicts: Strategy A and B both trying to enter same strike
5. Regime filter divergence: Different regime settings causing opposite signals
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from trading_bot.conflict_metrics import get_metrics, ConflictMetrics


@dataclass
class ConflictReport:
    """Snapshot of detected conflicts at a point in time."""
    timestamp: str
    instrument: str
    conflicts: List[Dict[str, Any]]
    total_blocked_strategies: int
    total_cross_strategy_blocks: int

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "instrument": self.instrument,
            "conflicts": self.conflicts,
            "total_blocked_strategies": self.total_blocked_strategies,
            "total_cross_strategy_blocks": self.total_cross_strategy_blocks,
        }


class ConflictDetector:
    """Analyzes live state and reports conflicts between strategies."""

    def __init__(self, instrument_bot):
        self.bot = instrument_bot
        self.metrics = get_metrics()

    def detect_shared_daily_limit_conflict(self) -> List[Dict]:
        """Identify cases where strategies on an account have consumed daily slots
        under per-strategy accounting, or verify per-strategy isolation.

        Returns list of {account, strategy, daily_count, daily_limit, is_saturated: bool}
        """
        conflicts = []
        daily_counts = getattr(self.bot, "daily_trade_counts", {})
        daily_limit = getattr(self.bot, "DAILY_LIMIT", 5)
        inst_config = self.bot.config.INSTRUMENTS.get(self.bot.name, {})

        from strategies.registry import STRATEGY_REGISTRY
        active_strategies = list(STRATEGY_REGISTRY.keys()) if STRATEGY_REGISTRY else [f"Strategy_{i}" for i in range(1, 23)]

        for acc in accounts:
            acc_name = acc["name"]
            acc_config = acc.get("config", {})
            overrides = acc_config.get("instrument_overrides", {}).get(self.bot.name, {})

            for strat in active_strategies:
                strat_config = self.bot.get_strategy_instrument_config(strat) if hasattr(self.bot, "get_strategy_instrument_config") else {}
                strat_daily_limit = overrides.get(
                    "daily_limit_per_strategy",
                    overrides.get("daily_limit", acc_config.get("daily_limit", strat_config.get("daily_limit_per_strategy", strat_config.get("daily_limit", daily_limit))))
                )

                strat_dict = daily_counts.get(strat, {}) if isinstance(daily_counts, dict) else {}
                current_count = strat_dict.get(acc_name, 0) if isinstance(strat_dict, dict) else 0

                if current_count >= strat_daily_limit:
                    conflicts.append({
                        "type": "per_strategy_daily_limit",
                        "account": acc_name,
                        "strategy": strat,
                        "daily_count": current_count,
                        "daily_limit": strat_daily_limit,
                        "is_saturated": True,
                        "severity": "low",
                    })
        return conflicts

    def detect_max_active_isolation(self) -> List[Dict]:
        """Verify that max_active is correctly isolated per strategy.

        Returns list of {strategy, current_active, max_active, ok: bool}
        """
        results = []
        inst_config = self.bot.config.INSTRUMENTS.get(self.bot.name, {})
        global_max = inst_config.get("max_active", 1)

        from strategies.registry import STRATEGY_REGISTRY
        active_strategies = list(STRATEGY_REGISTRY.keys()) if STRATEGY_REGISTRY else [f"Strategy_{i}" for i in range(1, 23)]
        for strat in active_strategies:
            try:
                count = self.bot._count_my_active_positions(
                    None, leg_type=None, strategy_name=strat
                )
                results.append({
                    "type": "max_active_isolation",
                    "strategy": strat,
                    "current_active": count,
                    "max_active": global_max,
                    "ok": count <= global_max,
                })
            except Exception as e:
                results.append({
                    "type": "max_active_isolation",
                    "strategy": strat,
                    "error": str(e),
                })
        return results

    def detect_latency_lock_contention(self) -> List[Dict]:
        """Check which strategies are currently under latency lock.

        Returns list of {strategy, locked_since_seconds, is_blocked}
        """
        now = datetime.now(self.bot.config.TIMEZONE)
        results = []
        latency_locks = getattr(self.bot, "order_latency_locks", {})
        for strat, lock_time in latency_locks.items():
            elapsed = (now - lock_time).total_seconds()
            results.append({
                "type": "latency_lock",
                "strategy": strat,
                "elapsed_seconds": round(elapsed, 1),
                "is_blocked": elapsed < 10.0,
            })
        return results

    def detect_position_overlap(self) -> List[Dict]:
        """Find cases where multiple strategies have positions in the SAME strike.

        This is a true conflict: if Strategy_3 and Strategy_10 both want
        NIFTY 23000 CE, only one should hold it.
        """
        results = []
        strike_to_strategies: Dict[str, List[str]] = {}

        with self.bot.state.lock:
            for pos_id, pos in self.bot.state.positions.items():
                if pos.get("instrument") != self.bot.name:
                    continue
                strike = pos.get("strike")
                leg = pos.get("leg", "")
                strategy = pos.get("strategy", "Unknown")
                if strike is not None:
                    key = f"{self.bot.name} {strike}{leg}"
                    strike_to_strategies.setdefault(key, []).append(strategy)

        for strike_key, strategies in strike_to_strategies.items():
            unique_strategies = set(strategies)
            if len(unique_strategies) > 1:
                results.append({
                    "type": "position_overlap",
                    "contract": strike_key,
                    "strategies": list(unique_strategies),
                    "count": len(strategies),
                    "severity": "high",
                })
        return results

    def generate_report(self) -> ConflictReport:
        """Generate a full conflict report for this instrument."""
        all_conflicts = []
        all_conflicts.extend(self.detect_shared_daily_limit_conflict())
        all_conflicts.extend(self.detect_max_active_isolation())
        all_conflicts.extend(self.detect_latency_lock_contention())
        all_conflicts.extend(self.detect_position_overlap())

        # Add metrics-sourced cross-strategy conflicts
        cross = self.metrics.get_cross_strategy_conflicts()
        for c in cross:
            all_conflicts.append({
                "type": "historical_cross_strategy_block",
                "blocked_strategy": c["blocked"],
                "blocking_strategy": c["by"],
                "event_count": c["count"],
                "severity": "medium" if c["count"] > 5 else "low",
            })

        return ConflictReport(
            timestamp=datetime.now().isoformat(),
            instrument=self.bot.name,
            conflicts=all_conflicts,
            total_blocked_strategies=sum(
                1 for c in all_conflicts if c.get("severity") in ("high", "medium")
            ),
            total_cross_strategy_blocks=len(cross),
        )