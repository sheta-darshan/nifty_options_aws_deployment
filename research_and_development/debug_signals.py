import pandas as pd
import os
import logging
from backtest_multi_strategy import process_market_data, BacktestConfig

if __name__ == "__main__":
    conf = BacktestConfig()
    cache_dir = os.path.join(conf.BASE_DIR, "data", "backtest_cache")
    file = os.path.join(cache_dir, "18457_NSE_EQ.csv")
    
    if os.path.exists(file):
        df = pd.read_csv(file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Localize if needed
        if df.index.tz is None:
            df.index = df.index.tz_localize(conf.TIMEZONE)
        else:
            df.index = df.index.tz_convert(conf.TIMEZONE)
            
        logger = logging.getLogger("debug")
        df_processed = process_market_data(df, conf, logger)
        
        print("Summary of Signals for POWERINDIA:")
        print(f"Total Rows: {len(df_processed)}")
        print(f"TM Buy Signals: {df_processed['TM_Signal'].gt(0).sum()}")
        print(f"TM Sell Signals: {df_processed['TM_Signal'].lt(0).sum()}")
        print(f"S1 Buy Signals: {df_processed['S1_Buy'].sum()}")
        print(f"S2 Buy Signals: {df_processed['S2_Buy'].sum()}")
        
        # Check a few rows in April
        april_data = df_processed[df_processed.index >= "2026-04-01"]
        print("\nFirst 10 rows of April with Indicators:")
        print(df_processed[['close', 'TM_WMA_Long', 'TM_WMA_Short', 'TM_SMA', 'TM_Signal']].tail(10))
    else:
        print(f"Cache file not found: {file}")
