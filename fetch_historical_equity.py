import os
import sys
import time
import json
import argparse
import threading
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
os.makedirs(DATA_DIR, exist_ok=True)

# Load Dhan API credentials
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "").strip().strip("'").strip('"')
API_TOKEN = os.getenv("DHAN_API_TOKEN", "").strip().strip("'").strip('"')

SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
SCRIP_MASTER_CACHE = os.path.join(BASE_DIR, "dhan_equity_master_cache.csv")
EQUITY_LIST_FILE = os.path.join(BASE_DIR, "EQUITY_L.csv")
HOLIDAYS_FILE = os.path.join(BASE_DIR, "holidays_cache.json")

class ThreadSafeRateLimiter:
    """
    Coordinates multi-threaded HTTP calls to stay safely within Dhan API limits (e.g. 8 req/s).
    """
    def __init__(self, max_req_per_sec=8.0):
        self.interval = 1.0 / max_req_per_sec
        self.lock = threading.Lock()
        self.last_call = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self.last_call = time.time()

# Global session and rate limiter
RATE_LIMITER = ThreadSafeRateLimiter(max_req_per_sec=8.0)
SESSION = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=1)
SESSION.mount("https://", adapter)

def load_nse_holidays():
    """
    Loads known NSE trading holidays from cache.
    """
    holidays = set()
    if os.path.exists(HOLIDAYS_FILE):
        try:
            with open(HOLIDAYS_FILE, "r") as f:
                data = json.load(f)
                for item in data.get("holidays", []):
                    if "NSE" in item.get("closed_exchanges", []):
                        holidays.add(item.get("date"))
        except Exception:
            pass
    return holidays

def get_last_completed_trading_session(now=None):
    """
    Calculates the exact timestamp of the last completed NSE trading session.
    Skips weekends, market holidays, and pre-market hours.
    """
    if now is None:
        now = datetime.now()
    
    holidays = load_nse_holidays()
    curr = now
    
    # If today is a weekday and not a holiday:
    if curr.weekday() < 5 and curr.strftime("%Y-%m-%d") not in holidays:
        # If market has closed today (15:30 onwards)
        if curr.hour > 15 or (curr.hour == 15 and curr.minute >= 30):
            return curr.replace(hour=15, minute=30, second=0, microsecond=0)
    
    # Otherwise, step backward to find the previous completed trading day
    curr = curr - timedelta(days=1)
    while True:
        if curr.weekday() < 5 and curr.strftime("%Y-%m-%d") not in holidays:
            return curr.replace(hour=15, minute=30, second=0, microsecond=0)
        curr = curr - timedelta(days=1)

def get_scrip_master_mapping():
    """
    Downloads or loads cached Dhan scrip master and creates a dictionary
    mapping: SYMBOL -> security_id for NSE Equity stocks.
    """
    rebuild = False
    if not os.path.exists(SCRIP_MASTER_CACHE):
        rebuild = True
    else:
        file_age_days = (time.time() - os.path.getmtime(SCRIP_MASTER_CACHE)) / 86400.0
        if file_age_days > 7.0:
            rebuild = True

    if rebuild:
        print("[INFO] Downloading latest scrip master from Dhan API...")
        try:
            r = SESSION.get(SCRIP_MASTER_URL, timeout=60)
            if r.status_code == 200:
                temp_master = os.path.join(BASE_DIR, "temp_scrip_master.csv")
                with open(temp_master, "wb") as f:
                    f.write(r.content)
                
                df = pd.read_csv(temp_master, low_memory=False)
                df_nse_eq = df[
                    (df['SEM_EXM_EXCH_ID'].astype(str).str.strip().str.upper() == 'NSE') &
                    (df['SEM_SEGMENT'].astype(str).str.strip().str.upper() == 'E')
                ].copy()
                
                df_nse_eq['SYMBOL'] = df_nse_eq['SEM_TRADING_SYMBOL'].astype(str).str.split('-').str[0].str.strip().str.upper()
                df_nse_eq['SECURITY_ID'] = df_nse_eq['SEM_SMST_SECURITY_ID'].astype(str).str.strip()
                
                df_out = df_nse_eq[['SYMBOL', 'SECURITY_ID', 'SEM_TRADING_SYMBOL', 'SEM_INSTRUMENT_NAME']].drop_duplicates(subset=['SYMBOL'])
                df_out.to_csv(SCRIP_MASTER_CACHE, index=False)
                print(f"[SUCCESS] Cached {len(df_out)} NSE Equity security IDs to {SCRIP_MASTER_CACHE}")
                
                if os.path.exists(temp_master):
                    os.remove(temp_master)
            else:
                print(f"[WARNING] Failed to download scrip master (HTTP {r.status_code}). Trying existing cache...")
        except Exception as e:
            print(f"[WARNING] Could not fetch Dhan scrip master online: {e}. Falling back to local cache.")

    if os.path.exists(SCRIP_MASTER_CACHE):
        df_cache = pd.read_csv(SCRIP_MASTER_CACHE)
        mapping = {}
        for _, row in df_cache.iterrows():
            sym = str(row['SYMBOL']).strip().upper()
            sec_id = str(row['SECURITY_ID']).strip()
            mapping[sym] = sec_id
        return mapping
    else:
        raise FileNotFoundError("[ERROR] No scrip master available to map stock symbols to Dhan security IDs.")

