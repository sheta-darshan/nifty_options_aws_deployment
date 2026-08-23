import os
import requests
import pandas as pd

BASE_DIR = r"g:\100 Days of code\boxdata\Live trading\nifty_options_aws_deployment"
master_csv_url = "https://images.dhan.co/api-data/api-scrip-master.csv"
output_path = os.path.join(BASE_DIR, "dhanhq_master_cache.csv")

print("Downloading latest api-scrip-master.csv from Dhan...")
try:
    response = requests.get(master_csv_url, timeout=60)
    if response.status_code == 200:
        temp_csv = os.path.join(BASE_DIR, "api-scrip-master.csv")
        with open(temp_csv, "wb") as f:
            f.write(response.content)
        print("Download complete. Parsing CSV...")
        
        df = pd.read_csv(temp_csv, low_memory=False)
        print(f"Loaded {len(df)} rows. Mapping columns...")
        
        # Build mapped DataFrame
        df_mapped = pd.DataFrame()
        df_mapped['EXCH_ID'] = df['SEM_EXM_EXCH_ID'].astype(str).str.strip().str.upper()
        df_mapped['SEGMENT'] = df['SEM_SEGMENT'].astype(str).str.strip().str.upper()
        df_mapped['SECURITY_ID'] = df['SEM_SMST_SECURITY_ID']
        
        # Derive UNDERLYING_SYMBOL from SEM_TRADING_SYMBOL split
        df_mapped['UNDERLYING_SYMBOL'] = df['SEM_TRADING_SYMBOL'].astype(str).str.split('-').str[0].str.strip().str.upper()
        
        df_mapped['OPTION_TYPE'] = df['SEM_OPTION_TYPE'].astype(str).str.strip().str.upper()
        df_mapped['STRIKE_PRICE'] = pd.to_numeric(df['SEM_STRIKE_PRICE'], errors='coerce')
        
        # Clean expiry date format
        # Dhan expiry date format in compact is usually YYYY-MM-DD HH:MM:SS
        df_mapped['SM_EXPIRY_DATE'] = df['SEM_EXPIRY_DATE'].astype(str).str.split(' ').str[0].str.strip()
        
        # Save to output path
        df_mapped.to_csv(output_path, index=False)
        print(f"[SUCCESS] Rebuilt {output_path} with {len(df_mapped)} rows.")
        
        # Clean up temp file
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
    else:
        print(f"[ERROR] Failed to download scrip master. Status code: {response.status_code}")
except Exception as e:
    print(f"[ERROR] Rebuild master cache failed: {e}")
