import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

def calculate_smma(series: pd.Series, length: int) -> pd.Series:
    """
    Calculates Smoothed Moving Average (SMMA / Wilder's Smoothing).
    SMMA is equivalent to EMA with alpha = 1 / length (Wilder's EWM).
    """
    if len(series) < length:
        return pd.Series(index=series.index, dtype=float)
    return series.ewm(alpha=1.0 / length, adjust=False).mean()

@register_strategy
class Strategy16(BaseStrategy):
    """
    Strategy 16: 18 SMMA Breakout Strategy with Exact Crossover Phase Engine
    
    Timeframe: Configurable (1min, 5min, 15min, or 1D)
    Indicator: 18-period Smoothed Moving Average (18 SMMA)
    
    Rules:
    1. Crossover Phase: A new crossover phase begins when price crosses 18 SMMA.
    2. Setup: 2 consecutive candles completely above 18 SMMA (Low > 18 SMMA) in the active phase.
    3. Trigger: Breakout target level = High of the 2nd setup candle.
    4. Single Entry per Crossover Phase: Emits EXACTLY ONE entry signal per crossover phase when price breaks out.
    5. Exit: Exits when price closes back below 18 SMMA (Exit_Long = True).
    """
    name = "Strategy_16"

    def get_default_params(self) -> dict:
        return {
            "TIMEFRAME": "1min",
            "SMA_PERIOD": 18,
            "MA_TYPE": "SMMA",
            "PRICE_SOURCE": "close",
            "STRICT_LOW_FILTER": True,
            "CONSECUTIVE_CLOSES": 2,
            "SWING_LOW_LOOKBACK": 5,
            "ATR_PERIOD": 14
        }

    def get_optimization_grid(self) -> dict:
        return {
            "TIMEFRAME": ["1min", "5min", "15min", "1D"],
            "SMA_PERIOD": [14, 18, 20, 21],
            "MA_TYPE": ["SMMA", "SMA"],
            "PRICE_SOURCE": ["close", "OHLC4"],
            "STRICT_LOW_FILTER": [True, False],
            "CONSECUTIVE_CLOSES": [2, 3]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # Calculate 14-period ATR for intraday risk scaling
        if 'ATR' not in df.columns:
            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=self.params.get("ATR_PERIOD", 14))
            df['ATR'] = df['ATR'].ffill().bfill()

        tf_param = str(self.params.get("TIMEFRAME", "1min")).lower()
        sma_period = self.params.get("SMA_PERIOD", 18)
        swing_lookback = self.params.get("SWING_LOW_LOOKBACK", 5)
        strict_low = self.params.get("STRICT_LOW_FILTER", True)
        ma_type = str(self.params.get("MA_TYPE", "SMMA")).upper()
        price_src = str(self.params.get("PRICE_SOURCE", "close")).upper()

        # Resample to target timeframe
        if tf_param in ["1min", "1m"]:
            df_tf = df.copy()
        elif tf_param in ["5min", "5m"]:
            df_tf = df.resample('5min').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna()
        elif tf_param in ["15min", "15m"]:
            df_tf = df.resample('15min').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna()
        else:
            df_tf = df.resample('1D').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna()
        
        if len(df_tf) < sma_period + 5:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            df['Exit_Long'] = False
            df['Exit_Short'] = False
            return df

        # Calculate Price Source (OHLC4 vs Close)
        if price_src == "OHLC4":
            df_tf['price_src'] = (df_tf['open'] + df_tf['high'] + df_tf['low'] + df_tf['close']) / 4.0
        else:
            df_tf['price_src'] = df_tf['close']

        # 1. Primary 18 SMMA (or SMA) Indicator
        if ma_type == "SMMA":
            df_tf['MA_18'] = calculate_smma(df_tf['price_src'], length=sma_period)
        else:
            df_tf['MA_18'] = ta.sma(df_tf['price_src'], length=sma_period)
        
        # 2. Setup Qualification & Crossover Event
        if strict_low:
            df_tf['Above_MA'] = df_tf['low'] > df_tf['MA_18']
            df_tf['Below_MA'] = df_tf['high'] < df_tf['MA_18']
        else:
            df_tf['Above_MA'] = df_tf['close'] > df_tf['MA_18']
            df_tf['Below_MA'] = df_tf['close'] < df_tf['MA_18']
        
        df_tf['Consecutive_Above'] = df_tf['Above_MA'].rolling(2).sum() == 2
        df_tf['Consecutive_Below'] = df_tf['Below_MA'].rolling(2).sum() == 2
        
        # Prior candle (2 candles ago) was BELOW SMMA (Matching Strategy 10 cross logic)
        df_tf['Prev_Was_Below'] = df_tf['close'].shift(2) <= df_tf['MA_18'].shift(2)
        df_tf['Prev_Was_Above'] = df_tf['close'].shift(2) >= df_tf['MA_18'].shift(2)
        
        # Crossover Event
        cross_buy = df_tf['Prev_Was_Below'] & df_tf['Consecutive_Above']
        cross_sell = df_tf['Prev_Was_Above'] & df_tf['Consecutive_Below']
        
        # Active Crossover Phase Grouping (resets when price crosses back across 18 SMMA)
        df_tf['Long_Phase_ID'] = (~df_tf['Above_MA']).astype(int).cumsum()
        df_tf['Short_Phase_ID'] = (~df_tf['Below_MA']).astype(int).cumsum()
        
        # Lock Trigger High/Low on the setup candle and ffill within the active crossover phase
        df_tf['Raw_Sig_High'] = np.where(cross_buy, df_tf['high'], np.nan)
        df_tf['Sig_High'] = df_tf.groupby('Long_Phase_ID')['Raw_Sig_High'].ffill()
        
        df_tf['Raw_Sig_Low'] = np.where(cross_sell, df_tf['low'], np.nan)
        df_tf['Sig_Low'] = df_tf.groupby('Short_Phase_ID')['Raw_Sig_Low'].ffill()
        
        # Active setup flags: Remains active while price stays in the crossover phase
        df_tf['S16_Long_Trend'] = df_tf['Above_MA'] & df_tf['Sig_High'].notna()
        df_tf['S16_Short_Trend'] = df_tf['Below_MA'] & df_tf['Sig_Low'].notna()
        
        # Swing Low / High
        df_tf['Swing_Low'] = df_tf['low'].rolling(swing_lookback).min()
        df_tf['Swing_High'] = df_tf['high'].rolling(swing_lookback).max()
        
        # Dynamic Exits: Price drops below 18 SMMA (Exit_Long) or rises above 18 SMMA (Exit_Short)
        df_tf['Exit_Long'] = df_tf['close'] < df_tf['MA_18']
        df_tf['Exit_Short'] = df_tf['close'] > df_tf['MA_18']

        # 3. Shift indicators by 1 bar to avoid lookahead bias (matching Strategy 10/3/12)
        cols_to_shift = ['MA_18', 'S16_Long_Trend', 'S16_Short_Trend', 'Sig_High', 'Sig_Low', 'Swing_Low', 'Swing_High']
        
        if tf_param in ["1min", "1m"]:
            df[cols_to_shift] = df_tf[cols_to_shift].shift(1)
            df['Exit_Long'] = df_tf['Exit_Long']
            df['Exit_Short'] = df_tf['Exit_Short']
        else:
            df_tf[cols_to_shift] = df_tf[cols_to_shift].shift(1)
            df = df.drop(columns=[c for c in cols_to_shift if c in df.columns], errors='ignore')
            df = df.join(df_tf[cols_to_shift + ['Exit_Long', 'Exit_Short']], how='left')
            df[cols_to_shift] = df[cols_to_shift].ffill()
            df['Exit_Long'] = df['Exit_Long'].fillna(False).astype(bool)
            df['Exit_Short'] = df['Exit_Short'].fillna(False).astype(bool)

        # Cast booleans
        df['S16_Long_Trend'] = df['S16_Long_Trend'].fillna(False).astype(bool)
        df['S16_Short_Trend'] = df['S16_Short_Trend'].fillna(False).astype(bool)
        
        # 4. Generate Breakout Signals (Single Entry per crossover window, matching Strategy 10)
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        
        s16_buy_raw = (df['S16_Long_Trend'] == True) & (df['close'] > df['Sig_High'])
        s16_sell_raw = (df['S16_Short_Trend'] == True) & (df['close'] < df['Sig_Low'])
        
        s16_buy = s16_buy_raw & (~s16_buy_raw.shift(1).fillna(False))
        s16_sell = s16_sell_raw & (~s16_sell_raw.shift(1).fillna(False))
        
        df.loc[s16_buy, 'Signal'] = 1
        df.loc[s16_buy, 'Signal_Source'] = f"18_{ma_type}_{tf_param.upper()}_BUY"
        
        df.loc[s16_sell, 'Signal'] = -1
        df.loc[s16_sell, 'Signal_Source'] = f"18_{ma_type}_{tf_param.upper()}_SELL"
                
        return df
