# Smart Algorithmic Trading Platform (SATP) - System Blueprint & AI Context Index

> **AI Agent Notice:** This document contains the complete, authoritative architectural blueprint of the SATP repository. Consult this file before reading extensive source files to minimize token utilization and ensure zero-bug plan generation.

---

## 1. System Overview & Core Architecture

SATP is an institutional-grade, multi-account algorithmic trading platform designed for **DhanHQ** and deployed on **AWS infrastructure** (Ubuntu 24.04 LTS / local Windows venv execution).

### Execution Context & Virtual Environment Rules
* **Python Runtime:** `..\venv\Scripts\python.exe` (Windows) / `venv/bin/python` (Linux).
* **No Docker Dependency:** The platform runs directly inside a Python virtual environment (`venv`), NOT Docker.
* **Database Drivers:** `DATABASE_URL` uses `asyncpg` (async, FastAPI), while `DB_SYNC_URL` uses `psycopg2` (sync, Alembic migrations). Inside containers host is `'db'`, locally host is `'localhost'`.
* **API Rate Limits:** DhanHQ API permits max 10 requests/sec for market data, 5 requests/sec for orders.

---

## 2. Codebase Directory & File Map

```
nifty_options_aws_deployment/
├── instruments.json             # Dynamic master instrument configuration (Reloads every 5 mins)
├── accounts.json                # Multi-account credentials & account-level overrides
├── .env                         # Global environment setup (Dhan Token, Leg Mode, Exits)
├── SYSTEM_BLUEPRINT.md          # Unified architectural reference map (THIS FILE)
│
├── backtest_engine.py           # Core simulation engine (Options & Stocks, Parity checks)
├── run_multi_instrument_backtest.py # Flexible multi-symbol/multi-strategy CLI runner
├── run_strategy20_backtest.py   # Dedicated strategy runner for Option Writing
├── prefetch_options.py          # Targeted option contract pre-fetcher & stitcher
├── optimize.py                  # Joint multi-stage walk-forward parameter optimizer
├── send_daily_digest.py         # Automated daily Telegram/Slack PnL & risk digest CLI tool
├── renew_tokens.py              # Automated Dhan API token refresher
├── fetch_historical_equity.py   # Institutional incremental historical 1-min data ingestion engine (Dhan)
├── EQUITY_L.csv                 # Master NSE listed equity stock universe
│
├── strategies/                  # Modular Strategy Registry Directory
│   ├── base.py                  # Abstract Base class BaseStrategy
│   ├── registry.py              # Dynamic strategy registration decorator @register_strategy
│   ├── config.py                # Configuration loader & defaults (range(1, 25))
│   ├── strategy_1.py ... 24.py  # Standalone technical & quant strategy implementations
│   ├── strategy_btst.py         # Buy Today Sell Tomorrow afternoon breakout strategy
│   └── utils.py                 # Shared math utilities (EMA, Supertrend, Heikin-Ashi, ATR)
│
├── stock_selection/             # Machine Learning & Quantitative Stock Selection Subsystem
│   ├── feature_matrix_v2.py     # Advanced Feature Matrix 2.0 (42 technical, volume, auction & RS alphas)
│   ├── train_joint_v2.py        # Dual-Head XGBoost probability training with isotonic calibration
│   ├── select_joint.py          # True Dual-Head ML momentum expansion selector with safe JSON rotation
│   ├── select_prebreakout.py    # Institutional Pre-Breakout / Pre-Breakdown Coiled Selector (Bidirectional)
│   ├── fno_registry.json        # Official Dhan-verified NSE F&O 210 stock registry (lot sizes & strike steps)
│   ├── models/                  # Serialized ML artifacts (global_dual_head_joint_model.pkl)
│   └── README_STOCK_SELECTION.md# Comprehensive stock selection pipeline documentation
│
└── trading_bot/                 # Live Execution Bot Package
    ├── live_trade_fixed.py      # Facade launch script / Entry point
    ├── config.py                # Environment & holiday calendar manager
    ├── network.py               # Rate limiters & multi-EIP source IP adapter
    ├── alerts.py                # Telegram & Slack webhook alert dispatch
    ├── state.py                 # Active position JSON state serializer
    ├── api_wrapper.py           # Resilient DhanHQ API client with retries
    ├── account_manager.py       # Concurrent multi-account order dispatcher
    ├── data_pipeline.py         # Live indicators, Greeks, and strike resolution
    ├── instrument_bot.py        # Core instrument execution thread loops & exit monitors
    └── manager.py               # Thread lifecycle & dynamic instrument reloader
```

---

## 3. Configuration Reference Schemas

