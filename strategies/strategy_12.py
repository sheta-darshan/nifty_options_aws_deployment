import pandas as pd
import numpy as np
import pandas_ta as ta
import datetime
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy12(BaseStrategy):
    name = "Strategy_12"

    def get_default_params(self) -> dict:
        return {
            "rsi_period": 56,
            "rsi_overbought": 60.0,
            "rsi_oversold": 40.0,
            "rsi_mid": 50.0
        }

    def get_optimization_grid(self) -> dict:
        return {
            "rsi_period": [56, 70, 84, 98, 112],
            "rsi_overbought": [65.0],
            "rsi_oversold": [35.0],
            "rsi_mid": [50.0]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # Ingest parameters
        rsi_len = int(self.params.get("rsi_period", 100))
        rsi_ob = float(self.params.get("rsi_overbought", 60.0))
        rsi_os = float(self.params.get("rsi_oversold", 40.0))
        rsi_mid_val = float(self.params.get("rsi_mid", 50.0))
        
        # Ensure volume exists (fallback if missing)
        if 'volume' not in df.columns:
            df['volume'] = 1.0
            
        # Initialize default output columns
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        df['Exit_Long'] = False
        df['Exit_Short'] = False
        
        if len(df) < rsi_len + 2:
            return df
            
        # Calculate VWAP (Typical price hlc3 based cumulative)
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3.0
        df['pv'] = df['typical_price'] * df['volume']
        
        df['cum_pv'] = df.groupby(df.index.date)['pv'].cumsum()
        df['cum_vol'] = df.groupby(df.index.date)['volume'].cumsum()
        df['cum_vol'] = df['cum_vol'].replace(0, 1.0) # avoid division by zero
        df['VWAP'] = df['cum_pv'] / df['cum_vol']
        
        # Calculate RSI (100) on 1-Minute close
        df['RSI'] = ta.rsi(df['close'], length=rsi_len)
        
        # Intraday State Machine for Overbought/Oversold crossings
        current_date = None
        overbought = False
        oversold = False
        
        closes = df['close'].values
        opens = df['open'].values
        vwaps = df['VWAP'].values
        rsis = df['RSI'].values
        timestamps = df.index
        signals = np.zeros(len(df))
        
        for i in range(len(df)):
            date = timestamps[i].date()
            # Reset daily flags on new trading day
            if date != current_date:
                current_date = date
                overbought = False
                oversold = False
                
            rsi_val = rsis[i]
            close_val = closes[i]
            open_val = opens[i]
            vwap_val = vwaps[i]
            
            if pd.isna(rsi_val) or pd.isna(vwap_val):
                continue
                
            # Update state machine flags based on RSI levels
            if rsi_val > rsi_ob:
                overbought = True
                oversold = False
            elif rsi_val < rsi_os:
                oversold = True
                overbought = False
                
            # Check PE Entry: RSI was overbought (>60) and now closes below 50, with a red candle closing below VWAP
            if overbought and rsi_val < rsi_mid_val:
                if close_val < open_val and close_val < vwap_val:
                    signals[i] = -1
                    overbought = False # Reset state after trigger
                    
            # Check CE Entry: RSI was oversold (<40) and now closes above 50, with a green candle closing above VWAP
            elif oversold and rsi_val > rsi_mid_val:
                if close_val > open_val and close_val > vwap_val:
                    signals[i] = 1
                    oversold = False # Reset state after trigger
                    
        df['Signal'] = signals
        df.loc[df['Signal'] == 1, 'Signal_Source'] = "RSI_VWAP_CE"
        df.loc[df['Signal'] == -1, 'Signal_Source'] = "RSI_VWAP_PE"
        
        return df
