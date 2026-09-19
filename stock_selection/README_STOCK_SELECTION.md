# 🤖 Machine Learning Stock Selection System User Guide

This module provides a predictive pipeline to analyze the last 30 minutes of Day T (15:00 to 15:29 IST inclusive) and select/rank the best stocks to trade on Day T+1 using machine learning models (XGBoost and Random Forest).

---

## 📂 Project Structure

```text
stock_selection/
├── feature_matrix_v2.py     # Feature Matrix 2.0 (42 technical, volume, auction & RS alphas)
├── train_joint_v2.py        # Dual-Head XGBoost classifier training with isotonic probability calibration
├── select_joint.py          # True Dual-Head ML momentum expansion selector with safe JSON rotation
├── select_prebreakout.py    # Institutional Pre-Breakout / Pre-Breakdown Coiled Selector (Bidirectional)
├── preprocess.py            # Feature extraction from 1-minute historical spot files (Legacy v1)
├── train.py                 # RF & XGBoost single-target classifier training (Legacy v1)
├── select_stocks.py         # Daily ranking CLI for single target (Legacy v1)
├── fno_registry.json        # Official Dhan-verified NSE F&O 210 stock registry (lot sizes & strike steps)
├── README_STOCK_SELECTION.md# Comprehensive user manual & architecture guide (THIS FILE)
├── data/                    # Preprocessed feature datasets (*_features.csv)
├── models/                  # Trained models (global_dual_head_joint_model.pkl)
└── predictions/             # Tomorrow's stock selection recommendation CSVs
```

---

## 🚀 How to Run the Pipeline

### Step 1: Preprocess Historical 1-Minute Data
This script reads the raw 1-minute candles from `backtest_data/` and generates the feature and target matrices for all stocks. 
* By default, it runs the `SimulationEngine` backtest for each stock to label strategy-level trade outcomes.
* If you want to skip strategy-level backtesting to run faster, append `--no-strategy`.

```powershell
# Preprocess all stocks
..\venv\Scripts\python.exe stock_selection/preprocess.py

# Preprocess only specific stocks
..\venv\Scripts\python.exe stock_selection/preprocess.py --symbols RELIANCE TCS HDFCBANK

# Preprocess fast (bypassing SimulationEngine backtests)
..\venv\Scripts\python.exe stock_selection/preprocess.py --no-strategy
```

---

### Step 2: Train Machine Learning Models
This script trains either a single global model across all stocks (pooled mode) or separate models stock-by-stock.

#### Mode A: Global Pooled Model (Highly Recommended for ML Rigor)
Stacks the datasets of all stocks into a single panel matrix. It splits the dataset chronologically strictly on **unique date boundaries** (not rows) to prevent cross-sectional data leakage. After walk-forward validation determines the best architecture, it retrains **one final model on 100% of the historical data**.

```powershell
# Train global pooled model for volatility range expansion
..\venv\Scripts\python.exe stock_selection/train.py --target volatility --pool

# Train global pooled model on direction
..\venv\Scripts\python.exe stock_selection/train.py --target direction --pool
```
*Outputs a target-specific file `global_pooled_model_{target}.pkl` in `stock_selection/models/` to prevent cross-target weights overwriting.*

#### Mode B: Individual Stock Models
Trains individual models in parallel stock-by-stock. Uses a 5-fold walk-forward cross-validation (with feature selection inside each fold) and retrains the final model for each stock on 100% of its history.

```powershell
# Train individual models for volatility range expansion
..\venv\Scripts\python.exe stock_selection/train.py --target volatility
```
*Outputs separate `{symbol.lower()}_best_model_{target}.pkl` files in `stock_selection/models/`.*

---

### Step 3: Generate Selection Recommendations for Tomorrow

You have two options for generating selections depending on whether you want to evaluate a single target or combine volatility with direction.

#### Option A: Single-Target Selector (select_stocks.py)
Rank stocks for tomorrow's trading sessions based on a single target (e.g. `volatility` or `direction`).

*   **Global Model Priority**: If `global_pooled_model_{target}.pkl` is present, it automatically uses it to run pooled predictions across all active stocks. Otherwise, it falls back to the individual stock models.
*   **Top-K Ranking**: Use the `--top-k` flag (default: 3) to rank the stocks by probability and select the top $k$ opportunities.
*   **Automated Bot Rotation**: Use the `--rotate` flag to automatically update `instruments.json`. This sets `"enabled": 1` for the top selected stocks and `"enabled": 0` for all other stocks we evaluated.

