# F&O & Stock Backtesting & Optimization: Complete Self-Service Guide

Welcome to the SATP Backtesting and Parameter Optimization system. This document provides a comprehensive guide on how our backtest engine, targeted pre-fetcher, multi-instrument runner, and multi-layer optimizers function. It details the exact steps to configure, run, and analyze backtests for any instrument in either **`OPTION`** or **`STOCK`** execution modes.

---

## 1. System Architecture: The Optimization Pipeline

Our system consists of five primary components designed to work together to deliver 100% accurate backtests at extreme speeds (sub-10 seconds per run) by combining targeted pre-fetching, stock-mode shortcuts, and in-memory caches:

```
                  ┌───────────────────────┐
                  │   instruments.json    │◄─────────────────┐
                  └───────────┬───────────┘                  │
                              │ Read Config                  │
                              ▼                              │
                  ┌───────────────────────┐                  │
                  │  prefetch_options.py  │                  │
                  └───────────┬───────────┘                  │
                              │ Pre-downloads options        │
                              ▼                              │ Apply Optimized
                  ┌───────────────────────┐                  │ Parameters
                  │     contract_cache/   │                  │ (SL, Trail, TP,
                  └───────────┬───────────┘                  │  Indicators)
                              │ High-speed local cache       │
                              ▼                              │
                  ┌───────────────────────┐                  │
                  │      optimize.py      │──────────────────┘
                  │                       │
                  └───────────────────────┘
```

### Script Directory Map
*   **[instruments.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/instruments.json)**: The centralized configuration store. Holds structural, execution mode, and risk parameters for each index or stock. Both the live trading bot (`live_trade_fixed.py`) and backtest scripts read this file directly.
*   **[backtest_engine.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/backtest_engine.py)**: Core simulation engine. Manages trade execution, entry slippage, SL/trailing SL triggers, and Indian NSE regulatory charges. Powered by module-level fast dictionary caching to achieve near-instant lookups.
*   **[run_multi_instrument_backtest.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/run_multi_instrument_backtest.py)**: High-level backtest execution command tool. Allows backtesting multiple instruments over custom timeframes, strategies, and leg configurations in one command.
*   **[prefetch_options.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/prefetch_options.py)**: Targeted options pre-fetcher. Runs indicator signals on spot data and downloads/stitches only the option contracts required for active signal dates. **Automatically skipped when instruments are in STOCK mode.**
*   **[optimize.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/optimize.py)**: Command-line multi-stage walk-forward parameter optimizer. Executes joint coarse-to-fine grids on the training split, and validates robustness on the testing split (Out-of-Sample) in a single pass.

---

## 2. Configuration (`instruments.json` & `.env`)

To configure any index or stock, open [instruments.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/instruments.json). You can trade/test the asset in either **`OPTION`** or **`STOCK`** mode.

### A. Options Execution Configuration (`"execution_mode": "OPTION"`)
Used for indices (NIFTY, BANKNIFTY) or stocks where you want to trade Call (CE) or Put (PE) options:
```json
  "NIFTY": {
    "security_id": 13,
    "type": "INDEX",
    "exchange_segment": "IDX_I",
    "option_segment": "NSE_FNO",
    "execution_mode": "OPTION",
    "lot_size": 65,
    "num_lots_buy": 1,
    "num_lots_sell": 1,
    "strike_step": 100,
    "strike_offset": 0,
    "strike_offset_buy": 0,
    "strike_offset_sell": 2,
    "option_strategy_mode": "DIRECT",
    "strategy_leg_width": 1,
    "num_strikes": 1,
    "expiry_index": 0,
    "option_delta": 0.5,
    "sl_mult_buy": 2.5,
    "sl_mult_sell": 5.0,
    "tp_mult_buy": 1.0,
    "tp_mult_sell": 2.5,
    "trailing_mult_buy": 0.0,
    "trailing_mult_sell": 0.0,
    "enabled": 1,
    "daily_limit": 1
  }
```

