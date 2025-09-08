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

// 카카오 팝업 로그인
export const signInWithKakao = () => {
  return new Promise((resolve, reject) => {
    if (!window.Kakao || !window.Kakao.Auth) {
      reject(new Error('카카오 SDK가 로드되지 않았습니다'));
      return;
    }

    window.Kakao.Auth.login({
      success: function(response) {
        console.log('카카오 팝업 로그인 성공:', response);
        
        // 토큰을 변수에 저장
        kakaoAccessToken = response.access_token;
        
        // SDK에도 설정 시도
        try {
          window.Kakao.Auth.setAccessToken(response.access_token);
        } catch (e) {
          console.log('SDK 토큰 설정 실패, 변수 저장으로 대체');
        }
        
        resolve(response);
      },
      fail: function(error) {
        console.error('카카오 팝업 로그인 실패:', error);
        reject(error);
      }
    });
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
        window.Kakao.Auth.logout();
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