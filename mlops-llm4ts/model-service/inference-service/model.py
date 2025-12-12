# model.py - Model class definitions for inference

import torch
import torch.nn as nn
from transformers import GPT2Model, GPT2Config

class TokenEncoding(nn.Module):
    def __init__(self, input_dim, embedding_dim, kernel_size=3):
        super(TokenEncoding, self).__init__()
        self.conv = nn.Conv1d(input_dim, embedding_dim, kernel_size=kernel_size, padding=1)
    def forward(self, x):
        x = x.transpose(1, 2)
        x = self.conv(x)
        return x.transpose(1, 2)

class PositionalEncoding(nn.Module):
    def __init__(self, num_patches, embedding_dim):
        super(PositionalEncoding, self).__init__()
        self.embedding = nn.Embedding(num_patches, embedding_dim)
    def forward(self, x):
        batch_size, num_patches, _ = x.size()
        positions = torch.arange(0, num_patches, device=x.device).unsqueeze(0).expand(batch_size, num_patches)
        return self.embedding(positions)

class TemporalEncoding(nn.Module):
    def __init__(self, embedding_dim):
        super(TemporalEncoding, self).__init__()
        self.temporal_embedding = nn.Linear(1, embedding_dim)
    def forward(self, t_info):
        return self.temporal_embedding(t_info.unsqueeze(-1))

class PatchReconstruction(nn.Module):
    def __init__(self, embedding_dim, patch_length):
        super(PatchReconstruction, self).__init__()
        self.linear = nn.Linear(embedding_dim, patch_length)
    def forward(self, z):
        return self.linear(z)

# Model hyperparameters
D = 768
T_IN = 60
T_OUT = 10

class ForecastingModel(nn.Module):
    def __init__(self):
        super(ForecastingModel, self).__init__()
        self.token_encoder = TokenEncoding(input_dim=1, embedding_dim=D)
        self.pos_encoder = PositionalEncoding(num_patches=T_IN, embedding_dim=D)
        self.temp_encoder = TemporalEncoding(embedding_dim=D)
        self.reconstructor = PatchReconstruction(embedding_dim=D, patch_length=T_OUT)
        
        config = GPT2Config(n_embd=D, n_layer=6, n_head=8)
        self.backbone = GPT2Model(config)
    
    def forward(self, x, temporal_info):
        x_token = self.token_encoder(x)
        x_pos = self.pos_encoder(x_token)
        x_temp = self.temp_encoder(temporal_info)
        x_combined = x_token + x_pos + x_temp
        z = self.backbone(inputs_embeds=x_combined).last_hidden_state
        z_last = z[:, -1, :]
        reconstructed = self.reconstructor(z_last.unsqueeze(1))
        return reconstructed.squeeze(1)
