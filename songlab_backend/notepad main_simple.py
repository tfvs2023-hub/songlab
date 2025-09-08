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
    # 간단한 더미 분석 결과
    result = {
        "mbti": {
            "typeCode": "BTCP",
            "typeName": "크리스털 디바",
            "typeIcon": "💎",
            "description": "간단한 테스트 분석 결과입니다",
            "scores": {
                "brightness": random.randint(30, 80),
                "thickness": random.randint(30, 80),
                "clarity": random.randint(30, 80),
                "power": random.randint(30, 80)
            }
        },
        "success": True
    }
    return JSONResponse(content=result)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SongLab Simple API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)