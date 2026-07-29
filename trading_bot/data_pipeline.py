import os
import json
import time
import re
import threading
import pytz
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from trading_bot.config import Config
from trading_bot.api_wrapper import DhanAPIWrapper, safe_int

# ========== STRATEGY & SIGNAL LOGIC ==========

def process_market_data(df: pd.DataFrame, config: Config, logger, instrument_name=None) -> pd.DataFrame:
    """
    1. Validate Data (1-min)
    2. Resample to 5m and 15m to calculate Indicators
    3. Shift MTF constraints by true-completion time to avoid Look-Ahead Bias
    4. Generate Signals on active 1-minute dataframe
    """
    if df is None or df.empty:
        return pd.DataFrame()
        
    df = df.copy()
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    elif not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception as e:
            logger.error(f"[ERROR] Could not convert index to DatetimeIndex: {e}")
            return pd.DataFrame()

    if df.index.tz is None and not (config.__class__.__name__ == 'BacktestConfig'):
        df.index = df.index.tz_localize('UTC').tz_convert(config.TIMEZONE)

    # Drop incomplete current minute candle if in live trading mode
    if not (config.__class__.__name__ == 'BacktestConfig') and not df.empty:
        last_row_time = df.index[-1]
        if last_row_time.tzinfo is None:
            last_row_time_local = last_row_time.tz_localize('UTC').tz_convert(config.TIMEZONE).tz_localize(None)
        else:
            last_row_time_local = last_row_time.tz_convert(config.TIMEZONE).tz_localize(None)
            
        current_minute = datetime.now(config.TIMEZONE).replace(second=0, microsecond=0, tzinfo=None)
        
        if last_row_time_local >= current_minute:
            logger.info(f"[{instrument_name or 'SYSTEM'}] [DATA] Last candle {last_row_time_local} is incomplete (current minute {current_minute}). Dropping it to align indicators with completed candle backtest.")
            df = df.iloc[:-1]

    import strategies as strat
    
    # 1. Determine all active strategies dynamically using the registry
    active_strategies = []
    for s in strat.STRATEGY_REGISTRY.keys():
        if getattr(config, f"ENABLE_{s.upper()}", False):
            active_strategies.append(s)
            
    if not active_strategies:
        active_strategies = ["Strategy_3"]  # Fallback

    # Create merged DataFrame initialized with 0 signals
    merged_df = df.copy()
    merged_df['Signal'] = 0
    merged_df['Signal_Source'] = "None"
    merged_df['Exit_Long'] = False
    merged_df['Exit_Short'] = False
    merged_df['Exit_Source'] = "None"
    
    try:
        for s_name in active_strategies:
            # Load default parameters for this strategy to prevent collision
            strat_cls = strat.get_strategy_class(s_name)
            params = strat_cls().get_default_params()
            
            # Overlay global configuration variables onto strategy defaults
            for k in params.keys():
                if hasattr(config, k):
                    params[k] = getattr(config, k)
                    
            # Overlay instrument-specific overrides
            inst_cfg = {}
            if instrument_name:
                if hasattr(config, 'INSTRUMENTS') and config.INSTRUMENTS and instrument_name in config.INSTRUMENTS:
                    inst_cfg = config.INSTRUMENTS[instrument_name]
                elif os.path.exists("instruments.json"):
                    try:
                        with open("instruments.json", "r") as f:
                            all_inst = json.load(f)
                            inst_cfg = all_inst.get(instrument_name, {})
                    except Exception:
                        pass
                        
            if inst_cfg:
                for k in params.keys():
                    if k in inst_cfg:
                        params[k] = inst_cfg[k]
                for base_k in ["allowed_regimes_trend", "allowed_regimes_vol", "allowed_actions"]:
                    if base_k in inst_cfg:
                        params[base_k] = inst_cfg[base_k]
                        
                # Merge strategy-specific overrides for this strategy
                strat_overrides = inst_cfg.get("strategy_overrides", {}).get(s_name, {})
                if not strat_overrides and s_name in inst_cfg and isinstance(inst_cfg[s_name], dict):
                    strat_overrides = inst_cfg[s_name]
                    
                if isinstance(strat_overrides, dict) and strat_overrides:
                    for k, v in strat_overrides.items():
                        params[k] = v
                        
            # Instantiate and generate signals
            strategy = strat.get_strategy(s_name, params)
            df_strat = strategy.generate_signals(df.copy())
            
            if not df_strat.empty:
                # Merge Entry Signals
                sig_mask = df_strat['Signal'] != 0
                merged_df.loc[sig_mask, 'Signal'] = df_strat.loc[sig_mask, 'Signal']
                merged_df.loc[sig_mask, 'Signal_Source'] = s_name
                
                # Merge Exit Signals
                for col in ['Exit_Long', 'Exit_Short']:
                    if col in df_strat.columns:
                        exit_mask = df_strat[col] == True
                        merged_df.loc[exit_mask, col] = True
                        merged_df.loc[exit_mask, 'Exit_Source'] = s_name
                        
        return merged_df
        
    except Exception as e:
        logger.error(f"[ERROR] Modular process_market_data failed: {e}", exc_info=True)
        return pd.DataFrame()

