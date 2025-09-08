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
      console.log('저장된 카카오 토큰:', kakaoAccessToken.substring(0, 10) + '...');
      return true;
    }
    
    // SDK 토큰도 확인
    if (window.Kakao && window.Kakao.Auth) {
      const sdkToken = window.Kakao.Auth.getAccessToken();
      if (sdkToken) {
        console.log('SDK 카카오 토큰:', sdkToken.substring(0, 10) + '...');
        kakaoAccessToken = sdkToken; // 동기화
        return true;
      }
    }
    
    console.log('카카오 토큰: null');
    return false;
  } catch (error) {
    console.error('카카오 상태 확인 오류:', error);
    return false;
  }
};

// 카카오 로그인 - 여러 방식 시도
export const signInWithKakao = () => {
  return new Promise((resolve, reject) => {
    if (!window.Kakao || !window.Kakao.Auth) {
      reject(new Error('카카오 SDK가 로드되지 않았습니다'));
      return;
    }

    // 사용 가능한 함수들 확인
    console.log('사용 가능한 카카오 Auth 함수들:', Object.keys(window.Kakao.Auth));

    // 방법 1: login 시도
    if (typeof window.Kakao.Auth.login === 'function') {
      window.Kakao.Auth.login({
        success: function(response) {
          console.log('카카오 login 성공:', response);
          kakaoAccessToken = response.access_token;
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
      window.Kakao.Auth.loginForm({
        success: function(response) {
          console.log('카카오 loginForm 성공:', response);
          kakaoAccessToken = response.access_token;
          resolve(response);
        },
        fail: function(error) {
          console.error('카카오 loginForm 실패:', error);
          reject(error);
        }
      });
      return;
    }

    // 방법 3: authorize 시도 (리다이렉트 방식)
    if (typeof window.Kakao.Auth.authorize === 'function') {
      console.log('authorize 방식 사용');
      window.Kakao.Auth.authorize({
        redirectUri: window.location.origin
      });
      resolve();
      return;
    }

    // 모든 방법 실패
    reject(new Error('사용 가능한 카카오 로그인 함수가 없습니다'));
  });
};

// 로그아웃
export const logout = async () => {
  try {
    // Firebase 로그아웃
    await signOut(auth);
    
    // 카카오 로그아웃
    if (window.Kakao && window.Kakao.Auth && getKakaoLoginStatus()) {
      try {
        if (typeof window.Kakao.Auth.logout === 'function') {
          window.Kakao.Auth.logout();
        }
      } catch (e) {
        console.log('카카오 SDK 로그아웃 실패');
      }
      // 저장된 토큰도 삭제
      kakaoAccessToken = null;
    }
  } catch (error) {
    console.error('로그아웃 오류:', error);
    throw error;
  }
};