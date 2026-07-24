# SATP Parameter Optimization & Walk-Forward Validation Guide

Welcome to the parameter optimization documentation for the Smart Algorithmic Trading Platform (SATP). This guide explains how to use our unified optimizer ([optimize.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/optimize.py)) to find, fine-tune, and validate strategy and risk parameters.

---

## 1. System Design: The Walk-Forward Framework

In algorithmic trading, parameter overfitting is the most common reason strategies lose money live despite looking highly profitable in backtests. Decoupling risk optimization (SL/TP) from strategy optimization (signal rules) creates a sequential fallacy where exit rules are tuned to sub-optimal indicators.

Our optimizer solves this using a **joint multi-stage coarse-to-fine parameter sweep** supporting two modes:
1. **Single-Split Mode (`--mode single`)**: Runs a 67% training partition and validates on a 33% out-of-sample partition.
2. **Rolling Walk-Forward Mode (`--mode rolling`)**: Partitions data into rolling overlapping windows (Train 6 months, Test 2 months, rolling forward by 2-month steps) to ensure the strategy is validated over diverse market regimes.

### Walk-Forward Optimization (WFO) Timeline
```
Timeline: ═══════════════════════════════════════════════════════════════►
Window 1: [█████████ Train 6M █████████] [░░ Test 2M ░░]
Window 2:         [█████████ Train 6M █████████] [░░ Test 2M ░░]
Window 3:                 [█████████ Train 6M █████████] [░░ Test 2M ░░]
OOS Curve:                             [░░░░ Combined Out-Of-Sample Trades ░░░░]
```
For each window, the optimizer sweeps parameters on the **Train** block (In-Sample), selects the plateau center using K-Means clustering, executes the chosen parameter set on the **Test** block (Out-of-Sample), and aggregates all out-of-sample trades to evaluate the combined WFO equity curve.

---

## 2. Command Line Usage & Argument Reference

Execute the optimizer using the Python virtual environment launcher from your workspace directory:

```powershell
# Syntax: python optimize.py --strategy [STRATEGY_NAME] [FLAGS]
```

### Argument Reference

| CLI Flag | Short | Default | Allowed Values | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`--strategy`** | `-s` | `"Strategy_3"` | `Strategy_1` to `Strategy_14` | The strategy configuration code class to optimize. |
| **`--days`** | `-d` | `720` | e.g. `90`, `180`, `365`, `730` | Calendar lookback span in days. |
| **`--leg`** | `-l` | None (reads `.env`) | `BUY`, `SELL`, `BOTH` | Directional leg mode filter. Falls back to `.env` if omitted. |
| **`--mode`** | — | `"single"` | `"single"`, `"rolling"` | Run mode: legacy train/test split or rolling walk-forward (WFO). |
| **`--max-combos`**| — | `50` | e.g. `20`, `30`, `100` | Safety cap for strategy combinations. Samples randomly if exceeded. |
| **`--symbol`** | `--sym` | None | e.g. `NIFTY`, `COLPAL` | Specify a single symbol to optimize instead of all enabled. |
| **`--exit-sweep`**| — | False | Flags / Actions | Automatically sweep and compare POINTS, ATR, and SWING exit modes. |

### Configuration Requirements
The optimizer reads [instruments.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/instruments.json) to locate symbols to optimize.
* The script loops through and optimizes **only** symbols where `"enabled": 1` in `instruments.json`.
* If no enabled symbol is found, it defaults to optimizing **NIFTY**.

---

## 3. How to Run Optimization (Examples)

### A. Run Rolling Walk-Forward Optimization on COLPAL
Runs WFO partitioning (6-month train / 2-month test steps) on COLPAL:
```powershell
..\.venv\Scripts\python.exe optimize.py -s Strategy_3 -l BUY -d 360 --symbol COLPAL --mode rolling
```

### B. Run Legacy Single Sweep (NIFTY, SELL mode)
Used to optimize Strategy 3 for selling options using a single 67%/33% split:
```powershell
..\.venv\Scripts\python.exe optimize.py --strategy Strategy_3 --days 720 --leg SELL --mode single
```

### C. Large Strategy Sweep with Safety Cap
Restrict the maximum combinations to 30 to prevent long CPU runtimes:
```powershell
..\.venv\Scripts\python.exe optimize.py -s Strategy_6 -d 720 --max-combos 30
```

### D. Run Automated Exit Mode Comparison Sweep
Compare POINTS, ATR, and SWING exit modes side-by-side on NIFTY:
```powershell
..\.venv\Scripts\python.exe optimize.py --symbol NIFTY -s Strategy_14 -d 180 --exit-sweep --max-combos 15
```

---

## 4. The Institutional-Grade Upgrades & Metrics

When evaluating combinations or walk-forward windows, the system implements the following checks:

### 1. Monte Carlo Robustness (Priority 2)
To verify that profitability is not a function of lucky trade order, the returns of the equity curve are randomly shuffled $1,000$ times:
* **`MC_Worst_DD_95Pct`**: The peak-to-trough drawdown that $95\%$ of path shuffles did not exceed.
* **`MC_Median_DD`**: Median path-shuffled drawdown.
* **`MC_Robustness`**: Calculated as `Net_PnL / MC_Worst_DD_95Pct`. Fragile trading curves with high path dependency are penalized.

