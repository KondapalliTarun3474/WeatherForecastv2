import logging
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import torch
import sys
import io

# Modify path to find local modules
import sys
import os
sys.path.append(os.path.abspath("/mnt/data/LLM4TS (copy)/MLOps-Pipeline"))

from retraining_service import attempt_retrain
from model_evaluator import evaluate_model_health
from forecast import run_forecast

class TestConditionalRetraining(unittest.TestCase):

    @patch('model_evaluator.fetch_data')
    @patch('model_evaluator.load_model')
    def test_health_check_failure(self, mock_load_model, mock_fetch_data):
        print("\n--- Test 1: Health Check (Unhealthy) ---")
        
        # Mock Data: 75 days of constant 0, but actual future is 100 (Huge Error)
        # 1-60 (input) = 0
        # 61-70 (target) = 100
        days = 75
        mock_df = MagicMock()
        mock_df.__len__.return_value = 75
        # Create a dataframe with "Value" column
        import pandas as pd
        mock_df = pd.DataFrame({"Value": [0.0]*60 + [100.0]*15})
        mock_fetch_data.return_value = mock_df

        # Mock Model: Predicts 0 always
        mock_model = MagicMock()
        mock_model.eval.return_value = None
        
        
        # internal mock for parameters() generator
        mock_param = MagicMock()
        mock_param.device = 'cpu'
        mock_model.parameters.return_value = iter([mock_param])
        
        # Mock forward pass to return zeros (T_OUT=10)
        mock_model.side_effect = lambda x, t: torch.zeros((1, 10, 1)) 
        mock_load_model.return_value = mock_model

        is_healthy, mae = evaluate_model_health("T2M")
        print(f"Computed MAE: {mae}, Healthy: {is_healthy}")
        
        self.assertFalse(is_healthy)
        self.assertGreater(mae, 2.0)

    @patch('retraining_service.input', create=True)
    @patch('model_evaluator.evaluate_model_health')
    @patch('retraining_service.train_model')
    def test_interactive_skip(self, mock_train, mock_eval, mock_input):
        print("\n--- Test 2: Interactive Skip (Mock Retrain) ---")
        
        # Setup:
        # First eval: False (Unhealthy) -> Triggers loop
        # Loop attempts:
        #   User input: 's' (Skip)
        #   Result: Return True (Simulated Success)
        
        mock_input.return_value = 's'
        
        # We don't need mock_eval to return healthy because 's' returns early True
        # But let's verify logic flow
        
        result = attempt_retrain("T2M")
        
        self.assertTrue(result) # Should return True because we "skipped/mocked" it
        mock_train.assert_not_called()
        print("Successfully skipped training via 's' input.")

    @patch('retraining_service.input', create=True)
    @patch('model_evaluator.evaluate_model_health')
    @patch('retraining_service.train_model')
    def test_real_retrain_flow(self, mock_train, mock_eval, mock_input):
        print("\n--- Test 3: Real Retrain Success ---")
        
        # Setup:
        # User input: '' (Enter -> Real Train)
        # Train happens
        # Re-eval returns True (Healthy)
        
        mock_input.return_value = '' # Enter
        mock_eval.return_value = (True, 0.5) # Healthy after retrain
        
        result = attempt_retrain("T2M")
        
        self.assertTrue(result)
        mock_train.assert_called_once()
        print("Successfully retrained and verified health.")

if __name__ == '__main__':
    unittest.main()
