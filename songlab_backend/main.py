from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://www.songlab.kr", 
        "https://songlab.kr",
        "https://songlab-git-main-riseones-projects-4944954f.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_voice(file: UploadFile = File(...)):
    scores = {
        "brightness": random.randint(30, 90),
        "thickness": random.randint(30, 90), 
        "clarity": random.randint(30, 90),
        "power": random.randint(30, 90)
    }
    
    # 가장 낮은 점수 하나만 찾아서 매핑
    lowest_score = min(scores, key=scores.get)
    
    keyword_map = {
        "brightness": ["포먼트 조절 보컬 레슨", "공명 훈련 발성법"],
        "thickness": ["성구 전환 연습법", "믹스 보이스 만들기"],
        "clarity": ["성대 내전 발성법", "발음 명료 딕션 훈련"],
        "power": ["아포지오 호흡법", "호흡 근육 훈련"]
    }
    
    keywords = keyword_map.get(lowest_score, ["보컬 기초 발성법"])
    
    result = {
        "status": "success",
        "mbti": {
            "typeCode": "ENFP",
            "typeName": "ENFP",
            "typeIcon": "🎤", 
            "description": "ENFP 보컬 스타일",
            "scores": scores,
            "youtubeKeywords": keywords
        },
        "success": True
    }
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)