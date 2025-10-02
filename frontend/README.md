# SongLab Frontend

React + Vite 기반의 SongLab 프런트엔드입니다. 음성 파일을 업로드하여 백엔드(`/api/analyze`)에서 분석한 결과를 시각화하고, OpenAI 요약과 YouTube 추천 강의를 보여줍니다.

## 빠른 시작

```bash
cd frontend
npm install
npm run dev
```

개발 서버는 `/api` 요청을 기본적으로 `http://localhost:8000`으로 프록시합니다. 다른 주소를 사용하려면 `VITE_DEV_API_PROXY` 환경 변수를 지정하거나 `.env` 파일의 `VITE_API_BASE_URL`로 명시하세요. 프로덕션 빌드에서는 동일한 오리진(`/api`)이 기본값입니다.

```env
VITE_API_BASE_URL=https://your-backend.example.com
```

## 주요 기능
- 음성 파일 업로드 및 분석 요청
- 포먼트/흉성·두성 비율/명료도/파워 지표 카드
- OpenAI 기반 발성 해석 코멘트
- YouTube 추천 강의 목록

## 빌드

```bash
npm run build
```

생성된 정적 파일은 `frontend/dist`에 위치합니다.

