"""
strategies/strategy_23.py

Strategy 23: Stealth Absorption Multi-Day Swing Engine (S-AMS)
=============================================================
Identifies early institutional volume absorption during the opening 10 minutes (09:15 - 09:25)
where relative volume is abnormally high (RVOL >= 1.5x) but price range is compressed (<= 0.8%).
When price breaks out past the opening 10m box high between 09:25 and 11:00 AM, the strategy
enters a Multi-Day Cash Delivery (CNC) position.

Exit Architecture:
  - Initial Stop Loss: Opposite side of the 10-minute box (Box Low)
  - Breakeven Guard: Once stock gains +2.5%, Stop Loss moves to Entry (Zero Risk)
  - Trailing Trend Runner: Once stock gains +4.0%, Stop Loss trails 2.0% behind the highest peak
  - Time Stop: Maximum hold of 10 trading days
  - Lookahead Guard: All indicators and opening box statistics use shift(1) completed bars
"""

import os
import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any

from .base import BaseStrategy
from .registry import register_strategy

_NIFTY_DAILY_RETURNS = None

def _get_nifty_daily_returns():
    global _NIFTY_DAILY_RETURNS
    if _NIFTY_DAILY_RETURNS is not None:
        return _NIFTY_DAILY_RETURNS
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        nifty_path = os.path.join(base_dir, "backtest_data", "nifty_spot.csv")
        if os.path.exists(nifty_path):
            df_n = pd.read_csv(nifty_path, usecols=['timestamp', 'close'])
            df_n['dt'] = pd.to_datetime(df_n['timestamp'])
            df_n['date'] = df_n['dt'].dt.date
            n_daily = df_n.groupby('date')['close'].last()
            n_ret20 = (n_daily.shift(1) - n_daily.shift(21)) / n_daily.shift(21)
            _NIFTY_DAILY_RETURNS = pd.DataFrame({'nifty_ret20': n_ret20})
            return _NIFTY_DAILY_RETURNS
    except Exception:
        pass
    return None