### B. Stock Execution Configuration (`"execution_mode": "STOCK"`)
Used to trade equity shares directly (Long on Buy signal, Short/Intraday on Sell signal):
```json
  "BHEL": {
    "security_id": 438,
    "type": "STOCK",
    "exchange_segment": "NSE_EQ",
    "option_segment": "NSE_FNO",
    "execution_mode": "STOCK",
    "stock_qty_override": 100,
    "lot_size": 1,
    "num_lots_buy": 1,
    "num_lots_sell": 1,
    "sl_mult_buy": 1.5,
    "sl_mult_sell": 1.5,
    "tp_mult_buy": 2.0,
    "tp_mult_sell": 2.0,
    "trailing_mult_buy": 0.5,
    "trailing_mult_sell": 0.5,
    "enabled": 1,
    "daily_limit": 2
  }
```

### C. Strategy-Specific Config Overrides
SATP supports strategy-specific parameter overrides. You can define custom risk limits, targets, allowed actions, or execution modes for specific strategies by adding a `"strategy_overrides"` dictionary inside the instrument's config block. The backtester dynamically loads these values matching the active strategy:

```json
  "NIFTY": {
    "security_id": 13,
    "points_sl_buy": 24,
    "points_target_buy": 75,
    "strategy_overrides": {
      "Strategy_14": {
        "points_sl_buy": 36,
        "points_target_buy": 72
      }
    }
  }
```

### Key Parameter Definitions:
1.  **`execution_mode`**: Either `"OPTION"` (trades CE/PE contracts via rolling option parameters) or `"STOCK"` (trades equity shares directly on the spot candles with `delta = 1.0`).
2.  **`stock_qty_override`**: (STOCK Mode only) Optional integer specifying the exact number of shares to trade. If set to `null` or omitted, defaults to `lot_size * num_lots`.
3.  **`lot_size`**: Options lot contract multiplier (e.g. 65 for Nifty). For STOCK mode, acts as the unit base if `stock_qty_override` is not set.
4.  **`sl_mult` / `tp_mult` / `trailing_mult`**: Risk multipliers applied to the ATR (Average True Range) at signal confirmation:
    - `opt_sl_points = ATR * sl_mult * delta`
    - `opt_tp_points = ATR * tp_mult * delta`
    - `opt_trail_jump = ATR * trailing_mult * delta`
5.  **`option_delta`**: (OPTION Mode only) Proxy delta (e.g. 0.5) used to calculate options price movement relative to spot ATR changes.
6.  **`type`**: `"INDEX"` or `"STOCK"`.
7.  **`exchange_segment`**: `"IDX_I"` for indices, `"NSE_EQ"` for stocks.
8.  **`exit_mode`**: One of the following exit styles:
    - `"ATR"`: Legacy option premium target orders.
    - `"SWING"`: Structural swing stops and local monitoring loop based on the underlying Spot index price.
    - `"SWING_CONTRACT"`: Structural swing stops and local monitoring loop calculated and monitored directly on the traded contract's premium (option premium chart or stock chart) itself.
    - `"POINTS"`: Fixed point-based stop loss, target, and trailing stops calculated and monitored directly on the traded contract's premium (option premium chart or stock chart) itself.
