# 🏠 SongLab 새 프론트엔드 배포 가이드

## ✅ 완료된 작업
- **새로운 프론트엔드 완전 구축 완료**
  - `frontend/index.html`: 메인 홈페이지 (소셜로그인, 파일업로드, 광고시스템, 결과표시)
  - `frontend/style.css`: 모던 반응형 디자인 스타일
  - `frontend/script.js`: 완전한 API 연동 및 광고 워크플로우
  - `frontend/auth/kakao/callback.html`: 카카오 OAuth 콜백 페이지
  - `frontend/auth/google/callback.html`: 구글 OAuth 콜백 페이지

## 📋 배포 우선순위

### 1️⃣ **백엔드 서버 배포 및 설정**
```bash
# AWS 서버에 업로드
scp -r songlab_backend/ ubuntu@your-server:/home/ubuntu/

# 서버에서 실행
cd /home/ubuntu/songlab_backend
pip install -r requirements.txt
python main.py
```

### 2️⃣ **환경변수 설정 (.env 파일)**
```env
# JWT 토큰 암호화 키
JWT_SECRET_KEY=your-super-secret-jwt-key-12345

# 카카오 OAuth (https://developers.kakao.com)
KAKAO_CLIENT_ID=your-kakao-app-key
KAKAO_REDIRECT_URI=https://songlab.kr/auth/kakao/callback

# 구글 OAuth (https://console.cloud.google.com)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://songlab.kr/auth/google/callback

# Google AdSense
ADSENSE_CLIENT_ID=ca-pub-your-adsense-id
```

### 3️⃣ **새 프론트엔드 파일 업로드**

#### A. 기존 홈페이지 파일 백업 및 교체
```bash
# 기존 파일 백업
mv index.html index.html.backup
mv style.css style.css.backup  
mv script.js script.js.backup

# 새 파일 업로드
cp frontend/index.html ./
cp frontend/style.css ./
cp frontend/script.js ./

# OAuth 콜백 페이지 디렉토리 생성 및 업로드
mkdir -p auth/kakao auth/google
cp frontend/auth/kakao/callback.html auth/kakao/
cp frontend/auth/google/callback.html auth/google/
```

#### B. 완성된 API 연동 시스템 (이미 구현완료)
async function analyzeVoice(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // 1단계: 분석 시작
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'analysis_completed') {
            // 결과보기 버튼 표시
            showResultButton(result.session_id);
        }
        
    } catch (error) {
        console.error('분석 실패:', error);
        showError('분석 중 오류가 발생했습니다.');
    }
}

// 결과보기 버튼 이벤트
async function showAnalysisResult(sessionId) {
    try {
        // 2단계: 결과보기 (광고 포함)
        const response = await fetch(`/analyze/result/${sessionId}`);
        const data = await response.json();
        
        if (data.status === 'show_ad_first') {
            // 광고 표시
            displayAdvertisement(data.advertisement);
            
            // 5초 후 또는 광고 클릭 후 실제 결과 표시
            setTimeout(async () => {
                const finalResponse = await fetch(data.next_endpoint);
                const finalResult = await finalResponse.json();
                
                // 기존 결과 표시 함수 사용
                displayMBTIResult(finalResult.mbti);
            }, 5000);
        } else {
            // 광고 없으면 바로 표시
            displayMBTIResult(data.mbti);
        }
        
    } catch (error) {
        console.error('결과 조회 실패:', error);
        showError('결과를 불러올 수 없습니다.');
    }
}
```

#### B. 광고 표시 함수 추가
```javascript
// 광고 표시 함수
function displayAdvertisement(adData) {
    const adContainer = document.getElementById('ad-container') || createAdContainer();
    
    if (adData.type === 'adsense') {
        // Google AdSense 광고
        adContainer.innerHTML = adData.content;
        
        // AdSense 스크립트 실행
        if (window.adsbygoogle) {
            (adsbygoogle = window.adsbygoogle || []).push({});
        }
        
    } else {
        // 자체 광고
        adContainer.innerHTML = adData.content;
        
        // 클릭 이벤트 추가
        if (adData.click_url) {
            adContainer.addEventListener('click', () => {
                window.open(adData.click_url, '_blank');
            });
        }
    }
    
    // 광고 컨테이너 표시
    adContainer.style.display = 'block';
}

