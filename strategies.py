import pandas as pd
import numpy as np
from engine import ema, smma, sma, rsi, atr, vwap_intraday


def strat_smma_breakout(df, sma_period=18, ma_type='SMMA', strict_low=True):
    """Strategy 16 style: 18 SMMA setup + breakout, but signal only (exit handled by engine target/SL)."""
    d = df.copy()
    if ma_type == 'SMMA':
        d['MA'] = smma(d['close'], sma_period)
    else:
        d['MA'] = sma(d['close'], sma_period)

    if strict_low:
        above = d['low'] > d['MA']
        below = d['high'] < d['MA']
    else:
        above = d['close'] > d['MA']
        below = d['close'] < d['MA']

    consec_above = above.rolling(2).sum() == 2
    consec_below = below.rolling(2).sum() == 2
    prev_below = d['close'].shift(2) <= d['MA'].shift(2)
    prev_above = d['close'].shift(2) >= d['MA'].shift(2)

    cross_buy = prev_below & consec_above
    cross_sell = prev_above & consec_below

    long_phase = (~above).astype(int).cumsum()
    short_phase = (~below).astype(int).cumsum()

    raw_sig_high = np.where(cross_buy, d['high'], np.nan)
    sig_high = pd.Series(raw_sig_high, index=d.index).groupby(long_phase).ffill()
    raw_sig_low = np.where(cross_sell, d['low'], np.nan)
    sig_low = pd.Series(raw_sig_low, index=d.index).groupby(short_phase).ffill()

    long_trend = above & sig_high.notna()
    short_trend = below & sig_low.notna()

    # shift by 1 bar to avoid lookahead
    MA = d['MA'].shift(1)
    long_trend = long_trend.shift(1).fillna(False)
    short_trend = short_trend.shift(1).fillna(False)
    sig_high_s = sig_high.shift(1)
    sig_low_s = sig_low.shift(1)

    buy_raw = long_trend & (d['close'] > sig_high_s)
    sell_raw = short_trend & (d['close'] < sig_low_s)
    buy = buy_raw & (~buy_raw.shift(1).fillna(False))
    sell = sell_raw & (~sell_raw.shift(1).fillna(False))

    sig = pd.Series(0, index=d.index)
    sig[buy] = 1
    sig[sell] = -1
    d['SIG'] = sig
    return d


def strat_ema_pullback(df, fast=9, slow=21, rsi_len=14):
    """Trend continuation: fast EMA > slow EMA (uptrend), price pulls back to touch fast EMA, then closes back above it -> buy.
       Mirror for downtrend."""
    d = df.copy()
    d['EMA_F'] = ema(d['close'], fast)
    d['EMA_S'] = ema(d['close'], slow)
    uptrend = d['EMA_F'] > d['EMA_S']
    downtrend = d['EMA_F'] < d['EMA_S']

    touched_fast_from_above = (d['low'] <= d['EMA_F']) & (d['close'] > d['EMA_F'])
    touched_fast_from_below = (d['high'] >= d['EMA_F']) & (d['close'] < d['EMA_F'])

    buy_raw = uptrend & touched_fast_from_above
    sell_raw = downtrend & touched_fast_from_below

    buy_raw = buy_raw.shift(1).fillna(False)
    sell_raw = sell_raw.shift(1).fillna(False)
    buy = buy_raw & (~buy_raw.shift(1).fillna(False))
    sell = sell_raw & (~sell_raw.shift(1).fillna(False))

    sig = pd.Series(0, index=d.index)
    sig[buy] = 1
    sig[sell] = -1
    d['SIG'] = sig
    return d


def strat_vwap_reversion(df, band_mult=1.0, roll=20):
    d = df.copy()
    d['VWAP'] = vwap_intraday(d)
    d['STD'] = d['close'].rolling(roll).std()
    upper = d['VWAP'] + band_mult * d['STD']
    lower = d['VWAP'] - band_mult * d['STD']

    buy_raw = (d['low'] <= lower) & (d['close'] > lower)
    sell_raw = (d['high'] >= upper) & (d['close'] < upper)

    buy_raw = buy_raw.shift(1).fillna(False)
    sell_raw = sell_raw.shift(1).fillna(False)
    buy = buy_raw & (~buy_raw.shift(1).fillna(False))
    sell = sell_raw & (~sell_raw.shift(1).fillna(False))

    sig = pd.Series(0, index=d.index)
    sig[buy] = 1
    sig[sell] = -1
    d['SIG'] = sig
    return d


def strat_rsi_trend_bounce(df, rsi_len=14, trend_len=200, low_th=35, high_th=65):
    d = df.copy()
    d['RSI'] = rsi(d['close'], rsi_len)
    d['EMA_TREND'] = ema(d['close'], trend_len)
    uptrend = d['close'] > d['EMA_TREND']
    downtrend = d['close'] < d['EMA_TREND']

    rsi_cross_up = (d['RSI'] > low_th) & (d['RSI'].shift(1) <= low_th)
    rsi_cross_dn = (d['RSI'] < high_th) & (d['RSI'].shift(1) >= high_th)

    buy_raw = uptrend & rsi_cross_up
    sell_raw = downtrend & rsi_cross_dn

    buy_raw = buy_raw.shift(1).fillna(False)
    sell_raw = sell_raw.shift(1).fillna(False)

    sig = pd.Series(0, index=d.index)
    sig[buy_raw] = 1
    sig[sell_raw] = -1
    d['SIG'] = sig
    return d


def strat_orb(df, range_minutes=15):
    """Opening range breakout: first `range_minutes` after 9:15 defines high/low. Breakout above -> buy, below -> sell.
       One trade per day per direction (first breakout only)."""
    d = df.copy()
    d['time'] = d.index.time
    results = []
    for date, g in d.groupby('date'):
        g = g.copy()
        start = g.index[0]
        cutoff = start + pd.Timedelta(minutes=range_minutes)
        orb = g[g.index < cutoff]
        if orb.empty:
            continue
        orb_high = orb['high'].max()
        orb_low = orb['low'].min()
        rest = g[g.index >= cutoff]
        bought = False
        sold = False
        for ts, row in rest.iterrows():
            if not bought and row['close'] > orb_high:
                results.append((ts, 1))
                bought = True
            if not sold and row['close'] < orb_low:
                results.append((ts, -1))
                sold = True
            if bought and sold:
                break
    sig = pd.Series(0, index=d.index)
    for ts, direction in results:
        sig.loc[ts] = direction
    d['SIG'] = sig
    return d
