# Empirical Quantitative Research Report: Intraday NIFTY Options Alpha Signals (2021–2026)

> **EXECUTIVE SUMMARY:** Comprehensive 5.4-year empirical study (1,255 trading sessions, 6,565,579 1-minute option candles, near-the-money $\text{ATM}\pm 3$ universe) evaluating three distinct structural intraday option hypotheses.

---

## 1. Summary of Tested Hypotheses & Definitive Conclusions

| Hypothesis Tested | Underlying Mechanism | Statistical Status | Economic / Friction Status | Final Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **1. Abnormal Volume Spikes** | Directional Momentum / Whale Buying | **FAIL** ($p > 0.45$) | Buyer Win Rate $< 48\%$ | **Definitively Closed (Null Result)** |
| **2. Volume Spike Fade / IV** | Mean-Reversion / Volatility Crush | **FAIL** ($p > 0.20$) | Win rate $\approx$ random theta baseline | **Definitively Closed (Null Result)** |
| **3. Open Interest (OI) Dynamics**| Institutional Conviction (Vol + $\Delta\text{OI}$) | **FAIL** ($p > 0.10$) | Forward return negative ($-2.9\%$ in 30m) | **Definitively Closed (Null Result)** |
| **4. 3-Leg Synthetic Arbitrage** | Delta-Neutral Basis Parity ($\Delta = 0$) | **PASS** ($p < 10^{-50}$) | Gross $1.4\text{–}3.0\text{ pts}$ vs Cost $\mathbf{11.7\text{ pts}}$ | **Unviable (Sub-Friction)** |
| **5. 2-Leg Synthetic Conversion** | Options-Only Leaner Basis ($\Delta = 1.0$) | **PASS** ($p < 10^{-30}$) | Gross $2.8\text{ pts}$ vs Cost $\mathbf{4.5\text{ pts}}$, $\Delta=1.0$ risk | **Unviable (Naked Spot Drag)** |

---

## 2. Rigorous Itemized Cost Breakdown: 2-Leg vs 3-Leg Structures

To ensure complete mathematical and institutional consistency, below is the exact itemized cost breakdown for a 1-lot NIFTY position (50 qty) at typical ATM option premiums (~₹120) and Spot Index (~22,000):

| Fee Component | Statutory / Brokerage Rate | 2-Leg Structure ($+C, -P$) [4 Orders] | 3-Leg Structure ($+C, -P, -\text{Fut}$) [6 Orders] |
| :--- | :--- | :---: | :---: |
| **Brokerage** | ₹20 per executed order | ₹80.00 (4 orders = 1.60 pts) | ₹120.00 (6 orders = 2.40 pts) |
| **STT (Options)** | 0.15% on option sell turnover (₹12,000) | ₹18.00 (0.36 pts) | ₹18.00 (0.36 pts) |
| **STT (Futures)** | 0.02% on futures notional turnover (₹11,00,000) | ₹0.00 (0.00 pts) | **₹220.00 (4.40 pts)** |
| **Exchange Turnover** | 0.03553% (Opts) / 0.00173% (Fut) | ₹8.53 (0.17 pts) | ₹46.59 (0.93 pts) |
| **GST (18%)** | 18% on (Brokerage + Exchange Charges) | ₹15.94 (0.32 pts) | ₹29.99 (0.60 pts) |
| **Stamp Duty & SEBI** | 0.003% (Opts) / 0.002% (Fut) + SEBI fee | ₹1.02 (0.02 pts) | ₹23.22 (0.46 pts) |
| **Bid-Ask Slippage** | 0.5% per option leg / 0.05 pt per future leg | ₹120.00 (2.40 pts) | ₹125.00 (2.50 pts) |
| **Total Round-Trip Friction** | **Brokerage + Taxes + Slippage** | **₹243.49 (`4.87 index pts`)** | **₹582.80 (`11.66 index pts`)** |

### Reconciliation Note:
* **2-Leg vs 3-Leg Friction:** 2-Leg conversion friction ($\approx 4.5\text{ to }4.9\text{ pts}$) is indeed significantly lower than 3-Leg conversion friction ($\approx 11.7\text{ pts}$). The futures leg introduces a substantial ₹220 (4.40 pts) cost burden due to the **0.02% STT levied on the full ₹11,00,000 futures contract notional value**.
* **The No-Arbitrage Trap:**
  1. **3-Leg Arbitrage:** Delta-neutral ($\Delta = 0$), but gross mean-reversion ($1.4\text{ to }3.0\text{ pts}$) is completely overwhelmed by the **`11.7 pt`** round-trip friction.
  2. **2-Leg Conversion:** Reduces friction to **`4.5 pts`**, but gross basis alpha is only **`2.8 pts`** (Net PnL $= -1.7\text{ pts}$), while exposing the position to an unhedged **$\Delta = 1.0$ naked directional spot swing**.

---

## 3. Deep Dive: 2-Leg Options-Only Conversion ($+C_{\text{ATM}}, -P_{\text{ATM}}$)

When the Synthetic Future is significantly cheap relative to spot ($Z \le -2.0\sigma$, $N = 48,064$ events across 5.4 years), the 2-leg option synthetic long captures option repricing:

### A. Payoff vs Real Execution Friction

$$\text{Gross PnL} = (C_{\text{exit}} - P_{\text{exit}}) - (C_{\text{entry}} - P_{\text{entry}})$$

