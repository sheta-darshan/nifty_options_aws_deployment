"""
Quantitative Research & Backtesting: Multi-Pivot Rejection & Reversal Engine
=============================================================================
Strictly for Research & Development. Independent of production live bot.
Analyzes NIFTY spot historical data over the last 2 years.

Combines:
1. Dynamic Price-Action Rejections (Fractal Swing Highs/Lows with multi-touch memory)
2. Daily Central Pivot Range (CPR: Pivot, TC, BC)
3. Daily Camarilla Reversal Levels (H3, L3)
4. Previous Day High & Low (PDH, PDL)
5. Multi-Level Confluence Detection
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


class PivotLevel:
    def __init__(self, price: float, level_type: str, created_time, touch_count: int = 1):
        self.price = price
        self.level_type = level_type  # 'DYNAMIC_SWING', 'CPR', 'CAMARILLA', 'PDH_PDL', 'CONFLUENCE'
        self.created_time = created_time
        self.touch_count = touch_count
        self.last_touched = created_time
        self.is_active = True

    def __repr__(self):
        return f"[{self.level_type}] {self.price:.1f} (touches={self.touch_count})"


def calculate_daily_formulaic_pivots(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes daily CPR, Camarilla, and PDH/PDL from daily resampled candles.
    All shifted by 1 to prevent look-ahead bias.
    """
    daily = df.resample('1D', on='timestamp').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()

    daily = daily[daily['open'] > 0].copy()

    # Shift by 1 day so today uses yesterday's data
    daily['prev_h'] = daily['high'].shift(1)
    daily['prev_l'] = daily['low'].shift(1)
    daily['prev_c'] = daily['close'].shift(1)

    # CPR
    daily['pivot'] = (daily['prev_h'] + daily['prev_l'] + daily['prev_c']) / 3.0
    daily['bc'] = (daily['prev_h'] + daily['prev_l']) / 2.0
    daily['tc'] = (daily['pivot'] - daily['bc']) + daily['pivot']
    daily['cpr_top'] = daily[['tc', 'bc']].max(axis=1)
    daily['cpr_bot'] = daily[['tc', 'bc']].min(axis=1)
    daily['cpr_width_pct'] = (daily['cpr_top'] - daily['cpr_bot']) / daily['pivot'] * 100.0

    # Camarilla
    range_hl = daily['prev_h'] - daily['prev_l']
    daily['cam_h3'] = daily['prev_c'] + range_hl * (1.1 / 4.0)
    daily['cam_l3'] = daily['prev_c'] - range_hl * (1.1 / 4.0)
    daily['cam_h4'] = daily['prev_c'] + range_hl * (1.1 / 2.0)
    daily['cam_l4'] = daily['prev_c'] - range_hl * (1.1 / 2.0)

    # PDH / PDL
    daily['pdh'] = daily['prev_h']
    daily['pdl'] = daily['prev_l']

    return daily.dropna(subset=['pivot'])