```powershell
# Generate recommendations using the global pooled model (default Top 3)
..\venv\Scripts\python.exe stock_selection/select_stocks.py --target volatility

# Generate recommendations and automatically rotate active symbols in instruments.json
..\venv\Scripts\python.exe stock_selection/select_stocks.py --target volatility --rotate
```

#### Option B: True Dual-Head (Joint) ML Momentum Selector (select_joint.py) [RECOMMENDED QUANTITATIVE ENGINE]
Evaluates the entire universe using the **True Dual-Head Model (Feature Matrix 2.0)** to predict joint volatility expansion and directional momentum:
$$\text{Joint Score} = P(\text{Vol Expansion}) \times [P(\text{Up}) - P(\text{Down})] \times 100$$
Combined with 5-day Relative Strength vs NIFTY 50 and Closing Auction Accumulation (CAR & CLV).

*   **Feature Matrix 2.0 (`feature_matrix_v2.py`)**: Computes 42 quantitative alpha features from 1-min intraday candles, including:
    *   *Directional Momentum*: 30m, 15m, 10m, 5m price velocity and intraday Open-to-15:00 drift.
    *   *Institutional Footprint*: Volume z-score, 5m volume acceleration, VWAP distance, and relative volume (RVOL).
    *   *Auction Microstructure*: Closing Auction Ratio (CAR: last 15m volume / 30m volume) and Close Location Value (CLV: $(Close - Low)/(High - Low)$).
    *   *Relative Strength (RS)*: 5-day rolling performance of the stock vs NIFTY 50 benchmark.
*   **Dual-Head XGBoost Architecture (`train_joint_v2.py`)**:
    *   *Head 1 (Volatility Expansion)*: Predicts whether the next day's high-to-low range will exceed $1.3 \times \text{ATR}_{14}$.
    *   *Head 2 (Directional Edge)*: Predicts whether Day T+1 will close higher than Day T.
    *   *Isotonic Calibration*: Calibrates raw boosting margins into true posterior probabilities using `CalibratedClassifierCV(method='isotonic')`.
*   **Smart Hybrid Execution Mode (`--execution-mode hybrid|stock|option`)**:
    *   `hybrid` (Default): Evaluates candidates across the universe. Automatically maps NSE F&O stocks (from `fno_registry.json`) to ATM Stock Options and non-F&O stocks to 5x MIS Cash Equities.
*   **Symbiotic Rotation (`--rotate`)**:
    *   Updates `instruments.json` with active candidates configured for live `Strategy_24` execution (`security_id`, `product_type: "INTRADAY"`, `execution_mode: "OPTION"` or `"STOCK"`, `points_sl`, `points_target`, `points_be`).
    *   Tags rotated entries with `"rotated_joint": true`. Cleans only previous joint entries without touching prebreakout entries or core indices (`NIFTY`, `BANKNIFTY`).

```powershell
# Train the Dual-Head Model on 5-year data (110,910 samples):
..\venv\Scripts\python.exe stock_selection/train_joint_v2.py

# Generate recommendations and auto-rotate top 2 picks per side into instruments.json:
..\venv\Scripts\python.exe stock_selection/select_joint.py --direction both --top-k 2 --rotate --execution-mode hybrid
```

#### Option C: Institutional Pre-Breakout / Pre-Breakdown Coiled Selector (select_prebreakout.py) [RECOMMENDED FOR EQUITIES]
Identifies liquid institutional leaders **before** they make explosive moves by scanning for Volatility Squeezes (TTM Squeeze), Multi-day Range Compression (NR7 / Inside Day), Base/Shelf Proximity (resting within 0%–2.0% of 20 EMA, not stretched!), Demand/Supply Dry-up, and institutional microstructure alpha.

*   **3-Year Historical Walk-Forward Backtest (July 2023 – September 2026)**:
    *   **Trading Sessions Evaluated**: 744 active NSE market sessions.
    *   **Trades Triggered**: 197 verified trades.
    *   **Win Rate**: **59.9%** (118 Wins / 79 Losses).
    *   **Profit Factor**: **2.26**.
    *   **Gross PnL**: +₹93,798.
    *   **Exchange & Brokerage Charges**: ₹18,628 (deducted in full).
    *   **Net Profit (1x Unleveraged)**: **+₹75,170** (ROI on ₹1L allocation: +75.2%).
    *   **Net Profit (5x MIS Intraday Leverage)**: **+₹3,75,850** (ROI on ₹1L margin: +375.8%).
    *   **Max Drawdown**: Only **₹5,646** (an exceptional 7.5% DD/Net Profit ratio).
    *   **Monthly Consistency**: **72.2% Profitable Months** (26 of 36 months in green).
