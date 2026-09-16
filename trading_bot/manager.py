import os
import time
import logging
from datetime import datetime, timedelta, time as dt_time
import pandas as pd

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
        digest_sent = False
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
                        except RuntimeError as e:
                            self.logger.critical(f"[MANAGER] [SQ_OFF] CRITICAL circuit-breaker failure during square-off for '{acc_name}': {e}")
                            if self.alert_manager:
                                self.alert_manager.send_alert(
                                    f"🚨 *Critical Square-off Failure for {acc_name}*\n"
                                    f"Circuit breaker tripped during EOD square-off: {e}\n"
                                    f"Manual intervention required to verify open positions immediately.",
                                    header="EOD Square-Off Critical Failure"
                                )
                        except Exception as e:
                            self.logger.error(f"[MANAGER] [SQ_OFF] Failed to square off positions for '{acc_name}': {e}")
                
                # 3:35 PM Daily Telegram PnL & Risk Digest trigger
                if not digest_sent and current_time >= dt_time(15, 35):
                    self.logger.info("[MANAGER] 3:35 PM reached. Triggering Daily PnL & Risk Digest...")
                    self.send_daily_digest()
                    digest_sent = True

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
                    if not digest_sent:
                        self.logger.info("[MANAGER] Sending EOD Daily PnL & Risk Digest before shutdown...")
                        self.send_daily_digest()
                        digest_sent = True
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
            
            if not digest_sent:
                try:
                    self.send_daily_digest()
                except Exception as e:
                    self.logger.error(f"[MANAGER] Error sending digest on shutdown: {e}")

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
                            actual_order_resp = api._make_request(api.dhan.get_order_by_id, order_id=oid)
                            if actual_order_resp and actual_order_resp.get('status') == 'success':
                                order_data = actual_order_resp.get('data', [])
                                if isinstance(order_data, list) and order_data:
                                    target_data = order_data[0]
                                elif isinstance(order_data, dict):
                                    target_data = order_data
                                else:
                                    target_data = {}
                                
                                if target_data:
                                    real_status = str(target_data.get('orderStatus', '')).upper()
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

    def generate_daily_digest(self) -> str:
        """Generates a comprehensive Daily PnL, Strategy, and Risk Digest."""
        now_dt = datetime.now(self.config.TIMEZONE)
        today_str = now_dt.strftime("%Y-%m-%d")
        time_str = now_dt.strftime("%H:%M:%S")

        lines = [
            f"📅 *Date:* `{today_str}` | ⏰ *Time:* `{time_str}`",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "💰 *ACCOUNT-WISE REALIZED PnL*"
        ]

        total_realized_pnl = 0.0
        total_unrealized_pnl = 0.0
        total_open_positions = 0

        accounts = self.order_manager.get_accounts() if self.order_manager else []
        if not accounts:
            lines.append("• _No active trading accounts connected._")
        else:
            for acc in accounts:
                acc_name = acc.get('name', 'Unknown')
                acc_api = acc.get('api')
                if not acc_api:
                    continue

                realized_pnl = 0.0
                unrealized_pnl = 0.0
                avail_margin = 0.0
                util_margin = 0.0
                open_pos_count = 0

                try:
                    positions = acc_api.get_positions() or []
                    for pos in positions:
                        rp = float(pos.get('realizedProfit', 0.0) or 0.0)
                        up = float(pos.get('unrealizedProfit', 0.0) or 0.0)
                        realized_pnl += rp
                        unrealized_pnl += up
                        if abs(float(pos.get('netQty', 0.0) or 0.0)) > 0:
                            open_pos_count += 1
                except Exception as e:
                    self.logger.error(f"[DIGEST] Error fetching positions for {acc_name}: {e}")

                try:
                    funds_resp = acc_api._make_request(acc_api.dhan.get_fund_limits)
                    if funds_resp and isinstance(funds_resp.get('data'), dict):
                        fdata = funds_resp['data']
                        avail_margin = float(fdata.get('availMargin', 0.0) or fdata.get('cashWithdrawable', 0.0) or 0.0)
                        util_margin = float(fdata.get('utilisedMargin', 0.0) or 0.0)
                except Exception as e:
                    self.logger.error(f"[DIGEST] Error fetching funds for {acc_name}: {e}")

                total_realized_pnl += realized_pnl
                total_unrealized_pnl += unrealized_pnl
                total_open_positions += open_pos_count

                pnl_icon = "🟢" if realized_pnl >= 0 else "🔴"
                lines.append(
                    f"• *{acc_name}*: {pnl_icon} `₹{realized_pnl:+,.2f}` | Open Pos: `{open_pos_count}`\n"
                    f"  └ *Avail Margin:* `₹{avail_margin:,.2f}` | *Utilized:* `₹{util_margin:,.2f}`"
                )

            total_icon = "🟢" if total_realized_pnl >= 0 else "🔴"
            lines.append(f"\n*Total Realized PnL:* {total_icon} *`₹{total_realized_pnl:+,.2f}`*")
            if total_unrealized_pnl != 0:
                lines.append(f"*Total Unrealized PnL:* `₹{total_unrealized_pnl:+,.2f}`")

        # Today's Executed Trades Breakdown
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("📈 *TODAY'S TRADING ACTIVITY*")
        
        trade_log_file = getattr(self.config, 'TRADE_LOG_CSV', None)
        today_trades_count = 0
        instrument_activity = {}

        if trade_log_file and os.path.exists(trade_log_file):
            try:
                df_trades = pd.read_csv(trade_log_file)
                if 'timestamp' in df_trades.columns:
                    df_trades['date'] = df_trades['timestamp'].astype(str).str.slice(0, 10)
                    today_df = df_trades[df_trades['date'] == today_str]
                    today_trades_count = len(today_df)

                    for _, row in today_df.iterrows():
                        inst = str(row.get('instrument', 'Unknown'))
                        instrument_activity[inst] = instrument_activity.get(inst, 0) + 1

                    lines.append(f"• *Total Events Logged:* `{today_trades_count}`")
                    for inst, cnt in instrument_activity.items():
                        lines.append(f"• *{inst}*: `{cnt}` trade event(s)")
            except Exception as e:
                self.logger.error(f"[DIGEST] Error parsing trade log CSV: {e}")
                lines.append(f"• _Error reading trade log: {e}_")
        else:
            lines.append("• _No trade events recorded in CSV today._")

        # SL and Risk Status
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("🛡️ *RISK & CIRCUIT CONTROLS*")

        aggregated_sls = {}
        for bot in self.bots:
            for strat, accs in getattr(bot, 'daily_sl_counts', {}).items():
                for acc, count in accs.items():
                    key = f"{strat} ({acc})"
                    aggregated_sls[key] = aggregated_sls.get(key, 0) + count

        if aggregated_sls:
            for strat_acc, count in aggregated_sls.items():
                lines.append(f"• *{strat_acc}*: `{count}` SL hit(s)")
        else:
            lines.append("• *Daily SL Hits:* `0` (Zero stop-loss breaches)")

        # Carry-forward positions
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("📦 *CARRY-FORWARD POSITIONS*")
        with self.state.lock:
            open_positions = {k: v for k, v in self.state.positions.items() if abs(float(v.get('qty', 0))) > 0}
        
        if open_positions:
            for k, pos in open_positions.items():
                sym = pos.get('symbol', k)
                action = pos.get('action', 'N/A')
                qty = pos.get('qty', 0)
                entry = pos.get('Entry_Price', 0.0)
                strat = pos.get('strategy', 'Unknown')
                lines.append(f"• `{sym}` ({action} {qty} qty @ ₹{entry:.2f}) | Strat: `{strat}`")
        else:
            lines.append("• _None. 100% Intraday Flat / Zero Overnight Exposure._")

        return "\n".join(lines)

    def send_daily_digest(self):
        """Builds and sends the Daily PnL & Risk Digest via AlertManager."""
        try:
            digest_msg = self.generate_daily_digest()
            if self.alert_manager:
                self.alert_manager.send_alert(digest_msg, header="Daily PnL & Risk Digest")
                self.logger.info("[MANAGER] Daily PnL & Risk Digest successfully sent via AlertManager.")
            else:
                self.logger.info(f"[MANAGER] AlertManager not configured. Digest:\n{digest_msg}")
        except Exception as e:
            self.logger.error(f"[MANAGER] Failed to generate/send daily digest: {e}")

