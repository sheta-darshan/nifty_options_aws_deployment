"""
optimize_per_strategy.py - Per-Strategy Optimizer
===================================================
Tests each strategy individually on full data, then optimizes S1 & S2 parameters.

Usage:
    python optimize_per_strategy.py
"""
import os
import time
import itertools
import pandas as pd
import numpy as np
from strategies import BacktestConfig, get_strategy_class, STRATEGY_REGISTRY
from backtest_engine import SimulationEngine
from optimize_combined import evaluate_pnls, RESULTS_DIR

INSTRUMENT = "NIFTY"

def test_single_strategy(strategy_num):
    """Run a single strategy using SimulationEngine and return metrics."""
    config = BacktestConfig()
    
    # Disable all, enable only the target
    config.ENABLE_STRATEGY_1 = (strategy_num == 1)
    config.ENABLE_STRATEGY_2 = (strategy_num == 2)
    config.ENABLE_STRATEGY_3 = (strategy_num == 3)
    config.ENABLE_STRATEGY_4 = (strategy_num == 4)
    config.ENABLE_STRATEGY_5 = (strategy_num == 5)
    config.ENABLE_STRATEGY_6 = (strategy_num == 6)
    config.ENABLE_STRATEGY_7 = (strategy_num == 7)
    
    strategy_name = f"Strategy_{strategy_num}"
    config.apply_strategy_defaults(strategy_name)
    
    engine = SimulationEngine(config, instrument_name=INSTRUMENT, offline_mode=False)
    engine.load_data()
    
    # Run warmup/simulation
    engine.trades = []
    engine.active_trades = []
    engine.cooldown_until = None
    engine.run(write_to_csv=False)
    
    pnls = [t["PnL"] for t in engine.trades]
    r = evaluate_pnls(pnls)
    
    # Count signals
    sig_count = (engine.df_spot['Signal'] != 0).sum()
    r["Signals"] = sig_count
    return r

def optimize_strategy_1(engine, df_spot_raw):
    """Grid search over Strategy 1 parameters."""
    print(f"\n{'='*60}")
    print(f"  OPTIMIZING: Strategy 1 (Standard Trend)")
    print(f"{'='*60}")
    
    strategy_grid = get_strategy_class("Strategy_1")().get_optimization_grid()
    keys = list(strategy_grid.keys())
    values = list(strategy_grid.values())
    combos = [dict(zip(keys, v)) for v in itertools.product(*values)]
    total = len(combos)
    print(f"  Total combinations: {total}")
    
    results = []
    start = time.time()
    for i, combo in enumerate(combos):
        if (i + 1) % 50 == 0 or i == 0:
            elapsed = time.time() - start
            eta = (elapsed / (i + 1)) * (total - i - 1) if i > 0 else 0
            print(f"  Progress: {i+1}/{total} ({elapsed:.0f}s, ETA: {eta:.0f}s)")
        
        cfg = BacktestConfig()
        cfg.ENABLE_STRATEGY_1 = True
        cfg.apply_strategy_defaults("Strategy_1")
        for key, val in combo.items():
            setattr(cfg, key, val)
        
        engine.config = cfg
        df_spot = engine.strategy.generate_signals(df_spot_raw.copy())
        engine.df_spot = df_spot
        
        engine.trades = []
        engine.active_trades = []
        engine.cooldown_until = None
        engine.run(write_to_csv=False)
        
        pnls = [t["PnL"] for t in engine.trades]
        r = evaluate_pnls(pnls)
        r.update(combo)
        results.append(r)
    
    df = pd.DataFrame(results).sort_values("Robustness_Score", ascending=False)
    outfile = os.path.join(RESULTS_DIR, "strategy1_optimization.csv")
    df.to_csv(outfile, index=False)
    
    print(f"\n  Done in {time.time()-start:.0f}s -> {outfile}")
    print(f"\n  TOP 10:")
    print(f"  {'-'*100}")
    for _, r in df.head(10).iterrows():
        param_str = " ".join([f"{k}={r[k]:.1f}" if isinstance(r[k], (int, float)) else f"{k}={r[k]}" for k in strategy_grid.keys() if k in r])
        print(f"  {param_str}  => Trades={r['Total_Trades']:.0f}, WR={r['Win_Rate']:.1f}%, PF={r['Profit_Factor']:.2f},"
              f" PnL=Rs.{r['Net_PnL']:.0f}, Score={r['Robustness_Score']:.1f}")
    print(f"  {'-'*100}")
    return df

def optimize_strategy_2(engine, df_spot_raw):
    """Grid search over Strategy 2 parameters."""
    print(f"\n{'='*60}")
    print(f"  OPTIMIZING: Strategy 2 (Pullback)")
    print(f"{'='*60}")
    
    strategy_grid = get_strategy_class("Strategy_2")().get_optimization_grid()
    keys = list(strategy_grid.keys())
    values = list(strategy_grid.values())
    combos = [dict(zip(keys, v)) for v in itertools.product(*values)]
    total = len(combos)
    print(f"  Total combinations: {total}")
    
    results = []
    start = time.time()
    for i, combo in enumerate(combos):
        if (i + 1) % 50 == 0 or i == 0:
            elapsed = time.time() - start
            eta = (elapsed / (i + 1)) * (total - i - 1) if i > 0 else 0
            print(f"  Progress: {i+1}/{total} ({elapsed:.0f}s, ETA: {eta:.0f}s)")
        
        cfg = BacktestConfig()
        cfg.ENABLE_STRATEGY_2 = True
        cfg.apply_strategy_defaults("Strategy_2")
        for key, val in combo.items():
            setattr(cfg, key, val)
        
        engine.config = cfg
        df_spot = engine.strategy.generate_signals(df_spot_raw.copy())
        engine.df_spot = df_spot
        
        engine.trades = []
        engine.active_trades = []
        engine.cooldown_until = None
        engine.run(write_to_csv=False)
        
        pnls = [t["PnL"] for t in engine.trades]
        r = evaluate_pnls(pnls)
        r.update(combo)
        results.append(r)
    
    df = pd.DataFrame(results).sort_values("Robustness_Score", ascending=False)
    outfile = os.path.join(RESULTS_DIR, "strategy2_optimization.csv")
    df.to_csv(outfile, index=False)
    
    print(f"\n  Done in {time.time()-start:.0f}s -> {outfile}")
    print(f"\n  TOP 10:")
    print(f"  {'-'*100}")
    for _, r in df.head(10).iterrows():
        param_str = " ".join([f"{k}={r[k]:.1f}" if isinstance(r[k], (int, float)) else f"{k}={r[k]}" for k in strategy_grid.keys() if k in r])
        print(f"  {param_str}  => Trades={r['Total_Trades']:.0f}, WR={r['Win_Rate']:.1f}%, PF={r['Profit_Factor']:.2f},"
              f" PnL=Rs.{r['Net_PnL']:.0f}, Score={r['Robustness_Score']:.1f}")
    print(f"  {'-'*100}")
    return df

