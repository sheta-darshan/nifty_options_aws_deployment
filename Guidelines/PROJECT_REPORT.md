# Smart Algorithmic Trading Platform (SATP) - Project Report

## Executive Summary
This project is an institutional-grade, multi-account algorithmic trading system designed for **DhanHQ** and deployed on **AWS infrastructure**. The platform automates complex derivative strategies (NIFTY/BANKNIFTY/SENSEX Options) and spot equities (STOCK mode) with a focus on regulatory compliance, network resiliency, risk management, and precise backtest-to-live parity.

---

## 🚀 Key Features

### 1. Multi-Account Portfolio Management
- **Concurrent Execution**: Orchestrates trades across 5+ independent Dhan accounts simultaneously.
- **Account-Specific Scaling**: Supports global multipliers and per-instrument lot overrides for each sub-account.
- **Independent Asset Limits**: Tracks and limits active trades for CE and PE option legs independently across all modes (BOTH, BUY, and SELL) to ensure capital efficiency and concurrent leg execution.
- **Risk Siloing**: Enforces per-account "Max Active Positions" and "Daily Trade Limits" to prevent over-exposure.
- **Dynamic Configuration Reloading**: Automatically reloads `instruments.json` and `accounts.json` on-the-fly every 5 minutes without requiring bot restarts.

### 2. Regulatory & Network Architecture
- **Dedicated IP Binding**: Implements a custom `SourceAddressAdapter` for the `requests` library, ensuring each account's traffic originates from a unique, whitelisted Elastic IP (EIP) on AWS.
- **Multi-ENI Routing**: Custom Linux routing tables (Policy Based Routing) managed via Systemd to handle multiple network interfaces on a single Ubuntu instance.
- **Proxy Support**: Optional routing through secure proxies for specific accounts.

### 3. Advanced Strategy Engine
- **Modular Strategy Registry**: Decouples technical calculations from execution. Custom strategies inherit from a unified `BaseStrategy` and register via a decorator (`@register_strategy`).
- **Dual Execution Modes**: 
  - **OPTION Mode**: Automatically selects ATM/OTM options based on real-time Spot prices and handles expiry rollover. Supports various leg configurations: `"DIRECT"`, `"STRADDLE"`, and `"DEBIT_SPREAD"`.
  - **STOCK Mode**: Direct spot equity execution with custom margin rules, stock-specific slippage (0.05%), and equity-appropriate transaction charge models.
- **Multi-Exit Execution Modes**:
  - **ATR Mode (`"exit_mode": "ATR"`)**: Dynamic Stop Loss, Take Profit, and Trailing Stops scaled and snapped to the option premium or stock execution price, managed directly on the broker exchange using Dhan Bracket/Super Orders.
  - **SWING Mode (`"exit_mode": "SWING"`)**: Stop Loss and Targets defined in terms of Spot chart structures (e.g. N-candle high/low swing support/resistance plus ATR buffer), monitored locally in Python and exited via market orders.
- **Delta-Adjusted Risk**: Dynamically calculates Stop Loss (SL) and Take Profit (TP) points based on **ATR (Average True Range)** multiplied by the option's Greeks (Delta).
- **Same-Day Expiry Rollover**: Automatically rolls over to the next week's/month's contract on the contract's expiry day to avoid decay and premature square-offs at 15:00.
- **Dynamic Strategy Exits**: Supports real-time exit signals (e.g., SuperTrend direction shift) to close active positions dynamically, canceling pending Stop Loss trigger orders at the broker immediately.
- **Comparative/Multi-Instrument Strategy Design**: A declarative dependency system allowing custom strategies to query and compare multiple instruments (e.g., stock vs index) for signal generation.
- **Dynamic Strike Step & Lot Size Resolution**: Bypasses static configuration lag by resolving parameters dynamically at execution:
  - *Backtesting & Optimization*: Lazily loads historical registries ([strike_step_history.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strike_step_history.json) and [lot_size_history.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/lot_size_history.json) compiled from 200+ historical F&O bhavcopies) to determine contract parameters matching the exact trade and expiry dates.
  - *Live Trading*: Queries the Dhan active F&O master contracts to automatically calculate the active strike step and look up the live contract lot size in-memory at trade execution.
- **Gate Keeper Option Entry Validation**: A secondary validation layer that protects option buying and selling from low-participation false breakouts:
  - Evaluates contract price, open interest (OI) velocity, and volume buildup across ATM, ATM-1, and ATM+1 strikes.
  - Filters out signals generated in the first few minutes of the market open (noise filter).
  - Gracefully handles missing exchange data columns by executing matching logic on the remaining parameters.

---

## 📈 Fully Implemented Strategies

SATP features a modular suite of technical and quantitative trading strategies:

