import os
import sys
import time
import argparse
import pandas as pd
from datetime import datetime, date, timedelta

# Add workspace directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import SimulationEngine
from strategies import BacktestConfig

def prefetch_data(instrument_name="NIFTY", strike_offsets=[-2, -1, 0, 1, 2], expiry_indices=[0, 1], limit_days=None, config=None):
    if config is None:
        config = BacktestConfig()
    
    print(f"[INFO] Initializing SimulationEngine for {instrument_name} to generate signals...")
    engine = SimulationEngine(config, instrument_name=instrument_name, offline_mode=False)
    
    execution_mode = engine.inst_config.get('execution_mode', 'OPTION')
    if execution_mode == 'STOCK':
        print(f"[INFO] {instrument_name} is configured with execution_mode = STOCK. Skipping options prefetch.")
        return
        
    engine.load_data()
    
    df_spot = engine.df_spot
    if df_spot is None or df_spot.empty:
        print("[ERROR] Spot data is empty or could not be loaded.")
        return
        
    df_signals = df_spot[df_spot['Signal'] != 0]
    
    # Exclude weekends and NSE holidays from pre-fetch signals
    from backtest_engine import NSE_HOLIDAYS
    df_signals = df_signals[df_signals.index.dayofweek < 5]
    df_signals = df_signals[~df_signals.index.strftime('%Y-%m-%d').isin(NSE_HOLIDAYS)]
    
    if df_signals.empty:
        print("[WARNING] No entry signals were generated on the Spot dataset for trading days.")
        return
        
    print(f"[INFO] Found {len(df_signals)} signal timestamps across {df_spot.index.normalize().nunique()} days.")
    
    # Get all signal timestamps
    signal_timestamps = sorted(list(df_signals.index))
    
    if limit_days is not None:
        # Limit to the most recent N days with signals
        unique_dates = sorted(list(set(ts.date() for ts in signal_timestamps)))
        target_dates = set(unique_dates[-limit_days:])
        signal_timestamps = [ts for ts in signal_timestamps if ts.date() in target_dates]
        print(f"[INFO] Limiting pre-fetch to the most recent {limit_days} signal days ({len(signal_timestamps)} signals).")

    strike_step = engine.inst_config.get('strike_step', 100)
    
    requested = set()
    total_downloads = 0
    skipped_cache = 0
    
    print(f"[INFO] Starting targeted pre-fetch for {instrument_name} options...")
    print(f"Offsets to fetch: {strike_offsets}")
    print(f"Expiries to fetch: {expiry_indices}")
    print("=" * 60)
    
    for i, ts in enumerate(signal_timestamps):
        trade_date = ts.date()
        date_str = trade_date.strftime("%Y-%m-%d")
        
        # Get spot price at the signal minute
        spot_price = df_spot.loc[ts, 'close']
        if isinstance(spot_price, pd.Series):
            spot_price = spot_price.iloc[0]
            
        atm_strike = int(round(spot_price / strike_step) * strike_step)
        
        print(f"\n[{i+1}/{len(signal_timestamps)}] Signal at {ts} | Spot: {spot_price:.2f} | ATM: {atm_strike}")
        
        for offset in strike_offsets:
            strike = atm_strike + (offset * strike_step)
            for exp_idx in expiry_indices:
                for opt_type in ["CE", "PE"]:
                    contract_key = (trade_date, strike, opt_type, exp_idx)
                    if contract_key in requested:
                        continue
                    requested.add(contract_key)
                    
                    # Update engine inst_config expiry_index dynamically so the fetch knows which weekly contract to download
                    engine.inst_config["expiry_index"] = exp_idx
                    
                    # Check cache status first
                    prefix = instrument_name.lower()
                    expiry_str = engine._get_actual_expiry_date(trade_date, exp_idx)
                    cache_filename = f"{prefix}_{strike}_{opt_type}_exp{exp_idx}_expiry{expiry_str}_{date_str}.csv"
                    cache_path = os.path.join(engine.cache_dir, cache_filename)
                    
                    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100:
                        skipped_cache += 1
                        continue
                        
                    # Cache Miss -> Download it
                    print(f"  -> Fetching {strike} {opt_type} (Expiry index: {exp_idx}) for {date_str}...")
                    
                    try:
                        # Fetch the candles using the existing stitching/Dhan API logic
                        df_opt = engine._get_option_candles(strike, opt_type, trade_date, relative_strike=f"ATM{offset:+d}" if offset != 0 else "ATM")
                        if not df_opt.empty:
                            total_downloads += 1
                        else:
                            print(f"  [WARNING] Empty option candles returned for {strike} {opt_type} on {date_str}")
                    except Exception as e:
                        print(f"  [ERROR] Failed to fetch {strike} {opt_type} on {date_str}: {e}")
                        
                    # Sleep briefly to protect rate limits
                    time.sleep(0.5)
                    
    print("\n" + "=" * 60)
    print("   PRE-FETCH SUMMARY")
    print("=" * 60)
    print(f"Total Unique Contracts Checked:  {len(requested)}")
    print(f"Skipped (Already Cached):       {skipped_cache}")
    print(f"Newly Downloaded:               {total_downloads}")
    print("=" * 60)
    print("[SUCCESS] Targeted pre-fetching complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Targeted Option Pre-Fetcher for Backtesting")
    parser.add_argument("--instrument", type=str, default="NIFTY", help="Instrument to pre-fetch (e.g. NIFTY, BANKNIFTY)")
    parser.add_argument("--offsets", type=str, default="-2,-1,0,1,2", help="Comma-separated strike offsets from ATM (default: -2,-1,0,1,2)")
    parser.add_argument("--expiries", type=str, default="0,1", help="Comma-separated expiry indices (default: 0,1)")
    parser.add_argument("--strategy", "-s", type=int, choices=list(range(1, 24)), help="Strategy index to run (1-23). If omitted, uses active strategy from config/env")
    parser.add_argument("--limit-days", type=int, default=None, help="Limit to most recent N days with signals (for testing)")
    
    args = parser.parse_args()
    
    try:
        strike_offsets = [int(o) for o in args.offsets.split(",")]
        expiry_indices = [int(e) for e in args.expiries.split(",")]
    except ValueError:
        print("[ERROR] Invalid offsets or expiries argument format.")
        sys.exit(1)
        
    config = BacktestConfig()
    if args.strategy:
        for i in range(1, 24):
            setattr(config, f"ENABLE_STRATEGY_{i}", (i == args.strategy))
        config.apply_strategy_defaults(f"Strategy_{args.strategy}")
        
    prefetch_data(
        instrument_name=args.instrument.upper(),
        strike_offsets=strike_offsets,
        expiry_indices=expiry_indices,
        limit_days=args.limit_days,
        config=config
    )
