"""
stock_selection/constants.py
==========================================================================================
CENTRALIZED TIME WINDOWS & FEATURE EXTRACTION CONSTANTS
==========================================================================================
Provides unified time window definitions and helper functions for feature extraction across
training (preprocess.py) and live/inference (select_stocks.py, select_joint.py) to eliminate
train/serve skew.
==========================================================================================
"""

from datetime import date, time as dt_time

# Cutoff date where intraday spot data feed switched from 15:30 close (last bar 15:29)
# to 15:15 close (last bar 15:14).
MARKET_TIMING_CHANGE_DATE = date(2026, 8, 3)

# 30-minute feature extraction window prior to August 3, 2026 (Standard 15:30 close)
PRE_CHANGE_WINDOW_START = "15:00"
PRE_CHANGE_WINDOW_END = "15:29"

# 30-minute feature extraction window on/after August 3, 2026 (15:15 close)
POST_CHANGE_WINDOW_START = "14:45"
POST_CHANGE_WINDOW_END = "15:14"

# Minimum completed candles required in the 30-minute window to avoid incomplete data
MIN_WINDOW_CANDLES = 25


def get_last_30m_window(day_df, target_date):
    """
    Extracts the final 30-minute trading window of day T dynamically.

    Rationale:
    - On/after 2026-08-03: The Dhan spot intraday feed concludes at 15:15 (last candle 15:14).
      The last 30 minutes of the session is 14:45 to 15:14.
    - Prior to 2026-08-03: The standard session concluded at 15:30 (last candle 15:29).
      If candles up to 15:25+ exist, the last 30 minutes is 15:00 to 15:29; otherwise falls
      back to 14:45 to 15:14 if later afternoon bars were incomplete.
    """
    if target_date >= MARKET_TIMING_CHANGE_DATE:
        return day_df.between_time(POST_CHANGE_WINDOW_START, POST_CHANGE_WINDOW_END)
    else:
        max_time = day_df.index.max().time() if not day_df.empty else None
        if max_time and max_time >= dt_time(15, 25):
            return day_df.between_time(PRE_CHANGE_WINDOW_START, PRE_CHANGE_WINDOW_END)
        else:
            return day_df.between_time(POST_CHANGE_WINDOW_START, POST_CHANGE_WINDOW_END)
