import { initializeApp } from 'firebase/app';
import { getAuth, signInWithPopup, GoogleAuthProvider, signOut } from 'firebase/auth';

// Firebase 설정 (songlab-v2)
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

// 카카오 로그인 (Popup 방식)
export const signInWithKakao = () => {
  return new Promise((resolve, reject) => {
    if (!window.Kakao || !window.Kakao.Auth) {
      reject(new Error('카카오 SDK가 로드되지 않았습니다'));
      return;
    }

    try {
      window.Kakao.Auth.login({
        success: function(authObj) {
          console.log('카카오 로그인 성공:', authObj);
          resolve(authObj);
        },
        fail: function(err) {
          console.error('카카오 로그인 실패:', err);
          reject(err);
        }
      });
    } catch (error) {
      console.error('카카오 로그인 오류:', error);
      reject(error);
    }
  });
};

// 로그아웃
export const logout = async () => {
  try {
    // Firebase 로그아웃
    await signOut(auth);
    
    // 카카오 로그아웃
    if (window.Kakao && window.Kakao.Auth) {
      window.Kakao.Auth.logout();
    }
  } catch (error) {
    console.error('로그아웃 오류:', error);
    throw error;
  }
};

// 카카오 초기화 (HTML에서 SDK 로드 후 호출)
export const initKakao = () => {
  if (window.Kakao && !window.Kakao.isInitialized()) {
    window.Kakao.init('2ae9be2d22fc1649379d85aca7b8cd4c'); // 카카오 JavaScript 키
  }
};