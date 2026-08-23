import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy
from .utils import fast_supertrend_dir

@register_strategy
class Strategy5(BaseStrategy):
    name = "Strategy_5"

    def get_default_params(self) -> dict:
        return {
            "STOCH_LEN": 14,
            "S2_RSI_OVERSOLD": 25,
            "S2_RSI_OVERBOUGHT": 75,
            "S2_ST15_LEN": 10,
            "S2_ST15_MUL": 3.0,
            "S2_ST5_MUL": 4.0,
            "ATR_PERIOD": 14,
            "EMA_FAST": 10,
            "EMA_SLOW": 20,
            "VOL_SMA": 20
        }

    def get_optimization_grid(self) -> dict:
        return {
            "S2_ST15_MUL": [2.5, 3.0, 3.5],
            "S2_ST5_MUL": [3.5, 4.0, 4.5],
            "S2_RSI_OVERSOLD": [20, 25, 30],
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
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df
            
        # 2. Add Gabani Value Area & Volume Filters
        df_5min['EMA_10'] = ta.ema(df_5min['close'], length=self.params["EMA_FAST"])
        df_5min['EMA_20'] = ta.ema(df_5min['close'], length=self.params["EMA_SLOW"])
        df_5min['VOL_SMA'] = ta.sma(df_5min['volume'], length=self.params["VOL_SMA"])
        
        # Gabani Check 1: Volume Contraction (Current vol is less than average)
        df_5min['Dry_Volume'] = df_5min['volume'] < df_5min['VOL_SMA']
        
        # Gabani Check 2: Price Tightening (Inside Bar formation)
        df_5min['Inside_Bar'] = (df_5min['high'] <= df_5min['high'].shift(1)) & (df_5min['low'] >= df_5min['low'].shift(1))
        
        # Gabani Check 3: Orderly Landing (Price is near the 20 EMA, not crashing through it)
        df_5min['Near_EMA'] = (df_5min['low'] <= df_5min['EMA_10'] * 1.002) & (df_5min['close'] >= df_5min['EMA_20'] * 0.998)

        # 3. Existing 5-min Stochastic Logic
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
        
        # 4. 15-min Trend Filter (Supertrend)
        df_15min = df_5min.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
        df_15min['ST15_Dir'] = fast_supertrend_dir(df_15min['high'], df_15min['low'], df_15min['close'], self.params["S2_ST15_LEN"], self.params["S2_ST15_MUL"])
        
        df_5min = df_5min.join(df_15min[['ST15_Dir']].shift(1), how='left')
        df_5min['ST15_Dir'] = df_5min['ST15_Dir'].ffill()
        
        df_5min['ST5_S2_Dir'] = fast_supertrend_dir(df_5min['high'], df_5min['low'], df_5min['close'], self.params["S2_ST15_LEN"], self.params["S2_ST5_MUL"])
        
        # 5. Combined Setup Condition
        df_5min['Buy_Setup'] = (df_5min['ST15_Dir'] == 1) & (df_5min['ST5_S2_Dir'] == 1) & \
                               (df_5min['Stoch_K'] < self.params["S2_RSI_OVERSOLD"]) & bullish_cross & \
                               df_5min['Dry_Volume'] & df_5min['Near_EMA'] & df_5min['Inside_Bar']
                               
        df_5min['Sell_Setup'] = (df_5min['ST15_Dir'] == -1) & (df_5min['ST5_S2_Dir'] == -1) & \
                                (df_5min['Stoch_K'] > self.params["S2_RSI_OVERBOUGHT"]) & bearish_cross & \
                                df_5min['Dry_Volume'] & df_5min['Near_EMA'] & df_5min['Inside_Bar']

        # Store the high/low of the setup bar to act as our breakout trigger
        df_5min['Setup_High'] = np.where(df_5min['Buy_Setup'], df_5min['high'], np.nan)
        df_5min['Setup_Low'] = np.where(df_5min['Sell_Setup'], df_5min['low'], np.nan)
        df_5min[['Setup_High', 'Setup_Low']] = df_5min[['Setup_High', 'Setup_Low']].ffill()
        
        # Trigger entry ONLY when the next candle breaks the Setup High/Low
        df_5min['S2_Buy'] = df_5min['Buy_Setup'].shift(1).fillna(False) & (df_5min['close'] > df_5min['Setup_High'])
        df_5min['S2_Sell'] = df_5min['Sell_Setup'].shift(1).fillna(False) & (df_5min['close'] < df_5min['Setup_Low'])

        # 6. Shift 5-min indicators to prevent lookahead and join to 1-min
        cols_to_shift = ['ATR', 'S2_Buy', 'S2_Sell']
        df_5min[cols_to_shift] = df_5min[cols_to_shift].shift(1)
        
        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns])
        df = df.join(df_5min[cols_to_shift], how='left')
        
        df['ATR'] = df['ATR'].ffill()
        df['S2_Buy'] = df['S2_Buy'].fillna(False).astype(bool)
        df['S2_Sell'] = df['S2_Sell'].fillna(False).astype(bool)
        
        df['Signal'] = 0
        df.loc[df['S2_Buy'], 'Signal'] = 1
        df.loc[df['S2_Sell'], 'Signal'] = -1
        
        df['Signal_Source'] = "None"
        df.loc[(df['Signal'] != 0), 'Signal_Source'] = "Strategy_5"
        
        return df
