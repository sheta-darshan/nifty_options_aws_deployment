import pandas as pd
import numpy as np
import pandas_ta as ta

from .base import BaseStrategy
from .registry import register_strategy

def run_cond_ema(x_arr, cond_arr, n):
    res = np.zeros_like(x_arr)
    if len(x_arr) == 0:
        return res
    last_ema = np.nan
    multiplier = 2.0 / (n + 1.0)
    for i in range(len(x_arr)):
        if cond_arr[i]:
            x = x_arr[i]
            if np.isnan(last_ema):
                last_ema = x
            else:
                last_ema = (x - last_ema) * multiplier + last_ema
        res[i] = last_ema if not np.isnan(last_ema) else x_arr[i]
    return res

@register_strategy
class Strategy6(BaseStrategy):
    name = "Strategy_6"

    def get_default_params(self) -> dict:
        return {
            "S6_FILTER_TYPE": "Type 2",         # "Type 1" or "Type 2"
            "S6_MOVEMENT_SOURCE": "Close",       # "Close" or "Wicks"
            "S6_RANGE_SIZE": 3.618,              # Multiplier for range
            "S6_RANGE_SCALE": "Average Change",   # "Points", "Pips", "Ticks", "% of Price", "ATR", "Average Change", "Standard Deviation", "Absolute"
            "S6_RANGE_PERIOD": 14,               # Period for dynamic scales
            "S6_SMOOTH_RANGE": True,             # Smooth range size
            "S6_SMOOTH_PERIOD": 27,              # Smoothing length
            "S6_AVERAGE_CHANGES": False,         # Average changes
            "S6_AVERAGE_SAMPLES": 2,             # Averaging length
            "ATR_PERIOD": 14,                    # Platform exit compatibility
            "ST_LENGTH": 10,
            "ST_MULTIPLIER": 3.0,
        }

    def get_optimization_grid(self) -> dict:
        return {
            "S6_RANGE_SIZE": [1.0, 1.618, 2.618, 3.0],
            "S6_RANGE_PERIOD": [10, 14, 20],
            "S6_SMOOTH_PERIOD": [20, 27, 35],
            "ATR_PERIOD": [14],
            "ST_LENGTH": [7, 10, 14],
            "ST_MULTIPLIER": [2.0, 3.0, 4.0],
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot

        df = df_spot.copy()
        df_rf = df.copy()

        # Minimum required data check
        per = int(self.params.get("S6_RANGE_PERIOD", 14))
        smooth_per = int(self.params.get("S6_SMOOTH_PERIOD", 27))
        req_len = max(100, per, smooth_per)
        
        if len(df_rf) < req_len:
            cols = ['ATR', 'S6_Long_Trend', 'S6_Short_Trend', 'S6_Sig_High', 'S6_Sig_Low', 'S6_Filter', 'SuperTrend', 'SuperTrend_Direction', 'Range_Filter_Direction']
            for col in cols:
                df[col] = np.nan
            df['Signal'] = 0
            df['S6_Signal'] = 0
            df['Signal_Source'] = "None"
            return df

        # Choose High/Low values based on Movement Source
        mov_src = self.params.get("S6_MOVEMENT_SOURCE", "Close")
        if mov_src == "Wicks":
            h_val = df_rf['high']
            l_val = df_rf['low']
        else:
            h_val = df_rf['close']
            l_val = df_rf['close']

        x_val = (h_val + l_val) / 2

        # 1. Compute True Range (TR)
        prev_close = df_rf['close'].shift(1)
        tr = pd.concat([
            df_rf['high'] - df_rf['low'],
            (df_rf['high'] - prev_close).abs(),
            (df_rf['low'] - prev_close).abs()
        ], axis=1).max(axis=1)

        # 2. Compute dynamic scales for range filter
        atr_ema = tr.ewm(span=per, adjust=False).mean()
        ac_ema = x_val.diff().abs().ewm(span=per, adjust=False).mean()
        sd_val = x_val.rolling(window=per).std(ddof=0)

        # Apply Range Scale
        scale = self.params.get("S6_RANGE_SCALE", "Average Change")
        qty = float(self.params.get("S6_RANGE_SIZE", 2.618))

        if scale == "Pips":
            rng = qty * 0.0001
        elif scale == "Points":
            rng = qty * 1.0  # Point value is 1.0 for Nifty
        elif scale == "% of Price":
            rng = df_rf['close'] * qty / 100.0
        elif scale == "ATR":
            rng = qty * atr_ema
        elif scale == "Average Change":
            rng = qty * ac_ema
        elif scale == "Standard Deviation":
            rng = qty * sd_val
        elif scale == "Ticks":
            rng = qty * 0.05  # Min tick size is 0.05 for Nifty/NSE
        else:  # Absolute
            rng = pd.Series(qty, index=df_rf.index)

        # Smooth range size if configured
        smooth = self.params.get("S6_SMOOTH_RANGE", True)
        if smooth:
            r_arr = rng.ewm(span=smooth_per, adjust=False).mean().fillna(0.0).to_numpy()
        else:
            r_arr = rng.fillna(0.0).to_numpy()

        h_arr = h_val.to_numpy()
        l_arr = l_val.to_numpy()
        n_rows = len(df_rf)

        # 3. Two Type Range Filter stateful loop
        rfilt = np.zeros(n_rows, dtype=np.float64)
        rfilt[0] = (h_arr[0] + l_arr[0]) / 2

        f_type = self.params.get("S6_FILTER_TYPE", "Type 1")

        for i in range(1, n_rows):
            prev_filt = rfilt[i-1]
            r_val = r_arr[i]
            hi = h_arr[i]
            lo = l_arr[i]

            if f_type == "Type 1":
                val = prev_filt
                if hi - r_val > prev_filt:
                    val = hi - r_val
                if lo + r_val < prev_filt:
                    val = lo + r_val
                rfilt[i] = val
            else:  # Type 2
                val = prev_filt
                if r_val > 1e-9:
                    if hi >= prev_filt + r_val:
                        val = prev_filt + np.floor(abs(hi - prev_filt) / r_val) * r_val
                    if lo <= prev_filt - r_val:
                        val = prev_filt - np.floor(abs(lo - prev_filt) / r_val) * r_val
                rfilt[i] = val

        hi_band = rfilt + r_arr
        lo_band = rfilt - r_arr

        # Optional averaging based on filter changes
        av_rf = self.params.get("S6_AVERAGE_CHANGES", False)
        av_n = int(self.params.get("S6_AVERAGE_SAMPLES", 2))

        if av_rf:
            cond_arr = np.zeros(n_rows, dtype=bool)
            for i in range(1, n_rows):
                cond_arr[i] = (rfilt[i] != rfilt[i-1])

            rfilt_final = run_cond_ema(rfilt, cond_arr, av_n)
            hi_band_final = run_cond_ema(hi_band, cond_arr, av_n)
            lo_band_final = run_cond_ema(lo_band, cond_arr, av_n)
        else:
            rfilt_final = rfilt
            hi_band_final = hi_band
            lo_band_final = lo_band

        df_rf['S6_Filter'] = rfilt_final
        df_rf['S6_Sig_High'] = hi_band_final
        df_rf['S6_Sig_Low'] = lo_band_final

        # Calculate trend direction (fdir) statefully
        fdir = np.zeros(n_rows, dtype=np.float64)
        fdir[0] = 0.0
        for i in range(1, n_rows):
            if rfilt_final[i] > rfilt_final[i-1]:
                fdir[i] = 1.0
            elif rfilt_final[i] < rfilt_final[i-1]:
                fdir[i] = -1.0
            else:
                fdir[i] = fdir[i-1]

        df_rf['S6_Long_Trend'] = (fdir == 1.0)
        df_rf['S6_Short_Trend'] = (fdir == -1.0)

        # Copy Range Filter columns back to df
        df['S6_Filter'] = df_rf['S6_Filter']
        df['S6_Sig_High'] = df_rf['S6_Sig_High']
        df['S6_Sig_Low'] = df_rf['S6_Sig_Low']
        df['S6_Long_Trend'] = df_rf['S6_Long_Trend']
        df['S6_Short_Trend'] = df_rf['S6_Short_Trend']
        df['Range_Filter_Direction'] = fdir

        # Change 2: Keep ATR exactly like Strategy 9
        df_5min = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        atr_period = int(self.params.get("ATR_PERIOD", 14))
        if len(df_5min) >= atr_period:
            df_5min['ATR'] = ta.atr(
                df_5min['high'],
                df_5min['low'],
                df_5min['close'],
                length=atr_period
            )
            df_5min['ATR'] = df_5min['ATR'].shift(1)
            df = df.drop(columns=['ATR'], errors='ignore')
            df = df.join(df_5min[['ATR']], how='left')
            df['ATR'] = (
                df['ATR']
                .ffill()
                .bfill()
                .fillna(0.0)
            )
        else:
            df['ATR'] = 0.0

        # Change 3: Add SuperTrend
        st = ta.supertrend(
            df['high'],
            df['low'],
            df['close'],
            length=self.params["ST_LENGTH"],
            multiplier=self.params["ST_MULTIPLIER"]
        )
        if st is not None and not st.empty:
            dir_col = [c for c in st.columns if "SUPERTd" in c][0]
            line_col = [c for c in st.columns if "SUPERT_" in c and "SUPERTd" not in c][0]
            df['SuperTrend'] = st[line_col]
            df['SuperTrend_Direction'] = (
                st[dir_col]
                .replace({1: 1, -1: -1})
                .fillna(0)
            )
        else:
            df['SuperTrend'] = np.nan
            df['SuperTrend_Direction'] = 0

        # Change 5: Replace signal generation completely
        buy_armed = False
        sell_armed = False

        signals = np.zeros(len(df), dtype=int)

        rf_dir = df['Range_Filter_Direction'].values
        st_dir = df['SuperTrend_Direction'].values

        for i in range(1, len(df)):
            # RF flips bullish
            if rf_dir[i] == 1 and rf_dir[i - 1] == -1:
                buy_armed = True
                sell_armed = False
            # RF flips bearish
            elif rf_dir[i] == -1 and rf_dir[i - 1] == 1:
                sell_armed = True
                buy_armed = False

            # BUY trigger
            if buy_armed and st_dir[i] == 1:
                signals[i] = 1
                buy_armed = False
            # SELL trigger
            elif sell_armed and st_dir[i] == -1:
                signals[i] = -1
                sell_armed = False

        # Change 6: Final assignment
        df['Signal'] = signals
        df['S6_Signal'] = signals
        df['Signal_Source'] = np.where(
            signals != 0,
            "Strategy 6",
            "None"
        )

        return df