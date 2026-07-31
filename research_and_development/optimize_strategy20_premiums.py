import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime

def run_premium_backtest(target_otm_p=150.0, target_itm_p=450.0):
    spot_path = "backtest_data/nifty_spot.csv"
    if not os.path.exists(spot_path):
        return pd.DataFrame()

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
    
    # Pre-parse option filenames in cache
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
    
    # Active portfolio state
    active_portfolio = {
        "CALL": {"monthly_long": None, "weekly_short1": None, "weekly_short2": None},
        "PUT": {"monthly_long": None, "weekly_short1": None, "weekly_short2": None}
    }
    
    completed_trades = []
    trade_id_counter = 1
    
    for i, curr_date in enumerate(target_dates):
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        curr_weekday = curr_date.weekday()
        day_df = daily_groups[curr_date]
        
        # Check active positions for expiry at 15:20 on every day
        exit_candle = day_df[day_df['timestamp'].dt.strftime('%H:%M') == '15:20']
        if exit_candle.empty:
            exit_candle = day_df.iloc[-1:]
        exit_spot = float(exit_candle['close'].iloc[0])
        
        for stance in ["CALL", "PUT"]:
            port = active_portfolio[stance]
            
            for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
                leg = port[leg_name]
                if leg is not None:
                    if curr_date_str >= leg["expiry_date"]:
                        strike = leg["strike"]
                        entry_px = leg["entry_px"]
                        qty = leg["qty"]
                        
                        if stance == "CALL":
                            settlement_px = max(0.0, exit_spot - strike)
                        else:
                            settlement_px = max(0.0, strike - exit_spot)
                            
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
            
        # Entry check: Wednesday (2) at 09:20 AM
        if curr_weekday == 2:
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
                    
            monthly_expiry = None
            for exp in unique_expiries:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                curr_dt = datetime.combine(curr_date, datetime.min.time())
                if (exp_dt - curr_dt).days >= 18:
                    monthly_expiry = exp
                    break
            if not monthly_expiry:
                monthly_expiry = unique_expiries[-1]
                
            if weekly_expiry == monthly_expiry:
                for exp in unique_expiries:
                    if exp != weekly_expiry:
                        monthly_expiry = exp
                        break
                        
            # Execute both CALL & PUT for Dual Stance evaluation
            for stance in ["CALL", "PUT"]:
                port = active_portfolio[stance]
                opt_type = 'CE' if stance == "CALL" else 'PE'
                
                chain_weekly = day_cache[(day_cache['expiry_date'] == weekly_expiry) & (day_cache['opt_type'] == opt_type)]
                chain_monthly = day_cache[(day_cache['expiry_date'] == monthly_expiry) & (day_cache['opt_type'] == opt_type)]
                
                if chain_weekly.empty or chain_monthly.empty:
                    continue
                    
                def match_leg(df_leg, target_p):
                    best_leg = None
                    min_diff = 9999.0
                    for _, row in df_leg.iterrows():
                        try:
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
                    matched_s1 = match_leg(chain_weekly, target_otm_p)
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
                    matched_s2 = match_leg(chain_weekly, target_itm_p)
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
                        
    # Forced close remaining at the end
    last_date = target_dates[-1]
    day_df = daily_groups[last_date]
    exit_candle = day_df.iloc[-1:]
    exit_spot = float(exit_candle['close'].iloc[0])
    
    for stance in ["CALL", "PUT"]:
        port = active_portfolio[stance]
        for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
            leg = port[leg_name]
            if leg is not None:
                strike = leg["strike"]
                entry_px = leg["entry_px"]
                qty = leg["qty"]
                
                if stance == "CALL":
                    settlement_px = max(0.0, exit_spot - strike)
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
    results = []
    
    # Target short premium pairs to test
    premium_pairs = [
        (100.0, 300.0),
        (150.0, 450.0), # current base case
        (200.0, 500.0),
        (100.0, 400.0),
        (120.0, 360.0)
    ]
    
    print("="*100)
    print("            STRATEGY 20 SHORT PREMIUM OPTIMIZATION SWEEP")
    print("="*100)
    
    for otm_p, itm_p in premium_pairs:
        print(f"[RUNNING] Weekly Short 1 Target: Rs. {otm_p} | Weekly Short 2 Target: Rs. {itm_p}...")
        df = run_premium_backtest(target_otm_p=otm_p, target_itm_p=itm_p)
        if not df.empty:
            num_trades = len(df)
            gross_pnl = df['Net_PnL'].sum()
            charges = num_trades * 50.0
            net_pnl = gross_pnl - charges
            win_rate = len(df[df['Net_PnL'] > 0]) / num_trades * 100
            
            results.append({
                "OTM_Short_Target": f"Rs. {otm_p}",
                "ITM_Short_Target": f"Rs. {itm_p}",
                "Total_Trades": num_trades,
                "Win_Rate": f"{win_rate:.2f}%",
                "Gross_PnL_Rs": round(gross_pnl, 2),
                "Charges_Rs": round(charges, 2),
                "Net_PnL_Rs": round(net_pnl, 2)
            })
            
    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values(by="Net_PnL_Rs", ascending=False).reset_index(drop=True)
    
    print("\n" + "="*100)
    print("                         PREMIUM OPTIMIZATION RANKINGS")
    print("="*100)
    print(df_res.to_string(index=True))
    print("="*100)
    df_res.to_csv("strategy20_premium_optimization_results.csv", index=False)
