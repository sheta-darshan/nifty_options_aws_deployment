# 📊 Backtesting & Optimization Experiment Log

This file tracks all historical backtesting and optimization runs. Updates automatically.

| Date/Time | Type | Symbol | Strategy | Days | Leg | Train PnL (WR) | Test PnL (WR) | Best Parameters / Config | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06-11 17:42:49 | Optimization | NIFTY | Strategy_3 | 30 | SELL | Rs.33905.19 (72.7%) | Rs.-12782.80 (33.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-11 17:43:30 | Backtest | NIFTY | Strategy_3 | 30 | SELL | N/A (N/A) | Rs.20489.58 (55.9%) | sl_mult_buy=3, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-11 19:00:22 | Optimization | NIFTY | Strategy_3 | 730 | BOTH | Rs.5860.53 (40.6%) | Rs.-88515.84 (38.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-11 19:59:59 | Optimization | NIFTY | Strategy_3 | 730 | SELL | Rs.21027.95 (46.3%) | Rs.-20732.54 (42.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-12 13:52:14 | Optimization | POWERINDIA | Strategy_3 | 1825 | BOTH | Rs.-315116.10 (58.5%) | Rs.-335044.90 (61.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-12 17:36:59 | Optimization | POWERINDIA | Strategy_3 | 730 | BOTH | Rs.-180844.57 (52.9%) | Rs.-251259.95 (54.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-12 21:49:37 | Optimization | PERSISTENT | Strategy_3 | 730 | BOTH | Rs.-336795.27 (44.0%) | Rs.-596745.79 (35.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-12 22:16:01 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-65614.67 (25.3%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-12 22:22:34 | Optimization | POWERINDIA | Strategy_3 | 730 | BOTH | Rs.-180844.57 (52.9%) | Rs.-251259.95 (54.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-12 22:49:42 | Backtest | NIFTY | Strategy_7 | 730 | BOTH | N/A (N/A) | Rs.-211438.10 (41.1%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 07:56:35 | Backtest | NIFTY | Strategy_7 | 200 | BOTH | N/A (N/A) | Rs.-102408.10 (31.5%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 07:57:05 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-250198.26 (32.9%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 08:27:59 | Optimization | NIFTY | Strategy_7 | 1825 | BOTH | Rs.-289550.51 (61.1%) | Rs.-251331.38 (57.1%) | DO_RSI_LENGTH=10.0, HM_LENGTH=7.0, HM_WMA_LENGTH=14.0, AT... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-13 08:42:32 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-240220.39 (33.2%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 08:47:07 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-267292.25 (33.3%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 08:59:56 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-468516.73 (32.6%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:11:08 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-384210.94 (32.3%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:26:39 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-403616.06 (31.5%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:27:15 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-363269.67 (31.9%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:30:20 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-363301.47 (31.9%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:48:17 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-239273.57 (29.2%) | sl_mult_buy=1.5, tp_mult_buy=3, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:49:22 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-238037.24 (31.2%) | sl_mult_buy=2.5, tp_mult_buy=5, trailing_mult_buy=0.1, sl... | UNPROFITABLE |
| 2026-06-13 09:50:36 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-222532.97 (47.9%) | sl_mult_buy=2.5, tp_mult_buy=5, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:51:00 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-205091.08 (40.1%) | sl_mult_buy=2.5, tp_mult_buy=5, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:51:24 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-215385.11 (35.4%) | sl_mult_buy=2.5, tp_mult_buy=5, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:51:39 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-937769.18 (36.2%) | sl_mult_buy=2.5, tp_mult_buy=5, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:52:09 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-885715.29 (40.9%) | sl_mult_buy=2.5, tp_mult_buy=5, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-06-13 09:53:01 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-733034.99 (36.6%) | sl_mult_buy=2.5, tp_mult_buy=5, trailing_mult_buy=2.6, sl... | UNPROFITABLE |
| 2026-06-13 09:53:15 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-174517.99 (30.3%) | sl_mult_buy=2.5, tp_mult_buy=5, trailing_mult_buy=2.6, sl... | UNPROFITABLE |
| 2026-06-13 09:53:38 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-198817.42 (32.8%) | sl_mult_buy=2.5, tp_mult_buy=4, trailing_mult_buy=2.6, sl... | UNPROFITABLE |
| 2026-06-13 09:54:02 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-258127.02 (23.0%) | sl_mult_buy=1.5, tp_mult_buy=4, trailing_mult_buy=1.6, sl... | UNPROFITABLE |
| 2026-06-13 10:05:31 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-382492.90 (28.9%) | sl_mult_buy=1.5, tp_mult_buy=4, trailing_mult_buy=1.6, sl... | UNPROFITABLE |
| 2026-06-13 10:12:52 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-258127.02 (23.0%) | sl_mult_buy=1.5, tp_mult_buy=4, trailing_mult_buy=1.6, sl... | UNPROFITABLE |
| 2026-06-13 10:14:49 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.1798.40 (41.9%) | sl_mult_buy=1.5, tp_mult_buy=4, trailing_mult_buy=1.6, sl... | PROFITABLE |
| 2026-06-13 10:46:56 | Optimization | NIFTY | Strategy_7 | 1825 | BOTH | Rs.14418.90 (87.5%) | Rs.-1330.06 (33.3%) | DO_RSI_LENGTH=21.0, HM_LENGTH=7.0, HM_WMA_LENGTH=21.0, AT... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-13 11:03:54 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-954.45 (33.3%) | sl_mult_buy=2, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 11:16:48 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-192457.13 (42.4%) | sl_mult_buy=2, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 11:18:45 | Backtest | NIFTY | Strategy_7 | 720 | SELL | N/A (N/A) | Rs.-132715.78 (34.8%) | sl_mult_buy=2, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 11:19:50 | Backtest | NIFTY | Strategy_7 | 720 | SELL | N/A (N/A) | Rs.-114292.84 (34.3%) | sl_mult_buy=2, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 11:21:32 | Backtest | NIFTY | Strategy_3 | 720 | SELL | N/A (N/A) | Rs.9086.27 (41.4%) | sl_mult_buy=2, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-13 14:18:03 | Optimization | POWERINDIA | Strategy_3 | 720 | BOTH | Rs.250384.74 (51.0%) | Rs.2222.76 (44.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-13 15:41:42 | Backtest | NIFTY | Strategy_7 | 720 | SELL | N/A (N/A) | Rs.-114292.84 (34.3%) | sl_mult_buy=2, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 15:47:24 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-354282.73 (43.4%) | sl_mult_buy=2, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 15:52:38 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-321648.52 (29.8%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 15:57:11 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-232024.28 (26.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 16:00:58 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.-50176.47 (23.7%) | sl_mult_buy=1, tp_mult_buy=20, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-06-13 16:03:50 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-195388.11 (35.6%) | sl_mult_buy=1, tp_mult_buy=20, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-06-13 16:12:17 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.25669.73 (5.6%) | sl_mult_buy=1, tp_mult_buy=20, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-06-13 16:17:24 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.39865.59 (10.1%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-06-13 16:18:02 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.35304.19 (12.2%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-13 16:18:30 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-20005.03 (12.7%) | sl_mult_buy=1, tp_mult_buy=7, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-13 16:18:55 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.50535.25 (11.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-13 16:19:19 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-199939.27 (25.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.2, sl_m... | UNPROFITABLE |
| 2026-06-13 16:19:44 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-208075.35 (24.4%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.1, sl_m... | UNPROFITABLE |
| 2026-06-13 16:20:12 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.50535.25 (11.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 16:37:25 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.50535.25 (11.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:01:04 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.174420.26 (14.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:02:06 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.174420.26 (14.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:05:38 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.209952.16 (15.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:06:27 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.174420.26 (14.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:38:39 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.128500.94 (12.7%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.0, sl_... | PROFITABLE |
| 2026-06-13 17:45:40 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.951393.63 (14.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:46:09 | Backtest | NIFTY | Strategy_7 | 60 | BUY | N/A (N/A) | Rs.107257.53 (18.6%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:46:46 | Backtest | NIFTY | Strategy_7 | 120 | BUY | N/A (N/A) | Rs.127865.15 (16.7%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:47:05 | Backtest | NIFTY | Strategy_7 | 365 | BUY | N/A (N/A) | Rs.716944.68 (16.5%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:49:48 | Backtest | NIFTY | Strategy_7 | 365 | SELL | N/A (N/A) | Rs.90095.41 (28.3%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:55:24 | Backtest | NIFTY | Strategy_7 | 720 | SELL | N/A (N/A) | Rs.102414.86 (25.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:55:58 | Backtest | NIFTY | Strategy_7 | 720 | BOTH | N/A (N/A) | Rs.117726.05 (27.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:56:36 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.149713.26 (20.9%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 17:57:42 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.951393.63 (14.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 18:00:28 | Backtest | NIFTY | Strategy_7 | 720 | SELL | N/A (N/A) | Rs.102414.86 (25.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 18:01:24 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.174420.26 (14.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 18:41:53 | Backtest | NIFTY | Strategy_7 | 720 | SELL | N/A (N/A) | Rs.14735.26 (37.5%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 18:42:39 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.174420.26 (14.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 18:47:59 | Backtest | NIFTY | Strategy_7 | 1825 | BUY | N/A (N/A) | Rs.156662.65 (12.4%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 18:50:05 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.951393.63 (14.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 18:50:33 | Backtest | NIFTY | Strategy_7 | 1825 | BUY | N/A (N/A) | Rs.947325.36 (12.4%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 18:53:55 | Backtest | POWERINDIA | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-126146.73 (16.3%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-13 18:54:01 | Backtest | PERSISTENT | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-89341.60 (30.8%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:54:07 | Backtest | COLPAL | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-6406.85 (0.0%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:54:17 | Backtest | GODREJPROP | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.3767.58 (37.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 18:55:16 | Backtest | PAGEIND | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-315928.30 (19.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:55:21 | Backtest | APOLLOHOSP | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-119049.77 (20.3%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:55:27 | Backtest | MCX | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-10506.25 (20.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:55:32 | Backtest | KEI | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-19662.44 (41.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:56:37 | Backtest | ABB | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-231462.26 (13.0%) | sl_mult_buy=3, tp_mult_buy=20, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-06-13 18:56:47 | Backtest | ADANIENT | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-2146.72 (33.3%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:57:03 | Backtest | ALKEM | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-87653.52 (21.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:57:07 | Backtest | AMBER | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-207950.12 (29.7%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-13 18:57:28 | Backtest | ASIANPAINT | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-4669.72 (50.0%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:57:51 | Backtest | BAJAJ-AUTO | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-208774.14 (23.4%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:59:13 | Backtest | BLUESTARCO | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-2373.49 (0.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:59:19 | Backtest | BOSCHLTD | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-348329.38 (23.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 18:59:30 | Backtest | BRITANNIA | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-43623.22 (30.6%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-13 18:59:35 | Backtest | BSE | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-18100.98 (37.5%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-13 19:00:50 | Backtest | CUMMINSIND | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-44086.91 (30.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:01:11 | Backtest | DIVISLAB | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-44703.27 (33.3%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:01:17 | Backtest | DIXON | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-243935.90 (27.2%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-13 19:01:28 | Backtest | DMART | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-13636.03 (33.3%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-13 19:01:39 | Backtest | EICHERMOT | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-65445.22 (30.6%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:02:20 | Backtest | HAL | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-37861.96 (40.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:02:37 | Backtest | HDFCAMC | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.61111.24 (100.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:02:54 | Backtest | HEROMOTOCO | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.5562.78 (31.6%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:04:10 | Backtest | INDIGO | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.47621.03 (37.0%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:05:27 | Backtest | KAYNES | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-67439.42 (32.2%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:06:01 | Backtest | LT | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-14372.63 (0.0%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:06:07 | Backtest | LTIM | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-42534.94 (36.8%) | sl_mult_buy=2, tp_mult_buy=15, trailing_mult_buy=1.5, sl_... | UNPROFITABLE |
| 2026-06-13 19:06:18 | Backtest | M&M | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.11836.79 (100.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:06:39 | Backtest | MARUTI | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-236076.17 (23.5%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-13 19:06:48 | Backtest | MAZDOCK | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.6341.78 (100.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:07:13 | Backtest | MPHASIS | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.42298.74 (33.3%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:07:19 | Backtest | MUTHOOTFIN | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-28316.34 (25.0%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:08:04 | Backtest | OFSS | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-216107.95 (26.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:08:45 | Backtest | PIIND | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-3829.86 (30.0%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:08:53 | Backtest | POLICYBZR | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.1964.76 (100.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:08:59 | Backtest | POLYCAB | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-227348.27 (24.3%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:10:00 | Backtest | SHREECEM | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-389176.33 (19.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:10:15 | Backtest | SIEMENS | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-133896.01 (33.7%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:10:21 | Backtest | SOLARINDS | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-208948.14 (25.1%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:10:35 | Backtest | SRF | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-11242.74 (25.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:10:49 | Backtest | SUPREMEIND | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.48873.38 (42.9%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-13 19:11:10 | Backtest | TATAELXSI | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-30874.67 (32.1%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:11:46 | Backtest | TIINDIA | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-23771.69 (0.0%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-13 19:11:53 | Backtest | TITAN | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.17134.99 (75.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:12:03 | Backtest | TORNTPHARM | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.3711.07 (50.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-13 19:12:14 | Backtest | TRENT | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-110888.17 (28.4%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:12:21 | Backtest | TVSMOTOR | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-991.44 (50.0%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:12:27 | Backtest | ULTRACEMCO | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-200894.33 (22.3%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-13 19:51:50 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.335633.52 (11.3%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 19:59:28 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.407832.98 (11.4%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:16:35 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-39511.82 (11.3%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-13 20:18:38 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-47258.84 (11.5%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-13 20:19:27 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.210481.63 (12.3%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:21:39 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-87463.77 (9.6%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-13 20:22:13 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.30796.17 (11.6%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:29:39 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.350802.23 (11.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:34:08 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.350802.23 (11.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:35:02 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.49199.86 (11.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:42:41 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.49199.86 (11.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:43:08 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.61612.34 (11.4%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:43:28 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.91610.92 (11.9%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-13 20:59:53 | Backtest | NIFTY | Strategy_7 | 1825 | BUY | N/A (N/A) | Rs.-234350.27 (9.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-13 21:16:04 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-63067.89 (9.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-13 21:55:40 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-208744.34 (8.8%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-13 23:20:51 | Optimization | PERSISTENT | Strategy_3 | 720 | BOTH | Rs.-454958.13 (43.2%) | Rs.-680461.88 (37.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-13 23:35:08 | Optimization | COLPAL | Strategy_3 | 720 | BOTH | Rs.270943.51 (51.2%) | Rs.-12376.37 (45.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-13 23:44:43 | Optimization | ANGELONE | Strategy_3 | 720 | BOTH | Rs.582169.30 (50.0%) | Rs.128028.53 (45.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-13 23:57:32 | Optimization | GODREJPROP | Strategy_3 | 720 | BOTH | Rs.327265.07 (68.1%) | Rs.-14628.84 (61.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 00:07:25 | Optimization | PAYTM | Strategy_3 | 720 | BOTH | Rs.243881.78 (53.2%) | Rs.-225174.24 (45.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 00:20:29 | Optimization | LAURUSLABS | Strategy_3 | 720 | BOTH | Rs.225986.98 (48.5%) | Rs.237671.54 (49.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 00:33:34 | Optimization | RECLTD | Strategy_3 | 720 | BOTH | Rs.242671.58 (62.7%) | Rs.88517.96 (66.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 00:46:58 | Optimization | ABCAPITAL | Strategy_3 | 720 | BOTH | Rs.157751.90 (38.2%) | Rs.-387791.18 (29.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 00:55:25 | Optimization | IREDA | Strategy_3 | 720 | BOTH | Rs.182898.88 (43.3%) | Rs.94534.22 (41.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 01:08:18 | Optimization | NATIONALUM | Strategy_3 | 720 | BOTH | Rs.56824.51 (39.2%) | Rs.-59469.99 (35.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 01:18:50 | Optimization | UNIONBANK | Strategy_3 | 720 | BOTH | Rs.230510.79 (40.9%) | Rs.-202683.78 (33.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 01:32:32 | Optimization | CANBK | Strategy_3 | 720 | BOTH | Rs.633609.21 (59.1%) | Rs.-32993.66 (45.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 01:42:45 | Optimization | GMRAIRPORT | Strategy_3 | 720 | BOTH | Rs.258352.34 (57.2%) | Rs.-72376.55 (48.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 01:56:26 | Optimization | PNB | Strategy_3 | 720 | BOTH | Rs.500671.13 (52.5%) | Rs.-70678.66 (45.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 02:02:09 | Optimization | SUZLON | Strategy_3 | 720 | BOTH | Rs.82389.30 (31.5%) | Rs.-58028.66 (21.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 02:16:04 | Optimization | PAGEIND | Strategy_3 | 720 | BOTH | Rs.17886.63 (50.8%) | Rs.-70928.35 (48.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 02:29:58 | Optimization | APOLLOHOSP | Strategy_3 | 720 | BOTH | Rs.321541.58 (45.6%) | Rs.-39545.48 (37.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 02:42:31 | Optimization | MCX | Strategy_3 | 720 | BOTH | Rs.663478.64 (41.5%) | Rs.-309226.97 (29.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 02:52:31 | Optimization | KEI | Strategy_3 | 720 | BOTH | Rs.244269.83 (48.2%) | Rs.35651.83 (43.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 03:06:00 | Optimization | GLENMARK | Strategy_3 | 720 | BOTH | Rs.118266.52 (47.0%) | Rs.-205145.65 (42.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 03:19:56 | Optimization | UNITDSPR | Strategy_3 | 720 | BOTH | Rs.226244.24 (39.1%) | Rs.-87036.92 (29.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 03:33:06 | Optimization | BHARATFORG | Strategy_3 | 720 | BOTH | Rs.70609.65 (34.1%) | Rs.-199568.79 (29.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 03:41:48 | Optimization | PATANJALI | Strategy_3 | 720 | BOTH | Rs.92176.10 (54.3%) | Rs.-200415.59 (29.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 03:55:23 | Optimization | AUBANK | Strategy_3 | 720 | BOTH | Rs.108142.98 (40.1%) | Rs.-43064.95 (37.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 04:09:11 | Optimization | UPL | Strategy_3 | 720 | BOTH | Rs.-379462.32 (58.6%) | Rs.-173326.46 (57.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-14 04:23:33 | Optimization | NTPC | Strategy_3 | 720 | BOTH | Rs.28717.16 (39.3%) | Rs.-162728.01 (31.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 04:36:37 | Optimization | LTF | Strategy_3 | 720 | BOTH | Rs.86072.89 (40.0%) | Rs.-190836.28 (28.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 04:49:03 | Optimization | RBLBANK | Strategy_3 | 720 | BOTH | Rs.481786.91 (33.6%) | Rs.-246444.55 (21.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 04:55:19 | Optimization | 360ONE | Strategy_3 | 720 | BOTH | Rs.-19632.11 (51.0%) | Rs.-81645.28 (46.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-14 05:08:57 | Optimization | ABB | Strategy_3 | 720 | BOTH | Rs.523972.38 (41.2%) | Rs.-163791.48 (36.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 05:18:51 | Optimization | ADANIENSOL | Strategy_3 | 720 | BOTH | Rs.222840.76 (48.5%) | Rs.255905.12 (49.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 05:32:29 | Optimization | ADANIENT | Strategy_3 | 720 | BOTH | Rs.114403.31 (57.1%) | Rs.-74963.46 (54.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 05:42:02 | Optimization | ADANIGREEN | Strategy_3 | 720 | BOTH | Rs.551916.50 (50.3%) | Rs.393498.16 (47.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 05:55:47 | Optimization | ADANIPORTS | Strategy_3 | 720 | BOTH | Rs.87187.29 (33.3%) | Rs.51354.62 (35.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 06:09:46 | Optimization | ALKEM | Strategy_3 | 720 | BOTH | Rs.-273657.86 (52.9%) | Rs.-363715.77 (47.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-14 06:16:04 | Optimization | AMBER | Strategy_3 | 720 | BOTH | Rs.246825.59 (52.1%) | Rs.-109957.97 (39.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 06:29:36 | Optimization | AMBUJACEM | Strategy_3 | 720 | BOTH | Rs.249788.58 (44.9%) | Rs.-131267.88 (36.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 06:40:09 | Optimization | APLAPOLLO | Strategy_3 | 720 | BOTH | Rs.169101.54 (43.4%) | Rs.171947.96 (48.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 06:53:31 | Optimization | ASHOKLEY | Strategy_3 | 720 | BOTH | Rs.-85866.19 (59.6%) | Rs.-366493.78 (53.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-14 07:08:07 | Optimization | ASIANPAINT | Strategy_3 | 720 | BOTH | Rs.-166498.14 (58.0%) | Rs.-92768.53 (58.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-14 07:22:08 | Optimization | ASTRAL | Strategy_3 | 720 | BOTH | Rs.70003.41 (52.3%) | Rs.29825.52 (53.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 07:36:07 | Optimization | AUROPHARMA | Strategy_3 | 720 | BOTH | Rs.199755.69 (46.2%) | Rs.-146788.90 (39.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 07:50:52 | Optimization | AXISBANK | Strategy_3 | 720 | BOTH | Rs.16533.39 (38.2%) | Rs.-92242.41 (35.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 08:05:30 | Optimization | BAJAJ-AUTO | Strategy_3 | 720 | BOTH | Rs.326575.78 (40.4%) | Rs.-173924.75 (28.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 08:19:56 | Optimization | BAJAJFINSV | Strategy_3 | 720 | BOTH | Rs.-138770.91 (59.7%) | Rs.-60524.53 (61.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-14 08:34:28 | Optimization | BAJFINANCE | Strategy_3 | 720 | BOTH | Rs.85439.53 (40.1%) | Rs.98864.80 (42.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 08:48:37 | Optimization | BANDHANBNK | Strategy_3 | 720 | BOTH | Rs.310057.41 (64.6%) | Rs.-311266.67 (51.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 09:02:58 | Optimization | BANKBARODA | Strategy_3 | 720 | BOTH | Rs.323849.20 (39.6%) | Rs.-112874.08 (28.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 09:14:11 | Optimization | BANKINDIA | Strategy_3 | 720 | BOTH | Rs.351093.76 (46.0%) | Rs.-40391.69 (38.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 09:24:53 | Optimization | BDL | Strategy_3 | 720 | BOTH | Rs.221879.60 (44.3%) | Rs.-41826.97 (32.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 09:27:30 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-181903.53 (9.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-14 09:40:33 | Optimization | BEL | Strategy_3 | 720 | BOTH | Rs.276218.76 (45.9%) | Rs.-90879.53 (37.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 09:55:38 | Optimization | BHARTIARTL | Strategy_3 | 720 | BOTH | Rs.97578.37 (43.8%) | Rs.-196027.87 (36.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 10:11:40 | Optimization | BIOCON | Strategy_3 | 720 | BOTH | Rs.343731.93 (40.4%) | Rs.-419621.44 (32.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 10:19:01 | Optimization | BLUESTARCO | Strategy_3 | 720 | BOTH | Rs.-106711.56 (46.9%) | Rs.54652.01 (51.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-14 10:33:24 | Optimization | BOSCHLTD | Strategy_3 | 720 | BOTH | Rs.162523.41 (44.4%) | Rs.-22342.30 (40.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 10:47:51 | Optimization | BPCL | Strategy_3 | 720 | BOTH | Rs.-437563.95 (50.4%) | Rs.-154049.01 (50.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-14 11:03:09 | Optimization | BRITANNIA | Strategy_3 | 720 | BOTH | Rs.211764.39 (56.1%) | Rs.-334439.33 (40.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 11:06:08 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.-8469.30 (8.3%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-14 11:07:19 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.46402.98 (31.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-14 11:13:46 | Optimization | BSE | Strategy_3 | 720 | BOTH | Rs.865866.58 (47.3%) | Rs.683220.80 (44.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 11:24:31 | Optimization | CAMS | Strategy_3 | 720 | BOTH | Rs.477619.80 (45.8%) | Rs.-64618.41 (30.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-14 11:25:22 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-79980.92 (27.0%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-14 11:28:03 | Backtest | NIFTY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.33789.04 (29.3%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-14 11:31:32 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-79980.92 (27.0%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-14 11:34:21 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-29689.61 (27.5%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-14 11:53:05 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.7394.59 (27.5%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-14 12:00:10 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.7420.10 (25.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-14 12:09:39 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.-4931.25 (30.0%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-14 12:10:44 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.25316.79 (27.2%) | sl_mult_buy=1, tp_mult_buy=9, trailing_mult_buy=0.0, sl_m... | PROFITABLE |
| 2026-06-14 12:14:41 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-8856.57 (27.6%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-14 12:22:01 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-44026.05 (40.1%) | sl_mult_buy=1, tp_mult_buy=2, trailing_mult_buy=0.0, sl_m... | UNPROFITABLE |
| 2026-06-14 12:23:02 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-7103.73 (41.3%) | sl_mult_buy=1, tp_mult_buy=2, trailing_mult_buy=0.1, sl_m... | UNPROFITABLE |
| 2026-06-14 12:28:51 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-73100.41 (38.3%) | sl_mult_buy=1, tp_mult_buy=2, trailing_mult_buy=0.1, sl_m... | UNPROFITABLE |
| 2026-06-14 13:07:19 | Optimization | NIFTY | Strategy_7 | 730 | BOTH | Rs.91936.53 (38.1%) | Rs.53786.29 (46.5%) | DO_RSI_LENGTH=150.0, DO_SMA_LENGTH=100.0, DO_EMA1_LENGTH=... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-14 13:23:29 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.61018.60 (39.4%) | sl_mult_buy=1.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | PROFITABLE |
| 2026-06-15 14:52:05 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.5606.66 (45.8%) | sl_mult_buy=1.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | PROFITABLE |
| 2026-06-15 14:52:39 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.-1505.26 (41.7%) | sl_mult_buy=1.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 14:56:00 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-86035.99 (31.6%) | sl_mult_buy=1.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:03:00 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.-2943.07 (62.5%) | sl_mult_buy=1.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:05:18 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-92234.48 (47.1%) | sl_mult_buy=1.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:08:05 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-200389.22 (58.0%) | sl_mult_buy=1.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:09:23 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-200389.22 (58.0%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:10:15 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-165914.24 (39.5%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:15:07 | Backtest | NIFTY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-153297.33 (38.3%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:16:01 | Backtest | NIFTY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-202858.36 (57.5%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:16:24 | Backtest | NIFTY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-197878.82 (56.8%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:16:55 | Backtest | NIFTY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-185753.91 (50.8%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:17:22 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-184443.91 (52.2%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:20:22 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-178032.59 (52.1%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:21:32 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-171824.93 (46.3%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:22:03 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-170010.61 (43.7%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:24:17 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-424349.72 (39.6%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:45:34 | Optimization | NIFTY | Strategy_7 | 730 | BOTH | Rs.-452316.50 (51.3%) | Rs.-334052.30 (48.4%) | DO_RSI_LENGTH=14.0, DO_SMA_LENGTH=9.0, DO_EMA1_LENGTH=7.0... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-15 15:48:05 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-459460.97 (38.5%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:49:35 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-273846.72 (37.6%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:50:09 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-201844.83 (38.3%) | sl_mult_buy=0.5, tp_mult_buy=4.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 15:51:56 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-232453.77 (42.9%) | sl_mult_buy=1.5, tp_mult_buy=1.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 16:45:31 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-56643.04 (42.9%) | sl_mult_buy=1.5, tp_mult_buy=1.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 17:05:42 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-248184.51 (39.2%) | sl_mult_buy=1.5, tp_mult_buy=1.5, trailing_mult_buy=1.1, ... | UNPROFITABLE |
| 2026-06-15 17:07:13 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-257877.06 (28.1%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-15 23:20:58 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-298730.38 (26.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 09:35:44 | Backtest | NIFTY | Strategy_7 | 730 | SELL | N/A (N/A) | Rs.-96320.42 (37.7%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 10:45:23 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.-13524.52 (30.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 10:57:21 | Optimization | NIFTY | Strategy_7 | 15 | BUY | Rs.6447.62 (41.7%) | Rs.-5467.38 (20.0%) | DO_RSI_LENGTH=14.0, DO_SMA_LENGTH=9.0, DO_EMA1_LENGTH=5.0... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-16 11:57:18 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.-13524.52 (30.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 11:57:37 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.-13524.52 (30.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 11:58:33 | Backtest | NIFTY | Strategy_7 | 30 | BUY | N/A (N/A) | Rs.-13524.52 (30.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 12:10:33 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.109201.03 (65.8%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-16 12:18:25 | Backtest | NIFTY | Strategy_7 | 730 | BUY | N/A (N/A) | Rs.-293240.31 (44.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 12:18:57 | Backtest | NIFTY | Strategy_7 | 1825 | BUY | N/A (N/A) | Rs.-293240.31 (44.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 12:38:36 | Backtest | NIFTY | Strategy_9 | 30 | BUY | N/A (N/A) | Rs.-11380.18 (41.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 12:40:54 | Optimization | NIFTY | Strategy_9 | 30 | BUY | Rs.10346.82 (45.5%) | Rs.-1983.21 (25.0%) | S9_BODY_MIN_BUY=0.08, S9_EMA_DIFF_MAX_BUY=-0.4, S9_BODY_M... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-16 13:03:22 | Backtest | NIFTY | Strategy_9 | 30 | BUY | N/A (N/A) | Rs.-11380.18 (41.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 13:19:32 | Backtest | NIFTY | Strategy_9 | 720 | BUY | N/A (N/A) | Rs.-167569.53 (47.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 13:27:02 | Backtest | NIFTY | Strategy_9 | 720 | BUY | N/A (N/A) | Rs.-120363.26 (54.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 13:28:04 | Backtest | NIFTY | Strategy_9 | 720 | BUY | N/A (N/A) | Rs.-147976.83 (41.8%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:12:56 | Backtest | NIFTY | Strategy_9 | 30 | BUY | N/A (N/A) | Rs.-13235.78 (34.1%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:24:17 | Optimization | NIFTY | Strategy_9 | 730 | BOTH | Rs.-211754.83 (59.6%) | Rs.-43499.09 (62.5%) | S9_BODY_MIN_BUY=0.04, S9_EMA_DIFF_MAX_BUY=-0.2, S9_BODY_M... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-16 14:26:18 | Backtest | NIFTY | Strategy_9 | 720 | BUY | N/A (N/A) | Rs.-116131.01 (28.1%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:28:21 | Backtest | NIFTY | Strategy_3 | 720 | BOTH | N/A (N/A) | Rs.-417214.27 (43.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:30:03 | Backtest | NIFTY | Strategy_3 | 720 | BOTH | N/A (N/A) | Rs.-385056.84 (38.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:31:32 | Backtest | NIFTY | Strategy_3 | 720 | BOTH | N/A (N/A) | Rs.-347333.03 (33.2%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:33:06 | Backtest | NIFTY | Strategy_3 | 720 | BOTH | N/A (N/A) | Rs.-294467.14 (38.1%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:36:06 | Backtest | NIFTY | Strategy_3 | 720 | BOTH | N/A (N/A) | Rs.-112628.84 (42.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:39:14 | Backtest | NIFTY | Strategy_3 | 720 | BOTH | N/A (N/A) | Rs.-31675.03 (44.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:44:42 | Backtest | NIFTY | Strategy_3 | 720 | BOTH | N/A (N/A) | Rs.22029.18 (44.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-16 14:53:24 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-89356.78 (42.1%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:55:54 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-118313.26 (45.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 14:56:49 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-220915.19 (41.8%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:01:38 | Backtest | NIFTY | Strategy_7 | 720 | BUY | N/A (N/A) | Rs.-236379.45 (31.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:13:18 | Backtest | NIFTY | Strategy_8 | 30 | BUY | N/A (N/A) | Rs.-19596.33 (10.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:16:53 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-112534.92 (34.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:17:19 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-122648.98 (33.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:21:44 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-71675.09 (35.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:22:07 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-101896.36 (34.8%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:22:32 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-75173.91 (34.7%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:23:00 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-98473.12 (34.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:25:01 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-173571.45 (35.2%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:25:29 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-214431.28 (34.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:26:10 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-218598.90 (28.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:47:36 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-175546.12 (36.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 15:56:12 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-83444.84 (34.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 16:09:26 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-83444.84 (34.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 16:10:06 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-64848.52 (34.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 16:43:29 | Backtest | NIFTY | Strategy_8 | 720 | BOTH | N/A (N/A) | Rs.-83444.84 (34.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 20:39:54 | Backtest | NIFTY | Strategy_6 | 30 | BUY | N/A (N/A) | Rs.-418.35 (30.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 20:41:49 | Backtest | NIFTY | Strategy_6 | 30 | BUY | N/A (N/A) | Rs.-418.35 (30.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 20:48:01 | Backtest | NIFTY | Strategy_6 | 30 | BUY | N/A (N/A) | Rs.-35377.27 (25.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 20:49:31 | Backtest | NIFTY | Strategy_6 | 60 | BOTH | N/A (N/A) | Rs.-75203.43 (26.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 20:51:42 | Backtest | NIFTY | Strategy_6 | 60 | BOTH | N/A (N/A) | Rs.-71589.91 (22.1%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 20:54:04 | Backtest | NIFTY | Strategy_6 | 60 | BOTH | N/A (N/A) | Rs.-48135.56 (28.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 20:54:40 | Backtest | NIFTY | Strategy_6 | 60 | BOTH | N/A (N/A) | Rs.-27584.96 (38.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 21:12:37 | Optimization | NIFTY | Strategy_6 | 730 | BOTH | Rs.40670.95 (38.1%) | Rs.-191033.26 (31.3%) | S6_RANGE_SIZE=3.0, S6_RANGE_PERIOD=20.0, S6_SMOOTH_PERIOD... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-16 21:19:17 | Backtest | NIFTY | Strategy_6 | 60 | BOTH | N/A (N/A) | Rs.-33979.96 (37.6%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-16 21:19:53 | Backtest | NIFTY | Strategy_6 | 60 | SELL | N/A (N/A) | Rs.-34723.11 (32.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-17 09:26:30 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.90500.31 (76.7%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 09:32:21 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.191936.13 (70.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 09:44:23 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.206115.62 (66.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 11:01:36 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.60976.27 (59.8%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 11:07:41 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.152547.50 (74.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 11:10:22 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.-25596.83 (59.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-17 11:11:34 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.100386.55 (55.8%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 11:51:58 | Optimization | NIFTY | Strategy_3 | 730 | SELL | Rs.199148.94 (49.8%) | Rs.-11823.02 (38.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 11:56:31 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.246096.26 (42.6%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 12:10:24 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.237338.72 (39.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 12:12:22 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.90368.26 (49.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 12:13:16 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.246096.26 (42.6%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 12:13:47 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.212530.70 (42.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 12:14:34 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.251070.19 (42.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 12:15:24 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.247038.61 (42.2%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 12:16:05 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.142500.06 (37.2%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 13:13:23 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.66253.42 (34.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 13:14:13 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.247038.61 (42.2%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 13:18:01 | Backtest | NIFTY | Strategy_3 | 730 | SELL | N/A (N/A) | Rs.240673.60 (42.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-17 16:30:06 | Optimization | NIFTY | Strategy_3 | 15 | BUY | Rs.-3197.06 (61.5%) | Rs.-2416.48 (62.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 16:31:35 | Optimization | SBIN | Strategy_3 | 15 | BUY | Rs.-3590.15 (36.4%) | Rs.8548.82 (42.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 16:44:26 | Optimization | POWERINDIA | Strategy_3 | 730 | BUY | Rs.-47830.44 (30.3%) | Rs.-69742.87 (25.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 16:53:47 | Optimization | PERSISTENT | Strategy_3 | 730 | BUY | Rs.-227238.52 (38.1%) | Rs.-137200.67 (34.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 17:06:05 | Optimization | COLPAL | Strategy_3 | 15 | BUY | Rs.-4458.69 (20.0%) | Rs.1661.39 (50.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 17:06:39 | Backtest | COLPAL | Strategy_3 | 15 | BUY | N/A (N/A) | Rs.-6477.15 (28.6%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-17 17:16:32 | Optimization | POWERINDIA | Strategy_3 | 730 | BOTH | Rs.17765.79 (51.7%) | Rs.-64740.98 (46.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 17:28:05 | Optimization | COLPAL | Strategy_3 | 15 | BUY | Rs.-4458.69 (20.0%) | Rs.1661.39 (50.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 17:29:25 | Optimization | NIFTY | Strategy_3 | 15 | BUY | Rs.-5232.69 (46.2%) | Rs.25.16 (62.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 17:36:00 | Optimization | POWERINDIA | Strategy_3 | 730 | BOTH | Rs.17765.79 (51.7%) | Rs.-64740.98 (46.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 17:48:02 | Optimization | PERSISTENT | Strategy_3 | 730 | BOTH | Rs.-295748.63 (57.7%) | Rs.-163921.91 (56.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 17:58:03 | Optimization | COLPAL | Strategy_3 | 730 | BOTH | Rs.-516788.16 (54.7%) | Rs.-160212.34 (56.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 19:32:02 | Optimization | ANGELONE | Strategy_3 | 730 | BOTH | Rs.134749.80 (28.2%) | Rs.122887.75 (32.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-17 19:42:49 | Optimization | GODREJPROP | Strategy_3 | 730 | BOTH | Rs.-410375.21 (58.1%) | Rs.-57084.05 (62.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 19:49:07 | Optimization | PAYTM | Strategy_3 | 730 | BOTH | Rs.-335587.07 (50.9%) | Rs.-196883.53 (51.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 19:56:33 | Optimization | LAURUSLABS | Strategy_3 | 730 | BOTH | Rs.-328804.70 (50.8%) | Rs.-351229.74 (47.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 20:05:55 | Optimization | RECLTD | Strategy_3 | 730 | BOTH | Rs.-465865.14 (57.1%) | Rs.-93637.92 (59.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 20:17:07 | Optimization | ABCAPITAL | Strategy_3 | 730 | BOTH | Rs.-389703.46 (66.7%) | Rs.-402753.22 (63.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 20:26:15 | Optimization | IREDA | Strategy_3 | 730 | BOTH | Rs.227257.97 (43.9%) | Rs.121647.14 (40.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-17 20:40:57 | Optimization | NATIONALUM | Strategy_3 | 730 | BOTH | Rs.-293502.12 (64.4%) | Rs.-285604.00 (61.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 20:55:13 | Optimization | UNIONBANK | Strategy_3 | 730 | BOTH | Rs.205206.61 (42.1%) | Rs.-99333.93 (40.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 21:16:22 | Optimization | CANBK | Strategy_3 | 730 | BOTH | Rs.708418.95 (49.3%) | Rs.-16524.59 (39.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 21:33:25 | Optimization | GMRAIRPORT | Strategy_3 | 730 | BOTH | Rs.296874.02 (48.1%) | Rs.-55315.10 (36.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 21:53:55 | Optimization | PNB | Strategy_3 | 730 | BOTH | Rs.605734.30 (57.2%) | Rs.-69652.01 (46.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 22:02:34 | Optimization | SUZLON | Strategy_3 | 730 | BOTH | Rs.220574.94 (57.9%) | Rs.-69655.11 (35.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 22:10:38 | Optimization | PAGEIND | Strategy_3 | 730 | BOTH | Rs.-583947.14 (41.4%) | Rs.-106737.10 (48.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 22:17:34 | Optimization | APOLLOHOSP | Strategy_3 | 730 | BOTH | Rs.-731202.65 (45.9%) | Rs.-354205.95 (46.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 22:28:02 | Optimization | MCX | Strategy_3 | 730 | BOTH | Rs.76420.35 (35.1%) | Rs.-376752.06 (30.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 22:36:07 | Optimization | KEI | Strategy_3 | 730 | BOTH | Rs.-185506.18 (53.4%) | Rs.-244844.66 (47.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 22:46:01 | Optimization | GLENMARK | Strategy_3 | 730 | BOTH | Rs.-471229.75 (64.7%) | Rs.-406708.67 (57.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 22:53:50 | Optimization | UNITDSPR | Strategy_3 | 730 | BOTH | Rs.-405709.28 (48.4%) | Rs.-130421.78 (52.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 23:04:22 | Optimization | BHARATFORG | Strategy_3 | 730 | BOTH | Rs.-383130.95 (67.5%) | Rs.-446598.69 (57.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 23:09:17 | Optimization | PATANJALI | Strategy_3 | 730 | BOTH | Rs.-188322.25 (52.4%) | Rs.-136749.40 (44.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 23:17:47 | Optimization | AUBANK | Strategy_3 | 730 | BOTH | Rs.-463688.32 (66.2%) | Rs.-335817.65 (65.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 23:26:13 | Optimization | UPL | Strategy_3 | 730 | BOTH | Rs.-726414.66 (53.6%) | Rs.-524898.43 (47.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 23:34:54 | Optimization | NTPC | Strategy_3 | 730 | BOTH | Rs.-383437.18 (56.0%) | Rs.-241678.78 (53.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-17 23:47:14 | Optimization | LTF | Strategy_3 | 730 | BOTH | Rs.5677.12 (46.1%) | Rs.-212290.59 (40.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-17 23:57:32 | Optimization | RBLBANK | Strategy_3 | 730 | BOTH | Rs.132949.42 (38.5%) | Rs.-419734.14 (26.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 00:02:18 | Optimization | 360ONE | Strategy_3 | 730 | BOTH | Rs.-269427.36 (59.0%) | Rs.-117034.88 (62.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 00:12:34 | Optimization | ABB | Strategy_3 | 730 | BOTH | Rs.-595357.46 (64.3%) | Rs.-333722.77 (61.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 00:20:13 | Optimization | ADANIENSOL | Strategy_3 | 730 | BOTH | Rs.-275119.58 (58.6%) | Rs.-212923.95 (55.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 00:30:24 | Optimization | ADANIENT | Strategy_3 | 730 | BOTH | Rs.-380503.95 (54.9%) | Rs.-231432.06 (50.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 00:38:28 | Optimization | ADANIGREEN | Strategy_3 | 730 | BOTH | Rs.264593.43 (45.1%) | Rs.84539.41 (43.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-18 00:48:00 | Optimization | ADANIPORTS | Strategy_3 | 730 | BOTH | Rs.-476433.59 (49.0%) | Rs.-313437.74 (46.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 00:55:38 | Optimization | ALKEM | Strategy_3 | 730 | BOTH | Rs.-582324.18 (53.4%) | Rs.-293557.97 (53.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 01:00:30 | Optimization | AMBER | Strategy_3 | 730 | BOTH | Rs.-266162.01 (49.1%) | Rs.-73372.94 (53.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 01:09:01 | Optimization | AMBUJACEM | Strategy_3 | 730 | BOTH | Rs.-363553.35 (50.7%) | Rs.-134847.43 (54.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 01:16:34 | Optimization | APLAPOLLO | Strategy_3 | 730 | BOTH | Rs.-377195.72 (53.9%) | Rs.-163448.97 (57.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 01:32:22 | Optimization | ASHOKLEY | Strategy_3 | 730 | BOTH | Rs.13119.80 (36.2%) | Rs.63990.59 (36.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-18 01:39:27 | Optimization | ASIANPAINT | Strategy_3 | 730 | BOTH | Rs.-568565.76 (52.4%) | Rs.-340257.47 (46.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 01:47:18 | Optimization | ASTRAL | Strategy_3 | 730 | BOTH | Rs.-510806.58 (56.2%) | Rs.-185747.32 (58.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 01:57:29 | Optimization | AUROPHARMA | Strategy_3 | 730 | BOTH | Rs.-441385.28 (56.0%) | Rs.-447493.64 (46.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 02:04:27 | Optimization | AXISBANK | Strategy_3 | 730 | BOTH | Rs.-681576.35 (51.0%) | Rs.-368150.36 (50.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 02:12:18 | Optimization | BAJAJ-AUTO | Strategy_3 | 730 | BOTH | Rs.-374995.08 (45.3%) | Rs.-343718.18 (39.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 02:20:07 | Optimization | BAJAJFINSV | Strategy_3 | 730 | BOTH | Rs.-446142.83 (52.2%) | Rs.-200337.55 (53.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 02:27:57 | Optimization | BAJFINANCE | Strategy_3 | 730 | BOTH | Rs.-476598.51 (54.9%) | Rs.-280475.87 (53.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 02:41:18 | Optimization | BANDHANBNK | Strategy_3 | 730 | BOTH | Rs.342263.06 (48.2%) | Rs.-272768.05 (32.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 02:53:04 | Optimization | BANKBARODA | Strategy_3 | 730 | BOTH | Rs.32930.98 (33.7%) | Rs.-385051.17 (24.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 03:04:22 | Optimization | BANKINDIA | Strategy_3 | 730 | BOTH | Rs.527221.73 (49.1%) | Rs.-234480.18 (26.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 03:09:43 | Optimization | BDL | Strategy_3 | 730 | BOTH | Rs.-76941.70 (65.3%) | Rs.-78624.29 (56.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 03:19:50 | Optimization | BEL | Strategy_3 | 730 | BOTH | Rs.47979.30 (30.5%) | Rs.-192029.45 (24.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 03:26:47 | Optimization | BHARTIARTL | Strategy_3 | 730 | BOTH | Rs.-566570.23 (55.1%) | Rs.-422665.32 (50.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 03:37:03 | Optimization | BHEL | Strategy_3 | 730 | BOTH | Rs.263496.47 (42.3%) | Rs.-65339.49 (38.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 03:44:43 | Optimization | BIOCON | Strategy_3 | 730 | BOTH | Rs.-656737.48 (65.4%) | Rs.-469158.84 (60.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 03:49:13 | Optimization | BLUESTARCO | Strategy_3 | 730 | BOTH | Rs.-130246.39 (53.1%) | Rs.-177217.80 (45.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 03:57:09 | Optimization | BOSCHLTD | Strategy_3 | 730 | BOTH | Rs.-672918.19 (55.9%) | Rs.-266923.16 (57.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 04:06:55 | Optimization | BPCL | Strategy_3 | 730 | BOTH | Rs.-520729.17 (59.9%) | Rs.-322129.49 (58.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 04:14:47 | Optimization | BRITANNIA | Strategy_3 | 730 | BOTH | Rs.-614570.73 (41.0%) | Rs.-384928.69 (37.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 04:22:26 | Optimization | BSE | Strategy_3 | 730 | BOTH | Rs.551103.19 (36.4%) | Rs.41594.22 (29.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-18 04:29:42 | Optimization | CAMS | Strategy_3 | 730 | BOTH | Rs.-353328.71 (63.6%) | Rs.-110480.35 (66.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 04:37:53 | Optimization | CDSL | Strategy_3 | 730 | BOTH | Rs.283641.20 (38.2%) | Rs.80326.43 (36.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-18 04:45:32 | Optimization | CGPOWER | Strategy_3 | 730 | BOTH | Rs.-291907.32 (57.5%) | Rs.-161422.31 (56.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 04:55:32 | Optimization | CHOLAFIN | Strategy_3 | 730 | BOTH | Rs.-493817.71 (58.7%) | Rs.-376897.89 (55.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 05:03:22 | Optimization | CIPLA | Strategy_3 | 730 | BOTH | Rs.-591479.55 (49.8%) | Rs.-248096.76 (51.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 05:11:30 | Optimization | COALINDIA | Strategy_3 | 730 | BOTH | Rs.-330438.86 (44.8%) | Rs.-293272.63 (38.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 05:21:25 | Optimization | COFORGE | Strategy_3 | 730 | BOTH | Rs.-199704.38 (47.7%) | Rs.-128056.32 (45.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 05:29:25 | Optimization | CONCOR | Strategy_3 | 730 | BOTH | Rs.-469765.44 (58.6%) | Rs.-238075.84 (56.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 05:37:12 | Optimization | CROMPTON | Strategy_3 | 730 | BOTH | Rs.-288249.66 (46.7%) | Rs.-126124.64 (44.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 05:47:04 | Optimization | CUMMINSIND | Strategy_3 | 730 | BOTH | Rs.-537666.17 (64.3%) | Rs.-355080.62 (63.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 05:54:01 | Optimization | DABUR | Strategy_3 | 730 | BOTH | Rs.-586225.99 (54.1%) | Rs.-280683.19 (53.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 06:02:28 | Optimization | DALBHARAT | Strategy_3 | 730 | BOTH | Rs.-487496.69 (55.1%) | Rs.-265421.66 (53.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 06:08:24 | Optimization | DELHIVERY | Strategy_3 | 730 | BOTH | Rs.-421988.91 (57.3%) | Rs.-273009.60 (55.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 06:16:09 | Optimization | DIVISLAB | Strategy_3 | 730 | BOTH | Rs.-412348.14 (49.5%) | Rs.-345767.69 (42.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 06:26:15 | Optimization | DIXON | Strategy_3 | 730 | BOTH | Rs.-481440.16 (55.5%) | Rs.-165884.13 (59.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 06:34:46 | Optimization | DLF | Strategy_3 | 730 | BOTH | Rs.-322091.49 (47.2%) | Rs.-113234.42 (48.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 06:40:45 | Optimization | DMART | Strategy_3 | 730 | BOTH | Rs.-230203.27 (53.0%) | Rs.-171332.13 (49.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 06:48:22 | Optimization | DRREDDY | Strategy_3 | 730 | BOTH | Rs.-864235.44 (48.0%) | Rs.-363205.99 (51.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 06:56:02 | Optimization | EICHERMOT | Strategy_3 | 730 | BOTH | Rs.-380562.43 (56.0%) | Rs.-298149.79 (51.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 07:02:17 | Optimization | ETERNAL | Strategy_3 | 730 | BOTH | Rs.92161.90 (41.5%) | Rs.-99146.78 (33.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 07:11:27 | Optimization | EXIDEIND | Strategy_3 | 730 | BOTH | Rs.-475356.79 (58.0%) | Rs.-283603.71 (53.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 07:25:02 | Optimization | FEDERALBNK | Strategy_3 | 730 | BOTH | Rs.32813.10 (33.9%) | Rs.-255349.12 (26.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 07:41:00 | Optimization | FORTIS | Strategy_3 | 730 | BOTH | Rs.-193287.15 (73.2%) | Rs.-98209.11 (72.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 07:53:39 | Optimization | GAIL | Strategy_3 | 730 | BOTH | Rs.57838.41 (42.1%) | Rs.-150029.62 (33.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 08:01:23 | Optimization | GODREJCP | Strategy_3 | 730 | BOTH | Rs.-520379.71 (53.9%) | Rs.-268075.97 (53.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 08:09:00 | Optimization | GRASIM | Strategy_3 | 730 | BOTH | Rs.-425712.35 (50.4%) | Rs.-411132.00 (40.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 08:19:01 | Optimization | HAL | Strategy_3 | 730 | BOTH | Rs.-127971.32 (44.7%) | Rs.-130587.72 (42.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 08:27:43 | Optimization | HAVELLS | Strategy_3 | 730 | BOTH | Rs.-571954.94 (49.5%) | Rs.-229220.74 (48.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 08:37:24 | Optimization | HCLTECH | Strategy_3 | 730 | BOTH | Rs.-579969.76 (44.1%) | Rs.-187314.71 (47.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 08:46:11 | Optimization | HDFCAMC | Strategy_3 | 730 | BOTH | Rs.-349355.93 (51.6%) | Rs.-238828.95 (52.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 08:52:43 | Optimization | HDFCBANK | Strategy_3 | 730 | BOTH | Rs.-440425.15 (45.0%) | Rs.-87920.88 (53.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 09:00:44 | Optimization | HDFCLIFE | Strategy_3 | 730 | BOTH | Rs.-663700.37 (53.1%) | Rs.-251735.67 (56.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 09:08:43 | Optimization | HEROMOTOCO | Strategy_3 | 730 | BOTH | Rs.-419293.17 (57.8%) | Rs.-281480.12 (56.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 09:17:55 | Optimization | HINDALCO | Strategy_3 | 730 | BOTH | Rs.-410048.01 (53.6%) | Rs.-267000.74 (53.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 09:28:42 | Optimization | HINDPETRO | Strategy_3 | 730 | BOTH | Rs.-492568.61 (58.1%) | Rs.-330053.38 (53.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 09:37:54 | Optimization | HINDUNILVR | Strategy_3 | 730 | BOTH | Rs.-692882.61 (45.0%) | Rs.-208051.07 (50.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 09:45:47 | Optimization | HINDZINC | Strategy_3 | 730 | BOTH | Rs.-266307.66 (65.1%) | Rs.-203780.67 (59.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 09:56:39 | Optimization | HUDCO | Strategy_3 | 730 | BOTH | Rs.278899.61 (44.4%) | Rs.-49488.37 (34.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 10:07:44 | Optimization | ICICIBANK | Strategy_3 | 730 | BOTH | Rs.-924957.41 (42.1%) | Rs.-215713.22 (53.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 10:18:22 | Optimization | ICICIGI | Strategy_3 | 730 | BOTH | Rs.-491118.21 (55.3%) | Rs.-234043.58 (55.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 10:31:59 | Optimization | ICICIPRULI | Strategy_3 | 730 | BOTH | Rs.-450607.12 (48.3%) | Rs.-145015.99 (50.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 10:59:44 | Optimization | IDEA | Strategy_3 | 730 | BOTH | Rs.487535.88 (66.7%) | Rs.140631.66 (42.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both Train AND Out-of-Sample Test data. |
| 2026-06-18 11:28:09 | Optimization | IDFCFIRSTB | Strategy_3 | 730 | BOTH | Rs.148574.41 (54.4%) | Rs.-261820.89 (44.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 12:01:23 | Optimization | IEX | Strategy_3 | 730 | BOTH | Rs.189690.15 (47.7%) | Rs.-18147.79 (42.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on unseen Out-of-Sample test data. |
| 2026-06-18 12:11:12 | Optimization | INDHOTEL | Strategy_3 | 730 | BOTH | Rs.-409203.86 (69.0%) | Rs.-254638.21 (64.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 12:17:59 | Optimization | INDIANB | Strategy_3 | 730 | BOTH | Rs.-390848.70 (54.6%) | Rs.-252496.81 (54.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 12:27:04 | Optimization | INDIGO | Strategy_3 | 730 | BOTH | Rs.-476552.31 (66.1%) | Rs.-330825.16 (62.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 12:36:31 | Optimization | INDUSINDBK | Strategy_3 | 730 | BOTH | Rs.-493279.72 (56.0%) | Rs.-210784.76 (55.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 12:47:03 | Optimization | INDUSTOWER | Strategy_3 | 730 | BOTH | Rs.-500320.18 (64.3%) | Rs.-294860.51 (63.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 12:56:29 | Optimization | INFY | Strategy_3 | 730 | BOTH | Rs.-604087.96 (39.3%) | Rs.-156194.95 (43.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 13:04:57 | Optimization | INOXWIND | Strategy_3 | 730 | BOTH | Rs.-183223.94 (70.8%) | Rs.-98885.26 (59.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 13:21:13 | Optimization | IOC | Strategy_3 | 730 | BOTH | Rs.-479471.87 (57.8%) | Rs.-329364.29 (57.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 13:30:00 | Optimization | IRCTC | Strategy_3 | 730 | BOTH | Rs.-515964.57 (50.8%) | Rs.-147011.22 (49.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 13:41:45 | Optimization | IRFC | Strategy_3 | 730 | BOTH | Rs.-207639.52 (60.2%) | Rs.-113992.45 (54.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 13:42:31 | Optimization | COLPAL | Strategy_3 | 30 | BUY | Rs.-6520.12 (33.3%) | Rs.-3606.33 (20.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 13:46:28 | Optimization | COLPAL | Strategy_3 | 30 | BUY | Rs.-6520.12 (33.3%) | Rs.-3606.33 (20.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 13:55:28 | Optimization | POWERINDIA | Strategy_3 | 1825 | BOTH | Rs.-145687.55 (34.8%) | Rs.-104025.10 (32.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 14:16:50 | Optimization | COLPAL | Strategy_3 | 180 | BUY | Rs.-67004.17 (18.8%) | Rs.-29379.24 (28.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 14:51:54 | Optimization | POWERINDIA | Strategy_3 | 1825 | BOTH | Rs.-256965.80 (37.6%) | Rs.-482488.40 (5.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed to generate positive PnL on training data. |
| 2026-06-18 15:48:49 | Walk-Forward (Rolling) | COLPAL | Strategy_3 | 360 | BUY | Rs.-124238.02 (11.6%) | Rs.-86367.30 (19.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-18 17:19:49 | Walk-Forward (Rolling) | POWERINDIA | Strategy_3 | 1825 | BUY | Rs.-15476.66 (29.7%) | Rs.-299754.71 (25.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-18 17:51:06 | Walk-Forward (Rolling) | POWERINDIA | Strategy_3 | 720 | BUY | Rs.-34800.24 (29.1%) | Rs.-168130.78 (25.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-18 20:03:06 | Walk-Forward (Rolling) | POWERINDIA | Strategy_3 | 720 | BUY | Rs.-36157.48 (36.0%) | Rs.-9738.05 (34.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-18 22:53:35 | Walk-Forward (Rolling) | COLPAL | Strategy_3 | 720 | BUY | Rs.4182.95 (34.1%) | Rs.-115957.35 (31.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-18 23:53:01 | Walk-Forward (Rolling) | ANGELONE | Strategy_3 | 720 | BUY | Rs.-379454.98 (19.6%) | Rs.-656881.31 (24.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-19 02:37:59 | Walk-Forward (Rolling) | GODREJPROP | Strategy_3 | 720 | BUY | Rs.-5659.52 (35.9%) | Rs.-18488.50 (36.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-19 04:36:06 | Walk-Forward (Rolling) | PAYTM | Strategy_3 | 720 | BUY | Rs.112699.08 (41.7%) | Rs.-7158.01 (35.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-19 06:22:39 | Walk-Forward (Rolling) | LAURUSLABS | Strategy_3 | 720 | BUY | Rs.-26751.12 (32.0%) | Rs.-164968.55 (28.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-19 09:10:12 | Walk-Forward (Rolling) | RECLTD | Strategy_3 | 720 | BUY | Rs.127800.44 (43.5%) | Rs.208217.67 (42.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined Out-of-Sample Walk-Forward results are profitable. |
| 2026-06-19 09:19:25 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.420365.74 (43.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 09:23:15 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.353243.53 (39.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 09:26:28 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.420365.74 (43.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 09:37:12 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.421224.44 (43.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 10:47:29 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.273787.21 (37.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 10:47:29 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.295521.13 (37.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 11:19:20 | Walk-Forward (Rolling) | RECLTD | Strategy_3 | 720 | BUY | Rs.58200.30 (35.5%) | Rs.86703.30 (34.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined Out-of-Sample Walk-Forward results are profitable. |
| 2026-06-19 11:30:28 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.140069.54 (36.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 11:31:29 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.295521.13 (37.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 11:32:20 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.196189.91 (34.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 11:33:45 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.295521.13 (37.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 12:17:57 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.247292.29 (34.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 12:26:48 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.247292.29 (34.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 12:30:40 | Backtest | RECLTD | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-79822.26 (28.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-19 12:36:23 | Backtest | RECLTD | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-12045.36 (32.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-19 15:39:11 | Walk-Forward (Rolling) | NATIONALUM | Strategy_3 | 720 | BUY | Rs.-97600.16 (29.0%) | Rs.-433756.10 (25.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-19 15:41:19 | Backtest | NATIONALUM | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-185689.09 (30.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-19 15:42:23 | Backtest | NATIONALUM | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-234045.01 (25.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-19 15:43:23 | Backtest | NATIONALUM | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-278715.57 (23.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-19 16:09:38 | Walk-Forward (Rolling) | COLPAL | Strategy_3 | 720 | BUY | Rs.4182.95 (34.1%) | Rs.-115957.35 (31.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-19 16:27:04 | Walk-Forward (Rolling) | GODREJPROP | Strategy_3 | 720 | BUY | Rs.-5659.52 (35.9%) | Rs.-18488.50 (36.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-19 18:03:38 | Backtest | RECLTD | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.8885.36 (33.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 18:54:42 | Backtest | RECLTD | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.8885.36 (33.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 20:59:12 | Walk-Forward (Rolling) | COLPAL | Strategy_3 | 720 | BUY | Rs.-31290.52 (32.4%) | Rs.-109194.44 (31.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-19 22:25:54 | Backtest | RECLTD | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.159268.97 (37.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-19 22:57:55 | Walk-Forward (Rolling) | GODREJPROP | Strategy_3 | 720 | BUY | Rs.-41001.36 (35.7%) | Rs.-129421.36 (35.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 00:42:14 | Walk-Forward (Rolling) | ABB | Strategy_3 | 720 | BUY | Rs.-13273.11 (33.7%) | Rs.-100960.95 (32.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 00:58:58 | Walk-Forward (Rolling) | GLENMARK | Strategy_3 | 720 | BUY | Rs.-35194.26 (34.3%) | Rs.-119278.26 (34.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 02:09:42 | Walk-Forward (Rolling) | ADANIENSOL | Strategy_3 | 720 | BUY | Rs.-19122.88 (34.9%) | Rs.-61301.30 (34.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 02:54:20 | Walk-Forward (Rolling) | BHARATFORG | Strategy_3 | 720 | BUY | Rs.-4610.04 (35.4%) | Rs.-44777.75 (33.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 03:36:06 | Walk-Forward (Rolling) | 360ONE | Strategy_3 | 720 | BUY | Rs.-505.63 (38.3%) | Rs.-28853.76 (34.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 03:52:04 | Walk-Forward (Rolling) | ADANIENSOL | Strategy_3 | 720 | BUY | Rs.-19122.88 (34.9%) | Rs.-61301.30 (34.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 05:01:59 | Walk-Forward (Rolling) | ADANIENT | Strategy_3 | 720 | BUY | Rs.-50827.88 (27.3%) | Rs.-221272.48 (26.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 05:02:00 | Walk-Forward (Rolling) | ADANIENT | Strategy_3 | 720 | BUY | Rs.-50827.88 (27.3%) | Rs.-221272.48 (26.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 06:30:35 | Walk-Forward (Rolling) | ADANIGREEN | Strategy_3 | 720 | BUY | Rs.-46100.80 (28.9%) | Rs.-134114.75 (28.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 06:42:01 | Walk-Forward (Rolling) | ADANIPORTS | Strategy_3 | 720 | BUY | Rs.-25897.37 (31.7%) | Rs.-149401.67 (29.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 06:56:15 | Walk-Forward (Rolling) | ADANIPORTS | Strategy_3 | 720 | BUY | Rs.-25897.37 (31.7%) | Rs.-149401.67 (29.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 08:42:50 | Walk-Forward (Rolling) | ABB | Strategy_3 | 720 | BUY | Rs.-18779.58 (32.8%) | Rs.-75992.41 (30.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 08:48:35 | Walk-Forward (Rolling) | APLAPOLLO | Strategy_3 | 720 | BUY | Rs.-5978.66 (37.6%) | Rs.-30135.33 (37.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 09:22:53 | Walk-Forward (Rolling) | ADANIENSOL | Strategy_3 | 720 | BUY | Rs.-25756.07 (33.2%) | Rs.-81630.55 (31.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 09:56:12 | Walk-Forward (Rolling) | ADANIENT | Strategy_3 | 720 | BUY | Rs.-53203.34 (28.8%) | Rs.-234960.78 (26.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-20 10:10:58 | Backtest | RECLTD | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.159268.97 (37.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-20 10:19:38 | Backtest | RECLTD | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.15555.77 (38.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-20 10:24:52 | Backtest | RECLTD | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.11171.62 (43.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-20 13:16:18 | Backtest | RECLTD | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-16431.62 (32.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-20 14:03:25 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-76895.56 (42.7%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-20 15:21:42 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-4644.42 (45.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-20 16:51:29 | Backtest | NIFTY | Strategy_3 | 720 | SELL | N/A (N/A) | Rs.93743.83 (47.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-20 16:53:41 | Backtest | NIFTY | Strategy_3 | 720 | SELL | N/A (N/A) | Rs.3324.05 (42.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-20 17:23:22 | Backtest | NIFTY | Strategy_3 | 720 | SELL | N/A (N/A) | Rs.233875.10 (39.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 00:55:48 | Walk-Forward (Rolling) | ANGELONE | Strategy_3 | 720 | BUY | Rs.-11292.30 (15.2%) | Rs.-29984.81 (14.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-21 03:16:06 | Walk-Forward (Rolling) | RVNL | Strategy_3 | 720 | BUY | Rs.1778.00 (28.3%) | Rs.-7893.37 (32.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-21 03:39:52 | Walk-Forward (Rolling) | HINDALCO | Strategy_3 | 720 | BUY | Rs.-18372.74 (29.7%) | Rs.-65136.54 (31.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-21 04:21:10 | Walk-Forward (Rolling) | PAYTM | Strategy_3 | 720 | BUY | Rs.-30039.12 (34.9%) | Rs.-143578.03 (26.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-21 11:53:08 | Walk-Forward (Rolling) | ANGELONE | Strategy_3 | 720 | BOTH | Rs.-17797.52 (24.2%) | Rs.-41726.48 (26.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-21 11:55:57 | Backtest | ANGELONE | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-289315.79 (23.1%) | sl_mult_buy=3, tp_mult_buy=15, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-06-21 12:00:40 | Backtest | ANGELONE | Strategy_3 | 720 | SELL | N/A (N/A) | Rs.38162.49 (33.6%) | sl_mult_buy=3, tp_mult_buy=15, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-06-21 12:21:43 | Backtest | PAYTM | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-248608.68 (29.9%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-21 12:22:59 | Walk-Forward (Rolling) | RVNL | Strategy_3 | 720 | BUY | Rs.15387.00 (47.3%) | Rs.-8660.96 (35.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-21 12:25:54 | Backtest | ANGELONE | Strategy_3 | 150 | BOTH | N/A (N/A) | Rs.-88308.78 (24.2%) | sl_mult_buy=3, tp_mult_buy=15, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-06-21 13:12:59 | Backtest | NIFTY | Strategy_3 | 720 | SELL | N/A (N/A) | Rs.226527.97 (38.6%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 13:18:15 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-13291.75 (45.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-21 14:55:36 | Walk-Forward (Rolling) | NIFTY | Strategy_3 | 720 | BUY | Rs.-1808.00 (34.6%) | Rs.-36041.95 (33.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-21 15:00:28 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.85661.47 (43.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 15:02:00 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-6342.28 (33.5%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-21 15:03:08 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.-14695.04 (37.3%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | UNPROFITABLE |
| 2026-06-21 15:03:49 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.85661.47 (43.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 15:11:30 | Backtest | NIFTY | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.85661.47 (43.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 15:22:13 | Backtest | NIFTY | Strategy_3 | 720 | BOTH | N/A (N/A) | Rs.192735.59 (41.1%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 15:28:32 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.102248.40 (44.2%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 15:29:14 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.144881.68 (38.9%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 15:40:06 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.178948.70 (44.7%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 15:40:39 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 18:29:15 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 18:33:25 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.178948.70 (44.7%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 19:16:38 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.114957.38 (47.1%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 20:03:26 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.232797.57 (46.4%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 20:06:26 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.815475.33 (48.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 20:20:16 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.354663.54 (49.2%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-21 20:21:02 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.61086.80 (48.8%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-22 09:07:14 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.582933.98 (45.7%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-22 09:33:47 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.147471.24 (44.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-22 09:34:08 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-22 10:19:23 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.178948.70 (44.7%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-22 10:19:36 | Backtest | BANKNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-50681.79 (37.5%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-22 10:20:23 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.146046.35 (44.8%) | sl_mult_buy=1, tp_mult_buy=5, trailing_mult_buy=0.3, sl_m... | PROFITABLE |
| 2026-06-22 10:53:29 | Walk-Forward (Rolling) | BANKNIFTY | Strategy_3 | 365 | BUY | Rs.-54970.14 (26.7%) | Rs.-25562.86 (32.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-22 12:41:49 | Walk-Forward (Rolling) | SENSEX | Strategy_3 | 365 | BUY | Rs.-13097.11 (28.0%) | Rs.-15260.91 (28.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined Out-of-Sample Walk-Forward results lose money. |
| 2026-06-22 15:41:15 | Optimization | SENSEX | Strategy_3 | 30 | BOTH | Rs.-2264.28 (36.0%) | Rs.-1965.15 (36.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-06-22 15:42:55 | Optimization | NIFTY | Strategy_3 | 30 | BOTH | Rs.10899.63 (48.1%) | Rs.-4455.63 (26.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -81.8%). |
| 2026-06-22 15:51:15 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-22 15:51:43 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.2509.94 (46.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-22 16:11:09 | Walk-Forward (Rolling) | SENSEX | Strategy_3 | 365 | BOTH | Rs.-27019.08 (24.1%) | Rs.-33888.70 (18.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-22 17:01:39 | Optimization | RVNL | Strategy_3 | 30 | BOTH | Rs.581.51 (57.1%) | Rs.3348.36 (77.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both splits (WFE: 1151.6%). |
| 2026-06-22 17:38:51 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-22 18:06:37 | Walk-Forward (Rolling) | BSE | Strategy_3 | 365 | BUY | Rs.-19424.72 (36.8%) | Rs.-43048.98 (33.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-22 18:30:55 | Walk-Forward (Rolling) | BSE | Strategy_3 | 365 | BUY | Rs.-36836.04 (33.7%) | Rs.-56413.51 (31.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-22 21:27:58 | Walk-Forward (Rolling) | RVNL | Strategy_3 | 365 | BUY | Rs.-55853.33 (28.4%) | Rs.15363.31 (37.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 0.0%). |
| 2026-06-22 21:53:15 | Walk-Forward (Rolling) | RVNL | Strategy_3 | 720 | BUY | Rs.-30348.10 (31.4%) | Rs.35968.37 (31.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 0.0%). |
| 2026-06-23 08:16:29 | Backtest | RVNL | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-110423.01 (19.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-23 08:19:08 | Backtest | RVNL | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-164326.49 (27.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-23 08:30:50 | Backtest | RVNL | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-63537.95 (26.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-23 08:40:34 | Backtest | RVNL | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-63537.95 (26.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-23 08:40:50 | Backtest | RVNL | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-96940.47 (24.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-23 10:28:21 | Backtest | HDFCBANK | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-151677.32 (22.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-23 11:14:55 | Backtest | HDFCBANK | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-36539.94 (32.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-23 12:30:41 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.108253.08 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 12:31:30 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 12:33:11 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.178948.70 (44.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:12:59 | Backtest | HDFCBANK | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.-72243.47 (38.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-23 13:23:13 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.140985.63 (44.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:24:10 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.146046.35 (44.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:25:13 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.152079.70 (47.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:25:46 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.166102.09 (46.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:26:19 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.177813.87 (52.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:26:59 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:28:44 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.185505.71 (45.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:29:19 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.168334.49 (44.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:30:48 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.178948.70 (44.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:31:18 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.187980.22 (42.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 13:58:22 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 14:05:28 | Backtest | SENSEX | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.-7856.80 (46.8%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-23 14:10:02 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.143397.33 (50.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 14:10:30 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.130366.90 (44.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 14:15:08 | Backtest | SENSEX | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.42755.95 (44.4%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 14:17:31 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.1311678.46 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 14:21:20 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.187980.22 (42.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 14:25:18 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.114524.66 (40.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 14:58:24 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.17576.98 (36.0%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:03:24 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.99866.77 (48.0%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:09:46 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.121028.12 (36.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:17:47 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.110727.35 (30.5%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:28:04 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.115108.83 (31.5%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:28:58 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.98957.69 (32.5%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:29:29 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.121028.12 (36.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:29:53 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.118291.57 (36.9%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:30:27 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.91105.46 (42.5%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:30:53 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.129621.78 (32.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:31:36 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.129744.38 (41.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 15:31:54 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 15:36:08 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.96491.03 (29.7%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:37:46 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.129621.78 (32.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:38:12 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.118198.62 (31.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:38:47 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.129621.78 (32.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:39:18 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.132603.59 (33.3%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:39:59 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.119961.15 (32.0%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 15:40:20 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.132603.59 (33.3%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 16:32:23 | Backtest | SENSEX | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.77209.83 (29.0%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 16:40:57 | Backtest | SENSEX | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.86157.17 (33.3%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 16:44:24 | Backtest | SENSEX | Strategy_3 | 720 | BUY | N/A (N/A) | Rs.77972.01 (28.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 16:50:39 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.72612.20 (45.9%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 16:51:03 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.115109.48 (34.9%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 16:51:53 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.95319.78 (30.7%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 16:52:16 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.132603.59 (33.3%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 17:43:39 | Backtest | SENSEX | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.145081.18 (40.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 18:05:15 | Backtest | SENSEX | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.165469.80 (38.7%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 18:11:54 | Backtest | SENSEX | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.185738.46 (39.4%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 18:39:37 | Backtest | SENSEX | Strategy_3 | 60 | SELL | N/A (N/A) | Rs.21216.59 (29.4%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 18:43:51 | Backtest | SENSEX | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.185738.46 (39.4%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-23 18:44:15 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 18:55:27 | Walk-Forward (Rolling) | NIFTY | Strategy_3 | 365 | BUY | Rs.10487.54 (30.7%) | Rs.22566.13 (29.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 212.8%). |
| 2026-06-23 19:03:12 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.109615.94 (34.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:03:43 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.120536.58 (36.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:04:44 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.109615.94 (34.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:05:36 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.153709.66 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:10:55 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.152120.50 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:13:03 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.3706.97 (30.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:13:23 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.47095.27 (36.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:13:51 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.68627.16 (42.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:14:10 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.45421.14 (42.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:14:31 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.152120.50 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:14:58 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.81221.07 (51.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:15:34 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.152120.50 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 19:15:49 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.164686.16 (41.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 20:16:28 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.120143.34 (35.1%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-23 20:36:19 | Walk-Forward (Rolling) | BSE | Strategy_3 | 365 | BUY | Rs.-11875.20 (31.5%) | Rs.76841.61 (33.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 0.0%). |
| 2026-06-23 20:38:12 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.278475.22 (29.7%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-23 20:40:06 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.161816.37 (43.9%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-23 20:40:41 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.120143.34 (35.1%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-23 20:41:11 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.278475.22 (29.7%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-23 20:58:28 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.122205.45 (40.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 21:35:03 | Backtest | BSE | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.314228.76 (38.1%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-23 21:39:05 | Backtest | BSE | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.352600.99 (40.8%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-23 21:42:28 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.277895.63 (31.5%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-23 21:51:16 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.164686.19 (41.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-23 23:19:22 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.78737.54 (28.7%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 04:41:13 | Walk-Forward (Rolling) | MIDCPNIFTY | Strategy_3 | 730 | BUY | Rs.134703.17 (35.6%) | Rs.119152.90 (34.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 29.2%). |
| 2026-06-24 07:33:52 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.275529.81 (41.5%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 07:35:10 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.163723.01 (34.0%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 07:35:50 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.275529.81 (41.5%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 07:40:04 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.421307.77 (44.7%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 07:57:28 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.163723.01 (34.0%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 08:23:52 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.344538.99 (46.4%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 08:25:39 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.297798.28 (37.1%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 09:48:22 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.-61892.21 (22.6%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-24 14:02:50 | Walk-Forward (Rolling) | MIDCPNIFTY | Strategy_3 | 730 | SELL | Rs.27113.81 (39.2%) | Rs.88465.27 (39.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 107.6%). |
| 2026-06-24 15:34:35 | Backtest | MIDCPNIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.-136560.14 (36.6%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-24 19:11:01 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.277895.63 (31.5%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-24 19:43:03 | Backtest | BHARATFORG | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-134856.22 (25.7%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-25 01:16:42 | Walk-Forward (Rolling) | BHARATFORG | Strategy_3 | 730 | BUY | Rs.-63545.16 (25.4%) | Rs.-56693.93 (28.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 09:10:33 | Backtest | BSE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.870509.23 (30.3%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-26 09:10:41 | Backtest | BHARATFORG | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-282114.49 (26.1%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:10:48 | Backtest | POWERINDIA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-311632.77 (16.2%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:10:55 | Backtest | PERSISTENT | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-356482.48 (28.3%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:11:02 | Backtest | COLPAL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-521257.05 (10.8%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:11:11 | Backtest | ANGELONE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.130197.40 (38.5%) | sl_mult_buy=3, tp_mult_buy=15, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-06-26 09:11:20 | Backtest | GODREJPROP | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-64847.09 (36.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:11:22 | Backtest | PAYTM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-90293.54 (29.2%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:11:35 | Backtest | LAURUSLABS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.476479.84 (41.3%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:11:44 | Backtest | RECLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-468433.55 (16.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:12:02 | Backtest | ABCAPITAL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.250415.48 (41.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:12:17 | Backtest | IREDA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-352039.41 (26.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:12:27 | Backtest | NATIONALUM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.18007.80 (32.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:12:37 | Backtest | UNIONBANK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-119982.10 (32.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:12:48 | Backtest | CANBK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-32925.76 (33.9%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:12:59 | Backtest | GMRAIRPORT | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-217078.39 (34.1%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:13:10 | Backtest | PNB | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-71046.34 (34.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:13:19 | Backtest | SUZLON | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.33229.24 (36.5%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:13:29 | Backtest | PAGEIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-190371.83 (33.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:13:42 | Backtest | APOLLOHOSP | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-393843.94 (26.8%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:13:53 | Backtest | MCX | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.151010.81 (39.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:14:07 | Backtest | KEI | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-84572.42 (37.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:14:19 | Backtest | GLENMARK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-220772.34 (32.5%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:14:35 | Backtest | UNITDSPR | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-139655.59 (33.4%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:14:48 | Backtest | PATANJALI | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-29686.85 (34.5%) | sl_mult_buy=2, tp_mult_buy=15, trailing_mult_buy=1.5, sl_... | UNPROFITABLE |
| 2026-06-26 09:15:03 | Backtest | AUBANK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.7274.02 (34.6%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:15:19 | Backtest | UPL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-58908.82 (31.9%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:15:34 | Backtest | NTPC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-167863.47 (30.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:15:49 | Backtest | LTF | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.13552.28 (33.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:16:01 | Backtest | RBLBANK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.89759.24 (35.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:16:13 | Backtest | 360ONE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.4071.05 (37.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:16:41 | Backtest | ABB | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.189342.77 (13.4%) | sl_mult_buy=3, tp_mult_buy=20, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-06-26 09:16:53 | Backtest | ADANIENSOL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.67536.07 (37.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:17:08 | Backtest | ADANIENT | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-65019.66 (31.9%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:17:20 | Backtest | ADANIGREEN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.64245.12 (37.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:17:32 | Backtest | ADANIPORTS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-111173.77 (34.0%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:17:40 | Backtest | ALKEM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-647239.75 (17.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:17:48 | Backtest | AMBER | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-321733.35 (28.2%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:17:56 | Backtest | AMBUJACEM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-461808.66 (22.4%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:18:07 | Backtest | APLAPOLLO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-121802.91 (34.6%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:18:19 | Backtest | ASHOKLEY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-88021.19 (34.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:18:32 | Backtest | ASIANPAINT | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-266187.49 (29.8%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:18:44 | Backtest | ASTRAL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-161067.73 (31.1%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:18:57 | Backtest | AUROPHARMA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-266034.58 (30.1%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:19:09 | Backtest | AXISBANK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-519741.37 (25.0%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:19:21 | Backtest | BAJAJ-AUTO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-198844.79 (32.0%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:19:35 | Backtest | BAJAJFINSV | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-140035.15 (28.7%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:19:46 | Backtest | BAJFINANCE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-376569.03 (30.3%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:19:58 | Backtest | BANDHANBNK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-51696.99 (35.1%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:20:10 | Backtest | BANKBARODA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-209956.23 (32.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:20:20 | Backtest | BANKINDIA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-112886.48 (32.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:20:31 | Backtest | BDL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-88733.54 (33.5%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:20:44 | Backtest | BEL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-190336.00 (30.4%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:20:55 | Backtest | BHARTIARTL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-264797.63 (30.7%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:21:03 | Backtest | BHEL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-624783.22 (0.0%) | sl_mult_buy=0, tp_mult_buy=0, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-26 09:21:13 | Backtest | BIOCON | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-234470.57 (28.9%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:21:23 | Backtest | BLUESTARCO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.124484.25 (39.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:21:35 | Backtest | BOSCHLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-109219.31 (33.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:21:43 | Backtest | BPCL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-606745.79 (0.0%) | sl_mult_buy=4, tp_mult_buy=0, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-26 09:21:58 | Backtest | BRITANNIA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-334257.22 (30.1%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:22:09 | Backtest | CAMS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-28335.48 (33.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:24:15 | Backtest | CGPOWER | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.143555.77 (41.6%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-26 09:24:26 | Backtest | CHOLAFIN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-198073.61 (30.1%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:24:43 | Backtest | CIPLA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-339934.32 (28.3%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:24:54 | Backtest | COALINDIA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-221410.72 (30.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:25:05 | Backtest | COFORGE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-4661.10 (33.8%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:25:16 | Backtest | CONCOR | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-431914.25 (31.7%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-26 09:25:25 | Backtest | CROMPTON | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-131166.60 (32.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:25:34 | Backtest | CUMMINSIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-59094.01 (34.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:25:44 | Backtest | DABUR | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-333315.69 (34.2%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-26 09:25:57 | Backtest | DALBHARAT | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-121812.49 (31.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:26:11 | Backtest | DELHIVERY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-242722.61 (35.7%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:26:23 | Backtest | DIVISLAB | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-190498.13 (29.5%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:26:36 | Backtest | DIXON | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-148738.12 (31.4%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:26:48 | Backtest | DLF | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-186686.79 (32.0%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:26:57 | Backtest | DMART | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-174851.36 (30.0%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:27:08 | Backtest | DRREDDY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-365006.33 (30.5%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:27:20 | Backtest | EICHERMOT | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-101654.21 (32.0%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:27:29 | Backtest | ETERNAL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.64501.53 (38.2%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:27:40 | Backtest | EXIDEIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-114922.86 (30.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:27:51 | Backtest | FEDERALBNK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-70781.33 (33.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:28:01 | Backtest | FORTIS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-138940.26 (36.2%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:28:11 | Backtest | GAIL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-73656.41 (32.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:28:22 | Backtest | GODREJCP | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-117252.13 (35.0%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:28:34 | Backtest | GRASIM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-282095.20 (28.9%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:28:45 | Backtest | HAL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-272884.48 (29.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:28:59 | Backtest | HAVELLS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-266735.21 (32.4%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:29:05 | Backtest | HCLTECH | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-99486.80 (30.9%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:29:14 | Backtest | HDFCAMC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-67786.44 (35.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:29:27 | Backtest | HDFCBANK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-240730.12 (29.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:29:40 | Backtest | HDFCLIFE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-320832.52 (28.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:30:04 | Backtest | HEROMOTOCO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.16002.44 (34.6%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:30:27 | Backtest | HINDALCO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-216733.82 (32.6%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:30:54 | Backtest | HINDPETRO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-203917.77 (34.4%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:31:20 | Backtest | HINDUNILVR | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-141343.17 (29.8%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:31:44 | Backtest | HINDZINC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-12688.48 (33.3%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:32:05 | Backtest | HUDCO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.46787.70 (35.7%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:32:25 | Backtest | ICICIBANK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-441721.63 (27.4%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:32:41 | Backtest | ICICIGI | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.2625.97 (35.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:32:45 | Backtest | ICICIPRULI | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-16906.93 (39.5%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:32:56 | Backtest | IDEA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.145178.43 (28.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:33:10 | Backtest | IDFCFIRSTB | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-95985.19 (34.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:33:23 | Backtest | IEX | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.5795.39 (34.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:33:36 | Backtest | INDHOTEL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.104365.75 (38.6%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:33:50 | Backtest | INDIANB | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-87552.11 (32.5%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:34:11 | Backtest | INDIGO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-26994.62 (35.3%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:34:31 | Backtest | INDUSINDBK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-13646.94 (36.6%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:34:48 | Backtest | INDUSTOWER | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-252339.87 (26.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:35:09 | Backtest | INFY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-260915.57 (28.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:35:22 | Backtest | INOXWIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.45310.07 (35.6%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-26 09:35:42 | Backtest | IOC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-88544.85 (32.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:36:09 | Backtest | IRCTC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-233860.47 (26.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:36:33 | Backtest | IRFC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-49483.76 (31.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:36:56 | Backtest | ITC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-333049.88 (26.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:37:09 | Backtest | JINDALSTEL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-174384.08 (31.7%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:37:22 | Backtest | JIOFIN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-89611.69 (33.4%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:37:37 | Backtest | JSWENERGY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-95965.08 (29.9%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:37:53 | Backtest | JSWSTEEL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-320952.12 (29.4%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:38:13 | Backtest | JUBLFOOD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-433657.84 (30.6%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-06-26 09:38:26 | Backtest | KALYANKJIL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.15445.06 (32.3%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:38:37 | Backtest | KAYNES | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.72995.28 (35.6%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:38:47 | Backtest | KFINTECH | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-34317.17 (35.1%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:39:01 | Backtest | KOTAKBANK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-261653.31 (29.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:39:12 | Backtest | KPITTECH | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-93453.13 (33.1%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:39:23 | Backtest | LICHSGFIN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-39737.79 (31.2%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:39:32 | Backtest | LICI | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-84716.91 (29.0%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:39:42 | Backtest | LODHA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-113199.96 (30.6%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:39:55 | Backtest | LT | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-188344.97 (29.7%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:40:09 | Backtest | LTIM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-198056.00 (32.6%) | sl_mult_buy=2, tp_mult_buy=15, trailing_mult_buy=1.5, sl_... | UNPROFITABLE |
| 2026-06-26 09:40:21 | Backtest | LUPIN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-313274.17 (31.1%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:40:34 | Backtest | M&M | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.3829.14 (32.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:40:45 | Backtest | MANAPPURAM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.3455.19 (35.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:40:55 | Backtest | MANKIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.39834.97 (36.8%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:41:07 | Backtest | MARICO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-323850.38 (30.7%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:41:19 | Backtest | MARUTI | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-212051.54 (31.1%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:41:31 | Backtest | MAXHEALTH | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-189221.84 (34.1%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:41:42 | Backtest | MAZDOCK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-106769.02 (34.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:41:54 | Backtest | MFSL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-70129.43 (35.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:44:00 | Backtest | MPHASIS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-6148.71 (34.8%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:44:12 | Backtest | MUTHOOTFIN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-53809.25 (35.2%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:44:24 | Backtest | NAUKRI | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-57517.68 (33.5%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:44:34 | Backtest | NBCC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.105416.16 (35.0%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:44:47 | Backtest | NESTLEIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-245620.90 (32.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:44:58 | Backtest | NHPC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-137896.12 (33.6%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:45:10 | Backtest | NMDC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-55016.21 (30.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:45:20 | Backtest | NUVAMA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.40746.69 (34.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:45:31 | Backtest | NYKAA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-71722.84 (34.7%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:45:42 | Backtest | OBEROIRLTY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-157379.53 (31.6%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:45:54 | Backtest | OFSS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.56236.64 (35.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:46:05 | Backtest | OIL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.25154.23 (34.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:46:17 | Backtest | ONGC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-139450.74 (33.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:46:30 | Backtest | PETRONET | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-20020.00 (33.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:46:41 | Backtest | PFC | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.39717.94 (36.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:46:50 | Backtest | PGEL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.29623.87 (36.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:47:03 | Backtest | PHOENIXLTD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.7225.44 (37.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:47:18 | Backtest | PIDILITIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-172954.79 (29.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:47:29 | Backtest | PIIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-172265.25 (31.7%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:47:41 | Backtest | PNBHOUSING | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.112709.83 (38.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:47:51 | Backtest | POLICYBZR | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.175858.48 (40.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:48:03 | Backtest | POLYCAB | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.25294.00 (33.8%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:48:17 | Backtest | POWERGRID | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-213012.84 (30.8%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:48:25 | Backtest | PPLPHARMA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-48847.52 (29.0%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:48:36 | Backtest | PRESTIGE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.149192.63 (41.2%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:48:50 | Backtest | RELIANCE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-454405.01 (28.4%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:48:59 | Backtest | RVNL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-99638.70 (33.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:49:09 | Backtest | SAIL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-147949.80 (32.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:49:18 | Backtest | SAMMAANCAP | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.78376.23 (33.2%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:49:29 | Backtest | SBICARD | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-105687.18 (33.2%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:49:40 | Backtest | SBILIFE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-226078.40 (29.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:49:50 | Backtest | SBIN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-149397.73 (29.2%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:50:02 | Backtest | SHREECEM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-247078.95 (29.3%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:50:14 | Backtest | SHRIRAMFIN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-78395.12 (33.7%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:50:27 | Backtest | SIEMENS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-43972.25 (34.9%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:50:38 | Backtest | SOLARINDS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.15444.04 (34.0%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:50:49 | Backtest | SONACOMS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-114062.53 (31.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:51:01 | Backtest | SRF | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-175521.22 (30.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:51:14 | Backtest | SUNPHARMA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-236393.81 (31.6%) | sl_mult_buy=1, tp_mult_buy=13, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:51:24 | Backtest | SUPREMEIND | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.54786.91 (34.8%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-26 09:51:36 | Backtest | SYNGENE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-110829.87 (31.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:51:48 | Backtest | TATACONSUM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-175728.05 (32.4%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:52:00 | Backtest | TATAELXSI | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-122983.01 (32.7%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:52:13 | Backtest | TATAPOWER | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-17011.78 (33.8%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:52:26 | Backtest | TATASTEEL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-145787.56 (30.1%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:52:36 | Backtest | TATATECH | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-191520.94 (30.7%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:52:49 | Backtest | TCS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-344589.38 (25.7%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-06-26 09:53:01 | Backtest | TECHM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-89733.41 (33.9%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:53:13 | Backtest | TIINDIA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.107102.53 (39.2%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-26 09:53:26 | Backtest | TITAN | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-131633.19 (32.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:53:38 | Backtest | TMPV | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-143516.79 (32.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:53:51 | Backtest | TORNTPHARM | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-88137.93 (32.7%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:54:01 | Backtest | TORNTPOWER | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.8109.53 (35.2%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:54:14 | Backtest | TRENT | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.135296.49 (36.4%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:54:28 | Backtest | TVSMOTOR | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-113071.10 (34.5%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:54:40 | Backtest | ULTRACEMCO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-174963.47 (31.6%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:54:49 | Backtest | UNOMINDA | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.37666.24 (36.3%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-06-26 09:54:59 | Backtest | VBL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-115693.64 (35.3%) | sl_mult_buy=1, tp_mult_buy=11, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:55:10 | Backtest | VEDL | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-95224.99 (31.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:55:22 | Backtest | VOLTAS | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.54871.46 (36.3%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-06-26 09:55:32 | Backtest | WIPRO | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-200625.16 (30.0%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:55:40 | Backtest | YESBANK | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-42502.41 (26.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-06-26 09:55:51 | Backtest | ZYDUSLIFE | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.-444966.72 (27.9%) | sl_mult_buy=2, tp_mult_buy=15, trailing_mult_buy=1.5, sl_... | UNPROFITABLE |
| 2026-06-26 11:01:28 | Walk-Forward (Rolling) | BSE | Strategy_3 | 730 | BUY | Rs.23129.43 (25.6%) | Rs.-11763.65 (25.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: -16.7%). |
| 2026-06-26 11:26:47 | Walk-Forward (Rolling) | BHARATFORG | Strategy_3 | 730 | BUY | Rs.-138477.14 (22.9%) | Rs.-373013.21 (24.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 12:12:10 | Walk-Forward (Rolling) | POWERINDIA | Strategy_3 | 730 | BUY | Rs.-11696.48 (28.1%) | Rs.-97975.68 (23.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 12:38:27 | Walk-Forward (Rolling) | PERSISTENT | Strategy_3 | 730 | BUY | Rs.-89878.71 (18.2%) | Rs.-237794.82 (18.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 13:07:43 | Walk-Forward (Rolling) | COLPAL | Strategy_3 | 730 | BUY | Rs.-122205.56 (23.1%) | Rs.-335316.16 (21.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 13:34:33 | Walk-Forward (Rolling) | ANGELONE | Strategy_3 | 730 | BUY | Rs.-125008.40 (19.8%) | Rs.-402756.04 (20.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 14:03:17 | Walk-Forward (Rolling) | GODREJPROP | Strategy_3 | 730 | BUY | Rs.-109871.21 (17.0%) | Rs.-189817.62 (20.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 14:08:21 | Walk-Forward (Rolling) | PAYTM | Strategy_3 | 730 | BUY | Rs.-52020.10 (25.5%) | Rs.-17376.32 (33.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 14:38:30 | Walk-Forward (Rolling) | LAURUSLABS | Strategy_3 | 730 | BUY | Rs.-107325.50 (11.7%) | Rs.-393708.95 (11.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-26 15:10:03 | Walk-Forward (Rolling) | RECLTD | Strategy_3 | 730 | BUY | Rs.-113654.98 (20.4%) | Rs.-227511.58 (22.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-06-28 21:35:48 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.173954.43 (42.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:02:24 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.139787.62 (46.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:03:04 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.162043.11 (41.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:06:09 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.23643.98 (44.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:06:40 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.162043.11 (41.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:07:30 | Backtest | NIFTY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.143148.24 (34.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:08:42 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.173954.43 (42.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:09:14 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.130535.57 (33.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:09:48 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.173954.43 (42.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:15:37 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.176276.36 (42.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:16:01 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.120338.94 (44.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-28 22:16:42 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.173954.43 (42.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 12:59:30 | Backtest | NIFTY | Strategy_3 | 1095 | BUY | N/A (N/A) | Rs.128854.22 (36.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 13:09:20 | Backtest | NIFTY | Strategy_3 | 1095 | BUY | N/A (N/A) | Rs.128854.22 (36.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 13:31:12 | Backtest | NIFTY | Strategy_3 | 1095 | SELL | N/A (N/A) | Rs.378553.60 (40.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 13:36:41 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.173954.43 (42.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 13:37:47 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.175175.29 (42.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 13:59:00 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.80609.87 (54.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 13:59:40 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.127015.94 (49.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:02:36 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.147278.15 (40.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:03:23 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.135316.97 (42.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:03:56 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.175175.29 (42.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:04:33 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.47783.94 (42.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:05:00 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.34438.98 (40.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:05:38 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.114288.08 (28.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:06:18 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.107118.78 (28.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:06:55 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.113577.46 (37.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:16:29 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.150232.06 (43.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:17:01 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.175175.29 (42.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 14:50:21 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.111427.58 (38.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:15:19 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.175175.29 (42.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:32:41 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.139567.03 (45.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:35:56 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.41942.32 (37.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:36:41 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.107953.95 (38.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:37:12 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.242633.77 (44.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:40:53 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.258641.97 (45.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:42:58 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.242633.77 (44.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:43:50 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.275221.13 (48.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:44:18 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.272133.41 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:45:23 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.184735.96 (52.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:47:12 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.184735.96 (52.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 15:48:20 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.272133.41 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:33:05 | Backtest | NIFTY | Strategy_3 | 1095 | BUY | N/A (N/A) | Rs.209959.24 (38.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:39:09 | Backtest | NIFTY | Strategy_3 | 1095 | SELL | N/A (N/A) | Rs.275342.11 (43.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:40:04 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.272133.41 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:40:20 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.145882.46 (32.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:40:44 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.224166.50 (42.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:41:17 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.242932.85 (50.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:41:47 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.229647.25 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:42:10 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.136199.13 (44.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:42:42 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.234402.14 (44.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:46:02 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.272133.41 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:46:31 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.8390574.24 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:48:26 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.272133.41 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:56:24 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.272133.41 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:56:41 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.131959.27 (45.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:59:20 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.180373.53 (24.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 16:59:52 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.239182.63 (39.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 17:00:21 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.272133.41 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 18:01:55 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.125204.04 (60.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:00:48 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.100151.93 (45.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:03:36 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.271805.11 (50.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:04:06 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.228320.77 (49.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:04:30 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.244870.80 (49.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:04:52 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.271805.11 (50.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:08:46 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.245049.21 (57.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:09:17 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.139371.77 (49.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:09:43 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.241277.98 (53.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:10:11 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.250864.48 (52.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:10:51 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.271805.11 (50.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:11:24 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.272133.41 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:11:54 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.265203.99 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:12:24 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.247999.32 (53.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:15:31 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.137467.48 (50.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:16:57 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.74521.39 (48.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:17:41 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.247999.32 (53.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:18:13 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.200043.73 (53.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:19:09 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.247999.32 (53.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:20:56 | Backtest | NIFTY | Strategy_3 | 1095 | BUY | N/A (N/A) | Rs.227775.45 (41.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:22:13 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.247999.32 (53.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:22:49 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.271805.11 (50.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:24:46 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.200043.73 (53.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:25:39 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.247999.32 (53.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:58:22 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.234774.13 (45.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:59:10 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.196350.31 (48.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 19:59:47 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.221429.39 (45.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 21:40:21 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.265875.31 (50.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 22:10:59 | Walk-Forward (Rolling) | NIFTY | Strategy_3 | 365 | BUY | Rs.179263.58 (61.1%) | Rs.224757.35 (60.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 124.0%). |
| 2026-06-29 22:16:58 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.330474.35 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 22:19:44 | Backtest | NIFTY | Strategy_3 | 730 | BUY | N/A (N/A) | Rs.267569.46 (43.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 22:37:53 | Backtest | NIFTY | Strategy_3 | 1095 | BUY | N/A (N/A) | Rs.260369.11 (42.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 22:40:49 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.296947.44 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 22:45:04 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.330474.35 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 22:57:28 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.310795.53 (52.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-29 23:00:18 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.123994.92 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 08:42:15 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.186546.95 (53.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 08:48:38 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.162848.40 (47.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 08:50:42 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.149569.45 (52.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 08:51:12 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.186546.95 (53.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 09:54:40 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.69675.89 (32.7%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-30 11:20:03 | Walk-Forward (Rolling) | SENSEX | Strategy_3 | 365 | BUY | Rs.63096.41 (36.3%) | Rs.25128.37 (30.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 39.4%). |
| 2026-06-30 11:34:42 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.60337.68 (14.4%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-30 11:37:42 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.247340.82 (28.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 11:39:56 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.330474.35 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 13:12:10 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.103800.68 (17.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 13:12:50 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.328509.79 (41.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 13:13:23 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.278797.11 (34.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 13:13:51 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.330474.35 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 13:15:28 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.330474.35 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 13:16:15 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.252809.42 (45.6%) | sl_mult_buy=3, tp_mult_buy=2, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-06-30 13:16:54 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.330474.35 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 13:17:32 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.265875.31 (50.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 13:25:27 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.265875.31 (50.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 14:32:27 | Backtest | NIFTY | Strategy_3 | 25 | BUY | N/A (N/A) | Rs.14740.46 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:28:38 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.258018.09 (50.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:30:21 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.258018.09 (50.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:31:26 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.297151.19 (55.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:48:55 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.296773.05 (55.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:50:30 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.313114.40 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:51:31 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.172147.06 (52.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:52:22 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.149865.56 (48.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:53:04 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.136387.18 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:54:03 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.155185.98 (51.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:54:46 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.146072.65 (57.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:56:35 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.182388.45 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:57:13 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.170146.05 (44.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 15:58:10 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.182388.45 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:00:03 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.297916.60 (30.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:00:41 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.313114.40 (49.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:01:43 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.307565.19 (48.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:02:29 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.316838.26 (47.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:03:03 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.286962.93 (43.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:03:49 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.300641.06 (43.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:04:54 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.316838.26 (47.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:15:54 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.239783.60 (56.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:29:09 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.258018.09 (50.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:33:47 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.252388.14 (45.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:34:20 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.254317.83 (50.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:35:02 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.269351.68 (47.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:35:28 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.276419.89 (45.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:36:17 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.297058.00 (48.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:40:12 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.283489.36 (44.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:42:20 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.297058.00 (48.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 16:52:37 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.320380.75 (53.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-06-30 17:02:03 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.182388.45 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 08:55:33 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.320380.72 (53.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:06:35 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.259386.64 (53.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:07:34 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.259386.64 (53.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:11:52 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.226719.91 (49.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:12:29 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.217964.09 (46.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:12:52 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.259386.64 (53.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:13:59 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.116038.24 (48.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:16:00 | Backtest | NIFTY | Strategy_3 | 550 | SELL | N/A (N/A) | Rs.153892.98 (46.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:16:33 | Backtest | NIFTY | Strategy_3 | 550 | BUY | N/A (N/A) | Rs.219274.93 (47.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 09:19:15 | Backtest | NIFTY | Strategy_3 | 550 | BUY | N/A (N/A) | Rs.281855.85 (47.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 10:56:36 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.235082.74 (45.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 12:36:38 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.158764.61 (41.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 12:39:01 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.5317.88 (35.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 13:23:27 | Walk-Forward (Rolling) | NIFTY | Strategy_3 | 365 | BUY | Rs.98222.56 (35.3%) | Rs.32307.68 (28.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 32.9%). |
| 2026-07-01 13:28:25 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.5317.88 (35.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 13:29:16 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.104747.02 (25.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 13:29:56 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-29777.44 (36.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-01 13:30:29 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.259386.64 (53.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 13:31:02 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.199429.11 (33.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 13:31:24 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.110163.73 (42.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 13:31:57 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.116038.24 (48.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:16:52 | Walk-Forward (Rolling) | NIFTY | Strategy_3 | 550 | SELL | Rs.52028.33 (62.7%) | Rs.81364.54 (58.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 76.5%). |
| 2026-07-01 14:27:37 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.122145.07 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:28:11 | Backtest | NIFTY | Strategy_3 | 550 | SELL | N/A (N/A) | Rs.149911.31 (50.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:29:36 | Backtest | NIFTY | Strategy_3 | 550 | SELL | N/A (N/A) | Rs.201667.56 (48.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:30:31 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.172243.62 (48.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:32:18 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.190111.25 (34.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:33:43 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.190111.25 (34.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:38:06 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.155692.89 (50.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:38:48 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.109923.28 (51.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:50:59 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.320380.72 (53.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:52:58 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.155692.89 (50.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:54:57 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.320380.72 (53.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:57:00 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.259386.64 (53.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 14:57:23 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.320380.72 (53.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 15:00:38 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.140074.50 (60.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 15:01:29 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.166261.36 (48.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 15:02:02 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.172243.62 (48.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 15:02:36 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.170810.54 (47.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 15:03:13 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.172243.62 (48.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-01 15:06:08 | Backtest | RECLTD | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-166627.71 (24.5%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-07-01 15:06:53 | Backtest | RECLTD | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-229061.87 (10.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-07-01 15:07:33 | Backtest | RECLTD | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-229061.87 (10.9%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-07-01 15:11:35 | Backtest | RECLTD | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.29873.08 (29.6%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-01 19:12:10 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.252858.63 (25.5%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-07-01 19:13:23 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.304861.23 (34.4%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-07-01 19:17:33 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.235543.31 (35.7%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-07-01 20:52:15 | Walk-Forward (Rolling) | BSE | Strategy_3 | 365 | BUY | Rs.8094.31 (39.6%) | Rs.31215.96 (28.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 385.7%). |
| 2026-07-01 20:55:31 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.26840.93 (31.0%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-01 21:01:00 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.184825.14 (22.7%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 21:04:16 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.77923.13 (20.4%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 21:06:19 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.111902.85 (40.7%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 22:30:43 | Walk-Forward (Rolling) | BSE | Strategy_3 | 365 | BUY | Rs.111060.74 (43.7%) | Rs.82773.06 (39.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 74.5%). |
| 2026-07-01 22:38:05 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.283737.10 (39.2%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 22:39:32 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.327681.65 (36.6%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 22:43:28 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.309617.34 (37.2%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 22:44:24 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.142456.37 (36.1%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 22:45:28 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.309617.34 (37.2%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 23:02:18 | Backtest | BSE | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.117932.24 (30.7%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 23:06:16 | Backtest | BSE | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.13347.69 (38.0%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-01 23:16:26 | Backtest | BSE | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.342385.52 (21.7%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-02 08:54:06 | Backtest | BSE | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.80269.92 (52.9%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-02 09:42:23 | Walk-Forward (Rolling) | BSE | Strategy_3 | 365 | SELL | Rs.107732.98 (52.3%) | Rs.106777.46 (46.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 99.1%). |
| 2026-07-02 09:49:05 | Backtest | BSE | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.244484.50 (37.0%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-02 09:57:52 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.309617.34 (37.2%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-02 10:06:57 | Backtest | SENSEX | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.65370.48 (14.5%) | sl_mult_buy=1, tp_mult_buy=4, trailing_mult_buy=0, sl_mul... | PROFITABLE |
| 2026-07-02 10:14:48 | Backtest | NIFTY | Strategy_1 | 365 | BUY | N/A (N/A) | Rs.-4809.36 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-02 10:15:21 | Backtest | NIFTY | Strategy_1 | 365 | SELL | N/A (N/A) | Rs.-2527.70 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-02 10:15:56 | Backtest | NIFTY | Strategy_2 | 365 | SELL | N/A (N/A) | Rs.-1807.25 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-03 09:02:09 | Backtest | NIFTY | Strategy_3 | 10 | BUY | N/A (N/A) | Rs.23902.91 (100.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-03 10:40:33 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.264934.51 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-03 10:41:11 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.349102.94 (55.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-03 10:42:07 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.349102.94 (55.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-03 10:43:01 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.342280.97 (55.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-03 10:45:21 | Backtest | NIFTY | Strategy_3 | 180 | SELL | N/A (N/A) | Rs.84024.84 (45.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-03 10:45:51 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.185788.50 (49.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-03 10:46:26 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.324824.61 (54.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-03 10:47:03 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.342280.97 (55.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-04 08:18:38 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.342280.97 (55.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-04 16:15:40 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.194995.57 (34.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-04 16:19:00 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.184835.53 (49.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-04 21:06:20 | Backtest | NIFTY | Strategy_4 | 365 | BUY | N/A (N/A) | Rs.-13930.37 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-04 21:10:29 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.340473.83 (37.2%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-04 21:13:09 | Backtest | BHARATFORG | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-333493.50 (23.3%) | sl_mult_buy=1, tp_mult_buy=8, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-07-04 21:14:45 | Walk-Forward (Rolling) | BHARATFORG | Strategy_3 | 365 | BUY | Rs.-185485.16 (19.9%) | Rs.-197157.60 (24.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-04 21:17:35 | Walk-Forward (Rolling) | POWERINDIA | Strategy_3 | 365 | BUY | Rs.-67954.38 (28.7%) | Rs.-54161.77 (32.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-04 21:18:35 | Walk-Forward (Rolling) | BHARATFORG | Strategy_3 | 365 | BUY | Rs.-185485.16 (19.9%) | Rs.-197157.60 (24.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-04 21:26:42 | Walk-Forward (Rolling) | BHARATFORG | Strategy_3 | 365 | BUY | Rs.-13707.35 (32.2%) | Rs.-13590.22 (32.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-04 22:01:55 | Walk-Forward (Rolling) | POWERINDIA | Strategy_3 | 365 | BUY | Rs.77254.78 (39.3%) | Rs.78167.26 (46.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 207.0%). |
| 2026-07-04 22:43:13 | Walk-Forward (Rolling) | POWERINDIA | Strategy_3 | 365 | BUY | Rs.59672.92 (39.0%) | Rs.-715.02 (26.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: -2.5%). |
| 2026-07-04 22:48:58 | Backtest | POWERINDIA | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.39269.47 (14.7%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | PROFITABLE |
| 2026-07-04 22:51:02 | Backtest | POWERINDIA | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-26913.66 (7.0%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-07-05 00:34:01 | Backtest | POWERINDIA | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-1834.36 (15.2%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-07-05 01:22:43 | Backtest | POWERINDIA | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-32665.44 (13.1%) | sl_mult_buy=1, tp_mult_buy=6, trailing_mult_buy=0.7, sl_m... | UNPROFITABLE |
| 2026-07-05 11:07:42 | Walk-Forward (Rolling) | POWERINDIA | Strategy_3 | 365 | BUY | Rs.-14470.06 (19.0%) | Rs.-9718.42 (5.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-05 13:59:04 | Walk-Forward (Rolling) | PERSISTENT | Strategy_3 | 365 | BUY | Rs.69467.50 (33.5%) | Rs.2433.70 (24.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 3.5%). |
| 2026-07-05 16:25:59 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.85503.15 (24.2%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-05 16:27:09 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.120596.98 (23.0%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-05 16:30:36 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.91148.05 (28.9%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-05 16:32:43 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.22240.03 (32.3%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-05 16:33:19 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.120596.98 (23.0%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-05 16:37:00 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.61928.00 (23.8%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-05 16:37:26 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.61928.00 (23.8%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-05 16:38:14 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.59537.26 (38.8%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-05 16:41:09 | Backtest | PERSISTENT | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-19918.19 (20.7%) | sl_mult_buy=1, tp_mult_buy=14, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-07-05 18:37:44 | Backtest | COLPAL | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-221855.75 (18.7%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-07-06 01:38:22 | Walk-Forward (Rolling) | COLPAL | Strategy_3 | 365 | BUY | Rs.-40799.44 (27.3%) | Rs.-55181.27 (20.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-06 08:57:44 | Backtest | COLPAL | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-5473.56 (33.0%) | sl_mult_buy=1, tp_mult_buy=10, trailing_mult_buy=0.7, sl_... | UNPROFITABLE |
| 2026-07-06 08:59:38 | Backtest | ANGELONE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.204212.04 (24.5%) | sl_mult_buy=3, tp_mult_buy=15, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-06 09:09:03 | Backtest | ANGELONE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-50187.69 (15.9%) | sl_mult_buy=3, tp_mult_buy=15, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-07-06 09:16:13 | Backtest | ANGELONE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.-54182.06 (30.3%) | sl_mult_buy=3, tp_mult_buy=15, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-07-06 09:29:03 | Optimization | ANGELONE | Strategy_3 | 180 | BUY | Rs.67334.87 (71.9%) | Rs.-10595.99 (56.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -33.4%). |
| 2026-07-06 09:29:48 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.172672.54 (46.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:30:11 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.194995.57 (34.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:31:28 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.116503.43 (54.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:37:49 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.193002.72 (39.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:39:15 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.116503.43 (54.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:44:10 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.97848.44 (51.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:50:05 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.184835.53 (49.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:54:38 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.264314.31 (45.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:58:25 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.247653.23 (45.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:58:55 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.264314.31 (45.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 09:59:36 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.348575.28 (55.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 17:57:28 | Backtest | NIFTY | Strategy_3 | 50 | BUY | N/A (N/A) | Rs.41245.16 (55.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 17:58:24 | Backtest | NIFTY | Strategy_3 | 50 | SELL | N/A (N/A) | Rs.35291.83 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 17:59:50 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.248870.44 (56.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 18:00:18 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.239416.53 (39.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 18:01:07 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.253420.60 (48.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-06 18:01:38 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.260681.70 (45.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-07 21:20:07 | Optimization | NIFTY | Strategy_10 | 360 | BOTH | Rs.119679.25 (71.4%) | Rs.84203.55 (70.0%) | rsi_length=7.0, ema_length=3.0, wma_length=15.0, use_vwap... | [ROBUST] Profitable on both splits (WFE: 137.8%). |
| 2026-07-07 21:26:42 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.150867.17 (54.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-07 21:28:33 | Backtest | NIFTY | Strategy_10 | 365 | SELL | N/A (N/A) | Rs.-14412.45 (19.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-07 21:30:50 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.245049.56 (43.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-07 21:32:08 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.157548.57 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-07 21:32:29 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.157548.57 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-07 21:35:40 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.135620.93 (38.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 09:44:31 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.353728.64 (54.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 12:44:13 | Backtest | NIFTY | Strategy_3 | 30 | BOTH | N/A (N/A) | Rs.3509.20 (25.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:04:01 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.7572.47 (35.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:27:50 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.281340.86 (44.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:28:37 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.293635.86 (45.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:34:40 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.300797.94 (46.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:46:49 | Backtest | NIFTY | Strategy_3 | 30 | BOTH | N/A (N/A) | Rs.30999.73 (41.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:47:35 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.300797.94 (46.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:50:50 | Backtest | NIFTY | Strategy_3 | 30 | BOTH | N/A (N/A) | Rs.30999.73 (41.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:51:25 | Backtest | NIFTY | Strategy_3 | 30 | BOTH | N/A (N/A) | Rs.30999.73 (41.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:56:02 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.300797.94 (46.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 13:59:53 | Backtest | NIFTY | Strategy_3 | 30 | BOTH | N/A (N/A) | Rs.32017.92 (47.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:02:03 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.365078.16 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:05:34 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.312640.32 (50.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:06:03 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.324387.49 (53.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:07:21 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.365078.16 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:10:24 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.345003.10 (54.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:10:50 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.322254.89 (52.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:17:14 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.150867.17 (54.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:41:37 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.366049.43 (55.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:44:57 | Backtest | NIFTY | Strategy_1 | 365 | BUY | N/A (N/A) | Rs.366050.25 (55.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 14:45:23 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.365078.16 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 15:47:27 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.365078.16 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 15:48:01 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.296130.56 (55.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 16:02:26 | Backtest | NIFTY | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.25881.29 (62.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 16:03:39 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.296130.56 (55.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 16:05:51 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.274105.11 (51.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 16:06:26 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.278874.05 (53.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 17:18:32 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.296130.56 (55.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 18:23:29 | Backtest | BSE | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.318601.41 (37.0%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-08 19:49:10 | Backtest | NIFTY | Strategy_3 | 10 | BOTH | N/A (N/A) | Rs.30021.01 (100.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 19:51:36 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.97519.75 (44.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 19:56:41 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.67714.68 (41.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 19:57:06 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.-9393.71 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-08 19:57:36 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.67714.68 (41.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 20:04:08 | Backtest | NIFTY | Strategy_10 | 10 | BOTH | N/A (N/A) | Rs.-2821.75 (25.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-08 20:05:53 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.37071.59 (40.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-08 20:06:26 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.-23541.43 (35.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-09 18:07:05 | Walk-Forward (Rolling) | ANGELONE | Strategy_3 | 1095 | BUY | Rs.17052.55 (23.6%) | Rs.90264.36 (24.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Combined OOS is profitable (WFE: 104.6%). |
| 2026-07-09 19:14:11 | Walk-Forward (Rolling) | GODREJPROP | Strategy_3 | 1095 | BUY | Rs.-79891.29 (20.5%) | Rs.-440292.75 (21.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-09 19:55:10 | Walk-Forward (Rolling) | PAYTM | Strategy_3 | 1095 | BUY | Rs.-88850.02 (20.3%) | Rs.-351274.30 (23.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-09 20:42:00 | Walk-Forward (Rolling) | LAURUSLABS | Strategy_3 | 1095 | BUY | Rs.-78573.24 (22.8%) | Rs.-474748.27 (21.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-09 21:24:11 | Walk-Forward (Rolling) | RECLTD | Strategy_3 | 1095 | BUY | Rs.-117956.28 (16.1%) | Rs.-567422.81 (17.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-09 22:11:06 | Walk-Forward (Rolling) | ABCAPITAL | Strategy_3 | 1095 | BUY | Rs.-169907.05 (20.8%) | Rs.-729740.83 (21.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-09 22:54:01 | Walk-Forward (Rolling) | IREDA | Strategy_3 | 1095 | BUY | Rs.-56198.61 (19.7%) | Rs.-389423.04 (18.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-09 23:34:56 | Walk-Forward (Rolling) | NATIONALUM | Strategy_3 | 1095 | BUY | Rs.-38044.87 (18.9%) | Rs.-377378.15 (17.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 00:15:42 | Walk-Forward (Rolling) | UNIONBANK | Strategy_3 | 1095 | BUY | Rs.-115080.09 (16.6%) | Rs.-570518.96 (17.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 00:58:00 | Walk-Forward (Rolling) | CANBK | Strategy_3 | 1095 | BUY | Rs.-133237.70 (15.2%) | Rs.-822723.86 (15.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 01:38:52 | Walk-Forward (Rolling) | GMRAIRPORT | Strategy_3 | 1095 | BUY | Rs.-137290.86 (17.8%) | Rs.-741266.00 (18.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 02:20:52 | Walk-Forward (Rolling) | PNB | Strategy_3 | 1095 | BUY | Rs.-138807.27 (19.8%) | Rs.-797408.28 (21.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 02:58:26 | Walk-Forward (Rolling) | SUZLON | Strategy_3 | 1095 | BUY | Rs.-49936.77 (24.2%) | Rs.-266856.14 (24.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 03:41:53 | Walk-Forward (Rolling) | PAGEIND | Strategy_3 | 1095 | BUY | Rs.-97013.00 (25.7%) | Rs.-420867.99 (24.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 04:25:50 | Walk-Forward (Rolling) | APOLLOHOSP | Strategy_3 | 1095 | BUY | Rs.-173908.49 (20.2%) | Rs.-957430.59 (20.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 05:07:16 | Walk-Forward (Rolling) | MCX | Strategy_3 | 1095 | BUY | Rs.-60449.71 (21.7%) | Rs.-509675.20 (20.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 05:48:16 | Walk-Forward (Rolling) | KEI | Strategy_3 | 1095 | BUY | Rs.-84162.98 (24.1%) | Rs.-547225.34 (22.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 06:31:03 | Walk-Forward (Rolling) | GLENMARK | Strategy_3 | 1095 | BUY | Rs.-123261.53 (18.9%) | Rs.-576601.47 (20.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 07:14:36 | Walk-Forward (Rolling) | UNITDSPR | Strategy_3 | 1095 | BUY | Rs.-113019.55 (21.6%) | Rs.-511430.59 (22.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 07:54:39 | Walk-Forward (Rolling) | PATANJALI | Strategy_3 | 1095 | BUY | Rs.-100192.22 (22.4%) | Rs.-477623.33 (20.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 08:44:57 | Walk-Forward (Rolling) | AUBANK | Strategy_3 | 1095 | BUY | Rs.-120889.80 (19.7%) | Rs.-607754.60 (19.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 09:40:10 | Walk-Forward (Rolling) | UPL | Strategy_3 | 1095 | BUY | Rs.-170195.77 (22.1%) | Rs.-852685.19 (21.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 10:30:26 | Walk-Forward (Rolling) | NTPC | Strategy_3 | 1095 | BUY | Rs.-92504.46 (21.4%) | Rs.-471128.87 (19.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 10:54:46 | Optimization | ANGELONE | Strategy_3 | 180 | BUY | Rs.187928.29 (34.3%) | Rs.85977.27 (33.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both splits (WFE: 96.3%). |
| 2026-07-10 10:56:53 | Optimization | GODREJPROP | Strategy_3 | 180 | BUY | Rs.-43748.31 (27.7%) | Rs.-3265.56 (34.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:32:19 | Optimization | ANGELONE | Strategy_3 | 120 | BUY | Rs.217997.26 (36.4%) | Rs.19082.90 (30.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both splits (WFE: 19.4%). |
| 2026-07-10 13:33:30 | Optimization | GODREJPROP | Strategy_3 | 120 | BUY | Rs.-42374.26 (25.4%) | Rs.-13527.62 (28.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:34:41 | Optimization | PAYTM | Strategy_3 | 120 | BUY | Rs.-28101.98 (21.3%) | Rs.-22284.60 (18.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:36:00 | Optimization | LAURUSLABS | Strategy_3 | 120 | BUY | Rs.-143759.87 (12.3%) | Rs.-50647.00 (26.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:37:19 | Optimization | RECLTD | Strategy_3 | 120 | BUY | Rs.-50031.67 (6.3%) | Rs.-25797.86 (5.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:38:49 | Optimization | ABCAPITAL | Strategy_3 | 120 | BUY | Rs.-74806.74 (23.5%) | Rs.-36388.72 (16.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:40:08 | Optimization | IREDA | Strategy_3 | 120 | BUY | Rs.60733.52 (19.0%) | Rs.-21821.41 (3.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -79.6%). |
| 2026-07-10 13:41:24 | Optimization | NATIONALUM | Strategy_3 | 120 | BUY | Rs.-54557.00 (20.0%) | Rs.-35215.92 (15.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:42:44 | Optimization | UNIONBANK | Strategy_3 | 120 | BUY | Rs.-35147.46 (31.0%) | Rs.-35130.89 (26.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:43:59 | Optimization | CANBK | Strategy_3 | 120 | BUY | Rs.-92026.98 (14.8%) | Rs.-86.95 (30.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:45:13 | Optimization | GMRAIRPORT | Strategy_3 | 120 | BUY | Rs.-81388.53 (23.4%) | Rs.-14540.60 (25.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:46:28 | Optimization | PNB | Strategy_3 | 120 | BUY | Rs.-43674.89 (42.1%) | Rs.-4666.43 (34.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:47:44 | Optimization | SUZLON | Strategy_3 | 120 | BUY | Rs.-60372.95 (4.8%) | Rs.-33954.82 (3.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:49:14 | Optimization | PAGEIND | Strategy_3 | 120 | BUY | Rs.-11149.18 (36.5%) | Rs.-23408.28 (24.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:50:44 | Optimization | APOLLOHOSP | Strategy_3 | 120 | BUY | Rs.-138887.41 (17.2%) | Rs.-66797.71 (28.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:52:06 | Optimization | MCX | Strategy_3 | 120 | BUY | Rs.152348.85 (45.2%) | Rs.-154778.57 (15.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -225.2%). |
| 2026-07-10 13:53:33 | Optimization | KEI | Strategy_3 | 120 | BUY | Rs.-70317.18 (28.3%) | Rs.-31996.10 (21.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:54:56 | Optimization | GLENMARK | Strategy_3 | 120 | BUY | Rs.-68157.19 (20.7%) | Rs.-43605.66 (17.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:56:30 | Optimization | UNITDSPR | Strategy_3 | 120 | BUY | Rs.-24803.20 (20.4%) | Rs.-20452.03 (15.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:58:04 | Optimization | PATANJALI | Strategy_3 | 120 | BUY | Rs.-57221.55 (23.3%) | Rs.-33653.17 (10.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 13:59:46 | Optimization | AUBANK | Strategy_3 | 120 | BUY | Rs.-50716.40 (29.8%) | Rs.-4033.06 (48.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:01:22 | Optimization | UPL | Strategy_3 | 120 | BUY | Rs.-91385.00 (18.3%) | Rs.-35202.04 (23.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:02:52 | Optimization | NTPC | Strategy_3 | 120 | BUY | Rs.-60785.59 (23.9%) | Rs.-34200.68 (17.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:04:22 | Optimization | LTF | Strategy_3 | 120 | BUY | Rs.-56213.91 (16.7%) | Rs.-18244.55 (32.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:05:52 | Optimization | RBLBANK | Strategy_3 | 120 | BUY | Rs.-47997.62 (19.2%) | Rs.-64394.74 (25.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:07:27 | Optimization | 360ONE | Strategy_3 | 120 | BUY | Rs.-61977.35 (8.5%) | Rs.-43324.70 (2.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:09:00 | Optimization | ABB | Strategy_3 | 120 | BUY | Rs.-16556.29 (28.8%) | Rs.-28873.21 (30.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:10:25 | Optimization | ADANIENSOL | Strategy_3 | 120 | BUY | Rs.192873.21 (19.6%) | Rs.-49159.71 (3.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -56.5%). |
| 2026-07-10 14:11:55 | Optimization | ADANIENT | Strategy_3 | 120 | BUY | Rs.-55755.83 (17.9%) | Rs.-67583.63 (11.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:13:25 | Optimization | ADANIGREEN | Strategy_3 | 120 | BUY | Rs.234367.51 (42.9%) | Rs.-29105.88 (20.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -27.5%). |
| 2026-07-10 14:14:50 | Optimization | ADANIPORTS | Strategy_3 | 120 | BUY | Rs.-56621.82 (21.9%) | Rs.-30359.00 (17.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:31:05 | Walk-Forward (Rolling) | RELIANCE | Strategy_10 | 360 | BOTH | Rs.0.00 (0.0%) | Rs.0.00 (0.0%) | Walk-Forward=Rolling WFO (WFE: 0.00%) | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 14:52:57 | Walk-Forward (Rolling) | RELIANCE | Strategy_10 | 360 | BOTH | Rs.-7736.28 (20.9%) | Rs.-19448.79 (7.7%) | rsi_length=7, ema_length=5, wma_length=15, adx_length=14,... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 14:54:41 | Optimization | ALKEM | Strategy_3 | 120 | BUY | Rs.-36039.54 (20.0%) | Rs.-58663.46 (24.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:56:04 | Optimization | AMBER | Strategy_3 | 120 | BUY | Rs.-45771.73 (24.6%) | Rs.-14952.73 (30.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:57:12 | Backtest | NIFTY | Strategy_10 | 60 | BUY | N/A (N/A) | Rs.-5546.64 (25.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-10 14:57:31 | Optimization | AMBUJACEM | Strategy_3 | 120 | BUY | Rs.-29327.56 (20.0%) | Rs.-22627.72 (6.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 14:58:55 | Optimization | APLAPOLLO | Strategy_3 | 120 | BUY | Rs.-59592.79 (22.8%) | Rs.-29345.65 (12.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:00:20 | Optimization | ASHOKLEY | Strategy_3 | 120 | BUY | Rs.-73179.39 (24.1%) | Rs.-36383.73 (18.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:01:56 | Optimization | ASIANPAINT | Strategy_3 | 120 | BUY | Rs.-65560.65 (11.1%) | Rs.-37022.84 (20.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:03:23 | Optimization | ASTRAL | Strategy_3 | 120 | BUY | Rs.-56007.52 (24.1%) | Rs.-37423.28 (10.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:04:51 | Optimization | AUROPHARMA | Strategy_3 | 120 | BUY | Rs.-98466.11 (12.7%) | Rs.-52458.54 (13.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:06:21 | Optimization | AXISBANK | Strategy_3 | 120 | BUY | Rs.-59900.48 (21.9%) | Rs.-38238.73 (15.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:07:50 | Optimization | BAJAJ-AUTO | Strategy_3 | 120 | BUY | Rs.-70787.48 (18.0%) | Rs.-43712.73 (10.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:09:15 | Optimization | BAJAJFINSV | Strategy_3 | 120 | BUY | Rs.-36934.12 (22.2%) | Rs.-20818.57 (17.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:10:39 | Optimization | BAJFINANCE | Strategy_3 | 120 | BUY | Rs.-63272.66 (19.0%) | Rs.-47404.75 (15.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:11:58 | Optimization | BANDHANBNK | Strategy_3 | 120 | BUY | Rs.-57593.80 (18.0%) | Rs.-33541.95 (13.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:13:19 | Optimization | BANKBARODA | Strategy_3 | 120 | BUY | Rs.-85528.86 (26.7%) | Rs.-16262.12 (24.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:14:36 | Optimization | BANKINDIA | Strategy_3 | 120 | BUY | Rs.-9026.59 (30.8%) | Rs.15995.86 (34.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:16:06 | Optimization | BDL | Strategy_3 | 120 | BUY | Rs.-29754.92 (22.0%) | Rs.-25682.95 (18.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:17:29 | Optimization | BEL | Strategy_3 | 120 | BUY | Rs.-59293.15 (17.3%) | Rs.-37764.50 (12.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:18:59 | Optimization | BHARTIARTL | Strategy_3 | 120 | BUY | Rs.-22442.55 (35.3%) | Rs.5651.29 (44.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:20:29 | Optimization | BHEL | Strategy_3 | 120 | BUY | Rs.295633.37 (42.5%) | Rs.24861.37 (26.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both splits (WFE: 18.6%). |
| 2026-07-10 15:22:20 | Optimization | BIOCON | Strategy_3 | 120 | BUY | Rs.-114037.87 (13.8%) | Rs.-27126.54 (16.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 15:39:22 | Walk-Forward (Rolling) | RELIANCE | Strategy_10 | 360 | BOTH | Rs.-25646.37 (5.9%) | Rs.-21551.08 (8.7%) | rsi_length=7, ema_length=5, wma_length=28, adx_length=14,... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-10 15:40:35 | Backtest | NIFTY | Strategy_10 | 60 | BUY | N/A (N/A) | Rs.5443.20 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 16:13:33 | Optimization | BLUESTARCO | Strategy_3 | 120 | BUY | Rs.-28995.35 (24.5%) | Rs.-29525.19 (20.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:14:53 | Optimization | BOSCHLTD | Strategy_3 | 120 | BUY | Rs.-43763.32 (24.0%) | Rs.-74019.93 (15.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:16:15 | Optimization | BPCL | Strategy_3 | 120 | BUY | Rs.-42379.44 (23.7%) | Rs.-29493.83 (15.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:17:45 | Optimization | BRITANNIA | Strategy_3 | 120 | BUY | Rs.-62024.07 (19.4%) | Rs.-39129.99 (14.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:19:12 | Optimization | CAMS | Strategy_3 | 120 | BUY | Rs.-34775.92 (21.8%) | Rs.-21532.77 (20.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:20:45 | Optimization | CDSL | Strategy_3 | 120 | BUY | Rs.-35760.91 (7.1%) | Rs.-28380.37 (6.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:22:16 | Optimization | CGPOWER | Strategy_3 | 120 | BUY | Rs.-31184.63 (31.7%) | Rs.-34093.59 (23.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:23:46 | Optimization | CHOLAFIN | Strategy_3 | 120 | BUY | Rs.-100375.88 (15.8%) | Rs.-57489.49 (17.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:25:14 | Optimization | CIPLA | Strategy_3 | 120 | BUY | Rs.-60259.24 (23.6%) | Rs.-27651.13 (16.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 16:26:32 | Backtest | NIFTY | Strategy_10 | 60 | BUY | N/A (N/A) | Rs.12397.05 (60.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 16:37:53 | Backtest | NIFTY | Strategy_10 | 60 | BUY | N/A (N/A) | Rs.9689.68 (66.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 16:51:10 | Backtest | NIFTY | Strategy_10 | 60 | BUY | N/A (N/A) | Rs.6927.25 (100.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 16:51:31 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.9621.73 (66.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 16:51:53 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.-2628.29 (37.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-10 16:53:02 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.-1316.98 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-10 17:01:23 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.-1316.98 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-10 17:02:01 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.-5656.99 (25.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-10 17:04:30 | Optimization | COALINDIA | Strategy_3 | 120 | BUY | Rs.-84926.88 (18.8%) | Rs.-11977.29 (27.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:05:55 | Optimization | COFORGE | Strategy_3 | 120 | BUY | Rs.134228.53 (47.1%) | Rs.-14182.86 (37.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -23.4%). |
| 2026-07-10 17:07:24 | Optimization | CONCOR | Strategy_3 | 120 | BUY | Rs.-83837.71 (22.4%) | Rs.-25692.82 (32.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:08:44 | Optimization | CROMPTON | Strategy_3 | 120 | BUY | Rs.-68037.60 (22.7%) | Rs.-29477.12 (13.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:10:05 | Optimization | CUMMINSIND | Strategy_3 | 120 | BUY | Rs.-73805.66 (13.1%) | Rs.-63049.67 (10.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:11:28 | Optimization | DABUR | Strategy_3 | 120 | BUY | Rs.-51355.75 (16.7%) | Rs.-25695.73 (14.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:12:47 | Optimization | DALBHARAT | Strategy_3 | 120 | BUY | Rs.-47424.04 (28.9%) | Rs.-19296.92 (32.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:14:10 | Optimization | DELHIVERY | Strategy_3 | 120 | BUY | Rs.-71923.59 (22.7%) | Rs.-1695.34 (28.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:15:35 | Optimization | DIVISLAB | Strategy_3 | 120 | BUY | Rs.-79916.20 (4.3%) | Rs.-42872.83 (2.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:16:59 | Optimization | DIXON | Strategy_3 | 120 | BUY | Rs.-41395.40 (22.4%) | Rs.-27366.51 (25.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:18:24 | Optimization | DLF | Strategy_3 | 120 | BUY | Rs.-56983.21 (11.3%) | Rs.-17682.97 (28.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:19:44 | Optimization | DMART | Strategy_3 | 120 | BUY | Rs.-52548.73 (23.3%) | Rs.-32608.64 (16.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:21:07 | Optimization | DRREDDY | Strategy_3 | 120 | BUY | Rs.-50227.21 (25.5%) | Rs.-26690.18 (31.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:22:34 | Optimization | EICHERMOT | Strategy_3 | 120 | BUY | Rs.-77537.74 (7.5%) | Rs.-28114.47 (15.2%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:23:53 | Optimization | ETERNAL | Strategy_3 | 120 | BUY | Rs.-67110.65 (5.2%) | Rs.-43486.10 (3.1%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:25:15 | Optimization | EXIDEIND | Strategy_3 | 120 | BUY | Rs.-53341.66 (20.7%) | Rs.-20943.16 (26.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:26:40 | Optimization | FEDERALBNK | Strategy_3 | 120 | BUY | Rs.-70468.31 (8.1%) | Rs.-59238.82 (4.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:28:07 | Optimization | FORTIS | Strategy_3 | 120 | BUY | Rs.-76777.31 (25.0%) | Rs.-20152.72 (29.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:29:48 | Optimization | GAIL | Strategy_3 | 120 | BUY | Rs.-56327.05 (16.2%) | Rs.-42808.31 (7.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 17:31:23 | Optimization | GODREJCP | Strategy_3 | 120 | BUY | Rs.-49435.51 (22.8%) | Rs.-24996.00 (25.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-10 18:25:45 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.-3271.96 (42.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-10 18:26:24 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.26372.70 (39.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 18:27:09 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.82313.99 (38.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 18:27:49 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.36385.83 (40.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 18:49:44 | Walk-Forward (Rolling) | NIFTY | Strategy_10 | 365 | BUY | Rs.59082.13 (49.0%) | Rs.1906.00 (38.9%) | rsi_length=9, ema_length=3, wma_length=21, adx_length=14,... | [ROBUST] Combined OOS is profitable (WFE: 3.2%). |
| 2026-07-10 18:57:01 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.89944.99 (36.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 18:57:33 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.110802.24 (41.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-10 18:57:58 | Backtest | NIFTY | Strategy_10 | 365 | BUY | N/A (N/A) | Rs.13473.36 (27.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-13 16:42:04 | Backtest | NIFTY | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.17546.24 (44.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-13 16:43:46 | Backtest | NIFTY | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.12847.63 (44.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-13 17:09:46 | Backtest | NIFTY | Strategy_3 | 60 | SELL | N/A (N/A) | Rs.69151.02 (56.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-13 17:13:30 | Backtest | NIFTY | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.12847.63 (44.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-13 17:16:10 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.257802.26 (45.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-13 17:18:55 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.266632.79 (52.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-13 17:19:25 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.248723.48 (54.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-14 15:49:22 | Backtest | BSE | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.134583.40 (42.3%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-14 15:53:43 | Backtest | BSE | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.134583.40 (42.3%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-14 16:12:09 | Backtest | NIFTY | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.8301.99 (38.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-14 16:12:51 | Backtest | NIFTY | Strategy_3 | 60 | SELL | N/A (N/A) | Rs.65564.77 (52.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-14 16:24:19 | Backtest | KALYANKJIL | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.-833.29 (18.6%) | sl_mult_buy=3, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-07-14 16:27:36 | Backtest | KALYANKJIL | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.11957.25 (26.9%) | sl_mult_buy=3, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | PROFITABLE |
| 2026-07-14 16:40:33 | Backtest | CONCOR | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.-54631.00 (18.2%) | sl_mult_buy=1, tp_mult_buy=3, trailing_mult_buy=0, sl_mul... | UNPROFITABLE |
| 2026-07-14 16:53:05 | Backtest | SBICARD | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.46517.99 (50.0%) | sl_mult_buy=1, tp_mult_buy=12, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-14 17:04:11 | Backtest | ICICIGI | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.34629.56 (44.4%) | sl_mult_buy=1, tp_mult_buy=15, trailing_mult_buy=0.7, sl_... | PROFITABLE |
| 2026-07-15 16:06:18 | Backtest | NIFTY | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.15210.00 (42.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-15 16:37:23 | Backtest | NIFTY | Strategy_3 | 60 | SELL | N/A (N/A) | Rs.67229.67 (53.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-15 16:38:37 | Backtest | NIFTY | Strategy_3 | 60 | BUY | N/A (N/A) | Rs.15210.00 (42.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-15 16:39:01 | Backtest | BSE | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.-22004.32 (28.6%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-07-15 16:46:50 | Backtest | BSE | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.-22004.32 (28.6%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-07-15 17:00:00 | Backtest | BSE | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.-27624.54 (33.3%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-07-16 16:25:17 | Backtest | NIFTY | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.14036.83 (55.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:15:23 | Optimization | NIFTY | Strategy_3 | 60 | BUY | Rs.2510.98 (35.7%) | Rs.-2370.74 (33.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -211.0%). |
| 2026-07-16 17:19:54 | Backtest | NIFTY | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.3088.74 (33.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:20:48 | Backtest | NIFTY | Strategy_3 | 30 | BUY | N/A (N/A) | Rs.3088.74 (33.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:21:54 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.207958.68 (44.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:24:06 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.133961.71 (32.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:30:08 | Optimization | NIFTY | Strategy_3 | 365 | BUY | Rs.106806.77 (40.0%) | Rs.12173.53 (33.3%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both splits (WFE: 22.4%). |
| 2026-07-16 17:33:34 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.187203.58 (42.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:34:56 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.107508.76 (35.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:35:17 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.120180.62 (40.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:35:44 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.187203.58 (42.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:38:19 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.11836.73 (63.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:38:50 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.21536.96 (54.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:43:04 | Optimization | NIFTY | Strategy_3 | 180 | BUY | Rs.35417.18 (39.6%) | Rs.-4224.06 (20.7%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -25.1%). |
| 2026-07-16 17:49:01 | Optimization | NIFTY | Strategy_3 | 180 | BUY | Rs.28395.77 (42.6%) | Rs.-8922.55 (28.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [OVERFITTED] Strategy loses money on test split (WFE: -66.2%). |
| 2026-07-16 17:52:25 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.118980.30 (38.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 17:58:44 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.133961.71 (32.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 18:04:35 | Optimization | NIFTY | Strategy_3 | 365 | SELL | Rs.85976.37 (47.1%) | Rs.82607.50 (53.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both splits (WFE: 189.0%). |
| 2026-07-16 18:07:07 | Backtest | NIFTY | Strategy_3 | 365 | SELL | N/A (N/A) | Rs.171434.92 (49.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 18:15:16 | Optimization | NIFTY | Strategy_3 | 190 | BUY | Rs.24631.98 (48.0%) | Rs.2557.73 (37.0%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both splits (WFE: 21.3%). |
| 2026-07-16 18:18:03 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.27453.45 (39.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 18:18:24 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.27453.45 (39.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 18:21:06 | Optimization | NIFTY | Strategy_3 | 190 | SELL | Rs.57563.62 (42.9%) | Rs.43715.12 (51.9%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [ROBUST] Profitable on both splits (WFE: 155.6%). |
| 2026-07-16 18:24:27 | Backtest | NIFTY | Strategy_3 | 190 | SELL | N/A (N/A) | Rs.106607.35 (45.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 18:24:45 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.27453.45 (39.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 18:25:27 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.27453.45 (39.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 18:25:39 | Backtest | NIFTY | Strategy_3 | 190 | SELL | N/A (N/A) | Rs.106607.35 (45.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 20:33:38 | Backtest | NIFTY | Strategy_3 | 190 | SELL | N/A (N/A) | Rs.69751.16 (34.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 20:37:05 | Backtest | NIFTY | Strategy_3 | 190 | SELL | N/A (N/A) | Rs.64110.45 (37.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 20:51:41 | Backtest | NIFTY | Strategy_3 | 190 | SELL | N/A (N/A) | Rs.118557.55 (43.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 20:53:51 | Backtest | NIFTY | Strategy_3 | 190 | SELL | N/A (N/A) | Rs.107853.65 (46.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 20:55:53 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.86127.41 (38.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 20:58:23 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.-43682.26 (30.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-16 21:00:39 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.27453.45 (39.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 21:17:46 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.86127.41 (38.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 21:20:22 | Backtest | NIFTY | Strategy_1 | 190 | BUY | N/A (N/A) | Rs.-321.00 (33.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-16 21:20:39 | Backtest | NIFTY | Strategy_2 | 190 | BUY | N/A (N/A) | Rs.-9829.11 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-16 21:20:54 | Backtest | NIFTY | Strategy_10 | 190 | BUY | N/A (N/A) | Rs.887.84 (20.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 21:21:25 | Backtest | NIFTY | Strategy_9 | 190 | BUY | N/A (N/A) | Rs.43422.78 (46.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 21:25:09 | Backtest | NIFTY | Strategy_7 | 190 | BUY | N/A (N/A) | Rs.8918.64 (43.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-16 21:25:42 | Backtest | NIFTY | Strategy_6 | 190 | BUY | N/A (N/A) | Rs.-34396.81 (27.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-16 21:28:04 | Backtest | NIFTY | Strategy_10 | 190 | BUY | N/A (N/A) | Rs.-13801.68 (31.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 12:51:11 | Backtest | NIFTY | Strategy_11 | 30 | BUY | N/A (N/A) | Rs.-4162.43 (33.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 13:02:55 | Optimization | NIFTY | Strategy_11 | 365 | BUY | Rs.-16061.84 (27.1%) | Rs.-11304.44 (14.3%) | timeframe=15min, breakout_wait_bars=2, use_vwap_filter=0,... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-17 13:08:50 | Optimization | NIFTY | Strategy_11 | 365 | BUY | Rs.-16061.84 (27.1%) | Rs.-11304.44 (14.3%) | timeframe=15min, breakout_wait_bars=2, use_vwap_filter=0,... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-17 13:09:16 | Backtest | NIFTY | Strategy_3 | 365 | BUY | N/A (N/A) | Rs.97974.34 (42.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 13:16:29 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.27453.45 (39.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 13:25:43 | Backtest | NIFTY | Strategy_11 | 30 | BUY | N/A (N/A) | Rs.-41.16 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 13:31:48 | Optimization | NIFTY | Strategy_11 | 365 | BUY | Rs.-6069.14 (33.3%) | Rs.-5509.53 (22.2%) | timeframe_ce=15min, timeframe_pe=5min, breakout_wait_bars... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-17 13:34:33 | Backtest | BSE | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.-22422.78 (28.9%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-07-17 13:38:01 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.10650.07 (35.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 13:48:53 | Optimization | NIFTY | Strategy_11 | 365 | BUY | Rs.12100.48 (43.3%) | Rs.8697.63 (62.5%) | timeframe_ce=15min, timeframe_pe=5min, breakout_wait_bars... | [ROBUST] Profitable on both splits (WFE: 141.4%). |
| 2026-07-17 13:50:55 | Backtest | NIFTY | Strategy_11 | 190 | BUY | N/A (N/A) | Rs.4546.70 (100.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 18:36:07 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.-7562.49 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 18:38:03 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.-4026.48 (33.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 18:40:17 | Optimization | NIFTY | Strategy_12 | 365 | BUY | Rs.0.00 (0.0%) | Rs.0.00 (0.0%) | entry_time=09:30, exit_time=10:00, trend_lookback_mins=15... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-17 18:40:33 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-1221.24 (55.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 18:41:01 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.18877.67 (45.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 18:42:39 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-1522.96 (57.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 18:42:57 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.24966.69 (53.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 18:44:45 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.18877.67 (45.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 18:45:43 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.18877.67 (45.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 19:33:12 | Optimization | NIFTY | Strategy_12 | 190 | BUY | Rs.17615.51 (48.4%) | Rs.-19687.08 (30.3%) | entry_time=09:30, exit_time=10:45, trend_lookback_mins=30... | [OVERFITTED] Strategy loses money on test split (WFE: -228.9%). |
| 2026-07-17 19:49:03 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-40622.36 (42.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 19:49:32 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-31717.14 (40.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 19:50:10 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-52738.93 (34.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 19:50:25 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-28971.98 (40.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 19:50:58 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-7146.16 (37.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 19:56:10 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-7146.16 (37.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 19:56:54 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-40622.36 (42.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 19:59:00 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-40622.36 (42.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:23:21 | Optimization | NIFTY | Strategy_12 | 365 | BUY | Rs.-30494.63 (37.1%) | Rs.2224.65 (55.8%) | entry_time=09:30, exit_time=10:00, trend_lookback_mins=15... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-17 20:23:54 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-26467.23 (44.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:24:26 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-4230.82 (33.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:25:42 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-20177.78 (36.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:29:10 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.-5312.04 (38.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:29:50 | Backtest | NIFTY | Strategy_12 | 365 | SELL | N/A (N/A) | Rs.-25931.10 (46.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:32:31 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.9505.77 (43.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-17 20:33:47 | Backtest | NIFTY | Strategy_12 | 190 | SELL | N/A (N/A) | Rs.-2679.86 (46.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:41:26 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-39983.64 (35.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:44:47 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-33915.48 (34.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 20:49:11 | Optimization | NIFTY | Strategy_12 | 190 | BUY | Rs.11448.55 (61.1%) | Rs.-5304.35 (30.0%) | entry_time=14:30, exit_time=15:00, trend_lookback_mins=15... | [OVERFITTED] Strategy loses money on test split (WFE: -98.1%). |
| 2026-07-17 21:08:46 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-44102.28 (36.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 21:09:05 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.-925.89 (35.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-17 21:24:50 | Optimization | NIFTY | Strategy_3 | 190 | BUY | Rs.-18757.88 (46.3%) | Rs.-10434.87 (52.5%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-17 21:39:16 | Optimization | NIFTY | Strategy_12 | 190 | BUY | Rs.0.00 (0.0%) | Rs.0.00 (0.0%) | entry_time=09:30, exit_time=10:00, trend_lookback_mins=30... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-17 21:52:35 | Optimization | NIFTY | Strategy_12 | 190 | BUY | Rs.29879.84 (72.4%) | Rs.-29966.95 (25.8%) | entry_time=09:30, exit_time=15:00, trend_lookback_mins=30... | [OVERFITTED] Strategy loses money on test split (WFE: -212.3%). |
| 2026-07-19 12:57:09 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.8206.55 (45.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 12:58:02 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.37242.07 (47.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:01:19 | Backtest | NIFTY | Strategy_12 | 365 | BUY | N/A (N/A) | Rs.6638.18 (40.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:01:42 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.37242.07 (47.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:10:34 | Optimization | NIFTY | Strategy_12 | 190 | BUY | Rs.43747.00 (61.4%) | Rs.14280.41 (46.9%) | rsi_period=14.0, rsi_overbought=65.0, rsi_oversold=30.0, ... | [ROBUST] Profitable on both splits (WFE: 69.1%). |
| 2026-07-19 13:12:55 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.55908.81 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:13:19 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.4550.21 (57.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:13:36 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.55908.81 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:31:23 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.58583.55 (52.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:32:39 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.55908.81 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:40:47 | Backtest | NIFTY | Strategy_12 | 190 | SELL | N/A (N/A) | Rs.126654.22 (47.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:53:06 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.57460.36 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:53:39 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.55908.81 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:54:13 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.58235.13 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 13:54:36 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.56686.59 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:17:26 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.29569.11 (85.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:19:04 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.68188.74 (73.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:19:38 | Backtest | NIFTY | Strategy_12 | 190 | SELL | N/A (N/A) | Rs.75763.78 (72.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:21:06 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.68188.74 (73.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:24:32 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.29569.11 (85.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:24:56 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.58235.13 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:27:49 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.3129.58 (40.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:28:04 | Backtest | NIFTY | Strategy_12 | 15 | BUY | N/A (N/A) | Rs.1622.82 (42.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:28:16 | Backtest | NIFTY | Strategy_12 | 60 | BUY | N/A (N/A) | Rs.14507.31 (50.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 14:28:34 | Backtest | NIFTY | Strategy_12 | 75 | BUY | N/A (N/A) | Rs.25406.85 (52.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-19 15:18:18 | Backtest | BSE | Strategy_12 | 75 | BUY | N/A (N/A) | Rs.-38633.15 (0.0%) | sl_mult_buy=2, tp_mult_buy=12, trailing_mult_buy=0, sl_mu... | UNPROFITABLE |
| 2026-07-20 10:28:41 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.58235.13 (56.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 15:53:53 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.59706.95 (56.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 16:01:54 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.-400.75 (25.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:10:12 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-12417.25 (20.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:15:18 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.-2471.27 (36.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:16:45 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-18582.14 (35.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:17:05 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-12417.25 (20.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:26:40 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.-1937.07 (25.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:27:12 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-11600.35 (23.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:36:55 | Optimization | NIFTY | Strategy_12 | 190 | BUY | Rs.76189.93 (38.6%) | Rs.-26494.38 (19.4%) | rsi_period=14.0, rsi_overbought=65.0, rsi_oversold=30.0, ... | [OVERFITTED] Strategy loses money on test split (WFE: -72.4%). |
| 2026-07-20 16:43:16 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-27826.97 (23.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:54:23 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-15474.22 (23.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:55:37 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.-2711.84 (25.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 16:57:37 | Backtest | NIFTY | Strategy_12 | 30 | BUY | N/A (N/A) | Rs.2575.24 (38.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 16:58:03 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-16553.14 (24.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:07:31 | Optimization | NIFTY | Strategy_12 | 190 | BUY | Rs.76189.93 (38.6%) | Rs.-26494.38 (19.4%) | rsi_period=14.0, rsi_overbought=65.0, rsi_oversold=30.0, ... | [OVERFITTED] Strategy loses money on test split (WFE: -72.4%). |
| 2026-07-20 17:11:55 | Backtest | NIFTY | None | 30 | BUY | N/A (N/A) | Rs.-2031.85 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:12:26 | Backtest | NIFTY | Strategy_13 | 30 | BUY | N/A (N/A) | Rs.-2031.85 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:12:43 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-1910.43 (22.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:17:24 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-964.26 (22.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:17:28 | Optimization | NIFTY | Strategy_13 | 90 | BUY | Rs.1297.25 (37.5%) | Rs.-2905.01 (0.0%) | supertrend_period=10.0, supertrend_mult=2.5, ema_period=5... | [OVERFITTED] Strategy loses money on test split (WFE: -419.0%). |
| 2026-07-20 17:19:23 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.6352.12 (63.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 17:23:28 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.8167.63 (65.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 17:32:47 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-7843.56 (55.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:33:20 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-15972.65 (35.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:33:48 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-43705.86 (17.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:34:31 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.11513.49 (81.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 17:35:21 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-8524.47 (55.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:36:08 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.12697.80 (78.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 17:36:51 | Backtest | NIFTY | Strategy_13 | 30 | BUY | N/A (N/A) | Rs.1818.02 (100.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 17:37:30 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.12697.80 (78.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 17:39:57 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-5474.36 (56.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:40:43 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-16526.71 (46.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:42:30 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-37577.17 (53.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:44:01 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-12795.19 (54.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:45:23 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.391.68 (57.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 17:46:20 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-32482.83 (41.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 17:47:18 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.391.68 (57.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-20 17:57:01 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-6984.65 (35.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-20 18:17:33 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.-4169.31 (36.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 09:08:14 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-37577.17 (53.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 09:12:01 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-20029.04 (55.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 09:14:13 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.-6676.51 (58.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 09:15:08 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.10947.33 (58.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:16:02 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.7002.49 (55.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:16:37 | Backtest | NIFTY | Strategy_13 | 180 | BUY | N/A (N/A) | Rs.10947.33 (58.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:17:42 | Backtest | NIFTY | Strategy_11 | 190 | BUY | N/A (N/A) | Rs.3891.59 (56.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:20:09 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.15877.57 (60.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:30:46 | Optimization | NIFTY | Strategy_13 | 190 | BUY | Rs.16335.96 (43.5%) | Rs.2435.14 (48.4%) | supertrend_period=10.0, supertrend_mult=2.5, ema_period=3... | [ROBUST] Profitable on both splits (WFE: 31.0%). |
| 2026-07-21 09:36:01 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.24319.72 (46.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:38:52 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.23798.05 (40.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:42:41 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.17053.80 (38.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:43:42 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.24319.72 (46.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:46:07 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.21872.96 (46.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:52:51 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.23465.85 (45.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 09:53:38 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.-7394.71 (38.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 10:12:44 | Backtest | NIFTY | Strategy_11 | 190 | BUY | N/A (N/A) | Rs.-40095.89 (36.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 10:13:21 | Backtest | NIFTY | Strategy_11 | 190 | BUY | N/A (N/A) | Rs.-86683.72 (30.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 10:15:05 | Backtest | NIFTY | Strategy_11 | 190 | BUY | N/A (N/A) | Rs.-60464.51 (32.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 10:16:03 | Backtest | NIFTY | Strategy_11 | 190 | BUY | N/A (N/A) | Rs.-44014.98 (30.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 10:24:00 | Optimization | NIFTY | Strategy_11 | 190 | BUY | Rs.0.00 (0.0%) | Rs.0.00 (0.0%) | MIN_GAP_PCT=0.5, ENTRY_BAR_INDEX=0.0, WFE=0.00%, points_s... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-21 11:27:10 | Backtest | NIFTY | Strategy_12 | 180 | BUY | N/A (N/A) | Rs.-1921.35 (41.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 11:27:47 | Backtest | NIFTY | Strategy_12 | 180 | BUY | N/A (N/A) | Rs.8491.34 (40.7%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 11:28:53 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.18591.87 (43.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 11:29:22 | Backtest | NIFTY | Strategy_12 | 180 | BUY | N/A (N/A) | Rs.6970.90 (40.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 11:31:16 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-45373.28 (29.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 11:37:46 | Optimization | NIFTY | Strategy_12 | 190 | BUY | Rs.-37787.94 (22.9%) | Rs.3296.27 (33.3%) | rsi_period=56.0, rsi_overbought=65.0, rsi_oversold=35.0, ... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-21 11:38:45 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.21872.96 (46.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 11:39:21 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-45373.28 (29.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 11:39:53 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-37559.42 (43.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 11:40:20 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-35038.71 (20.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 11:40:45 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-43409.80 (23.4%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 17:34:44 | Backtest | NIFTY | Strategy_14 | 180 | BUY | N/A (N/A) | Rs.7013.57 (62.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 17:36:36 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.13208.32 (70.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 17:38:33 | Backtest | NIFTY | Strategy_14 | 180 | BUY | N/A (N/A) | Rs.7013.57 (62.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:04:42 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.13208.32 (70.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:05:22 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.17080.18 (60.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:05:47 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.13014.39 (70.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:07:16 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.14885.15 (60.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:07:46 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.-6214.87 (20.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-21 18:08:17 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.15466.01 (70.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:08:46 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.10239.52 (70.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:09:12 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.15466.01 (70.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:09:55 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.22904.39 (46.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:10:22 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.7770.26 (42.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:24:24 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.13976.59 (44.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:24:51 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.2538.00 (42.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:25:03 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.7920.49 (57.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:25:23 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.7920.49 (57.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-21 18:25:42 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.15466.01 (70.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-22 14:30:24 | Backtest | NIFTY | Strategy_14 | 180 | BUY | N/A (N/A) | Rs.12048.10 (62.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-22 14:33:28 | Backtest | NIFTY | Strategy_13 | 5 | BUY | N/A (N/A) | Rs.-3185.80 (0.0%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-22 17:01:04 | Optimization | NIFTY | Strategy_3 | 190 | BUY | Rs.-14203.10 (19.3%) | Rs.-1259.07 (23.8%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-22 17:23:29 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.-17759.56 (28.8%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-22 17:24:02 | Backtest | NIFTY | Strategy_3 | 190 | BUY | N/A (N/A) | Rs.-35257.47 (25.2%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-22 17:24:50 | Backtest | NIFTY | Strategy_12 | 190 | BUY | N/A (N/A) | Rs.-50063.79 (22.6%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-22 17:25:22 | Backtest | NIFTY | Strategy_13 | 190 | BUY | N/A (N/A) | Rs.-9308.09 (49.3%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-22 17:25:38 | Backtest | NIFTY | Strategy_14 | 190 | BUY | N/A (N/A) | Rs.25014.05 (80.0%) | sl_mult_buy=2.5, tp_mult_buy=3.75, trailing_mult_buy=0.0,... | PROFITABLE |
| 2026-07-23 09:46:30 | Walk-Forward (Rolling) | NIFTY | Strategy_13 | 360 | BUY | Rs.43405.08 (29.7%) | Rs.-17645.43 (30.1%) | supertrend_period=10.0, supertrend_mult=2.5, ema_period=3... | [NOT VIABLE] Combined OOS loses money (WFE: -42.1%). |
| 2026-07-23 10:10:54 | Backtest | NIFTY | Strategy_13 | 360 | BOTH | N/A (N/A) | Rs.32029.14 (30.6%) | sl_mult_buy=2.5, tp_mult_buy=5.0, trailing_mult_buy=0.0, ... | PROFITABLE |
| 2026-07-23 11:11:40 | Walk-Forward (Rolling) | NIFTY | Strategy_13 | 360 | BUY | Rs.-5671.64 (32.4%) | Rs.-18319.69 (42.0%) | supertrend_period=10.0, supertrend_mult=3.0, ema_period=3... | [NOT VIABLE] Combined OOS loses money (WFE: 0.0%). |
| 2026-07-23 11:27:22 | Backtest | NIFTY | Strategy_13 | 200 | BUY | N/A (N/A) | Rs.35953.53 (34.6%) | sl_mult_buy=2.5, tp_mult_buy=5.0, trailing_mult_buy=0.0, ... | PROFITABLE |
| 2026-07-23 11:39:51 | Backtest | NIFTY | Strategy_13 | 200 | BUY | N/A (N/A) | Rs.-50290.71 (37.5%) | sl_mult_buy=2.5, tp_mult_buy=5.0, trailing_mult_buy=0.0, ... | UNPROFITABLE |
| 2026-07-23 11:43:10 | Backtest | NIFTY | Strategy_13 | 200 | BUY | N/A (N/A) | Rs.41806.43 (35.5%) | sl_mult_buy=1.5, tp_mult_buy=6.0, trailing_mult_buy=0.0, ... | PROFITABLE |
| 2026-07-23 11:43:35 | Backtest | NIFTY | Strategy_13 | 200 | BUY | N/A (N/A) | Rs.-7254.78 (37.0%) | sl_mult_buy=1.5, tp_mult_buy=6.0, trailing_mult_buy=0.1, ... | UNPROFITABLE |
| 2026-07-23 11:44:09 | Backtest | NIFTY | Strategy_13 | 200 | BUY | N/A (N/A) | Rs.2501.66 (43.0%) | sl_mult_buy=1.5, tp_mult_buy=6.0, trailing_mult_buy=1.5, ... | PROFITABLE |
| 2026-07-23 11:44:38 | Backtest | NIFTY | Strategy_13 | 200 | BUY | N/A (N/A) | Rs.35953.53 (34.6%) | sl_mult_buy=1.5, tp_mult_buy=5.0, trailing_mult_buy=0.0, ... | PROFITABLE |
| 2026-07-23 12:05:25 | Walk-Forward (Rolling) | NIFTY | Strategy_3 | 360 | BUY | Rs.11421.49 (40.1%) | Rs.-10604.47 (37.4%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: -96.0%). |
| 2026-07-23 12:21:06 | Walk-Forward (Rolling) | NIFTY | Strategy_3 | 360 | BUY | Rs.15144.82 (41.5%) | Rs.-22972.31 (35.6%) | TM_EMA_LONG=30.0, TM_EMA_SHORT=8.0, TM_EMA_BASE=18.0, TM_... | [NOT VIABLE] Combined OOS loses money (WFE: -156.9%). |
| 2026-07-23 13:22:49 | Backtest | NIFTY | Strategy_3 | 200 | BUY | N/A (N/A) | Rs.-22801.86 (20.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-23 13:24:44 | Backtest | NIFTY | Strategy_3 | 200 | BUY | N/A (N/A) | Rs.-22801.86 (20.5%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
| 2026-07-23 13:25:33 | Backtest | NIFTY | Strategy_3 | 200 | BUY | N/A (N/A) | Rs.11471.44 (35.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-23 13:40:00 | Backtest | NIFTY | Strategy_14 | 200 | BUY | N/A (N/A) | Rs.22561.43 (80.0%) | sl_mult_buy=2.5, tp_mult_buy=3.75, trailing_mult_buy=0.0,... | PROFITABLE |
| 2026-07-24 15:44:23 | Backtest | NIFTY | Strategy_14 | 200 | SELL | N/A (N/A) | Rs.19902.09 (30.0%) | sl_mult_buy=2.5, tp_mult_buy=3.75, trailing_mult_buy=0.0,... | PROFITABLE |
| 2026-07-24 16:11:54 | Optimization | NIFTY | Strategy_15 | 180 | SELL | Rs.0.00 (0.0%) | Rs.0.00 (0.0%) | ENTRY_TIME=09:17:00, ATR_PERIOD=14, WFE=0.00%, points_sl_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-24 16:16:16 | Optimization | NIFTY | Strategy_15 | 180 | SELL | Rs.-34061.79 (51.9%) | Rs.391.87 (58.5%) | ENTRY_TIME=09:20:00, ATR_PERIOD=14, WFE=0.00%, points_sl_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-24 16:44:18 | Backtest | NIFTY | Strategy_15 | 200 | SELL | N/A (N/A) | Rs.38493.90 (30.1%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | PROFITABLE |
| 2026-07-24 16:50:54 | Optimization | NIFTY | Strategy_15 | 365 | SELL | Rs.-15106.00 (35.5%) | Rs.-26971.40 (37.7%) | ENTRY_TIME=09:17:00, ATR_PERIOD=14, WFE=0.00%, points_sl_... | [NOT VIABLE] Strategy failed on train split (WFE: 0.0%). |
| 2026-07-24 17:04:06 | Backtest | NIFTY | Strategy_15 | 365 | SELL | N/A (N/A) | Rs.-7227.71 (23.9%) | sl_mult_buy=1.5, tp_mult_buy=2, trailing_mult_buy=0, sl_m... | UNPROFITABLE |
