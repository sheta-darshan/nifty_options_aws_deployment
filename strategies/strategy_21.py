"""
Strategy 21: NIFTY Institutional Multi-Pivot Reversal Engine
============================================================
Fuses Dhan custom indicators (Multi-Timeframe Weekly CPR, Daily CPR, Camarilla H3/L3, PDH/PDL)
with causal fractal price-action rejection memory.
Executes ATM option buying (CE on Bullish Reversals, PE on Bearish Reversals).
"""

import os
import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any
from .base import BaseStrategy
from .registry import register_strategy


@register_strategy
class Strategy21(BaseStrategy):
    name = "Strategy_21"

    def get_default_params(self) -> dict:
        return {
            "timeframe": "5min",
            "min_wick_ratio": 0.50,
            "risk_reward": 2.2,
            "min_cpr_width_pct": 0.08,
            "max_daily_trades": 2,
            "sl_buffer_pts": 6.0,
            "min_sl_pts": 15.0,
            "max_sl_pts": 40.0,
            "tolerance_pts": 14.0,
            "entry_start_time": "09:20",
            "entry_end_time": "14:45",
            "leg_mode": "BUY"
        }

    def get_optimization_grid(self) -> dict:
        return {
            "min_wick_ratio": [0.42, 0.45, 0.50],
            "risk_reward": [1.8, 2.0, 2.2, 2.5],
            "min_cpr_width_pct": [0.08, 0.10, 0.12],
            "max_daily_trades": [2, 3],
            "timeframe": ["5min"]
        }

    @staticmethod
    def calculate_daily_pivots(df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes Daily CPR, Camarilla, and PDH/PDL shifted by 1 to prevent lookahead bias.
        """
        daily = df.resample('1D').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        daily = daily[daily['open'] > 0].copy()

        daily['prev_h'] = daily['high'].shift(1)
        daily['prev_l'] = daily['low'].shift(1)
        daily['prev_c'] = daily['close'].shift(1)

        # Daily CPR
        daily['pivot'] = (daily['prev_h'] + daily['prev_l'] + daily['prev_c']) / 3.0
        daily['bc'] = (daily['prev_h'] + daily['prev_l']) / 2.0
        daily['tc'] = (daily['pivot'] - daily['bc']) + daily['pivot']
        daily['cpr_top'] = daily[['tc', 'bc']].max(axis=1)
        daily['cpr_bot'] = daily[['tc', 'bc']].min(axis=1)
        daily['cpr_width_pct'] = (daily['cpr_top'] - daily['cpr_bot']) / daily['pivot'] * 100.0

        # Camarilla H3 / L3
        range_hl = daily['prev_h'] - daily['prev_l']
        daily['cam_h3'] = daily['prev_c'] + range_hl * (1.1 / 4.0)
        daily['cam_l3'] = daily['prev_c'] - range_hl * (1.1 / 4.0)

        # PDH / PDL
        daily['pdh'] = daily['prev_h']
        daily['pdl'] = daily['prev_l']

        return daily.dropna(subset=['pivot'])

    @staticmethod
    def calculate_weekly_pivots(df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes Weekly CPR (Dhan Indicator #16) shifted by 1 week.
        """
        weekly = df.resample('W-FRI').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        weekly = weekly[weekly['open'] > 0].copy()

        weekly['prev_h'] = weekly['high'].shift(1)
        weekly['prev_l'] = weekly['low'].shift(1)
        weekly['prev_c'] = weekly['close'].shift(1)

        weekly['w_pivot'] = (weekly['prev_h'] + weekly['prev_l'] + weekly['prev_c']) / 3.0
        weekly['w_bc'] = (weekly['prev_h'] + weekly['prev_l']) / 2.0
        weekly['w_tc'] = (weekly['w_pivot'] - weekly['w_bc']) + weekly['w_pivot']
        weekly['w_cpr_top'] = weekly[['w_tc', 'w_bc']].max(axis=1)
        weekly['w_cpr_bot'] = weekly[['w_tc', 'w_bc']].min(axis=1)

        return weekly.dropna(subset=['w_pivot'])

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot

        df = df_spot.copy()

        # Handle index
        has_ts_col = 'timestamp' in df.columns
        if has_ts_col and not isinstance(df.index, pd.DatetimeIndex):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        elif not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception:
                pass

        # Parameters
        min_wick_ratio = float(self.params.get("min_wick_ratio", 0.50))
        risk_reward = float(self.params.get("risk_reward", 2.2))
        min_cpr_width_pct = float(self.params.get("min_cpr_width_pct", 0.08))
        max_daily_trades = int(self.params.get("max_daily_trades", 2))
        sl_buffer_pts = float(self.params.get("sl_buffer_pts", 6.0))
        min_sl_pts = float(self.params.get("min_sl_pts", 15.0))
        max_sl_pts = float(self.params.get("max_sl_pts", 40.0))
        tolerance_pts = float(self.params.get("tolerance_pts", 14.0))
        leg_mode = str(self.params.get("leg_mode", "BUY")).upper()

        t_start = datetime.datetime.strptime(self.params.get("entry_start_time", "09:20"), "%H:%M").time()
        t_end = datetime.datetime.strptime(self.params.get("entry_end_time", "14:45"), "%H:%M").time()

        # 1. Compute Daily & Weekly Institutional Pivots
        daily_pivots = self.calculate_daily_pivots(df)
        weekly_pivots = self.calculate_weekly_pivots(df)

        daily_pivot_dict = {}
        for dt_idx, row in daily_pivots.iterrows():
            daily_pivot_dict[dt_idx.date()] = {
                'pivot': row['pivot'],
                'cpr_top': row['cpr_top'],
                'cpr_bot': row['cpr_bot'],
                'cpr_width_pct': row.get('cpr_width_pct', 0.0),
                'cam_h3': row['cam_h3'],
                'cam_l3': row['cam_l3'],
                'pdh': row['pdh'],
                'pdl': row['pdl']
            }

        # 2. Resample to 5-minute candles
        df_5m = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        if len(df_5m) < 10:
            df['Signal'] = 0
            df['Signal_Source'] = ""
            return df

        # Fractal Swings (k=4)
        lookback = 4
        highs = df_5m['high'].values
        lows = df_5m['low'].values
        n_5m = len(df_5m)

        swing_highs = np.zeros(n_5m, dtype=bool)
        swing_lows = np.zeros(n_5m, dtype=bool)
        for i in range(lookback, n_5m - lookback):
            if (highs[i] >= highs[i - lookback:i].max()) and (highs[i] >= highs[i + 1:i + lookback + 1].max()):
                swing_highs[i] = True
            if (lows[i] <= lows[i - lookback:i].min()) and (lows[i] <= lows[i + 1:i + lookback + 1].min()):
                swing_lows[i] = True

        df_5m['swing_high'] = swing_highs
        df_5m['swing_low'] = swing_lows

        # Top institutional level targets
        elite_types = {
            'CAM_L3', 'CAM_L3_CONFLUENCE', 'CPR_PIVOT_CONFLUENCE', 'CAM_H3', 'PDH', 'PDH_CONFLUENCE',
            'PDL_CONFLUENCE', 'CPR_BC', 'CPR_BC_CONFLUENCE',
            'WEEKLY_PIVOT_CONFLUENCE', 'WEEKLY_TC_CONFLUENCE', 'WEEKLY_BC_CONFLUENCE'
        }

        # Dynamic Signal Generation
        signals_5m = np.zeros(n_5m, dtype=int)
        signal_source_5m = [""] * n_5m
        sl_points_5m = np.zeros(n_5m, dtype=float)
        target_points_5m = np.zeros(n_5m, dtype=float)

        dynamic_swings = []
        daily_trades_count = {}

        for i in range(lookback * 2, n_5m - 1):
            curr_time = df_5m.index[i]
            curr_date = curr_time.date()
            curr_tod = curr_time.time()

            o = df_5m['open'].iloc[i]
            h = df_5m['high'].iloc[i]
            l = df_5m['low'].iloc[i]
            c = df_5m['close'].iloc[i]
            candle_range = max(h - l, 1.0)

            # Update confirmed swings
            confirm_idx = i - lookback
            if df_5m['swing_high'].iloc[confirm_idx]:
                dynamic_swings.append(df_5m['high'].iloc[confirm_idx])
            if df_5m['swing_low'].iloc[confirm_idx]:
                dynamic_swings.append(df_5m['low'].iloc[confirm_idx])

            # Timing & Daily limits
            if curr_tod < t_start or curr_tod > t_end:
                continue

            today_trades = daily_trades_count.get(curr_date, 0)
            if today_trades >= max_daily_trades:
                continue

            day_pivots = daily_pivot_dict.get(curr_date, {})
            if min_cpr_width_pct > 0.0:
                if day_pivots.get('cpr_width_pct', 0.0) < min_cpr_width_pct:
                    continue

            # Assemble institutional candidate levels
            candidate_levels = []
            if day_pivots:
                candidate_levels.append(('CPR_PIVOT', day_pivots['pivot']))
                candidate_levels.append(('CPR_TC', day_pivots['cpr_top']))
                candidate_levels.append(('CPR_BC', day_pivots['cpr_bot']))
                candidate_levels.append(('CAM_H3', day_pivots['cam_h3']))
                candidate_levels.append(('CAM_L3', day_pivots['cam_l3']))
                candidate_levels.append(('PDH', day_pivots['pdh']))
                candidate_levels.append(('PDL', day_pivots['pdl']))

            wk_matches = weekly_pivots[weekly_pivots.index <= curr_time]
            if not wk_matches.empty:
                last_wk = wk_matches.iloc[-1]
                candidate_levels.append(('WEEKLY_PIVOT', last_wk['w_pivot']))
                candidate_levels.append(('WEEKLY_TC', last_wk['w_cpr_top']))
                candidate_levels.append(('WEEKLY_BC', last_wk['w_cpr_bot']))

            lower_wick = min(o, c) - l
            upper_wick = h - max(o, c)
            lower_wick_ratio = lower_wick / candle_range
            upper_wick_ratio = upper_wick / candle_range

            next_open = df_5m['open'].iloc[i + 1]

            # Signal 1: Bullish Reversal (Call Buying)
            if lower_wick_ratio >= min_wick_ratio and c >= (l + candle_range * 0.40):
                matched_level = None
                matched_type = None

                for lvl_type, lvl_price in candidate_levels:
                    if abs(l - lvl_price) <= tolerance_pts or (l <= lvl_price and c >= lvl_price):
                        has_conf = any(
                            abs(lvl_price - other_p) <= tolerance_pts and other_t != lvl_type
                            for other_t, other_p in candidate_levels
                        )
                        if not has_conf and len(dynamic_swings) > 0:
                            has_conf = np.any(np.abs(np.array(dynamic_swings[-20:]) - lvl_price) <= tolerance_pts)

                        cand_type = f"{lvl_type}_CONFLUENCE" if has_conf else lvl_type
                        if cand_type in elite_types:
                            matched_level = lvl_price
                            matched_type = cand_type
                            break

                if matched_level is not None:
                    sl_dist = max(next_open - (l - sl_buffer_pts), min_sl_pts)
                    sl_dist = min(sl_dist, max_sl_pts)
                    target_dist = sl_dist * risk_reward

                    # Trigger on candle i+1 open
                    signals_5m[i + 1] = 1
                    signal_source_5m[i + 1] = f"Strategy_21 ({matched_type} Bullish Reversal)"
                    sl_points_5m[i + 1] = sl_dist
                    target_points_5m[i + 1] = target_dist
                    daily_trades_count[curr_date] = today_trades + 1
                    continue

            # Signal 2: Bearish Reversal (Put Buying)
            if upper_wick_ratio >= min_wick_ratio and c <= (h - candle_range * 0.40):
                matched_level = None
                matched_type = None

                for lvl_type, lvl_price in candidate_levels:
                    if abs(h - lvl_price) <= tolerance_pts or (h >= lvl_price and c <= lvl_price):
                        has_conf = any(
                            abs(lvl_price - other_p) <= tolerance_pts and other_t != lvl_type
                            for other_t, other_p in candidate_levels
                        )
                        if not has_conf and len(dynamic_swings) > 0:
                            has_conf = np.any(np.abs(np.array(dynamic_swings[-20:]) - lvl_price) <= tolerance_pts)

                        cand_type = f"{lvl_type}_CONFLUENCE" if has_conf else lvl_type
                        if cand_type in elite_types:
                            matched_level = lvl_price
                            matched_type = cand_type
                            break

                if matched_level is not None:
                    sl_dist = max((h + sl_buffer_pts) - next_open, min_sl_pts)
                    sl_dist = min(sl_dist, max_sl_pts)
                    target_dist = sl_dist * risk_reward

                    signals_5m[i + 1] = -1
                    signal_source_5m[i + 1] = f"Strategy_21 ({matched_type} Bearish Reversal)"
                    sl_points_5m[i + 1] = sl_dist
                    target_points_5m[i + 1] = target_dist
                    daily_trades_count[curr_date] = today_trades + 1
                    continue

        df_5m['Signal'] = signals_5m
        df_5m['Signal_Source'] = signal_source_5m
        df_5m['SL_Points'] = sl_points_5m
        df_5m['Target_Points'] = target_points_5m

        # Join to 1-minute execution dataframe
        df['Signal'] = 0
        df['signal'] = 0
        df['Signal_Source'] = ""
        df['SL_Points'] = 0.0
        df['Target_Points'] = 0.0
        df['option_action'] = ""

        # Map 5-min signals directly to exact 1-min timestamps
        valid_signals = df_5m[df_5m['Signal'] != 0]
        for ts, s_row in valid_signals.iterrows():
            if ts in df.index:
                sig_val = int(s_row['Signal'])
                df.loc[ts, 'Signal'] = sig_val
                df.loc[ts, 'signal'] = sig_val
                df.loc[ts, 'Signal_Source'] = s_row['Signal_Source']
                df.loc[ts, 'SL_Points'] = s_row['SL_Points']
                df.loc[ts, 'Target_Points'] = s_row['Target_Points']

                if sig_val == 1:
                    df.loc[ts, 'option_action'] = "BUY_CE" if leg_mode == "BUY" else "SELL_PE"
                elif sig_val == -1:
                    df.loc[ts, 'option_action'] = "BUY_PE" if leg_mode == "BUY" else "SELL_CE"

        if has_ts_col and 'timestamp' not in df.columns:
            df = df.reset_index()

        return df

    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.generate_signals(df)


def get_strategy_instance(params: Dict[str, Any] = None):
    return Strategy21(params)
