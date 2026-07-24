import os
import json
import time
import argparse
import itertools
import random
import sys
import pandas as pd
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

# Add workspace directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from strategies import BacktestConfig, STRATEGY_REGISTRY, get_strategy_class
from backtest_engine import SimulationEngine

RESULTS_DIR = os.path.join(BASE_DIR, "optimization_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

METRIC_MAP = {
    "robustness": "Robustness_Score",
    "pnl": "Net_PnL",
    "recovery_factor": "Recovery_Factor",
    "expectancy": "Expectancy",
    "winrate": "Win_Rate"
}

# =========================================================================
#  PERFORMANCE EVALUATOR (Net PnL, Win Rate, PF, DD, Expectancy, Robustness)
# =========================================================================
def evaluate_pnls(trades_or_pnls, backtest_days=720, mc_iter=1000, min_trades_override=None, strategy_name=None):
    if not trades_or_pnls:
        return {
            "Total_Trades": 0, "Win_Rate": 0.0, "Profit_Factor": 0.0,
            "Net_PnL": 0.0, "Avg_PnL": 0.0, "Max_Drawdown": 0.0,
            "Expectancy": 0.0, "Recovery_Factor": 0.0, "Robustness_Score": 0.0,
            "MC_Worst_DD_95Pct": 0.0, "MC_Median_DD": 0.0, "MC_Robustness": 0.0,
            "Equity_R2": 0.0, "PnL_Ex_Lucky": 0.0, "Lucky_Drop_Pct": 0.0,
            "Stability_Score": 1.0, "PnL_Trend": 0.0, "PF_Trend": 1.0,
            "PnL_Range": 0.0, "PF_Range": 1.0, "PnL_High_VIX": 0.0,
            "PF_High_VIX": 1.0, "PnL_Low_VIX": 0.0, "PF_Low_VIX": 1.0
        }
    
    if isinstance(trades_or_pnls[0], dict):
        trades = trades_or_pnls
        pnls = [t["PnL"] for t in trades]
    else:
        trades = []
        pnls = trades_or_pnls

    total = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    losses = total - wins
    win_rate = (wins / total) * 100 if total > 0 else 0.0
    
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else np.inf
    
    net_pnl = sum(pnls)
    avg_pnl = net_pnl / total if total > 0 else 0.0
    
    # Drawdown
    arr = np.array(pnls)
    cum = np.cumsum(arr)
    peaks = np.maximum.accumulate(cum)
    drawdowns = peaks - cum
    max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
    recovery_factor = net_pnl / max_dd if max_dd > 0 else 0.0
    
    avg_win = gross_profit / wins if wins > 0 else 0
    avg_loss = gross_loss / losses if losses > 0 else 0
    expectancy = (avg_win * (win_rate / 100)) - (avg_loss * (1 - win_rate / 100))
    
    # 1. Monte Carlo path shuffling robustness (Priority 2)
    worst_dd_95pct = 0.0
    median_dd = 0.0
    mc_robustness = 0.0
    if total > 0:
        sim_drawdowns = []
        for _ in range(mc_iter):
            shuffled = np.random.permutation(arr)
            cum_shuf = np.cumsum(shuffled)
            peaks_shuf = np.maximum.accumulate(cum_shuf)
            dds_shuf = peaks_shuf - cum_shuf
            sim_drawdowns.append(np.max(dds_shuf) if len(dds_shuf) > 0 else 0.0)
        
        sim_drawdowns = np.array(sim_drawdowns)
        worst_dd_95pct = float(np.percentile(sim_drawdowns, 95))
        median_dd = float(np.percentile(sim_drawdowns, 50))
        if net_pnl > 0:
            mc_robustness = net_pnl / worst_dd_95pct if worst_dd_95pct > 0 else net_pnl
        else:
            mc_robustness = 0.0

    # 2. Equity Curve Quality (R2) (Priority 4)
    equity_r2 = 0.0
    if total > 2:
        x_vals = np.arange(total)
        slope, intercept = np.polyfit(x_vals, cum, 1)
        fitted = slope * x_vals + intercept
        ss_tot = np.sum((cum - np.mean(cum)) ** 2)
        ss_res = np.sum((cum - fitted) ** 2)
        equity_r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    # 3. Regime Analysis (Priority 3)
    pnl_trend = 0.0
    pf_trend = 0.0
    pnl_range = 0.0
    pf_range = 0.0
    pnl_high_vix = 0.0
    pf_high_vix = 0.0
    pnl_low_vix = 0.0
    pf_low_vix = 0.0
    
    if trades:
        trend_trades = [t for t in trades if t.get("Regime_Trend") == "TREND"]
        range_trades = [t for t in trades if t.get("Regime_Trend") == "RANGE"]
        high_vix_trades = [t for t in trades if t.get("Regime_Vol") == "HIGH_VIX"]
        low_vix_trades = [t for t in trades if t.get("Regime_Vol") == "LOW_VIX"]
        
        def calc_pnl_pf(subset):
            if not subset:
                return 0.0, 1.0
            sub_pnls = [t["PnL"] for t in subset]
            sub_net = sum(sub_pnls)
            gp = sum(p for p in sub_pnls if p > 0)
            gl = abs(sum(p for p in sub_pnls if p < 0))
            sub_pf = gp / gl if gl > 0 else (np.inf if gp > 0 else 1.0)
            return sub_net, sub_pf
            
        pnl_trend, pf_trend = calc_pnl_pf(trend_trades)
        pnl_range, pf_range = calc_pnl_pf(range_trades)
        pnl_high_vix, pf_high_vix = calc_pnl_pf(high_vix_trades)
        pnl_low_vix, pf_low_vix = calc_pnl_pf(low_vix_trades)

    # 4. Remove Lucky Trades Test (Priority 6) - Proportional (top 5%, min 3)
    pnl_ex_lucky = net_pnl
    lucky_drop_pct = 0.0
    lucky_count = max(3, int(total * 0.05))
    if total > lucky_count:
        sorted_pnls = sorted(pnls)
        pnls_ex = sorted_pnls[:-lucky_count]
        pnl_ex_lucky = sum(pnls_ex)
        if net_pnl > 0:
            lucky_drop_pct = (net_pnl - pnl_ex_lucky) / net_pnl
        else:
            lucky_drop_pct = 1.0
    elif total > 0:
        pnl_ex_lucky = 0.0
        lucky_drop_pct = 1.0

    # 5. Stability Score (Period Consistency) (Priority 7) - Simplified count penalty
    stability_score = 1.0
    if trades:
        dates = []
        for t in trades:
            dt = t.get("Entry_Time")
            if dt:
                if isinstance(dt, str):
                    dt = pd.to_datetime(dt)
                dates.append(dt)
        if dates:
            span_days = (max(dates) - min(dates)).days
            period_pnls = {}
            for t in trades:
                dt = t.get("Entry_Time")
                if dt:
                    if isinstance(dt, str):
                        dt = pd.to_datetime(dt)
                    key = dt.year if span_days >= 365 else (dt.year, dt.month)
                    period_pnls.setdefault(key, []).append(t["PnL"])
            
            if len(period_pnls) > 1:
                period_sums = [sum(v) for v in period_pnls.values()]
                min_p = min(period_sums)
                max_p = max(period_sums)
                if max_p > 0:
                    if min_p >= 0:
                        stability_score = min_p / max_p
                    else:
                        neg_count = sum(1 for p in period_sums if p < 0)
                        stability_score = max(0.0, 1.0 - (neg_count / len(period_sums)))
                else:
                    stability_score = 0.0

    # Simplified, dimensionless Robustness score calculation
    if net_pnl > 0 and max_dd > 0:
        recovery_factor = net_pnl / max_dd
    else:
        recovery_factor = 0.0

    if net_pnl > 0 and pf > 1.0:
        pf_clipped = min(pf, 3.0) if pf != np.inf else 3.0
        rec_factor_clipped = min(recovery_factor, 6.0)
        win_rate_ratio = win_rate / 100.0
        
        # Simple weighted sum (0.40 * PF + 0.40 * Recovery_Factor + 0.10 * Win_Rate + 0.10 * Stability = 1.0 normalized)
        pf_norm = pf_clipped / 3.0
        rec_norm = rec_factor_clipped / 6.0
        
        base_score = 0.40 * pf_norm + 0.40 * rec_norm + 0.10 * win_rate_ratio + 0.10 * stability_score
        
        # Scale slightly by R2 (linearity) and lucky trade drop (robustness verification)
        robustness = base_score * (0.5 + 0.5 * max(0.1, equity_r2)) * (1.0 - 0.5 * lucky_drop_pct)
    else:
        robustness = 0.0

    # 6. Outlier Protection (Legacy fallback check)
    if net_pnl > 0 and total > 0 and robustness > 0:
        max_single_pnl = max(pnls)
        if max_single_pnl > 0.3 * net_pnl:
            # Soften penalty factor to prevent excessive drops
            penalty_factor = max(0.3, 1.0 - 0.5 * (max_single_pnl / net_pnl))
            robustness *= penalty_factor

    # 7. Monthly PnL Consistency (Legacy fallback check)
    if trades and robustness > 0:
        monthly_pnls = {}
        for t in trades:
            dt = t.get("Exit_Time") or t.get("Entry_Time")
            if dt:
                if isinstance(dt, str):
                    dt = pd.to_datetime(dt)
                month_key = (dt.year, dt.month)
                monthly_pnls.setdefault(month_key, []).append(t["PnL"])
        if monthly_pnls:
            profitable_months = sum(1 for m, m_pnls in monthly_pnls.items() if sum(m_pnls) > 0)
            total_months = len(monthly_pnls)
            consistency_ratio = profitable_months / total_months
            # Soften consistency ratio penalty for short/low-frequency runs
            robustness *= (0.5 + 0.5 * consistency_ratio)

    # 8. Minimum Trade Filter (with dynamic strategy scaling & override support)
    if min_trades_override is not None:
        min_trades = min_trades_override
    else:
        # Dynamic trade expectations per month
        if strategy_name == "Strategy_14":
            trades_per_month = 0.5
            base_min = 4
        elif strategy_name in ["Strategy_BTST", "Strategy_11"]:
            trades_per_month = 1.5
            base_min = 8
        else:
            trades_per_month = 3.0
            base_min = 18
            
        min_trades = max(base_min, int(trades_per_month * (backtest_days * 0.67 / 30.0)))
        
    if total < min_trades:
        robustness = 0.0

    return {
        "Total_Trades": total,
        "Win_Rate": round(win_rate, 1),
        "Profit_Factor": round(pf, 3) if pf != np.inf else 999.0,
        "Net_PnL": round(net_pnl, 2),
        "Avg_PnL": round(avg_pnl, 2),
        "Max_Drawdown": round(max_dd, 2),
        "Expectancy": round(expectancy, 2),
        "Recovery_Factor": round(recovery_factor, 2),
        "Robustness_Score": round(robustness, 3),
        "MC_Worst_DD_95Pct": round(worst_dd_95pct, 2),
        "MC_Median_DD": round(median_dd, 2),
        "MC_Robustness": round(mc_robustness, 2),
        "Equity_R2": round(equity_r2, 4),
        "PnL_Ex_Lucky": round(pnl_ex_lucky, 2),
        "Lucky_Drop_Pct": round(lucky_drop_pct, 4),
        "Stability_Score": round(stability_score, 3),
        "PnL_Trend": round(pnl_trend, 2),
        "PF_Trend": round(pf_trend, 3) if pf_trend != np.inf else 999.0,
        "PnL_Range": round(pnl_range, 2),
        "PF_Range": round(pf_range, 3) if pf_range != np.inf else 999.0,
        "PnL_High_VIX": round(pnl_high_vix, 2),
        "PF_High_VIX": round(pf_high_vix, 3) if pf_high_vix != np.inf else 999.0,
        "PnL_Low_VIX": round(pnl_low_vix, 2),
        "PF_Low_VIX": round(pf_low_vix, 3) if pf_low_vix != np.inf else 999.0
    }

def generate_rolling_windows(df_spot, train_months=6, test_months=2, step_months=2):
    unique_dates = sorted(list(set(df_spot.index.date)))
    if not unique_dates:
        return []
        
    start_date = pd.Timestamp(unique_dates[0])
    end_date = pd.Timestamp(unique_dates[-1])
    
    windows = []
    curr_start = start_date
    
    while True:
        train_end = curr_start + pd.DateOffset(months=train_months)
        test_start = train_end
        test_end = test_start + pd.DateOffset(months=test_months)
        
        if train_end >= end_date:
            break
            
        if test_start >= end_date:
            break
            
        if test_end > end_date:
            test_end = end_date
            
        windows.append({
            "train_start": curr_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end
        })
        
        if test_end == end_date:
            break
            
        curr_start = curr_start + pd.DateOffset(months=step_months)
        
    return windows

def log_experiment_to_tracker(run_type, instrument, strategy_name, leg_mode, days, train_res, test_res, best_params, verdict):
    import csv
    from datetime import datetime
    csv_file = os.path.join(BASE_DIR, "experiments_tracker.csv")
    md_file = os.path.join(BASE_DIR, "BACKTEST_LOG.md")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Write to CSV
    file_exists = os.path.exists(csv_file)
    headers = [
        "timestamp", "type", "instrument", "strategy", "days", "leg_mode",
        "train_trades", "train_win_rate", "train_pf", "train_pnl", "train_max_dd",
        "test_trades", "test_win_rate", "test_pf", "test_pnl", "test_max_dd",
        "best_params", "verdict"
    ]
    
    row = {
        "timestamp": timestamp,
        "type": run_type,
        "instrument": instrument,
        "strategy": strategy_name,
        "days": days,
        "leg_mode": leg_mode,
        "train_trades": train_res.get("Total_Trades", 0) if train_res else "",
        "train_win_rate": train_res.get("Win_Rate", 0.0) if train_res else "",
        "train_pf": train_res.get("Profit_Factor", 0.0) if train_res else "",
        "train_pnl": train_res.get("Net_PnL", 0.0) if train_res else "",
        "train_max_dd": train_res.get("Max_Drawdown", 0.0) if train_res else "",
        "test_trades": test_res.get("Total_Trades", 0) if test_res else "",
        "test_win_rate": test_res.get("Win_Rate", 0.0) if test_res else "",
        "test_pf": test_res.get("Profit_Factor", 0.0) if test_res else "",
        "test_pnl": test_res.get("Net_PnL", 0.0) if test_res else "",
        "test_max_dd": test_res.get("Max_Drawdown", 0.0) if test_res else "",
        "best_params": json.dumps(best_params, cls=NumpyEncoder) if best_params else "",
        "verdict": verdict
    }
    
    try:
        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        print(f"[TRACKER ERROR] Failed to write CSV log: {e}")
        
    # 2. Write to Markdown (BACKTEST_LOG.md)
    try:
        # Build clean string representations of params
        param_str = ", ".join(f"{k}={v}" for k, v in best_params.items()) if best_params else "Default"
        if len(param_str) > 60:
            param_str = param_str[:57] + "..."
            
        train_pnl_val = f"Rs.{train_res['Net_PnL']:.2f}" if train_res else "N/A"
        test_pnl_val = f"Rs.{test_res['Net_PnL']:.2f}" if test_res else "N/A"
        train_wr = f"{train_res['Win_Rate']}%" if train_res else "N/A"
        test_wr = f"{test_res['Win_Rate']}%" if test_res else "N/A"
        
        md_row = f"| {timestamp} | {run_type} | {instrument} | {strategy_name} | {days} | {leg_mode} | {train_pnl_val} ({train_wr}) | {test_pnl_val} ({test_wr}) | {param_str} | {verdict} |\n"
        
        if not os.path.exists(md_file):
            with open(md_file, "w", encoding="utf-8") as f:
                f.write("# 📊 Backtesting & Optimization Experiment Log\n\n")
                f.write("This file tracks all historical backtesting and optimization runs. Updates automatically.\n\n")
                f.write("| Date/Time | Type | Symbol | Strategy | Days | Leg | Train PnL (WR) | Test PnL (WR) | Best Parameters / Config | Verdict |\n")
                f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
                f.write(md_row)
        else:
            with open(md_file, "a", encoding="utf-8") as f:
                f.write(md_row)
    except Exception as e:
        print(f"[TRACKER ERROR] Failed to write Markdown log: {e}")

# =========================================================================
#  MULTIPROCESSING WORKER
# =========================================================================
def init_worker(parent_cache):
    from backtest_engine import _OPT_DF_CACHE
    _OPT_DF_CACHE.update(parent_cache)

def worker_run_backtest(args):
    combo_dict, leg_mode, instrument_name, config_dict, inst_config_dict, df_spot, strategy_name, mc_iter = args
    
    from strategies import BacktestConfig
    from backtest_engine import SimulationEngine
    import contextlib
    
    config = BacktestConfig()
    for k, v in config_dict.items():
        setattr(config, k, v)
    config.LEG_MODE = leg_mode
    
    # Enable the target strategy and disable others using the registry
    for name in STRATEGY_REGISTRY.keys():
        toggle_name = f"ENABLE_{name.upper()}"
        setattr(config, toggle_name, (name == strategy_name))
    config.apply_strategy_defaults(strategy_name)
    
    # Apply strategy parameter overrides from combo_dict
    for k, v in combo_dict.items():
        if not k.startswith("sl_mult_") and not k.startswith("tp_mult_") and not k.startswith("trailing_mult_"):
            setattr(config, k, v)
            
    engine = SimulationEngine(config, instrument_name=instrument_name, df_spot=None, offline_mode=False)
    engine.inst_config.update(inst_config_dict)
    
    # Apply risk parameter overrides from combo_dict
    exit_mode = inst_config_dict.get("exit_mode", "ATR")
    if exit_mode == "POINTS":
        if leg_mode in ["BUY", "BOTH"]:
            engine.inst_config['points_sl_buy'] = combo_dict.get('points_sl_buy', inst_config_dict.get('points_sl_buy'))
            engine.inst_config['points_target_buy'] = combo_dict.get('points_target_buy', inst_config_dict.get('points_target_buy'))
            engine.inst_config['points_trail_buy'] = combo_dict.get('points_trail_buy', inst_config_dict.get('points_trail_buy'))
            engine.inst_config['points_be_buy'] = combo_dict.get('points_be_buy', inst_config_dict.get('points_be_buy', 0.0))
        if leg_mode in ["SELL", "BOTH"]:
            engine.inst_config['points_sl_sell'] = combo_dict.get('points_sl_sell', inst_config_dict.get('points_sl_sell'))
            engine.inst_config['points_target_sell'] = combo_dict.get('points_target_sell', inst_config_dict.get('points_target_sell'))
            engine.inst_config['points_trail_sell'] = combo_dict.get('points_trail_sell', inst_config_dict.get('points_trail_sell'))
            engine.inst_config['points_be_sell'] = combo_dict.get('points_be_sell', inst_config_dict.get('points_be_sell', 0.0))
    else:
        if leg_mode in ["BUY", "BOTH"]:
            engine.inst_config['sl_mult_buy'] = combo_dict.get('sl_mult_buy', inst_config_dict.get('sl_mult_buy'))
            engine.inst_config['tp_mult_buy'] = combo_dict.get('tp_mult_buy', inst_config_dict.get('tp_mult_buy'))
            engine.inst_config['trailing_mult_buy'] = combo_dict.get('trailing_mult_buy', inst_config_dict.get('trailing_mult_buy'))
            engine.inst_config['atr_be_buy'] = combo_dict.get('atr_be_buy', inst_config_dict.get('atr_be_buy', 0.0))
        if leg_mode in ["SELL", "BOTH"]:
            engine.inst_config['sl_mult_sell'] = combo_dict.get('sl_mult_sell', inst_config_dict.get('sl_mult_sell'))
            engine.inst_config['tp_mult_sell'] = combo_dict.get('tp_mult_sell', inst_config_dict.get('tp_mult_sell'))
            engine.inst_config['trailing_mult_sell'] = combo_dict.get('trailing_mult_sell', inst_config_dict.get('trailing_mult_sell'))
            engine.inst_config['atr_be_sell'] = combo_dict.get('atr_be_sell', inst_config_dict.get('atr_be_sell', 0.0))
        
    # Run backtest on worker's local copy of spot data (with stdout suppressed)
    with open(os.devnull, 'w') as fnull:
        with contextlib.redirect_stdout(fnull):
            engine.df_spot = df_spot
            engine.run(write_to_csv=False)
    
    unique_dates = df_spot.index.date
    backtest_days = (unique_dates.max() - unique_dates.min()).days if len(unique_dates) > 0 else 720
    min_trades_override = engine.inst_config.get("min_trades_override")
    metrics = evaluate_pnls(engine.trades, backtest_days=backtest_days, mc_iter=mc_iter, min_trades_override=min_trades_override, strategy_name=strategy_name)
    metrics.update(combo_dict)
    return metrics


# =========================================================================
#  GRID EXECUTION HELPER
# =========================================================================
def run_grid_sweep(combos, leg_mode, instrument_name, config, inst_config, df_spot_raw, strategy_name, label="Grid Search", sort_by="robustness", mc_iter=100):
    import multiprocessing
    num_workers = max(1, multiprocessing.cpu_count() - 1)
    total = len(combos)
    
    config_dict = {
        k: getattr(config, k) 
        for k in dir(config) 
        if not k.startswith("__") and not callable(getattr(config, k))
    }
    
    # Pre-generate df_spot for each unique strategy parameter set in combos
    # to avoid redundant calculations across 1000s of iterations.
    strat_keys = []
    if len(combos) > 0:
        first_combo = combos[0]
        strat_keys = [
            k for k in first_combo.keys() 
            if not k.startswith("sl_mult_") 
            and not k.startswith("tp_mult_") 
            and not k.startswith("trailing_mult_")
            and not k.startswith("atr_be_")
            and not k.startswith("points_sl_")
            and not k.startswith("points_target_")
            and not k.startswith("points_trail_")
            and not k.startswith("points_be_")
        ]
        
    from strategies import BacktestConfig
    from backtest_engine import SimulationEngine
    
    df_spot_cache = {}
    for combo in combos:
        strat_vals = tuple(combo.get(k) for k in strat_keys)
        if strat_vals not in df_spot_cache:
            temp_config = BacktestConfig()
            for k in strat_keys:
                setattr(temp_config, k, combo[k])
            for name in STRATEGY_REGISTRY.keys():
                setattr(temp_config, f"ENABLE_{name.upper()}", (name == strategy_name))
            temp_config.apply_strategy_defaults(strategy_name)
            
            temp_engine = SimulationEngine(temp_config, instrument_name=instrument_name, df_spot=None, offline_mode=False)
            temp_engine.inst_config.update(inst_config)
            df_spot_sig = temp_engine.strategy.generate_signals(df_spot_raw.copy())
            df_spot_cache[strat_vals] = df_spot_sig
            
    args_list = []
    for combo in combos:
        strat_vals = tuple(combo.get(k) for k in strat_keys)
        df_spot_sig = df_spot_cache[strat_vals]
        args_list.append(
            (combo, leg_mode, instrument_name, config_dict, inst_config, df_spot_sig, strategy_name, mc_iter)
        )
    
    results = []
    start = time.time()
    from backtest_engine import _OPT_DF_CACHE
    with multiprocessing.Pool(
        processes=num_workers,
        initializer=init_worker,
        initargs=(_OPT_DF_CACHE,)
    ) as pool:
        for i, metrics in enumerate(pool.imap(worker_run_backtest, args_list), 1):
            results.append(metrics)
            if i % 20 == 0 or i == total:
                elapsed = time.time() - start
                eta = (elapsed / i) * (total - i) if i > 0 else 0
                print(f"  {label} Progress: {i}/{total} ({elapsed:.1f}s elapsed, ETA: {eta:.1f}s)")
                
    sort_col = METRIC_MAP.get(sort_by, "Robustness_Score")
    return pd.DataFrame(results).sort_values(sort_col, ascending=False)

def optimize_in_sample(df_spot_train, engine, strategy_name, leg_mode, max_combos, config, sort_by="robustness"):
    # Extract training average ATR
    print("\n[INFO] Extracting average training Spot ATR...")
    try:
        df_sig = engine.strategy.generate_signals(df_spot_train.copy())
        avg_atr = df_sig['ATR'].mean()
    except Exception as e:
        print(f"[WARNING] Failed to compute training signals for ATR extraction: {e}")
        avg_atr = np.nan
        
    if pd.isna(avg_atr) or avg_atr <= 0:
        avg_atr = df_spot_train['close'].mean() * 0.001
        print(f"[INFO] Using fallback ATR (0.1% of spot): {avg_atr:.2f}")
    else:
        print(f"[INFO] Average Training Spot ATR: {avg_atr:.2f}")

    execution_mode = engine.inst_config.get("execution_mode", "OPTION")
    is_stock = (execution_mode == "STOCK")
    avg_close = df_spot_train['close'].mean()
    def snap_tick(val):
        if is_stock and avg_close < 100:
            return round(float(val) * 100.0) / 100.0 # 0.01 tick size for low-priced stocks
        return round(float(val) * 20.0) / 20.0 # 0.05 tick size

    # 4. Define Coarse Grid for Stage 1 Joint Search
    # Extract strategy search spaces
    strategy_cls = get_strategy_class(strategy_name)
    strategy_grid = strategy_cls().get_optimization_grid()
    
    keys = list(strategy_grid.keys())
    values = list(strategy_grid.values())
    strategy_combos = [dict(zip(keys, v)) for v in itertools.product(*values)]
    if len(strategy_combos) > max_combos:
        print(f"[WARNING] Strategy parameter combinations ({len(strategy_combos)}) exceeds safety limit ({max_combos}).")
        print(f"          Applying Shuffled Random Sampling with fixed seed (42) to select {max_combos} combinations...")
        random.seed(42)
        strategy_combos = random.sample(strategy_combos, max_combos)
    else:
        print(f"[INFO] Optimization grid holds {len(strategy_combos)} strategy parameter combinations.")

    target_type = engine.inst_config.get("short_option_target_type", "ATR")
    exit_mode = engine.inst_config.get("exit_mode", "ATR")

    opt_grid = engine.inst_config.get("optimization_grid", {})
    has_custom_grid = False
    custom_risk_combos = []
    
    if opt_grid:
        has_custom_grid = True
        print(f"[INFO] Custom optimization_grid found in instruments.json for {engine.instrument_name}: {opt_grid}")
        
        # Helper to retrieve list of numbers from grid, with fallback to config value or default
        def get_val_list(key, default_val):
            val = opt_grid.get(key)
            if val is not None:
                if isinstance(val, list):
                    return [float(x) for x in val]
                else:
                    return [float(val)]
            cfg_val = engine.inst_config.get(key)
            if cfg_val is not None:
                try:
                    return [float(cfg_val)]
                except (ValueError, TypeError):
                    pass
            return [default_val]

        if exit_mode == "POINTS":
            buy_grid = {
                "points_sl_buy": get_val_list("points_sl_buy", 15.0),
                "points_target_buy": get_val_list("points_target_buy", 30.0),
                "points_trail_buy": get_val_list("points_trail_buy", 0.0),
                "points_be_buy": get_val_list("points_be_buy", 0.0)
            }
            sell_grid = {
                "points_sl_sell": get_val_list("points_sl_sell", 15.0),
                "points_target_sell": get_val_list("points_target_sell", 30.0),
                "points_trail_sell": get_val_list("points_trail_sell", 0.0),
                "points_be_sell": get_val_list("points_be_sell", 0.0)
            }
            sl_vals = sorted(list(set(buy_grid["points_sl_buy"] if leg_mode in ["BUY", "BOTH"] else sell_grid["points_sl_sell"])))
        else: # ATR mode
            buy_grid = {
                "sl_mult_buy": get_val_list("sl_mult_buy", 1.5),
                "tp_mult_buy": get_val_list("tp_mult_buy", 3.0),
                "trailing_mult_buy": get_val_list("trailing_mult_buy", 0.0),
                "atr_be_buy": get_val_list("atr_be_buy", 0.0)
            }
            sell_grid = {
                "sl_mult_sell": get_val_list("sl_mult_sell", 1.5),
                "tp_mult_sell": get_val_list("tp_mult_sell", 3.0),
                "trailing_mult_sell": get_val_list("trailing_mult_sell", 0.0),
                "atr_be_sell": get_val_list("atr_be_sell", 0.0)
            }
            sl_vals = sorted(list(set(buy_grid["sl_mult_buy"] if leg_mode in ["BUY", "BOTH"] else sell_grid["sl_mult_sell"])))

        # Generate combinations
        if leg_mode == "BUY":
            keys_to_prod = list(buy_grid.keys())
            lists_to_prod = list(buy_grid.values())
        elif leg_mode == "SELL":
            keys_to_prod = list(sell_grid.keys())
            lists_to_prod = list(sell_grid.values())
        else: # BOTH
            keys_to_prod = list(buy_grid.keys()) + list(sell_grid.keys())
            lists_to_prod = list(buy_grid.values()) + list(sell_grid.values())

        for p in itertools.product(*lists_to_prod):
            custom_risk_combos.append(dict(zip(keys_to_prod, p)))

        # Subsample for Stage 1 coarse_risk
        if len(custom_risk_combos) <= 4:
            coarse_risk = custom_risk_combos
        else:
            indices = [0, len(custom_risk_combos)//3, 2*len(custom_risk_combos)//3, len(custom_risk_combos)-1]
            coarse_risk = [custom_risk_combos[i] for i in sorted(list(set(indices)))]

        print(f"[INFO] Generated {len(custom_risk_combos)} custom risk parameter combinations from instruments.json.")

    if not has_custom_grid:
        if exit_mode == "POINTS":
            base_pt = max(1.0, avg_atr) if is_stock else max(1.0, avg_atr * 0.5)
            
            inst_type = engine.inst_config.get("type", "INDEX")
            
            if is_stock:
                min_sl = max(0.5, snap_tick(avg_close * 0.001))
                min_tp = max(0.5, snap_tick(avg_close * 0.002))
                min_trail = max(0.1, snap_tick(avg_close * 0.0005))
            elif inst_type == "INDEX":
                min_sl = 5.0
                min_tp = 10.0
                min_trail = 2.0
            else:
                min_sl = 0.5
                min_tp = 0.5
                min_trail = 0.1
    
            sl1 = max(min_sl, snap_tick(base_pt * 0.75))
            sl2 = max(min_sl, snap_tick(base_pt * 1.0))
            sl3 = max(min_sl, snap_tick(base_pt * 1.5))
            
            tp1 = max(min_tp, snap_tick(base_pt * 1.5))
            tp2 = max(min_tp, snap_tick(base_pt * 2.0))
            tp3 = max(min_tp, snap_tick(base_pt * 4.0))
            
            tr1 = max(min_trail, snap_tick(base_pt * 0.3))
            tr2 = max(min_trail, snap_tick(base_pt * 0.5))
            
            if leg_mode == "BUY":
                coarse_risk = [
                    {"points_sl_buy": sl1, "points_target_buy": tp1, "points_trail_buy": 0.0},
                    {"points_sl_buy": sl2, "points_target_buy": tp2, "points_trail_buy": 0.0},
                    {"points_sl_buy": sl2, "points_target_buy": tp2, "points_trail_buy": tr1},
                    {"points_sl_buy": sl3, "points_target_buy": tp3, "points_trail_buy": tr2},
                ]
            elif leg_mode == "SELL":
                coarse_risk = [
                    {"points_sl_sell": sl1, "points_target_sell": tp1, "points_trail_sell": 0.0},
                    {"points_sl_sell": sl2, "points_target_sell": tp2, "points_trail_sell": 0.0},
                    {"points_sl_sell": sl2, "points_target_sell": tp2, "points_trail_sell": tr1},
                    {"points_sl_sell": sl3, "points_target_sell": tp3, "points_trail_sell": tr2},
                ]
            else: # BOTH
                coarse_risk = [
                    {"points_sl_buy": sl2, "points_target_buy": tp2, "points_trail_buy": tr1,
                     "points_sl_sell": sl2, "points_target_sell": tp2, "points_trail_sell": tr1},
                    {"points_sl_buy": sl3, "points_target_buy": tp3, "points_trail_buy": tr2,
                     "points_sl_sell": sl3, "points_target_sell": tp3, "points_trail_sell": tr2},
                ]
        else:
            if leg_mode == "BUY":
                coarse_risk = [
                    {"sl_mult_buy": 1.5, "tp_mult_buy": 2.0, "trailing_mult_buy": 0.0},
                    {"sl_mult_buy": 1.5, "tp_mult_buy": 4.0, "trailing_mult_buy": 0.0},
                    {"sl_mult_buy": 3.0, "tp_mult_buy": 2.0, "trailing_mult_buy": 0.0},
                    {"sl_mult_buy": 3.0, "tp_mult_buy": 4.0, "trailing_mult_buy": 0.0},
                ]
            elif leg_mode == "SELL":
                if target_type == "MAX_PROFIT":
                    coarse_risk = [
                        {"sl_mult_sell": 2.0, "tp_mult_sell": 4.0, "trailing_mult_sell": 0.0},
                        {"sl_mult_sell": 4.0, "tp_mult_sell": 4.0, "trailing_mult_sell": 0.0},
                    ]
                else:
                    coarse_risk = [
                        {"sl_mult_sell": 2.0, "tp_mult_sell": 2.0, "trailing_mult_sell": 0.0},
                        {"sl_mult_sell": 2.0, "tp_mult_sell": 4.0, "trailing_mult_sell": 0.0},
                        {"sl_mult_sell": 4.0, "tp_mult_sell": 2.0, "trailing_mult_sell": 0.0},
                        {"sl_mult_sell": 4.0, "tp_mult_sell": 4.0, "trailing_mult_sell": 0.0},
                    ]
            else:  # BOTH
                coarse_risk = [
                    {"sl_mult_buy": 1.5, "tp_mult_buy": 2.0, "trailing_mult_buy": 0.0,
                     "sl_mult_sell": 2.0, "tp_mult_sell": 4.0, "trailing_mult_sell": 0.0},
                    {"sl_mult_buy": 3.0, "tp_mult_buy": 4.0, "trailing_mult_buy": 0.0,
                     "sl_mult_sell": 4.0, "tp_mult_sell": 4.0, "trailing_mult_sell": 0.0},
                ]

    # Stage 1: Coarse Joint Parameter Sweep (Strategy + Risk)
    print(f"\n[STAGE 1] Running Joint Coarse Search ({len(strategy_combos) * len(coarse_risk)} runs) on TRAIN Data...")
    stage1_combos = []
    for s_combo in strategy_combos:
        for r_combo in coarse_risk:
            stage1_combos.append({**s_combo, **r_combo})
            
    df_stage1 = run_grid_sweep(
        stage1_combos, leg_mode, engine.instrument_name, config, engine.inst_config, 
        df_spot_train, strategy_name, label="Stage 1 Sweep", sort_by=sort_by, mc_iter=100
    )
    
    if df_stage1.empty:
        raise ValueError("Stage 1 returned no viable trading metrics. Optimization stopped.")
        
    unique_strat_combos = []
    seen_combos = set()
    trading_stage1 = df_stage1[df_stage1["Total_Trades"] > 0]
    df_stage1_for_selection = trading_stage1 if not trading_stage1.empty else df_stage1
    for _, row in df_stage1_for_selection.iterrows():
        combo_tuple = tuple(row[k] for k in keys)
        if combo_tuple not in seen_combos:
            seen_combos.add(combo_tuple)
            unique_strat_combos.append(dict(zip(keys, combo_tuple)))
            if len(unique_strat_combos) >= 5:
                break
    print(f"[SUCCESS] Stage 1 complete! Retained Top {len(unique_strat_combos)} unique strategy configurations: {unique_strat_combos}")

    # Stage 2: Fine Risk Parameter Sweep
    print("\n[STAGE 2] Running Fine-Grained Risk Parameter Sweep on TRAIN Data...")
    
    fine_risk_combos = []
    if has_custom_grid:
        risk_sweep = custom_risk_combos
        max_risk_combos = 50
        if len(risk_sweep) > max_risk_combos:
            print(f"[WARNING] Custom risk combinations ({len(risk_sweep)}) exceeds safety limit ({max_risk_combos}) for Stage 2.")
            print(f"          Applying Shuffled Random Sampling with fixed seed (42) to select {max_risk_combos} combinations...")
            random.seed(42)
            risk_sweep = random.sample(risk_sweep, max_risk_combos)
        for strat_params in unique_strat_combos:
            for r_combo in risk_sweep:
                fine_risk_combos.append({**strat_params, **r_combo})
    else:
        inst_type = engine.inst_config.get("type", "INDEX")
        avg_close = df_spot_train['close'].mean()
        
        if execution_mode == "STOCK":
            floor_sl = snap_tick(max(0.5, avg_close * 0.001))
            floor_tp = snap_tick(max(0.5, avg_close * 0.002))
            floor_trail = snap_tick(max(0.1, avg_close * 0.0005))
        elif inst_type == "INDEX":
            floor_sl = 5.0
            floor_tp = 10.0
            floor_trail = 2.0
        else:
            floor_sl = 0.5
            floor_tp = 0.5
            floor_trail = 0.1
    
        if exit_mode == "POINTS":
            # Check if baseline point stop loss is configured
            base_sl = 0.0
            if leg_mode in ["BUY", "BOTH"]:
                base_sl = float(engine.inst_config.get("points_sl_buy", 0.0))
            if base_sl <= 0.0 and leg_mode in ["SELL", "BOTH"]:
                base_sl = float(engine.inst_config.get("points_sl_sell", 0.0))
                
            if base_sl > 0.0:
                print(f"[INFO] Optimizing POINTS exit directly around configured baseline SL: {base_sl} points")
                sl_factors = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0]
                sl_vals = sorted(list(set([max(floor_sl, snap_tick(base_sl * f)) for f in sl_factors])))
            else:
                sl_mults = [0.8, 1.2, 1.6, 2.0, 2.5, 3.0]
                opt_delta = engine.inst_config.get('option_delta', 0.5) if execution_mode != "STOCK" else 1.0
                sl_vals = sorted(list(set([max(floor_sl, snap_tick(avg_atr * opt_delta * m)) for m in sl_mults])))
        else:
            sl_vals = [0.8, 1.2, 1.6, 2.0, 2.5, 3.0]
    
        if leg_mode == "BUY":
            rr_vals = [1.5, 2.0, 3.0, 4.0, 5.0]
        elif leg_mode == "SELL":
            rr_vals = [0.75, 1.0, 1.5, 2.0]
        else: # BOTH
            # Decouple: generate asymmetric pairs of (rr_buy, rr_sell) to limit search space
            rr_pairs = []
            for rb in [1.5, 2.0, 3.0, 4.0]:
                for rs in [0.75, 1.0, 1.5, 2.0]:
                    rr_pairs.append((rb, rs))
    
        trail_ratios = [0.0, 0.25, 0.5, 0.75]
        be_mults = [0.0, 1.0, 1.5]
    
        risk_sweep = []
        for sl in sl_vals:
            for trail_ratio in trail_ratios:
                for be in be_mults:
                    if leg_mode == "BOTH":
                        for rr_buy, rr_sell in rr_pairs:
                            r_dict = {}
                            if exit_mode == "POINTS":
                                tp_buy = max(floor_tp, snap_tick(sl * rr_buy))
                                tp_sell = max(floor_tp, snap_tick(sl * rr_sell))
                                trail = max(floor_trail, snap_tick(sl * trail_ratio)) if trail_ratio > 0 else 0.0
                                r_dict = {
                                    "points_sl_buy": sl, "points_target_buy": tp_buy, "points_trail_buy": trail,
                                    "points_be_buy": be,
                                    "points_sl_sell": sl, "points_target_sell": tp_sell, "points_trail_sell": trail,
                                    "points_be_sell": be
                                }
                            else: # ATR mode
                                tp_mult_buy = sl * rr_buy
                                tp_mult_sell = sl * rr_sell
                                trail_mult = sl * trail_ratio
                                r_dict = {
                                    "sl_mult_buy": sl, "tp_mult_buy": tp_mult_buy, "trailing_mult_buy": trail_mult,
                                    "atr_be_buy": be,
                                    "sl_mult_sell": sl, "tp_mult_sell": tp_mult_sell, "trailing_mult_sell": trail_mult,
                                    "atr_be_sell": be
                                }
                            risk_sweep.append(r_dict)
                    else: # BUY or SELL
                        for rr in rr_vals:
                            r_dict = {}
                            if exit_mode == "POINTS":
                                tp = max(floor_tp, snap_tick(sl * rr))
                                trail = max(floor_trail, snap_tick(sl * trail_ratio)) if trail_ratio > 0 else 0.0
                                if leg_mode == "BUY":
                                    r_dict = {
                                        "points_sl_buy": sl, "points_target_buy": tp, "points_trail_buy": trail,
                                        "points_be_buy": be
                                    }
                                else: # SELL
                                    r_dict = {
                                        "points_sl_sell": sl, "points_target_sell": tp, "points_trail_sell": trail,
                                        "points_be_sell": be
                                    }
                            else: # ATR mode
                                tp_mult = sl * rr
                                trail_mult = sl * trail_ratio
                                if leg_mode == "BUY":
                                    r_dict = {
                                        "sl_mult_buy": sl, "tp_mult_buy": tp_mult, "trailing_mult_buy": trail_mult,
                                        "atr_be_buy": be
                                    }
                                else: # SELL
                                    r_dict = {
                                        "sl_mult_sell": sl, "tp_mult_sell": tp_mult, "trailing_mult_sell": trail_mult,
                                        "atr_be_sell": be
                                    }
                            risk_sweep.append(r_dict)
                            
        # Apply safety limit of max 100 risk combos for high speed & robustness
        max_risk_combos = 100
        if len(risk_sweep) > max_risk_combos:
            print(f"[INFO] Generated risk combinations ({len(risk_sweep)}) exceeds safety limit ({max_risk_combos}) for Stage 2.")
            print(f"       Applying Shuffled Random Sampling with fixed seed (42) to select {max_risk_combos} combinations...")
            random.seed(42)
            risk_sweep = random.sample(risk_sweep, max_risk_combos)
            
        for strat_params in unique_strat_combos:
            for r_combo in risk_sweep:
                fine_risk_combos.append({**strat_params, **r_combo})

    df_stage2 = run_grid_sweep(
        fine_risk_combos, leg_mode, engine.instrument_name, config, engine.inst_config, 
        df_spot_train, strategy_name, label="Stage 2 Sweep", sort_by=sort_by, mc_iter=100
    )
    
    if df_stage2.empty:
        raise ValueError("Stage 2 returned no viable trading metrics. Optimization stopped.")

    # Stage 2.5: Sensitivity Check & Plateau Optimization
    print("\n[STAGE 2.5] Performing Parameter Sensitivity Plateau Check...")
    top_count = max(1, int(len(df_stage2) * 0.1))
    top_indices = df_stage2.index[:top_count]
    
    lookup = {}
    for idx, row in df_stage2.iterrows():
        strat_key = tuple(row[k] for k in keys)
        if exit_mode == "POINTS":
            if leg_mode in ["BUY", "BOTH"]:
                risk_key = (row.get("points_sl_buy"), row.get("points_target_buy"), row.get("points_trail_buy"), row.get("points_be_buy"))
            else:
                risk_key = (row.get("points_sl_sell"), row.get("points_target_sell"), row.get("points_trail_sell"), row.get("points_be_sell"))
        else:
            if leg_mode in ["BUY", "BOTH"]:
                risk_key = (row.get("sl_mult_buy"), row.get("tp_mult_buy"), row.get("trailing_mult_buy"), row.get("atr_be_buy"))
            else:
                risk_key = (row.get("sl_mult_sell"), row.get("tp_mult_sell"), row.get("trailing_mult_sell"), row.get("atr_be_sell"))
        lookup[(strat_key, risk_key)] = row.get("Net_PnL", 0.0)

    penalized_scores = []
    for idx, row in df_stage2.iterrows():
        score = row["Robustness_Score"]
        strat_key = tuple(row[k] for k in keys)
        if idx in top_indices and score > 0:
            if exit_mode == "POINTS":
                if leg_mode in ["BUY", "BOTH"]:
                    sl = row.get("points_sl_buy")
                    tp = row.get("points_target_buy")
                    trail = row.get("points_trail_buy")
                    be = row.get("points_be_buy")
                else:
                    sl = row.get("points_sl_sell")
                    tp = row.get("points_target_sell")
                    trail = row.get("points_trail_sell")
                    be = row.get("points_be_sell")
            else:
                if leg_mode in ["BUY", "BOTH"]:
                    sl = row.get("sl_mult_buy")
                    tp = row.get("tp_mult_buy")
                    trail = row.get("trailing_mult_buy")
                    be = row.get("atr_be_buy")
                else:
                    sl = row.get("sl_mult_sell")
                    tp = row.get("tp_mult_sell")
                    trail = row.get("trailing_mult_sell")
                    be = row.get("atr_be_sell")
            
            try:
                sl_idx = sl_vals.index(sl)
            except ValueError:
                sl_idx = -1
                
            all_tps = sorted(list(set(k[1][1] for k in lookup.keys() if k[0] == strat_key)))
            try:
                tp_idx = all_tps.index(tp)
            except ValueError:
                tp_idx = -1
                
            neighbors = []
            if sl_idx > 0:
                neighbors.append((sl_vals[sl_idx-1], tp, trail, be))
            if sl_idx >= 0 and sl_idx < len(sl_vals) - 1:
                neighbors.append((sl_vals[sl_idx+1], tp, trail, be))
            if tp_idx > 0:
                neighbors.append((sl, all_tps[tp_idx-1], trail, be))
            if tp_idx >= 0 and tp_idx < len(all_tps) - 1:
                neighbors.append((sl, all_tps[tp_idx+1], trail, be))
                
            unprofitable_neighbors = sum(1 for n_risk in neighbors if lookup.get((strat_key, n_risk), 0.0) <= 0)
            if unprofitable_neighbors > 0:
                # Soften the penalty to avoid discarding local optima
                penalty = min(0.2, unprofitable_neighbors * 0.05)
                score = round(score * (1.0 - penalty), 3)
        penalized_scores.append(score)
        
    df_stage2["Robustness_Score"] = penalized_scores
    sort_col = METRIC_MAP.get(sort_by, "Robustness_Score")
    df_stage2 = df_stage2.sort_values(sort_col, ascending=False)

    trading_candidates = df_stage2[df_stage2["Total_Trades"] > 0]
    df_stage2_for_selection = trading_candidates if not trading_candidates.empty else df_stage2

    prefix = engine.instrument_name.lower()
    df_stage2_top50 = df_stage2_for_selection.head(50)
    df_stage2_top50.to_csv(os.path.join(RESULTS_DIR, f"{prefix}_fine_risk_optimization_{execution_mode}_{exit_mode}.csv"), index=False)
    print(f"[SUCCESS] Stage 2 complete! Top 50 results saved to {prefix}_fine_risk_optimization_{execution_mode}_{exit_mode}.csv")

    # Stage 2.6: Parameter Plateau Selection (Priority 5)
    print("\n[STAGE 2.6] Performing Plateau Parameter Frequency Mode Selection on Top 30 candidates...")
    try:
        cluster_keys = []
        if exit_mode == "POINTS":
            if leg_mode in ["BUY", "BOTH"]:
                cluster_keys += ["points_sl_buy", "points_target_buy", "points_trail_buy", "points_be_buy"]
            if leg_mode in ["SELL", "BOTH"]:
                cluster_keys += ["points_sl_sell", "points_target_sell", "points_trail_sell", "points_be_sell"]
        else:
            if leg_mode in ["BUY", "BOTH"]:
                cluster_keys += ["sl_mult_buy", "tp_mult_buy", "trailing_mult_buy", "atr_be_buy"]
            if leg_mode in ["SELL", "BOTH"]:
                cluster_keys += ["sl_mult_sell", "tp_mult_sell", "trailing_mult_sell", "atr_be_sell"]
                
        # Include strategy keys to ensure risk settings align with the most frequent strategy
        cluster_keys = list(set([k for k in cluster_keys + keys if k in df_stage2_top50.columns]))
        
        top_30 = df_stage2_top50.head(30)
        if len(top_30) >= 3 and cluster_keys:
            # 1. Compute the mode for each key across the top 30
            modes = {}
            for k in cluster_keys:
                modes[k] = top_30[k].mode()[0]
                
            # 2. For each candidate in top 30, count how many parameters match the modes
            match_counts = []
            for idx, row in top_30.iterrows():
                matches = sum(1 for k in cluster_keys if row[k] == modes[k])
                match_counts.append((matches, row["Robustness_Score"], idx))
                
            # 3. Sort candidates by matches (descending) and then robustness score (descending)
            match_counts.sort(key=lambda x: (-x[0], -x[1]))
            best_idx = match_counts[0][2]
            best_overall_train = df_stage2_top50.loc[best_idx]
            
            # Extract the actual strategy parameters for the winning candidate
            best_strat_params = {k: best_overall_train[k] for k in keys}
            print(f"[SUCCESS] Parameter plateau selection complete! Selected tested candidate representing the mode parameter centroid.")
            print(f"          Selected candidate strategy params: {best_strat_params}")
        else:
            best_overall_train = df_stage2_for_selection.iloc[0]
            best_strat_params = {k: best_overall_train[k] for k in keys}
            print("[INFO] Insufficient combinations/keys for plateau selection. Defaulting to peak candidate.")
    except Exception as e:
        print(f"[WARNING] Parameter plateau selection failed: {e}. Defaulting to peak candidate.")
        best_overall_train = df_stage2_for_selection.iloc[0]
        best_strat_params = {k: best_overall_train[k] for k in keys}

    return best_strat_params, best_overall_train

# =========================================================================
#  MAIN OPTIMIZATION PIPELINE
# =========================================================================
def run_optimization(instrument_name, strategy_name, leg_mode, backtest_days, max_combos=50, mode="single", sort_by="robustness", exit_sweep=False):
    print("=" * 80)
    print(f"   JOINT PARAMETER SEARCH & WALK-FORWARD OPTIMIZER: {instrument_name}   ")
    print(f"   Strategy: {strategy_name} | Mode: {leg_mode} | Period: {backtest_days} Days")
    print("=" * 80)

    # 1. Initialize baseline configurations
    config = BacktestConfig()
    config.LEG_MODE = leg_mode
    
    for name in STRATEGY_REGISTRY.keys():
        toggle_name = f"ENABLE_{name.upper()}"
        setattr(config, toggle_name, (name == strategy_name))
    config.apply_strategy_defaults(strategy_name)

    engine = SimulationEngine(config, instrument_name=instrument_name, offline_mode=False, backtest_days=backtest_days)
    engine.load_data()
    
    df_spot_raw_all = engine.df_spot[['open', 'high', 'low', 'close', 'volume']].copy()
    print(f"[INFO] Loaded spot dataset size: {len(df_spot_raw_all)} rows.")
    print(f"[INFO] Timeline bounds: {df_spot_raw_all.index.min().date()} to {df_spot_raw_all.index.max().date()}")

    execution_mode = engine.inst_config.get("execution_mode", "OPTION")
    exit_mode = engine.inst_config.get("exit_mode", "ATR")
    is_stock = (execution_mode == "STOCK")

    # 2. Targeted Thread-pooled Option Contract Warmup Pass
    if not is_stock:
        print("\n[INFO] Running concurrent targeted warmup pass to populate options data cache...")
        try:
            # Generate spot signals to find exact dates of entry breakouts
            df_sig = engine.strategy.generate_signals(df_spot_raw_all.copy())
            from backtest_engine import NSE_HOLIDAYS
            df_sig = df_sig[df_sig['Signal'] != 0]
            df_sig = df_sig[df_sig.index.dayofweek < 5]
            df_sig = df_sig[~df_sig.index.strftime('%Y-%m-%d').isin(NSE_HOLIDAYS)]
            
            strike_step = engine.inst_config.get('strike_step', 100)
            strike_offset = engine.inst_config.get('strike_offset', 0)
            width = engine.inst_config.get("strategy_leg_width", 1)
            strat_mode = engine.inst_config.get("option_strategy_mode", "DIRECT")
            
            offsets_to_check = [0, strike_offset]
            if strat_mode != "DIRECT":
                offsets_to_check.append(strike_offset + width)
            offsets = sorted(list(set([o for o in offsets_to_check if o is not None])))
            
            requested_contracts = set()
            for ts, row in df_sig.iterrows():
                trade_date = ts.date()
                spot_price = row['close']
                atm_strike = int(round(spot_price / strike_step) * strike_step)
                for offset in offsets:
                    strike = atm_strike + (offset * strike_step)
                    sig_val = row['Signal']
                    types_to_fetch = []
                    if strat_mode != "DIRECT":
                        types_to_fetch.extend(["CE", "PE"])
                    else:
                        if leg_mode in ["BUY", "BOTH"] and sig_val > 0:
                            types_to_fetch.append("CE")
                        if leg_mode in ["SELL", "BOTH"] and sig_val < 0:
                            types_to_fetch.append("PE")
                    for opt_type in types_to_fetch:
                        requested_contracts.add((trade_date, strike, opt_type))
                        
            total_contracts = len(requested_contracts)
            print(f"[INFO] Found {total_contracts} unique option contracts to fetch for warmup.")
            
            if total_contracts > 0:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                def fetch_single(args_tuple):
                    t_date, strk, o_type = args_tuple
                    try:
                        engine._get_option_candles(strk, o_type, t_date)
                        return True
                    except Exception:
                        return False
                
                # Limit to 4 concurrent threads to protect Dhan API rate limits
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {executor.submit(fetch_single, arg): arg for arg in requested_contracts}
                    completed = 0
                    for future in as_completed(futures):
                        completed += 1
                        if completed % 20 == 0 or completed == total_contracts:
                            print(f"  Warmup Progress: {completed}/{total_contracts} option contracts populated.")
                            
            print(f"[SUCCESS] Warmup complete. In-memory option cache holds {len(engine._opt_df_cache)} contracts.")
        except Exception as e:
            print(f"[WARNING] Warmup pass encountered an error: {e}. Falling back to dynamic fetching during sweeps.")
    else:
        print("\n[INFO] STOCK execution mode detected. Bypassing options data pre-fetch.")

    if exit_sweep:
        # Run a comparative sweep of POINTS, ATR, and SWING exit modes
        orig_exit_mode = engine.inst_config.get("exit_mode", "ATR")
        orig_grid = engine.inst_config.get("optimization_grid", {})
        
        sweep_modes = ["POINTS", "ATR", "SWING"]
        sweep_results = []
        
        # Calculate Train/Test Split (67% Train, 33% Test)
        unique_dates = sorted(list(set(df_spot_raw_all.index.date)))
        if len(unique_dates) >= 3:
            split_idx = int(len(unique_dates) * 0.67)
            split_date = unique_dates[split_idx]
            train_end_ts = pd.Timestamp(split_date)
        else:
            train_end_ts = df_spot_raw_all.index[int(len(df_spot_raw_all) * 0.67)]

        df_spot_train = df_spot_raw_all[df_spot_raw_all.index < train_end_ts].copy()
        df_spot_test = df_spot_raw_all[df_spot_raw_all.index >= train_end_ts].copy()
        
        train_dates = df_spot_train.index.date
        train_days = (train_dates.max() - train_dates.min()).days if len(train_dates) > 0 else 365
        test_dates = df_spot_test.index.date
        test_days = (test_dates.max() - test_dates.min()).days if len(test_dates) > 0 else 180

        for em in sweep_modes:
            print("\n" + "=" * 60)
            print(f" [EXIT SWEEP] Optimizing under exit_mode: {em}")
            print("=" * 60)
            
            # Temporary setup
            engine.inst_config["exit_mode"] = em
            if "optimization_grid" in engine.inst_config:
                del engine.inst_config["optimization_grid"]
                
            try:
                # 1. Run optimization on train data
                best_strat_params, best_overall_train = optimize_in_sample(
                    df_spot_train, engine, strategy_name, leg_mode, max_combos, config, sort_by=sort_by
                )
                
                # 2. Setup testing engine
                config_wf = BacktestConfig()
                config_wf.LEG_MODE = leg_mode
                for name in STRATEGY_REGISTRY.keys():
                    setattr(config_wf, f"ENABLE_{name.upper()}", (name == strategy_name))
                config_wf.apply_strategy_defaults(strategy_name)
                
                for k, v in best_strat_params.items():
                    setattr(config_wf, k, v)
                    
                engine_test = SimulationEngine(config_wf, instrument_name=instrument_name, offline_mode=False)
                engine_test.inst_config.update(engine.inst_config)
                
                risk_keys = [
                    'sl_mult_buy', 'tp_mult_buy', 'trailing_mult_buy', 'atr_be_buy',
                    'sl_mult_sell', 'tp_mult_sell', 'trailing_mult_sell', 'atr_be_sell',
                    'points_sl_buy', 'points_target_buy', 'points_trail_buy', 'points_be_buy',
                    'points_sl_sell', 'points_target_sell', 'points_trail_sell', 'points_be_sell'
                ]
                for r_k in risk_keys:
                    if r_k in best_overall_train:
                        engine_test.inst_config[r_k] = best_overall_train[r_k]
                
                # 3. Out-Of-Sample (TEST) validation pass
                df_test_sig = engine_test.strategy.generate_signals(df_spot_test.copy())
                engine_test.df_spot = df_test_sig
                engine_test.trades = []
                engine_test.active_trades = []
                engine_test.cooldown_until = None
                engine_test.run(write_to_csv=False)
                
                test_result = evaluate_pnls(engine_test.trades, backtest_days=test_days, strategy_name=strategy_name)
                
                # Store key params for formatting
                if em == "POINTS":
                    k_sl = "points_sl_buy" if leg_mode in ["BUY", "BOTH"] else "points_sl_sell"
                    k_tp = "points_target_buy" if leg_mode in ["BUY", "BOTH"] else "points_target_sell"
                else:
                    k_sl = "sl_mult_buy" if leg_mode in ["BUY", "BOTH"] else "sl_mult_sell"
                    k_tp = "tp_mult_buy" if leg_mode in ["BUY", "BOTH"] else "tp_mult_sell"
                    
                val_sl = best_overall_train.get(k_sl)
                val_tp = best_overall_train.get(k_tp)
                
                sweep_results.append({
                    "Exit_Mode": em,
                    "SL": val_sl,
                    "Target": val_tp,
                    "Trades": test_result["Total_Trades"],
                    "Win_Rate": test_result["Win_Rate"],
                    "Profit_Factor": test_result["Profit_Factor"],
                    "Net_PnL": test_result["Net_PnL"],
                    "Max_DD": test_result["Max_Drawdown"],
                    "Robustness_Score": test_result["Robustness_Score"]
                })
            except Exception as e:
                print(f"[ERROR] Failed exit sweep loop for {em}: {e}")
                
        # Restore original configs
        engine.inst_config["exit_mode"] = orig_exit_mode
        if orig_grid:
            engine.inst_config["optimization_grid"] = orig_grid
        elif "optimization_grid" in engine.inst_config:
            del engine.inst_config["optimization_grid"]
            
        # Print comparative matrix
        print("\n" + "=" * 90)
        print(f"             COMPARATIVE EXIT MODE OPTIMIZATION REPORT: {instrument_name}             ")
        print("=" * 90)
        print(f"  {'Exit Mode':<15} | {'Best SL/Target':<16} | {'Trades':<6} | {'Win Rate':<8} | {'PF':<5} | {'Net PnL (Rs.)':<13} | {'Max DD':<7} | {'Robustness':<10}")
        print("-" * 90)
        for r in sweep_results:
            param_display = f"SL={r['SL']}, TP={r['Target']}"
            print(f"  {r['Exit_Mode']:<15} | {param_display:<16} | {r['Trades']:<6} | {r['Win_Rate']:<7}% | {r['Profit_Factor']:<5.2f} | "
                  f"Rs.{r['Net_PnL']:<10.2f} | Rs.{r['Max_DD']:<5.0f} | {r['Robustness_Score']:<10.3f}")
        print("=" * 90)
        
        # Save sweep report
        prefix = instrument_name.lower()
        sweep_df = pd.DataFrame(sweep_results)
        sweep_df.to_csv(os.path.join(RESULTS_DIR, f"{prefix}_exit_mode_sweep_comparison.csv"), index=False)
        print(f"[SUCCESS] Exit mode sweep comparison saved to {prefix}_exit_mode_sweep_comparison.csv\n")
        return

    if mode == "rolling":
        print("\n[INFO] Running Rolling Walk-Forward Optimization (WFO)...")
        windows = generate_rolling_windows(df_spot_raw_all, train_months=6, test_months=2, step_months=2)
        if not windows:
            print("[WARNING] Not enough data to generate rolling windows. Falling back to single-split mode.")
            mode = "single"
            
    if mode == "rolling":
        all_oos_trades = []
        window_results = []
        
        config_wf = BacktestConfig()
        config_wf.LEG_MODE = leg_mode
        for name in STRATEGY_REGISTRY.keys():
            setattr(config_wf, f"ENABLE_{name.upper()}", (name == strategy_name))
        config_wf.apply_strategy_defaults(strategy_name)
        
        for idx, window in enumerate(windows, 1):
            train_start, train_end = window["train_start"], window["train_end"]
            test_start, test_end = window["test_start"], window["test_end"]
            print("\n" + "=" * 60)
            print(f"   WINDOW {idx}/{len(windows)}: Train ({train_start.date()} to {train_end.date()}) | Test ({test_start.date()} to {test_end.date()})")
            print("=" * 60)
            
            df_spot_train = df_spot_raw_all[(df_spot_raw_all.index >= train_start) & (df_spot_raw_all.index < train_end)].copy()
            df_spot_test = df_spot_raw_all[(df_spot_raw_all.index >= test_start) & (df_spot_raw_all.index < test_end)].copy()
            
            if len(df_spot_train) < 10 or len(df_spot_test) < 5:
                print(f"[WARNING] Skipping window {idx} due to insufficient data rows.")
                continue
                
            try:
                best_strat_params, best_overall_train = optimize_in_sample(
                    df_spot_train, engine, strategy_name, leg_mode, max_combos, config, sort_by=sort_by
                )
            except Exception as e:
                print(f"[WARNING] Optimization failed for Window {idx}: {e}. Skipping window.")
                continue
            
            # Run backtest on Train and Test with these parameters to measure IS and OOS performance
            engine_test = SimulationEngine(config_wf, instrument_name=instrument_name, offline_mode=False)
            engine_test.inst_config.update(engine.inst_config)
            
            for k, v in best_strat_params.items():
                setattr(engine_test.config, k, v)
                
            risk_keys = [
                'sl_mult_buy', 'tp_mult_buy', 'trailing_mult_buy', 'atr_be_buy',
                'sl_mult_sell', 'tp_mult_sell', 'trailing_mult_sell', 'atr_be_sell',
                'points_sl_buy', 'points_target_buy', 'points_trail_buy', 'points_be_buy',
                'points_sl_sell', 'points_target_sell', 'points_trail_sell', 'points_be_sell'
            ]
            for r_k in risk_keys:
                if r_k in best_overall_train:
                    engine_test.inst_config[r_k] = best_overall_train[r_k]
                    
            # In-Sample (TRAIN) validation pass
            df_train_sig = engine_test.strategy.generate_signals(df_spot_train.copy())
            engine_test.df_spot = df_train_sig
            engine_test.trades = []
            engine_test.active_trades = []
            engine_test.cooldown_until = None
            engine_test.run(write_to_csv=False)
            train_dates = df_spot_train.index.date
            train_days = (train_dates.max() - train_dates.min()).days if len(train_dates) > 0 else 180
            train_result = evaluate_pnls(engine_test.trades, backtest_days=train_days, strategy_name=strategy_name)
            
            # Out-Of-Sample (TEST) validation pass
            df_test_sig = engine_test.strategy.generate_signals(df_spot_test.copy())
            engine_test.df_spot = df_test_sig
            engine_test.trades = []
            engine_test.active_trades = []
            engine_test.cooldown_until = None
            engine_test.run(write_to_csv=False)
            test_dates = df_spot_test.index.date
            test_days = (test_dates.max() - test_dates.min()).days if len(test_dates) > 0 else 60
            test_result = evaluate_pnls(engine_test.trades, backtest_days=test_days, strategy_name=strategy_name)
            
            # Accumulate OOS trades
            all_oos_trades.extend(engine_test.trades)
            
            best_params_display = {**best_strat_params}
            for r_k in risk_keys:
                if r_k in best_overall_train:
                    best_params_display[r_k] = best_overall_train[r_k]
                    
            window_results.append({
                "Window": idx,
                "Train_Start": str(train_start.date()),
                "Train_End": str(train_end.date()),
                "Test_Start": str(test_start.date()),
                "Test_End": str(test_end.date()),
                "Train_Trades": train_result["Total_Trades"],
                "Train_Win_Rate": train_result["Win_Rate"],
                "Train_PF": train_result["Profit_Factor"],
                "Train_PnL": train_result["Net_PnL"],
                "Test_Trades": test_result["Total_Trades"],
                "Test_Win_Rate": test_result["Win_Rate"],
                "Test_PF": test_result["Profit_Factor"],
                "Test_PnL": test_result["Net_PnL"],
                "Params": json.dumps(best_params_display, cls=NumpyEncoder)
            })
            
            print(f"[WINDOW {idx} RESULT] Train PnL: Rs.{train_result['Net_PnL']:.2f} | Test PnL: Rs.{test_result['Net_PnL']:.2f}")

        # Combine and sort all Out-Of-Sample (OOS) trades
        all_oos_trades = sorted(all_oos_trades, key=lambda x: pd.to_datetime(x["Entry_Time"]))
        
        # Calculate span of OOS test periods
        total_test_days = 0
        if windows:
            total_test_days = sum((w["test_end"] - w["test_start"]).days for w in windows)
        if total_test_days <= 0:
            total_test_days = backtest_days
            
        combined_oos_result = evaluate_pnls(all_oos_trades, backtest_days=total_test_days, strategy_name=strategy_name)
        
        # Calculate average train result metrics
        avg_train_res = {}
        if window_results:
            keys_to_avg = ["Train_Trades", "Train_Win_Rate", "Train_PF", "Train_PnL"]
            for k in keys_to_avg:
                avg_train_res[k.replace("Train_", "")] = np.mean([w[k] for w in window_results])
            train_res_for_log = {
                "Total_Trades": int(avg_train_res.get("Trades", 0)),
                "Win_Rate": round(avg_train_res.get("Win_Rate", 0.0), 1),
                "Profit_Factor": round(avg_train_res.get("PF", 0.0), 3),
                "Net_PnL": round(avg_train_res.get("PnL", 0.0), 2),
                "Max_Drawdown": 0.0
            }
        else:
            train_res_for_log = evaluate_pnls([], strategy_name=strategy_name)
            
        # Print Walk-Forward Comparative Report
        print("\n" + "=" * 80)
        print(f"             COMBINED WALK-FORWARD OOS PERFORMANCE REPORT: {instrument_name}             ")
        print("=" * 80)
        print(f"  {'Dataset Partition':<22} | {'Trades':<6} | {'Win Rate':<8} | {'PF':<5} | {'Net PnL (Rs.)':<13} | {'Max DD':<7}")
        print("-" * 80)
        if window_results:
            print(f"  {'TRAIN (Average IS)':<22} | {train_res_for_log['Total_Trades']:<6} | {train_res_for_log['Win_Rate']:<7}% | {train_res_for_log['Profit_Factor']:<5.2f} | "
                  f"Rs.{train_res_for_log['Net_PnL']:<10.2f} | N/A")
        print(f"  {'TEST (Combined OOS)':<22} | {combined_oos_result['Total_Trades']:<6} | {combined_oos_result['Win_Rate']:<7}% | {combined_oos_result['Profit_Factor']:<5.2f} | "
              f"Rs.{combined_oos_result['Net_PnL']:<10.2f} | Rs.{combined_oos_result['Max_Drawdown']:<5.0f}")
        print("-" * 80)
        
        # Calculate WFE
        oos_daily = combined_oos_result['Net_PnL'] / total_test_days if total_test_days > 0 else 0
        train_daily = train_res_for_log['Net_PnL'] / 180.0
        wfe = oos_daily / train_daily if train_daily > 0 else 0.0
        
        if wfe >= 0.67:
            wfe_status = "[HIGHLY ROBUST] Excellent out-of-sample consistency."
        elif wfe >= 0.50:
            wfe_status = "[STABLE] Moderate out-of-sample decay."
        else:
            wfe_status = "[WARNING: HIGH OVERFITTING RISK] Parameter set shows severe out-of-sample decay."
            
        print(f"  Walk-Forward Efficiency (WFE): {wfe:.2%}  {wfe_status}")
        
        if combined_oos_result['Net_PnL'] > 0:
            verdict = f"[ROBUST] Combined OOS is profitable (WFE: {wfe:.1%})."
        else:
            verdict = f"[NOT VIABLE] Combined OOS loses money (WFE: {wfe:.1%})."
        print(f"  VERDICT: {verdict}")
        print("=" * 80)
        
        # Save Walk-Forward report
        report_rows = []
        for w_res in window_results:
            report_rows.append({
                "Period": f"WINDOW_{w_res['Window']}_TRAIN",
                "Start_Date": w_res["Train_Start"],
                "End_Date": w_res["Train_End"],
                "Total_Trades": w_res["Train_Trades"],
                "Win_Rate": w_res["Train_Win_Rate"],
                "Profit_Factor": w_res["Train_PF"],
                "Net_PnL": w_res["Train_PnL"],
                "Selected_Params": w_res["Params"]
            })
            report_rows.append({
                "Period": f"WINDOW_{w_res['Window']}_TEST",
                "Start_Date": w_res["Test_Start"],
                "End_Date": w_res["Test_End"],
                "Total_Trades": w_res["Test_Trades"],
                "Win_Rate": w_res["Test_Win_Rate"],
                "Profit_Factor": w_res["Test_PF"],
                "Net_PnL": w_res["Test_PnL"],
                "Selected_Params": w_res["Params"]
            })
            
        report_rows.append({
            "Period": "COMBINED_OOS",
            "Start_Date": str(windows[0]["test_start"].date()) if windows else "",
            "End_Date": str(windows[-1]["test_end"].date()) if windows else "",
            "Total_Trades": combined_oos_result["Total_Trades"],
            "Win_Rate": combined_oos_result["Win_Rate"],
            "Profit_Factor": combined_oos_result["Profit_Factor"],
            "Net_PnL": combined_oos_result["Net_PnL"],
            "MC_Worst_DD_95Pct": combined_oos_result["MC_Worst_DD_95Pct"],
            "MC_Robustness": combined_oos_result["MC_Robustness"],
            "Equity_R2": combined_oos_result["Equity_R2"],
            "Selected_Params": f"Combined Walk-Forward (WFE: {wfe:.2%})"
        })
        
        prefix = instrument_name.lower()
        wf_df = pd.DataFrame(report_rows)
        wf_df.to_csv(os.path.join(RESULTS_DIR, f"{prefix}_walk_forward_validation_{execution_mode}_{exit_mode}.csv"), index=False)
        print(f"[SUCCESS] Walk-Forward report saved to {prefix}_walk_forward_validation_{execution_mode}_{exit_mode}.csv\n")
        
        best_params_log = {"Walk-Forward": f"Rolling WFO (WFE: {wfe:.2%})"}
        if window_results:
            try:
                best_params_log = json.loads(window_results[-1]["Params"])
                best_params_log["WFE"] = f"{wfe:.2%}"
            except Exception:
                pass
                
        log_experiment_to_tracker(
            run_type="Walk-Forward (Rolling)",
            instrument=instrument_name,
            strategy_name=strategy_name,
            leg_mode=leg_mode,
            days=backtest_days,
            train_res=train_res_for_log,
            test_res=combined_oos_result,
            best_params=best_params_log,
            verdict=verdict
        )
        return

    if mode == "single":
        # 3. Calculate Train/Test Split (67% Train, 33% Test)
        unique_dates = sorted(list(set(df_spot_raw_all.index.date)))
        if len(unique_dates) >= 3:
            split_idx = int(len(unique_dates) * 0.67)
            split_date = unique_dates[split_idx]
            train_end_ts = pd.Timestamp(split_date)
        else:
            train_end_ts = df_spot_raw_all.index[int(len(df_spot_raw_all) * 0.67)]

        df_spot_train = df_spot_raw_all[df_spot_raw_all.index < train_end_ts].copy()
        df_spot_test = df_spot_raw_all[df_spot_raw_all.index >= train_end_ts].copy()

        print(f"\n[INFO] Data Partitioning:")
        print(f"  -> TRAIN (In-Sample): {df_spot_train.index.min().date()} to {df_spot_train.index.max().date()} ({len(df_spot_train)} rows)")
        print(f"  -> TEST  (Out-of-Sample): {df_spot_test.index.min().date()} to {df_spot_test.index.max().date()} ({len(df_spot_test)} rows)")

        # Run optimize_in_sample helper to get best parameters
        best_strat_params, best_overall_train = optimize_in_sample(
            df_spot_train, engine, strategy_name, leg_mode, max_combos, config, sort_by=sort_by
        )
        
        exit_mode = engine.inst_config.get("exit_mode", "ATR")
        prefix = instrument_name.lower()

        print(f"\n[INFO] Best Overall Parameters on TRAIN split:")
        print(f"  -> Strategy: {best_strat_params}")
        if exit_mode == "POINTS":
            if leg_mode in ["BUY", "BOTH"]:
                print(f"  -> Buy Risk (Points): SL={best_overall_train.get('points_sl_buy')}, Target={best_overall_train.get('points_target_buy')}, Trail={best_overall_train.get('points_trail_buy')}, BE={best_overall_train.get('points_be_buy')}")
            if leg_mode in ["SELL", "BOTH"]:
                print(f"  -> Sell Risk (Points): SL={best_overall_train.get('points_sl_sell')}, Target={best_overall_train.get('points_target_sell')}, Trail={best_overall_train.get('points_trail_sell')}, BE={best_overall_train.get('points_be_sell')}")
        else:
            if leg_mode in ["BUY", "BOTH"]:
                print(f"  -> Buy Risk: SL_mult={best_overall_train.get('sl_mult_buy')}, TP_mult={best_overall_train.get('tp_mult_buy')}, Trail_mult={best_overall_train.get('trailing_mult_buy')}, BE={best_overall_train.get('atr_be_buy')}")
            if leg_mode in ["SELL", "BOTH"]:
                print(f"  -> Sell Risk: SL_mult={best_overall_train.get('sl_mult_sell')}, TP_mult={best_overall_train.get('tp_mult_sell')}, Trail_mult={best_overall_train.get('trailing_mult_sell')}, BE={best_overall_train.get('atr_be_sell')}")

    # Stage 3: Walk-Forward Out-Of-Sample Validation (Single backtest runs)
    print("\n[STAGE 3] Running Walk-Forward Out-Of-Sample Validation on unseen TEST data...")
    
    config_wf = BacktestConfig()
    config_wf.LEG_MODE = leg_mode
    for name in STRATEGY_REGISTRY.keys():
        setattr(config_wf, f"ENABLE_{name.upper()}", (name == strategy_name))
    config_wf.apply_strategy_defaults(strategy_name)
    
    for k, v in best_strat_params.items():
        setattr(config_wf, k, v)

    engine_test = SimulationEngine(config_wf, instrument_name=instrument_name, offline_mode=False)
    engine_test.inst_config.update(engine.inst_config)

    risk_keys = [
        'sl_mult_buy', 'tp_mult_buy', 'trailing_mult_buy', 'atr_be_buy',
        'sl_mult_sell', 'tp_mult_sell', 'trailing_mult_sell', 'atr_be_sell',
        'points_sl_buy', 'points_target_buy', 'points_trail_buy', 'points_be_buy',
        'points_sl_sell', 'points_target_sell', 'points_trail_sell', 'points_be_sell'
    ]
    for r_k in risk_keys:
        if r_k in best_overall_train:
            engine_test.inst_config[r_k] = best_overall_train[r_k]

    # In-Sample (TRAIN) validation pass
    df_train_sig = engine_test.strategy.generate_signals(df_spot_train.copy())
    engine_test.df_spot = df_train_sig
    engine_test.trades = []
    engine_test.active_trades = []
    engine_test.cooldown_until = None
    engine_test.run(write_to_csv=False)
    train_dates = df_spot_train.index.date
    train_days = (train_dates.max() - train_dates.min()).days if len(train_dates) > 0 else 720
    train_result = evaluate_pnls(engine_test.trades, backtest_days=train_days, strategy_name=strategy_name)

    # Out-Of-Sample (TEST) validation pass
    df_test_sig = engine_test.strategy.generate_signals(df_spot_test.copy())
    engine_test.df_spot = df_test_sig
    engine_test.trades = []
    engine_test.active_trades = []
    engine_test.cooldown_until = None
    engine_test.run(write_to_csv=False)
    test_dates = df_spot_test.index.date
    test_days = (test_dates.max() - test_dates.min()).days if len(test_dates) > 0 else 720
    test_result = evaluate_pnls(engine_test.trades, backtest_days=test_days, strategy_name=strategy_name)

    # Output Comparative Report
    print("\n" + "=" * 80)
    print(f"                 WALK-FORWARD PERFORMANCE REPORT: {instrument_name}                 ")
    print("=" * 80)
    print(f"  {'Dataset Partition':<22} | {'Trades':<6} | {'Win Rate':<8} | {'PF':<5} | {'Net PnL (Rs.)':<13} | {'Max DD':<7}")
    print("-" * 80)
    print(f"  {'TRAIN (In-Sample)':<22} | {train_result['Total_Trades']:<6} | {train_result['Win_Rate']:<7}% | {train_result['Profit_Factor']:<5.2f} | "
          f"Rs.{train_result['Net_PnL']:<10.2f} | Rs.{train_result['Max_Drawdown']:<5.0f}")
    print(f"  {'TEST (Out-of-Sample)':<22} | {test_result['Total_Trades']:<6} | {test_result['Win_Rate']:<7}% | {test_result['Profit_Factor']:<5.2f} | "
          f"Rs.{test_result['Net_PnL']:<10.2f} | Rs.{test_result['Max_Drawdown']:<5.0f}")
    print("-" * 80)

    # Compute WFE
    oos_daily = test_result['Net_PnL'] / test_days if test_days > 0 else 0
    train_daily = train_result['Net_PnL'] / train_days if train_days > 0 else 0
    wfe = oos_daily / train_daily if train_daily > 0 else 0.0
    
    if wfe >= 0.67:
        wfe_status = "[HIGHLY ROBUST] Excellent out-of-sample consistency."
    elif wfe >= 0.50:
        wfe_status = "[STABLE] Moderate out-of-sample decay."
    else:
        wfe_status = "[WARNING: HIGH OVERFITTING RISK] Parameter set shows severe out-of-sample decay."
        
    print(f"  Walk-Forward Efficiency (WFE): {wfe:.2%}  {wfe_status}")

    if train_result['Net_PnL'] > 0 and test_result['Net_PnL'] > 0:
        verdict = f"[ROBUST] Profitable on both splits (WFE: {wfe:.1%})."
    elif train_result['Net_PnL'] > 0 and test_result['Net_PnL'] <= 0:
        verdict = f"[OVERFITTED] Strategy loses money on test split (WFE: {wfe:.1%})."
    else:
        verdict = f"[NOT VIABLE] Strategy failed on train split (WFE: {wfe:.1%})."
    print(f"  VERDICT: {verdict}")
    print("=" * 80)

    # Save Walk-Forward report
    wf_df = pd.DataFrame([
        {"Period": "TRAIN_IN_SAMPLE", **train_result},
        {"Period": "TEST_OUT_OF_SAMPLE", **test_result}
    ])
    wf_df.to_csv(os.path.join(RESULTS_DIR, f"{prefix}_walk_forward_validation.csv"), index=False)
    print(f"[SUCCESS] Walk-Forward report saved to {prefix}_walk_forward_validation.csv\n")

    # Construct combined parameters dictionary for logging
    combined_params = {**best_strat_params}
    combined_params["WFE"] = f"{wfe:.2%}"
    risk_keys = [
        'sl_mult_buy', 'tp_mult_buy', 'trailing_mult_buy',
        'sl_mult_sell', 'tp_mult_sell', 'trailing_mult_sell',
        'points_sl_buy', 'points_target_buy', 'points_trail_buy',
        'points_sl_sell', 'points_target_sell', 'points_trail_sell'
    ]
    for r_k in risk_keys:
        if r_k in best_overall_train:
            combined_params[r_k] = best_overall_train[r_k]
            
    # Log to local history tracker
    log_experiment_to_tracker(
        run_type="Optimization",
        instrument=instrument_name,
        strategy_name=strategy_name,
        leg_mode=leg_mode,
        days=backtest_days,
        train_res=train_result,
        test_res=test_result,
        best_params=combined_params,
        verdict=verdict
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified Grid Search and Walk-Forward Optimizer")
    parser.add_argument("--strategy", "-s", type=str, default="Strategy_3", help="Strategy key (e.g. Strategy_3, Strategy_5)")
    parser.add_argument("--days", "-d", type=int, default=720, help="Total dataset backtest days (default: 720)")
    parser.add_argument("--leg", "-l", type=str, default=None, help="Leg mode filter: BUY, SELL, BOTH (default: read from .env)")
    parser.add_argument("--max-combos", type=int, default=50, help="Max strategy combinations to random sample for performance safety")
    parser.add_argument("--symbol", "--sym", type=str, default=None, help="Specify a single symbol to optimize instead of all enabled instruments")
    parser.add_argument("--mode", type=str, default="rolling", choices=["single", "rolling"], help="Optimization mode: single train/test split or rolling walk-forward")
    parser.add_argument("--sort-by", type=str, default="robustness", choices=["robustness", "pnl", "recovery_factor", "expectancy", "winrate"], help="Objective metric to sort and select the best parameter combination (default: robustness)")
    parser.add_argument("--exit-sweep", action="store_true", help="Automatically sweep and compare POINTS, ATR, and SWING exit modes")
    args = parser.parse_args()

    # Determine execution mode from env
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
    leg_mode = args.leg
    if not leg_mode:
        leg_mode = os.getenv("LEG_MODE", "BOTH").upper()
    if leg_mode not in ["BUY", "SELL", "BOTH"]:
        leg_mode = "BOTH"

    # Load F&O underlying symbols from Dhan master cache to filter enabled symbols
    cache_path = os.path.join(BASE_DIR, "dhanhq_master_cache.csv")
    fno_symbols = set()
    if os.path.exists(cache_path):
        try:
            print("[INFO] Loading F&O symbols from dhanhq_master_cache.csv to filter instruments...")
            df_cache = pd.read_csv(
                cache_path,
                usecols=["INSTRUMENT", "UNDERLYING_SYMBOL"],
                dtype={"INSTRUMENT": str, "UNDERLYING_SYMBOL": str},
                low_memory=False
            )
            fno_df = df_cache[df_cache["INSTRUMENT"].isin(["OPTIDX", "OPTSTK"])]
            fno_symbols = set(fno_df["UNDERLYING_SYMBOL"].dropna().str.strip().str.upper().unique())
            print(f"[SUCCESS] Loaded {len(fno_symbols)} valid F&O underlying symbols from master cache.")
        except Exception as e:
            print(f"[WARNING] Failed to load F&O symbols from master cache: {e}")

    # Find enabled instruments from instruments.json
    inst_file = os.path.join(BASE_DIR, "instruments.json")
    enabled_symbols = []
    instruments = {}
    if os.path.exists(inst_file):
        try:
            with open(inst_file, "r") as f:
                instruments = json.load(f)
            for sym, config in instruments.items():
                if config.get("enabled", 0) == 1:
                    enabled_symbols.append(sym)
        except Exception as e:
            print(f"[ERROR] Failed to load instruments.json: {e}")
            
    filtered_symbols = []
    for sym in enabled_symbols:
        cfg = instruments.get(sym, {})
        exec_mode = cfg.get("execution_mode", "OPTION")
        if exec_mode == "STOCK":
            spot_file = os.path.join(BASE_DIR, "backtest_data", f"{sym.lower()}_spot.csv")
            if not os.path.exists(spot_file):
                print(f"[WARNING] Skipping STOCK instrument {sym} because spot data file {spot_file} is missing.")
                continue
            filtered_symbols.append(sym)
        else:
            # OPTION execution mode
            fno_prefix = cfg.get("fno_prefix", sym).upper()
            
            # Check F&O segment status in master cache
            if fno_symbols and fno_prefix not in fno_symbols:
                print(f"[WARNING] Skipping OPTION instrument {sym} (F&O Prefix: {fno_prefix}) because it is not in F&O segment in master cache.")
                continue
                
            # Check spot file existence
            spot_file = os.path.join(BASE_DIR, "backtest_data", f"{sym.lower()}_spot.csv")
            if not os.path.exists(spot_file):
                print(f"[WARNING] Skipping OPTION instrument {sym} because spot data file {spot_file} is missing.")
                continue
                
            filtered_symbols.append(sym)

    enabled_symbols = filtered_symbols
    if args.symbol:
        symbol_upper = args.symbol.upper()
        if symbol_upper in enabled_symbols:
            enabled_symbols = [symbol_upper]
        else:
            if symbol_upper in instruments:
                print(f"[WARNING] Symbol {symbol_upper} was filtered out from enabled sweep. Forcing inclusion.")
                enabled_symbols = [symbol_upper]
            else:
                print(f"[ERROR] Symbol {symbol_upper} not found in instruments.json!")
                import sys
                sys.exit(1)
    elif not enabled_symbols:
        print("[WARNING] No valid enabled symbols found. Defaulting to NIFTY.")
        enabled_symbols = ["NIFTY"]

    print(f"[INFO] Enabled instruments for optimization sweep: {enabled_symbols}")
    
    for symbol in enabled_symbols:
        run_optimization(symbol, args.strategy, leg_mode, args.days, args.max_combos, mode=args.mode, sort_by=args.sort_by, exit_sweep=args.exit_sweep)
