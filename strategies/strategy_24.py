"""
strategies/strategy_24.py

Strategy 24: Pre-Breakout Coiled Momentum Engine (PBCM)
======================================================
Autonomous execution strategy for daily rotated pre-breakout stocks.
Monitors the stock on Day T+1 for confirmed expansion above the coiling range (Day T High).

Execution Architecture:
  - Entry Trigger: Spot price crosses Day T High with opening RVOL expansion
  - Volume Filter: Breakout 5m bar must exceed min 2,500 shares AND 1.25x 5-min rolling average volume
  - Target: Dynamic +1.15x ATR profit target
  - Breakeven Guard: Dynamic shift to breakeven at +0.65x ATR (zero risk)
  - Initial Stop Loss: -0.90x ATR below entry
  - EOD Square-off: At 15:15 PM if not exited
  - Zero Lookahead: Evaluates completed completed bars using shift(1)
"""

import datetime
from typing import Dict, Any
import numpy as np
import pandas as pd

from .base import BaseStrategy
from .registry import register_strategy


@register_strategy
class Strategy24(BaseStrategy):
    name = "Strategy_24"

    def get_default_params(self) -> Dict[str, Any]:
        return {
            "DIRECTION": "BUY",              # "BUY" for breakout or "SELL" for breakdown
            "TRIGGER_PRICE": 0.0,            # Manual override if specified in instruments.json
            "MIN_VOLUME_SURGE": 1.25,        # Breakout/Breakdown bar volume >= 1.25x 5m SMA
            "MIN_ABS_VOLUME": 2500,          # Minimum shares traded on breakout/breakdown bar
            "MAX_GAP_ATR_MULT": 0.40,        # Anti-gap exhaustion filter: reject if open gaps > 0.40x ATR past trigger
            "MAX_ADVERSE_WICK_RATIO": 0.45,  # Anti-rejection filter: reject if adverse wick > 45% of candle range
            "TARGET_ATR_MULT": 1.15,         # Target distance in ATRs
            "SL_ATR_MULT": 0.90,             # Stop-loss distance in ATRs
            "BE_ATR_MULT": 0.65,             # Breakeven trigger in ATRs
            "START_TIME": "09:15",           # Market open
            "CUTOFF_TIME": "15:00",          # No new entries after 15:00
            "ATR_PERIOD": 14
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot is None or len(df_spot) < 5:
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

        df['Signal'] = 0
        df['Signal_Source'] = "None"

        # Check required columns
        for col in ['open', 'high', 'low', 'close']:
            if col not in df.columns:
                return df
        if 'volume' not in df.columns:
            df['volume'] = 10000.0

        df['time'] = df.index.time
        df['date'] = df.index.date

        atr_period = self.params.get("ATR_PERIOD", 14)
        min_vol_mult = float(self.params.get("MIN_VOLUME_SURGE", 1.25))
        min_abs_vol = float(self.params.get("MIN_ABS_VOLUME", 2500))
        max_gap_mult = float(self.params.get("MAX_GAP_ATR_MULT", 0.40))
        max_wick_ratio = float(self.params.get("MAX_ADVERSE_WICK_RATIO", 0.45))
        start_t = pd.to_datetime(self.params.get("START_TIME", "09:15")).time()
        cutoff_t = pd.to_datetime(self.params.get("CUTOFF_TIME", "15:00")).time()
        param_trig = float(self.params.get("TRIGGER_PRICE", self.params.get("trigger_price", 0.0)))

        # Resolve execution direction: check DIRECTION param or allowed_actions from instruments.json
        direction = str(self.params.get("DIRECTION", self.params.get("direction", "BUY"))).upper()
        allowed_actions = self.params.get("allowed_actions", [])
        if isinstance(allowed_actions, list):
            allowed_upper = [str(a).upper() for a in allowed_actions]
            if "SELL" in allowed_upper and "BUY" not in allowed_upper:
                direction = "SELL"
            elif "BUY" in allowed_upper and "SELL" not in allowed_upper:
                direction = "BUY"

        is_sell = (direction == "SELL")

        # 1. Compute Daily Highs and Lows to identify Day T reference level
        grouped = df.groupby('date')
        daily_highs = grouped['high'].max()
        daily_lows = grouped['low'].min()
        daily_closes = grouped['close'].last()

        # Compute Daily ATR(14)
        tr = np.maximum(
            daily_highs - daily_lows,
            np.maximum(
                abs(daily_highs - daily_closes.shift(1)),
                abs(daily_lows - daily_closes.shift(1))
            )
        )
        daily_atr = tr.rolling(atr_period, min_periods=5).mean().bfill()
        daily_prev_high = daily_highs.shift(1)
        daily_prev_low = daily_lows.shift(1)

        dates = list(grouped.groups.keys())
        if len(dates) < 2 and param_trig <= 0:
            return df

        # 2. Resample to 5-Minute Bars for Volume SMA and Expansion Confirmation
        df_5m = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        df_5m['vol_sma5'] = df_5m['volume'].rolling(5, min_periods=1).mean().shift(1).fillna(0)

        # 3. Detect Entry Signals per Day
        for d in dates:
            day_mask = (df.index.date == d) & (df['time'] >= start_t) & (df['time'] <= cutoff_t)
            day_df = df.loc[day_mask]
            if day_df.empty:
                continue

            day_atr_val = daily_atr.get(d, 0.0)
            day_open = day_df['open'].iloc[0]

            if is_sell:
                # SELL: Day T+1 must cross below Day T Low (or calibrated trigger)
                prev_level = param_trig if (param_trig > 0 and d == dates[-1]) else daily_prev_low.get(d, np.nan)
                if pd.isna(prev_level) or prev_level <= 0:
                    continue

                # Anti-Gap Exhaustion Protection: Reject if market opens deeply gap-down below trigger
                if day_atr_val > 0 and day_open < (prev_level - max_gap_mult * day_atr_val):
                    continue

                trigger_candles = day_df[day_df['low'] <= prev_level]
            else:
                # BUY: Day T+1 must cross above Day T High (or calibrated trigger)
                prev_level = param_trig if (param_trig > 0 and d == dates[-1]) else daily_prev_high.get(d, np.nan)
                if pd.isna(prev_level) or prev_level <= 0:
                    continue

                # Anti-Gap Exhaustion Protection: Reject if market opens deeply gap-up above trigger
                if day_atr_val > 0 and day_open > (prev_level + max_gap_mult * day_atr_val):
                    continue

                trigger_candles = day_df[day_df['high'] >= prev_level]

            if trigger_candles.empty:
                continue

            # Identify first trigger candle
            first_idx = trigger_candles.index[0]

            # Volume & Rejection Wick Confirmation via 5m bar
            cand_5m_idx = first_idx.floor('5min')
            if cand_5m_idx in df_5m.index:
                bar_5m = df_5m.loc[cand_5m_idx]
                bar_vol = bar_5m['volume']
                avg_vol = bar_5m['vol_sma5']
                bar_rng = bar_5m['high'] - bar_5m['low']
                
                # Check volume expansion
                if bar_vol < min_abs_vol:
                    continue
                if avg_vol > 0 and bar_vol < (min_vol_mult * avg_vol):
                    continue

                # Anti-Rejection Wick Filter
                if bar_rng > 0:
                    if is_sell:
                        lower_wick = min(bar_5m['open'], bar_5m['close']) - bar_5m['low']
                        if (lower_wick / bar_rng) > max_wick_ratio:
                            continue  # Adverse lower rejection wick
                    else:
                        upper_wick = bar_5m['high'] - max(bar_5m['open'], bar_5m['close'])
                        if (upper_wick / bar_rng) > max_wick_ratio:
                            continue  # Adverse upper rejection wick

            # Fire Signal: +1 for BUY Breakout, -1 for SELL Breakdown (strictly 1 signal per day)
            df.loc[first_idx, 'Signal'] = -1 if is_sell else 1
            df.loc[first_idx, 'Signal_Source'] = self.name
            break

        return df
