from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from voice_analyzer_original import VoiceAnalyzer
from youtube_service import YouTubeService
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
analyzer = VoiceAnalyzer()
youtube_service = YouTubeService()

@app.post("/api/analyze")
async def analyze_voice(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")
        
        # Read audio file
        audio_data = await file.read()
        
        # Analyze audio
        logger.info(f"Analyzing audio file: {file.filename}")
        scores = analyzer.analyze_audio(audio_data)
        
        # Generate MBTI-style result with high note potential
        mbti_result = analyzer.generate_mbti_style(scores)
        
        # Add high note potential if available
        if 'potential_high_note' in scores:
            mbti_result['potentialNote'] = scores['potential_high_note']
            logger.info(f"High note potential: {scores['potential_high_note']}")
        else:
            logger.warning("No potential_high_note found in scores")
        
        # Get YouTube recommendations based on keywords
        youtube_videos = []
        if mbti_result.get('youtubeKeywords'):
            # 각 키워드로 2개씩 검색해서 총 6개
            for keyword in mbti_result['youtubeKeywords'][:3]:  # 3개 키워드 사용
                videos = youtube_service.search_videos(keyword, max_results=2)
                youtube_videos.extend(videos)
        
        result = {
            "status": "success",
            "mbti": mbti_result,
            "youtubeVideos": youtube_videos[:6],  # 최대 6개 동영상
            "success": True
        }
        
        logger.info(f"Analysis complete. Scores: {scores}")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing voice: {str(e)}")
        # Return demo result if analysis fails
        import random
        demo_scores = {
            "brightness": random.randint(-50, 50),
            "thickness": random.randint(-50, 50), 
            "clarity": random.randint(-50, 50),
            "power": random.randint(-50, 50)
        }
        
        demo_mbti = analyzer.generate_mbti_style(demo_scores)
        
        return {
            "status": "demo",
            "mbti": demo_mbti,
            "success": True,
            "isDemo": True,
            "error": str(e)
        }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "voice-analysis-api"}

@app.get("/")
async def root():
    return {"message": "Voice Analysis API is running"}