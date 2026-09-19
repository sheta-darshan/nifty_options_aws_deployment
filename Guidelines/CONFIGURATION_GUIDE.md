# Configuration Guide: `instruments.json` & `accounts.json`

This guide explains how to customize and control your algorithmic trading bot using [instruments.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/instruments.json) and [accounts.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/accounts.json).

---

## 📊 1. `instruments.json`

This file controls the list of active trading symbols, their strategy parameters, and execution modes. The bot reloads this file dynamically every **5 minutes** without requiring a restart.

### Configuration Schema Reference

| Parameter Name | Type | Allowed Values | Description |
| :--- | :--- | :--- | :--- |
| **`security_id`** | `int` | e.g. `13` (Nifty) | **Required**: Unique security identifier for the underlying asset mapped in Dhan. Script fails to load instrument if missing. |
| **`enabled`** | `int` | `1` (on), `0` (off) | Toggle whether the thread for this instrument is active. |
| **`type`** | `string` | `"INDEX"`, `"STOCK"`, `"OPTION"` | Type of underlying or instrument. `"OPTION"` fetches from F&O segments. |
| **`execution_mode`** | `string` | `"OPTION"`, `"STOCK"` | **New**: `"OPTION"` places trades on CE/PE contract legs. `"STOCK"` trades the stock directly on equity exchange segments. |
| **`stock_qty_override`**| `int` | e.g. `5`, `50` | **New**: Override base quantity in `STOCK` mode (ignores lot size multiplier). |
| **`product_type`** | `string` | `"MARGIN"`, `"INTRADAY"`, `"CNC"` | **New**: Overrides product type for orders. Note: Stock bracket orders default to `"INTRADAY"`. |
| **`exchange_segment`** | `string` | `"IDX_I"`, `"NSE_EQ"` | Segment of the underlying asset (used for data fetching and equity entries). |
| **`option_segment`** | `string` | `"NSE_FNO"`, `"BSE_FNO"`| Exchange segment where the F&O derivatives reside. |
| **`lot_size`** | `int` | e.g. `65` (Nifty) | Lot unit multiplier. Used as base trade quantity if `stock_qty_override` is absent. |
| **`num_lots_buy`** | `int` | e.g. `1`, `2` | Multiplier for buy signals (e.g. `lot_size` * `num_lots_buy` shares/options). |
| **`num_lots_sell`** | `int` | e.g. `1`, `3` | Multiplier for sell signals (base lots). |
| **`enable_dynamic_conviction`** | `bool` | `true`, `false` | When enabled, dynamically scales position sizing based on macro trend conviction (e.g., 15m Supertrend alignment with 5m breakout). |
| **`num_lots_high_conviction`** | `int` | e.g. `7` | Scaled lot multiplier deployed when high-conviction macro alignment is active (`Conviction >= 1.5`). |
| **`daily_limit`** | `int` | e.g. `5` | Maximum entry signals allowed per day for this instrument. |
| **`max_active`** | `int` | e.g. `1` | Max simultaneous open positions permitted (per account). |
| **`fno_prefix`** | `string` | e.g. `"NIFTY"` | Option chain prefix search string. |
| **`strike_step`** | `float` | e.g. `50.0`, `100.0` | Step size between strikes (used to calculate ATM/OTM strikes). |
| **`strike_offset`** | `int` | e.g. `0` | Default strike offset fallback if specific offsets are not set. |
| **`strike_offset_buy`** | `int` | e.g. `0` (ATM), `1` (OTM+1) | Strikes offset for BUY/Long signals (falls back to `strike_offset`). |
| **`strike_offset_sell`**| `int` | e.g. `0` (ATM), `2` (OTM+2) | Strikes offset for SELL/Short signals (falls back to `strike_offset`). |
| **`option_strategy_mode`**| `string`| `"DIRECT"`, `"DEBIT_SPREAD"`, `"CREDIT_SPREAD"`, `"SHORT_STRADDLE"`, `"LONG_STRADDLE"`, `"SHORT_STRANGLE"`, `"LONG_STRANGLE"`, `"IRON_CONDOR"`, `"IRON_FLY"`, `"CALENDAR_SPREAD"` | Selects option leg strategy (ignored in `STOCK` execution mode). See details below. |
| **`strategy_leg_width`**| `int` | e.g. `1` | Width of option strategy legs in strike steps (for multi-leg options like spreads). |
| `float` | e.g. `0.35` | Percentage premium Stop Loss threshold (e.g. 0.35 = 35% SL) for Strategy 20 Option Selling. |
| **`opt_tp_points`**       | `float` | e.g. `2000.0` | Portfolio target cap (₹) for Strategy 20 Option Selling. |
| **`expiry_index`** | `int` | `0` (current), `1` (next) | **Important**: The expiry week contract selection index. `0` represents the nearest weekly expiry. |
| **`num_strikes`** | `int` | e.g. `1`, `2` | Number of option strike contract legs to trade simultaneously. |
| **`sl_mult_buy` / `_sell`**| `float`| e.g. `1.5` | Stop loss ATR multiplier (Distance = ATR * Multiplier). |
| **`tp_mult_buy` / `_sell`**| `float`| e.g. `2.0` | Take profit ATR multiplier (Distance = ATR * Multiplier). |
| **`trailing_mult_buy`/`_sell`**| `float`| e.g. `0.5` | Trailing jump ATR multiplier (0 to disable trailing). |
| **`profit_target_buy`/`_sell`**| `float`| e.g. `1000.0` | Fixed INR profit target (bypasses dynamic ATR profit targets if > 0 in both ATR and SWING_CONTRACT modes). |
| **`profit_target_per_lot`**| `float`| e.g. `1250.0` | Fixed profit target per lot in INR (fallback for buy order targets). |
| **`points_sl_buy` / `_sell`**| `float`| e.g. `15.0` | Fixed premium/stock points for Stop Loss in `"POINTS"` exit mode. |
| **`points_target_buy` / `_sell`**| `float`| e.g. `30.0` | Fixed premium/stock points for Take Profit target in `"POINTS"` exit mode. |
| **`points_target_high_conviction`**| `float`| e.g. `45.0` | Dynamic extended profit target points applied when macro trend conviction alignment is active (`Conviction >= 1.5`). Bypasses base target. |
| **`points_trail_buy` / `_sell`**| `float`| e.g. `5.0` | Fixed premium/stock points for Trailing Jump stop trigger in `"POINTS"` exit mode (set to `0` to disable). |
| **`points_be_buy` / `_sell`**   | `float`| e.g. `25.0` | Breakeven trigger for `"POINTS"` exit mode. **Dual behavior:** If `<= 1.0`, acts as a ratio multiplier (`Initial_SL_Points * multiplier`). If `> 1.0`, acts as an **absolute points threshold in favor** (e.g., `25.0` on NIFTY, `45.0` on BANKNIFTY, `40.0` on SENSEX). Once premium moves favorably by this distance, Stop Loss is shifted to entry price. Set to `0` to disable. |
| **`atr_be_buy` / `_sell`**      | `float`| e.g. `0.5` | Breakeven trigger multiplier for ATR-based exit modes. Moves SL to entry price once the trade moves in favor by `Initial_SL_Points * multiplier`. Set to `0` to disable. |
| **`exit_mode`**            | `string`| `"ATR"`, `"SWING"`, `"SWING_CONTRACT"`, `"POINTS"`| `"ATR"` for legacy option premium orders. `"SWING"` for structural Spot swing stops and targets with local monitor. `"SWING_CONTRACT"` for structural swing stops and targets calculated and monitored directly on the traded option contract/stock premium itself. `"POINTS"` for fixed point-based stop loss, target, and trailing stops calculated and monitored directly on the traded contract's premium. |
| **`swing_window_size`**    | `int`   | e.g. `10`   | Lookback window size in 1-minute candles to compute swing extremes (Spot or Contract wicks). |
| **`sl_buffer_atr_mult`**   | `float` | e.g. `0.2`   | ATR multiplier to add safety buffer to the swing extremes. |
| **`local_exit_monitoring`**| `bool`  | `true`, `false` | Determines whether exits are monitored locally in Python (`true`) or placed as exchange-side broker Bracket/Super orders (`false`). Automatically defaults to `true` for `SWING`, `SWING_CONTRACT`, and `POINTS` exit modes. |
| **`broker_safety_sl`**     | `bool`  | `true`, `false` | **Hybrid Crash-Proof Protection**: When `local_exit_monitoring` is `true`, setting this to `true` places a native Dhan Super Order at entry with hard Stop Loss (`opt_sl`) resting on exchange. When local breakeven triggers, bot dynamically calls `modify_super_order_sl` (`PUT /super/orders/{orderId}`) to move the exchange-resting `STOP_LOSS_LEG` to entry price. Guarantees 100% EC2 crash immunity. |
| **`gatekeeper_enabled`**    | `int`   | `1` (on), `0` (off) | **New**: Toggle the Gate Keeper Option Entry Validation System to filter breakouts. |
| **`gatekeeper_single_strike`** | `int`  | `1` (on), `0` (off) | **New**: If enabled, validates only the target strike, skipping multi-strike consensus (recommended for stock options). |
| **`gatekeeper_time_filter_minutes`**| `int` | e.g. `20` | **New**: Skip entries generated within this many minutes of market open. |
| **`gatekeeper_window_minutes`**| `int`  | e.g. `5`  | **New**: Lookback period in minutes for option price and OI change velocity calculations. |
| **`gatekeeper_oi_min_change_pct`**| `float` | e.g. `1.0` | **New**: Minimum percentage change in Open Interest required for buildup confirmation. |
| **`gatekeeper_volume_sma_period`**| `int` | e.g. `15` | **New**: Lookback period in minutes to compute the rolling volume simple moving average. |
| **`gatekeeper_volume_multiplier`**| `float` | e.g. `1.2` | **New**: Multiplier for volume SMA confirmation (current volume must exceed multiplier * SMA). |
| **`TM_MAX_STRETCH`**       | `float` | e.g. `0.002` | **New**: Maximum ratio distance allowed between the spot price and the short-term EMA at entry (e.g. `0.002` means 0.2%). Blocks chasing overextended breakouts. |
| **`block_expiry_day_trades`**| `int`   | `1` (on), `0` (off) | **New**: Expiry day filter. If set to `1`, blocks signal executions on the weekly expiry day **only for Option BUYING** trades. Option SELLING (writing) trades are allowed to run normally to capture expiry time decay. |
| **`optimization_grid`**    | `dict`  | Custom nested object | **New**: Optional instrument-specific custom search grids for parameter optimization in `optimize.py` (see details below). |
| **`allowed_regimes_trend`** | `array` | e.g. `["TREND"]` | **New**: Centralized ADX trend filter. Allowed states: `"TREND"` (ADX > 25.0), `"RANGE"` (ADX < 20.0), `"NEUTRAL"` (20.0 <= ADX <= 25.0). If omitted, no filter is applied. |
| **`allowed_regimes_vol`**  | `array` | e.g. `["LOW_VIX"]` | **New**: Centralized ATR volatility filter. Allowed states: `"LOW_VIX"` (ATR% <= Median ATR%), `"HIGH_VIX"` (ATR% > Median ATR%). If omitted, no filter is applied. |
| **`allowed_actions`**      | `array` | `["BUY"]` or `["SELL"]` | **New**: Trade direction lock at the instrument level. Restricts the bot from executing counter-trend signals (e.g., if set to `["BUY"]`, the bot ignores any `'sell'` signals). If omitted, no direction lock is applied. |
| **`trigger_price`**        | `float` | e.g. `489.55` | **New**: Exact price trigger threshold for `Strategy_24` (Opening Pre-Breakout / Pre-Breakdown Momentum). For BUY (`direction: "BUY"`), fires when spot crosses above `Day T High + 0.05`. For SELL (`direction: "SELL"`), fires when spot drops below `Day T Low - 0.05`. |
| **`direction`**            | `string`| `"BUY"`, `"SELL"` | **New**: Directional mode for rotated cash stock setups in `Strategy_24`. Aligns `allowed_actions: ["BUY"]` or `["SELL"]`. |
| **`rotated_prebreakout`**  | `bool`  | `true`, `false` | **New**: Set to `true` by the automated EOD Pre-Breakout/Breakdown Stock Selection scanner (`select_prebreakout.py --rotate`) when a stock is rotated into the active daily rotation pool. |
| **`rotated_joint`**       | `bool`  | `true`, `false` | **New**: Set to `true` by the automated EOD Dual-Head Quantitative ML Momentum scanner (`select_joint.py --rotate`) when a stock is rotated into the active daily rotation pool. Co-exists symbiotically with `rotated_prebreakout`. |
| **`stock_qty_override`**   | `int`   | e.g. `1125` | **New**: Exact share quantity allocated for cash equity execution (`execution_mode: "STOCK"`). Automatically computed via SEBI 5x MIS leverage formula: $\max(1, \text{int}((\text{capital} \times \text{leverage}) / \text{trigger\_price}))$. |