def get_latest_signal(df: pd.DataFrame, logger, config: Config) -> Tuple[Optional[str], float, str]:
    """
    Check the last COMPLETED 1-min candle for a signal.
    Returns: (Signal, ATR_Value, Trigger_Source)
    """
    if df.empty: return None, 0.0, ""
    
    # Dynamically determine the last completed row.
    # If the last row's timestamp is >= the current minute, it is incomplete, so we look at iloc[-2].
    # Otherwise, the last row is already completed, so we look at iloc[-1].
    last_row = df.iloc[-1]
    last_row_time = last_row.name if isinstance(last_row.name, pd.Timestamp) else None
    
    use_last_row = True
    if last_row_time is not None:
        try:
            if last_row_time.tzinfo is None:
                last_row_time_local = last_row_time.tz_localize('UTC').tz_convert(config.TIMEZONE).tz_localize(None)
            else:
                last_row_time_local = last_row_time.tz_convert(config.TIMEZONE).tz_localize(None)
            current_minute = datetime.now(config.TIMEZONE).replace(second=0, microsecond=0, tzinfo=None)
            if last_row_time_local >= current_minute:
                use_last_row = False
        except Exception:
            pass
            
    if use_last_row:
        completed_row = df.iloc[-1]
    else:
        if len(df) < 2:
            return None, 0.0, ""
        completed_row = df.iloc[-2]
    
    sig = completed_row.get('Signal', 0)
    source = completed_row.get('Signal_Source', 'None')
    
    if sig == 0 or pd.isna(sig) or source == 'None' or pd.isna(source):
        return None, 0.0, ""
        
    disp_time = completed_row.name
    try:
        if isinstance(disp_time, pd.Timestamp):
            if disp_time.tz is None:
                disp_time = disp_time.tz_localize('UTC')
            disp_time = disp_time.tz_convert(config.TIMEZONE)
        disp_time_str = disp_time.strftime('%H:%M:%S')
    except:
        disp_time_str = str(disp_time)
        disp_time = None

    # STRICT TIMEFRAME FIX
    if isinstance(disp_time, pd.Timestamp) and disp_time.time() < config.RUN_START:
        return None, 0.0, ""

    logger.info(f"  >>> TRIGGER: {source} ({'BUY' if sig == 1 else 'SELL'}) @ {disp_time_str}")
    
    atr = completed_row.get('ATR', 0.0)
    return ('buy' if sig == 1 else 'sell'), atr, source

# ========== OPTION SELECTION ==========
def load_security_master(dhan, log_func=None) -> Optional[pd.DataFrame]:
    """Load DhanHQ security master list and filter for NIFTY options."""
    log = log_func or (lambda x: print(x))
    
    try:
        cache_file = 'dhanhq_nifty_options_cache.csv'
        
        if os.path.exists(cache_file):
            from datetime import datetime
            mod_date = datetime.fromtimestamp(os.path.getmtime(cache_file)).date()
            if mod_date == datetime.now().date():
                log(f"Loading cached security list from {cache_file}")
                df = pd.read_csv(cache_file, dtype={'SEM_SMST_SECURITY_ID': 'int64'})
                log(f"Loaded {len(df)} NIFTY option contracts from cache")
                return df
        
        log("Fetching fresh security master list from DhanHQ...")
        df = dhan.fetch_security_list(mode='compact', filename='dhanhq_securities_compact.csv')
        
        nifty_mask = df['SEM_TRADING_SYMBOL'].str.contains('NIFTY-', case=False, na=False)
        option_mask = df['SEM_INSTRUMENT_NAME'].str.contains('OPT', case=False, na=False)
        df = df[nifty_mask & option_mask].copy()
        
        df.to_csv(cache_file, index=False)
        log(f"Fetched {len(df)} NIFTY option contracts and cached to {cache_file}")
        
        return df
        
    except Exception as e:
        log(f"Error loading security master: {e}")
        return None