9.  **`local_exit_monitoring`**: (Optional boolean) Determines whether exits are monitored locally in Python (`true`) or placed as exchange-side broker Bracket/Super orders (`false`). If omitted, defaults to `true` for `SWING`, `SWING_CONTRACT`, and `POINTS` exit modes, and `false` for `ATR` mode.
10. **`points_sl_buy` / `points_sl_sell`**: Stop Loss points for buy and sell legs under `POINTS` exit mode.
11. **`points_target_buy` / `points_target_sell`**: Take Profit Target points for buy and sell legs under `POINTS` exit mode.
12. **`points_target_high_conviction`**: Extended Take Profit Target points under `POINTS` exit mode when dynamic conviction is triggered (`Conviction >= 1.5`).
13. **`points_trail_buy` / `points_trail_sell`**: Trailing jump points for buy and sell legs under `POINTS` exit mode.
14. **`points_be_buy` / `points_be_sell`**: Breakeven trigger under `POINTS` exit mode. Ratio if <= 1.0 (multiplier of SL distance), or absolute points in favor if > 1.0. Moves SL to entry price once reached.
15. **`swing_window_size`**: (SWING and SWING_CONTRACT exit modes only) Lookback window size in candles (e.g. 10) to determine structural swing high/low.
16. **`sl_buffer_atr_mult`**: (SWING and SWING_CONTRACT exit modes only) ATR multiplier buffer added/subtracted to the swing low/high to avoid liquidity sweeps (default: 0.2).
17. **`profit_target_buy` / `profit_target_sell`**: (ATR and SWING_CONTRACT modes only) Fixed INR profit target (e.g. 650.0). If greater than 0, it overrides the dynamic ATR-based target premium calculation. The target points added/subtracted to the entry price are calculated as `profit_target / lot_size`.
16. **`gatekeeper_enabled`**: (0/1) Enable or disable the secondary Gate Keeper validation system at entry.
17. **`gatekeeper_single_strike`**: (0/1) If set to 1, checks only the target strike contract, skipping the default 3-strike basket consensus (recommended for stocks).
18. **`gatekeeper_time_filter_minutes`**: (e.g., 20) Skip signals fired within N minutes of market open to avoid initial volatility.
19. **`gatekeeper_window_minutes`**: (e.g., 5) Lookback interval in minutes for price/OI/Volume buildup calculations.
20. **`gatekeeper_oi_min_change_pct`**: (e.g., 1.0) Minimum required open interest change percentage.
21. **`gatekeeper_volume_sma_period`**: (e.g., 15) Simple Moving Average period for volume SMA checks.
22. **`gatekeeper_volume_multiplier`**: (e.g., 1.2) Multiplier requiring volume to exceed volume SMA by N times.
23. **`allowed_regimes_trend`**: (Optional array/list of strings) If specified, restricts trade entries to specific ADX trend regimes. Values: `"TREND"` (ADX > 25.0), `"RANGE"` (ADX < 20.0), `"NEUTRAL"` (20.0 <= ADX <= 25.0).
24. **`allowed_regimes_vol`**: (Optional array/list of strings) If specified, restricts trade entries to specific ATR% volatility regimes. Values: `"LOW_VIX"` (ATR% <= Median ATR%), `"HIGH_VIX"` (ATR% > Median ATR%).


---

### Global settings (`.env`)
The `.env` file determines global execution configurations:
*   **`LEG_MODE`**: Determines trade actions allowed:
    - `"BUY"`: Buy signals trigger long trades (Buy CE or Buy Stock).
    - `"SELL"`: Sell signals trigger short trades (Sell PE or Short Stock).
    - `"BOTH"`: Allows both long and short trades.
*   **`USE_DYNAMIC_EXITS`**: (`True`/`False`) If `True`, enables strategy-defined dynamic exits. Positions are closed immediately when `Exit_Long` or `Exit_Short` signals trigger.
*   **`DISABLE_FALLBACKS`**: (`True`/`False`) Bypasses preloaded offline ATM files, forcing the prefetcher to fetch stitched contracts dynamically.
*   **`ONLY_USE_CACHE`**: (`True`/`False`) If `True`, prevents backtest runs from fetching online contracts if there is a cache miss.

---

## 3. How to Run Backtests & Optimizations

Always run your commands from the workspace directory using the activated Python virtual environment:

### A. Run a Baseline Single-Instrument Backtest
To execute a backtest using settings defined in `instruments.json` and `.env`:
```powershell
..\venv\Scripts\python.exe backtest_engine.py
```
*Note: Detailed trade-by-trade logs are exported directly to `backtest_results.csv`.*

### B. Run the Multi-Instrument Runner (Flexible Parameters)
To execute backtests for multiple symbols, customize lookback lengths, select specific strategies, or override leg modes on the fly:
```powershell
# Syntax: python run_multi_instrument_backtest.py [SYMBOLS...] [FLAGS]

# Example 1: Backtest NIFTY and BHEL for the last 60 days using Strategy 3
..\venv\Scripts\python.exe run_multi_instrument_backtest.py NIFTY BHEL --days 60 --strategy 3

# Example 2: Backtest BHEL in STOCK mode for 90 days, BUY legs only
..\venv\Scripts\python.exe run_multi_instrument_backtest.py BHEL --days 90 --strategy 3 --leg-mode BUY

# Example 3: Backtest all enabled instruments in instruments.json for 30 days
..\venv\Scripts\python.exe run_multi_instrument_backtest.py --days 30
```
#### Command Flags:
*   `symbols`: Positional names of instruments to run (e.g., `NIFTY BHEL`). If omitted, reads all instruments where `"enabled": 1` in `instruments.json`.
*   `--days` / `-d`: Number of calendar days of history to backtest (default: 30).
*   `--strategy` / `-s`: Strategy index to run (1-20, including Strategy 20 Option Selling).
*   `--leg-mode` / `-l`: Leg execution mode (`BUY`, `SELL`, `BOTH`).
*   `--offline` / `-o`: Run backtest in offline mode using preloaded ATM option files.

