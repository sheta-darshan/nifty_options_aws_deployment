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

def load_contract_df(df_cache, strike, opt_type, expiry_date, file_date):
    """Load 1-minute historical data for a specific option contract on a given trading date."""
    matched = df_cache[
        (df_cache['strike'] == strike) & 
        (df_cache['opt_type'] == opt_type) & 
        (df_cache['expiry_date'] == expiry_date) & 
        (df_cache['file_date'] == file_date)
    ]
    if not matched.empty:
        file_path = matched.iloc[0]['file_path']
        try:
            df = pd.read_csv(file_path)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # Round to minute to align index lookups cleanly
                df['timestamp'] = df['timestamp'].dt.round('min')
                df.set_index('timestamp', inplace=True)
                # Sort to ensure forward-filling matches time order
                df = df.sort_index()
                return df
        except Exception:
            pass
    return None

def get_price_at_minute(contract_df, target_ts, last_known_px=None):
    """Retrieve close price at timestamp, or forward-fill last known price if no trade occurred."""
    if contract_df is None or contract_df.empty:
        return last_known_px
    if target_ts in contract_df.index:
        val = contract_df.loc[target_ts]
        # In case of duplicate index timestamps, pick first close
        close_val = val['close'].iloc[0] if isinstance(val, pd.DataFrame) else val['close']
        return float(close_val)
    # Forward-fill: find the last close before target_ts
    prior_rows = contract_df[contract_df.index < target_ts]
    if not prior_rows.empty:
        return float(prior_rows.iloc[-1]['close'])
    return last_known_px