@register_strategy
class Strategy23(BaseStrategy):
    name = "Strategy_23"

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "RVOL_THRESHOLD": 1.5,
            "MAX_BOX_RANGE_PCT": 0.80,
            "BOX_START_TIME": "09:15",
            "BOX_END_TIME": "09:24",
            "TRIGGER_CUTOFF_TIME": "11:00",
            "EOD_TIME": "15:15",
            "BREAKEVEN_PCT": 0.025,       # +2.5% move triggers breakeven
            "TRAIL_ACTIVATION_PCT": 0.040, # +4.0% move activates trailing
            "TRAIL_DISTANCE_PCT": 0.020,   # Trail 2.0% behind peak
            "MAX_HOLD_DAYS": 10,
            "MIN_RISK_PCT": 0.001,         # Avoid division by zero
            "USE_MACRO_TREND_FILTER": True, # Stock must be above 200-day SMA
            "USE_RS_FILTER": True           # Stock 20-day return must outperform NIFTY
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot is None or len(df_spot) < 100:
            df = df_spot.copy() if df_spot is not None else pd.DataFrame()
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df

        df = df_spot.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            else:
                df.index = pd.to_datetime(df.index)

        df.sort_index(inplace=True)

        rvol_min = self.params.get("RVOL_THRESHOLD", 1.5)
        max_range_pct = self.params.get("MAX_BOX_RANGE_PCT", 0.80)
        box_start_time = pd.to_datetime(self.params.get("BOX_START_TIME", "09:15")).time()
        box_end_time = pd.to_datetime(self.params.get("BOX_END_TIME", "09:24")).time()
        trigger_cutoff = pd.to_datetime(self.params.get("TRIGGER_CUTOFF_TIME", "11:00")).time()
        use_macro = self.params.get("USE_MACRO_TREND_FILTER", True)
        use_rs = self.params.get("USE_RS_FILTER", True)

        df['time'] = df.index.time
        df['date'] = df.index.date

        # 1. Compute Daily 10-Minute Opening Box Stats & Daily Closes
        grouped = df.groupby('date')
        dates = list(grouped.groups.keys())

        opening_stats = []
        for d in dates:
            day_df = grouped.get_group(d)
            open_box = day_df[(day_df['time'] >= box_start_time) & (day_df['time'] <= box_end_time)]
            if len(open_box) >= 7:
                o_px = open_box['open'].iloc[0]
                h_10 = open_box['high'].max()
                l_10 = open_box['low'].min()
                c_day = day_df['close'].iloc[-1]
                v_sum = open_box['volume'].sum() if 'volume' in open_box.columns else 1.0
                opening_stats.append({
                    'date': d,
                    'box_open': o_px,
                    'box_high': h_10,
                    'box_low': l_10,
                    'day_close': c_day,
                    'box_vol': v_sum
                })

        if len(opening_stats) < 15:
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df

        df_open = pd.DataFrame(opening_stats).set_index('date')
        # 20-day rolling average opening volume shifted by 1 to strictly prevent look-ahead bias
        df_open['vol_20_avg'] = df_open['box_vol'].rolling(20, min_periods=5).mean().shift(1)
        df_open['rvol'] = df_open['box_vol'] / df_open['vol_20_avg']
        df_open['box_range_pct'] = ((df_open['box_high'] - df_open['box_low']) / df_open['box_open']) * 100.0

        # Macro 200 SMA Gate: Shifted by 1
        df_open['sma_200'] = df_open['day_close'].rolling(200, min_periods=30).mean().shift(1)
        df_open['is_uptrend'] = df_open['box_open'] >= df_open['sma_200'].fillna(0.0)

        # Relative Strength Gate vs NIFTY 50: Shifted by 1
        df_open['rs_positive'] = True
        if use_rs:
            nifty_daily = _get_nifty_daily_returns()
            if nifty_daily is not None:
                df_open['stk_ret20'] = (df_open['day_close'].shift(1) - df_open['day_close'].shift(21)) / df_open['day_close'].shift(21)
                df_open = df_open.join(nifty_daily, how='left')
                if 'nifty_ret20' in df_open.columns:
                    df_open['rs_positive'] = df_open['stk_ret20'].fillna(0.0) >= df_open['nifty_ret20'].fillna(0.0)

        # Map daily opening stats back onto 1-minute dataframe
        cols_to_join = ['box_high', 'box_low', 'rvol', 'box_range_pct', 'is_uptrend', 'rs_positive']
        df = df.join(df_open[cols_to_join], on='date', how='left')

        # 2. Setup Conditions (Absorption Filter + Macro Regime Gate + Relative Strength Gate)
        cond = (df['rvol'] >= rvol_min) & (df['box_range_pct'] <= max_range_pct)
        if use_macro:
            cond = cond & (df['is_uptrend'] == True)
        if use_rs:
            cond = cond & (df['rs_positive'] == True)

        is_stealth_setup = cond
        in_trigger_window = (df['time'] > box_end_time) & (df['time'] <= trigger_cutoff)

        # Breakout Trigger: Current high crosses above box high
        breakout_trigger = is_stealth_setup & in_trigger_window & (df['high'] > df['box_high'])

        # Initialize Signal and Execution metadata columns
        df['Signal'] = 0
        df['Strat23_Signal'] = 0
        df['Signal_Source'] = "None"
        df['Conviction'] = 1.0

        # Stop loss and targets
        df['Strat23_SL'] = df['box_low']
        df['Strat23_BE_Target'] = df['box_high'] * (1.0 + self.params.get("BREAKEVEN_PCT", 0.025))
        df['Strat23_Trail_Trigger'] = df['box_high'] * (1.0 + self.params.get("TRAIL_ACTIVATION_PCT", 0.040))
        df['Strat23_Trail_Dist'] = self.params.get("TRAIL_DISTANCE_PCT", 0.020)
        df['Strat23_Max_Hold'] = self.params.get("MAX_HOLD_DAYS", 10)

        # 3. Prevent multiple duplicate triggers on the same date
        # Only the first bar of the day that breaks out triggers an entry
        df['is_breakout'] = breakout_trigger.astype(int)
        df['cum_breakout_day'] = df.groupby('date')['is_breakout'].cumsum()
        first_breakout_mask = (df['is_breakout'] == 1) & (df['cum_breakout_day'] == 1)

        df.loc[first_breakout_mask, 'Signal'] = 1
        df.loc[first_breakout_mask, 'Strat23_Signal'] = 1
        df.loc[first_breakout_mask, 'Signal_Source'] = "Strategy 23 (Stealth Swing)"

        # High Conviction boost when RVOL >= 2.5 (Massive Block Accumulation)
        ultra_vol_mask = first_breakout_mask & (df['rvol'] >= 2.5)
        df.loc[ultra_vol_mask, 'Conviction'] = 2.0

        # Clean up temporary columns
        df.drop(columns=['is_breakout', 'cum_breakout_day', 'time', 'date'], inplace=True, errors='ignore')

        return df
