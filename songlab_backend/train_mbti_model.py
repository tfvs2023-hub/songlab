"""
MBTI 보컬 분류 딥러닝 모델 학습 시스템
라벨링된 데이터셋으로 4축 MBTI 점수 예측 모델 학습
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
import librosa
from sklearn.model_selection import train_test_split
from typing import Dict, Tuple
import json
import os

class VocalMBTIDataset(Dataset):
    """
    보컬 MBTI 데이터셋 클래스
    """
    def __init__(self, data_path: str, labels_path: str, sr=22050):
        """
        data_path: 오디오 파일들이 있는 폴더
        labels_path: 라벨 CSV 파일 경로
        
        CSV 형식:
        filename,brightness,thickness,clarity,power
        voice1.wav,-65,75,45,82
        voice2.wav,70,-40,85,65
        """
        self.sr = sr
        self.data_path = data_path
        
        # 라벨 로드
        self.labels_df = pd.read_csv(labels_path)
        self.filenames = self.labels_df['filename'].tolist()
        
        # MBTI 점수 정규화 (-100 ~ 100 -> -1 ~ 1)
        self.brightness = self.labels_df['brightness'].values / 100
        self.thickness = self.labels_df['thickness'].values / 100
        self.clarity = self.labels_df['clarity'].values / 100
        self.power = self.labels_df['power'].values / 100
        
    def __len__(self):
        return len(self.filenames)
    
    def __getitem__(self, idx):
        # 오디오 로드 및 특징 추출
        audio_path = os.path.join(self.data_path, self.filenames[idx])
        features = self.extract_features(audio_path)
        
        # 라벨 (4축 MBTI 점수)
        labels = torch.FloatTensor([
            self.brightness[idx],
            self.thickness[idx],
            self.clarity[idx],
            self.power[idx]
        ])
        
        return features, labels
    
    def extract_features(self, audio_path: str) -> torch.Tensor:
        """
        오디오에서 특징 추출 (MFCC + 스펙트럼 특징)
        """
        # 오디오 로드
        audio, sr = librosa.load(audio_path, sr=self.sr, mono=True)
        
        # 전처리
        audio = librosa.effects.trim(audio, top_db=20)[0]
        audio = librosa.util.normalize(audio)
        
        # 특징 추출
        features = []
        
        # 1. MFCC (13차원)
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1)
        mfcc_std = np.std(mfcc, axis=1)
        features.extend(mfcc_mean)
        features.extend(mfcc_std)
        
        # 2. 스펙트럼 중심
        spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        features.append(np.mean(spectral_centroid))
        features.append(np.std(spectral_centroid))
        
        # 3. 스펙트럼 대역폭
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0]
        features.append(np.mean(spectral_bandwidth))
        features.append(np.std(spectral_bandwidth))
        
        # 4. 스펙트럼 롤오프
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
        features.append(np.mean(spectral_rolloff))
        features.append(np.std(spectral_rolloff))
        
        # 5. Zero Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        features.append(np.mean(zcr))
        features.append(np.std(zcr))
        
        # 6. RMS 에너지
        rms = librosa.feature.rms(y=audio)[0]
        features.append(np.mean(rms))
        features.append(np.std(rms))
        
        # 7. 하모닉-퍼커시브 비율
        harmonic, percussive = librosa.effects.hpss(audio)
        harmonic_ratio = np.mean(np.abs(harmonic)) / (np.mean(np.abs(harmonic)) + np.mean(np.abs(percussive)) + 1e-6)
        features.append(harmonic_ratio)
        
        return torch.FloatTensor(features)


class MBTIVocalNet(nn.Module):
    """
    MBTI 보컬 분류 딥러닝 모델
    """
    def __init__(self, input_size=37):
        super(MBTIVocalNet, self).__init__()
        
        # 특징 추출 네트워크
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
            nn.Dropout(0.3),
            
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.BatchNorm1d(512),
            nn.Dropout(0.3),
            
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.BatchNorm1d(256),
        )
        
        # 4축 예측 헤드 (각 축별 전문화)
        self.brightness_head = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Tanh()  # -1 ~ 1 범위
        )
        
        self.thickness_head = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Tanh()
        )
        
        self.clarity_head = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Tanh()
        )
        
        self.power_head = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Tanh()
        )
    
    def forward(self, x):
        # 공통 특징 추출
        features = self.feature_extractor(x)
        
        # 4축 예측
        brightness = self.brightness_head(features)
        thickness = self.thickness_head(features)
        clarity = self.clarity_head(features)
        power = self.power_head(features)
        
        return torch.cat([brightness, thickness, clarity, power], dim=1)


def train_model(data_path: str, labels_path: str, epochs: int = 100):
    """
    모델 학습 메인 함수
    """
    # 데이터셋 생성
    dataset = VocalMBTIDataset(data_path, labels_path)
    
    # 학습/검증 분리 (8:2)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    # 데이터로더
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    # 모델, 손실함수, 옵티마이저
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = MBTIVocalNet().to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10)
    
    print(f"🚀 학습 시작 - Device: {device}")
    print(f"   학습 데이터: {train_size}개, 검증 데이터: {val_size}개")
    
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        # 학습 페이즈
        model.train()
        train_loss = 0
        for features, labels in train_loader:
            features, labels = features.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        # 검증 페이즈
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                outputs = model(features)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
        
        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        
        # 학습률 조정
        scheduler.step(avg_val_loss)
        
        # 진행상황 출력
        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}] Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
        
        # 최고 모델 저장
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': avg_val_loss,
            }, 'best_mbti_model.pth')
            print(f"   ✅ 최고 모델 저장 (Val Loss: {avg_val_loss:.4f})")
    
    print(f"\n🎯 학습 완료! 최종 검증 손실: {best_val_loss:.4f}")
    return model


def predict_mbti(model_path: str, audio_path: str) -> Dict:
    """
    학습된 모델로 MBTI 예측
    """
    # 모델 로드
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = MBTIVocalNet().to(device)
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # 특징 추출
    dataset = VocalMBTIDataset('.', 'dummy.csv')  # 더미 인스턴스
    features = dataset.extract_features(audio_path).unsqueeze(0).to(device)
    
    # 예측
    with torch.no_grad():
        outputs = model(features)
        predictions = outputs.squeeze().cpu().numpy() * 100  # -100 ~ 100 범위로 복원
    
    return {
        'brightness': int(predictions[0]),
        'thickness': int(predictions[1]),
        'clarity': int(predictions[2]),
        'power': int(predictions[3])
    }


if __name__ == "__main__":
    # 사용 예시
    print("=" * 50)
    print("🎤 MBTI 보컬 딥러닝 모델 학습")
    print("=" * 50)
    
    # 1. 데이터 준비 (CSV 파일 형식)
    sample_csv = """filename,brightness,thickness,clarity,power
voice1.wav,-65,75,45,82
voice2.wav,70,-40,85,65
voice3.wav,30,-60,-35,-45
voice4.wav,-45,65,70,90
"""
    
    with open('sample_labels.csv', 'w') as f:
        f.write(sample_csv)
    
    print("📊 샘플 라벨 파일 생성됨: sample_labels.csv")
    print("\n필요한 데이터:")
    print("1. 오디오 파일들 (./audio_data/ 폴더)")
    print("2. 라벨 CSV 파일 (filename, brightness, thickness, clarity, power)")
    print("\n학습 시작: train_model('./audio_data/', 'labels.csv', epochs=100)")