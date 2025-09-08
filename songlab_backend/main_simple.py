from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

# CORS 설정 (웹사이트에서 API 호출 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_voice(file: UploadFile = File(...)):
    # 점수 생성
    scores = {
        "brightness": random.randint(30, 80),
        "thickness": random.randint(30, 80),
        "clarity": random.randint(30, 80),
        "power": random.randint(30, 80)
    }
    
    # 점수별 유튜브 검색 키워드 매핑
    recommendations = []
    
    # 밝기 부족시 (50 이하)
    if scores["brightness"] < 50:
        recommendations.extend([
            "포먼트 조절 보컬 레슨",
            "공명 훈련 발성법",
            "톤 밝기 개선 방법"
        ])
    
    # 두께 부족시 (성구 전환 문제)
    if scores["thickness"] < 50:
        recommendations.extend([
            "성구 전환 연습법",
            "브릿지 훈련 보컬",
            "믹스 보이스 만들기"
        ])
    
    # 선명도 부족시
    if scores["clarity"] < 50:
        recommendations.extend([
            "성대 내전 발성법",
            "발음 명료 딕션 훈련",
            "발성 내전 연습"
        ])
    
    # 음압 부족시
    if scores["power"] < 50:
        recommendations.extend([
            "아포지오 호흡법",
            "호흡 근육 훈련",
            "호흡 조절 발성법"
        ])
    
    # 추천이 없으면 기본 추천
    if not recommendations:
        recommendations = ["보컬 기초 발성법", "음성 훈련 기본기"]
    
    # MBTI는 단순화
    mbti_types = ["ENFP", "ESFJ", "ENTJ", "INFJ"]
    selected_mbti = random.choice(mbti_types)
    
    result = {
        "mbti": {
            "typeCode": selected_mbti,
            "typeName": selected_mbti,
            "typeIcon": "🎤",
            "description": f"{selected_mbti} 보컬 스타일",
            "scores": scores,
            "recommendations": recommendations[:3]  # 최대 3개 추천
        },
        "success": True
    }
    return JSONResponse(content=result)