### A. `instruments.json` (Per-Symbol Controls)
- **`execution_mode`**: `"OPTION"` (CE/PE contract legs) or `"STOCK"` (direct equity shares).
- **`option_strategy_mode`**: Options leg structure. Allowed values:
  - `"DIRECT"` (Single Call or Put leg)
  - `"DEBIT_SPREAD"` (Bull Call / Bear Put spread)
  - `"CREDIT_SPREAD"` (Bull Put / Bear Call spread)
  - `"SHORT_STRADDLE"` / `"LONG_STRADDLE"`
  - `"SHORT_STRANGLE"` / `"LONG_STRANGLE"`
  - `"IRON_CONDOR"` / `"IRON_FLY"`
  - `"CALENDAR_SPREAD"` (Multi-contract ratio calendar spread: 3 long monthly + 1 short weekly)
- **`exit_mode`**:
  - `"ATR"`: Dynamic ATR-based Stop Loss & Target premium orders on exchange.
  - `"SWING"`: Spot structural swing highs/lows monitored locally in Python.
  - `"POINTS"`: Fixed point Stop Loss (`points_sl_buy`/`_sell`), Target (`points_target_buy`/`_sell`), Dynamic Extended Target (`points_target_high_conviction`), Trailing (`points_trail_buy`/`_sell`), and Breakeven (`points_be_buy`/`_sell` - ratio if <= 1.0, absolute points if > 1.0).
- **`local_exit_monitoring`**: `true` monitors target/trailing/BE in Python thread; `false` places exchange bracket order.
- **`broker_safety_sl`**: `true` enables **Hybrid Crash-Proof Mode**: submits native Dhan Super Order with Hard SL on exchange at entry, then uses `modify_super_order_sl` (`PUT /super/orders/{orderId}`) to shift the exchange-resting `STOP_LOSS_LEG` to entry price on breakeven.
- **`block_expiry_day_trades`**: `1` blocks option buying on expiry day (option selling runs normally).
- **`allowed_actions`**: Restricts direction (`["BUY"]` or `["SELL"]`).
- **`strategy_overrides`**: Nested parameter overrides for specific strategy IDs.
- **`rotated_prebreakout`**: `true` marks symbol as dynamically rotated by `select_prebreakout.py` (Minervini VCP + TTM Squeeze).
- **`rotated_joint`**: `true` marks symbol as dynamically rotated by `select_joint.py` (Dual-Head ML momentum model).
- **`stock_qty_override`**: Explicit share quantity calculated from capital allocation & 5x MIS leverage for cash equity execution.

### B. `accounts.json` (Broker Account Controls)
- Supports global multipliers (`global_multiplier`), per-account instrument overrides (`instrument_overrides`), action locks (`allowed_actions`), strategy filters (`allowed_strategies`), and dedicated network binding (`source_ip`).

---

## 4. Strategy Catalog & Registry Index

All strategies inherit from `BaseStrategy` and register via `@register_strategy`. Dynamic strategy loops use **`range(1, 25)`** to include all 24 numbered strategies + `Strategy_BTST`.

