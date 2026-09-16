import os
import json
import time
import logging
import threading
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

from trading_bot.config import Config
from trading_bot.api_wrapper import DhanAPIWrapper

# ========== CENTRALIZED POSITION MANAGER ==========
class CentralizedPositionManager(threading.Thread):
    """
    Background Thread to poll positions once globally for all accounts.
    Redundant individual loops are replaced by this shared cache dictionary.
    """
    def __init__(self, order_manager, logger: logging.Logger, poll_interval: int = 10):
        super().__init__()
        self.order_manager = order_manager
        self.logger = logger
        self.poll_interval = poll_interval
        self.running = True
        self.cache = {}  # dict of {account_name: pos_list}
        self.lock = threading.Lock()
        self.daemon = True
        self.logger.info("[POS_MANAGER] Centralized Position Manager Initialized.")

    def run(self):
        self.logger.info("[POS_MANAGER] Centralized Position Manager thread started.")
        while self.running:
            try:
                accounts = self.order_manager.get_accounts()
                if not accounts:
                    time.sleep(1)
                    continue

                for acc in accounts:
                    acc_name = acc['name']
                    acc_api = acc['api']
                    try:
                        pos_list = acc_api.get_positions()
                        with self.lock:
                            self.cache[acc_name] = pos_list or []
                    except Exception as e:
                        self.logger.error(f"[POS_MANAGER] Error polling positions for '{acc_name}': {e}")
                
            except Exception as e:
                self.logger.error(f"[POS_MANAGER] Exception in positions run loop: {e}")
                
            # Sleep poll_interval seconds in small increments to check self.running
            for _ in range(int(self.poll_interval * 10)):
                if not self.running:
                    break
                time.sleep(0.1)

        self.logger.info("[POS_MANAGER] Centralized Position Manager thread stopped.")

    def get_cached_positions(self, account_name) -> list:
        with self.lock:
            return self.cache.get(account_name, [])

    def stop(self):
        self.running = False


# ========== MULTI-ACCOUNT MANAGER ==========
class MultiAccountManager:
    """
    Manages multiple DhanAPIWrapper instances for order execution across accounts.
    Loads configuration from accounts.json.
    """
    def __init__(self, config: Config, logger):
        self.config = config
        self.logger = logger
        self.accounts = [] # List of {'name': str, 'api': DhanAPIWrapper, 'config': dict}
        self.load_accounts()
        self.executor = ThreadPoolExecutor(max_workers=10)

    def load_accounts(self):
        """Load accounts from JSON file with retries for concurrency"""
        accounts_file = self.config.ACCOUNTS_FILE
        if not os.path.exists(accounts_file):
            self.logger.warning(f"'{accounts_file}' not found. Multi-account Execution DISABLED.")
            return

        data = []
        for attempt in range(3):
            try:
                with open(accounts_file, 'r') as f:
                    data = json.load(f)
                break
            except (json.JSONDecodeError, IOError) as e:
                if attempt == 2:
                    self.logger.error(f"[MULTI_ACC] Failed to read accounts.json after 3 attempts: {e}")
                    return
                time.sleep(0.5)

        self.accounts = []
        count = 0
        for acc in data:
            if acc.get('enabled', False):
                name = acc.get('name', f"Account_{count+1}")
                client_id = acc.get('client_id')
                token = acc.get('access_token')
                
                if client_id and token:
                    source_ip = acc.get('source_ip')
                    proxy_url = acc.get('proxy_url')
                    
                    api = DhanAPIWrapper(
                        client_id, token, self.config, self.logger, 
                        account_type='secondary',
                        source_ip=source_ip,
                        proxy_url=proxy_url
                    )
                    self.accounts.append({'name': name, 'api': api, 'config': acc})
                    self.logger.info(f"[MULTI_ACC] Loaded Account: {name} ({client_id}) | Net: {'EIP' if source_ip else 'Proxy' if proxy_url else 'Default'}")
                    count += 1
        
        self.logger.info(f"[MULTI_ACC] Total Enabled Accounts: {count}")

    def reload_accounts(self):
        """Public method to trigger a reload of accounts"""
        self.logger.info("[MULTI_ACC] Reloading accounts from disk...")
        self.load_accounts()

    def get_accounts(self):
        return self.accounts

    def execute_order_all(self, method_name: str, **kwargs) -> List[Dict]:
        """
        Execute a method (e.g., place_entry_order) on ALL enabled accounts concurrently.
        Returns a list of results (one per account).
        """
        results = []
        if not self.accounts:
            self.logger.warning("[MULTI_ACC] No accounts loaded! Order dispatch skipped.")
            return results

        futures = []
        for i, acc in enumerate(self.accounts):
            name = acc['name']
            api = acc['api']
            
            try:
                func = getattr(api, method_name, None)
                if func:
                    self.logger.info(f"[MULTI_ACC] >>> Dispatching concurrently to {name} (idx={i})...")
                    fut = self.executor.submit(func, **kwargs)
                    futures.append((name, fut))
                else:
                    self.logger.error(f"[MULTI_ACC] Method {method_name} not found on API wrapper for {name}")
                    results.append({'account': name, 'error': f"Method {method_name} not found"})
            except Exception as e:
                self.logger.error(f"[MULTI_ACC] Submission failed for {name}: {e}")
                results.append({'account': name, 'error': str(e)})

        for name, future in futures:
            try:
                resp = future.result(timeout=15)
                results.append({'account': name, 'response': resp})
            except Exception as e:
                self.logger.error(f"[MULTI_ACC] Concurrent execution failed for {name}: {e}")
                results.append({'account': name, 'error': str(e)})
        
        return results
