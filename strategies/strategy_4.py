import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy4(BaseStrategy):
    name = "Strategy_4"

    def get_default_params(self) -> dict:
        return {
            "S4_WMA_87": 87,
            "S4_WMA_200": 200,
            "ATR_PERIOD": 14,
        }

    def get_optimization_grid(self) -> dict:
        return {
            "S4_WMA_87": [80, 87, 95],
            "S4_WMA_200": [180, 200, 220],
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        if len(df) < 250:
            df['ATR'] = np.nan
            df['S4_Long_Trend'] = False
            df['S4_Short_Trend'] = False
            df['S4_Sig_High'] = np.nan
            df['S4_Sig_Low'] = np.nan
            df['Exit_Long'] = False
            df['Exit_Short'] = False
            df['Signal'] = 0
            df['Strat1_Signal'] = 0
            df['Strat2_Signal'] = 0
            df['TM_Signal'] = 0
            df['S4_Signal'] = 0
            df['Signal_Source'] = "None"
            return df
        
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=self.params["ATR_PERIOD"])
        
        # Calculate WMA 87, WMA 200, and VWAP
        df['S4_WMA87'] = ta.wma(df['close'], length=self.params["S4_WMA_87"])
        df['S4_WMA200'] = ta.wma(df['close'], length=self.params["S4_WMA_200"])
        df['S4_VWAP'] = ta.vwap(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'])
        
        # Calculate rises and falls
        df['S4_WMA200_Rising'] = df['S4_WMA200'].diff() > 0
        df['S4_VWAP_Rising'] = df['S4_VWAP'].diff() > 0
        df['S4_WMA200_Falling'] = df['S4_WMA200'].diff() < 0
        df['S4_VWAP_Falling'] = df['S4_VWAP'].diff() < 0
        
        # Check previous state (shift by 1)
        wma200_was_falling = df['S4_WMA200_Falling'].shift(1)
        vwap_was_falling = df['S4_VWAP_Falling'].shift(1)
        wma200_was_rising = df['S4_WMA200_Rising'].shift(1)
        vwap_was_rising = df['S4_VWAP_Rising'].shift(1)
        
        # Reversal Conditions
        wma_long_reversal = wma200_was_falling & df['S4_WMA200_Rising']
        vwap_long_reversal = vwap_was_falling & df['S4_VWAP_Rising']
        
        wma_short_reversal = wma200_was_rising & df['S4_WMA200_Falling']
        vwap_short_reversal = vwap_was_rising & df['S4_VWAP_Falling']
        
        # Trend Definition
        df['S4_Long_Trend'] = (df['S4_WMA87'] > df['S4_WMA200']) & \
                               (wma_long_reversal & vwap_long_reversal)
                               
        df['S4_Short_Trend'] = (df['S4_WMA87'] < df['S4_WMA200']) & \
                                (wma_short_reversal & vwap_short_reversal)

        # Reference Levels
        df['S4_Sig_High'] = df['high']
        df['S4_Sig_Low'] = df['low']
        
        # Prevent lookahead bias by shifting trend signals by 1 bar
        df['Prev_High'] = df['high'].shift(1)
        df['Prev_Low'] = df['low'].shift(1)
        df['Prev_Long_Trend'] = df['S4_Long_Trend'].shift(1)
        df['Prev_Short_Trend'] = df['S4_Short_Trend'].shift(1)
        
        # Dynamic exits removed: set to False
        df['Exit_Long'] = False
        df['Exit_Short'] = False

        # Initialize signal columns
        df['Signal'] = 0
        df['Strat1_Signal'] = 0
        df['Strat2_Signal'] = 0
        df['TM_Signal'] = 0
        df['S4_Signal'] = 0
        df['Signal_Source'] = "None"
        
        # Breakout Entries (Current close breaks previous candle's High/Low during the active trend)
        s4_buy = (df['Prev_Long_Trend'] == True) & (df['close'] > df['Prev_High'])
        s4_sell = (df['Prev_Short_Trend'] == True) & (df['close'] < df['Prev_Low'])
        
        df.loc[s4_buy, 'Signal'] = 1
        df.loc[s4_buy, 'S4_Signal'] = 1
        df.loc[s4_buy, 'Signal_Source'] = "Strategy 4 (WMA)"
        
        df.loc[s4_sell, 'Signal'] = -1
        df.loc[s4_sell, 'S4_Signal'] = -1
        df.loc[s4_sell, 'Signal_Source'] = "Strategy 4 (WMA)"
        
        # Clean up temporary columns
        df.drop(columns=['Prev_High', 'Prev_Low', 'Prev_Long_Trend', 'Prev_Short_Trend'], inplace=True, errors='ignore')
        
        return df
