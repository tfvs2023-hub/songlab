# Advanced Vocal Analysis 설치 가이드

## 방법 1: Docker 사용 (권장)

### 1. Docker 빌드 및 실행
```bash
cd C:\Users\user\Desktop\songlab_advanced

# 이미지 빌드
docker-compose build

# 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f vocal-analyzer

# 테스트
curl http://localhost:8000/api/health
```

### 2. 오디오 파일 테스트
```bash
# audio_data 폴더 생성
mkdir audio_data

# 오디오 파일 복사 (예시)
copy "C:\Users\user\Downloads\상일2.wav" "audio_data\test.wav"

# API 테스트 (Postman이나 curl 사용)
curl -X POST "http://localhost:8000/api/analyze" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@audio_data/test.wav"
```

## 방법 2: Conda 환경

### 1. Conda 환경 생성
```bash
# 환경 생성
conda env create -f conda_setup.yml

# 환경 활성화  
conda activate vocal-analyzer-advanced

# Essentia 수동 설치 (필요시)
pip install essentia==2.1b5 --no-deps
```

### 2. 서비스 실행
```bash
# FastAPI 서버 실행
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 또는 직접 테스트
python test_audio_analysis.py
```

## 방법 3: 개발 환경 (Jupyter)

```bash
# 개발용 Jupyter 실행
docker-compose --profile dev up jupyter

# 브라우저에서 접속
# http://localhost:8888
```

## 트러블슈팅

### Essentia 설치 오류
1. **Ubuntu/Linux**: `apt-get install libessentia-dev`
2. **Windows**: Docker 사용 권장
3. **macOS**: `brew install essentia`

### Docker 메모리 부족
```bash
# Docker Desktop > Settings > Resources
# Memory를 최소 4GB로 설정
```

### 오디오 파일 포맷 지원
- 지원: WAV, MP3, FLAC, OGG, M4A
- 권장: WAV (16bit, 44.1kHz)

## API 엔드포인트

- **GET** `/` - 서비스 정보
- **GET** `/api/health` - 헬스체크
- **POST** `/api/analyze` - 4축 보컬 분석
- **GET** `/api/compare` - 시스템 비교 정보
- **GET** `/docs` - Swagger 문서

## 원래 계획 (수정 금지)

### 4축 분석 시스템:
1. **밝기 (Brightness)**: Spectral centroid + Formant 비율 (Essentia + Praat)
2. **두께 (Thickness)**: Harmonic richness + Spectral complexity (Essentia + Torchaudio) 
3. **성대 내전 (Adduction)**: HNR + Jitter/Shimmer (Praat)
4. **음압 (SPL)**: RMS + LUFS + Dynamic range (Torchaudio + PyLoudnorm)

### 라이브러리 조합:
- **Praat**: 성대 내전 + 포먼트 분석
- **Essentia**: 하모닉 + 스펙트럼 분석
- **Torchaudio**: GPU 가속 처리
- **PyLoudnorm**: LUFS 표준 음압 측정