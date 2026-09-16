# SATP Architecture & AI Agent Working Map

> **AUTOMATIC ONBOARDING & CONTEXT PRESERVATION PROTOCOL:** This file is the single-source-of-truth operational guide for all AI coding agents working on the Smart Algorithmic Trading Platform (SATP).

---

## 1. Project Summary

The **Smart Algorithmic Trading Platform (SATP)** is a production-grade algorithmic trading and quantitative research framework designed for Indian equity and derivatives markets (NSE Indices and Equities) powered by the DhanHQ API. The system operates in two synchronized environments:
1. **Backtesting & Walk-Forward Optimization Engine:** Contract-accurate option simulation with dynamic strike step and lot size registries, continuous price-continuity option stitching (`/v2/charts/rollingoption`), multi-strategy portfolio backtesting, and machine learning walk-forward parameter tuning.
2. **Live Execution Bot:** Multi-threaded, multi-account execution engine (`live_trade_fixed.py`, `trading_bot/`) supporting exchange-managed Super Orders (Bracket Orders with automated SL/TP/Trailing), direct equity and option writing/buying (22+ technical and quantitative ML strategies), dynamic config reloading, and real-time risk controls.

---

## 2. Architecture Map & Data Flow

```text
nifty_options_aws_deployment/
├── AGENTS.md                        # Primary AI onboarding & persistent architectural map (THIS FILE)
├── instruments.json                 # Master instrument & strategy-override configurations (Hot-reloads every 5m)
├── accounts.json                    # Multi-account credentials, margin allocations & trading permissions
├── .env                             # Environment setup (Dhan API token, Leg Mode, Webhooks)
│
├── backtest_engine.py               # Core simulation engine (Parity checks, Option Stitcher, Charges calculation)
├── run_multi_instrument_backtest.py # Flexible multi-instrument & multi-strategy backtest runner CLI
├── run_multi_strategy_portfolio.py  # Institutional multi-strategy portfolio backtester (Concurrent execution)
├── run_strategy20_backtest.py       # Dedicated calendar spread & option writing backtest runner
├── optimize.py                      # Multi-stage walk-forward parameter optimizer
├── optimize_per_strategy.py         # Strategy-specific parameter grid search optimizer
├── prefetch_options.py              # Targeted option contract pre-fetcher & cache stitcher
├── fetch_historical_equity.py       # Institutional 1-min historical data ingestion engine for 2,289 NSE stocks
├── send_daily_digest.py             # Automated daily Telegram/Slack PnL & risk digest CLI tool
├── renew_tokens.py                  # Automated Dhan API JWT token refresher
├── is_market_open.py                # NSE holiday calendar & market hours validator
│
├── trading_bot/                     # Production Live Execution Engine
│   ├── manager.py                   # ThreadedBotManager: thread lifecycles, dynamic reloader, position monitor
│   ├── instrument_bot.py            # InstrumentBot thread loop: candle polling, signal handler, Super Order execution
│   ├── config.py                    # Environment, holiday calendar, and in-memory index builder
│   ├── api_wrapper.py               # Resilient DhanHQ API client with retry logic and error classification
│   ├── account_manager.py           # MultiAccountManager: concurrent order dispatcher and position reconciler
│   ├── network.py                   # Token-Bucket RateLimiter (DATA: 4 req/s, ORDER: 10 req/s, QUOTE: 1 req/s)
│   ├── data_pipeline.py             # Live indicators, Greeks, strike resolution, and signal processor
│   ├── state.py                     # Thread-safe persistent JSON trade state serializer (`order_state.json`)
│   └── alerts.py                    # Real-time Telegram and Slack alert dispatcher
│
├── strategies/                      # Modular Strategy Registry Directory
│   ├── base.py                      # BaseStrategy abstract base class
│   ├── registry.py                  # Dynamic strategy registration decorator `@register_strategy`
│   ├── config.py                    # Strategy parameter schema & registry range loader
│   ├── strategy_1.py ... 20.py      # Standalone technical & quant strategy implementations
│   ├── strategy_btst.py             # Buy Today Sell Tomorrow afternoon breakout strategy
│   └── utils.py                     # Shared math utilities (EMA, Supertrend, Heikin-Ashi, ATR)
│
├── stock_selection/                 # Machine Learning Stock Selection Subsystem
│   ├── preprocess.py                # Feature engineering from 1-min spot candles (28 alpha features)
│   ├── train.py                     # XGBoost & Random Forest walk-forward classifier training
│   ├── select_stocks.py             # Single-target stock selection ranking CLI
│   ├── select_joint.py              # Joint Volatility + Direction selection with automated `instruments.json` rotation
│   └── README_STOCK_SELECTION.md    # Stock selection pipeline user manual
│
├── models/                          # Serialized ML model artifacts (e.g. `nifty_quant_xgb.pkl`)
├── Guidelines/                      # Canonical Documentation Hub
│   ├── SYSTEM_BLUEPRINT.md          # Architectural index and single-source-of-truth parameter registry
│   ├── CONFIGURATION_GUIDE.md       # Comprehensive configuration parameter reference
│   ├── STRATEGY_DEVELOPMENT_GUIDE.md# Step-by-step guide for creating new strategies
│   ├── backtesting_self_service_guide.md # Backtesting self-service & lookback limits
│   ├── PARAMETER_OPTIMIZATION_GUIDE.md   # Walk-forward optimization guide
│   └── AWS_SETUP_GUIDE.md           # Production deployment & EC2 infrastructure setup
│
├── research_and_development/        # Experimental backtests, audit scripts, and R&D verification tools
└── tests/                           # Unit & integration test suites (API, Concurrency, Strategy Parity)
```

