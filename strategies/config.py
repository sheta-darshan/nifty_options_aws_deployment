import pandas as pd

class BacktestConfig:
    def __init__(self):
        # Timeframe configs
        self.TIMEZONE = 'Asia/Kolkata'
        self.RUN_START = pd.to_datetime('09:20:00').time()
        
        # Strategy Toggles
        self.ENABLE_STRATEGY_1 = False
        self.ENABLE_STRATEGY_2 = False
        self.ENABLE_STRATEGY_3 = False   
        self.ENABLE_STRATEGY_4 = False
        self.ENABLE_STRATEGY_5 = False  
        self.ENABLE_STRATEGY_6 = False  
        self.ENABLE_STRATEGY_7 = False  
        self.ENABLE_STRATEGY_9 = False  
        self.ENABLE_STRATEGY_10 = False
        self.ENABLE_STRATEGY_11 = False
        self.ENABLE_STRATEGY_12 = False
        self.ENABLE_STRATEGY_13 = False
        self.ENABLE_STRATEGY_14 = True
        self.ENABLE_STRATEGY_15 = False
        self.ENABLE_STRATEGY_16 = False
        self.ENABLE_STRATEGY_17 = False
        self.ENABLE_STRATEGY_18 = False
        self.ENABLE_STRATEGY_19 = True
        
        # Risk parameters useful for backtest
        self.ATR_PERIOD = 14
        self.ATR_SL_MULTIPLIER = 1.4
        self.ATR_TP_MULTIPLIER = 4.0
        self.OPTION_DELTA = 0.5
        self.TRAIL_TRIGGER_ATR = 2.5
        self.TRAILING_JUMP = 0
        self.USE_DELTA_PROXY = False
        
        # Breakeven Stop Loss parameters
        self.USE_BREAKEVEN = False
        self.BREAKEVEN_TRIGGER_ATR = 1.0
        
        # Execution Leg Mode: "BUY", "SELL", or "BOTH"
        self.LEG_MODE = "BOTH"
        
        # Carry Forward (Overnight) Mode: False = Intraday SquareOff at 15:00, True = Hold Overnight
        # Enable dynamic strategy-based exits (e.g. exit on SuperTrend direction change in Strategy 4)
        import os
        self.CARRY_FORWARD = os.getenv("CARRY_FORWARD", "True").strip().upper() == "TRUE"
        self.USE_DYNAMIC_EXITS = os.getenv("USE_DYNAMIC_EXITS", "False").strip().upper() == "TRUE"

        self.ENABLE_STRATEGY_17 = False
        self.ENABLE_STRATEGY_18 = False
        self.ENABLE_STRATEGY_19 = False
        self.ENABLE_STRATEGY_20 = False
        
        # Resolve active strategy parameters to prevent collision
        active_strategy = "Strategy_3"
        for i in range(1, 21):
            if getattr(self, f"ENABLE_STRATEGY_{i}", False):
                active_strategy = f"Strategy_{i}"
                break
        
        # Strategy 12 relies on dynamic exits for time-based closures
        if active_strategy == "Strategy_12":
            self.USE_DYNAMIC_EXITS = True

        self.apply_strategy_defaults(active_strategy)

    def apply_strategy_defaults(self, strategy_name: str):
        """Apply default parameters for the specified strategy to prevent collision."""
        from strategies.registry import get_strategy_class
        try:
            strat_cls = get_strategy_class(strategy_name)
            defaults = strat_cls().get_default_params()
            for k, v in defaults.items():
                setattr(self, k, v)
        except Exception as e:
            pass
            
        # Ensure dynamic exits are enabled if Strategy 12 is active
        if strategy_name == "Strategy_12":
            self.USE_DYNAMIC_EXITS = True
            
        if strategy_name == "Strategy_14":
            self.RUN_START = pd.to_datetime('09:15:00').time()

