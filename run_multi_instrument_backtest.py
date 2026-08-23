import os
import json
import argparse
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from strategies import BacktestConfig
from backtest_engine import SimulationEngine

# Load .env settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

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
        "best_params": json.dumps(best_params, default=str) if best_params else "",
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

def main():
    print("=" * 80)
    print("        DYNAMIC MULTI-INSTRUMENT PARITY BACKTESTING REPORT LOG        ")
    print("=" * 80)
    
    # 1. Load instruments.json
    inst_file = os.path.join(BASE_DIR, "instruments.json")
    if not os.path.exists(inst_file):
        print(f"[ERROR] Could not find instruments.json at: {inst_file}")
        return
        
    try:
        with open(inst_file, "r") as f:
            instruments = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse instruments.json: {e}")
        return
        
    # 2. Parse command line arguments
    parser = argparse.ArgumentParser(description="Dynamic Multi-Instrument Parity Backtesting Runner")
    parser.add_argument("symbols", nargs="*", help="Instruments to backtest (e.g., NIFTY BHEL). If omitted, reads enabled from instruments.json")
    parser.add_argument("--strategy", "-s", type=int, choices=list(range(1, 24)), help="Strategy index to run (1-23). If omitted, uses active strategy from config/env")
    parser.add_argument("--leg-mode", "-l", choices=["BUY", "SELL", "BOTH"], help="Option leg execution mode (BUY, SELL, BOTH)")
    parser.add_argument("--offline", "-o", action="store_true", help="Run backtest in offline mode using preloaded ATM option files")
    parser.add_argument("--days", "-d", type=int, default=30, help="Number of days of history to backtest (default: 30)")
    
    args = parser.parse_args()
    
    # 3. Extract enabled instruments
    if args.symbols:
        enabled_instruments = [sym.upper() for sym in args.symbols]
        print(f"[INFO] Command line instruments specified: {enabled_instruments}\n")
    else:
        enabled_instruments = []
        for symbol, cfg in instruments.items():
            if cfg.get("enabled") == 1 or cfg.get("enabled") is True:
                enabled_instruments.append(symbol)
                
        if not enabled_instruments:
            print("[INFO] No instruments are enabled in instruments.json. Defaulting to NIFTY.")
            enabled_instruments = ["NIFTY"]
        else:
            print(f"[INFO] Found {len(enabled_instruments)} enabled instruments in instruments.json: {enabled_instruments}\n")
            
    # 4. Setup configurations
    config = BacktestConfig()
    
    # Align Leg Mode
    env_leg_mode = args.leg_mode or os.getenv("LEG_MODE", "BOTH").upper()
    if env_leg_mode in ["BUY", "SELL", "BOTH"]:
        config.LEG_MODE = env_leg_mode
        
    # Align Strategy
    if args.strategy:
        for i in range(1, 23):
            setattr(config, f"ENABLE_STRATEGY_{i}", False)
        setattr(config, f"ENABLE_STRATEGY_{args.strategy}", True)
        config.apply_strategy_defaults(f"Strategy_{args.strategy}")
        
    # Detect the active strategy
    active_strat = "None"
    for i in range(1, 23):
        if getattr(config, f"ENABLE_STRATEGY_{i}", False):
            active_strat = f"Strategy_{i}"
            break
            
    print(f"[CONFIG] Active Strategy: {active_strat}")
    print(f"[CONFIG] Leg Execution Mode: {config.LEG_MODE}\n")
    
    # 5. Execute backtests
    all_results = []
    
    for symbol in enabled_instruments:
        print(f"\n{'='*60}")
        print(f" [RUNNING] Backtesting {symbol} on {active_strat} ({config.LEG_MODE} legs)")
        print(f"{'='*60}")
        
        try:
            # Instantiate SimulationEngine for target instrument
            engine = SimulationEngine(config, instrument_name=symbol, offline_mode=args.offline, backtest_days=args.days)
            
            # Automatically loads/downloads the spot data
            engine.load_data()
            
            results = engine.run(write_to_csv=False)
            
            if not results.empty:
                total_trades = len(results)
                win_rate = (len(results[results['PnL'] > 0]) / total_trades) * 100
                gross_pnl = results['Gross_PnL'].sum()
                charges = results['Charges'].sum()
                net_pnl = results['PnL'].sum()
                
                gross_profit = results[results['PnL'] > 0]['PnL'].sum()
                gross_loss = abs(results[results['PnL'] < 0]['PnL'].sum())
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
                
                avg_pnl = net_pnl / total_trades
                max_win = results['PnL'].max()
                max_loss = results['PnL'].min()
                
                all_results.append({
                    "Instrument": symbol,
                    "Strategy": active_strat,
                    "Leg Mode": config.LEG_MODE,
                    "Trades": total_trades,
                    "Win Rate (%)": round(win_rate, 1),
                    "Profit Factor": round(profit_factor, 2),
                    "Gross PnL (Rs.)": round(gross_pnl, 2),
                    "Charges (Rs.)": round(charges, 2),
                    "Net PnL (Rs.)": round(net_pnl, 2),
                    "Avg PnL/Trade": round(avg_pnl, 2),
                    "Max Win": round(max_win, 2),
                    "Max Loss": round(max_loss, 2)
                })
                
                # Save detailed trades to instrument-specific file to prevent overwriting
                trades_file = os.path.join(BASE_DIR, f"backtest_results_{symbol.lower()}.csv")
                try:
                    results.to_csv(trades_file, index=False)
                except PermissionError:
                    temp_trades_file = os.path.join(BASE_DIR, f"backtest_results_{symbol.lower()}_temp.csv")
                    print(f"[WARNING] Permission denied to write to '{trades_file}'. Saving to '{temp_trades_file}' instead.")
                    results.to_csv(temp_trades_file, index=False)
                
                print(f"\n[SUCCESS] {symbol} backtest complete:")
                print(f"  -> Total Trades:          {total_trades}")
                print(f"  -> Win Rate:              {win_rate:.1f}%")
                print(f"  -> Net PnL:               Rs.{net_pnl:.2f}")
                print(f"  -> Detailed trades saved: backtest_results_{symbol.lower()}.csv")
                
                # Calculate max drawdown for logging
                arr_pnl = np.array(results['PnL'].tolist())
                cum_pnl = np.cumsum(arr_pnl)
                peaks_pnl = np.maximum.accumulate(cum_pnl)
                drawdowns_pnl = peaks_pnl - cum_pnl
                max_dd_pnl = np.max(drawdowns_pnl) if len(drawdowns_pnl) > 0 else 0.0
                
                test_res = {
                    "Total_Trades": total_trades,
                    "Win_Rate": round(win_rate, 1),
                    "Profit_Factor": round(profit_factor, 2) if profit_factor != np.inf else 999.0,
                    "Net_PnL": round(net_pnl, 2),
                    "Max_Drawdown": round(max_dd_pnl, 2)
                }
                
                active_params = {}
                # Extract relevant risk parameters from engine inst_config
                for pk in ['sl_mult_buy', 'tp_mult_buy', 'trailing_mult_buy', 'sl_mult_sell', 'tp_mult_sell', 'trailing_mult_sell', 'strike_offset_sell', 'strike_offset_buy']:
                    if pk in engine.inst_config:
                        active_params[pk] = engine.inst_config[pk]
                # Extract relevant indicators from strategy params
                if hasattr(engine.strategy, "params"):
                    for ik, iv in engine.strategy.params.items():
                        active_params[ik] = iv
                        
                log_experiment_to_tracker(
                    run_type="Backtest",
                    instrument=symbol,
                    strategy_name=active_strat,
                    leg_mode=config.LEG_MODE,
                    days=args.days,
                    train_res=None,
                    test_res=test_res,
                    best_params=active_params,
                    verdict="PROFITABLE" if net_pnl > 0 else "UNPROFITABLE"
                )
            else:
                print(f"[INFO] No signals or trades executed for {symbol}.")
                all_results.append({
                    "Instrument": symbol, "Strategy": active_strat, "Leg Mode": config.LEG_MODE,
                    "Trades": 0, "Win Rate (%)": 0.0, "Profit Factor": 0.0,
                    "Gross PnL (Rs.)": 0.0, "Charges (Rs.)": 0.0, "Net PnL (Rs.)": 0.0,
                    "Avg PnL/Trade": 0.0, "Max Win": 0.0, "Max Loss": 0.0
                })
        except Exception as e:
            print(f"[ERROR] Failed to backtest {symbol}: {e}")
            import traceback
            traceback.print_exc()
            
    # 6. Display Consolidated Results
    if all_results:
        df_summary = pd.DataFrame(all_results)
        df_summary = df_summary.sort_values(by="Net PnL (Rs.)", ascending=False)
        
        print("\n" + "="*115)
        print("                         CONSOLIDATED INSTRUMENT PERFORMANCE RANKINGS           ")
        print("="*115)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df_summary.to_string(index=False))
        print("="*115)
        
        # Save to CSV
        output_csv = os.path.join(BASE_DIR, "multi_instrument_results.csv")
        try:
            df_summary.to_csv(output_csv, index=False)
            print(f"[SUCCESS] Multi-instrument rankings saved to multi_instrument_results.csv\n")
        except PermissionError:
            temp_output_csv = os.path.join(BASE_DIR, "multi_instrument_results_temp.csv")
            print(f"[WARNING] Permission denied to write to '{output_csv}'. Saving to '{temp_output_csv}' instead.")
            df_summary.to_csv(temp_output_csv, index=False)

if __name__ == "__main__":
    main()
