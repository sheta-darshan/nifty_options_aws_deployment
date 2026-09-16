"""
==========================================================================================
        TOP 2 BUY & TOP 2 SELL MORNING STOCK SCREENER & BOT ACTIVATOR
==========================================================================================
Scans live 15-minute marketfeed data at 09:25 - 09:30 AM, evaluates Relative Strength (RS)
vs NIFTY, selects the Top 2 Outperformers (BUY) and Top 2 Underperformers (SELL),
and dynamically activates them in instruments.json for live bot execution (Strategy 23).
==========================================================================================
"""

import os
import sys
import json
import time
import requests
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# Default High-Volume Liquid F&O Universe
DEFAULT_FNO_UNIVERSE = [
    'RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS', 'SBIN', 'BHARTIARTL',
    'ITC', 'LT', 'BAJFINANCE', 'KOTAKBANK', 'TATAMOTORS', 'AXISBANK',
    'ADANIENT', 'MARUTI', 'SUNPHARMA', 'TITAN', 'TATASTEEL', 'COALINDIA',
    'BHEL', 'JSWSTEEL', 'HINDALCO', 'DLF', 'TRENT', 'VEDL'
]

TELEGRAM_URL = os.getenv("ALERT_WEBHOOK_URL")

def send_telegram_alert(message: str, header: str = "Morning Stock Screener"):
    if not TELEGRAM_URL:
        return
    formatted = f"🔔 *{header}*\n\n{message}"
    try:
        if "chat_id=" in TELEGRAM_URL:
            url = f"{TELEGRAM_URL}&text={requests.utils.quote(formatted)}"
            requests.get(url, timeout=10)
        else:
            requests.post(TELEGRAM_URL, json={"text": formatted}, timeout=10)
    except Exception as e:
        print(f"[WARNING] Failed to send Telegram alert: {e}")