def get_target_symbols(args_symbols=None, csv_path=EQUITY_LIST_FILE, limit=None):
    """
    Retrieves the list of stock symbols to process.
    """
    if args_symbols:
        symbols = [s.strip().upper() for s in args_symbols if s.strip()]
        return symbols

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"[ERROR] Equity list CSV not found at: {csv_path}")

    df_eq = pd.read_csv(csv_path)
    sym_col = None
    for c in ['SYMBOL', 'Symbol', 'symbol', 'INSTRUMENT', 'Instrument']:
        if c in df_eq.columns:
            sym_col = c
            break
    if not sym_col:
        sym_col = df_eq.columns[0]

    if 'SERIES' in df_eq.columns:
        df_eq = df_eq[df_eq['SERIES'].astype(str).str.strip().str.upper() == 'EQ']

    symbols = df_eq[sym_col].astype(str).str.strip().str.upper().tolist()
    symbols = [s for s in symbols if s and s != 'NAN']

    if limit and limit > 0:
        symbols = symbols[:limit]

    return symbols

def get_last_recorded_timestamp(filepath):
    """
    Ultra-fast binary seek to inspect the last line of a CSV file (< 0.1ms).
    """
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 50:
        return None

    try:
        with open(filepath, "rb") as f:
            f.seek(0, os.SEEK_END)
            filesize = f.tell()
            buffer_size = min(filesize, 4096)
            f.seek(-buffer_size, os.SEEK_END)
            lines = f.readlines()
            
            for line in reversed(lines):
                line_str = line.decode('utf-8', errors='ignore').strip()
                if line_str and not line_str.startswith('timestamp') and not line_str.startswith('start_time'):
                    parts = line_str.split(',')
                    if parts:
                        ts_str = parts[0].strip()
                        try:
                            ts = pd.to_datetime(ts_str)
                            if pd.notna(ts):
                                return ts
                        except Exception:
                            pass
    except Exception:
        pass

    return None

