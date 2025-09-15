"""
SongLab 딥러닝 모델 아키텍처
4축 보컬 분석을 위한 멀티모달 신경망
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple, Optional

class ConvBlock(nn.Module):
    """1D Convolution Block with BatchNorm and Dropout"""
    
    def __init__(self, in_channels: int, out_channels: int, 
                 kernel_size: int = 3, stride: int = 1, 
                 dropout: float = 0.1):
        super().__init__()
        
        self.conv = nn.Conv1d(in_channels, out_channels, 
                             kernel_size, stride, 
                             padding=kernel_size//2)
        self.bn = nn.BatchNorm1d(out_channels)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.ReLU()
        
    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.activation(x)
        x = self.dropout(x)
        return x

class AudioEncoder(nn.Module):
    """Raw Audio Encoder using 1D CNN"""
    
    def __init__(self, input_length: int = 480000):  # 30초 * 16kHz
        super().__init__()
        
        # 1D CNN for raw audio processing
        self.conv_layers = nn.Sequential(
            ConvBlock(1, 64, kernel_size=80, stride=4),    # 480000 -> 120000
            ConvBlock(64, 128, kernel_size=3, stride=2),   # 120000 -> 60000
            ConvBlock(128, 256, kernel_size=3, stride=2),  # 60000 -> 30000
            ConvBlock(256, 512, kernel_size=3, stride=2),  # 30000 -> 15000
            ConvBlock(512, 512, kernel_size=3, stride=2),  # 15000 -> 7500
            ConvBlock(512, 1024, kernel_size=3, stride=2), # 7500 -> 3750
        )
        
        # Global Average Pooling
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        
        # Final projection
        self.projection = nn.Linear(1024, 512)
        
    def forward(self, x):
        # x: [batch_size, audio_length]
        x = x.unsqueeze(1)  # [batch_size, 1, audio_length]
        
        x = self.conv_layers(x)  # [batch_size, 1024, length]
        x = self.global_pool(x)  # [batch_size, 1024, 1]
        x = x.squeeze(-1)        # [batch_size, 1024]
        x = self.projection(x)   # [batch_size, 512]
        
        return x

class FeatureEncoder(nn.Module):
    """Hand-crafted Features Encoder"""
    
    def __init__(self, input_dim: int = 9):
        super().__init__()
        
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.1),
            
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.1),
            
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.1),
            
            nn.Linear(256, 128),
        )
        
    def forward(self, x):
        return self.layers(x)

class AttentionFusion(nn.Module):
    """Attention-based fusion of audio and feature embeddings"""
    
    def __init__(self, audio_dim: int = 512, feature_dim: int = 128):
        super().__init__()
        
        self.audio_dim = audio_dim
        self.feature_dim = feature_dim
        self.hidden_dim = 256
        
        # Attention weights computation
        self.audio_proj = nn.Linear(audio_dim, self.hidden_dim)
        self.feature_proj = nn.Linear(feature_dim, self.hidden_dim)
        self.attention = nn.Linear(self.hidden_dim, 2)  # 2개 modality
        
        # Fusion layer
        self.fusion = nn.Linear(audio_dim + feature_dim, 512)
        
    def forward(self, audio_emb, feature_emb):
        # Project to common space
        audio_proj = torch.tanh(self.audio_proj(audio_emb))
        feature_proj = torch.tanh(self.feature_proj(feature_emb))
        
        # Compute attention weights
        combined = audio_proj + feature_proj
        attention_weights = F.softmax(self.attention(combined), dim=1)
        
        # Apply attention
        audio_weighted = audio_emb * attention_weights[:, 0:1]
        feature_weighted = feature_emb * attention_weights[:, 1:2]
        
        # Concatenate and fuse
        fused = torch.cat([audio_weighted, feature_weighted], dim=1)
        output = self.fusion(fused)
        
        return output, attention_weights

class VocalAnalyzer(nn.Module):
    """
    4축 보컬 분석을 위한 멀티모달 딥러닝 모델
    
    Architecture:
    1. Raw Audio Encoder (1D CNN)
    2. Hand-crafted Features Encoder (MLP)
    3. Attention-based Fusion
    4. 4-axis Regression Head
    """
    
    def __init__(self, 
                 audio_length: int = 480000,
                 feature_dim: int = 9,
                 num_axes: int = 4):
        super().__init__()
        
        self.audio_encoder = AudioEncoder(audio_length)
        self.feature_encoder = FeatureEncoder(feature_dim)
        self.fusion = AttentionFusion(512, 128)
        
        # 4축 예측 헤드
        self.regression_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.2),
            
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.2),
            
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.1),
            
            nn.Linear(64, num_axes),
            nn.Sigmoid()  # 0-1 범위로 출력
        )
        
        # 개별 축 예측 헤드 (더 정확한 예측을 위해)
        self.axis_heads = nn.ModuleDict({
            'brightness': self._create_axis_head(),
            'thickness': self._create_axis_head(),
            'loudness': self._create_axis_head(),
            'clarity': self._create_axis_head()
        })
        
    def _create_axis_head(self):
        """개별 축을 위한 전용 헤드"""
        return nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    
    def forward(self, audio, features):
        # Encode inputs
        audio_emb = self.audio_encoder(audio)      # [batch, 512]
        feature_emb = self.feature_encoder(features)  # [batch, 128]
        
        # Fusion
        fused_emb, attention_weights = self.fusion(audio_emb, feature_emb)
        
        # Main regression
        main_output = self.regression_head(fused_emb)  # [batch, 4]
        
        # Individual axis predictions
        axis_outputs = {}
        for axis_name, head in self.axis_heads.items():
            axis_outputs[axis_name] = head(fused_emb).squeeze(-1)  # [batch]
        
        return {
            'main_output': main_output,
            'axis_outputs': axis_outputs,
            'attention_weights': attention_weights,
            'embeddings': {
                'audio': audio_emb,
                'features': feature_emb,
                'fused': fused_emb
            }
        }

class VocalAnalyzerLoss(nn.Module):
    """커스텀 손실 함수"""
    
    def __init__(self, 
                 main_weight: float = 1.0,
                 axis_weight: float = 0.5,
                 consistency_weight: float = 0.1):
        super().__init__()
        
        self.main_weight = main_weight
        self.axis_weight = axis_weight
        self.consistency_weight = consistency_weight
        
        self.mse_loss = nn.MSELoss()
        self.l1_loss = nn.L1Loss()
        
    def forward(self, predictions, targets):
        """
        Args:
            predictions: 모델 출력 딕셔너리
            targets: [batch, 4] 타겟 텐서
        """
        main_output = predictions['main_output']
        axis_outputs = predictions['axis_outputs']
        
        # Main regression loss
        main_loss = self.mse_loss(main_output, targets)
        
        # Individual axis losses
        axis_losses = []
        axis_names = ['brightness', 'thickness', 'loudness', 'clarity']
        
        for i, axis_name in enumerate(axis_names):
            if axis_name in axis_outputs:
                axis_loss = self.mse_loss(axis_outputs[axis_name], targets[:, i])
                axis_losses.append(axis_loss)
        
        axis_loss_total = torch.stack(axis_losses).mean() if axis_losses else 0
        
        # Consistency loss (main vs individual predictions)
        consistency_loss = 0
        if axis_outputs:
            individual_concat = torch.stack([
                axis_outputs[name] for name in axis_names 
                if name in axis_outputs
            ], dim=1)
            consistency_loss = self.l1_loss(main_output, individual_concat)
        
        # Total loss
        total_loss = (self.main_weight * main_loss + 
                     self.axis_weight * axis_loss_total + 
                     self.consistency_weight * consistency_loss)
        
        return {
            'total_loss': total_loss,
            'main_loss': main_loss,
            'axis_loss': axis_loss_total,
            'consistency_loss': consistency_loss
        }

class VocalAnalyzerConfig:
    """모델 설정"""
    
    def __init__(self):
        # 모델 파라미터
        self.audio_length = 480000  # 30초 * 16kHz
        self.feature_dim = 9
        self.num_axes = 4
        
        # 학습 파라미터
        self.batch_size = 16
        self.learning_rate = 1e-4
        self.weight_decay = 1e-5
        self.num_epochs = 100
        
        # 손실 함수 가중치
        self.main_weight = 1.0
        self.axis_weight = 0.5
        self.consistency_weight = 0.1
        
        # 스케줄러
        self.scheduler_step_size = 20
        self.scheduler_gamma = 0.5
        
        # Early stopping
        self.patience = 10
        self.min_delta = 1e-4

# 사용 예시
if __name__ == "__main__":
    # 모델 초기화
    config = VocalAnalyzerConfig()
    model = VocalAnalyzer(
        audio_length=config.audio_length,
        feature_dim=config.feature_dim,
        num_axes=config.num_axes
    )
    
    # 손실 함수
    criterion = VocalAnalyzerLoss(
        main_weight=config.main_weight,
        axis_weight=config.axis_weight,
        consistency_weight=config.consistency_weight
    )
    
    # 테스트 입력
    batch_size = 4
    audio_input = torch.randn(batch_size, config.audio_length)
    feature_input = torch.randn(batch_size, config.feature_dim)
    targets = torch.rand(batch_size, config.num_axes)
    
    # Forward pass
    with torch.no_grad():
        outputs = model(audio_input, feature_input)
        loss_dict = criterion(outputs, targets)
    
    print("Model output keys:", outputs.keys())
    print("Main output shape:", outputs['main_output'].shape)
    print("Attention weights shape:", outputs['attention_weights'].shape)
    print("Total loss:", loss_dict['total_loss'].item())
    
    # 모델 파라미터 수
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")
    print(f"Model size: {total_params * 4 / 1024 / 1024:.2f} MB")  # float32 기준