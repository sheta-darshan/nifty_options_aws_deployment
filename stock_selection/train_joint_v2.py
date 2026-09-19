"""
stock_selection/train_joint_v2.py

Institutional True Dual-Head (Joint) Model Training & Calibration
==================================================================
Trains and calibrates a dual-head quantitative model for stock selection:
  - Head 1 (Volatility Expansion): P(Range_{T+1} >= 1.3 * ATR_14)
  - Head 2 (Directional Edge):     P(Close_{T+1} > Close_T)

Employs:
  - Feature Matrix 2.0 (26 clean institutional alpha features)
  - 5-Fold Walk-Forward Cross Validation with 5-day purged embargo
  - Isotonic Probability Calibration (CalibratedClassifierCV)
  - Bidirectional Alpha Ranking Validation (IC, Top-K Hit Rates, Brier Score)
  - Model serialization to stock_selection/models/global_dual_head_joint_model.pkl
"""

import os
import sys
import argparse
import json
import gzip
import time
import warnings
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from multiprocessing import Pool, cpu_count

from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score, precision_score, recall_score, f1_score
from sklearn.calibration import CalibratedClassifierCV
from xgboost import XGBClassifier
import joblib

# Setup root path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from stock_selection.feature_matrix_v2 import FEATURE_NAMES_V2, extract_features_v2_df