1. **Strategy 1 (Trend)**: Stochastic RSI crossover, ADX filter, EMA-21 trend filter, and Supertrend on 5-minute resampled candles.
2. **Strategy 2 (Pullback)**: Confluence of 15-minute and 5-minute Supertrend indicators with a 5-minute Stochastic RSI crossover to capture high-probability pullbacks.
3. **Strategy 3 (Trend Momentum / TM)**: Multi-timeframe Trend-Following strategy on 5-minute resampled candles combining EMA stacks (8, 18, 30), ATR breakout, and ADX slope.
4. **Strategy 4 (WMA Breakout)**: Weighted Moving Average crossover (WMA 87 & WMA 200) and VWAP reversal breakout scalping on 1-minute base candles.
5. **Strategy 5 (Gabani Value Area)**: Setup and breakout strategy utilizing volume contraction (dry volume relative to 20-period volume SMA), price tightening (inside bars), orderly landing near EMAs (10/20), and Stochastic RSI breakouts.
6. **Strategy 6 (Multi-Factor Scoring)**: Advanced multi-factor scoring system (EMA band, RSI bull/bear levels, VWAP, ADX, Candle Body Strength, Stretch Penalty, and No-Trade Zone) run on 9-minute resampled candles with breakout buffers.
7. **Strategy 7 (Derivative Oscillator)**: Zero-crossover breakout strategy using a high-period Derivative Oscillator (RSI/EMA/SMA) computed on 1-minute candles with a 5-minute validation breakout window.
8. **Strategy 8 (Pending / MTF Trend Pulse)**: A 3-layer confluence strategy utilizing 15-minute macro trend gates (VWAP, Hull MA, ADX), 5-minute trend structures (Supertrend, EMA stack, MACD hist), and 1-minute entry triggers (breakouts, RSI exhaustion filters, and volume surges).
9. **Strategy 10 (Hilega Milega WMA 50 Breakout)**: Institutional Hilega Milega momentum breakout strategy using WMA 50.
10. **Strategy 16 (18 SMMA Smooth Trend)**: Smoothed Moving Average trend breakout strategy on 5-minute resampled candles.
11. **Strategy 17 (High-Conviction Opening Scalp)**: Opening window volatility expansion scalp strategy.
12. **Strategy 18 (SMA Breakout with 09:45 Time Gate)**: Time-gated opening range SMA breakout strategy.
13. **Strategy 19 (Institutional Quant Machine Learning)**: Institutional ML-Gated strategy trained on 5+ years of Nifty 1-minute data using XGBoost classifiers and Walk-Forward cross validation, yielding **+Rs. 106,600.86 Net Profit** in multi-strategy portfolio testing.
14. **Strategy 20 (15-Min Volatility-Adaptive Supertrend Option Writing System)**: 1-Trade-per-day option selling strategy powered by a single indicator (15-minute Supertrend 10, 2.0) selling Put options in Supertrend uptrends and Call options in downtrends, with +45 pts target, -20 pts SL, +15 pts Breakeven protection, and dynamic Supertrend reversal exits.

---

## 🤖 Institutional Quant Machine Learning Engine (`Strategy_19`)

SATP features an institutional **Quantitative Machine Learning Pipeline**:
- **Dataset**: 5+ years of 1-minute Nifty spot candles (538,465 bars from 2021 to 2026).
- **Noise Reduction**: Computes Mean Price $P_{\text{mean}} = \frac{\text{Open} + \text{High} + \text{Low} + \text{Close}}{4}$ before indicator calculation.
- **Multitimeframe Feature Engineering**: 5-minute RSI, EMA/WMA crossovers, ADX trend strength, VWAP distance, relative ATR, overnight gap %, C1 candle range expansion, and time-of-day features.
- **Walk-Forward Validation**: Trained with 5-fold TimeSeriesSplit CV using XGBoost classifiers to eliminate lookahead bias and data leakage.
- **Signal Gating**: Executes trades only when model prediction probability $P_{\text{trend}} \ge 42\%$, eliminating sideways chop trades.

---

## 🛠 Tech Stack

| Component | Technology |
| :--- | :--- |
| **Cloud Provider** | AWS (EC2, Elastic IPs, ENIs) |
| **Operating System** | Ubuntu Server 24.04 LTS |
| **Language** | Python 3.12 (Virtual Environment) |
| **Core Libraries** | `dhanhq`, `pandas`, `pandas-ta`, `requests`, `pytz`, `python-dotenv`, `scikit-learn`, `xgboost` |
| **Process Management**| Linux Systemd (Auto-restart, Journaled Logging) |
| **Optimization** | Python `multiprocessing` for parallel grid search (Layer 1 & Layer 2) |
| **Automation** | Cron (Start/Stop/Maintenance) |

---

## 📂 Codebase Modularization & Package Structure
To ensure scalability, clean separation of concerns, and ease of maintenance, the live execution engine has been fully refactored from a single monolith script into a modular Python package structure:

