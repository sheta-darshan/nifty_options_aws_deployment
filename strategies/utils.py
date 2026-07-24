import numpy as np
import pandas as pd
import pandas_ta as ta

try:
    from numba import njit
except ImportError:
    def njit(func):
        return func

@njit
def _compute_st_dir_loop(close, basic_ub, basic_lb, start_idx):
    n = len(close)
    direction = np.ones(n, dtype=np.int8)
    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    
    # Init warm-up
    for i in range(start_idx):
        final_ub[i] = basic_ub[i] if not np.isnan(basic_ub[i]) else close[i]
        final_lb[i] = basic_lb[i] if not np.isnan(basic_lb[i]) else close[i]
        
    for i in range(start_idx, n):
        # Upper band
        if basic_ub[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]:
            final_ub[i] = basic_ub[i]
        else:
            final_ub[i] = final_ub[i-1]
            
        # Lower band
        if basic_lb[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]:
            final_lb[i] = basic_lb[i]
        else:
            final_lb[i] = final_lb[i-1]
            
        # Direction
        if close[i] > final_ub[i]:
            direction[i] = 1
        elif close[i] < final_lb[i]:
            direction[i] = -1
        else:
            direction[i] = direction[i-1]
            
    return direction

def fast_supertrend_dir(high, low, close, length, multiplier):
    hl2 = (high + low) / 2.0
    atr = ta.atr(high, low, close, length=length)
    if atr is None:
        return np.ones(len(close), dtype=np.int8)
    
    close_arr = close.values
    hl2_arr = hl2.values
    atr_arr = atr.values
    
    basic_ub = hl2_arr + multiplier * atr_arr
    basic_lb = hl2_arr - multiplier * atr_arr
    
    return _compute_st_dir_loop(close_arr, basic_ub, basic_lb, int(length))
