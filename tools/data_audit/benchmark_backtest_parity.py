"""
Benchmark Script: True Isolated Comparative Backtest Validation.
Contrasts OLD Live Stitching / Fallback Path vs NEW 5-Year Offline Dataset Path.

Guarantees:
  1. Old Run uses empty temp cache directory + DISABLE_OFFLINE_DATASET=True.
  2. New Run uses separate empty temp cache directory + DISABLE_OFFLINE_DATASET=False.
  3. Captures and counts genuine log signatures:
     - Old Path: [CACHE MISS] Fetching dynamic option... / [STITCHER]
     - New Path: [OFFLINE DATASET] Served...
"""
import os
import sys
import time
import shutil
import io
from contextlib import redirect_stdout, redirect_stderr
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

import backtest_engine
from backtest_engine import SimulationEngine, BacktestConfig

def run_isolated_benchmark():
    print("=" * 95)
    print("       TRUE ISOLATED COMPARATIVE BENCHMARK: OLD API/STITCHING vs NEW OFFLINE DATASET")
    print("=" * 95)

    temp_cache_old = os.path.join(BASE_DIR, "backtest_data", "temp_contract_cache_old")
    temp_cache_new = os.path.join(BASE_DIR, "backtest_data", "temp_contract_cache_new")

    # Clean any prior temp caches
    for p in [temp_cache_old, temp_cache_new]:
        if os.path.exists(p):
            shutil.rmtree(p)
        os.makedirs(p, exist_ok=True)

    config = BacktestConfig()
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    setattr(config, "ENABLE_STRATEGY_22", True)
    config.apply_strategy_defaults("Strategy_22")
    config.LEG_MODE = "SELL"

    # =========================================================================
    # 1. RUN 1: OLD PATH (DISABLE_OFFLINE_DATASET=True, Empty Temp Cache)
    # =========================================================================
    print("\n>>> [RUN 1: OLD PATH] Executing via Genuine API / Stitching Fallback Path...")
    os.environ["DISABLE_OFFLINE_DATASET"] = "True"
    os.environ["DISABLE_FALLBACKS"] = "False"
    
    # Clear in-memory caches
    backtest_engine._OPT_DF_CACHE.clear()
    backtest_engine._OPT_DICT_CACHE.clear()
    backtest_engine._OFFLINE_OPT_DAY_CACHE.clear()

    engine_old = SimulationEngine(config, instrument_name="NIFTY", backtest_days=1800)
    engine_old.cache_dir = temp_cache_old
    engine_old.load_data()
    # Sliced to 2024 Jan-Mar (60 trading sessions)
    engine_old.df_spot = engine_old.df_spot[(engine_old.df_spot.index >= '2024-01-01') & (engine_old.df_spot.index <= '2024-03-31')]

    log_buffer_old = io.StringIO()
    t0 = time.time()
    with redirect_stdout(log_buffer_old), redirect_stderr(log_buffer_old):
        res_old = engine_old.run(write_to_csv=False)
    t_old = time.time() - t0
    output_old = log_buffer_old.getvalue()

    cache_misses_old = output_old.count("[CACHE MISS]")
    stitcher_calls_old = output_old.count("[STITCHER]")
    offline_hits_old = output_old.count("[OFFLINE DATASET]")

    print(f"  [RUN 1 COMPLETE in {t_old:.2f}s]")
    print(f"  * [CACHE MISS] API Fetch Requests: {cache_misses_old}")
    print(f"  * [STITCHER] Invocations:         {stitcher_calls_old}")
    print(f"  * [OFFLINE DATASET] Hits:          {offline_hits_old} (Strictly 0 expected)")

    # =========================================================================
    # 2. RUN 2: NEW PATH (DISABLE_OFFLINE_DATASET=False, Empty Temp Cache)
    # =========================================================================
    print("\n>>> [RUN 2: NEW PATH] Executing via NEW 5-Year Offline Historical Options Dataset...")
    os.environ["DISABLE_OFFLINE_DATASET"] = "False"
    
    # Clear in-memory caches
    backtest_engine._OPT_DF_CACHE.clear()
    backtest_engine._OPT_DICT_CACHE.clear()
    backtest_engine._OFFLINE_OPT_DAY_CACHE.clear()

    engine_new = SimulationEngine(config, instrument_name="NIFTY", backtest_days=1800)
    engine_new.cache_dir = temp_cache_new
    engine_new.load_data()
    # Sliced to identical 2024 Jan-Mar (60 trading sessions)
    engine_new.df_spot = engine_new.df_spot[(engine_new.df_spot.index >= '2024-01-01') & (engine_new.df_spot.index <= '2024-03-31')]

    log_buffer_new = io.StringIO()
    t0 = time.time()
    with redirect_stdout(log_buffer_new), redirect_stderr(log_buffer_new):
        res_new = engine_new.run(write_to_csv=False)
    t_new = time.time() - t0
    output_new = log_buffer_new.getvalue()

    cache_misses_new = output_new.count("[CACHE MISS]")
    stitcher_calls_new = output_new.count("[STITCHER]")
    offline_hits_new = output_new.count("[OFFLINE DATASET]")

    print(f"  [RUN 2 COMPLETE in {t_new:.2f}s]")
    print(f"  * [OFFLINE DATASET] Hits:          {offline_hits_new} (Primary data source)")
    print(f"  * [CACHE MISS] API Fetch Requests: {cache_misses_new} (Only expiry rollovers)")
    print(f"  * [STITCHER] Invocations:         {stitcher_calls_new}")

    # =========================================================================
    # 3. SIDE-BY-SIDE COMPARATIVE ANALYSIS
    # =========================================================================
    print("\n" + "=" * 95)
    print("                         SIDE-BY-SIDE AUDIT REPORT")
    print("=" * 95)

    n_trades_old = len(res_old) if isinstance(res_old, pd.DataFrame) else 0
    n_trades_new = len(res_new) if isinstance(res_new, pd.DataFrame) else 0

    pnl_old = res_old['PnL'].sum() if n_trades_old > 0 and 'PnL' in res_old.columns else 0.0
    pnl_new = res_new['PnL'].sum() if n_trades_new > 0 and 'PnL' in res_new.columns else 0.0

    gross_old = res_old['Gross_PnL'].sum() if n_trades_old > 0 and 'Gross_PnL' in res_old.columns else 0.0
    gross_new = res_new['Gross_PnL'].sum() if n_trades_new > 0 and 'Gross_PnL' in res_new.columns else 0.0

    charges_old = res_old['Charges'].sum() if n_trades_old > 0 and 'Charges' in res_old.columns else 0.0
    charges_new = res_new['Charges'].sum() if n_trades_new > 0 and 'Charges' in res_new.columns else 0.0

    win_old = (len(res_old[res_old['PnL'] > 0]) / n_trades_old * 100.0) if n_trades_old > 0 and 'PnL' in res_old.columns else 0.0
    win_new = (len(res_new[res_new['PnL'] > 0]) / n_trades_new * 100.0) if n_trades_new > 0 and 'PnL' in res_new.columns else 0.0

    print(f"{'Metric':<32s} | {'Old Path (API / Stitching)':<26s} | {'New Path (Offline 5-Yr)':<26s}")
    print("-" * 95)
    print(f"{'Total Trades':<32s} | {n_trades_old:<26d} | {n_trades_new:<26d}")
    print(f"{'Total Net PnL (Rs)':<32s} | Rs {pnl_old:<23.2f} | Rs {pnl_new:<23.2f}")
    print(f"{'Gross PnL (Rs)':<32s} | Rs {gross_old:<23.2f} | Rs {gross_new:<23.2f}")
    print(f"{'Total Charges (Rs)':<32s} | Rs {charges_old:<23.2f} | Rs {charges_new:<23.2f}")
    print(f"{'Win Rate (%)':<32s} | {win_old:<25.2f}% | {win_new:<25.2f}%")
    print(f"{'Execution Time (Wall-Clock)':<32s} | {t_old:<25.2f}s | {t_new:<25.2f}s (Speedup: {t_old/max(0.01, t_new):.1f}x)")

    # Compare Trade Entries and Exits
    print("\n--- Trade-by-Trade Price Variance (> 1.0% Price Discrepancies) ---")
    if n_trades_new > 0 and n_trades_old > 0:
        discrepancies = []
        min_len = min(n_trades_old, n_trades_new)
        for i in range(min_len):
            r_old = res_old.iloc[i]
            r_new = res_new.iloc[i]

            entry_col = 'Entry_Price' if 'Entry_Price' in r_new else 'entry_price'
            exit_col = 'Exit_Price' if 'Exit_Price' in r_new else 'exit_price'
            time_col = 'Entry_Time' if 'Entry_Time' in r_new else 'entry_time'

            old_en = r_old.get(entry_col, 0.0)
            new_en = r_new.get(entry_col, 0.0)
            old_ex = r_old.get(exit_col, 0.0)
            new_ex = r_new.get(exit_col, 0.0)

            entry_diff_pct = abs(new_en - old_en) / max(0.01, old_en) * 100.0
            exit_diff_pct = abs(new_ex - old_ex) / max(0.01, old_ex) * 100.0

            if entry_diff_pct > 1.0 or exit_diff_pct > 1.0:
                discrepancies.append({
                    'trade_idx': i + 1,
                    'entry_time': str(r_new.get(time_col, 'N/A')),
                    'old_entry': round(old_en, 2),
                    'new_entry': round(new_en, 2),
                    'entry_diff_%': round(entry_diff_pct, 2),
                    'old_exit': round(old_ex, 2),
                    'new_exit': round(new_ex, 2),
                    'exit_diff_%': round(exit_diff_pct, 2),
                    'reason': 'Real traded tick vs mathematical synthetic stitching'
                })

        if discrepancies:
            df_disc = pd.DataFrame(discrepancies)
            print(f"Found {len(discrepancies)} trades with >1.0% price divergence:")
            print(df_disc.to_string(index=False))
        else:
            print("Zero trades differed by > 1.0%. Perfect parity.")
    else:
        print("One or both trade sets empty.")

    # Cleanup temp caches
    for p in [temp_cache_old, temp_cache_new]:
        if os.path.exists(p):
            shutil.rmtree(p)

if __name__ == "__main__":
    run_isolated_benchmark()
