import logging
import traceback
from datetime import datetime

import mlflow
import mlflow.pyfunc

from model_evaluator import evaluate_model_health
from retraining_service import attempt_retrain

# =============================================
# CONFIGURATION
# =============================================

PROPERTIES = ["T2M", "RH2M", "WS2M"]
# MAE_THRESHOLD is now handled in model_evaluator

# MLflow Tracking Server
MLFLOW_URI = "http://mlflow:5005"  # Change to 5001 if local

import sys

# Logging setup
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# =============================================
# DAILY RETRAINING PIPELINE
# =============================================
def run_retraining_cycle():
    logging.info("=== DAILY RETRAINING CYCLE STARTED ===")

    # Setup MLflow
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("llm4ts-drift-monitoring")

    for param in PROPERTIES:
        try:
            logging.info(f"[{param}] Evaluating model...")

            # -------------------------------
            # Step 1: Drift detection (Shared Logic)
            # -------------------------------
            is_healthy, mae_backtest = evaluate_model_health(param)

            # Start MLflow run for today's evaluation
            with mlflow.start_run(run_name=f"{param}_daily_retrain_{datetime.now().strftime('%Y%m%d')}"):

                mlflow.log_param("parameter", param)
                mlflow.log_metric("backtest_mae", mae_backtest)
                
                if is_healthy:
                    # SKIPPED retraining
                    decision = "SKIPPED"
                    mlflow.log_param("retrain_decision", decision)
                    logging.info(f"[{param}] MAE={mae_backtest:.4f} OK. Retraining skipped.")
                    continue

                # -------------------------------
                # Step 2: Drift Detected
                # -------------------------------
                logging.warning(f"[{param}] ALERT: Model Health Failed (MAE={mae_backtest:.4f}).")
                
                # Check option: ENABLE_RETRAINING
                import os # Ensure os is imported
                if os.getenv("ENABLE_RETRAINING", "false").lower() == "true":
                    logging.info(f"[{param}] ENABLE_RETRAINING=true. Starting Automatic Retraining (Heavy Task)...")
                    decision = "RETRAIN_ATTEMPTED"
                    mlflow.log_param("retrain_decision", decision)
                    
                    success = attempt_retrain(param)
                    mlflow.log_param("retrain_success", success)
                    
                    if success:
                         logging.info(f"[{param}] Retrain process COMPLETED successfully.")
                    else:
                         logging.error(f"[{param}] Retrain process FAILED after max attempts.")
                         
                else:
                    decision = "DRIFT_DETECTED_MANUAL_REQUIRED"
                    logging.warning(f"[{param}] Check MLflow to confirm drift.")
                    logging.warning(f"[{param}] OPTION: To enable auto-retrain, set env ENABLE_RETRAINING=true")
                    mlflow.log_param("retrain_decision", decision)
                    continue

        except Exception as e:
            logging.error(f"[{param}] ERROR during retraining: {e}")
            logging.error(traceback.format_exc())

    logging.info("=== DAILY RETRAINING CYCLE FINISHED ===")


# =============================================
# EXECUTION ENTRYPOINT
# =============================================
if __name__ == "__main__":
    run_retraining_cycle()

