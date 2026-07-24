# SATP Latency & Scalability Report: Scaling from 2 to 40 Instruments

## 1. Executive Summary

This report evaluates the timing, latency, and scalability characteristics of the Smart Algorithmic Trading Platform (SATP) live trading bot (`live_trade_fixed.py`). We analyze the latency profile across different order placement facilities (Standard vs. Bracket/Super Orders, single vs. multi-leg options, stock vs. options), technical calculations, and multi-account loops. 

Specifically, we compare system performance when scaling from **2 enabled instruments** (e.g., NIFTY index and one stock) to **40 enabled instruments** (e.g., a diversified stock option trading basket).

### Key Findings:
1. **Data Ingestion Bottleneck**: At 40 instruments, fetching spot candles sequentially or in individual threads causes a queue at the Dhan API data rate limiter (5 requests/sec). The last instrument thread will experience up to **8.0 seconds of latency** before starting signal processing.
2. **Gate Keeper Overhead**: If Gate Keeper validation is enabled under options mode, it requires fetching historical candles for 3 strikes (ATM, ATM-1, ATM+1). For 40 instruments, a cluster of signals will instantly trigger Dhan's **429 Too Many Requests** circuit breaker (which halts all bots for 30 seconds).
3. **Sequential Multi-Account Ordering**: Orders are dispatched to accounts (typically 4+ accounts) sequentially. For multi-leg options (e.g., Spreads or Straddles), this sequential dispatch leads to execution delays of **1.5 to 3.2 seconds**, exposing the trade to execution slippage.
4. **Position Polling Redundancy**: The local monitoring loop checks exits every 5 seconds. If multiple instruments are active, they independently poll positions (`get_positions`) for all accounts. With 10 active positions, this generates **40 position checks every 5 seconds**, causing rate limit starvation.

---

## 2. Latency Profiles in Different Situations

### A. Order Placement Facilities
Order placement latency depends heavily on the execution mode and order type:

| Facility | API Calls Required | Exchange Processing | Local Thread Latency (Sequential) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Standard Orders** | 1 (`place_order`) | Immediate | ~150 - 250 ms per account | Relies on local Python monitoring for exits. |
| **Bracket / Super Orders** | 1 (`place_super_order`) | Validates SL/TP levels | ~250 - 450 ms per account | Exchange-side SL/TP. Slightly higher API latency. |
| **DIRECT Option Leg** | 1 per account | Order entry | ~1.6 seconds (4 accounts) | Single ATM Call/Put contract. |
| **DEBIT / CREDIT SPREAD** | 2 per account | Leg 1 Entry + Leg 2 Entry | ~3.2 seconds (4 accounts) | Sequential order entry increases spread slippage. |
| **STRADDLE / STRANGLE** | 2 per account | Leg 1 Entry + Leg 2 Entry | ~3.2 seconds (4 accounts) | Delta-neutral execution requires quick entries. |
| **IRON CONDOR / FLY** | 4 per account | 4 independent order legs | ~6.4 seconds (4 accounts) | Extreme delay; highly vulnerable to slippage. |
| **STOCK Mode** | 1 per account | Immediate | ~150 - 250 ms per account | Direct equity trading (no contract resolution). |

### B. Computational Overhead
*   **Technical Indicators (Resampling + `pandas-ta`)**: ~1 - 5 ms per instrument. The calculations are fast, but because of Python's Global Interpreter Lock (GIL), running 40 threads forces serial execution. However, <200 ms total CPU time is negligible on a 1-minute cycle.
*   **Option Chain & Greeks Resolution**:
    *   *API Queries*: ~150 - 300 ms network roundtrip.
    *   *Security Master CSV Scan*: Searching the ~40MB cache files (`dhanhq_cache_{prefix}.csv`) takes **200 - 600 ms** of CPU time if done via regex searches or raw pandas scans on every signal. Doing this on multiple threads concurrently blocks the GIL.
*   **Gate Keeper Entry Validation**:
    *   *API Queries*: Requires 3 historical candle API calls (ATM, ATM-1, ATM+1 strikes) to measure price velocity and OI/volume.
    *   *Total Latency*: Minimum **600 ms** network time + rate-limiter queuing. Bypassing missing columns (OI/Volume) saves logic computation, but does not reduce network latency.

### C. Local Exit Monitoring (Standard Exits & Swing Exits)
*   **Spot Swing Exit**: Requires fetching spot index LTP (~200 ms).
*   **Contract Swing & Points Exit**: Requires fetching option contract LTP (~200 ms).
*   **Position Verification**: Requires fetching positions from broker (`get_positions`) for each active account (~200 ms per account).
*   **Cancel & Close**: If exit is triggered, requires canceling pending orders (~200 ms) and placing a market close order (~200 ms).

---

## 3. Scale Comparison: 2 Instruments vs. 40 Instruments

The table below illustrates the mathematical differences in API request load and latency when scaling the system:

