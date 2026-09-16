import os
import sys
import copy
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from strategies import BacktestConfig
from backtest_engine import SimulationEngine

def run_conviction_sizing_simulation(days=180):
    print("================================================================================")
    print(f" DYNAMIC CONVICTION SIZING EXPERIMENT ON NIFTY ({days} DAYS) ")
    print("================================================================================")

    config = BacktestConfig()
    config.LEG_MODE = "SELL"
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    config.ENABLE_STRATEGY_22 = True
    config.apply_strategy_defaults("Strategy_22")

    engine = SimulationEngine(config, instrument_name="NIFTY", offline_mode=False, backtest_days=days)
    engine.load_data()
    engine.inst_config['points_target_sell'] = 25.0
    engine.inst_config['points_sl_sell'] = 74.0
    # Run with 1 lot base so we get per-lot PnL and charges
    engine.inst_config['num_lots_sell'] = 1
    df_trades = engine.run(write_to_csv=False)

    if df_trades.empty:
        print("[ERROR] No trades generated.")
        return

    # 1. Compute 15m Supertrend to label High vs Standard conviction
    import pandas_ta as ta
    df_spot = engine.df_spot
    df_15m = df_spot.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    st_15m = ta.supertrend(df_15m['high'], df_15m['low'], df_15m['close'], length=10, multiplier=2.5)
    st_dir_col = [c for c in st_15m.columns if c.startswith('SUPERTd_')][0]
    df_15m['ST_15m_Dir'] = st_15m[st_dir_col].shift(1)  # Shifted by 1
    df_spot_ind = df_spot.join(df_15m[['ST_15m_Dir']], how='left').ffill()

    # 2. Tag each trade with conviction
    conviction_labels = []
    for idx, trade in df_trades.iterrows():
        e_time = pd.to_datetime(trade['Entry_Time'])
        trade_type = trade['Type']
        is_high = False
        if e_time in df_spot_ind.index:
            st_dir = df_spot_ind.loc[e_time, 'ST_15m_Dir']
            if isinstance(st_dir, pd.Series):
                st_dir = st_dir.iloc[0]
            if trade_type == "PE" and st_dir == 1:
                is_high = True
            elif trade_type == "CE" and st_dir == -1:
                is_high = True
        conviction_labels.append("HIGH" if is_high else "STANDARD")

    df_trades['Conviction'] = conviction_labels

    high_conv_trades = df_trades[df_trades['Conviction'] == "HIGH"]
    std_conv_trades = df_trades[df_trades['Conviction'] == "STANDARD"]

    print(f"\nBreakdown of Detected Trades:")
    print(f"  Total Trades:           {len(df_trades)}")
    print(f"  High Conviction (15m):  {len(high_conv_trades)} ({len(high_conv_trades)/len(df_trades)*100:.1f}%) | WR: {(len(high_conv_trades[high_conv_trades['PnL']>0])/len(high_conv_trades))*100:.1f}%")
    print(f"  Standard Conv (5m only):{len(std_conv_trades)} ({len(std_conv_trades)/len(df_trades)*100:.1f}%) | WR: {(len(std_conv_trades[std_conv_trades['PnL']>0])/len(std_conv_trades))*100:.1f}%")
    print("-" * 80)

    # 3. Simulate Sizing Schemes
    # Note: df_trades was run with 1 lot (65 qty).
    # To scale to N lots:
    # Gross PnL scales linearly with N
    # Charges scale with turnover/contracts: Base charge ~Rs.35 + STT/turnover
    # We can accurately scale: Qty = 65 * N. 
    # Option Pts = (Entry_Price - Exit_Price).
    lot_size = 65

    schemes = [
        {"name": "Flat Baseline (5 Lots)", "base_lots": 5, "high_lots": 5},
        {"name": "Scheme A (3 Base / 6 High)", "base_lots": 3, "high_lots": 6},
        {"name": "Scheme B (3 Base / 7 High)", "base_lots": 3, "high_lots": 7},
        {"name": "Scheme C (2 Base / 6 High)", "base_lots": 2, "high_lots": 6},
        {"name": "Scheme D (Filter: 0 Base / 5 High)", "base_lots": 0, "high_lots": 5},
        {"name": "Scheme E (Filter: 0 Base / 7 High)", "base_lots": 0, "high_lots": 7},
    ]

    print(f"\n{'Sizing Scheme':<35} | {'Trades':>6} | {'Win Rate':>8} | {'PF':>6} | {'Gross PnL (Rs.)':>16} | {'Charges (Rs.)':>14} | {'Net PnL (Rs.)':>16} | {'Max DD (Rs.)':>14} | {'Net vs Flat':>14}")
    print("-" * 140)

    for sc in schemes:
        sc_trades = []
        cum_pnl = 0.0
        peak = 0.0
        max_dd = 0.0

        for idx, trade in df_trades.iterrows():
            lots = sc["high_lots"] if trade['Conviction'] == "HIGH" else sc["base_lots"]
            if lots == 0:
                continue

            pts = trade['Entry_Price'] - trade['Exit_Price'] # positive = profit for SELL
            qty = lots * lot_size
            gross_pnl = pts * qty
            # Compute exact realistic Indian derivatives charges
            turnover = (trade['Entry_Price'] + trade['Exit_Price']) * qty
            brokerage = 40.0 # Rs.20 entry + Rs.20 exit
            stt = round(trade['Exit_Price'] * qty * 0.000625, 2) # STT on sell turnover (0.0625%)
            etc = round(turnover * 0.0005, 2)
            gst = round((brokerage + etc) * 0.18, 2)
            sebi = round(turnover * 0.000001, 2)
            stamp = round(trade['Entry_Price'] * qty * 0.00003, 2)
            total_charges = brokerage + stt + etc + gst + sebi + stamp
            net_pnl = gross_pnl - total_charges

            cum_pnl += net_pnl
            if cum_pnl > peak:
                peak = cum_pnl
            dd = peak - cum_pnl
            if dd > max_dd:
                max_dd = dd

            sc_trades.append({
                "Gross_PnL": gross_pnl,
                "Charges": total_charges,
                "Net_PnL": net_pnl,
                "Is_Win": net_pnl > 0
            })

        df_sc = pd.DataFrame(sc_trades)
        if not df_sc.empty:
            t_cnt = len(df_sc)
            w_cnt = len(df_sc[df_sc['Is_Win']])
            wr = (w_cnt / t_cnt) * 100
            gross_tot = df_sc['Gross_PnL'].sum()
            chg_tot = df_sc['Charges'].sum()
            net_tot = df_sc['Net_PnL'].sum()
            
            wins = df_sc[df_sc['Gross_PnL'] > 0]['Gross_PnL'].sum()
            losses = abs(df_sc[df_sc['Gross_PnL'] < 0]['Gross_PnL'].sum())
            pf = round(wins / losses, 2) if losses > 0 else 99.99

            if sc["name"] == "Flat Baseline (5 Lots)":
                baseline_net = net_tot
                diff_str = "Baseline"
            else:
                diff = net_tot - baseline_net
                diff_str = f"+Rs.{diff:,.2f}" if diff >= 0 else f"-Rs.{abs(diff):,.2f}"

            print(f"{sc['name']:<35} | {t_cnt:>6} | {wr:>7.1f}% | {pf:>6.2f} | Rs.{gross_tot:>13,.2f} | Rs.{chg_tot:>11,.2f} | Rs.{net_tot:>13,.2f} | Rs.{max_dd:>11,.2f} | {diff_str:>14}")

if __name__ == "__main__":
    days = 180
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    run_conviction_sizing_simulation(days=days)
