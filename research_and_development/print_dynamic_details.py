import pandas as pd

def print_summary(csv_file, name):
    try:
        df = pd.read_csv(csv_file)
        print(f"\n==================================================")
        print(f"       {name.upper()} DETAILED PROFILE")
        print(f"==================================================")
        
        # Group by Trade_ID (each leg has the same Trade_ID if it belongs to the same entry event? No, trade_id_counter is unique per leg)
        # Let's group by Entry_Date and Stance to reconstruct each stance cycle
        df['Cycle_ID'] = df['Entry_Date'] + "_" + df['Stance']
        cycles = df.groupby(['Entry_Date', 'Stance'])
        
        total_cycles = 0
        winning_cycles = 0
        early_exits = 0
        cycle_pnls = []
        
        early_exit_examples = []
        
        for keys, group in cycles:
            total_cycles += 1
            cycle_pnl = group['Net_PnL'].sum()
            cycle_pnls.append(cycle_pnl)
            if cycle_pnl > 0:
                winning_cycles += 1
            
            # Check if any leg had EARLY_EXIT
            has_early_exit = (group['Status'] == 'EARLY_EXIT').any()
            if has_early_exit:
                early_exits += 1
                early_exit_examples.append({
                    'Entry_Date': keys[0],
                    'Exit_Date': group['Exit_Date'].iloc[0],
                    'Stance': keys[1],
                    'PnL': cycle_pnl
                })
                
        avg_cycle_pnl = sum(cycle_pnls) / len(cycle_pnls) if cycle_pnls else 0
        win_rate = winning_cycles / total_cycles * 100 if total_cycles else 0
        
        print(f"Total Calendar Cycles:     {total_cycles}")
        print(f"Winning Cycles:            {winning_cycles} ({win_rate:.2f}%)")
        print(f"Early Exit Cycles:         {early_exits}")
        print(f"Average Profit per Cycle:  Rs. {avg_cycle_pnl:,.2f}")
        print(f"Total Net PnL (legs):      Rs. {df['Net_PnL'].sum():,.2f}")
        
        print("\n--- Examples of Early Exit Cycles (> Rs. 5000) ---")
        for i, ex in enumerate(early_exit_examples[:5]):
            print(f"{i+1}. {ex['Stance']} entered on {ex['Entry_Date']}, exited early on {ex['Exit_Date']} with profit: Rs. {ex['PnL']:,.2f}")
            
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")

if __name__ == "__main__":
    print_summary("detailed_trades_option_a_(max_profit).csv", "Option A (200 Monthly)")
    print_summary("detailed_trades_option_b_(net_credit_collected).csv", "Option B (150 Monthly)")