### End-to-End Data Flow
1. **Data Ingestion:** `fetch_historical_equity.py` syncs 1-min OHLCV candles into `backtest_data/{symbol}_spot.csv`.
2. **Strategy Signal Generation:** `strategies/` processes completed candles (`shift(1)` to prevent look-ahead bias) and outputs Buy/Sell/Exit signals.
3. **Backtest Engine:** `backtest_engine.py` simulates trade fills at index $i+1$, matches option contract expiries and strike step histories, computes dynamic charges, and generates performance metrics.
4. **Live Execution:** `InstrumentBot` polls live candles, validates signals with Gatekeeper filters, resolves ATM/OTM strikes, and dispatches Super Orders to Dhan with automated SL/TP/Trailing.

---

## 3. Entry Points for Common Tasks

### A. Run a Strategy Backtest
```bash
# 180-day SELL leg backtest on NIFTY Strategy 22
..\venv\Scripts\python.exe run_multi_instrument_backtest.py NIFTY --strategy 22 --days 180 --leg-mode SELL

# Multi-strategy combined portfolio backtest
..\venv\Scripts\python.exe run_multi_strategy_portfolio.py NIFTY -s 10 18 19 -d 365 --leg-mode BOTH
```

### B. Run Parameter Optimization (Walk-Forward)
```bash
..\venv\Scripts\python.exe optimize.py --strategy Strategy_22 --days 365 --leg SELL --mode single --symbol NIFTY
```

### C. Ingest / Sync 5-Year Historical Stock Data
```bash
# Rapid incremental or full 5-year sync for all 2,289 NSE stocks
..\venv\Scripts\python.exe fetch_historical_equity.py --years 5
```

### D. Run Daily ML Stock Selection
```bash
# Select top 3 momentum stocks for tomorrow and auto-rotate in instruments.json
..\venv\Scripts\python.exe stock_selection/select_joint.py --rotate --top-k 3
```

### E. Launch Production Live Trading Bot
```bash
..\venv\Scripts\python.exe live_trade_fixed.py
```

### F. Run Test Suite
```bash
..\venv\Scripts\python.exe -m unittest discover -s tests
```

### G. Dispatch Daily Telegram / Slack PnL Digest
```bash
# Preview digest in console without sending webhook
..\venv\Scripts\python.exe send_daily_digest.py --preview

# Dispatch live digest to configured Telegram & Slack channels
..\venv\Scripts\python.exe send_daily_digest.py
```

---

## 4. Coding Conventions & Best Practices

