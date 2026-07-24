import pandas as pd
import numpy as np
import pandas_ta as ta
import datetime
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy13(BaseStrategy):
    name = "Strategy_13"

    def get_default_params(self) -> dict:
        return {
            "supertrend_period": 10,
            "supertrend_mult": 3.0,
            "ema_period": 50,
            "adx_period": 14,
            "adx_threshold": 20.0,
            "max_trades_per_day": 1,
            "cooldown_minutes": 45
        }

    def get_optimization_grid(self) -> dict:
        return {
            "supertrend_period": [10],
            "supertrend_mult": [2.0, 2.5, 3.0, 3.5],
            "ema_period": [30, 50, 80, 100],
            "adx_period": [14],
            "adx_threshold": [20.0, 22.0, 24.0, 26.0]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # Ingest parameters
        st_len = int(self.params.get("supertrend_period", 10))
        st_mult = float(self.params.get("supertrend_mult", 3.0))
        ema_len = int(self.params.get("ema_period", 50))
        adx_len = int(self.params.get("adx_period", 14))
        adx_thresh = float(self.params.get("adx_threshold", 20.0))
        cooldown_mins = int(self.params.get("cooldown_minutes", 45))
        
        # Resample to 5-minute
        df_5m = df.resample('5Min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if len(df_5m) < max(st_len, ema_len, adx_len) + 10:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df
            
        # Calculate Indicators
        # 1. EMA
        df_5m['EMA'] = ta.ema(df_5m['close'], length=ema_len)
        
        # 2. ADX
        adx_df = ta.adx(df_5m['high'], df_5m['low'], df_5m['close'], length=adx_len)
        df_5m['ADX'] = adx_df[f'ADX_{adx_len}'] if adx_df is not None else 20.0
        
        # 3. Supertrend
        st_df = ta.supertrend(df_5m['high'], df_5m['low'], df_5m['close'], length=st_len, multiplier=st_mult)
        df_5m['ST_dir'] = st_df[f'SUPERTd_{st_len}_{st_mult}'] if st_df is not None else 0
        
        # Shifted columns for crossover checks
        df_5m['ST_dir_prev'] = df_5m['ST_dir'].shift(1)
        df_5m['close_prev'] = df_5m['close'].shift(1)
        df_5m['EMA_prev'] = df_5m['EMA'].shift(1)
        
        df_5m['Signal'] = 0
        df_5m['Signal_Source'] = "None"
        
        # Entry logic loop (Limit signals using a cooldown to prevent cluster entry, let engine handle daily limits)
        last_signal_time = None
        
        for idx, row in df_5m.iterrows():
            if last_signal_time is not None:
                cooldown_elapsed = (idx - last_signal_time).total_seconds() / 60.0
                if cooldown_elapsed < cooldown_mins:
                    continue
                    
            st_dir = row['ST_dir']
            close_val = row['close']
            ema_val = row['EMA']
            adx_val = row['ADX']
            
            st_dir_prev = row['ST_dir_prev']
            close_prev = row['close_prev']
            ema_prev = row['EMA_prev']
            
            if pd.isna(st_dir) or pd.isna(ema_val) or pd.isna(adx_val) or pd.isna(st_dir_prev) or pd.isna(ema_prev):
                continue
                
            # CE Entry Crossover checks
            st_ce_cross = (st_dir == 1 and st_dir_prev != 1)
            ema_ce_cross = (close_val > ema_val and close_prev <= ema_prev)
            
            # PE Entry Crossover checks
            st_pe_cross = (st_dir == -1 and st_dir_prev != -1)
            ema_pe_cross = (close_val < ema_val and close_prev >= ema_prev)
            
            # CE Entry: Supertrend bullish (1), Close above EMA, and ADX shows momentum (> threshold)
            if st_dir == 1 and close_val > ema_val and adx_val >= adx_thresh and (st_ce_cross or ema_ce_cross):
                df_5m.at[idx, 'Signal'] = 1
                df_5m.at[idx, 'Signal_Source'] = "ST_EMA_CE"
                last_signal_time = idx
            # PE Entry: Supertrend bearish (-1), Close below EMA, and ADX shows momentum (> threshold)
            elif st_dir == -1 and close_val < ema_val and adx_val >= adx_thresh and (st_pe_cross or ema_pe_cross):
                df_5m.at[idx, 'Signal'] = -1
                df_5m.at[idx, 'Signal_Source'] = "ST_EMA_PE"
                last_signal_time = idx
                
        # 4. Map 5-Minute signals back to the last available 1-Minute candle of each 5-minute bar
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
                
        print(f"[DEBUG Strategy 13] Generated {len(sig_indices)} 5m signals. Mapped {df[df['Signal'] != 0].shape[0]} to 1m DataFrame.")
        return df