*Note: Individual results are exported to `backtest_results_{symbol}.csv` and a consolidated performance comparison is saved to `multi_instrument_results.csv`.*

### C. Run the Unified Walk-Forward Parameter Optimizer
To run the joint multi-stage parameter optimizer to find the best strategy and risk parameters:
1. Ensure the target instrument(s) are set to `"enabled": 1` in [instruments.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/instruments.json).
2. Execute the optimizer script from the command line, passing the desired strategy and flags:
```powershell
# Syntax: python optimize.py --strategy [STRATEGY] [FLAGS]

# Example 1: Optimize NIFTY (Strategy 3, default BOTH leg mode) over 720 days
..\venv\Scripts\python.exe optimize.py -s Strategy_3 -d 720

# Example 2: Optimize Strategy 5 in SELL mode over 365 days
..\venv\Scripts\python.exe optimize.py -s Strategy_5 -d 365 -l SELL

# Example 3: Optimize Strategy 3 with a safety cap of 30 strategy combinations
..\venv\Scripts\python.exe optimize.py -s Strategy_3 -d 720 --max-combos 30

# Example 4: Compare POINTS, ATR, and SWING exit modes side-by-side on Strategy 14
..\venv\Scripts\python.exe optimize.py --symbol NIFTY -s Strategy_14 -d 180 --exit-sweep
```

#### Command Flags:
*   `--strategy` / `-s`: The strategy key to optimize (e.g. `Strategy_3`, `Strategy_5`, `Strategy_14`. Default: `Strategy_3`).
*   `--days` / `-d`: Number of calendar days of history to optimize over (default: `720`).
*   `--leg` / `-l`: Leg execution mode filter (`BUY`, `SELL`, or `BOTH`). If omitted, reads the default `LEG_MODE` from the `.env` file.
*   `--max-combos`: Maximum number of strategy parameter combinations to sweep. If the strategy's optimization grid exceeds this number, the script will randomly sample this amount to protect CPU execution times (default: `50`).
*   `--exit-sweep`: If passed, runs parallel parameter optimization sweeps side-by-side across POINTS, ATR, and SWING exits, printing a comparative report matrix and saving it to `<symbol>_exit_mode_sweep_comparison.csv`.

#### The 3-Stage Pipeline Execution:
*   **Warmup Pass**: Runs a single baseline backtest to fetch and cache required options historical data sequentially in a single process. (Automatically skipped if `execution_mode` is `STOCK` for the instrument).
*   **Data Partitioning**: Splits the spot data timeline into a **67% Train** (In-Sample) partition and a **33% Test** (Out-of-Sample) partition.
*   **Stage 1 (Coarse Joint Sweep)**: Runs on the Train partition. Sweeps strategy parameter combinations jointly with a coarse grid of risk parameters to ensure indicator signals and exit structures are aligned.
*   **Stage 2 (Fine Risk Tuning)**: Freezes the best strategy parameters found in Stage 1 and sweeps a fine-grained grid of risk parameters (SL, Target, Trailing, Breakeven multipliers) on the Train partition. Capped at a safety limit of **100 random combinations** to prevent combinatorial explosions and accelerate runtimes by 16x.
*   **Stage 3 (Walk-Forward Validation)**: Runs a single-pass validation backtest on the unseen Test partition using the optimized parameters and outputs a performance comparative report.

