import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy15(BaseStrategy):
    name = "Strategy_15"

    def get_default_params(self) -> dict:
        return {
            "OPENING_PATTERN_FILTER": True,
            "DYNAMIC_TIMING_MODE": True,
            "EVALUATION_TIME": "09:45:00",
            "ENTRY_TIME": "09:45:00",
            "ENTRY_TIMES": [
                "09:45:00"
            ],
            "ATR_PERIOD": 14,
            "ADX_PERIOD": 14,
            "MAX_ADX": 25.0,
            "MAX_CANDLE_BODY": 20.0
        }

    def get_optimization_grid(self) -> dict:
        return {
            "ENTRY_TIME": ["09:45:00", "10:15:00", "10:45:00", "11:15:00"],
            "ATR_PERIOD": [14]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # Calculate ATR and ADX
        if 'ATR' not in df.columns:
            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=self.params.get("ATR_PERIOD", 14))
            df['ATR'] = df['ATR'].ffill().bfill()
            
        if 'ADX' not in df.columns and 'TM_ADX' not in df.columns:
            try:
                adx_df = ta.adx(df['high'], df['low'], df['close'], length=self.params.get("ADX_PERIOD", 14))
                df['ADX'] = adx_df[f"ADX_{self.params.get('ADX_PERIOD', 14)}"].ffill().bfill()
            except Exception:
                df['ADX'] = 20.0
        elif 'TM_ADX' in df.columns:
            df['ADX'] = df['TM_ADX']
        
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        
        use_opening_filter = self.params.get("OPENING_PATTERN_FILTER", True)
        use_dynamic_timing = self.params.get("DYNAMIC_TIMING_MODE", True)
        max_adx = self.params.get("MAX_ADX", 25.0)
        max_body = self.params.get("MAX_CANDLE_BODY", 20.0)
        
        entry_times = self.params.get("ENTRY_TIMES", [self.params.get("ENTRY_TIME", "09:45:00")])
        if not isinstance(entry_times, list):
            entry_times = [entry_times]
        target_times = [pd.Timestamp(t).time() for t in entry_times]
        
        signals_to_emit = []
        
        for date_val, group in df.groupby(df.index.date):
            if len(group) < 5:
                continue
                
            # 1. Opening Pattern Breakout Filter
            if use_opening_filter:
                or_df = group.between_time('09:15', '09:45')
                if len(or_df) >= 3:
                    or_open = or_df['open'].iloc[0]
                    or_high = or_df['high'].max()
                    or_low = or_df['low'].min()
                    or_close = or_df['close'].iloc[-1]
                    or_range = or_high - or_low
                    body_pct = abs(or_close - or_open) / or_range if or_range > 0 else 0
                    
                    # Directional Breakout -> Skip day to protect capital
                    if body_pct >= 0.65 and or_range >= 45.0:
                        continue
            
            # 2. Dynamic Adaptive Timing vs Fixed Time Signals
            signal_emitted = False
            
            if use_dynamic_timing:
                # Scan window 09:30 to 11:30 for optimal entry candle
                window = group.between_time('09:30', '11:30')
                or_df_full = group.between_time('09:15', '09:45')
                or_high_val = or_df_full['high'].max() if not or_df_full.empty else window['high'].max()
                or_low_val = or_df_full['low'].min() if not or_df_full.empty else window['low'].min()
                or_range_val = max(or_high_val - or_low_val, 1.0)
                
                mid_low = or_low_val + (or_range_val * 0.20)
                mid_high = or_high_val - (or_range_val * 0.20)
                
                for ts, row in window.iterrows():
                    adx_val = row.get('ADX', 20.0)
                    candle_body = abs(row['close'] - row['open'])
                    spot_close = row['close']
                    
                    is_ranging = (adx_val <= max_adx)
                    is_quiet = (candle_body <= max_body)
                    in_mid_zone = (mid_low <= spot_close <= mid_high)
                    
                    if is_ranging and is_quiet and in_mid_zone:
                        signals_to_emit.append((ts, "DynamicAdaptive_Entry"))
                        signal_emitted = True
                        break
            
            # Fallback to fixed target times ONLY if dynamic timing is explicitly disabled
            if not use_dynamic_timing and not signal_emitted:
                for ts, row in group.iterrows():
                    if row.name.time() in target_times:
                        signals_to_emit.append((ts, "FixedTime_Entry"))
                        break

        # Emit signals onto dataframe
        for ts, source in signals_to_emit:
            if ts in df.index:
                df.loc[ts, 'Signal'] = 1
                df.loc[ts, 'Signal_Source'] = source
                
        return df