def fetch_intraday_chunks(sec_id, start_dt, end_dt, client_id=CLIENT_ID, api_token=API_TOKEN, verbose=False):
    """
    Downloads 1-minute OHLCV candles from Dhan API in 30-day chunks with rate limiting and connection pooling.
    """
    url = "https://api.dhan.co/v2/charts/intraday"
    headers = {
        "access-token": api_token,
        "client-id": client_id,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    all_dfs = []
    current = start_dt

    while current < end_dt:
        next_chunk = current + timedelta(days=30)
        chunk_end = min(next_chunk, end_dt)

        payload = {
            "securityId": str(sec_id),
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "interval": "1",
            "fromDate": current.strftime("%Y-%m-%d 09:15:00"),
            "toDate": chunk_end.strftime("%Y-%m-%d 15:30:00")
        }

        for attempt in range(3):
            RATE_LIMITER.wait()
            try:
                resp = SESSION.post(url, headers=headers, json=payload, timeout=15)
                if resp.status_code == 200:
                    resp_json = resp.json()
                    raw_data = resp_json.get("data", resp_json)
                    
                    df_chunk = pd.DataFrame()
                    if raw_data and isinstance(raw_data, list):
                        df_chunk = pd.DataFrame(raw_data)
                    elif raw_data and isinstance(raw_data, dict) and "close" in raw_data:
                        df_chunk = pd.DataFrame(raw_data)

                    if not df_chunk.empty:
                        df_chunk.columns = df_chunk.columns.str.lower()
                        if 'timestamp' in df_chunk.columns:
                            if pd.api.types.is_numeric_dtype(df_chunk['timestamp']):
                                df_chunk['timestamp'] = pd.to_datetime(df_chunk['timestamp'], unit='s')
                                df_chunk['timestamp'] = df_chunk['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                            else:
                                df_chunk['timestamp'] = pd.to_datetime(df_chunk['timestamp'])
                        elif 'start_time' in df_chunk.columns:
                            df_chunk['timestamp'] = pd.to_datetime(df_chunk['start_time'])

                        cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                        cols = [c for c in cols if c in df_chunk.columns]
                        all_dfs.append(df_chunk[cols])
                        if verbose:
                            print(f"    Chunk {current.strftime('%Y-%m-%d')} -> {chunk_end.strftime('%Y-%m-%d')}: {len(df_chunk)} candles")
                    break
                elif resp.status_code == 429:
                    time.sleep(2.0)
                elif resp.status_code == 400:
                    break
                else:
                    time.sleep(0.3)
            except Exception:
                time.sleep(0.5)

        current = next_chunk

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        combined.dropna(subset=['timestamp', 'close'], inplace=True)
        combined.sort_values(by='timestamp', inplace=True)
        combined.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
        return combined
    else:
        return pd.DataFrame()

def sync_stock_historical_data(symbol, sec_id, years=5.0, force_full=False, dry_run=False, verbose=False, last_session_cutoff=None):
    """
    Performs full or incremental sync for a single stock symbol.
    """
    out_file = os.path.join(DATA_DIR, f"{symbol.lower()}_spot.csv")
    now = datetime.now()

    if last_session_cutoff is None:
        last_session_cutoff = get_last_completed_trading_session(now)

    last_ts = None if force_full else get_last_recorded_timestamp(out_file)
    if last_ts is not None and pd.isna(last_ts):
        last_ts = None

    if last_ts is not None:
        # Check if already up to date with the last completed session
        # If last_ts is within 20 mins of session close, or within 10 mins of now (if during live session)
        if last_ts >= (last_session_cutoff - timedelta(minutes=20)):
            return {"symbol": symbol, "status": "UP_TO_DATE", "new_rows": 0, "last_ts": str(last_ts)}
        
        # If currently within live trading hours and updated within last 15 mins
        if (now - last_ts).total_seconds() < 900.0:
            return {"symbol": symbol, "status": "UP_TO_DATE", "new_rows": 0, "last_ts": str(last_ts)}

        start_date = last_ts - timedelta(minutes=5)
        is_incremental = True
    else:
        start_date = now - timedelta(days=int(years * 365))
        is_incremental = False

    if dry_run:
        return {
            "symbol": symbol, 
            "status": "DRY_RUN", 
            "incremental": is_incremental,
            "from": start_date.strftime("%Y-%m-%d %H:%M"),
            "to": now.strftime("%Y-%m-%d %H:%M")
        }

    df_new = fetch_intraday_chunks(sec_id, start_date, now, verbose=verbose)

    if df_new.empty:
        if not is_incremental:
            return {"symbol": symbol, "status": "NO_DATA_FROM_API", "new_rows": 0}
        else:
            return {"symbol": symbol, "status": "UP_TO_DATE", "new_rows": 0, "last_ts": str(last_ts)}

    if is_incremental and os.path.exists(out_file):
        df_old = pd.read_csv(out_file)
        if 'timestamp' in df_old.columns:
            df_old['timestamp'] = pd.to_datetime(df_old['timestamp'])
        df_final = pd.concat([df_old, df_new], ignore_index=True)
        df_final.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
        df_final.sort_values(by='timestamp', inplace=True)
        new_count = len(df_final) - len(df_old)
    else:
        df_final = df_new
        new_count = len(df_final)

    df_final.to_csv(out_file, index=False)
    latest_ts_str = str(df_final['timestamp'].iloc[-1])

    return {
        "symbol": symbol,
        "status": "SYNCED",
        "incremental": is_incremental,
        "new_rows": new_count,
        "total_rows": len(df_final),
        "latest_ts": latest_ts_str
    }

def main():
    parser = argparse.ArgumentParser(description="High-Speed Incremental Historical Data Ingestion Engine for NSE Stocks")
    parser.add_argument("--years", type=float, default=5.0, help="Years of history for new stocks (default: 5.0)")
    parser.add_argument("--csv", type=str, default=EQUITY_LIST_FILE, help="Path to EQUITY_L.csv stock list")
    parser.add_argument("--symbols", nargs="+", default=None, help="Target specific stock symbols (e.g. --symbols RELIANCE TCS)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of stocks to process")
    parser.add_argument("--workers", type=int, default=5, help="Number of concurrent download worker threads (default: 5)")
    parser.add_argument("--force-full", action="store_true", help="Force full redownload instead of incremental update")
    parser.add_argument("--dry-run", action="store_true", help="Preview missing date ranges without calling APIs")
    parser.add_argument("--verbose", action="store_true", help="Print per-chunk download details")
    args = parser.parse_args()

    print("=" * 90)
    print("      INSTITUTIONAL HIGH-SPEED EQUITY HISTORICAL INGESTION ENGINE (DHAN API)")
    print("=" * 90)

    if not CLIENT_ID or not API_TOKEN:
        print("[CRITICAL ERROR] Missing DHAN_CLIENT_ID or DHAN_API_TOKEN in .env file.")
        sys.exit(1)

    now = datetime.now()
    last_session = get_last_completed_trading_session(now)
    print(f"[MARKET TIMING] Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[MARKET TIMING] Last Completed Session Cutoff: {last_session.strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n[STEP 1] Loading Dhan Scrip Master Mapping...")
    mapping = get_scrip_master_mapping()
    print(f"Loaded mapping with {len(mapping)} active NSE equity securities.")

    print("\n[STEP 2] Resolving Target Stock Symbols...")
    symbols = get_target_symbols(args.symbols, args.csv, args.limit)
    print(f"Total symbols in universe: {len(symbols)}")

    # Pre-Flight In-Memory Disk Scan (< 0.2s)
    print("\n[STEP 3] Running Instant Pre-Flight Disk Scan...")
    t0_scan = time.time()
    
    scan_up_to_date = []
    scan_needs_sync = []
    scan_missing_id = []

    for sym in symbols:
        sec_id = mapping.get(sym)
        if not sec_id:
            scan_missing_id.append(sym)
            continue
        
        if args.force_full:
            scan_needs_sync.append((sym, sec_id, False))
            continue

        out_file = os.path.join(DATA_DIR, f"{sym.lower()}_spot.csv")
        last_ts = get_last_recorded_timestamp(out_file)
        
        if last_ts is not None and last_ts >= (last_session - timedelta(minutes=20)):
            scan_up_to_date.append((sym, str(last_ts)))
        elif last_ts is not None:
            scan_needs_sync.append((sym, sec_id, True)) # Incremental delta
        else:
            scan_needs_sync.append((sym, sec_id, False)) # Full init

    scan_elapsed = time.time() - t0_scan
    print("=" * 90)
    print(f"  Instant Pre-Scan Completed in {scan_elapsed:.3f}s:")
    print(f"  * Already Up-to-Date:        {len(scan_up_to_date)} stocks (Skipped instantly)")
    print(f"  * Require Delta / Full Sync: {len(scan_needs_sync)} stocks")
    print(f"  * Missing Security IDs:      {len(scan_missing_id)} stocks")
    print("=" * 90)

    if not scan_needs_sync:
        print("\n[ALL DATA CURRENT] All stock historical datasets are 100% up-to-date! No downloads needed.")
        return

    # Multi-Threaded Execution for Pending Stocks
    print(f"\n[STEP 4] Processing {len(scan_needs_sync)} stocks with {args.workers} concurrent workers...")
    synced_count = 0
    up_to_date_count = len(scan_up_to_date)
    error_count = 0
    start_time = time.time()

    def process_symbol_task(task_data):
        sym, sec_id, is_inc = task_data
        try:
            res = sync_stock_historical_data(
                symbol=sym,
                sec_id=sec_id,
                years=args.years,
                force_full=args.force_full,
                dry_run=args.dry_run,
                verbose=args.verbose,
                last_session_cutoff=last_session
            )
            return True, res
        except Exception as e:
            return False, {"symbol": sym, "error": str(e)}

    completed = 0
    total_to_process = len(scan_needs_sync)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_symbol_task, item): item[0] for item in scan_needs_sync}
        
        for future in as_completed(futures):
            completed += 1
            success, res = future.result()
            sym = res.get("symbol")
            
            if success:
                status = res.get("status")
                if status == "UP_TO_DATE":
                    up_to_date_count += 1
                    print(f"[{completed}/{total_to_process}] {sym:12s} -> [UP TO DATE] Last: {res.get('last_ts', 'N/A')}")
                elif status == "SYNCED":
                    synced_count += 1
                    mode_str = "Incremental" if res.get('incremental') else "Full Init"
                    print(f"[{completed}/{total_to_process}] {sym:12s} -> [SYNCED] ({mode_str}) +{res.get('new_rows')} rows | Total: {res.get('total_rows')} | Last: {res.get('latest_ts')}")
                elif status == "DRY_RUN":
                    mode_str = "Incremental" if res.get('incremental') else "Full Init"
                    print(f"[{completed}/{total_to_process}] {sym:12s} -> [DRY RUN] ({mode_str}) Window: {res.get('from')} -> {res.get('to')}")
                else:
                    print(f"[{completed}/{total_to_process}] {sym:12s} -> [{status}]")
            else:
                error_count += 1
                print(f"[{completed}/{total_to_process}] {sym:12s} -> [ERROR] {res.get('error')}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 90)
    print("                         DATA INGESTION SUMMARY REPORT")
    print("=" * 90)
    print(f"Total Target Stocks:      {len(symbols)}")
    print(f"Already Up-To-Date:       {up_to_date_count}")
    print(f"Synced / Updated Stocks:  {synced_count}")
    print(f"Missing Security IDs:     {len(scan_missing_id)}")
    print(f"Errors Encountered:       {error_count}")
    print(f"Total Execution Time:     {elapsed:.1f}s ({elapsed/60.0:.2f} mins)")
    print(f"Output Directory:         {DATA_DIR}")
    print("=" * 90)

if __name__ == "__main__":
    main()