### 🎛️ Custom Optimization Grids (`optimization_grid`)

You can define optional custom search grids for parameter optimization directly within each instrument's block in `instruments.json`. The keys and values in the grid change based on the instrument's `exit_mode`:

#### A. For `exit_mode`: "POINTS"
The grid specifies lists of point values to sweep for stop loss, target, trailing jump, and breakeven:
```json
"optimization_grid": {
    "points_sl_buy": [15, 20],
    "points_target_buy": [30, 45],
    "points_trail_buy": [0, 5],
    "points_be_buy": [0],
    "points_sl_sell": [15, 20],
    "points_target_sell": [30, 45],
    "points_trail_sell": [0, 5],
    "points_be_sell": [0]
}
```

#### B. For `exit_mode`: "ATR"
The grid specifies lists of ATR multipliers to sweep for stop loss, target, trailing jump, and breakeven:
```json
"optimization_grid": {
    "sl_mult_buy": [1.0, 1.5],
    "tp_mult_buy": [2.0, 3.0],
    "trailing_mult_buy": [0.0, 0.3],
    "atr_be_buy": [0.0],
    "sl_mult_sell": [1.0, 1.5],
    "tp_mult_sell": [2.0, 3.0],
    "trailing_mult_sell": [0.0, 0.3],
    "atr_be_sell": [0.0]
}
```
If `"optimization_grid"` is defined, the optimizer `optimize.py` will generate the Cartesian product of the lists to execute a fine-grained risk parameter sweep, bypassing the default ranges.

