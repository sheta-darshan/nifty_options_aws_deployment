import pandas as pd
import numpy as np
from engine import load_data, backtest_signals, summarize, dedup_signals, ema, smma
import strategies as S

df = load_data()

# Daily trend filter (same one that helped ORB): prior day's close vs 50-day EMA of daily closes
daily = df.groupby('date')['close'].last()
daily_ema = daily.ewm(span=50, adjust=False).mean()
prior_trend_up = (daily > daily_ema).shift(1)
trend_map = prior_trend_up.to_dict()
df['trend_up'] = pd.Series(df['date']).map(trend_map).values


def apply_trend_filter(sig_df):
    d = sig_df.copy()
    trend_up = d['trend_up'].values
    sig = d['SIG'].values.copy()
    # keep only long signals in uptrend days, short signals in downtrend days
    mask_kill = ((sig == 1) & (trend_up != True)) | ((sig == -1) & (trend_up != False))
    sig[mask_kill] = 0
    d['SIG'] = sig
    return d


def yearly_breakdown(trades):
    if trades.empty:
        return {}
    t = trades.copy()
    t['year'] = pd.to_datetime(t['exit_time']).dt.year
    g = t.groupby('year')['points'].agg(['count', 'sum'])
    return {int(y): (int(r['count']), round(r['sum'], 1)) for y, r in g.iterrows()}


targets = [35, 40, 45, 50]
sls = [15, 20, 25, 30]
rows = []

candidates = {
    'EMA9_21_pullback': S.strat_ema_pullback(df, fast=9, slow=21),
    'EMA9_50_pullback': S.strat_ema_pullback(df, fast=9, slow=50),
    'SMMA18_breakout': S.strat_smma_breakout(df, sma_period=18, ma_type='SMMA'),
    'RSI35_65_bounce': S.strat_rsi_trend_bounce(df, low_th=35, high_th=65),
}

for name, sig_df in candidates.items():
    sig_df = sig_df.copy()
    sig_df['SIG'] = dedup_signals(sig_df['SIG'], cooldown_bars=15)
    sig_df['trend_up'] = df['trend_up']
    filtered = apply_trend_filter(sig_df)
    n_sig = (filtered['SIG'] != 0).sum()
    print(name, 'n_sig after trend filter:', n_sig)
    if n_sig < 50:
        continue
    for t in targets:
        for s in sls:
            trades = backtest_signals(filtered, 'SIG', t, s)
            if len(trades) < 50:
                continue
            summ = summarize(trades, t, s)
            summ['strategy'] = name
            summ['yearly'] = yearly_breakdown(trades)
            rows.append(summ)

res = pd.DataFrame(rows)
res.to_csv('/home/claude/nifty_bt/results_trend_filtered.csv', index=False)
pd.set_option('display.width', 220)
pd.set_option('display.max_columns', 20)
print(res.sort_values('expectancy_pts', ascending=False).head(25)[
    ['strategy', 'target_pts', 'sl_pts', 'n_trades', 'win_rate_%', 'avg_win_pts', 'avg_loss_pts', 'expectancy_pts', 'total_points']
].to_string())
