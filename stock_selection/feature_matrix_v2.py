"""
stock_selection/feature_matrix_v2.py

Institutional Feature Matrix 2.0 (Alpha Microstructure & Regime Conditioning)
=============================================================================
Computes 26 high-conviction institutional alpha features for quantitative stock
selection, replacing the 90 noisy 1-minute sequential tick features:
  - Microstructure & Smart Money Footprint (CAR, CLV, UVR)
  - Multi-stage Volatility Contraction Pattern (VCP Wave 3 / Wave 1)
  - Multi-day Range Compression (TTM Squeeze, NR7, Inside Day)
  - Relative Strength (RS) vs NIFTY 50 (1-Day, 5-Day, 20-Day)
  - Anchor Distances (20 EMA, 50 EMA, 200 SMA, VWAP)
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import time as dt_time, datetime

FEATURE_NAMES_V2 = [
    "vcp_ratio",
    "car",
    "clv_day",
    "clv_close",
    "uvr",
    "ttm_squeeze",
    "bb_width",
    "is_nr7",
    "is_inside_day",
    "range_ratio_atr",
    "dist_ema20",
    "dist_ema50",
    "dist_sma200",
    "dist_vwap",
    "ema_9_21_diff",
    "rsi_14",
    "vol_ratio_20d",
    "vol_surge_last30m",
    "ret_30m",
    "ret_day",
    "rs_nifty_1d",
    "rs_nifty_5d",
    "rs_nifty_20d",
    "nifty_rsi_14",
    "high_52w_dist",
    "turnover_cr"
]

def compute_vcp_ratio(daily_sub: pd.DataFrame) -> float:
    """Computes 3-stage progressive wave shrinkage ratio (Wave 3 / Wave 1)."""
    if len(daily_sub) < 20:
        return 1.0
    w1_high = daily_sub['high'].iloc[-19:-11].max()
    w1_low = daily_sub['low'].iloc[-19:-11].min()
    w1_range = w1_high - w1_low

    w3_high = daily_sub['high'].iloc[-5:].max()
    w3_low = daily_sub['low'].iloc[-5:].min()
    w3_range = w3_high - w3_low

    if w1_range <= 0:
        return 1.0
    return float(np.clip(w3_range / (w1_range + 1e-9), 0.05, 2.5))

def compute_closing_footprint(m1_day_bars: pd.DataFrame):
    """Analyzes 14:30 - 15:25 IST institutional closing footprint (CAR, CLV, UVR)."""
    default_res = {'car': 0.14, 'clv_close': 0.0, 'uvr': 0.50, 'vol_surge_last30m': 1.0, 'ret_30m': 0.0, 'dist_vwap': 0.0}
    if m1_day_bars is None or m1_day_bars.empty or len(m1_day_bars) < 30:
        return default_res

    total_vol = float(m1_day_bars['volume'].sum())
    if total_vol <= 0:
        return default_res

    # VWAP
    cum_pv = (m1_day_bars['close'] * m1_day_bars['volume']).sum()
    day_vwap = cum_pv / total_vol if total_vol > 0 else m1_day_bars['close'].iloc[-1]
    last_c = float(m1_day_bars['close'].iloc[-1])
    dist_vwap = (last_c - day_vwap) / (day_vwap + 1e-9) * 100.0

    # 14:30 - 15:25 window (CAR and CLV_close)
    t_start = dt_time(14, 30)
    t_end = dt_time(15, 25)
    close_mask = (m1_day_bars.index.time >= t_start) & (m1_day_bars.index.time <= t_end)
    close_window = m1_day_bars[close_mask]
    
    close_vol = float(close_window['volume'].sum()) if not close_window.empty else 0.0
    car = close_vol / total_vol

    if not close_window.empty:
        cw_h = float(close_window['high'].max())
        cw_l = float(close_window['low'].min())
        cw_c = float(close_window['close'].iloc[-1])
        cw_rng = cw_h - cw_l
        clv_close = (2.0 * cw_c - cw_h - cw_l) / (cw_rng + 1e-9) if cw_rng > 0 else 0.0
    else:
        clv_close = 0.0

    # Up/Down Volume Ratio (UVR)
    up_bars = m1_day_bars[m1_day_bars['close'] >= m1_day_bars['open']]
    up_vol = float(up_bars['volume'].sum())
    uvr = up_vol / total_vol

    # Last 30-min window (15:00 - 15:29)
    t30_start = dt_time(15, 0)
    l30_mask = (m1_day_bars.index.time >= t30_start) & (m1_day_bars.index.time <= t_end)
    l30_bars = m1_day_bars[l30_mask]
    if not l30_bars.empty and len(l30_bars) >= 5:
        l30_open = float(l30_bars['open'].iloc[0])
        l30_close = float(l30_bars['close'].iloc[-1])
        ret_30m = (l30_close - l30_open) / (l30_open + 1e-9) * 100.0
        avg_30m_vol = total_vol / max(1.0, len(m1_day_bars) / 30.0)
        vol_surge_last30m = float(l30_bars['volume'].sum()) / (avg_30m_vol + 1e-9)
    else:
        ret_30m = 0.0
        vol_surge_last30m = 1.0

    return {
        'car': float(np.clip(car, 0.0, 1.0)),
        'clv_close': float(np.clip(clv_close, -1.0, 1.0)),
        'uvr': float(np.clip(uvr, 0.0, 1.0)),
        'vol_surge_last30m': float(np.clip(vol_surge_last30m, 0.1, 10.0)),
        'ret_30m': float(np.clip(ret_30m, -15.0, 15.0)),
        'dist_vwap': float(np.clip(dist_vwap, -20.0, 20.0))
    }

def extract_features_v2_for_date(daily_df: pd.DataFrame, m1_df: pd.DataFrame, target_date, nifty_daily: pd.DataFrame = None) -> dict:
    """
    Extracts the 26 Feature Matrix 2.0 features for a single stock at close of target_date.
    """
    if daily_df is None or len(daily_df) < 50 or target_date not in daily_df.index:
        return None

    idx_loc = daily_df.index.get_loc(target_date)
    if idx_loc < 25:
        return None

    sub_daily = daily_df.iloc[:idx_loc + 1]
    last_row = sub_daily.iloc[-1]

    c = float(last_row['close'])
    h = float(last_row['high'])
    l = float(last_row['low'])
    o = float(last_row['open'])
    v = float(last_row['volume'])

    if c <= 0 or o <= 0 or h <= 0 or l <= 0:
        return None

    # Technical Indicators on daily data
    e20 = float(sub_daily['close'].ewm(span=20, adjust=False).mean().iloc[-1])
    e50 = float(sub_daily['close'].ewm(span=50, adjust=False).mean().iloc[-1])
    sma200 = float(sub_daily['close'].rolling(200, min_periods=40).mean().iloc[-1])
    e9 = float(sub_daily['close'].ewm(span=9, adjust=False).mean().iloc[-1])
    e21 = float(sub_daily['close'].ewm(span=21, adjust=False).mean().iloc[-1])

    # ATR 14
    tr_series = np.maximum(
        sub_daily['high'] - sub_daily['low'],
        np.maximum(
            abs(sub_daily['high'] - sub_daily['close'].shift(1)),
            abs(sub_daily['low'] - sub_daily['close'].shift(1))
        )
    )
    atr14 = float(tr_series.rolling(14, min_periods=10).mean().iloc[-1])
    if atr14 <= 0:
        atr14 = h - l if (h - l) > 0 else c * 0.015

    # 1. Microstructure Footprint
    if m1_df is not None:
        t_bars = m1_df[m1_df['date'] == target_date] if 'date' in m1_df.columns else m1_df.loc[str(target_date)[:10]] if str(target_date)[:10] in m1_df.index else None
        fp = compute_closing_footprint(t_bars)
    else:
        fp = {'car': 0.14, 'clv_close': 0.0, 'uvr': 0.50, 'vol_surge_last30m': 1.0, 'ret_30m': 0.0, 'dist_vwap': 0.0}

    # 2. Structural Contraction & Coiling
    vcp_ratio = compute_vcp_ratio(sub_daily)

    # TTM Squeeze / Bollinger vs Keltner
    sma20 = float(sub_daily['close'].rolling(20).mean().iloc[-1])
    std20 = float(sub_daily['close'].rolling(20).std().iloc[-1])
    bb_upper = sma20 + 2.0 * std20
    bb_lower = sma20 - 2.0 * std20
    bb_width = (bb_upper - bb_lower) / (e20 + 1e-9) * 100.0

    kc_upper = e20 + 1.5 * atr14
    kc_lower = e20 - 1.5 * atr14
    ttm_squeeze = 1.0 if (bb_lower >= kc_lower and bb_upper <= kc_upper) else 0.0

    # NR7 and Inside Day
    rng_today = h - l
    ranges_7 = (sub_daily['high'] - sub_daily['low']).iloc[-7:]
    is_nr7 = 1.0 if rng_today <= (ranges_7.min() + 1e-6) else 0.0

    prev_h = float(sub_daily['high'].iloc[-2]) if len(sub_daily) >= 2 else h
    prev_l = float(sub_daily['low'].iloc[-2]) if len(sub_daily) >= 2 else l
    is_inside_day = 1.0 if (h <= prev_h and l >= prev_l) else 0.0

    range_ratio_atr = rng_today / (atr14 + 1e-9)

    # 3. Anchors & Momentum
    dist_ema20 = (c - e20) / (e20 + 1e-9) * 100.0
    dist_ema50 = (c - e50) / (e50 + 1e-9) * 100.0
    dist_sma200 = (c - sma200) / (sma200 + 1e-9) * 100.0
    ema_9_21_diff = (e9 - e21) / (e21 + 1e-9) * 100.0

    # Daily RSI 14
    delta = sub_daily['close'].diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=10).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=10).mean()
    rs = gain / (loss + 1e-9)
    rsi_14 = float(100.0 - (100.0 / (1.0 + rs.iloc[-1]))) if not rs.empty and not np.isnan(rs.iloc[-1]) else 50.0

    # Volume & Turnover
    v_sma20 = float(sub_daily['volume'].rolling(20, min_periods=10).mean().iloc[-1])
    vol_ratio_20d = v / (v_sma20 + 1e-9)
    turnover_cr = (c * v) / 10000000.0  # Crores

    # Full day returns
    ret_day = (c - o) / (o + 1e-9) * 100.0
    clv_day = (2.0 * c - h - l) / (rng_today + 1e-9) if rng_today > 0 else 0.0

    # 52-Week High Distance
    h_52w = float(sub_daily['high'].rolling(min(252, len(sub_daily))).max().iloc[-1])
    high_52w_dist = (c - h_52w) / (h_52w + 1e-9) * 100.0

    # 4. Relative Strength vs NIFTY
    rs_nifty_1d = ret_day
    rs_nifty_5d = ret_day
    rs_nifty_20d = ret_day
    nifty_rsi_14 = 50.0

    if nifty_daily is not None and target_date in nifty_daily.index:
        n_idx = nifty_daily.index.get_loc(target_date)
        if n_idx >= 20:
            n_sub = nifty_daily.iloc[:n_idx + 1]
            n_c = float(n_sub['close'].iloc[-1])
            n_ret_1d = (n_c - float(n_sub['close'].iloc[-2])) / float(n_sub['close'].iloc[-2]) * 100.0
            n_ret_5d = (n_c - float(n_sub['close'].iloc[-6])) / float(n_sub['close'].iloc[-6]) * 100.0
            n_ret_20d = (n_c - float(n_sub['close'].iloc[-21])) / float(n_sub['close'].iloc[-21]) * 100.0

            stock_ret_1d = (c - float(sub_daily['close'].iloc[-2])) / float(sub_daily['close'].iloc[-2]) * 100.0
            stock_ret_5d = (c - float(sub_daily['close'].iloc[-6])) / float(sub_daily['close'].iloc[-6]) * 100.0 if len(sub_daily) >= 6 else stock_ret_1d
            stock_ret_20d = (c - float(sub_daily['close'].iloc[-21])) / float(sub_daily['close'].iloc[-21]) * 100.0 if len(sub_daily) >= 21 else stock_ret_5d

            rs_nifty_1d = stock_ret_1d - n_ret_1d
            rs_nifty_5d = stock_ret_5d - n_ret_5d
            rs_nifty_20d = stock_ret_20d - n_ret_20d

            n_delta = n_sub['close'].diff()
            n_gain = n_delta.clip(lower=0).rolling(14).mean()
            n_loss = (-n_delta.clip(upper=0)).rolling(14).mean()
            n_rs = n_gain / (n_loss + 1e-9)
            nifty_rsi_14 = float(100.0 - (100.0 / (1.0 + n_rs.iloc[-1]))) if not n_rs.empty else 50.0

    feature_dict = {
        "vcp_ratio": round(vcp_ratio, 4),
        "car": round(fp['car'], 4),
        "clv_day": round(float(np.clip(clv_day, -1.0, 1.0)), 4),
        "clv_close": round(fp['clv_close'], 4),
        "uvr": round(fp['uvr'], 4),
        "ttm_squeeze": float(ttm_squeeze),
        "bb_width": round(float(np.clip(bb_width, 0.1, 50.0)), 4),
        "is_nr7": float(is_nr7),
        "is_inside_day": float(is_inside_day),
        "range_ratio_atr": round(float(np.clip(range_ratio_atr, 0.05, 5.0)), 4),
        "dist_ema20": round(float(np.clip(dist_ema20, -40.0, 40.0)), 4),
        "dist_ema50": round(float(np.clip(dist_ema50, -50.0, 50.0)), 4),
        "dist_sma200": round(float(np.clip(dist_sma200, -70.0, 70.0)), 4),
        "dist_vwap": round(fp['dist_vwap'], 4),
        "ema_9_21_diff": round(float(np.clip(ema_9_21_diff, -20.0, 20.0)), 4),
        "rsi_14": round(float(np.clip(rsi_14, 0.0, 100.0)), 2),
        "vol_ratio_20d": round(float(np.clip(vol_ratio_20d, 0.05, 20.0)), 4),
        "vol_surge_last30m": round(fp['vol_surge_last30m'], 4),
        "ret_30m": round(fp['ret_30m'], 4),
        "ret_day": round(float(np.clip(ret_day, -25.0, 25.0)), 4),
        "rs_nifty_1d": round(float(np.clip(rs_nifty_1d, -25.0, 25.0)), 4),
        "rs_nifty_5d": round(float(np.clip(rs_nifty_5d, -40.0, 40.0)), 4),
        "rs_nifty_20d": round(float(np.clip(rs_nifty_20d, -60.0, 60.0)), 4),
        "nifty_rsi_14": round(float(np.clip(nifty_rsi_14, 0.0, 100.0)), 2),
        "high_52w_dist": round(float(np.clip(high_52w_dist, -90.0, 10.0)), 4),
        "turnover_cr": round(turnover_cr, 2)
    }

    return feature_dict


def extract_features_v2_df(spot_m1_df: pd.DataFrame, nifty_daily: pd.DataFrame = None, is_training: bool = True) -> pd.DataFrame:
    """
    High-performance vectorized Feature Matrix 2.0 extractor for training and historical backtesting.
    Computes all 26 alpha features + target labels across the entire date range of the stock.
    """
    if spot_m1_df is None or spot_m1_df.empty:
        return None

    df = spot_m1_df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        ts_col = 'timestamp' if 'timestamp' in df.columns else ('start_time' if 'start_time' in df.columns else df.columns[0])
        df[ts_col] = pd.to_datetime(df[ts_col], errors='coerce')
        df.set_index(ts_col, inplace=True)
    df = df[df.index.notna()].sort_index()
    df = df.between_time('09:15', '15:30')
    if len(df) < 100:
        return None

    df['date'] = df.index.date
    daily = df.groupby('date').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    min_days = 50 if is_training else 25
    if len(daily) < min_days:
        return None

    # Microstructure Footprint across all dates
    df['pv'] = df['close'] * df['volume']
    df['up_vol'] = np.where(df['close'] >= df['open'], df['volume'], 0.0)

    day_vol = df.groupby('date')['volume'].sum()
    day_pv = df.groupby('date')['pv'].sum()
    day_up_vol = df.groupby('date')['up_vol'].sum()

    day_vwap = day_pv / (day_vol + 1e-9)
    uvr = (day_up_vol / (day_vol + 1e-9)).clip(0.0, 1.0)
    dist_vwap = ((daily['close'] - day_vwap) / (day_vwap + 1e-9) * 100.0).clip(-20.0, 20.0)

    # 14:30 - 15:25 window (CAR, CLV_close)
    c_mask = df.between_time('14:30', '15:25')
    c_vol = c_mask.groupby('date')['volume'].sum()
    car = (c_vol / (day_vol + 1e-9)).clip(0.0, 1.0)

    c_high = c_mask.groupby('date')['high'].max()
    c_low = c_mask.groupby('date')['low'].min()
    c_close = c_mask.groupby('date')['close'].last()
    c_rng = c_high - c_low
    clv_close = np.where(c_rng > 0, (2.0 * c_close - c_high - c_low) / (c_rng + 1e-9), 0.0)
    clv_close = pd.Series(clv_close, index=c_high.index).clip(-1.0, 1.0)

    # 15:00 - 15:25 window (last 30m)
    l30 = df.between_time('15:00', '15:25')
    l30_open = l30.groupby('date')['open'].first()
    l30_close = l30.groupby('date')['close'].last()
    ret_30m = ((l30_close - l30_open) / (l30_open + 1e-9) * 100.0).clip(-15.0, 15.0)
    vol_surge_last30m = (l30.groupby('date')['volume'].sum() / (day_vol / 13.0 + 1e-9)).clip(0.1, 10.0)

    # Technical Indicators on daily series
    e9 = daily['close'].ewm(span=9, adjust=False).mean()
    e20 = daily['close'].ewm(span=20, adjust=False).mean()
    e21 = daily['close'].ewm(span=21, adjust=False).mean()
    e50 = daily['close'].ewm(span=50, adjust=False).mean()
    sma200 = daily['close'].rolling(200, min_periods=40).mean()

    # ATR 14
    tr_series = np.maximum(
        daily['high'] - daily['low'],
        np.maximum(
            abs(daily['high'] - daily['close'].shift(1)),
            abs(daily['low'] - daily['close'].shift(1))
        )
    )
    atr14 = tr_series.rolling(14, min_periods=10).mean()

    # VCP Ratio
    w1_range = daily['high'].shift(12).rolling(8).max() - daily['low'].shift(12).rolling(8).min()
    w3_range = daily['high'].rolling(5).max() - daily['low'].rolling(5).min()
    vcp_ratio = (w3_range / (w1_range + 1e-9)).clip(0.05, 2.5)

    # TTM Squeeze
    sma20 = daily['close'].rolling(20).mean()
    std20 = daily['close'].rolling(20).std()
    bb_upper = sma20 + 2.0 * std20
    bb_lower = sma20 - 2.0 * std20
    bb_width = ((bb_upper - bb_lower) / (e20 + 1e-9) * 100.0).clip(0.1, 50.0)

    kc_upper = e20 + 1.5 * atr14
    kc_lower = e20 - 1.5 * atr14
    ttm_squeeze = np.where((bb_lower >= kc_lower) & (bb_upper <= kc_upper), 1.0, 0.0)

    # NR7 and Inside Day
    rng_today = daily['high'] - daily['low']
    rng_7_min = rng_today.rolling(7).min()
    is_nr7 = np.where(rng_today <= (rng_7_min + 1e-6), 1.0, 0.0)

    prev_h = daily['high'].shift(1)
    prev_l = daily['low'].shift(1)
    is_inside_day = np.where((daily['high'] <= prev_h) & (daily['low'] >= prev_l), 1.0, 0.0)

    range_ratio_atr = (rng_today / (atr14 + 1e-9)).clip(0.05, 5.0)

    # Anchors
    dist_ema20 = ((daily['close'] - e20) / (e20 + 1e-9) * 100.0).clip(-40.0, 40.0)
    dist_ema50 = ((daily['close'] - e50) / (e50 + 1e-9) * 100.0).clip(-50.0, 50.0)
    dist_sma200 = ((daily['close'] - sma200) / (sma200 + 1e-9) * 100.0).clip(-70.0, 70.0)
    ema_9_21_diff = ((e9 - e21) / (e21 + 1e-9) * 100.0).clip(-20.0, 20.0)

    # Daily RSI 14
    delta = daily['close'].diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=10).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=10).mean()
    rs = gain / (loss + 1e-9)
    rsi_14 = (100.0 - (100.0 / (1.0 + rs))).clip(0.0, 100.0)

    # Volume & Turnover
    v_sma20 = daily['volume'].rolling(20, min_periods=10).mean()
    vol_ratio_20d = (daily['volume'] / (v_sma20 + 1e-9)).clip(0.05, 20.0)
    turnover_cr = (daily['close'] * daily['volume']) / 10000000.0

    ret_day = ((daily['close'] - daily['open']) / (daily['open'] + 1e-9) * 100.0).clip(-25.0, 25.0)
    clv_day = np.where(rng_today > 0, (2.0 * daily['close'] - daily['high'] - daily['low']) / (rng_today + 1e-9), 0.0)
    clv_day = pd.Series(clv_day, index=daily.index).clip(-1.0, 1.0)

    h_52w = daily['high'].rolling(252, min_periods=30).max()
    high_52w_dist = ((daily['close'] - h_52w) / (h_52w + 1e-9) * 100.0).clip(-90.0, 10.0)

    # Relative Strength vs NIFTY
    stock_ret_1d = daily['close'].pct_change(1) * 100.0
    stock_ret_5d = daily['close'].pct_change(5) * 100.0
    stock_ret_20d = daily['close'].pct_change(20) * 100.0

    if nifty_daily is not None and not nifty_daily.empty:
        n_idx = nifty_daily.index
        # Align nifty
        n_c = nifty_daily['close'].reindex(daily.index).ffill()
        n_ret_1d = n_c.pct_change(1) * 100.0
        n_ret_5d = n_c.pct_change(5) * 100.0
        n_ret_20d = n_c.pct_change(20) * 100.0

        n_delta = n_c.diff()
        n_gain = n_delta.clip(lower=0).rolling(14, min_periods=10).mean()
        n_loss = (-n_delta.clip(upper=0)).rolling(14, min_periods=10).mean()
        n_rs = n_gain / (n_loss + 1e-9)
        nifty_rsi_14 = (100.0 - (100.0 / (1.0 + n_rs))).clip(0.0, 100.0).fillna(50.0)

        rs_nifty_1d = (stock_ret_1d - n_ret_1d).clip(-25.0, 25.0)
        rs_nifty_5d = (stock_ret_5d - n_ret_5d).clip(-40.0, 40.0)
        rs_nifty_20d = (stock_ret_20d - n_ret_20d).clip(-60.0, 60.0)
    else:
        rs_nifty_1d = stock_ret_1d.clip(-25.0, 25.0)
        rs_nifty_5d = stock_ret_5d.clip(-40.0, 40.0)
        rs_nifty_20d = stock_ret_20d.clip(-60.0, 60.0)
        nifty_rsi_14 = pd.Series(50.0, index=daily.index)

    # Forward Targets on T+1
    next_high = daily['high'].shift(-1)
    next_low = daily['low'].shift(-1)
    next_close = daily['close'].shift(-1)

    target_volatility = np.where((next_high - next_low) >= (1.3 * atr14), 1, 0)
    target_direction = np.where(next_close > daily['close'], 1, 0)
    next_ret = ((next_close - daily['close']) / (daily['close'] + 1e-9) * 100.0).clip(-30.0, 30.0)

    out_df = pd.DataFrame({
        "vcp_ratio": vcp_ratio.round(4),
        "car": car.reindex(daily.index).fillna(0.14).round(4),
        "clv_day": clv_day.round(4),
        "clv_close": clv_close.reindex(daily.index).fillna(0.0).round(4),
        "uvr": uvr.reindex(daily.index).fillna(0.50).round(4),
        "ttm_squeeze": ttm_squeeze,
        "bb_width": bb_width.round(4),
        "is_nr7": is_nr7,
        "is_inside_day": is_inside_day,
        "range_ratio_atr": range_ratio_atr.round(4),
        "dist_ema20": dist_ema20.round(4),
        "dist_ema50": dist_ema50.round(4),
        "dist_sma200": dist_sma200.round(4),
        "dist_vwap": dist_vwap.reindex(daily.index).fillna(0.0).round(4),
        "ema_9_21_diff": ema_9_21_diff.round(4),
        "rsi_14": rsi_14.round(2),
        "vol_ratio_20d": vol_ratio_20d.round(4),
        "vol_surge_last30m": vol_surge_last30m.reindex(daily.index).fillna(1.0).round(4),
        "ret_30m": ret_30m.reindex(daily.index).fillna(0.0).round(4),
        "ret_day": ret_day.round(4),
        "rs_nifty_1d": rs_nifty_1d.fillna(0.0).round(4),
        "rs_nifty_5d": rs_nifty_5d.fillna(0.0).round(4),
        "rs_nifty_20d": rs_nifty_20d.fillna(0.0).round(4),
        "nifty_rsi_14": nifty_rsi_14.round(2),
        "high_52w_dist": high_52w_dist.round(4),
        "turnover_cr": turnover_cr.round(2),
        "close": daily['close'].round(2),
        "high": daily['high'].round(2),
        "low": daily['low'].round(2),
        "atr14": atr14.round(2),
        "target_volatility": target_volatility,
        "target_direction": target_direction,
        "next_ret": next_ret.round(4)
    }, index=daily.index)

    if is_training:
        # Warmup and last row (no target)
        out_df = out_df.iloc[30:-1]
        return out_df.dropna()
    else:
        # In inference mode, keep latest completed session (today's close)
        feat_cols = [c for c in out_df.columns if c not in ["target_volatility", "target_direction", "next_ret"]]
        warmup = min(20, len(out_df) - 1)
        return out_df[feat_cols].iloc[warmup:].dropna()