### 🎛️ Detailed Option Strategy Modes

The `option_strategy_mode` parameter defines the exact multi-leg or single-leg options structure that is executed when the bot generates a signal. SATP has **10** options strategy modes defined:

1. **`DIRECT`**: Trades a single directional call or put option.
   - **Buy/Long Signal**: Buys ATM Call (if `LEG_MODE` is `"BUY"` or `"BOTH"`) or sells ATM Put (if `LEG_MODE` is `"SELL"` or `"BOTH"`).
   - **Sell/Short Signal**: Buys ATM Put (if `LEG_MODE` is `"BUY"` or `"BOTH"`) or sells ATM Call (if `LEG_MODE` is `"SELL"` or `"BOTH"`).
   - *Offsets*: Uses `strike_offset_buy` and `strike_offset_sell` to shift the selected strike OTM/ITM.

2. **`DEBIT_SPREAD`**: Defined-risk directional spreads (Bull Call or Bear Put).
   - **Buy/Long Signal**: Buys ATM Call, Sells OTM Call (ATM + `strategy_leg_width` strikes).
   - **Sell/Short Signal**: Buys ATM Put, Sells OTM Put (ATM - `strategy_leg_width` strikes).

3. **`CREDIT_SPREAD`**: Defined-risk directional spreads (Bull Put or Bear Call).
   - **Buy/Long Signal**: Sells ATM Put, Buys OTM Put (ATM - `strategy_leg_width` strikes) as a hedge.
   - **Sell/Short Signal**: Sells ATM Call, Buys OTM Call (ATM + `strategy_leg_width` strikes) as a hedge.

4. **`SHORT_STRADDLE`**: Delta-neutral credit strategy (theta decay).
   - Sells ATM Call and PE ATM on any signal (triggers on both BUY or SELL signals).

5. **`LONG_STRADDLE`**: Delta-neutral debit strategy (high volatility).
   - Buys ATM Call and PE ATM on any signal.

6. **`SHORT_STRANGLE`**: Delta-neutral credit strategy (theta decay with a wider range).
   - Sells OTM Call (ATM + `strategy_leg_width` strikes) and PE OTM (ATM - `strategy_leg_width` strikes) on any signal.

7. **`LONG_STRANGLE`**: Delta-neutral debit strategy (high volatility breakout).
   - Buys OTM Call (ATM + `strategy_leg_width` strikes) and PE OTM (ATM - `strategy_leg_width` strikes) on any signal.

8. **`IRON_CONDOR`**: Defined-risk delta-neutral credit strategy.
   - Sells OTM Call and PE OTM (ATM + `strategy_leg_width`), and buys further OTM Call and PE (ATM + `strategy_leg_width` * 2) as hedges. Triggers on any signal.

9. **`IRON_FLY`**: Defined-risk delta-neutral credit strategy with a peaked profit zone.
   - Sells ATM Call and PE ATM, and buys OTM Call and PE (ATM + `strategy_leg_width` / ATM - `strategy_leg_width`) as hedges. Triggers on any signal.

10. **`CALENDAR_SPREAD`**: Multi-contract ratio calendar spread strategy.
    - Trades 3 long monthly contracts and 1 short weekly contract (Leg 1 & Leg 2) to capture theta decay across weekly vs. monthly option contracts. Supports dual stance execution (`trade_both_sides: 1`).

---

## 🔑 2. `accounts.json`

This file manages your broker credentials and allows you to enforce risk rules, action filters, and custom trade sizes for individual accounts. The bot reloads this file automatically if modified.

### Configuration Schema Reference

