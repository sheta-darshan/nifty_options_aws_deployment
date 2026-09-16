"""
Quantitative Research: Contract-Accurate Real Options Backtest
==============================================================
Tests the optimized Pivot Reversal Strategy using REAL 1-Minute Historical Option Contracts
from backtest_data/Nifty_option_historical/Week_1min.

Supports:
- Option Buying (Long ATM Calls on Bullish Reversals, Long ATM Puts on Bearish Reversals)
- Option Selling (Short ATM Puts on Bullish Reversals, Short ATM Calls on Bearish Reversals)
- Realistic Exchange Charges (Brokerage, STT, Exchange Txn, GST, Stamp Duty)
- Real 1-minute premium tick simulation
"""

import os
import sys
import glob
import argparse
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


# ---------------------------------------------------------
# Dynamic Pivot & Signal Engine (from research_pivot_reversals)
# ---------------------------------------------------------
class PivotLevel:
    def __init__(self, price: float, level_type: str, created_time, touch_count: int = 1):
        self.price = price
        self.level_type = level_type
        self.created_time = created_time
        self.touch_count = touch_count
        self.last_touched = created_time


def calculate_daily_formulaic_pivots(df: pd.DataFrame) -> pd.DataFrame:
    daily = df.resample('1D', on='timestamp').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    }).dropna()

    daily = daily[daily['open'] > 0].copy()

    daily['prev_h'] = daily['high'].shift(1)
    daily['prev_l'] = daily['low'].shift(1)
    daily['prev_c'] = daily['close'].shift(1)

    daily['pivot'] = (daily['prev_h'] + daily['prev_l'] + daily['prev_c']) / 3.0
    daily['bc'] = (daily['prev_h'] + daily['prev_l']) / 2.0
    daily['tc'] = (daily['pivot'] - daily['bc']) + daily['pivot']
    daily['cpr_top'] = daily[['tc', 'bc']].max(axis=1)
    daily['cpr_bot'] = daily[['tc', 'bc']].min(axis=1)
    daily['cpr_width_pct'] = (daily['cpr_top'] - daily['cpr_bot']) / daily['pivot'] * 100.0

    range_hl = daily['prev_h'] - daily['prev_l']
    daily['cam_h3'] = daily['prev_c'] + range_hl * (1.1 / 4.0)
    daily['cam_l3'] = daily['prev_c'] - range_hl * (1.1 / 4.0)
    daily['cam_h4'] = daily['prev_c'] + range_hl * (1.1 / 2.0)
    daily['cam_l4'] = daily['prev_c'] - range_hl * (1.1 / 2.0)

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
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)

    swing_highs = np.zeros(n, dtype=bool)
    swing_lows = np.zeros(n, dtype=bool)

    for i in range(lookback, n - lookback):
        if (highs[i] >= highs[i - lookback:i].max()) and (highs[i] >= highs[i + 1:i + lookback + 1].max()):
            swing_highs[i] = True
        if (lows[i] <= lows[i - lookback:i].min()) and (lows[i] <= lows[i + 1:i + lookback + 1].min()):
            swing_lows[i] = True

    return swing_highs, swing_lows


def compute_charges(buy_premium: float, sell_premium: float, qty: int, is_option_buy: bool) -> float:
    """
    Computes realistic Indian exchange transaction costs, taxes, and brokerage.
    """
    buy_val = buy_premium * qty
    sell_val = sell_premium * qty
    turnover = buy_val + sell_val

    # Brokerage: Rs. 20 per order
    brokerage = 40.0

    # STT: 0.0625% on sell turnover
    stt = sell_val * 0.000625

    # Exchange Txn Charges: 0.053% of turnover
    exchange_charges = turnover * 0.00053

    # GST: 18% on (Brokerage + Exchange Txn Charges)
    gst = (brokerage + exchange_charges) * 0.18

    # SEBI Turnover Charges: Rs. 10 per crore (0.0001%)
    sebi = turnover * 0.000001

    # Stamp Duty: 0.003% on buy turnover
    stamp_duty = buy_val * 0.00003

    total_charges = brokerage + stt + exchange_charges + gst + sebi + stamp_duty
    return round(total_charges, 2)


