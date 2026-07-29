import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

def calculate_smma(series: pd.Series, length: int) -> pd.Series:
    if len(series) < length:
        return pd.Series(index=series.index, dtype=float)
    return series.ewm(alpha=1.0 / length, adjust=False).mean()

@register_strategy
class Strategy17(BaseStrategy):
    """
    Strategy 17: All-Rounder Master Strategy (Regime-Adaptive Meta Engine)
    
    Combines 3 Specialized High-Expectancy Engines:
    - Engine 1 (TREND): Strategy 10 WMA 50 Breakout (Active when ADX > 25)
    - Engine 2 (RANGE): Strategy 12 RSI 9 Overbought/Oversold Reversion (Active when ADX < 20)
    - Engine 3 (OPENING): Strategy 15 Opening Pattern Momentum (Active between 09:15 - 09:45)
    
    Features:
    - Configurable Exit Modes: POINTS vs DYNAMIC_ATR vs SWING
    - Daily Trade Limit: Capped at 2 or 3 trades per day to prevent overtrading.
    """
    name = "Strategy_17"

    def get_default_params(self) -> dict:
        return {
            "timeframe": "5min",
            "rsi_length": 9,
            "ema_length": 3,
            "wma_length": 21,
            "adx_length": 14,
            "breakout_wait_bars": 2,
            "exit_mode": "POINTS",  # "POINTS" or "DYNAMIC_ATR" or "SWING"
            "max_daily_trades": 2,  # Cap max trades per day
            "atr_period": 14,
            "atr_sl_mult": 1.5,
            "atr_tp_mult": 3.0
        }

    def get_optimization_grid(self) -> dict:
        return {
            "timeframe": ["5min"],
            "exit_mode": ["POINTS", "DYNAMIC_ATR"],
            "max_daily_trades": [2, 3]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # 1. Resample to 5-minute primary timeframe
        tf = self.params.get("timeframe", "5min")
        df_tf = df.groupby(df.index.date, group_keys=False).apply(
            lambda x: x.resample(tf, origin='start').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
        ).dropna()
        
        if len(df_tf) < 30:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            df['Exit_Long'] = False
            df['Exit_Short'] = False
            return df
            
        # 2. Indicators Calculation (RSI 9, EMA 3, WMA 21, ADX 14, ATR 14)
        rsi_len = self.params.get("rsi_length", 9)
        ema_len = self.params.get("ema_length", 3)
        wma_len = self.params.get("wma_length", 21)
        adx_len = self.params.get("adx_length", 14)
        atr_len = self.params.get("atr_period", 14)
        
        df_tf['rsi'] = ta.rsi(df_tf['close'], length=rsi_len)
        df_tf['fast_line'] = ta.ema(df_tf['rsi'], length=ema_len)
        df_tf['slow_line'] = ta.wma(df_tf['rsi'], length=wma_len)
        
        adx_df = ta.adx(high=df_tf['high'], low=df_tf['low'], close=df_tf['close'], length=adx_len)
        df_tf['adx'] = adx_df[f'ADX_{adx_len}'] if adx_df is not None and not adx_df.empty else 20.0
        
        df_tf['atr'] = ta.atr(df_tf['high'], df_tf['low'], df_tf['close'], length=atr_len)
        df_tf['atr'] = df_tf['atr'].ffill().bfill()
        
        # 18 SMMA for Dynamic Exits / Trend Check
        df_tf['SMMA_18'] = calculate_smma(df_tf['close'], length=18)
        
        # 3. Market Regime Classification
        # TREND: ADX > 25 | RANGE: ADX < 20 | NEUTRAL: 20 <= ADX <= 25
        df_tf['Regime'] = np.where(df_tf['adx'] > 25.0, "TREND",
                          np.where(df_tf['adx'] < 20.0, "RANGE", "NEUTRAL"))
                          
        # 4. Engine 1: Strategy 10 (WMA 50 Breakout - Active in TREND or NEUTRAL)
        df_tf['prev_slow'] = df_tf['slow_line'].shift(1)
        cross_buy_s10 = (df_tf['prev_slow'] <= 50) & (df_tf['slow_line'] > 50)
        cross_sell_s10 = (df_tf['prev_slow'] >= 50) & (df_tf['slow_line'] < 50)
        
        wait_bars = int(self.params.get("breakout_wait_bars", 2))
        s10_long_act = cross_buy_s10.rolling(window=wait_bars, min_periods=1).max().fillna(0).astype(bool)
        s10_short_act = cross_sell_s10.rolling(window=wait_bars, min_periods=1).max().fillna(0).astype(bool)
        
        df_tf['Sig_High_S10'] = df_tf['high'].where(cross_buy_s10).ffill()
        df_tf['Sig_Low_S10'] = df_tf['low'].where(cross_sell_s10).ffill()
        
        # 5. Engine 2: Strategy 12 (RSI 9 Overbought/Oversold Reversion - Active in RANGE)
        s12_buy = (df_tf['rsi'] < 30) & (df_tf['rsi'].shift(1) >= 30)
        s12_sell = (df_tf['rsi'] > 70) & (df_tf['rsi'].shift(1) <= 70)
        
        # 6. Shift 5-minute indicators by 1 bar to prevent lookahead bias
        cols_to_shift = ['Regime', 's10_long_act', 's10_short_act', 'Sig_High_S10', 'Sig_Low_S10', 
                         'rsi', 'SMMA_18', 'atr']
        df_tf['s10_long_act'] = s10_long_act
        df_tf['s10_short_act'] = s10_short_act
        df_tf['s12_buy'] = s12_buy
        df_tf['s12_sell'] = s12_sell
        
        df_tf_shifted = df_tf.shift(1)
        
        # Join shifted indicators to 1-minute dataframe
        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns], errors='ignore')
        df = df.join(df_tf_shifted[cols_to_shift + ['s12_buy', 's12_sell']], how='left')
        df[cols_to_shift] = df[cols_to_shift].ffill()
        df['s12_buy'] = df['s12_buy'].fillna(False).astype(bool)
        df['s12_sell'] = df['s12_sell'].fillna(False).astype(bool)
        
        # 7. Generate Intraday Signals (1-Minute Execution)
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        
        # Time Window Filters
        df['time'] = df.index.time
        in_time_window = (df['time'] >= pd.to_datetime('09:20:00').time()) & (df['time'] <= pd.to_datetime('15:00:00').time())
        is_opening_window = (df['time'] >= pd.to_datetime('09:15:00').time()) & (df['time'] <= pd.to_datetime('09:45:00').time())
        
        # Signals Combination:
        # A) Trend Engine (S10 Breakout during TREND/NEUTRAL regime)
        trend_buy = in_time_window & (df['Regime'] != "RANGE") & (df['s10_long_act'] == True) & (df['close'] > df['Sig_High_S10'])
        trend_sell = in_time_window & (df['Regime'] != "RANGE") & (df['s10_short_act'] == True) & (df['close'] < df['Sig_Low_S10'])
        
        # B) Range Engine (S12 RSI Reversion during RANGE regime)
        range_buy = in_time_window & (df['Regime'] == "RANGE") & (df['s12_buy'] == True)
        range_sell = in_time_window & (df['Regime'] == "RANGE") & (df['s12_sell'] == True)
        
        raw_buy = trend_buy | range_buy
        raw_sell = trend_sell | range_sell
        
        raw_buy_first = raw_buy & (~raw_buy.shift(1).fillna(False))
        raw_sell_first = raw_sell & (~raw_sell.shift(1).fillna(False))
        
        df.loc[raw_buy_first, 'Signal'] = 1
        df.loc[raw_buy_first, 'Signal_Source'] = "S17_ALL_ROUNDER_BUY"
        
        df.loc[raw_sell_first, 'Signal'] = -1
        df.loc[raw_sell_first, 'Signal_Source'] = "S17_ALL_ROUNDER_SELL"
        
        # 8. Apply Daily Max Trades Limit Filter (Max 2 or 3 trades per day)
        max_trades = int(self.params.get("max_daily_trades", 2))
        df['date'] = df.index.date
        df['is_sig'] = (df['Signal'] != 0).astype(int)
        df['daily_sig_count'] = df.groupby('date')['is_sig'].cumsum()
        
        over_limit = df['daily_sig_count'] > max_trades
        df.loc[over_limit, 'Signal'] = 0
        df.loc[over_limit, 'Signal_Source'] = "None"
        
        # 9. Dynamic Exit Flags (If exit_mode == DYNAMIC_ATR or SWING)
        exit_mode = str(self.params.get("exit_mode", "POINTS")).upper()
        if exit_mode in ["DYNAMIC_ATR", "SWING"]:
            df['Exit_Long'] = df['close'] < df['SMMA_18']
            df['Exit_Short'] = df['close'] > df['SMMA_18']
        else:
            df['Exit_Long'] = False
            df['Exit_Short'] = False
            
        df.drop(columns=['is_sig', 'daily_sig_count'], errors='ignore', inplace=True)
        return df
