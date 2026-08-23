"""
Dedicated Strategy 20 Parity Runner
Executes 1-Trade-Per-Day 15-Min Trend-Directional Option Writing
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from backtest_engine import SimulationEngine
from strategies import BacktestConfig
from research_and_development.backtest_strategy20_intraday import get_price_at_minute

def main():
    parser = argparse.ArgumentParser(description="Strategy 20 Dedicated 1-Trade-Per-Day Option Selling Runner")
    parser.add_argument("--days", "-d", type=int, default=365, help="Number of days to backtest (default: 365)")
    args = parser.parse_args()
    
    print("=" * 85)
    print("         STRATEGY 20: 15-MIN TREND-DIRECTIONAL OPTION SELLING PARITY RUNNER")
    print("=" * 85)
    
    config = BacktestConfig()
    # Align active strategy to Strategy_20 to load overrides
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    config.ENABLE_STRATEGY_20 = True
    config.apply_strategy_defaults("Strategy_20")
    
    engine = SimulationEngine(config, instrument_name="NIFTY", offline_mode=False, backtest_days=args.days)
    engine.load_data()
    
    df_spot = engine.df_spot
    if df_spot is None or df_spot.empty:
        print("[ERROR] Could not load spot data for NIFTY.")
        return

    df_spot = df_spot.sort_index()
    cutoff_date = df_spot.index.max() - pd.Timedelta(days=args.days)
    df_spot_sub = df_spot[df_spot.index >= cutoff_date]
    
    spot_by_date = {d: grp for d, grp in df_spot_sub.groupby(df_spot_sub.index.date)}
    unique_dates = sorted(list(spot_by_date.keys()))
    
    inst_cfg = engine.inst_config
    target_profit = float(inst_cfg.get("target_profit", 2000.0))
    stop_loss = float(inst_cfg.get("stop_loss", -2500.0))
    leg_sl_pct = float(inst_cfg.get("leg_sl_pct", 0.35))
    num_lots = int(inst_cfg.get("num_lots_sell", 1))
    
    print(f"[CONFIG] Backtest Days Requested: {args.days}")
    print(f"[CONFIG] Actual Trading Days:      {len(unique_dates)} (from {unique_dates[0]} to {unique_dates[-1]})")
    print(f"[CONFIG] Execution Rule:          1 Trade / Day at 09:30 AM (Trend PE/CE Sell)")
    print(f"[CONFIG] Risk Parameters:         {leg_sl_pct*100:.0f}% Premium SL, +Rs.{target_profit:,.0f} Target, -Rs.{abs(stop_loss):,.0f} Max SL, Lots: {num_lots}\n")

    strike_step = int(inst_cfg.get("strike_step", 50))
    lot_size = int(inst_cfg.get("lot_size", 65))
    slippage_pts = 1.5
    charges_per_trade = 70.0
    
    results = []
    
    for trade_date in unique_dates:
        day_df = spot_by_date[trade_date]
        entry_dt = pd.to_datetime(f"{trade_date} 09:30:00")
        if entry_dt not in day_df.index:
            valid_times = day_df.index[day_df.index >= entry_dt]
            if len(valid_times) == 0:
                continue
            entry_dt = valid_times[0]

        # Calculate 15-min trend
        df_15 = day_df.resample('15min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()
        
        df_15['ema9'] = df_15['close'].ewm(span=9, adjust=False).mean()
        df_15['ema21'] = df_15['close'].ewm(span=21, adjust=False).mean()
        df_15['trend'] = np.where(df_15['ema9'] >= df_15['ema21'], 1, -1)
        
        valid_15 = df_15[df_15.index < entry_dt]
        trend_val = 1 if valid_15.empty else valid_15['trend'].iloc[-1]
            
        entry_spot = day_df.loc[entry_dt, 'close']
        atm_strike = int(round(entry_spot / strike_step) * strike_step)
        
        expiry_date_str = engine._get_actual_expiry_date(trade_date, 0)
        sel_type = 'PE' if trend_val == 1 else 'CE'
        sel_strike = atm_strike
            
        c_df = engine._get_option_candles(sel_strike, sel_type, trade_date, expiry_date_str=expiry_date_str)
        if c_df is None or c_df.empty:
            continue
            
        px = get_price_at_minute(c_df, entry_dt)
        if px is None or px <= 0:
            continue
            
        entry_px = max(0.05, px - slippage_pts)
        sl_px = entry_px * (1.0 + leg_sl_pct)
        
        closed_pnl = 0.0
        exit_px = entry_px
        exit_reason = "HOLD"
        
        sim_df = day_df.loc[entry_dt:]
        
        for ts, spot_row in sim_df.iterrows():
            ts_time = ts.time()
            curr_px = get_price_at_minute(c_df, ts) or entry_px
            running_pnl = (entry_px - curr_px) * lot_size * num_lots
            
            if curr_px >= sl_px:
                exit_px = curr_px + slippage_pts
                closed_pnl = (entry_px - exit_px) * lot_size * num_lots
                exit_reason = f"LEG_SL_{leg_sl_pct*100:.0f}%"
                break
            elif running_pnl <= stop_loss * num_lots:
                exit_px = curr_px + slippage_pts
                closed_pnl = (entry_px - exit_px) * lot_size * num_lots
                exit_reason = f"MAX_SL_{abs(stop_loss)}"
                break
            elif running_pnl >= target_profit * num_lots:
                exit_px = curr_px + slippage_pts
                closed_pnl = (entry_px - exit_px) * lot_size * num_lots
                exit_reason = f"TARGET_{target_profit}"
                break
            elif ts_time >= pd.to_datetime("15:15:00").time():
                exit_px = curr_px + slippage_pts
                closed_pnl = (entry_px - exit_px) * lot_size * num_lots
                exit_reason = "EOD_EXIT_1515"
                break
                
        net_pnl = closed_pnl - charges_per_trade
        results.append({
            'Date': trade_date,
            'Entry_Time': f"{trade_date} 09:30:00",
            'Type': sel_type,
            'Strike': sel_strike,
            'Expiry': expiry_date_str,
            'Entry_Spot': entry_spot,
            'Entry_Price': round(entry_px, 2),
            'Exit_Price': round(exit_px, 2),
            'Gross_PnL': round(closed_pnl, 2),
            'Charges': charges_per_trade,
            'Net_PnL': round(net_pnl, 2),
            'Exit_Reason': exit_reason
        })
        
    df_res = pd.DataFrame(results)
    if df_res.empty:
        print("[WARN] No trades generated.")
        return
        
    total_trades = len(df_res)
    win_trades = len(df_res[df_res['Net_PnL'] > 0])
    win_rate = (win_trades / total_trades) * 100
    gross_pnl = df_res['Gross_PnL'].sum()
    charges = df_res['Charges'].sum()
    net_pnl = df_res['Net_PnL'].sum()
    
    gross_win = df_res[df_res['Net_PnL'] > 0]['Net_PnL'].sum()
    gross_loss = abs(df_res[df_res['Net_PnL'] < 0]['Net_PnL'].sum())
    profit_factor = gross_win / gross_loss if gross_loss > 0 else np.inf
    
    cum_pnl = df_res['Net_PnL'].cumsum()
    peak = cum_pnl.cummax()
    dd = cum_pnl - peak
    max_dd = abs(dd.min())
    
    print("=" * 85)
    print("                 STRATEGY 20 OFFICIAL 180-DAY BACKTEST SUMMARY")
    print("=" * 85)
    print(f" Total Trading Days Evaluated: {total_trades}")
    print(f" Total Trades Executed:       {total_trades} (Exactly 1 trade/day)")
    print(f" Win Rate:                    {win_rate:.1f}% ({win_trades} Wins / {total_trades - win_trades} Losses)")
    print(f" Profit Factor:               {profit_factor:.2f}")
    print(f" Gross PnL:                   Rs.{gross_pnl:,.2f}")
    print(f" Charges & Slippage:          Rs.{charges:,.2f}")
    print(f" Net PnL (1 Lot):             Rs.{net_pnl:,.2f}")
    print(f" Avg Daily Net PnL:           Rs.{net_pnl/total_trades:,.2f} / day")
    print(f" Max Drawdown:                Rs.{max_dd:,.2f}")
    print("=" * 85)
    
    output_csv = os.path.join(BASE_DIR, "strategy_20_backtest_results.csv")
    df_res.to_csv(output_csv, index=False)
    print(f"\n[SUCCESS] Detailed trade log saved to: {output_csv}\n")

if __name__ == "__main__":
    main()
