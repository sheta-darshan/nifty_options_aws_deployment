# SATP Strategy Development & Implementation Guide

Welcome to the strategy development documentation for the Smart Algorithmic Trading Platform (SATP). This guide explains how strategies are structured, how to build a custom strategy from scratch, and how to successfully register and execute it in both backtesting simulations and live trading environments.

---

## 1. Modular Strategy Architecture

SATP uses a modular, registry-based architecture located under the [strategies/](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/) folder. This design decouples signal calculation logic from the trading execution bot and backtester, allowing developers to create new strategies without touching core trade placement code.

```
                      ┌────────────────────────┐
                      │    BaseStrategy Class  │
                      └───────────┬────────────┘
                                  ▼
                      ┌────────────────────────┐
                      │    Custom Strategy     │ (e.g. Strategy_8)
                      └───────────┬────────────┘
                                  ▼
                      ┌────────────────────────┐
                      │   @register_strategy   │ (Appends to Registry)
                      └───────────┬────────────┘
                                  ▼
      ┌───────────────────────────┴───────────────────────────┐
      ▼                                                       ▼
┌───────────────────────────┐                           ┌───────────────────────────┐
│     Backtest Engine       │                           │     Live Trading Bot      │
│  (backtest_engine.py)     │                           │   (live_trade_fixed.py)   │
└───────────────────────────┘                           └───────────────────────────┘
```

### File Layout:
*   `strategies/base.py`: The abstract base class (`BaseStrategy`) outlining the API interface.
*   `strategies/registry.py`: Dynamic registry dictionary and decorators mapping strategy names to classes.
*   `strategies/config.py`: Backtest configurations. Loads strategy parameters dynamically using class defaults.
*   `strategies/strategy_X.py`: Standalone strategy files implementing mathematical and technical logic.

---

## 2. Step-by-Step Guide to Build a Strategy

To create a new strategy (e.g., **`Strategy_8`**), follow these steps:

### Step 1: Create the Strategy File
Create a new file `strategies/strategy_8.py` and implement the class structure below:

