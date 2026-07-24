import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
except ImportError:
    ta = None

class BaseStrategy:
    name: str = "Base"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'generate_signals') and cls.generate_signals != BaseStrategy.generate_signals:
            orig_gen = cls.generate_signals
            def wrapped(self, df_spot):
                df = orig_gen(self, df_spot)
                return self.apply_regime_filter(df)
            cls.generate_signals = wrapped

    def __init__(self, params: dict = None):
        self.params = self.get_default_params()
        if params:
            for k, v in params.items():
                if k in self.params:
                    # Safeguard: if default value is an int (and not bool), cast override to int to prevent Pandas float rolling issues
                    if isinstance(self.params[k], int) and not isinstance(self.params[k], bool):
                        try:
                            # Use round first to handle potential float representations cleanly (like 14.0)
                            self.params[k] = int(round(float(v)))
                        except (ValueError, TypeError):
                            self.params[k] = v
                    else:
                        self.params[k] = v
                elif k in ["allowed_regimes_trend", "allowed_regimes_vol"]:
                    self.params[k] = v

    def get_default_params(self) -> dict:
        """Return default parameter configuration."""
        return {}

    def get_optimization_grid(self) -> dict:
        """Return parameter search space grids for optimization."""
        return {}

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        """
        Vectorized signal generation. 
        Must append 'Signal' and 'Signal_Source' columns to df_spot.
        """
        raise NotImplementedError

    def apply_regime_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        allowed_trend = self.params.get("allowed_regimes_trend")
        allowed_vol = self.params.get("allowed_regimes_vol")
        
        # If neither filter is defined, bypass immediately
        if not allowed_trend and not allowed_vol:
            return df
            
        # Standardize allowed lists
        if allowed_trend is not None:
            if isinstance(allowed_trend, str):
                allowed_trend = [t.strip().upper() for t in allowed_trend.split(",")]
            else:
                allowed_trend = [str(t).strip().upper() for t in allowed_trend]
                
        if allowed_vol is not None:
            if isinstance(allowed_vol, str):
                allowed_vol = [v.strip().upper() for v in allowed_vol.split(",")]
            else:
                allowed_vol = [str(v).strip().upper() for v in allowed_vol]

        # 1. Trend Regime Filter (ADX)
        if allowed_trend:
            adx_col = None
            for col in ['TM_ADX', 'ADX', 'ADX_14']:
                if col in df.columns:
                    adx_col = col
                    break
                    
            if adx_col is None and ta is not None:
                # Calculate 5-minute ADX if not present
                try:
                    df_5min = df.resample('5min').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last'
                    }).dropna()
                    adx_df = ta.adx(df_5min['high'], df_5min['low'], df_5min['close'], length=14)
                    if adx_df is not None:
                        df_5min['ADX_14'] = adx_df['ADX_14'].shift(1) # shift to avoid lookahead
                        df = df.join(df_5min[['ADX_14']], how='left')
                        df['ADX_14'] = df['ADX_14'].ffill().fillna(20.0)
                        adx_col = 'ADX_14'
                except Exception as e:
                    print(f"[WARNING] Failed to calculate ADX for regime filter: {e}")
                    
            if adx_col is not None:
                # Compute trend regime series
                adx_series = df[adx_col].fillna(20.0)
                # "TREND" if adx > 25 else ("RANGE" if adx < 20 else "NEUTRAL")
                regime_series = np.where(adx_series > 25.0, "TREND", 
                                         np.where(adx_series < 20.0, "RANGE", "NEUTRAL"))
                
                # Check if regime matches allowed_trend
                trend_mask = np.isin(regime_series, allowed_trend)
                # Nullify signals where trend regime is not allowed
                df.loc[~trend_mask, 'Signal'] = 0
                df.loc[~trend_mask, 'Signal_Source'] = "None"

        # 2. Volatility Regime Filter (ATR% / Median ATR%)
        if allowed_vol:
            atr_col = None
            for col in ['ATR', 'ATR_14']:
                if col in df.columns:
                    atr_col = col
                    break
                    
            if atr_col is None and ta is not None:
                # Calculate 5-minute ATR if not present
                try:
                    df_5min = df.resample('5min').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last'
                    }).dropna()
                    atr_df = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=14)
                    if atr_df is not None:
                        df_5min['ATR_14'] = atr_df.shift(1) # shift to avoid lookahead
                        df = df.join(df_5min[['ATR_14']], how='left')
                        df['ATR_14'] = df['ATR_14'].ffill().fillna(0.0)
                        atr_col = 'ATR_14'
                except Exception as e:
                    print(f"[WARNING] Failed to calculate ATR for regime filter: {e}")
                    
            if atr_col is not None:
                # Calculate median atr% from df
                non_zero = df[df['close'] > 0]
                if not non_zero.empty:
                    atr_pct_series = (df[atr_col] / df['close']) * 100
                    non_zero_atr_pct = (non_zero[atr_col] / non_zero['close']) * 100
                    median_val = float(non_zero_atr_pct.median())
                else:
                    atr_pct_series = pd.Series(0.0, index=df.index)
                    median_val = 0.0
                    
                regime_series = np.where(atr_pct_series > median_val, "HIGH_VIX", "LOW_VIX")
                
                # Check if regime matches allowed_vol
                vol_mask = np.isin(regime_series, allowed_vol)
                # Nullify signals where vol regime is not allowed
                df.loc[~vol_mask, 'Signal'] = 0
                df.loc[~vol_mask, 'Signal_Source'] = "None"

        return df
