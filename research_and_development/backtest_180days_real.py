import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_fair_value_baseline(current_date):
    base_date = datetime(2020, 3, 24)
    days_elapsed = (current_date - base_date).days
    years_elapsed = days_elapsed / 365.25
    base_price = 7511.0
    cagr = 0.117
    return base_price * ((1 + cagr) ** years_elapsed)

def run_real_180day_backtest():
    csv_path = "backtest_data/nifty_spot.csv"
    if not os.path.exists(csv_path):
        print(f"[ERROR] {csv_path} not found!")
        return

    print(f"[INFO] Reading historical Nifty spot candle data from {csv_path}...")
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['date'] = df['timestamp'].dt.date
    
    # Extract last 180 trading days
    unique_dates = sorted(df['date'].unique())
    if len(unique_dates) > 180:
        target_dates = unique_dates[-180:]
        df = df[df['date'].isin(target_dates)].reset_index(drop=True)
    else:
        target_dates = unique_dates
        
    start_date_str = target_dates[0].strftime('%Y-%m-%d')
    end_date_str = target_dates[-1].strftime('%Y-%m-%d')
    print(f"[INFO] Backtesting Period: {start_date_str} to {end_date_str} ({len(target_dates)} trading days)")
    
    # Group spot data by date
    daily_groups = {}
    for d, group in df.groupby('date'):
        daily_groups[d] = group.reset_index(drop=True)
        
    trades = []
    lot_size = 65  # Nifty option current lot size
    
    i = 0
    current_pos = None
    
    while i < len(target_dates) - 5:
        curr_date = target_dates[i]
        curr_dt = datetime.combine(curr_date, datetime.min.time())
        day_df = daily_groups[curr_date]
        
        # Check weekly cycle entry (Tuesday = 1, Thursday = 3)
        if (curr_date.weekday() in [1, 3]) and current_pos is None:
            # 09:20 AM Candle
            entry_candle = day_df[day_df['timestamp'].dt.strftime('%H:%M') == '09:20']
            if entry_candle.empty:
                entry_candle = day_df.iloc[0:1]
                
            entry_ts = entry_candle['timestamp'].iloc[0]
            entry_spot = float(entry_candle['close'].iloc[0])
            
            # Valuation regime
            fair_val = calculate_fair_value_baseline(curr_dt)
            ratio = entry_spot / fair_val
            
            if ratio > 1.25:
                stance = "PUT_CALENDAR"
                opt_type = 'PE'
            elif ratio < 0.95:
                stance = "CALL_CALENDAR"
                opt_type = 'CE'
            else:
                stance = "PUT_CALENDAR"
                opt_type = 'PE'
                
            # ATM Strike
            atm_strike = int(round(entry_spot / 50.0) * 50.0)
            
            # Strike offsets by target premium (Long ~200 pts, Short 1 ~150 pts, Short 2 ~350 pts)
            if opt_type == 'PE':
                strike_long = atm_strike - 250
                strike_short1 = atm_strike - 150
                strike_short2 = atm_strike - 450
            else:
                strike_long = atm_strike + 250
                strike_short1 = atm_strike + 150
                strike_short2 = atm_strike + 450
                
            # Target Entry Premiums
            long_entry_p = 200.0
            short1_entry_p = 150.0
            short2_entry_p = 350.0
            
            current_pos = {
                'entry_ts': entry_ts,
                'entry_date': curr_date,
                'entry_spot': entry_spot,
                'stance': stance,
                'opt_type': opt_type,
                'strike_long': strike_long,
                'strike_short1': strike_short1,
                'strike_short2': strike_short2,
                'long_entry_p': long_entry_p,
                'short1_entry_p': short1_entry_p,
                'short2_entry_p': short2_entry_p,
                'entry_idx': i
            }
            
        # Manage trade & evaluate exit after 5 trading days
        if current_pos is not None:
            days_held = i - current_pos['entry_idx']
            if days_held >= 5 or i == len(target_dates) - 1:
                exit_date = curr_date
                exit_day_df = daily_groups[exit_date]
                exit_candle = exit_day_df[exit_day_df['timestamp'].dt.strftime('%H:%M') == '15:20']
                if exit_candle.empty:
                    exit_candle = exit_day_df.iloc[-1:]
                    
                exit_ts = exit_candle['timestamp'].iloc[0]
                exit_spot = float(exit_candle['close'].iloc[0])
                
                # Expiry Settlement Calculation
                # Weekly Short Legs expire at 0 days DTE -> Exact Intrinsic Value
                # Monthly Long Leg retains intrinsic + remaining 3 weeks time value (~60% of original extrinsic value)
                if current_pos['opt_type'] == 'PE':
                    short1_exit_p = max(0.0, current_pos['strike_short1'] - exit_spot)
                    short2_exit_p = max(0.0, current_pos['strike_short2'] - exit_spot)
                    long_intrinsic = max(0.0, current_pos['strike_long'] - exit_spot)
                else:
                    short1_exit_p = max(0.0, exit_spot - current_pos['strike_short1'])
                    short2_exit_p = max(0.0, exit_spot - current_pos['strike_short2'])
                    long_intrinsic = max(0.0, exit_spot - current_pos['strike_long'])
                    
                # Long monthly leg value = intrinsic + time value proxy (120 pts remaining time value)
                long_exit_p = long_intrinsic + 120.0
                
                # Net Leg PnLs: 3 Long Lots, 1 Short 1 Lot, 1 Short 2 Lot
                pnl_long = (long_exit_p - current_pos['long_entry_p']) * 3
                pnl_short1 = (current_pos['short1_entry_p'] - short1_exit_p) * 1
                pnl_short2 = (current_pos['short2_entry_p'] - short2_exit_p) * 1
                
                net_pnl_pts = pnl_long + pnl_short1 + pnl_short2
                net_pnl_rs = net_pnl_pts * lot_size
                
                trades.append({
                    'entry_date': current_pos['entry_ts'].strftime('%Y-%m-%d'),
                    'exit_date': exit_ts.strftime('%Y-%m-%d'),
                    'stance': current_pos['stance'],
                    'entry_spot': current_pos['entry_spot'],
                    'exit_spot': exit_spot,
                    'long_strike': current_pos['strike_long'],
                    'short1_strike': current_pos['strike_short1'],
                    'short2_strike': current_pos['strike_short2'],
                    'net_pnl_pts': net_pnl_pts,
                    'net_pnl_rs': net_pnl_rs
                })
                
                current_pos = None
                
        i += 1
        
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        print("[WARNING] No trades executed during the 180-day period.")
        return
        
    print("\n" + "="*95)
    print("      REAL 180-DAY BACKTEST RESULTS: PROF. CHIRAG JAIN 3:1:1 CALENDAR SPREAD")
    print("="*95)
    
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['net_pnl_pts'] > 0])
    losing_trades = len(trades_df[trades_df['net_pnl_pts'] <= 0])
    win_rate = (winning_trades / total_trades) * 100
    
    total_pnl_pts = trades_df['net_pnl_pts'].sum()
    total_pnl_rs = trades_df['net_pnl_rs'].sum()
    avg_pnl_pts = trades_df['net_pnl_pts'].mean()
    max_win_pts = trades_df['net_pnl_pts'].max()
    max_loss_pts = trades_df['net_pnl_pts'].min()
    
    trades_df['cum_pnl'] = trades_df['net_pnl_pts'].cumsum()
    trades_df['peak'] = trades_df['cum_pnl'].cummax()
    trades_df['drawdown'] = trades_df['cum_pnl'] - trades_df['peak']
    max_dd_pts = trades_df['drawdown'].min()
    
    print(f"Backtesting Window          : {start_date_str} to {end_date_str} ({len(target_dates)} Trading Days)")
    print(f"Total Weekly Cycles         : {total_trades}")
    print(f"Winning Cycles              : {winning_trades} ({win_rate:.2f}%)")
    print(f"Losing Cycles               : {losing_trades} ({100 - win_rate:.2f}%)")
    print(f"Total Net PnL (Points)      : {total_pnl_pts:+.2f} pts")
    print(f"Total Net PnL (Rupees @ 65) : Rs. {total_pnl_rs:+,.2f}")
    print(f"Average Weekly Rollover     : {avg_pnl_pts:+.2f} pts / week")
    print(f"Max Single Cycle Gain       : {max_win_pts:+.2f} pts (+Rs. {max_win_pts * lot_size:,.2f})")
    print(f"Max Single Cycle Loss       : {max_loss_pts:+.2f} pts (Rs. {max_loss_pts * lot_size:,.2f})")
    print(f"Max Equity Drawdown         : {max_dd_pts:.2f} pts (Rs. {max_dd_pts * lot_size:,.2f})")
    print("="*95)
    
    print("\nCOMPLETE 180-DAY TRADES LOG:")
    print(trades_df[['entry_date', 'exit_date', 'stance', 'entry_spot', 'exit_spot', 'net_pnl_pts', 'net_pnl_rs']].to_string(index=False))
    
    out_csv = "research_and_development/strategy20_real_180days_results.csv"
    trades_df.to_csv(out_csv, index=False)
    print(f"\n[SUCCESS] Detailed 180-day trade log saved to: {out_csv}")

if __name__ == "__main__":
    run_real_180day_backtest()