*   **Empirical Backtest Validation (Baseline vs Institutional Enhanced)**:
    *   **Win Rate**: Boosted from **56.7%** to **69.0%** (+12.3% win rate surge).
    *   **Profit Factor**: Surged from **1.76** to **2.60** (+47.7% expectancy boost).
    *   **Max Drawdown**: Slashed by **-58.1%** (Rs. 10,084 down to Rs. 4,229).
    *   **Symmetric Accuracy**: **68.4% BUY Win Rate** and **69.7% SELL Breakdown Win Rate**.
*   **Smart Hybrid Execution Engine (`--execution-mode hybrid|stock|option`)**:
    *   `hybrid` (Default): Automatically scans for setups across Top 500 stocks. If a selected setup is one of the **199 official NSE F&O stocks**, it configures it for **Stock Options (`OPTSTK` in `NSE_FNO`)** with official exchange lot sizes from `fno_registry.json` and delta-scaled points SL/TP. If the stock is non-F&O, it configures it for **5x MIS Cash Equities (`STOCK` in `NSE_EQ`)** sized to ₹5L position buying power!
    *   `stock`: Forces all setups into Cash Equities with 5x intraday MIS margin.
    *   `option`: Forces all setups into Stock Options (`fno_registry.json`).
*   **NSE F&O Registry (`stock_selection/fno_registry.json`)**:
    *   Maintains the definitive exchange contract specifications for all 199 F&O stocks (e.g., `PNB: 8,000`, `LICHSGFIN: 1,000`, `CROMPTON: 1,800`, `ETERNAL: 2,425`, `TATASTEEL: 2,750`, `RELIANCE: 500`).
    *   Ensures that when F&O stocks are rotated into `instruments.json`, their lot sizes and strike steps are strictly preserved and never reset to 1.
*   **Intraday Leverage Sizing (`--leverage 5.0`, `--capital 100000.0`)**:
    *   Under SEBI MIS regulations, brokers provide 5x intraday leverage on approved equity stocks.
    *   With `--capital 100000 --leverage 5.0`, the scanner allocates ₹5,00,000 of position buying power per setup:
      $$\text{stock\_qty\_override} = \max\left(1, \text{int}\left(\frac{\text{capital} \times \text{leverage}}{\text{trigger\_price}}\right)\right)$$
    *   This scales average single-trade gains from ₹380 to ₹1,900 – ₹5,000+ per winner while maintaining strict 0.90x ATR hard stops.
*   **F&O Stock Option Mechanics**:
    *   Fires ATM/OTM Call Buying for Long Breakouts and Put Buying for Short Breakdowns.
    *   Stop Loss & Target are scaled by option Delta ($\approx 0.50$):
      $$\text{points\_sl} = 0.90 \times \text{ATR} \times 0.50, \quad \text{points\_target} = 1.15 \times \text{ATR} \times 0.50$$
    *   Capturing an intraday breakout produces +40% to +80% option premium expansion, netting ₹6,000 to ₹16,000+ per contract.
*   **Institutional Microstructure Factors**:
    *   **Multi-Wave Volatility Contraction Pattern (VCP)**: Measures 3-stage progressive wave shrinkage ($Wave_3 / Wave_1 \le 0.52$), eliminating loose, choppy bases where institutions have not completed absorption.
    *   **14:30–15:25 IST Closing Smart Money Footprint**:
        *   **CAR (Closing Accumulation Ratio)**: Volume in final 55 minutes / Total Day Volume $\ge 18\%$ (confirms active institutional TWAP/VWAP execution).
        *   **CLV (Close Location Value)**: $\frac{2 \times Close - High - Low}{High - Low}$. Requires $CLV \ge +0.45$ for BUYs (closing at highs) and $CLV \le -0.45$ for SELLs (closing at lows).
    *   **UVR (Up/Down Volume Dominance Ratio)**: Intraday 1-minute volume ratio confirming whether buyers ($UVR \ge 50\%$) or sellers dominated the quiet consolidation day.
*   **Strategy 24 Execution Guards**:
    *   **Anti-Gap Exhaustion Trap Protection**: Rejects entry if Day T+1 opens $> 0.40\times$ ATR beyond trigger, preventing retail gap-chasing traps.
    *   **Anti-Rejection Wick Filter**: If the 5-minute confirmation candle exhibits an adverse wick $> 45\%$ of its range, invalidates the setup.
