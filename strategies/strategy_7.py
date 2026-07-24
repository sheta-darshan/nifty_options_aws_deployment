import pandas as pd
import numpy as np
import pandas_ta as ta

from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy7(BaseStrategy):
    name = "Strategy_7"

    def get_default_params(self) -> dict:
        return {
            # Derivative Oscillator params
            "DO_RSI_LENGTH": 21,
            "DO_SMA_LENGTH": 50,
            "DO_EMA1_LENGTH": 50,
            "DO_EMA2_LENGTH": 21,
            # Breakout params
            "BREAKOUT_WAIT_MINUTES": 3,
            # ATR params
            "ATR_PERIOD": 14,
        }

    def get_optimization_grid(self) -> dict:
        return {
            "DO_RSI_LENGTH": [14,21],
            "DO_SMA_LENGTH": [9,11],
            "DO_EMA1_LENGTH": [5,7],
            "DO_EMA2_LENGTH": [3,5],
            "BREAKOUT_WAIT_MINUTES": [1,2]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot

        df = df_spot.copy()

        # Insufficient data check
        if len(df) < 200:
            cols = ['S7_DO', 'S7_Sig_High', 'S7_Sig_Low', 'ATR']
            for col in cols:
                df[col] = np.nan
            df['Signal'] = 0
            df['S7_Signal'] = 0
            df['S7_Direction'] = 0
            df['Signal_Source'] = "None"
            return df

        # Calculate 5-minute resampled ATR (like Strategy 3)
        df_5min = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        if len(df_5min) >= 50:
            df_5min['ATR'] = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=self.params["ATR_PERIOD"])
            df_5min['ATR'] = df_5min['ATR'].shift(1)
            # Drop column from df if it already exists to prevent duplication error
            df = df.drop(columns=['ATR'], errors='ignore')
            df = df.join(df_5min[['ATR']], how='left')
            df['ATR'] = df['ATR'].ffill()
        else:
            df['ATR'] = np.nan

        # Calculate Derivative Oscillator directly on the 1-minute timeframe
        rsi_do = ta.rsi(df['close'], length=self.params["DO_RSI_LENGTH"])
        ema1 = ta.ema(rsi_do, length=self.params["DO_EMA1_LENGTH"])
        s1 = ta.ema(ema1, length=self.params["DO_EMA2_LENGTH"])
        sma_s1 = ta.sma(s1, length=self.params["DO_SMA_LENGTH"])
        
        DO = s1 - sma_s1
        df['S7_DO'] = DO

        # Crossover triggers on the 1-minute timeframe
        do_prev = DO.shift(1)
        do_cross_up = (DO > 0) & (do_prev <= 0)
        do_cross_down = (DO < 0) & (do_prev >= 0)

        # Store Signal high and low levels (on the 1-minute trigger candle itself)
        df['S7_Sig_High'] = np.where(do_cross_up, df['high'], np.nan)
        df['S7_Sig_Low'] = np.where(do_cross_down, df['low'], np.nan)

        df['S7_Direction'] = np.nan
        df.loc[do_cross_up, 'S7_Direction'] = 1
        df.loc[do_cross_down, 'S7_Direction'] = -1

        # Run 1-minute breakout loop (close confirmation of breakout)
        closes = df['close'].values
        raw_dir = df['S7_Direction'].values
        raw_sig_high = df['S7_Sig_High'].values
        raw_sig_low = df['S7_Sig_Low'].values
        n = len(df)
        max_wait = self.params.get("BREAKOUT_WAIT_MINUTES", 5)

        signal = np.zeros(n, dtype=int)
        sig_high = np.full(n, np.nan)
        sig_low = np.full(n, np.nan)
        direction = np.zeros(n, dtype=int)

        curr_dir = 0
        curr_high = np.nan
        curr_low = np.nan
        bars_elapsed = 0

        for i in range(n):
            # 1. Check for breakout entry if there is an active signal candle setup
            if curr_dir == 1:
                if closes[i] > curr_high:
                    signal[i] = 1
                    curr_dir = 0
                    curr_high = np.nan
                    curr_low = np.nan
                else:
                    bars_elapsed += 1
                    if bars_elapsed >= max_wait:
                        curr_dir = 0
                        curr_high = np.nan
                        curr_low = np.nan
            elif curr_dir == -1:
                if closes[i] < curr_low:
                    signal[i] = -1
                    curr_dir = 0
                    curr_high = np.nan
                    curr_low = np.nan
                else:
                    bars_elapsed += 1
                    if bars_elapsed >= max_wait:
                        curr_dir = 0
                        curr_high = np.nan
                        curr_low = np.nan

            # 2. Check if there is a new crossover trigger candle *at the current bar*
            if not np.isnan(raw_dir[i]):
                curr_dir = int(raw_dir[i])
                curr_high = raw_sig_high[i]
                curr_low = raw_sig_low[i]
                bars_elapsed = 0

            direction[i] = curr_dir
            sig_high[i] = curr_high
            sig_low[i] = curr_low

        df['Signal'] = signal
        df['S7_Signal'] = signal
        df['S7_Direction'] = direction
        df['S7_Sig_High'] = sig_high
        df['S7_Sig_Low'] = sig_low
        df['Signal_Source'] = np.where(signal != 0, "Strategy 7", "None")

        return df