"""
Advanced Vocal Analysis API
4축 보컬 분석 시스템 - FastAPI 통합
"""

import logging
import os
from typing import Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from advanced_vocal_analyzer import AdvancedVocalAnalyzer  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency
    AdvancedVocalAnalyzer = None  # type: ignore
    _ADVANCED_ANALYZER_IMPORT_ERROR = exc
else:
    _ADVANCED_ANALYZER_IMPORT_ERROR = None

try:
    from advanced_vocal_analyzer_no_essentia import \
        AdvancedVocalAnalyzerNoEssentia  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency
    AdvancedVocalAnalyzerNoEssentia = None  # type: ignore
    _NO_ESSENTIA_ANALYZER_IMPORT_ERROR = exc
else:
    _NO_ESSENTIA_ANALYZER_IMPORT_ERROR = None

# Logging 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Advanced Vocal Analysis API",
    description="고급 4축 보컬 분석 시스템 (밝기, 두께, 성대내전, 음압)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 분석기 초기화 (환경 감안)
analyzer: Optional[object] = None
analyzer_backend: Optional[str] = None
analyzer_init_errors: Dict[str, str] = {}
_ANALYZER_BACKEND_ENV = os.getenv("ANALYZER_BACKEND", "auto").lower()


def _initialize_analyzer() -> Optional[object]:
    """환경에 맞춰 사용할 분석 엔진을 초기화합니다."""
    global analyzer_backend

    if _ANALYZER_BACKEND_ENV in {"advanced", "pro"}:
        backend_preference: List[str] = ["advanced"]
    elif _ANALYZER_BACKEND_ENV in {"no_essentia", "fallback"}:
        backend_preference = ["no_essentia"]
    else:
        backend_preference = ["advanced", "no_essentia"]

    for backend_candidate in backend_preference:
        if backend_candidate == "advanced":
            if AdvancedVocalAnalyzer is None:
                if _ADVANCED_ANALYZER_IMPORT_ERROR is not None:
                    analyzer_init_errors["advanced"] = repr(
                        _ADVANCED_ANALYZER_IMPORT_ERROR
                    )
                continue
            try:
                instance = AdvancedVocalAnalyzer()
                analyzer_backend = "advanced"
                logger.info("Loaded AdvancedVocalAnalyzer backend.")
                return instance
            except Exception as exc:  # noqa: BLE001
                analyzer_init_errors["advanced"] = repr(exc)
                logger.warning("Advanced analyzer init failed: %s", exc)
        elif backend_candidate == "no_essentia":
            if AdvancedVocalAnalyzerNoEssentia is None:
                if _NO_ESSENTIA_ANALYZER_IMPORT_ERROR is not None:
                    analyzer_init_errors["no_essentia"] = repr(
                        _NO_ESSENTIA_ANALYZER_IMPORT_ERROR
                    )
                continue
            try:
                instance = AdvancedVocalAnalyzerNoEssentia()
                analyzer_backend = "no_essentia"
                logger.info("Loaded AdvancedVocalAnalyzerNoEssentia backend.")
                return instance
            except Exception as exc:  # noqa: BLE001
                analyzer_init_errors["no_essentia"] = repr(exc)
                logger.warning("No-Essentia analyzer init failed: %s", exc)

    logger.error(
        "Unable to initialize analyzer backend. errors=%s", analyzer_init_errors
    )
    return None


def _get_analyzer() -> Optional[object]:
    """현재 사용 가능한 분석기를 반환합니다."""
    global analyzer

    if analyzer is None:
        analyzer = _initialize_analyzer()
    return analyzer


@app.post("/api/analyze")
async def analyze_voice(file: UploadFile = File(...)):
    """
    고급 4축 보컬 분석
    - brightness: 밝기 (-100 어두움 ~ +100 밝음)
    - thickness: 음색 두께 (-100 얇음 ~ +100 두꺼움)
    - adduction: 성대 내전 정도 (-100 불완전 ~ +100 완전)
    - spl: 음압/소리 세기 (-100 약함 ~ +100 강함)
    """
    try:
        # 파일 타입 검증
        if not file.content_type or not file.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an audio file.",
            )

        # 분석기 준비
        active_analyzer = _get_analyzer()
        if active_analyzer is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Analyzer backend is not available.",
                    "preferred_backend": _ANALYZER_BACKEND_ENV,
                    "backend": analyzer_backend,
                    "errors": dict(analyzer_init_errors),
                },
            )

        # 오디오 데이터 읽기
        audio_data = await file.read()
        logger.info(
            "Analyzing audio file '%s' with backend '%s'",
            file.filename,
            analyzer_backend,
        )

        # 4축 분석 수행
        scores = active_analyzer.analyze_audio(audio_data)

        # MBTI 스타일 결과 생성 (기존 호환성)
        mbti_result = generate_advanced_mbti_style(scores)

        result = {
            "status": "success",
            "scores": scores,
            "gender": scores.get("gender", "unknown"),
            "potential_high_note": scores.get("potential_high_note", "E5"),
            "mbti": mbti_result,
            "analysis_type": "advanced_4axis",
            "analyzer_backend": analyzer_backend,
            "success": True,
        }

        logger.info(
            "Analysis complete with backend '%s'. Scores: %s", analyzer_backend, scores
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Error analyzing voice with backend '%s'", analyzer_backend or "unknown"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to analyze voice.",
                "backend": analyzer_backend,
                "error": str(exc),
            },
        ) from exc


