import sys
import argparse
import json
import os
import requests
from datetime import datetime, date
import pytz

# Constants
UPSTOX_HOLIDAY_API = "https://api.upstox.com/v2/market/holidays"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "holidays_cache.json")

# Fallback Holidays (Emergency only if API and Cache both fail)
FALLBACK_HOLIDAYS = {
    "2026": [
        "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31", 
        "2026-04-03", "2026-04-14", "2026-05-01", "2026-12-25"
    ]
}

def fetch_holidays_from_api():
    """Fetch holidays from Upstox Public API"""
    try:
        response = requests.get(UPSTOX_HOLIDAY_API, headers={"Accept": "application/json"}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return data.get("data", [])
    except Exception as e:
        print(f"Error fetching from API: {e}", file=sys.stderr)
    return None

def update_cache(holiday_data):
    """Save API data to local cache file"""
    try:
        cache_data = {
            "last_updated": datetime.now().isoformat(),
            "holidays": holiday_data
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error updating cache: {e}", file=sys.stderr)
    return False

def load_from_cache():
    """Load holidays from local cache file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                return data.get("holidays", [])
        except Exception as e:
            print(f"Error reading cache: {e}", file=sys.stderr)
    return None

def get_holiday_dates():
    """Get unique set of holiday dates from API, Cache, or Fallback"""
    holiday_data = fetch_holidays_from_api()
    
    if holiday_data:
        update_cache(holiday_data)
    else:
        holiday_data = load_from_cache()
    
    holiday_set = set()
    
    # Process dynamic data (from API or Cache)
    if holiday_data:
        for item in holiday_data:
            # We filter for NSE holidays generally. 
            # The API returns list of exchanges like ["NSE", "BSE", "BCD", "MCX", "NSCOM"]
            exchanges = item.get("closed_exchanges", [])
            if "NSE" in exchanges or "BSE" in exchanges:
                date_str = item.get("date")
                if date_str:
                    holiday_set.add(date_str)
    
    # Always add Fallback for the current known year if set is empty
    if not holiday_set:
        print("Warning: Using hardcoded fallback holidays.", file=sys.stderr)
        current_year = str(datetime.now().year)
        for d in FALLBACK_HOLIDAYS.get(current_year, []):
            holiday_set.add(d)
            
    return holiday_set

def is_market_open(check_date: date) -> bool:
    """Check if market is open on a specific date"""
    # 1. Weekends
    if check_date.weekday() >= 5:
        return False
    
    # 2. Get holidays
    holidays = get_holiday_dates()
    if check_date.strftime("%Y-%m-%d") in holidays:
        return False
        
    return True

def main():
    parser = argparse.ArgumentParser(description="Automated NSE/BSE Market Holiday Checker")
    parser.add_argument("--test", type=str, help="Test a specific date (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true", help="Print detailed status")
    parser.add_argument("--force-update", action="store_true", help="Force API update and exit")
    
    args = parser.parse_args()
    
    if args.force_update:
        data = fetch_holidays_from_api()
        if data and update_cache(data):
            print("Successfully updated holiday cache from Upstox API.")
        else:
            print("Failed to update holiday cache.")
        sys.exit(0)

    if args.test:
        try:
            target_date = datetime.strptime(args.test, "%Y-%m-%d").date()
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(2)
    else:
        ist = pytz.timezone("Asia/Kolkata")
        target_date = datetime.now(ist).date()
        
    is_open = is_market_open(target_date)
    
    if args.verbose:
        status = "OPEN" if is_open else "CLOSED (Holiday or Weekend)"
        print(f"Market Status for {target_date}: {status}")
        
    sys.exit(0 if is_open else 1)

if __name__ == "__main__":
    main()
