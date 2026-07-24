import os
import sys
import json
import time
import requests
import argparse
from dotenv import load_dotenv, find_dotenv

# Setup pathing
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# Global Filter Default Configurations
DEFAULT_TOP_N = 5
DEFAULT_MAX_SPREAD_VAL = 0.30  # Maximum flat bid-ask spread in Rs
DEFAULT_MAX_SPREAD_PCT = 1.5   # Maximum spread as a percentage of the premium
DEFAULT_MIN_OI_CHANGE = 5    # Minimum percentage change in Open Interest
DEFAULT_MIN_PRICE_CHANGE = 0.8  # Minimum % price change from previous close (momentum)
DEFAULT_MAX_PRICE_CHANGE = 3.5  # Maximum % price change from previous close (exhaustion)

# Config options
TELEGRAM_URL = os.getenv("ALERT_WEBHOOK_URL")

def send_telegram_alert(message):
    if not TELEGRAM_URL:
        return
    try:
        if "chat_id=" in TELEGRAM_URL:
            url = f"{TELEGRAM_URL}&text={requests.utils.quote(message)}"
            requests.get(url, timeout=10)
        else:
            requests.post(TELEGRAM_URL, json={"text": message}, timeout=10)
    except Exception as e:
        print(f"[WARNING] Failed to send Telegram alert: {e}")