| ID | Name | Core Concept | Timeframe | Execution Mode | Key Parameters / Exit Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy_1** | Strategy1 | Supertrend + EMA 21 + ADX + StochRSI | 5-Min | OPTION/STOCK | Supertrend direction flip + ADX filter |
| **Strategy_2** | Strategy2 | Dual Supertrend Pullback | 15-Min / 5-Min | OPTION/STOCK | 15m trend filter + 5m StochRSI pullback |
| **Strategy_3** | Strategy3 | Triple Momentum Breakout | 5-Min | OPTION/STOCK | EMA stack (8,18,30) + `TM_MAX_STRETCH` penalty |
| **Strategy_4** | Strategy4 | WMA Crossover & VWAP Scalp | 1-Min | OPTION/STOCK | WMA 87 vs 200 crossover + VWAP reversal |
| **Strategy_5** | Strategy5 | Gabani Value Area / Keltner | 15-Min / 5-Min | OPTION/STOCK | Volume contraction + inside bar breakouts |
| **Strategy_6** | Strategy6 | DW Range Filter | 5-Min | OPTION/STOCK | DonovanWall volatility-adaptive range filter |
| **Strategy_7** | Strategy7 | Derivative Oscillator | 5-Min | OPTION/STOCK | Double-smoothed RSI zero-line crossover |
| **Strategy_8** | Strategy8 | Opening 09:30 AM Breakout | 1-Min | OPTION/STOCK | Morning opening breakout execution |
| **Strategy_9** | Strategy9 | ML Decision Tree Rules | 1-Min | OPTION/STOCK | Rule-tree derived from 5-year Nifty data |
| **Strategy_10** | Strategy10 | Hilega Milega Reversal | 1-Min / 5-Min | OPTION/STOCK | Nitish Sir's RSI 9 vs EMA 3 / WMA 21 model |
| **Strategy_11** | Strategy11 | Gap Fade & Reversal | Daily / 1-Min | OPTION/STOCK | Fades opening gap against yesterday's direction |
| **Strategy_12** | Strategy12 | 1m RSI-100 Mean Reversion | 1-Min | OPTION/STOCK | RSI 100 mid-level cross from oversold/overbought |
| **Strategy_13** | Strategy13 | 5m Supertrend-EMA Cross | 5-Min | OPTION/STOCK | Supertrend (10, 3) + EMA 50 cross + ADX 14 |
| **Strategy_14** | Strategy14 | Nifty MCI Reversal | Daily / 1-Min | OPTION/STOCK | Counter-trend open when MCI $\ge 75$ |
| **Strategy_15** | Strategy15 | Opening Pattern Scalp | 1-Min / 15-Min | OPTION/STOCK | 09:45 AM scalp on 15m opening range breakout |
| **Strategy_16** | Strategy16 | VWAP Mean Reversion | 1-Min | OPTION/STOCK | Bollinger Band outer wicks + VWAP fade |
| **Strategy_17** | Strategy17 | Multi-Timeframe Supertrend | 1m/5m/15m | OPTION/STOCK | Requires 1m, 5m, 15m Supertrends alignment |
| **Strategy_18** | Strategy18 | 50 SMA Breakout | 5-Min | OPTION/STOCK | 50 SMA slope breakout after 09:45 AM |
| **Strategy_19** | Strategy19 | Institutional Quant ML | 1-Min | OPTION/STOCK | XGBoost ML Classifier ($P_{\text{trend}} \ge 42\%$) |
| **Strategy_20** | Strategy_20 | 15-Min Supertrend Option Writer | 15-Min / 1-Min | OPTION (SELL) | 1-Trade/Day; 15m Supertrend (10, 2.0); Target 45 pts, SL 20 pts, Breakeven 15 pts |
| **Strategy_21** | Strategy21 | NIFTY Institutional Multi-Pivot Reversal | 5-Min | OPTION (BUY) | Dhan MTF Weekly CPR (#16) + Daily CPR (#15) + Cam L3/H3 + PDH/PDL; Rejection Wick $\ge 50\%$, 2.2R, Max 2 Trades/Day |
| **Strategy_22** | Strategy22 | Triple Momentum Enhanced (TM-Pro) | 5-Min / 15-Min | OPTION (SELL) | 5m Triple EMA (8, 18, 30) + Supertrend 10/2.5 + ADX + Midday Chop Filter (13:00-13:50) + 15m Macro Trend Dynamic Conviction Sizing (`enable_dynamic_conviction`: 1 base / 2 high lots) + Dynamic Targets (`points_target_high_conviction`). Multi-Index Calibrated: NIFTY (SL 74, TP 25/45, BE 25), BANKNIFTY (SL 100, TP 45/75, BE 45), SENSEX (SL 140, TP 50/90, BE 40) with 81-82% WR. |
| **Strategy_23** | Strategy23 | Stealth Absorption Multi-Day Swing (S-AMS) | 1-Min / Multi-Day | STOCK (CNC / Delivery) | 10m Opening Box (09:15-09:25), RVOL >= 1.5x, Range <= 0.8%, Breakout before 11:00 AM. Stop at Box Low; Breakeven at +2.5%; Trailing Stop 2.0% from peak after +4.0%; Max Hold 10 Days. +₹12.2L net profit (1.92 PF) on 3-year data |
| **Strategy_24** | Strategy24 | Coiled Pre-Breakout / Pre-Breakdown Momentum | 1-Min (T+1) / Daily (T) | HYBRID (STOCK MIS / OPTION) | Daily Institutional Coiled Scanner (TTM Squeeze + NR7/Inside Day + 20 EMA Base/Shelf + Minervini 3-Wave VCP shrinkage $\le 0.52$ + 14:30–15:25 Closing Smart Money Footprint CAR $\ge 18\%$ / CLV + UVR); Anti-Gap Exhaustion Protection ($< 0.40\times$ ATR) + Anti-Rejection Wick Filter ($< 45\%$); Bidirectional: Long breakout over Day T High + 0.05 or Short breakdown below Day T Low - 0.05; 5m volume surge $\ge$ 1.25x SMA; Dynamic Breakeven at 0.65x ATR; Target at 1.15x ATR; Stop at 0.90x ATR; EOD Exit 15:15. **Smart Hybrid Routing**: F&O stocks execute as native Stock Options (`OPTSTK`, 199 registry contracts); non-F&O cash equities execute with 5x MIS leverage (`stock_qty_override` sized to ₹5L position exposure). 3-Year Walk-Forward Backtest (744 sessions): 197 trades, 59.9% WR, 2.26 PF, +₹75,170 net (1x) / +₹3,75,850 net (5x MIS), Max Drawdown ₹5,646 (7.5% DD/Net Profit). |
| **Strategy_BTST**| StrategyBTST| Buy Today Sell Tomorrow | Daily / 5-Min | OPTION/STOCK | 14:50 PM afternoon breakout for overnight gap |


---

## 5. Backtest-to-Live Parity & Key Mechanics

1. **1-Minute Base DataFrame Alignment:** Both backtester and live bot evaluate signals on 1-minute base data. Indicator calculations use completed candles (`shift(1)`) to eliminate look-ahead bias.
2. **Index + 1 Execution Rule:** Signals detected at index `i` (candle close) trigger trade execution at index `i + 1` (candle open).
3. **Dynamic Exit Monitoring:** When `USE_DYNAMIC_EXITS = "True"` in `.env`, triggering an exit signal immediately cancels pending exchange SL trigger orders and closes positions at market.
4. **Expiry Rollover:** Option buying automatically shifts to the next weekly/monthly contract on the expiry date to avoid time decay collapse. Option selling allows normal execution to capture time decay.
5. **Hybrid Crash-Proof Breakeven:** Native Dhan Super Orders are placed at entry with Hard SL on exchange. When local monitoring triggers breakeven, `modify_super_order_sl` shifts the exchange-resting `STOP_LOSS_LEG` to the entry price for 100% EC2 crash immunity.
6. **Graceful Margin Downsizing Fallback:** Live order dispatcher retries orders down to 1 lot if Dhan RMS rejects due to margin shortfall (`RS-9005` or `"Margin Insufficient"`).
7. **Automated Daily Digest:** Internal scheduler runs at 15:35 IST daily and upon bot shutdown to generate and dispatch Telegram/Slack PnL & Risk summaries (`send_daily_digest.py`).
8. **Smart Hybrid Stock & Options Execution Engine:** `select_prebreakout.py` and `select_joint.py` orchestrate setups across liquid stocks. F&O stocks are automatically routed to official monthly `OPTSTK` contracts (`stock_selection/fno_registry.json`) with contract-accurate exchange lot sizes, while non-F&O cash equities are sized using 5x SEBI intraday MIS margin (`stock_qty_override` sized to ₹5L position buying power).
9. **Dual-Engine Symbiotic Alpha Pair (100% Monthly Consistency):** `select_prebreakout.py` (Rule-based Minervini VCP + TTM Squeeze + Volume Footprint + CLV) and `select_joint.py` (True Dual-Head XGBoost with Feature Matrix 2.0) operate as an uncorrelated alpha pair. In a 260-session 1-year backtest across 200 stocks, running both concurrently delivered **13 out of 13 profitable months (100% monthly win rate)**, **+₹24,16,106.79 net profit**, a **3.39 Profit Factor**, and reduced peak-to-trough drawdown to **-₹87,502.11**. Both engines co-exist in `instruments.json` using isolated tags (`rotated_prebreakout` vs `rotated_joint`) without overwriting each other.

---

## 6. AI Agent Protocol & Guardrails

When working in this codebase, AI agents MUST follow these instructions:

1. **Consult `SYSTEM_BLUEPRINT.md` First:** Always check this file before doing broad grep or multi-file reading.
2. **Plan Before Code Edits:** Write an explicit technical implementation plan detailing file changes before modifying code.
3. **Use Range-Based File Reading:** Use `StartLine` and `EndLine` parameters in `view_file` to read only relevant code sections. Never read 3,000-line files in their entirety.
4. **Preserve Codebase Integrity:** Maintain existing strategy registration decorators (`@register_strategy`), range loops (`range(1, 25)`), and dynamic override pathways.
5. **Verify Changes:** Run unit tests (`python -m unittest discover -s tests`) or fast backtests after modifying code.

---

## 7. Historical Data Ingestion & Maintenance Pipeline

The platform uses [`fetch_historical_equity.py`](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/fetch_historical_equity.py) to maintain an institutional 1-minute historical OHLCV database in `backtest_data/` across all NSE equity stocks listed in [`EQUITY_L.csv`](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/EQUITY_L.csv):

* **Smart Incremental Updates:** Inspects the last candle of existing files (`backtest_data/{symbol}_spot.csv`) and only fetches missing deltas up to today's market close. If already up to date, it exits in 0.0s with 0 API calls.
* **Full Ingestion:** Downloads 5 years of 1-minute data in 30-day API chunks for any newly listed stocks.
* **Rate-Limit Compliance:** Enforces ~0.12s request delays with automatic exponential backoff on HTTP `429 Too Many Requests`.
* **Daily Cron Execution (03:45 PM):**
  ```bash
  ..\venv\Scripts\python.exe fetch_historical_equity.py
  ```

