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

def run_day_by_day_backtest(trade_both_sides=1, forced_stance=None):
    spot_path = "backtest_data/nifty_spot.csv"
    if not os.path.exists(spot_path):
        print(f"[ERROR] {spot_path} not found!")
        return pd.DataFrame()

    print(f"[INFO] Reading spot data from {spot_path}...")
    df_spot = pd.read_csv(spot_path)
    df_spot['timestamp'] = pd.to_datetime(df_spot['timestamp'])
    df_spot = df_spot.sort_values('timestamp').reset_index(drop=True)
    df_spot['date'] = df_spot['timestamp'].dt.date
    
    unique_dates = sorted(df_spot['date'].unique())
    if len(unique_dates) > 180:
        target_dates = unique_dates[-180:]
        df_spot = df_spot[df_spot['date'].isin(target_dates)].reset_index(drop=True)
    else:
        target_dates = unique_dates

    daily_groups = {d: g.reset_index(drop=True) for d, g in df_spot.groupby('date')}
    cache_dir = "backtest_data/contract_cache"
    lot_size = 65
    
    # Active portfolio state
    active_portfolio = {
        "CALL": {"monthly_long": None, "weekly_short1": None, "weekly_short2": None},
        "PUT": {"monthly_long": None, "weekly_short1": None, "weekly_short2": None}
    }
    
    completed_trades = []
    trade_id_counter = 1
    
    # Pre-parse option filenames in cache for quick lookup
    print("[INFO] Indexing cache directory...")
    all_files = glob.glob(os.path.join(cache_dir, "nifty_*.csv"))
    cache_index = []
    for f in all_files:
        try:
            fname = os.path.basename(f)
            parts = fname.split('_')
            strike = int(parts[1])
            opt_type = parts[2]
            exp_idx = int(parts[3].replace('exp', ''))
            expiry_date = parts[4].replace('expiry', '')
            file_date = parts[5].replace('.csv', '')
            cache_index.append({
                'strike': strike,
                'opt_type': opt_type,
                'exp_idx': exp_idx,
                'expiry_date': expiry_date,
                'file_date': file_date,
                'file_path': f
            })
        except Exception:
            continue
            
    df_cache = pd.DataFrame(cache_index)
    print(f"[INFO] Indexed {len(df_cache)} cached option day files.")
    
    for i, curr_date in enumerate(target_dates):
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        curr_weekday = curr_date.weekday()
        day_df = daily_groups[curr_date]
        
        # Check active positions for expiry at 15:20 on every day
        exit_candle = day_df[day_df['timestamp'].dt.strftime('%H:%M') == '15:20']
        if exit_candle.empty:
            exit_candle = day_df.iloc[-1:]
        exit_spot = float(exit_candle['close'].iloc[0])
        exit_ts = exit_candle['timestamp'].iloc[0]
        
        for stance in ["CALL", "PUT"]:
            # Skip if we don't trade both sides and this stance doesn't match active regime
            if trade_both_sides == 0 and stance == "PUT":
                # For single-stance, we dynamically decide or force PUT
                pass
                
            port = active_portfolio[stance]
            
            # Settle expired positions
            for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
                leg = port[leg_name]
                if leg is not None:
                    if curr_date_str >= leg["expiry_date"]:
                        # Expired! Settle at intrinsic
                        strike = leg["strike"]
                        entry_px = leg["entry_px"]
                        qty = leg["qty"]
                        
                        if stance == "CALL":
                            settlement_px = max(0.0, exit_spot - strike)
                        else:
                            settlement_px = max(0.0, strike - exit_spot)
                            
                        # If monthly long leg expires, its exit value is settlement
                        pnl = (settlement_px - entry_px) * qty * lot_size
                        completed_trades.append({
                            'Trade_ID': leg['trade_id'],
                            'Stance': f"{stance}_CALENDAR",
                            'Leg': leg_name.upper(),
                            'Strike': strike,
                            'Entry_Date': leg['entry_date'],
                            'Exit_Date': curr_date_str,
                            'Entry_Spot': leg['entry_spot'],
                            'Exit_Spot': exit_spot,
                            'Entry_Px': entry_px,
                            'Exit_Px': settlement_px,
                            'Qty': qty,
                            'Net_PnL': pnl,
                            'Status': 'SETTLED'
                        })
                        port[leg_name] = None
            
        # Entry check: Tuesday (1) or Thursday (3) at 09:20 AM
        if curr_weekday in [1, 3]:
            entry_candle = day_df[day_df['timestamp'].dt.strftime('%H:%M') == '09:20']
            if entry_candle.empty:
                entry_candle = day_df.iloc[0:1]
            entry_spot = float(entry_candle['close'].iloc[0])
            entry_ts = entry_candle['timestamp'].iloc[0]
            
            # Resolve expiry dates from cache available on this date
            day_cache = df_cache[df_cache['file_date'] == curr_date_str]
            if day_cache.empty:
                continue
                
            unique_expiries = sorted(day_cache['expiry_date'].unique())
            if len(unique_expiries) < 2:
                continue
                
            weekly_expiry = unique_expiries[0]
            # Shift weekly expiry to next week if today is expiry day
            if weekly_expiry == curr_date_str:
                if len(unique_expiries) > 1:
                    weekly_expiry = unique_expiries[1]
                else:
                    continue
                    
            # Monthly expiry resolution (expiry >= 18 days out)
            monthly_expiry = None
            for exp in unique_expiries:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                curr_dt = datetime.combine(curr_date, datetime.min.time())
                if (exp_dt - curr_dt).days >= 18:
                    monthly_expiry = exp
                    break
            if not monthly_expiry:
                monthly_expiry = unique_expiries[-1]
                
            # If weekly and monthly expiries overlap
            if weekly_expiry == monthly_expiry:
                for exp in unique_expiries:
                    if exp != weekly_expiry:
                        monthly_expiry = exp
                        break
                        
            stances_to_trade = ["CALL", "PUT"] if trade_both_sides == 1 else []
            if trade_both_sides == 0:
                if forced_stance is not None:
                    stances_to_trade = [forced_stance]
                else:
                    # Dynamic stance selection based on CAGR valuation baseline
                    fair_val = calculate_fair_value_baseline(datetime.combine(curr_date, datetime.min.time()))
                    ratio = entry_spot / fair_val
                    regime_stance = "PUT" if ratio >= 0.95 else "CALL"
                    stances_to_trade = [regime_stance]
                
            for stance in stances_to_trade:
                port = active_portfolio[stance]
                opt_type = 'CE' if stance == "CALL" else 'PE'
                
                # Fetch available chain details for today
                chain_weekly = day_cache[(day_cache['expiry_date'] == weekly_expiry) & (day_cache['opt_type'] == opt_type)]
                chain_monthly = day_cache[(day_cache['expiry_date'] == monthly_expiry) & (day_cache['opt_type'] == opt_type)]
                
                if chain_weekly.empty or chain_monthly.empty:
                    continue
                    
                # Match strikes
                def match_leg(df_leg, target_p):
                    best_leg = None
                    min_diff = 9999.0
                    for _, row in df_leg.iterrows():
                        try:
                            # Read premium at 09:20
                            px = get_premium_at_time(row['file_path'], entry_ts)
                            if px is not None and px > 0:
                                diff = abs(px - target_p)
                                if diff < min_diff:
                                    min_diff = diff
                                    best_leg = {
                                        'strike': row['strike'],
                                        'expiry_date': row['expiry_date'],
                                        'entry_px': px,
                                        'file_path': row['file_path']
                                    }
                        except Exception:
                            continue
                    return best_leg
                    
                # 1. Manage Monthly Long Leg (Mode B)
                if port["monthly_long"] is None:
                    matched_long = match_leg(chain_monthly, 200.0)
                    if matched_long:
                        port["monthly_long"] = {
                            'trade_id': trade_id_counter,
                            'strike': matched_long['strike'],
                            'expiry_date': matched_long['expiry_date'],
                            'entry_px': matched_long['entry_px'],
                            'entry_date': curr_date_str,
                            'entry_spot': entry_spot,
                            'qty': 3
                        }
                        trade_id_counter += 1
                        
                # 2. Manage Weekly Short Legs
                if port["weekly_short1"] is None:
                    matched_s1 = match_leg(chain_weekly, 150.0)
                    if matched_s1:
                        port["weekly_short1"] = {
                            'trade_id': trade_id_counter,
                            'strike': matched_s1['strike'],
                            'expiry_date': matched_s1['expiry_date'],
                            'entry_px': matched_s1['entry_px'],
                            'entry_date': curr_date_str,
                            'entry_spot': entry_spot,
                            'qty': -1
                        }
                        trade_id_counter += 1
                        
                if port["weekly_short2"] is None:
                    matched_s2 = match_leg(chain_weekly, 450.0)
                    if matched_s2:
                        port["weekly_short2"] = {
                            'trade_id': trade_id_counter,
                            'strike': matched_s2['strike'],
                            'expiry_date': matched_s2['expiry_date'],
                            'entry_px': matched_s2['entry_px'],
                            'entry_date': curr_date_str,
                            'entry_spot': entry_spot,
                            'qty': -1
                        }
                        trade_id_counter += 1
                        
    # End of backtest: Force exit any open positions at intrinsic
    last_date = target_dates[-1]
    day_df = daily_groups[last_date]
    exit_candle = day_df.iloc[-1:]
    exit_spot = float(exit_candle['close'].iloc[0])
    exit_ts = exit_candle['timestamp'].iloc[0]
    
    for stance in ["CALL", "PUT"]:
        port = active_portfolio[stance]
        for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
            leg = port[leg_name]
            if leg is not None:
                strike = leg["strike"]
                entry_px = leg["entry_px"]
                qty = leg["qty"]
                
                # Settle at intrinsic
                if stance == "CALL":
                    settlement_px = max(0.0, exit_spot - strike)
                    # Add extrinsic time value if monthly long is forced closed early
                    if leg_name == "monthly_long":
                        settlement_px += 120.0
                else:
                    settlement_px = max(0.0, strike - exit_spot)
                    if leg_name == "monthly_long":
                        settlement_px += 120.0
                        
                pnl = (settlement_px - entry_px) * qty * lot_size
                completed_trades.append({
                    'Trade_ID': leg['trade_id'],
                    'Stance': f"{stance}_CALENDAR",
                    'Leg': leg_name.upper(),
                    'Strike': strike,
                    'Entry_Date': leg['entry_date'],
                    'Exit_Date': last_date.strftime("%Y-%m-%d"),
                    'Entry_Spot': leg['entry_spot'],
                    'Exit_Spot': exit_spot,
                    'Entry_Px': entry_px,
                    'Exit_Px': settlement_px,
                    'Qty': qty,
                    'Net_PnL': pnl,
                    'Status': 'FORCED_CLOSED'
                })
                port[leg_name] = None
                
    df_trades = pd.DataFrame(completed_trades)
    return df_trades

