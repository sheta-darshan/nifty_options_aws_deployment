import os
import pandas as pd
import numpy as np
import datetime
from scipy.stats import rankdata
from .base import BaseStrategy
from .registry import register_strategy

@register_strategy
class Strategy14(BaseStrategy):
    name = "Strategy_14"

    def get_default_params(self) -> dict:
        return {
            "rolling_window": 90,
            "mci_threshold": 75.0,
            "history_file": "backtest_data/daily_mci_history.csv",
            "spot_backup_file": "backtest_data/nifty_spot.csv"
        }

    def get_optimization_grid(self) -> dict:
        return {
            "rolling_window": [90],
            "mci_threshold": [70.0, 75.0, 80.0]
        }

    @staticmethod
    def _calculate_hurst(ts: np.ndarray) -> float:
        if len(ts) < 20:
            return 0.5
        lags = range(2, 20)
        tau = [
            np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags
        ]
        tau = [t if t > 1e-8 else 1e-8 for t in tau]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return float(np.clip(poly[0] * 2.0, 0.0, 1.0))

    @staticmethod
    def _calculate_entropy(ts: np.ndarray) -> float:
        returns = np.diff(ts)
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        counts, _ = np.histogram(returns, bins=10)
        probs = counts / np.sum(counts)
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log2(probs))
        return float(entropy / np.log2(10))

    def _compute_day_metrics(self, group: pd.DataFrame) -> dict:
        closes = group['close'].values
        opens = group['open'].values
        
        net_move = abs(closes[-1] - opens[0])
        path_move = np.sum(np.abs(np.diff(closes)))
        efficiency = net_move / path_move if path_move > 0 else 0.0
        
        log_returns = np.diff(np.log(closes))
        realized_vol = np.std(log_returns) * np.sqrt(375 * 252)
        
        hurst = self._calculate_hurst(closes)
        entropy_norm = self._calculate_entropy(closes)
        
        return {
            'efficiency': efficiency,
            'hurst': hurst,
            'realized_vol': realized_vol,
            'entropy_norm': entropy_norm,
            'net_move_signed': closes[-1] - opens[0]
        }

    def generate_signals(self, df_spot: pd.DataFrame) -> pd.DataFrame:
        if df_spot.empty:
            return df_spot
            
        df = df_spot.copy()
        
        # Paths
        hist_file = self.params.get("history_file", "backtest_data/daily_mci_history.csv")
        spot_backup = self.params.get("spot_backup_file", "backtest_data/nifty_spot.csv")
        
        mci_history_df = None
        
        # 1. Try to load existing daily metrics history
        if os.path.exists(hist_file):
            try:
                mci_history_df = pd.read_csv(hist_file)
                mci_history_df['date'] = pd.to_datetime(mci_history_df['date']).dt.date
            except Exception:
                mci_history_df = None
                
        # 2. If daily metrics history doesn't exist, build it from spot_backup
        if mci_history_df is None or mci_history_df.empty:
            if os.path.exists(spot_backup):
                try:
                    print(f"[Strategy_14] Rebuilding daily MCI metrics database from {spot_backup}...")
                    spot_df = pd.read_csv(spot_backup)
                    timestamp_col = 'timestamp' if 'timestamp' in spot_df.columns else spot_df.columns[0]
                    spot_df['datetime'] = pd.to_datetime(spot_df[timestamp_col])
                    spot_df['date'] = spot_df['datetime'].dt.date
                    spot_df['time'] = spot_df['datetime'].dt.strftime("%H:%M")
                    # official market hours
                    spot_df = spot_df[(spot_df['time'] >= '09:15') & (spot_df['time'] <= '15:30')].copy()
                    
                    records = []
                    for date, group in spot_df.groupby('date'):
                        if len(group) < 100:
                            continue
                        metrics = self._compute_day_metrics(group)
                        metrics['date'] = date
                        records.append(metrics)
                        
                    if records:
                        mci_history_df = pd.DataFrame(records)
                        # Save
                        os.makedirs(os.path.dirname(hist_file), exist_ok=True)
                        mci_history_df.to_csv(hist_file, index=False)
                        print(f"[Strategy_14] Saved {len(mci_history_df)} daily records to {hist_file}")
                except Exception as e:
                    print(f"[Strategy_14] Failed to build daily MCI history: {e}")
                    
        # Fallback to dynamic loop if still empty
        if mci_history_df is None:
            mci_history_df = pd.DataFrame(columns=['date', 'efficiency', 'hurst', 'realized_vol', 'entropy_norm', 'net_move_signed'])
            
        # 3. Process new days present in the input df_spot
        # Ensure timestamp is index-compatible
        temp_input = df.reset_index()
        ts_col = 'timestamp' if 'timestamp' in temp_input.columns else temp_input.columns[0]
        temp_input['datetime'] = pd.to_datetime(temp_input[ts_col])
        temp_input['date'] = temp_input['datetime'].dt.date
        temp_input['time'] = temp_input['datetime'].dt.strftime("%H:%M")
        temp_input = temp_input[(temp_input['time'] >= '09:15') & (temp_input['time'] <= '15:30')].copy()
        
        known_dates = set(mci_history_df['date'].values)
        updated = False
        
        for date, group in temp_input.groupby('date'):
            if date in known_dates:
                continue
            if len(group) < 100:
                continue
                
            metrics = self._compute_day_metrics(group)
            metrics['date'] = date
            mci_history_df = pd.concat([mci_history_df, pd.DataFrame([metrics])], ignore_index=True)
            known_dates.add(date)
            updated = True
            
        if updated:
            try:
                os.makedirs(os.path.dirname(hist_file), exist_ok=True)
                mci_history_df.to_csv(hist_file, index=False)
            except Exception as e:
                print(f"[Strategy_14] Failed to save updated history file: {e}")
                
        # Sort history by date to ensure proper rolling calculation
        mci_history_df = mci_history_df.sort_values('date').reset_index(drop=True)
        
        # 4. Calculate Rolling Percentile Ranks on the complete daily database
        n = len(mci_history_df)
        w = int(self.params.get("rolling_window", 90))
        mci_thresh = float(self.params.get("mci_threshold", 75.0))
        
        if n < w + 2:
            # Not enough history to calculate ranks
            df['Signal'] = 0
            df['Signal_Source'] = "None"
            return df
            
        eff_ranks = np.zeros(n)
        hurst_ranks = np.zeros(n)
        vol_ranks = np.zeros(n)
        entropy_ranks = np.zeros(n)
        
        for i in range(n):
            if i < w:
                eff_ranks[i] = 50.0
                hurst_ranks[i] = 50.0
                vol_ranks[i] = 50.0
                entropy_ranks[i] = 50.0
                continue
            eff_ranks[i] = pd.Series(mci_history_df['efficiency'].iloc[i-w:i+1]).rank(pct=True).iloc[-1] * 100.0
            hurst_ranks[i] = pd.Series(mci_history_df['hurst'].iloc[i-w:i+1]).rank(pct=True).iloc[-1] * 100.0
            vol_ranks[i] = pd.Series(mci_history_df['realized_vol'].iloc[i-w:i+1]).rank(pct=True).iloc[-1] * 100.0
            entropy_ranks[i] = (1.0 - pd.Series(mci_history_df['entropy_norm'].iloc[i-w:i+1]).rank(pct=True).iloc[-1]) * 100.0
            
        mci_history_df['MCI'] = 0.35 * eff_ranks + 0.25 * hurst_ranks + 0.20 * vol_ranks + 0.20 * entropy_ranks
        mci_history_df['prev_MCI'] = mci_history_df['MCI'].shift(1)
        mci_history_df['prev_net_move_signed'] = mci_history_df['net_move_signed'].shift(1)
        
        # Create mapping dictionary: date -> signal
        date_signals = {}
        for idx, row in mci_history_df.dropna().iterrows():
            date = row['date']
            prev_mci = row['prev_MCI']
            prev_net_move = row['prev_net_move_signed']
            
            if prev_mci >= mci_thresh:
                date_signals[date] = -1 if prev_net_move > 0 else 1
                
        # Initialize output
        df['Signal'] = 0
        df['Signal_Source'] = "None"
        
        temp_df2 = pd.DataFrame(index=df.index)
        temp_df2['date'] = temp_df2.index.date
        
        for date, sig in date_signals.items():
            day_mask = temp_df2['date'] == date
            if not day_mask.any():
                continue
            day_candles = temp_df2[day_mask]
            target_time = day_candles.index[0]
            df.loc[target_time, 'Signal'] = sig
            df.loc[target_time, 'Signal_Source'] = "MCI_REVERSAL"
            
        return df
