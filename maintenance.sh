#!/bin/bash
# Pre-run maintenance script for the Live Trading Bot
# Designed to be run by systemd before starting the main Python process

# Set timezone explicitly just in case
sudo timedatectl set-timezone Asia/Kolkata

cd "$(dirname "$0")" || exit

echo "==========================================="
echo "Date: $(date)"
echo "Running Pre-Start Maintenance..."

# 0. Market Holiday Check
IS_OPEN_SCRIPT="./venv/bin/python is_market_open.py"
if [ ! -f "is_market_open.py" ]; then
    echo "Warning: is_market_open.py not found. Proceeding without holiday check."
else
    # Run the script and check exit code
    # Exit code 0 = Open, 1 = Closed
    if ! $IS_OPEN_SCRIPT; then
        echo "==========================================="
        echo "MARKET IS CLOSED (Holiday or Weekend)."
        echo "Proceeding to main bot for graceful exit (Status 0)..."
        echo "==========================================="
        exit 0 # Exit 0 to prevent systemd from marking this as a FAILURE
    fi
    echo "Market is OPEN. Proceeding..."
fi

echo "==========================================="

# 1. Archive order_state.json safely
STATE_FILE="order_state.json"
ARCHIVE_DIR="archive"
TODAY=$(date +"%Y-%m-%d")

if [ -f "$STATE_FILE" ]; then
    mkdir -p "$ARCHIVE_DIR"
    
    # Check if we are in the safe pre-market window (e.g. 08:00 to 09:00 IST)
    # This prevents blindly wiping the state if systemd auto-restarts the bot mid-day.
    CURRENT_HOUR=$(date +%H)
    if [ "$CURRENT_HOUR" -lt 9 ]; then
        echo "Safe pre-market window detected. Archiving previous day's state..."
        cp "$STATE_FILE" "$ARCHIVE_DIR/order_state_$TODAY.json"
        
        # Clear the state file safely by putting an empty JSON object
        echo "{}" > "$STATE_FILE"
        echo "State file cleared for new trading day."
    else
        echo "WARNING: Restarting mid-session (Hour: $CURRENT_HOUR). DO NOT clear state."
        echo "Preserving existing $STATE_FILE to retain open order tracking."
    fi
else
    echo "No $STATE_FILE found. Creating empty state..."
    echo "{}" > "$STATE_FILE"
fi

echo "Maintenance complete. Safe to launch python bot."
exit 0