def choose_option_instruments(api: DhanAPIWrapper, signal: str, instrument_config: Dict, logger) -> Tuple[List[Dict], List[Dict]]:
    """Find ATM CE and PE option security IDs using cached security master."""
    try:
        underlying_id = int(instrument_config['security_id'])
        underlying_segment = instrument_config.get('exchange_segment', 'IDX_I')
        underlying_type = instrument_config.get('type', 'INDEX')
        hist_inst_type = 'INDEX' if underlying_type == 'INDEX' else 'EQUITY'
        
        ltp = 0.0
        try:
             resp = api._make_request(api.dhan.ohlc_data, securities={underlying_segment: [underlying_id]})
             if resp and 'data' in resp:
                 d = resp['data'].get(underlying_segment, {}).get(str(underlying_id), {})
                 ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
        except Exception as e:
             logger.debug(f"[CHOOSE_OPT] Quick LTP fetch failed for underlying {underlying_id}: {e}")
        
        if ltp == 0:
             df = api.get_historical_data(str(underlying_id), 1, underlying_segment, hist_inst_type)
             if df is not None and not df.empty:
                 ltp = float(df.iloc[-1]['close'])
        if ltp == 0:
             logger.error(f"[CHOOSE_OPT] Could not fetch LTP for {instrument_config['fno_prefix']}")
             return [], []
        
        logger.info(f"[CHOOSE_OPT] {instrument_config['fno_prefix']} LTP: {ltp}")
        
        expiry_list = []
        try:
             resp = api._make_request(api.dhan.expiry_list, under_security_id=underlying_id, under_exchange_segment=underlying_segment)
             if resp and resp.get('data'):
                  raw_data = resp['data']
                  
                  logger.info(f"[CHOOSE_OPT] Fetching Expiry for {underlying_id} ({underlying_segment}). Type: {type(raw_data)}")
                  
                  if isinstance(raw_data, list):
                      expiry_list = raw_data
                  elif isinstance(raw_data, dict):
                      found_list = False
                      for k, v in raw_data.items():
                          if isinstance(v, list):
                              expiry_list = v
                              found_list = True
                              logger.info(f"[CHOOSE_OPT] Found expiry list in key: {k}")
                              break
                      
                      if not found_list:
                          logger.warning(f"[CHOOSE_OPT] No list found in dict values. Keys: {list(raw_data.keys())}")
                          expiry_list = [str(x) for x in raw_data.values() if isinstance(x, (str, datetime))]
                  else:
                      logger.warning(f"[CHOOSE_OPT] Expiry list unknown type: {type(raw_data)}")
                      expiry_list = []
                      
        except Exception as e:
              logger.error(f"[CHOOSE_OPT] Error fetching expiry: {e}")
        
        if expiry_list:
            expiry_list = [str(x) for x in expiry_list if isinstance(x, str)]
        
        if not expiry_list:
            logger.error("[CHOOSE_OPT] No expiry list found.")
            return [], []
        
        expiry_list.sort()
        target_expiry_idx = instrument_config.get('expiry_index', 1)
        
        if len(expiry_list) > target_expiry_idx:
            nearest_expiry = expiry_list[target_expiry_idx]
        else:
            nearest_expiry = expiry_list[-1]
            logger.warning(f"[CHOOSE_OPT] Expiry Index {target_expiry_idx} out of range. Using last: {nearest_expiry}")
        
        timezone = pytz.timezone("Asia/Kolkata")
        if hasattr(api, 'config') and hasattr(api.config, 'TIMEZONE'):
            timezone = api.config.TIMEZONE
        trading_date_str = datetime.now(timezone).strftime('%Y-%m-%d')
        if nearest_expiry == trading_date_str:
            try:
                curr_idx = expiry_list.index(nearest_expiry)
                if curr_idx + 1 < len(expiry_list):
                    nearest_expiry = expiry_list[curr_idx + 1]
                    logger.info(f"[CHOOSE_OPT] Today is expiry date {trading_date_str}. Shifted to next: {nearest_expiry}")
            except ValueError:
                pass

        logger.info(f"[CHOOSE_OPT] Selected Expiry: {nearest_expiry}")

        prefix_upper = instrument_config['fno_prefix'].upper()
        use_lookup_fallback = True
        
        if api.config.master_cache_index:
            try:
                detected_strikes = []
                detected_lot_size = None
                for key, value in api.config.master_cache_index.items():
                    k_prefix, k_expiry, k_strike, k_type = key
                    if k_prefix == prefix_upper and k_expiry == nearest_expiry:
                        detected_strikes.append(k_strike)
                        if detected_lot_size is None:
                            detected_lot_size = value[1]
                            
                strike_step = instrument_config['strike_step']
                if strike_step <= 0:
                    logger.error(f"[CHOOSE_OPT] Invalid Configured Strike Step: {strike_step}")
                    return [], []
                    
                if len(detected_strikes) >= 2:
                    detected_strikes = sorted(list(set(detected_strikes)))
                    diffs = [detected_strikes[i+1] - detected_strikes[i] for i in range(len(detected_strikes)-1)]
                    if diffs:
                        detected_step = max(set(diffs), key=diffs.count)
                        if detected_step > 0:
                            strike_step = detected_step
                if detected_lot_size is not None and detected_lot_size > 0:
                    instrument_config['lot_size'] = detected_lot_size
                use_lookup_fallback = False
            except Exception as e:
                logger.error(f"[CHOOSE_OPT] Failed lookup mapping: {e}. Falling back to CSV.")
                use_lookup_fallback = True
                
        if use_lookup_fallback:
            cache_file = f"dhanhq_cache_{instrument_config['fno_prefix']}.csv"
            df = None
            if os.path.exists(cache_file):
                from datetime import datetime as dt
                mod_date = dt.fromtimestamp(os.path.getmtime(cache_file)).date()
                if mod_date == dt.now().date():
                    df = pd.read_csv(cache_file, dtype={'SEM_SMST_SECURITY_ID': 'int64'})
            
            if df is None:
                master_csv = 'dhanhq_securities_compact.csv'
                need_download = True
                if os.path.exists(master_csv):
                     from datetime import datetime as dt
                     mod_date = dt.fromtimestamp(os.path.getmtime(master_csv)).date()
                     if mod_date == dt.now().date():
                          need_download = False
                if need_download:
                    full_df = api.dhan.fetch_security_list(mode='compact', filename=master_csv)
                else:
                    full_df = pd.read_csv(master_csv)
                prefix = instrument_config['fno_prefix']
                nifty_mask = full_df['SEM_TRADING_SYMBOL'].str.contains(f'{prefix}-', case=False, na=False)
                option_mask = full_df['SEM_INSTRUMENT_NAME'].str.contains('OPT', case=False, na=False)
                target_exch = 'BSE' if 'BSE' in instrument_config.get('option_segment', 'NSE') else 'NSE'
                exch_mask = full_df['SEM_EXM_EXCH_ID'].str.contains(target_exch, case=False, na=False)
                df = full_df[nifty_mask & option_mask & exch_mask].copy()
                df.to_csv(cache_file, index=False)

            exp_date = datetime.strptime(nearest_expiry, '%Y-%m-%d')
            exp_month_year = exp_date.strftime('%b%Y')
            prefix_regex = instrument_config['fno_prefix']

            strike_step = instrument_config['strike_step']
            if strike_step <= 0:
                logger.error(f"[CHOOSE_OPT] Invalid Configured Strike Step: {strike_step}")
                return [], []

            detected_strikes = []
            detected_lot_size = None
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    sym = row['SEM_TRADING_SYMBOL']
                    expiry_date_str = str(row['SEM_EXPIRY_DATE']).split(' ')[0]
                    if expiry_date_str != nearest_expiry:
                        continue
                    match = re.search(rf'\b{prefix_regex}-{re.escape(exp_month_year)}-(\d+(?:\.\d+)?)-(CE|PE)', sym, re.IGNORECASE)
                    if match:
                        val = float(match.group(1))
                        detected_strikes.append(int(val) if val.is_integer() else val)
                        if 'LOT_SIZE' in row:
                            try:
                                detected_lot_size = int(row['LOT_SIZE'])
                            except Exception as e:
                                logger.debug(f"[CHOOSE_OPT] Failed to parse LOT_SIZE for {sym}: {e}")
                if len(detected_strikes) >= 2:
                    detected_strikes = sorted(list(set(detected_strikes)))
                    diffs = [detected_strikes[i+1] - detected_strikes[i] for i in range(len(detected_strikes)-1)]
                    if diffs:
                        detected_step = max(set(diffs), key=diffs.count)
                        if detected_step > 0:
                            strike_step = detected_step
                if detected_lot_size is not None and detected_lot_size > 0:
                    instrument_config['lot_size'] = detected_lot_size

        # ATM Strike and offsets calculation
        atm_strike = round(ltp / strike_step) * strike_step
        strike_offset = instrument_config.get('strike_offset', 0)
        strike_offset_buy = instrument_config.get('strike_offset_buy', strike_offset)
        strike_offset_sell = instrument_config.get('strike_offset_sell', strike_offset)
        
        ce_action, pe_action = get_trade_actions(signal, api.config, logger)
        ce_offset = strike_offset_buy if ce_action == 'BUY' else (strike_offset_sell if ce_action == 'SELL' else strike_offset)
        pe_offset = strike_offset_buy if pe_action == 'BUY' else (strike_offset_sell if pe_action == 'SELL' else strike_offset)
        
        ce_start_strike = atm_strike + (ce_offset * strike_step)
        pe_start_strike = atm_strike - (pe_offset * strike_step)
        
        direction = 1 if signal.lower() == 'buy' else -1
        num_strikes = instrument_config.get('num_strikes', api.config.NUM_STRIKES)
        step = strike_step
        
        ce_target_strikes_list = [int(ce_start_strike + (i * step * direction)) for i in range(num_strikes)]
        pe_target_strikes_list = [int(pe_start_strike + (i * step * direction)) for i in range(num_strikes)]
        
        ce_target_strikes = {strike: i for i, strike in enumerate(ce_target_strikes_list)}
        pe_target_strikes = {strike: i for i, strike in enumerate(pe_target_strikes_list)}
        
        # Live Greeks fetch
        strike_delta_map = {}
        try:
            chain_resp = api._make_request(
                api.dhan.option_chain,
                under_security_id=underlying_id,
                under_exchange_segment=underlying_segment,
                expiry=nearest_expiry
            )
            if chain_resp:
                chain_map = chain_resp.get('data', {}).get('oc') or chain_resp.get('oc') or chain_resp
                all_targets = set(ce_target_strikes.keys()) | set(pe_target_strikes.keys())
                for strike in all_targets:
                    strike_key = f"{float(strike):.6f}"
                    if strike_key in chain_map:
                        strike_node = chain_map[strike_key]
                        if 'ce' in strike_node and 'greeks' in strike_node['ce']:
                             d = strike_node['ce']['greeks'].get('delta')
                             if d is not None: strike_delta_map[(strike, 'CE')] = float(d)
                        if 'pe' in strike_node and 'greeks' in strike_node['pe']:
                             d = strike_node['pe']['greeks'].get('delta')
                             if d is not None: strike_delta_map[(strike, 'PE')] = float(d)
        except Exception as e:
            logger.error(f"[OPT_CHAIN] Error fetching Greeks: {e}")

        ce_final = [None] * num_strikes
        pe_final = [None] * num_strikes
        
        use_lookup_result = False
        if not use_lookup_fallback:
            try:
                for strike in ce_target_strikes_list:
                    key = (prefix_upper, nearest_expiry, strike, 'CE')
                    if key in api.config.master_cache_index:
                        sec_id, lot_size, sym = api.config.master_cache_index[key]
                        rank = ce_target_strikes[strike]
                        real_delta = strike_delta_map.get((strike, 'CE'))
                        ce_final[rank] = {'id': sec_id, 'strike': strike, 'type': 'CE', 'delta': real_delta, 'symbol': sym}
                for strike in pe_target_strikes_list:
                    key = (prefix_upper, nearest_expiry, strike, 'PE')
                    if key in api.config.master_cache_index:
                        sec_id, lot_size, sym = api.config.master_cache_index[key]
                        rank = pe_target_strikes[strike]
                        real_delta = strike_delta_map.get((strike, 'PE'))
                        pe_final[rank] = {'id': sec_id, 'strike': strike, 'type': 'PE', 'delta': real_delta, 'symbol': sym}
                use_lookup_result = True
            except Exception as lookup_err:
                logger.error(f"[CHOOSE_OPT] Memory lookup error: {lookup_err}")
                use_lookup_result = False
                
        if not use_lookup_result:
            found_count = 0
            total = num_strikes * 2
            prefix_regex = instrument_config['fno_prefix']
            exp_date = datetime.strptime(nearest_expiry, '%Y-%m-%d')
            exp_month_year = exp_date.strftime('%b%Y')
            
            for idx, row in df.iterrows():
                sym = row['SEM_TRADING_SYMBOL']
                sec_id = str(int(row['SEM_SMST_SECURITY_ID']))
                expiry_date_str = str(row['SEM_EXPIRY_DATE']).split(' ')[0]
                if expiry_date_str != nearest_expiry: continue

                match = re.search(rf'\b{prefix_regex}-{re.escape(exp_month_year)}-(\d+(?:\.\d+)?)-(CE|PE)', sym, re.IGNORECASE)
                if not match: continue
                
                val = float(match.group(1))
                strike = int(val) if val.is_integer() else val
                option_type = match.group(2).upper()
                
                def build_node(s_id, s_strike, s_type):
                    real_delta = strike_delta_map.get((s_strike, s_type))
                    return {'id': s_id, 'strike': s_strike, 'type': s_type, 'delta': real_delta, 'symbol': sym}

                if option_type == 'CE' and strike in ce_target_strikes:
                    rank = ce_target_strikes[strike]
                    ce_final[rank] = build_node(sec_id, strike, 'CE')
                    found_count += 1
                elif option_type == 'PE' and strike in pe_target_strikes:
                    rank = pe_target_strikes[strike]
                    pe_final[rank] = build_node(sec_id, strike, 'PE')
                    found_count += 1
                
                if found_count >= total: break
        
        ce_res = [x for x in ce_final if x]
        pe_res = [x for x in pe_final if x]
        return ce_res, pe_res
    except Exception as e:
        logger.exception(f"[CHOOSE_OPT] Exception: {e}")
        return [], []

