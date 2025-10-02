"""FastAPI server exposing SongLab vocal analysis endpoint."""
from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

from analysis import PyWorldVocalAnalyzer
from openai_client import OpenAIClient
from youtube_client import YouTubeClient

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
DEFAULT_FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"
FRONTEND_DIST_ENV = os.getenv("SONGLAB_FRONTEND_DIST")
FRONTEND_DIST_DIR = (Path(FRONTEND_DIST_ENV).expanduser().resolve() if FRONTEND_DIST_ENV else DEFAULT_FRONTEND_DIST)

app = FastAPI(title="SongLab API", version="1.0.0")

origins_raw = os.getenv("SONGLAB_CORS_ORIGINS", "")
if origins_raw:
    allowed_origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
else:
    allowed_origins = DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = PyWorldVocalAnalyzer()
youtube_client = YouTubeClient()
openai_client = OpenAIClient()


def _metrics_prompt(metrics: Dict[str, float]) -> str:
    return (
        "당신은 전문 보컬 트레이너입니다. 곧 제공되는 발성 분석 결과를 정리하고, 하이브리드(가슴/두성) 발성 향상에 "
        "도움이 되는 코칭 포인트 3가지를 제안하세요.\n\n"
        "[분석 수치]\n"
        f"F1: {metrics.get('f1_hz', float('nan')):.1f} Hz\n"
        f"F2: {metrics.get('f2_hz', float('nan')):.1f} Hz\n"
        f"F3: {metrics.get('f3_hz', float('nan')):.1f} Hz\n"
        f"흉/두성 비율: {metrics.get('chest_head_ratio', float('nan')):.2f}\n"
        f"명료도: {metrics.get('clarity', float('nan')):.2f}\n"
        f"소리 파워: {metrics.get('power_db', float('nan')):.2f} dB\n\n"
        "- 수치를 간단히 해석하고, 발성 전략 3가지를 문장형 bullet으로 제시하세요."
    )


def _recommendation_query(metrics: Dict[str, float]) -> str:
    ratio = metrics.get("chest_head_ratio")
    clarity = metrics.get("clarity")
    if ratio is not None:
        if ratio > 2.5:
            focus = "head voice transition"
        elif ratio < 1.0:
            focus = "chest voice support"
        else:
            focus = "mix voice balance"
    else:
        focus = "vocal technique"

    if clarity is not None and clarity < 0.4:
        focus += " resonance clarity"

    return f"{focus} vocal lesson"


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일을 찾을 수 없습니다.")
    if not file.content_type or not file.content_type.startswith("audio"):
        raise HTTPException(status_code=400, detail="음성 파일을 업로드해주세요.")

    suffix = Path(file.filename).suffix or ".wav"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = Path(tmp.name)
        content = await file.read()
        tmp.write(content)

    try:
        metrics_obj = analyzer.analyze(temp_path)
        metrics = metrics_obj.to_dict()
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=f"분석에 실패했습니다: {exc}") from exc
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

    try:
        interpretation = openai_client.summarize_text(_metrics_prompt(metrics))
    except Exception as exc:  # pylint: disable=broad-except
        interpretation = "AI 코멘트를 생성하지 못했습니다. 나중에 다시 시도해주세요."
        print(f"[SongLab] OpenAI 요약 실패: {exc}")

    try:
        query = _recommendation_query(metrics)
        videos = youtube_client.search_videos(query, max_results=6)
        recommendations: List[Dict[str, str]] = [
            {
                "video_id": video.video_id,
                "title": video.title,
                "channel": video.channel,
                "description": video.description,
                "published_at": video.published_at,
            }
            for video in videos
        ]
    except Exception as exc:  # pylint: disable=broad-except
        recommendations = []
        print(f"[SongLab] YouTube 추천 실패: {exc}")

    return JSONResponse(
        {
            "metrics": metrics,
            "interpretation": interpretation,
            "recommendations": recommendations,
        }
    )


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


# Serve built frontend if available.
if FRONTEND_DIST_DIR.exists():
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="songlab-assets")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = FRONTEND_DIST_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