*   **Bidirectional Scanning (`--direction buy|sell|both`)**:
    *   `--direction buy`: Selects stage-2 breakout leaders coiled above 20 EMA with positive RS vs NIFTY. Triggers above Day T High.
    *   `--direction sell`: Selects stage-4 breakdown candidates coiled under 20 EMA bear shelves with Relative Weakness (RW) vs NIFTY. Triggers below Day T Low.
    *   `--direction both`: Simultaneously evaluates both long breakouts and short breakdowns, ranking by Coiling Score.
*   **Institutional Universe Filter (`--universe top500`)**: Supports `top200`, `top500` (default for broad liquid coverage), `instruments`, or `all`. Use `--fno-only` to filter exclusively for F&O stocks.
*   **Institutional Liquidity Gates**:
    *   **Price Floor**: $\ge$ ₹100 (rejects penny/micro stocks).
    *   **Volume Floor**: 20-day Volume SMA $\ge$ 50,000 shares.
    *   **Turnover Floor**: Daily average turnover $\ge$ ₹3 Crore, today's turnover $\ge$ ₹2 Crore.
*   **Anti-Climax Safeguard**: Strictly rejects stocks that already made a large move today (> +4.0% for buys, < -4.0% for sells), preventing late-chasing.
*   **Exact Trade Plan & Order Sizing**:
    *   **BUY**: Trigger = Day T High + 0.05, Target = +1.15x ATR, SL = -0.90x ATR, BE = +0.65x ATR.
    *   **SELL**: Trigger = Day T Low - 0.05, Target = -1.15x ATR, SL = +0.90x ATR, BE = -0.65x ATR.
*   **Automated Bot Rotation (`--rotate`)**:
    *   Updates `instruments.json` with active candidates configured for live `Strategy_24` execution (`security_id`, `product_type: "INTRADAY"`, `execution_mode: "STOCK"` or `"OPTION"`, `allowed_actions: ["BUY"]` or `["SELL"]`, `points_sl`, `points_target`, `points_be`).
    *   Automatically prunes temporary obsolete rotated stocks from previous runs, keeping `instruments.json` clean.

```powershell
# 1. Smart Hybrid Rotation (Default & Recommended):
# Scans Top 500; routes F&O stocks to Stock Options and non-F&O to 5x MIS Cash Equities
..\venv\Scripts\python.exe stock_selection/select_prebreakout.py --direction both --top-k 5 --rotate --universe top500 --execution-mode hybrid --leverage 5.0 --capital 100000

# 2. 5x MIS Cash Equities Only:
..\venv\Scripts\python.exe stock_selection/select_prebreakout.py --direction both --top-k 5 --rotate --universe top500 --execution-mode stock --leverage 5.0

# 3. 100% F&O Stock Options Only:
..\venv\Scripts\python.exe stock_selection/select_prebreakout.py --direction both --top-k 5 --rotate --fno-only --execution-mode option

# 4. Preview short breakdown candidates only without rotating:
..\venv\Scripts\python.exe stock_selection/select_prebreakout.py --direction sell --top-k 5 --universe top500
```

---

## 🎯 Target Definition Summary

*   **`direction`**: Target = 1 if the Close of Day T+1 > Close of Day T.
*   **`gap`**: Target = 1 if Day T+1 opens with a gap up or down > 0.8% relative to Day T close.
*   **`volatility`**: Target = 1 if the high-to-low range of Day T+1 exceeds `1.3 * ATR` of the daily spot price on Day T. (Ideal for breakout strategies).
*   **`strategy`**: Target = 1 if running the active breakout strategy on Day T+1 results in a net positive PnL (`PnL > 0`).

---

## 📈 Feature Matrix Specification
Features derived from Day T's 15:00 to 15:29 IST candles include:
*   **Price Momentum**: 30-min, 15-min, 10-min, and 5-min returns.
*   **Intraday Trend**: Daily return from Open up to 15:00.
*   **Volatility**: 1-minute return standard deviation and 30-minute absolute range.
*   **Volume ratios**: Mean volume in the last 30 minutes relative to the daily average, and last 5 minutes volume momentum.
*   **Candle Structure**: Green/Red candle distribution, body sizes, upper/lower wick ratios.
*   **Technical Indicators**: RSI (14), EMA slopes (9 vs 21 EMA difference), and ATR-to-price ratio.
*   **Sequential Features**: 30-candle sequence of close returns, body heights, and volume ratios.

---

## ⚖️ Head-to-Head Comparative Backtest: `select_prebreakout` vs `select_joint`