function createAdContainer() {
    const container = document.createElement('div');
    container.id = 'ad-container';
    container.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 10000;
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        max-width: 400px;
        width: 90%;
    `;
    
    document.body.appendChild(container);
    return container;
}

// 결과보기 버튼 생성
function showResultButton(sessionId) {
    const resultButton = document.createElement('button');
    resultButton.textContent = '🎤 결과보기';
    resultButton.className = 'result-button';
    resultButton.style.cssText = `
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 15px 30px;
        border-radius: 25px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        transition: all 0.3s ease;
    `;
    
    resultButton.onclick = () => showAnalysisResult(sessionId);
    
    // 기존 업로드 영역을 버튼으로 교체
    const uploadArea = document.querySelector('.upload-area, #upload-section');
    if (uploadArea) {
        uploadArea.innerHTML = '';
        uploadArea.appendChild(resultButton);
    }
}
```

### 4️⃣ **HTML 수정**

#### A. Google AdSense 코드 추가 (head 태그 내)
```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-your-adsense-id"></script>
```

#### B. 소셜 로그인 버튼 추가
```html
<!-- 헤더에 로그인 버튼 추가 -->
<div class="auth-buttons">
    <button id="kakao-login" class="login-btn kakao">
        <img src="/images/kakao-icon.png" alt="카카오"> 카카오 로그인
    </button>
    <button id="google-login" class="login-btn google">  
        <img src="/images/google-icon.png" alt="구글"> 구글 로그인
    </button>
</div>

<style>
.login-btn {
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    margin: 0 5px;
    cursor: pointer;
    font-weight: bold;
}
.login-btn.kakao { background: #FEE500; color: #000; }
.login-btn.google { background: #fff; border: 1px solid #ddd; }
</style>
```

#### C. 로그인 JavaScript 추가
```javascript
// 소셜 로그인 초기화
document.addEventListener('DOMContentLoaded', async () => {
    // 로그인 URL 가져오기
    const authResponse = await fetch('/auth/urls');
    const authUrls = await authResponse.json();
    
    // 카카오 로그인
    document.getElementById('kakao-login').onclick = () => {
        window.location.href = authUrls.kakao_login_url;
    };
    
    // 구글 로그인  
    document.getElementById('google-login').onclick = () => {
        window.location.href = authUrls.google_login_url;
    };
    
    // 현재 로그인 상태 확인
    checkLoginStatus();
});

async function checkLoginStatus() {
    const token = localStorage.getItem('songlab_token');
    if (token) {
        try {
            const response = await fetch('/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                const user = await response.json();
                showUserInfo(user);
            }
        } catch (error) {
            localStorage.removeItem('songlab_token');
        }
    }
}
```

### 5️⃣ **OAuth 콜백 페이지 생성**

#### A. 카카오 콜백 페이지 (/auth/kakao/callback)
```html
<!DOCTYPE html>
<html>
<head>
    <title>카카오 로그인 처리중...</title>
</head>
<body>
    <div style="text-align: center; margin-top: 100px;">
        <h2>🔄 로그인 처리 중...</h2>
        <p>잠시만 기다려주세요.</p>
    </div>
    
    <script>
    document.addEventListener('DOMContentLoaded', async () => {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        
        if (code) {
            try {
                const response = await fetch('/auth/kakao', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code })
                });
                
                const result = await response.json();
                
                if (result.access_token) {
                    localStorage.setItem('songlab_token', result.access_token);
                    window.location.href = '/';
                } else {
                    alert('로그인 실패: ' + result.detail);
                    window.location.href = '/';
                }
            } catch (error) {
                alert('로그인 처리 중 오류 발생');
                window.location.href = '/';
            }
        }
    });
    </script>
</body>
</html>
```

### 6️⃣ **CSS 스타일 추가**
```css
/* 광고 스타일 */
#ad-container {
    backdrop-filter: blur(5px);
    border: 2px solid #667eea;
}

/* 결과보기 버튼 호버 효과 */
.result-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

/* 로딩 애니메이션 */
.loading {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
```

## 🚀 배포 체크리스트

- [ ] 1. 백엔드 서버 AWS 배포  
- [ ] 2. .env 환경변수 설정
- [ ] 3. **새 프론트엔드 파일 업로드 (핵심!)**
  - [ ] 기존 index.html, style.css, script.js 백업
  - [ ] 새로운 frontend/ 파일들로 교체
  - [ ] OAuth 콜백 페이지 auth/ 디렉토리 생성
- [ ] 4. 카카오/구글 OAuth 앱 등록 및 콜백 URL 설정
  - [ ] 카카오: `https://yourdomain.com/auth/kakao/callback.html`
  - [ ] 구글: `https://yourdomain.com/auth/google/callback.html`
- [ ] 5. Google AdSense 계정 연동
- [ ] 6. HTTPS 인증서 적용 (OAuth 필수)
- [ ] 7. 테스트 및 최종 확인

## ✅ 이미 완료된 부분
- ✅ 프론트엔드 API 연동 코드 완성
- ✅ 소셜 로그인 UI 구현
- ✅ 광고 표시 시스템 구현  
- ✅ OAuth 콜백 페이지 생성

## 📞 지원이 필요한 부분

궁금한 점이나 막히는 부분이 있으면 언제든 말씀해주세요:
- OAuth 앱 등록 과정
- AdSense 연동 방법  
- 기존 코드와의 통합
- 서버 배포 관련
- 기타 기술적 문제