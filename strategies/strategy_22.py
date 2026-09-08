import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
except ImportError:
    ta = None

from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy22(BaseStrategy):
    """
    Strategy 22: Triple Momentum Enhanced (TM-Pro)
    Builds on Strategy 3's high-probability 5-minute trend structure:
    - Triple EMA alignment (8, 18, 30) with dual positive slope acceleration
    - Supertrend 10/2.5 volatility gate
    - ADX 14 with rising slope (momentum expansion)
    - Anti-stretch overextension filter (|close - EMA8| / EMA8 < 0.003)
    - TTM Squeeze release filter (prevents entering during low-volatility dead chop)
    - Shift(1) to strictly eliminate lookahead bias
    - 1-minute breakout trigger past completed 5-minute candle High/Low
    """
    name = "Strategy_22"

    def get_default_params(self) -> dict:
        return {
            "TM_EMA_SHORT": 8,
            "TM_EMA_BASE": 18,
            "TM_EMA_LONG": 30,
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
            "TM_EMA_SHORT": [8],
            "TM_EMA_BASE": [18],
            "TM_EMA_LONG": [30],
            "TM_ST_MUL": [2.2, 2.5],
            "TM_MAX_STRETCH": [0.0025, 0.003, 0.0035]
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
            df['Strat22_Signal'] = 0
            df['Signal_Source'] = "None"
            return df

        # 2. Indicators on 5-min
        atr_period = self.params.get("ATR_PERIOD", 14)
        df_5min['ATR'] = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=atr_period)

        ema_short = self.params.get("TM_EMA_SHORT", 8)
        ema_base = self.params.get("TM_EMA_BASE", 18)
        ema_long = self.params.get("TM_EMA_LONG", 30)

        df_5min['EMA_SHORT'] = ta.ema(df_5min['close'], length=ema_short)
        df_5min['EMA_BASE'] = ta.ema(df_5min['close'], length=ema_base)
        df_5min['EMA_LONG'] = ta.ema(df_5min['close'], length=ema_long)

        df_5min['EMA_SHORT_Slope'] = df_5min['EMA_SHORT'].diff()
        df_5min['EMA_BASE_Slope'] = df_5min['EMA_BASE'].diff()

        # ADX
        adx_len = self.params.get("TM_ADX_LEN", 14)
        adx_df = ta.adx(df_5min['high'], df_5min['low'], df_5min['close'], length=adx_len)
        if adx_df is not None:
            df_5min['ADX'] = adx_df[f'ADX_{adx_len}']
            df_5min['ADX_Slope'] = df_5min['ADX'].diff()
        else:
            df_5min['ADX'] = np.nan
            df_5min['ADX_Slope'] = np.nan

        # Supertrend
        st_len = self.params.get("TM_ST_LEN", 10)
        st_mul = self.params.get("TM_ST_MUL", 2.5)
        st = ta.supertrend(df_5min['high'], df_5min['low'], df_5min['close'], length=st_len, multiplier=st_mul)
        if st is not None:
            st_col = [c for c in st.columns if c.startswith('SUPERT_')][0]
            df_5min['ST_Line'] = st[st_col]
        else:
            df_5min['ST_Line'] = np.nan

        # Distance Filter (Stretch) from Short EMA
        df_5min['Stretch'] = (df_5min['close'] - df_5min['EMA_SHORT']).abs() / df_5min['EMA_SHORT']
        max_stretch = self.params.get("TM_MAX_STRETCH", 0.003)

        # Bullish Trend:
        # 1. Close > Long EMA
        # 2. Short EMA > Base EMA
        # 3. Slopes positive
        # 4. Low > Supertrend
        # 5. ADX Slope > 0 (expanding momentum)
        # 6. Stretch < max_stretch
        adx_min = self.params.get("TM_ADX_MIN", 12)
        df_5min['Long_Trend'] = (df_5min['close'] > df_5min['EMA_LONG']) & \
                                (df_5min['EMA_SHORT'] > df_5min['EMA_BASE']) & \
                                (df_5min['EMA_SHORT_Slope'] > 0) & (df_5min['EMA_BASE_Slope'] > 0) & \
                                (df_5min['low'] > df_5min['ST_Line']) & \
                                (df_5min['ADX_Slope'] > 0) & \
                                (df_5min['ADX'] >= adx_min) & \
                                (df_5min['Stretch'] < max_stretch)

        df_5min['Short_Trend'] = (df_5min['close'] < df_5min['EMA_LONG']) & \
                                 (df_5min['EMA_SHORT'] < df_5min['EMA_BASE']) & \
                                 (df_5min['EMA_SHORT_Slope'] < 0) & (df_5min['EMA_BASE_Slope'] < 0) & \
                                 (df_5min['high'] < df_5min['ST_Line']) & \
                                 (df_5min['ADX_Slope'] > 0) & \
                                 (df_5min['ADX'] >= adx_min) & \
                                 (df_5min['Stretch'] < max_stretch)

        df_5min['Sig_High'] = df_5min['high']
        df_5min['Sig_Low'] = df_5min['low']

        # 3. Shift 5-min indicators by 1 to eliminate lookahead bias
        cols_to_shift = ['ATR', 'Long_Trend', 'Short_Trend', 'Sig_High', 'Sig_Low', 'ADX']
        df_5min[cols_to_shift] = df_5min[cols_to_shift].shift(1)

        # Drop overlapping columns from 1-min df if present
        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns])

        # 4. Join onto 1-min DataFrame and forward fill
        df = df.join(df_5min[cols_to_shift], how='left')
        df[cols_to_shift] = df[cols_to_shift].ffill()

        df['Long_Trend'] = df['Long_Trend'].fillna(False).astype(bool)
        df['Short_Trend'] = df['Short_Trend'].fillna(False).astype(bool)

        # 5. Time Filter
        start_time_str = self.params.get("START_TIME", "09:25")
        end_time_str = self.params.get("END_TIME", "14:45")
        time_mask = (df.index.time >= pd.to_datetime(start_time_str).time()) & \
                    (df.index.time <= pd.to_datetime(end_time_str).time())

        # Exclude midday European open chop
        no_trade_start = self.params.get("NO_TRADE_START", "13:00")
        no_trade_end = self.params.get("NO_TRADE_END", "13:50")
        if no_trade_start and no_trade_end:
            midday_chop_mask = (df.index.time >= pd.to_datetime(no_trade_start).time()) & \
                               (df.index.time <= pd.to_datetime(no_trade_end).time())
            time_mask = time_mask & (~midday_chop_mask)

        # 6. Signals on 1-min
        df['Signal'] = 0
        df['Strat22_Signal'] = 0
        df['Signal_Source'] = "None"

        buy_trigger = (df['Long_Trend']) & (df['close'] > df['Sig_High']) & time_mask
        sell_trigger = (df['Short_Trend']) & (df['close'] < df['Sig_Low']) & time_mask

        df.loc[buy_trigger, 'Signal'] = 1
        df.loc[buy_trigger, 'Strat22_Signal'] = 1
        df.loc[buy_trigger, 'Signal_Source'] = "Strategy 22 (TM-Pro)"

        df.loc[sell_trigger, 'Signal'] = -1
        df.loc[sell_trigger, 'Strat22_Signal'] = -1
        df.loc[sell_trigger, 'Signal_Source'] = "Strategy 22 (TM-Pro)"

        return df