DATA_DIR = os.path.join(BASE_DIR, "backtest_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "stock_selection", "data")
MODEL_DIR = os.path.join(BASE_DIR, "stock_selection", "models")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

CACHE_FILE = os.path.join(OUTPUT_DIR, "fno_v2_feature_matrix.pkl.gz")
MODEL_SAVE_PATH = os.path.join(MODEL_DIR, "global_dual_head_joint_model.pkl")
SCORECARD_PATH = os.path.join(BASE_DIR, "stock_selection", "scorecard_joint_v2.json")


def load_nifty_daily() -> pd.DataFrame:
    """Loads NIFTY spot 1m data and aggregates to daily bars."""
    nifty_path = os.path.join(DATA_DIR, "nifty_spot.csv")
    if not os.path.exists(nifty_path):
        print("[WARNING] nifty_spot.csv not found in backtest_data. RS features will be neutral.")
        return None
    try:
        df = pd.read_csv(nifty_path)
        col = 'timestamp' if 'timestamp' in df.columns else ('start_time' if 'start_time' in df.columns else df.columns[0])
        df[col] = pd.to_datetime(df[col], errors='coerce')
        df.set_index(col, inplace=True)
        df = df[df.index.notna()].sort_index()
        df = df.between_time('09:15', '15:30')
        df['date'] = df.index.date
        daily = df.groupby('date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        return daily
    except Exception as e:
        print(f"[WARNING] Error loading NIFTY spot data: {e}")
        return None


def worker_extract_stock(args):
    """Worker task for multiprocessing feature extraction."""
    symbol, spot_path, nifty_daily_df, min_date = args
    try:
        if not os.path.exists(spot_path):
            return None
        df = pd.read_csv(spot_path)
        col = 'timestamp' if 'timestamp' in df.columns else ('start_time' if 'start_time' in df.columns else df.columns[0])
        df[col] = pd.to_datetime(df[col], errors='coerce')
        df.set_index(col, inplace=True)
        df = df[df.index.notna()].sort_index()
        df = df.between_time('09:15', '15:30')

        if min_date:
            df = df[df.index >= min_date]

        if len(df) < 500:
            return None

        feat_df = extract_features_v2_df(df, nifty_daily=nifty_daily_df)
        if feat_df is None or feat_df.empty:
            return None

        feat_df['symbol'] = symbol.upper()
        feat_df['date'] = feat_df.index
        return feat_df
    except Exception as e:
        return None


def build_or_load_dataset(years: int = 3, n_stocks: int = 150, force_extract: bool = False, workers: int = 4) -> pd.DataFrame:
    """Builds or loads cached Feature Matrix 2.0 dataset across liquid F&O stocks."""
    if not force_extract and os.path.exists(CACHE_FILE):
        print(f"[INFO] Loading cached dataset from {CACHE_FILE}...")
        try:
            with gzip.open(CACHE_FILE, 'rb') as f:
                df = joblib.load(f)
            print(f"[INFO] Cached dataset loaded: {len(df)} samples across {df['symbol'].nunique()} stocks.")
            return df
        except Exception as e:
            print(f"[WARNING] Failed to load cache: {e}. Rebuilding...")

    print(f"[INFO] Extracting Feature Matrix 2.0 for up to {n_stocks} F&O stocks over {years} years...")
    fno_path = os.path.join(BASE_DIR, "stock_selection", "fno_registry.json")
    if not os.path.exists(fno_path):
        raise FileNotFoundError(f"{fno_path} not found.")

    with open(fno_path, 'r', encoding='utf-8') as f:
        fno_dict = json.load(f)

    # Filter to available spot files
    eligible = []
    for sym in fno_dict.keys():
        s_path = os.path.join(DATA_DIR, f"{sym.lower()}_spot.csv")
        if os.path.exists(s_path):
            eligible.append((sym, s_path))

    eligible = eligible[:n_stocks]
    print(f"[INFO] Found {len(eligible)} eligible F&O stocks in {DATA_DIR}.")

    nifty_daily = load_nifty_daily()
    min_date = datetime.now() - timedelta(days=years * 365 + 60)

    tasks = [(sym, s_path, nifty_daily, min_date) for sym, s_path in eligible]
    results = []
    t0 = time.time()

    print(f"[INFO] Launching parallel extraction with {workers} workers...")
    with Pool(processes=workers) as pool:
        for res in pool.imap_unordered(worker_extract_stock, tasks):
            if res is not None and not res.empty:
                results.append(res)
                if len(results) % 25 == 0 or len(results) == len(tasks):
                    print(f"  Processed {len(results)}/{len(tasks)} stocks ({time.time() - t0:.1f}s)...")

    if not results:
        raise ValueError("No feature data could be extracted from available stocks.")

    stacked_df = pd.concat(results, ignore_index=True)
    stacked_df = stacked_df.sort_values(by=['date', 'symbol']).reset_index(drop=True)

    print(f"[INFO] Total extracted samples: {len(stacked_df)} across {stacked_df['symbol'].nunique()} stocks in {time.time() - t0:.1f}s.")
    print(f"[INFO] Saving cache to {CACHE_FILE}...")
    with gzip.open(CACHE_FILE, 'wb') as f:
        joblib.dump(stacked_df, f, compress=3)

    return stacked_df


def evaluate_dual_head_walk_forward(df: pd.DataFrame, n_splits: int = 5, embargo_days: int = 5):
    """
    Evaluates Dual-Head model using chronological walk-forward cross validation with 5-day purged embargo.
    """
    unique_dates = sorted(df['date'].unique())
    n_dates = len(unique_dates)
    print(f"[INFO] Running {n_splits}-Fold Walk-Forward Cross Validation over {n_dates} unique trading days...")

    fold_size = n_dates // (n_splits + 1)
    
    vol_auc_list = []
    vol_brier_list = []
    dir_auc_list = []
    dir_brier_list = []
    ic_long_list = []
    ic_short_list = []
    top3_long_ret_list = []
    top3_short_ret_list = []
    universe_ret_list = []

    for fold in range(1, n_splits + 1):
        tr_end_idx = fold * fold_size
        te_start_idx = tr_end_idx + embargo_days
        te_end_idx = min(te_start_idx + fold_size, n_dates)

        if te_start_idx >= n_dates:
            break

        tr_dates = set(unique_dates[:tr_end_idx])
        te_dates = set(unique_dates[te_start_idx:te_end_idx])

        train_df = df[df['date'].isin(tr_dates)]
        test_df = df[df['date'].isin(te_dates)]

        X_train = train_df[FEATURE_NAMES_V2]
        y_train_vol = train_df['target_volatility'].values
        y_train_dir = train_df['target_direction'].values

        X_test = test_df[FEATURE_NAMES_V2]
        y_test_vol = test_df['target_volatility'].values
        y_test_dir = test_df['target_direction'].values

        # 1. Train Head 1: Volatility Expansion
        neg_v = np.sum(y_train_vol == 0)
        pos_v = np.sum(y_train_vol == 1)
        scale_pos_v = float(neg_v) / float(pos_v + 1e-8)

        base_vol = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_v,
            random_state=42,
            eval_metric='logloss'
        )
        base_vol.fit(X_train, y_train_vol)
        cal_vol = CalibratedClassifierCV(estimator=base_vol, method='isotonic', cv=3)
        cal_vol.fit(X_train, y_train_vol)

        probs_vol = cal_vol.predict_proba(X_test)[:, 1]

        # 2. Train Head 2: Directional Edge
        neg_d = np.sum(y_train_dir == 0)
        pos_d = np.sum(y_train_dir == 1)
        scale_pos_d = float(neg_d) / float(pos_d + 1e-8)

        base_dir = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_d,
            random_state=42,
            eval_metric='logloss'
        )
        base_dir.fit(X_train, y_train_dir)
        cal_dir = CalibratedClassifierCV(estimator=base_dir, method='isotonic', cv=3)
        cal_dir.fit(X_train, y_train_dir)

        probs_dir = cal_dir.predict_proba(X_test)[:, 1]

        # Metrics for fold
        vol_auc = roc_auc_score(y_test_vol, probs_vol)
        vol_brier = brier_score_loss(y_test_vol, probs_vol)
        dir_auc = roc_auc_score(y_test_dir, probs_dir)
        dir_brier = brier_score_loss(y_test_dir, probs_dir)

        vol_auc_list.append(vol_auc)
        vol_brier_list.append(vol_brier)
        dir_auc_list.append(dir_auc)
        dir_brier_list.append(dir_brier)

        # Joint Bidirectional Scores & Portfolio Simulation on Fold Test Set
        fold_test = test_df.copy()
        fold_test['p_vol'] = probs_vol
        fold_test['p_dir'] = probs_dir

        rs_norm = (fold_test['rs_nifty_5d'] / 100.0).clip(-0.5, 0.5)
        fold_test['joint_score_long'] = fold_test['p_vol'] * fold_test['p_dir'] * (1.0 + rs_norm)
        fold_test['joint_score_short'] = fold_test['p_vol'] * (1.0 - fold_test['p_dir']) * (1.0 - rs_norm)

        # Daily IC and Top-K returns
        for d, grp in fold_test.groupby('date'):
            if len(grp) < 10:
                continue
            # IC
            ic_l, _ = spearmanr(grp['joint_score_long'], grp['next_ret'])
            ic_s, _ = spearmanr(grp['joint_score_short'], -grp['next_ret'])
            if not np.isnan(ic_l):
                ic_long_list.append(ic_l)
            if not np.isnan(ic_s):
                ic_short_list.append(ic_s)

            # Top 3 Longs
            top3_l = grp.nlargest(3, 'joint_score_long')
            # Top 3 Shorts
            top3_s = grp.nlargest(3, 'joint_score_short')

            top3_long_ret_list.append(top3_l['next_ret'].mean())
            top3_short_ret_list.append(top3_s['next_ret'].mean())
            universe_ret_list.append(grp['next_ret'].mean())

        print(f"  Fold {fold}/{n_splits} | Vol AUC: {vol_auc:.4f} (Brier: {vol_brier:.4f}) | Dir AUC: {dir_auc:.4f} (Brier: {dir_brier:.4f})")

    avg_vol_auc = float(np.mean(vol_auc_list))
    avg_dir_auc = float(np.mean(dir_auc_list))
    avg_vol_brier = float(np.mean(vol_brier_list))
    avg_dir_brier = float(np.mean(dir_brier_list))
    avg_ic_long = float(np.mean(ic_long_list)) if ic_long_list else 0.0
    avg_ic_short = float(np.mean(ic_short_list)) if ic_short_list else 0.0
    avg_top3_l_ret = float(np.mean(top3_long_ret_list)) if top3_long_ret_list else 0.0
    avg_top3_s_ret = float(np.mean(top3_short_ret_list)) if top3_short_ret_list else 0.0
    avg_univ_ret = float(np.mean(universe_ret_list)) if universe_ret_list else 0.0

    print("\n" + "=" * 70)
    print("           OUT-OF-SAMPLE WALK-FORWARD VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Head 1 (Volatility Expansion)  : ROC-AUC = {avg_vol_auc:.4f} | Brier Score = {avg_vol_brier:.4f}")
    print(f"Head 2 (Directional Edge)      : ROC-AUC = {avg_dir_auc:.4f} | Brier Score = {avg_dir_brier:.4f}")
    print(f"Information Coefficient (IC)   : Long IC = {avg_ic_long:+.4f} | Short IC = {avg_ic_short:+.4f}")
    print(f"Top-3 Long Avg Next-Day Return : {avg_top3_l_ret:+.3f}% (Universe Avg: {avg_univ_ret:+.3f}%) -> Alpha: {avg_top3_l_ret - avg_univ_ret:+.3f}%")
    print(f"Top-3 Short Avg Next-Day Return: {avg_top3_s_ret:+.3f}% (Universe Avg: {avg_univ_ret:+.3f}%) -> Alpha: {avg_univ_ret - avg_top3_s_ret:+.3f}%")
    print("=" * 70)

    return {
        "vol_auc": avg_vol_auc,
        "vol_brier": avg_vol_brier,
        "dir_auc": avg_dir_auc,
        "dir_brier": avg_dir_brier,
        "ic_long": avg_ic_long,
        "ic_short": avg_ic_short,
        "top3_long_alpha": avg_top3_l_ret - avg_univ_ret,
        "top3_short_alpha": avg_univ_ret - avg_top3_s_ret
    }


