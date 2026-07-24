# SATP Automated Testing Guide

This guide describes how to run, write, and maintain automated tests in the Smart Algorithmic Trading Platform (SATP). Establishing automated tests helps safeguard the integrity of signal processing and configuration overlays as the codebase grows.

---

## 🚀 Running the Test Suite

All tests are implemented using Python's standard `unittest` library. No additional dependencies are required.

### 1. Run All Tests
Execute this command from the repository root:
```powershell
..\venv\Scripts\python.exe -m unittest discover -s tests
```

### 2. Run a Specific Test Module
To run only a specific test class (for faster diagnostics):
```powershell
# Run only parameter loader tests
..\venv\Scripts\python.exe -m unittest tests/test_parameter_loader.py

# Run only signal merging tests
..\venv\Scripts\python.exe -m unittest tests/test_signal_merging.py

# Run only regime filtering tests
..\venv\Scripts\python.exe -m unittest tests/test_regime_filtering.py
```

---

## 📂 Core Test Suite Overview

The test files reside in the `tests/` package directory:

*   **`test_parameter_loader.py`**: Validates that system-wide configuration keys (such as `allowed_regimes_trend`, `allowed_regimes_vol`, and `allowed_actions` defined inside `instruments.json`) are correctly parsed and passed to strategy constructors, even when they do not exist inside the individual strategy's `get_default_params()` dictionary.
*   **`test_signal_merging.py`**: Simulates concurrent signal generation across multiple active strategies (e.g., `Strategy_3` and `Strategy_10`) and asserts that entry/exit signals merge seamlessly without collisions or overwrites.
*   **`test_regime_filtering.py`**: Feeds mock data with pre-calculated ADX values into the strategy base class to verify that the mathematical boundaries for trend regimes (`TREND`, `RANGE`, `NEUTRAL`) correctly filter signals according to the instrument settings.

---

## 🧪 How to Write New Tests

When adding a new strategy (e.g., `Strategy_11`) or modularizing a component, you should write a corresponding test under the `tests/` directory.

### Test Structure Template:
Create a new file `tests/test_my_feature.py` and use the following template:

```python
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

class TestMyFeature(unittest.TestCase):
    def setUp(self):
        # Initial setup run before every test method
        self.mock_data = pd.DataFrame({
            'open': [100.0, 101.0],
            'close': [100.5, 100.8]
        })

    def test_feature_behavior(self):
        # 1. Arrange (Setup inputs and mocks)
        test_val = 100.0
        
        # 2. Act (Execute target logic)
        result = self.mock_data['open'].iloc[0]
        
        # 3. Assert (Verify correctness)
        self.assertEqual(result, test_val)

if __name__ == '__main__':
    unittest.main()
```

---

## 🛡️ Best Practices
1.  **Run Tests Before Commits**: Always execute `python -m unittest discover -s tests` before committing edits or deploying to AWS.
2.  **Mock Expensive Operations**: Do not query the live Dhan API during unit testing. Use Python's standard `unittest.mock.patch` to simulate API responses.
3.  **Keep Data Naive**: Ensure test data dataframes reflect standard schema index formats (naive datetimes) to prevent timezone conversion discrepancies.
