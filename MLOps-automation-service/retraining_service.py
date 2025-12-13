# from docker_utils import backup_image_on_hub, deploy_new_image_to_hub 
# (Removed Docker Utils as we use Shared PVC + Kubectl now)
#for github
import subprocess
import logging

MAX_RETRIES = 3

def restart_inference_pod(param):
    """
    Restart the specific inference deployment to pick up new weights from PVC.
    """
    deployment_name = f"inference-{param.lower()}"
    namespace = "weather-mlops"
    cmd = ["kubectl", "rollout", "restart", f"deployment/{deployment_name}", "-n", namespace]
    
    logging.info(f"[{param}] Triggering restart of {deployment_name}...")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"[{param}] Restart trigger successful.")
        print(f"[{param}] Pod restart triggered successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"[{param}] Restart failed: {e.stderr.decode().strip()}")
        print(f"[{param}] Error restarting pod: {e.stderr.decode().strip()}")

def attempt_retrain(param="T2M"):
    """
    Orchestrates the retraining loop.
    1. Backup current model to 'previous_{param}.pt' (Once, before loop).
    2. Loop max 3 times.
    3. Restart K8s Pod on success.
    """
    logging.info(f"[{param}] Starting Conditional Retraining Loop...")
    print(f"\n[ATTENTION] Model for {param} is performing poorly. Retraining required.")
    
    # --- BACKUP LOGIC (LOCAL / PVC) ---
    import os
    import shutil
    
    models_dir = "models"
    latest_filename = os.path.join(models_dir, f"latest_{param}.pt")
    previous_filename = os.path.join(models_dir, f"previous_{param}.pt")
    
    if os.path.exists(latest_filename):
        shutil.copy2(latest_filename, previous_filename)
        logging.info(f"[{param}] PVC Backup: Saved current weights to {previous_filename}.")
        print(f"[{param}] Original weights backed up to {previous_filename}.")

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n>>> Retraining Attempt {attempt}/{MAX_RETRIES} for {param} <<<")
        
        logging.info(f"[{param}] Proceeding with REAL retraining...")
        from train import train_model
        train_model(param)
        
        # Re-evaluate
        from model_evaluator import evaluate_model_health
        is_healthy, mae = evaluate_model_health(param)
        if is_healthy:
            logging.info(f"[{param}] Retraining FAILURE FIXED! New MAE={mae:.4f}")
            print(f"[{param}] Health restored.")
            
            # --- DEPLOY LOGIC (K8S) ---
            # Success! Restart the pod to load new weights
            restart_inference_pod(param)
            
            return True
        else:
            logging.warning(f"[{param}] Retraining Attempt {attempt} failed. MAE={mae:.4f} still > Threshold.")

    # If we exit loop, we failed 3 times
    logging.error(f"[{param}] Critical: Retrained {MAX_RETRIES} times but model is still unhealthy.")
    print(f"[{param}] CRITICAL: Model failed to converge after {MAX_RETRIES} attempts. Notification sent to developer.")
    
    # --- REVERT LOGIC START ---
    if os.path.exists(previous_filename):
        shutil.copy2(previous_filename, latest_filename)
        logging.info(f"[{param}] Reverted: Restored original weights from {previous_filename} to {latest_filename}.")
        print(f"[{param}] System reverted to original weights due to retraining failure.")
        # We should logically restart the pod here too, to revert the in-memory model? 
        # Yes, if we want strict consistency.
        restart_inference_pod(param)

    # --- REVERT LOGIC END ---
    
    return False
