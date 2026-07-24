# 🤖 Machine Learning Stock Selection System User Guide

This module provides a predictive pipeline to analyze the last 30 minutes of Day T (15:00 to 15:29 IST inclusive) and select/rank the best stocks to trade on Day T+1 using machine learning models (XGBoost and Random Forest).

---

## 📂 Project Structure

```text
stock_selection/
├── preprocess.py        # Extracts features & outcomes from 5-year Spot 1-minute files
├── train.py             # Trains RF & XGBoost classifiers (individual-stock or global pooled panel)
├── select_stocks.py     # Generates daily selection rankings for a single target
├── select_joint.py      # Generates joint volatility + direction rankings with automated trade side constraint
├── README_STOCK_SELECTION.md # User Guide (This file)
├── data/                # Preprocessed feature datasets (*_features.csv)
├── models/              # Target-specific models (global_pooled_model_{target}.pkl or individual *_{target}.pkl)
└── predictions/         # CSV files containing tomorrow's stock selections
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

#### Option B: Joint Volatility + Direction Selector (select_joint.py) [RECOMMENDED]
Evaluate both `volatility` and `direction` models simultaneously to filter for the most volatile stocks and automatically determine which side to trade (BUY vs. SELL).

*   **Selection Ranking**: Ranks stocks by their `volatility` selection score first to guarantee high-potential range expansion.
*   **Direction Overrides**: Evaluates the `direction` model's probability for the selected stocks:
    *   Direction $\ge 50\%$ $\rightarrow$ BULLISH (BUY)
    *   Direction $< 50\%$ $\rightarrow$ BEARISH (SELL)
*   **Automated Rotation & Actions Constraint**: Running with `--rotate` updates `instruments.json` by:
    *   Enabling selected stocks (`"enabled": 1`).
    *   Constraining trading to the predicted direction (`"allowed_actions": ["BUY"]` or `["SELL"]`). This completely automates trade execution constraints!

```powershell
# Generate joint recommendations and rotate active symbols in instruments.json with directional constraints
..\venv\Scripts\python.exe stock_selection/select_joint.py --rotate
```

*A ranked table will print to the console, a detailed CSV scorecard will be saved in `stock_selection/predictions/`, and a Telegram notification will be dispatched if webhook settings are configured.*

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
