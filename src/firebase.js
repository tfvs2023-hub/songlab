import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithRedirect, getRedirectResult, signOut } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyC7Igb5sDzPeSU19A6b5xazhnj4WufFuG8",
  authDomain: "songlab-3f884.firebaseapp.com",
  projectId: "songlab-3f884",
  storageBucket: "songlab-3f884.firebasestorage.app",
  messagingSenderId: "268083149803",
  appId: "1:268083149803:web:2b91e785379b8cd933f7ae"
};


// Firebase 초기화
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

// 구글 로그인 함수
export const signInWithGoogle = () => {
  return signInWithRedirect(auth, googleProvider);
};

// 리다이렉트 결과 확인 함수
export const handleRedirectResult = () => {
  return getRedirectResult(auth);
};

// 로그아웃 함수
export const logout = () => {
  return signOut(auth);
};

export { auth };