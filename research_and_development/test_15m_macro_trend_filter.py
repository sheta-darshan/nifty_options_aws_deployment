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

def run_15m_filter_experiment():
    print("================================================================================")
    print(" EXPERIMENT 4: 15-MINUTE MACRO TREND ALIGNMENT FILTER ON NIFTY 180D ")
    print("================================================================================")

    config = BacktestConfig()
    config.LEG_MODE = "SELL"
    for i in range(1, 23):
        setattr(config, f"ENABLE_STRATEGY_{i}", False)
    config.ENABLE_STRATEGY_22 = True
    config.apply_strategy_defaults("Strategy_22")

    engine = SimulationEngine(config, instrument_name="NIFTY", offline_mode=False, backtest_days=180)
    engine.load_data()
    engine.inst_config['points_target_sell'] = 25.0
    engine.inst_config['points_sl_sell'] = 74.0
    df_baseline = engine.run(write_to_csv=False)

    total_baseline_trades = len(df_baseline)
    base_wins = df_baseline[df_baseline['PnL'] > 0]
    base_losses = df_baseline[df_baseline['PnL'] < 0]
    base_wr = (len(base_wins) / total_baseline_trades) * 100
    base_net = df_baseline['PnL'].sum()
    base_pf = round(base_wins['Gross_PnL'].sum() / abs(base_losses['Gross_PnL'].sum()), 2)
    base_avg_loss = base_losses['PnL'].mean()

    print(f"Baseline: Trades {total_baseline_trades} | WR: {base_wr:.1f}% ({len(base_wins)} W / {len(base_losses)} L) | Net PnL: Rs.{base_net:,.2f} | PF: {base_pf}")
    print("-" * 85)

    df_spot = engine.df_spot
    import pandas_ta as ta
    
    # 1. Resample to 15-min
    df_15m = df_spot.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    df_15m['EMA_20'] = ta.ema(df_15m['close'], length=20)
    df_15m['EMA_50'] = ta.ema(df_15m['close'], length=50)
    st_15m = ta.supertrend(df_15m['high'], df_15m['low'], df_15m['close'], length=10, multiplier=2.5)
    st_col = [c for c in st_15m.columns if c.startswith('SUPERT_')][0]
    st_dir = [c for c in st_15m.columns if c.startswith('SUPERTd_')][0]
    df_15m['ST_15m_Line'] = st_15m[st_col]
    df_15m['ST_15m_Dir'] = st_15m[st_dir] # 1 = Bullish, -1 = Bearish

    # Shift 15m indicators by 1 to prevent lookahead
    df_15m_shifted = df_15m[['EMA_20', 'EMA_50', 'ST_15m_Line', 'ST_15m_Dir']].shift(1)
    df_spot_ind = df_spot.join(df_15m_shifted, how='left').ffill()

    filters = [
        "15m_ST_Aligned",
        "15m_Close_vs_EMA50",
        "15m_Close_vs_EMA20",
        "15m_EMA20_vs_EMA50",
        "15m_ST_AND_EMA50"
    ]

    print(f"{'Macro Filter':<25} | {'Trades':>6} | {'Wins':>5} | {'Loss':>5} | {'Win Rate':>8} | {'PF':>6} | {'Net PnL (Rs.)':>16} | {'Net vs Base':>14}")
    print("-" * 98)

    for flt in filters:
        filtered_trades = []
        for idx, trade in df_baseline.iterrows():
            entry_time = pd.to_datetime(trade['Entry_Time'])
            trade_type = trade['Type'] # PE = Bullish view, CE = Bearish view
            
            if entry_time not in df_spot_ind.index:
                filtered_trades.append(trade)
                continue
                
            row = df_spot_ind.loc[entry_time]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
                
            spot_close = row['close']
            st_dir_val = row['ST_15m_Dir']
            ema20 = row['EMA_20']
            ema50 = row['EMA_50']
            
            allowed = True
            if flt == "15m_ST_Aligned":
                # Bullish (PE sell) requires 15m ST == 1 (Bullish)
                # Bearish (CE sell) requires 15m ST == -1 (Bearish)
                if trade_type == "PE" and st_dir_val != 1:
                    allowed = False
                elif trade_type == "CE" and st_dir_val != -1:
                    allowed = False
            elif flt == "15m_Close_vs_EMA50":
                if trade_type == "PE" and spot_close < ema50:
                    allowed = False
                elif trade_type == "CE" and spot_close > ema50:
                    allowed = False
            elif flt == "15m_Close_vs_EMA20":
                if trade_type == "PE" and spot_close < ema20:
                    allowed = False
                elif trade_type == "CE" and spot_close > ema20:
                    allowed = False
            elif flt == "15m_EMA20_vs_EMA50":
                if trade_type == "PE" and ema20 < ema50:
                    allowed = False
                elif trade_type == "CE" and ema20 > ema50:
                    allowed = False
            elif flt == "15m_ST_AND_EMA50":
                if trade_type == "PE" and (st_dir_val != 1 or spot_close < ema50):
                    allowed = False
                elif trade_type == "CE" and (st_dir_val != -1 or spot_close > ema50):
                    allowed = False

            if allowed:
                filtered_trades.append(trade)

        df_flt = pd.DataFrame(filtered_trades)
        if not df_flt.empty:
            t_count = len(df_flt)
            w_trades = df_flt[df_flt['PnL'] > 0]
            l_trades = df_flt[df_flt['PnL'] < 0]
            wr = (len(w_trades) / t_count) * 100
            net = df_flt['PnL'].sum()
            w_gross = w_trades['Gross_PnL'].sum()
            l_gross = abs(l_trades['Gross_PnL'].sum())
            pf = round(w_gross / l_gross, 2) if l_gross > 0 else 99.99
            diff = net - base_net
            diff_str = f"+Rs.{diff:,.2f}" if diff >= 0 else f"-Rs.{abs(diff):,.2f}"
            print(f"{flt:<25} | {t_count:>6} | {len(w_trades):>5} | {len(l_trades):>5} | {wr:>7.1f}% | {pf:>6.2f} | Rs.{net:>13,.2f} | {diff_str:>14}")

if __name__ == "__main__":
    run_15m_filter_experiment()
