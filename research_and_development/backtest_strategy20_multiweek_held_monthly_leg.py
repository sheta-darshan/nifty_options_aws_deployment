import os
import glob
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

def run_multiweek_held_monthly_leg_backtest():
    spot_path = "backtest_data/nifty_spot.csv"
    if not os.path.exists(spot_path):
        print(f"[ERROR] {spot_path} not found!")
        return

    print(f"[INFO] Reading historical 1-minute Nifty spot candle data from {spot_path}...")
    df_spot = pd.read_csv(spot_path)
    df_spot['timestamp'] = pd.to_datetime(df_spot['timestamp'])
    df_spot = df_spot.sort_values('timestamp').reset_index(drop=True)
    df_spot['date'] = df_spot['timestamp'].dt.date
    
    # Filter to last 180 trading days
    unique_dates = sorted(df_spot['date'].unique())
    if len(unique_dates) > 180:
        target_dates = unique_dates[-180:]
        df_spot = df_spot[df_spot['date'].isin(target_dates)].reset_index(drop=True)
    else:
        target_dates = unique_dates
        
    start_str = target_dates[0].strftime("%Y-%m-%d")
    end_str = target_dates[-1].strftime("%Y-%m-%d")
    print(f"[INFO] Multi-Week Held Monthly Leg Backtest Window: {start_str} to {end_str} ({len(target_dates)} Trading Days / Last 180 Days).")
    
    daily_groups = {d: g.reset_index(drop=True) for d, g in df_spot.groupby('date')}
    cache_dir = "backtest_data/contract_cache"
    lot_size = 65  # Nifty option current lot size
    
    trades = []
    i = 0
    cycle_num = 1
    
    open_monthly_long = None
    
    while i < len(target_dates) - 5:
        curr_date = target_dates[i]
        curr_dt = datetime.combine(curr_date, datetime.min.time())
        day_df = daily_groups[curr_date]
        
        # Check weekly cycle entry (Tuesday = 1, Thursday = 3)
        if (curr_date.weekday() in [1, 3]):
            # 09:20 AM Entry Candle
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
                
            date_str = curr_date.strftime("%Y-%m-%d")
            
            # Scan cached option files
            pattern = os.path.join(cache_dir, f"nifty_*_{opt_type}_*_{date_str}.csv")
            cached_files = glob.glob(pattern)
            
            weekly_options = []
            monthly_options = []
            
            for f in cached_files:
                try:
                    fname = os.path.basename(f)
                    parts = fname.split('_')
                    strike = int(parts[1])
                    exp_idx = int(parts[3].replace('exp', ''))
                    
                    cdf = pd.read_csv(f)
                    cdf['timestamp'] = pd.to_datetime(cdf['timestamp'])
                    ts_row = cdf[cdf['timestamp'] == entry_ts]
                    if not ts_row.empty:
                        px = float(ts_row['close'].iloc[0])
                        if px > 0:
                            node = {'strike': strike, 'px': px, 'file': f, 'exp_idx': exp_idx}
                            if exp_idx == 0:
                                weekly_options.append(node)
                            else:
                                monthly_options.append(node)
                except Exception:
                    continue
                    
            # 1. If Monthly Long Leg is not open, open a new Monthly Long Leg (~₹200 target)
            if open_monthly_long is None:
                if monthly_options:
                    long_leg = min(monthly_options, key=lambda x: abs(x['px'] - 200.0))
                else:
                    long_leg = {'strike': int(round(entry_spot/50)*50) - 250 if opt_type=='PE' else int(round(entry_spot/50)*50) + 250, 'px': 200.0}
                open_monthly_long = {
                    'entry_date': curr_date,
                    'entry_ts': entry_ts,
                    'entry_spot': entry_spot,
                    'strike': long_leg['strike'],
                    'entry_px': long_leg['px'],
                    'opt_type': opt_type,
                    'weeks_held': 0
                }
            else:
                long_leg = {'strike': open_monthly_long['strike'], 'px': open_monthly_long['entry_px']}
                
            # 2. Select Weekly Short Legs (~₹150 & ~₹450 targets)
            if weekly_options:
                short1_leg = min(weekly_options, key=lambda x: abs(x['px'] - 150.0))
                short2_leg = min(weekly_options, key=lambda x: abs(x['px'] - 450.0))
            else:
                short1_leg = {'strike': int(round(entry_spot/50)*50) - 150 if opt_type=='PE' else int(round(entry_spot/50)*50) + 150, 'px': 150.0}
                short2_leg = {'strike': int(round(entry_spot/50)*50) - 450 if opt_type=='PE' else int(round(entry_spot/50)*50) + 450, 'px': 350.0}
                
            # Evaluate weekly exit 5 trading days later
            exit_idx = min(i + 5, len(target_dates) - 1)
            exit_date = target_dates[exit_idx]
            exit_day_df = daily_groups[exit_date]
            exit_candle = exit_day_df[exit_day_df['timestamp'].dt.strftime('%H:%M') == '15:20']
            if exit_candle.empty:
                exit_candle = exit_day_df.iloc[-1:]
            exit_ts = exit_candle['timestamp'].iloc[0]
            exit_spot = float(exit_candle['close'].iloc[0])
            
            # Settlement of Weekly Short Legs
            if opt_type == 'PE':
                short1_exit_px = max(0.0, short1_leg['strike'] - exit_spot)
                short2_exit_px = max(0.0, short2_leg['strike'] - exit_spot)
            else:
                short1_exit_px = max(0.0, exit_spot - short1_leg['strike'])
                short2_exit_px = max(0.0, exit_spot - short2_leg['strike'])
                
            short1_pnl_pts = (short1_leg['px'] - short1_exit_px) * 1
            short2_pnl_pts = (short2_leg['px'] - short2_exit_px) * 1
            
            open_monthly_long['weeks_held'] += 1
            
            # Check if monthly expiry reached (held for 4 weeks or end of month)
            is_monthly_expiry_roll = (open_monthly_long['weeks_held'] >= 4) or (exit_idx == len(target_dates) - 1)
            
            if is_monthly_expiry_roll:
                if opt_type == 'PE':
                    long_intrinsic = max(0.0, open_monthly_long['strike'] - exit_spot)
                else:
                    long_intrinsic = max(0.0, exit_spot - open_monthly_long['strike'])
                long_exit_px = long_intrinsic  # Fully expired / settled at intrinsic value on monthly expiry
                long_pnl_pts = (long_exit_px - open_monthly_long['entry_px']) * 3
                open_monthly_long = None  # Reset monthly long position
                monthly_action = "MONTHLY_EXPIRY_CLOSED_AND_ROLLED"
            else:
                long_exit_px = 0.0  # Kept open across weekly roll
                long_pnl_pts = 0.0  # Unrealized across weekly roll
                monthly_action = f"MONTHLY_HELD_OPEN_WEEK_{open_monthly_long['weeks_held']}"
                
            net_pnl_pts = short1_pnl_pts + short2_pnl_pts + long_pnl_pts
            net_pnl_rs = net_pnl_pts * lot_size
            
            trades.append({
                'Cycle': cycle_num,
                'Entry_Timestamp': entry_ts.strftime('%Y-%m-%d %H:%M'),
                'Exit_Timestamp': exit_ts.strftime('%Y-%m-%d %H:%M'),
                'Stance': stance,
                'Entry_Spot': entry_spot,
                'Exit_Spot': exit_spot,
                'Monthly_Long_Strike': long_leg['strike'],
                'Monthly_Status': monthly_action,
                'Short1_Strike': short1_leg['strike'],
                'Short1_PnL_Pts': short1_pnl_pts,
                'Short2_Strike': short2_leg['strike'],
                'Short2_PnL_Pts': short2_pnl_pts,
                'Long_PnL_Pts': long_pnl_pts,
                'Net_Cycle_PnL_Pts': net_pnl_pts,
                'Net_Cycle_PnL_Rs': net_pnl_rs
            })
            
            cycle_num += 1
            i = exit_idx
        else:
            i += 1
            
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        print("[WARNING] No trades executed.")
        return
        
    print("\n" + "="*95)
    print("   MULTI-WEEK HELD MONTHLY LEG BACKTEST (180 DAYS / 24 CYCLES): PROF. CHIRAG JAIN 3:1:1")
    print("="*95)
    
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['Net_Cycle_PnL_Pts'] > 0])
    losing_trades = len(trades_df[trades_df['Net_Cycle_PnL_Pts'] <= 0])
    win_rate = (winning_trades / total_trades) * 100
    
    total_pnl_pts = trades_df['Net_Cycle_PnL_Pts'].sum()
    total_pnl_rs = trades_df['Net_Cycle_PnL_Rs'].sum()
    avg_pnl_pts = trades_df['Net_Cycle_PnL_Pts'].mean()
    max_win_pts = trades_df['Net_Cycle_PnL_Pts'].max()
    max_loss_pts = trades_df['Net_Cycle_PnL_Pts'].min()
    
    print(f"Backtesting Window          : {start_str} to {end_str} ({len(target_dates)} Trading Days / Last 180 Days)")
    print(f"Total Weekly Decay Cycles   : {total_trades}")
    print(f"Winning Cycles              : {winning_trades} ({win_rate:.2f}%)")
    print(f"Losing Cycles               : {losing_trades} ({100 - win_rate:.2f}%)")
    print(f"Total Net PnL (Points)      : {total_pnl_pts:+.2f} pts")
    print(f"Total Net PnL (Rupees @ 65) : Rs. {total_pnl_rs:+,.2f}")
    print(f"Average Weekly Rollover     : {avg_pnl_pts:+.2f} pts / week")
    print(f"Max Single Cycle Gain       : {max_win_pts:+.2f} pts (+Rs. {max_win_pts * lot_size:,.2f})")
    print(f"Max Single Cycle Loss       : {max_loss_pts:+.2f} pts (Rs. {max_loss_pts * lot_size:,.2f})")
    print("="*95)
    
    print("\nCOMPLETE MULTI-WEEK HELD MONTHLY LEG LOG:")
    print(trades_df[['Cycle', 'Entry_Timestamp', 'Exit_Timestamp', 'Stance', 'Monthly_Status', 'Net_Cycle_PnL_Pts', 'Net_Cycle_PnL_Rs']].to_string(index=False))
    
    out_csv = "research_and_development/strategy20_multiweek_held_monthly_leg_log.csv"
    trades_df.to_csv(out_csv, index=False)
    print(f"\n[SUCCESS] Multi-week held monthly leg trade log saved to: {out_csv}")

if __name__ == "__main__":
    run_multiweek_held_monthly_leg_backtest()