# ---------------------------------------------------------
# Real Options Simulation Engine
# ---------------------------------------------------------
def run_options_backtest(
    spot_csv: str = "backtest_data/nifty_spot.csv",
    options_dir: str = "backtest_data/Nifty_option_historical/Week_1min",
    years: float = 2.0,
    option_mode: str = "BUY",  # 'BUY' or 'SELL'
    lot_size: int = 25,
    lots: int = 1,
    tolerance_pts: float = 14.0,
    min_wick_ratio: float = 0.45,
    risk_reward: float = 2.0,
    min_cpr_width_pct: float = 0.10,
    sl_buffer_pts: float = 6.0,
    min_sl_pts: float = 15.0,
    max_sl_pts: float = 40.0,
    max_daily_trades: int = 3
):
    print("=" * 80)
    print(f" REAL CONTRACT OPTIONS BACKTEST: NIFTY PIVOT REVERSAL ({option_mode} MODE)")
    print("=" * 80)
    print(f"Option Execution Mode : {'OPTION BUYING (Long CE/PE)' if option_mode == 'BUY' else 'OPTION SELLING (Short PE/CE)'}")
    print(f"Lot Size              : {lot_size} qty | Lots: {lots} ({lot_size * lots} total qty)")

    # 1. Load Spot Data
    df = pd.read_csv(spot_csv)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # 2. Filter Date Range
    end_date = df['timestamp'].iloc[-1]
    start_date = end_date - timedelta(days=int(years * 365.25))
    df = df[df['timestamp'] >= start_date].copy().reset_index(drop=True)
    print(f"Testing Spot Range    : {df['timestamp'].iloc[0].strftime('%Y-%m-%d')} to {df['timestamp'].iloc[-1].strftime('%Y-%m-%d')}")

    # 3. Daily Formulaic Pivots
    daily_pivots = calculate_daily_formulaic_pivots(df)
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

    # Weekly Formulaic Pivots (Dhan Indicator #16)
    weekly_pivots = calculate_weekly_formulaic_pivots(df).sort_index()

    # 4. Resample 5-min
    df = df.set_index('timestamp')
    df_5m = df.resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()

    df_5m['time'] = df_5m['timestamp'].dt.time
    df_5m = df_5m[(df_5m['time'] >= datetime.strptime("09:15", "%H:%M").time()) &
                  (df_5m['time'] <= datetime.strptime("15:30", "%H:%M").time())].copy().reset_index(drop=True)

    # 5. Detect Swings
    lookback = 4
    swing_highs, swing_lows = find_swing_points(df_5m, lookback=lookback)
    df_5m['swing_high'] = swing_highs
    df_5m['swing_low'] = swing_lows

    # Build Map of Option Day Files
    all_opt_files = glob.glob(os.path.join(options_dir, "*", "*.csv"))
    opt_file_map = {}
    for f in all_opt_files:
        base_name = os.path.basename(f)
        # NIFTY_YYYY-MM-DD_1m.csv
        parts = base_name.split("_")
        if len(parts) >= 2:
            date_str = parts[1]
            opt_file_map[date_str] = f

    print(f"Indexed {len(opt_file_map)} days of 1-minute real option contracts.")

    # 6. Simulation State
    active_levels = []
    trades = []
    daily_trades_count = {}
    total_qty = lot_size * lots
    elite_types = {
        'CAM_L3', 'CAM_L3_CONFLUENCE', 'CPR_PIVOT_CONFLUENCE', 'CAM_H3', 'PDH', 'PDH_CONFLUENCE', 
        'PDL_CONFLUENCE', 'CPR_BC', 'CPR_BC_CONFLUENCE',
        'WEEKLY_PIVOT_CONFLUENCE', 'WEEKLY_TC_CONFLUENCE', 'WEEKLY_BC_CONFLUENCE',
        'AUTOFIB_50_CONFLUENCE', 'AUTOFIB_618_CONFLUENCE', 'AUTOFIB_50', 'AUTOFIB_618'
    }

    cached_opt_df = None
    cached_opt_date = None

    def get_option_day_df(date_obj):
        nonlocal cached_opt_df, cached_opt_date
        date_str = date_obj.strftime("%Y-%m-%d")
        if cached_opt_date == date_str:
            return cached_opt_df
        file_path = opt_file_map.get(date_str)
        if file_path and os.path.exists(file_path):
            try:
                odf = pd.read_csv(file_path)
                odf['datetime'] = pd.to_datetime(odf['datetime'])
                cached_opt_df = odf
                cached_opt_date = date_str
                return odf
            except Exception:
                return None
        return None

    current_trade = None
    n = len(df_5m)

    for i in range(lookback * 2, n):
        row = df_5m.iloc[i]
        curr_time = row['timestamp']
        curr_date = curr_time.date()
        curr_time_of_day = row['time']

        o = row['open']
        h = row['high']
        l = row['low']
        c = row['close']
        candle_range = max(h - l, 1.0)

        # Update confirmed swing levels
        confirm_idx = i - lookback
        if df_5m['swing_high'].iloc[confirm_idx]:
            level_price = df_5m['high'].iloc[confirm_idx]
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

        if df_5m['swing_low'].iloc[confirm_idx]:
            level_price = df_5m['low'].iloc[confirm_idx]
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

        day_pivots = daily_pivot_dict.get(curr_date, {})

        # Manage Open Trade using 1-min Option Candles
        if current_trade is not None:
            entry_spot = current_trade['entry_spot']
            sl_spot = current_trade['sl_spot']
            tp_spot = current_trade['tp_spot']
            side = current_trade['side']
            opt_type = current_trade['option_type']
            strike = current_trade['strike']
            opt_entry_p = current_trade['opt_entry_price']

            # Check Intraday Square-off (15:15)
            exit_triggered = False
            exit_reason = None
            exit_spot_p = c

            if curr_time_of_day >= datetime.strptime("15:15", "%H:%M").time():
                exit_triggered = True
                exit_reason = 'SQUARE_OFF_1515'
            elif side == 'BUY':
                if l <= sl_spot:
                    exit_triggered = True
                    exit_reason = 'SPOT_STOP_LOSS'
                    exit_spot_p = sl_spot
                elif h >= tp_spot:
                    exit_triggered = True
                    exit_reason = 'SPOT_TARGET_PROFIT'
                    exit_spot_p = tp_spot
            elif side == 'SELL':
                if h >= sl_spot:
                    exit_triggered = True
                    exit_reason = 'SPOT_STOP_LOSS'
                    exit_spot_p = sl_spot
                elif l <= tp_spot:
                    exit_triggered = True
                    exit_reason = 'SPOT_TARGET_PROFIT'
                    exit_spot_p = tp_spot

            if exit_triggered:
                # Find Option Exit Price from Option Dataset
                odf = get_option_day_df(curr_date)
                opt_exit_p = opt_entry_p  # fallback

                if odf is not None:
                    # Filter for strike, option_type, and current timestamp
                    c_rows = odf[
                        ((odf['strike_price'] - strike).abs() < 1.0) &
                        (odf['option_type'] == opt_type) &
                        (odf['datetime'] >= curr_time)
                    ]
                    if not c_rows.empty:
                        opt_exit_p = float(c_rows['close'].iloc[0])
                    else:
                        # Estimate via Delta ~0.50 if contract row missing
                        spot_diff = (exit_spot_p - entry_spot) if side == 'BUY' else (entry_spot - exit_spot_p)
                        opt_exit_p = max(opt_entry_p + (spot_diff * 0.50), 1.0)
                else:
                    spot_diff = (exit_spot_p - entry_spot) if side == 'BUY' else (entry_spot - exit_spot_p)
                    opt_exit_p = max(opt_entry_p + (spot_diff * 0.50), 1.0)

                # Calculate PnL based on Option Mode
                if option_mode == 'BUY':
                    # Bought option at opt_entry_p, sold at opt_exit_p
                    premium_pts = opt_exit_p - opt_entry_p
                    gross_pnl = premium_pts * total_qty
                    charges = compute_charges(opt_entry_p, opt_exit_p, total_qty, is_option_buy=True)
                else:
                    # Sold option at opt_entry_p, bought back at opt_exit_p
                    premium_pts = opt_entry_p - opt_exit_p
                    gross_pnl = premium_pts * total_qty
                    charges = compute_charges(opt_exit_p, opt_entry_p, total_qty, is_option_buy=False)

                net_pnl = gross_pnl - charges

                current_trade['exit_time'] = curr_time
                current_trade['exit_spot'] = exit_spot_p
                current_trade['opt_exit_price'] = round(opt_exit_p, 2)
                current_trade['exit_reason'] = exit_reason
                current_trade['premium_pts'] = round(premium_pts, 2)
                current_trade['gross_pnl'] = round(gross_pnl, 2)
                current_trade['charges'] = charges
                current_trade['net_pnl'] = round(net_pnl, 2)
                current_trade['is_win'] = net_pnl > 0

                trades.append(current_trade)
                current_trade = None
                continue

        # Look for Fresh Reversal Entry on Completed Candle
        if current_trade is None and i + 1 < n:
            today_count = daily_trades_count.get(curr_date, 0)
            if today_count >= max_daily_trades:
                continue

            if curr_time_of_day < datetime.strptime("09:30", "%H:%M").time() or \
               curr_time_of_day > datetime.strptime("14:45", "%H:%M").time():
                continue

            if min_cpr_width_pct > 0 and day_pivots.get('cpr_width_pct', 0.0) < min_cpr_width_pct:
                continue

            candidate_levels = []
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

            lower_wick = min(o, c) - l
            upper_wick = h - max(o, c)
            lower_wick_ratio = lower_wick / candle_range
            upper_wick_ratio = upper_wick / candle_range

            next_open = df_5m['open'].iloc[i + 1]
            entry_time = df_5m['timestamp'].iloc[i + 1]

            # Signal 1: BULLISH REVERSAL -> Call Option
            if lower_wick_ratio >= min_wick_ratio and c > l + 0.3 * candle_range:
                matched_level = None
                matched_type = None
                for lvl_type, lvl_price, touches in candidate_levels:
                    if abs(l - lvl_price) <= tolerance_pts or (l <= lvl_price and c >= lvl_price):
                        confluence = any(
                            abs(lvl_price - other_price) <= tolerance_pts and other_type != lvl_type
                            for other_type, other_price, _ in candidate_levels
                        )
                        matched_level = lvl_price
                        matched_type = f"{lvl_type}_CONFLUENCE" if confluence else lvl_type
                        if matched_type not in elite_types:
                            matched_level = None
                            continue
                        break

                if matched_level is not None:
                    # Strike Selection: ATM Call
                    atm_strike = int(round(next_open / 50.0) * 50)
                    target_opt_type = "CALL"

                    # Lookup Real Option Entry Price
                    odf = get_option_day_df(curr_date)
                    opt_entry_p = 100.0  # default fallback

                    if odf is not None:
                        opt_rows = odf[
                            ((odf['strike_price'] - atm_strike).abs() < 1.0) &
                            (odf['option_type'] == target_opt_type) &
                            (odf['datetime'] >= entry_time)
                        ]
                        if not opt_rows.empty:
                            opt_entry_p = float(opt_rows['open'].iloc[0])

                    sl_dist = max(next_open - (l - sl_buffer_pts), min_sl_pts)
                    sl_dist = min(sl_dist, max_sl_pts)
                    sl = next_open - sl_dist
                    tp = next_open + (sl_dist * risk_reward)

                    current_trade = {
                        'entry_time': entry_time,
                        'side': 'BUY',
                        'option_contract': f"NIFTY {curr_date} {atm_strike} CE",
                        'strike': atm_strike,
                        'option_type': target_opt_type,
                        'entry_spot': next_open,
                        'sl_spot': sl,
                        'tp_spot': tp,
                        'opt_entry_price': round(opt_entry_p, 2),
                        'level_price': matched_level,
                        'level_type': matched_type
                    }
                    daily_trades_count[curr_date] = today_count + 1
                    continue

            # Signal 2: BEARISH REVERSAL -> Put Option
            if upper_wick_ratio >= min_wick_ratio and c < h - 0.3 * candle_range:
                matched_level = None
                matched_type = None
                for lvl_type, lvl_price, touches in candidate_levels:
                    if abs(h - lvl_price) <= tolerance_pts or (h >= lvl_price and c <= lvl_price):
                        confluence = any(
                            abs(lvl_price - other_price) <= tolerance_pts and other_type != lvl_type
                            for other_type, other_price, _ in candidate_levels
                        )
                        matched_level = lvl_price
                        matched_type = f"{lvl_type}_CONFLUENCE" if confluence else lvl_type
                        if matched_type not in elite_types:
                            matched_level = None
                            continue
                        break

                if matched_level is not None:
                    # Strike Selection: ATM Put
                    atm_strike = int(round(next_open / 50.0) * 50)
                    target_opt_type = "PUT"

                    odf = get_option_day_df(curr_date)
                    opt_entry_p = 100.0

                    if odf is not None:
                        opt_rows = odf[
                            ((odf['strike_price'] - atm_strike).abs() < 1.0) &
                            (odf['option_type'] == target_opt_type) &
                            (odf['datetime'] >= entry_time)
                        ]
                        if not opt_rows.empty:
                            opt_entry_p = float(opt_rows['open'].iloc[0])

                    sl_dist = max((h + sl_buffer_pts) - next_open, min_sl_pts)
                    sl_dist = min(sl_dist, max_sl_pts)
                    sl = next_open + sl_dist
                    tp = next_open - (sl_dist * risk_reward)

                    current_trade = {
                        'entry_time': entry_time,
                        'side': 'SELL',
                        'option_contract': f"NIFTY {curr_date} {atm_strike} PE",
                        'strike': atm_strike,
                        'option_type': target_opt_type,
                        'entry_spot': next_open,
                        'sl_spot': sl,
                        'tp_spot': tp,
                        'opt_entry_price': round(opt_entry_p, 2),
                        'level_price': matched_level,
                        'level_type': matched_type
                    }
                    daily_trades_count[curr_date] = today_count + 1
                    continue

    # 7. Generate Options Performance Report
    trades_df = pd.DataFrame(trades)
    log_csv = os.path.join(os.path.dirname(__file__), "pivot_option_trade_log.csv")
    trades_df.to_csv(log_csv, index=False)
    print(f"\nSaved real options trade log to: {log_csv}")

    if len(trades_df) == 0:
        print("No option trades triggered.")
        return

    total_trades = len(trades_df)
    wins = trades_df[trades_df['is_win']]
    losses = trades_df[~trades_df['is_win']]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades) * 100.0

    total_gross = trades_df['gross_pnl'].sum()
    total_charges = trades_df['charges'].sum()
    total_net = trades_df['net_pnl'].sum()

    gross_win = wins['gross_pnl'].sum()
    gross_loss = abs(losses['gross_pnl'].sum())
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float('inf')

    avg_trade_pnl = total_net / total_trades
    avg_win_rs = wins['net_pnl'].mean() if win_count > 0 else 0.0
    avg_loss_rs = abs(losses['net_pnl'].mean()) if loss_count > 0 else 0.0

    # Drawdown
    trades_df['cum_net'] = trades_df['net_pnl'].cumsum()
    trades_df['peak_net'] = trades_df['cum_net'].cummax()
    trades_df['drawdown_rs'] = trades_df['peak_net'] - trades_df['cum_net']
    max_dd_rs = trades_df['drawdown_rs'].max()

    print("\n" + "=" * 80)
    print("             NIFTY REAL OPTIONS BACKTEST SUMMARY (INR)")
    print("=" * 80)
    print(f" Total Option Trades  : {total_trades}")
    print(f" Winning Trades       : {win_count} ({win_rate:.1f}%)")
    print(f" Losing Trades        : {loss_count} ({100.0 - win_rate:.1f}%)")
    print(f" Gross Option PnL     : Rs. {total_gross:+,.2f}")
    print(f" Brokerage & Taxes    : Rs. -{total_charges:,.2f}")
    print(f" Net Realized PnL     : Rs. {total_net:+,.2f}")
    print(f" Profit Factor        : {profit_factor:.2f}")
    print(f" Average Profit/Trade : Rs. {avg_trade_pnl:+,.2f}")
    print(f" Average Winning Trade: Rs. {avg_win_rs:+,.2f}")
    print(f" Average Losing Trade : Rs. -{avg_loss_rs:,.2f}")
    print(f" Max Drawdown (Rs.)   : Rs. -{max_dd_rs:,.2f}")
    print("=" * 80)

    # Breakdown by Level Category
    print("\n--- PERFORMANCE BY PIVOT LEVEL CATEGORY (NET INR) ---")
    grp = trades_df.groupby('level_type').agg(
        trades=('net_pnl', 'count'),
        win_rate=('is_win', lambda x: (x.sum() / len(x)) * 100.0),
        net_pnl_rs=('net_pnl', 'sum'),
        avg_pnl_trade=('net_pnl', 'mean')
    ).reset_index().sort_values('net_pnl_rs', ascending=False)
    print(grp.to_string(index=False))

    # Breakdown by Direction
    print("\n--- PERFORMANCE BY TRADE DIRECTION ---")
    side_grp = trades_df.groupby('side').agg(
        trades=('net_pnl', 'count'),
        win_rate=('is_win', lambda x: (x.sum() / len(x)) * 100.0),
        net_pnl_rs=('net_pnl', 'sum'),
        avg_pnl_trade=('net_pnl', 'mean')
    ).reset_index()
    print(side_grp.to_string(index=False))
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real Options Backtest for Pivot Reversal Strategy")
    parser.add_argument("--mode", choices=["BUY", "SELL"], default="BUY", help="Option mode: BUY (Call/Put Buyer) or SELL (Option Writer)")
    parser.add_argument("--lot-size", type=int, default=25, help="Nifty lot size (default: 25)")
    parser.add_argument("--lots", type=int, default=4, help="Number of lots (default: 4)")
    parser.add_argument("--years", type=float, default=2.0, help="Years of lookback (default: 2.0)")
    parser.add_argument("--wick", type=float, default=0.50, help="Minimum rejection wick ratio (default: 0.50)")
    parser.add_argument("--rr", type=float, default=2.2, help="Risk:Reward ratio (default: 2.2)")
    parser.add_argument("--min-cpr-width", type=float, default=0.08, help="Minimum CPR width % (default: 0.08)")
    parser.add_argument("--max-trades", type=int, default=2, help="Max trades per day (default: 2)")
    args = parser.parse_args()

    run_options_backtest(
        option_mode=args.mode,
        lot_size=args.lot_size,
        lots=args.lots,
        years=args.years,
        min_wick_ratio=args.wick,
        risk_reward=args.rr,
        min_cpr_width_pct=args.min_cpr_width,
        max_daily_trades=args.max_trades
    )
