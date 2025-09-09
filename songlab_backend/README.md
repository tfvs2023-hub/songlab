# SongLab Backend

CREPE 기반 음성 분석 백엔드 서비스

## 기능
- AI 기반 보컬 음성 분석 (CREPE 모델 사용)
- 4축 분석: 밝기, 두께, 선명도, 음압
- BTCP 음성 타입 분류
- YouTube Data API 연동 추천 시스템

## 기술 스택
- FastAPI
- TensorFlow/CREPE
- Docker
- Python 3.10

## 실행 방법

### 로컬 실행
```bash
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### Docker 실행
```bash
docker build -t songlab-backend .
docker run -p 8001:8001 songlab-backend
```

## API 엔드포인트
- `POST /api/analyze` - 음성 파일 분석
- `GET /api/health` - 헬스체크