| Performance Metric | 2 Instruments (Low Scale) | 40 Instruments (High Scale) | Scaling Impact |
| :--- | :--- | :--- | :--- |
| **Active Threads** | 2 bots + 2 exit monitors = 4 | 40 bots + 40 exit monitors = 80 | **20x Thread Context Switching** |
| **Spot Data Fetches (Per min)** | 2 requests | 40 requests | **20x Data Requests** |
| **Data Fetch Queuing Time** | ~100 - 300 ms (Concurrently) | **~8.0 seconds** (Queued at 5 req/s) | **26x Signal Delay** |
| **Max Simultaneous Signals** | 1 - 2 | 5 - 10 | **Concurrently signaling clusters** |
| **Gate Keeper API Requests** | 3 - 6 requests | 15 - 30 requests | **Rate limit exhaustion (429 trigger)** |
| **Order Placement Latency** | ~400 - 800 ms (2 legs, 1 acc) | **~4.0 - 8.0 seconds** (10 req/s limit) | **10x execution slippage** |
| **Exit Monitor API Load (10 active)**| 4 position checks / 5s | **40 position + 10 LTP checks / 5s** | **Continuous Rate Limit Block** |

---

## 4. Identified Bottlenecks & Scale Risks

```
[40 Instrument Threads wake up at 09:20:00]
         │
         ├──► sequential data fetches (Rate Limit: 5 req/s)
         │    └───► Latency: 8.0s for the 40th bot
         │
         ├──► 5 bots signal simultaneously (Multi-Account: 4 accounts)
         │    └───► 40 order requests (Rate Limit: 10 req/s)
         │          └───► Latency: 4.0s delay for last order (Slippage)
         │
         └──► 10 exit monitors run independently every 5s
              └───► 50 API requests every 5s (Exceeds limit)
                    └───► Dhan triggers 429 Circuit Breaker (30s Lockout)
```

### 1. Spot Data Queuing (The 09:20:00 Problem)
When the market opens or on new minute boundaries, all 40 threads call `process_cycle()` and query the Dhan API. Since Dhan limits historical data queries to **5 requests/second**, the rate limiter serializes these requests. The 40th thread has to wait 8 seconds before it receives its data, making its breakout signal obsolete or heavily delayed.

### 2. Exit Monitor API Overload (The Polling Trap)
Each of the 40 bots runs an independent `_local_monitoring_loop` thread sleeping for 5 seconds. If 10 bots have open positions across 4 accounts:
*   Each of the 10 threads queries `get_positions` for 4 accounts every 5 seconds = 40 requests.
*   Each thread queries contract LTP = 10 requests.
*   **Total = 50 API requests every 5 seconds (10 req/sec)**.
This continuously saturates Dhan's rate limits and triggers a 30-second circuit breaker, preventing execution during critical exit moments.

### 3. Sequential Multi-Account Execution
Under options strategies (Spreads/Straddles), order placement loops through accounts sequentially:
```python
for acc in accounts:
    resp = acc_api.place_entry_order(...)
```
Each API call takes 200 ms. For 4 accounts and a 2-leg spread (8 API calls), the execution takes **1.6 seconds**. For an Iron Condor (16 API calls), it takes **3.2 seconds**. This time gap creates severe leg-execution imbalances (leg risk) where the index moves before the spread is completed.

---

## 5. Architectural Recommendations for 40+ Stocks

To successfully scale SATP to trade 40 stocks concurrently across multiple accounts, the following refactoring steps are highly recommended:

### 1. Centralized Position Manager (Eliminate Duplicate Polling)
*   **Current**: Each thread runs its own loop checking broker positions.
*   **Upgrade**: Implement a single, centralized global position checking thread. This thread queries `get_positions` once every 2-5 seconds for the 4 accounts, updates a shared thread-safe global cache, and all 40 bots read from this local memory.
*   **Impact**: Reduces exit monitor API usage from **50 req/5s** to **4 req/5s** (a **92% reduction**).

### 2. Batch Spot Data Fetching
*   **Current**: 40 threads make 40 independent API requests to fetch spot candles.
*   **Upgrade**: Replace individual fetches with a single batch lookup using Dhan's `/marketfeed` WebSockets or `/ohlc` batch APIs to retrieve spot data for all 40 symbols in a single request.
*   **Impact**: Cuts data fetch latency at minute boundaries from **8.0 seconds** to **300 ms**.

### 3. Asynchronous Order Dispatching
*   **Current**: Sequential loop placing orders to accounts one by one.
*   **Upgrade**: Dispatch order placement requests concurrently using a thread pool (`concurrent.futures.ThreadPoolExecutor`) or Python `asyncio`.
*   **Impact**: Cuts order placement lag for 4 accounts from **1.6 seconds** to **250 ms** (parallel dispatch).

### 4. Indexing the Security Master Cache
*   **Current**: Searching 40MB CSV master files using pandas regex on every signal.
*   **Upgrade**: Load and index the F&O CSV cache into a memory-resident nested dictionary (e.g., `dict[symbol][expiry][strike][type]`) once at bot startup.
*   **Impact**: Reduces CPU search latency from **500 ms** to **< 1 ms**, completely eliminating GIL lockouts during signal clusters.

### 5. Staggered Poll Offsets
*   **Current**: Bots attempt to fetch data at the exact same second.
*   **Upgrade**: Introduce minor, staggered offsets (e.g., Bot 1 polls at 0s, Bot 2 at 0.5s, Bot 3 at 1.0s) to evenly distribute API traffic.