def choose_strategy_instruments(api: DhanAPIWrapper, signal: str, strategy_mode: str, instrument_config: Dict, logger) -> List[Dict]:
    """Select contracts for multi-leg option strategies."""
    try:
        underlying_id = int(instrument_config['security_id'])
        underlying_segment = instrument_config.get('exchange_segment', 'IDX_I')
        underlying_type = instrument_config.get('type', 'INDEX')
        hist_inst_type = 'INDEX' if underlying_type == 'INDEX' else 'EQUITY'
        
        ltp = 0.0
        try:
             resp = api._make_request(api.dhan.ohlc_data, securities={underlying_segment: [underlying_id]})
             if resp and 'data' in resp:
                 d = resp['data'].get(underlying_segment, {}).get(str(underlying_id), {})
                 ltp = float(d.get('last_price', 0) or d.get('ltp', 0))
        except Exception as e:
             logger.debug(f"[CHOOSE_STRAT] Quick LTP fetch failed for underlying {underlying_id}: {e}")
        
        if ltp == 0:
             df = api.get_historical_data(str(underlying_id), 1, underlying_segment, hist_inst_type)
             if df is not None and not df.empty:
                 ltp = float(df.iloc[-1]['close'])
                   
        if ltp == 0:
            logger.error(f"[CHOOSE_STRAT] Could not fetch LTP for {instrument_config['fno_prefix']}")
            return []
        
        expiry_list = []
        try:
             resp = api._make_request(api.dhan.expiry_list, under_security_id=underlying_id, under_exchange_segment=underlying_segment)
             if resp and resp.get('data'):
                  raw_data = resp['data']
                  if isinstance(raw_data, list):
                      expiry_list = raw_data
                  elif isinstance(raw_data, dict):
                      found_list = False
                      for k, v in raw_data.items():
                          if isinstance(v, list):
                              expiry_list = v
                              found_list = True
                              break
                      if not found_list:
                          expiry_list = [str(x) for x in raw_data.values() if isinstance(x, (str, datetime))]
        except Exception as e:
              logger.error(f"[CHOOSE_STRAT] Error: {e}")
        
        if expiry_list:
            expiry_list = [str(x) for x in expiry_list if isinstance(x, str)]
            expiry_list.sort()
            
        if not expiry_list:
            logger.error("[CHOOSE_STRAT] No expiry list found.")
            return []
            
        target_expiry_idx = instrument_config.get('expiry_index', 0)
        nearest_expiry = expiry_list[target_expiry_idx] if len(expiry_list) > target_expiry_idx else expiry_list[-1]
        
        timezone = pytz.timezone("Asia/Kolkata")
        if hasattr(api, 'config') and hasattr(api.config, 'TIMEZONE'):
            timezone = api.config.TIMEZONE
        trading_date_str = datetime.now(timezone).strftime('%Y-%m-%d')
        if nearest_expiry == trading_date_str:
            try:
                curr_idx = expiry_list.index(nearest_expiry)
                if curr_idx + 1 < len(expiry_list):
                    nearest_expiry = expiry_list[curr_idx + 1]
            except ValueError: pass

        prefix_upper = instrument_config['fno_prefix'].upper()
        use_strat_fallback = True
        
        if api.config.master_cache_index:
            try:
                detected_strikes = []
                detected_lot_size = None
                for key, value in api.config.master_cache_index.items():
                    k_prefix, k_expiry, k_strike, k_type = key
                    if k_prefix == prefix_upper and k_expiry == nearest_expiry:
                        detected_strikes.append(k_strike)
                        if detected_lot_size is None:
                            detected_lot_size = value[1]
                            
                strike_step = instrument_config['strike_step']
                if strike_step <= 0:
                    logger.error(f"[CHOOSE_STRAT] Invalid configured strike step: {strike_step}")
                    return []
                    
                if len(detected_strikes) >= 2:
                    detected_strikes = sorted(list(set(detected_strikes)))
                    diffs = [detected_strikes[i+1] - detected_strikes[i] for i in range(len(detected_strikes)-1)]
                    if diffs:
                        detected_step = max(set(diffs), key=diffs.count)
                        if detected_step > 0:
                            strike_step = detected_step
                if detected_lot_size is not None and detected_lot_size > 0:
                    instrument_config['lot_size'] = detected_lot_size
                use_strat_fallback = False
            except Exception as e:
                logger.error(f"[CHOOSE_STRAT] Memory index failed: {e}")
                use_strat_fallback = True
                
        if use_strat_fallback:
            cache_file = f"dhanhq_cache_{instrument_config['fno_prefix']}.csv"
            df = None
            if os.path.exists(cache_file):
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < 86400:
                    df = pd.read_csv(cache_file, dtype={'SEM_SMST_SECURITY_ID': 'int64'})
                    
            if df is None:
                master_csv = 'dhanhq_securities_compact.csv'
                need_download = True
                if os.path.exists(master_csv):
                     if (time.time() - os.path.getmtime(master_csv)) < 86400:
                          need_download = False
                if need_download:
                    full_df = api.dhan.fetch_security_list(mode='compact', filename=master_csv)
                else:
                    full_df = pd.read_csv(master_csv)
                prefix = instrument_config['fno_prefix']
                nifty_mask = full_df['SEM_TRADING_SYMBOL'].str.contains(f'{prefix}-', case=False, na=False)
                option_mask = full_df['SEM_INSTRUMENT_NAME'].str.contains('OPT', case=False, na=False)
                target_exch = 'BSE' if 'BSE' in instrument_config.get('option_segment', 'NSE') else 'NSE'
                exch_mask = full_df['SEM_EXM_EXCH_ID'].str.contains(target_exch, case=False, na=False)
                df = full_df[nifty_mask & option_mask & exch_mask].copy()
                df.to_csv(cache_file, index=False)

            exp_date = datetime.strptime(nearest_expiry, '%Y-%m-%d')
            exp_month_year = exp_date.strftime('%b%Y')
            prefix_regex = instrument_config['fno_prefix']

            strike_step = instrument_config['strike_step']
            if strike_step <= 0:
                logger.error(f"[CHOOSE_STRAT] Invalid strike step: {strike_step}")
                return []

            detected_strikes = []
            detected_lot_size = None
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    sym = row['SEM_TRADING_SYMBOL']
                    expiry_date_str = str(row['SEM_EXPIRY_DATE']).split(' ')[0]
                    if expiry_date_str != nearest_expiry: continue
                    match = re.search(rf'\b{prefix_regex}-{re.escape(exp_month_year)}-(\d+(?:\.\d+)?)-(CE|PE)', sym, re.IGNORECASE)
                    if match:
                        val = float(match.group(1))
                        detected_strikes.append(int(val) if val.is_integer() else val)
                        if 'LOT_SIZE' in row:
                            try:
                                detected_lot_size = int(row['LOT_SIZE'])
                            except Exception as e:
                                logger.debug(f"[CHOOSE_STRAT] Failed to parse LOT_SIZE for {sym}: {e}")
                if len(detected_strikes) >= 2:
                    detected_strikes = sorted(list(set(detected_strikes)))
                    diffs = [detected_strikes[i+1] - detected_strikes[i] for i in range(len(detected_strikes)-1)]
                    if diffs:
                        detected_step = max(set(diffs), key=diffs.count)
                        if detected_step > 0:
                            strike_step = detected_step
                if detected_lot_size is not None and detected_lot_size > 0:
                    instrument_config['lot_size'] = detected_lot_size

        atm_strike = round(ltp / strike_step) * strike_step
        strike_offset_buy = instrument_config.get('strike_offset_buy', 0)
        strike_offset_sell = instrument_config.get('strike_offset_sell', 0)
        width = instrument_config.get('strategy_leg_width', 1)
        
        blueprints = []
        mode = strategy_mode.upper()
        if mode == "DEBIT_SPREAD":
            if signal.lower() == 'buy':
                blueprints = [
                    ("BUY", "CE", strike_offset_buy, "CE_LONG"),
                    ("SELL", "CE", strike_offset_buy + width, "CE_SHORT")
                ]
            else:
                blueprints = [
                    ("BUY", "PE", strike_offset_buy, "PE_LONG"),
                    ("SELL", "PE", strike_offset_buy + width, "PE_SHORT")
                ]
        elif mode == "CREDIT_SPREAD":
            if signal.lower() == 'buy':
                blueprints = [
                    ("BUY", "PE", strike_offset_sell + width, "PE_LONG"),
                    ("SELL", "PE", strike_offset_sell, "PE_SHORT")
                ]
            else:
                blueprints = [
                    ("BUY", "CE", strike_offset_sell + width, "CE_LONG"),
                    ("SELL", "CE", strike_offset_sell, "CE_SHORT")
                ]
        elif mode == "SHORT_STRADDLE":
            blueprints = [
                ("SELL", "CE", strike_offset_sell, "CE_SHORT"),
                ("SELL", "PE", strike_offset_sell, "PE_SHORT")
            ]
        elif mode == "LONG_STRADDLE":
            blueprints = [
                ("BUY", "CE", strike_offset_buy, "CE_LONG"),
                ("BUY", "PE", strike_offset_buy, "PE_LONG")
            ]
        elif mode == "SHORT_STRANGLE":
            blueprints = [
                ("SELL", "CE", strike_offset_sell + width, "CE_SHORT"),
                ("SELL", "PE", strike_offset_sell + width, "PE_SHORT")
            ]
        elif mode == "LONG_STRANGLE":
            blueprints = [
                ("BUY", "CE", strike_offset_buy + width, "CE_LONG"),
                ("BUY", "PE", strike_offset_buy + width, "PE_LONG")
            ]
        elif mode == "IRON_CONDOR":
            blueprints = [
                ("BUY", "PE", strike_offset_sell + width, "PE_LONG"),
                ("SELL", "PE", strike_offset_sell + width, "PE_SHORT"),
                ("SELL", "CE", strike_offset_sell + width, "CE_SHORT"),
                ("BUY", "CE", strike_offset_sell + width, "CE_LONG")
            ]
        elif mode == "IRON_FLY":
            blueprints = [
                ("BUY", "PE", strike_offset_sell + width, "PE_LONG"),
                ("SELL", "PE", strike_offset_sell, "PE_SHORT"),
                ("SELL", "CE", strike_offset_sell, "CE_SHORT"),
                ("BUY", "CE", strike_offset_sell + width, "CE_LONG")
            ]
        else:
            logger.error(f"[CHOOSE_STRAT] Unknown strategy mode: {strategy_mode}")
            return []
            
        legs_to_find = []
        for action, opt_type, offset, label in blueprints:
            if opt_type == "CE":
                strike = int(atm_strike + (offset * strike_step))
            else:
                strike = int(atm_strike - (offset * strike_step))
            legs_to_find.append({'action': action, 'type': opt_type, 'strike': strike, 'label': label})
            
        strike_delta_map = {}
        try:
            chain_resp = api._make_request(
                api.dhan.option_chain,
                under_security_id=underlying_id,
                under_exchange_segment=underlying_segment,
                expiry=nearest_expiry
            )
            if chain_resp:
                chain_map = chain_resp.get('data', {}).get('oc') or chain_resp.get('oc') or chain_resp
                for leg in legs_to_find:
                    strike_key = f"{float(leg['strike']):.6f}"
                    if strike_key in chain_map:
                        node = chain_map[strike_key]
                        opt_key = leg['type'].lower()
                        if opt_key in node and 'greeks' in node[opt_key]:
                            d = node[opt_key]['greeks'].get('delta')
                            if d is not None: strike_delta_map[(leg['strike'], leg['type'])] = float(d)
        except Exception as e:
            logger.error(f"[CHOOSE_STRAT] Greeks error: {e}")

        legs_matched = {}
        use_lookup_result = False
        if not use_strat_fallback:
            try:
                for leg_idx, leg in enumerate(legs_to_find):
                    key = (prefix_upper, nearest_expiry, leg['strike'], leg['type'])
                    if key in api.config.master_cache_index:
                        sec_id, lot_size, sym = api.config.master_cache_index[key]
                        d = strike_delta_map.get((leg['strike'], leg['type']), api.config.OPTION_DELTA)
                        legs_matched[leg_idx] = {
                            'item': {'id': sec_id, 'strike': leg['strike'], 'type': leg['type'], 'delta': d, 'symbol': sym},
                            'action': leg['action'],
                            'leg_type': leg['label']
                        }
                use_lookup_result = True
            except Exception as lookup_err:
                logger.error(f"[CHOOSE_STRAT] Memory lookup mapping error: {lookup_err}")
                use_lookup_result = False
                
        if not use_lookup_result:
            prefix_regex = instrument_config['fno_prefix']
            exp_date = datetime.strptime(nearest_expiry, '%Y-%m-%d')
            exp_month_year = exp_date.strftime('%b%Y')
            for idx, row in df.iterrows():
                sym = row['SEM_TRADING_SYMBOL']
                expiry_date_str = str(row['SEM_EXPIRY_DATE']).split(' ')[0]
                if expiry_date_str != nearest_expiry: continue

                match = re.search(rf'\b{prefix_regex}-{re.escape(exp_month_year)}-(\d+(?:\.\d+)?)-(CE|PE)', sym, re.IGNORECASE)
                if not match: continue
                
                val = float(match.group(1))
                row_strike = int(val) if val.is_integer() else val
                row_type = match.group(2).upper()
                
                for leg_idx, leg in enumerate(legs_to_find):
                    if leg_idx in legs_matched: continue
                    if leg['strike'] == row_strike and leg['type'] == row_type:
                        sec_id = str(int(row['SEM_SMST_SECURITY_ID']))
                        d = strike_delta_map.get((row_strike, row_type), api.config.OPTION_DELTA)
                        legs_matched[leg_idx] = {
                            'item': {'id': sec_id, 'strike': row_strike, 'type': row_type, 'delta': d, 'symbol': sym},
                            'action': leg['action'],
                            'leg_type': leg['label']
                        }
                        break
                if len(legs_matched) == len(legs_to_find): break
                    
        results = [legs_matched[idx] for idx in range(len(legs_to_find)) if idx in legs_matched]
        return results
    except Exception as e:
        logger.exception(f"[CHOOSE_STRAT] Exception: {e}")
        return []

