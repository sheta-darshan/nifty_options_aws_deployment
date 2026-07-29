import os
import pickle
import datetime
import pandas as pd
import numpy as np
import pandas_ta as ta
from .base import BaseStrategy
from .registry import register_strategy

_QUANT_MODEL_CACHE = None

def _load_quant_model():
    global _QUANT_MODEL_CACHE
    if _QUANT_MODEL_CACHE is not None:
        return _QUANT_MODEL_CACHE
        
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "nifty_quant_xgb.pkl")
    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                _QUANT_MODEL_CACHE = pickle.load(f)
            return _QUANT_MODEL_CACHE
        except Exception as e:
            print(f"[WARNING] Failed to load Quant ML model from {model_path}: {e}")
    return None

@register_strategy
class Strategy19(BaseStrategy):
    name = "Strategy_19"

    def get_default_params(self) -> dict:
        return {
            "rsi_length": 9,
            "ema_length": 3,
            "wma_length": 21,
            "adx_length": 14,
            "min_ml_prob": 0.42,  # Minimum confidence threshold (42%)
            "timeframe": "5min",
            "entry_start_time": "09:20",
            "entry_end_time": "14:45"
        }

    def get_optimization_grid(self) -> dict:
        return {
            "rsi_length": [9],
            "ema_length": [3],
            "wma_length": [21],
            "adx_length": [14],
            "min_ml_prob": [0.38, 0.40, 0.42, 0.45],
            "timeframe": ["5min"]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # Parse timing
        try:
            start_str = self.params.get("entry_start_time", "09:20")
            end_str = self.params.get("entry_end_time", "14:45")
            t_start = datetime.datetime.strptime(start_str, "%H:%M").time()
            t_end = datetime.datetime.strptime(end_str, "%H:%M").time()
        except Exception:
            t_start = datetime.time(9, 20)
            t_end = datetime.time(14, 45)
            
        # 1. Noise Reduction: Mean price calculation
        df['mean_price'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4.0

        # 2. Resample to 5-min
        tf = self.params.get("timeframe", "5min")
        df_tf = df.groupby(df.index.date, group_keys=False).apply(
            lambda x: x.resample(tf, origin='start').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'mean_price': 'mean',
                'volume': 'sum'
            })
        ).dropna()

        if len(df_tf) < 30:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df

        # Technical Indicators on Mean Price
        df_tf['rsi'] = ta.rsi(df_tf['mean_price'], length=self.params["rsi_length"])
        df_tf['fast_ema'] = ta.ema(df_tf['rsi'], length=self.params["ema_length"])
        df_tf['slow_wma'] = ta.wma(df_tf['rsi'], length=self.params["wma_length"])
        df_tf['rsi_slope'] = df_tf['rsi'] - df_tf['rsi'].shift(2)
        df_tf['wma_diff'] = df_tf['fast_ema'] - df_tf['slow_wma']

        adx_df = ta.adx(high=df_tf['high'], low=df_tf['low'], close=df_tf['close'], length=self.params["adx_length"])
        if adx_df is not None and not adx_df.empty:
            df_tf['adx'] = adx_df[f'ADX_{self.params["adx_length"]}']
            df_tf['dmp'] = adx_df[f'DMP_{self.params["adx_length"]}']
            df_tf['dmn'] = adx_df[f'DMN_{self.params["adx_length"]}']
        else:
            df_tf['adx'] = 20.0
            df_tf['dmp'] = 10.0
            df_tf['dmn'] = 10.0

        df_tf['atr'] = ta.atr(high=df_tf['high'], low=df_tf['low'], close=df_tf['close'], length=14)
        df_tf['rel_atr'] = df_tf['atr'] / df_tf['close']

        if 'volume' in df_tf.columns and df_tf['volume'].sum() > 0:
            df_tf['vwap'] = ta.vwap(high=df_tf['high'], low=df_tf['low'], close=df_tf['close'], volume=df_tf['volume'])
            df_tf['vwap_dist'] = (df_tf['close'] - df_tf['vwap']) / df_tf['vwap']
        else:
            df_tf['vwap_dist'] = 0.0

        # Daily Gap & C1 Range
        day_starts = pd.Series(df_tf.index.date, index=df_tf.index).shift(1) != df_tf.index.date
        prev_close = df_tf['close'].shift(1).where(day_starts).ffill()
        df_tf['gap_pct'] = ((df_tf['open'] - prev_close) / prev_close).fillna(0.0)

        c1_range_series = (df_tf['high'] - df_tf['low']).where(day_starts).groupby(df_tf.index.date).transform('first')
        df_tf['c1_range_ratio'] = (c1_range_series / df_tf['open']).fillna(0.0)

        df_tf['minute_of_day'] = df_tf.index.hour * 60 + df_tf.index.minute
        df_tf['day_of_week'] = df_tf.index.dayofweek

        # 3. Model Inference
        model_pack = _load_quant_model()
        df_tf['ml_prob_bullish'] = 0.0
        df_tf['ml_prob_bearish'] = 0.0

        if model_pack is not None:
            model = model_pack["model"]
            feat_cols = model_pack["feature_cols"]
            
            # Fill NAs for feature prediction
            X_infer = df_tf[feat_cols].ffill().bfill().fillna(0)
            try:
                probs = model.predict_proba(X_infer) # Returns probabilities for classes [0, 1, 2]
                if probs.shape[1] == 3:
                    df_tf['ml_prob_bullish'] = probs[:, 1]
                    df_tf['ml_prob_bearish'] = probs[:, 2]
            except Exception as e:
                pass

        # 4. Trigger Signals
        min_prob = float(self.params.get("min_ml_prob", 0.42))
        
        # Rule: Hilega Milega Cross + High ML Confidence
        cross_buy = (df_tf['fast_ema'].shift(1) <= df_tf['slow_wma'].shift(1)) & (df_tf['fast_ema'] > df_tf['slow_wma'])
        cross_sell = (df_tf['fast_ema'].shift(1) >= df_tf['slow_wma'].shift(1)) & (df_tf['fast_ema'] < df_tf['slow_wma'])
        
        df_tf['long_trigger'] = cross_buy & (df_tf['ml_prob_bullish'] >= min_prob)
        df_tf['short_trigger'] = cross_sell & (df_tf['ml_prob_bearish'] >= min_prob)

        # 5. Shift & Join back to 1-min
        cols_to_shift = ['long_trigger', 'short_trigger', 'ml_prob_bullish', 'ml_prob_bearish']
        df_tf[cols_to_shift] = df_tf[cols_to_shift].shift(1)

        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns], errors='ignore')
        df = df.join(df_tf[cols_to_shift], how='left')
        df[cols_to_shift] = df[cols_to_shift].ffill()

        df['long_trigger'] = df['long_trigger'].fillna(False).astype(bool)
        df['short_trigger'] = df['short_trigger'].fillna(False).astype(bool)

        df['Signal'] = 0
        df['Signal_Source'] = "None"

        df_time = df.index.time
        time_cond = (df_time >= t_start) & (df_time <= t_end)

        buy_cond = df['long_trigger'] & time_cond
        sell_cond = df['short_trigger'] & time_cond

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[buy_cond, 'Signal_Source'] = "Quant ML Long"

        df.loc[sell_cond, 'Signal'] = -1
        df.loc[sell_cond, 'Signal_Source'] = "Quant ML Short"

        df.drop(columns=['mean_price', 'long_trigger', 'short_trigger'], inplace=True, errors='ignore')
        return df
