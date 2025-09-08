"""
지식 증류(Knowledge Distillation) - 소형 MBTI 모델 → 대형 모델 전달
전문가 모델의 지식을 대형 모델에 효율적으로 전달
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
from typing import Dict, List, Tuple

class TeacherModel(nn.Module):
    """
    Teacher 모델 (기존 학습된 소형 MBTI 모델)
    """
    def __init__(self, model_path: str):
        super().__init__()
        from train_mbti_model import MBTIVocalNet
        
        self.model = MBTIVocalNet()
        checkpoint = torch.load(model_path, map_location='cpu')
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        # Teacher는 고정 (학습하지 않음)
        for param in self.model.parameters():
            param.requires_grad = False
    
    def forward(self, x):
        return self.model(x)
    
    def get_soft_targets(self, x, temperature=3.0):
        """
        소프트 타겟 생성 (온도 스케일링)
        """
        with torch.no_grad():
            logits = self.model(x)
            # 온도로 소프트맥스 스케일링
            soft_targets = torch.softmax(logits / temperature, dim=1)
        return soft_targets


class StudentModel(nn.Module):
    """
    Student 모델 (대형 트랜스포머 기반)
    """
    def __init__(self, input_size=37, hidden_size=1024, num_layers=8):
        super().__init__()
        
        # 대형 트랜스포머 블록
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=16,
            dim_feedforward=hidden_size * 4,
            dropout=0.1,
            activation='gelu'
        )
        
        self.input_projection = nn.Linear(input_size, hidden_size)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.layer_norm = nn.LayerNorm(hidden_size)
        
        # 4축 MBTI 출력 헤드
        self.output_head = nn.Sequential(
            nn.Linear(hidden_size, 512),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, 4),  # brightness, thickness, clarity, power
            nn.Tanh()
        )
    
    def forward(self, x):
        # [batch_size, input_size] -> [batch_size, 1, hidden_size]
        x = self.input_projection(x).unsqueeze(1)
        
        # 트랜스포머 처리
        x = self.transformer(x.transpose(0, 1))  # [1, batch_size, hidden_size]
        x = self.layer_norm(x.squeeze(0))  # [batch_size, hidden_size]
        
        # MBTI 4축 출력
        return self.output_head(x)


class DistillationLoss(nn.Module):
    """
    지식 증류 손실 함수
    """
    def __init__(self, temperature=3.0, alpha=0.7):
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha  # teacher loss 가중치
        self.mse_loss = nn.MSELoss()
        self.kl_loss = nn.KLDivLoss(reduction='batchmean')
    
    def forward(self, student_outputs, teacher_outputs, true_labels):
        # 1. 하드 타겟 손실 (실제 라벨과의 MSE)
        hard_loss = self.mse_loss(student_outputs, true_labels)
        
        # 2. 소프트 타겟 손실 (teacher와의 KL divergence)
        student_soft = torch.log_softmax(student_outputs / self.temperature, dim=1)
        teacher_soft = torch.softmax(teacher_outputs / self.temperature, dim=1)
        soft_loss = self.kl_loss(student_soft, teacher_soft) * (self.temperature ** 2)
        
        # 3. 가중 결합
        total_loss = self.alpha * soft_loss + (1 - self.alpha) * hard_loss
        
        return total_loss, hard_loss, soft_loss


def distill_knowledge(teacher_model_path: str, 
                     train_loader: DataLoader,
                     val_loader: DataLoader,
                     epochs: int = 50):
    """
    지식 증류 학습
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Teacher와 Student 모델 초기화
    teacher = TeacherModel(teacher_model_path).to(device)
    student = StudentModel().to(device)
    
    # 손실함수와 옵티마이저
    distill_criterion = DistillationLoss(temperature=4.0, alpha=0.8)
    optimizer = optim.AdamW(student.parameters(), lr=1e-4, weight_decay=0.01)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    print(f"🎓 지식 증류 시작")
    print(f"   Teacher: {sum(p.numel() for p in teacher.parameters() if p.requires_grad)}M params")
    print(f"   Student: {sum(p.numel() for p in student.parameters() if p.requires_grad)/1e6:.1f}M params")
    
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        # 학습 페이즈
        student.train()
        total_loss, total_hard, total_soft = 0, 0, 0
        
        for features, labels in train_loader:
            features, labels = features.to(device), labels.to(device)
            
            # Teacher의 예측 (고정)
            with torch.no_grad():
                teacher_outputs = teacher(features)
            
            # Student의 예측
            student_outputs = student(features)
            
            # 지식 증류 손실 계산
            loss, hard_loss, soft_loss = distill_criterion(
                student_outputs, teacher_outputs, labels
            )
            
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
            optimizer.step()
            
            total_loss += loss.item()
            total_hard += hard_loss.item()
            total_soft += soft_loss.item()
        
        scheduler.step()
        
        # 검증
        student.eval()
        val_loss = 0
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                
                teacher_outputs = teacher(features)
                student_outputs = student(features)
                
                loss, _, _ = distill_criterion(student_outputs, teacher_outputs, labels)
                val_loss += loss.item()
        
        avg_train_loss = total_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        avg_hard_loss = total_hard / len(train_loader)
        avg_soft_loss = total_soft / len(train_loader)
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}]")
            print(f"   Total: {avg_train_loss:.4f}, Hard: {avg_hard_loss:.4f}, Soft: {avg_soft_loss:.4f}")
            print(f"   Val: {avg_val_loss:.4f}, LR: {optimizer.param_groups[0]['lr']:.6f}")
        
        # 최고 모델 저장
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save({
                'epoch': epoch,
                'student_state_dict': student.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': avg_val_loss,
            }, 'distilled_large_model.pth')
    
    print(f"\n🎯 지식 증류 완료! 대형 모델 저장됨")
    return student