# ========== TRADE LOGGING ==========
LOG_LOCK = threading.Lock()

def log_trade_event(data: Dict, csv_file: str, logger):
    """Log trade execution to CSV (thread-safe)"""
    with LOG_LOCK:
        try:
            df = pd.DataFrame([data])
            if not os.path.exists(csv_file):
                df.to_csv(csv_file, index=False)
                logger.info(f"Created new trade log: {csv_file}")
            else:
                df.to_csv(csv_file, mode='a', header=False, index=False)
            logger.info(f"Trade logged: {data.get('signal')} at {data.get('timestamp')}")
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")

# ========== COUNT ACTIVE ORDERS ==========
def count_active_option_orders(positions: List[Dict], logger) -> int:
    """Count active F&O positions"""
    if not positions:
        return 0
    try:
        active_count = 0
        for pos in positions:
            exchange = pos.get('exchangeSegment', '')
            net_qty = safe_int(pos.get('netQty', 0))
            if (exchange == 'NSE_FNO' or exchange == 'BSE_FNO') and net_qty != 0:
                active_count += 1
                logger.debug(f"Active F&O position: {pos.get('securityId')} x {net_qty}")
        logger.info(f"Active F&O orders: {active_count}/{2}")
        return active_count
    except Exception as e:
        logger.error(f"Error counting active orders: {e}")
        return 0

