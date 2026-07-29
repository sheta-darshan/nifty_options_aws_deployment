import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy18(BaseStrategy):
    """
    Strategy 18: First 5-Minute Opening Momentum Breakout Strategy
    
    Based on 5-year Nifty statistical research (1,271 trading days) showing a 90% continuation rate:
    - Candle 1 (09:15 - 09:20 AM) defines C1_High and C1_Low.
    - If Candle 1 is GREEN, target = C1_High.
    - If Candle 1 is RED, target = C1_Low.
    - Intraday 1-minute candle CLOSE above C1_High triggers BUY (Call Option).
    - Intraday 1-minute candle CLOSE below C1_Low triggers SELL (Put Option).
    - Execution Window: 09:20 AM to 09:45 AM.
    - Daily Limit: Strictly max 1 trade per day.
    """
    name = "Strategy_18"

    def get_default_params(self) -> dict:
        return {
            "timeframe": "5min",
            "breakout_window_end": "09:45",
            "entry_mode": "CLOSE",  # Confirmed 1-minute candle close
            "max_daily_trades": 1,   # Max 1 trade per day
            "points_sl_buy": 15.0,
            "points_target_buy": 45.0,
            "points_trail_buy": 0.0,
            "points_sl_sell": 15.0,
            "points_target_sell": 45.0,
            "points_trail_sell": 0.0
        }

    def get_optimization_grid(self) -> dict:
        return {
            "breakout_window_end": ["09:35", "09:45", "10:00"],
            "points_sl_buy": [15.0, 20.0],
            "points_target_buy": [30.0, 45.0, 60.0],
            "points_trail_buy": [0.0, 10.0, 15.0]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        df['date'] = df.index.date
        df['time'] = df.index.time
        
        # 1. Calculate Candle 1 (09:15 - 09:20 AM) for each date
        df_5m = df.groupby('date', group_keys=False).apply(
            lambda x: x.resample('5min', origin='start').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            })
        ).dropna()
        
        if len(df_5m) < 2:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df
            
        df_5m['date'] = df_5m.index.date
        df_5m['time'] = df_5m.index.time
        
        # Filter for the 09:15 AM candle
        c1 = df_5m[df_5m['time'] == pd.to_datetime('09:15:00').time()].copy()
        c1['c1_high'] = c1['high']
        c1['c1_low'] = c1['low']
        c1['c1_green'] = c1['close'] > c1['open']
        c1['c1_red'] = c1['close'] < c1['open']
        
        # Map Candle 1 levels back to 1-minute dataframe
        c1_dict_high = c1.set_index('date')['c1_high'].to_dict()
        c1_dict_low = c1.set_index('date')['c1_low'].to_dict()
        c1_dict_green = c1.set_index('date')['c1_green'].to_dict()
        c1_dict_red = c1.set_index('date')['c1_red'].to_dict()
        
        df['c1_high'] = df['date'].map(c1_dict_high)
        df['c1_low'] = df['date'].map(c1_dict_low)
        df['c1_green'] = df['date'].map(c1_dict_green).fillna(False).astype(bool)
        df['c1_red'] = df['date'].map(c1_dict_red).fillna(False).astype(bool)

        # Candle 1 Range Filter
        min_range = float(self.params.get("min_c1_range_pts", 0.0))
        c1['c1_range'] = c1['c1_high'] - c1['c1_low']
        c1['valid_range'] = c1['c1_range'] >= min_range if min_range > 0 else True
        
        c1_dict_range_valid = c1.set_index('date')['valid_range'].to_dict()
        df['valid_range'] = df['date'].map(c1_dict_range_valid).fillna(True).astype(bool)

        # 2. Define Execution Window (09:20 AM to breakout_window_end)
        window_end_str = self.params.get("breakout_window_end", "09:45")
        try:
            import datetime
            t_end = datetime.datetime.strptime(window_end_str, "%H:%M").time()
        except Exception:
            t_end = datetime.time(9, 45)
            
        in_window = (df['time'] >= pd.to_datetime('09:20:00').time()) & (df['time'] <= t_end)
        
        # 3. Entry Condition (Confirmed 1-minute Candle CLOSE & Valid Range)
        buy_breakout = in_window & df['valid_range'] & df['c1_green'] & (df['close'] > df['c1_high'])
        sell_breakout = in_window & df['valid_range'] & df['c1_red'] & (df['close'] < df['c1_low'])
        
        buy_sig = buy_breakout & (~buy_breakout.shift(1).fillna(False))
        sell_sig = sell_breakout & (~sell_breakout.shift(1).fillna(False))
        
        # 4. Strictly 1 Trade per Day Limit
        df['is_sig'] = (buy_sig | sell_sig).astype(int)
        df['daily_sig_count'] = df.groupby('date')['is_sig'].cumsum()
        
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        
        valid_buy = buy_sig & (df['daily_sig_count'] == 1)
        valid_sell = sell_sig & (df['daily_sig_count'] == 1)
        
        df.loc[valid_buy, 'Signal'] = 1
        df.loc[valid_buy, 'Signal_Source'] = "18_FIRST_5MIN_BUY"
        
        df.loc[valid_sell, 'Signal'] = -1
        df.loc[valid_sell, 'Signal_Source'] = "18_FIRST_5MIN_SELL"
        
        df['Exit_Long'] = False
        df['Exit_Short'] = False
        
        df.drop(columns=['is_sig', 'daily_sig_count', 'date', 'time'], errors='ignore', inplace=True)
        return df
