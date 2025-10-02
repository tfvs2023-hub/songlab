# SongLab PyWorld Vocal Analyzer

pyworld와 CREPE를 활용해 발성 지표를 계산하고, OpenAI/YouTube API를 결합해 개인 맞춤형 학습 추천을 제공하는 실험 환경입니다.

## 구성 요소
- **Backend (`server.py`)**: FastAPI 기반 `/api/analyze` 엔드포인트(음성 분석 + OpenAI 해석 + YouTube 추천)
- **Vocal Analysis Core (`analysis.py`)**: 음성 파일에서 포먼트·흉성/두성 비율·명료도·파워 계산
- **OpenAI Helper (`openai_client.py`)** / **YouTube Helper (`youtube_client.py`)**
- **Frontend (`frontend/`)**: React + Vite로 구현한 SongLab UI

## 설치
```bash
python -m venv .venv
.\.venv\Scripts\activate        # PowerShell 기준
pip install -r requirements.txt
cd frontend
npm install
```

## 환경 변수 설정
루트에 `.env` 파일을 만들고 아래 키를 붙여넣습니다.
```env
YOUTUBE_API_KEY=발급받은_유튜브_API키
OPENAI_API_KEY=발급받은_OpenAI_API키
```
`python-dotenv` 덕분에 백엔드 실행 시 자동으로 로드됩니다.

## 실행 방법
### 1. 백엔드 (FastAPI)
```bash
# 루트(songlab)에서
uvicorn server:app --reload
```

### 2. 프런트엔드 (Vite)
```bash
cd frontend
npm run dev
```
기본 API 엔드포인트는 `http://localhost:8000`이며, 프런트 개발 서버는 `http://localhost:5173`에서 열립니다.

## API 요약
`POST /api/analyze`
- 입력: `multipart/form-data`의 `file` 필드(음성 파일)
- 출력: `metrics`, `interpretation`, `recommendations`

## 참고 사항
- 최초 CREPE 실행 시 모델 다운로드로 10초가량 소요될 수 있습니다.
- OpenAI 호출 시 과금이 발생할 수 있으니 모델/토큰 사용량을 확인하세요.
- YouTube API는 할당량 제한이 있으므로 일일 호출 횟수를 관리하세요.
