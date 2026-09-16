"""
Strategy 20: John Ehlers Decycler Oscillator & SuperSmoother DSP Trend System
An institutional quantitative trading system powered by Digital Signal Processing (DSP):
1. High-Pass Filter extracts instantaneous zero-lag trend component (Ehlers Decycler).
2. Dual-pole SuperSmoother filter provides noise-free velocity and momentum structure.
3. Supertrend dynamic volatility channel & ADX expansion confirm institutional participation.
4. Anti-exhaustion stretch filter prevents chasing extended candles.
5. 1-minute breakout trigger confirms market entry with zero look-ahead bias.
"""

import os
import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
except ImportError:
    ta = None
from typing import Dict, Any
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy_20(BaseStrategy):
    """
    Strategy 20: John Ehlers Decycler Oscillator & SuperSmoother DSP Trend Strategy
    """
    name = "Strategy_20"

    def get_default_params(self) -> dict:
        return {
            "timeframe": "5min",
            "hp_period": 30,
            "ss_fast": 8,
            "ss_base": 18,
            "st_len": 10,
            "st_mul": 2.5,
            "max_stretch": 0.003,
            "leg_mode": "SELL",
            "points_sl_sell": 50.0,
            "points_target_sell": 90.0,
            "points_trail_sell": 0.0,
            "points_be_sell": 0.0,
            "carry_forward": True,
            "block_expiry_day_trades": 1,
            "entry_time": "09:30",
            "max_active": 1,
            "daily_limit": 1
        }

    def get_optimization_grid(self) -> dict:
        return {
            "timeframe": ["5min", "15min", "30min"],
            "hp_period": [20, 25, 30, 40],
            "ss_fast": [6, 8, 10],
            "ss_base": [14, 18, 22],
            "points_sl_sell": [45.0, 50.0, 64.0],
            "points_target_sell": [84.0, 90.0, 100.0]
        }

    @staticmethod
    def calc_ehlers_decycler(df_tf: pd.DataFrame, hp_period: int = 30) -> pd.Series:
        """
        Computes John Ehlers 2-Pole High-Pass filtered Zero-Lag Decycler.
        """
        close = df_tf['close'].values
        n = len(close)
        hp = np.zeros(n)
        rad = np.radians(0.707 * 360.0 / hp_period)
        cos_val = np.cos(rad)
        sin_val = np.sin(rad)
        alpha = (cos_val + sin_val - 1.0) / cos_val if cos_val != 0 else 0.1
        
        a_sq = (1.0 - alpha / 2.0) ** 2
        two_1_a = 2.0 * (1.0 - alpha)
        one_a_sq = (1.0 - alpha) ** 2
        
        for i in range(2, n):
            hp[i] = (a_sq * (close[i] - 2.0 * close[i-1] + close[i-2]) 
                     + two_1_a * hp[i-1] 
                     - one_a_sq * hp[i-2])
            
        decycler = close - hp
        return pd.Series(decycler, index=df_tf.index)

    @staticmethod
    def calc_super_smoother(series: pd.Series, period: int = 10) -> pd.Series:
        """
        Computes John Ehlers 2-Pole SuperSmoother Filter.
        """
        close = series.values
        n = len(close)
        filt = np.zeros(n)
        a1 = np.exp(-1.414 * np.pi / period)
        b1 = 2.0 * a1 * np.cos(np.radians(1.414 * 180.0 / period))
        c2 = b1
        c3 = -a1 * a1
        c1 = 1.0 - c2 - c3
        for i in range(2, n):
            filt[i] = c1 * (close[i] + close[i-1]) / 2.0 + c2 * filt[i-1] + c3 * filt[i-2]
        return pd.Series(filt, index=series.index)

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot

        df = df_spot.copy()
        
        # Ensure DateTime Index
        if not isinstance(df.index, pd.DatetimeIndex):
            t_col = 'timestamp' if 'timestamp' in df.columns else 'datetime'
            if t_col in df.columns:
                df[t_col] = pd.to_datetime(df[t_col])
                df = df.set_index(t_col)

        df['Signal'] = 0
        df['Signal_Source'] = "None"
        df['signal'] = 0
        df['option_action'] = "NONE"
        df['trend'] = 0
        df['Exit_Long_Strategy_20'] = False
        df['Exit_Short_Strategy_20'] = False

        # Configurable Parameters
        tf = str(self.params.get("timeframe", "5min"))
        hp_period = int(self.params.get("hp_period", 30))
        ss_fast_p = int(self.params.get("ss_fast", 8))
        ss_base_p = int(self.params.get("ss_base", 18))
        st_len = int(self.params.get("st_len", 10))
        st_mul = float(self.params.get("st_mul", 2.5))
        max_stretch = float(self.params.get("max_stretch", 0.003))
        leg_mode = str(self.params.get("leg_mode", "SELL")).upper()

        # 1. Resample spot to higher timeframe
        df_tf = df.resample(tf).agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna()

        if len(df_tf) < 50:
            return df

        # 2. Ehlers Decycler Macro Trend Component
        df_tf['Decycler_Line'] = self.calc_ehlers_decycler(df_tf, hp_period=hp_period)

        # 3. Ehlers 2-Pole SuperSmoother Dual Velocity
        df_tf['SS_Fast'] = self.calc_super_smoother(df_tf['close'], period=ss_fast_p)
        df_tf['SS_Base'] = self.calc_super_smoother(df_tf['close'], period=ss_base_p)
        df_tf['SS_Fast_Slope'] = df_tf['SS_Fast'].diff()
        df_tf['SS_Base_Slope'] = df_tf['SS_Base'].diff()

        # 4. Supertrend Dynamic Volatility Boundary
        if ta is not None:
            st_res = ta.supertrend(df_tf['high'], df_tf['low'], df_tf['close'], length=st_len, multiplier=st_mul)
            if st_res is not None:
                st_col = [c for c in st_res.columns if c.startswith('SUPERT_')][0]
                df_tf['ST_Line'] = st_res[st_col]
            else:
                df_tf['ST_Line'] = df_tf['Decycler_Line']
                
            adx_res = ta.adx(df_tf['high'], df_tf['low'], df_tf['close'], length=14)
            if adx_res is not None:
                df_tf['ADX_Slope'] = adx_res['ADX_14'].diff()
            else:
                df_tf['ADX_Slope'] = 0.1
        else:
            df_tf['ST_Line'] = df_tf['Decycler_Line']
            df_tf['ADX_Slope'] = 0.1

        # 5. Anti-Exhaustion Stretch Filter
        df_tf['Stretch'] = (df_tf['close'] - df_tf['SS_Fast']).abs() / df_tf['SS_Fast']

        # 6. Trend Confluence Logic
        df_tf['Long_Trend'] = (df_tf['close'] > df_tf['Decycler_Line']) & \
                              (df_tf['SS_Fast'] > df_tf['SS_Base']) & \
                              (df_tf['SS_Fast_Slope'] > 0) & (df_tf['SS_Base_Slope'] > 0) & \
                              (df_tf['low'] > df_tf['ST_Line']) & \
                              (df_tf['ADX_Slope'] > 0) & \
                              (df_tf['Stretch'] < max_stretch)

        df_tf['Short_Trend'] = (df_tf['close'] < df_tf['Decycler_Line']) & \
                               (df_tf['SS_Fast'] < df_tf['SS_Base']) & \
                               (df_tf['SS_Fast_Slope'] < 0) & (df_tf['SS_Base_Slope'] < 0) & \
                               (df_tf['high'] < df_tf['ST_Line']) & \
                               (df_tf['ADX_Slope'] > 0) & \
                               (df_tf['Stretch'] < max_stretch)

        df_tf['Sig_High'] = df_tf['high']
        df_tf['Sig_Low'] = df_tf['low']

        # 7. Shift completed bar by 1 to prevent lookahead bias
        cols_to_shift = ['Long_Trend', 'Short_Trend', 'Sig_High', 'Sig_Low', 'Decycler_Line']
        df_tf[cols_to_shift] = df_tf[cols_to_shift].shift(1)

        # Drop overlapping columns
        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns])

        # Join to 1-minute execution dataframe
        df = df.join(df_tf[cols_to_shift], how='left')
        df['Long_Trend'] = df['Long_Trend'].ffill().fillna(False).astype(bool)
        df['Short_Trend'] = df['Short_Trend'].ffill().fillna(False).astype(bool)
        df['Sig_High'] = df['Sig_High'].ffill()
        df['Sig_Low'] = df['Sig_Low'].ffill()
        df['Decycler_Line'] = df['Decycler_Line'].ffill()

        # 8. 1-minute Breakout Triggers
        buy_cond = (df['Long_Trend'] == True) & (df['close'] > df['Sig_High'])
        sell_cond = (df['Short_Trend'] == True) & (df['close'] < df['Sig_Low'])

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[buy_cond, 'signal'] = 1
        df.loc[buy_cond, 'Signal_Source'] = "Strategy 20 (Ehlers DSP Decycler Bullish Breakout)"
        df.loc[buy_cond, 'option_action'] = "SELL_PE" if leg_mode == "SELL" else "BUY_CE"

        df.loc[sell_cond, 'Signal'] = -1
        df.loc[sell_cond, 'signal'] = -1
        df.loc[sell_cond, 'Signal_Source'] = "Strategy 20 (Ehlers DSP Decycler Bearish Breakout)"
        df.loc[sell_cond, 'option_action'] = "SELL_CE" if leg_mode == "SELL" else "BUY_PE"

        df['trend'] = np.where(df['Long_Trend'], 1, np.where(df['Short_Trend'], -1, 0))
        return df

    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.generate_signals(df)

def get_strategy_instance(params: Dict[str, Any] = None):
    return Strategy_20(params)
