import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_premium_at_time(file_path, timestamp_to_match):
    df_c = pd.read_csv(file_path)
    df_c['timestamp'] = pd.to_datetime(df_c['timestamp'])
    ts_row = df_c[df_c['timestamp'] == timestamp_to_match]
    if not ts_row.empty:
        return float(ts_row['close'].iloc[0])
    return None

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

def run_backtest_with_roll_rule(roll_threshold_days=7):
    spot_path = "backtest_data/nifty_spot.csv"
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
    
    # Pre-scan cache files to map (date, expiry, opt_type, strike) to file_path
    cache_files = glob.glob(os.path.join(cache_dir, "*.csv"))
    cache_rows = []
    for f in cache_files:
        fname = os.path.basename(f)
        parts = fname.split('_')
        if len(parts) >= 5:
            try:
                strike = int(parts[1])
                opt_type = parts[2]
                expiry_str = parts[4].replace("expiry", "")
                file_date_str = parts[5].replace(".csv", "")
                cache_rows.append({
                    'strike': strike,
                    'opt_type': opt_type,
                    'expiry_date': expiry_str,
                    'file_date': file_date_str,
                    'file_path': f
                })
            except Exception:
                continue
                
    df_cache = pd.DataFrame(cache_rows)
    lot_size = 65
    
    active_portfolio = {
        "CALL": {"monthly_long": None, "weekly_short1": None, "weekly_short2": None},
        "PUT": {"monthly_long": None, "weekly_short1": None, "weekly_short2": None}
    }
    
    reenter_next_day = {"CALL": False, "PUT": False}
    completed_trades = []
    trade_id_counter = 1
    
    for i, curr_date in enumerate(target_dates):
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        curr_weekday = curr_date.weekday()
        day_df = daily_groups[curr_date]
        
        exit_candle = day_df[day_df['timestamp'].dt.strftime('%H:%M') == '15:20']
        if exit_candle.empty:
            exit_candle = day_df.iloc[-1:]
        exit_spot = float(exit_candle['close'].iloc[0])
        
        for stance in ["CALL", "PUT"]:
            port = active_portfolio[stance]
            
            # 1. Early Exit check
            if port["monthly_long"] is not None and port["weekly_short1"] is not None and port["weekly_short2"] is not None:
                opt_type = 'CE' if stance == "CALL" else 'PE'
                l_val = get_contract_price_on_day(cache_dir, port["monthly_long"]["strike"], opt_type, 1, port["monthly_long"]["expiry_date"], curr_date_str)
                s1_val = get_contract_price_on_day(cache_dir, port["weekly_short1"]["strike"], opt_type, 0, port["weekly_short1"]["expiry_date"], curr_date_str)
                s2_val = get_contract_price_on_day(cache_dir, port["weekly_short2"]["strike"], opt_type, 0, port["weekly_short2"]["expiry_date"], curr_date_str)
                
                if l_val is not None and s1_val is not None and s2_val is not None:
                    long_pnl = (l_val - port["monthly_long"]["entry_px"]) * 3 * lot_size
                    short1_pnl = (port["weekly_short1"]["entry_px"] - s1_val) * lot_size
                    short2_pnl = (port["weekly_short2"]["entry_px"] - s2_val) * lot_size
                    total_open_pnl = long_pnl + short1_pnl + short2_pnl
                    
                    # Target or SL
                    trigger_exit = False
                    status_reason = 'EARLY_EXIT'
                    if total_open_pnl >= 5000.0:
                        trigger_exit = True
                        status_reason = 'EARLY_EXIT'
                    elif total_open_pnl <= -4000.0:
                        trigger_exit = True
                        status_reason = 'STOP_LOSS_EXIT'
                        
                    if trigger_exit:
                        for leg_name, current_val in [("monthly_long", l_val), ("weekly_short1", s1_val), ("weekly_short2", s2_val)]:
                            leg = port[leg_name]
                            pnl = (current_val - leg["entry_px"]) * leg["qty"] * lot_size
                            completed_trades.append({
                                'Leg': leg_name.upper(),
                                'Net_PnL': pnl,
                                'Status': status_reason
                            })
                            port[leg_name] = None
                        reenter_next_day[stance] = True
                        continue
            
            # 2. Regular Weekly Expiry Checks
            for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
                leg = port[leg_name]
                if leg is not None:
                    if curr_date_str >= leg["expiry_date"]:
                        strike = leg["strike"]
                        entry_px = leg["entry_px"]
                        qty = leg["qty"]
                        settlement_px = max(0.0, exit_spot - strike) if stance == "CALL" else max(0.0, strike - exit_spot)
                        pnl = (settlement_px - entry_px) * qty * lot_size
                        completed_trades.append({
                            'Leg': leg_name.upper(),
                            'Net_PnL': pnl,
                            'Status': 'SETTLED'
                        })
                        port[leg_name] = None
                        
        # Entry check at 09:20 AM
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
                
                # Check for roll rule threshold:
                if port["monthly_long"] is not None:
                    exp_dt = datetime.strptime(port["monthly_long"]["expiry_date"], "%Y-%m-%d")
                    curr_dt = datetime.combine(curr_date, datetime.min.time())
                    days_to_expiry = (exp_dt - curr_dt).days
                    if days_to_expiry < roll_threshold_days:
                        # Exiting Monthly Long early
                        opt_type = 'CE' if stance == "CALL" else 'PE'
                        l_val = get_premium_at_time(port["monthly_long"]["file_path"], entry_ts)
                        if l_val is not None:
                            pnl = (l_val - port["monthly_long"]["entry_px"]) * 3 * lot_size
                            completed_trades.append({
                                'Leg': 'MONTHLY_LONG',
                                'Net_PnL': pnl,
                                'Status': 'ROLLED_OUT'
                            })
                            port["monthly_long"] = None
                
                should_enter = False
                if curr_weekday == 2 and port["weekly_short1"] is None:
                    should_enter = True
                elif reenter_next_day[stance] and port["weekly_short1"] is None:
                    should_enter = True
                    reenter_next_day[stance] = False
                    
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
                    
                if port["monthly_long"] is None:
                    matched_long = match_leg(chain_monthly, 200.0)
                    if matched_long:
                        port["monthly_long"] = {
                            'strike': matched_long['strike'],
                            'expiry_date': matched_long['expiry_date'],
                            'entry_px': matched_long['entry_px'],
                            'entry_date': curr_date_str,
                            'entry_spot': entry_spot,
                            'file_path': matched_long['file_path'],
                            'qty': 3
                        }
                        
                if port["weekly_short1"] is None:
                    matched_s1 = match_leg(chain_weekly, 120.0)
                    if matched_s1:
                        port["weekly_short1"] = {
                            'strike': matched_s1['strike'],
                            'expiry_date': matched_s1['expiry_date'],
                            'entry_px': matched_s1['entry_px'],
                            'entry_date': curr_date_str,
                            'entry_spot': entry_spot,
                            'qty': -1
                        }
                        
                if port["weekly_short2"] is None:
                    matched_s2 = match_leg(chain_weekly, 300.0)
                    if matched_s2:
                        port["weekly_short2"] = {
                            'strike': matched_s2['strike'],
                            'expiry_date': matched_s2['expiry_date'],
                            'entry_px': matched_s2['entry_px'],
                            'entry_date': curr_date_str,
                            'entry_spot': entry_spot,
                            'qty': -1
                        }
                        
    # End forced close
    last_date = target_dates[-1]
    day_df = daily_groups[last_date]
    exit_candle = day_df.iloc[-1:]
    exit_spot = float(exit_candle['close'].iloc[0])
    for stance in ["CALL", "PUT"]:
        port = active_portfolio[stance]
        for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
            leg = port[leg_name]
            if leg is not None:
                settlement_px = max(0.0, exit_spot - leg['strike']) if stance == "CALL" else max(0.0, leg['strike'] - exit_spot)
                if leg_name == "monthly_long":
                    settlement_px += 120.0
                pnl = (settlement_px - leg['entry_px']) * leg['qty'] * lot_size
                completed_trades.append({
                    'Leg': leg_name.upper(),
                    'Net_PnL': pnl,
                    'Status': 'FORCED_CLOSED'
                })
                port[leg_name] = None
                
    df_res = pd.DataFrame(completed_trades)
    net_pnl = df_res['Net_PnL'].sum()
    charges = len(df_res) * 50.0 # simple estimate
    print(f"Roll Threshold: {roll_threshold_days} days -> Net PnL: Rs. {net_pnl - charges:,.2f} (Gross: Rs. {net_pnl:,.2f}, Trades: {len(df_res)})")
    
if __name__ == "__main__":
    for threshold in [0, 4, 7, 10]:
        run_backtest_with_roll_rule(threshold)
