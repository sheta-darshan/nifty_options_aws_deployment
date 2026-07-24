import time
import threading
import sys
import logging
import requests
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

# ========== RATE LIMITER ==========
class RateLimiter:
    """
    Thread-Safe Multi-Category Token Bucket Rate Limiter.
    Enforces different rate limits for different Dhan API categories:
    - QUOTE: 1 req/sec
    - DATA: 5 req/sec
    - ORDER: 10 req/sec
    - NON_TRADING: 20 req/sec
    """
    def __init__(self):
        # Category Definitions (req/sec)
        self.limits = {
            'QUOTE': 1.0,
            'DATA': 4.0,
            'ORDER': 10.0,
            'NON_TRADING': 20.0,
            'DEFAULT': 5.0
        }
        
        # Token Buckets: { category: { tokens, last_refill, last_call, lock } }
        self.buckets = {}
        for cat, rate in self.limits.items():
            self.buckets[cat] = {
                'rate': rate,
                'capacity': rate,
                'tokens': rate,
                'last_refill': time.time(),
                'last_call': 0,
                'min_interval': 1.0 / rate,
                'lock': threading.Lock()
            }
        
        # Circuit Breaker for 429s (Global)
        self.circuit_breaker_until = 0
        self.cb_lock = threading.Lock()

    def wait_if_needed(self, category: str = 'DEFAULT'):
        """Block thread until a token is available in the specified category"""
        cat = category if category in self.buckets else 'DEFAULT'
        bucket = self.buckets[cat]
        
        while True:
            # 1. Check Global Circuit Breaker
            with self.cb_lock:
                 if time.time() < self.circuit_breaker_until:
                     pause_time = self.circuit_breaker_until - time.time()
                     if pause_time > 0.1:
                         time.sleep(pause_time)
                         continue 

            # 2. Token Bucket Logic for Category
            with bucket['lock']:
                 now = time.time()
                 
                 # Refill tokens
                 elapsed = now - bucket['last_refill']
                 if elapsed > 0:
                     new_tokens = elapsed * bucket['rate']
                     bucket['tokens'] = min(bucket['capacity'], bucket['tokens'] + new_tokens)
                     bucket['last_refill'] = now
                 
                 # Smoothing: check min interval
                 time_since_last = now - bucket['last_call']
                 if time_since_last < bucket['min_interval']:
                     required_wait = bucket['min_interval'] - time_since_last
                 else:
                     required_wait = 0
                 
                 if required_wait == 0 and bucket['tokens'] >= 1:
                     bucket['tokens'] -= 1
                     bucket['last_call'] = time.time()
                     return # Success!
                 
                 # Calculate wait time for next available token/slot
                 if required_wait == 0:
                     required_wait = (1 - bucket['tokens']) / bucket['rate']
            
            # 3. Wait outside lock
            if required_wait > 0:
                time.sleep(required_wait + 0.01)

    def trigger_circuit_breaker(self, seconds: int = 30):
        """Pause all requests globally for a set duration"""
        with self.cb_lock:
            self.circuit_breaker_until = time.time() + seconds


# ========== NETWORK CONTEXT (IP & PROXY BINDING) ==========
class SourceAddressAdapter(HTTPAdapter):
    """Custom adapter to bind to a specific Source IP (Private IP on AWS)"""
    def __init__(self, source_address, **kwargs):
        self.source_address = source_address
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            source_address=self.source_address,
            **pool_kwargs
        )

# ========== THREAD-SAFE NETWORK PATCHING ==========
_thread_local_network = threading.local()

def get_network_settings():
    """Retrieve or initialize thread-local network settings"""
    if not hasattr(_thread_local_network, 'settings'):
        _thread_local_network.settings = {'source_ip': None, 'proxy_url': None}
    return _thread_local_network.settings

# Capture the original requests.Session.request method ONCE
_original_session_request = requests.Session.request

def patched_session_request(session_self, method, url, **kwargs):
    """
    A single global patch for requests.Session.request that applies 
    settings from thread-local storage. This avoids recursion issues 
    caused by multiple threads re-patching the same method.
    """
    settings = get_network_settings()
    source_ip = settings.get('source_ip')
    proxy_url = settings.get('proxy_url')
    
    # 1. Apply Source IP (EIP) binding if present in this thread's context
    if source_ip:
        adapter = SourceAddressAdapter(source_address=(source_ip, 0))
        session_self.mount("http://", adapter)
        session_self.mount("https://", adapter)
    
    # 2. Apply Proxy URL binding if present in this thread's context
    if proxy_url:
        kwargs['proxies'] = {'http': proxy_url, 'https': proxy_url}
    
    # 3. Call the original, un-patched request method
    return _original_session_request(session_self, method, url, **kwargs)

# Apply the one-time global monkey patch
requests.Session.request = patched_session_request

class NetworkContext:
    """
    A context manager that temporarily patches thread-local network settings.
    This ensures third-party libraries (like dhanhq) comply with IP whitelisting 
    regulations in a thread-safe manner.
    """
    def __init__(self, source_ip: Optional[str] = None, proxy_url: Optional[str] = None, logger: Optional[logging.Logger] = None):
        self.source_ip = source_ip.strip() if source_ip else None
        self.proxy_url = proxy_url.strip() if proxy_url else None
        self.logger = logger
        self.prev_settings = None

    def __enter__(self):
        # Save current settings for restoration
        self.prev_settings = get_network_settings().copy()
        
        # Test if source_ip is bindable on this host to prevent WinError 10049
        active_source_ip = self.source_ip
        if active_source_ip:
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind((active_source_ip, 0))
                s.close()
            except Exception:
                if self.logger:
                    self.logger.warning(f"[NETWORK] Source IP {active_source_ip} is not present/bindable on this host. Routing through default interface.")
                active_source_ip = None
        
        # Apply new settings to thread-local storage
        get_network_settings().update({
            'source_ip': active_source_ip,
            'proxy_url': self.proxy_url
        })
        
        if self.logger:
            if self.source_ip: self.logger.debug(f"[NETWORK] Thread Context -> Source IP: {self.source_ip}")
            if self.proxy_url: self.logger.debug(f"[NETWORK] Thread Context -> Proxy: {self.proxy_url}")
            
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous settings
        if self.prev_settings is not None:
            get_network_settings().update(self.prev_settings)
