import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from transformers import GPT2Model, GPT2Config
import os
import argparse
from datetime import datetime

import os
import mlflow
import mlflow.pytorch


# Local Imports
from model import ForecastingModel, D, T_IN, T_OUT
from data_pipeline import run_pipeline

# Parameters
BATCH_SIZE = 64
EPOCHS = 15 # Reduced for quicker demo, increase for prod
LEARNING_RATE = 21e-5

def train_model(param="T2M"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"--- Starting Training for {param} on {device} ---")

    # 1. Data Pipeline
    X, y, temporal_info, mean, std = run_pipeline(param)
    
    # 2. Train/Test Split
    split_idx = int(0.8 * len(X))
    X_train, y_train, t_train = X[:split_idx], y[:split_idx], temporal_info[:split_idx]
    X_test, y_test, t_test = X[split_idx:], y[split_idx:], temporal_info[split_idx:]
    
    train_dataset = TensorDataset(X_train, y_train, t_train)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # 3. Model Init
    print("[Model] Initializing ForecastingModel...")
    model = ForecastingModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_function = torch.nn.MSELoss()
    
    # 4. Training Loop
    print("[Training] Starting Loop...")
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        for b_x, b_y, b_t in train_loader:
            b_x, b_y, b_t = b_x.to(device), b_y.to(device), b_t.to(device)
            
            optimizer.zero_grad()
            output = model(b_x.unsqueeze(-1), b_t)
            loss = loss_function(output, b_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        print(f"Epoch {epoch + 1}/{EPOCHS}, Loss: {total_loss / len(train_loader):.6f}")
        
    # 5. Evaluation
    model.eval()
    with torch.no_grad():
        X_test, y_test, t_test = X_test.to(device), y_test.to(device), t_test.to(device)
        predictions = model(X_test.unsqueeze(-1), t_test)
        test_mse = loss_function(predictions, y_test).item()
        test_mae = torch.mean(torch.abs(predictions - y_test)).item()
        
    print(f"[Evaluation] Test MSE: {test_mse:.6f}, Test MAE: {test_mae:.6f}")
    
    # 6. Save & Version
    if not os.path.exists("models"):
        os.makedirs("models")
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_filename = f"models/v{timestamp}_{param}.pt"
    latest_filename = f"models/latest_{param}.pt"
    previous_filename = f"models/previous_{param}.pt"
    
    torch.save(model.state_dict(), version_filename)
    print(f"[Saved] Versioned model: {version_filename}")
    
    # Update latest symlink/copy
    torch.save(model.state_dict(), latest_filename)
    print(f"[Saved] Updated latest model: {latest_filename}")
    
    return test_mse

def train_and_log(param):
    X_train, y_train, X_test, y_test, temporal_train, temporal_test, mean, std = run_pipeline(param)
    model, test_mse, test_mae = train_model(
        param, X_train, y_train, X_test, y_test, temporal_train, temporal_test
    )

    # MLflow logging
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001"))
    mlflow.set_experiment("llm4ts-weather")

    with mlflow.start_run(run_name=f"{param}_train"):
        mlflow.log_param("param", param)
        mlflow.log_param("T_IN", 60)
        mlflow.log_param("T_OUT", 10)
        mlflow.log_param("epochs", 15)

        mlflow.log_metric("test_mse", test_mse)
        mlflow.log_metric("test_mae", test_mae)

        mlflow.pytorch.log_model(model, artifact_path="model")

    return model, test_mse, test_mae


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--param", type=str, default="T2M", help="Parameter to train (T2M, RH2M, WS2M)")
    args = parser.parse_args()
    
    train_model(args.param)