*   **[live_trade_fixed.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/live_trade_fixed.py)**: Serves as the lightweight Facade launch script, handling systemd shutdown signals and re-exporting modules for backward-compatibility.
*   **[trading_bot/config.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/config.py)**: Manages environment variables, instrument scrubbing, and holiday calendars.
*   **[trading_bot/network.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/network.py)**: Controls token-bucket rate limiters and thread-safe source IP/proxy binding.
*   **[trading_bot/alerts.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/alerts.py)**: Manages Telegram/Slack webhook formatting and alerts.
*   **[trading_bot/state.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/state.py)**: Serializes active positions and orders state to disk.
*   **[trading_bot/api_wrapper.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/api_wrapper.py)**: Handles API requests with transient failure retry logic.
*   **[trading_bot/account_manager.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/account_manager.py)**: Dispatches orders across sub-accounts concurrently.
*   **[trading_bot/data_pipeline.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/data_pipeline.py)**: Computes multi-strategy indicators, greeks, and handles strike selection.
*   **[trading_bot/instrument_bot.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/instrument_bot.py)**: Implements the execution thread loops for each active instrument.
*   **[trading_bot/manager.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/trading_bot/manager.py)**: Orchestrates thread lifecycle, cleaning stale orders, and instruments reloading.

### 🧪 Automated Regression Testing
To guarantee that parameter overrides, multi-strategy signal merging, and trend regime filters perform correctly without side effects, a regression testing pipeline has been established inside the `tests/` folder:
*   **[test_parameter_loader.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/tests/test_parameter_loader.py)**: Verifies dynamic overrides overlay from configuration files.
*   **[test_signal_merging.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/tests/test_signal_merging.py)**: Validates parallel signal extraction and merging.
*   **[test_regime_filtering.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/tests/test_regime_filtering.py)**: Asserts ADX-based regime trend limits.

Run tests locally with:
```powershell
..\venv\Scripts\python.exe -m unittest discover -s tests
```

---

## 📊 Backtest-to-Live Parity & Risk Validation

### 1. Engine Parity & Broker Rules
- **Trailing Logic Parity**: Removed artificial activation thresholds; implemented exact trailing jump logic replicating Dhan Super Order behavior where trailing begins immediately from entry.
- **Target/Exit Logic Parity**: Implemented option buy target calculations based on fixed INR target per lot (`profit_target_buy` / `profit_target_per_lot` from `instruments.json`) and option sell decay targets.
- **Accurate Fee Structures**: Includes exact brokerage (flat ₹20/order), STT, transaction fees, and GST. Dynamic BSE transaction fees for SENSEX and BANKEX options (`0.0325%`) match exchange reality.
- **Option Price Lower Bounds & Slippage Floors**: Enforces a minimum ₹0.05 (1 tick) slippage floor and minimum price bounds (0.05 minimum) for options to prevent unrealistic zero-slippage executions.

### 2. Data Integrity & Logging
- **Dual-Spot Tracking**: Logs both `Entry_Spot` and `Exit_Spot` for every trade, enabling complete EOD audits on whether trades exited in or against market direction.

---

## 📈 Parallel Optimizer & Grid Search
- **Multi-Stage Coarse-to-Fine Grid Sweeps**: Automatically tunes strategy parameters (Stage 1 Coarse sweep) and risk parameters (Stage 2 Fine sweep) in parallel using Python `multiprocessing`.
- **Rolling Walk-Forward Validation (WFO)**: Supports a rolling overlapping window partitioning (Train 6 months, Test 2 months, step 2 months) that combines Out-of-Sample test trades into a unified walk-forward validation equity curve to reject curve-fitted parameters.
- **Parameter Clustering Plateau Check**: Groups the top 50 risk grid candidates using K-Means clustering ($K=3$) and snaps parameters to the centroid of the largest cluster (plateau) to choose robust, non-isolated coordinates.
- **Advanced Robustness Metrics**: Computes $1,000$ path shuffles using Monte Carlo analysis (tracking the $95\%$ worst drawdown and sequence robustness), cumulative curve linear regression $R^2$ fit, yearly/monthly stability checks, and a top-5 lucky trade drop exclusion penalty.
- **ADX & Relative ATR% Regime Profiling**: Automatically categorizes trades into TREND/RANGE and HIGH_VIX/LOW_VIX market regimes.
- **Early-Rejection Engine**: Aborts optimization backtest runs early if performance bounds (Profit Factor $<0.7$, Win Rate $<30\%$, or net drawdown $<-5R$) are violated after 30 trades.

---

## 📊 Operational Flow (Daily)
1. **08:00 AM**: Cron triggers `renew_tokens.py` (Refreshing all active accounts).
2. **09:10 AM**: Cron triggers `maintenance.sh` (Holiday check + Archive state).
3. **09:10 AM**: Bot starts via `live_trade.service` (Enters waiting mode).
4. **09:20 AM**: Strategy engine activates (Starts monitoring 1-min and 5-min candles).
5. **03:05 PM**: Cron triggers `systemctl stop` (Finalizing all operations).

---
**Developer/Architect**: SATP Engineering Team  
**Deployment**: AWS Mumbai (ap-south-1)
