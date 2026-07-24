import pandas as pd
import os
import logging
import pandas_ta as ta
from backtest_multi_strategy import process_market_data, BacktestConfig

def debug_instrument(name):
    conf = BacktestConfig()
    inst = conf.INSTRUMENTS.get(name)
    if not inst:
        print(f"Instrument {name} not found in config.")
        return

    cache_dir = os.path.join(conf.BASE_DIR, "data", "backtest_cache")
    security_id = inst['security_id']
    exch_seg = 'NSE_EQ' if inst.get('type') == 'STOCK' else 'IDX_I'
    file = os.path.join(cache_dir, f"{security_id}_{exch_seg}.csv")
    
    if not os.path.exists(file):
        print(f"Cache file not found for {name}: {file}")
        return

    print(f"\n--- Debugging {name} (ID: {security_id}) ---")
    df = pd.read_csv(file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp').sort_index()
    if df.index.tz is None: df.index = df.index.tz_localize(conf.TIMEZONE)
    else: df.index = df.index.tz_convert(conf.TIMEZONE)
    
    print(f"Total 1m candles: {len(df)}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    
    logger = logging.getLogger("debug")
    df_processed = process_market_data(df, conf, logger)
    
    if df_processed.empty:
        print("Processed dataframe is EMPTY. Check resampling logic or minimum length requirement (50 rows).")
        return

    print(f"Processed 5m/1m rows: {len(df_processed)}")
    
    print(f"Processed columns: {df_processed.columns.tolist()}")
    
    # Check Indicators (Use available columns)
    check_cols = [c for c in ['TM_WMA87', 'TM_WMA21', 'TM_SMA21', 'TM_ST_Line', 'TM_ADX', 'ATR'] if c in df_processed.columns]
    if check_cols:
        null_counts = df_processed[check_cols].isnull().sum()
        print("\nIndicator Null Counts:")
        print(null_counts)
    else:
        # Check if they are prefixed with TM_
        check_cols = [c for c in ['TM_WMA87', 'TM_WMA21', 'TM_SMA21', 'TM_ST_Line', 'TM_ADX', 'ATR'] if f"TM_{c}" in df_processed.columns]
        # ... just print them all
        print("\nSearching for indicators...")
    
    # Check Signals
    sig_cols = ['TM_Long_Trend', 'TM_Short_Trend', 'TM_Signal', 'S1_Buy', 'S1_Sell', 'S2_Buy', 'S2_Sell']
    print("\nSignal Counts:")
    signals = {}
    for col in sig_cols:
        if col in df_processed.columns:
            val = df_processed[col].sum() if df_processed[col].dtype != 'object' else 0
            signals[col] = val
            print(f"  {col}: {val}")
        else:
            signals[col] = 0
            print(f"  {col}: NOT FOUND")

    if signals['TM_Long_Trend'] > 0 and signals['TM_Signal'] == 0:
        print("\nDEBUG: TM_Long_Trend exists but TM_Signal did not trigger.")
        print("Checking price vs TM_Sig_High condition...")
        mask = df_processed['TM_Long_Trend']
        sample = df_processed[mask][['close', 'TM_Sig_High']].tail(5)
        print(sample)

if __name__ == "__main__":
    debug_instrument("POWERINDIA")
    debug_instrument("ANGELONE")