# ========== CANDLE ALIGNMENT ==========
def wait_for_next_candle(current_time: datetime, poll_interval: int, logger, offset_seconds: int = 0) -> datetime:
    """Wait until the next candle starts (minute boundary) + offset"""
    now_fresh = datetime.now(current_time.tzinfo)
    next_minute = now_fresh.replace(second=0, microsecond=0) + timedelta(minutes=1)
    if offset_seconds > 0:
        next_minute += timedelta(seconds=offset_seconds)
    sleep_seconds = (next_minute - now_fresh).total_seconds()
    if sleep_seconds > 0:
        logger.debug(f"Waiting {sleep_seconds:.1f}s for next candle (incl. {offset_seconds}s offset)...")
        time.sleep(sleep_seconds)
    return next_minute

# ========== TRADE ACTION DETERMINATION ==========
def get_trade_actions(signal: str, config: Config, logger) -> Tuple[Optional[str], Optional[str]]:
    """Determine CE and PE actions based on signal and LEG_MODE"""
    if config.LEG_MODE == "BOTH":
        if signal.lower() == 'buy':
            logger.info(f"[DIRECTION] Mode=BOTH, Signal=BUY >> CE=BUY, PE=SELL")
            return ('BUY', 'SELL')
        else: # sell
            logger.info(f"[DIRECTION] Mode=BOTH, Signal=SELL >> CE=SELL, PE=BUY")
            return ('SELL', 'BUY')
    elif config.LEG_MODE == "BUY":
        if signal.lower() == 'buy':
            logger.info(f"[DIRECTION] Mode=BUY, Signal=BUY >> CE=BUY, PE=None")
            return ('BUY', None)
        else:
            logger.info(f"[DIRECTION] Mode=BUY, Signal=SELL >> CE=None, PE=BUY")
            return (None, 'BUY')
    elif config.LEG_MODE == "SELL":
        if signal.lower() == 'buy':
            logger.info(f"[DIRECTION] Mode=SELL, Signal=BUY >> CE=None, PE=SELL")
            return (None, 'SELL')
        else:
            logger.info(f"[DIRECTION] Mode=SELL, Signal=SELL >> CE=SELL, PE=None")
            return ('SELL', None)
    return None, None

