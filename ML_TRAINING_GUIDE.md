# 🤖 SongLab 딥러닝 모델 학습 가이드

## 📋 개요

SongLab의 4축 보컬 분석을 위한 딥러닝 모델 학습 시스템입니다.

### 🎯 모델 특징
- **멀티모달 아키텍처**: Raw Audio + Hand-crafted Features
- **4축 동시 예측**: Brightness, Thickness, Loudness, Clarity
- **Attention 기반 Fusion**: 두 모달리티를 효과적으로 결합
- **NO Librosa**: Parselmouth 기반으로 알러지 없음
- **CPU/GPU 모두 지원**: CUDA 가속 가능

## 🏗️ 아키텍처

```
Raw Audio (30초)          Hand-crafted Features (9차원)
       ↓                              ↓
   1D CNN Encoder                 MLP Encoder
   (AudioEncoder)               (FeatureEncoder)
       ↓                              ↓
   Audio Embedding                Feature Embedding
    (512차원)                      (128차원)
        ↓─────────── Attention Fusion ────────────↓
                         ↓
                   Fused Embedding
                      (512차원)
                         ↓
              ┌─────────────────────────┐
              ↓                         ↓
         Main Head                 Individual Heads
        (4축 동시)                  (축별 전용)
              ↓                         ↓
         [B,T,L,C]                [B][T][L][C]
```

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 의존성 설치
pip install -r ml/requirements.txt
```

### 2. 데이터 수집
```bash
# 데이터 수집기 실행 (웹서버와 연동)
python -c "
from ml.data_pipeline import DataCollector
collector = DataCollector()
print('데이터 수집 준비 완료')
print(f'현재 샘플 수: {collector.metadata[\"total_samples\"]}')
"
```

### 3. 학습 시작
```bash
# 기본 학습
python ml/train.py --experiment-name my_experiment

# 파라미터 조정
python ml/train.py \
  --experiment-name vocal_v2 \
  --batch-size 32 \
  --epochs 200 \
  --lr 1e-3
```

## 📊 데이터 파이프라인

### 데이터 구조
```
data/collected/
├── audio/           # 원본 음성 파일 (.wav)
├── labels/          # 분석 결과 라벨 (.json)
└── metadata.json    # 전체 메타데이터
```

### 데이터 수집 과정
1. **사용자 음성 녹음** → 웹 인터페이스
2. **기존 분석기 분석** → 4축 점수 생성
3. **사용자 동의 확인** → 개인정보 처리방침
4. **데이터 저장** → 익명화 후 저장
5. **학습 데이터셋 구성** → 자동 train/val 분할

### 특징 추출
- **Pitch**: F0 평균, 표준편차, 최솟값, 최댓값
- **Formants**: F1, F2 평균
- **Intensity**: 음압 평균, 표준편차
- **Spectral**: 스펙트럴 중심, 롤오프
- **Temporal**: Zero Crossing Rate

## 🎛️ 모델 설정

### VocalAnalyzerConfig
```python
class VocalAnalyzerConfig:
    # 모델 파라미터
    audio_length = 480000      # 30초 * 16kHz
    feature_dim = 9            # 특징 벡터 차원
    num_axes = 4               # 4축 출력
    
    # 학습 파라미터
    batch_size = 16            # 배치 크기
    learning_rate = 1e-4       # 학습률
    weight_decay = 1e-5        # L2 정규화
    num_epochs = 100           # 에포크 수
    
    # 손실 함수 가중치
    main_weight = 1.0          # 메인 회귀 손실
    axis_weight = 0.5          # 개별 축 손실
    consistency_weight = 0.1   # 일관성 손실
```

## 📈 학습 모니터링

### TensorBoard
```bash
# TensorBoard 실행
tensorboard --logdir experiments/

# 브라우저에서 확인
# http://localhost:6006
```

### 주요 메트릭
- **Loss**: Total, Main, Axis, Consistency
- **MSE**: 평균 제곱 오차 (전체 및 축별)
- **MAE**: 평균 절대 오차 (전체 및 축별)
- **R²**: 결정계수 (전체 및 축별)
- **Attention Weights**: 모달리티별 가중치

### 로그 파일
```
experiments/my_experiment/
├── logs/
│   ├── training.log         # 텍스트 로그
│   └── events.out.tfevents  # TensorBoard 로그
├── checkpoints/
│   ├── best.pth            # 최고 성능 모델
│   ├── latest.pth          # 최신 체크포인트
│   └── checkpoint_epoch_*.pth
├── config.json             # 학습 설정
└── training_history.png    # 학습 곡선 그래프
```

## 🔧 고급 사용법

### 1. 체크포인트에서 재시작
```bash
python ml/train.py \
  --resume experiments/my_experiment/checkpoints/latest.pth \
  --experiment-name my_experiment_continued
