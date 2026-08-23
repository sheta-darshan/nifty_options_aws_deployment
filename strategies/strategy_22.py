import pandas as pd
import numpy as np
import datetime
try:
    import pandas_ta as ta
except ImportError:
    ta = None

from .base import BaseStrategy
from .registry import register_strategy

def calculate_price_series(df: pd.DataFrame, source: str = "OHLC4") -> pd.Series:
    """
    Computes the price series based on the chosen source:
    - OHLC4: (Open + High + Low + Close) / 4
    - HLC3:  (High + Low + Close) / 3
    - HL2:   (High + Low) / 2
    - CLOSE: Close price
    """
    src = source.upper()
    if src == "OHLC4":
        return (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
    elif src == "HLC3":
        return (df['high'] + df['low'] + df['close']) / 3.0
    elif src == "HL2":
        return (df['high'] + df['low']) / 2.0
    elif src == "CLOSE":
        return df['close']
    elif src == "OPEN":
        return df['open']
    elif src == "HIGH":
        return df['high']
    elif src == "LOW":
        return df['low']
    else:
        return (df['open'] + df['high'] + df['low'] + df['close']) / 4.0

def calculate_smma(series: pd.Series, length: int) -> pd.Series:
    """
    Calculates Wilder's Smoothed Moving Average (RMA / SMMA).
    SMMA_t = (SMMA_{t-1} * (length - 1) + Price_t) / length
    Initializes with SMA(length) seed.
    """
    if len(series) < length:
        return pd.Series(np.nan, index=series.index)
    
    values = series.to_numpy(dtype=float)
    smma = np.full_like(values, np.nan)
    
    valid_idx = np.where(~np.isnan(values))[0]
    if len(valid_idx) < length:
        return pd.Series(np.nan, index=series.index)
        
    start_i = valid_idx[length - 1]
    smma[start_i] = np.mean(values[valid_idx[:length]])
    
    alpha_inv = float(length)
    for i in range(start_i + 1, len(values)):
        if np.isnan(values[i]):
            smma[i] = smma[i - 1]
        else:
            smma[i] = (smma[i - 1] * (alpha_inv - 1.0) + values[i]) / alpha_inv
            
    return pd.Series(smma, index=series.index)

def calculate_ema(series: pd.Series, length: int) -> pd.Series:
    """Calculates Exponential Moving Average (EMA)"""
    return series.ewm(span=length, adjust=False).mean()

def _run_core_engine(df_calc: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Core state machine evaluation on the target timeframe dataframe.
    """
    source_name = str(params.get("PRICE_SOURCE", "OHLC4"))
    ema_len = int(params.get("EMA_FAST", 18))
    smma_len = int(params.get("SMMA_BASE", 18))
    entry_mode = str(params.get("ENTRY_MODE", "CROSSOVER")).upper()
    exit_mode = str(params.get("EXIT_MODE", "OPPOSITE_CROSS")).upper()
    
    confirm_candles = int(params.get("CONFIRMATION_CANDLES", 1))
    min_spread_atr = float(params.get("MIN_SPREAD_ATR", 0.15))
    slope_lookback = int(params.get("SLOPE_LOOKBACK", 3))
    min_slope = float(params.get("MIN_SLOPE", 0.002))
    require_accel = bool(params.get("REQUIRE_ACCELERATION", True))
    spread_decay_bars = int(params.get("SPREAD_DECAY_BARS", 2))
    
    use_atr_exp = bool(params.get("USE_ATR_EXPANSION", False))
    atr_period = int(params.get("ATR_PERIOD", 14))
    atr_base_len = int(params.get("ATR_BASELINE_PERIOD", 20))
    atr_ratio_thresh = float(params.get("ATR_RATIO_THRESHOLD", 1.0))
    
    start_time_str = str(params.get("START_TIME", "09:20:00"))
    end_time_str = str(params.get("END_TIME", "14:45:00"))

    # 1. Base Series
    price_series = calculate_price_series(df_calc, source_name)
    df_calc['Price_Src'] = price_series
    
    ema_series = calculate_ema(price_series, ema_len)
    smma_series = calculate_smma(price_series, smma_len)
    df_calc['EMA'] = ema_series
    df_calc['SMMA'] = smma_series
    
    spread = ema_series - smma_series
    df_calc['Spread'] = spread
    
    velocity = spread.diff()
    smoothed_velocity = velocity.rolling(3, min_periods=1).mean()
    acceleration = smoothed_velocity.diff()
    df_calc['Velocity'] = velocity
    df_calc['Acceleration'] = acceleration
    
    ema_prev = ema_series.shift(slope_lookback)
    smma_prev = smma_series.shift(slope_lookback)
    df_calc['EMA_Slope'] = ((ema_series - ema_prev) / ema_prev) * 100.0
    df_calc['SMMA_Slope'] = ((smma_series - smma_prev) / smma_prev) * 100.0

    if ta is not None:
        df_calc['ATR'] = ta.atr(df_calc['high'], df_calc['low'], df_calc['close'], length=atr_period).fillna(0.0)
    else:
        tr = np.maximum(df_calc['high'] - df_calc['low'], 
                        np.maximum(abs(df_calc['high'] - df_calc['close'].shift(1)), 
                                   abs(df_calc['low'] - df_calc['close'].shift(1))))
        df_calc['ATR'] = tr.rolling(atr_period).mean().fillna(0.0)

    atr_sma = df_calc['ATR'].rolling(atr_base_len).mean()
    df_calc['ATR_Ratio'] = np.where(atr_sma > 0, df_calc['ATR'] / atr_sma, 1.0)
    df_calc['ATR_Ratio'] = df_calc['ATR_Ratio'].fillna(1.0)
    df_calc['Normalized_Spread'] = np.where(df_calc['ATR'] > 0, df_calc['Spread'] / df_calc['ATR'], 0.0)

    # 2. Session & Filter Gating
    time_index = df_calc.index.time
    start_t = datetime.time.fromisoformat(start_time_str)
    end_t = datetime.time.fromisoformat(end_time_str)
    
    time_allowed_v = np.array((time_index >= start_t) & (time_index <= end_t), dtype=bool)
    vol_allowed_v = (df_calc['ATR_Ratio'].values >= atr_ratio_thresh) if use_atr_exp else np.ones(len(df_calc), dtype=bool)
    day_idx = df_calc.groupby(df_calc.index.date).cumcount().values

    # 3. Vectorized Evaluation
    n = len(df_calc)
    ema_v = df_calc['EMA'].values
    smma_v = df_calc['SMMA'].values
    spread_v = df_calc['Spread'].values
    norm_spread_v = df_calc['Normalized_Spread'].values
    vel_v = df_calc['Velocity'].values
    acc_v = df_calc['Acceleration'].values
    ema_slope_v = df_calc['EMA_Slope'].values
    smma_slope_v = df_calc['SMMA_Slope'].values
    src_v = df_calc['Price_Src'].values
    high_v = df_calc['high'].values
    low_v = df_calc['low'].values
    close_v = df_calc['close'].values

    raw_signals = np.zeros(n, dtype=int)
    raw_exit_long = np.zeros(n, dtype=bool)
    raw_exit_short = np.zeros(n, dtype=bool)

    trend_state = 0
    pullback_armed = 0

    for i in range(1, n):
        if day_idx[i] == 0:
            trend_state = 0
            pullback_armed = 0

        if np.isnan(ema_v[i]) or np.isnan(smma_v[i]) or np.isnan(ema_v[i-1]) or np.isnan(smma_v[i-1]):
            continue

        cross_up = (ema_v[i-1] <= smma_v[i-1]) and (ema_v[i] > smma_v[i])
        cross_down = (ema_v[i-1] >= smma_v[i-1]) and (ema_v[i] < smma_v[i])

        if cross_up:
            trend_state = 1
            pullback_armed = 0
        elif cross_down:
            trend_state = -1
            pullback_armed = 0

        can_enter = time_allowed_v[i] and vol_allowed_v[i] and (day_idx[i] >= 2)

        long_trigger = False
        short_trigger = False

        if can_enter:
            if entry_mode == "CROSSOVER":
                long_trigger = cross_up
                short_trigger = cross_down

            elif entry_mode == "CROSS_PERSISTENCE":
                if trend_state == 1:
                    if i >= confirm_candles:
                        is_confirmed = all(ema_v[i - c] > smma_v[i - c] for c in range(confirm_candles))
                        is_prior_cross = (ema_v[i - confirm_candles] <= smma_v[i - confirm_candles])
                        long_trigger = is_confirmed and is_prior_cross
                elif trend_state == -1:
                    if i >= confirm_candles:
                        is_confirmed = all(ema_v[i - c] < smma_v[i - c] for c in range(confirm_candles))
                        is_prior_cross = (ema_v[i - confirm_candles] >= smma_v[i - confirm_candles])
                        short_trigger = is_confirmed and is_prior_cross

            elif entry_mode == "SPREAD_EXPANSION":
                accel_long_ok = (acc_v[i] > 0) if require_accel else True
                accel_short_ok = (acc_v[i] < 0) if require_accel else True
                vel_rebound_up = (vel_v[i-1] <= 0) and (vel_v[i] > 0)
                vel_rebound_down = (vel_v[i-1] >= 0) and (vel_v[i] < 0)
                
                long_trigger = (ema_v[i] > smma_v[i]) and (cross_up or vel_rebound_up) and accel_long_ok
                short_trigger = (ema_v[i] < smma_v[i]) and (cross_down or vel_rebound_down) and accel_short_ok

            elif entry_mode == "SLOPE_ALIGNED":
                slopes_bull = (ema_slope_v[i] >= min_slope) and (smma_slope_v[i] >= min_slope)
                slopes_bear = (ema_slope_v[i] <= -min_slope) and (smma_slope_v[i] <= -min_slope)
                slopes_prev_bull = (ema_slope_v[i-1] >= min_slope) and (smma_slope_v[i-1] >= min_slope)
                slopes_prev_bear = (ema_slope_v[i-1] <= -min_slope) and (smma_slope_v[i-1] <= -min_slope)
                
                long_trigger = (ema_v[i] > smma_v[i]) and slopes_bull and (not slopes_prev_bull or cross_up)
                short_trigger = (ema_v[i] < smma_v[i]) and slopes_bear and (not slopes_prev_bear or cross_down)

            elif entry_mode == "SPREAD_ATR":
                norm_cross_up = (norm_spread_v[i-1] < min_spread_atr) and (norm_spread_v[i] >= min_spread_atr)
                norm_cross_down = (norm_spread_v[i-1] > -min_spread_atr) and (norm_spread_v[i] <= -min_spread_atr)
                
                long_trigger = (ema_v[i] > smma_v[i]) and (cross_up or norm_cross_up)
                short_trigger = (ema_v[i] < smma_v[i]) and (cross_down or norm_cross_down)

            elif entry_mode == "PULLBACK_TOUCH":
                if trend_state == 1:
                    if low_v[i] <= ema_v[i] and close_v[i] > ema_v[i]:
                        long_trigger = True
                elif trend_state == -1:
                    if high_v[i] >= ema_v[i] and close_v[i] < ema_v[i]:
                        short_trigger = True

            elif entry_mode == "PULLBACK_ZONE":
                if trend_state == 1:
                    if smma_v[i] <= src_v[i] <= ema_v[i]:
                        pullback_armed = 1
                    elif pullback_armed == 1 and close_v[i] > high_v[i-1]:
                        long_trigger = True
                        pullback_armed = 0
                    elif close_v[i] < smma_v[i]:
                        pullback_armed = 0
                elif trend_state == -1:
                    if ema_v[i] <= src_v[i] <= smma_v[i]:
                        pullback_armed = -1
                    elif pullback_armed == -1 and close_v[i] < low_v[i-1]:
                        short_trigger = True
                        pullback_armed = 0
                    elif close_v[i] > smma_v[i]:
                        pullback_armed = 0

        if long_trigger:
            raw_signals[i] = 1
        elif short_trigger:
            raw_signals[i] = -1

        # Exits
        if exit_mode == "OPPOSITE_CROSS":
            raw_exit_long[i] = cross_down
            raw_exit_short[i] = cross_up
        elif exit_mode == "FAST_LINE_CROSS":
            raw_exit_long[i] = (src_v[i] < ema_v[i]) or cross_down
            raw_exit_short[i] = (src_v[i] > ema_v[i]) or cross_up
        elif exit_mode == "SMMA_CROSS":
            raw_exit_long[i] = (src_v[i] < smma_v[i]) or cross_down
            raw_exit_short[i] = (src_v[i] > smma_v[i]) or cross_up
        elif exit_mode == "SPREAD_REVERSAL":
            if i >= spread_decay_bars:
                spread_decay_long = all(spread_v[i - k] < spread_v[i - k - 1] for k in range(spread_decay_bars))
                spread_decay_short = all(spread_v[i - k] > spread_v[i - k - 1] for k in range(spread_decay_bars))
                raw_exit_long[i] = spread_decay_long or cross_down
                raw_exit_short[i] = spread_decay_short or cross_up

    # Deduplication state machine
    final_signals = np.zeros(n, dtype=int)
    last_sig = 0

    for i in range(n):
        if day_idx[i] == 0:
            last_sig = 0

        sig = raw_signals[i]
        if sig != 0:
            if sig != last_sig:
                final_signals[i] = sig
                last_sig = sig
            else:
                final_signals[i] = 0
        
        if last_sig == 1 and raw_exit_long[i]:
            last_sig = 0
        elif last_sig == -1 and raw_exit_short[i]:
            last_sig = 0

    df_calc['raw_signal'] = final_signals
    df_calc['raw_exit_long'] = raw_exit_long
    df_calc['raw_exit_short'] = raw_exit_short

    return df_calc

@register_strategy
class Strategy22(BaseStrategy):
    """
    Strategy 22: Modular EMA 18 / SMMA 18 (OHLC4) Algorithmic Engine
    Supports 1-Minute and Multi-Timeframe execution (e.g. 5min, 15min),
    Multiple Entry Modes (Crossover, Persistence, Spread Expansion, 
    Slope Alignment, Pullbacks) and Exit Modes.
    """
    name = "Strategy_22"

    def get_default_params(self) -> dict:
        return {
            # 1. Base Series Parameters
            "TIMEFRAME": "1min",              # "1min", "5min", "15min"
            "PRICE_SOURCE": "OHLC4",          # "OHLC4", "HLC3", "HL2", "CLOSE"
            "EMA_FAST": 18,                   # Fast EMA Period
            "SMMA_BASE": 18,                  # Base SMMA Period (Wilder's RMA)
            
            # 2. Entry Mode Configuration
            "ENTRY_MODE": "PULLBACK_ZONE",    # "CROSSOVER", "CROSS_PERSISTENCE", "SPREAD_EXPANSION", "SLOPE_ALIGNED", "PULLBACK_TOUCH", "PULLBACK_ZONE", "SPREAD_ATR"
            
            # Entry Specific Thresholds
            "CONFIRMATION_CANDLES": 1,        # For CROSS_PERSISTENCE (1 to 5)
            "MIN_SPREAD_ATR": 0.15,           # For SPREAD_ATR
            "SLOPE_LOOKBACK": 3,              # Slope calculation lookback
            "MIN_SLOPE": 0.002,               # Slope threshold in percentage
            "REQUIRE_ACCELERATION": True,     # Require positive acceleration for expansion
            
            # 3. Exit Mode Configuration
            "EXIT_MODE": "OPPOSITE_CROSS",    # "OPPOSITE_CROSS", "FAST_LINE_CROSS", "SMMA_CROSS", "SPREAD_REVERSAL"
            "SPREAD_DECAY_BARS": 2,           # For SPREAD_REVERSAL
            
            # 4. Volatility & Timing Filters
            "USE_ATR_EXPANSION": False,       # ATR(14) / SMA(ATR, 20) >= ATR_RATIO_THRESHOLD
            "ATR_PERIOD": 14,
            "ATR_BASELINE_PERIOD": 20,
            "ATR_RATIO_THRESHOLD": 1.0,
            
            "START_TIME": "09:20:00",         # Avoid opening auction spikes
            "END_TIME": "14:45:00",           # No new entries after cutoff
        }

    def get_optimization_grid(self) -> dict:
        return {
            "TIMEFRAME": ["1min", "5min"],
            "ENTRY_MODE": ["CROSSOVER", "CROSS_PERSISTENCE", "SPREAD_EXPANSION", "SLOPE_ALIGNED", "PULLBACK_ZONE", "SPREAD_ATR"],
            "EXIT_MODE": ["OPPOSITE_CROSS", "FAST_LINE_CROSS", "SPREAD_REVERSAL"],
            "EMA_FAST": [12, 15, 18, 21],
            "SMMA_BASE": [15, 18, 21, 24, 30],
            "MIN_SPREAD_ATR": [0.05, 0.10, 0.15, 0.25],
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty or len(df_spot) < 40:
            df = df_spot.copy()
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            df['Exit_Long'] = False
            df['Exit_Short'] = False
            df['ATR'] = 0.0
            return df

        df = df_spot.copy()
        
        # Ensure proper DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            elif 'Datetime' in df.columns:
                df['Datetime'] = pd.to_datetime(df['Datetime'])
                df.set_index('Datetime', inplace=True)
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            else:
                df.index = pd.to_datetime(df.index)

        tf = str(self.params.get("TIMEFRAME", "1min")).lower()
        atr_period = int(self.params.get("ATR_PERIOD", 14))

        if tf in ["1min", "1m", "1"]:
            # Direct 1-minute execution
            df_res = _run_core_engine(df, self.params)
            
            df['Signal'] = pd.Series(df_res['raw_signal'], index=df.index).shift(1).fillna(0).astype(int)
            df['Exit_Long'] = pd.Series(df_res['raw_exit_long'], index=df.index).shift(1).fillna(False).astype(bool)
            df['Exit_Short'] = pd.Series(df_res['raw_exit_short'], index=df.index).shift(1).fillna(False).astype(bool)
            df['ATR'] = df_res['ATR'].shift(1).fillna(0.0)
        else:
            # Resample day-by-day aligned to session start (e.g. 5min)
            minutes_val = 5
            try:
                minutes_val = int(''.join(filter(str.isdigit, tf))) or 5
            except Exception:
                minutes_val = 5

            df_tf = df.groupby(df.index.date, group_keys=False).apply(
                lambda x: x.resample(tf, origin='start').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last'
                }).dropna()
            )

            df_tf_res = _run_core_engine(df_tf, self.params)
            
            # Map back to 1-minute dataframe with zero lookahead:
            # A 5M candle starting at 09:15 ends at 09:20:00 and is available at 09:20:00
            df_tf_res['avail_time'] = df_tf_res.index + pd.Timedelta(minutes=minutes_val)
            
            df_temp = df.reset_index().rename(columns={'index': 'orig_time', 'timestamp': 'orig_time'})
            merged = pd.merge_asof(
                df_temp.sort_values('orig_time'),
                df_tf_res[['avail_time', 'raw_signal', 'raw_exit_long', 'raw_exit_short', 'ATR']].sort_values('avail_time'),
                left_on='orig_time',
                right_on='avail_time',
                direction='backward'
            ).set_index('orig_time')

            # Ensure each 5-min signal fires once on the exact boundary minute (zero lookahead)
            raw_sig_mapped = np.zeros(len(df), dtype=int)
            raw_exit_l_mapped = np.zeros(len(df), dtype=bool)
            raw_exit_s_mapped = np.zeros(len(df), dtype=bool)

            avail_times_set = set(df_tf_res['avail_time'])
            times_series = df.index

            for i in range(len(df)):
                t = times_series[i]
                if t in avail_times_set:
                    raw_sig_mapped[i] = merged['raw_signal'].iloc[i]
                    raw_exit_l_mapped[i] = merged['raw_exit_long'].iloc[i]
                    raw_exit_s_mapped[i] = merged['raw_exit_short'].iloc[i]

            df['Signal'] = raw_sig_mapped
            df['Exit_Long'] = raw_exit_l_mapped
            df['Exit_Short'] = raw_exit_s_mapped
            df['ATR'] = merged['ATR'].fillna(0.0)

        df['Signal_Source'] = np.where(df['Signal'] == 1, "Strategy_22_CE", 
                                       np.where(df['Signal'] == -1, "Strategy_22_PE", "None"))

        return df
