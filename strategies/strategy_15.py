import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy15(BaseStrategy):
    name = "Strategy_15"

    def get_default_params(self) -> dict:
        return {
            "ENTRY_TIME": "09:19:00",
            "ATR_PERIOD": 14
        }

    def get_optimization_grid(self) -> dict:
        return {
            "ENTRY_TIME": ["09:17:00", "09:18:00", "09:19:00", "09:20:00"],
            "ATR_PERIOD": [14]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # Calculate ATR on the 1-minute close (required by execution engines)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=self.params["ATR_PERIOD"])
        
        # Forward fill or backfill NaN ATR values to avoid computation errors
        df['ATR'] = df['ATR'].ffill().bfill()
        
        # Initialize default signal columns
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        
        # Generate the entry signal at the exact target index time
        target_time = pd.Timestamp(self.params["ENTRY_TIME"]).time()
        is_entry = (df.index.time == target_time)
        
        df.loc[is_entry, 'Signal'] = 1
        df.loc[is_entry, 'Signal_Source'] = "920_Straddle"
        
        return df
