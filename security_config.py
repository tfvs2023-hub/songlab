"""
보안 설정 - 프로덕션 배포 전 필수 적용
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi import Request, HTTPException
from typing import List
import time
import collections
import os

# Rate Limiting 설정
class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = collections.defaultdict(list)
    
    async def check_rate_limit(self, request: Request):
        client_ip = request.client.host
        now = time.time()
        
        # 오래된 요청 제거
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > now - self.window_seconds
        ]
        
        # 요청 수 확인
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Too many requests")
        
        self.requests[client_ip].append(now)

# CORS 설정 (프로덕션용)
def get_cors_origins() -> List[str]:
    """
    프로덕션에서는 특정 도메인만 허용
    """
    if os.getenv("ENVIRONMENT") == "production":
        return [
            "https://yourdomain.com",
            "https://www.yourdomain.com",
            # 실제 도메인으로 변경
        ]
    else:
        # 개발 환경
        return ["http://localhost:5173", "http://localhost:4173"]

# API 키 검증
def verify_api_key(api_key: str) -> bool:
    """
    API 키 검증 (프로덕션에서 사용)
    """
    valid_api_key = os.getenv("API_SECRET_KEY")
    if not valid_api_key:
        return True  # 개발 환경에서는 통과
    return api_key == valid_api_key

# 파일 크기 제한
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 허용된 파일 타입
ALLOWED_AUDIO_TYPES = [
    'audio/wav',
    'audio/mpeg',
    'audio/mp3',
    'audio/webm',
    'audio/ogg',
    'audio/m4a',
    'audio/x-m4a'
]