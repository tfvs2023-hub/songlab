"""
Advanced Vocal Analysis API v2.0
폰 녹음 최적화 4축 분석 시스템
Lite(즉시) + Pro(정밀) 듀얼 엔진
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import (BackgroundTasks, FastAPI, File, HTTPException, Request,
                     UploadFile)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from recording_detector import RecordingDetector

# 분석 엔진들 will be imported lazily inside getters to avoid
# hard dependency on heavy native libs at import time (e.g. parselmouth)

# Logging 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vocal Analysis API v2.0",
    description="폰 녹음 최적화 4축 보컬 분석 (밝기, 두께, 음압, 선명도)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 분석기 초기화 (지연 초기화: 헬스체크와 빠른 임포트를 위해 즉시 생성하지 않음)
_lite_analyzer = None
_studio_analyzer = None
_detector = None
_youtube_service = None


def get_lite_analyzer():
    """Lazy getter for Lite analyzer."""
    global _lite_analyzer
    if _lite_analyzer is None:
        try:
            from vocal_analyzer_lite import VocalAnalyzerLite
        except ImportError as e:
            # keep import-time lightweight; raise when actually used
            raise RuntimeError("Lite analyzer not available: %s" % e)
        _lite_analyzer = VocalAnalyzerLite()
    return _lite_analyzer


def get_studio_analyzer():
    """Lazy getter for Studio analyzer."""
    global _studio_analyzer
    if _studio_analyzer is None:
        try:
            from vocal_analyzer_studio import VocalAnalyzerStudio
        except ImportError as e:
            raise RuntimeError("Studio analyzer not available: %s" % e)
        _studio_analyzer = VocalAnalyzerStudio()
    return _studio_analyzer


def get_detector():
    """Lazy getter for RecordingDetector."""
    global _detector
    if _detector is None:
        _detector = RecordingDetector()
    return _detector


def get_youtube_service():
    """Lazy getter for YouTubeService."""
    global _youtube_service
    if _youtube_service is None:
        try:
            from youtube_service import YouTubeService
        except ImportError as e:
            # YouTube recommendations are optional; provide a minimal stub
            class YouTubeService:
                def get_recommended_videos(self, *args, **kwargs):
                    return []

            _youtube_service = YouTubeService()
            return _youtube_service
        _youtube_service = YouTubeService()
    return _youtube_service


# 임시 결과 저장소 (실제로는 Redis/DB 사용)
analysis_results = {}


import json
# Simple uploads storage (local filesystem + metadata log) for anonymous collection
import os

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
METADATA_LOG = os.path.join(UPLOAD_DIR, "metadata.log")


@app.post("/api/upload")
async def upload_audio(request: Request, file: UploadFile = File(...)):
    """Accept audio uploads, store file locally and append metadata (anon_id, timestamp)

    This is a minimal, low-risk implementation for anonymous data collection. Files are
    written to `uploads/` and metadata appended as JSON lines to `uploads/metadata.log`.
    """
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file")

        # enforce max size 50MB
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")

        ts = datetime.utcnow().isoformat() + "Z"
        safe_name = (
            f"{int(time.time())}_{uuid.uuid4().hex}_{os.path.basename(file.filename)}"
        )
        file_path = os.path.join(UPLOAD_DIR, safe_name)

        with open(file_path, "wb") as f:
            f.write(contents)

        # collect metadata: try to read anon_id from header or cookie
        anon_id = None
        if "x-anon-id" in request.headers:
            anon_id = request.headers.get("x-anon-id")
        else:
            # attempt to read Cookie header
            cookie = request.headers.get("cookie", "")
            for part in cookie.split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    if k == "anon_id":
                        anon_id = v
                        break

        metadata = {
            "filename": safe_name,
            "original_filename": file.filename,
            "anon_id": anon_id,
            "timestamp": ts,
            "size": len(contents),
        }

        # append metadata as JSON line
        with open(METADATA_LOG, "a", encoding="utf-8") as ml:
            ml.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        return {"status": "success", "file": safe_name, "metadata": metadata}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload error")
        raise HTTPException(status_code=500, detail=str(e))


class AnalysisResult(BaseModel):
    """분석 결과 모델"""

    brightness: float
    thickness: float
    loudness: float
    clarity: float
    confidence: float
    quality: Dict
    engine: str
    model: Optional[str] = None


class FeedbackData(BaseModel):
    """사용자 피드백 모델"""

    analysis_id: str
    brightness: float
    thickness: float
    loudness: float
    clarity: float


@app.post("/api/analyze")
async def analyze_voice_auto(
    file: UploadFile = File(...),
    force_engine: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
):
    """
    자동 엔진 선택 분석
    환경 감지 후 Lite(폰) 또는 Studio(고품질) 엔진 선택
    force_engine: 'lite' 또는 'studio'로 강제 지정 가능
    """
    analysis_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # 파일 타입 검증: 일부 clients (curl) may omit content-type; allow based on filename
        allowed_exts = (".wav", ".mp3", ".flac", ".ogg", ".m4a")
        content_type_ok = bool(
            file.content_type and file.content_type.startswith("audio/")
        )
        filename_ok = bool(
            file.filename and file.filename.lower().endswith(allowed_exts)
        )
        logger.info(f"Upload content_type={file.content_type} filename={file.filename}")
        if not content_type_ok and not filename_ok:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an audio file.",
            )

        # 파일 크기 체크 (최대 50MB)
        contents = await file.read()
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=400, detail="File too large. Maximum size is 50MB."
            )

        logger.info(f"Analyzing file: {file.filename}")

        # 1. 강제 엔진 지정이 없으면 환경 감지
        if force_engine:
            engine_type = force_engine.lower()
            detection_result = {
                "environment": engine_type,
                "confidence": 1.0,
                "reason": "사용자 지정",
            }
        else:
            detection_result = get_detector().detect_environment(contents)
            engine_type = detection_result["environment"]

        # 2. 적절한 엔진 선택 및 분석
        if engine_type == "studio" or detection_result.get("studio_score", 0.5) > 0.5:
            logger.info("Using Studio engine for high-quality analysis")
            result = get_studio_analyzer().analyze(contents)
            engine_name = "studio"
        else:
            logger.info("Using Lite engine for phone-optimized analysis")
            result = get_lite_analyzer().analyze(contents)
            engine_name = "lite"

        # 처리 시간
        processing_time = time.time() - start_time

        # 품질 게이트 체크
        quality = result["quality"]
        if quality["snr"] < 15:
            warning = "낮은 SNR 감지. 조용한 환경에서 재녹음을 권장합니다."
        elif quality["clipping_percent"] > 3:
            warning = "클리핑 감지. 마이크에서 조금 떨어져서 녹음해주세요."
        elif quality["silence_percent"] > 60:
            warning = "무음 구간이 너무 많습니다. 더 크게 녹음해주세요."
        else:
            warning = None

        # 신뢰도 기반 메시지
        confidence = result["confidence"]
        if confidence < 0.3:
            confidence_badge = "low"
            confidence_message = "녹음 품질이 낮아 정확도가 제한적입니다."
        elif confidence < 0.7:
            confidence_badge = "medium"
            confidence_message = "분석 신뢰도 보통"
        else:
            confidence_badge = "high"
            confidence_message = "높은 신뢰도"

        # 결과 저장 (Pro 분석용)
        analysis_results[analysis_id] = {
            "file_data": contents,
            "lite_result": result,
            "timestamp": datetime.now(),
        }

        # Pro 분석 백그라운드 실행 (옵션)
        # if background_tasks:
        #     background_tasks.add_task(analyze_with_pro, analysis_id, contents)

        # Studio 엔진 특별 정보 추가
        extra_info = {}
        if engine_name == "studio" and "features_summary" in result:
            fs = result["features_summary"]
            extra_info = {
                "hnr": fs.get("hnr", 0),
                "jitter": fs.get("jitter", 0),
                "shimmer": fs.get("shimmer", 0),
                "formants": {
                    "f1": fs.get("f1", 0),
                    "f2": fs.get("f2", 0),
                    "f3": fs.get("f3", 0),
                },
                "pitch_mean": fs.get("pitch_mean", 0),
            }

        # 점수 보정: -100 .. +100 범위로 클램프 및 소수 한 자리로 반올림
        def _clamp_scores(raw_scores: Dict) -> Dict:
            out = {}
            for k, v in raw_scores.items():
                try:
                    num = float(v)
                except Exception:
                    num = 0.0
                num = max(-100.0, min(100.0, num))
                out[k] = round(num, 1)
            return out

        normalized_scores = _clamp_scores(result.get("scores", {}))

        # YouTube 추천 비디오 가져오기 (정규화된 점수 사용)
        # Allow disabling YouTube lookups via DISABLE_YOUTUBE=1 in the environment.
        youtube_videos = []
        try:
            disable_youtube = os.getenv("DISABLE_YOUTUBE", "0").strip() in (
                "1",
                "true",
                "yes",
            )
            if not disable_youtube:
                youtube_videos = get_youtube_service().get_recommended_videos(
                    normalized_scores, max_results=6
                )
                logger.info(f"Retrieved {len(youtube_videos)} YouTube recommendations")
            else:
                logger.info("DISABLE_YOUTUBE is set; skipping YouTube recommendations")
        except Exception as e:
            logger.error(f"YouTube recommendation error: {str(e)}")
            youtube_videos = []

        # 응답
        response = {
            "status": "success",
            "analysis_id": analysis_id,
            "scores": normalized_scores,
            "confidence": confidence,
            "confidence_badge": confidence_badge,
            "confidence_message": confidence_message,
            "quality": quality,
            "engine": engine_name,
            "processing_time": round(processing_time, 2),
            "warning": warning,
            "detection": {
                "environment": detection_result.get("environment", "unknown"),
                "studio_score": detection_result.get("studio_score", 0.5),
                "reason": detection_result.get("reason", ""),
            },
            "extra_info": extra_info,
            "youtube_videos": youtube_videos,  # YouTube 추천 비디오 추가
            "mbti": generate_mbti_from_scores(normalized_scores),  # 하위 호환성
            "success": True,
        }

        logger.info(
            f"{engine_name.capitalize()} analysis complete in {processing_time:.2f}s. Scores: {result['scores']}"
        )
        return response

    except HTTPException:
        # let FastAPI handle HTTPExceptions (bad request, etc.) so client gets proper status code
        raise
    except Exception as e:
        # log full traceback for debugging
        logger.exception("Unhandled exception during analysis")

        # 실패 시 응답 (keep same shape but include error message)
        return {
            "status": "error",
            "analysis_id": analysis_id,
            "scores": {
                "brightness": 0.0,
                "thickness": 0.0,
                "loudness": 0.0,
                "clarity": 0.0,
            },
            "confidence": 0.0,
            "confidence_badge": "error",
            "quality": {
                "lufs": -30.0,
                "snr": 0.0,
                "clipping_percent": 0.0,
                "silence_percent": 100.0,
            },
            "engine": "auto",
            "error": str(e),
            "reason": "analysis_failed",
            "success": False,
        }


@app.post("/api/analyze/pro")
async def analyze_voice_pro(analysis_id: str):
    """
    Pro 엔진 정밀 분석 (< 3초)
    WavLM 임베딩 + 약한 지도학습
    """
    # TODO: Pro 엔진 구현 후 활성화
    return {
        "status": "not_implemented",
        "message": "Pro engine will be available soon",
        "analysis_id": analysis_id,
    }


@app.post("/api/feedback")
async def save_feedback(feedback: FeedbackData):
    """
    사용자 피드백 저장 (골드 라벨)
    Pro 엔진 학습에 사용
    """
    try:
        # 실제로는 DB에 저장
        logger.info(f"Feedback received for {feedback.analysis_id}: {feedback.dict()}")

        # 피드백 저장 로직
        # db.save_feedback(feedback)

        return {"status": "success", "message": "Feedback saved successfully"}

    except Exception as e:
        logger.error(f"Error saving feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": "vocal-analysis-api-v2",
        "version": "2.0.0",
        "engines": {"lite": "active", "studio": "active", "auto": "active"},
        "features": ["brightness", "thickness", "loudness", "clarity"],
    }


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Vocal Analysis API v2.0",
        "description": "폰 녹음 최적화 4축 보컬 분석",
        "axes": {
            "brightness": "음색 밝기 (-100 ~ +100)",
            "thickness": "음색 두께 (-100 ~ +100)",
            "loudness": "음압/소리 세기 (-100 ~ +100)",
            "clarity": "선명도/명료성 (-100 ~ +100)",
        },
        "endpoints": {
            "/api/analyze": "자동 엔진 선택 분석 (환경 감지)",
            "/api/analyze?force_engine=lite": "Lite 엔진 강제 사용 (폰 최적화)",
            "/api/analyze?force_engine=studio": "Studio 엔진 강제 사용 (고품질)",
            "/api/analyze/pro": "Pro 엔진 정밀 분석 (준비중)",
            "/api/feedback": "사용자 피드백 저장",
        },
        "docs": "/docs",
    }


def generate_mbti_from_scores(scores: Dict) -> Dict:
    """
    4축 점수를 MBTI 스타일로 변환 (하위 호환성)
    """
    brightness = scores["brightness"]
    thickness = scores["thickness"]
    loudness = scores["loudness"]
    clarity = scores["clarity"]

    # 타입 코드 생성
    type_code = ""
    type_code += "B" if brightness > 0 else "D"  # Bright vs Dark
    type_code += "T" if thickness > 0 else "L"  # Thick vs Light
    type_code += "S" if loudness > 0 else "W"  # Strong vs Weak
    type_code += "C" if clarity > 0 else "R"  # Clear vs Rough

    # 특성 생성
    characteristics = []
    pros = []
    cons = []

    # 밝기
    if abs(brightness) > 30:
        if brightness > 0:
            characteristics.append("밝고 경쾌한 음색")
            pros.append("활기찬 인상")
        else:
            characteristics.append("깊고 차분한 음색")
            pros.append("안정적인 느낌")

    # 두께
    if abs(thickness) > 30:
        if thickness > 0:
            characteristics.append("풍성하고 두꺼운 음색")
            pros.append("존재감이 강함")
        else:
            characteristics.append("가볍고 민첩한 음색")
            pros.append("고음 처리 유리")

    # 음압
    if abs(loudness) > 30:
        if loudness > 0:
            characteristics.append("파워풀한 음량")
            pros.append("무대 장악력")
        else:
            characteristics.append("섬세한 음량 컨트롤")
            pros.append("감성적 표현")

    # 선명도
    if abs(clarity) > 30:
        if clarity > 0:
            characteristics.append("또렷한 발음과 전달력")
            pros.append("가사 전달 우수")
            if clarity < -50:
                cons.append("발성 기법 개선 필요")
        else:
            characteristics.append("부드러운 발성")
            pros.append("편안한 느낌")

    if not characteristics:
        characteristics = ["균형잡힌 보컬 특성"]
    if not pros:
        pros = ["개성 있는 음색", "발전 가능성"]
    if not cons:
        cons = ["지속적인 연습 필요"]

    return {
        "type_code": type_code,
        "name": f"{type_code} 보컬 타입",
        "characteristics": characteristics[:3],
        "pros": pros[:4],
        "cons": cons[:3],
        "description": f"4축 분석 기반 {type_code} 보컬 특성",
    }


# 임시 클린업 (24시간 후 데이터 삭제)
async def cleanup_old_results():
    """오래된 분석 결과 삭제"""
    cutoff_time = datetime.now() - timedelta(hours=24)
    to_delete = []

    for analysis_id, data in analysis_results.items():
        if data["timestamp"] < cutoff_time:
            to_delete.append(analysis_id)

    for analysis_id in to_delete:
        del analysis_results[analysis_id]

    logger.info(f"Cleaned up {len(to_delete)} old results")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)  # Studio 엔진 API v2.0
