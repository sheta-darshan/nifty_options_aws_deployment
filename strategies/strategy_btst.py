import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class StrategyBTST(BaseStrategy):
    name = "Strategy_BTST"

    def get_default_params(self) -> dict:
        return {
            "rsi_period": 14,
            "rsi_long_min": 50,
            "rsi_long_max": 75,
            "rsi_short_min": 25,
            "rsi_short_max": 45,
            "gatekeeper_time_filter_minutes": 20
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # 1. Resample to 5-min candles
        df_5m = df.resample('5Min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if len(df_5m) < 10:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df
            
        # 2. Daily timeframe levels (PDH, PDL)
        # Resample to Daily to get CPR and Previous Day High/Low
        df_daily = df.resample('1D').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        
        if len(df_daily) < 2:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df
            
        df_daily['pdh'] = df_daily['high'].shift(1)
        df_daily['pdl'] = df_daily['low'].shift(1)
        
        # CPR
        P = (df_daily['high'] + df_daily['low'] + df_daily['close']) / 3
        BC = (df_daily['high'] + df_daily['low']) / 2
        TC = (P - BC) + P
        df_daily['cpr_tc'] = TC.shift(1)
        df_daily['cpr_bc'] = BC.shift(1)
        
        # Map daily levels back to the 5-minute rows
        df_daily['date'] = df_daily.index.date
        df_5m['date'] = df_5m.index.date
        
        df_daily_lookup = df_daily[['pdh', 'pdl', 'cpr_tc', 'cpr_bc', 'date']].set_index('date')
        df_5m = df_5m.join(df_daily_lookup, on='date')
        
        # 3. RSI Calculation on 5-minute candles
        df_5m['rsi'] = ta.rsi(df_5m['close'], length=self.params["rsi_period"])
        
        # 4. Initialize Signal columns
        df_5m['Signal'] = 0
        df_5m['Signal_Source'] = "None"
        
        # Drop rows missing indicators
        df_5m.dropna(subset=['pdh', 'pdl', 'rsi'], inplace=True)
        
        # Filter for the 2:55 PM candle (represented by index time 14:50:00 in 5-minute charts)
        is_255 = (df_5m.index.time == pd.Timestamp("14:50:00").time())
        
        # Long condition
        long_cond = is_255 & \
                    (df_5m['close'] > df_5m['pdh']) & \
                    (df_5m['rsi'] >= self.params["rsi_long_min"]) & \
                    (df_5m['rsi'] <= self.params["rsi_long_max"])
                    
        # Short condition
        short_cond = is_255 & \
                     (df_5m['close'] < df_5m['pdl']) & \
                     (df_5m['rsi'] >= self.params["rsi_short_min"]) & \
                     (df_5m['rsi'] <= self.params["rsi_short_max"])
                     
        df_5m.loc[long_cond, 'Signal'] = 1
        df_5m.loc[long_cond, 'Signal_Source'] = "BTST CE"
        
        df_5m.loc[short_cond, 'Signal'] = -1
        df_5m.loc[short_cond, 'Signal_Source'] = "BTST PE"
        
        # 5. Map 5-min signals back to the last 1-minute candle of each 5-minute bar
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        
        sig_indices = df_5m[df_5m['Signal'] != 0].index
        for idx in sig_indices:
            start_range = idx
            end_range = idx + pd.Timedelta(minutes=4)
            sub_df = df.loc[start_range:end_range]
            if not sub_df.empty:
                target_idx = sub_df.index[-1]
                df.loc[target_idx, 'Signal'] = df_5m.loc[idx, 'Signal']
                df.loc[target_idx, 'Signal_Source'] = df_5m.loc[idx, 'Signal_Source']
                
        return df
