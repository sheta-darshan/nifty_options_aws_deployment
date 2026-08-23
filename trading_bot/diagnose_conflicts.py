"""
Conflict Diagnostic CLI

Usage:
    python -m trading_bot.diagnose_conflicts
    python -m trading_bot.diagnose_conflicts --instrument NIFTY
    python -m trading_bot.diagnose_conflicts --output report.json

Reads the current bot state and conflict metrics to produce a
human-readable report of all detected cross-strategy conflicts.

This is a READ-ONLY diagnostic - it does not place orders or
modify any state.
"""
import argparse
import json
import sys
import os
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Diagnose multi-strategy conflicts")
    parser.add_argument("--instrument", default="NIFTY",
                        help="Instrument name to analyze (default: NIFTY)")
    parser.add_argument("--output", default=None,
                        help="Output file for JSON report (default: stdout)")
    parser.add_argument("--metrics-file", default=None,
                        help="Path to metrics dump file (from conflict_metrics.dump_to_file)")
    args = parser.parse_args()

    # Add parent dir to path so we can import trading_bot
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from trading_bot.conflict_metrics import get_metrics
    metrics = get_metrics()

    # Print header (ASCII only for Windows console compatibility)
    print("=" * 70)
    print("  SATP Conflict Diagnostic Report")
    print(f"  Instrument: {args.instrument}")
    print(f"  Timestamp:  {datetime.now().isoformat()}")
    print("=" * 70)

    # Metrics summary
    print("")
    print("[1] Conflict Metrics Summary")
    print("-" * 70)
    summary = metrics.get_summary()
    print(f"  Total blocking events recorded: {summary['total_events']}")
    if summary["gate_counts"]:
        print("  By gate:")
        for gate, count in sorted(summary["gate_counts"].items(), key=lambda x: -x[1]):
            print(f"    - {gate:25s} {count:>5d}")
    else:
        print("  (no events recorded yet - bot may not be running)")

    # Block rates per strategy
    if summary["strategy_block_rates"]:
        print("")
        print("  Block rates by strategy:")
        print(f"    {'Strategy':<20s} {'Attempted':>10s} {'Executed':>10s} {'Blocked':>10s} {'Rate':>8s}")
        for strat, data in sorted(summary["strategy_block_rates"].items()):
            print(f"    {strat:<20s} {data['attempted']:>10d} {data['executed']:>10d} "
                  f"{data['blocked']:>10d} {data['block_rate']:>7.1%}")

    # Cross-strategy conflicts
    print("")
    print("[2] Cross-Strategy Conflicts")
    print("-" * 70)
    cross = metrics.get_cross_strategy_conflicts()
    if cross:
        for c in cross:
            severity = "HIGH" if c["count"] > 10 else "MED " if c["count"] > 3 else "LOW "
            print(f"  [{severity}] {c['blocked']:<15s} blocked by {c['by']:<15s} ({c['count']} times)")
    else:
        print("  [OK] No cross-strategy conflicts detected in metrics history.")

    # Known structural conflicts
    print("")
    print("[3] Known Structural Conflict Points")
    print("-" * 70)
    print("  The following conflicts CAN occur in this codebase:")
    print("    [CRITICAL] daily_trade_counts[acc_name] is shared across strategies.")
    print("               Strategy_A trading N times will block Strategy_B on")
    print("               the same account for the rest of the day.")
    print("    [OK]       _count_my_active_positions IS isolated per strategy.")
    print("    [OK]       order_latency_locks IS isolated per strategy.")
    print("    [OK]       strategy_cooldowns IS isolated per strategy.")

    # Recommendations
    print("")
    print("[4] Recommendations")
    print("-" * 70)
    print("  1. Set per-strategy daily_limit in accounts.json to prevent starvation.")
    print("     Example: instrument_overrides.<INSTRUMENT>.daily_limit_per_strategy")
    print("  2. Add max_active_per_strategy override if multiple strategies")
    print("     share the same instrument.")
    print("  3. Run this script after each trading day to detect patterns.")
    print("  4. Wire record_block() into _handle_signal_inner at each gate")
    print("     for automatic detection (see conflict_detector.py).")

    print("")
    print("=" * 70)
    print("  End of Report")
    print("=" * 70)

    # Optionally write JSON
    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"")
        print(f"Summary written to: {args.output}")


if __name__ == "__main__":
    main()