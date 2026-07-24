import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy10(BaseStrategy):
    name = "Strategy_10"

    def get_default_params(self) -> dict:
        return {
            "rsi_length": 9,
            "ema_length": 3,
            "wma_length": 21,
            "adx_length": 14,
            "use_vwap_filter": 0,  # 0 = False, 1 = True
            "timeframe": "5min",  # e.g., "5min", "60min"
            "entry_rule": "wma_cross_breakout",  # "slow_cross_50", "fast_cross_slow", "wma_cross_breakout"
            "breakout_wait_bars": 2,  # wait time in resampled bars for breakout
            "entry_start_time": "09:15",
            "entry_end_time": "15:00"
        }

    def get_optimization_grid(self) -> dict:
        return {
            "rsi_length": [9],
            "ema_length": [3],
            "wma_length": [21],
            "adx_length": [14],
            "use_vwap_filter": [0],
            "timeframe": ["5min"],
            "entry_rule": ["wma_cross_breakout"],
            "breakout_wait_bars": [1, 2, 3]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # Parse start and end time parameters
        import datetime
        try:
            start_str = self.params.get("entry_start_time", "09:15")
            end_str = self.params.get("entry_end_time", "15:00")
            t_start = datetime.datetime.strptime(start_str, "%H:%M").time()
            t_end = datetime.datetime.strptime(end_str, "%H:%M").time()
        except Exception:
            t_start = datetime.time(9, 15)
            t_end = datetime.time(15, 0)
            
        # 1. Resample to timeframe day-by-day (aligned exactly to start time of each session to match Indian market 09:15 open)
        tf = self.params.get("timeframe", "60min")
        df_tf = df.groupby(df.index.date, group_keys=False).apply(
            lambda x: x.resample(tf, origin='start').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
        ).dropna()
        
        if len(df_tf) < 50:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df
            
        # 2. Calculate RSI based on configured length on resampled timeframe
        df_tf['rsi'] = ta.rsi(df_tf['close'], length=self.params["rsi_length"])
        
        # 3. Calculate Hilega Milega Lines on resampled timeframe
        df_tf['fast_line'] = ta.ema(df_tf['rsi'], length=self.params["ema_length"])
        df_tf['slow_line'] = ta.wma(df_tf['rsi'], length=self.params["wma_length"])
        
        # Calculate ADX on resampled timeframe
        adx_df = ta.adx(high=df_tf['high'], low=df_tf['low'], close=df_tf['close'], length=self.params["adx_length"])
        if adx_df is not None and not adx_df.empty:
            df_tf['adx'] = adx_df[f'ADX_{self.params["adx_length"]}']
        else:
            df_tf['adx'] = 0.0
        
        # 4. Calculate VWAP on resampled timeframe
        has_valid_volume = ('volume' in df_tf.columns) and (df_tf['volume'].sum() > 0)
        if self.params["use_vwap_filter"] == 1 and has_valid_volume:
            df_tf['vwap'] = ta.vwap(high=df_tf['high'], low=df_tf['low'], close=df_tf['close'], volume=df_tf['volume'])
            df_tf['above_vwap'] = df_tf['close'] > df_tf['vwap']
            df_tf['below_vwap'] = df_tf['close'] < df_tf['vwap']
        else:
            df_tf['above_vwap'] = True
            df_tf['below_vwap'] = True
            
        # 5. Determine Trigger Conditions based on entry rule
        rule = self.params.get("entry_rule", "wma_cross_breakout")
        
        df_tf['prev_slow'] = df_tf['slow_line'].shift(1)
        df_tf['prev_fast'] = df_tf['fast_line'].shift(1)
        
        cross_buy = (df_tf['prev_slow'] <= 50) & (df_tf['slow_line'] > 50)
        cross_sell = (df_tf['prev_slow'] >= 50) & (df_tf['slow_line'] < 50)
        
        if rule == "slow_cross_50":
            df_tf['long_trigger_active'] = cross_buy
            df_tf['short_trigger_active'] = cross_sell
            df_tf['Sig_High'] = df_tf['close']
            df_tf['Sig_Low'] = df_tf['close']
        elif rule == "fast_cross_slow":
            df_tf['long_trigger_active'] = (df_tf['prev_fast'] <= df_tf['prev_slow']) & (df_tf['fast_line'] > df_tf['slow_line'])
            df_tf['short_trigger_active'] = (df_tf['prev_fast'] >= df_tf['prev_slow']) & (df_tf['fast_line'] < df_tf['slow_line'])
            df_tf['Sig_High'] = df_tf['close']
            df_tf['Sig_Low'] = df_tf['close']
        else: # "wma_cross_breakout"
            wait_bars = int(self.params.get("breakout_wait_bars", 3))
            
            # Record breakout targets (High of cross-over candle for long, Low for short)
            # We use ffill to carry forward the level during the wait window
            df_tf['Sig_High'] = df_tf['high'].where(cross_buy).ffill()
            df_tf['Sig_Low'] = df_tf['low'].where(cross_sell).ffill()
            
            # Track the date of the signal candle
            df_tf['Sig_Date_Long'] = df_tf.index.to_series().dt.date.where(cross_buy).ffill().fillna(datetime.date(1970, 1, 1))
            df_tf['Sig_Date_Short'] = df_tf.index.to_series().dt.date.where(cross_sell).ffill().fillna(datetime.date(1970, 1, 1))
            
            # Active trigger flags propagated using rolling max
            long_act = cross_buy.rolling(window=wait_bars, min_periods=1).max().fillna(0).astype(bool)
            short_act = cross_sell.rolling(window=wait_bars, min_periods=1).max().fillna(0).astype(bool)
            
            # Cancel opposite signals immediately
            if wait_bars > 1:
                long_act = np.where(cross_sell, False, long_act)
                short_act = np.where(cross_buy, False, short_act)
                
            df_tf['long_trigger_active'] = long_act
            df_tf['short_trigger_active'] = short_act
            
        # 6. Shift resampled indicators by 1 bar to prevent lookahead bias in backtests
        cols_to_shift = ['fast_line', 'slow_line', 'adx', 'above_vwap', 'below_vwap', 
                         'long_trigger_active', 'short_trigger_active', 'Sig_High', 'Sig_Low']
        if rule == "wma_cross_breakout":
            cols_to_shift.extend(['Sig_Date_Long', 'Sig_Date_Short'])
        df_tf[cols_to_shift] = df_tf[cols_to_shift].shift(1)
        
        # Drop overlapping columns from 1-min df to prevent duplicate column errors
        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns], errors='ignore')
        
        # Join the resampled state variables back to the 1-min dataframe
        df = df.join(df_tf[cols_to_shift], how='left')
        
        # Forward-fill state variables so every 1-min row has the latest resampled state
        df[cols_to_shift] = df[cols_to_shift].ffill()
        
        # Cast boolean columns correctly after forward-filling
        df['above_vwap'] = df['above_vwap'].fillna(True).astype(bool)
        df['below_vwap'] = df['below_vwap'].fillna(True).astype(bool)
        df['long_trigger_active'] = df['long_trigger_active'].fillna(False).astype(bool)
        df['short_trigger_active'] = df['short_trigger_active'].fillna(False).astype(bool)
        
        # 7. Initialize Signal columns
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        
        df['prev_adx'] = df['adx'].shift(1)
        
        # Check time condition on the 1-minute DataFrame index
        df_time = df.index.time
        time_cond = (df_time >= t_start) & (df_time <= t_end)
        
        # Determine 1-minute entries based on target rule crossing/breakout
        if rule in ["slow_cross_50", "fast_cross_slow"]:
            buy_cond = df['long_trigger_active'] & (df['adx'] > df['prev_adx']) & df['above_vwap'] & time_cond
            sell_cond = df['short_trigger_active'] & (df['adx'] > df['prev_adx']) & df['below_vwap'] & time_cond
        else: # "wma_cross_breakout"
            # Parse signal dates to standard Python date objects
            df['Sig_Date_Long'] = pd.to_datetime(df['Sig_Date_Long']).dt.date
            df['Sig_Date_Short'] = pd.to_datetime(df['Sig_Date_Short']).dt.date
            
            # Detect first candle of each trading day
            day_start_mask = pd.Series(df.index.date, index=df.index).shift(1) != df.index.date
            day_start_mask.iloc[0] = False
            
            # Extract previous day's close price and calculate opening gap percentage
            yesterday_close = df['close'].shift(1).where(day_start_mask).ffill()
            gap_pct = (abs(df['open'] - yesterday_close) / yesterday_close).where(day_start_mask).fillna(0.0)
            
            is_carry_over_long = df.index.date > df['Sig_Date_Long']
            is_carry_over_short = df.index.date > df['Sig_Date_Short']
            
            # Invalidation conditions on the opening tick:
            # 1. Level breach: price opens already past the breakout level
            # 2. Large gap: open gaps relative to yesterday close by > 0.5% (0.005)
            level_breach_long = is_carry_over_long & (df['open'] > df['Sig_High'])
            level_breach_short = is_carry_over_short & (df['open'] < df['Sig_Low'])
            large_gap = (is_carry_over_long | is_carry_over_short) & (gap_pct > 0.005)
            
            cancel_long_start = day_start_mask & (level_breach_long | large_gap)
            cancel_short_start = day_start_mask & (level_breach_short | large_gap)
            
            # Propagate cancellation throughout all candles of the day
            cancel_long_today = cancel_long_start.astype(int).groupby(df.index.date).transform('max').astype(bool)
            cancel_short_today = cancel_short_start.astype(int).groupby(df.index.date).transform('max').astype(bool)
            
            # Invalidate the active triggers if they are carry-overs and met cancellation conditions
            active_long = df['long_trigger_active'] & ~(is_carry_over_long & cancel_long_today)
            active_short = df['short_trigger_active'] & ~(is_carry_over_short & cancel_short_today)
            
            # Breakout logic (no ADX or VWAP filters as per request)
            buy_cond = active_long & (df['close'] > df['Sig_High']) & time_cond
            sell_cond = active_short & (df['close'] < df['Sig_Low']) & time_cond
            
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[buy_cond, 'Signal_Source'] = "Hilega Milega Long"
        
        df.loc[sell_cond, 'Signal'] = -1
        df.loc[sell_cond, 'Signal_Source'] = "Hilega Milega Short"
        
        # Clean up shift columns to keep DataFrame clean
        df.drop(columns=['prev_slow', 'prev_fast', 'prev_adx', 'above_vwap', 'below_vwap', 
                         'long_trigger_active', 'short_trigger_active', 'Sig_High', 'Sig_Low',
                         'Sig_Date_Long', 'Sig_Date_Short'], inplace=True, errors='ignore')
        
        return df
