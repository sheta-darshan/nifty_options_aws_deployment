import os
import json
import time
import re
import threading
import pytz
import pandas as pd
from datetime import datetime, timedelta, time as dt_time
from typing import Optional, List, Dict, Tuple

from trading_bot.config import Config
from trading_bot.api_wrapper import DhanAPIWrapper, safe_int

import logging
logger = logging.getLogger("live-dhan-bot.pipeline")

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
    
    # 1. Overlay instrument-specific configuration
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

    # 2. Determine active strategies dynamically using the registry
    inst_strat = inst_cfg.get("strategy")
    if inst_strat and inst_strat in strat.STRATEGY_REGISTRY:
        # Instrument is strictly dedicated to this specific strategy (e.g. Strategy_24 for cash stocks)
        active_strategies = [inst_strat]
    else:
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
    merged_df['Conviction'] = 1.0
    merged_df['Exit_Long'] = False
    merged_df['Exit_Short'] = False
    merged_df['Exit_Source'] = "None"
    
    # Initialize strategy-specific columns
    for s_name in active_strategies:
        merged_df[f'Signal_{s_name}'] = 0
        merged_df[f'Exit_Long_{s_name}'] = False
        merged_df[f'Exit_Short_{s_name}'] = False
        merged_df[f'Conviction_{s_name}'] = 1.0
        
    try:
        for s_name in active_strategies:
            # Load default parameters for this strategy to prevent collision
            strat_cls = strat.get_strategy_class(s_name)
            params = strat_cls().get_default_params()
            
            # Overlay global configuration variables onto strategy defaults (preserve strategy-specific timing defaults)
            for k in params.keys():
                if k not in ["START_TIME", "CUTOFF_TIME"] and hasattr(config, k):
                    params[k] = getattr(config, k)
                    
            if inst_cfg:
                for k in params.keys():
                    if k in inst_cfg:
                        params[k] = inst_cfg[k]
                    elif k.lower() in inst_cfg:
                        params[k] = inst_cfg[k.lower()]
                    elif k.upper() in inst_cfg:
                        params[k] = inst_cfg[k.upper()]
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
                        if k.upper() in params:
                            params[k.upper()] = v
                        
            # Instantiate and generate signals
            strategy = strat.get_strategy(s_name, params)
            df_strat = strategy.generate_signals(df.copy())
            
            if not df_strat.empty:
                # Merge Entry Signals
                sig_mask = df_strat['Signal'] != 0
                merged_df.loc[sig_mask, f'Signal_{s_name}'] = df_strat.loc[sig_mask, 'Signal']
                
                # Check if we should populate global fallback
                fallback_mask = sig_mask & (merged_df['Signal'] == 0)
                merged_df.loc[fallback_mask, 'Signal'] = df_strat.loc[fallback_mask, 'Signal']
                merged_df.loc[fallback_mask, 'Signal_Source'] = s_name

                # Merge Conviction score
                if 'Conviction' in df_strat.columns:
                    merged_df.loc[sig_mask, f'Conviction_{s_name}'] = df_strat.loc[sig_mask, 'Conviction']
                    merged_df.loc[fallback_mask, 'Conviction'] = df_strat.loc[fallback_mask, 'Conviction']
                
                # Merge Exit Signals
                for col in ['Exit_Long', 'Exit_Short']:
                    if col in df_strat.columns:
                        exit_mask = df_strat[col] == True
                        merged_df.loc[exit_mask, f'{col}_{s_name}'] = True
                        
                        fallback_exit_mask = exit_mask & (merged_df[col] == False)
                        merged_df.loc[fallback_exit_mask, col] = True
                        merged_df.loc[fallback_exit_mask, 'Exit_Source'] = s_name
                        
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
    except Exception:
        disp_time_str = str(disp_time)
        disp_time = None

    # STRICT TIMEFRAME FIX
    if isinstance(disp_time, pd.Timestamp) and disp_time.time() < config.RUN_START:
        return None, 0.0, ""

    logger.info(f"  >>> TRIGGER: {source} ({'BUY' if sig == 1 else 'SELL'}) @ {disp_time_str}")
    
    return ('buy' if sig == 1 else 'sell'), atr, source