def generate_advanced_mbti_style(scores: dict) -> dict:
    """
    4축 점수를 기반으로 MBTI 스타일 결과 생성
    """
    brightness = scores["brightness"]
    thickness = scores["thickness"]
    adduction = scores["adduction"]
    spl = scores["spl"]

    # 타입 코드 결정 (기존 호환성 유지)
    type_code = ""
    type_code += "B" if brightness > 0 else "D"  # Bright vs Dark
    type_code += "T" if thickness > 0 else "L"  # Thick vs Light
    type_code += "C" if adduction > 0 else "R"  # Complete vs Rough
    type_code += "S" if spl > 0 else "W"  # Strong vs Weak

    # 동적 특성 생성
    characteristics = []
    pros = []
    cons = []

    # 밝기 분석
    if abs(brightness) > 30:
        if brightness > 0:
            characteristics.append("밝고 경쾌한 음색")
            pros.append("활발한 인상")
            if brightness > 70:
                cons.append("때로는 가벼워 보일 수 있음")
        else:
            characteristics.append("깊고 성숙한 음색")
            pros.append("진지한 느낌")
            if brightness < -70:
                cons.append("때로는 어둡게 느껴질 수 있음")

    # 두께 분석
    if abs(thickness) > 30:
        if thickness > 0:
            characteristics.append("풍성하고 두꺼운 음색")
            pros.append("임팩트가 강함")
            if thickness > 70:
                cons.append("고음역에서 부담스러울 수 있음")
        else:
            characteristics.append("섬세하고 가벼운 음색")
            pros.append("고음에 유리함")
            if thickness < -70:
                cons.append("파워가 부족해 보일 수 있음")

    # 성대 내전 분석 (핵심!)
    if abs(adduction) > 30:
        if adduction > 0:
            characteristics.append("깔끔하고 선명한 발성")
            pros.append("전달력이 뛰어남")
            if adduction > 80:
                pros.append("프로페셔널한 기법")
        else:
            characteristics.append("자연스럽고 편안한 발성")
            pros.append("친근한 느낌")
            if adduction < -50:
                cons.append("발성 기법 개선 필요")

    # 음압 분석
    if abs(spl) > 30:
        if spl > 0:
            characteristics.append("파워풀한 음량")
            pros.append("존재감이 강함")
            if spl > 70:
                pros.append("무대 장악력 우수")
        else:
            characteristics.append("부드러운 음량")
            pros.append("섬세한 표현")
            if spl < -50:
                cons.append("음량 보강이 필요할 수 있음")

    # 기본값 설정
    if not characteristics:
        characteristics = ["균형잡힌 보컬 특성"]
    if not pros:
        pros = ["개성 있는 음색", "독특한 매력"]
    if not cons:
        cons = ["더 많은 연습으로 발전 가능"]

    return {
        "type_code": type_code,
        "name": f"{type_code} 보컬 타입",
        "characteristics": characteristics[:3],
        "pros": pros[:4],
        "cons": cons[:3],
        "description": f"4축 분석 결과 - {type_code} 특성을 가진 보컬 타입",
        "technical_analysis": {
            "brightness_level": get_level_description(brightness, "밝기"),
            "thickness_level": get_level_description(thickness, "두께"),
            "adduction_level": get_level_description(adduction, "성대내전"),
            "spl_level": get_level_description(spl, "음압"),
        },
    }


def get_level_description(score: float, axis: str) -> str:
    """점수를 레벨 설명으로 변환"""
    abs_score = abs(score)

    if abs_score < 20:
        level = "보통"
    elif abs_score < 50:
        level = "중간"
    elif abs_score < 80:
        level = "높음"
    else:
        level = "매우 높음"

    direction = "+" if score > 0 else "-" if score < 0 else ""

    return f"{level} ({direction}{abs_score:.1f})"


@app.get("/api/health")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": "advanced-vocal-analysis-api",
        "version": "2.0.0",
        "features": ["brightness", "thickness", "adduction", "spl"],
    }


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Advanced Vocal Analysis API v2.0",
        "description": "고급 4축 보컬 분석 시스템",
        "axes": {
            "brightness": "음색 밝기 (-100 ~ +100)",
            "thickness": "음색 두께 (-100 ~ +100)",
            "adduction": "성대 내전 정도 (-100 ~ +100)",
            "spl": "음압/소리 세기 (-100 ~ +100)",
        },
        "docs": "/docs",
    }


@app.get("/api/compare")
async def compare_systems():
    """기존 시스템과 비교 정보"""
    return {
        "legacy_system": {
            "axes": ["brightness", "thickness", "clarity", "power"],
            "libraries": ["librosa", "tensorflow"],
        },
        "advanced_system": {
            "axes": ["brightness", "thickness", "adduction", "spl"],
            "libraries": ["praat-parselmouth", "essentia", "torchaudio", "pyloudnorm"],
            "improvements": [
                "성대 내전 정도 정밀 측정",
                "음성학적으로 검증된 분석",
                "GPU 가속 처리",
                "LUFS 기반 객관적 음압 측정",
            ],
        },
    }
