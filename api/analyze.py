from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import random
import tempfile
import os
from typing import Dict, Any

# FastAPI 앱 생성
app = FastAPI()

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze")
async def analyze_voice(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    음성 파일 분석 API
    """
    try:
        # 파일 크기 제한 (10MB)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="파일 크기가 너무 큽니다 (최대 10MB)")
        
        # 지원하는 파일 형식 확인
        allowed_types = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/m4a', 'audio/ogg']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다")
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 실제 분석 로직 (현재는 데모 데이터)
            scores = {
                "brightness": random.randint(30, 90),
                "thickness": random.randint(30, 90), 
                "clarity": random.randint(30, 90),
                "power": random.randint(30, 90)
            }
            
            # 가장 낮은 점수 찾기
            lowest_score = min(scores, key=scores.get)
            
            # 키워드 매핑
            keyword_map = {
                "brightness": ["포먼트 조절 보컬 레슨", "공명 훈련 발성법"],
                "thickness": ["성구 전환 연습법", "믹스 보이스 만들기"],
                "clarity": ["성대 내전 발성법", "발음 명료 딕션 훈련"],
                "power": ["아포지오 호흡법", "호흡 근육 훈련"]
            }
            
            keywords = keyword_map.get(lowest_score, ["보컬 기초 발성법"])
            
            # MBTI 타입 결정
            mbti_code = determine_mbti_type(scores)
            mbti_info = get_mbti_info(mbti_code)
            
            result = {
                "status": "success",
                "success": True,
                "mbti": {
                    "typeCode": mbti_code,
                    "typeName": mbti_info['name'],
                    "typeIcon": mbti_info['icon'],
                    "description": mbti_info['description'],
                    "scores": scores,
                    "youtubeKeywords": keywords
                }
            }
            
            return result
            
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "message": "SongLab API is running"}

def determine_mbti_type(scores: Dict[str, int]) -> str:
    """4축 점수로 MBTI 타입 결정"""
    code = ''
    code += 'B' if scores['brightness'] > 50 else 'D'  # Bright/Dark
    code += 'T' if scores['thickness'] > 50 else 'L'   # Thick/Light
    code += 'C' if scores['clarity'] > 50 else 'H'     # Clear/Hazy
    code += 'P' if scores['power'] > 50 else 'S'       # Powerful/Soft
    return code

def get_mbti_info(mbti_code: str) -> Dict[str, str]:
    """MBTI 타입별 상세 정보"""
    types = {
        'BTCP': {
            'name': '크리스털 디바',
            'icon': '💎',
            'description': '맑고 강렬한 고음역대의 소유자. 크리스털처럼 투명하면서도 파워풀한 음성으로 듣는 이를 사로잡습니다.'
        },
        'BTCS': {
            'name': '실버 벨',
            'icon': '🔔', 
            'description': '은방울 같은 청아한 음색의 소유자. 맑고 부드러우면서도 풍성한 하모닉스가 특징입니다.'
        },
        'BTHP': {
            'name': '파워 소프라노',
            'icon': '⚡',
            'description': '강력한 고음 발성의 소유자. 오페라 가수 같은 웅장하고 드라마틱한 음성이 특징입니다.'
        },
        'BTHS': {
            'name': '엔젤 보이스', 
            'icon': '👼',
            'description': '천사의 목소리. 부드럽고 따뜻하면서도 신비로운 매력을 지닌 음성입니다.'
        },
        'BLCP': {
            'name': '레이저 보컬',
            'icon': '🔦',
            'description': '정확하고 예리한 음성의 소유자. 레이저처럼 직진하는 명확한 발성이 특징입니다.'
        },
        'BLCS': {
            'name': '클리어 톤',
            'icon': '✨',
            'description': '맑고 투명한 음색의 소유자. 물방울처럼 깨끗하고 순수한 음성이 매력적입니다.'
        },
        'BLHP': {
            'name': '하이 텐션',
            'icon': '🎺',
            'description': '에너지 넘치는 고음역의 소유자. 밝고 활기찬 음성으로 분위기를 끌어올립니다.'
        },
        'BLHS': {
            'name': '스위트 멜로디',
            'icon': '🍯',
            'description': '꿀같이 달콤한 음색의 소유자. 부드럽고 감미로운 음성으로 마음을 따뜻하게 합니다.'
        },
        'DTCP': {
            'name': '메탈 보이스',
            'icon': '🤘',
            'description': '강철 같은 음성의 소유자. 묵직하고 강렬한 저음으로 강한 인상을 남깁니다.'
        },
        'DTCS': {
            'name': '다크 나이트',
            'icon': '🌙',
            'description': '어둠의 기사 같은 신비로운 음성. 깊고 풍부한 저음이 매혹적입니다.'
        },
        'DTHP': {
            'name': '썬더 보컬',
            'icon': '⚡',
            'description': '천둥 같은 폭발적인 음성의 소유자. 강력한 저음으로 압도적인 존재감을 보입니다.'
        },
        'DTHS': {
            'name': '벨벳 보이스',
            'icon': '🎭',
            'description': '벨벳처럼 부드러운 음성의 소유자. 깊고 따뜻한 중저음이 감성적입니다.'
        },
        'DLCP': {
            'name': '샤프 슈터',
            'icon': '🎯',
            'description': '정확한 음정의 저음 전문가. 날카롭고 명확한 저음 발성이 특징입니다.'
        },
        'DLCS': {
            'name': '미스틱 보이스',
            'icon': '🔮',
            'description': '신비로운 음색의 소유자. 몽환적이면서도 깊이 있는 음성이 매력적입니다.'
        },
        'DLHP': {
            'name': '파워 레인저',
            'icon': '💪',
            'description': '강력한 중저음의 소유자. 파워레인저처럼 힘있고 안정감 있는 음성입니다.'
        },
        'DLHS': {
            'name': '허스키 보이스',
            'icon': '🐺',
            'description': '매력적인 허스키톤의 소유자. 거칠면서도 부드러운 독특한 음색이 인상적입니다.'
        }
    }
    
    return types.get(mbti_code, {
        'name': '미분류 보이스',
        'icon': '❓',
        'description': '고유한 특성을 가진 음성입니다.'
    })

# Vercel 핸들러
from mangum import Mangum

handler = Mangum(app)