| Parameter Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`name`** | `string` | Yes | Friendly identifier used in console logs and Telegram alerts. |
| **`client_id`** | `string` | Yes | Dhan client ID. |
| **`access_token`** | `string` | Yes | Dhan API token. |
| **`enabled`** | `bool` | Yes | Enable or disable trading for this specific account. |
| **`max_active`** | `int` | No | Global max simultaneous positions permitted for this account (defaults to instrument configuration). |
| **`daily_limit`** | `int` | No | Global max daily entry trades permitted for this account (defaults to instrument configuration). |
| **`global_multiplier`**| `float` | No | Scales trade quantities (e.g. `2.0` doubles the base quantity). |
| **`allowed_instruments`**| `array` | No | List of symbols this account is allowed to trade (e.g. `["NIFTY"]`). If omitted, all enabled symbols are allowed. |
| **`allowed_actions`** | `array` | No | **Important**: Restricts actions (e.g. `["BUY"]` allows buying calls or going long stocks; `["SELL"]` allows selling calls/puts or shorting). |
| **`allowed_option_types`**| `array`| No | **New**: Restricts option contract types (e.g. `["CE"]` allows Call options only; `["PE"]` allows Put options only). If omitted, both are allowed. |
| **`allowed_strategies`**| `array` | No | **New**: List of strategies allowed to trade on this account (e.g. `["Strategy_3", "Strategy_10"]`). If omitted, all enabled strategies are allowed. |
| **`source_ip`** | `string` | No | Static IP address for binding connections (required if IP whitelist is set on Dhan). |
| **`proxy_url`** | `string` | No | Proxy string (e.g. `http://user:pass@ip:port`) to route API traffic. |
| **`is_master`** | `bool` | No | Legacy template parameter to designate master/primary account (not used programmatically). |
| **`instrument_overrides`**| `dict` | No | Custom overrides for specific instruments (see below). |

### Custom Instrument Overrides

You can override standard instrument rules for specific accounts using the `instrument_overrides` key.
*Example Configuration:*
```json
{
  "name": "Hedge_Account",
  "client_id": "123456789",
  "enabled": true,
  "instrument_overrides": {
    "NIFTY": {
      "max_active": 1,
      "daily_limit": 2,
      "num_lots_buy": 1,
      "num_lots_sell": 1,
      "product_type": "INTRADAY"
    }
  }
}
```

---

## ⚙️ 3. Environment Variables (`.env`)

The `.env` file in the root directory manages global execution configurations and credentials.

| Variable Name | Required | Default Value | Description |
| :--- | :--- | :--- | :--- |
| **`DHAN_API_TOKEN`** | Yes | - | Access token for the primary Dhan API account. |
| **`DHAN_CLIENT_ID`** | Yes | - | Client ID for the primary Dhan API account. |
| **`LEG_MODE`** | No | `"BOTH"` | Trading action filter. `"BUY"` (only take long trades), `"SELL"` (only take short trades), or `"BOTH"` (take both). |
| **`USE_DYNAMIC_EXITS`** | No | `"False"` | **New**: Set to `"True"` to enable strategy-defined dynamic exits. Triggering `Exit_Long` or `Exit_Short` signals will cancel pending SL orders and close positions via market orders immediately. |
| **`ALERT_WEBHOOK_URL`**| No | - | Telegram Bot Webhook URL used by AlertManager to send trade execution and status alerts. |
| **`DHAN_SOURCE_IP`** | No | - | Global source IP (AWS private IP) for whitelisted Dhan API network calls. |
| **`DHAN_PROXY_URL`** | No | - | Global proxy URL routing all Dhan API connection traffic. |
| **`PRODUCT_TYPE`** | No | `"MARGIN"` | Global default order product type fallback (`"MARGIN"`, `"INTRADAY"`, or `"CNC"`). |

---

## 💡 4. Common Use Cases & How to Configure Them

### Use Case A: Trading Stock Equity Directly
To trade `POWERINDIA` stock directly on the equity exchange instead of buying option contracts:
1. Open **`instruments.json`** and look up `"POWERINDIA"`.
2. Configure `"execution_mode": "STOCK"`.
3. Set `"stock_qty_override": 5` if you want to trade exactly 5 shares. If omitted, the bot trades F&O lots (e.g., `lot_size` 50 * `num_lots` 1 = 50 shares).
4. Save the file. The next trading signal will execute a bracket order on `NSE_EQ` with delta=1.0.

### Use Case B: Restricting an Account to Option Writing / Shorting Only
If you have a high-margin account and want it to only sell/write options (benefiting from decay) while using other accounts to buy options:
1. Open **`accounts.json`**.
2. For the high-margin account, configure `"allowed_actions": ["SELL"]`.
3. For the lower-margin accounts, configure `"allowed_actions": ["BUY"]`.
4. Save the file.
   - On a `BUY` signal: The selling account will sell Puts; buying accounts will buy Calls.
   - On a `SELL` signal: The selling account will sell Calls; buying accounts will buy Puts.

### Use Case C: Restricting a Risky Asset to a Single Account
If you want to trade a highly volatile stock (e.g. `SUZLON`) but only on your primary account:
1. Open **`accounts.json`**.
2. For your primary account, add `"SUZLON"` to `allowed_instruments` (e.g. `["NIFTY", "SUZLON"]`).
3. Ensure other accounts do not include `"SUZLON"` in their `allowed_instruments` list (or exclude it).
4. Save the file.

