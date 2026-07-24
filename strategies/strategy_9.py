import pandas as pd
import numpy as np
import pandas_ta as ta

from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy9(BaseStrategy):
    name = "Strategy_9"

    def get_default_params(self) -> dict:
        return {
            # Parameters extracted via 5-year Decision Tree Reverse Engineering
            "S9_EMA_LENGTH": 50,
            "S9_BODY_MIN_BUY": 0.0578,      # Minimum body size percent of close for long entry
            "S9_EMA_DIFF_MAX_BUY": -0.3088, # Maximum percentage close-to-EMA50 difference for long entry
            "S9_BODY_MIN_SELL": 0.0430,     # Minimum body size percent of close for short entry
            "S9_EMA_DIFF_MAX_SELL": -0.1578, # Maximum percentage close-to-EMA50 difference for short entry
            "ATR_PERIOD": 14,
        }

    def get_optimization_grid(self) -> dict:
        return {
            "S9_BODY_MIN_BUY": [0.04, 0.058, 0.08],
            "S9_EMA_DIFF_MAX_BUY": [-0.2, -0.31, -0.4],
            "S9_BODY_MIN_SELL": [0.03, 0.043, 0.06],
            "S9_EMA_DIFF_MAX_SELL": [-0.1, -0.16, -0.25],
            "ATR_PERIOD": [14]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot

        df = df_spot.copy()
        
        # Guard clause for data length
        ema_len = int(self.params["S9_EMA_LENGTH"])
        if len(df) < ema_len:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            df['ATR'] = np.nan
            return df

        # Calculate resampled 5-min ATR (matching Strategy 3) to support ATR exit modes
        df_5min = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        atr_period = int(self.params.get("ATR_PERIOD", 14))
        if len(df_5min) >= atr_period:
            df_5min['ATR'] = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=atr_period)
            df_5min['ATR'] = df_5min['ATR'].shift(1)
            
            if 'ATR' in df.columns:
                df = df.drop(columns=['ATR'])
            df = df.join(df_5min[['ATR']], how='left')
            df['ATR'] = df['ATR'].ffill().bfill().fillna(0.0)
        else:
            df['ATR'] = 0.0

        # Calculate EMA
        ema_val = ta.ema(df['close'], length=ema_len)
        
        # Compute relative values
        body_size_pct = (df['close'] - df['open']).abs() / df['close'] * 100
        ema_diff_pct = (df['close'] - ema_val) / df['close'] * 100
        
        # Conditions based on extracted tree paths
        # BUY: Bullish candle, body size > min, price significantly below EMA
        buy_cond = (
            (df['close'] > df['open']) & 
            (body_size_pct > self.params["S9_BODY_MIN_BUY"]) & 
            (ema_diff_pct <= self.params["S9_EMA_DIFF_MAX_BUY"])
        )
        
        # SELL: Bearish candle, body size > min, price significantly below EMA (momentum continuation)
        sell_cond = (
            (df['close'] < df['open']) & 
            (body_size_pct > self.params["S9_BODY_MIN_SELL"]) & 
            (ema_diff_pct <= self.params["S9_EMA_DIFF_MAX_SELL"])
        )
        
        # Vectorized signal assignment
        df['Signal'] = 0
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        
        df['Signal_Source'] = np.where(df['Signal'] != 0, "Strategy 9", "None")
        
        return df