1. **Virtual Environment Execution:** Always run commands using `..\venv\Scripts\python.exe` on Windows. Never rely on Docker.
2. **Strategy Registration Pattern:** Every strategy class must subclass `BaseStrategy` from `strategies.base` and use the `@register_strategy` decorator from `strategies.registry`. Dynamic strategy loops must scan across `range(1, 24)` (covering strategies 1-23 + BTST).
3. **Dynamic Overrides:** Respect `instruments.json` `strategy_overrides` and dynamic parameter reloading; never hardcode magic numbers.
4. **Thread-Safe Rate Limiting:** All Dhan API requests must route through `RateLimiter` in `trading_bot/network.py` or `ThreadSafeRateLimiter` in standalone scripts.
5. **Zero Look-Ahead Bias:** Indicator calculations in backtests must use completed candles (`shift(1)`), executing at candle open $i+1$.
6. **Hybrid Crash-Proof Breakeven:** For point-based option selling/buying strategies, use `"local_exit_monitoring": true` combined with `"broker_safety_sl": true`. Entry orders are submitted as native Dhan Super Orders with hard SL (`opt_sl`) resting directly on the exchange. Upon local breakeven trigger, the bot calls `modify_super_order_sl` (`PUT /super/orders/{orderId}`) to slide the exchange-resting `STOP_LOSS_LEG` directly to the trade entry price, ensuring 100% crash immunity.
7. **Graceful Margin Downsizing Fallback:** Live order routing in `InstrumentBot` routes orders through `place_order_with_margin_fallback`. If Dhan RMS returns a margin shortfall (`RS-9005` or text matching `"margin"/"insufficient"`), the bot automatically attempts `num_lots_high_conviction` -> `num_lots_sell` -> `1 lot minimum` before failing, preventing missed setups during margin spikes.
8. **Dynamic Target Scaling:** Support `points_target_high_conviction` in both backtest engine and live bot for setups with multi-timeframe trend alignment (e.g. 15m Supertrend + 5m breakout), allowing extended profit capture on high-conviction trades.

---

## 5. Known Gotchas & Historical Learnings

* **Dhan Token Expiration:** JWT tokens expire every 24 hours. Check token validity or run `renew_tokens.py` before diagnosing API errors.
* **Super Order Mechanics & Modifications:** In live execution, SL, TP, and Trailing jumps are submitted at order time to Dhan as Super Orders. When modifying an existing Super Order SL via `modify_super_order_sl`, the payload must target `legName: "STOP_LOSS_LEG"` with `stopLossPrice`. **Crucial:** Dhan rejects the modification if `order_type` is included in the modify payload.
* **Dynamic Breakeven Threshold Semantics:** In `POINTS` exit mode, if `points_be <= 1.0`, it acts as a multiplier of initial SL distance (`Initial_SL_Points * points_be`). If `points_be > 1.0`, it specifies the **absolute points in favor** required to trigger breakeven (e.g., 25.0 pts for NIFTY, 45.0 pts for BANKNIFTY, 40.0 pts for SENSEX).
* **Expired Options Resolution:** Historical expired option contracts return empty on `/v2/charts/intraday`. The backtest engine routes expired contracts (`expiry_dt.date() < datetime.now().date()`) directly to continuous price-continuity stitching (`/v2/charts/rollingoption`).
* **Weekend/Holiday Data Cutoff:** When syncing historical data on weekends or holidays, the target cutoff must be the last completed NSE trading session (e.g. Friday 15:30) to prevent making redundant queries for non-trading days.
* **Automated Daily Digest Schedule:** `ThreadedBotManager` runs an automated background scheduler that triggers `generate_daily_digest()` and `send_daily_digest()` at 15:35 IST daily and automatically on bot shutdown.

---

## 6. Strict AI Agent Guardrails ("DO NOT" Rules)

* ⛔ **DO NOT** read large CSV/JSON files (e.g., `EQUITY_L.csv`, `instruments.json`, cache CSVs, `multi_strategy_portfolio_trades.csv`) in full without `StartLine` and `EndLine` parameters.
* ⛔ **DO NOT** commit real credentials, `.env`, `accounts.json`, or API access tokens to version control.
* ⛔ **DO NOT** modify strategy execution logic without first checking `Guidelines/SYSTEM_BLUEPRINT.md` and `Guidelines/CONFIGURATION_GUIDE.md`.
* ⛔ **DO NOT** run destructive git commands (`git reset --hard`, `git clean -fd`, `git restore`) without explicit user permission.
* ⛔ **DO NOT** suggest or execute Docker containers or commands; the user environment is strictly a native Python virtual environment (`venv`).
