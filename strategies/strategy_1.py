import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy
from .utils import fast_supertrend_dir

@register_strategy
class Strategy1(BaseStrategy):
    name = "Strategy_1"

    def get_default_params(self) -> dict:
        return {
            "STOCH_LEN": 14,
            "RSI_OVERSOLD": 30,
            "RSI_OVERBOUGHT": 70,
            "SUPERTREND_LEN": 12,
            "SUPERTREND_MUL": 3,
            "ADX_THRESHOLD": 18,
            "EMA_FILTER_LEN": 21,
            "ATR_PERIOD": 14,
        }

    def get_optimization_grid(self) -> dict:
        return {
            "SUPERTREND_LEN": [10, 12, 14],
            "SUPERTREND_MUL": [2.5, 3.0, 3.5],
            "ADX_THRESHOLD": [15, 18, 20],
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # 1. Resample to 5-min
        df_5min = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if len(df_5min) < 50:
            df['ATR'] = np.nan
            df['S1_Buy'] = False
            df['S1_Sell'] = False
            df['Signal'] = 0
            df['Strat1_Signal'] = 0
            df['Signal_Source'] = "None"
            return df
            
        # 2. Indicators
        rsi = ta.rsi(df_5min['close'], length=self.params["STOCH_LEN"])
        if rsi is not None:
            min_rsi = rsi.rolling(self.params["STOCH_LEN"]).min()
            max_rsi = rsi.rolling(self.params["STOCH_LEN"]).max()
            diff = max_rsi - min_rsi
            diff = diff.replace(0, np.nan)
            raw_k = ((rsi - min_rsi) / diff) * 100
            df_5min['Stoch_K'] = raw_k.rolling(3).mean()
            df_5min['Stoch_D'] = df_5min['Stoch_K'].rolling(3).mean()
        else:
            df_5min['Stoch_K'] = 0
            df_5min['Stoch_D'] = 0
            
        bullish_cross = (df_5min['Stoch_K'] > df_5min['Stoch_D']) & (df_5min['Stoch_K'].shift(1) <= df_5min['Stoch_D'].shift(1))
        bearish_cross = (df_5min['Stoch_K'] < df_5min['Stoch_D']) & (df_5min['Stoch_K'].shift(1) >= df_5min['Stoch_D'].shift(1))
        
        df_5min['ATR'] = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=self.params["ATR_PERIOD"])
        
        adx = ta.adx(df_5min['high'], df_5min['low'], df_5min['close'], length=14)
        if adx is not None and not adx.empty:
            df_5min['ADX'] = adx['ADX_14']
        else:
            df_5min['ADX'] = 0
            
        df_5min['EMA21'] = ta.ema(df_5min['close'], length=self.params["EMA_FILTER_LEN"])
        df_5min['ST_Dir'] = fast_supertrend_dir(df_5min['high'], df_5min['low'], df_5min['close'], 
                                               self.params["SUPERTREND_LEN"], self.params["SUPERTREND_MUL"])
        
        df_5min['S1_Buy'] = (df_5min['ST_Dir'] == 1) & (df_5min['ADX'] > self.params["ADX_THRESHOLD"]) & \
                            (df_5min['close'] > df_5min['EMA21']) & (df_5min['Stoch_K'] < self.params["RSI_OVERSOLD"]) & bullish_cross
        df_5min['S1_Sell'] = (df_5min['ST_Dir'] == -1) & (df_5min['ADX'] > self.params["ADX_THRESHOLD"]) & \
                             (df_5min['close'] < df_5min['EMA21']) & (df_5min['Stoch_K'] > self.params["RSI_OVERBOUGHT"]) & bearish_cross
                             
        # 3. Shift 5m indicators to prevent lookahead
        cols_to_shift = ['ATR', 'S1_Buy', 'S1_Sell']
        df_5min[cols_to_shift] = df_5min[cols_to_shift].shift(1)
        
        # Drop overlapping columns from df to prevent ValueError
        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns])
        
        # Join to 1m
        df = df.join(df_5min[cols_to_shift], how='left')
        df['ATR'] = df['ATR'].ffill()
        df['S1_Buy'] = df['S1_Buy'].fillna(False).astype(bool)
        df['S1_Sell'] = df['S1_Sell'].fillna(False).astype(bool)
        
        df['Signal'] = 0
        df['Strat1_Signal'] = 0
        df['Strat2_Signal'] = 0
        df['TM_Signal'] = 0
        df['S4_Signal'] = 0
        df.loc[df['S1_Buy'], 'Signal'] = 1
        df.loc[df['S1_Sell'], 'Signal'] = -1
        df.loc[df['S1_Buy'], 'Strat1_Signal'] = 1
        df.loc[df['S1_Sell'], 'Strat1_Signal'] = -1
        
        df['Signal_Source'] = "None"
        df.loc[(df['Strat1_Signal'] != 0), 'Signal_Source'] = "Strategy 1 (Trend)"
        
        return df
