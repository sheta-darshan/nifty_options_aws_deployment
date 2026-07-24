import json
import os

file_path = r"instruments.json"

to_enable = [
    "ANGELONE",
    "SAMMAANCAP",
    "AMBER",
    "ADANIENT",
    "BANDHANBNK",
    "POLICYBZR",
    "KEI",
    "TIINDIA",
    "SONACOMS",
    "CAMS",
    "RBLBANK",
    "PAYTM",
    "PNBHOUSING",
    "DIXON",
    "RECLTD",
    "GODREJPROP",
    "POLYCAB",
    "BDL",
    "KAYNES",
    "JSWENERGY",
    "ADANIPORTS",
    "HAL",
    "INDIANB",
    "BIOCON",
    "BOSCHLTD",
    "BSE",
    "SAIL",
    "POWERINDIA",
    "KPITTECH",
    "MPHASIS",
    "MAZDOCK",
    "NAUKRI",
    "BHEL",
    "DALBHARAT",
    "LICI",
    "UNIONBANK",
    "KALYANKJIL",
    "HUDCO",
    "TATAELXSI",
    "DELHIVERY",
    "DLF",
    "SHREECEM",
    "PRESTIGE",
    "COFORGE",
    "PAGEIND",
    "DMART",
    "IRCTC",
    "ETERNAL",
    "BANKBARODA",
    "LICHSGFIN"
]

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

count_enabled = 0
found_symbols = []

for key, item in data.items():
    if key in to_enable:
        item['enabled'] = True
        item['num_lots_buy'] = 1
        item['num_lots_sell'] = 1
        item['daily_limit'] = 2
        count_enabled += 1
        found_symbols.append(key)
    else:
        item['enabled'] = False

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)

missing = set(to_enable) - set(found_symbols)

print(f"Updated {count_enabled} instruments.")
if missing:
    print("Missing symbols in JSON:")
    for symbol in sorted(missing):
        print(symbol)