#### How to Analyze and Interpret Reports:
The script outputs reports under the `optimization_results/` directory:
1.  **Fine Risk Grid Results (`{symbol}_fine_risk_optimization.csv`)**: Holds sorted rankings of all Stage 2 risk parameter sweeps on Train data.
2.  **Walk-Forward Report (`{symbol}_walk_forward_validation.csv`)**: Holds side-by-side performance statistics for the Train split vs. the unseen Test split.
3.  **Terminal Comparative Table**: Prints a summary comparison at completion:
    ```
    ================================================================================
                     WALK-FORWARD PERFORMANCE REPORT: NIFTY                 
    ================================================================================
      Dataset Partition      | Trades | Win Rate | PF    | Net PnL (Rs.) | Max DD 
    --------------------------------------------------------------------------------
      TRAIN (In-Sample)      | 11     | 81.8   % | 6.91  | Rs.27116.84   | Rs.3060 
      TEST (Out-of-Sample)   | 8      | 62.5   % | 1.69  | Rs.5996.75    | Rs.7443 
    --------------------------------------------------------------------------------
      VERDICT: [ROBUST] Profitable on both Train AND Out-of-Sample Test data.
    ================================================================================
    ```
    *   **Verdict `[ROBUST]`**: Profitable on both training (In-Sample) and testing (Out-of-Sample) data. This indicates high stability and low risk of overfitting.
    *   **Verdict `[OVERFITTED]`**: Profitable on train data but lost money on test data. **Do not use this parameter set in live trading.**
    *   **Verdict `[NOT VIABLE]`**: Failed to generate a profit even on the training data.

### D. Understanding Backtest Results & Exit Classification

Detailed trade-by-trade logs are exported directly to `backtest_results_{symbol}.csv`. The **`Exit_Reason`** column indicates the exact reason a position was closed. The simulator distinguishes standard, inside-candle wick triggers from overnight or candle-opening gap breaches:

#### 1. Standard Exits (Inside-Candle)
These exits occur when the price touches a threshold during the candle's lifetime (high/low wick checks):
*   **`"StopLoss"`**: The price reached the stop loss boundary (Spot structure or Premium points/ATR).
*   **`"Target"`**: The price reached the take profit target boundary.
*   **`"Time_SquareOff"`**: Closed at the end of the day or session limit (default: 15:00).
*   **`"End_Of_Simulation"`**: The backtest timeframe ended while the trade was still open.

#### 2. Gap Exits (Opening Price Breach)
These exits occur when a market gap at the start of a candle opens beyond the SL or Target boundaries. Instead of closing at the boundary price, the position is filled at the candle's open price (with slippage applied) to accurately represent real-world execution slippage:
*   **`"GapDown_SL"`**: For **Long** positions (Buy CE/Buy Stock), the candle opened at or below the Stop Loss price.
*   **`"GapUp_Target"`**: For **Long** positions, the candle opened at or above the Target price.
*   **`"GapUp_SL"`**: For **Short** positions (Buy PE/Short Stock), the candle opened at or above the Stop Loss price.
*   **`"GapDown_Target"`**: For **Short** positions, the candle opened at or below the Target price.

---

## 4. Historical Lookback Limits (How Far Back Can We Test?)

### A. Spot / Historical Candle Data
*   The backtest engine fetches 1-minute historical candles directly from Dhan API chart endpoints on demand.
*   The maximum dynamic lookup range supported by the engine is configured via the `backtest_days` parameter (defaulting to **730 days**, or **2 years** of historical 1-minute candles).
*   Downloaded spot candles are cached permanently on disk under `backtest_data/{symbol}_spot.csv` for high-speed subsequent runs.
*   **Automated Ingestion Engine**: To pre-populate or incrementally maintain 5+ years of 1-minute spot history across the entire 2,289 NSE stock universe ([`EQUITY_L.csv`](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/EQUITY_L.csv)), use [fetch_historical_equity.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/fetch_historical_equity.py).
*   **Limit**: Dhan's API allows intraday charts query ranges up to 5+ years in 30-day chunks.

### B. Options Contracts (Option Mode)
*   **Prefetch limits**: Since options contracts expire weekly or monthly, the engine uses the targeted prefetcher to fetch and cache options historical data on signal timestamps.
*   Option contracts are cached under `backtest_data/contract_cache/`.
*   **Limit**: Option contracts can be fetched historically for the signal dates as long as they are still stored in the Dhan historical database or local fallbacks.

### C. Stocks (Stock Mode)
*   **No Prefetch Limit**: In `STOCK` mode, the simulation executes directly on the spot candles dataset (`backtest_data/{symbol}_spot.csv`) without needing option chain lookups or contract cache stitching.
*   **Limit**: You can test stock execution mode as far back in the past as you have 1-minute spot historical data saved in your spot CSV.

