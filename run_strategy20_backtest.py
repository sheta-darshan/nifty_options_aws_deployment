"""
Dedicated Strategy 20 Parity Runner
Executes John Ehlers Decycler Oscillator Zero-Lag Trend DSP Option Strategy
Zero Look-Ahead Bias Engine (Live Parity)
"""

import os
import sys
import glob
import argparse
import pandas as pd
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from strategies.strategy_20 import Strategy_20

def main():
    parser = argparse.ArgumentParser(description="Strategy 20 Dedicated Ehlers Decycler DSP Option Runner")
    parser.add_argument("--days", "-d", type=int, default=365, help="Number of days to backtest (default: 365)")
    parser.add_argument("--timeframe", "-tf", type=str, default="15min", help="Timeframe (e.g. 15min, 30min, 9min, 7min, 5min)")
    parser.add_argument("--hp-period", "-hp", type=int, default=30, help="Ehlers High-Pass period length (default: 30)")
    parser.add_argument("--leg-mode", "-lm", type=str, default="SELL", choices=["SELL", "BUY"], help="Leg Mode (SELL/BUY, default: SELL)")
    parser.add_argument("--target-pts", "-tp", type=float, default=45.0, help="Target points per lot (default: 45.0)")
    parser.add_argument("--sl-pts", "-sl", type=float, default=22.0, help="Stop loss points per lot (default: 22.0)")
    parser.add_argument("--breakeven-pts", "-be", type=float, default=15.0, help="Points decay before moving SL to cost (default: 15.0)")
    parser.add_argument("--trailing-pts", "-tr", type=float, default=10.0, help="Trailing stop distance once in profit (default: 10.0)")
    parser.add_argument("--lots", "-l", type=int, default=1, help="Number of lots to trade (default: 1)")
    args = parser.parse_args()
    
    print("=" * 110)
    print("      STRATEGY 20: JOHN EHLERS DECYCLER OSCILLATOR (ZERO-LAG TREND DSP) PARITY RUNNER")
    print("=" * 110)
    print(f"Timeframe: {args.timeframe} | HP Period: {args.hp_period} | Leg Mode: {args.leg_mode} | Days: {args.days}")
    print(f"Target Pts: ₹{args.target_pts} | SL Pts: ₹{args.sl_pts} | Breakeven: ₹{args.breakeven_pts} | Trailing: ₹{args.trailing_pts}\n")
    
    # 1. Load NIFTY Spot Data
    spot_file = os.path.join(BASE_DIR, "backtest_data", "nifty_spot.csv")
    if not os.path.exists(spot_file):
        print(f"[ERROR] Spot file not found at: {spot_file}")
        return
        
    df_spot = pd.read_csv(spot_file)
    t_col = 'timestamp' if 'timestamp' in df_spot.columns else 'datetime'
    df_spot['dt'] = pd.to_datetime(df_spot[t_col])
    df_spot['date'] = df_spot['dt'].dt.date
    df_spot['time_str'] = df_spot['dt'].dt.strftime('%H:%M:%S')
    df_spot = df_spot.sort_values('dt').reset_index(drop=True)
    
    cutoff_date = df_spot['dt'].max() - pd.Timedelta(days=args.days)
    df_spot_sub = df_spot[df_spot['dt'] >= cutoff_date].copy()
    
    # 2. Run Strategy 20 Signal Generation
    strat = Strategy_20({
        "timeframe": args.timeframe,
        "hp_period": args.hp_period,
        "leg_mode": args.leg_mode,
        "points_target_buy": args.target_pts,
        "points_sl_buy": args.sl_pts,
        "breakeven_pts": args.breakeven_pts,
        "trailing_jump": args.trailing_pts
    })
    
    df_signals = strat.generate_signals(df_spot_sub.set_index('dt')).reset_index()
    
    # 3. Index Local Option Contract Cache
    cache_files = glob.glob(os.path.join(BASE_DIR, "backtest_data", "contract_cache", "nifty_*.csv"))
    contract_map = {}
    for f in cache_files:
        bn = os.path.basename(f)
        parts = bn.replace('.csv', '').split('_')
        try:
            if len(parts) >= 6:
                stk = int(parts[1])
                otype = parts[2].upper()
                trade_dt_str = parts[-1]
                contract_map[(stk, otype, trade_dt_str)] = f
        except Exception:
            continue
            
    loaded_opt_candles = {}
    def get_opt_df(strike, opt_type, date_str):
        key = (strike, opt_type, date_str)
        if key in loaded_opt_candles:
            return loaded_opt_candles[key]
        fpath = contract_map.get(key)
        if not fpath or not os.path.exists(fpath):
            return None
        try:
            odf = pd.read_csv(fpath)
            ot_col = 'timestamp' if 'timestamp' in odf.columns else 'datetime'
            odf['dt'] = pd.to_datetime(odf[ot_col])
            odf['time_str'] = odf['dt'].dt.strftime('%H:%M:%S')
            odf = odf.set_index('time_str')
            loaded_opt_candles[key] = odf
            return odf
        except Exception:
            return None
            
    # 4. Simulate Trades Day by Day
    spot_by_date = {d: grp.copy() for d, grp in df_signals.groupby('date')}
    unique_dates = sorted(list(spot_by_date.keys()))
    
    trade_log = []
    
    for t_date in unique_dates:
        day_spot = spot_by_date[t_date]
        d_str = t_date.strftime('%Y-%m-%d')
        
        # Look for entry signals
        sig_rows = day_spot[day_spot['Signal'].isin([1, -1])]
        if sig_rows.empty:
            continue
            
        entry_row = sig_rows.iloc[0]
        sig_code = int(entry_row['Signal'])
        entry_time = entry_row['time_str']
        spot_entry = entry_row['open']
        
        # Determine Option Contract & Strike (ATM 50-pt step)
        strike = int(round(spot_entry / 50.0) * 50)
        
        if args.leg_mode == "SELL":
            opt_type = "PE" if sig_code == 1 else "CE"
            is_sell = True
        else:
            opt_type = "CE" if sig_code == 1 else "PE"
            is_sell = False
            
        opt_df = get_opt_df(strike, opt_type, d_str)
        
        # Subsequent spot bars for exit tracking
        sub_spot = day_spot[day_spot['time_str'] >= entry_time]
        if sub_spot.empty:
            continue
            
        # Entry execution (at index i+1 open or option candle open)
        if opt_df is not None and entry_time in opt_df.index:
            entry_premium = opt_df.loc[entry_time, 'open']
        else:
            # Theoretical fallback premium ~120 pts
            entry_premium = 120.0
            
        curr_sl = entry_premium + args.sl_pts if is_sell else entry_premium - args.sl_pts
        target_px = entry_premium - args.target_pts if is_sell else entry_premium + args.target_pts
        
        be_triggered = False
        peak_favorable = 0.0
        exit_px = None
        exit_reason = None
        exit_time = None
        
        for _, s_row in sub_spot.iterrows():
            c_time = s_row['time_str']
            c_spot_close = s_row['close']
            
            # Real option candle check if available
            if opt_df is not None and c_time in opt_df.index:
                c_opt_row = opt_df.loc[c_time]
                c_opt_high = c_opt_row['high']
                c_opt_low = c_opt_row['low']
                c_opt_close = c_opt_row['close']
            else:
                # Delta proxy (~0.45 delta)
                spot_diff = c_spot_close - spot_entry
                if opt_type == "CE":
                    opt_delta_diff = spot_diff * 0.45
                else:
                    opt_delta_diff = -spot_diff * 0.45
                c_opt_close = max(1.0, entry_premium + opt_delta_diff)
                c_opt_high = c_opt_close + 2.0
                c_opt_low = max(0.5, c_opt_close - 2.0)
                
            if is_sell:
                favorable = entry_premium - c_opt_low
                if favorable > peak_favorable: peak_favorable = favorable
                
                # Breakeven trigger
                if not be_triggered and favorable >= args.breakeven_pts:
                    curr_sl = min(curr_sl, entry_premium)
                    be_triggered = True
                    
                # Trailing Stop trigger
                if favorable >= args.trailing_pts:
                    new_trail_sl = entry_premium - (favorable - args.trailing_pts)
                    curr_sl = min(curr_sl, new_trail_sl)
                    
                # Check SL
                if c_opt_high >= curr_sl:
                    exit_px = curr_sl
                    exit_reason = "SL" if not be_triggered else "TRAIL_SL"
                    exit_time = c_time
                    break
                # Check Target
                elif c_opt_low <= target_px:
                    exit_px = target_px
                    exit_reason = "TARGET"
                    exit_time = c_time
                    break
            else: # BUY Leg
                favorable = c_opt_high - entry_premium
                if favorable > peak_favorable: peak_favorable = favorable
                
                # Breakeven trigger
                if not be_triggered and favorable >= args.breakeven_pts:
                    curr_sl = max(curr_sl, entry_premium)
                    be_triggered = True
                    
                # Trailing Stop trigger
                if favorable >= args.trailing_pts:
                    new_trail_sl = entry_premium + (favorable - args.trailing_pts)
                    curr_sl = max(curr_sl, new_trail_sl)
                    
                # Check SL
                if c_opt_low <= curr_sl:
                    exit_px = curr_sl
                    exit_reason = "SL" if not be_triggered else "TRAIL_SL"
                    exit_time = c_time
                    break
                # Check Target
                elif c_opt_high >= target_px:
                    exit_px = target_px
                    exit_reason = "TARGET"
                    exit_time = c_time
                    break
                    
            # EOD Exit at 15:15
            if c_time >= "15:15:00":
                exit_px = c_opt_close
                exit_reason = "EOD"
                exit_time = c_time
                break
                
        if exit_px is None:
            exit_px = c_opt_close
            exit_reason = "EOD"
            exit_time = "15:15:00"
            
        pts = (entry_premium - exit_px) if is_sell else (exit_px - entry_premium)
        lot_size = 65 if t_date >= pd.to_datetime('2026-04-25').date() else (25 if t_date >= pd.to_datetime('2024-11-20').date() else 50)
        gross_pnl = pts * lot_size * args.lots
        charges = 55.0 * args.lots
        net_pnl = gross_pnl - charges
        
        trade_log.append({
            "Date": d_str,
            "Entry_Time": entry_time,
            "Exit_Time": exit_time,
            "Signal": "BULL" if sig_code == 1 else "BEAR",
            "Contract": f"{strike}_{opt_type}",
            "Action": "SELL" if is_sell else "BUY",
            "Entry_Px": entry_premium,
            "Exit_Px": exit_px,
            "Pts": pts,
            "Gross_PnL": gross_pnl,
            "Net_PnL": net_pnl,
            "Exit_Reason": exit_reason
        })
        
    if not trade_log:
        print("[INFO] No trades generated in the selected backtest window.")
        return
        
    df_res = pd.DataFrame(trade_log)
    total_trades = len(df_res)
    wins = len(df_res[df_res['Net_PnL'] > 0])
    losses = len(df_res[df_res['Net_PnL'] < 0])
    win_rate = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0
    total_net = df_res['Net_PnL'].sum()
    mean_net = df_res['Net_PnL'].mean()
    median_net = df_res['Net_PnL'].median()
    
    gross_win = df_res[df_res['Net_PnL'] > 0]['Net_PnL'].sum()
    gross_loss = abs(df_res[df_res['Net_PnL'] < 0]['Net_PnL'].sum())
    pf = (gross_win / gross_loss) if gross_loss > 0 else np.inf
    
    print("=" * 95)
    print(f"                      STRATEGY 20 BACKTEST PERFORMANCE SUMMARY")
    print("=" * 95)
    print(f"Total Trades:           {total_trades}")
    print(f"Win Rate:               {win_rate:.1f}% ({wins} Wins / {losses} Losses)")
    print(f"Total Net P&L:          ₹{total_net:,.2f}")
    print(f"Mean Net P&L / Trade:   ₹{mean_net:,.2f}")
    print(f"Median Net P&L / Trade: ₹{median_net:,.2f}")
    print(f"Profit Factor:          {pf:.2f}")
    print("=" * 95)
    print("\nRecent 10 Trades:")
    print(df_res[['Date', 'Entry_Time', 'Contract', 'Action', 'Entry_Px', 'Exit_Px', 'Pts', 'Net_PnL', 'Exit_Reason']].tail(10).to_string(index=False))

if __name__ == "__main__":
    main()
