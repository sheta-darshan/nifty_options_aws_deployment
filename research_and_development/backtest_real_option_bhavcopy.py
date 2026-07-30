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

def run_real_option_bhavcopy_backtest():
    bhavcopy_dir = "bhavcopy_cache"
    files = sorted(glob.glob(os.path.join(bhavcopy_dir, "BhavCopy_NSE_FO_*.csv")))
    
    if not files:
        print(f"Error: No BhavCopy files found in {bhavcopy_dir}!")
        return

    print(f"Found {len(files)} real NSE F&O Bhavcopy files in {bhavcopy_dir}. Parsing Nifty Option contracts...")
    
    # Load and aggregate daily Nifty spot/option data from BhavCopy files
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
            
            # Underlying Spot Price
            spot_price = float(nifty_df['UndrlygPric'].iloc[0])
            
            daily_records[trade_dt] = {
                "spot": spot_price,
                "df": nifty_df
            }
        except Exception as e:
            continue

    sorted_dates = sorted(daily_records.keys())
    print(f"Loaded {len(sorted_dates)} trading days of real Nifty option chain data from {sorted_dates[0].strftime('%Y-%m-%d')} to {sorted_dates[-1].strftime('%Y-%m-%d')}.")
    
    trades = []
    lot_size = 65  # Nifty option lot size
    
    i = 0
    current_pos = None
    
    while i < len(sorted_dates) - 1:
        entry_date = sorted_dates[i]
        entry_info = daily_records[entry_date]
        entry_spot = entry_info["spot"]
        entry_df = entry_info["df"]
        
        # Check weekly cycle start (Tuesday = 1, Thursday = 3)
        if (entry_date.weekday() in [1, 3]) and current_pos is None:
            # 1. Regime Identification
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
                
            # Filter options for the current stance
            opt_df = entry_df[entry_df['OptnTp'] == opt_type].copy()
            opt_df['StrkPric'] = opt_df['StrkPric'].astype(float)
            opt_df['ClsPric'] = opt_df['ClsPric'].astype(float)
            opt_df['SttlmPric'] = opt_df['SttlmPric'].astype(float)
            opt_df['price'] = np.where(opt_df['ClsPric'] > 0, opt_df['ClsPric'], opt_df['SttlmPric'])
            
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
                
            # Match Strikes by Target Premium in REAL BhavCopy Data
            # Long Monthly Leg (~200 pts)
            monthly_opts.loc[:, 'diff'] = (monthly_opts['price'] - 200.0).abs()
            long_match = monthly_opts.sort_values('diff').iloc[0]
            
            # Short Weekly 1 (~150 pts)
            weekly_opts.loc[:, 'diff1'] = (weekly_opts['price'] - 150.0).abs()
            short1_match = weekly_opts.sort_values('diff1').iloc[0]
            
            # Short Weekly 2 (~350 pts)
            weekly_opts.loc[:, 'diff2'] = (weekly_opts['price'] - 350.0).abs()
            short2_match = weekly_opts.sort_values('diff2').iloc[0]
            
            # Golden Constraint Filter (1500 pts max)
            gap1 = abs(short1_match['StrkPric'] - long_match['StrkPric'])
            gap2 = abs(short2_match['StrkPric'] - long_match['StrkPric'])
            if max(gap1, gap2) > 1500:
                i += 1
                continue
                
            current_pos = {
                'entry_date': entry_date,
                'entry_spot': entry_spot,
                'stance': stance,
                'opt_type': opt_type,
                'weekly_exp': weekly_exp,
                'monthly_exp': monthly_exp,
                'long_strike': long_match['StrkPric'],
                'long_entry_price': long_match['price'],
                'long_symbol': long_match['FinInstrmNm'],
                'short1_strike': short1_match['StrkPric'],
                'short1_entry_price': short1_match['price'],
                'short1_symbol': short1_match['FinInstrmNm'],
                'short2_strike': short2_match['StrkPric'],
                'short2_entry_price': short2_match['price'],
                'short2_symbol': short2_match['FinInstrmNm'],
                'entry_idx': i
            }
            
        # Check Exit after ~5 trading days (next weekly cycle)
        if current_pos is not None:
            days_held = i - current_pos['entry_idx']
            if days_held >= 5 or i == len(sorted_dates) - 1:
                exit_date = sorted_dates[i]
                exit_info = daily_records[exit_date]
                exit_spot = exit_info["spot"]
                exit_df = exit_info["df"]
                
                # Fetch Real Settlement Prices from Exit Date BhavCopy
                def get_exit_price(symbol, fallback_strike, is_weekly):
                    matches = exit_df[exit_df['FinInstrmNm'] == symbol]
                    if not matches.empty:
                        p = float(matches['ClsPric'].iloc[0] or matches['SttlmPric'].iloc[0])
                        if p > 0:
                            return p
                    # Intrinsic Value Fallback if contract expired
                    if current_pos['opt_type'] == 'CE':
                        return max(0.0, exit_spot - fallback_strike) if is_weekly else max(0.01, (exit_spot - fallback_strike) * 0.5)
                    else:
                        return max(0.0, fallback_strike - exit_spot) if is_weekly else max(0.01, (fallback_strike - exit_spot) * 0.5)

                long_exit_price = get_exit_price(current_pos['long_symbol'], current_pos['long_strike'], False)
                short1_exit_price = get_exit_price(current_pos['short1_symbol'], current_pos['short1_strike'], True)
                short2_exit_price = get_exit_price(current_pos['short2_symbol'], current_pos['short2_strike'], True)
                
                # Net PnL in Points (3 Long Lots, 1 Short Lot 1, 1 Short Lot 2)
                pnl_long = (long_exit_price - current_pos['long_entry_price']) * 3
                pnl_short1 = (current_pos['short1_entry_price'] - short1_exit_price) * 1
                pnl_short2 = (current_pos['short2_entry_price'] - short2_exit_price) * 1
                
                net_pnl_pts = pnl_long + pnl_short1 + pnl_short2
                net_pnl_rs = net_pnl_pts * lot_size
                
                trades.append({
                    'entry_date': current_pos['entry_date'].strftime('%Y-%m-%d'),
                    'exit_date': exit_date.strftime('%Y-%m-%d'),
                    'stance': current_pos['stance'],
                    'entry_spot': current_pos['entry_spot'],
                    'exit_spot': exit_spot,
                    'long_symbol': current_pos['long_symbol'],
                    'long_entry': current_pos['long_entry_price'],
                    'long_exit': long_exit_price,
                    'short1_entry': current_pos['short1_entry_price'],
                    'short1_exit': short1_exit_price,
                    'short2_entry': current_pos['short2_entry_price'],
                    'short2_exit': short2_exit_price,
                    'net_pnl_pts': net_pnl_pts,
                    'net_pnl_rs': net_pnl_rs
                })
                
                current_pos = None
                
        i += 1
        
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        print("No trades executed.")
        return
        
    print("\n" + "="*95)
    print("   REAL NSE BHAVCOPY OPTION DATA BACKTEST: PROF. CHIRAG JAIN 3:1:1 CALENDAR SPREAD")
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
    
    print(f"Total Weekly Cycles Simulated : {total_trades}")
    print(f"Winning Cycles               : {winning_trades} ({win_rate:.2f}%)")
    print(f"Losing Cycles                : {losing_trades} ({100 - win_rate:.2f}%)")
    print(f"Total Net PnL (Points)       : {total_pnl_pts:+.2f} pts")
    print(f"Total Net PnL (Rupees @ 65)  : Rs. {total_pnl_rs:+,.2f}")
    print(f"Average Weekly Rollover      : {avg_pnl_pts:+.2f} pts / week")
    print(f"Max Single Cycle Gain        : {max_win_pts:+.2f} pts")
    print(f"Max Single Cycle Loss        : {max_loss_pts:+.2f} pts")
    print(f"Max Equity Drawdown          : {max_dd_pts:.2f} pts")
    print("="*95)
    
    print("\nSAMPLE REAL OPTION BHAVCOPY TRADES:")
    print(trades_df[['entry_date', 'exit_date', 'stance', 'entry_spot', 'exit_spot', 'long_symbol', 'net_pnl_pts', 'net_pnl_rs']].tail(10).to_string(index=False))
    
    out_csv = "research_and_development/chirag_jain_real_bhavcopy_results.csv"
    trades_df.to_csv(out_csv, index=False)
    print(f"\nDetailed real option trade logs saved to: {out_csv}")

if __name__ == "__main__":
    run_real_option_bhavcopy_backtest()