---

## 5. Dynamic Parameter Registries (Strike Steps & Lot Sizes)

To ensure the backtest simulation matches historic realities where exchanges periodically adjust option contract lot sizes and strike step intervals (e.g. `RECLTD` switching between 10.0, 5.0, and 2.5), the engine loads parameters dynamically:
*   **Registries**: Maps symbols and specific contract expiry dates to historical parameters using two localized JSON maps: [strike_step_history.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strike_step_history.json) and [lot_size_history.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/lot_size_history.json).
*   **Backtest Engine Matching**: On trade entry, the engine matches the active trade date and contract expiry against the history maps to load the correct historical parameters.
*   **Quantity & PnL Parity**: The resolved lot size dynamically determines the trade size (`Qty = lot_size * lots`) at entry, which is stored inside the trade log. PnL and broker fees are calculated with the exact historical lot multiplier.

---

## 6. Multi-Strategy Combined Portfolio Backtester (`run_multi_strategy_portfolio.py`)

To simulate institutional multi-strategy portfolio execution where **multiple active strategies operate concurrently** on the same asset (e.g. `Strategy_10`, `Strategy_18`, and `Strategy_19` active simultaneously on `NIFTY`):

### Command Syntax
```bash
python run_multi_strategy_portfolio.py NIFTY -s 10 18 19 -d 365 --leg-mode BOTH
```

### Features & Capabilities
1. **Concurrent Signal Merging**: Each strategy evaluates the market data independently and generates signals. Simultaneous signals are merged cleanly to prevent over-leveraged orders on the same strike.
2. **Strategy-Specific Exit Rules**: Each trade retains its strategy tag (`Active_Strategy`) and executes Stop Loss, Target, and Trailing SL exits according to its strategy overrides in `instruments.json`.
3. **Consolidated Portfolio PnL & Breakdown**: Outputs gross PnL, transaction charges, net PnL, profit factor, and a strategy-by-strategy comparative breakdown table.
4. **Detailed CSV Export**: Saves every single trade with its triggering strategy tag to `multi_strategy_portfolio_trades.csv`.

---

## 7. Gate Keeper Option Entry Validation System

The Gate Keeper acts as a validation filter between spot signal generation and option order execution to verify market participation and breakout strength:
*   **Multi-Strike Check**: Evaluates ATM, ATM-1, and ATM+1 contract price, open interest (OI) velocity, and volume buildup. If `"gatekeeper_single_strike": 1` is configured, it skips the adjacent strikes and only checks the target strike.
*   **Buildup Rules**:
    *   **Long Leg (Option Buy)**: Requires positive option price change (`price_change > 0`).
    *   **Short Leg (Option Sell)**: Requires negative option price change (`price_change < 0`).
    *   **OI Velocity & Volume**: OI change percentage must meet the `gatekeeper_oi_min_change_pct` threshold, and volume must exceed the volume SMA by `gatekeeper_volume_multiplier`.
*   **Resilience & Skipped Executions**: If the database is missing `'oi'` or `'volume'` columns, the check is bypassed gracefully to validate on remaining parameters. If validation fails on any of the leg checks, the entry is skipped and a warning is logged.

---

## 7. Parameter Checklist before Going Live

Before updating your live trading bot configurations, verify that:
*   [ ] The target instrument is configured with the correct `"execution_mode"` (`"STOCK"` or `"OPTION"`) in `instruments.json`.
*   [ ] If in `STOCK` mode, verify that `"type"` is set to `"STOCK"`, `"exchange_segment"` is set to `"NSE_EQ"`, and `"stock_qty_override"` is set appropriately.
*   [ ] If dynamic strategy-based exits are desired, verify that `USE_DYNAMIC_EXITS=True` is configured in the `.env` file and the target strategy outputs the required `Exit_Long` and `Exit_Short` columns.
*   [ ] Pre-fetching was executed (only required if in `"OPTION"` mode) to stitch F&O cache files.
*   [ ] The parameter set was validated using **Walk-Forward Validation** (Phase 3) and marked as **`[ROBUST]`**.
*   [ ] **Max Drawdown** on the historical run is within your acceptable capital risk tolerance.
*   [ ] Intraday equity charges have been checked (using custom commission rates calculated by the simulator).