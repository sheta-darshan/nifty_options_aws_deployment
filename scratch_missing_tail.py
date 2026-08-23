                                item_total_qty += dispatch['acc_qty']
                                item_success = True
                                order_id = resp.get('orderId', 'unknown')
                                
                                self.state.add_order(order_id, {
                                    'order_id': order_id, 'account': acc_name, 'instrument': self.name,
                                    'type': f"{self.config.INSTRUMENTS[self.name]['fno_prefix']}_{leg_type}_{action}", 
                                    'signal': signal, 'leg': leg_type, 'action': action,
                                    'security_id': sec_id, 'symbol': item.get('symbol', sec_id),
                                    'price': ltp, 'qty': dispatch['acc_qty'], 'target_points': opt_tp, 'sl_points': opt_sl,
                                    'status': resp.get('orderStatus', 'SUBMITTED'),
                                    'timestamp': datetime.now(self.config.TIMEZONE).isoformat(),
                                    'exit_mode': exit_mode,
                                    'spot_sl_price': spot_sl_price,
                                    'spot_target_price': spot_target_price,
                                    'opt_sl_price': opt_sl_price if local_exit_monitoring and exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else 0.0,
                                    'opt_target_price': opt_target_price if local_exit_monitoring and exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else 0.0,
                                    'Breakeven_Mult': breakeven_mult,
                                    'Initial_SL_Points': initial_sl_points,
                                    'Breakeven_Triggered': False
                                })

                                # For SWING exit mode, track the position in state
                                if local_exit_monitoring:
                                    with self.state.lock:
                                        self.state.positions[str(sec_id)] = {
                                            'security_id': str(sec_id),
                                            'symbol': item.get('symbol', sec_id),
                                            'instrument': self.name,
                                            'account': acc_name,
                                            'strategy': clean_source,
                                            'leg': leg_type,
                                            'action': action,
                                            'qty': dispatch['acc_qty'],
                                            'product_type': dispatch['inst_product_type'],
                                            'exchange_segment': opt_seg,
                                            'exit_mode': exit_mode,
                                            'spot_sl_price': spot_sl_price,
                                            'spot_target_price': spot_target_price,
                                            'spot_initial_sl': spot_sl_price,
                                            'spot_mfe': self.df_spot['close'].iloc[-1] if self.df_spot is not None else ltp,
                                            'spot_atr': atr_val,
                                            'Entry_Spot': self.df_spot['close'].iloc[-1] if self.df_spot is not None else ltp,
                                            'Entry_Price': ltp,
                                            'order_id': order_id,
                                            'created_at': datetime.now(self.config.TIMEZONE).isoformat(),
                                            'opt_sl_price': opt_sl_price,
                                            'opt_target_price': opt_target_price,
                                            'opt_initial_sl': opt_sl_price,
                                            'opt_mfe': ltp,
                                            'opt_atr': contract_atr_val,
                                            'Breakeven_Mult': breakeven_mult,
                                            'Initial_SL_Points': initial_sl_points,
                                            'Breakeven_Triggered': False
                                        }
                                    self.state.save_state()

                                log_trade_event({
                                    'timestamp': datetime.now(self.config.TIMEZONE).isoformat(),
                                    'instrument': self.name, 'signal': signal, 'leg': leg_type, 'action': action,
                                    'symbol': item.get('symbol', sec_id), 'security_id': sec_id,
                                    'price': ltp, 'qty': dispatch['acc_qty'], 'atr': atr_val, 'delta': delta,
                                    'target_points': opt_tp, 'sl_points': opt_sl, 'order_id': order_id,
                                    'status': resp.get('orderStatus', 'SUBMITTED'), 'account': acc_name
                                }, self.config.TRADE_LOG_CSV, self.logger)
                        except Exception as e:
                            self.logger.error(f"[{self.name}] Async dispatch result error for '{acc_name}': {e}")
                
            if item_success:
                if local_exit_monitoring:
                    abs_tp = opt_target_price if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else spot_target_price
                    abs_sl = opt_sl_price if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else spot_sl_price
                    successful_trades.append({
                        'symbol': item.get('symbol', sec_id),
                        'price': ltp,
                        'qty': item_total_qty,
                        'sl_pts': abs(opt_sl_price - ltp) if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else (abs(spot_sl_price - self.df_spot['close'].iloc[-1]) if self.df_spot is not None else 0.0),
                        'tp_pts': abs(opt_target_price - ltp) if exit_mode in ["SWING_CONTRACT", "POINTS", "ATR"] else (abs(spot_target_price - self.df_spot['close'].iloc[-1]) if self.df_spot is not None else 0.0),
                        'tr_pts': 0.0,
                        'abs_sl': abs_sl,
                        'abs_tp': abs_tp,
                        'is_swing': True,
                        'exit_mode': exit_mode
                    })
                else:
                    # Calculate absolute target prices natively used by Dhan API for Super Orders
                    if action == 'BUY':
                        abs_tp = ltp + opt_tp
                        abs_sl = max(0.05, ltp - opt_sl)
                    else: # SELL
                        abs_tp = max(0.05, ltp - opt_tp)
                        abs_sl = ltp + opt_sl

                    successful_trades.append({
                        'symbol': item.get('symbol', sec_id),
                        'price': ltp,
                        'qty': item_total_qty,
                        'sl_pts': opt_sl,
                        'tp_pts': opt_tp,
                        'tr_pts': opt_trail,
                        'abs_sl': abs_sl,
                        'abs_tp': abs_tp,
                        'is_swing': False,
                        'exit_mode': exit_mode
                    })
                
            time.sleep(0.2)
        
        # --- SEND TELEGRAM NOTIFICATION ---
        if successful_trades and self.alert_manager:
            acc_list = sorted(list(success_accounts))
            acc_str = f"{acc_list[0]} (+{len(acc_list)-1} others)" if len(acc_list) > 1 else acc_list[0]
            
            # Create a combined message for all successful items in this batch
            trade_reports = []
            for trade in successful_trades:
                if trade.get('is_swing'):
                    mode_label = trade.get('exit_mode', 'SWING')
                    report = (
                        f"≡ƒôÄ *Symbol:* `{trade['symbol']}`\n"
                        f"≡ƒÆ░ *Entry Price:* {trade['price']:.2f} (Ref) | *Total Qty:* {trade['qty']}\n"
                        f"≡ƒ¢í∩╕Å *SL:* {trade['abs_sl']:.2f} | *TP:* {trade['abs_tp']:.2f} ({mode_label} mode)"
                    )
                else:
                    report = (
                        f"≡ƒôÄ *Symbol:* `{trade['symbol']}`\n"
                        f"≡ƒÆ░ *Entry Price:* {trade['price']:.2f} (Ref) | *Total Qty:* {trade['qty']}\n"
                        f"≡ƒ¢í∩╕Å *SL:* {trade['abs_sl']:.2f} ({trade['sl_pts']:.1f} pts) | *TP:* {trade['abs_tp']:.2f} ({trade['tp_pts']:.1f} pts)\n"
                        f"≡ƒôê *Trailing Jump:* {trade['tr_pts']:.1f} pts"
                    )
                trade_reports.append(report)
            
            trades_msg = "\n\n".join(trade_reports)
            full_msg = (
                f"{trades_msg}\n\n"
                f"≡ƒôí *Signal:* {signal.upper()} ΓåÆ ≡ƒôé *Action:* {action} | *Leg:* {leg_type}\n"
                f"≡ƒæñ *Accounts:* {acc_str}\n"
                f"≡ƒôè *Source:* {source}"
            )
            self.alert_manager.send_alert(full_msg, header="Trade Executed")
            
        return success_accounts

    def _local_monitoring_loop(self):
        """High-frequency python-side monitoring loop for Spot-based exits."""
        self.logger.info(f"[{self.name}] Starting local stop monitoring loop...")
        while self.running:
            try:
                # 1. Check if we have active positions in self.state.positions
                # Filter to positions of this instrument that have exit_mode == "SWING" or "SWING_CONTRACT"
                with self.state.lock:
                    swing_positions = {
                        sec_id: pos for sec_id, pos in self.state.positions.items()
                        if pos.get('instrument') == self.name
                    }
                
                if not swing_positions:
                    time.sleep(5)
                    continue
                
                # 2. Verify against broker actual positions to prevent double execution or sync issues
                accounts = self.order_manager.get_accounts()
                for acc in accounts:
                    acc_name = acc['name']
                    acc_api = acc['api']
                    
                    try:
                        pos_list = self.order_manager.position_manager.get_cached_positions(acc_name)
                        if not pos_list:
                            continue
                        
                        # Find open positions for this instrument in this account
                        open_broker_positions = {}
                        for pos in pos_list:
                            net_qty = safe_int(pos.get('netQty', 0))
                            if net_qty != 0:
                                open_broker_positions[str(pos.get('securityId'))] = pos
                        
                        # Check each swing position
                        for sec_id, position in list(swing_positions.items()):
                            if position.get('account') != acc_name:
                                continue
                                
                            if sec_id not in open_broker_positions:
                                # Position already closed on broker or not open yet. Clean up local state if created > 2 mins ago to avoid race conditions on entry
                                created_str = position.get('created_at', position.get('timestamp'))
                                if created_str:
                                    created_dt = datetime.fromisoformat(created_str)
                                    if (datetime.now(self.config.TIMEZONE) - created_dt).total_seconds() > 120:
                                        self.logger.info(f"[{self.name}] Cleaning up stale local position state for {sec_id}")
                                        with self.state.lock:
                                            self.state.positions.pop(sec_id, None)
                                        self.state.save_state()
                                continue
                                
                            # If it is open, check the exit mode logic
                            pos_exit_mode = position.get('exit_mode', 'SWING')
                            if pos_exit_mode in ['SWING_CONTRACT', 'POINTS', 'ATR']:
                                opt_seg = position.get('exchange_segment', 'NSE_FNO')
                                contract_ltp = 0.0
                                try:
                                    resp = self.data_api._make_request(self.data_api.dhan.ohlc_data, securities={opt_seg: [int(sec_id)]})
                                    if resp:
                                        d = resp.get('data', {}).get(opt_seg, {}).get(str(sec_id), {})
                                        contract_ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
                                except Exception as e:
                                    self.logger.error(f"[{self.name}] Error fetching Contract LTP in monitor for {sec_id}: {e}")
                                
                                if contract_ltp <= 0:
                                    contract_ltp = float(open_broker_positions[sec_id].get('lastPrice', 0) or open_broker_positions[sec_id].get('ltp', 0))
                                    
                                if contract_ltp <= 0:
                                    continue
                                    
                                action = position.get('action')
                                if pos_exit_mode == 'POINTS':
                                    trail_jump = position.get('opt_atr', 0.0) # For POINTS mode, opt_atr stores raw trail_points
                                else:
                                    trail_mult = self.config.INSTRUMENTS[self.name].get('trailing_mult_sell' if action == 'SELL' else 'trailing_mult_buy', 1.6)
                                    opt_atr = position.get('opt_atr', 1.0)
                                    trail_jump = opt_atr * trail_mult
                                
                                # 1. Check Breakeven Trigger
                                updated = False
                                hit_sl = False
                                hit_target = False
                                with self.state.lock:
                                    be_mult = position.get("Breakeven_Mult", 0.0)
                                    if be_mult > 0.0 and not position.get("Breakeven_Triggered", False) and position.get("Initial_SL_Points", 0.0) > 0.0:
                                        if action == 'BUY':
                                            trigger_level = position["Entry_Price"] + (position["Initial_SL_Points"] * be_mult)
                                            if contract_ltp >= trigger_level:
                                                position["opt_sl_price"] = max(position["opt_sl_price"], position["Entry_Price"])
                                                position["Breakeven_Triggered"] = True
                                                self.logger.info(f"[{self.name}] [BREAKEVEN SL TRIGGER] Moved SL to entry: {position['opt_sl_price']:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                updated = True
                                        else: # SELL
                                            trigger_level = position["Entry_Price"] - (position["Initial_SL_Points"] * be_mult)
                                            if contract_ltp <= trigger_level:
                                                position["opt_sl_price"] = min(position["opt_sl_price"], position["Entry_Price"])
                                                position["Breakeven_Triggered"] = True
                                                self.logger.info(f"[{self.name}] [BREAKEVEN SL TRIGGER] Moved SL to entry: {position['opt_sl_price']:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                updated = True

                                    if action == 'BUY':
                                        if contract_ltp > position.get('opt_mfe', position.get('Entry_Price', contract_ltp)):
                                            position['opt_mfe'] = contract_ltp
                                            updated = True
                                        if trail_jump > 0 and contract_ltp > position.get('Entry_Price', contract_ltp):
                                            steps = int((contract_ltp - position.get('Entry_Price', contract_ltp)) / trail_jump)
                                            if steps >= 1:
                                                new_sl = position.get('opt_initial_sl', position.get('opt_sl_price')) + (steps * trail_jump)
                                                if new_sl > position.get('opt_sl_price'):
                                                    position['opt_sl_price'] = new_sl
                                                    self.logger.info(f"[{self.name}] [TRAILING SL UPDATE] New Contract SL: {new_sl:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                    updated = True
                                                    
                                        hit_sl = (contract_ltp <= position.get('opt_sl_price'))
                                        hit_target = (contract_ltp >= position.get('opt_target_price'))
                                    else: # SELL
                                        if contract_ltp < position.get('opt_mfe', position.get('Entry_Price', contract_ltp)):
                                            position['opt_mfe'] = contract_ltp
                                            updated = True
                                        if trail_jump > 0 and contract_ltp < position.get('Entry_Price', contract_ltp):
                                            steps = int((position.get('Entry_Price', contract_ltp) - contract_ltp) / trail_jump)
                                            if steps >= 1:
                                                new_sl = position.get('opt_initial_sl', position.get('opt_sl_price')) - (steps * trail_jump)
                                                if new_sl < position.get('opt_sl_price'):
                                                    position['opt_sl_price'] = new_sl
                                                    self.logger.info(f"[{self.name}] [TRAILING SL UPDATE] New Contract SL: {new_sl:.2f} (Contract LTP: {contract_ltp:.2f})")
                                                    updated = True
                                                    
                                        hit_sl = (contract_ltp >= position.get('opt_sl_price'))
                                        hit_target = (contract_ltp <= position.get('opt_target_price'))
                                
                                if updated:
                                    self.state.save_state()
                                    
                                current_ltp_ref = contract_ltp
                                sl_price_ref = position.get('opt_sl_price')
                                target_price_ref = position.get('opt_target_price')
                                mode_label = "CONTRACT"
                                
                            else: # SWING (Spot-based)
                                spot_sec_id = self.config.INSTRUMENTS[self.name]['security_id']
                                spot_seg = 'IDX_I' if self.TYPE != 'STOCK' else 'NSE_EQ'
                                spot_ltp = 0.0
                                try:
                                    resp = self.data_api._make_request(self.data_api.dhan.ohlc_data, securities={spot_seg: [int(spot_sec_id)]})
                                    if resp:
                                        d = resp.get('data', {}).get(spot_seg, {}).get(str(spot_sec_id), {})
                                        spot_ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
                                except Exception as e:
                                    self.logger.error(f"[{self.name}] Error fetching Spot LTP in monitor: {e}")
                                    
                                if spot_ltp <= 0:
                                    continue
                                    
                                # Determine Spot Direction
                                leg_type = position.get('leg')
                                action = position.get('action')
                                spot_is_bearish = (leg_type == "PE" and action == "BUY") or (leg_type == "CE" and action == "SELL") or (leg_type == "STOCK" and action == "SELL")
                                
                                # Trailing SL update logic
                                trail_mult = self.config.INSTRUMENTS[self.name].get('trailing_mult_sell' if action == 'SELL' else 'trailing_mult_buy', 1.6)
                                spot_atr = position.get('spot_atr', 10.0)
                                trail_jump = spot_atr * trail_mult
                                
                                updated = False
                                hit_sl = False
                                hit_target = False
                                with self.state.lock:
                                    if not spot_is_bearish:
                                        # Trailing check
                                        if spot_ltp > position['spot_mfe']:
                                            position['spot_mfe'] = spot_ltp
                                            updated = True
                                        if trail_jump > 0 and spot_ltp > position['Entry_Spot']:
                                            steps = int((spot_ltp - position['Entry_Spot']) / trail_jump)
                                            if steps >= 1:
                                                new_sl = position['spot_initial_sl'] + (steps * trail_jump)
                                                if new_sl > position['spot_sl_price']:
                                                    position['spot_sl_price'] = new_sl
                                                    self.logger.info(f"[{self.name}] [TRAILING SL UPDATE] New SL: {new_sl:.2f} (Spot LTP: {spot_ltp:.2f})")
                                                    updated = True
                                                    
                                        # Check exit conditions
                                        hit_sl = (spot_ltp <= position['spot_sl_price'])
                                        hit_target = (spot_ltp >= position['spot_target_price'])
                                    else:
                                        # Trailing check
                                        if spot_ltp < position['spot_mfe']:
                                            position['spot_mfe'] = spot_ltp
                                            updated = True
                                        if trail_jump > 0 and spot_ltp < position['Entry_Spot']:
                                            steps = int((position['Entry_Spot'] - spot_ltp) / trail_jump)
                                            if steps >= 1:
                                                new_sl = position['spot_initial_sl'] - (steps * trail_jump)
                                                if new_sl < position['spot_sl_price']:
                                                    position['spot_sl_price'] = new_sl
                                                    self.logger.info(f"[{self.name}] [TRAILING SL UPDATE] New SL: {new_sl:.2f} (Spot LTP: {spot_ltp:.2f})")
                                                    updated = True
                                                    
                                        # Check exit conditions
                                        hit_sl = (spot_ltp >= position['spot_sl_price'])
                                        hit_target = (spot_ltp <= position['spot_target_price'])
                                    
                                    sl_price_ref = position['spot_sl_price']
                                    target_price_ref = position['spot_target_price']
                                
                                if updated:
                                    self.state.save_state()
                                    
                                current_ltp_ref = spot_ltp
                                mode_label = "SPOT"
                                
                            if hit_sl or hit_target:
                                reason = "StopLoss" if hit_sl else "Target"
                                sym = open_broker_positions[sec_id].get('tradingSymbol', sec_id)
                                net_qty = safe_int(open_broker_positions[sec_id].get('netQty', 0))
                                abs_qty = abs(net_qty)
                                
                                self.logger.warning(f"[{self.name}] [{mode_label} EXIT TRIGGER] {sym} triggers {reason} ({mode_label} LTP: {current_ltp_ref:.2f}, SL: {sl_price_ref:.2f}, Target: {target_price_ref:.2f})")
                                
                                # Cancel pending orders for this contract
                                try:
                                    pending = acc_api.get_pending_orders()
                                    pos_pending = [o for o in pending if str(o.get('securityId')) == sec_id]
                                    for o in pos_pending:
                                        acc_api.cancel_order(o.get('orderId'))
                                except Exception as e:
                                    self.logger.error(f"[{self.name}] Error cancelling pending orders on exit: {e}")
                                    
                                # Close position with Market order
                                close_action = 'SELL' if net_qty > 0 else 'BUY'
                                exch = open_broker_positions[sec_id].get('exchangeSegment', 'NSE_FNO')
                                product = open_broker_positions[sec_id].get('productType', 'MARGIN')
                                
                                resp = acc_api.place_order(
                                    security_id=sec_id,
                                    transaction_type=close_action,
                                    quantity=abs_qty,
                                    exchange_segment=exch,
                                    product_type=product,
                                    order_type="MARKET",
                                    price=0.0,
                                    should_slice=(exch in ['NSE_FNO', 'BSE_FNO'])
                                )
                                
                                if resp:
                                    self.logger.warning(f"[{self.name}] Position closed successfully: {resp}")
                                    with self.state.lock:
                                        self.state.positions.pop(sec_id, None)
                                    self.state.save_state()
                                    
                                    if self.alert_manager:
                                        strat_name = position.get('strategy', 'Unknown')
                                        msg = (
                                            f"≡ƒÜ¿ *Position Closed:* `{sym}`\n"
                                            f"≡ƒôè *Strategy:* `{strat_name}`\n"
                                            f"≡ƒôè *Reason:* {reason} ({mode_label} LTP: {current_ltp_ref:.2f})\n"
                                            f"≡ƒ¢í∩╕Å *Levels:* SL: {sl_price_ref:.2f} | Target: {target_price_ref:.2f}\n"
                                            f"≡ƒæñ *Account:* {acc_name}"
                                        )
                                        self.alert_manager.send_alert(msg, header="Trade Closed")
                                        
                    except Exception as acc_err:
                        self.logger.error(f"[{self.name}] Error checking positions for {acc_name} in loop: {acc_err}")
                        
            except Exception as loop_err:
                self.logger.error(f"[{self.name}] Error in local stop monitor loop: {loop_err}")
                
            time.sleep(5)
# ========== MAIN TRADING LOOP ==========
# LEGACY LOOP (UNUSED - KEPT FOR REFERENCE)
'''
def main_loop(config: Config, logger):
    """Main trading loop for 5-minute Strategy"""
    logger.info("=" * 60)
    logger.info("Starting NIFTY 50 Options Bot (Supertrend + ADX + StochRSI)")
    logger.info(f"Timezone: {config.TIMEZONE.zone}")
    logger.info(f"Trading Hours: {config.RUN_START} - {config.RUN_END}")
    logger.info(f"Timeframe: {config.TIMEFRAME} (Direct Fetch {config.DATA_INTERVAL}min)")
    logger.info("=" * 60)
    
    # Log LEG_MODE configuration
    logger.info("=" * 60)
    logger.info("TRADING DIRECTION MODE CONFIGURATION")
    logger.info(f"  Active Mode: {config.LEG_MODE}")
    logger.info("=" * 60)
    flush_logs(logger)
    
    # Initialize API wrapper
    api = DhanAPIWrapper(config.CLIENT_ID, config.API_TOKEN, config, logger)
    
    # Initialize state management
    state = TradeState(config.ORDER_STATE_FILE, logger)
    
    # Trading state
    last_processed_candle_time = None
    trades_today_count = 0
    last_data_fetch = None
    
    # Initial Alignment (Wait for next minute start)
    startup_now = datetime.now(config.TIMEZONE)
    if startup_now.second > 10:
        logger.info(f"Started at {startup_now.strftime('%H:%M:%S')}. Aligning...")
        wait_for_next_candle(startup_now, config.POLL_INTERVAL_SECS, logger, offset_seconds=2)

    while True:
        try:
            now = datetime.now(config.TIMEZONE)
            current_time_only = now.time()
            
            # Check market hours
            if not (config.RUN_START <= current_time_only <= config.RUN_END):
                # Square Off Time Check
                if current_time_only >= config.SQ_OFF_TIME:
                    logger.info("Square Off Time Reached. Exiting trading session.")
                    logger.warning("[SQ_OFF] Triggering Auto Square-off...")
                    # api.close_all_intraday_positions() # temprory not closing open positions
                    break
                    
                if current_time_only > config.RUN_END:
                    logger.info("Market entry window closed. Waiting...")
                    time.sleep(60)
                    continue
                
                logger.debug(f"Outside trading hours. Waiting... ({current_time_only})")
                time.sleep(30)
                continue
            
            # =========================================================
            # MULTI-INDEX LOOP
            # =========================================================
            logger.info(f"--- Processing Candle {now.strftime('%H:%M')} ---")
            
            for inst_name, inst_config in config.INSTRUMENTS.items():
                if not inst_config.get('enabled', False):
                    continue
                    
                security_id = inst_config['security_id']
                prefix = inst_config['fno_prefix']
                
                # logger.info(f"[{prefix}] Fetching data...")
                
                # ===== FETCH MARKET DATA =====
                # Fetch 5-min data directly
                df = fetch_candle_with_retry(api, security_id, config, logger, interval=config.DATA_INTERVAL)
                
                if df is None or df.empty:
                    logger.warning(f"[{prefix}] Failed to fetch market data.")
                    continue
                
                # ===== PROCESS & GENERATE SIGNALS =====
                df_5min = process_market_data(df, config, logger, instrument_name=inst_name)
                
                if df_5min.empty:
                    # logger.info(f"[{prefix}] Waiting for more data...")
                    continue
                    
                # Get latest complete candle signal
                signal, atr_val = get_latest_signal(df_5min, logger)
                current_candle_time = df_5min.index[-1]
                
                logger.info(f"[{prefix}] Time: {current_candle_time.strftime('%H:%M')} | Signal: {signal} | Close: {df_5min['close'].iloc[-1]}")
                
                 # Check if this candle is new and hasn't been processed
                 # We need a tracker per instrument now. 
                 # Since 'last_processed_candle_time' was single variable, we need a dict.
                 # Initializing it dynamically if not present in state
                
                # Hack: Store last processed time in a local dict in main_loop scope
                # But 'state' object is persistent. Let's rely on transient dict for runtime loop
                if not hasattr(main_loop, 'processed_candles'):
                     main_loop.processed_candles = {}
                
                last_time = main_loop.processed_candles.get(prefix)
                is_new_candle = (last_time != current_candle_time)
                
                if is_new_candle:
                    # Update tracker
                    main_loop.processed_candles[prefix] = current_candle_time
                    
                    if signal:
                        logger.info(f"!!! [{prefix}] SIGNAL DETECTED: {signal.upper()} !!!")
                        
                        # Validate Trade Constraints
                        if trades_today_count >= config.MAX_TRADES_PER_DAY:
                            logger.warning("Max trades reached. Ignoring signal.")
                        else:
                            active_orders = count_active_option_orders(api.get_positions(), logger)
                            if active_orders >= config.MAX_ACTIVE_ORDERS:
                                logger.warning("Max active orders reached. Ignoring signal.")
                            else:
                                # ===== EXECUTE TRADE =====
                                logger.info(f"Executing {signal.upper()} trade for {prefix}...")
                                
                                # Check for Strategy 20 (Math Calendar Spread)
                                if inst_config.get("strategy_type") == "CALENDAR_SPREAD" or getattr(config, "ENABLE_STRATEGY_20", False):
                                    spot_close = float(df_5min['close'].iloc[-1])
                                    regime_stance = getattr(df_5min, 'regime', ['PUT_CALENDAR'])[-1] if hasattr(df_5min, 'regime') else ("PUT_CALENDAR" if signal == "SELL" else "CALL_CALENDAR")
                                    
                                    logger.info(f"[{prefix}] Executing Strategy 20 Calendar Spread: Stance={regime_stance}, Spot={spot_close}")
                                    if inst_config.get("trade_both_sides", 0) == 1:
                                        logger.info(f"[{prefix}] DUAL STANCE ENABLED: Resolving BOTH Call & Put Calendar Spreads...")
                                        call_legs = choose_calendar_spread_v2(api, spot_close, stance="CALL_CALENDAR", instrument_config=inst_config)
                                        put_legs = choose_calendar_spread_v2(api, spot_close, stance="PUT_CALENDAR", instrument_config=inst_config)
                                        cal_legs = (call_legs or []) + (put_legs or [])
                                    else:
                                        cal_legs = choose_calendar_spread_v2(api, spot_close, stance=regime_stance, instrument_config=inst_config)
                                    
                                    if cal_legs:
                                        # Pre-trade margin check via Dhan API v2
                                        scrip_list = [
                                            {
                                                "exchangeSegment": inst_config.get("option_segment", "NSE_FNO"),
                                                "transactionType": leg["action"],
                                                "quantity": leg["quantity"],
                                                "productType": "MARGIN",
                                                "securityId": str(leg["security_id"]),
                                                "price": float(leg["ltp"])
                                            } for leg in cal_legs
                                        ]
                                        margin_resp = api.calculate_multi_order_margin(scrip_list)
                                        
                                        # Staged Order Execution: Stage 1 = Long Monthly FIRST, Stage 2 = Short Weekly SECOND
                                        long_legs = [l for l in cal_legs if l["action"] == "BUY"]
                                        short_legs = [l for l in cal_legs if l["action"] == "SELL"]
                                        
                                        # Execute Long Legs First
                                        for leg in long_legs:
                                            resp = api.place_order(
                                                security_id=leg["security_id"],
                                                transaction_type="BUY",
                                                quantity=leg["quantity"],
                                                exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                                                product_type="MARGIN",
                                                order_type="MARKET",
                                                price=leg["ltp"]
                                            )
                                            logger.info(f"[{prefix}] Stage 1 Long Leg Order Executed: {leg['tag']} -> {resp}")
                                            
                                        # Execute Short Legs Second
                                        for leg in short_legs:
                                            resp = api.place_order(
                                                security_id=leg["security_id"],
                                                transaction_type="SELL",
                                                quantity=leg["quantity"],
                                                exchange_segment=inst_config.get("option_segment", "NSE_FNO"),
                                                product_type="MARGIN",
                                                order_type="MARKET",
                                                price=leg["ltp"]
                                            )
                                            logger.info(f"[{prefix}] Stage 2 Short Leg Order Executed: {leg['tag']} -> {resp}")
                                            
                                        continue

                                # 1. Select Options (Pass instrument config)
                                ce_items, pe_items = choose_option_instruments(api, signal, inst_config, logger)
                                
                                if ce_items and pe_items:
                                    # 2. Determine Action
                                    ce_action, pe_action = get_trade_actions(signal, config, logger)
                                    
                                    # Helper to Place BO (Updated for dynamic delta)
                                    def place_leg_with_delta(item, action, leg_tag):
                                        if not action: return None
                                        
                                        sec_id = item['id']
                                        leg_delta = item.get('delta')
                                        
                                        # Fallback to default check
                                        used_delta = abs(leg_delta) if leg_delta is not None and leg_delta != 0 else config.OPTION_DELTA
                                            
                                        # Calculate Dynamic Points
                                        # Spot Points
                                        spot_sl = atr_val * config.ATR_SL_MULTIPLIER
                                        spot_tp = atr_val * config.ATR_TP_MULTIPLIER
                                        spot_trail = atr_val * config.ATR_TRAIL_MULTIPLIER
                                        
                                        # Option Points (Refined)
                                        opt_sl_points = round(spot_sl * used_delta, 1)
                                        
                                        # BUY: Fixed Profit Target Logic
                                        if action == "BUY":
                                            lot_size = inst_config.get('lot_size', 1)
                                            target_per_lot = inst_config.get('profit_target_per_lot', config.PROFIT_TARGET_PER_LOT)
                                            opt_tp_points = round(target_per_lot / lot_size, 1)
                                            # Keep jump consistent with new lower TP? Or keep purely ATR?
                                            # Using original logic for Jump:
                                            opt_jump_points = round(spot_trail * used_delta, 1)
                                            logger.info(f"[{leg_tag}] BUY Target: {target_per_lot} INR / {lot_size} Qty = {opt_tp_points} pts")
                                        else:
                                            # SELL: Original ATR Logic
                                            opt_tp_points = round(spot_tp * used_delta, 1)
                                            opt_jump_points = round(spot_trail * used_delta, 1)

                                        logger.info(f"[{leg_tag}] Delta: {used_delta:.2f} | SL: {opt_sl_points} | TP: {opt_tp_points} | Trail: {opt_jump_points}")
    
                                        # Quick LTP fetch for Reference
                                        # Use generic fetch with dynamic segment
                                        opt_segment = inst_config.get('option_segment', 'NSE_FNO')
                                        ltp_resp = api._make_request(api.dhan.ohlc_data, securities={opt_segment: [int(sec_id)]})
                                        ltp = 0.0
                                        if ltp_resp and 'data' in ltp_resp:
                                            # ... parsing ...
                                            try:
                                                d = ltp_resp['data']
                                                if opt_segment in d: d = d[opt_segment]
                                                if str(sec_id) in d: d = d[str(sec_id)]
                                                ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
                                            except: pass
                                        
                                        if ltp <= 0:
                                            # Emergency fallback: Historical
                                            h_df = api.get_historical_data(sec_id, 1, opt_segment, 'OPTIDX')
                                            if h_df is not None and not h_df.empty:
                                                ltp = float(h_df.iloc[-1]['close'])
                                        
                                        if ltp <= 0:
                                            logger.error(f"[{leg_tag}] Could not get Price for {sec_id}. Skipping this leg.")
                                            return None
                                            
                                        # Recalculate Quantity based on Split Lots
                                        base_lot_size = inst_config.get('lot_size', 1)
                                        if action == 'BUY':
                                            num_lots = inst_config.get('num_lots_buy', 1)
                                        else:
                                            num_lots = inst_config.get('num_lots_sell', 1)
                                            
                                        # Recalculate Quantity based on Split Lots Logic
                                        trade_quantity = base_lot_size * num_lots
                                        
                                        resp = api.place_entry_order(
                                            security_id=sec_id,
                                            transaction_type=action,
                                            quantity=trade_quantity, # Use Calculated Total Quantity
                                            order_type="MARKET",
                                            price=ltp, # Reference for BO calc
                                            target_points=opt_tp_points,
                                            sl_points=opt_sl_points,
                                            trailing_jump=opt_jump_points,
                                            product_type="MARGIN",
                                            exchange_segment=opt_segment
                                        )
                                        
                                        # LOGGING RESTORED
                                        if resp:
                                            # 1. Update State
                                            order_id = resp.get('orderId', 'unknown')
                                            state.add_order(order_id, {
                                                'type': f"{prefix}_{leg_tag}_{action}", # Prefix with Instrument
                                                'security_id': sec_id,
                                                'symbol': item.get('symbol', 'unknown'),
                                                'price': ltp,
                                                'status': resp.get('orderStatus', 'SUBMITTED'),
                                                'target_points': opt_tp_points,
                                                'sl_points': opt_sl_points,
                                                'timestamp': datetime.now(config.TIMEZONE).isoformat()
                                            })
                                            
                                            # 2. Log to CSV
                                            log_trade_event({
                                                'timestamp': datetime.now(config.TIMEZONE).isoformat(),
                                                'instrument': prefix, # Add Instrument column
                                                'signal': signal,
                                                'leg': leg_tag,
                                                'action': action,
                                                'symbol': item.get('symbol', sec_id),
                                                'security_id': sec_id,
                                                'price': ltp,
                                                'order_id': order_id,
                                                'status': resp.get('orderStatus', 'SUBMITTED')
                                            }, config.TRADE_LOG_CSV, logger)
    
                                        return resp
    
                                    # Execute CE Orders
                                    if ce_action:
                                        logger.info(f"[EXECUTION] Processing {len(ce_items)} CE Orders for {prefix}...")
                                        for i, item in enumerate(ce_items):
                                            logger.info(f"  >> Order {i+1}/{len(ce_items)}: {item.get('symbol', item['id'])}")
                                            place_leg_with_delta(item, ce_action, f"CE_{i+1}")
                                            time.sleep(0.5)
                                        
                                    # Execute PE Orders
                                    if pe_action:
                                        logger.info(f"[EXECUTION] Processing {len(pe_items)} PE Orders for {prefix}...")
                                        for i, item in enumerate(pe_items):
                                            logger.info(f"  >> Order {i+1}/{len(pe_items)}: {item.get('symbol', item['id'])}")
                                            place_leg_with_delta(item, pe_action, f"PE_{i+1}")
                                            time.sleep(0.5)
                                        
                                    trades_today_count += 1
                                    logger.info(f"Trades Today: {trades_today_count}")

            # ===== WAIT ======
            # Wait for next minute to check again (we resample 1-min data, so we check every minute)
            # This aligns the global cycle
            wait_for_next_candle(now, config.POLL_INTERVAL_SECS, logger)
        
        except KeyboardInterrupt:
            logger.info("Exiting...")
            break
        
        except Exception as e:
            logger.exception(f"Loop Error: {e}")
            time.sleep(10)
'''

