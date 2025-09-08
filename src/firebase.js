// firebase.js - 완전히 새로운 접근
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

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

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

// 카카오 초기화 및 로그인 - 통합된 접근
export const initializeKakao = () => {
  if (window.Kakao && !window.Kakao.isInitialized()) {
    window.Kakao.init('2ae9be2d22fc1649379d85aca7b8cd4c');
    console.log('카카오 초기화 완료');
  }
};

// 카카오 로그인 상태 확인 (더 단순하게)
export const getKakaoLoginStatus = () => {
  try {
    if (!window.Kakao || !window.Kakao.Auth) {
      return false;
    }
    
    const accessToken = window.Kakao.Auth.getAccessToken();
    console.log('카카오 토큰:', accessToken);
    return !!accessToken;
  } catch (error) {
    console.error('카카오 상태 확인 오류:', error);
    return false;
  }
};

// 카카오 로그인 실행
export const signInWithKakao = () => {
  if (!window.Kakao?.Auth) {
    throw new Error('카카오 SDK가 로드되지 않았습니다');
  }
  
  // 현재 URL을 저장하여 로그인 후 돌아올 위치 지정
  const redirectUri = window.location.origin + window.location.pathname;
  
  window.Kakao.Auth.authorize({
    redirectUri: redirectUri
  });
};

// 로그아웃
export const logout = async () => {
  try {
    // Firebase 로그아웃
    await signOut(auth);
    
    // 카카오 로그아웃
    if (window.Kakao?.Auth && getKakaoLoginStatus()) {
      window.Kakao.Auth.logout();
    }
  } catch (error) {
    console.error('로그아웃 오류:', error);
    throw error;
  }
};