```

### 2. 하이퍼파라미터 튜닝
```bash
# 높은 학습률 + 더 큰 배치
python ml/train.py \
  --lr 5e-4 \
  --batch-size 32 \
  --experiment-name high_lr_experiment

# 더 강한 정규화
python ml/train.py \
  --experiment-name strong_reg \
  # config.py에서 weight_decay = 1e-4로 수정
```

### 3. 데이터 증강 (향후 추가 예정)
- Pitch shifting
- Time stretching  
- Background noise 추가
- SpecAugment

## 📱 모델 배포

### ONNX 변환
```python
# 학습된 모델을 ONNX로 변환
import torch
from ml.model import VocalAnalyzer

model = VocalAnalyzer()
model.load_state_dict(torch.load('best.pth')['model_state_dict'])
model.eval()

# 더미 입력
audio_input = torch.randn(1, 480000)
feature_input = torch.randn(1, 9)

# ONNX 내보내기
torch.onnx.export(
    model, 
    (audio_input, feature_input),
    'vocal_analyzer.onnx',
    export_params=True,
    opset_version=11,
    input_names=['audio', 'features'],
    output_names=['predictions']
)
```

### 프로덕션 통합
```python
# 기존 vocal_analyzer_studio.py에 통합
import onnxruntime as ort

class DeepLearningAnalyzer:
    def __init__(self, model_path):
        self.session = ort.InferenceSession(model_path)
    
    def analyze(self, audio, features):
        outputs = self.session.run(
            None, 
            {'audio': audio, 'features': features}
        )
        return outputs[0]  # 4축 예측 결과
```

## 🔍 문제 해결

### 일반적인 문제들

#### 1. CUDA 메모리 부족
```bash
# 배치 크기 줄이기
python ml/train.py --batch-size 8

# 또는 Gradient Accumulation 사용 (구현 예정)
```

#### 2. 데이터 부족
```
최소 요구사항: 20개 샘플 (학습/검증용)
권장사항: 1000개 이상 샘플

해결방법:
- 더 많은 사용자 데이터 수집
- 데이터 증강 기법 적용
- Transfer Learning (사전 훈련된 모델 사용)
```

#### 3. 과적합 (Overfitting)
```python
# config.py에서 정규화 강화
weight_decay = 1e-4
dropout = 0.3

# Early stopping patience 줄이기
patience = 5
```

#### 4. 학습이 안됨 (Loss 감소 없음)
```bash
# 학습률 조정
python ml/train.py --lr 1e-3  # 높이기
python ml/train.py --lr 1e-5  # 낮추기

# 배치 크기 조정
python ml/train.py --batch-size 4   # 줄이기
python ml/train.py --batch-size 64  # 늘리기
```

## 📊 성능 벤치마크

### 목표 성능
- **MSE < 0.01**: 매우 우수
- **MSE < 0.05**: 우수  
- **MSE < 0.1**: 양호
- **R² > 0.9**: 매우 우수
- **R² > 0.8**: 우수

### 축별 성능 가이드
```
Brightness (밝기):   가장 예측하기 쉬움
Clarity (명료도):    두 번째로 쉬움
Loudness (음압):     보통 난이도
Thickness (두께):    가장 어려움 (주관적)
```

## 🚀 향후 계획

### Phase 1 (v1.0.0)
- [x] 기본 멀티모달 아키텍처
- [x] 4축 동시 예측
- [x] 학습 파이프라인 구축
- [ ] 프로덕션 배포

### Phase 2 (v2.0.0)
- [ ] Transformer 기반 아키텍처
- [ ] Self-supervised pre-training
- [ ] 리듬 분석 추가
- [ ] 성구 전환 감지
- [ ] 가수 유사도 측정

### Phase 3 (v3.0.0)
- [ ] 실시간 스트리밍 분석
- [ ] 멀티모달 (오디오 + 비디오)
- [ ] 개인화된 추천 시스템
- [ ] 클라우드 AutoML 지원

---

## 💡 Tips

1. **데이터 품질이 가장 중요**: 노이즈가 적고 다양한 샘플 수집
2. **단계적 학습**: 작은 데이터셋으로 파이프라인 검증 후 확장
3. **정기적 모니터링**: TensorBoard로 실시간 학습 상태 확인
4. **앙상블 고려**: 여러 모델의 예측을 결합하여 성능 향상
5. **도메인 지식 활용**: 보컬 전문가의 피드백을 모델에 반영

**성공적인 딥러닝 학습을 위해 화이팅! 🎤✨**