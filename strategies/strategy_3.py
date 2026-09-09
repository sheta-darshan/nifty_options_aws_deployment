import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy3(BaseStrategy):
    name = "Strategy_3"

    def get_default_params(self) -> dict:
        return {
            "TM_EMA_LONG": 30,
            "TM_EMA_SHORT": 8,
            "TM_EMA_BASE": 18,
            "TM_ST_LEN": 10,
            "TM_ST_MUL": 2.5,
            "TM_ADX_LEN": 14,
            "TM_ADX_MIN": 12,
            "TM_MAX_STRETCH": 0.003,
            "ATR_PERIOD": 14,
            "START_TIME": "09:25",
            "END_TIME": "14:45",
            "NO_TRADE_START": "13:00",
            "NO_TRADE_END": "13:50"
        }
    def get_optimization_grid(self) -> dict:
        return {
            # 1. Sweep these to find the best Trend Structure:
            "TM_EMA_LONG": [30],
            "TM_EMA_SHORT": [8],
            "TM_EMA_BASE": [18],

            # 2. Hold these constant at their default values (only 1 item in list):
            "TM_ST_LEN": [10],
            "TM_ST_MUL": [2.5],
            "TM_ADX_MIN": [12],
            "TM_MAX_STRETCH": [0.003],
            "ATR_PERIOD": [14],
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
            df['TM_Long_Trend'] = False
            df['TM_Short_Trend'] = False
            df['TM_Sig_High'] = np.nan
            df['TM_Sig_Low'] = np.nan
            df['TM_ADX'] = np.nan
            df['Signal'] = 0
            df['Strat1_Signal'] = 0
            df['Strat2_Signal'] = 0
            df['TM_Signal'] = 0
            df['S4_Signal'] = 0
            df['Signal_Source'] = "None"
            return df
        df_5min['ATR'] = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=self.params.get("ATR_PERIOD", 14))
        
        # 3. Strategy 3 EMAs and Supertrend
        df_5min['TM_EMA_LONG'] = ta.ema(df_5min['close'], length=self.params.get("TM_EMA_LONG", 30))
        df_5min['TM_EMA_SHORT'] = ta.ema(df_5min['close'], length=self.params.get("TM_EMA_SHORT", 8))
        df_5min['TM_EMA_BASE'] = ta.ema(df_5min['close'], length=self.params.get("TM_EMA_BASE", 18))
        
        df_5min['TM_EMA_SHORT_Slope'] = df_5min['TM_EMA_SHORT'].diff()
        df_5min['TM_EMA_BASE_Slope'] = df_5min['TM_EMA_BASE'].diff()
        
        adx_len = self.params.get("TM_ADX_LEN", 14)
        adx_min = self.params.get("TM_ADX_MIN", 12)
        adx_tm = ta.adx(df_5min['high'], df_5min['low'], df_5min['close'], length=adx_len)
        if adx_tm is not None:
            df_5min['TM_ADX'] = adx_tm[f'ADX_{adx_len}']
            df_5min['TM_ADX_Slope'] = df_5min['TM_ADX'].diff()
        else:
            df_5min['TM_ADX'] = np.nan
            df_5min['TM_ADX_Slope'] = np.nan
            
        st_tm = ta.supertrend(df_5min['high'], df_5min['low'], df_5min['close'], 
                              length=self.params.get("TM_ST_LEN", 10), multiplier=self.params.get("TM_ST_MUL", 2.5))
        if st_tm is not None:
            line_col_tm = [c for c in st_tm.columns if c.startswith('SUPERT_')][0]
            df_5min['TM_ST_Line'] = st_tm[line_col_tm]
        else:
            df_5min['TM_ST_Line'] = np.nan

        # Distance Filter (Stretch)
        df_5min['TM_Stretch'] = (df_5min['close'] - df_5min['TM_EMA_SHORT']).abs() / df_5min['TM_EMA_SHORT']

        # Determine maximum stretch
        max_stretch = self.params.get("TM_MAX_STRETCH", 0.003)
        if (self.params.get("type") == "OPTION" or self.params.get("instrument_type") == "OPTION") and max_stretch == 0.003:
            max_stretch = 0.05

        # Trend Selection with rising ADX and minimum ADX strength
        df_5min['TM_Long_Trend'] = (df_5min['close'] > df_5min['TM_EMA_LONG']) & \
                                   (df_5min['TM_EMA_SHORT'] > df_5min['TM_EMA_BASE']) & \
                                   (df_5min['TM_EMA_SHORT_Slope'] > 0) & (df_5min['TM_EMA_BASE_Slope'] > 0) & \
                                   (df_5min['low'] > df_5min['TM_ST_Line']) & \
                                   (df_5min['TM_ADX_Slope'] > 0) & \
                                   (df_5min['TM_ADX'] >= adx_min) & \
                                   (df_5min['TM_Stretch'] < max_stretch)
                                   
        df_5min['TM_Short_Trend'] = (df_5min['close'] < df_5min['TM_EMA_LONG']) & \
                                    (df_5min['TM_EMA_SHORT'] < df_5min['TM_EMA_BASE']) & \
                                    (df_5min['TM_EMA_SHORT_Slope'] < 0) & (df_5min['TM_EMA_BASE_Slope'] < 0) & \
                                    (df_5min['high'] < df_5min['TM_ST_Line']) & \
                                    (df_5min['TM_ADX_Slope'] > 0) & \
                                    (df_5min['TM_ADX'] >= adx_min) & \
                                    (df_5min['TM_Stretch'] < max_stretch)

        # Reference levels
        df_5min['TM_Sig_High'] = df_5min['high']
        df_5min['TM_Sig_Low'] = df_5min['low']
        
        # 4. Shift 5-min indicators to prevent lookahead
        cols_to_shift = ['ATR', 'TM_Long_Trend', 'TM_Short_Trend', 'TM_Sig_High', 'TM_Sig_Low', 'TM_ADX']
        df_5min[cols_to_shift] = df_5min[cols_to_shift].shift(1)
        
        # Drop overlapping columns from df to prevent ValueError
        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns])
        
        # Join to 1-min
        df = df.join(df_5min[cols_to_shift], how='left')
        
        # Forward fill continuous state variables
        state_cols = ['TM_Long_Trend', 'TM_Short_Trend', 'TM_Sig_High', 'TM_Sig_Low', 'ATR', 'TM_ADX']
        df[state_cols] = df[state_cols].ffill()
        
        # Cast booleans
        df['TM_Long_Trend'] = df['TM_Long_Trend'].fillna(False).astype(bool)
        df['TM_Short_Trend'] = df['TM_Short_Trend'].fillna(False).astype(bool)

        # 5. Time Filter & Midday European open chop exclusion
        start_time_str = self.params.get("START_TIME", "09:25")
        end_time_str = self.params.get("END_TIME", "14:45")
        time_mask = (df.index.time >= pd.to_datetime(start_time_str).time()) & \
                    (df.index.time <= pd.to_datetime(end_time_str).time())

        no_trade_start = self.params.get("NO_TRADE_START", "13:00")
        no_trade_end = self.params.get("NO_TRADE_END", "13:50")
        if no_trade_start and no_trade_end:
            midday_chop_mask = (df.index.time >= pd.to_datetime(no_trade_start).time()) & \
                               (df.index.time <= pd.to_datetime(no_trade_end).time())
            time_mask = time_mask & (~midday_chop_mask)
        
        # Signals (1m Breakout)
        df['Signal'] = 0
        df['Strat1_Signal'] = 0
        df['Strat2_Signal'] = 0
        df['TM_Signal'] = 0
        df['S4_Signal'] = 0
        tm_buy = (df['TM_Long_Trend'] == True) & (df['close'] > df['TM_Sig_High']) & time_mask
        tm_sell = (df['TM_Short_Trend'] == True) & (df['close'] < df['TM_Sig_Low']) & time_mask
        df.loc[tm_buy, 'Signal'] = 1
        df.loc[tm_sell, 'Signal'] = -1
        df.loc[tm_buy, 'TM_Signal'] = 1
        df.loc[tm_sell, 'TM_Signal'] = -1
        
        df['Signal_Source'] = "None"
        df.loc[(df['TM_Signal'] != 0), 'Signal_Source'] = "Strategy 3 (TM)"
        return df