def main():
    parser = argparse.ArgumentParser(description="30-Minute Option Chain Stock Selection Scanner")
    parser.add_argument("--dry-run", action="store_true", help="Calculate rankings and print results without modifying instruments.json")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help=f"Number of stock instruments to enable (default: {DEFAULT_TOP_N})")
    parser.add_argument("--max-spread-val", type=float, default=DEFAULT_MAX_SPREAD_VAL, help=f"Maximum flat bid-ask spread in Rs allowed for the ATM option (default: {DEFAULT_MAX_SPREAD_VAL})")
    parser.add_argument("--max-spread-pct", type=float, default=DEFAULT_MAX_SPREAD_PCT, help=f"Maximum spread as percentage of premium allowed (default: {DEFAULT_MAX_SPREAD_PCT}%)")
    parser.add_argument("--min-oi-change", type=float, default=DEFAULT_MIN_OI_CHANGE, help=f"Minimum percentage change in Open Interest required to confirm buildup (default: {DEFAULT_MIN_OI_CHANGE}%)")
    parser.add_argument("--min-price-change", type=float, default=DEFAULT_MIN_PRICE_CHANGE, help=f"Minimum daily price change % required (default: {DEFAULT_MIN_PRICE_CHANGE}%)")
    parser.add_argument("--max-price-change", type=float, default=DEFAULT_MAX_PRICE_CHANGE, help=f"Maximum daily price change % allowed (default: {DEFAULT_MAX_PRICE_CHANGE}%)")
    args = parser.parse_args()

    # 1. Load credentials (support dual accounts)
    token = os.getenv("DHAN_API_TOKEN_2") or os.getenv("DHAN_API_TOKEN")
    client_id = os.getenv("DHAN_CLIENT_ID_2") or os.getenv("DHAN_CLIENT_ID")
    is_secondary = bool(os.getenv("DHAN_API_TOKEN_2") and os.getenv("DHAN_CLIENT_ID_2"))

    if not token or not client_id:
        print("[ERROR] Missing DHAN_API_TOKEN or DHAN_CLIENT_ID in environment variables.")
        sys.exit(1)

    # Throttling delay (5 req/sec = 0.2s delay for secondary; 2 req/sec = 0.5s delay for primary/shared)
    delay = 0.2 if is_secondary else 0.5

    print("=" * 80)
    print("                30-MINUTE OPTION CHAIN STOCK SCANNER RUNNING                ")
    print(f"Using Credentials: {'SECONDARY ACCOUNT' if is_secondary else 'PRIMARY ACCOUNT (Shared - Throttling enabled)'}")
    print(f"Throttling rate: {1/delay:.1f} requests per second")
    print(f"Target count to enable: {args.top_n}")
    print(f"Price change Sweet Spot: {args.min_price_change}% to {args.max_price_change}%")
    print("=" * 80)

    # 2. Load instruments.json
    inst_path = os.path.join(BASE_DIR, "instruments.json")
    if not os.path.exists(inst_path):
        print(f"[ERROR] instruments.json not found at: {inst_path}")
        sys.exit(1)

    try:
        with open(inst_path, "r") as f:
            instruments = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load instruments.json: {e}")
        sys.exit(1)

    # Extract all STOCK type instruments
    stock_candidates = {symbol: config for symbol, config in instruments.items() if config.get("type") == "STOCK"}
    
    if not stock_candidates:
        print("[INFO] No STOCK type candidates found in instruments.json. Exiting.")
        sys.exit(0)

    print(f"[INFO] Found {len(stock_candidates)} stock candidates to scan.")

    headers = {
        "access-token": token,
        "client-id": client_id,
        "Content-Type": "application/json"
    }

    # 3. Step 1: Pre-filter stocks using single OHLC request & Advanced Gap Selection Logic
    print(f"[INFO] Fetching daily OHLC quote for {len(stock_candidates)} stocks in a single request...")
    ohlc_payload = {}
    for symbol, config in stock_candidates.items():
        seg = config.get("exchange_segment", "NSE_EQ")
        sec_id = int(config.get("security_id"))
        if seg not in ohlc_payload:
            ohlc_payload[seg] = []
        ohlc_payload[seg].append(sec_id)

    ohlc_url = "https://api.dhan.co/v2/marketfeed/ohlc"
    qualified_candidates = {}

    try:
        time.sleep(delay)
        resp_ohlc = requests.post(ohlc_url, headers=headers, json=ohlc_payload, timeout=10)
        if resp_ohlc.status_code != 200:
            print(f"[ERROR] Failed to fetch marketfeed OHLC data: {resp_ohlc.text}")
            sys.exit(1)
        
        ohlc_data = resp_ohlc.json().get("data", {})
        
        for symbol, config in stock_candidates.items():
            seg = config.get("exchange_segment", "NSE_EQ")
            sec_id_str = str(config.get("security_id"))
            
            stock_quote = ohlc_data.get(seg, {}).get(sec_id_str, {})
            if not stock_quote:
                print(f"  [WARNING] No quote found for {symbol} in segment {seg}")
                continue

            last_price = stock_quote.get("last_price", 0)
            ohlc_fields = stock_quote.get("ohlc", {})
            today_open = ohlc_fields.get("open", 0)
            prev_close = ohlc_fields.get("close", 0)
            high_30m = ohlc_fields.get("high", 0)
            low_30m = ohlc_fields.get("low", 0)

            if prev_close <= 0 or today_open <= 0 or (high_30m - low_30m) <= 0:
                print(f"  [INFO] Skipping {symbol} due to flat ranges or invalid prices")
                continue

            # Advanced Gap Analysis Calculations
            gap_pct = ((today_open - prev_close) / prev_close) * 100
            intraday_move = ((last_price - today_open) / today_open) * 100
            opening_range_pct = ((high_30m - low_30m) / today_open) * 100
            price_position = (last_price - low_30m) / (high_30m - low_30m)

            price_change_pct = (last_price - prev_close) / prev_close * 100
            abs_change = abs(price_change_pct)

            # --- GAP SELECTION RULES ---

            # 1. Reject exhausted gaps (Huge gap + no participation/movement = possible fade)
            if abs(gap_pct) > 4.5 and abs(intraday_move) < 0.3:
                print(f"  [INFO] Skipping {symbol} (Exhausted Gap: Gap {gap_pct:.2f}%, Intraday move {intraday_move:.2f}%)")
                continue

            # 2. Reject indecision gaps (Gap + tiny range = no conviction)
            if opening_range_pct < 0.4:
                print(f"  [INFO] Skipping {symbol} (Indecision Gap: Range {opening_range_pct:.2f}% is too narrow)")
                continue

            # 3. Reject weak positioning (Gap up but trading near range low, or Gap down but trading near range high)
            if gap_pct > 0 and price_position < 0.5:
                print(f"  [INFO] Skipping {symbol} (Weak Position: Gap Up {gap_pct:.2f}% but price position {price_position:.2f} is in lower half)")
                continue
            if gap_pct < 0 and price_position > 0.5:
                print(f"  [INFO] Skipping {symbol} (Weak Position: Gap Down {gap_pct:.2f}% but price position {price_position:.2f} is in upper half)")
                continue

            # 4. Standard sweet-spot price change limits
            if abs_change < args.min_price_change:
                print(f"  [INFO] Skipping {symbol} (Price change {price_change_pct:.2f}% is below momentum threshold of {args.min_price_change}%)")
            elif abs_change > args.max_price_change:
                print(f"  [INFO] Skipping {symbol} (Price change {price_change_pct:.2f}% exceeds exhaustion threshold of {args.max_price_change}%)")
            else:
                qualified_candidates[symbol] = {
                    "config": config,
                    "direction": "BUY" if price_change_pct > 0 else "SELL"
                }
                print(f"  [PASS] {symbol} qualified. Gap: {gap_pct:.2f}%, Intraday Move: {intraday_move:.2f}%, Position: {price_position:.2f} | Direction: {qualified_candidates[symbol]['direction']}")

    except Exception as e:
        print(f"[ERROR] Exception occurred during OHLC pre-filter: {e}")
        sys.exit(1)

    print(f"[INFO] {len(qualified_candidates)} out of {len(stock_candidates)} stocks qualified for Option Chain scan.")
    if not qualified_candidates:
        print("[INFO] No stocks qualified. Exiting.")
        sys.exit(0)

    rankings = []

    # 4. Step 2: Scan Option Chains only for the qualified candidates
    for idx, (symbol, info) in enumerate(qualified_candidates.items()):
        config = info["config"]
        direction = info["direction"]
        print(f"[{idx+1}/{len(qualified_candidates)}] Scanning Option Chain for {symbol}...")
        sec_id = config.get("security_id")
        seg = config.get("exchange_segment", "NSE_EQ")
        strike_step = config.get("strike_step", 1)

        # Get available expiry dates
        exp_url = "https://api.dhan.co/v2/optionchain/expirylist"
        payload_exp = {
            "UnderlyingScrip": int(sec_id),
            "UnderlyingSeg": seg
        }

        try:
            time.sleep(3.1)
            resp_exp = requests.post(exp_url, headers=headers, json=payload_exp, timeout=10)
            if resp_exp.status_code != 200:
                print(f"  [WARNING] Failed to fetch expiries for {symbol}: {resp_exp.text}")
                continue
            
            exp_dates = resp_exp.json().get("data", [])
            if not exp_dates:
                print(f"  [WARNING] No active expiries found for {symbol}")
                continue
            
            first_expiry = exp_dates[0]
            
            # Fetch Option Chain
            oc_url = "https://api.dhan.co/v2/optionchain"
            payload_oc = {
                "UnderlyingScrip": int(sec_id),
                "UnderlyingSeg": seg,
                "Expiry": first_expiry
            }

            # Enforce Option Chain specific rate limit
            time.sleep(3.1)
            resp_oc = requests.post(oc_url, headers=headers, json=payload_oc, timeout=10)
            if resp_oc.status_code != 200:
                print(f"  [WARNING] Failed to fetch option chain for {symbol}: {resp_oc.text}")
                continue

            oc_data = resp_oc.json().get("data", {})
            spot_price = oc_data.get("last_price", 0)
            oc_dict = oc_data.get("oc", {})

            if not oc_dict or spot_price == 0:
                print(f"  [WARNING] Empty option chain or spot price for {symbol}")
                continue

            # Calculate ATM Strike
            closest_strike = min([float(s) for s in oc_dict.keys()], key=lambda x: abs(x - spot_price))
            closest_strike_str = f"{closest_strike:.6f}"

            # Retrieve ATM contract data
            atm_data = oc_dict.get(closest_strike_str, {})
            atm_ce = atm_data.get("ce", {})
            atm_pe = atm_data.get("pe", {})

            # Option Spread / Bid-Ask Spread check to prevent high slippage
            ce_price = atm_ce.get("last_price", 0) if atm_ce else 0
            pe_price = atm_pe.get("last_price", 0) if atm_pe else 0

            if ce_price <= 0 or pe_price <= 0:
                print(f"  [INFO] Skipping {symbol} due to zero ATM price (CE: {ce_price}, PE: {pe_price})")
                continue

            ce_spread = atm_ce.get("top_ask_price", 0) - atm_ce.get("top_bid_price", 0)
            pe_spread = atm_pe.get("top_ask_price", 0) - atm_pe.get("top_bid_price", 0)

            ce_spread_pct = (ce_spread / ce_price * 100)
            pe_spread_pct = (pe_spread / pe_price * 100)

            # Limit: flat spread limit OR percentage of premium limit
            MAX_SPREAD_VAL = args.max_spread_val
            MAX_SPREAD_PCT = args.max_spread_pct

            is_ce_liquid = (ce_spread <= MAX_SPREAD_VAL) or (ce_spread_pct <= MAX_SPREAD_PCT)
            is_pe_liquid = (pe_spread <= MAX_SPREAD_VAL) or (pe_spread_pct <= MAX_SPREAD_PCT)

            if not is_ce_liquid or not is_pe_liquid:
                print(f"  [INFO] Skipping {symbol} due to high ATM spread (CE: {ce_spread:.2f} [{ce_spread_pct:.1f}%], PE: {pe_spread:.2f} [{pe_spread_pct:.1f}%])")
                continue
            
            # Find strikes around ATM (ATM +/- 3 strikes)
            near_strikes = []
            for offset in range(-3, 4):
                target_strike = closest_strike + (offset * strike_step)
                match = min(oc_dict.keys(), key=lambda x: abs(float(x) - target_strike))
                if abs(float(match) - target_strike) < (strike_step / 2.0):
                    near_strikes.append(match)

            total_volume = 0
            total_oi = 0
            total_prev_oi = 0

            for strike in near_strikes:
                strike_data = oc_dict.get(strike, {})
                for opt in ["ce", "pe"]:
                    opt_data = strike_data.get(opt)
                    if opt_data:
                        total_volume += opt_data.get("volume", 0)
                        total_oi += opt_data.get("oi", 0)
                        total_prev_oi += opt_data.get("previous_oi", 0)

            oi_change = total_oi - total_prev_oi
            oi_change_pct = (oi_change / total_prev_oi * 100) if total_prev_oi > 0 else 0.0

            # Block deal filter: ensure significant OI change
            MIN_OI_CHANGE_PCT = args.min_oi_change
            if abs(oi_change_pct) < MIN_OI_CHANGE_PCT:
                print(f"  [INFO] Skipping {symbol} due to insignificant OI change ({oi_change_pct:.2f}%)")
                continue

            rankings.append({
                "Symbol": symbol,
                "Spot": spot_price,
                "ATM": closest_strike,
                "Volume": total_volume,
                "OI Change": oi_change,
                "OI Change (%)": round(oi_change_pct, 2),
                "Direction": direction
            })

            print(f"  -> Spot: {spot_price} | ATM: {closest_strike} | Volume: {total_volume} | OI Change: {oi_change} ({oi_change_pct:.2f}%) | Direction: {direction}")

        except Exception as e:
            print(f"  [ERROR] Exception occurred scanning {symbol}: {e}")

    if not rankings:
        print("[ERROR] No successful option chain scans completed.")
        sys.exit(1)

    # 5. Rank qualified Candidates
    sorted_ranks = sorted(rankings, key=lambda x: abs(x["OI Change (%)"]), reverse=True)
    
    print("\n" + "=" * 105)
    print("                                OPTION CHAIN SCANNER RANKING SUMMARY                             ")
    print("=" * 105)
    print(f"{'Symbol':<15}{'Spot Price':<12}{'ATM Strike':<12}{'Near-ATM Volume':<18}{'OI Change':<12}{'OI Change (%)':<15}{'Direction':<12}")
    print("-" * 105)
    for r in sorted_ranks:
        print(f"{r['Symbol']:<15}{r['Spot']:<12.2f}{r['ATM']:<12.2f}{r['Volume']:<18,}{r['OI Change']:<12,}{r['OI Change (%)']:<15.2f}{r['Direction']:<12}")
    print("=" * 105)

    # Select Top N stocks
    selected_symbols = [r["Symbol"] for r in sorted_ranks[:args.top_n]]
    print(f"\n[INFO] Selected Top Stocks: {selected_symbols}")

    if args.dry_run:
        print("[DRY-RUN] Script running in dry-run mode. Instruments file will NOT be modified.")
        send_telegram_alert(f"Option Chain Scanner (Dry-run):\nSelected Stocks: {', '.join(selected_symbols)}")
    else:
        # Modify instruments.json
        print(f"[INFO] Writing configuration changes to {inst_path}...")
        for symbol in list(instruments.keys()):
            if instruments[symbol].get("type") == "STOCK":
                if symbol in selected_symbols:
                    instruments[symbol]["enabled"] = 1
                    # Find direction from rankings
                    rank_info = next((r for r in sorted_ranks if r["Symbol"] == symbol), None)
                    if rank_info:
                        instruments[symbol]["allowed_actions"] = [rank_info["Direction"]]
                else:
                    instruments[symbol]["enabled"] = 0
                    if "allowed_actions" in instruments[symbol]:
                        del instruments[symbol]["allowed_actions"]

        try:
            with open(inst_path, "w") as f:
                json.dump(instruments, f, indent=4)
            print("[SUCCESS] instruments.json updated successfully.")
            
            # Send Telegram alert
            alert_msg = f"🔔 *Option Chain Scanner Alert*\n\nTop selected stocks activated for today:\n"
            for r in sorted_ranks[:args.top_n]:
                alert_msg += f"• *{r['Symbol']}*: Direction={r['Direction']}, Volume={r['Volume']:,}, OI Change={r['OI Change (%)']}%\n"
            send_telegram_alert(alert_msg)
            
        except Exception as e:
            print(f"[ERROR] Failed to save updated instruments.json: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
