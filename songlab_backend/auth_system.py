"""
SongLab 소셜 로그인 시스템
카카오, 구글 OAuth2 인증 및 사용자 관리
"""

import os
import jwt
import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict
import sqlite3
import hashlib

# JWT 설정
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-this")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7일

security = HTTPBearer()

class AuthSystem:
    def __init__(self, db_path="songlab_data.db"):
        self.db_path = db_path
        self.init_auth_tables()
        
        # OAuth 설정
        self.kakao_client_id = os.getenv("KAKAO_CLIENT_ID")
        self.kakao_redirect_uri = os.getenv("KAKAO_REDIRECT_URI")
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    
    def init_auth_tables(self):
        """인증 관련 테이블 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 사용자 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            social_id TEXT UNIQUE NOT NULL,
            provider TEXT NOT NULL,
            email TEXT,
            name TEXT,
            profile_image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_premium BOOLEAN DEFAULT FALSE,
            subscription_expires TIMESTAMP
        )
        ''')
        
        # 사용자 분석 기록 연결 테이블 수정
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            analysis_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (analysis_id) REFERENCES user_analyses (id)
        )
        ''')
        
        # 인덱스
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_social_id ON users(social_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_provider ON users(provider)')
        
        conn.commit()
        conn.close()
    
    def create_access_token(self, user_data: Dict) -> str:
        """JWT 토큰 생성"""
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "user_id": user_data["id"],
            "social_id": user_data["social_id"],
            "provider": user_data["provider"],
            "exp": expire
        }
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Dict:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    
    async def kakao_login(self, code: str) -> Dict:
        """카카오 로그인 처리"""
        try:
            # 1. 액세스 토큰 요청
            token_url = "https://kauth.kakao.com/oauth/token"
            token_data = {
                "grant_type": "authorization_code",
                "client_id": self.kakao_client_id,
                "redirect_uri": self.kakao_redirect_uri,
                "code": code
            }
            
            async with httpx.AsyncClient() as client:
                token_response = await client.post(token_url, data=token_data)
                token_info = token_response.json()
                
                if "access_token" not in token_info:
                    raise HTTPException(status_code=400, detail="카카오 토큰 획득 실패")
                
                # 2. 사용자 정보 요청
                user_url = "https://kapi.kakao.com/v2/user/me"
                headers = {"Authorization": f"Bearer {token_info['access_token']}"}
                
                user_response = await client.get(user_url, headers=headers)
                user_info = user_response.json()
                
                # 3. 사용자 생성/업데이트
                user_data = {
                    "social_id": str(user_info["id"]),
                    "provider": "kakao",
                    "email": user_info.get("kakao_account", {}).get("email"),
                    "name": user_info.get("kakao_account", {}).get("profile", {}).get("nickname"),
                    "profile_image": user_info.get("kakao_account", {}).get("profile", {}).get("profile_image_url")
                }
                
                user = self.create_or_update_user(user_data)
                access_token = self.create_access_token(user)
                
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": user
                }
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"카카오 로그인 실패: {str(e)}")
    
    async def google_login(self, code: str) -> Dict:
        """구글 로그인 처리"""
        try:
            # 1. 액세스 토큰 요청
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "client_id": self.google_client_id,
                "client_secret": self.google_client_secret,
                "redirect_uri": self.google_redirect_uri,
                "grant_type": "authorization_code",
                "code": code
            }
            
            async with httpx.AsyncClient() as client:
                token_response = await client.post(token_url, data=token_data)
                token_info = token_response.json()
                
                if "access_token" not in token_info:
                    raise HTTPException(status_code=400, detail="구글 토큰 획득 실패")
                
                # 2. 사용자 정보 요청
                user_url = "https://www.googleapis.com/oauth2/v2/userinfo"
                headers = {"Authorization": f"Bearer {token_info['access_token']}"}
                
                user_response = await client.get(user_url, headers=headers)
                user_info = user_response.json()
                
                # 3. 사용자 생성/업데이트
                user_data = {
                    "social_id": user_info["id"],
                    "provider": "google",
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "profile_image": user_info.get("picture")
                }
                
                user = self.create_or_update_user(user_data)
                access_token = self.create_access_token(user)
                
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": user
                }
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"구글 로그인 실패: {str(e)}")
    
    def create_or_update_user(self, user_data: Dict) -> Dict:
        """사용자 생성 또는 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 기존 사용자 확인
        cursor.execute('''
        SELECT * FROM users WHERE social_id = ? AND provider = ?
        ''', (user_data["social_id"], user_data["provider"]))
        
        existing_user = cursor.fetchone()
        
        if existing_user:
            # 기존 사용자 업데이트
            cursor.execute('''
            UPDATE users SET 
                email = ?, name = ?, profile_image = ?, last_login = CURRENT_TIMESTAMP
            WHERE social_id = ? AND provider = ?
            ''', (
                user_data["email"], user_data["name"], user_data["profile_image"],
                user_data["social_id"], user_data["provider"]
            ))
            user_id = existing_user[0]
        else:
            # 새 사용자 생성
            cursor.execute('''
            INSERT INTO users (social_id, provider, email, name, profile_image, last_login)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_data["social_id"], user_data["provider"], 
                user_data["email"], user_data["name"], user_data["profile_image"]
            ))
            user_id = cursor.lastrowid
        
        # 사용자 정보 반환
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        columns = ['id', 'social_id', 'provider', 'email', 'name', 'profile_image', 
                  'created_at', 'last_login', 'is_premium', 'subscription_expires']
        return dict(zip(columns, user_row))
    
    def get_user_by_token(self, token: str) -> Dict:
        """토큰으로 사용자 정보 조회"""
        payload = self.verify_token(token)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (payload["user_id"],))
        user_row = cursor.fetchone()
        conn.close()
        
        if not user_row:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        columns = ['id', 'social_id', 'provider', 'email', 'name', 'profile_image',
                  'created_at', 'last_login', 'is_premium', 'subscription_expires']
        return dict(zip(columns, user_row))


# 의존성 함수
auth_system = AuthSystem()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict]:
    """현재 로그인된 사용자 정보 반환"""
    try:
        return auth_system.get_user_by_token(credentials.credentials)
    except HTTPException:
        return None

async def get_current_user_required(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """로그인 필수인 경우 사용"""
    user = await get_current_user(credentials)
    if not user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    return user


# OAuth URL 생성 함수
def get_kakao_auth_url():
    """카카오 로그인 URL 생성"""
    client_id = os.getenv("KAKAO_CLIENT_ID")
    redirect_uri = os.getenv("KAKAO_REDIRECT_URI")
    
    return f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"

def get_google_auth_url():
    """구글 로그인 URL 생성"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    
    return f"https://accounts.google.com/oauth/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&scope=openid%20email%20profile&response_type=code"


if __name__ == "__main__":
    # 테스트
    auth = AuthSystem()
    print("✅ 인증 시스템 초기화 완료")
    print(f"📱 카카오 로그인 URL: {get_kakao_auth_url()}")
    print(f"🔍 구글 로그인 URL: {get_google_auth_url()}")