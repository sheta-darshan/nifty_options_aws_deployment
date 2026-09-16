import os
import json
import time
import logging
import threading
import requests
import uuid
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dhanhq import dhanhq

from trading_bot.config import Config
from trading_bot.network import RateLimiter, NetworkContext
from trading_bot.alerts import AlertManager

def safe_int(x, default=0):
    """Safely convert value to int, returns default if conversion fails"""
    try:
        return int(x)
    except (TypeError, ValueError):
        return default

class DhanAPIWrapper:
    """Wrapper around dhanhq with error handling and retry logic"""
    
    # Shared Rate Limiters by Client ID (to handle multiple instances/accounts)
    _limiters: Dict[str, RateLimiter] = {}
    _limiters_lock = threading.Lock()
    
    # Global failure tracking (Shared across all accounts/instances)
    _consecutive_failures = 0
    _failures_lock = threading.Lock()
    _MAX_CONSECUTIVE_FAILURES = 10  # Panic after 10 straight network failures
    
    def __init__(self, client_id: str, api_token: str, config: Config, logger: logging.Logger, alert_manager: AlertManager = None, account_type: str = 'primary', source_ip: str = None, proxy_url: str = None):
        self.logger = logger
        self.alert_manager = alert_manager
        self.account_type = account_type # 'primary' or 'secondary'
        self.source_ip = source_ip
        self.proxy_url = proxy_url
        
        # Support for both dhanhq v2.0 and v2.2+
        try:
            from dhanhq import DhanContext
            context = DhanContext(client_id, api_token)
            self.dhan = dhanhq(context)
        except (ImportError, TypeError):
            self.dhan = dhanhq(client_id, api_token)
        self.client_id = client_id
        self.api_token = api_token
        self.config = config
        
        # Get or Create Shared Multi-Tier Rate Limiter
        with DhanAPIWrapper._limiters_lock:
            if client_id not in DhanAPIWrapper._limiters:
                logger.info(f"[RATE_LIMIT] Creating Multi-Category RateLimiter for Client {client_id}")
                DhanAPIWrapper._limiters[client_id] = RateLimiter()
            
            self.rate_limiter = DhanAPIWrapper._limiters[client_id]

        # Cache for NIFTY LTP - used as fallback when API fails
        self.cached_nifty_ltp = None
        self.cached_ltp_timestamp = None
    
    def _make_request(self, api_call, *args, **kwargs):
        """Execute API call with category-specific rate limiting and backoff"""
        # 1. Identify API Category for Throttling
        func_name = str(api_call.__name__ if hasattr(api_call, '__name__') else api_call).lower()
        
        category = 'DATA'
        if 'ohlc' in func_name: 
            category = 'QUOTE'
        elif 'order' in func_name and 'ohlc' not in func_name: 
            category = 'ORDER'
        elif any(x in func_name for x in ['positions', 'expiry', 'master', 'security', 'portfolio']):
            category = 'NON_TRADING'
            
        # 2. Wait for Token
        self.rate_limiter.wait_if_needed(category)
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                with NetworkContext(self.source_ip, self.proxy_url, self.logger):
                    result = api_call(*args, **kwargs)
                
                if result is None:
                    raise ConnectionError("API returned None")
                    
                if not isinstance(result, dict):
                    raise ValueError(f"Invalid Response Type: {type(result)}")
                
                status = str(result.get('status') or "").strip().lower()
                if status != 'success':
                    raw_error = result.get('errorMessage') or result.get('remarks') or 'Unknown error'
                    error_msg = str(raw_error).lower()
                    
                    if "too many requests" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                        self.logger.error(f"[CIRCUIT_BREAKER] 429 Detected for {category}! Throttling globally.")
                        self.rate_limiter.trigger_circuit_breaker(30) # Global pause for 30s
                        time.sleep(5) # Local pause before retry
                        continue

                    # Fatal Authentication Errors
                    if "unauthorized" in error_msg or "token" in error_msg or "expired" in error_msg:
                        self.logger.warning(f"[AUTH_RECOVERY] Token failure for {self.client_id}. Attempting reload...")
                        success = False
                        if self.account_type == 'primary':
                            if self.config.reload_api_token():
                                self.api_token = self.config.API_TOKEN
                                success = True
                        else:
                            try:
                                with open(self.config.ACCOUNTS_FILE, 'r') as f:
                                    data = json.load(f)
                                for acc in data:
                                    if acc.get('client_id') == self.client_id:
                                        new_token = acc.get('access_token', '').strip()
                                        if new_token and new_token != self.api_token:
                                            self.api_token = new_token
                                            success = True
                                        break
                            except Exception as e:
                                self.logger.error(f"[AUTH_RECOVERY] Failed to read accounts.json: {e}")

                        if success:
                            try:
                                from dhanhq import DhanContext
                                context = DhanContext(self.client_id, self.api_token)
                                self.dhan = dhanhq(context)
                            except (ImportError, TypeError):
                                self.dhan = dhanhq(self.client_id, self.api_token)
                            continue
                        return None
                    
                    self.logger.warning(f"API error (status={status}): {error_msg}")
                    raise ConnectionError(f"Transient API Error: {error_msg}")
                
                with DhanAPIWrapper._failures_lock:
                    DhanAPIWrapper._consecutive_failures = 0
                return result
                
            except Exception as e:
                wait_time = self.config.RETRY_BACKOFF ** (attempt + 1) 
                err_str = str(e)
                
                self.logger.warning(f"API call failed (attempt {attempt + 1}/{self.config.MAX_RETRIES}): {err_str}")
                
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"API call completely failed after {self.config.MAX_RETRIES} attempts.")
                    if "connect" in err_str.lower() or "timeout" in err_str.lower():
                        with DhanAPIWrapper._failures_lock:
                            DhanAPIWrapper._consecutive_failures += 1
                            current_fails = DhanAPIWrapper._consecutive_failures
                        
                        if current_fails >= DhanAPIWrapper._MAX_CONSECUTIVE_FAILURES:
                            # H1 FIX: os._exit(1) hard-killed the process with no cleanup,
                            # leaving open positions on the broker and sending no alert.
                            # Now raise a clean exception that propagates to the InstrumentBot
                            # run() handler, which sends a Telegram alert and stops gracefully.
                            critical_msg = (
                                f"CRITICAL: {current_fails} consecutive network failures. "
                                f"Triggering graceful shutdown. Check connectivity immediately."
                            )
                            self.logger.critical(f"[CIRCUIT_BREAKER] {critical_msg}")
                            if self.alert_manager:
                                self.alert_manager.send_alert(
                                    f"🚨 *Critical Network Failure*\n"
                                    f"Bot experienced {current_fails} consecutive API failures.\n"
                                    f"Initiating graceful shutdown. Verify connectivity & positions.",
                                    header="Critical API Failure"
                                )
                            raise RuntimeError(critical_msg)
                    return None
        return None
    
    def get_historical_data(self, security_id: str, interval: int = 1, exchange_segment: str = 'IDX_I', instrument_type: str = 'INDEX', days: int = 7) -> Optional[pd.DataFrame]:
        """Fetch historical OHLC data for intraday with explicit time component"""
        try:
            # BUG-C3 FIX: datetime.now() returns server local time (UTC on AWS).
            # Must use IST explicitly so date ranges align with NSE market hours.
            import pytz as _pytz
            _IST = _pytz.timezone('Asia/Kolkata')
            now = datetime.now(_IST)
            
            # If days requested is greater than 80, fetch in chunks of 70 days to prevent API limit truncation
            if days > 80:
                self.logger.info(f"Requested {days} days of historical data. Splitting into chunks...")
                all_dfs = []
                chunk_size = 70
                remaining_days = days
                current_to_time = now
                
                while remaining_days > 0:
                    fetch_days = min(remaining_days, chunk_size)
                    from_datetime = (current_to_time - timedelta(days=fetch_days)).strftime('%Y-%m-%d 09:15:00')
                    to_datetime = current_to_time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    kwargs = {
                        "security_id": security_id,
                        "exchange_segment": exchange_segment,
                        "instrument_type": instrument_type,
                        "from_date": from_datetime,
                        "to_date": to_datetime,
                        "interval": interval
                    }
                    
                    import inspect
                    try:
                        sig = inspect.signature(self.dhan.intraday_minute_data)
                        if 'oi' in sig.parameters:
                            kwargs['oi'] = exchange_segment in ['NSE_FNO', 'BSE_FNO']
                    except Exception:
                        pass

                    response = self._make_request(
                        self.dhan.intraday_minute_data,
                        **kwargs
                    )
                    
                    df_chunk = None
                    if response and response.get('data'):
                        data = response['data']
                        if isinstance(data, dict) and 'close' in data:
                            df_chunk = pd.DataFrame(data)
                        elif isinstance(data, list) and len(data) > 0:
                            df_chunk = pd.DataFrame(data)
                            
                    if df_chunk is not None and not df_chunk.empty:
                        df_chunk.columns = df_chunk.columns.str.lower()
                        if 'open_interest' in df_chunk.columns:
                            df_chunk.rename(columns={'open_interest': 'oi'}, inplace=True)
                        
                        required_cols = ['open', 'high', 'low', 'close', 'volume']
                        if all(col in df_chunk.columns for col in required_cols):
                            if 'timestamp' in df_chunk.columns:
                                # Ensure timestamp is parsed
                                if df_chunk['timestamp'].dtype in [np.int64, np.float64, int, float]:
                                    df_chunk['timestamp'] = pd.to_datetime(df_chunk['timestamp'], unit='s')
                                else:
                                    df_chunk['timestamp'] = pd.to_datetime(df_chunk['timestamp'])
                            all_dfs.append(df_chunk)
                                
                    current_to_time = current_to_time - timedelta(days=fetch_days)
                    remaining_days -= fetch_days
                    time.sleep(0.3)  # Comply with API rate limits
                    
                if all_dfs:
                    df = pd.concat(all_dfs, ignore_index=True)
                    df.drop_duplicates(subset=['timestamp'], inplace=True)
                    df.sort_values('timestamp', inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    self.logger.info(f"Successfully stitched {len(df)} candles for past {days} days from chunks.")
                    return df
                else:
                    return None
            
            # Default standard single fetch for days <= 80
            from_datetime = (now - timedelta(days=days)).strftime('%Y-%m-%d 09:15:00')
            to_datetime = now.strftime('%Y-%m-%d %H:%M:%S')
            
            kwargs = {
                "security_id": security_id,
                "exchange_segment": exchange_segment,
                "instrument_type": instrument_type,
                "from_date": from_datetime,
                "to_date": to_datetime,
                "interval": interval
            }
            
            import inspect
            try:
                sig = inspect.signature(self.dhan.intraday_minute_data)
                if 'oi' in sig.parameters:
                    kwargs['oi'] = exchange_segment in ['NSE_FNO', 'BSE_FNO']
            except Exception:
                pass

            response = self._make_request(
                self.dhan.intraday_minute_data,
                **kwargs
            )
            
            if response and response.get('data'):
                data = response['data']
                
                if isinstance(data, dict) and 'close' in data:
                    df = pd.DataFrame(data)
                    df.columns = df.columns.str.lower()
                    if 'open_interest' in df.columns:
                        df.rename(columns={'open_interest': 'oi'}, inplace=True)
                    
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    if all(col in df.columns for col in required_cols):
                        if 'timestamp' in df.columns:
                            # Handle potential unix timestamps
                            if df['timestamp'].dtype in [np.int64, np.float64, int, float]:
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                            else:
                                df['timestamp'] = pd.to_datetime(df['timestamp'])
                        self.logger.info(f"Fetched {len(df)} candles for analysis (from {from_datetime} to {to_datetime})")
                        return df
                
                elif isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    df.columns = df.columns.str.lower()
                    if 'open_interest' in df.columns:
                        df.rename(columns={'open_interest': 'oi'}, inplace=True)
                        
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    if all(col in df.columns for col in required_cols):
                        if 'timestamp' in df.columns:
                            if df['timestamp'].dtype in [np.int64, np.float64, int, float]:
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                            else:
                                df['timestamp'] = pd.to_datetime(df['timestamp'])
                        self.logger.info(f"Fetched {len(data)} candles for analysis")
                        return df
            
            self.logger.warning(f"No historical data received from API")
            return None
            
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.exception(f"Exception in get_historical_data: {e}")
            return None
    
    def get_positions(self) -> Optional[List[Dict]]:
        """Get current open positions"""
        try:
            response = self._make_request(self.dhan.get_positions)
            
            if response and response.get('data'):
                positions = response['data']
                self.logger.debug(f"Fetched {len(positions)} positions")
                return positions if isinstance(positions, list) else [positions]
            
            return []
            
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.exception(f"Exception in get_positions: {e}")
            return []

    def get_order_status(self, order_id: str) -> Optional[str]:
        """Fetch order details from Dhan and return its status."""
        try:
            resp = self._make_request(self.dhan.get_order_by_id, order_id=order_id)
            if resp and resp.get('status') == 'success' and resp.get('data'):
                return resp['data'].get('orderStatus')
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"Error fetching status for order {order_id}: {e}")
        return None

    def place_order(self, security_id: str, transaction_type: str, quantity: int,
                   exchange_segment: str = "NSE_FNO", order_type: str = "MARKET",
                   product_type: str = "MARKET", price: float = 0.0, 
                   trigger_price: Optional[float] = None,
                   bo_profit_value: Optional[float] = None,
                   bo_stop_loss_value: Optional[float] = None,
                   should_slice: bool = False,
                   max_retries: int = 2, retry_delay: float = 1.0) -> Optional[Dict]:
        """Place order with retry mechanism and smart error handling"""
        attempt = 0
        correlation_id = str(uuid.uuid4())[:20]
        
        NON_RETRYABLE_ERRORS = [
            'insufficient', 'funds', 'invalid', 'security',
            'market closed', 'not allowed', 'margin', 'position limit'
        ]
        
        while attempt <= max_retries:
            attempt += 1
            try:
                self.logger.info(f"[PLACE_ORDER] Attempt {attempt}/{max_retries + 1} - SecurityID: {security_id}, Side: {transaction_type}, Qty: {quantity}, Slicing: {should_slice}")
                
                order_params = {
                    'security_id': security_id,
                    'exchange_segment': exchange_segment,
                    'transaction_type': transaction_type,
                    'quantity': int(quantity),
                    'order_type': order_type,
                    'product_type': product_type,
                    'price': float(price),
                    'validity': 'DAY',
                    'tag': correlation_id,
                    'should_slice': should_slice
                }
                
                if bo_profit_value is not None:
                    order_params['bo_profit_value'] = float(bo_profit_value)
                if bo_stop_loss_value is not None:
                    order_params['bo_stop_loss_Value'] = float(bo_stop_loss_value)
                
                if order_type == "STOPLOSS_MARKET":
                    if trigger_price is not None:
                        order_params['trigger_price'] = float(trigger_price)
                    else:
                        self.logger.error("[PLACE_ORDER] STOPLOSS_MARKET requires trigger_price")
                        return None
                
                self.logger.info(f"[PLACE_ORDER] Payload: {order_params}")
                response = self._make_request(self.dhan.place_order, **order_params)
                
                if response:
                    order_id = response.get('orderId')
                    status = response.get('orderStatus')
                    self.logger.info(f"[SUCCESS] Order placed: ID={order_id}, Status={status}, CorrelationID={correlation_id}")
                    response['correlationId'] = correlation_id
                    response['retry_attempts'] = attempt
                    return response
                
                self.logger.warning(f"[RETRY] No response from server. Attempt {attempt}/{max_retries + 1}")
                if attempt <= max_retries:
                    time.sleep(retry_delay)
                    continue
            except RuntimeError:
                raise
            except Exception as e:
                error_msg = str(e).lower()
                is_non_retryable = any(keyword in error_msg for keyword in NON_RETRYABLE_ERRORS)
                
                if is_non_retryable:
                    self.logger.error(f"[PERMANENT_FAILURE] {e}")
                    return None
                
                if attempt <= max_retries:
                    self.logger.warning(f"[TRANSIENT_ERROR] {e}. Retrying in {retry_delay}s (Attempt {attempt}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"[FAILED] Max retries ({max_retries}) exceeded. Error: {e}")
                    return None
        
        self.logger.error(f"[FAILED] Order placement failed after {max_retries} retries")
        return None

    def place_super_order(self, security_id: str, transaction_type: str, quantity: int,
                          price: float, target_price: float, stop_loss_price: float,
                          exchange_segment: str = "NSE_FNO", product_type: str = "MARKET",
                          order_type: str = "LIMIT", trailing_jump: float = 0.0) -> Optional[Dict]:
        """Place a 'Super Order' (Bracket Order) using the direct API endpoint."""
        url = "https://api.dhan.co/v2/super/orders"
        headers = {
            "access-token": self.api_token,
            "client-id": self.client_id,
            "Content-Type": "application/json"
        }
        
        payload = {
            "dhanClientId": self.client_id,
            "correlationId": str(uuid.uuid4())[:20],
            "transactionType": transaction_type,
            "exchangeSegment": exchange_segment,
            "productType": product_type,
            "orderType": order_type,
            "validity": "DAY",
            "securityId": str(security_id),
            "quantity": int(quantity),
            "price": float(price),
            "targetPrice": float(target_price),
            "stopLossPrice": float(stop_loss_price),
            "trailingJump": float(trailing_jump)
        }
        
        self.logger.info(f"[SUPER_ORDER] Placing BO via direct API: {payload}")
        
        self.rate_limiter.wait_if_needed()
        try:
            with NetworkContext(self.source_ip, self.proxy_url, self.logger):
                response = requests.post(url, headers=headers, json=payload, timeout=10)
            resp_json = response.json()
            
            self.logger.info(f"[SUPER_ORDER] Response: {resp_json}")
            
            if response.status_code == 200 and resp_json.get('orderStatus') in ['PENDING', 'TRANSIT', 'TRADED', 'SUBMITTED', 'SUCCESS']:
                return resp_json
            else:
                self.logger.error(f"[SUPER_ORDER] Failed: {resp_json}")
                if isinstance(resp_json, dict):
                    resp_json['failed'] = True
                    if 'orderStatus' not in resp_json or resp_json['orderStatus'] not in ['REJECTED', 'FAILED']:
                        resp_json['orderStatus'] = 'REJECTED'
                    return resp_json
                return {'orderStatus': 'REJECTED', 'remarks': str(resp_json), 'failed': True}
                
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.exception(f"[SUPER_ORDER] Exception: {e}")
            return {'orderStatus': 'FAILED', 'remarks': str(e), 'failed': True}

    def place_entry_order(self, 
                          security_id: str, 
                          transaction_type: str, 
                          quantity: int,
                          order_type: str = "MARKET",
                          price: float = 0.0,
                          target_points: float = 0.0,
                          sl_points: float = 0.0,
                          trailing_jump: float = 0.0,
                          tag: str = "",
                          product_type: str = "MARKET",
                          exchange_segment: str = "NSE_FNO",
                          ref_price: float = 0.0) -> Optional[Dict]:
        """Place the initial Entry Order. Supports BO via Super Order API if targets are provided."""
        if target_points > 0 and sl_points > 0:
            self.logger.info(f"[ENTRY] Placing SUPER ORDER (BO) {transaction_type} for {security_id} x {quantity} on {exchange_segment}")
            anchor_price = float(ref_price) if ref_price > 0 else float(price)
            
            if transaction_type == "BUY":
                target_price = anchor_price + target_points
                stop_loss_price = anchor_price - sl_points
            else: # SELL
                target_price = anchor_price - target_points
                stop_loss_price = anchor_price + sl_points
            
            target_price = max(0.05, target_price)
            stop_loss_price = max(0.05, stop_loss_price)
                
            self.logger.info(f"  >> Ref Price: {anchor_price} (Price: {price}), Target: {target_price}, SL: {stop_loss_price}")
            api_price = 0.0 if order_type == "MARKET" else float(price)
            
            return self.place_super_order(
                security_id=security_id,
                transaction_type=transaction_type,
                quantity=quantity,
                price=api_price,
                target_price=target_price,
                stop_loss_price=stop_loss_price,
                trailing_jump=trailing_jump,
                product_type=product_type,
                order_type=order_type,
                exchange_segment=exchange_segment
            )

        self.logger.info(f"[ENTRY] Placing {transaction_type} order for {security_id} x {quantity} on {exchange_segment}")
        is_fno = exchange_segment in ["NSE_FNO", "BSE_FNO"]
        return self.place_order(
            security_id=security_id,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            price=price if order_type == "LIMIT" else 0.0,
            product_type=product_type,
            exchange_segment=exchange_segment,
            should_slice=is_fno
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order by its ID."""
        try:
            self.logger.info(f"[CANCEL] Attempting to cancel order {order_id}...")
            resp = self._make_request(self.dhan.cancel_order, order_id)
            if resp and str(resp.get('orderStatus', '')).upper() in ['CANCELLED', 'SUCCESS']:
                self.logger.info(f"[CANCEL] Order {order_id} cancelled successfully.")
                return True
            else:
                self.logger.warning(f"[CANCEL] Order {order_id} cancellation failed or already cancelled. Resp: {resp}")
                return False
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"[CANCEL] Exception while cancelling order {order_id}: {e}")
            return False

    def modify_super_order_sl(self, order_id: str, new_sl_price: float) -> bool:
        """Modify the STOP_LOSS_LEG of an active Super Order to new_sl_price directly on Dhan."""
        try:
            rounded_sl = round(float(new_sl_price) * 20) / 20.0
            self.logger.info(f"[SUPER_ORDER] Modifying STOP_LOSS_LEG for order {order_id} to SL price {rounded_sl:.2f} on Dhan...")
            resp = self._make_request(
                self.dhan.modify_super_order,
                order_id=str(order_id),
                order_type="STOP_LOSS_MARKET",
                leg_name="STOP_LOSS_LEG",
                stopLossPrice=rounded_sl
            )
            is_success = resp and (
                str(resp.get('orderStatus', '')).upper() in ['SUCCESS', 'TRANSIT', 'PENDING', 'MODIFIED', 'TRADED']
                or resp.get('status') == 'success'
            )
            if is_success:
                self.logger.info(f"[SUPER_ORDER] STOP_LOSS_LEG for order {order_id} successfully updated on Dhan to {rounded_sl:.2f}.")
                return True
            else:
                self.logger.warning(f"[SUPER_ORDER] Failed to update STOP_LOSS_LEG for order {order_id}. Resp: {resp}")
                return False
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"[SUPER_ORDER] Exception while modifying STOP_LOSS_LEG for {order_id}: {e}")
            return False
            
    def get_pending_orders(self) -> List[Dict]:
        """Fetch all PENDING or OPEN orders from the broker."""
        try:
            resp = self._make_request(self.dhan.get_order_list)
            if resp and isinstance(resp.get('data'), list):
                orders = resp.get('data', [])
                pending = [o for o in orders if str(o.get('orderStatus', '')).upper() in ['PENDING', 'OPEN']]
                return pending
            return []
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"[ORDERS] Failed to fetch pending orders: {e}")
            return []

    def close_all_intraday_positions(self) -> List[Dict]:
        """Square off all open NSE_FNO intraday positions."""
        closed_positions = []
        last_runtime_error = None
        try:
            try:
                positions = self.get_positions()
            except RuntimeError as e:
                self.logger.error(f"[SQ_OFF] Circuit breaker tripped while fetching positions: {e}")
                raise

            if not positions:
                self.logger.info("[SQ_OFF] No open positions to close.")
                return []

            self.logger.info(f"[SQ_OFF] Checking {len(positions)} positions for square-off...")
            
            for pos in positions:
                exchange = pos.get('exchangeSegment', '')
                security_id = pos.get('securityId', '')
                net_qty = safe_int(pos.get('netQty', 0))
                product = pos.get('productType', 'MARKET')
                
                if (exchange in ['NSE_FNO', 'BSE_FNO', 'NSE_EQ', 'BSE_EQ']) and net_qty != 0:
                    transaction_type = 'SELL' if net_qty > 0 else 'BUY'
                    abs_qty = abs(net_qty)
                    
                    self.logger.warning(f"[SQ_OFF] Closing position: {security_id} (Qty: {net_qty}) via {transaction_type} on {exchange}")
                    
                    try:
                        response = self.place_order(
                            security_id=security_id,
                            transaction_type=transaction_type,
                            quantity=abs_qty,
                            exchange_segment=exchange,
                            product_type=product,
                            order_type='MARKET',
                            price=0.0
                        )
                        
                        if response:
                            closed_positions.append(response)
                            self.logger.info(f"[SQ_OFF] Success. Order ID: {response.get('orderId')}")
                        else:
                            self.logger.error(f"[SQ_OFF] Failed to square off {security_id}")
                    except RuntimeError as e:
                        last_runtime_error = e
                        self.logger.critical(f"[SQ_OFF] Circuit-breaker error while squaring off {security_id}: {e}. Continuing remaining positions...")
                    except Exception as e:
                        self.logger.error(f"[SQ_OFF] Exception while squaring off {security_id}: {e}")
            
            if last_runtime_error is not None:
                raise last_runtime_error

            return closed_positions

        except RuntimeError:
            raise
        except Exception as e:
            self.logger.exception(f"[SQ_OFF] Error during auto square-off: {e}")
            return []

    def get_expiry_list_v2(self, underlying_scrip: int = 13, underlying_seg: str = "IDX_I") -> List[str]:
        """
        Fetch active option expiry dates directly via Dhan API v2 (/v2/optionchain/expirylist).
        """
        url = "https://api.dhan.co/v2/optionchain/expirylist"
        headers = {
            "access-token": self.api_token,
            "client-id": self.client_id,
            "Content-Type": "application/json"
        }
        payload = {
            "UnderlyingScrip": int(underlying_scrip),
            "UnderlyingSeg": underlying_seg
        }
        self.rate_limiter.wait_if_needed('NON_TRADING')
        try:
            with NetworkContext(self.source_ip, self.proxy_url, self.logger):
                resp = requests.post(url, headers=headers, json=payload, timeout=self.config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                self.logger.info(f"[DHAN_API_V2] Expiry List fetched: {data[:5]} (Total {len(data)})")
                return data
            else:
                self.logger.error(f"[DHAN_API_V2] Expiry List Error {resp.status_code}: {resp.text}")
                return []
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"[DHAN_API_V2] Exception during get_expiry_list_v2: {e}")
            return []

    def get_option_chain_v2(self, underlying_scrip: int = 13, underlying_seg: str = "IDX_I", expiry: str = None) -> Dict:
        """
        Fetch real-time Option Chain data via Dhan API v2 (/v2/optionchain).
        Returns dictionary of strikes with LTP, security ID, and lot size.
        """
        url = "https://api.dhan.co/v2/optionchain"
        headers = {
            "access-token": self.api_token,
            "client-id": self.client_id,
            "Content-Type": "application/json"
        }
        payload = {
            "UnderlyingScrip": int(underlying_scrip),
            "UnderlyingSeg": underlying_seg
        }
        if expiry:
            payload["Expiry"] = expiry
            
        self.rate_limiter.wait_if_needed('NON_TRADING')
        try:
            with NetworkContext(self.source_ip, self.proxy_url, self.logger):
                resp = requests.post(url, headers=headers, json=payload, timeout=self.config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json().get("data", {})
            else:
                self.logger.error(f"[DHAN_API_V2] Option Chain Error {resp.status_code}: {resp.text}")
                return {}
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"[DHAN_API_V2] Exception during get_option_chain_v2: {e}")
            return {}

    def calculate_multi_order_margin(self, scrip_list: List[Dict]) -> Dict:
        """
        Calculate combined portfolio hedge margin requirements via Dhan API v2 (/v2/margincalculator/multi).
        scrip_list format:
        [
            {
                "exchangeSegment": "NSE_FNO",
                "transactionType": "BUY",
                "quantity": 195,
                "productType": "MARGIN",
                "securityId": "12345",
                "price": 200.0
            }, ...
        ]
        """
        url = "https://api.dhan.co/v2/margincalculator/multi"
        headers = {
            "access-token": self.api_token,
            "client-id": self.client_id,
            "Content-Type": "application/json"
        }
        payload = {
            "dhanClientId": self.client_id,
            "includePosition": True,
            "includeOrder": True,
            "scripList": scrip_list
        }
        self.rate_limiter.wait_if_needed('NON_TRADING')
        try:
            with NetworkContext(self.source_ip, self.proxy_url, self.logger):
                resp = requests.post(url, headers=headers, json=payload, timeout=self.config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                self.logger.info(f"[MARGIN_V2] Multi-Order Margin Required: {data.get('totalMargin')}, Available: {data.get('availableBalance')}")
                return data
            else:
                self.logger.error(f"[MARGIN_V2] Margin Calc Error {resp.status_code}: {resp.text}")
                return {}
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.error(f"[MARGIN_V2] Exception during calculate_multi_order_margin: {e}")
            return {}

    def resolve_option_security_id(self, prefix: str, strike: float, option_type: str, expiry_date: str = None, expiry_index: int = 0) -> Optional[str]:
        """
        Resolve the Dhan security ID for an option contract using master_cache_index or sec_master_df.
        """
        prefix_upper = str(prefix).upper()
        opt_type_upper = str(option_type).upper()
        strike_str = str(int(strike)) if isinstance(strike, (int, float)) and float(strike).is_integer() else str(strike)
        
        # 1. Resolve expiry date if not provided
        if not expiry_date:
            try:
                expiries = sorted(list(set(
                    key[1] for key in self.config.master_cache_index.keys()
                    if key[0] == prefix_upper
                )))
                if len(expiries) > expiry_index:
                    expiry_date = expiries[expiry_index]
            except RuntimeError:
                raise
            except Exception:
                pass

        # 2. Check master_cache_index lookup
        if expiry_date:
            strike_int = int(strike) if isinstance(strike, (int, float)) and float(strike).is_integer() else strike
            key = (prefix_upper, expiry_date, strike_int, opt_type_upper)
            if key in self.config.master_cache_index:
                return str(self.config.master_cache_index[key][0])
            key_float = (prefix_upper, expiry_date, float(strike), opt_type_upper)
            if key_float in self.config.master_cache_index:
                return str(self.config.master_cache_index[key_float][0])

        # 3. Fallback: Search master_cache_index for nearest valid future expiry
        try:
            matching_candidates = [
                (key[1], val[0]) for key, val in self.config.master_cache_index.items()
                if key[0] == prefix_upper
                and str(key[2]) == strike_str
                and key[3] == opt_type_upper
            ]
            if matching_candidates:
                today_str = datetime.now(self.config.TIMEZONE).strftime('%Y-%m-%d')
                future_candidates = [c for c in matching_candidates if c[0] >= today_str]
                if future_candidates:
                    future_candidates.sort(key=lambda x: x[0])
                    return str(future_candidates[0][1])
                matching_candidates.sort(key=lambda x: x[0])
                return str(matching_candidates[-1][1])
        except RuntimeError:
            raise
        except Exception:
            pass

        # 4. Fallback: Search sec_master_df dataframe if available
        sec_master_df = getattr(self.config, "sec_master_df", None)
        if sec_master_df is not None and not sec_master_df.empty:
            try:
                matching = sec_master_df[
                    (sec_master_df['SEM_TRADING_SYMBOL'].str.contains(f"-{strike_str}-", case=False, na=False)) &
                    (sec_master_df['SEM_TRADING_SYMBOL'].str.endswith(opt_type_upper, na=False))
                ]
                if expiry_date and not matching.empty:
                    matching_exp = matching[matching['SEM_EXPIRY_DATE'].str.startswith(expiry_date, na=False)]
                    if not matching_exp.empty:
                        matching = matching_exp
                if not matching.empty:
                    return str(matching.iloc[0]['SEM_SMST_SECURITY_ID'])
            except RuntimeError:
                raise
            except Exception as ex:
                self.logger.warning(f"[RESOLVE_SEC_ID] sec_master_df lookup failed: {ex}")

        return None


