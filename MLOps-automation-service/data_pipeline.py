import requests
import pandas as pd
import numpy as np
import torch
from io import StringIO
from datetime import datetime, timedelta

# --- CONFIGURATION ---
T_IN = 60
T_OUT = 10
NASA_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Bangalore Rural
LOCATION = {"lat": 13.18, "lon": 77.8} 

def fetch_data(param="T2M", days=5*365+4):
    """
    Ingestion: Fetch last N days of data from NASA POWER API.
    """
    print(f"[Ingestion] Fetching last {days} days of {param} data...")
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    url = (
        f"{NASA_API_URL}?"
        f"parameters={param}&community=AG&longitude={LOCATION['lon']}&latitude={LOCATION['lat']}"
        f"&start={start_date.strftime('%Y%m%d')}&end={now.strftime('%Y%m%d')}&format=CSV"
    )
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[Ingestion] Failed to fetch data: {e}")
        raise e

    df = pd.read_csv(StringIO(response.text), skiprows=9)
    df.columns = [c.strip() for c in df.columns]
    
    # Create Date Index
    df["Date"] = pd.to_datetime(
        df["YEAR"].astype(str) + df["DOY"].astype(str).str.zfill(3),
        format="%Y%j"
    )
    df.set_index("Date", inplace=True)
    df = df.sort_index()
    
    # Rename value column to 'Value' for generic handling
    df.rename(columns={param: "Value"}, inplace=True)
    
    print(f"[Ingestion] Retrieved {len(df)} records.")
    return df

def validate_and_clean(df, param="T2M"):
    """
    Validation: Check for missing values, clip ranges, and fill gaps.
    """
    print(f"[Validation] Checking data quality for {param}...")
    
    # 1. Handle Sentinel Values (-999 is common in NASA POWER for missing)
    df["Value"] = df["Value"].replace(-999.0, np.nan)
    
    # 2. Check Missing
    missing_count = df["Value"].isna().sum()
    if missing_count > 0:
        print(f"[Validation] Found {missing_count} missing values. Interpolating...")
        df["Value"] = df["Value"].interpolate(method='time')
        
    # 3. Clip Ranges
    if param == "RH2M":
        print("[Validation] Clipping RH2M to [0, 100]")
        df["Value"] = df["Value"].clip(0, 100)
    elif param == "WS2M":
         print("[Validation] Clipping WS2M to [0, inf)")
         df["Value"] = df["Value"].clip(lower=0)
         
    # 4. Drop remaining NaNs (if any at start/end)
    original_len = len(df)
    df.dropna(inplace=True)
    if len(df) < original_len:
         print(f"[Validation] Dropped {original_len - len(df)} rows with NaN.")
         
    return df

def compute_stats(df):
    """
    EDA: Log basic statistics for monitoring drift.
    """
    stats = {
        "mean": df["Value"].mean(),
        "std": df["Value"].std(),
        "min": df["Value"].min(),
        "max": df["Value"].max(),
        "count": len(df)
    }
    print(f"[EDA] Data Stats: {stats}")
    return stats

def prepare_tensors(df):
    """
    Feature Engineering: Normalize and create sliding windows.
    Returns: X (windows), y (targets), temporal_info, mean, std
    """
    print("[Feature Engineering] Preparing tensors...")
    series = df["Value"].values.astype(np.float32)
    
    # Normalization
    mean = series.mean()
    std = series.std() if series.std() > 0 else 1.0
    normalized = (series - mean) / std
    
    # Sliding Windows
    X, y = [], []
    for i in range(len(normalized) - T_IN - T_OUT):
        X.append(normalized[i : i + T_IN])
        y.append(normalized[i + T_IN : i + T_IN + T_OUT])
        
    X = np.array(X)
    y = np.array(y)
    
    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)
    
    # Temporal Info (0 to T_IN-1) repeated for batch
    temporal_info = torch.arange(T_IN, dtype=torch.float32).unsqueeze(0).expand(X_tensor.size(0), -1)
    
    print(f"[Feature Engineering] Created {len(X)} windows. Shape: {X_tensor.shape}")
    return X_tensor, y_tensor, temporal_info, mean, std

def run_pipeline(param="T2M"):
    """
    Pipeline entrypoint: Fetch -> Clean -> Stats -> Tensor Prep.
    """
    df = fetch_data(param)
    df = validate_and_clean(df, param)
    stats = compute_stats(df)
    return prepare_tensors(df)