def train_and_save_final_model(df: pd.DataFrame, cv_metrics: dict):
    """Trains calibrated dual-head models on full dataset and serializes artifact."""
    print("\n[INFO] Fitting final calibrated Dual-Head model on full dataset...")

    X = df[FEATURE_NAMES_V2]
    y_vol = df['target_volatility'].values
    y_dir = df['target_direction'].values

    # Volatility Model
    neg_v = np.sum(y_vol == 0)
    pos_v = np.sum(y_vol == 1)
    scale_pos_v = float(neg_v) / float(pos_v + 1e-8)

    base_vol = XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_v,
        random_state=42,
        eval_metric='logloss'
    )
    cal_vol = CalibratedClassifierCV(estimator=base_vol, method='isotonic', cv=5)
    cal_vol.fit(X, y_vol)

    # Direction Model
    neg_d = np.sum(y_dir == 0)
    pos_d = np.sum(y_dir == 1)
    scale_pos_d = float(neg_d) / float(pos_d + 1e-8)

    base_dir = XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_d,
        random_state=42,
        eval_metric='logloss'
    )
    cal_dir = CalibratedClassifierCV(estimator=base_dir, method='isotonic', cv=5)
    cal_dir.fit(X, y_dir)

    model_bundle = {
        "version": "2.0.0",
        "architecture": "True Dual-Head Joint Classifier with Isotonic Probability Calibration",
        "features": FEATURE_NAMES_V2,
        "volatility_model": cal_vol,
        "direction_model": cal_dir,
        "vol_threshold": 0.40,
        "dir_threshold": 0.50,
        "validation_metrics": cv_metrics,
        "trained_at": datetime.now().isoformat(),
        "num_samples": len(df),
        "num_stocks": int(df['symbol'].nunique()),
        "universe": "NSE F&O Liquid Universe"
    }

    joblib.dump(model_bundle, MODEL_SAVE_PATH)
    print(f"[SUCCESS] Global Dual-Head Joint Model saved to:\n  -> {MODEL_SAVE_PATH}")

    # Write Scorecard JSON
    scorecard_data = {
        "status": "trained",
        "version": "2.0.0",
        "model_file": os.path.basename(MODEL_SAVE_PATH),
        "trained_at": datetime.now().isoformat(),
        "num_samples": len(df),
        "num_stocks": int(df['symbol'].nunique()),
        "features": FEATURE_NAMES_V2,
        "metrics": cv_metrics
    }
    with open(SCORECARD_PATH, 'w', encoding='utf-8') as f:
        json.dump(scorecard_data, f, indent=2)
    print(f"[SUCCESS] Scorecard saved to:\n  -> {SCORECARD_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Train True Dual-Head (Joint) Model with Feature Matrix 2.0")
    parser.add_argument("--years", type=int, default=3, help="Lookback years of data (default: 3)")
    parser.add_argument("--n-stocks", type=int, default=150, help="Number of F&O stocks to process (default: 150)")
    parser.add_argument("--force-extract", action="store_true", help="Force re-extraction ignoring cache")
    parser.add_argument("--workers", type=int, default=min(cpu_count(), 6), help="Parallel extraction workers")
    args = parser.parse_args()

    df = build_or_load_dataset(
        years=args.years,
        n_stocks=args.n_stocks,
        force_extract=args.force_extract,
        workers=args.workers
    )

    cv_metrics = evaluate_dual_head_walk_forward(df, n_splits=5, embargo_days=5)
    train_and_save_final_model(df, cv_metrics)


if __name__ == "__main__":
    main()