def calculate_weekly_formulaic_pivots(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes Weekly CPR (Dhan Indicator #16) from weekly resampled candles.
    Shifted by 1 to prevent look-ahead bias.
    """
    weekly = df.resample('W-FRI', on='timestamp').agg({
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


def find_swing_points(df: pd.DataFrame, lookback: int = 4):
    """
    Detects local fractal swing highs and swing lows.
    A swing high at index i is confirmed only at index i + lookback (zero lookahead).
    """
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)

    swing_highs = np.zeros(n, dtype=bool)
    swing_lows = np.zeros(n, dtype=bool)

    for i in range(lookback, n - lookback):
        # Peak: current high is strictly >= surrounding lookback bars
        if (highs[i] >= highs[i - lookback:i].max()) and (highs[i] >= highs[i + 1:i + lookback + 1].max()):
            swing_highs[i] = True
        # Valley: current low is strictly <= surrounding lookback bars
        if (lows[i] <= lows[i - lookback:i].min()) and (lows[i] <= lows[i + 1:i + lookback + 1].min()):
            swing_lows[i] = True

    return swing_highs, swing_lows


def run_pivot_reversal_backtest(
    csv_path: str,
    years: float = 2.0,
    resample_rule: str = '5min',
    tolerance_pts: float = 14.0,
    min_wick_ratio: float = 0.35,
    risk_reward: float = 2.0,
    sl_buffer_pts: float = 6.0,
    min_sl_pts: float = 15.0,
    max_sl_pts: float = 40.0,
    max_daily_trades: int = 3,
    level_memory_days: int = 15,
    min_touches: int = 1,
    confluence_only: bool = False,
    elite_only: bool = False,
    trail_be: bool = False,
    trend_filter: str = 'none',  # 'none', 'ema50', 'cpr_pivot'
    rsi_filter: bool = False,
    min_cpr_width_pct: float = 0.0
):
    print("=" * 80)
    print(" QUANTITATIVE RESEARCH: NIFTY PIVOT REVERSAL & REJECTION ENGINE")
    print("=" * 80)
    print(f"Loading data from: {csv_path}")

    # 1. Load CSV
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # 2. Filter last N years
    end_date = df['timestamp'].iloc[-1]
    start_date = end_date - timedelta(days=int(years * 365.25))
    df = df[df['timestamp'] >= start_date].copy().reset_index(drop=True)
    print(f"Research Window: {df['timestamp'].iloc[0].strftime('%Y-%m-%d')} to {df['timestamp'].iloc[-1].strftime('%Y-%m-%d')} ({years} Years)")

    # 3. Calculate Daily & Weekly Formulaic Pivots (Dhan Indicators #15 & #16)
    daily_pivots = calculate_daily_formulaic_pivots(df)
    weekly_pivots = calculate_weekly_formulaic_pivots(df)

    daily_pivot_dict = {}
    for dt_idx, row in daily_pivots.iterrows():
        date_key = dt_idx.date()
        daily_pivot_dict[date_key] = {
            'pivot': row['pivot'],
            'cpr_top': row['cpr_top'],
            'cpr_bot': row['cpr_bot'],
            'cpr_width_pct': row.get('cpr_width_pct', 0.0),
            'cam_h3': row['cam_h3'],
            'cam_l3': row['cam_l3'],
            'pdh': row['pdh'],
            'pdl': row['pdl']
        }

    # Weekly CPR mapping
    weekly_pivots = weekly_pivots.sort_index()

    # 4. Resample to Target Timeframe (e.g. 5-min)
    df = df.set_index('timestamp')
    df_res = df.resample(resample_rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()

    # Filter market hours: 09:15 to 15:30
    df_res['time'] = df_res['timestamp'].dt.time
    df_res = df_res[(df_res['time'] >= datetime.strptime("09:15", "%H:%M").time()) &
                    (df_res['time'] <= datetime.strptime("15:30", "%H:%M").time())].copy().reset_index(drop=True)

    # Technical Indicators for Filtering
    df_res['ema50'] = df_res['close'].ewm(span=50, adjust=False).mean()
    delta = df_res['close'].diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    df_res['rsi14'] = 100.0 - (100.0 / (1.0 + rs))

    # 5. Detect Swing Highs & Swing Lows
    lookback = 4
    swing_highs, swing_lows = find_swing_points(df_res, lookback=lookback)
    df_res['swing_high'] = swing_highs
    df_res['swing_low'] = swing_lows

    # 6. Backtesting Simulation Loop
    active_levels = []  # List of PivotLevel objects
    trades = []
    daily_trades_count = {}

    n = len(df_res)
    print(f"Total {resample_rule} candles analyzed: {n:,}")
    print("Simulating bar-by-bar causal price-action execution...")

    current_trade = None

    for i in range(lookback * 2, n):
        row = df_res.iloc[i]
        curr_time = row['timestamp']
        curr_date = curr_time.date()
        curr_time_of_day = row['time']

        o = row['open']
        h = row['high']
        l = row['low']
        c = row['close']
        candle_range = max(h - l, 1.0)

        # Update confirmed swing levels (a swing at index i - lookback is confirmed now at bar i)
        confirm_idx = i - lookback
        if df_res['swing_high'].iloc[confirm_idx]:
            level_price = df_res['high'].iloc[confirm_idx]
            # Merge or create
            merged = False
            for lvl in active_levels:
                if abs(lvl.price - level_price) <= tolerance_pts:
                    lvl.price = (lvl.price * lvl.touch_count + level_price) / (lvl.touch_count + 1)
                    lvl.touch_count += 1
                    lvl.last_touched = curr_time
                    merged = True
                    break
            if not merged:
                active_levels.append(PivotLevel(level_price, 'DYNAMIC_SWING', curr_time))

        if df_res['swing_low'].iloc[confirm_idx]:
            level_price = df_res['low'].iloc[confirm_idx]
            merged = False
            for lvl in active_levels:
                if abs(lvl.price - level_price) <= tolerance_pts:
                    lvl.price = (lvl.price * lvl.touch_count + level_price) / (lvl.touch_count + 1)
                    lvl.touch_count += 1
                    lvl.last_touched = curr_time
                    merged = True
                    break
            if not merged:
                active_levels.append(PivotLevel(level_price, 'DYNAMIC_SWING', curr_time))

        # Prune old levels older than memory limit
        active_levels = [lvl for lvl in active_levels if (curr_time - lvl.created_time).days <= level_memory_days]

        # Gather current day's formulaic pivots
        day_pivots = daily_pivot_dict.get(curr_date, {})

        # Manage open trade
        if current_trade is not None:
            entry_p = current_trade['entry_price']
            sl_p = current_trade['sl_price']
            tp_p = current_trade['tp_price']
            side = current_trade['side']

            # Trailing Break-Even: lock in break-even once MFE >= 1.0 * sl_dist
            if trail_be:
                if side == 'BUY' and h >= entry_p + current_trade['sl_dist']:
                    current_trade['sl_price'] = max(current_trade['sl_price'], entry_p + 1.0)
                    sl_p = current_trade['sl_price']
                elif side == 'SELL' and l <= entry_p - current_trade['sl_dist']:
                    current_trade['sl_price'] = min(current_trade['sl_price'], entry_p - 1.0)
                    sl_p = current_trade['sl_price']

            # Check intraday square-off (15:15)
            if curr_time_of_day >= datetime.strptime("15:15", "%H:%M").time():
                pnl_pts = (c - entry_p) if side == 'BUY' else (entry_p - c)
                current_trade['exit_time'] = curr_time
                current_trade['exit_price'] = c
                current_trade['exit_reason'] = 'SQUARE_OFF_1515'
                current_trade['pnl_pts'] = pnl_pts
                current_trade['is_win'] = pnl_pts > 0
                trades.append(current_trade)
                current_trade = None
                continue

            if side == 'BUY':
                # Check SL hit
                if l <= sl_p:
                    pnl_pts = sl_p - entry_p
                    current_trade['exit_time'] = curr_time
                    current_trade['exit_price'] = sl_p
                    current_trade['exit_reason'] = 'BREAK_EVEN' if pnl_pts >= 0 else 'STOP_LOSS'
                    current_trade['pnl_pts'] = pnl_pts
                    current_trade['is_win'] = pnl_pts > 0
                    trades.append(current_trade)
                    current_trade = None
                    continue
                # Check TP hit
                elif h >= tp_p:
                    pnl_pts = tp_p - entry_p
                    current_trade['exit_time'] = curr_time
                    current_trade['exit_price'] = tp_p
                    current_trade['exit_reason'] = 'TARGET_PROFIT'
                    current_trade['pnl_pts'] = pnl_pts
                    current_trade['is_win'] = True
                    trades.append(current_trade)
                    current_trade = None
                    continue

            elif side == 'SELL':
                # Check SL hit
                if h >= sl_p:
                    pnl_pts = entry_p - sl_p
                    current_trade['exit_time'] = curr_time
                    current_trade['exit_price'] = sl_p
                    current_trade['exit_reason'] = 'BREAK_EVEN' if pnl_pts >= 0 else 'STOP_LOSS'
                    current_trade['pnl_pts'] = pnl_pts
                    current_trade['is_win'] = pnl_pts > 0
                    trades.append(current_trade)
                    current_trade = None
                    continue
                # Check TP hit
                elif l <= tp_p:
                    pnl_pts = entry_p - tp_p
                    current_trade['exit_time'] = curr_time
                    current_trade['exit_price'] = tp_p
                    current_trade['exit_reason'] = 'TARGET_PROFIT'
                    current_trade['pnl_pts'] = pnl_pts
                    current_trade['is_win'] = True
                    trades.append(current_trade)
                    current_trade = None
                    continue

        # If no open trade, scan for Reversal Signal on completed candle (i)
        if current_trade is None and i + 1 < n:
            # Check daily trade cap
            today_count = daily_trades_count.get(curr_date, 0)
            if today_count >= max_daily_trades:
                continue

            # Don't take fresh entries after 14:45 or in first 15 mins (09:15 - 09:30)
            if curr_time_of_day < datetime.strptime("09:30", "%H:%M").time() or \
               curr_time_of_day > datetime.strptime("14:45", "%H:%M").time():
                continue

            # Check narrow CPR filter (skip trend days)
            if min_cpr_width_pct > 0 and day_pivots.get('cpr_width_pct', 0.0) < min_cpr_width_pct:
                continue

            # Construct pool of all active candidate levels
            candidate_levels = []

            # 1. Dynamic swing levels
            for lvl in active_levels:
                candidate_levels.append(('DYNAMIC_SWING', lvl.price, lvl.touch_count))

            # 2. Formulaic Daily levels (Dhan Indicator #15 & #2)
            if day_pivots:
                candidate_levels.append(('CPR_PIVOT', day_pivots['pivot'], 1))
                candidate_levels.append(('CPR_TC', day_pivots['cpr_top'], 1))
                candidate_levels.append(('CPR_BC', day_pivots['cpr_bot'], 1))
                candidate_levels.append(('CAM_H3', day_pivots['cam_h3'], 1))
                candidate_levels.append(('CAM_L3', day_pivots['cam_l3'], 1))
                candidate_levels.append(('PDH', day_pivots['pdh'], 1))
                candidate_levels.append(('PDL', day_pivots['pdl'], 1))

            # 3. Weekly CPR (Dhan Indicator #16)
            wk_matches = weekly_pivots[weekly_pivots.index <= curr_time]
            if not wk_matches.empty:
                last_wk = wk_matches.iloc[-1]
                candidate_levels.append(('WEEKLY_PIVOT', last_wk['w_pivot'], 1))
                candidate_levels.append(('WEEKLY_TC', last_wk['w_cpr_top'], 1))
                candidate_levels.append(('WEEKLY_BC', last_wk['w_cpr_bot'], 1))

            # 4. AutoFib Golden Pocket 0.5 - 0.618 (Dhan Indicator #21)
            recent_swings = [lvl.price for lvl in active_levels]
            if len(recent_swings) >= 2:
                r_high = max(recent_swings)
                r_low = min(recent_swings)
                if r_high - r_low > 60.0:
                    candidate_levels.append(('AUTOFIB_50', r_low + 0.50 * (r_high - r_low), 1))
                    candidate_levels.append(('AUTOFIB_618', r_low + 0.618 * (r_high - r_low), 1))

            # CANDLE REVERSAL PATTERNS
            lower_wick = min(o, c) - l
            upper_wick = h - max(o, c)
            lower_wick_ratio = lower_wick / candle_range
            upper_wick_ratio = upper_wick / candle_range

            next_open = df_res['open'].iloc[i + 1]
            entry_time = df_res['timestamp'].iloc[i + 1]

            # Signal 1: BULLISH REVERSAL (Price dips into support/pivot, wicks out, closes green or high)
            can_buy = (lower_wick_ratio >= min_wick_ratio and c > l + 0.3 * candle_range)
            if can_buy:
                if trend_filter == 'ema50' and c < row['ema50']:
                    can_buy = False
                elif trend_filter == 'cpr_pivot' and day_pivots and c < day_pivots['pivot']:
                    can_buy = False
                elif rsi_filter and row['rsi14'] > 45.0:
                    can_buy = False

            if can_buy:
                # Find matching support level
                matched_level = None
                matched_type = None
                for lvl_type, lvl_price, touches in candidate_levels:
                    # Filter: dynamic swing must have at least min_touches unless confluence exists
                    if lvl_type == 'DYNAMIC_SWING' and touches < min_touches:
                        confluence_candidate = any(
                            abs(lvl_price - other_price) <= tolerance_pts and other_type != lvl_type
                            for other_type, other_price, _ in candidate_levels
                        )
                        if not confluence_candidate:
                            continue

                    # Low pierced or touched near the level, and close rebounded above it
                    if abs(l - lvl_price) <= tolerance_pts or (l <= lvl_price and c >= lvl_price):
                        # Confluence check: is there a dynamic level AND a formulaic level nearby?
                        confluence = any(
                            abs(lvl_price - other_price) <= tolerance_pts and other_type != lvl_type
                            for other_type, other_price, _ in candidate_levels
                        )
                        if confluence_only and not confluence and lvl_type == 'DYNAMIC_SWING':
                            continue

                        matched_level = lvl_price
                        matched_type = f"{lvl_type}_CONFLUENCE" if confluence else lvl_type
                        if elite_only:
                            elite_types = {
                                'CAM_L3', 'CAM_L3_CONFLUENCE', 'CPR_PIVOT_CONFLUENCE', 'CAM_H3', 'PDH', 'PDH_CONFLUENCE', 
                                'PDL_CONFLUENCE', 'CPR_BC', 'CPR_BC_CONFLUENCE',
                                'WEEKLY_PIVOT_CONFLUENCE', 'WEEKLY_TC_CONFLUENCE', 'WEEKLY_BC_CONFLUENCE',
                                'AUTOFIB_50_CONFLUENCE', 'AUTOFIB_618_CONFLUENCE', 'AUTOFIB_50', 'AUTOFIB_618'
                            }
                            if matched_type not in elite_types:
                                matched_level = None
                                continue
                        break

                if matched_level is not None:
                    sl_dist = max(next_open - (l - sl_buffer_pts), min_sl_pts)
                    sl_dist = min(sl_dist, max_sl_pts)
                    sl = next_open - sl_dist
                    tp = next_open + (sl_dist * risk_reward)

                    current_trade = {
                        'entry_time': entry_time,
                        'side': 'BUY',
                        'entry_price': next_open,
                        'sl_price': sl,
                        'tp_price': tp,
                        'sl_dist': sl_dist,
                        'level_price': matched_level,
                        'level_type': matched_type,
                        'wick_ratio': lower_wick_ratio
                    }
                    daily_trades_count[curr_date] = today_count + 1
                    continue

            # Signal 2: BEARISH REVERSAL (Price spikes into resistance/pivot, wicks down, closes red or low)
            can_sell = (upper_wick_ratio >= min_wick_ratio and c < h - 0.3 * candle_range)
            if can_sell:
                if trend_filter == 'ema50' and c > row['ema50']:
                    can_sell = False
                elif trend_filter == 'cpr_pivot' and day_pivots and c > day_pivots['pivot']:
                    can_sell = False
                elif rsi_filter and row['rsi14'] < 55.0:
                    can_sell = False

            if can_sell:
                matched_level = None
                matched_type = None
                for lvl_type, lvl_price, touches in candidate_levels:
                    if lvl_type == 'DYNAMIC_SWING' and touches < min_touches:
                        confluence_candidate = any(
                            abs(lvl_price - other_price) <= tolerance_pts and other_type != lvl_type
                            for other_type, other_price, _ in candidate_levels
                        )
                        if not confluence_candidate:
                            continue

                    if abs(h - lvl_price) <= tolerance_pts or (h >= lvl_price and c <= lvl_price):
                        confluence = any(
                            abs(lvl_price - other_price) <= tolerance_pts and other_type != lvl_type
                            for other_type, other_price, _ in candidate_levels
                        )
                        if confluence_only and not confluence and lvl_type == 'DYNAMIC_SWING':
                            continue

                        matched_level = lvl_price
                        matched_type = f"{lvl_type}_CONFLUENCE" if confluence else lvl_type
                        if elite_only:
                            elite_types = {
                                'CAM_L3', 'CAM_L3_CONFLUENCE', 'CPR_PIVOT_CONFLUENCE', 'CAM_H3', 'PDH', 'PDH_CONFLUENCE', 
                                'PDL_CONFLUENCE', 'CPR_BC', 'CPR_BC_CONFLUENCE',
                                'WEEKLY_PIVOT_CONFLUENCE', 'WEEKLY_TC_CONFLUENCE', 'WEEKLY_BC_CONFLUENCE',
                                'AUTOFIB_50_CONFLUENCE', 'AUTOFIB_618_CONFLUENCE', 'AUTOFIB_50', 'AUTOFIB_618'
                            }
                            if matched_type not in elite_types:
                                matched_level = None
                                continue
                        break

                if matched_level is not None:
                    sl_dist = max((h + sl_buffer_pts) - next_open, min_sl_pts)
                    sl_dist = min(sl_dist, max_sl_pts)
                    sl = next_open + sl_dist
                    tp = next_open - (sl_dist * risk_reward)

                    current_trade = {
                        'entry_time': entry_time,
                        'side': 'SELL',
                        'entry_price': next_open,
                        'sl_price': sl,
                        'tp_price': tp,
                        'sl_dist': sl_dist,
                        'level_price': matched_level,
                        'level_type': matched_type,
                        'wick_ratio': upper_wick_ratio
                    }
                    daily_trades_count[curr_date] = today_count + 1
                    continue

    # Close any lingering trade at backtest end
    if current_trade is not None:
        last_row = df_res.iloc[-1]
        pnl_pts = (last_row['close'] - current_trade['entry_price']) if current_trade['side'] == 'BUY' else (current_trade['entry_price'] - last_row['close'])
        current_trade['exit_time'] = last_row['timestamp']
        current_trade['exit_price'] = last_row['close']
        current_trade['exit_reason'] = 'BACKTEST_END'
        current_trade['pnl_pts'] = pnl_pts
        current_trade['is_win'] = pnl_pts > 0
        trades.append(current_trade)

    # 7. Analyze Performance & Generate Summary
    trades_df = pd.DataFrame(trades)
    output_csv = os.path.join(os.path.dirname(__file__), "pivot_reversal_trade_log.csv")
    trades_df.to_csv(output_csv, index=False)
    print(f"\nTrade log successfully saved to: {output_csv}")

    if len(trades_df) == 0:
        print("No trades triggered with the given parameters.")
        return

    total_trades = len(trades_df)
    wins = trades_df[trades_df['is_win']]
    losses = trades_df[~trades_df['is_win']]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades) * 100.0

    total_pts_won = wins['pnl_pts'].sum()
    total_pts_lost = abs(losses['pnl_pts'].sum())
    net_pts = trades_df['pnl_pts'].sum()
    profit_factor = (total_pts_won / total_pts_lost) if total_pts_lost > 0 else float('inf')

    avg_win_pts = wins['pnl_pts'].mean() if win_count > 0 else 0.0
    avg_loss_pts = abs(losses['pnl_pts'].mean()) if loss_count > 0 else 0.0
    realized_rr = (avg_win_pts / avg_loss_pts) if avg_loss_pts > 0 else 0.0

    # Drawdown calculation
    trades_df['cum_pts'] = trades_df['pnl_pts'].cumsum()
    trades_df['peak_pts'] = trades_df['cum_pts'].cummax()
    trades_df['drawdown_pts'] = trades_df['peak_pts'] - trades_df['cum_pts']
    max_dd_pts = trades_df['drawdown_pts'].max()

    print("\n" + "=" * 80)
    print("                 NIFTY PIVOT REVERSAL BACKTEST SUMMARY")
    print("=" * 80)
    print(f" Total Trades Taken   : {total_trades}")
    print(f" Winning Trades       : {win_count} ({win_rate:.1f}%)")
    print(f" Losing Trades        : {loss_count} ({100.0 - win_rate:.1f}%)")
    print(f" Net Points Captured  : {net_pts:+,.1f} pts")
    print(f" Total Points Won     : {total_pts_won:+,.1f} pts")
    print(f" Total Points Lost    : -{total_pts_lost:,.1f} pts")
    print(f" Profit Factor        : {profit_factor:.2f}")
    print(f" Average Win          : +{avg_win_pts:.1f} pts")
    print(f" Average Loss         : -{avg_loss_pts:.1f} pts")
    print(f" Realized Risk:Reward : 1:{realized_rr:.2f}")
    print(f" Max Drawdown         : -{max_dd_pts:,.1f} pts")
    print("=" * 80)

    # Breakdown by Pivot Type
    print("\n--- PERFORMANCE BY PIVOT LEVEL CATEGORY ---")
    type_group = trades_df.groupby('level_type').agg(
        trades=('pnl_pts', 'count'),
        win_rate=('is_win', lambda x: (x.sum() / len(x)) * 100.0),
        net_points=('pnl_pts', 'sum'),
        avg_pts_per_trade=('pnl_pts', 'mean')
    ).reset_index()
    type_group = type_group.sort_values('net_points', ascending=False)
    print(type_group.to_string(index=False))

    # Breakdown by Direction
    print("\n--- PERFORMANCE BY TRADE DIRECTION ---")
    side_group = trades_df.groupby('side').agg(
        trades=('pnl_pts', 'count'),
        win_rate=('is_win', lambda x: (x.sum() / len(x)) * 100.0),
        net_points=('pnl_pts', 'sum'),
        avg_pts_per_trade=('pnl_pts', 'mean')
    ).reset_index()
    print(side_group.to_string(index=False))
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Pivot Reversals on NIFTY Spot Data")
    parser.add_argument("--csv", default="backtest_data/nifty_spot.csv", help="Path to Nifty spot 1-min CSV")
    parser.add_argument("--years", type=float, default=2.0, help="Years of lookback to test (default: 2.0)")
    parser.add_argument("--timeframe", default="5min", help="Resample timeframe: 5min, 15min, 3min")
    parser.add_argument("--rr", type=float, default=2.0, help="Target Risk:Reward ratio (default: 2.0)")
    parser.add_argument("--wick", type=float, default=0.35, help="Minimum rejection wick ratio (default: 0.35)")
    parser.add_argument("--min-touches", type=int, default=1, help="Minimum touches required for dynamic levels (default: 1)")
    parser.add_argument("--confluence-only", action="store_true", help="Only trade when dynamic level confluences with CPR/Cam/PDH/PDL")
    parser.add_argument("--elite-only", action="store_true", help="Only trade top-tier institutional levels (Cam L3/H3, CPR Pivot/BC, PDH)")
    parser.add_argument("--trail-be", action="store_true", help="Move Stop Loss to Break-Even at 1.0R")
    parser.add_argument("--trend-filter", choices=['none', 'ema50', 'cpr_pivot'], default='none', help="Trend alignment filter")
    parser.add_argument("--rsi-filter", action="store_true", help="Filter for RSI pullback/exhaustion")
    parser.add_argument("--min-cpr-width", type=float, default=0.0, help="Skip days where CPR width % is below this threshold")
    args = parser.parse_args()

    run_pivot_reversal_backtest(
        csv_path=args.csv,
        years=args.years,
        resample_rule=args.timeframe,
        risk_reward=args.rr,
        min_wick_ratio=args.wick,
        min_touches=args.min_touches,
        confluence_only=args.confluence_only,
        elite_only=args.elite_only,
        trail_be=args.trail_be,
        trend_filter=args.trend_filter,
        rsi_filter=args.rsi_filter,
        min_cpr_width_pct=args.min_cpr_width
    )
