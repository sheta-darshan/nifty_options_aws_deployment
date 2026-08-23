import os
import json
import threading
import pytz
from datetime import datetime
from typing import Dict

class TradeState:
    """Manage trading state and order tracking"""
    
    def __init__(self, state_file: str, logger):
        self.state_file = state_file
        self.logger = logger
        self.orders = {}  # Order ID -> {details}
        self.positions = {}  # Security ID -> {position details}
        self.lock = threading.Lock()
        # H3 FIX: last_order_timestamp explicitly initialised so _enforce_order_stagger
        # works correctly even before the first order and after a restart.
        self.last_order_timestamp = 0.0
        self.load_state()
    
    def load_state(self):
        """Load state from disk"""
        with self.lock:
            try:
                if os.path.exists(self.state_file):
                    with open(self.state_file, 'r') as f:
                        data = json.load(f)
                        self.orders = data.get('orders', {})
                        self.positions = data.get('positions', {})
                        # H3 FIX: restore persisted stagger timestamp so burst guard
                        # survives process restarts.
                        self.last_order_timestamp = float(data.get('last_order_timestamp', 0.0))
                        self.logger.info(f"State loaded: {len(self.orders)} orders, {len(self.positions)} positions")
            except Exception as e:
                self.logger.warning(f"Failed to load state: {e}")
    
    def save_state(self):
        """Save state to disk atomically.
        
        C4 FIX: Write to a temp file first then os.replace() so a mid-write kill
        can never corrupt order_state.json — os.replace() is atomic on POSIX and
        effectively atomic on Windows (both NTFS rename-over semantics).
        """
        with self.lock:
            try:
                tmp_file = self.state_file + '.tmp'
                with open(tmp_file, 'w') as f:
                    json.dump({
                        'orders': self.orders,
                        'positions': self.positions,
                        'last_order_timestamp': self.last_order_timestamp,  # H3: persist stagger ts
                        'timestamp': datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
                    }, f, indent=2)
                os.replace(tmp_file, self.state_file)
            except Exception as e:
                self.logger.error(f"Failed to save state: {e}")
    
    def add_order(self, order_id: str, order_data: Dict):
        """Track an order"""
        with self.lock:
            self.orders[order_id] = {
                **order_data,
                'created_at': datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
            }
        self.save_state()
    
    def update_order_status(self, order_id: str, status: str):
        """Update order status"""
        with self.lock:
            if order_id in self.orders:
                self.orders[order_id]['status'] = status
                self.orders[order_id]['updated_at'] = datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
        self.save_state()