```python
import pandas as pd
import numpy as np
import pandas_ta as ta  # Technical indicators library
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy8(BaseStrategy):
    name = "Strategy_8"

    def get_default_params(self) -> dict:
        """Define default indicator parameters.
        These are dynamically loaded into Config at startup."""
        return {
            "S8_EMA_SHORT": 9,
            "S8_EMA_LONG": 21,
            "S8_RSI_LEN": 14,
            "S8_RSI_OB": 70,
            "S8_RSI_OS": 30,
            "ATR_PERIOD": 14
        }

    def get_optimization_grid(self) -> dict:
        """Define parameter ranges for the grid search optimizer (optimize_combined.py)."""
        return {
            "S8_EMA_SHORT": [5, 9, 12],
            "S8_EMA_LONG": [20, 21, 30],
            "S8_RSI_LEN": [14, 21]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        """Perform technical indicator calculations and generate signals.
        Must append 'Signal' (1=BUY, -1=SELL, 0=None), 'Signal_Source', and 'ATR' columns."""
        if df_spot.empty:
            return df_spot

        df = df_spot.copy()

        # 1. Resample to 5-minute candles to match execution timeframes and filter noise
        df_5min = df.resample('5min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        # 2. Calculate Indicators on 5-minute candles
        df_5min['EMA_S'] = ta.ema(df_5min['close'], length=self.params["S8_EMA_SHORT"])
        df_5min['EMA_L'] = ta.ema(df_5min['close'], length=self.params["S8_EMA_LONG"])
        df_5min['RSI'] = ta.rsi(df_5min['close'], length=self.params["S8_RSI_LEN"])
        df_5min['ATR'] = ta.atr(df_5min['high'], df_5min['low'], df_5min['close'], length=self.params["ATR_PERIOD"])

        # 3. Define Entry Rules
        # Long Entry: EMA cross over and RSI not overbought
        df_5min['Bullish_Signal'] = (df_5min['EMA_S'] > df_5min['EMA_L']) & (df_5min['RSI'] < self.params["S8_RSI_OB"])
        # Short Entry: EMA cross under and RSI not oversold
        df_5min['Bearish_Signal'] = (df_5min['EMA_S'] < df_5min['EMA_L']) & (df_5min['RSI'] > self.params["S8_RSI_OS"])

        # 4. PREVENT LOOKAHEAD BIAS (Shift indicator results by 1 candle)
        # Because we form signals on a candle close, execution happens at the open of the next minute.
        cols_to_shift = ['ATR', 'Bullish_Signal', 'Bearish_Signal']
        df_5min[cols_to_shift] = df_5min[cols_to_shift].shift(1)

        # 5. Join Indicators back to the 1-minute base DataFrame
        df = df.drop(columns=[c for c in cols_to_shift if c in df.columns], errors='ignore')
        df = df.join(df_5min[cols_to_shift], how='left')
        df[cols_to_shift] = df[cols_to_shift].ffill()

        # 6. Generate execution triggers
        df['Signal'] = 0
        df['S8_Signal'] = 0

        # Trigger on transitions (rising edge of signal)
        buy_trigger = (df['Bullish_Signal'] == True) & (df['Bullish_Signal'].shift(1) == False)
        sell_trigger = (df['Bearish_Signal'] == True) & (df['Bearish_Signal'].shift(1) == False)

        df.loc[buy_trigger, 'Signal'] = 1
        df.loc[buy_trigger, 'S8_Signal'] = 1
        
        df.loc[sell_trigger, 'Signal'] = -1
        df.loc[sell_trigger, 'S8_Signal'] = -1

        # Deduplicate to prevent repeated entries on consecutive minutes
        df['Signal'] = df['Signal'].where(
            ~df['Signal'].eq(df['Signal'].shift()) | df['Signal'].eq(0), 0
        )
        df['S8_Signal'] = df['S8_Signal'].where(
            ~df['S8_Signal'].eq(df['S8_Signal'].shift()) | df['S8_Signal'].eq(0), 0
        )

        df['Signal_Source'] = "None"
        df.loc[df['S8_Signal'] != 0, 'Signal_Source'] = self.name

        return df
```

---

## 3. Registering & Connecting to the System

Once your strategy class is built, link it to the platform:

### Step 1: Export in the `__init__.py` file
Open [strategies/\_\_init\_\_.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/__init__.py) and add your strategy module import at the bottom:
```python
# Import subclasses to trigger registration
from . import strategy_1
...
from . import strategy_8  # Add this line
```

### Step 2: Add Config Toggles
Add master enable toggles to both backtest and live config files:
1.  **Backtesting Config**: Open [strategies/config.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/config.py) and define:
    ```python
    self.ENABLE_STRATEGY_8 = False
    ```
2.  **Live Trading Bot Config**: Open [trading_bot/config.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/config.py) and define:
    ```python
    self.ENABLE_STRATEGY_8 = False
    ```
3.  Ensure the loop ranges checking active strategies match the new length (e.g., if you added Strategy 8, update checks to range `1 to 9`).

---

## 4. Backtesting & Optimizing Your Strategy

### Phase 1: Baseline Backtest Validation
Verify that your signal calculations don't throw syntax or execution errors:
```powershell
# Run the multi-instrument tool on a specific strategy
..\venv\Scripts\python.exe run_multi_instrument_backtest.py NIFTY --strategy 8 --days 30
```

### Phase 2: Run Parameter Optimization
1. Run the optimizer command line utility by specifying your target strategy name using the `-s` or `--strategy` argument:
   ```powershell
   ..\venv\Scripts\python.exe optimize.py --strategy Strategy_8
   ```
2. The optimizer will automatically partition the dataset into Train/Test splits, run Stage 1 and Stage 2 joint sweeps on the Train split, and validate robustness on the Out-of-Sample Test split (Stage 3).

