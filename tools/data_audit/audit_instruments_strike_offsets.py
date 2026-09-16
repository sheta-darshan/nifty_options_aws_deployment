"""
Audit Script: Scan instruments.json and Strategy Overrides for Strike Offsets.
Reports maximum strike_offset_buy and strike_offset_sell values to verify
if any exceed the dataset's coverage envelope of [-10, +10].
"""
import os
import json
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INSTRUMENTS_JSON = os.path.join(BASE_DIR, "instruments.json")

def main():
    print("=" * 90)
    print("      INSTRUMENTS.JSON & STRATEGY OVERRIDES STRIKE OFFSET AUDIT")
    print("=" * 90)

    if not os.path.exists(INSTRUMENTS_JSON):
        print(f"File {INSTRUMENTS_JSON} not found!")
        return

    with open(INSTRUMENTS_JSON, 'r') as f:
        data = json.load(f)

    records = []

    for inst_name, inst_cfg in data.items():
        base_buy = inst_cfg.get('strike_offset_buy', 0)
        base_sell = inst_cfg.get('strike_offset_sell', 0)
        base_offset = inst_cfg.get('strike_offset', 0)
        
        records.append({
            'instrument': inst_name,
            'scope': 'Base Instrument Config',
            'strike_offset_buy': base_buy,
            'strike_offset_sell': base_sell,
            'strike_offset': base_offset,
            'max_abs_offset': max(abs(base_buy), abs(base_sell), abs(base_offset))
        })
        
        # Check strategy overrides
        overrides = inst_cfg.get('strategy_overrides', {})
        for strat_name, strat_cfg in overrides.items():
            s_buy = strat_cfg.get('strike_offset_buy', base_buy)
            s_sell = strat_cfg.get('strike_offset_sell', base_sell)
            s_off = strat_cfg.get('strike_offset', base_offset)
            max_s = max(abs(s_buy), abs(s_sell), abs(s_off))
            records.append({
                'instrument': inst_name,
                'scope': f"Override: {strat_name}",
                'strike_offset_buy': s_buy,
                'strike_offset_sell': s_sell,
                'strike_offset': s_off,
                'max_abs_offset': max_s
            })

    df_offsets = pd.DataFrame(records)
    
    max_global = df_offsets['max_abs_offset'].max()
    print(f"Total Config Scopes Audited: {len(df_offsets)}")
    print(f"Maximum Strike Offset Used Anywhere: {max_global}")
    print(f"Coverage Envelope of Dataset:        [-10, +10] (Max offset = 10)")
    
    exceeding = df_offsets[df_offsets['max_abs_offset'] > 10]
    if not exceeding.empty:
        print(f"\n[ALERT] Found {len(exceeding)} configurations with offset > 10:")
        print(exceeding.to_string(index=False))
    else:
        print(f"\nAll configurations across instruments.json are strictly within [-10, +10].")
        print("ZERO strategy overrides exceed the offline dataset's strike envelope.")

    print("\nDetailed Strike Offset Table across all instruments and strategies:")
    print(df_offsets.to_string(index=False))

if __name__ == "__main__":
    main()
