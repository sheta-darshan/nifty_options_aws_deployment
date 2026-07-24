import os
import sys
import argparse
import json
import glob
from multiprocessing.pool import ThreadPool
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Setup project root pathing
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Import helpers from select_stocks
sys.path.append(os.path.join(BASE_DIR, "stock_selection"))
from select_stocks import (
    read_last_n_lines_to_df,
    precompute_nifty_features,
    extract_features_for_last_day,
    update_spot_file_if_stale,
    MODEL_DIR,
    PRED_DIR
)
import joblib

def main():
    parser = argparse.ArgumentParser(description="Generate Joint Volatility & Direction Stock Recommendations")
    parser.add_argument("--no-update", action="store_true", help="Bypass updating spot files from Dhan API")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of top stocks to recommend for selection")
    parser.add_argument("--rotate", action="store_true", help="Automatically rotate and enable top selections inside instruments.json with directional allowed_actions")
    args = parser.parse_args()

    # 1. Load scorecards
    scorecard_vol_path = os.path.join(BASE_DIR, "stock_selection", "scorecard_volatility.json")
    scorecard_dir_path = os.path.join(BASE_DIR, "stock_selection", "scorecard_direction.json")

    if not os.path.exists(scorecard_vol_path) or not os.path.exists(scorecard_dir_path):
        print("[ERROR] Both scorecard_volatility.json and scorecard_direction.json must exist. Train both targets first.")
        return

    with open(scorecard_vol_path, "r", encoding="utf-8") as f:
        scorecard_vol = json.load(f)
    with open(scorecard_dir_path, "r", encoding="utf-8") as f:
        scorecard_dir = json.load(f)

    # 2. Check for Global Pooled Models
    global_model_vol_path = os.path.join(MODEL_DIR, "global_pooled_model_volatility.pkl")
    global_model_dir_path = os.path.join(MODEL_DIR, "global_pooled_model_direction.pkl")

    use_pooled_vol = os.path.exists(global_model_vol_path)
    use_pooled_dir = os.path.exists(global_model_dir_path)

    # Load pooled models if they exist
    global_model_vol_pkg = joblib.load(global_model_vol_path) if use_pooled_vol else None
    global_model_dir_pkg = joblib.load(global_model_dir_path) if use_pooled_dir else None

    # Determine symbols trained under BOTH targets
    active_symbols = []
    for sym in scorecard_vol:
        if sym == "GLOBAL_POOLED":
            continue
        status_vol = scorecard_vol[sym].get("status") == "trained" or use_pooled_vol
        status_dir = scorecard_dir.get(sym, {}).get("status") == "trained" or use_pooled_dir
        if status_vol and status_dir:
            active_symbols.append(sym)

    if not active_symbols:
        print("[ERROR] No symbols found that have trained models for both volatility and direction.")
        return

    print(f"[INFO] Evaluating {len(active_symbols)} symbols using Joint Volatility + Direction filters...")

    # Load credentials to auto-update spot files
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
    client_id = os.getenv("DHAN_CLIENT_ID", "").strip().strip("'").strip('"')
    api_token = os.getenv("DHAN_API_TOKEN", "").strip().strip("'").strip('"')

    if client_id and api_token and not args.no_update:
        print("[INFO] Dhan API credentials found. Updating NIFTY spot file...")
        update_spot_file_if_stale("NIFTY", client_id, api_token)

        print(f"[INFO] Updating spot files for {len(active_symbols)} symbols in parallel...")
        pool = ThreadPool(10)
        pool.map(lambda sym: update_spot_file_if_stale(sym, client_id, api_token), active_symbols)
        pool.close()
        pool.join()
        print("[INFO] Spot files check and update complete.\n")

    # Precompute nifty features
    nifty_features = precompute_nifty_features()

    predictions = []
    run_date = None

    for symbol in active_symbols:
        features, last_date_obj = extract_features_for_last_day(symbol, nifty_features)
        if features is None:
            continue

        if run_date is None:
            run_date = last_date_obj.strftime("%Y-%m-%d")

        try:
            # A. Volatility Prediction
            if use_pooled_vol:
                feat_cols = global_model_vol_pkg["features"]
                X_pred = pd.DataFrame([features])[feat_cols]
                probs = global_model_vol_pkg["model"].predict_proba(X_pred)[0]
                vol_prob = probs[1] if len(probs) > 1 else probs[0]
                vol_thresh = global_model_vol_pkg.get("opt_threshold", 0.5)
                vol_precision = global_model_vol_pkg.get("test_precision", 0.5)
                # Raw probability for pooled
                vol_score = vol_prob * 100
                vol_model_type = global_model_vol_pkg.get("best_model_type", "xgboost") + " (Pooled)"
            else:
                mf_vol = os.path.join(MODEL_DIR, f"{symbol.lower()}_best_model_volatility.pkl")
                vol_pkg = joblib.load(mf_vol)
                feat_cols = vol_pkg["features"]
                X_pred = pd.DataFrame([features])[feat_cols]
                probs = vol_pkg["model"].predict_proba(X_pred)[0]
                vol_prob = probs[1] if len(probs) > 1 else probs[0]
                vol_thresh = vol_pkg.get("opt_threshold", 0.5)
                vol_precision = vol_pkg.get("test_precision", scorecard_vol[symbol]["metrics"]["precision"])
                vol_score = (vol_prob - vol_thresh) * 100
                vol_model_type = vol_pkg.get("best_model_type", scorecard_vol[symbol]["best_model"])

            # B. Direction Prediction
            if use_pooled_dir:
                feat_cols = global_model_dir_pkg["features"]
                X_pred = pd.DataFrame([features])[feat_cols]
                probs = global_model_dir_pkg["model"].predict_proba(X_pred)[0]
                dir_prob = probs[1] if len(probs) > 1 else probs[0]
                dir_thresh = global_model_dir_pkg.get("opt_threshold", 0.5)
                dir_model_type = global_model_dir_pkg.get("best_model_type", "xgboost") + " (Pooled)"
            else:
                mf_dir = os.path.join(MODEL_DIR, f"{symbol.lower()}_best_model_direction.pkl")
                dir_pkg = joblib.load(mf_dir)
                feat_cols = dir_pkg["features"]
                X_pred = pd.DataFrame([features])[feat_cols]
                probs = dir_pkg["model"].predict_proba(X_pred)[0]
                dir_prob = probs[1] if len(probs) > 1 else probs[0]
                dir_thresh = dir_pkg.get("opt_threshold", 0.5)
                dir_model_type = dir_pkg.get("best_model_type", scorecard_dir[symbol]["best_model"])

            # Suggested direction based on 50% split (or threshold if individual)
            # Above threshold/50% is BULLISH (BUY), below is BEARISH (SELL)
            direction_action = "BUY" if dir_prob >= 0.5 else "SELL"
            direction_label = "BULLISH (BUY)" if direction_action == "BUY" else "BEARISH (SELL)"

            predictions.append({
                "Symbol": symbol,
                "Vol Probability (%)": round(vol_prob * 100, 1),
                "Vol Selection Score (%)": round(vol_score, 1),
                "Dir Probability (%)": round(dir_prob * 100, 1),
                "Target Direction": direction_label,
                "Action": direction_action,
                "Vol Model": vol_model_type,
                "Dir Model": dir_model_type,
                "Vol Test Precision": vol_precision,
                "Verdict": "AVOID"
            })
        except Exception as e:
            print(f"[WARNING] Failed to run prediction model for {symbol}: {e}")

    if not predictions:
        print("[ERROR] No predictions could be generated.")
        return

    # Sort predictions by Vol Selection Score descending (Volatility is the primary selector)
    df_preds = pd.DataFrame(predictions)
    df_preds = df_preds.sort_values(by="Vol Selection Score (%)", ascending=False).reset_index(drop=True)

    # Apply Top-K ranking verdict
    top_k = int(args.top_k)
    for idx in range(len(df_preds)):
        vol_prob = df_preds.loc[idx, "Vol Probability (%)"]
        vol_score = df_preds.loc[idx, "Vol Selection Score (%)"]
        
        # Check condition to qualify as a valid selection
        if idx < top_k and (vol_prob >= 35.0 or (not use_pooled_vol and vol_score >= 0.0)):
            df_preds.loc[idx, "Verdict"] = "SELECT (TOP K)"
        else:
            df_preds.loc[idx, "Verdict"] = "AVOID"

    print("\n" + "=" * 125)
    print(f"               JOINT VOLATILITY + DIRECTION STOCK ROTATION RECOMMENDATIONS FOR TOMORROW              ")
    print(f"               Reference Trading Date: {run_date}")
    print("=" * 125)
    print(f"  {'Rank':<5} | {'Symbol':<12} | {'Vol Prob':<10} | {'Vol Score':<18} | {'Dir Prob':<10} | {'Suggested Side':<16} | {'Verdict':<18}")
    print("-" * 125)
    
    for idx, row in df_preds.iterrows():
        rank = idx + 1
        vol_prob_str = f"{float(row['Vol Probability (%)']):.1f}%"
        vol_score_val = float(row['Vol Selection Score (%)'])
        vol_score_str = f"{vol_score_val:+.1f}%" if not use_pooled_vol else f"{vol_score_val:.1f}% (Pooled)"
        dir_prob_str = f"{float(row['Dir Probability (%)']):.1f}%"
        
        print(f"  {rank:<5} | {row['Symbol']:<12} | {vol_prob_str:<10} | {vol_score_str:<18} | {dir_prob_str:<10} | {row['Target Direction']:<16} | {row['Verdict']:<18}")

    print("=" * 125)

    # Save predictions
    save_filename = f"predictions_joint_{run_date}.csv"
    save_path = os.path.join(PRED_DIR, save_filename)
    df_preds.to_csv(save_path, index=False)
    print(f"[SUCCESS] Joint selection recommendations saved to: {save_path}\n")

    # 4. Automate Stock Rotation & Direction Constraints in instruments.json
    rotation_status = "Rotation not requested (run with --rotate to update instruments.json)"
    activated = []
    deactivated = []

    if args.rotate:
        print("[ROTATE] Automating stock rotation & directional overrides...")
        
        top_selections_df = df_preds[df_preds["Verdict"] == "SELECT (TOP K)"]
        top_selections_dict = dict(zip(top_selections_df["Symbol"], top_selections_df["Action"]))
        evaluated_symbols = set(active_symbols)
        
        instruments_path = os.path.join(BASE_DIR, "instruments.json")
        if os.path.exists(instruments_path):
            try:
                with open(instruments_path, "r", encoding="utf-8") as f:
                    instruments = json.load(f)
                
                for symbol in instruments:
                    if symbol in evaluated_symbols:
                        if symbol in top_selections_dict:
                            action = top_selections_dict[symbol]
                            instruments[symbol]["enabled"] = 1
                            instruments[symbol]["allowed_actions"] = [action]
                            activated.append(f"{symbol} ({action})")
                        else:
                            instruments[symbol]["enabled"] = 0
                            # Reset allowed_actions to default so if manually enabled later it supports both sides
                            instruments[symbol]["allowed_actions"] = ["BUY", "SELL"]
                            deactivated.append(symbol)

                # Write back to instruments.json
                with open(instruments_path, "w", encoding="utf-8") as f:
                    json.dump(instruments, f, indent=4)
                    
                print(f"[SUCCESS] instruments.json updated successfully!")
                print(f"  * Activated:   {activated if activated else 'None'}")
                print(f"  * Deactivated: {deactivated if deactivated else 'None'}")
                rotation_status = f"Successfully rotated instruments.json!\n• Activated: {', '.join(activated) if activated else 'None'}\n• Deactivated: {len(deactivated)} symbols"
            except Exception as e:
                print(f"[ERROR] Failed to update instruments.json: {e}")
                rotation_status = f"Rotation failed: {e}"
        else:
            print(f"[ERROR] instruments.json not found at {instruments_path}")
            rotation_status = "Rotation failed: instruments.json not found"

    # 5. Telegram Notifications
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        print("[ALERT] Sending daily joint recommendations alert...")
        try:
            from trading_bot.alerts import AlertManager
            import logging
            alert_logger = logging.getLogger("select-joint-alert")
            alert_manager = AlertManager(webhook_url, alert_logger)
            
            top_df = df_preds[df_preds["Verdict"] == "SELECT (TOP K)"]
            msg = f"📊 *Daily ML Joint Selection Recommendations* ({run_date})\n\n"
            msg += f"*Status:* {rotation_status}\n\n"
            if not top_df.empty:
                msg += "🚀 *Selected Symbols:*\n"
                for idx, row in top_df.iterrows():
                    msg += f"• *{row['Symbol']}* - Vol: {row['Vol Probability (%)']:.1f}% | Dir: {row['Dir Probability (%)']:.1f}% ({row['Target Direction']})\n"
            else:
                msg += "⚠️ *No symbols passed the selection thresholds today.*\n"
                
            alert_manager.send_alert(msg)
            print("[SUCCESS] Telegram notification sent.")
        except Exception as e:
            print(f"[WARNING] Telegram notification failed: {e}")

if __name__ == "__main__":
    main()
