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
### 로컬 개발 (분리 실행)
- **백엔드 (FastAPI)**
  ```bash
  uvicorn server:app --reload
  ```
- **프런트엔드 (Vite)**
  ```bash
  cd frontend
  npm run dev
  ```
  Vite 개발 서버는 `/api` 요청을 기본적으로 `http://localhost:8000`으로 프록시합니다. 다른 주소를 사용하려면 `VITE_DEV_API_PROXY` 환경 변수를 지정하거나 `.env`에 `VITE_API_BASE_URL`을 설정하세요.

### 통합 실행 (FastAPI 정적 서빙)
```bash
npm --prefix frontend run build
uvicorn server:app --reload
```
`frontend/dist`가 존재하면 FastAPI가 정적 자산을 루트(`/`)에서 제공하고, `/api/*` 요청은 그대로 API로 전달됩니다. 빌드 디렉터리가 다른 위치라면 `SONGLAB_FRONTEND_DIST` 환경 변수로 경로를 지정하세요.

## 배포 (Google Cloud Run + GitHub Actions)
1. Google Cloud에서 Cloud Run, Cloud Build, Artifact Registry API를 활성화합니다.
2. Cloud Run용 서비스 계정을 만들고 `roles/run.admin`, `roles/artifactregistry.admin`, `roles/iam.serviceAccountUser` 권한을 부여한 뒤 키(JSON)를 발급합니다.
3. GitHub 저장소의 Settings → Secrets에서 다음 키를 등록합니다.
   - `GCP_PROJECT_ID`, `GCP_REGION`, `CLOUD_RUN_SERVICE`
   - `GOOGLE_CREDENTIALS` (2단계에서 발급한 서비스 계정 JSON)
   - `OPENAI_API_KEY`, `YOUTUBE_API_KEY`, 필요 시 `SONGLAB_CORS_ORIGINS`
4. `main` 브랜치에 push하거나 Actions에서 `Deploy to Cloud Run` 워크플로를 수동 실행하면 Dockerfile 기반 컨테이너를 빌드해 Cloud Run으로 배포합니다.
5. Cloud Run 배포 후 서비스의 환경 변수(`OPENAI_API_KEY`, `YOUTUBE_API_KEY` 등)가 올바르게 설정됐는지 확인하고, 도메인에 맞춰 CORS 원본을 조정하세요.

멀티 스테이지 `Dockerfile`이 프런트엔드를 먼저 빌드한 뒤 FastAPI 백엔드를 8080 포트에서 구동합니다. `crepe`/`pyworld` 의존성 설치로 최초 빌드가 10~15분까지 걸릴 수 있습니다.

## API 요약
`POST /api/analyze`
- 입력: `multipart/form-data`의 `file` 필드(음성 파일)
- 출력: `metrics`, `interpretation`, `recommendations`

## 참고 사항
- 최초 CREPE 실행 시 모델 다운로드로 10초가량 소요될 수 있습니다.
- OpenAI 호출 시 과금이 발생할 수 있으니 모델/토큰 사용량을 확인하세요.
- YouTube API는 할당량 제한이 있으므로 일일 호출 횟수를 관리하세요.

