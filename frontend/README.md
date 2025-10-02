# SongLab Frontend

React + Vite 기반의 SongLab 프런트엔드입니다. 음성 파일을 업로드하여 백엔드(`/api/analyze`)에서 분석한 결과를 시각화하고, OpenAI 요약과 YouTube 추천 강의를 보여줍니다.

## 빠른 시작

```bash
cd frontend
npm install
npm run dev
```

기본 API 엔드포인트는 `http://localhost:8000`입니다. 다른 서버를 사용하려면 `.env` 파일을 만들어 `VITE_API_BASE_URL`을 설정하세요.

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
