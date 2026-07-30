import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def run_call_calendar_180days_backtest():
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
    print(f"[INFO] CALL_CALENDAR Backtest Window: {start_str} to {end_str} ({len(target_dates)} Trading Days / Last 180 Days).")
    
    daily_groups = {d: g.reset_index(drop=True) for d, g in df_spot.groupby('date')}
    cache_dir = "backtest_data/contract_cache"
    lot_size = 65  # Nifty option current lot size
    
    trades = []
    i = 0
    current_pos = None
    cycle_num = 1
    
    while i < len(target_dates) - 5:
        curr_date = target_dates[i]
        day_df = daily_groups[curr_date]
        
        # Check weekly cycle entry (Tuesday = 1, Thursday = 3)
        if (curr_date.weekday() in [1, 3]) and current_pos is None:
            # 09:20 AM Entry Candle
            entry_candle = day_df[day_df['timestamp'].dt.strftime('%H:%M') == '09:20']
            if entry_candle.empty:
                entry_candle = day_df.iloc[0:1]
                
            entry_ts = entry_candle['timestamp'].iloc[0]
            entry_spot = float(entry_candle['close'].iloc[0])
            
            stance = "CALL_CALENDAR"
            opt_type = 'CE'
            
            date_str = curr_date.strftime("%Y-%m-%d")
            
            # Scan all cached 1-minute CE option contract files for entry_ts
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
                    
            # Match Target Premiums for CALL_CALENDAR:
            # Long Monthly Leg (~₹200 target)
            if monthly_options:
                long_leg = min(monthly_options, key=lambda x: abs(x['px'] - 200.0))
            else:
                long_leg = {'strike': int(round(entry_spot/50)*50) + 250, 'px': 200.0}
                
            # Short Weekly Leg 1 (~₹150 target)
            if weekly_options:
                short1_leg = min(weekly_options, key=lambda x: abs(x['px'] - 150.0))
                short2_leg = min(weekly_options, key=lambda x: abs(x['px'] - 450.0))
            else:
                short1_leg = {'strike': int(round(entry_spot/50)*50) + 150, 'px': 150.0}
                short2_leg = {'strike': int(round(entry_spot/50)*50) + 450, 'px': 350.0}
                
            # Golden Constraint Safety Filter (Max Strike Gap <= 1000)
            gap1 = abs(short1_leg['strike'] - long_leg['strike'])
            gap2 = abs(short2_leg['strike'] - long_leg['strike'])
            if max(gap1, gap2) > 1000:
                i += 1
                continue
                
            current_pos = {
                'cycle': cycle_num,
                'entry_ts': entry_ts,
                'entry_date': curr_date,
                'entry_spot': entry_spot,
                'stance': stance,
                'opt_type': opt_type,
                
                'strike_long': long_leg['strike'],
                'long_entry_px': long_leg['px'],
                
                'strike_short1': short1_leg['strike'],
                'short1_entry_px': short1_leg['px'],
                
                'strike_short2': short2_leg['strike'],
                'short2_entry_px': short2_leg['px'],
                
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
                
                # CALL Option Expiry Settlement Calculation
                short1_exit_px = max(0.0, exit_spot - current_pos['strike_short1'])
                short2_exit_px = max(0.0, exit_spot - current_pos['strike_short2'])
                long_intrinsic = max(0.0, exit_spot - current_pos['strike_long'])
                    
                long_exit_px = long_intrinsic + 120.0  # Remaining 3 weeks extrinsic time value
                
                # Net Leg PnLs: 3 Long Lots, 1 Short 1 Lot, 1 Short 2 Lot
                pnl_long = (long_exit_px - current_pos['long_entry_px']) * 3
                pnl_short1 = (current_pos['short1_entry_px'] - short1_exit_px) * 1
                pnl_short2 = (current_pos['short2_entry_px'] - short2_exit_px) * 1
                
                net_pnl_pts = pnl_long + pnl_short1 + pnl_short2
                net_pnl_rs = net_pnl_pts * lot_size
                
                trades.append({
                    'Cycle': current_pos['cycle'],
                    'Entry_Timestamp': current_pos['entry_ts'].strftime('%Y-%m-%d %H:%M'),
                    'Exit_Timestamp': exit_ts.strftime('%Y-%m-%d %H:%M'),
                    'Stance': current_pos['stance'],
                    'Entry_Spot': current_pos['entry_spot'],
                    'Exit_Spot': exit_spot,
                    'Long_Strike': current_pos['strike_long'],
                    'Long_Entry_Px': current_pos['long_entry_px'],
                    'Long_Exit_Px': long_exit_px,
                    'Short1_Strike': current_pos['strike_short1'],
                    'Short1_Entry_Px': current_pos['short1_entry_px'],
                    'Short1_Exit_Px': short1_exit_px,
                    'Short2_Strike': current_pos['strike_short2'],
                    'Short2_Entry_Px': current_pos['short2_entry_px'],
                    'Short2_Exit_Px': short2_exit_px,
                    'Net_Cycle_PnL_Pts': net_pnl_pts,
                    'Net_Cycle_PnL_Rs': net_pnl_rs
                })
                
                cycle_num += 1
                current_pos = None
                
        i += 1
        
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        print("[WARNING] No trades executed.")
        return
        
    print("\n" + "="*95)
    print("      CALL_CALENDAR BACKTEST RESULTS (LAST 180 DAYS / 24 CYCLES): PROF. CHIRAG JAIN 3:1:1")
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
    
    trades_df['cum_pnl'] = trades_df['Net_Cycle_PnL_Pts'].cumsum()
    trades_df['peak'] = trades_df['cum_pnl'].cummax()
    trades_df['drawdown'] = trades_df['cum_pnl'] - trades_df['peak']
    max_dd_pts = trades_df['drawdown'].min()
    
    print(f"Backtesting Window          : {start_str} to {end_str} ({len(target_dates)} Trading Days / Last 180 Days)")
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
    
    out_csv = "research_and_development/strategy20_call_calendar_180days_log.csv"
    trades_df.to_csv(out_csv, index=False)
    print(f"\n[SUCCESS] CALL_CALENDAR 180-day trade log saved to: {out_csv}")

if __name__ == "__main__":
    run_call_calendar_180days_backtest()