class HybridMBTISystem:
    """
    하이브리드 MBTI 시스템 (소형 + 대형 모델 앙상블)
    """
    def __init__(self, teacher_path: str, student_path: str):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Teacher 모델 (빠르고 정확)
        self.teacher = TeacherModel(teacher_path).to(self.device)
        
        # Student 모델 (대형, 표현력 풍부)
        self.student = StudentModel().to(self.device)
        checkpoint = torch.load(student_path, map_location=self.device)
        self.student.load_state_dict(checkpoint['student_state_dict'])
        self.student.eval()
    
    def predict(self, features: torch.Tensor, use_ensemble=True) -> Dict:
        """
        하이브리드 예측 (앙상블 또는 단일)
        """
        features = features.to(self.device)
        
        with torch.no_grad():
            # Teacher 예측 (빠름)
            teacher_pred = self.teacher(features).squeeze().cpu().numpy()
            
            if use_ensemble:
                # Student 예측 (정교함)
                student_pred = self.student(features).squeeze().cpu().numpy()
                
                # 가중 앙상블 (Teacher 70%, Student 30%)
                ensemble_pred = teacher_pred * 0.7 + student_pred * 0.3
                predictions = ensemble_pred * 100  # -100 ~ 100 범위
            else:
                predictions = teacher_pred * 100
        
        return {
            'brightness': int(predictions[0]),
            'thickness': int(predictions[1]),
            'clarity': int(predictions[2]),
            'power': int(predictions[3]),
            'confidence': 0.95 if use_ensemble else 0.85
        }


# 사용 예시
if __name__ == "__main__":
    print("🧠 MBTI 지식 증류 시스템")
    print("=" * 50)
    
    print("1단계: 소형 전문가 모델 학습")
    print("2단계: 지식 증류로 대형 모델 학습") 
    print("3단계: 하이브리드 앙상블 시스템 구축")
    print("\n💡 장점:")
    print("   • 소형 모델: 빠른 추론 속도")
    print("   • 대형 모델: 풍부한 표현력")
    print("   • 앙상블: 최고 정확도")
    
    # distill_knowledge('best_mbti_model.pth', train_loader, val_loader)