| Holding Horizon | Gross Reversion | 2-Leg Friction (Taxes + Slippage) | Net Realized PnL | Net INR / Lot | Net Win Rate ($>0$) | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **$+5\text{ min}$** | $+0.69\text{ pts}$ | $4.52\text{ pts}$ | **$-3.83\text{ pts}$** | ₹-191 | $36.8\%$ | $0.57$ |
| **$+15\text{ min}$** | $+1.46\text{ pts}$ | $4.51\text{ pts}$ | **$-3.05\text{ pts}$** | ₹-153 | $43.1\%$ | $0.69$ |
| **$+30\text{ min}$** | $+2.16\text{ pts}$ | $4.50\text{ pts}$ | **$-2.33\text{ pts}$** | ₹-117 | $45.5\%$ | $0.77$ |
| **$+60\text{ min}$** | $+2.79\text{ pts}$ | $4.48\text{ pts}$ | **$-1.69\text{ pts}$** | ₹-84 | $47.0\%$ | $0.84$ |
| **Day Close ($15:29$)**| $+2.76\text{ pts}$ | $4.41\text{ pts}$ | **$-1.65\text{ pts}$** | ₹-83 | $49.0\%$ | $0.87$ |
| **Next-Day Open ($09:30$)**| $+3.79\text{ pts}$ | $4.60\text{ pts}$ | **$-0.81\text{ pts}$** | ₹-40 | $47.8\%$ | $0.92$ |

* **Result:** At every single horizon, net realized PnL is negative, net win rate is sub-50%, and Profit Factor is below 0.92.

---

### B. Multi-Year Regime Trend (The Vanishing Arbitrage)

| Year | Events ($N$) | $+30\text{m}$ Net Pts | $+30\text{m}$ Win % | EOD Net Pts | EOD Win % | Next-Open Net Pts | Next-Open Win % |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2021** | 3,144 | $-1.26\text{ pts}$ | $46.1\%$ | **`+4.72 pts`** | $50.9\%$ | $+4.61\text{ pts}$ | $54.6\%$ |
| **2022** | 8,028 | $-1.95\text{ pts}$ | $46.4\%$ | **`+0.30 pts`** | $46.0\%$ | $-0.94\text{ pts}$ | $47.5\%$ |
| **2023** | 7,991 | $-1.44\text{ pts}$ | $47.8\%$ | **`-0.14 pts`** | $45.6\%$ | $-0.78\text{ pts}$ | $48.0\%$ |
| **2024** | 13,224 | $-2.70\text{ pts}$ | $44.9\%$ | **`-4.42 pts`** | $44.3\%$ | $-0.91\text{ pts}$ | $51.4\%$ |
| **2025** | 10,653 | $-2.15\text{ pts}$ | $45.5\%$ | **`-2.59 pts`** | $49.7\%$ | $-1.09\text{ pts}$ | $43.5\%$ |
| **2026** | 5,024 | $-4.46\text{ pts}$ | $41.5\%$ | **`-1.56 pts`** | $48.4\%$ | $-3.24\text{ pts}$ | $42.2\%$ |

> [!WARNING]
> **Market Efficiency Evolution:** While a small positive edge existed in 2021 (+4.72 pts), the rapid expansion of institutional algorithmic market making between 2022 and 2026 compressed option basis variance below exchange fee friction, turning the strategy net negative ($-1.5$ to $-4.4$ pts).

---

### C. The Fatal Structural Flaw: Naked Delta Exposure ($\Delta = 1.0$)

* **Target Microstructure Alpha:** $+2.76\text{ points}$ (EOD).
* **Underlying NIFTY Spot Volatility ($\sigma_{\text{Spot}}$):** **`93.38 points`** (Intraday) and **`191.99 points`** (Overnight Gap).
* **Signal-to-Noise Ratio (SNR):** $\mathbf{0.03}$ ($97\%$ random market noise vs $3\%$ alpha).
* **Conclusion:** Removing the futures leg creates an unhedged directional long position. Attempting to harvest $2.7$ points of basis alpha while exposing capital to a $93$-point random spot swing with $\approx ₹1.5\text{ Lakh}$ margin per lot is uncompensated variance.

---

### D. Live Trading Execution & Legging Risk

1. **Legging Latency:** Entering Long Call + Short Put simultaneously over broker APIs requires sequential order routing ($400\text{–}1,200\text{ ms}$). If Leg 1 fills and spot shifts $3\text{–}8$ points before Leg 2 fills, the entire basis edge is eradicated before the position is established.
2. **Capital Efficiency:** Short Put requires exchange margin of $\sim ₹1.2\text{–}1.5\text{ Lakhs}$ per lot. A $-0.81\text{ pt}$ average outcome yields negative return on capital.

---

## 4. Permanent Research Archetype Index

To prevent redundant reinvestigation in future research cycles:

1. **Single-Candle Option Volume:** Reflects passive market maker absorption and block hedging, not directional momentum ($p > 0.45$).
2. **Single-Candle OI Changes:** Bilateral flow (retail buying vs institutional writing); forward buyer returns remain negative ($-2.9\%$ in 30m).
3. **Put-Call Parity Basis Divergence:** Real mean-reverting property, but bounded within the $\approx 4.5\text{–}11.7\text{ pt}$ no-arbitrage friction band established by institutional market makers and statutory taxes.
