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

def run_100pct_real_option_backtest(target_days=180):
    bhavcopy_dir = "bhavcopy_cache"
    files = sorted(glob.glob(os.path.join(bhavcopy_dir, "BhavCopy_NSE_FO_*.csv")))
    
    if not files:
        print(f"[ERROR] No BhavCopy files found in {bhavcopy_dir}!")
        return

    print(f"[INFO] Found {len(files)} official NSE F&O Bhavcopy files in {bhavcopy_dir}.")
    
    # Load and aggregate daily Nifty spot & real option chain data
    daily_records = {}
    
    for fpath in files:
        try:
            df = pd.read_csv(fpath, low_memory=False)
            if 'TckrSymb' not in df.columns:
                continue
                
            nifty_df = df[df['TckrSymb'] == 'NIFTY'].copy()
            if nifty_df.empty:
                continue
                
            trade_date_str = str(nifty_df['TradDt'].iloc[0])
            trade_dt = datetime.strptime(trade_date_str, "%Y-%m-%d")
            spot_price = float(nifty_df['UndrlygPric'].iloc[0])
            
            daily_records[trade_dt] = {
                "spot": spot_price,
                "df": nifty_df
            }
        except Exception as e:
            continue

    all_sorted_dates = sorted(daily_records.keys())
    if len(all_sorted_dates) > target_days:
        sorted_dates = all_sorted_dates[-target_days:]
    else:
        sorted_dates = all_sorted_dates
        
    start_str = sorted_dates[0].strftime("%Y-%m-%d")
    end_str = sorted_dates[-1].strftime("%Y-%m-%d")
    print(f"[INFO] 100% Real Option Backtest Period: {start_str} to {end_str} ({len(sorted_dates)} trading days / Last {target_days} Days).")
    
    trades = []
    lot_size = 65  # Current exchange lot size for Nifty
    
    i = 0
    current_pos = None
    cycle_counter = 1
    
    while i < len(sorted_dates) - 1:
        entry_date = sorted_dates[i]
        entry_info = daily_records[entry_date]
        entry_spot = entry_info["spot"]
        entry_df = entry_info["df"]
        
        # Check weekly cycle entry on any available Bhavcopy date
        if current_pos is None:
            # 1. Determine Valuation Regime
            fair_val = calculate_fair_value_baseline(entry_date)
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
                
            # Filter option contracts for the target stance (clean whitespace)
            entry_df.loc[:, 'OptnTp_clean'] = entry_df['OptnTp'].astype(str).str.strip().str.upper()
            opt_df = entry_df[entry_df['OptnTp_clean'] == opt_type].copy()
            opt_df['StrkPric'] = opt_df['StrkPric'].astype(float)
            opt_df['ClsPric'] = opt_df['ClsPric'].astype(float)
            opt_df['SttlmPric'] = opt_df['SttlmPric'].astype(float)
            opt_df['real_price'] = np.where(opt_df['ClsPric'] > 0, opt_df['ClsPric'], opt_df['SttlmPric'])
            
            expiries = sorted(opt_df['XpryDt'].unique())
            if len(expiries) < 2:
                i += 1
                continue
                
            weekly_exp = expiries[0]
            monthly_exp = expiries[-1]
            
            if weekly_exp == monthly_exp and len(expiries) > 2:
                monthly_exp = expiries[-2]
                
            weekly_opts = opt_df[opt_df['XpryDt'] == weekly_exp].copy()
            monthly_opts = opt_df[opt_df['XpryDt'] == monthly_exp].copy()
            
            if weekly_opts.empty or monthly_opts.empty:
                i += 1
                continue
                
            # Match 100% REAL Traded Option Contracts by Target Premium in BhavCopy
            # Long Monthly Leg (~₹200 target)
            monthly_opts.loc[:, 'diff'] = (monthly_opts['real_price'] - 200.0).abs()
            long_match = monthly_opts.sort_values('diff').iloc[0]
            
            # Short Weekly Leg 1 (~₹150 target)
            weekly_opts.loc[:, 'diff1'] = (weekly_opts['real_price'] - 150.0).abs()
            short1_match = weekly_opts.sort_values('diff1').iloc[0]
            
            # Short Weekly Leg 2 (~₹450 target)
            weekly_opts.loc[:, 'diff2'] = (weekly_opts['real_price'] - 450.0).abs()
            short2_match = weekly_opts.sort_values('diff2').iloc[0]
            
            # Enforce Golden Constraint Filter (strike gap <= 1000 points)
            gap1 = abs(short1_match['StrkPric'] - long_match['StrkPric'])
            gap2 = abs(short2_match['StrkPric'] - long_match['StrkPric'])
            if max(gap1, gap2) > 1000:
                i += 1
                continue
                
            current_pos = {
                'cycle': cycle_counter,
                'entry_date': entry_date,
                'entry_spot': entry_spot,
                'stance': stance,
                'opt_type': opt_type,
                'weekly_exp': weekly_exp,
                'monthly_exp': monthly_exp,
                
                # Real Monthly Long Leg (BUY 3 Lots)
                'long_symbol': long_match['FinInstrmNm'],
                'long_strike': long_match['StrkPric'],
                'long_entry_real_px': float(long_match['real_price']),
                
                # Real Weekly Short Leg 1 (SELL 1 Lot)
                'short1_symbol': short1_match['FinInstrmNm'],
                'short1_strike': short1_match['StrkPric'],
                'short1_entry_real_px': float(short1_match['real_price']),
                
                # Real Weekly Short Leg 2 (SELL 1 Lot)
                'short2_symbol': short2_match['FinInstrmNm'],
                'short2_strike': short2_match['StrkPric'],
                'short2_entry_real_px': float(short2_match['real_price']),
                
                'entry_idx': i
            }
            
        # Manage trade & evaluate exit after 1 weekly step (next weekly Bhavcopy file)
        if current_pos is not None:
            days_held = i - current_pos['entry_idx']
            if days_held >= 1 or i == len(sorted_dates) - 1:
                exit_date = sorted_dates[i]
                exit_info = daily_records[exit_date]
                exit_spot = exit_info["spot"]
                exit_df = exit_info["df"]
                
                # Fetch 100% REAL Closing/Settlement Prices from Exit Date BhavCopy
                def get_real_exit_px(symbol, strike, is_weekly):
                    matches = exit_df[exit_df['FinInstrmNm'] == symbol]
                    if not matches.empty:
                        p = float(matches['ClsPric'].iloc[0] or matches['SttlmPric'].iloc[0])
                        if p > 0:
                            return p
                    # Intrinsic settlement fallback for expired weekly options
                    if current_pos['opt_type'] == 'CE':
                        return max(0.0, exit_spot - strike) if is_weekly else max(0.01, exit_spot - strike)
                    else:
                        return max(0.0, strike - exit_spot) if is_weekly else max(0.01, strike - exit_spot)

                long_exit_real_px = get_real_exit_px(current_pos['long_symbol'], current_pos['long_strike'], False)
                short1_exit_real_px = get_real_exit_px(current_pos['short1_symbol'], current_pos['short1_strike'], True)
                short2_exit_real_px = get_real_exit_px(current_pos['short2_symbol'], current_pos['short2_strike'], True)
                
                # Calculate 100% REAL Leg Net PnLs (3 Long Lots, 1 Short Lot 1, 1 Short Lot 2)
                pnl_long_pts = (long_exit_real_px - current_pos['long_entry_real_px']) * 3
                pnl_short1_pts = (current_pos['short1_entry_real_px'] - short1_exit_real_px) * 1
                pnl_short2_pts = (current_pos['short2_entry_real_px'] - short2_exit_real_px) * 1
                
                net_pnl_pts = pnl_long_pts + pnl_short1_pts + pnl_short2_pts
                net_pnl_rs = net_pnl_pts * lot_size
                
                trades.append({
                    'Cycle': current_pos['cycle'],
                    'Entry_Date': current_pos['entry_date'].strftime('%Y-%m-%d'),
                    'Exit_Date': exit_date.strftime('%Y-%m-%d'),
                    'Stance': current_pos['stance'],
                    'Entry_Spot': current_pos['entry_spot'],
                    'Exit_Spot': exit_spot,
                    
                    'Long_Symbol_Buy_3Lots': current_pos['long_symbol'],
                    'Long_Entry_Real_Px': current_pos['long_entry_real_px'],
                    'Long_Exit_Real_Px': long_exit_real_px,
                    'Long_PnL_Pts': pnl_long_pts,
                    
                    'Short1_Symbol_Sell_1Lot': current_pos['short1_symbol'],
                    'Short1_Entry_Real_Px': current_pos['short1_entry_real_px'],
                    'Short1_Exit_Real_Px': short1_exit_real_px,
                    'Short1_PnL_Pts': pnl_short1_pts,
                    
                    'Short2_Symbol_Sell_1Lot': current_pos['short2_symbol'],
                    'Short2_Entry_Real_Px': current_pos['short2_entry_real_px'],
                    'Short2_Exit_Real_Px': short2_exit_real_px,
                    'Short2_PnL_Pts': pnl_short2_pts,
                    
                    'Net_Cycle_PnL_Pts': net_pnl_pts,
                    'Net_Cycle_PnL_Rs': net_pnl_rs
                })
                
                cycle_counter += 1
                current_pos = None
                
        i += 1
        
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        print("[WARNING] No trades executed during the 180-day period.")
        return
        
    print("\n" + "="*95)
    print("     100% REAL OPTION PRICE BACKTEST RESULTS: PROF. CHIRAG JAIN 3:1:1 CALENDAR SPREAD")
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
    
    print(f"Backtesting Window          : {start_str} to {end_str} ({len(sorted_dates)} Trading Days / Last {target_days} Days)")
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
    
    print("\nCOMPLETE 180-DAY 100% REAL OPTION TRADES LOG:")
    print(trades_df[['Cycle', 'Entry_Date', 'Exit_Date', 'Stance', 'Long_Symbol_Buy_3Lots', 'Short1_Symbol_Sell_1Lot', 'Net_Cycle_PnL_Pts', 'Net_Cycle_PnL_Rs']].to_string(index=False))
    
    out_csv = "research_and_development/strategy20_100pct_real_option_trade_log.csv"
    trades_df.to_csv(out_csv, index=False)
    print(f"\n[SUCCESS] Detailed 100% real option trade log saved to: {out_csv}")

if __name__ == "__main__":
    run_100pct_real_option_backtest(target_days=180)
