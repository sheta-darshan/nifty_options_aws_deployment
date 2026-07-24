import pandas as pd
import json
import argparse
import os

def update_instruments(csv_path, json_path='instruments.json'):
    if not os.path.exists(csv_path):
        print(f"Error: CSV file '{csv_path}' not found.")
        return
        
    if not os.path.exists(json_path):
        print(f"Error: JSON file '{json_path}' not found.")
        return

    # Load existing JSON data
    print(f"Loading JSON from {json_path}...")
    with open(json_path, 'r') as f:
        try:
            instruments_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading JSON: {e}")
            return

    # Load CSV data
    print(f"Loading CSV from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    # Identify the instrument column in the CSV
    instrument_col = None
    possible_names = ['Instrument', 'instrument', 'Symbol', 'symbol', 'Name', 'name']
    for col in possible_names:
        if col in df.columns:
            instrument_col = col
            break
            
    if not instrument_col:
        print(f"Error: Could not find an instrument column. Looked for: {possible_names}")
        print("Available columns in your CSV:", list(df.columns))
        return
        
    updated_count = 0
    not_found = []
    
    # Valid keys we expect to update in instruments.json
    expected_keys = [
        'lot_size', 'daily_limit', 'strike_step', 
        'trailing_mult_buy', 'trailing_mult_sell', 
        'sl_mult_buy', 'sl_mult_sell', 'tp_mult_buy', 
        'tp_mult_sell', 'enabled'
    ]
    
    print(f"Matching instruments using column: '{instrument_col}'")
    
    for index, row in df.iterrows():
        # Get the instrument name and uppercase it just in case
        inst_name = str(row[instrument_col]).strip().upper()
        
        if inst_name in instruments_data:
            updated = False
            
            # Loop through all columns in the CSV
            for col in df.columns:
                if col == instrument_col:
                    continue
                    
                val = row[col]
                if pd.isna(val):
                    continue
                    
                # Normalize column name to match json keys (lowercase, replace spaces with underscores)
                json_key = str(col).strip().lower().replace(' ', '_')
                
                # Check if this column matches an expected JSON key
                if json_key in expected_keys or json_key in instruments_data[inst_name]:
                    # Convert pandas types to standard Python types for JSON serialization
                    if isinstance(val, (int, float)):
                        if pd.isna(val): continue
                        val = float(val)
                        if val.is_integer():
                            val = int(val)
                    elif isinstance(val, bool) or str(val).lower() in ['true', 'false']:
                        val = str(val).lower() == 'true'
                        
                    # Update the value
                    instruments_data[inst_name][json_key] = val
                    updated = True
                    
            if updated:
                updated_count += 1
        else:
            not_found.append(inst_name)
            
    # Save the updated JSON back to file
    if updated_count > 0:
        print(f"Saving {updated_count} updated instruments to {json_path}...")
        with open(json_path, 'w') as f:
            json.dump(instruments_data, f, indent=4)
        print("Update complete!")
    else:
        print("No instruments were updated. Check your CSV column names.")
        print("Column names should match JSON keys like: sl_mult_buy, trailing_mult_sell, lot_size, etc.")

    if not_found:
        print(f"\nWarning: Could not find {len(not_found)} instruments from the CSV in {json_path}.")
        print("First few missing:", ', '.join(not_found[:5]))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update instruments.json values from a CSV file.")
    parser.add_argument("csv_file", help="Path to the CSV file containing the data updates.")
    parser.add_argument("--json", default="instruments.json", help="Path to instruments.json (default: instruments.json)")
    
    args = parser.parse_args()
    update_instruments(args.csv_file, args.json)