if __name__ == "__main__":
    print("=" * 60)
    print("  PER-STRATEGY TESTER + OPTIMIZER (SimulationEngine)")
    print("=" * 60)
    
    # =========================================================================
    #  STEP 1: Test each strategy on FULL data
    # =========================================================================
    print(f"\n{'='*60}")
    print(f"  FULL PER-STRATEGY TEST")
    print(f"{'='*60}")
    
    strat_names = [
        "Strategy_1 (Trend)", 
        "Strategy_2 (Pullback)", 
        "Strategy_3 (Triple Momentum)", 
        "Strategy_4 (WMA/SMA)",
        "Strategy_5 (ATR Renko)",
        "Strategy_6 (New Strategy)",
        "Strategy_7 (Range-Bound Volatility)"
    ]
    
    print(f"\n  {'Strategy':<30} {'Signals':>8} {'Trades':>7} {'WR':>7} {'PF':>7} {'PnL':>12} {'Score':>8}")
    print(f"  {'-'*85}")
    
    full_results = []
    for i, name in enumerate(strat_names, 1):
        try:
            r = test_single_strategy(i)
            r["Strategy"] = name
            full_results.append(r)
            
            status = "PROFIT" if r['Net_PnL'] > 0 else "LOSS"
            print(f"  {name:<30} {r['Signals']:>8} {r['Total_Trades']:>7} {r['Win_Rate']:>6.1f}% "
                  f"{r['Profit_Factor']:>7.2f} Rs.{r['Net_PnL']:>10.0f} {r['Robustness_Score']:>8.1f}  [{status}]")
        except Exception as e:
            print(f"  {name:<30} Error: {e}")
    
    print(f"  {'-'*85}")
    pd.DataFrame(full_results).to_csv(os.path.join(RESULTS_DIR, "per_strategy_5year.csv"), index=False)
    
    # Setup a common engine instance to reuse data loading for optimizations
    base_cfg = BacktestConfig()
    base_cfg.ENABLE_STRATEGY_1 = True
    base_cfg.apply_strategy_defaults("Strategy_1")
    engine = SimulationEngine(base_cfg, instrument_name=INSTRUMENT, offline_mode=False)
    engine.load_data()
    df_spot_raw = engine.df_spot[['open', 'high', 'low', 'close', 'volume']].copy()

    # =========================================================================
    #  STEP 2: Optimize Strategy 1
    # =========================================================================
    s1_results = optimize_strategy_1(engine, df_spot_raw)
    
    # =========================================================================
    #  STEP 3: Optimize Strategy 2
    # =========================================================================
    s2_results = optimize_strategy_2(engine, df_spot_raw)
    
    # =========================================================================
    #  SUMMARY
    # =========================================================================
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    
    # Best S1
    if not s1_results.empty:
        best_s1 = s1_results.iloc[0]
        if best_s1['Net_PnL'] > 0:
            print(f"\n  Strategy 1 CAN be profitable with:")
            grid_keys = list(get_strategy_class("Strategy_1")().get_optimization_grid().keys())
            for k in grid_keys:
                if k in best_s1:
                    print(f"    {k}={best_s1[k]}")
            print(f"    -> PnL=Rs.{best_s1['Net_PnL']:.0f}, WR={best_s1['Win_Rate']:.1f}%, PF={best_s1['Profit_Factor']:.2f}")
        else:
            print(f"\n  Strategy 1: NO profitable parameter combination found.")
            print(f"    Best attempt: PnL=Rs.{best_s1['Net_PnL']:.0f} (still negative)")
            print(f"    RECOMMENDATION: Disable Strategy 1")
    
    # Best S2
    if not s2_results.empty:
        best_s2 = s2_results.iloc[0]
        if best_s2['Net_PnL'] > 0:
            print(f"\n  Strategy 2 CAN be profitable with:")
            grid_keys = list(get_strategy_class("Strategy_2")().get_optimization_grid().keys())
            for k in grid_keys:
                if k in best_s2:
                    print(f"    {k}={best_s2[k]}")
            print(f"    -> PnL=Rs.{best_s2['Net_PnL']:.0f}, WR={best_s2['Win_Rate']:.1f}%, PF={best_s2['Profit_Factor']:.2f}")
        else:
            print(f"\n  Strategy 2: NO profitable parameter combination found.")
            print(f"    Best attempt: PnL=Rs.{best_s2['Net_PnL']:.0f} (still negative)")
            print(f"    RECOMMENDATION: Disable Strategy 2")
    
    print(f"\n{'='*60}")
