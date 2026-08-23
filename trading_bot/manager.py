import time
import logging
from datetime import datetime, timedelta

from trading_bot.config import Config
from trading_bot.api_wrapper import DhanAPIWrapper
from trading_bot.alerts import AlertManager
from trading_bot.account_manager import MultiAccountManager, CentralizedPositionManager
from trading_bot.state import TradeState
from trading_bot.instrument_bot import InstrumentBot

# ========== ENTRY POINT ==========
class ThreadedBotManager:
    """
    Manages multiple InstrumentBots concurrently.
    """
    def __init__(self, config: Config, logger: logging.Logger, alert_manager: AlertManager):
        self.config = config
        self.logger = logger
        self.alert_manager = alert_manager
        self.primary_api = DhanAPIWrapper(
            config.CLIENT_ID, config.API_TOKEN, config, logger, alert_manager, 
            account_type='primary',
            source_ip=config.SOURCE_IP,
            proxy_url=config.PROXY_URL
        ) # Used for Data
        self.order_manager = MultiAccountManager(config, logger) # Used for Orders
        self.position_manager = CentralizedPositionManager(self.order_manager, logger)
        self.order_manager.position_manager = self.position_manager
        self.state = TradeState(config.ORDER_STATE_FILE, logger)
        self.bots = []

    def start(self):
        self.logger.info("=" * 60)
        self.logger.info("Starting MULTI-THREADED BOT (Stocks + Options)")
        self.logger.info("Independent Limits & Thread-Safe Architecture")
        self.logger.info("=" * 60)
        
        # 0. Weekend/Holiday Check
        if not self.config.is_market_day():
            now = datetime.now(self.config.TIMEZONE)
            reason = "WEEKEND" if now.weekday() >= 5 else "MARKET HOLIDAY"
            self.logger.warning(f"!!! TODAY IS NOT A TRADING DAY ({reason}) !!!")
            self.logger.warning("Bot will terminate now to save resources (Status 0).")
            return

        # Pre-build in-memory security master index
        self.config.build_master_index(self.logger)

        # Verify if executing accounts are loaded
        if not self.order_manager.get_accounts():
            self.logger.error("!!! CONFIGURATION ERROR: No active trading accounts configured in accounts.json !!!")
            self.logger.error("Live order execution will be disabled.")
            if self.alert_manager:
                self.alert_manager.send_alert("No active trading accounts found in accounts.json. Live execution is disabled.", header="Bot Configuration Error")

        # Start Position Polling Manager
        self.position_manager.start()

        # Initial Bot Creation
        self._sync_bots()

        if not self.bots:
            self.logger.error("No instruments enabled! Check Config.")
            if self.alert_manager:
                self.alert_manager.send_alert("Bot started but no instruments are enabled. Check Config.", header="Bot Warning")
        else:
            if self.alert_manager:
                instr_list = ", ".join([b.instrument_name for b in self.bots if b.is_alive()])
                self.alert_manager.send_alert(
                    f"Bot initialized successfully.\n*Active Instruments:* `{instr_list}`\n*Timezone:* {self.config.TIMEZONE.zone}\n*Net:* {'EIP/Proxy active' if self.config.SOURCE_IP or self.config.PROXY_URL else 'Default'}",
                    header="Bot Started"
                )
        
        # Monitor Loop
        last_instr_reload = time.time()
        sq_off_triggered = False
        try:
            while True:
                now = time.time()
                current_time = datetime.now(self.config.TIMEZONE).time()
                
                # EOD Auto Square-off if CARRY_FORWARD is False
                if not self.config.CARRY_FORWARD and current_time >= self.config.SQ_OFF_TIME and not sq_off_triggered:
                    self.logger.warning("[MANAGER] [SQ_OFF] Square-Off Time reached and CARRY_FORWARD is False. Triggering Auto Square-off...")
                    sq_off_triggered = True
                    for acc in self.order_manager.get_accounts():
                        acc_name = acc['name']
                        acc_api = acc['api']
                        try:
                            self.logger.warning(f"[MANAGER] [SQ_OFF] Closing all positions for account '{acc_name}'...")
                            acc_api.close_all_intraday_positions()
                        except Exception as e:
                            self.logger.error(f"[MANAGER] [SQ_OFF] Failed to square off positions for '{acc_name}': {e}")
                
                # 1. Periodically reload instruments (every 5 minutes)
                if now - last_instr_reload > 300:
                    reload_ok = self.config.reload_instruments()
                    if reload_ok:
                        self.logger.info("[MONITOR] Instruments reloaded from disk.")
                        self.config.build_master_index(self.logger)
                        self._sync_bots()
                    elif reload_ok is None:
                        # H4 FIX: reload returned None due to Exception/JSON error during reload —
                        # instruments.json is corrupt or unreadable. Alert the operator.
                        self.logger.error("[MONITOR] instruments.json reload FAILED. Bot running on stale config!")
                        if self.alert_manager:
                            self.alert_manager.send_alert(
                                "⚠️ *instruments.json Reload Failed*\n"
                                "Could not parse updated instruments.json. "
                                "Bot is running on the last valid config.\n"
                                "Please check the file for JSON syntax errors.",
                                header="Config Reload Error"
                            )
                    last_instr_reload = now

                # 2. Cleanup stale open orders (older than 3 mins)
                self._cleanup_stale_orders()

                time.sleep(10)
                
                # 3. Check if threads are alive and clean up
                self.bots = [b for b in self.bots if b.is_alive()]
                
                # If all bots are dead and it's past market hours, we can exit
                current_time = datetime.now(self.config.TIMEZONE).time()
                if not self.bots and current_time > self.config.SQ_OFF_TIME:
                    self.logger.info("All bots have stopped and market is closed. Exiting manager.")
                    self.position_manager.stop()
                    self.position_manager.join(timeout=3)
                    if self.alert_manager:
                        self.alert_manager.send_alert("All instrument threads have completed square-off. Manager exiting.", header="Bot Shutdown")
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("STOPPING ALL BOTS...")
            self.position_manager.stop()
            for bot in self.bots:
                bot.running = False
            
            for bot in self.bots:
                bot.join()
            self.position_manager.join(timeout=3)
            
            if self.alert_manager:
                self.alert_manager.send_alert(f"Manual shutdown triggered by user. All threads joined successfully.", header="Bot Stopped")

            self.logger.info("Shutdown Complete.")

    def _cleanup_stale_orders(self):
        """Cancel unfilled entry orders older than 3 minutes across all accounts"""
        now = datetime.now(self.config.TIMEZONE)
        stale_threshold = now - timedelta(minutes=3)
        
        with self.state.lock:
            active_orders = [
                (oid, data) for oid, data in self.state.orders.items() 
                if str(data.get('status', '')).upper() in ['SUBMITTED', 'PENDING', 'OPEN', 'TRANSIT']
            ]
            
        for oid, data in active_orders:
            try:
                created_str = data.get('created_at')
                if not created_str: continue
                created_dt = datetime.fromisoformat(created_str)
                
                if created_dt < stale_threshold:
                    acc_name = data.get('account')
                    self.logger.warning(f"[STALE ORDER] Cancelling order {oid} for account '{acc_name}' (older than 3m)")
                    
                    # Find correct API Wrapper
                    api = None
                    if acc_name == 'Primary_Account':
                        api = self.primary_api
                    else:
                        for acc in self.order_manager.get_accounts():
                            if acc['name'] == acc_name:
                                api = acc['api']
                                break
                    
                    if api:
                        try:
                            actual_order_resp = api.dhan.get_order_by_id(oid)
                            if actual_order_resp.get('status') == 'success':
                                order_data = actual_order_resp.get('data', [])
                                if order_data and isinstance(order_data, list):
                                    real_status = str(order_data[0].get('orderStatus', '')).upper()
                                    if real_status in ['TRADED', 'CANCELLED', 'REJECTED']:
                                        self.logger.info(f"Order {oid} already {real_status} on broker. Updating local state.")
                                        self.state.update_order_status(oid, real_status)
                                        continue
                        except Exception as e:
                            self.logger.debug(f"Could not verify status for {oid} before cancel: {e}")

                        success = api.cancel_order(oid)
                        if success:
                            self.state.update_order_status(oid, 'CANCELLED_STALE')
                            if self.alert_manager:
                                self.alert_manager.send_alert(f"Cancelled stale order `{oid}` for `{acc_name}`.\nPrice moved too fast.", header="Order Cleanup")
                        else:
                            self.logger.warning(f"Failed to cancel {oid}. May already be filled or cancelled.")
                            
                            # If it failed to cancel, let's mark it as un-cancellable by setting it to a fallback state
                            # so we don't infinitely retry. We will set it to UNKNOWN_STATE to prevent loop.
                            self.state.update_order_status(oid, 'UNKNOWN_STATE')
            except Exception as e:
                self.logger.error(f"Error processing stale order {oid}: {e}")

    def _sync_bots(self):
        """Create and start threads for newly enabled instruments"""
        # M2 FIX: Prune dead bots FIRST so idx_count / stk_count only reflect
        # actually-alive threads. Previously dead bots were counted, causing new
        # instruments to receive incorrectly large offsets and collide on poll timing.
        self.bots = [b for b in self.bots if b.is_alive()]

        active_names = {b.instrument_name for b in self.bots}
        
        # Determine current counts for staggering (using only live bots after pruning above)
        idx_count = len([b for b in self.bots if b.instrument_name in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY']])
        stk_count = len(self.bots) - idx_count
        
        sorted_keys = sorted(self.config.INSTRUMENTS.keys())
        for name in sorted_keys:
            inst_conf = self.config.INSTRUMENTS[name]
            if inst_conf.get('enabled', False) and name not in active_names:
                # Initialize new bot
                bot = InstrumentBot(name, self.config, self.primary_api, self.order_manager, self.state, self.logger, self.alert_manager)
                
                # Assign Stagger Offset
                if name in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY']:
                     offset = 1.0 + (idx_count * 1.0)
                     idx_count += 1
                else:
                     offset = 5.0 + (stk_count * 0.5)
                     stk_count += 1
                
                bot.poll_offset = offset
                bot.start()
                self.bots.append(bot)
                self.logger.info(f"[MONITOR] Started New Bot: {name} [Offset: {offset:.1f}s]")