def main():
    parser = argparse.ArgumentParser(description="Top 2 BUY & Top 2 SELL Stock Screener & Activator")
    parser.add_argument("--top-k", type=int, default=2, help="Number of Top Long and Short stocks to select (default: 2)")
    parser.add_argument("--dry-run", action="store_true", help="Calculate rankings and print without modifying instruments.json")
    parser.add_argument("--offline", action="store_true", help="Force using local spot CSV files instead of live Dhan API")
    args = parser.parse_args()

    print("=" * 90)
    print("      TOP 2 BUY & TOP 2 SELL MORNING STOCK SCREENER & ACTIVATOR (STRATEGY 23)")
    print("=" * 90)
    print(f"Target Selection: Top {args.top_k} BUY + Top {args.top_k} SELL Stocks (Total: {args.top_k*2})")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE ACTIVATION'}")
    print("=" * 90)

    # 1. Load instruments.json
    inst_path = os.path.join(BASE_DIR, "instruments.json")
    if not os.path.exists(inst_path):
        print(f"[ERROR] instruments.json not found at: {inst_path}")
        sys.exit(1)

    with open(inst_path, "r", encoding="utf-8") as f:
        instruments = json.load(f)

    # Check candidates
    universe_symbols = [s for s in DEFAULT_FNO_UNIVERSE if s in instruments]
    if not universe_symbols:
        universe_symbols = [s for s, conf in instruments.items() if conf.get("type") == "STOCK"]
    if not universe_symbols:
        universe_symbols = DEFAULT_FNO_UNIVERSE

    # 2. Check API credentials or Fallback to Local Spot Files
    token = os.getenv("DHAN_API_TOKEN_2") or os.getenv("DHAN_API_TOKEN")
    client_id = os.getenv("DHAN_CLIENT_ID_2") or os.getenv("DHAN_CLIENT_ID")
    use_live_api = (token and client_id and not args.offline)

    candidates = []

    if use_live_api:
        print(f"[API] Fetching live marketfeed OHLC for {len(universe_symbols)} candidate stocks + NIFTY...")
        headers = {
            "access-token": token,
            "client-id": client_id,
            "Content-Type": "application/json"
        }
        
        # Build payload for single batch OHLC
        ohlc_payload = {"NSE_EQ": [], "IDX_I": [13]} # 13 is NIFTY 50 security ID on Dhan
        for sym in universe_symbols:
            if sym in instruments and "security_id" in instruments[sym]:
                sec_id = int(instruments[sym]["security_id"])
                ohlc_payload["NSE_EQ"].append(sec_id)

        try:
            resp = requests.post("https://api.dhan.co/v2/marketfeed/ohlc", headers=headers, json=ohlc_payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                eq_data = data.get("NSE_EQ", {})
                idx_data = data.get("IDX_I", {}).get("13", {})
                
                nifty_open = idx_data.get("ohlc", {}).get("open", 0)
                nifty_last = idx_data.get("last_price", nifty_open)
                nifty_ret = ((nifty_last - nifty_open) / nifty_open * 100) if nifty_open > 0 else 0.0

                for sym in universe_symbols:
                    if sym not in instruments or "security_id" not in instruments[sym]:
                        continue
                    sec_id_str = str(instruments[sym]["security_id"])
                    stk_q = eq_data.get(sec_id_str, {})
                    if not stk_q:
                        continue
                    
                    last_px = stk_q.get("last_price", 0)
                    ohlc = stk_q.get("ohlc", {})
                    op = ohlc.get("open", 0)
                    hi = ohlc.get("high", 0)
                    lo = ohlc.get("low", 0)
                    prev_cl = ohlc.get("close", 0)

                    if op <= 0 or prev_cl <= 0:
                        continue

                    stk_ret = (last_px - op) / op * 100
                    rs = stk_ret - nifty_ret
                    range_pct = (hi - lo) / op * 100

                    # Read yesterday's spot file for PDH & PDL
                    spot_file = os.path.join(BASE_DIR, "backtest_data", f"{sym.lower()}_spot.csv")
                    pdh, pdl = 0.0, 0.0
                    if os.path.exists(spot_file):
                        try:
                            df_tail = pd.read_csv(spot_file).tail(800)
                            t_col = 'timestamp' if 'timestamp' in df_tail.columns else df_tail.columns[0]
                            df_tail['dt'] = pd.to_datetime(df_tail[t_col])
                            dates = sorted(df_tail['dt'].dt.date.unique())
                            if len(dates) >= 2:
                                prev_d = dates[-2] if dates[-1] == datetime.now().date() else dates[-1]
                                prev_df = df_tail[df_tail['dt'].dt.date == prev_d]
                                pdh = prev_df['high'].max()
                                pdl = prev_df['low'].min()
                        except Exception:
                            pass

                    candidates.append({
                        'Symbol': sym, 'LTP': last_px, 'Stock_Ret': stk_ret,
                        'Nifty_Ret': nifty_ret, 'RS': rs, 'Range_Pct': range_pct,
                        'PDH': pdh if pdh > 0 else hi, 'PDL': pdl if pdl > 0 else lo
                    })
        except Exception as e:
            print(f"[WARNING] Live API fetch failed ({e}). Falling back to local spot files.")
            use_live_api = False

    if not use_live_api:
        print("[LOCAL] Evaluating using local 1-minute historical spot files...")
        nifty_file = os.path.join(BASE_DIR, "backtest_data", "nifty_spot.csv")
        df_n = pd.read_csv(nifty_file).tail(400)
        df_n['dt'] = pd.to_datetime(df_n['timestamp'])
        last_d = df_n['dt'].dt.date.max()
        n_day = df_n[df_n['dt'].dt.date == last_d]
        n_open = n_day['open'].iloc[0]
        n_close = n_day['close'].iloc[-1]
        nifty_ret = (n_close - n_open) / n_open * 100

        for sym in universe_symbols:
            fpath = os.path.join(BASE_DIR, "backtest_data", f"{sym.lower()}_spot.csv")
            if not os.path.exists(fpath):
                fpath = os.path.join(BASE_DIR, "backtest_data", f"{sym.lower()}.csv")
            if not os.path.exists(fpath):
                continue
            try:
                df_s = pd.read_csv(fpath).tail(800)
                t_col = 'timestamp' if 'timestamp' in df_s.columns else df_s.columns[0]
                df_s['dt'] = pd.to_datetime(df_s[t_col])
                dates = sorted(df_s['dt'].dt.date.unique())
                if len(dates) < 2:
                    continue
                prev_d = dates[-2]
                curr_d = dates[-1]
                
                prev_day = df_s[df_s['dt'].dt.date == prev_d]
                curr_day = df_s[df_s['dt'].dt.date == curr_d]
                
                pdh = prev_day['high'].max()
                pdl = prev_day['low'].min()
                
                op = curr_day['open'].iloc[0]
                lp = curr_day['close'].iloc[-1]
                hi = curr_day['high'].max()
                lo = curr_day['low'].min()
                
                stk_ret = (lp - op) / op * 100
                rs = stk_ret - nifty_ret
                range_pct = (hi - lo) / op * 100
                
                candidates.append({
                    'Symbol': sym, 'LTP': lp, 'Stock_Ret': stk_ret,
                    'Nifty_Ret': nifty_ret, 'RS': rs, 'Range_Pct': range_pct,
                    'PDH': pdh, 'PDL': pdl
                })
            except Exception:
                continue

    if not candidates:
        print("[ERROR] No valid stock candidates evaluated.")
        sys.exit(1)

    df_cand = pd.DataFrame(candidates)
    
    # 3. Rank Top K BUY (Highest RS) and Top K SELL (Lowest RS)
    top_buy = df_cand.sort_values('RS', ascending=False).head(args.top_k)
    top_sell = df_cand.sort_values('RS', ascending=True).head(args.top_k)

    print("\n" + "=" * 100)
    print("                      SELECTED TOP BUY (BULLISH OUTPERFORMERS)                      ")
    print("=" * 100)
    print(f"{'Symbol':<15}{'LTP (Rs)':<12}{'Rel Strength (%)':<18}{'PDH Trigger':<15}{'Stop Loss (0.8%)':<18}{'Target (1.6%)':<15}")
    print("-" * 100)
    for _, r in top_buy.iterrows():
        sl_val = r['PDH'] * 0.992
        tgt_val = r['PDH'] * 1.016
        print(f"{r['Symbol']:<15}{r['LTP']:<12.2f}{r['RS']:<+18.2f}{r['PDH']:<15.2f}{sl_val:<18.2f}{tgt_val:<15.2f}")

    print("\n" + "=" * 100)
    print("                      SELECTED TOP SELL (BEARISH UNDERPERFORMERS)                   ")
    print("=" * 100)
    print(f"{'Symbol':<15}{'LTP (Rs)':<12}{'Rel Strength (%)':<18}{'PDL Trigger':<15}{'Stop Loss (0.8%)':<18}{'Target (1.6%)':<15}")
    print("-" * 100)
    for _, r in top_sell.iterrows():
        sl_val = r['PDL'] * 1.008
        tgt_val = r['PDL'] * 0.984
        print(f"{r['Symbol']:<15}{r['LTP']:<12.2f}{r['RS']:<+18.2f}{r['PDL']:<15.2f}{sl_val:<18.2f}{tgt_val:<15.2f}")
    print("=" * 100)

    # 4. Update instruments.json
    selected_buy_syms = set(top_buy['Symbol'].tolist())
    selected_sell_syms = set(top_sell['Symbol'].tolist())
    all_selected = selected_buy_syms.union(selected_sell_syms)

    if args.dry_run:
        print("\n[DRY-RUN] instruments.json not modified.")
    else:
        print(f"\n[ROTATE] Updating instruments.json...")
        for sym, conf in instruments.items():
            if conf.get("type") == "STOCK" or sym in universe_symbols:
                if sym in selected_buy_syms:
                    conf["enabled"] = 1
                    conf["type"] = "STOCK"
                    conf["execution_mode"] = "STOCK"
                    conf["allowed_actions"] = ["BUY"]
                    conf["strategy_overrides"] = {
                        "Strategy_18": {
                            "exit_mode": "PERCENTAGE",
                            "percentage_sl_buy": 0.8,
                            "percentage_target_buy": 1.6,
                            "breakout_window_end": "09:45",
                            "carry_forward": False
                        }
                    }
                elif sym in selected_sell_syms:
                    conf["enabled"] = 1
                    conf["type"] = "STOCK"
                    conf["execution_mode"] = "STOCK"
                    conf["allowed_actions"] = ["SELL"]
                    conf["strategy_overrides"] = {
                        "Strategy_18": {
                            "exit_mode": "PERCENTAGE",
                            "percentage_sl_sell": 0.8,
                            "percentage_target_sell": 1.6,
                            "breakout_window_end": "09:45",
                            "carry_forward": False
                        }
                    }
                else:
                    conf["enabled"] = 0
                    if "allowed_actions" in conf:
                        del conf["allowed_actions"]

        with open(inst_path, "w", encoding="utf-8") as f:
            json.dump(instruments, f, indent=4)
        print("[SUCCESS] instruments.json successfully updated and hot-reloaded!")

        # Telegram Notification
        msg = "🚀 *Morning Stock Screener (Strategy 23)*\n\n"
        msg += "🟢 *TOP BUY STOCKS:*\n"
        for _, r in top_buy.iterrows():
            msg += f"• *{r['Symbol']}*: RS={r['RS']:+.2f}%, PDH Trigger=`Rs.{r['PDH']:.2f}`, Target=`Rs.{r['PDH']*1.016:.2f}`\n"
        msg += "\n🔴 *TOP SELL STOCKS:*\n"
        for _, r in top_sell.iterrows():
            msg += f"• *{r['Symbol']}*: RS={r['RS']:+.2f}%, PDL Trigger=`Rs.{r['PDL']:.2f}`, Target=`Rs.{r['PDL']*0.984:.2f}`\n"
        send_telegram_alert(msg, header="Live Stock Selection Active")

if __name__ == '__main__':
    main()