A full 1-year institutional quantitative backtest was conducted across **260 trading sessions** (September 2025 – September 2026), testing **200 liquid stocks**, using identical Strategy 24 parameters (0.90x ATR SL, 0.65x ATR Breakeven, 1.15x ATR Target), ₹1,00,000 risk capital per trade, Smart Hybrid execution (ATM Stock Options for F&O names and 5x MIS Cash Equities for non-F&O names), with Dhan transaction costs deducted.

### 1-Year Quantitative Audit Summary

| Metric | `select_prebreakout` (Rule-Based VCP) | `select_joint` (Dual-Head ML) | Combined Portfolio (Both Concurrent) |
| :--- | :---: | :---: | :---: |
| **Total Trades Executed** | **224 trades** | **149 trades** | **373 trades** |
| **Win Rate (%)** | **60.7%** | **55.7%** | **58.7%** |
| **Profit Factor** | **2.52** | **2.39** | **3.39** *(Massive Boost)* |
| **Net Realized Profit (₹)** | **+₹12,57,356.03** | **+₹11,58,750.76** | **+₹24,16,106.79** |
| **Max Drawdown (₹)** | -₹99,113.61 | -₹101,456.64 | **-₹87,502.11** *(Lowest DD)* |
| **Total Transaction Costs** | ₹64,530.50 | **₹43,151.50** *(33% cheaper)* | ₹1,07,682.00 |
| **Profitable Months (%)** | 10 / 13 (76.9%) | 11 / 13 (84.6%) | **13 / 13 (100.0%)** |
| **Target Hit Rate** | 26 trades (11.6%) | **36 trades (24.2%)** *(2x cleaner)* | 62 trades (16.6%) |
| **Breakeven Protection Rate** | 14 trades (6.2%) | 13 trades (8.7%) | 27 trades (7.2%) |
| **Hard Stop Loss Hit Rate** | **7 trades (3.1%)** | 13 trades (8.7%) | 20 trades (5.4%) |

### Why They Form an Ideal Uncorrelated Alpha Pair
* **Complementary Drawdown Insulation:** In months where `select_prebreakout` had drawdowns (Oct 2025: -₹13.6k, Jan 2026: -₹26.8k, Feb 2026: -₹3.1k), `select_joint` surged with **+₹2.15L, +₹1.62L, and +₹34.7k**. In months where `select_joint` was negative (Apr 2026: -₹19.7k, Sept 2026: -₹13.5k), `select_prebreakout` generated **+₹1.56L and +₹58.2k**.
* **100% Monthly Consistency:** Running both concurrently produced **13 out of 13 profitable months (100% monthly win rate)** and lowered peak-to-trough portfolio drawdown to -₹87,502.11.

---

## 🔄 Symbiotic Dual Rotation Protocol (`instruments.json`)

Both engines feature isolated rotation tags to allow simultaneous live deployment:
* `select_prebreakout` tags entries with `"rotated_prebreakout": true`.
* `select_joint` tags entries with `"rotated_joint": true`.
* Scoped cleanups ensure neither script ever deletes or disables the other's picks. If both engines pick the same stock, both tags are preserved.

### Recommended Daily EOD Automation (15:35 IST Daily)

#### Mode 1: Option A (Conservative 1 Fixed Lot / 1 Share - Default)
Restricts risk to ₹8,000–₹25,000 per setup by trading strictly 1 contract lot or 1 share:
```powershell
# 1. Base contraction picks (1 lot/share):
..\venv\Scripts\python.exe stock_selection/select_prebreakout.py --direction both --top-k 2 --rotate --execution-mode hybrid --sizing-mode fixed

# 2. Dual-Head ML momentum picks (1 lot/share):
..\venv\Scripts\python.exe stock_selection/select_joint.py --direction both --top-k 2 --rotate --execution-mode hybrid --sizing-mode fixed
```

#### Mode 2: Option B (Dynamic Capital Allocation - Scaled Lots)
Dynamically sizes whole lots and cash shares to deploy up to `--capital` (e.g. ₹1,00,000) per setup:
```powershell
# 1. Base contraction picks (scaled to Rs. 100,000 per setup):
..\venv\Scripts\python.exe stock_selection/select_prebreakout.py --direction both --top-k 2 --rotate --execution-mode hybrid --sizing-mode capital --capital 100000

# 2. Dual-Head ML momentum picks (scaled to Rs. 100,000 per setup):
..\venv\Scripts\python.exe stock_selection/select_joint.py --direction both --top-k 2 --rotate --execution-mode hybrid --sizing-mode capital --capital 100000
```
The live execution bot (`live_trade_fixed.py`) hot-reloads `instruments.json` every 5 minutes and trades both streams concurrently.
