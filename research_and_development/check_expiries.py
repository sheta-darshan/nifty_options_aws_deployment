import requests
import json
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
token = os.getenv("DHAN_API_TOKEN")
cid = os.getenv("DHAN_CLIENT_ID")

url = "https://api.dhan.co/v2/optionchain/expirylist"
headers = {
    "access-token": token,
    "client-id": cid,
    "Content-Type": "application/json"
}

payload = {
    "UnderlyingScrip": 13, # INTEGER
    "UnderlyingSeg": "IDX_I"
}

print("\nFetching Expiry List for NIFTY (Integer ID):")
response = requests.post(url, headers=headers, json=payload)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    expiries = response.json().get('data', [])
    print(f"Active Expiries (First 5): {expiries[:5]}")
else:
    print(f"Response: {response.text}")