---

## 5. Critical Development Best Practices

To ensure your strategy executes successfully without losing money or failing due to broker constraints:

1.  **Prevent Lookahead Bias**: Always apply `.shift(1)` to indicators computed on historical candle intervals. Trading decisions must be made on *completed* candles. Checking indices without a shift will simulate unrealistic profits by trading on prices that haven't occurred yet in real-time.
2.  **Handle Missing Data**: Always verify that your indicator columns handle `NaN` inputs gracefully. Populate missing data using forward filling (`.ffill()`) before running comparative conditional statements.
3.  **Include the ATR Column**: Every strategy must calculate and append an `ATR` column to the returned spot DataFrame (usually resampled to 5-minute bars and shifted by 1 to prevent lookahead). This column is required by the backtesting engine and live trading bot to compute stop losses, targets, and trailing stops under various exit modes (such as ATR and SWING).
4.  **Sanitize Indicator Casting**: Ensure any parameters used by rolling windows are cast explicitly (e.g. integer casting). Floating values passed to index lengths can crash technical libraries.
5.  **Snap Tick Sizes**: Snapping your order limits to the Indian market tick size (e.g., `round(price * 20) / 20.0` for 0.05 intervals) prevents Dhan API placement rejections.
6.  **Deduplicate Triggers**: Never allow consecutive duplicate signal values (like multiple `1` triggers in a row) to pass. Always use the `.where(...)` deduplicator shown in the tutorial.

---

## 6. Strategy-Defined Dynamic Exits

SATP supports **Dynamic Strategy-Based Exits** as an alternative to (or in conjunction with) broker-side fixed stop-losses and targets. 

To implement dynamic exits in your custom strategy:
1. Generate two additional boolean columns in your `generate_signals` output:
   * `Exit_Long` (bool): `True` when active long/bullish positions should be squared off immediately.
   * `Exit_Short` (bool): `True` when active short/bearish positions should be squared off immediately.
2. Ensure you apply lookahead prevention (e.g., shift by 1 bar on their native timeframe) before joining and outputting these columns to the 1-minute base DataFrame.
3. Enable the feature by setting `USE_DYNAMIC_EXITS=True` in your `.env` file or configuration class.

For reference, see `strategies/strategy_4.py` which triggers `Exit_Long` and `Exit_Short` when the 5-minute SuperTrend direction changes. When `USE_DYNAMIC_EXITS` is active, the execution engine cancels any pending broker-side safety stop-loss/target orders and places a `MARKET` close order to square off the position immediately.

---

## 7. Strategy Exit Modes (ATR vs. SWING vs. SWING_CONTRACT vs. POINTS)

Strategies in SATP can use one of four primary exit execution modes configured via `instruments.json`:

1. **ATR Mode (`"exit_mode": "ATR"`)**:
   - Stop Loss and Targets are scaled and snapped directly to the option premium or stock execution price.
   - Triggers order execution directly on the exchange utilizing broker-managed Bracket/Super Orders.
   - Recommended for strategies with high-volatility premium trends where structural underlying charts are secondary to fast execution.

2. **SWING Mode (`"exit_mode": "SWING"`)**:
   - Stops and Targets are defined in terms of the underlying Spot chart structures (e.g., recent 10-candle low for support or high for resistance, padded with an ATR buffer).
   - Keeps option execution orders completely independent on Dhan (placing standard limit/market entry orders) and relies on the bot's high-frequency local Python monitor loop.
   - Triggers exit market orders only when the Spot LTP invalidates the support/resistance structure.
   - Recommended for options buying strategies to prevent premium whipsaws, spread sweeps, and time-decay stop-outs.