def get_all_latest_signals(df: pd.DataFrame, logger, config: Config) -> list:
    """
    Check the last COMPLETED 1-min candle for signals across all active strategies.
    Returns a list of Tuples: [(direction, ATR_Value, Strategy_Name), ...]
    """
    if df.empty: return []
    
    # Determine the completed row
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
            return []
        completed_row = df.iloc[-2]
        
    disp_time = completed_row.name
    try:
        if isinstance(disp_time, pd.Timestamp):
            if disp_time.tz is None:
                disp_time = disp_time.tz_localize('UTC')
            disp_time = disp_time.tz_convert(config.TIMEZONE)
        disp_time_str = disp_time.strftime('%H:%M:%S')
    except Exception:
        disp_time_str = str(disp_time)
        disp_time = None
        
    # STRICT TIMEFRAME FIX
    run_start_time = config.RUN_START
    early_strategies = {"Strategy_14", "Strategy_20", "Strategy_24"}
    if hasattr(config, 'INSTRUMENTS') and isinstance(config.INSTRUMENTS, dict):
        for item in config.INSTRUMENTS.values():
            if isinstance(item, dict) and item.get('enabled', 0) and item.get('strategy') in early_strategies:
                run_start_time = dt_time(9, 15)
                break
    if isinstance(disp_time, pd.Timestamp) and disp_time.time() < run_start_time:
        return []
        
    active_signals = []
    # Scan columns for strategy-specific signals
    for col in completed_row.index:
        if col.startswith("Signal_") and col != "Signal_Source":
            sig = completed_row.get(col, 0)
            if sig != 0 and pd.notna(sig):
                s_name = col.split("Signal_")[-1]
                # Double check that the strategy is actually enabled globally or assigned to an active instrument
                is_strat_enabled = getattr(config, f"ENABLE_{s_name.upper()}", False)
                if not is_strat_enabled and hasattr(config, 'INSTRUMENTS') and isinstance(config.INSTRUMENTS, dict):
                    for item in config.INSTRUMENTS.values():
                        if isinstance(item, dict) and item.get('enabled', 0) and item.get('strategy') == s_name:
                            is_strat_enabled = True
                            break
                if is_strat_enabled:
                    direction = 'buy' if sig == 1 else ('sell' if sig == -1 else 'both')
                    atr = completed_row.get('ATR', 0.0)
                    active_signals.append((direction, atr, s_name))
                    logger.info(f"  >>> CONCURRENT TRIGGER: {s_name} ({direction.upper()}) @ {disp_time_str}")
                    
    return active_signals

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
        target_expiry_idx = instrument_config.get('expiry_index', 0)
        
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
        elif mode in ("1", "DIRECT", "2", "OPTION_WRITING", "DIRECT_SELL"):
            leg_mode = instrument_config.get("LEG_MODE", getattr(config, "LEG_MODE", "BUY")).upper()
            sig_str = str(signal).lower()
            if sig_str in ('both', 'strangle', '2'):
                if leg_mode == "SELL":
                    blueprints = [
                        ("SELL", "CE", strike_offset_sell, "CE_SHORT"),
                        ("SELL", "PE", strike_offset_sell, "PE_SHORT")
                    ]
                elif leg_mode == "BUY":
                    blueprints = [
                        ("BUY", "CE", strike_offset_buy, "CE_LONG"),
                        ("BUY", "PE", strike_offset_buy, "PE_LONG")
                    ]
                else: # BOTH
                    blueprints = [
                        ("SELL", "CE", strike_offset_sell, "CE_SHORT"),
                        ("SELL", "PE", strike_offset_sell, "PE_SHORT")
                    ]
            elif sig_str in ('buy', 'call', '1', '+1'):
                if leg_mode == "SELL":
                    blueprints = [("SELL", "PE", strike_offset_sell, "PE_SHORT")]
                elif leg_mode == "BUY":
                    blueprints = [("BUY", "CE", strike_offset_buy, "CE_LONG")]
                else: # BOTH
                    blueprints = [
                        ("BUY", "CE", strike_offset_buy, "CE_LONG"),
                        ("SELL", "PE", strike_offset_sell, "PE_SHORT")
                    ]
            else: # sell / put / -1
                if leg_mode == "SELL":
                    blueprints = [("SELL", "CE", strike_offset_sell, "CE_SHORT")]
                elif leg_mode == "BUY":
                    blueprints = [("BUY", "PE", strike_offset_buy, "PE_LONG")]
                else: # BOTH
                    blueprints = [
                        ("BUY", "PE", strike_offset_buy, "PE_LONG"),
                        ("SELL", "CE", strike_offset_sell, "CE_SHORT")
                    ]
        elif mode in ("10", "CALENDAR_SPREAD"):
            logger.info("[CHOOSE_STRAT] Calendar spread mode requested, resolved via dedicated multi-expiry builder.")
            return []
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
def get_trade_actions(signal: str, config: Config, logger, leg_mode_override: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Determine CE and PE actions based on signal and LEG_MODE (supporting strategy overrides)"""
    mode = (leg_mode_override or getattr(config, 'LEG_MODE', 'BOTH')).upper()
    if mode == "BOTH":
        if signal.lower() == 'buy':
            logger.info(f"[DIRECTION] Mode=BOTH, Signal=BUY >> CE=BUY, PE=SELL")
            return ('BUY', 'SELL')
        else: # sell
            logger.info(f"[DIRECTION] Mode=BOTH, Signal=SELL >> CE=SELL, PE=BUY")
            return ('SELL', 'BUY')
    elif mode == "BUY":
        if signal.lower() == 'buy':
            logger.info(f"[DIRECTION] Mode=BUY, Signal=BUY >> CE=BUY, PE=None")
            return ('BUY', None)
        else:
            logger.info(f"[DIRECTION] Mode=BUY, Signal=SELL >> CE=None, PE=BUY")
            return (None, 'BUY')
    elif mode == "SELL":
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
                except Exception: return t

            last_candle_log = _log_time(last_candle_time)
            if last_candle_time >= expected_candle_time:
                return df
            else:
                time.sleep(retry_retry_delay)
        else:
            time.sleep(retry_retry_delay)
            
    return df

# ========== DATA RESTORATION HELPER ==========
def get_today_trade_count(csv_file: str, instrument_name: str, timezone, strategy_name: str = None) -> dict:
    """Count unique trades for a given instrument today per account by reading the CSV log."""
    if not isinstance(csv_file, (str, bytes)):
        return {}
    try:
        if not os.path.exists(csv_file):
            return {}
    except Exception:
        return {}
    try:
        try:
            today = datetime.now(timezone).date()
        except Exception:
            today = datetime.now().date()
        df = pd.read_csv(csv_file, usecols=lambda c: c in ['timestamp', 'instrument', 'account', 'strategy'])
        
        if 'timestamp' not in df.columns or 'instrument' not in df.columns:
            return {}
            
        df = df[df['instrument'] == instrument_name]
        if strategy_name and 'strategy' in df.columns:
            df = df[df['strategy'] == strategy_name]
            
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

def get_today_sl_count(csv_file: str, instrument_name: str, timezone, strategy_name: str = None) -> dict:
    """Count StopLoss exits today per account by reading the CSV log."""
    if not isinstance(csv_file, (str, bytes)):
        return {}
    try:
        if not os.path.exists(csv_file):
            return {}
    except Exception:
        return {}
    try:
        try:
            today = datetime.now(timezone).date()
        except Exception:
            today = datetime.now().date()
        df = pd.read_csv(csv_file)
        
        if 'timestamp' not in df.columns or 'instrument' not in df.columns:
            return {}
            
        df = df[df['instrument'] == instrument_name]
        if strategy_name and 'strategy' in df.columns:
            df = df[df['strategy'] == strategy_name]
            
        if df.empty:
            return {}
            
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df_today = df[df['timestamp'].dt.date == today]
        
        if df_today.empty:
            return {}
            
        # Match StopLoss or SL in signal or exit_reason
        sl_mask = pd.Series(False, index=df_today.index)
        if 'signal' in df_today.columns:
            sl_mask = sl_mask | df_today['signal'].astype(str).str.contains('StopLoss|SL', case=False, na=False)
        if 'exit_reason' in df_today.columns:
            sl_mask = sl_mask | df_today['exit_reason'].astype(str).str.contains('StopLoss|SL', case=False, na=False)
            
        df_sl = df_today[sl_mask]
        if df_sl.empty:
            return {}
            
        if 'account' not in df_sl.columns:
            df_sl['account'] = 'UNKNOWN_ACCOUNT'
            
        df_sl['minute'] = df_sl['timestamp'].dt.floor('min')
        counts = df_sl.groupby('account')['minute'].nunique().to_dict()
        return counts
    except Exception as e:
        import logging
        logging.error(f"[RESTORE] Failed to count SLs for {instrument_name}: {e}")
        return {}


# ========== STRATEGY 20: CALENDAR SPREAD OPTION RESOLVER ==========
def choose_calendar_spread_v2(api, spot_price: float, stance: str = "PUT_CALENDAR", instrument_config: dict = None) -> list:
    """
    Dynamic 3:1:1 Calendar Spread Option Contract Resolver using Dhan API v2.
    stance: "PUT_CALENDAR" (P options) or "CALL_CALENDAR" (C options).
    """
    if instrument_config is None:
        instrument_config = {}
        
    underlying_scrip = instrument_config.get("security_id", 13)
    target_long_p = instrument_config.get("target_long_premium", 200.0)
    target_short1_p = instrument_config.get("target_short1_premium", 150.0)
    target_short2_p = instrument_config.get("target_short2_premium", 450.0)
    max_strike_gap = instrument_config.get("max_strike_gap", 1000)
    
    option_type = 'P' if "PUT" in stance.upper() else 'C'
    
    # 1. Fetch Active Expiries via Dhan API v2
    expiry_list = api.get_expiry_list_v2(underlying_scrip=underlying_scrip)
    if not expiry_list or len(expiry_list) < 2:
        logger.error("[CALENDAR_V2] Failed to fetch active expiries from Dhan API v2.")
        return []
        
    weekly_expiry = expiry_list[0]
    
    # Monthly Expiry Determination (Last Tuesday/Thursday of the month)
    monthly_expiry = None
    for exp in expiry_list:
        # Pick expiry > 20 days out as monthly
        exp_dt = datetime.strptime(exp, "%Y-%m-%d")
        today_dt = datetime.now()
        if (exp_dt - today_dt).days >= 18:
            monthly_expiry = exp
            break
            
    if not monthly_expiry:
        monthly_expiry = expiry_list[-1]
        
    # Check Monthly Expiry Overlap (Last Week of Month Edge Case)
    if weekly_expiry == monthly_expiry:
        logger.warning(f"[CALENDAR_V2] Weekly Expiry equals Monthly Expiry ({weekly_expiry}). Shifting Monthly to Next Month!")
        for exp in expiry_list[1:]:
            if exp != weekly_expiry:
                monthly_expiry = exp
                break
                
    logger.info(f"[CALENDAR_V2] Expiries Selected -> Weekly: {weekly_expiry}, Monthly: {monthly_expiry}")
    
    # 2. Fetch Real-Time Option Chains
    chain_weekly = api.get_option_chain_v2(underlying_scrip=underlying_scrip, expiry=weekly_expiry)
    chain_monthly = api.get_option_chain_v2(underlying_scrip=underlying_scrip, expiry=monthly_expiry)
    
    if not chain_weekly or not chain_monthly:
        logger.error("[CALENDAR_V2] Option chain payload empty. Cannot resolve strikes.")
        return []
        
    # Helper to scan chain for best target premium strike
    def match_strike(chain_data, target_premium, opt_t):
        best_item = None
        best_diff = float('inf')
        
        # Parse chain items
        items = chain_data.get("oc", {}) if isinstance(chain_data, dict) else {}
        for strike_str, strike_data in items.items():
            try:
                strike_val = float(strike_str)
                opt_data = strike_data.get("ce" if opt_t == 'C' else "pe", {})
                ltp = float(opt_data.get("last_price", 0.0) or opt_data.get("ltp", 0.0))
                sec_id = str(opt_data.get("security_id", "") or opt_data.get("securityId", ""))
                lot_sz = safe_int(opt_data.get("lot_size", 65), 65)
                
                if ltp > 0 and sec_id:
                    diff = abs(ltp - target_premium)
                    if diff < best_diff:
                        best_diff = diff
                        best_item = {
                            "strike": strike_val,
                            "ltp": ltp,
                            "security_id": sec_id,
                            "lot_size": lot_sz
                        }
            except Exception:
                continue
        return best_item
        
    long_leg = match_strike(chain_monthly, target_long_p, option_type)
    short1_leg = match_strike(chain_weekly, target_short1_p, option_type)
    short2_leg = match_strike(chain_weekly, target_short2_p, option_type)
    
    if not long_leg or not short1_leg or not short2_leg:
        logger.error("[CALENDAR_V2] Failed to match all 3 premium legs in Option Chain.")
        return []
        
    # Ensure short legs do not overlap on the same strike (degenerate spread)
    if short1_leg['strike'] == short2_leg['strike']:
        logger.warning(f"[CALENDAR_V2] Strike Collision! Weekly Short 1 and Weekly Short 2 both matched strike {short1_leg['strike']}. Skipping Trade!")
        return []
        
    # 3. Apply Golden Constraint Safety Filter
    gap1 = abs(short1_leg['strike'] - long_leg['strike'])
    gap2 = abs(short2_leg['strike'] - long_leg['strike'])
    max_gap = max(gap1, gap2)
    
    if max_gap > max_strike_gap:
        logger.warning(f"[CALENDAR_V2] Golden Constraint Violated! Max Strike Gap {max_gap} > {max_strike_gap}. Skipping Trade!")
        return []
        
    lot_size = long_leg['lot_size']
    instrument_config['lot_size'] = lot_size
    
    logger.info(f"[CALENDAR_V2] 3:1:1 Leg Matching Success (Lot Size: {lot_size}):")
    logger.info(f"   -> Long Monthly (3 Lots): Strike {long_leg['strike']} @ LTP {long_leg['ltp']} (SecID: {long_leg['security_id']})")
    logger.info(f"   -> Short Weekly 1 (1 Lot): Strike {short1_leg['strike']} @ LTP {short1_leg['ltp']} (SecID: {short1_leg['security_id']})")
    logger.info(f"   -> Short Weekly 2 (1 Lot): Strike {short2_leg['strike']} @ LTP {short2_leg['ltp']} (SecID: {short2_leg['security_id']})")
    
    legs = [
        {
            "tag": "LONG_MONTHLY",
            "action": "BUY",
            "lots": 3,
            "quantity": 3 * lot_size,
            "security_id": long_leg['security_id'],
            "strike": long_leg['strike'],
            "expiry": monthly_expiry,
            "ltp": long_leg['ltp'],
            "option_type": option_type
        },
        {
            "tag": "SHORT_WEEKLY_1",
            "action": "SELL",
            "lots": 1,
            "quantity": 1 * lot_size,
            "security_id": short1_leg['security_id'],
            "strike": short1_leg['strike'],
            "expiry": weekly_expiry,
            "ltp": short1_leg['ltp'],
            "option_type": option_type
        },
        {
            "tag": "SHORT_WEEKLY_2",
            "action": "SELL",
            "lots": 1,
            "quantity": 1 * lot_size,
            "security_id": short2_leg['security_id'],
            "strike": short2_leg['strike'],
            "expiry": weekly_expiry,
            "ltp": short2_leg['ltp'],
            "option_type": option_type
        }
    ]
    
    return legs