# ========== SMART WAIT DATA FETCHING ==========
def fetch_candle_with_retry(api, security_id, config, logger, interval: int = 1, exchange_segment='IDX_I', instrument_type='INDEX') -> Optional[pd.DataFrame]:
    """Fetch historical data with 'Smart Wait' logic to ensure the latest candle is present."""
    max_retries = 5
    retry_retry_delay = 2.0
    now = datetime.now(config.TIMEZONE)
    
    current_minute = now.minute
    remainder = current_minute % interval
    current_candle_start_ist = now.replace(second=0, microsecond=0) - timedelta(minutes=remainder)
    expected_candle_time_ist = current_candle_start_ist - timedelta(minutes=interval)
    expected_candle_time = expected_candle_time_ist.astimezone(pytz.UTC).replace(tzinfo=None)
    
    for attempt in range(max_retries + 1):
        t0 = time.time()
        df = api.get_historical_data(security_id, interval=interval, exchange_segment=exchange_segment, instrument_type=instrument_type)
        latency = time.time() - t0
        
        if df is not None and not df.empty:
            logger.debug(f"[API] History Fetch {security_id}: {latency:.3f}s")
        else:
            logger.warning(f"[API] History Fetch {security_id} FAILED: {latency:.3f}s")
        
        if df is None:
             return None

        if df.empty:
             time.sleep(retry_retry_delay)
             continue

        if 'timestamp' in df.columns and len(df) > 0:
            last_candle_time = df.iloc[-1]['timestamp']
            
            def _log_time(t):
                try:
                    if isinstance(t, pd.Timestamp):
                        if t.tz is None:
                           t = t.tz_localize('UTC')
                        return t.tz_convert(config.TIMEZONE)
                    return t
                except: return t

            last_candle_log = _log_time(last_candle_time)
            if last_candle_time >= expected_candle_time:
                return df
            else:
                time.sleep(retry_retry_delay)
        else:
            time.sleep(retry_retry_delay)
            
    return df

# ========== DATA RESTORATION HELPER ==========
def get_today_trade_count(csv_file: str, instrument_name: str, timezone) -> dict:
    """Count unique trades for a given instrument today per account by reading the CSV log."""
    if not os.path.exists(csv_file):
        return {}
    try:
        today = datetime.now(timezone).date()
        df = pd.read_csv(csv_file, usecols=lambda c: c in ['timestamp', 'instrument', 'account'])
        
        if 'timestamp' not in df.columns or 'instrument' not in df.columns:
            return {}
            
        df = df[df['instrument'] == instrument_name]
        if df.empty:
            return {}
            
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df_today = df[df['timestamp'].dt.date == today]
        
        if df_today.empty:
            return {}
            
        if 'account' not in df_today.columns:
            df_today['account'] = 'UNKNOWN_ACCOUNT'
            
        df_today['minute'] = df_today['timestamp'].dt.floor('min')
        counts = df_today.groupby('account')['minute'].nunique().to_dict()
        return counts
    except Exception as e:
        import logging
        logging.error(f"[RESTORE] Failed to count trades for {instrument_name}: {e}")
        return {}