3. **SWING_CONTRACT Mode (`"exit_mode": "SWING_CONTRACT"`)**:
   - Stops and Targets are defined in terms of the traded contract's own chart structures (e.g., recent 10-candle low of the option contract premium or stock, padded with an ATR buffer calculated on the contract's premium candles).
   - Places standard limit/market entry orders on the broker and monitors contract-level exits via the bot's high-frequency local Python monitor loop.
   - Triggers exit market orders only when the contract LTP invalidates the contract's swing structures.
   - Supports fixed profit targets `profit_target_buy` / `profit_target_sell` defined in `instruments.json` (INR amount converted to contract points by dividing by `lot_size`), overriding dynamic ATR-based targets if configured `> 0`.
   - Recommended for options trading where stop losses and targets need to be measured, trailed, and managed directly on the traded derivative contract premium chart.

4. **POINTS Mode (`"exit_mode": "POINTS"`)**:
   - Stop Loss, Take Profit, and Trailing Stops are defined as fixed premium or stock points directly in `instruments.json` (e.g. `points_sl_buy`, `points_target_buy`, `points_trail_buy`).
   - Places standard entry orders on the broker and monitors exit thresholds locally via the Python bot's high-frequency monitoring loop, executing market close orders instantly.
   - Completely bypasses broker-side Bracket Order leg restrictions, strike-price boundaries, and intraday-only limitations.
   - Recommended for strategies where risk parameters are structured explicitly around option premium or stock pricing points (e.g., risking 15 points to target 30 points, with a 5-point trailing jump).

---

## 8. Broker-Side vs. Local Monitoring (`local_exit_monitoring`)

For certain exit modes (`ATR` and `POINTS`), you can choose whether the Stop Loss, Take Profit, and Trailing stop levels are monitored locally on your machine by the Python bot (`local_exit_monitoring: true`) or placed directly on the broker's exchange servers as Bracket/Super Orders (`local_exit_monitoring: false`).

*   **`local_exit_monitoring: true`**:
    *   **How it works**: Places a standard entry limit/market order on Dhan. Once filled, the bot tracks the option premium or stock price in a high-frequency polling loop. When a target, stop loss, or trailing stop trigger is hit, the bot cancels any pending orders for the contract and sends a market square-off order.
    *   **Advantages**: Bypasses broker-side Bracket Order restrictions (e.g., tick size alignment issues, minimum distance limits, strike selection limits, and product type constraints like forced intraday square-offs).
    *   **Defaults**: Automatically set to `true` if `exit_mode` is `"SWING"`, `"SWING_CONTRACT"`, or `"POINTS"`.
*   **`local_exit_monitoring: false`**:
    *   **How it works**: Places the entry order along with linked stop loss, take profit, and trailing stop points directly using Dhan's native Bracket/Super Order API.
    *   **Advantages**: Exits execute instantly on exchange matching engines, even if your local bot loses power or internet connectivity.
    *   **Defaults**: Automatically set to `false` if `exit_mode` is `"ATR"`.

---

## 9. Strategy-Specific Config Overrides

To run multiple strategies on the same underlying instrument without colliding on risk parameters (like stop loss, target, or daily trade limits), SATP allows defining nested strategy overrides inside [instruments.json](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/instruments.json) using the `"strategy_overrides"` key.

When a strategy is active:
1. The configuration loader merges any matching parameters defined inside `"strategy_overrides": { "<strategy_name>": { ... } }` into the active instrument configuration dictionary.
2. If no overrides are found, it falls back to the base configurations.
3. This is supported in both live trading bots (`trading_bot/config.py`) and backtest simulation engines (`backtest_engine.py`).

