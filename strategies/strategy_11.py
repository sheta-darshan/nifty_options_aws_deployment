import pandas as pd
import numpy as np
from .base import BaseStrategy
from .registry import register_strategy


@register_strategy
class Strategy11(BaseStrategy):
    """
    Gap-Fade + Previous-Day-Reversal (agreement-only) strategy.

    Rationale (from spot backtest, NIFTY 2021-2026):
      - signal_gap = fade today's opening gap vs yesterday's close
      - signal_rev = fade yesterday's own open->close move
      - Trade ONLY when both signals agree (same direction) and neither is zero.
      - This is a single decision per day, made using only information known
        BEFORE today's session starts (yesterday's OHLC) -> no lookahead.
      - Out-of-sample (2025-2026) this showed ~53% win rate, ann. Sharpe ~0.9
        on spot returns BEFORE transaction costs. Edge is thin (~0.04-0.07%
        avg move) -- real option spread/slippage/brokerage may erase it.
        Validate cost sensitivity in your engine before sizing this up.

    Signal convention (matches Strategy_3):
      Signal =  1  -> long bias for the day (buy ATM CE)
      Signal = -1  -> short bias for the day (buy ATM PE)
      Signal =  0  -> no trade (signals disagree, or no gap)

    Exit/stop/target logic is intentionally NOT included here -- per your
    note, that is handled by other scripts. This strategy only emits the
    single daily entry signal.
    """

    name = "Strategy_11"

    def get_default_params(self) -> dict:
        return {
            "MIN_GAP_PCT": 0.0,      # minimum abs gap size (in %) required to consider a trade; 0 = no filter
            "ENTRY_BAR_INDEX": 0,    # which 1-min bar of the session to fire the signal on (0 = first bar of day)
        }

    def get_optimization_grid(self) -> dict:
        return {
            # Sweep gap-size filter -- in the spot backtest, larger gaps did NOT
            # clearly improve out-of-sample results, but worth re-checking with
            # real option costs since it changes trade frequency a lot.
            "MIN_GAP_PCT": [0.0, 0.1, 0.2, 0.3, 0.5],
            "ENTRY_BAR_INDEX": [0],
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot

        df = df_spot.copy()
        df["Signal"] = 0
        df["GapFade_Signal"] = 0
        df["Signal_Source"] = "None"

        # session date for each bar (index must be a DatetimeIndex, as in Strategy_3)
        session_date = df.index.date

        # ---- Build one row per trading day: open, close ----
        # NOTE: this groups the FULL df_spot passed in. That's correct for both
        # live and backtest modes -- but it means the caller controls efficiency.
        # If your live engine calls this every minute with an ever-growing
        # multi-year history, that's on the engine side to bound (e.g. only pass
        # the last ~5-10 trading days once you're live, since this strategy only
        # ever needs yesterday's close/open + today's first bar). Don't bound it
        # inside this function based on df.index[-1], since that silently breaks
        # correctness when the full history is passed in one shot for backtesting.
        daily = pd.DataFrame({
            "date": session_date,
            "open": df["open"].values,
            "close": df["close"].values,
        })
        daily = daily.groupby("date").agg(
            day_open=("open", "first"),
            day_close=("close", "last"),
        )

        if len(daily) < 2:
            return df

        # ---- Signals, using only info known before today's session opens ----
        daily["prev_close"] = daily["day_close"].shift(1)
        daily["prev_open"] = daily["day_open"].shift(1)

        daily["gap_pct"] = (daily["day_open"] - daily["prev_close"]) / daily["prev_close"] * 100
        daily["prev_day_ret_pct"] = (daily["prev_close"] - daily["prev_open"]) / daily["prev_open"] * 100

        sig_gap = -np.sign(daily["gap_pct"])          # fade the gap
        sig_rev = -np.sign(daily["prev_day_ret_pct"])  # fade yesterday's move

        min_gap = self.params.get("MIN_GAP_PCT", 0.0)
        gap_ok = daily["gap_pct"].abs() >= min_gap

        agree = (sig_gap == sig_rev) & (sig_gap != 0) & gap_ok
        daily["day_signal"] = 0
        daily.loc[agree, "day_signal"] = sig_gap[agree].astype(int)

        # ---- Map the once-per-day signal onto the entry bar in the 1-min df ----
        entry_idx = self.params.get("ENTRY_BAR_INDEX", 0)
        signal_by_date = daily["day_signal"]

        # group bar timestamps by date once, for fast lookup of the Nth bar of each session
        date_index = pd.Series(df.index, index=session_date)

        for date, sig in signal_by_date.items():
            if sig == 0:
                continue
            day_timestamps = date_index.loc[[date]] if date in date_index.index else None
            if day_timestamps is None or len(day_timestamps) <= entry_idx:
                continue
            entry_ts = day_timestamps.iloc[entry_idx]
            df.loc[entry_ts, "Signal"] = int(sig)
            df.loc[entry_ts, "GapFade_Signal"] = int(sig)
            df.loc[entry_ts, "Signal_Source"] = "Strategy 11 (GapFade+Reversal)"

        return df
