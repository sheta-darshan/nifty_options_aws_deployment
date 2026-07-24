import pandas as pd
import numpy as np
import pandas_ta as ta

from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy8(BaseStrategy):
    name = "Strategy_8"

    def get_default_params(self) -> dict:
        return {
            "S8_SIGNAL_VAL": 1,  # 1 for BUY CE / LONG, -1 for BUY PE / SHORT
            "ATR_PERIOD": 14,
        }

    def get_optimization_grid(self) -> dict:
        return {
            "S8_SIGNAL_VAL": [1, -1],
            "ATR_PERIOD": [14]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot

        df = df_spot.copy()

        # Calculate standard 14 ATR column on spot data to prevent engine warnings
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=int(self.params.get("ATR_PERIOD", 14))).fillna(0.0)

        # Set default values for other TM/Strategy columns expected by logging/engine
        df['TM_Sig_High'] = np.nan
        df['TM_Sig_Low'] = np.nan
        df['TM_Long_Trend'] = False
        df['TM_Short_Trend'] = False
        df['TM_ADX'] = np.nan
        df['Signal'] = 0
        df['Signal_Source'] = "None"

        # Generate a signal exactly at 09:30 AM on every trading day
        is_930 = (df.index.hour == 9) & (df.index.minute == 30)
        
        sig_val = int(self.params.get("S8_SIGNAL_VAL", 1))
        df.loc[is_930, 'Signal'] = sig_val
        df['Signal_Source'] = np.where(df['Signal'] != 0, "Strategy 8", "None")

        return df
