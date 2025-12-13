import logging
import torch
import numpy as np
from datetime import datetime, timedelta

from data_pipeline import fetch_data, validate_and_clean, T_IN, T_OUT
from model_loader import load_model

# Constants from requirements
TRAIN_LAT = 13.18
TRAIN_LON = 77.80
MAE_THRESHOLD = 2.0 

def compute_mae(a, b):
    return float(np.mean(np.abs(np.array(a) - np.array(b))))

def preprocess_for_eval(series):
    """
    Standard preprocessing for evaluation (same as forecast.py but for specific slice).
    """
    mean = series.mean()
    std = series.std() if series.std() > 0 else 1.0
    normalized = (series - mean) / std

    # tailored for the 1-60 input to predict 61-70
    # Input indices: 0 to 59 (60 points) -> T_IN=60
    input_slice = normalized[:T_IN]
    
    input_tensor = torch.tensor(
        input_slice, dtype=torch.float32
    ).unsqueeze(0).unsqueeze(-1) # [1, 60, 1]

    temporal_info = torch.arange(T_IN, dtype=torch.float32).unsqueeze(0) # [1, 60]

    return input_tensor, temporal_info, mean, std

def evaluate_model_health(param="T2M"):
    """
    Fetches last 70 days.
    Uses days 1-60 to predict 61-70.
    Compares with actual 61-70.
    Returns: (is_healthy, mae)
    """
    logging.info(f"[{param}] Checking model health...")

    # Fetch 70 days
    # Note: fetch_data fetches a bit more to be safe, we need strict 70 days for the logic
    # The requirement says "take the last 70 days data"
    df = fetch_data(days=75, param=param) 
    df = validate_and_clean(df, param)
    
    if len(df) < 70:
        logging.warning(f"[{param}] Not enough data for validation (got {len(df)}). Assuming Unhealthy.")
        return False, 9999.0

    # Get strictly last 70 days
    recent_70 = df.tail(70)
    series_70 = recent_70["Value"].values.astype(np.float32)

    # Actual Future (last 10 days: indices 60-69)
    actual_future = series_70[60:]
    
    # Input Series (first 60 days: indices 0-59)
    input_series = series_70[:60]

    # Preprocess
    window_tensor, temporal_info, mean, std = preprocess_for_eval(input_series)

    # Load Model
    try:
        model = load_model(param)
    except FileNotFoundError:
        logging.error(f"[{param}] Model file not found.")
        return False, 9999.0

    # Inference
    model.eval()
    with torch.no_grad():
        device = next(model.parameters()).device # Get model device
        window_tensor = window_tensor.to(device)
        temporal_info = temporal_info.to(device)
        
        pred_norm = model(window_tensor, temporal_info).cpu().numpy().flatten()

    # Denormalize
    pred_values = pred_norm * std + mean

    # Compute Error
    mae = compute_mae(pred_values, actual_future)
    is_healthy = mae < MAE_THRESHOLD

    logging.info(f"[{param}] Health Check: MAE={mae:.4f} (Threshold={MAE_THRESHOLD}). Healthy={is_healthy}")
    
    return is_healthy, mae