def run_intraday_backtest(target_monthly_p=200.0, target_otm_p=130.0, target_itm_p=400.0, 
                          target_exit_pnl=5000.0, stop_loss_pnl=-4000.0, roll_threshold_days=7,
                          df_spot=None, trade_both_sides=1, num_lots_long=1, df_cache=None,
                          symbol="NIFTY", lot_size=None):
    if df_spot is None:
        spot_path = f"backtest_data/{symbol.lower()}_spot.csv"
        if not os.path.exists(spot_path):
            print(f"[ERROR] {symbol.lower()}_spot.csv not found!")
            return pd.DataFrame()
        df_spot = pd.read_csv(spot_path)
        df_spot['timestamp'] = pd.to_datetime(df_spot['timestamp'])
        df_spot = df_spot.sort_values('timestamp').reset_index(drop=True)
        df_spot['date'] = df_spot['timestamp'].dt.date
        
        from strategies.strategy_20 import Strategy_20
        strat = Strategy_20()
        df_spot = strat.generate_signals(df_spot)
    else:
        df_spot = df_spot.copy()
        if 'timestamp' not in df_spot.columns:
            df_spot = df_spot.reset_index()
        df_spot['timestamp'] = pd.to_datetime(df_spot['timestamp'])
        df_spot = df_spot.sort_values('timestamp').reset_index(drop=True)
        df_spot['date'] = df_spot['timestamp'].dt.date
        if 'regime' not in df_spot.columns:
            from strategies.strategy_20 import Strategy_20
            strat = Strategy_20()
            df_spot = strat.generate_signals(df_spot)

    unique_dates = sorted(df_spot['date'].unique())
    daily_groups = {d: g.reset_index(drop=True) for d, g in df_spot.groupby('date')}
    cache_dir = "backtest_data/contract_cache"
    
    if lot_size is None:
        lot_size = 65
        
    if df_cache is None:
        all_files = glob.glob(os.path.join(cache_dir, f"{symbol.lower()}_*.csv"))
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
    
    reenter_next_day = {"CALL": False, "PUT": False}
    completed_trades = []
    trade_id_counter = 1
    
    for i, curr_date in enumerate(unique_dates):
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        curr_weekday = curr_date.weekday()
        day_df = daily_groups[curr_date]
        
        # Sort the day's spot candles to run sequentially
        day_df = day_df.sort_values('timestamp').reset_index(drop=True)
        
        # Determine Weekly and Monthly Expiries for matching on entry
        expiries = sorted(df_cache[df_cache['file_date'] == curr_date_str]['expiry_date'].unique())
        if len(expiries) < 2:
            continue
            
        weekly_expiry = expiries[0]
        monthly_expiry = None
        for exp in expiries:
            exp_dt = datetime.strptime(exp, "%Y-%m-%d")
            today_dt = datetime.combine(curr_date, datetime.min.time())
            if (exp_dt - today_dt).days >= 18:
                monthly_expiry = exp
                break
        if not monthly_expiry:
            monthly_expiry = expiries[-1]
            
        if weekly_expiry == monthly_expiry:
            for exp in expiries[1:]:
                if exp != weekly_expiry:
                    monthly_expiry = exp
                    break
                    
        # 0. Settle expired weekly shorts or monthly longs at start of day
        day_exit_spot = float(day_df.iloc[-1]['close'])
        for stance in ["CALL", "PUT"]:
            port = active_portfolio[stance]
            
            # Settle expired weekly shorts
            if port["weekly_short1"] is not None:
                if curr_date_str >= port["weekly_short1"]["expiry_date"]:
                    for leg_name in ["weekly_short1", "weekly_short2"]:
                        leg = port[leg_name]
                        if leg is not None:
                            strike = leg["strike"]
                            entry_px = leg["entry_px"]
                            if stance == "CALL":
                                settlement_px = max(0.0, day_exit_spot - strike)
                            else:
                                settlement_px = max(0.0, strike - day_exit_spot)
                            pnl = (settlement_px - entry_px) * leg["qty"] * lot_size
                            completed_trades.append({
                                'Trade_ID': leg['trade_id'],
                                'Stance': f"{stance}_CALENDAR",
                                'Leg': leg_name.upper(),
                                'Strike': strike,
                                'Expiry_Date': leg['expiry_date'],
                                'Entry_Date': leg['entry_date'],
                                'Exit_Date': curr_date_str,
                                'Entry_Spot': leg['entry_spot'],
                                'Exit_Spot': day_exit_spot,
                                'Entry_Px': entry_px,
                                'Exit_Px': settlement_px,
                                'Qty': leg["qty"],
                                'Net_PnL': pnl,
                                'Status': 'SETTLED',
                                'Exit_Time': '15:20'
                            })
                            port[leg_name] = None
                            
            # Settle expired monthly longs
            if port["monthly_long"] is not None:
                if curr_date_str >= port["monthly_long"]["expiry_date"]:
                    leg = port["monthly_long"]
                    strike = leg["strike"]
                    entry_px = leg["entry_px"]
                    if stance == "CALL":
                        settlement_px = max(0.0, day_exit_spot - strike)
                    else:
                        settlement_px = max(0.0, strike - day_exit_spot)
                    pnl = (settlement_px - entry_px) * leg["qty"] * lot_size
                    completed_trades.append({
                        'Trade_ID': leg['trade_id'],
                        'Stance': f"{stance}_CALENDAR",
                        'Leg': 'MONTHLY_LONG',
                        'Strike': strike,
                        'Expiry_Date': leg['expiry_date'],
                        'Entry_Date': leg['entry_date'],
                        'Exit_Date': curr_date_str,
                        'Entry_Spot': leg['entry_spot'],
                        'Exit_Spot': day_exit_spot,
                        'Entry_Px': entry_px,
                        'Exit_Px': settlement_px,
                        'Qty': leg["qty"],
                        'Net_PnL': pnl,
                        'Status': 'SETTLED',
                        'Exit_Time': '15:20'
                    })
                    port["monthly_long"] = None
        
        # 1. Load option contract dataframes for the current day if active positions exist
        active_contracts = {}
        for stance in ["CALL", "PUT"]:
            port = active_portfolio[stance]
            opt_type = 'CE' if stance == "CALL" else 'PE'
            
            for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
                leg = port[leg_name]
                if leg is not None:
                    c_df = load_contract_df(df_cache, leg['strike'], opt_type, leg['expiry_date'], curr_date_str)
                    active_contracts[f"{stance}_{leg_name}"] = c_df
                    
        # 2. Iterate minute-by-minute across the trading day (9:15 to 15:30)
        # We start checking exits from 09:20 onwards
        for idx, row in day_df.iterrows():
            ts = row['timestamp']
            ts_time_str = ts.strftime('%H:%M')
            ts_dt = ts.to_pydatetime()
            
            # --- MONITOR & EXECUTE EXITS ---
            for stance in ["CALL", "PUT"]:
                port = active_portfolio[stance]
                opt_type = 'CE' if stance == "CALL" else 'PE'
                
                if port["monthly_long"] is not None:
                    # Get prices of active legs at this minute
                    spot_px = float(row['close'])
                    l_val  = get_price_at_minute(active_contracts.get(f"{stance}_monthly_long"), ts)
                    if l_val is None:
                        entry_spot = port["monthly_long"]["entry_spot"]
                        entry_px = port["monthly_long"]["entry_px"]
                        delta = 0.6
                        if stance == "CALL":
                            l_val = max(0.0, entry_px + delta * (spot_px - entry_spot))
                        else:
                            l_val = max(0.0, entry_px - delta * (spot_px - entry_spot))
                    
                    s1_val = None
                    if port["weekly_short1"] is not None:
                        s1_val = get_price_at_minute(active_contracts.get(f"{stance}_weekly_short1"), ts)
                        if s1_val is None:
                            entry_spot = port["weekly_short1"]["entry_spot"]
                            entry_px = port["weekly_short1"]["entry_px"]
                            delta = 0.3
                            if stance == "CALL":
                                s1_val = max(0.0, entry_px + delta * (spot_px - entry_spot))
                            else:
                                s1_val = max(0.0, entry_px - delta * (spot_px - entry_spot))
                        
                    s2_val = None
                    if port["weekly_short2"] is not None:
                        s2_val = get_price_at_minute(active_contracts.get(f"{stance}_weekly_short2"), ts)
                        if s2_val is None:
                            entry_spot = port["weekly_short2"]["entry_spot"]
                            entry_px = port["weekly_short2"]["entry_px"]
                            delta = 0.8
                            if stance == "CALL":
                                s2_val = max(0.0, entry_px + delta * (spot_px - entry_spot))
                            else:
                                s2_val = max(0.0, entry_px - delta * (spot_px - entry_spot))
                        
                    has_all_prices = True
                    if has_all_prices:
                        long_pnl   = (l_val  - port["monthly_long"]["entry_px"])  * port["monthly_long"]["qty"]  * lot_size
                        
                        short1_pnl = 0.0
                        if port["weekly_short1"] is not None:
                            short1_pnl = (port["weekly_short1"]["entry_px"] - s1_val) * lot_size
                            
                        short2_pnl = 0.0
                        if port["weekly_short2"] is not None:
                            short2_pnl = (port["weekly_short2"]["entry_px"] - s2_val) * lot_size
                            
                        total_pnl  = long_pnl + short1_pnl + short2_pnl
                        
                        trigger_exit = False
                        status_reason = 'EARLY_EXIT'
                        
                        if total_pnl >= target_exit_pnl:
                            trigger_exit = True
                            status_reason = 'EARLY_EXIT'
                        elif stop_loss_pnl is not None and total_pnl <= stop_loss_pnl:
                            trigger_exit = True
                            status_reason = 'STOP_LOSS_EXIT'
                            
                        # Weekly Expiry forced close at 15:20 on Expiry Day
                        if port["weekly_short1"] is not None:
                            is_expiry_day = (curr_date_str == port["weekly_short1"]["expiry_date"])
                            if is_expiry_day and ts_time_str == '15:20':
                                trigger_exit = True
                                status_reason = 'WEEKLY_EXPIRY'
                                
                        if trigger_exit:
                            # Exit all active legs at this minute's price
                            for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
                                leg = port[leg_name]
                                if leg is not None:
                                    pnl = 0.0
                                    if leg_name == "monthly_long":
                                        exit_val = l_val
                                        pnl = (exit_val - leg["entry_px"]) * leg["qty"] * lot_size
                                    elif leg_name == "weekly_short1":
                                        exit_val = s1_val
                                        pnl = (leg["entry_px"] - exit_val) * lot_size
                                    else:
                                        exit_val = s2_val
                                        pnl = (leg["entry_px"] - exit_val) * lot_size
                                        
                                    completed_trades.append({
                                        'Trade_ID': leg['trade_id'],
                                        'Stance': f"{stance}_CALENDAR",
                                        'Leg': leg_name.upper(),
                                        'Strike': leg['strike'],
                                        'Expiry_Date': leg['expiry_date'],
                                        'Entry_Date': leg['entry_date'],
                                        'Exit_Date': curr_date_str,
                                        'Entry_Spot': leg['entry_spot'],
                                        'Exit_Spot': float(row['close']),
                                        'Entry_Px': leg['entry_px'],
                                        'Exit_Px': exit_val,
                                        'Qty': leg['qty'],
                                        'Net_PnL': pnl,
                                        'Status': status_reason,
                                        'Exit_Time': ts_time_str
                                    })
                                    port[leg_name] = None
                            # If exited on SL or profit target, enable next-day re-entry
                            if status_reason in ['EARLY_EXIT', 'STOP_LOSS_EXIT']:
                                reenter_next_day[stance] = True
            
            # --- EVALUATE ROLLOVERS & ENTRIES (Only at 09:20 AM) ---
            if ts_time_str == '09:20':
                entry_spot = float(row['close'])
                day_cache = df_cache[df_cache['file_date'] == curr_date_str]
                
                for stance in ["CALL", "PUT"]:
                    port = active_portfolio[stance]
                    
                    # 1. Roll Near-Expiry Monthly Longs
                    if port["monthly_long"] is not None and roll_threshold_days > 0:
                        exp_dt = datetime.strptime(port["monthly_long"]["expiry_date"], "%Y-%m-%d")
                        days_to_expiry = (exp_dt - ts_dt).days
                        if days_to_expiry < roll_threshold_days:
                            opt_type = 'CE' if stance == "CALL" else 'PE'
                            l_df = load_contract_df(df_cache, port["monthly_long"]["strike"], opt_type, port["monthly_long"]["expiry_date"], curr_date_str)
                            l_val = get_price_at_minute(l_df, ts)
                            if l_val is not None:
                                pnl = (l_val - port["monthly_long"]["entry_px"]) * num_lots_long * 3 * lot_size
                                completed_trades.append({
                                    'Trade_ID': port["monthly_long"]['trade_id'],
                                    'Stance': f"{stance}_CALENDAR",
                                    'Leg': 'MONTHLY_LONG',
                                    'Strike': port["monthly_long"]['strike'],
                                    'Expiry_Date': port["monthly_long"]['expiry_date'],
                                    'Entry_Date': port["monthly_long"]['entry_date'],
                                    'Exit_Date': curr_date_str,
                                    'Entry_Spot': port["monthly_long"]['entry_spot'],
                                    'Exit_Spot': entry_spot,
                                    'Entry_Px': port["monthly_long"]['entry_px'],
                                    'Exit_Px': l_val,
                                    'Qty': num_lots_long * 3,
                                    'Net_PnL': pnl,
                                    'Status': 'ROLLED_OUT',
                                    'Exit_Time': '09:20'
                                })
                                port["monthly_long"] = None
                                
                    # 2. Close Monthly Long on Regime Shift
                    if trade_both_sides == 0:
                        regime = row.get('regime')
                        if regime and f"{stance}_CALENDAR" != regime:
                            if port["monthly_long"] is not None:
                                opt_type = 'CE' if stance == "CALL" else 'PE'
                                l_df = load_contract_df(df_cache, port["monthly_long"]["strike"], opt_type, port["monthly_long"]["expiry_date"], curr_date_str)
                                l_val = get_price_at_minute(l_df, ts)
                                if l_val is not None:
                                    pnl = (l_val - port["monthly_long"]["entry_px"]) * num_lots_long * 3 * lot_size
                                    completed_trades.append({
                                        'Trade_ID': port["monthly_long"]['trade_id'],
                                        'Stance': f"{stance}_CALENDAR",
                                        'Leg': 'MONTHLY_LONG',
                                        'Strike': port["monthly_long"]['strike'],
                                        'Expiry_Date': port["monthly_long"]['expiry_date'],
                                        'Entry_Date': port["monthly_long"]['entry_date'],
                                        'Exit_Date': curr_date_str,
                                        'Entry_Spot': port["monthly_long"]['entry_spot'],
                                        'Exit_Spot': entry_spot,
                                        'Entry_Px': port["monthly_long"]['entry_px'],
                                        'Exit_Px': l_val,
                                        'Qty': num_lots_long * 3,
                                        'Net_PnL': pnl,
                                        'Status': 'REGIME_SHIFT',
                                        'Exit_Time': '09:20'
                                    })
                                    port["monthly_long"] = None
                            continue

                    # 3. Enter Positions
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
                        for _, r in df_leg.iterrows():
                            try:
                                c_df = load_contract_df(df_cache, r['strike'], opt_type, r['expiry_date'], curr_date_str)
                                px = get_price_at_minute(c_df, ts)
                                if px is not None and px > 0:
                                    diff = abs(px - target_p)
                                    if diff < min_diff:
                                        min_diff = diff
                                        best_leg = {
                                            'strike': r['strike'],
                                            'expiry_date': r['expiry_date'],
                                            'entry_px': px
                                        }
                            except Exception:
                                continue
                        return best_leg
                        
                    # Match Spreads
                    long_leg = None
                    if port["monthly_long"] is None:
                        long_leg = match_leg(chain_monthly, target_monthly_p)
                    else:
                        # Fetch price of currently held monthly long
                        c_df = load_contract_df(df_cache, port["monthly_long"]['strike'], opt_type, port["monthly_long"]['expiry_date'], curr_date_str)
                        curr_px = get_price_at_minute(c_df, ts)
                        if curr_px is not None:
                            long_leg = {
                                'strike': port["monthly_long"]['strike'],
                                'expiry_date': port["monthly_long"]['expiry_date'],
                                'entry_px': curr_px
                            }
                            
                    short1_leg = match_leg(chain_weekly, target_otm_p)
                    short2_leg = match_leg(chain_weekly, target_itm_p)
                    
                    if not long_leg or not short1_leg or not short2_leg:
                        continue
                        
                    # Ensure short legs do not overlap on the same strike
                    if short1_leg['strike'] == short2_leg['strike']:
                        continue
                        
                    # Golden Constraint Safety Filter
                    gap1 = abs(short1_leg['strike'] - long_leg['strike'])
                    gap2 = abs(short2_leg['strike'] - long_leg['strike'])
                    if max(gap1, gap2) > 1000.0:
                        # Skip trade if gap violates constraint
                        continue
                        
                    # Enter monthly long
                    if port["monthly_long"] is None:
                        port["monthly_long"] = {
                            'trade_id': trade_id_counter,
                            'strike': long_leg['strike'],
                            'expiry_date': long_leg['expiry_date'],
                            'entry_px': long_leg['entry_px'],
                            'entry_date': curr_date_str,
                            'entry_spot': entry_spot,
                            'qty': num_lots_long * 3
                        }
                        trade_id_counter += 1
                        
                    # Enter weekly shorts
                    port["weekly_short1"] = {
                        'trade_id': trade_id_counter,
                        'strike': short1_leg['strike'],
                        'expiry_date': short1_leg['expiry_date'],
                        'entry_px': short1_leg['entry_px'],
                        'entry_date': curr_date_str,
                        'entry_spot': entry_spot,
                        'qty': -1
                    }
                    trade_id_counter += 1
                    
                    port["weekly_short2"] = {
                        'trade_id': trade_id_counter,
                        'strike': short2_leg['strike'],
                        'expiry_date': short2_leg['expiry_date'],
                        'entry_px': short2_leg['entry_px'],
                        'entry_date': curr_date_str,
                        'entry_spot': entry_spot,
                        'qty': -1
                    }
                    trade_id_counter += 1
                    
                    # Refresh active_contracts cache for the newly entered legs
                    for leg_name, leg_data in [("monthly_long", port["monthly_long"]), ("weekly_short1", port["weekly_short1"]), ("weekly_short2", port["weekly_short2"])]:
                        c_df = load_contract_df(df_cache, leg_data['strike'], opt_type, leg_data['expiry_date'], curr_date_str)
                        active_contracts[f"{stance}_{leg_name}"] = c_df

    # Forced close remaining at the end
    last_date = unique_dates[-1]
    last_date_str = last_date.strftime("%Y-%m-%d")
    day_df = daily_groups[last_date]
    exit_candle = day_df.iloc[-1:]
    exit_spot = float(exit_candle['close'].iloc[0])
    
    for stance in ["CALL", "PUT"]:
        port = active_portfolio[stance]
        opt_type = 'CE' if stance == "CALL" else 'PE'
        for leg_name in ["monthly_long", "weekly_short1", "weekly_short2"]:
            leg = port[leg_name]
            if leg is not None:
                strike = leg["strike"]
                entry_px = leg["entry_px"]
                qty = leg["qty"]
                
                l_df = load_contract_df(df_cache, strike, opt_type, leg["expiry_date"], last_date_str)
                market_px = get_price_at_minute(l_df, exit_candle['timestamp'].iloc[0])
                
                if market_px is not None:
                    settlement_px = market_px
                else:
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
                    'Expiry_Date': leg['expiry_date'],
                    'Entry_Date': leg['entry_date'],
                    'Exit_Date': last_date_str,
                    'Entry_Spot': leg['entry_spot'],
                    'Exit_Spot': exit_spot,
                    'Entry_Px': entry_px,
                    'Exit_Px': settlement_px,
                    'Qty': qty,
                    'Net_PnL': pnl,
                    'Status': 'FORCED_CLOSED',
                    'Exit_Time': '15:29'
                })
                port[leg_name] = None
                
    return pd.DataFrame(completed_trades)