Refer to the [Configuration Guide](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/CONFIGURATION_GUIDE.md#7-strategy-specific-configuration-overrides-centralized) for a detailed list of overridable parameters and json examples.

---

## 10. Strategy 9: Reverse-Engineered Decision Tree Strategy

Strategy 9 is the platform's first machine-learning-derived breakout strategy. It was developed by reverse-engineering 5 years of historical NIFTY 1-minute spot data (over 520,000 candles) using a Decision Tree Classifier.

### Development Methodology
The reverse engineering process is automated via [reverse_engineer_nifty.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/scratch/reverse_engineer_nifty.py):
1. **Labeling Engine**: Scans each historical minute $t$. If price moves $+35$ points (target) within a 25-candle horizon before experiencing a $-25$ point drawdown (stop loss), the bar is labeled as a **BUY (1)**. If price moves $-35$ points before a $+25$ point drawdown, it is labeled as a **SELL (-1)**. Otherwise, it is labeled as **NONE (0)**.
2. **Feature Computation**: Technical features (RSIs, EMA distances, Bollinger Band Widths, MACD, and candle price action indicators) are computed.
3. **Decision Tree Extraction**: A pruned Decision Tree Classifier (`max_depth=4`, `min_samples_leaf=200`, `class_weight='balanced'`) is fitted. Test-set indices are mapped back to leaf nodes to calculate true unweighted out-of-sample win rates (precisions).

### Implemented Rules in [strategy_9.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_9.py)
*   **BUY Setup**: Triggers when a bullish candle closes significantly below the 50-period EMA.
    ```python
    (close > open) and (body_size_pct > S9_BODY_MIN_BUY) and (ema_50_diff_pct <= S9_EMA_DIFF_MAX_BUY)
    ```
    - *Default parameters*: `S9_BODY_MIN_BUY = 0.0578%`, `S9_EMA_DIFF_MAX_BUY = -0.3088%` (tested win rate: **42.76%** vs. 14.8% baseline).
*   **SELL Setup**: Triggers when a bearish candle closes below the 50-period EMA.
    ```python
    (close < open) and (body_size_pct > S9_BODY_MIN_SELL) and (ema_50_diff_pct <= S9_EMA_DIFF_MAX_SELL)
    ```
    - *Default parameters*: `S9_BODY_MIN_SELL = 0.0430%`, `S9_EMA_DIFF_MAX_SELL = -0.1578%` (tested win rate: **35.15%** vs. 17.6% baseline).

---

## 11. Advanced Strategies (16–19) & Institutional Quant Machine Learning Pipeline

SATP includes advanced quantitative strategies and machine learning integration:

### Strategy 16: 18 SMMA Smooth Trend Breakout
* **Logic**: Uses a 5-minute resampled 18-period Smoothed Moving Average (SMMA) trend band.
* **Entry**: Triggers `BUY` on bullish crossover of 18 SMMA; `SELL` on bearish crossover.
* **Exit**: POINTS mode (fixed SL & Target) or dynamic SMMA direction reversal.

### Strategy 17: High-Conviction Opening Scalp
* **Logic**: Opening window (09:15–09:45) volatility expansion scalp strategy.
* **Entry**: Identifies initial candle momentum expansion using 1-minute ATR breakouts and high volume surges.
* **Exit**: Fast scalp target (30 points) with strict 15-point stop loss.

### Strategy 18: SMA Breakout with 09:45 Time Gate
* **Logic**: Time-gated opening range SMA breakout strategy.
* **Time Gate**: Evaluates candle patterns strictly after `09:45 AM` to allow early opening noise to settle.
* **Entry**: Triggers breakout entry on 5-minute SMA trend confirmation.

### Strategy 19: Institutional Quant Machine Learning Strategy (`Strategy_19`)
* **Overview**: Institutional machine-learning-gated trend and opening strategy trained on 5+ years of Nifty 1-minute data (538,465 candles from 2021 to 2026).
* **Noise Reduction**: Computes Mean Price $P_{\text{mean}} = \frac{\text{Open} + \text{High} + \text{Low} + \text{Close}}{4}$ before indicator computation to filter out high-frequency noise.
* **Feature Engineering Matrix**:
  - `rsi`: 9-period RSI on Mean Price
  - `fast_ema` / `slow_wma`: 3-period EMA and 21-period WMA on RSI
  - `wma_diff`: Fast EMA - Slow WMA difference
  - `adx` / `dmp` / `dmn`: 14-period Directional Movement Index
  - `atr` / `rel_atr`: 14-period ATR relative to close price
  - `vwap_dist`: Percentage distance from intraday VWAP `(close - vwap)/vwap`
  - `gap_pct`: Overnight gap magnitude `(open - prev_day_close)/prev_day_close`
  - `c1_range_ratio`: Opening 5-minute Candle 1 range ratio relative to open
  - `minute_of_day` & `day_of_week`: Intraday timing features
* **Walk-Forward ML Classifier**: XGBoost Multi-Class Classifier trained with 5-fold TimeSeriesSplit CV.
* **Probability Gating**: Executes trades only when model prediction probability $P_{\text{trend}} \ge 42\%$ (`min_ml_prob`), eliminating 300+ weak sideways trades.
* **Performance**: Produced **+Rs. 106,600.86 Net Profit** with an average gain of **+$1,665.64 per trade** in multi-strategy portfolio backtesting.

---

## 11. Strategy 6: Range Filter [DW] (TradingView Volatility-Gated Trend Filter)

Strategy 6 is an implementation of DonovanWall's **Range Filter [DW]** TradingView indicator. It is designed to filter out minor price action noise to capture clean trends.

### Core Mathematical Components

1. **Range Sizing (`rng_size`)**:
   Calculates the threshold distance for gating price action based on volatility metrics. Supported scale types include:
   - **Average Change** (Default): Multiplies range size by the EMA of absolute differences (`abs(price - price[1])`).
   - **ATR**: Multiplies range size by the EMA of the True Range.
   - **Standard Deviation**: Multiplies range size by the rolling population standard deviation.
   - **% of Price**: Multiplies range size by a percentage of the close price.
   - **Points / Pips / Ticks**: Uses standard tick/pip step sizes.
   - **Absolute**: Uses a fixed raw point value.

2. **Filter Type Logic**:
   - **Type 1** (Original Formula): Adjusts the filter level if the high minus range exceeds the previous filter, or low plus range falls below the previous filter.
   - **Type 2**: Steps the filter level in discrete multiples of the calculated range `r` when price breaches the bounds.

3. **Conditional Sampling EMA (`Cond_EMA`)**:
   An optional filter value averaging module. When `S6_AVERAGE_CHANGES` is active, the strategy takes a new sample only when the underlying filter changes value, creating an averaged volatility-adaptive trend line.

### Implemented Parameters in [strategy_6.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_6.py)

* **`S6_FILTER_TYPE`**: `"Type 1"` or `"Type 2"`
* **`S6_MOVEMENT_SOURCE`**: `"Close"` (uses close prices) or `"Wicks"` (uses high/low wicks)
* **`S6_RANGE_SIZE`**: Quant quantity multiplier (default: `2.618`)
* **`S6_RANGE_SCALE`**: Sizing model (default: `"Average Change"`)
* **`S6_RANGE_PERIOD`**: Lookback length for ATR, Average Change, and Standard Deviation (default: `14`)
* **`S6_SMOOTH_RANGE`**: Boolean toggle to smooth calculated range size (default: `True`)
* **`S6_SMOOTH_PERIOD`**: EMA smoothing period for range size (default: `27`)
* **`S6_AVERAGE_CHANGES`**: Boolean toggle to average filter changes using conditional EMA (default: `False`)
* **`S6_AVERAGE_SAMPLES`**: Samples count for conditional EMA averaging (default: `2`)
* **`ATR_PERIOD`**: Backtesting exit compatibility (default: `14`)

---

## 11. Strategy Timing & Timeframe Alignment Guidelines

To guarantee that a strategy's backtest results translate perfectly into live trading performance, signal timestamps must be mapped correctly onto the 1-minute base DataFrame.

### 1. The Core Ingestion Rules
* **1-Minute Base**: The live bot (`live_trade_fixed.py`) and the backtest engine (`backtest_engine.py`) both evaluate decisions on a 1-minute timeline.
* **Look-Ahead Bias Prevention**: Decisions must only be made on *completed* candles. Always shift indicator calculations by 1 candle relative to their timeframe before making conditional decisions (e.g., `df_5m['indicator'] = df_5m['indicator'].shift(1)`).
* **The Index + 1 Execution Rule**:
  * **Backtest**: If a signal is detected at index `i`, the simulator confirms the signal at the close of `i` and executes the order at the open of `i + 1`.
  * **Live Bot**: The live data pipeline drops the active incomplete candle, checks the last completed candle (index `i`), detects the signal, and places the order at `i + 1`.

### 2. Alignment Patterns for Different Timeframes

Use the following design patterns to align your strategy timeframes:

#### A. Resampled 5-Minute Strategies (e.g., Strategy 3 & Strategy 13)
* **Calculation**: Resample the 1-minute DataFrame to 5-minute intervals. Calculate your indicators and place signals at the 5-minute bar index (e.g., `09:15:00` represents the `09:15:00 - 09:20:00` bar).
* **Signal Mapping**: Map the 5-minute signal back to the **last 1-minute candle of the 5-minute bar** (`target_idx = idx + 4 minutes` $\rightarrow$ `09:19:00`).
* **Execution**:
  * **Backtest**: Detects the signal at `09:19:00` and enters at `i + 1` (`09:20:00` open).
  * **Live Bot**: At `09:20:05` (after the `09:19:00` candle has closed), it detects the signal at `09:19:00` and enters.
  * **Outcome**: Perfect alignment at exactly `09:20:00`.

#### B. Daily Start-of-Session Strategies (e.g., Strategy 11 & Strategy 14)
* **Calculation**: Yesterday's daily OHLC metrics are used to generate a signal for today's market session.
* **Signal Mapping**: Map the signal to the **first 1-minute candle of today's session** (`09:15:00`).
* **Execution**:
  * **Backtest**: Detects signal at `09:15:00` and enters at `09:16:00` open.
  * **Live Bot**: Runs at `09:16:05` (after the `09:15:00` candle closes), spots the signal at index `09:15:00`, and fires immediately.
  * **Outcome**: Perfect execution at exactly `09:16:00`.

#### C. Intraday Specific-Time Strategies (e.g., StrategyBTST)
* **Calculation**: If checking indicators at a specific time of day (e.g., checking a completed 5-minute candle at 2:55 PM):
  * **Incorrect**: Directly checking `df.index.time == Timestamp("14:50:00")` on 1-minute data will check a 1-minute candle starting at 2:50 PM.
  * **Correct**: Resample the spot DataFrame to 5-minute bars first. A candle labeled `14:50:00` represents the completed `14:50:00 - 14:55:00` bar. Apply conditions to `df_5m` and map the signal back to the 1-minute index at `14:54:00`.
  * **Outcome**: Both backtest and live trading will enter at exactly `14:55:00` open.

---

## 12. Reference: Summary of All Implemented Strategies

Here is a complete catalog of all strategies registered in the platform under `strategies/`. Use this as a reference when selecting models for backtesting or configuring live trading bot loops:

| Strategy ID | Class Name | Technical Concept | Target Timeframe | Key Entry Conditions & Logic |
| :--- | :--- | :--- | :--- | :--- |
| **Strategy_1** | [Strategy1](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_1.py) | Supertrend + EMA + ADX | 5-Minute (Resampled) | Enters on a bullish (1) or bearish (-1) Supertrend direction crossover when price is on the correct side of the EMA filter (e.g. above for calls, below for puts) and ADX trend strength exceeds the threshold (default: 18). |
| **Strategy_2** | [Strategy2](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_2.py) | Dual Supertrend Pullback | 5-Minute (Resampled) | Triggers on pullbacks. Requires the 15-minute Supertrend trend to be bullish/bearish, then enters on a shorter 5-minute Supertrend pullback confirmation combined with Stochastics/RSI oversold/overbought levels. |
| **Strategy_3** | [Strategy3](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_3.py) | Triple Momentum Breakout | 5-Minute (Resampled) | Enters when EMA, Supertrend, and RSI all align bullishly (for Calls) or bearishly (for Puts), with an added `TM_MAX_STRETCH` limit to avoid entering when the price has moved too far from the base EMA. |
| **Strategy_4** | [Strategy4](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_4.py) | WMA/SMA Trend Crossover | 5-Minute (Resampled) | Standard WMA 87 vs WMA 200 crossover system. Also emits `Exit_Long` and `Exit_Short` dynamic signals when the short-term Supertrend flips against the active trade direction. |
| **Strategy_5** | [Strategy5](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_5.py) | Volatility-Adjusted Keltner | 5-Minute (Resampled) | Monitors price boundaries relative to a dynamic Keltner Channel. Executes breakout trades when price closes outside the bands and Stochastic/RSI support the momentum. |
| **Strategy_6** | [Strategy6](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_6.py) | Range Filter [DW] | 1-Minute / 5-Minute | Volatility-gated trend tracker based on DonovanWall's TradingView indicator. Smooths price action wicks and filters noise using dynamic average change scales. |
| **Strategy_7** | [Strategy7](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_7.py) | Derivative Oscillator | 5-Minute (Resampled) | Evaluates double-smoothed RSI momentum differences (Derivative Oscillator). Enters on zero-line crossover after a breakout validation window has elapsed. |
| **Strategy_8** | [Strategy8](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_8.py) | Daily 9:30 AM Breakout | 1-Minute | Morning opening breakout execution. Emits a fixed buy signal (Call or Put based on config parameter `S8_SIGNAL_VAL`) on exactly the 09:30:00 1-minute candle. |
| **Strategy_9** | [Strategy9](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_9.py) | ML Decision Tree Rules | 1-Minute | Uses a ruleset derived from a 5-year Decision Tree Classifier on NIFTY 1-minute data, looking for extreme standard deviations below/above the EMA 50 on green/red candles. |
| **Strategy_10** | [Strategy10](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_10.py) | Hilega Milega Reversal | 5-Minute (Resampled) | Re-implements Nitish Sir's high-probability Hilega Milega model. Uses RSI 9 crossovers with its EMA 3 and WMA 21 lines to determine trend exhaustions. |
| **Strategy_11** | [Strategy11](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_11.py) | Gap Fade & Reversal | Daily/1-Minute | Fades the day's opening gap if it is in agreement with a reversal of yesterday's net candle direction. Triggers a single signal at the session open. |
| **Strategy_12** | [Strategy12](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_12.py) | 1m RSI-100 Mean Reversion | 1-Minute | Enters counter-trend when a high-period RSI (100) crosses the mid-level (50.0) from extreme oversold (<40) or overbought (>60) territory, supported by a VWAP cross. |
| **Strategy_13** | [Strategy13](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_13.py) | 5m Supertrend-EMA Cross | 5-Minute (Resampled) | A clean crossover system between Supertrend (10, 3.0) and EMA 50, filtered by ADX (14) trend strength. Built specifically for high-efficiency option buying. |
| **Strategy_14** | [Strategy14](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_14.py) | Nifty MCI Reversal | Daily/1-Minute | Evaluates rolling Market Complexity Index (MCI). Triggers a counter-trend position at the next day's open (`09:16:00`) when yesterday's MCI $\ge 75$. |
| **Strategy_BTST** | [StrategyBTST](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strategies/strategy_btst.py) | Buy Today Sell Tomorrow | Daily/5-Minute | Analyzes afternoon price action (at 14:50:00). Triggers CE/PE buy entries to capture overnight gap returns when price breaks previous-day highs/lows with strong RSI. |





