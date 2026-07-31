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

def get_contract_price_on_day(cache_dir, strike, opt_type, exp_idx, expiry_date, date_str):
    filename = f"nifty_{strike}_{opt_type}_exp{exp_idx}_expiry{expiry_date}_{date_str}.csv"
    file_path = os.path.join(cache_dir, filename)
    if os.path.exists(file_path):
        try:
            df_c = pd.read_csv(file_path)
            if not df_c.empty:
                df_c['timestamp'] = pd.to_datetime(df_c['timestamp'])
                exit_candle = df_c[df_c['timestamp'].dt.strftime('%H:%M') == '15:20']
                if not exit_candle.empty:
                    return float(exit_candle['close'].iloc[0])
                return float(df_c.iloc[-1]['close'])
        except Exception:
            pass
    return None

def run_dynamic_backtest(target_monthly_p=200.0, target_otm_p=120.0, target_itm_p=360.0):
    spot_path = "backtest_data/nifty_spot.csv"
    if not os.path.exists(spot_path):
        print("[ERROR] nifty_spot.csv not found!")
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
    
    # Re-entry triggers for next day
    reenter_next_day = {"CALL": False, "PUT": False}
    
    completed_trades = []
    trade_id_counter = 1
    
    for i, curr_date in enumerate(target_dates):
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        curr_weekday = curr_date.weekday()
        day_df = daily_groups[curr_date]
        
        # Check active positions for early exit or expiry at 15:20
        exit_candle = day_df[day_df['timestamp'].dt.strftime('%H:%M') == '15:20']
        if exit_candle.empty:
            exit_candle = day_df.iloc[-1:]
        exit_spot = float(exit_candle['close'].iloc[0])
        
        for stance in ["CALL", "PUT"]:
            port = active_portfolio[stance]
            
            # 1. Check for Early Exit if all 3 legs are active
            if port["monthly_long"] is not None and port["weekly_short1"] is not None and port["weekly_short2"] is not None:
                opt_type = 'CE' if stance == "CALL" else 'PE'
                
                l_val = get_contract_price_on_day(cache_dir, port["monthly_long"]["strike"], opt_type, 1, port["monthly_long"]["expiry_date"], curr_date_str)
                s1_val = get_contract_price_on_day(cache_dir, port["weekly_short1"]["strike"], opt_type, 0, port["weekly_short1"]["expiry_date"], curr_date_str)
                s2_val = get_contract_price_on_day(cache_dir, port["weekly_short2"]["strike"], opt_type, 0, port["weekly_short2"]["expiry_date"], curr_date_str)
                
                if l_val is not None and s1_val is not None and s2_val is not None:
                    long_pnl = (l_val - port["monthly_long"]["entry_px"]) * 3 * lot_size
                    short1_pnl = (port["weekly_short1"]["entry_px"] - s1_val) * (-1) * -1 * lot_size # -1 * (s1_val - entry) * lot_size
                    short2_pnl = (port["weekly_short2"]["entry_px"] - s2_val) * (-1) * -1 * lot_size
                    
                    total_open_pnl = long_pnl + short1_pnl + short2_pnl
                    
                    if total_open_pnl >= 5000.0:
                        # Target reached! Trigger early exit for all legs
                        for leg_name, current_val in [("monthly_long", l_val), ("weekly_short1", s1_val), ("weekly_short2", s2_val)]:
                            leg = port[leg_name]
                            pnl = (current_val - leg["entry_px"]) * leg["qty"] * lot_size
                            completed_trades.append({
                                'Trade_ID': leg['trade_id'],
                                'Stance': f"{stance}_CALENDAR",
                                'Leg': leg_name.upper(),
                                'Strike': leg['strike'],
                                'Entry_Date': leg['entry_date'],
                                'Exit_Date': curr_date_str,
                                'Entry_Spot': leg['entry_spot'],
                                'Exit_Spot': exit_spot,
                                'Entry_Px': leg['entry_px'],
                                'Exit_Px': current_val,
                                'Qty': leg['qty'],
                                'Net_PnL': pnl,
                                'Status': 'EARLY_EXIT'
                            })
                            port[leg_name] = None
                        
                        # Set trigger to re-enter on the next trading day
                        reenter_next_day[stance] = True
                        continue # Stance exited, skip normal expiry checks
            
            # 2. Check for normal weekly expiry settlement
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
            
        # Entry check at 09:20 AM
        # Entry allowed on Wednesday (2), Thursday (3), Friday (4) only (no entries on Monday 0 and Tuesday 1)
        if curr_weekday in [2, 3, 4]:
            entry_candle = day_df[day_df['timestamp'].dt.strftime('%H:%M') == '09:20']
            if entry_candle.empty:
                entry_candle = day_df.iloc[0:1]
            entry_spot = float(entry_candle['close'].iloc[0])
            entry_ts = entry_candle['timestamp'].iloc[0]
            
            day_cache = df_cache[df_cache['file_date'] == curr_date_str]
            if day_cache.empty:
                continue
                
            unique_expiries = sorted(day_cache['expiry_date'].unique())
            if len(unique_expiries) < 2:
                continue
                
            weekly_expiry = unique_expiries[0]
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
                        
            for stance in ["CALL", "PUT"]:
                port = active_portfolio[stance]
                
                # Determine if we should enter today:
                # 1. It is Wednesday (primary entry day), and we have no active weekly shorts.
                # 2. Or we exited early yesterday (reenter_next_day is True).
                should_enter = False
                if curr_weekday == 2 and port["weekly_short1"] is None:
                    should_enter = True
                elif reenter_next_day[stance] and port["weekly_short1"] is None:
                    should_enter = True
                    reenter_next_day[stance] = False # clear trigger
                    
                if not should_enter:
                    continue
                    
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
                    matched_long = match_leg(chain_monthly, target_monthly_p)
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
    # Test both Option A (200 Monthly) and Option B (150 Monthly)
    options = [
        {"name": "Option A (Max Profit)", "monthly": 200.0, "otm": 120.0, "itm": 360.0},
        {"name": "Option B (Net Credit collected)", "monthly": 150.0, "otm": 120.0, "itm": 360.0}
    ]
    
    print("="*100)
    print("      RUNNING STRATEGY 20 DYNAMIC EXIT (>Rs. 5000) & RE-ENTRY BACKTEST")
    print("="*100)
    
    for opt in options:
        print(f"\n[RUNNING] {opt['name']} (Monthly Long: Rs. {opt['monthly']}, OTM: Rs. {opt['otm']}, ITM: Rs. {opt['itm']})...")
        df = run_dynamic_backtest(target_monthly_p=opt['monthly'], target_otm_p=opt['otm'], target_itm_p=opt['itm'])
        if not df.empty:
            df.to_csv(f"detailed_trades_{opt['name'].lower().replace(' ', '_')}.csv", index=False)
            num_trades = len(df)
            gross_pnl = df['Net_PnL'].sum()
            charges = num_trades * 50.0
            net_pnl = gross_pnl - charges
            win_rate = len(df[df['Net_PnL'] > 0]) / num_trades * 100
            
            # Print stats
            print(f"Total Trade Legs:  {num_trades}")
            print(f"Win Rate of Legs:  {win_rate:.2f}%")
            print(f"Gross PnL:         Rs. {gross_pnl:,.2f}")
            print(f"Charges:           Rs. {charges:,.2f}")
            print(f"Net PnL:           Rs. {net_pnl:,.2f}")
            
            # Check how many early exits triggered
            early_exits = len(df[df['Status'] == 'EARLY_EXIT']) // 3
            print(f"Early Exits:       {early_exits} cycles triggered early exit.")
            
    print("="*100)