def get_premium_at_time(file_path, timestamp_to_match):
    df_c = pd.read_csv(file_path)
    df_c['timestamp'] = pd.to_datetime(df_c['timestamp'])
    ts_row = df_c[df_c['timestamp'] == timestamp_to_match]
    if not ts_row.empty:
        return float(ts_row['close'].iloc[0])
    return None

if __name__ == "__main__":
    print("\n" + "="*80)
    print("      RUNNING STRATEGY 20 DUAL STANCE BACKTEST (BOTH CE & PE)")
    print("="*80)
    df_dual = run_day_by_day_backtest(trade_both_sides=1)
    if not df_dual.empty:
        df_dual.to_csv("detailed_trades_verification_dual.csv", index=False)
        num_trades = len(df_dual)
        gross_pnl = df_dual['Net_PnL'].sum()
        charges = num_trades * 50.0
        net_pnl = gross_pnl - charges
        win_rate = len(df_dual[df_dual['Net_PnL'] > 0]) / num_trades * 100
        print(f"Total Trades: {num_trades}")
        print(f"Win Rate:     {win_rate:.2f}%")
        print(f"Gross PnL:    Rs. {gross_pnl:,.2f}")
        print(f"Charges:      Rs. {charges:,.2f}")
        print(f"Net PnL:      Rs. {net_pnl:,.2f}")
        
    print("\n" + "="*80)
    print("      RUNNING STRATEGY 20 DYNAMIC SINGLE STANCE BACKTEST")
    print("="*80)
    df_single = run_day_by_day_backtest(trade_both_sides=0)
    if not df_single.empty:
        df_single.to_csv("detailed_trades_verification_single.csv", index=False)
        num_trades = len(df_single)
        gross_pnl = df_single['Net_PnL'].sum()
        charges = num_trades * 50.0
        net_pnl = gross_pnl - charges
        win_rate = len(df_single[df_single['Net_PnL'] > 0]) / num_trades * 100
        print(f"Total Trades: {num_trades}")
        print(f"Win Rate:     {win_rate:.2f}%")
        print(f"Gross PnL:    Rs. {gross_pnl:,.2f}")
        print(f"Charges:      Rs. {charges:,.2f}")
        print(f"Net PnL:      Rs. {net_pnl:,.2f}")
        
    print("\n" + "="*80)
    print("      RUNNING STRATEGY 20 FORCED CALL-ONLY BACKTEST")
    print("="*80)
    df_call = run_day_by_day_backtest(trade_both_sides=0, forced_stance="CALL")
    if not df_call.empty:
        df_call.to_csv("detailed_trades_verification_call_only.csv", index=False)
        num_trades = len(df_call)
        gross_pnl = df_call['Net_PnL'].sum()
        charges = num_trades * 50.0
        net_pnl = gross_pnl - charges
        win_rate = len(df_call[df_call['Net_PnL'] > 0]) / num_trades * 100
        print(f"Total Trades: {num_trades}")
        print(f"Win Rate:     {win_rate:.2f}%")
        print(f"Gross PnL:    Rs. {gross_pnl:,.2f}")
        print(f"Charges:      Rs. {charges:,.2f}")
        print(f"Net PnL:      Rs. {net_pnl:,.2f}")
        
    print("\n" + "="*80)
    print("      RUNNING STRATEGY 20 FORCED PUT-ONLY BACKTEST")
    print("="*80)
    df_put = run_day_by_day_backtest(trade_both_sides=0, forced_stance="PUT")
    if not df_put.empty:
        df_put.to_csv("detailed_trades_verification_put_only.csv", index=False)
        num_trades = len(df_put)
        gross_pnl = df_put['Net_PnL'].sum()
        charges = num_trades * 50.0
        net_pnl = gross_pnl - charges
        win_rate = len(df_put[df_put['Net_PnL'] > 0]) / num_trades * 100
        print(f"Total Trades: {num_trades}")
        print(f"Win Rate:     {win_rate:.2f}%")
        print(f"Gross PnL:    Rs. {gross_pnl:,.2f}")
        print(f"Charges:      Rs. {charges:,.2f}")
        print(f"Net PnL:      Rs. {net_pnl:,.2f}")
    print("="*80)
