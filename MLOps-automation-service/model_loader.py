import torch
from model import ForecastingModel
import os

MODELS_DIR = "models"
_models = {}

def load_model(param="T2M"):
    global _models
    
    # Map param to filename
    # Assuming params are T2M, RH2M, WS2M
    filename = f"latest_{param}.pt"
    model_path = os.path.join(MODELS_DIR, filename)

    if param not in _models:
        print(f"Loading model for {param} from {model_path}...")
        model = ForecastingModel()
        if os.path.exists(model_path):
            model.load_state_dict(torch.load(model_path, map_location="cpu"))
        else:
            raise FileNotFoundError(f"Model weights not found: {model_path}")
            
        model.eval()
        _models[param] = model
    
    return _models[param]
