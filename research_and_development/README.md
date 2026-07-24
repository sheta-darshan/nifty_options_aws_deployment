# Research & Development Directory

This directory contains utility scripts, analysis tools, comparisons, and statistical logs used for backtesting, debugging, and optimizing strategies.

## 🛠 Script Directory Catalog

### 1. Verification & Verification Scripts
*   **[verify_backtest.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/verify_backtest.py)**: Cross-verifies backtested option Entry/Exit prices against the NSE F&O bhavcopies downloaded directly from the NSE archives.
*   **[verify_data.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/verify_data.py)**: A quick structural validator checking the downloaded historical minute CSV caches for continuity and indexing errors.

### 2. Parameter Tuning & Optimization Guides
*   **[compile_best_settings.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/compile_best_settings.py)**: Compiles the best parameter candidate offsets (win rates, profit factors) returned by Stage 1 coarse sweeps and updates the CSV matrix.
*   **[set_starting_settings.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/set_starting_settings.py)**: Programmatically computes starting point-based targets/SL values (e.g. SL at 30% of ATM premium, Target at 60%) to seed initial parameters in JSON config.
*   **[generate_statistical_grids.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/generate_statistical_grids.py)**: Automatically inserts ATR-based percentage ranges inside STOCK definitions for grid search optimizations.

### 3. Comparison & Debugging Utilities
*   **[compare_s3_s4.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/compare_s3_s4.py)**: Runs multi-index backtests for Strategy 3 (Triple Momentum) and Strategy 4 (WMA/VWAP Breakout) and compares their win rates side-by-side.
*   **[debug_signals.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/debug_signals.py)**: Inspects signals and resampled indicator columns on a specific security cache (e.g. POWERINDIA).
*   **[debug_stocks.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/debug_stocks.py)**: Evaluates indicator values for the live stock scanner data on disk.

### 4. Dhan API Scratchpads
*   **[check_expiries.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/check_expiries.py)**: Tests options expiry API list responses with raw HTTP requests.
*   **[inspect_dhan.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/inspect_dhan.py)**: Audits the imported SDK version signatures.
*   **[scratch_fetch.py](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/research_and_development/scratch_fetch.py)**: Fetches the latest 10 orders from the broker active book.

---
*Note: Run all scripts from the repository root to ensure virtual environments and path references resolve properly.*
