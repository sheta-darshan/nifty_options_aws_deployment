"""
Strategy 20: Math-Based 3:1:1 Calendar Spread Strategy
Based on Prof. Chirag Jain's quantitative option framework.

Core Principles:
1. Fair Value CAGR Baseline: V_Fair(t) = 7511 * (1 + 0.117)^(years since 2020-03-24)
2. Market Regime Stance:
   - Upper Zone (ATH Extension, Spot / V_Fair > 1.25): PUT Calendar Spread (reversion down expected)
   - Lower Zone (Severe Dip, Spot / V_Fair < 0.95): CALL Calendar Spread (reversion up expected)
   - Middle Zone (Neutral Fair Value): CALL or PUT Calendar Spread based on short-term trend
3. 3:1:1 Ratio Structure:
   - 3 Lots Monthly Long Option (~200 target premium)
   - 1 Lot Weekly Short Option (~150 target premium, Strike A)
   - 1 Lot Weekly Short Option (~450 target premium, Strike B)
4. Golden Constraint Filter:
   - Max strike gap between Short and Long legs <= 1,000 points.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy_20(BaseStrategy):
    """
    Math-Based 3:1:1 Calendar Spread Strategy (Strategy 20)
    """
    name = "Strategy_20"
    
    def get_default_params(self) -> dict:
        return {
            "base_covid_low": 7511.0,
            "cagr_rate": 0.117,
            "cagr_base_date": "2020-03-24",
            "target_long_premium": 200.0,
            "target_short1_premium": 150.0,
            "target_short2_premium": 450.0,
            "max_strike_gap": 1000,
            "upper_threshold": 1.25,
            "lower_threshold": 0.95,
            "timeframe": "5min"
        }
        
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.params = params or self.get_default_params()
        self.name = "Strategy_20"
        
        # Strategy Parameters
        self.base_covid_low = self.params.get("base_covid_low", 7511.0)
        self.cagr_rate = self.params.get("cagr_rate", 0.117)
        self.cagr_base_date = self.params.get("cagr_base_date", "2020-03-24")
        
        self.target_long_premium = self.params.get("target_long_premium", 200.0)
        self.target_short1_premium = self.params.get("target_short1_premium", 150.0)
        self.target_short2_premium = self.params.get("target_short2_premium", 450.0)
        self.max_strike_gap = self.params.get("max_strike_gap", 1000)
        
        self.upper_threshold = self.params.get("upper_threshold", 1.25)
        self.lower_threshold = self.params.get("lower_threshold", 0.95)

    def calculate_fair_value(self, current_datetime: datetime) -> float:
        """
        Calculate 11.7% CAGR baseline fair value from 2020 COVID bottom.
        """
        base_dt = datetime.strptime(self.cagr_base_date, "%Y-%m-%d")
        days_elapsed = (current_datetime - base_dt).days
        years_elapsed = max(0.0, days_elapsed / 365.25)
        fair_value = self.base_covid_low * ((1.0 + self.cagr_rate) ** years_elapsed)
        return float(fair_value)

    def determine_regime(self, current_spot: float, current_datetime: datetime, trend_slope: float = 0.0) -> str:
        """
        Determine market valuation regime:
        - PUT_CALENDAR: Market extended above fair value baseline (ATH extension)
        - CALL_CALENDAR: Market depressed below fair value baseline (Crash/Dip)
        - Middle Zone: Assigned based on short-term trend slope
        """
        fair_val = self.calculate_fair_value(current_datetime)
        ratio = current_spot / fair_val if fair_val > 0 else 1.0
        
        if ratio > self.upper_threshold:
            return "PUT_CALENDAR"
        elif ratio < self.lower_threshold:
            return "CALL_CALENDAR"
        else:
            return "PUT_CALENDAR" if trend_slope >= 0 else "CALL_CALENDAR"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate strategy signals for DataFrame.
        Outputs:
        - 'Signal': +1 for CALL_CALENDAR, -1 for PUT_CALENDAR, 0 for Neutral
        - 'regime': Stance string ('CALL_CALENDAR' or 'PUT_CALENDAR')
        - 'fair_value': Fair value baseline float
        """
        df = df.copy()
        if 'close' not in df.columns:
            df['Signal'] = 0
            return df

        # Calculate 10-period momentum for middle zone regime determination
        df['trend_10'] = df['close'].diff(10)
        
        signals = []
        regimes = []
        fair_vals = []
        
        for idx, row in df.iterrows():
            # Get current timestamp
            dt_obj = None
            if 'timestamp' in df.columns:
                ts = row['timestamp']
                if isinstance(ts, str):
                    try:
                        dt_obj = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    except:
                        dt_obj = datetime.strptime(ts[:10], "%Y-%m-%d")
                elif hasattr(ts, 'to_pydatetime'):
                    dt_obj = ts.to_pydatetime()
            if dt_obj is None:
                dt_obj = datetime.now()
                
            spot = float(row['close'])
            slope = float(row['trend_10']) if pd.notna(row['trend_10']) else 0.0
            
            fair_val = self.calculate_fair_value(dt_obj)
            regime = self.determine_regime(spot, dt_obj, slope)
            
            # Emit entry signal ONLY on weekly cycle start (Tuesday/Thursday at 09:20 AM)
            is_weekly_entry_time = (dt_obj.weekday() in [1, 3]) and (dt_obj.hour == 9 and dt_obj.minute == 20)
            if is_weekly_entry_time:
                sig = 1 if regime == "CALL_CALENDAR" else -1
            else:
                sig = 0
                
            signals.append(sig)
            regimes.append(regime)
            fair_vals.append(fair_val)
            
        df['Signal'] = signals
        df['signal'] = signals
        df['regime'] = regimes
        df['fair_value'] = fair_vals
        
        return df

    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.generate_signals(df)

def get_strategy_instance(params: Dict[str, Any] = None):
    return Strategy_20(params)
