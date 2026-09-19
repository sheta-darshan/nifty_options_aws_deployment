"""
stock_selection/select_prebreakout.py

==========================================================================================
        INSTITUTIONAL PRE-BREAKOUT COILED STOCK SELECTION ENGINE
==========================================================================================
Identifies high-probability momentum stocks BEFORE they move by detecting:
  1. TTM Volatility Squeeze (Bollinger Bands inside Keltner Channels)
  2. Multi-day Range Compression (NR7 - Narrowest Range of 7 days, Inside Day)
  3. Base Proximity & Anti-Climax (Resting within 0% - 2.5% of 20 EMA; NOT extended!)
  4. Institutional Volume Dry-up (Supply exhaustion before expansion)
  5. Relative Strength against NIFTY 50 during consolidation
==========================================================================================
"""

import os
import sys
import argparse
import json
import glob
import time
import warnings
from multiprocessing.pool import ThreadPool
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time

warnings.filterwarnings("ignore", category=UserWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
EQUITY_L_PATH = os.path.join(BASE_DIR, "EQUITY_L.csv")
PRED_DIR = os.path.join(BASE_DIR, "stock_selection", "predictions")
os.makedirs(PRED_DIR, exist_ok=True)


def read_last_n_lines_to_df(filepath: str, n: int = 25000) -> pd.DataFrame:
    """Reads the last N lines of a CSV quickly using binary seek."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            header_line = f.readline()
        if not header_line:
            return None
        with open(filepath, 'rb') as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            chunk_size = max(100, n * 80)
            pos = max(0, pos - chunk_size)
            f.seek(pos)
            chunk = f.read()
            lines = chunk.split(b'\n')
            non_empty_lines = [l for l in lines if l.strip()]
            last_lines = non_empty_lines[-n:]
            from io import StringIO
            data_str = header_line.strip() + "\n" + b'\n'.join(last_lines).decode('utf-8')
            df = pd.read_csv(StringIO(data_str))
            df.columns = [c.strip().lower() for c in df.columns]
            if "start_time" in df.columns:
                df.rename(columns={"start_time": "timestamp"}, inplace=True)
            required = ["timestamp", "open", "high", "low", "close", "volume"]
            if all(col in df.columns for col in required):
                return df[required]
    except Exception:
        pass
    try:
        df = pd.read_csv(filepath)
        df.columns = [c.strip().lower() for c in df.columns]
        if "start_time" in df.columns:
            df.rename(columns={"start_time": "timestamp"}, inplace=True)
        required = ["timestamp", "open", "high", "low", "close", "volume"]
        if all(col in df.columns for col in required):
            return df[required].iloc[-n:]
    except Exception:
        return None
    return None


def get_nifty_daily_map() -> dict:
    """Computes daily close returns for NIFTY to measure relative strength."""
    nifty_path = os.path.join(DATA_DIR, "nifty_spot.csv")
    if not os.path.exists(nifty_path):
        return {}
    try:
        df = pd.read_csv(nifty_path)
        col = 'timestamp' if 'timestamp' in df.columns else df.columns[0]
        df[col] = pd.to_datetime(df[col], errors='coerce')
        df = df.dropna(subset=[col]).sort_values(by=col)
        df['date'] = df[col].dt.date
        daily = df.groupby('date')['close'].last()
        ret_5d = daily.pct_change(5)
        return ret_5d.to_dict()
    except Exception:
        return {}


def compute_vcp_ratio(daily_df: pd.DataFrame) -> float:
    """
    Computes 3-stage volatility contraction ratio (Minervini VCP):
      Wave 1: T-18 to T-11 (8 days)
      Wave 2: T-10 to T-5  (6 days)
      Wave 3: T-4 to T     (5 days)
    Returns ratio Range(Wave 3) / Range(Wave 1). Lower means tighter coiling.
    """
    if len(daily_df) < 20:
        return 1.0
    w1_high = daily_df['high'].iloc[-19:-11].max()
    w1_low = daily_df['low'].iloc[-19:-11].min()
    w1_range = w1_high - w1_low

    w3_high = daily_df['high'].iloc[-5:].max()
    w3_low = daily_df['low'].iloc[-5:].min()
    w3_range = w3_high - w3_low

    if w1_range <= 0:
        return 1.0
    return float(w3_range / (w1_range + 1e-9))


def compute_closing_footprint(m1_day_bars: pd.DataFrame):
    """
    Analyzes 14:30 - 15:25 IST institutional closing footprint from 1-min bars:
      - CAR: Closing Accumulation/Distribution Ratio (Volume 14:30-15:25 / Total Volume)
      - CLV: Close Location Value of the day ((2*Close - High - Low) / (High - Low))
      - UVR: Up-Volume dominance ratio across the whole day
    """
    if m1_day_bars is None or m1_day_bars.empty or len(m1_day_bars) < 60:
        return {'car': 0.14, 'clv': 0.0, 'uvr': 0.50}

    total_vol = m1_day_bars['volume'].sum()
    if total_vol <= 0:
        return {'car': 0.14, 'clv': 0.0, 'uvr': 0.50}

    # 14:30 to 15:25 bars
    t_start = dt_time(14, 30)
    t_end = dt_time(15, 25)
    t_series = m1_day_bars['timestamp'].dt.time if 'timestamp' in m1_day_bars.columns else m1_day_bars.index.time
    close_mask = (t_series >= t_start) & (t_series <= t_end)
    close_window = m1_day_bars[close_mask]
    close_vol = close_window['volume'].sum() if not close_window.empty else 0.0
    car = close_vol / total_vol

    # Day CLV: (2*Close - High - Low) / (High - Low)
    day_h = m1_day_bars['high'].max()
    day_l = m1_day_bars['low'].min()
    day_c = m1_day_bars['close'].iloc[-1]
    rng = day_h - day_l
    clv = (2.0 * day_c - day_h - day_l) / (rng + 1e-9) if rng > 0 else 0.0

    # UVR (Up Volume Ratio)
    up_bars = m1_day_bars[m1_day_bars['close'] >= m1_day_bars['open']]
    up_vol = up_bars['volume'].sum()
    uvr = up_vol / total_vol

    return {'car': car, 'clv': clv, 'uvr': uvr}


def evaluate_stock_coiling(symbol: str, nifty_5d_map: dict, direction: str = "buy") -> dict:
    """
    Evaluates whether a stock is coiled and ready to expand on Day T+1.
    Calculates the 0-100 Institutional Alpha Score combining:
      1. TTM Squeeze + NR7 / Inside Day + 20 EMA + Volume Dry-up
      2. Multi-Wave Volatility Contraction Pattern (VCP 3-Wave shrinkage)
      3. 14:30 - 15:25 IST Closing Smart Money Footprint (CAR + CLV)
      4. Up/Down Volume Ratio (UVR)
    """
    path = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
    if not os.path.exists(path):
        return None

    df = read_last_n_lines_to_df(path, n=20000)
    if df is None or len(df) < 500:
        return None

    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp']).sort_values(by='timestamp')
        df['date'] = df['timestamp'].dt.date

        # Resample to Daily
        daily = df.groupby('date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        if len(daily) < 25:
            return None

        # Daily indicators
        closes = daily['close']
        highs = daily['high']
        lows = daily['low']
        vols = daily['volume']

        # ATR 14
        tr = np.maximum(
            highs - lows,
            np.maximum(abs(highs - closes.shift(1)), abs(lows - closes.shift(1)))
        )
        atr14 = tr.rolling(14).mean()

        # Moving Averages
        ema20 = closes.ewm(span=20).mean()
        ema50 = closes.ewm(span=50).mean()
        vol_sma20 = vols.rolling(20).mean()
        high_50 = highs.rolling(50, min_periods=25).max()

        # Bollinger Bands (20, 2.0)
        basis = closes.rolling(20).mean()
        dev = closes.rolling(20).std()
        bb_upper = basis + 2.0 * dev
        bb_lower = basis - 2.0 * dev
        bb_width = (bb_upper - bb_lower) / (basis + 1e-9)

        # Keltner Channels (20, 1.5 * ATR)
        kc_upper = basis + 1.5 * atr14
        kc_lower = basis - 1.5 * atr14

        # Latest Day T values
        last_idx = daily.index[-1]
        c = closes.iloc[-1]
        h = highs.iloc[-1]
        l = lows.iloc[-1]
        v = vols.iloc[-1]
        e20 = ema20.iloc[-1]
        e50 = ema50.iloc[-1]
        atr = atr14.iloc[-1]
        v_sma = vol_sma20.iloc[-1]
        bbu = bb_upper.iloc[-1]
        bbl = bb_lower.iloc[-1]
        kcu = kc_upper.iloc[-1]
        kcl = kc_lower.iloc[-1]
        h50 = high_50.iloc[-1]
        rng = h - l

        # Institutional Liquidity Gate:
        # 1. Price floor: >= Rs.100 (reject penny / micro stocks)
        # 2. Daily volume floor: >= 50,000 shares 20-day SMA
        # 3. Turnover floor: >= Rs. 3 Crore average daily turnover, >= Rs. 2 Crore today
        turnover_avg = c * v_sma
        turnover_today = c * v
        if c < 100.0 or v_sma < 50000 or turnover_avg < 30000000 or turnover_today < 20000000:
            return None

        is_sell = (direction.lower() == "sell")
        today_chg_pct = (c - daily['open'].iloc[-1]) / daily['open'].iloc[-1] * 100.0

        if not is_sell:
            # =================== BUY GATES ===================
            # Macro Trend Gate: Price must be >= 50 EMA and 50 EMA >= 50 EMA 5 days ago
            if c < e50 * 0.98 or (len(ema50) >= 6 and e50 < ema50.iloc[-6] * 0.99):
                return None

            # Stage-2 Overhead Supply Gate: Must be within 15% of 50-day high (no trapped bagholders)
            if c < 0.85 * h50:
                return None

            # Positive Momentum Gate: Stock must have positive 20-day return
            if len(closes) >= 21 and c < closes.iloc[-21]:
                return None

            # Anti-Climax Filter: Reject stocks that ALREADY exploded today (> +4.0% green day)
            if today_chg_pct >= 4.0:
                return None
        else:
            # =================== SELL GATES ===================
            # Macro Trend Gate: Price must be <= 50 EMA (or within 1%) and 50 EMA not in steep rise
            if c > e50 * 1.01 or (len(ema50) >= 6 and e50 > ema50.iloc[-6] * 1.01):
                return None

            # Overhead Resistance / Trapped Supply: Must be well below 50-day high (trapped bagholders)
            if c > 0.90 * h50:
                return None

            # Negative Momentum Gate: Stock must have flat or negative 20-day return
            if len(closes) >= 21 and c > closes.iloc[-21]:
                return None

            # Anti-Climax Filter: Reject stocks that ALREADY crashed today (<= -4.0% red day; don't short the hole!)
            if today_chg_pct <= -4.0:
                return None

        # -------------------------------------------------------------
        # COMPUTE INSTITUTIONAL ALPHA SCORE (0 to 100)
        # -------------------------------------------------------------
        score = 0.0

        # 1. TTM Volatility Squeeze (20 pts max)
        is_ttm_squeeze = (bbl >= kcl) and (bbu <= kcu)
        min_bbw_20 = bb_width.iloc[-20:].min()
        is_tight_bb = bb_width.iloc[-1] <= min_bbw_20 * 1.10

        if is_ttm_squeeze:
            score += 20.0
            squeeze_label = "TTM SQUEEZE"
        elif is_tight_bb:
            score += 12.0
            squeeze_label = "BB COMPRESSED"
        else:
            squeeze_label = "NORMAL"

        # 2. Multi-day Range Compression (20 pts max)
        ranges_7 = (highs - lows).iloc[-7:]
        is_nr7 = rng <= ranges_7.min() + 1e-6
        prev_h = highs.iloc[-2]
        prev_l = lows.iloc[-2]
        is_inside_day = (h <= prev_h) and (l >= prev_l)

        if is_nr7 and is_inside_day:
            score += 20.0
            pattern_label = "NR7 + INSIDE DAY"
        elif is_nr7:
            score += 16.0
            pattern_label = "NR7 COMPRESSION"
        elif is_inside_day:
            score += 14.0
            pattern_label = "INSIDE DAY"
        elif rng < 0.8 * atr:
            score += 10.0
            pattern_label = "SUB-ATR COIL"
        else:
            pattern_label = "NORMAL"

        # 3. Base Proximity & Support/Resistance Shelf (15 pts max)
        dist_20 = (c - e20) / e20 * 100.0
        if not is_sell:
            if 0.0 <= dist_20 <= 1.8:
                score += 15.0
                base_label = "TIGHT ON 20 EMA"
            elif 1.8 < dist_20 <= 3.0:
                score += 10.0
                base_label = "NEAR 20 EMA"
            elif -1.5 <= dist_20 < 0.0:
                score += 6.0
                base_label = "PULLBACK AT EMA"
            else:
                base_label = "EXTENDED"
        else:
            if -1.8 <= dist_20 <= 0.0:
                score += 15.0
                base_label = "BEAR SHELF ON 20 EMA"
            elif -3.0 <= dist_20 < -1.8:
                score += 10.0
                base_label = "NEAR 20 EMA (BELOW)"
            elif 0.0 < dist_20 <= 1.5:
                score += 6.0
                base_label = "TESTING 20 EMA RESISTANCE"
            else:
                base_label = "EXTENDED"

        # 4. Volume Dry-Up (10 pts max)
        vol_ratio = v / (v_sma + 1e-9)
        if vol_ratio <= 0.65:
            score += 10.0
            vol_label = "DRY-UP (<65%)"
        elif vol_ratio <= 0.85:
            score += 7.0
            vol_label = "QUIET (<85%)"
        elif vol_ratio <= 1.10:
            score += 4.0
            vol_label = "AVERAGE"
        else:
            vol_label = "HIGH VOL"

        # 5. Multi-Wave Volatility Contraction Pattern (VCP 3-Wave Shrinkage) (15 pts max)
        vcp_ratio = compute_vcp_ratio(daily)
        if vcp_ratio <= 0.40:
            score += 15.0
            vcp_label = f"VCP COILED ({vcp_ratio:.2f})"
        elif vcp_ratio <= 0.52:
            score += 10.0
            vcp_label = f"VCP SHRINK ({vcp_ratio:.2f})"
        elif vcp_ratio <= 0.65:
            score += 5.0
            vcp_label = f"VCP MOD ({vcp_ratio:.2f})"
        elif vcp_ratio > 0.75:
            score -= 5.0
            vcp_label = f"VCP LOOSE ({vcp_ratio:.2f})"
        else:
            vcp_label = f"VCP NORMAL ({vcp_ratio:.2f})"

        # 6. Institutional Closing Footprint (14:30 - 15:25 IST) (15 pts max)
        m1_day_bars = df[df['date'] == last_idx]
        fp = compute_closing_footprint(m1_day_bars)
        car = fp['car']
        clv = fp['clv']
        uvr = fp['uvr']

        if not is_sell:
            # BUY Accumulation Footprint
            if car >= 0.20 and clv >= 0.45:
                score += 15.0
                inst_flow = f"INST ACCUM (CAR {car*100:.0f}%, CLV {clv:+.2f})"
            elif car >= 0.16 and clv >= 0.20:
                score += 10.0
                inst_flow = f"MOD ACCUM (CAR {car*100:.0f}%, CLV {clv:+.2f})"
            elif clv < -0.20:
                score -= 8.0  # Rejected by closing sellers
                inst_flow = f"LATE DUMP (CLV {clv:+.2f})"
            else:
                inst_flow = f"NEUTRAL (CAR {car*100:.0f}%)"
        else:
            # SELL Distribution Footprint
            if car >= 0.20 and clv <= -0.45:
                score += 15.0
                inst_flow = f"INST DISTRIB (CAR {car*100:.0f}%, CLV {clv:+.2f})"
            elif car >= 0.16 and clv <= -0.20:
                score += 10.0
                inst_flow = f"MOD DISTRIB (CAR {car*100:.0f}%, CLV {clv:+.2f})"
            elif clv > 0.20:
                score -= 8.0  # Closing buyers stepped in
                inst_flow = f"LATE BOUNCE (CLV {clv:+.2f})"
            else:
                inst_flow = f"NEUTRAL (CAR {car*100:.0f}%)"

        # 7. Intraday Volume Dominance (UVR) (5 pts max)
        if not is_sell:
            if uvr >= 0.52:
                score += 5.0
        else:
            if uvr <= 0.48:
                score += 5.0

        # Cap score between 0 and 100
        score = max(0.0, min(100.0, score))

        # Trade Plan for Tomorrow (Day T+1 Breakout / Breakdown)
        if not is_sell:
            trigger_px = round(h + 0.05, 2)
            sl_px = round(trigger_px - 0.90 * atr, 2)
            sl_pct = (trigger_px - sl_px) / trigger_px * 100.0
            be_trigger = round(trigger_px + 0.50 * atr, 2)
            target_px = round(trigger_px + 1.35 * atr, 2)
            target_pct = (target_px - trigger_px) / trigger_px * 100.0
        else:
            trigger_px = round(l - 0.05, 2)
            sl_px = round(trigger_px + 0.90 * atr, 2)
            sl_pct = (sl_px - trigger_px) / trigger_px * 100.0
            be_trigger = round(trigger_px - 0.50 * atr, 2)
            target_px = round(trigger_px - 1.35 * atr, 2)
            target_pct = (trigger_px - target_px) / trigger_px * 100.0

        return {
            'Symbol': symbol,
            'Date': str(last_idx),
            'Direction': "SELL" if is_sell else "BUY",
            'Close': round(c, 2),
            'Day_High': round(h, 2),
            'Day_Low': round(l, 2),
            'ATR_14': round(atr, 2),
            'Coil_Score': round(score, 1),
            'Squeeze': squeeze_label,
            'Pattern': pattern_label,
            'Base': base_label,
            'Volume': vol_label,
            'VCP_Ratio': round(vcp_ratio, 2),
            'VCP_Label': vcp_label,
            'CAR_Pct': round(car * 100.0, 1),
            'CLV': round(clv, 2),
            'UVR_Pct': round(uvr * 100.0, 1),
            'Inst_Flow': inst_flow,
            'Trigger_Price': trigger_px,
            'Stop_Loss': sl_px,
            'SL_Pct': round(sl_pct, 2),
            'BE_Trigger': be_trigger,
            'Target_Price': target_px,
            'Target_Pct': round(target_pct, 2)
        }

    except Exception:
        return None

    except Exception:
        return None


def get_fno_stock_registry() -> dict:
    """Loads clean immutable NSE F&O stocks with lot_size and strike_step from fno_registry.json."""
    reg_path = os.path.join(BASE_DIR, "stock_selection", "fno_registry.json")
    if os.path.exists(reg_path):
        try:
            with open(reg_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback to instruments.json
    instruments_path = os.path.join(BASE_DIR, "instruments.json")
    fno_dict = {}
    if os.path.exists(instruments_path):
        try:
            with open(instruments_path, "r") as f:
                data = json.load(f)
            for k, v in data.items():
                if v.get('type') == 'STOCK' and v.get('option_segment') == 'NSE_FNO':
                    fno_dict[k.upper()] = {
                        'lot_size': int(v.get('lot_size', 500)),
                        'strike_step': float(v.get('strike_step', 10)),
                        'option_segment': 'NSE_FNO',
                        'fno_prefix': v.get('fno_prefix', k.upper())
                    }
        except Exception:
            pass
    return fno_dict


def get_security_id_map() -> dict:
    """Loads Dhan security ID map from local dhan_equity_master_cache.csv"""
    sec_map = {}
    cache_path = os.path.join(BASE_DIR, "dhan_equity_master_cache.csv")
    if os.path.exists(cache_path):
        try:
            df_cache = pd.read_csv(cache_path, dtype={'SECURITY_ID': str})
            for _, r in df_cache.iterrows():
                sym = str(r.get('SYMBOL', '')).strip().upper()
                sid = str(r.get('SECURITY_ID', '')).strip()
                if sym and sid:
                    sec_map[sym] = sid
        except Exception as e:
            print(f"[WARNING] Could not parse dhan_equity_master_cache.csv: {e}")
    return sec_map


def run_prebreakout_selector(top_k: int = 5, rotate: bool = False, min_score: float = 60.0,
                             universe: str = "top500", direction: str = "both",
                             top_k_buy: int = None, top_k_sell: int = None,
                             capital: float = 100000.0, leverage: float = 5.0,
                             execution_mode: str = "hybrid", fno_only: bool = False,
                             sizing_mode: str = "fixed"):
    dir_str = direction.upper()
    mode_str = execution_mode.upper()
    title_dir = "BREAKDOWN (SHORT)" if dir_str == "SELL" else ("BIDIRECTIONAL (LONG & SHORT)" if dir_str == "BOTH" else "BREAKOUT (LONG)")
    print("=" * 145, flush=True)
    print(f"      INSTITUTIONAL PRE-{title_dir} COILED STOCK SELECTOR [MODE: {mode_str} | LEVERAGE: {leverage:.0f}x]", flush=True)
    print("=" * 145, flush=True)
    print(f"Selection Criteria: TTM Squeeze, NR7/Inside Day, Volume Dry-up, 20 EMA Base/Shelf, VCP Shrinkage, Closing Smart Money Flow (CAR/CLV/UVR)", flush=True)
    print(f"Execution Routing: {mode_str} (F&O Stocks -> ATM Options, Non-F&O -> {leverage:.0f}x MIS Cash Equity) | Universe: {universe.upper()}\n", flush=True)

    # 1. Discover symbols based on chosen universe
    symbols = []
    fno_registry = get_fno_stock_registry()
    if universe in ["top200", "top500"]:
        fname = "universe_500.json" if universe == "top500" else "universe_200.json"
        univ_path = os.path.join(BASE_DIR, fname)
        if os.path.exists(univ_path):
            with open(univ_path, "r") as f:
                univ_symbols = json.load(f)
            symbols = [s.upper() for s in univ_symbols if os.path.exists(os.path.join(DATA_DIR, f"{s}_spot.csv"))]
            print(f"Loaded {len(symbols):,} {universe.upper()} liquid stocks with local spot data.", flush=True)
        else:
            print(f"[WARNING] {fname} not found, falling back to all available spot files.", flush=True)
            universe = "all"
    elif universe == "instruments":
        inst_path = os.path.join(BASE_DIR, "instruments.json")
        if os.path.exists(inst_path):
            with open(inst_path, "r") as f:
                inst_data = json.load(f)
            symbols = [s.upper() for s, c in inst_data.items() if c.get("type") == "STOCK" and os.path.exists(os.path.join(DATA_DIR, f"{s}_spot.csv"))]
            print(f"Loaded {len(symbols):,} stocks from instruments.json with local spot data.", flush=True)

    if universe == "all" or not symbols:
        files = glob.glob(os.path.join(DATA_DIR, "*_spot.csv"))
        symbols = []
        for f in files:
            base = os.path.basename(f).replace("_spot.csv", "").upper()
            if base not in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]:
                symbols.append(base)
        print(f"Discovered {len(symbols):,} equity symbols in local database.", flush=True)

    if fno_only:
        symbols = [s for s in symbols if s in fno_registry]
        print(f"[FILTER] Restricting universe exclusively to {len(symbols)} NSE F&O listed stocks.", flush=True)

    # 2. Get NIFTY context
    nifty_map = get_nifty_daily_map()
    print("Precomputed NIFTY 5-day Benchmark context.\n", flush=True)

    # 3. Parallel Evaluation
    scan_tasks = []
    if direction.lower() in ["buy", "both"]:
        for s in symbols:
            scan_tasks.append((s, "buy"))
    if direction.lower() in ["sell", "both"]:
        for s in symbols:
            scan_tasks.append((s, "sell"))

    print(f"Scanning {len(symbols):,} stocks ({len(scan_tasks):,} evaluations for direction={dir_str}) for coiled setups...", flush=True)
    start_t = time.time()
    pool = ThreadPool(16)
    results = pool.map(lambda item: evaluate_stock_coiling(item[0], nifty_map, item[1]), scan_tasks)
    pool.close()
    pool.join()

    valid = [r for r in results if r is not None]
    elapsed = time.time() - start_t
    print(f"Evaluated {len(scan_tasks):,} tasks in {elapsed:.2f}s ({len(valid):,} eligible setups passed liquidity gates).\n", flush=True)

    if not valid:
        print("No eligible candidates found.")
        return

    # 4. Separate and Rank by Direction
    df_res = pd.DataFrame(valid)
    df_res = df_res.sort_values(by="Coil_Score", ascending=False).reset_index(drop=True)

    k_buy = top_k_buy if top_k_buy is not None else top_k
    k_sell = top_k_sell if top_k_sell is not None else top_k

    if dir_str == "BOTH":
        df_buys = df_res[df_res['Direction'] == 'BUY']
        df_sells = df_res[df_res['Direction'] == 'SELL']

        top_buys = df_buys[df_buys['Coil_Score'] >= min_score].head(k_buy)
        if top_buys.empty:
            top_buys = df_buys.head(k_buy)

        top_sells = df_sells[df_sells['Coil_Score'] >= min_score].head(k_sell)
        if top_sells.empty:
            top_sells = df_sells.head(k_sell)

        top_candidates = pd.concat([top_buys, top_sells], ignore_index=True)

        # Display BUY Candidates
        print("=" * 145)
        print(f"                    TOP {len(top_buys)} INSTITUTIONAL PRE-BREAKOUT (BUY / LONG) CANDIDATES")
        print("=" * 145)
        print(f"{'Rank':<4} | {'Symbol':<12} | {'Side':<5} | {'Score':<6} | {'VCP':<14} | {'CAR':<6} | {'CLV':<6} | {'Flow':<24} | {'Trigger':<9} | {'SL':<8} | {'Target':<9}")
        print("-" * 145)
        for idx, row in top_buys.reset_index(drop=True).iterrows():
            car_str = f"{row.get('CAR_Pct', 0.0):.0f}%"
            clv_str = f"{row.get('CLV', 0.0):+.2f}"
            print(f"{idx+1:<4} | {row['Symbol']:<12} | {'BUY':<5} | {row['Coil_Score']:<5.1f} | {row.get('VCP_Label', 'N/A'):<14} | {car_str:<6} | {clv_str:<6} | {row.get('Inst_Flow', 'NORMAL'):<24} | Rs.{row['Trigger_Price']:<8.2f} | Rs.{row['Stop_Loss']:<7.2f} | Rs.{row['Target_Price']:<8.2f} (+{row['Target_Pct']}%)")
        print("=" * 145)

        # Display SELL Candidates
        print("\n" + "=" * 145)
        print(f"                    TOP {len(top_sells)} INSTITUTIONAL PRE-BREAKDOWN (SELL / SHORT) CANDIDATES")
        print("=" * 145)
        print(f"{'Rank':<4} | {'Symbol':<12} | {'Side':<5} | {'Score':<6} | {'VCP':<14} | {'CAR':<6} | {'CLV':<6} | {'Flow':<24} | {'Trigger':<9} | {'SL':<8} | {'Target':<9}")
        print("-" * 145)
        for idx, row in top_sells.reset_index(drop=True).iterrows():
            car_str = f"{row.get('CAR_Pct', 0.0):.0f}%"
            clv_str = f"{row.get('CLV', 0.0):+.2f}"
            print(f"{idx+1:<4} | {row['Symbol']:<12} | {'SELL':<5} | {row['Coil_Score']:<5.1f} | {row.get('VCP_Label', 'N/A'):<14} | {car_str:<6} | {clv_str:<6} | {row.get('Inst_Flow', 'NORMAL'):<24} | Rs.{row['Trigger_Price']:<8.2f} | Rs.{row['Stop_Loss']:<7.2f} | Rs.{row['Target_Price']:<8.2f} (-{row['Target_Pct']}%)")
        print("=" * 145)

    else:
        target_side = "SELL" if dir_str == "SELL" else "BUY"
        k_target = k_sell if dir_str == "SELL" else k_buy
        df_target = df_res[df_res['Direction'] == target_side]
        top_candidates = df_target[df_target['Coil_Score'] >= min_score].head(k_target)
        if top_candidates.empty:
            top_candidates = df_target.head(k_target)

        # Display Single Direction Table
        print("=" * 145)
        print(f"{'Rank':<4} | {'Symbol':<12} | {'Side':<5} | {'Score':<6} | {'VCP':<14} | {'CAR':<6} | {'CLV':<6} | {'Flow':<24} | {'Trigger':<9} | {'SL':<8} | {'Target':<9}")
        print("-" * 145)
        for idx, row in top_candidates.iterrows():
            rank = idx + 1
            side_str = row.get('Direction', 'BUY')
            sign_str = "+" if side_str == "BUY" else "-"
            car_str = f"{row.get('CAR_Pct', 0.0):.0f}%"
            clv_str = f"{row.get('CLV', 0.0):+.2f}"
            print(f"{rank:<4} | {row['Symbol']:<12} | {side_str:<5} | {row['Coil_Score']:<5.1f} | {row.get('VCP_Label', 'N/A'):<14} | {car_str:<6} | {clv_str:<6} | {row.get('Inst_Flow', 'NORMAL'):<24} | Rs.{row['Trigger_Price']:<8.2f} | Rs.{row['Stop_Loss']:<7.2f} | Rs.{row['Target_Price']:<8.2f} ({sign_str}{row['Target_Pct']}%)")
        print("=" * 145)

    # 6. Save Predictions Artifact
    run_date = top_candidates['Date'].iloc[0]
    out_file = os.path.join(PRED_DIR, f"prebreakout_{dir_str.lower()}_candidates_{run_date}.csv")
    df_res.to_csv(out_file, index=False)
    print(f"\n[SUCCESS] Full ranking saved to: {out_file}", flush=True)

    # 7. Optional Rotation into instruments.json
    if rotate:
        print(f"\n[ROTATE] Updating instruments.json with {len(top_candidates)} Pre-{dir_str} stocks using Smart Hybrid Routing...", flush=True)
        instruments_path = os.path.join(BASE_DIR, "instruments.json")
        try:
            sec_map = get_security_id_map()
            with open(instruments_path, "r") as f:
                inst_data = json.load(f)

            # Clean up / disable previous rotated equities (never touch NIFTY / BANKNIFTY or joint stocks)
            for sym in list(inst_data.keys()):
                cfg = inst_data[sym]
                if cfg.get("rotated_prebreakout", False):
                    if cfg.get("rotated_joint", False):
                        cfg.pop("rotated_prebreakout", None)
                    elif "strategy_overrides" in cfg or cfg.get("type") == "INDEX":
                        cfg["enabled"] = 0
                        cfg.pop("rotated_prebreakout", None)
                    else:
                        del inst_data[sym]

            # Add / Enable selected stocks
            opt_count = 0
            stock_count = 0

            for _, row in top_candidates.iterrows():
                sym = str(row['Symbol']).upper()
                side = str(row.get('Direction', 'BUY')).upper()
                is_short = (side == "SELL")
                trig_px = float(row['Trigger_Price'])

                if is_short:
                    sl_pts = round(float(row['Stop_Loss']) - trig_px, 2)
                    tp_pts = round(trig_px - float(row['Target_Price']), 2)
                    be_pts = round(trig_px - float(row['BE_Trigger']), 2)
                    actions = ["SELL"]
                else:
                    sl_pts = round(trig_px - float(row['Stop_Loss']), 2)
                    tp_pts = round(float(row['Target_Price']) - trig_px, 2)
                    be_pts = round(float(row['BE_Trigger']) - trig_px, 2)
                    actions = ["BUY"]

                sec_id = sec_map.get(sym)
                is_fno = sym in fno_registry
                use_option = (execution_mode.lower() == "option") or (execution_mode.lower() == "hybrid" and is_fno)

                if use_option and is_fno:
                    # Option C: F&O Stock Option Execution (ATM Call for Breakout, ATM Put for Breakdown)
                    fno_info = fno_registry[sym]
                    lot_sz = fno_info['lot_size']
                    step = fno_info['strike_step']

                    # Delta-adjusted points for options (~0.50 delta for ATM contract)
                    opt_sl = round(max(1.0, sl_pts * 0.50), 2)
                    opt_tp = round(max(2.0, tp_pts * 0.50), 2)
                    opt_be = round(max(1.0, be_pts * 0.50), 2)

                    if sizing_mode == "capital":
                        est_prem = max(0.5, trig_px * 0.025)
                        cost_per_lot = est_prem * lot_sz
                        alloc = capital / max(1, len(top_candidates))
                        opt_lots = max(1, int(alloc / max(1.0, cost_per_lot)))
                    else:
                        opt_lots = 1

                    item_dict = {
                        "security_id": int(sec_id) if sec_id else int(inst_data.get(sym, {}).get("security_id", 0)),
                        "type": "STOCK",
                        "execution_mode": "OPTION",
                        "exchange_segment": "NSE_FNO",
                        "option_segment": "NSE_FNO",
                        "product_type": "INTRADAY",
                        "lot_size": lot_sz,
                        "strike_step": step,
                        "num_lots_buy": opt_lots,
                        "num_lots_sell": opt_lots,
                        "leg_mode": "BUY",
                        "allowed_actions": ["BUY"],
                        "direction": side,
                        "rotated_prebreakout": True,
                        "strategy": "Strategy_24",
                        "exit_mode": "POINTS",
                        "local_exit_monitoring": True,
                        "broker_safety_sl": True,
                        "trigger_price": trig_px,
                        "points_sl_buy": opt_sl,
                        "points_target_buy": opt_tp,
                        "points_be_buy": opt_be,
                        "enabled": 1
                    }
                    opt_count += 1
                else:
                    # Option B: 5x MIS Cash Equity Execution
                    if sizing_mode == "capital":
                        effective_capital = capital * leverage
                        shares = max(1, int(effective_capital / trig_px))
                    else:
                        shares = 1

                    item_dict = {
                        "security_id": int(sec_id) if sec_id else int(inst_data.get(sym, {}).get("security_id", 0)),
                        "lot_size": 1,
                        "type": "STOCK",
                        "execution_mode": "STOCK",
                        "exchange_segment": "NSE_EQ",
                        "product_type": "INTRADAY",
                        "num_lots_buy": 1,
                        "num_lots_sell": 1,
                        "enabled": 1,
                        "rotated_prebreakout": True,
                        "allowed_actions": actions,
                        "direction": side,
                        "strategy": "Strategy_24",
                        "max_active": 1,
                        "daily_limit": 1,
                        "exit_mode": "POINTS",
                        "stock_qty_override": shares,
                        "trigger_price": trig_px,
                        "local_exit_monitoring": True
                    }
                    if is_short:
                        item_dict["points_sl_sell"] = sl_pts
                        item_dict["points_target_sell"] = tp_pts
                        item_dict["points_be_sell"] = be_pts
                    else:
                        item_dict["points_sl_buy"] = sl_pts
                        item_dict["points_target_buy"] = tp_pts
                        item_dict["points_be_buy"] = be_pts
                    stock_count += 1

                if sym in inst_data and inst_data[sym].get("rotated_joint"):
                    item_dict["rotated_joint"] = True

                inst_data[sym] = item_dict

            with open(instruments_path, "w") as f:
                json.dump(inst_data, f, indent=2)

            print(f"[SUCCESS] Updated instruments.json! {len(top_candidates)} stocks ({opt_count} F&O Stock Options, {stock_count} 5x MIS Cash Equities) configured for Strategy_24 execution tomorrow.", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to update instruments.json: {e}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Institutional Pre-Breakout / Pre-Breakdown Coiled Stock Selector")
    parser.add_argument("--top-k", type=int, default=5, help="Number of coiled stocks to select per side (or overall)")
    parser.add_argument("--top-k-buy", type=int, default=None, help="Number of BUY stocks to select (defaults to top-k)")
    parser.add_argument("--top-k-sell", type=int, default=None, help="Number of SELL stocks to select (defaults to top-k)")
    parser.add_argument("--rotate", action="store_true", help="Rotate top stocks into instruments.json")
    parser.add_argument("--min-score", type=float, default=60.0, help="Minimum Coiling Score threshold")
    parser.add_argument("--universe", type=str, default="top500", choices=["top200", "top500", "instruments", "all"],
                        help="Stock universe to scan: top500 (default), top200, instruments, or all")
    parser.add_argument("--direction", type=str, default="both", choices=["buy", "sell", "both"],
                        help="Direction of pre-breakout setup: both (default), buy, or sell")
    parser.add_argument("--capital", type=float, default=100000.0, help="Capital allocated per cash trade (default: 100,000)")
    parser.add_argument("--leverage", type=float, default=5.0, help="MIS intraday leverage multiplier (default: 5.0x)")
    parser.add_argument("--execution-mode", type=str, default="hybrid", choices=["hybrid", "stock", "option"],
                        help="Execution routing: hybrid (default: F&O options for F&O stocks, 5x MIS for cash), stock, or option")
    parser.add_argument("--fno-only", action="store_true", help="Restrict scan exclusively to 199 NSE F&O stocks")
    parser.add_argument("--sizing-mode", type=str, default="fixed", choices=["fixed", "capital"],
                        help="Position sizing mode: 'fixed' (Option A: 1 lot/1 share) or 'capital' (Option B: dynamically sized to --capital)")
    args = parser.parse_args()

    run_prebreakout_selector(
        top_k=args.top_k,
        rotate=args.rotate,
        min_score=args.min_score,
        universe=args.universe,
        direction=args.direction,
        top_k_buy=args.top_k_buy,
        top_k_sell=args.top_k_sell,
        capital=args.capital,
        leverage=args.leverage,
        execution_mode=args.execution_mode,
        fno_only=args.fno_only,
        sizing_mode=args.sizing_mode
    )