### 2. Market Regime Breakdown (Priority 3)
On trade entry, the engine classifies the market environment to track performance indicators per regime:
* **Trend Regime**: Uses the Average Directional Index (ADX). `ADX > 25` = `TREND`, `ADX < 20` = `RANGE`.
* **Volatility Regime**: Uses relative ATR percentage (`Spot_ATR / Close * 100`) compared to the dataset's median. Categorized into `HIGH_VIX` and `LOW_VIX`.
* Outputs separate Profit Factors (`PF_Trend`, `PF_Range`, `PF_High_VIX`, `PF_Low_VIX`) to detect regime vulnerabilities.

### 3. Equity Curve Quality ($R^2$) (Priority 4)
Fits a linear regression line to the trade-by-trade cumulative profit curve:
* **`Equity_R2`**: Measures the coefficient of determination $R^2$. Smooth, consistent equity growth yields $R^2 \approx 1.0$, whereas erratic, jumpy curves approach $0.0$.

### 4. Parameter Clustering Plateau & Objective Index (Priority 5)
Peak values in optimization grids are often overfitted "spikes" that fail live.
* **Balanced Robustness Score**: We evaluate parameters using a normalized weighted index:
  $$\text{Robustness} = 0.40 \times \text{Profit Factor} + 0.40 \times \text{Recovery Factor} + 0.10 \times \text{Win Rate} + 0.10 \times \text{Stability}$$
  where $\text{Recovery Factor} = \text{Net PnL} / \text{Max Drawdown}$. This ensures parameter selection favors continuous, consistent returns and low drawdowns.
* **Centroid Search**: The top Stage 2 configurations are grouped into 3 clusters using **K-Means clustering** (normalized SL, TP, and Trailing coordinates). The centroid of the largest cluster (the plateau) is selected to choose a stable parameter zone.
* **Stage 2 Safety Cap**: Standard fine-grained risk parameter sweeps are capped at a maximum of **100 random combinations** to prevent combinatorial explosions and accelerate optimization by 16x.

### 5. Remove Lucky Trades Test (Priority 6)
* Sorts trade PnLs, excludes the top 5% highest-PnL trades (min 3), and recalculates Net PnL.
* Scales down the robustness score moderately by `(1.0 - 0.5 * lucky_drop_pct)` to identify systems relying on single outliers.

### 6. Period Stability Score & Dynamic Trade Filtering (Priority 7)
* **Dynamic Trade Filter**: Dynamic thresholds prevent low-frequency strategies from being discarded:
  * *Low-frequency (e.g. Strategy 14)*: Base min 4 trades, scaling at 0.5 trades/month.
  * *BTST / Strategy 11*: Base min 8 trades, scaling at 1.5 trades/month.
  * *Default*: Base min 18 trades, scaling at 3.0 trades/month.
* **Consistency Ratio**: Segments profits into calendar months. Scaled dynamically: `robustness *= (0.5 + 0.5 * consistency_ratio)` to prevent excessive penalization over short test datasets.

### 7. Early-Rejection Engine (Priority 8)
* Aborts backtests early to save compute cycles. After the first 30 trades and every 5 trades thereafter, the run is terminated if running `Profit_Factor < 0.7` and `Win_Rate < 30%` OR the running `Net_PnL` falls below $-5R$.

---

## 5. Analyzing Reports and Output Data

All optimization files are saved to the [optimization_results/](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/optimization_results/) directory:

### A. Fine Tuning Output (`{symbol}_fine_risk_optimization_{execution_mode}_{exit_mode}.csv`)
Contains the Stage 2 configurations sorted by `Robustness_Score` descending.

### B. Walk-Forward Output (`{symbol}_walk_forward_validation.csv`)
Logs metrics for each individual Train/Test window, plus a final **`COMBINED_OOS`** row representing the unified Out-of-Sample Walk-Forward results.

### C. Exit Mode Sweep Output (`{symbol}_exit_mode_sweep_comparison.csv`)
Logs the comparative performance results across POINTS, ATR, and SWING exit modes on test data, containing columns: `Exit_Mode`, `SL`, `Target`, `Trades`, `Win_Rate`, `Profit_Factor`, `Net_PnL`, `Max_DD`, and `Robustness_Score`.

### D. Interpreting the Robustness Verdict
*   **`[ROBUST]`**: The strategy is profitable on both splits (or combined WFO OOS). PROFITABLE and stable.
*   **`[OVERFITTED]`**: The strategy is profitable on training data but lost money on out-of-sample data. **Do not execute live.**
*   **`[NOT VIABLE]`**: The strategy loses money on in-sample data.

---

## 6. Instrument-Specific Custom Optimization Grids

By default, the optimizer constructs a standard range of test values based on training spot average ATR or configured point thresholds. However, to avoid meta-overfitting and optimize search efficiency for unique assets, you can define custom grids directly in [instruments.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/instruments.json) using the `"optimization_grid"` key.

### Custom Grid Integration
- **Direct Cartesian Product**: If a custom grid is configured, the Stage 2 fine search sweeps the exact Cartesian product of the parameters specified. This allows testing exact asymmetric settings (e.g. decoupling buy and sell grids, or sweeping specific point distances).
- **Unbiased Coarse Search Subsampling**: For the Stage 1 coarse search (which joint-searches indicators and risk settings), the optimizer automatically subsamples at most 4 combinations representing boundary and middle values of the custom grid.
- **Fail-safe Fallbacks**: If any parameter lists are missing from the `"optimization_grid"`, the optimizer falls back automatically to config values or baseline defaults.

