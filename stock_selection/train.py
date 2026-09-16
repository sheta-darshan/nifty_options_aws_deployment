import os
import sys
import argparse
import glob
import json
import warnings
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import spearmanr
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from multiprocessing import Pool, cpu_count

# Silence XGBoost use_label_encoder warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*use_label_encoder.*")

# Setup project root pathing
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

FEATURE_DIR = os.path.join(BASE_DIR, "stock_selection", "data")
MODEL_DIR = os.path.join(BASE_DIR, "stock_selection", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

def optimize_decision_threshold(y_val, probs_val, target_name):
    """
    Optimizes the decision threshold:
    - For balanced targets ('direction'): Uses Balanced Macro F1 across [0.40, 0.60] to prevent degenerate 100% positive predictions.
    - For imbalanced targets ('volatility', 'gap', 'strategy'): Uses Positive-class F1 across [0.05, 0.80].
    """
    from sklearn.metrics import f1_score
    best_t = 0.50
    best_score = 0.0
    
    if target_name == "direction":
        for t in np.arange(0.40, 0.61, 0.01):
            preds = (probs_val >= t).astype(int)
            f1_pos = f1_score(y_val, preds, zero_division=0)
            f1_neg = f1_score(1 - y_val, 1 - preds, zero_division=0)
            macro_f1 = (f1_pos + f1_neg) / 2.0
            if macro_f1 > best_score:
                best_score = macro_f1
                best_t = t
    else:
        for t in np.arange(0.05, 0.81, 0.01):
            preds = (probs_val >= t).astype(int)
            val_f1 = f1_score(y_val, preds, zero_division=0)
            if val_f1 > best_score:
                best_score = val_f1
                best_t = t
                
    return round(float(best_t), 2), best_score

def train_single_stock(filepath, target_name):
    symbol = os.path.basename(filepath).replace("_features.csv", "").upper()
    
    try:
        df = pd.read_csv(filepath)
        if df.empty or len(df) < 100:  # Need enough days for 5-fold walk-forward validation
            return symbol, {"status": "skipped", "reason": "Insufficient days of data (need >= 100 days)"}

        target_col = f"target_{target_name}"
        if target_col not in df.columns:
            return symbol, {"status": "skipped", "reason": f"Target column {target_col} missing"}

        # Sort chronologically
        df = df.sort_values(by="date").reset_index(drop=True)
        
        # Split features and labels
        all_feature_cols = [c for c in df.columns if c not in ["date", "target_direction", "target_gap", "target_volatility", "target_strategy"]]
        X_all = df[all_feature_cols]
        y_all = df[target_col]

        # Import ML libraries
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        from sklearn.model_selection import TimeSeriesSplit
        from xgboost import XGBClassifier
        import joblib

        # 1. Setup 5-Fold Walk-Forward Cross-Validation
        tscv = TimeSeriesSplit(n_splits=5)
        
        fold_rf_val_f1s = []
        fold_rf_test_metrics = []
        fold_rf_thresholds = []
        
        fold_xgb_val_f1s = []
        fold_xgb_test_metrics = []
        fold_xgb_thresholds = []
        
        for fold, (train_index, test_index) in enumerate(tscv.split(X_all)):
            # Further split train_index into train and validation with 5-day purged embargo gap
            fold_size = len(train_index)
            val_split = int(fold_size * 0.85)
            embargo = 5
            
            idx_train = train_index[:max(1, val_split - embargo)]
            idx_val = train_index[val_split:max(val_split + 1, fold_size - embargo)]
            idx_test = test_index
            
            X_tr_raw, y_tr = X_all.iloc[idx_train], y_all.iloc[idx_train]
            X_va_raw, y_va = X_all.iloc[idx_val], y_all.iloc[idx_val]
            X_te_raw, y_te = X_all.iloc[idx_test], y_all.iloc[idx_test]
            
            # Guard class diversity
            if len(np.unique(y_tr)) < 2 or len(np.unique(y_va)) < 2 or len(np.unique(y_te)) < 2:
                continue # Skip this fold if split lacks class diversity
                
            # --- Feature Selection INSIDE Fold ---
            rf_selector = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
            rf_selector.fit(X_tr_raw, y_tr)
            
            importances = rf_selector.feature_importances_
            indices = np.argsort(importances)[::-1]
            top_k = min(25, len(all_feature_cols))
            fold_selected_features = [all_feature_cols[indices[i]] for i in range(top_k)]
            
            X_tr = X_tr_raw[fold_selected_features]
            X_va = X_va_raw[fold_selected_features]
            X_te = X_te_raw[fold_selected_features]
            
            # --- Random Forest FOLD ---
            rf = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
            rf.fit(X_tr, y_tr)
            
            rf_val_probs = rf.predict_proba(X_va)[:, 1]
            rf_best_t, rf_best_val_f1 = optimize_decision_threshold(y_va, rf_val_probs, target_name)
                    
            rf_test_probs = rf.predict_proba(X_te)[:, 1]
            rf_test_preds = (rf_test_probs >= rf_best_t).astype(int)
            rf_test_metrics = {
                "accuracy": accuracy_score(y_te, rf_test_preds),
                "precision": precision_score(y_te, rf_test_preds, zero_division=0),
                "recall": recall_score(y_te, rf_test_preds, zero_division=0),
                "f1": f1_score(y_te, rf_test_preds, zero_division=0)
            }
            
            fold_rf_thresholds.append(rf_best_t)
            fold_rf_val_f1s.append(rf_best_val_f1)
            fold_rf_test_metrics.append(rf_test_metrics)
            
            # --- XGBoost FOLD ---
            neg_count = np.sum(y_tr == 0)
            pos_count = np.sum(y_tr == 1)
            ratio = float(neg_count) / float(pos_count + 1e-8)
            
            xgb = XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                scale_pos_weight=ratio,
                random_state=42,
                eval_metric='logloss'
            )
            xgb.fit(X_tr, y_tr)
            
            xgb_val_probs = xgb.predict_proba(X_va)[:, 1]
            xgb_best_t, xgb_best_val_f1 = optimize_decision_threshold(y_va, xgb_val_probs, target_name)
                    
            xgb_test_probs = xgb.predict_proba(X_te)[:, 1]
            xgb_test_preds = (xgb_test_probs >= xgb_best_t).astype(int)
            xgb_test_metrics = {
                "accuracy": accuracy_score(y_te, xgb_test_preds),
                "precision": precision_score(y_te, xgb_test_preds, zero_division=0),
                "recall": recall_score(y_te, xgb_test_preds, zero_division=0),
                "f1": f1_score(y_te, xgb_test_preds, zero_division=0)
            }
            
            fold_xgb_thresholds.append(xgb_best_t)
            fold_xgb_val_f1s.append(xgb_best_val_f1)
            fold_xgb_test_metrics.append(xgb_test_metrics)
            
        # Ensure we evaluated successfully on at least 3 folds
        if len(fold_rf_val_f1s) < 3:
            return symbol, {"status": "skipped", "reason": "Insufficient folds with class diversity during Walk-Forward validation"}
            
        # 2. Model Architecture Selection (Compare Folds Average Validation F1)
        mean_rf_val_f1 = np.mean(fold_rf_val_f1s)
        mean_xgb_val_f1 = np.mean(fold_xgb_val_f1s)
        
        if mean_xgb_val_f1 >= mean_rf_val_f1:
            best_model_name = "xgboost"
            ensemble_test_metrics = fold_xgb_test_metrics
            avg_threshold = np.mean(fold_xgb_thresholds)
        else:
            best_model_name = "random_forest"
            ensemble_test_metrics = fold_rf_test_metrics
            avg_threshold = np.mean(fold_rf_thresholds)
            
        # Compute mean test metrics across CV folds
        avg_test_acc = np.mean([m["accuracy"] for m in ensemble_test_metrics])
        avg_test_prec = np.mean([m["precision"] for m in ensemble_test_metrics])
        avg_test_rec = np.mean([m["recall"] for m in ensemble_test_metrics])
        avg_test_f1 = np.mean([m["f1"] for m in ensemble_test_metrics])
        
        # 3. Train Final Model on 100% of historical data
        # Feature Selection on full history
        rf_final_selector = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
        rf_final_selector.fit(X_all, y_all)
        
        final_importances = rf_final_selector.feature_importances_
        final_indices = np.argsort(final_importances)[::-1]
        top_k_final = min(25, len(all_feature_cols))
        final_selected_features = [all_feature_cols[final_indices[i]] for i in range(top_k_final)]
        
        X_final_all = X_all[final_selected_features]
        
        # Optimize threshold on final 15% validation split
        final_split = int(len(df) * 0.85)
        X_final_tr, y_final_tr = X_final_all.iloc[:final_split], y_all.iloc[:final_split]
        X_final_va, y_final_va = X_final_all.iloc[final_split:], y_all.iloc[final_split:]
        
        if best_model_name == "random_forest":
            final_model = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
            final_model.fit(X_final_tr, y_final_tr)
            final_val_probs = final_model.predict_proba(X_final_va)[:, 1]
            final_opt_threshold, final_best_val_f1 = optimize_decision_threshold(y_final_va, final_val_probs, target_name)
            
            # Retrain model on 100% of historical data
            final_model = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
            final_model.fit(X_final_all, y_all)
            
        else: # xgboost
            neg_count = np.sum(y_final_tr == 0)
            pos_count = np.sum(y_final_tr == 1)
            ratio = float(neg_count) / float(pos_count + 1e-8)
            
            final_model = XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                scale_pos_weight=ratio,
                random_state=42,
                eval_metric='logloss'
            )
            final_model.fit(X_final_tr, y_final_tr)
            final_val_probs = final_model.predict_proba(X_final_va)[:, 1]
            final_opt_threshold, final_best_val_f1 = optimize_decision_threshold(y_final_va, final_val_probs, target_name)
            
            # Retrain model on 100% of historical data
            neg_all = np.sum(y_all == 0)
            pos_all = np.sum(y_all == 1)
            ratio_all = float(neg_all) / float(pos_all + 1e-8)
            
            final_model = XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                scale_pos_weight=ratio_all,
                random_state=42,
                eval_metric='logloss'
            )
            final_model.fit(X_final_all, y_all)

        # Save serialized final model package
        model_path = os.path.join(MODEL_DIR, f"{symbol.lower()}_best_model_{target_name}.pkl")
        model_pkg = {
            "features": final_selected_features,
            "model": final_model,
            "opt_threshold": float(final_opt_threshold),
            "best_model_type": best_model_name,
            "test_precision": float(avg_test_prec)
        }
        joblib.dump(model_pkg, model_path)
        
        result = {
            "status": "trained",
            "best_model": best_model_name,
            "validation_methodology": "5-fold walk-forward cross-validation with 5-day purged embargo",
            "metrics": {
                "oos_accuracy": round(float(avg_test_acc), 4),
                "oos_precision": round(float(avg_test_prec), 4),
                "oos_recall": round(float(avg_test_rec), 4),
                "oos_f1_score": round(float(avg_test_f1), 4)
            },
            "opt_threshold": round(float(final_opt_threshold), 3),
            "total_days": len(df),
            "num_folds": 5,
            "positive_class_ratio": round(float(y_all.mean()), 4),
            "selected_features": final_selected_features,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return symbol, result
        
    except Exception as e:
        import traceback
        return symbol, {"status": "error", "error": f"{e}\n{traceback.format_exc()}"}

def train_pooled_model(target_files, target_name):
    print(f"[INFO] Initializing Stacked Pooled Model training on {len(target_files)} symbols...")
    
    all_dfs = []
    for filepath in target_files:
        symbol = os.path.basename(filepath).replace("_features.csv", "").upper()
        try:
            df = pd.read_csv(filepath)
            if df.empty or len(df) < 100:
                continue
            target_col = f"target_{target_name}"
            if target_col not in df.columns:
                continue
            df["symbol"] = symbol
            all_dfs.append(df)
        except Exception:
            pass
            
    if not all_dfs:
        print("[ERROR] No valid feature files found to stack for pooled training.")
        return
        
    df_stacked = pd.concat(all_dfs, ignore_index=True)
    # Sort chronologically by date
    df_stacked = df_stacked.sort_values(by="date").reset_index(drop=True)
    
    target_col = f"target_{target_name}"
    all_feature_cols = [c for c in df_stacked.columns if c not in ["date", "symbol", "target_direction", "target_gap", "target_volatility", "target_strategy"]]
    
    X_all = df_stacked[all_feature_cols]
    y_all = df_stacked[target_col]
    
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.model_selection import TimeSeriesSplit
    from xgboost import XGBClassifier
    import joblib
    
    unique_dates = sorted(df_stacked['date'].unique())
    if len(unique_dates) < 50:
        print("[ERROR] Insufficient unique dates in stacked dataset for walk-forward validation.")
        return
        
    tscv = TimeSeriesSplit(n_splits=5)
    
    fold_rf_val_f1s = []
    fold_rf_test_metrics = []
    fold_rf_thresholds = []
    
    fold_xgb_val_f1s = []
    fold_xgb_test_metrics = []
    fold_xgb_thresholds = []
    
    print(f"[INFO] Running 5-fold Date-Based Walk-Forward Cross-Validation on {len(unique_dates)} dates...")
    
    for fold, (train_index, test_index) in enumerate(tscv.split(unique_dates)):
        train_dates = set([unique_dates[i] for i in train_index])
        test_dates = set([unique_dates[i] for i in test_index])
        
        train_dates_list = sorted(list(train_dates))
        val_split = int(len(train_dates_list) * 0.85)
        embargo_days = 5
        
        # Apply 5-day purged embargo between train -> val and val -> test
        tr_dates_end = max(1, val_split - embargo_days)
        va_dates_end = max(val_split + 1, len(train_dates_list) - embargo_days)
        
        tr_dates = set(train_dates_list[:tr_dates_end])
        va_dates = set(train_dates_list[val_split:va_dates_end])
        
        train_mask = df_stacked['date'].isin(tr_dates)
        val_mask = df_stacked['date'].isin(va_dates)
        test_mask = df_stacked['date'].isin(test_dates)
        
        X_tr_raw = df_stacked.loc[train_mask, all_feature_cols]
        y_tr = df_stacked.loc[train_mask, target_col]
        
        X_va_raw = df_stacked.loc[val_mask, all_feature_cols]
        y_va = df_stacked.loc[val_mask, target_col]
        
        X_te_raw = df_stacked.loc[test_mask, all_feature_cols]
        y_te = df_stacked.loc[test_mask, target_col]
        
        if len(np.unique(y_tr)) < 2 or len(np.unique(y_va)) < 2 or len(np.unique(y_te)) < 2:
            continue
            
        # Feature Selection inside fold
        rf_selector = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
        rf_selector.fit(X_tr_raw, y_tr)
        
        importances = rf_selector.feature_importances_
        indices = np.argsort(importances)[::-1]
        top_k = min(25, len(all_feature_cols))
        fold_selected_features = [all_feature_cols[indices[i]] for i in range(top_k)]
        
        X_tr = X_tr_raw[fold_selected_features]
        X_va = X_va_raw[fold_selected_features]
        X_te = X_te_raw[fold_selected_features]
        
        # RF Fold
        rf = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
        rf.fit(X_tr, y_tr)
        
        rf_val_probs = rf.predict_proba(X_va)[:, 1]
        rf_best_t, rf_best_val_f1 = optimize_decision_threshold(y_va, rf_val_probs, target_name)
                
        # RF Test Evaluation
        rf_test_probs = rf.predict_proba(X_te)[:, 1]
        rf_test_preds = (rf_test_probs >= rf_best_t).astype(int)
        
        # Calculate fold Daily IC and Top-3 Hit Rate
        df_te_eval = df_stacked.loc[test_mask, ['date']].copy()
        df_te_eval['y'] = y_te.values
        df_te_eval['prob_rf'] = rf_test_probs
        
        daily_ics_rf, top3_hits_rf = [], []
        for d, grp in df_te_eval.groupby('date'):
            if len(grp) >= 10:
                if grp['y'].nunique() > 1 and grp['prob_rf'].nunique() > 1:
                    ic, _ = spearmanr(grp['prob_rf'], grp['y'])
                    if not np.isnan(ic):
                        daily_ics_rf.append(ic)
                top3 = grp.sort_values('prob_rf', ascending=False).head(3)
                top3_hits_rf.append(top3['y'].mean())
                
        mean_ic_rf = np.mean(daily_ics_rf) if daily_ics_rf else 0.0
        std_ic_rf = np.std(daily_ics_rf) if daily_ics_rf else 1.0
        t_stat_rf = (mean_ic_rf / (std_ic_rf + 1e-8)) * np.sqrt(len(daily_ics_rf))
        top3_hit_rf = np.mean(top3_hits_rf) * 100 if top3_hits_rf else 0.0

        rf_test_metrics = {
            "accuracy": accuracy_score(y_te, rf_test_preds),
            "precision": precision_score(y_te, rf_test_preds, zero_division=0),
            "recall": recall_score(y_te, rf_test_preds, zero_division=0),
            "f1": f1_score(y_te, rf_test_preds, zero_division=0),
            "auc": roc_auc_score(y_te, rf_test_probs) if len(np.unique(y_te)) > 1 else 0.5,
            "naive_baseline": max(y_te.mean(), 1 - y_te.mean()),
            "mean_daily_ic": mean_ic_rf,
            "ic_t_stat": t_stat_rf,
            "top3_hit_rate": top3_hit_rf
        }
        fold_rf_thresholds.append(rf_best_t)
        fold_rf_val_f1s.append(rf_best_val_f1)
        fold_rf_test_metrics.append(rf_test_metrics)
        
        # XGB Fold
        neg_count = np.sum(y_tr == 0)
        pos_count = np.sum(y_tr == 1)
        ratio = float(neg_count) / float(pos_count + 1e-8)
        
        xgb = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=ratio,
            random_state=42,
            eval_metric='logloss'
        )
        xgb.fit(X_tr, y_tr)
        
        xgb_val_probs = xgb.predict_proba(X_va)[:, 1]
        xgb_best_t, xgb_best_val_f1 = optimize_decision_threshold(y_va, xgb_val_probs, target_name)
                
        xgb_test_probs = xgb.predict_proba(X_te)[:, 1]
        xgb_test_preds = (xgb_test_probs >= xgb_best_t).astype(int)
        
        df_te_eval['prob_xgb'] = xgb_test_probs
        daily_ics_xgb, top3_hits_xgb = [], []
        for d, grp in df_te_eval.groupby('date'):
            if len(grp) >= 10:
                if grp['y'].nunique() > 1 and grp['prob_xgb'].nunique() > 1:
                    ic, _ = spearmanr(grp['prob_xgb'], grp['y'])
                    if not np.isnan(ic):
                        daily_ics_xgb.append(ic)
                top3 = grp.sort_values('prob_xgb', ascending=False).head(3)
                top3_hits_xgb.append(top3['y'].mean())
                
        mean_ic_xgb = np.mean(daily_ics_xgb) if daily_ics_xgb else 0.0
        std_ic_xgb = np.std(daily_ics_xgb) if daily_ics_xgb else 1.0
        t_stat_xgb = (mean_ic_xgb / (std_ic_xgb + 1e-8)) * np.sqrt(len(daily_ics_xgb))
        top3_hit_xgb = np.mean(top3_hits_xgb) * 100 if top3_hits_xgb else 0.0

        xgb_test_metrics = {
            "accuracy": accuracy_score(y_te, xgb_test_preds),
            "precision": precision_score(y_te, xgb_test_preds, zero_division=0),
            "recall": recall_score(y_te, xgb_test_preds, zero_division=0),
            "f1": f1_score(y_te, xgb_test_preds, zero_division=0),
            "auc": roc_auc_score(y_te, xgb_test_probs) if len(np.unique(y_te)) > 1 else 0.5,
            "naive_baseline": max(y_te.mean(), 1 - y_te.mean()),
            "mean_daily_ic": mean_ic_xgb,
            "ic_t_stat": t_stat_xgb,
            "top3_hit_rate": top3_hit_xgb
        }
        fold_xgb_thresholds.append(xgb_best_t)
        fold_xgb_val_f1s.append(xgb_best_val_f1)
        fold_xgb_test_metrics.append(xgb_test_metrics)
        
    if len(fold_rf_val_f1s) < 3:
        print("[ERROR] Insufficient folds with class diversity during CV.")
        return
        
    mean_rf_val_f1 = np.mean(fold_rf_val_f1s)
    mean_xgb_val_f1 = np.mean(fold_xgb_val_f1s)
    
    if mean_xgb_val_f1 >= mean_rf_val_f1:
        best_model_name = "xgboost"
        ensemble_test_metrics = fold_xgb_test_metrics
    else:
        best_model_name = "random_forest"
        ensemble_test_metrics = fold_rf_test_metrics
        
    avg_test_acc = np.mean([m["accuracy"] for m in ensemble_test_metrics])
    avg_test_prec = np.mean([m["precision"] for m in ensemble_test_metrics])
    avg_test_rec = np.mean([m["recall"] for m in ensemble_test_metrics])
    avg_test_f1 = np.mean([m["f1"] for m in ensemble_test_metrics])
    avg_test_auc = np.mean([m["auc"] for m in ensemble_test_metrics])
    avg_test_naive = np.mean([m["naive_baseline"] for m in ensemble_test_metrics])
    avg_daily_ic = np.mean([m["mean_daily_ic"] for m in ensemble_test_metrics])
    avg_ic_t_stat = np.mean([m["ic_t_stat"] for m in ensemble_test_metrics])
    avg_top3_hit = np.mean([m["top3_hit_rate"] for m in ensemble_test_metrics])
    
    # 3. Train Final Model on 100% of stacked dataset
    rf_final_selector = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
    rf_final_selector.fit(X_all, y_all)
    final_importances = rf_final_selector.feature_importances_
    final_indices = np.argsort(final_importances)[::-1]
    top_k_final = min(25, len(all_feature_cols))
    final_selected_features = [all_feature_cols[final_indices[i]] for i in range(top_k_final)]
    
    X_final_all = X_all[final_selected_features]
    
    final_split = int(len(unique_dates) * 0.85)
    final_tr_dates = set(unique_dates[:final_split])
    final_va_dates = set(unique_dates[final_split:])
    
    tr_mask = df_stacked['date'].isin(final_tr_dates)
    va_mask = df_stacked['date'].isin(final_va_dates)
    
    X_final_tr = X_final_all[tr_mask]
    y_final_tr = y_all[tr_mask]
    X_final_va = X_final_all[va_mask]
    y_final_va = y_all[va_mask]
    
    if best_model_name == "random_forest":
        final_model = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
        final_model.fit(X_final_tr, y_final_tr)
        val_probs = final_model.predict_proba(X_final_va)[:, 1]
        final_opt_threshold, best_val_f1 = optimize_decision_threshold(y_final_va, val_probs, target_name)
                
        # Fit on 100% of stacked dataset
        final_model = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
        final_model.fit(X_final_all, y_all)
        
    else: # xgboost
        neg_count = np.sum(y_final_tr == 0)
        pos_count = np.sum(y_final_tr == 1)
        ratio = float(neg_count) / float(pos_count + 1e-8)
        
        final_model = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=ratio,
            random_state=42,
            eval_metric='logloss'
        )
        final_model.fit(X_final_tr, y_final_tr)
        val_probs = final_model.predict_proba(X_final_va)[:, 1]
        final_opt_threshold, best_val_f1 = optimize_decision_threshold(y_final_va, val_probs, target_name)
                
        # Fit on 100% of stacked dataset
        neg_all = np.sum(y_all == 0)
        pos_all = np.sum(y_all == 1)
        ratio_all = float(neg_all) / float(pos_all + 1e-8)
        
        final_model = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=ratio_all,
            random_state=42,
            eval_metric='logloss'
        )
        final_model.fit(X_final_all, y_all)
        
    # Save the global model
    model_path = os.path.join(MODEL_DIR, f"global_pooled_model_{target_name}.pkl")
    model_pkg = {
        "features": final_selected_features,
        "model": final_model,
        "opt_threshold": float(final_opt_threshold),
        "best_model_type": best_model_name,
        "test_precision": float(avg_test_prec)
    }
    joblib.dump(model_pkg, model_path)
    print(f"[SUCCESS] Global Pooled Model saved to: {model_path}")
    
    # Save scorecard entry with strict out-of-sample metrics
    scorecard_result = {
        "status": "trained",
        "best_model": best_model_name,
        "validation_methodology": "5-fold walk-forward cross-validation with 5-day purged embargo",
        "samples": len(df_stacked),
        "num_stocks": len(target_files),
        "metrics": {
            "oos_accuracy": round(float(avg_test_acc), 4),
            "oos_precision": round(float(avg_test_prec), 4),
            "oos_recall": round(float(avg_test_rec), 4),
            "oos_f1_score": round(float(avg_test_f1), 4),
            "oos_auc": round(float(avg_test_auc), 4),
            "oos_naive_baseline": round(float(avg_test_naive), 4),
            "oos_mean_daily_ic": round(float(avg_daily_ic), 4),
            "oos_ic_t_stat": round(float(avg_ic_t_stat), 2),
            "oos_top3_hit_rate_%": round(float(avg_top3_hit), 2)
        },
        "opt_threshold": round(float(final_opt_threshold), 3),
        "positive_class_ratio": round(float(y_all.mean()), 4),
        "selected_features": final_selected_features,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    scorecard_path = os.path.join(BASE_DIR, "stock_selection", f"scorecard_{target_name}.json")
    scorecard = {}
    if os.path.exists(scorecard_path):
        try:
            with open(scorecard_path, "r", encoding="utf-8") as f:
                scorecard = json.load(f)
        except Exception:
            pass
    scorecard["GLOBAL_POOLED"] = scorecard_result
    
    with open(scorecard_path, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=4)
        
    print("\n" + "=" * 80)
    print(f"                 GLOBAL POOLED MODEL SUMMARY: {target_name.upper()}                 ")
    print("=" * 80)
    print(f"  Model Type:             {best_model_name}")
    print(f"  Total Days:             {len(df_stacked)} (across {len(target_files)} symbols)")
    print(f"  OOS Accuracy:           {avg_test_acc:.4f} (vs Naive Baseline {avg_test_naive:.4f})")
    print(f"  OOS Precision:          {avg_test_prec:.4f}")
    print(f"  OOS Recall:             {avg_test_rec:.4f}")
    print(f"  OOS F1-Score:           {avg_test_f1:.4f}")
    print(f"  OOS AUC:                {avg_test_auc:.4f}")
    print(f"  OOS Mean Daily IC:      {avg_daily_ic:.4f} (t-stat: {avg_ic_t_stat:.2f})")
    print(f"  OOS Top-3 Hit Rate:     {avg_top3_hit:.2f}% (vs Base Positive Ratio {y_all.mean():.2%})")
    print(f"  Opt Threshold:          {final_opt_threshold:.3f}")
    print(f"  Positive Ratio:         {y_all.mean():.3%}")
    print("=" * 80)

def train_wrapper(args):
    return train_single_stock(*args)

def main():
    parser = argparse.ArgumentParser(description="Multi-Stock Model Training Pipeline")
    parser.add_argument("--target", "-t", choices=["direction", "gap", "volatility", "strategy"], default="volatility", help="Target variable to train on")
    parser.add_argument("--symbols", nargs="*", help="List of symbols to train. If omitted, trains all processed CSVs in stock_selection/data/")
    parser.add_argument("--pool", action="store_true", help="Train a single global pooled model across all stock datasets combined")
    args = parser.parse_args()

    # Find processed feature files
    pattern = os.path.join(FEATURE_DIR, "*_features.csv")
    all_files = glob.glob(pattern)
    
    if not all_files:
        print(f"[ERROR] No feature files found in: {FEATURE_DIR}. Run preprocess.py first.")
        return

    target_files = []
    if args.symbols:
        requested = [s.lower() for s in args.symbols]
        for f in all_files:
            sym = os.path.basename(f).replace("_features.csv", "")
            if sym in requested:
                target_files.append(f)
    else:
        target_files = all_files

    if args.pool:
        train_pooled_model(target_files, args.target)
    else:
        print(f"[INFO] Found {len(target_files)} preprocessed stock files to train on target: {args.target}")

        # Launch multiprocessing
        cores = min(cpu_count(), len(target_files))
        print(f"[INFO] Training in parallel using {cores} CPU cores...")

        tasks = [(f, args.target) for f in target_files]
        with Pool(processes=cores) as pool:
            raw_results = pool.map(train_wrapper, tasks)

        # Compile scorecard
        scorecard = {}
        trained_count = 0
        skipped_count = 0
        error_count = 0

        print("\n" + "=" * 80)
        print(f"                       TRAINING SCORECARD: {args.target.upper()}                        ")
        print("=" * 80)
        print(f"  {'Symbol':<12} | {'Status':<10} | {'Best Model':<14} | {'Accuracy':<8} | {'Precision':<9} | {'F1-Score':<8}")
        print("-" * 80)

        for sym, res in raw_results:
            scorecard[sym] = res
            status = res.get("status", "error")
            if status == "trained":
                trained_count += 1
                metrics = res["metrics"]
                print(f"  {sym:<12} | {status:<10} | {res['best_model']:<14} | {metrics['accuracy']:<8.3f} | {metrics['precision']:<9.3f} | {metrics['f1']:<8.3f}")
            elif status == "skipped":
                skipped_count += 1
                print(f"  {sym:<12} | {status:<10} | {'N/A':<14} | {'Skipped: ' + res['reason']}")
            else:
                error_count += 1
                print(f"  {sym:<12} | {status:<10} | {'N/A':<14} | Error occurred during training.")

        print("=" * 80)
        print(f"[SUMMARY] Total: {len(raw_results)} | Trained: {trained_count} | Skipped: {skipped_count} | Errors: {error_count}")
        
        # Save scorecard to disk
        scorecard_path = os.path.join(BASE_DIR, "stock_selection", f"scorecard_{args.target}.json")
        with open(scorecard_path, "w", encoding="utf-8") as f:
            json.dump(scorecard, f, indent=4)
        print(f"[SUCCESS] Scorecard saved to: {scorecard_path}\n")

if __name__ == "__main__":
    main()