### Use Case E: Trading a Specific Option Contract Directly
If you want to trade a specific Call (CE) or Put (PE) option contract directly (analyzing its chart and buying/selling it directly):
1. Open **`instruments.json`** and add a new custom name (e.g. `"NIFTY_22000_CE"`).
2. Configure `"type": "OPTION"`.
3. Configure `"execution_mode": "STOCK"`.
4. Configure `"exchange_segment": "NSE_FNO"`.
5. Set `"security_id": 35078` (the specific option contract's Dhan security ID).
6. Set `"lot_size": 75` (the option contract's lot size unit).
7. Save. When a BUY signal triggers, it will place a direct buy order on this contract ID; on SELL, it will place a sell order.
8. **Configuring Short Exits (Optional)**:
   * `"short_option_target_type"`: Sets the target cover method. Options:
     * `"MAX_PROFIT"` (default for `OPTION` mode): Covers (buys back) the short option at a fixed low premium (decay target).
     * `"ATR"` (default for `STOCK` mode): Covers based on dynamic ATR volatility and the `tp_mult_sell` setting.
   * `"short_option_decay_value"`: The cover price target when using `"MAX_PROFIT"` (defaults to `0.05` Rs).


### Use Case F: Setting Up the Gate Keeper Option Entry Validation
To prevent the bot from entering trades on false breakouts where option volume or OI is insufficient:
1. Set `"gatekeeper_enabled": 1` on the target instrument block inside `instruments.json`.
2. **Optional (for Stock F&O/Illiquid Options)**: Set `"gatekeeper_single_strike": 1` to only validate the targeted strike contract, bypassing the default 3-strike basket consensus.
3. Configure `"gatekeeper_time_filter_minutes": 20` to prevent entries in the first 20 minutes of the market (9:15 AM - 9:35 AM) to filter morning noise.
4. Set your threshold values: e.g., `"gatekeeper_oi_min_change_pct": 1.0`, `"gatekeeper_volume_multiplier": 1.2`.
5. The system will fetch 1 hour of option candles in real-time and validate if a momentum push is verified before executing the order. If the verification fails, it logs a warning and skips the trade entry.

### Use Case G: Restricting an Account to CE-only or PE-only Trading
If you want a specific account to only buy/sell Call Options (CE) and completely ignore Put Options (PE) (or vice versa):
1. Open **`accounts.json`**.
2. For the Call-only account, configure `"allowed_option_types": ["CE"]`.
3. For the Put-only account, configure `"allowed_option_types": ["PE"]`.
4. Save the file. The live bot will reload this configuration dynamically, filtering out the opposite leg orders for these accounts during executions.

### Use Case H: Preventing Chasing Reversals (Stretch Filter)
To avoid entering breakouts that have already run up too far and are highly vulnerable to immediate pullbacks/reversals:
1. Open **`instruments.json`** and navigate to your target instrument (e.g. `"NIFTY"`).
2. Set `"TM_MAX_STRETCH": 0.002`. This restricts entry to breakouts where the spot price is within 0.2% of its short-term 8 EMA base.
3. Save the file. The live bot will automatically read this stretch parameter and block any breakout entries that are overextended.

### Use Case I: Routing Specific Strategies to Specific Accounts
If you manage multiple accounts and want to route specific strategy signals to specific accounts only (e.g., execute Strategy 3 trades on Account A, and Strategy 10 trades on Account B):
1. Open **`accounts.json`**.
2. For Account A, configure `"allowed_strategies": ["Strategy_3"]`.
3. For Account B, configure `"allowed_strategies": ["Strategy_10"]`.
4. Save the file. The live bot dynamically reloads this, routing only authorized strategy orders to their respective broker accounts.

### Use Case J: Blocking Option BUYING Trades on Weekly Expiry Day
To protect your option buying capital from rapid time decay (Theta melt) and whipsaws on expiry days, while still allowing option selling (writing) trades to capture decay profits:
1. Open **`instruments.json`** and navigate to your target instrument.
2. Configure `"block_expiry_day_trades": 1`.
3. Save the file. The live bot will dynamically fetch the nearest expiry date from Dhan. If today is the expiry day, it will block any signals that result in buying options (BUY mode), but will allow option selling (SELL mode) signals to execute normally.

### Use Case K: Machine Learning Quant Model Configuration (`Strategy_19`)
To configure the Institutional XGBoost Machine Learning Strategy:
1. Open **`instruments.json`** under `"NIFTY"`.
2. Add or modify the `"Strategy_19"` strategy override block:
   ```json
   "Strategy_19": {
       "timeframe": "5min",
       "min_ml_prob": 0.42,
       "exit_mode": "POINTS",
       "points_sl_buy": 25.0,
       "points_target_buy": 75.0,
       "points_trail_buy": 0.0,
       "points_be_buy": 0.0,
       "points_sl_sell": 15.0,
       "points_target_sell": 45.0,
       "points_trail_sell": 0.0,
       "points_be_sell": 0.0,
       "num_lots_buy": 1,
       "num_lots_sell": 1
   }
   ```
3. **`min_ml_prob`**: Sets the minimum model confidence threshold (default: `0.42` or 42%). Higher values (e.g. `0.48`) increase trade precision by filtering out sideways chop.

### Use Case L: Modular EMA 18 / SMMA 18 OHLC4 Strategy Configuration (`Strategy_22`)
To configure the Modular EMA 18 / SMMA 18 OHLC4 Strategy:
1. Open **`instruments.json`** under `"NIFTY"`.
2. Add or modify the `"Strategy_22"` strategy override block:
   ```json
   "Strategy_22": {
       "ENTRY_MODE": "PULLBACK_ZONE",
       "EXIT_MODE": "OPPOSITE_CROSS",
       "PRICE_SOURCE": "OHLC4",
       "EMA_FAST": 18,
       "SMMA_BASE": 18,
       "exit_mode": "POINTS",
       "carry_forward": false,
       "points_sl_buy": 20.0,
       "points_target_buy": 40.0,
       "points_trail_buy": 0.0,
       "points_be_buy": 0.0,
       "points_sl_sell": 36.0,
       "points_target_sell": 84.0,
       "points_trail_sell": 0.0,
       "points_be_sell": 0.0,
       "num_lots_buy": 1,
       "num_lots_sell": 1,
       "CONFIRMATION_CANDLES": 1,
       "MIN_SPREAD_ATR": 0.15,
       "USE_ATR_EXPANSION": false
   }
   ```
3. **`ENTRY_MODE` Options:** `"PULLBACK_ZONE"` (Recommended), `"CROSSOVER"`, `"CROSS_PERSISTENCE"`, `"SPREAD_EXPANSION"`, `"SLOPE_ALIGNED"`, `"SPREAD_ATR"`, `"PULLBACK_TOUCH"`.
4. **`EXIT_MODE` Options:** `"OPPOSITE_CROSS"`, `"FAST_LINE_CROSS"`, `"SMMA_CROSS"`, `"SPREAD_REVERSAL"`.


---

## 🛠️ 5. Dynamic Parameter Resolution (Strike Step & Lot Size)

To prevent issues with periodic exchange-driven lot size adjustments and strike step changes (for example, stock option revisions or index contract step changes), SATP uses an automated dynamic resolution hierarchy:

1. **Exchange Segment Filtering (Live Trading)**: 
   - When generating an option order, the live bot queries the active F&O contracts database directly.
   - It computes the **Strike Step** dynamically as the most frequent difference (`mode`) between adjacent strike prices.
   - It extracts the **Lot Size** dynamically from the active contract master rows under the `'LOT_SIZE'` column and updates the configuration in-memory.
   - This makes the live bot fully self-healing and immune to outdated configuration files.

2. **Historical Registry Mapping (Backtesting & Optimization)**:
   - For backtesting, since spot and options contracts span years of historical data, we compile daily bhavcopies into two registries: [strike_step_history.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/strike_step_history.json) and [lot_size_history.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/lot_size_history.json).
   - The engine automatically resolves the exact step and lot sizes matching the trade entry date and the contract's expiry date.

3. **Static Config Fallbacks**:
   - The values `"strike_step"` and `"lot_size"` configured inside `instruments.json` are now treated as **fallbacks**. They are only used if the dynamic registry query (in backtests) or active F&O master check (in live trading) fails to return a valid value.

---

## 🔒 6. Key Security Rules

1. **Token Refreshing**: Access tokens expire daily. Ensure your EOD cron job runs `renew_tokens.py` at **08:00 AM** to pull fresh tokens into `accounts.json`.
2. **Network Whitelisting**: If a static IP binding is configured on Dhan, enter the exact IP address in the `source_ip` parameter for that account to prevent `"IP Not Whitelisted (905)"` errors.

## ⚙️ 7. Strategy-Specific Configuration Overrides (Centralized)

To prevent risk parameter conflicts when running multiple strategies (like Strategy 12, 13, and 14) on the same underlying instrument, you can define strategy-specific parameter overrides directly inside each instrument's block in `instruments.json` using the optional `"strategy_overrides"` key.

### Configuration Schema
Create a nested dictionary where the keys are the target strategy names (e.g. `"Strategy_13"`, `"Strategy_14"`) and the values are the parameter overrides to apply when that strategy is active.

```json
"NIFTY": {
    "lot_size": 25,
    "points_sl_buy": 24,
    "points_target_buy": 75,
    "daily_limit": 1,
    
    "strategy_overrides": {
        "Strategy_14": {
            "points_sl_buy": 36,
            "points_target_buy": 72
        },
        "Strategy_13": {
            "points_sl_buy": 35,
            "points_target_buy": 30
        }
    }
}
```

### Overridable Parameters
Any configuration parameter supported inside `instruments.json` can be overridden. The most common overrides include:
- **Exits**: `points_sl_buy`, `points_target_buy`, `points_trail_buy`, `exit_mode`
- **Limits**: `lot_size`, `num_lots_buy`, `daily_limit`, `max_active`
- **Toggles**: `gatekeeper_enabled`, `block_expiry_day_trades`
- **Direction Locks**: `allowed_actions` (e.g. restrict to `["BUY"]` for a specific strategy only)

### Resolution Logic (Live & Backtest)
- **Live Trading**: When the live bot (`trading_bot/config.py`) loads the settings, it checks which strategy toggle is active, merges the override block, and automatically refreshes all thread parameters. In addition, the bot's dynamic reload listener (`reload_instruments`) automatically re-applies these overrides whenever you modify the file during market hours.
- **Backtesting**: The backtester (`backtest_engine.py`) retrieves the overrides dictionary matching `self.strategy.name` and applies them during simulation startup, ensuring complete parity between backtest results and live execution.
- **Fallback**: If the active strategy is not defined inside the `"strategy_overrides"` dictionary, the system automatically falls back to the base parameters defined at the root of the instrument block (maintaining full backward-compatibility).

---

## 🕒 8. 30-Minute Option Chain Stock Selection Scanner

The bot includes an automated scanner script, [run_option_chain_scanner.py](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/run_option_chain_scanner.py), designed to run at **09:45 AM** (after the first 30 minutes of the market session). It dynamically scans the option chain of all candidate stocks to select the top momentum stocks for trading today.

### How the Scanner Works:
1. **Candidate Pool:** Loads all instrument configurations defined in `instruments.json` where `"type": "STOCK"`.
2. **Option Chain Fetching:** Queries the Dhan API to retrieve the nearest expiry date and pulls the complete real-time Option Chain.
3. **ATM Score Calculation:** Identifies the ATM strike based on the underlying spot price and calculates cumulative statistics across a range of **ATM $\pm$ 3 strikes**:
   - **Total Near-ATM Volume:** Sums the daily cumulative trading volume.
   - **OI Change Percentage:** Sums the current Open Interest vs. the previous day's Open Interest:
     $$\text{OI Change (\%)} = \frac{\text{Total Current OI} - \text{Total Previous OI}}{\text{Total Previous OI}} \times 100$$
4. **Ranking & Selection:** Ranks the candidates by their absolute OI Change % and selects the top $N$ stocks (default: 3).
5. **Dynamic Configuration Update:** Updates [instruments.json](file:///c:/Users/sheta/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/instruments.json):
   - Sets `"enabled": 1` for the selected top $N$ stocks.
   - Sets `"enabled": 0` for all other stocks.
   - **Direction Lock:** Automatically computes and writes `"allowed_actions": ["BUY"]` for stocks with a daily bullish gap/momentum, or `"allowed_actions": ["SELL"]` for stocks with a daily bearish gap/momentum. This locks the trading side for each selected stock to follow its daily trend.
   - Leaves index configs (like `NIFTY`, `BANKNIFTY`, `SENSEX`) unchanged.
6. **Auto-spawning:** The running background bot (`live_trade_fixed.py`) automatically reloads the updated file within 5 minutes, detects the active stock instruments, spawns the required thread workers, and enforces the `allowed_actions` direction lock at the start of signal execution.

### Rate-Limit & Dual Account Safety:
To prevent rate-limit conflicts with your background trading bot, you can optionally configure a secondary Dhan account in `.env`:
* **Dual Account setup:** If `DHAN_API_TOKEN_2` and `DHAN_CLIENT_ID_2` are present in `.env`, the scanner uses them to run at full speed (**5 requests/second**).
* **Shared Account fallback:** If secondary credentials are not configured, it falls back to the primary credentials and automatically throttles its speed to **2 requests/second** to leave enough rate-limit headroom for your active trading bot.

* **Test/Dry-run Mode:** Calculate rankings, print results, and send Telegram notifications without modifying `instruments.json`:
  ```bash
  ..\venv\Scripts\python.exe run_option_chain_scanner.py --dry-run --top-n 3
  ```
* **Production Mode:** Rank candidates, update configurations, and alert on Telegram:
  ```bash
  ..\venv\Scripts\python.exe run_option_chain_scanner.py --top-n 3
  ```

### Advanced Scanner Configuration Flags:
* **`--top-n`** (Default: `3`): Number of stocks to enable.
* **`--min-oi-change`** (Default: `0.5`%): Minimum % OI change required to prevent retail block-deal fakeouts.
* **`--max-spread-val`** (Default: `0.50` Rs) / **`--max-spread-pct`** (Default: `3.0` %): Bid-Ask spread limits on the ATM strike to prevent entry slippage.
* **`--min-price-change`** (Default: `1.0`%) / **`--max-price-change`** (Default: `4.5`%): The daily price change "Sweet Spot" from yesterday's close. Stocks below the minimum have no momentum; stocks above the maximum are already exhausted.
  * *Note: The scanner uses a single OHLC API request to pre-filter candidates. If a stock is outside this range, the scanner automatically skips fetching its Option Chain. This optimizes execution speed from 1.5 minutes down to less than 30 seconds!*

Schedule the script to run every trading day at exactly **09:45 AM** via Windows Task Scheduler or cron.

---

## 📈 9. Institutional Historical Data Ingestion Engine (`fetch_historical_equity.py`)

The platform includes [`fetch_historical_equity.py`](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/fetch_historical_equity.py) to ingest and maintain 1-minute historical spot candles across the entire universe of **2,289 NSE listed stocks** defined in [`EQUITY_L.csv`](file:///g:/100%20Days%20of%20code/boxdata/Live%20trading/nifty_options_aws_deployment/EQUITY_L.csv).

### Key Ingestion Mechanics:
1. **Dhan Scrip Master Auto-Resolution:** Downloads and caches Dhan's security master to resolve the exact Dhan `security_id` for every NSE equity ticker.
2. **Zero-Waste Incremental Sync:**
   - Evaluates `backtest_data/{symbol.lower()}_spot.csv`.
   - If the file is already current with today's close, it skips in **0.0 seconds with 0 API calls**.
   - If data is missing (e.g., today's trading hours), it fetches **only the missing delta**, drops duplicate timestamps, sorts chronologically, and appends to the file.
3. **Full 5-Year Initial Download:** For newly listed stocks, downloads 5 years of 1-minute OHLCV candles in 30-day API chunks.
4. **Rate-Limit & Interruption Resilience:** Includes ~0.12s request delays, exponential backoff on HTTP `429 Too Many Requests`, and graceful checkpointing.

### Common Commands:
* **Daily Incremental Sync (Schedule daily at 03:45 PM):**
  ```bash
  ..\venv\Scripts\python.exe fetch_historical_equity.py
  ```
* **Full 5-Year Historical Download (All Stocks):**
  ```bash
  ..\venv\Scripts\python.exe fetch_historical_equity.py --years 5
  ```
* **Batch Ingestion (e.g. 100 stocks per run):**
  ```bash
  ..\venv\Scripts\python.exe fetch_historical_equity.py --limit 100
  ```
* **Sync Specific Symbols Only:**
  ```bash
  ..\venv\Scripts\python.exe fetch_historical_equity.py --symbols RELIANCE TCS INFOSYS HDFCBANK ABB
  ```
* **Dry-Run (Inspect missing date windows without calling API):**
  ```bash
  ..\venv\Scripts\python.exe fetch_historical_equity.py --dry-run
  ```

---

## 📊 10. Automated Daily Performance & Risk Digest (`send_daily_digest.py`)

At the end of every trading session, SATP generates and dispatches an institutional Daily PnL & Risk Digest to configured Telegram and Slack alert webhooks.

### Key Capabilities:
1. **Automated Scheduler (15:35 IST):** `ThreadedBotManager` runs an internal scheduler that triggers `generate_daily_digest()` and `send_daily_digest()` at exactly 15:35 IST after market close, as well as automatically during bot shutdown (`stop_all()`).
2. **Account Capital & Margin Breakdown:** Fetches live cash balance, utilized margin, collateral valuation, and net available trading margin from Dhan APIs.
3. **Execution & Win-Rate Analytics:** Aggregates trades executed across all instruments and strategies for the day, detailing win rate, gross/net PnL, profit factor, and average trade duration.
4. **Active Overnight Positions:** Outlines all open carry-forward legs with current unrealized MTM, contract expiries, and stop loss levels.

### Standalone CLI Execution:
```bash
# Preview digest in console without triggering webhooks
..\venv\Scripts\python.exe send_daily_digest.py --preview

# Dispatch live daily digest to Telegram & Slack
..\venv\Scripts\python.exe send_daily_digest.py

# Generate report for a specific historical trading date
..\venv\Scripts\python.exe send_daily_digest.py --date 2026-09-15 --preview
```

---

## 🛡️ 11. Institutional Order Resilience & Execution Architecture

### A. Graceful Margin Downsizing Fallback
When executing multi-lot or dynamic conviction positions (e.g. 2+ lots of index options), Dhan RMS may reject orders due to sudden intraday margin requirement spikes (`RS-9005` or `"Margin Insufficient"`).

To eliminate missed setups:
1. `InstrumentBot` routes orders through `place_order_with_margin_fallback` in `DhanAPIWrapper`.
2. If the initial order (e.g., 2 lots) is rejected due to margin shortfall, the bot logs an alert and automatically retries with base lots (e.g., 1 lot).
3. If base lots still exceed available margin, it attempts a final order of **1 lot minimum**.
4. Alerts are dispatched to Telegram informing the trader of the downsized execution.

### B. Hybrid Crash-Proof Breakeven Architecture (`broker_safety_sl`)
Native exchange bracket orders often lack dynamic features like breakeven and trailing adjustments. Local monitoring provides flexibility but risks naked exposure if the bot server crashes.

The **Hybrid Crash-Proof Mode** bridges this gap:
```text
Order Submission -> Real Dhan Super Order with Hard SL on Exchange
                        │
                        ▼
Local 1s Monitoring Loop tracks premium decay / price movement
                        │
                        ▼
Breakeven Trigger Hit (e.g. +25.0 pts decay on NIFTY)
                        │
                        ▼
DhanAPIWrapper.modify_super_order_sl(order_id, entry_price)
                        │
                        ▼
Dhan Exchange Matching Engine moves resting STOP_LOSS_LEG to Entry Price!
(EC2 can crash, disconnect, or reboot — trade is 100% risk-free on exchange)
```

Configuration in `instruments.json`:
```json
"exit_mode": "POINTS",
"local_exit_monitoring": true,
"broker_safety_sl": true,
"points_sl_sell": 74.0,
"points_target_sell": 25.0,
"points_target_high_conviction": 45.0,
"points_be_sell": 25.0
```

### C. Multi-Index Calibrated Presets (Strategy 22)
Calibrated across 365-day backtests with 81-82% win rates and optimal Profit Factors:

| Instrument | Base Lots | High Conviction Lots | Stop Loss (`pts`) | Target (`pts`) | High Conv. Target (`pts`) | Breakeven Trigger (`pts`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NIFTY** | 1 | 2 | 74.0 | 25.0 | 45.0 | 25.0 |
| **BANKNIFTY** | 1 | 2 | 100.0 | 45.0 | 75.0 | 45.0 |
| **SENSEX** | 1 | 2 | 140.0 | 50.0 | 90.0 | 40.0 |

---

## 🎯 12. Institutional Pre-Breakout / Pre-Breakdown Smart Hybrid Engine (Strategy 24)

### A. Overview & Strategy Intent
`Strategy_24` executes daily opening momentum trades on liquid equities and stock options that were identified by `select_prebreakout.py` during the post-market scan. The algorithm identifies institutional absorption, volatility compression (TTM Squeeze + NR7), 20 EMA base coiling, Minervini 3-wave VCP contraction ($\le 0.52$), and 14:30–15:25 IST Smart Money footprint (CAR $\ge 18\%$, CLV $\pm 0.45$, UVR $\ge 50\%$).

### B. Smart Hybrid Execution Modes (`--execution-mode`)
The EOD scanner supports three distinct operational modes:
1. **`hybrid` (Recommended Default)**:
   - Scans the Top 500 liquid universe.
   - If a candidate belongs to the **199 official NSE F&O stocks** (`stock_selection/fno_registry.json`), it configures it for **Stock Options (`OPTSTK` in `NSE_FNO`)** with exchange-mandated lot sizes and delta-scaled points SL/TP.
   - If a candidate is a non-F&O cash equity, it configures it for **5x MIS Cash Equities (`STOCK` in `NSE_EQ`)** with `stock_qty_override` sized to ₹5L position buying power.
2. **`stock`**:
   - Forces all selected setups into 5x Intraday MIS Cash Equities.
3. **`option`**:
   - Forces all selected setups into official NSE Stock Options. Use `--fno-only` to restrict scanning exclusively to F&O universe.

### C. SEBI 5x MIS Intraday Margin Formula
For cash equity setups, position sizing utilizes the 5x intraday margin provided by Indian brokers:
$$\text{stock\_qty\_override} = \max\left(1, \text{int}\left(\frac{\text{capital} \times \text{leverage}}{\text{trigger\_price}}\right)\right)$$
*Example:* With `capital = 100,000` and `leverage = 5.0`, a stock priced at ₹444.40 is allocated $\text{int}(500,000 / 444.40) = 1,125$ shares, scaling winning trade gains from ₹380 to ₹1,900 – ₹5,000+.

### D. F&O Stock Option Contract Presets
When an F&O stock is rotated:
- `segment`: `"NSE_FNO"`
- `instrument_type`: `"OPTSTK"`
- `lot_size`: Official exchange contract lot from `stock_selection/fno_registry.json` (e.g. `PNB: 8,000`, `LICHSGFIN: 1,000`, `CROMPTON: 1,800`, `ETERNAL: 2,425`).
- `points_sl`: $0.90 \times \text{ATR} \times 0.50$ (Option Delta scaling)
- `points_target`: $1.15 \times \text{ATR} \times 0.50$
- `points_be`: $0.65 \times \text{ATR} \times 0.50$

### E. Strategy 24 Execution Guards
- **Anti-Gap Exhaustion Trap (`MAX_GAP_ATR_MULT = 0.40`)**: If Day T+1 opens $> 0.40\times$ ATR beyond trigger, the setup is blocked to avoid retail gap-chasing traps.
- **Anti-Rejection Wick Filter (`MAX_ADVERSE_WICK_RATIO = 0.45`)**: If the 5-minute confirmation candle exhibits an adverse wick $> 45\%$ of its high-to-low range, entry is rejected.
- **Dynamic Breakeven**: Once spot gains $+0.65\times$ ATR in favor, SL is moved to entry price.
- **Strict Hard Stop**: $-0.90\times$ ATR.
- **Intraday EOD Square-Off**: Automatic exit at 15:15 IST.

### F. 3-Year Historical Walk-Forward Simulation Results (July 2023 – Sept 2026)
- **Sessions Tested**: 744 active NSE market sessions.
- **Trades**: 197 verified executions.
- **Win Rate**: **59.9%** (118 Wins / 79 Losses).
- **Profit Factor**: **2.26**.
- **Net Profit (1x Unleveraged)**: **+₹75,170** (ROI: +75.2%).
- **Net Profit (5x MIS Margin)**: **+₹3,75,850** (ROI: +375.8%).
- **Max Drawdown**: **₹5,646** (7.5% DD / Net Profit ratio).
- **Monthly Consistency**: **72.2% Profitable Months**.



