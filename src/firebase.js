import { initializeApp } from 'firebase/app';
import { getAuth, signInWithPopup, GoogleAuthProvider, signOut } from 'firebase/auth';

// Firebase 설정
const firebaseConfig = {
  apiKey: "AIzaSyC7Igb5sDzPeSU19A6b5xazhnj4WufFuG8",
  authDomain: "songlab-v2.firebaseapp.com",
  projectId: "songlab-v2",
  storageBucket: "songlab-v2.firebasestorage.app",
  messagingSenderId: "250128010188",
  appId: "1:250128010188:web:62d0d11aa90501db022b69"
};

// Firebase 초기화
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// 카카오 토큰 저장 변수
let kakaoAccessToken = null;
let kakaoUserInfo = null;

// Google 로그인
const googleProvider = new GoogleAuthProvider();
export const signInWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    return result.user;
  } catch (error) {
    console.error('Google 로그인 오류:', error);
    throw error;
  }
};

// 카카오 초기화
export const initializeKakao = () => {
  if (window.Kakao && !window.Kakao.isInitialized()) {
    window.Kakao.init('2ae9be2d22fc1649379d85aca7b8cd4c');
    console.log('카카오 초기화 완료');
  }
};

// 카카오 로그인 상태 확인
export const getKakaoLoginStatus = () => {
  try {
    // 저장된 토큰 확인
    if (kakaoAccessToken) {
      return true;
    }
    
    // SDK 토큰도 확인
    if (window.Kakao && window.Kakao.Auth) {
      const sdkToken = window.Kakao.Auth.getAccessToken();
      if (sdkToken) {
        kakaoAccessToken = sdkToken;
        return true;
      }
    }
    
    return false;
  } catch (error) {
    console.error('카카오 상태 확인 오류:', error);
    return false;
  }
};

// 강제 상태 업데이트를 위한 콜백
let statusUpdateCallback = null;
export const setKakaoStatusUpdateCallback = (callback) => {
  statusUpdateCallback = callback;
};

// 카카오 로그인
export const signInWithKakao = () => {
  return new Promise((resolve, reject) => {
    if (!window.Kakao || !window.Kakao.Auth) {
      reject(new Error('카카오 SDK가 로드되지 않았습니다'));
      return;
    }

    // 사용 가능한 함수들 확인
    const authMethods = Object.keys(window.Kakao.Auth);
    console.log('사용 가능한 카카오 Auth 메소드:', authMethods);

    // 방법 1: login 시도
    if (typeof window.Kakao.Auth.login === 'function') {
      console.log('login 메소드 사용');
      window.Kakao.Auth.login({
        success: function(response) {
          console.log('카카오 login 성공:', response);
          kakaoAccessToken = response.access_token;
          kakaoUserInfo = response;
          
          // 상태 업데이트 콜백 호출
          if (statusUpdateCallback) {
            statusUpdateCallback();
          }
          
          resolve(response);
        },
        fail: function(error) {
          console.error('카카오 login 실패:', error);
          reject(error);
        }
      });
      return;
    }

    // 방법 2: loginForm 시도
    if (typeof window.Kakao.Auth.loginForm === 'function') {
      console.log('loginForm 메소드 사용');
      window.Kakao.Auth.loginForm({
        success: function(response) {
          console.log('카카오 loginForm 성공:', response);
          kakaoAccessToken = response.access_token;
          kakaoUserInfo = response;
          
          if (statusUpdateCallback) {
            statusUpdateCallback();
          }
          
          resolve(response);
        },
        fail: function(error) {
          console.error('카카오 loginForm 실패:', error);
          reject(error);
        }
      });
      return;
    }

    // 방법 3: createLoginButton 시도
    if (typeof window.Kakao.Auth.createLoginButton === 'function') {
      console.log('createLoginButton 메소드 사용');
      
      // 임시 버튼 생성
      const tempButton = document.createElement('div');
      tempButton.id = 'kakao-login-temp';
      tempButton.style.display = 'none';
      document.body.appendChild(tempButton);
      
      window.Kakao.Auth.createLoginButton({
        container: '#kakao-login-temp',
        success: function(response) {
          console.log('카카오 createLoginButton 성공:', response);
          kakaoAccessToken = response.access_token;
          kakaoUserInfo = response;
          
          // 임시 버튼 제거
          document.body.removeChild(tempButton);
          
          if (statusUpdateCallback) {
            statusUpdateCallback();
          }
          
          resolve(response);
        },
        fail: function(error) {
          console.error('카카오 createLoginButton 실패:', error);
          document.body.removeChild(tempButton);
          reject(error);
        }
      });
      
      // 버튼 자동 클릭
      setTimeout(() => {
        const loginBtn = tempButton.querySelector('a');
        if (loginBtn) {
          loginBtn.click();
        }
      }, 100);
      return;
    }

    // 방법 4: authorize 시도 (리다이렉트 방식)
    if (typeof window.Kakao.Auth.authorize === 'function') {
      console.log('authorize 메소드 사용 (리다이렉트)');
      window.Kakao.Auth.authorize({
        redirectUri: window.location.origin
      });
      
      // 리다이렉트이므로 resolve 호출
      resolve({ method: 'authorize' });
      return;
    }

    // 모든 방법 실패
    reject(new Error('사용 가능한 카카오 로그인 메소드가 없습니다: ' + authMethods.join(', ')));
  });
};

// 로그아웃
export const logout = async () => {
  try {
    // Firebase 로그아웃
    await signOut(auth);
    
    // 카카오 로그아웃 (에러 무시)
    if (kakaoAccessToken || getKakaoLoginStatus()) {
      try {
        if (window.Kakao && window.Kakao.Auth && typeof window.Kakao.Auth.logout === 'function') {
          window.Kakao.Auth.logout(() => {
            console.log('카카오 로그아웃 완료');
          });
        }
      } catch (e) {
        // 401 등의 에러는 무시 (이미 로그아웃된 상태)
        console.log('카카오 로그아웃 에러 무시:', e.message);
      }
    }
    
    // 저장된 데이터 삭제
    kakaoAccessToken = null;
    kakaoUserInfo = null;
    
    // 상태 업데이트 콜백 호출
    if (statusUpdateCallback) {
      statusUpdateCallback();
    }
    
    console.log('로그아웃 완료');
    
  } catch (error) {
    console.error('로그아웃 오류:', error);
    // 에러가 있어도 토큰은 삭제
    kakaoAccessToken = null;
    kakaoUserInfo = null;
    
    if (statusUpdateCallback) {
      statusUpdateCallback();
    }
  }
};