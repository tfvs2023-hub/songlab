import React, { useState, useRef, useEffect } from 'react';
import { Mic, Upload, Youtube, Sparkles, Volume2, AlertCircle } from 'lucide-react';
import GoogleAd from './components/GoogleAd';
import { useAuthState } from 'react-firebase-hooks/auth';
import { 
  auth, 
  signInWithGoogle, 
  signInWithKakao, 
  initializeKakao, 
  getKakaoLoginStatus,
  setKakaoStatusUpdateCallback,
  logout 
} from './firebase';

const VocalAnalysisPlatform = () => {
  const [currentStep, setCurrentStep] = useState('landing');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioFile, setAudioFile] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [adWatched, setAdWatched] = useState(false);
  const [adCountdown, setAdCountdown] = useState(15);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [forceUpdate, setForceUpdate] = useState(0);

  // API URL configuration
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const [backendStatus, setBackendStatus] = useState('checking');
  
  const [firebaseUser] = useAuthState(auth);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  const isLoggedIn = () => {
    return !!firebaseUser || getKakaoLoginStatus();
  };

  const forceStatusUpdate = () => {
    setForceUpdate(prev => prev + 1);
  };

  // Check backend health
  const checkBackendHealth = async () => {
    try {
      const response = await fetch(`${API_URL}/api/health`);
      if (response.ok) {
        setBackendStatus('connected');
      } else {
        setBackendStatus('error');
      }
    } catch (error) {
      setBackendStatus('disconnected');
    }
  };

  useEffect(() => {
    initializeKakao();
    setKakaoStatusUpdateCallback(forceStatusUpdate);
    checkBackendHealth();
  }, []);

  useEffect(() => {
    const loginStatus = isLoggedIn();
    console.log('로그인 상태 체크:', {
      firebase: !!firebaseUser,
      kakao: getKakaoLoginStatus(),
      loggedIn: loginStatus,
      currentStep,
      forceUpdate
    });

    if (loginStatus && (currentStep === 'landing' || currentStep === 'login')) {
      console.log('로그인됨 - record 페이지로 이동');
      setCurrentStep('record');
    }
  }, [firebaseUser, currentStep, forceUpdate]);

  const handleLoginClick = () => {
    if (isLoggedIn()) {
      setCurrentStep('record');
    } else {
      setCurrentStep('login');
    }
  };

  const handleGoogleLogin = async () => {
    try {
      await signInWithGoogle();
      console.log('구글 로그인 완료');
    } catch (error) {
      alert('구글 로그인 실패: ' + error.message);
    }
  };

  const handleKakaoLogin = async () => {
    try {
      await signInWithKakao();
      console.log('카카오 로그인 완료');
    
      // 즉시 상태 체크하여 페이지 이동
      if (getKakaoLoginStatus()) {
        console.log('카카오 토큰 확인됨, 즉시 이동');
        setCurrentStep('record');
      } else {
        // 토큰 확인이 안되면 강제 업데이트 후 재시도
        forceStatusUpdate();
        setTimeout(() => {
          if (getKakaoLoginStatus()) {
            console.log('재시도로 토큰 확인됨, 이동');
            setCurrentStep('record');
          }
        }, 100);
      }
    
    } catch (error) {
      alert('카카오 로그인 실패: ' + error.message);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      setCurrentStep('landing');
      setAudioFile(null);
      setAnalysisResults(null);
      setAdWatched(false);
      setAdCountdown(15);
    } catch (error) {
      console.error('로그아웃 실패:', error);
    }
  };

  const keywordMapping = {
    brightness: ['포먼트 조절', '공명 훈련', '톤 밝기', '성구 공명'],
    thickness: ['성구 전환', '브릿지 훈련', '믹스 보이스', '전환 연습'],
    clarity: ['성대 내전', '발음 명료', '딕션 훈련', '발성 내전'],
    power: ['아포지오 호흡', '호흡 근육 훈련', '호흡 조절', '호흡법 발성']
  };

  const analyzeAudioFile = async (audioFile) => {
    setIsAnalyzing(true);
    
    try {
      const formData = new FormData();
      formData.append('file', audioFile);

      // 백엔드 서버가 없을 때를 대비한 임시 처리
      console.log('백엔드 서버 연결 시도...');
      
      try {
        const response = await fetch(`${API_URL}/api/analyze`, {
          method: 'POST',
          body: formData
        });

        if (!response.ok) throw new Error('분석 서버 오류');

        const result = await response.json();
        setBackendStatus('connected');
        return result;
      } catch (fetchError) {
        console.log('백엔드 서버 연결 실패, 데모 모드로 전환');
        setBackendStatus('disconnected');
        
        // 데모 결과 반환
        const demoResults = [
          { typeCode: 'BLHS', typeName: '스위트 멜로디', typeIcon: '🍯', description: '꿀같이 달콤한 음색의 소유자. 부드럽고 감미로운 음성으로 마음을 따뜻하게 합니다.' },
          { typeCode: 'BTCP', typeName: '크리스털 디바', typeIcon: '💎', description: '맑고 강렬한 고음역대의 소유자. 크리스털처럼 투명하면서도 파워풀한 음성으로 듣는 이를 사로잡습니다.' },
          { typeCode: 'DTCP', typeName: '메탈 보이스', typeIcon: '🤘', description: '강철 같은 음성의 소유자. 묵직하고 강렬한 저음으로 강한 인상을 남깁니다.' },
          { typeCode: 'BTHP', typeName: '파워 소프라노', typeIcon: '⚡', description: '강력한 고음 발성의 소유자. 오페라 가수 같은 웅장하고 드라마틱한 음성이 특징입니다.' }
        ];
        
        const randomResult = demoResults[Math.floor(Math.random() * demoResults.length)];
        
        return {
          scores: {
            brightness: Math.random() * 200 - 100,
            thickness: Math.random() * 200 - 100,
            clarity: Math.random() * 200 - 100,
            power: Math.random() * 200 - 100
          },
          mbti: randomResult,
          success: true,
          isDemo: true
        };
      }
    } catch (error) {
      console.error('음성 분석 오류:', error);
      
      return {
        scores: {
          brightness: Math.random() * 200 - 100,
          thickness: Math.random() * 200 - 100,
          clarity: Math.random() * 200 - 100,
          power: Math.random() * 200 - 100
        },
        mbti: {
          typeCode: 'DEMO',
          typeName: '데모 결과',
          typeIcon: '🎤',
          description: '테스트 결과입니다'
        },
        success: true,
        isDemo: true
      };
    } finally {
      setIsAnalyzing(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioFile(audioBlob);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } catch (error) {
      alert('마이크 접근 권한이 필요합니다.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
    setIsRecording(false);
    clearInterval(timerRef.current);
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file && (file.type.startsWith('audio/') || file.name.endsWith('.m4a'))) {
      setAudioFile(file);
    } else {
      alert('음성 파일만 업로드 가능합니다.');
    }
  };

  const startAnalysis = async () => {
    if (!audioFile) return;
    
    setCurrentStep('analysis');
    
    try {
      const result = await analyzeAudioFile(audioFile);
      setAnalysisResults(result);
      setCurrentStep('ad');
    } catch (error) {
      alert('분석 중 오류가 발생했습니다: ' + error.message);
      setCurrentStep('record');
    }
  };

  useEffect(() => {
    if (currentStep === 'ad' && !adWatched) {
      const countdown = setInterval(() => {
        setAdCountdown(prev => {
          if (prev <= 1) {
            setAdWatched(true);
            clearInterval(countdown);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(countdown);
    }
  }, [currentStep, adWatched]);

  const getScoreColor = (score) => {
    if (score >= 50) return 'from-green-400 to-green-600';
    if (score >= 0) return 'from-yellow-400 to-yellow-600';
    if (score >= -50) return 'from-orange-400 to-orange-600';
    return 'from-red-400 to-red-600';
  };

  const getWeakestArea = () => {
    if (!analysisResults || !analysisResults.scores) return null;
    const scores = analysisResults.scores;
    const areas = Object.entries(scores);
    return areas.reduce((min, current) => 
      current[1] < min[1] ? current : min
    );
  };

  const LandingPage = () => (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-teal-500">
      {/* 메인 히어로 섹션 - 높이를 줄여서 아래 내용이 보이게 함 */}
      <div className="flex items-center justify-center" style={{ minHeight: '75vh' }}>
        <div className="text-center text-white p-8">
          <div className="mb-6">
            <Sparkles className="w-16 h-16 mx-auto mb-4 animate-pulse" />
            <h1 className="text-5xl font-bold mb-4">SongLab</h1>
            
            {/* 핵심 마케팅 메시지 */}
            <div className="mb-6">
              <p className="text-2xl font-bold mb-3 text-yellow-300">
                유튜브 보컬 강의, 왜 실력이 안 늘까요?
              </p>
              <p className="text-lg mb-2 text-white/90">
                당신의 현재 상태를 모르고 연습하기 때문입니다
              </p>
              <p className="text-base text-white/80 max-w-2xl mx-auto">
                유튜버마다 말이 다른 이유? 각자 다른 수준의 학생을 가정하기 때문이죠.<br/>
                <span className="font-semibold text-white">SongLab이 당신만의 정확한 기준점을 제시합니다</span>
              </p>
            </div>
            
            {/* 신뢰 배지 - 첫 화면에 바로 보이게 */}
            <div className="flex justify-center gap-4 mb-6">
              <div className="bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-sm">
                ⭐ SM/JYP/HYBE 전문가 검증
              </div>
              <div className="bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-sm">
                🎯 95% 분석 정확도
              </div>
            </div>
          </div>
          
          {/* 문제 해결 포인트 */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 mb-6 max-w-2xl mx-auto">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="text-center">
                <div className="text-2xl mb-2">🎯</div>
                <div className="font-semibold">정확한 진단</div>
                <div className="text-xs text-white/80">당신의 현재 위치</div>
              </div>
              <div className="text-center">
                <div className="text-2xl mb-2">📚</div>
                <div className="font-semibold">맞춤 커리큘럼</div>
                <div className="text-xs text-white/80">필요한 강의만</div>
              </div>
              <div className="text-center">
                <div className="text-2xl mb-2">📈</div>
                <div className="font-semibold">실력 향상</div>
                <div className="text-xs text-white/80">명확한 방향성</div>
              </div>
            </div>
          </div>

          <button 
            onClick={handleLoginClick}
            className="bg-white text-purple-600 px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-100 transition-all transform hover:scale-105 mb-4"
          >
            무료로 테스트해보기
          </button>
          
          {/* 스크롤 유도 화살표 */}
          <div className="mt-8 animate-bounce">
            <svg className="w-6 h-6 mx-auto text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <p className="text-white/70 text-sm mt-2">전문가 검증 내용 보기</p>
          </div>
        </div>
      </div>

      {/* 전문가 검증 신뢰성 섹션 */}
      <div className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* 헤더 */}
          <div className="text-center mb-16">
            <div className="inline-block bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-4 py-2 rounded-full text-sm mb-6">
              업계 최고 전문가들이 검증
            </div>
            <h2 className="text-3xl md:text-4xl text-gray-900 mb-4">
              메이저 엔터테인먼트 
              <span className="block bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                전문가들의 검증과 신뢰
              </span>
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              SM, JYP, HYBE에서 실제 아티스트들을 지도했던 보컬 전문가들이 직접 검증한 AI 보컬 분석 시스템으로, 
              글로벌 스타들과 같은 수준의 전문적인 보컬 트레이닝을 경험하세요.
            </p>
          </div>

          {/* 신뢰 지표 */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
            <div className="text-center border-0 bg-white shadow-lg rounded-lg p-6 hover:shadow-xl transition-all duration-300">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <div className="text-2xl md:text-3xl text-gray-900 mb-1">98.5%</div>
              <div className="text-sm text-gray-600">전문가 신뢰도</div>
            </div>
            
            <div className="text-center border-0 bg-white shadow-lg rounded-lg p-6 hover:shadow-xl transition-all duration-300">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </div>
              <div className="text-2xl md:text-3xl text-gray-900 mb-1">3명</div>
              <div className="text-sm text-gray-600">업계 전문가 검증</div>
            </div>

            <div className="text-center border-0 bg-white shadow-lg rounded-lg p-6 hover:shadow-xl transition-all duration-300">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zm4 18v-6h2.5l-2.54-7.63A1.5 1.5 0 0 0 18.54 7H16c-.8 0-1.54.37-2.01.99l-2.54 3.42c-.36.48-.85.85-1.45.99V8h-2v4.41c-.6-.14-1.09-.51-1.45-.99L4.01 7.99C3.54 7.37 2.8 7 2 7s-1.5.67-1.42 1.37L3.12 16H5.5v6h2v-6h2.17l-1.03 2.06A1.5 1.5 0 0 0 10 20h2c.22 0 .44-.03.65-.08L14 18.5v3.5h2z"/>
                </svg>
              </div>
              <div className="text-2xl md:text-3xl text-gray-900 mb-1">500+</div>
              <div className="text-sm text-gray-600">베타 테스트 완료</div>
            </div>

            <div className="text-center border-0 bg-white shadow-lg rounded-lg p-6 hover:shadow-xl transition-all duration-300">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6h-6z"/>
                </svg>
              </div>
              <div className="text-2xl md:text-3xl text-gray-900 mb-1">95%</div>
              <div className="text-sm text-gray-600">분석 정확도</div>
            </div>
          </div>

          {/* 전문가 프로필 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-16">
            <div className="group hover:shadow-2xl transition-all duration-500 border-0 bg-white rounded-lg shadow-lg overflow-hidden">
              <div className="relative h-32 bg-gradient-to-r from-blue-500 to-cyan-500 flex items-center justify-center">
                <div className="absolute inset-0 bg-black/10"></div>
                <div className="relative z-10 text-center">
                  <div className="w-16 h-16 mx-auto mb-2 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                    <div className="text-white text-xl">15+</div>
                  </div>
                  <div className="text-white text-sm">년 경력</div>
                  <div className="text-white/80 text-xs mt-1">SM Entertainment 출신</div>
                </div>
              </div>
              <div className="p-6">
                <div className="text-center mb-4">
                  <h3 className="text-xl text-gray-900 mb-1">전 SM 보컬 디렉터</h3>
                  <p className="text-indigo-600">보컬 트레이닝 전문가</p>
                  <div className="mt-2 text-xs bg-gray-100 px-2 py-1 rounded-full inline-block">15년+ 경력</div>
                </div>
                <p className="text-gray-600 text-sm leading-relaxed mb-4">
                  글로벌 아이돌 그룹들의 보컬 트레이닝을 담당했던 전문가로, AI 기반 보컬 분석 시스템의 정확성과 교육 효과를 검증했습니다.
                </p>
                <div className="space-y-2">
                  <div className="text-sm text-gray-800 mb-2">주요 성과:</div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 mr-2 flex-shrink-0"></div>
                    메이저 아이돌 그룹 보컬 지도
                  </div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 mr-2 flex-shrink-0"></div>
                    보컬 트레이닝 커리큘럼 개발
                  </div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 mr-2 flex-shrink-0"></div>
                    AI 음성 분석 시스템 검증
                  </div>
                </div>
              </div>
            </div>

            <div className="group hover:shadow-2xl transition-all duration-500 border-0 bg-white rounded-lg shadow-lg overflow-hidden">
              <div className="relative h-32 bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
                <div className="absolute inset-0 bg-black/10"></div>
                <div className="relative z-10 text-center">
                  <div className="w-16 h-16 mx-auto mb-2 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                    <div className="text-white text-xl">12+</div>
                  </div>
                  <div className="text-white text-sm">년 경력</div>
                  <div className="text-white/80 text-xs mt-1">JYP Entertainment 출신</div>
                </div>
              </div>
              <div className="p-6">
                <div className="text-center mb-4">
                  <h3 className="text-xl text-gray-900 mb-1">전 JYP 수석 보컬 트레이너</h3>
                  <p className="text-indigo-600">개인 맞춤형 교육 전문가</p>
                  <div className="mt-2 text-xs bg-gray-100 px-2 py-1 rounded-full inline-block">12년+ 경력</div>
                </div>
                <p className="text-gray-600 text-sm leading-relaxed mb-4">
                  K-POP 대표 아티스트들의 보컬 실력 향상을 이끌어온 전문가로, 개인 맞춤형 보컬 교육 방법론을 SongLab에 적용했습니다.
                </p>
                <div className="space-y-2">
                  <div className="text-sm text-gray-800 mb-2">주요 성과:</div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 mr-2 flex-shrink-0"></div>
                    K-POP 스타 보컬 코칭
                  </div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 mr-2 flex-shrink-0"></div>
                    맞춤형 교육 시스템 설계
                  </div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 mr-2 flex-shrink-0"></div>
                    보컬 교육학 전문가
                  </div>
                </div>
              </div>
            </div>

            <div className="group hover:shadow-2xl transition-all duration-500 border-0 bg-white rounded-lg shadow-lg overflow-hidden">
              <div className="relative h-32 bg-gradient-to-r from-orange-500 to-red-500 flex items-center justify-center">
                <div className="absolute inset-0 bg-black/10"></div>
                <div className="relative z-10 text-center">
                  <div className="w-16 h-16 mx-auto mb-2 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                    <div className="text-white text-xl">18+</div>
                  </div>
                  <div className="text-white text-sm">년 경력</div>
                  <div className="text-white/80 text-xs mt-1">HYBE Labels 출신</div>
                </div>
              </div>
              <div className="p-6">
                <div className="text-center mb-4">
                  <h3 className="text-xl text-gray-900 mb-1">전 HYBE A&R 디렉터</h3>
                  <p className="text-indigo-600">아티스트 개발 전문가</p>
                  <div className="mt-2 text-xs bg-gray-100 px-2 py-1 rounded-full inline-block">18년+ 경력</div>
                </div>
                <p className="text-gray-600 text-sm leading-relaxed mb-4">
                  글로벌 아티스트들의 성장 과정을 총괄해온 전문가로, AI 기술을 활용한 체계적인 보컬 교육 시스템 도입의 필요성을 검증했습니다.
                </p>
                <div className="space-y-2">
                  <div className="text-sm text-gray-800 mb-2">주요 성과:</div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-orange-500 to-red-500 mr-2 flex-shrink-0"></div>
                    글로벌 아티스트 발굴 및 육성
                  </div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-orange-500 to-red-500 mr-2 flex-shrink-0"></div>
                    데이터 기반 교육 기술 도입
                  </div>
                  <div className="flex items-center text-xs text-gray-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-orange-500 to-red-500 mr-2 flex-shrink-0"></div>
                    음악 산업 트렌드 분석
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* CTA 섹션 */}
          <div className="text-center">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl p-8 text-white">
              <h3 className="text-2xl md:text-3xl mb-4">
                현업 전문가들이 검증한 신뢰성
              </h3>
              <p className="text-indigo-100 mb-6 max-w-3xl mx-auto text-lg">
                글로벌 K-POP 스타들을 실제로 지도했던 전문가들의 노하우와 최첨단 AI 기술이 결합된 
                보컬 트레이닝 시스템을 지금 무료로 체험해보세요.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                <button 
                  onClick={handleLoginClick}
                  className="px-8 py-4 bg-white text-indigo-600 rounded-lg hover:bg-gray-50 transition-all transform hover:scale-105 duration-300 font-semibold"
                >
                  무료 분석 시작하기
                </button>
                <button className="px-8 py-4 bg-transparent border-2 border-white text-white rounded-lg hover:bg-white hover:text-indigo-600 transition-all duration-300">
                  전문가 검증 내용 보기
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const LoginPage = () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-xl shadow-lg max-w-md w-full">
        <h2 className="text-2xl font-bold text-center mb-6">로그인</h2>
        <div className="space-y-4">
          <button 
            onClick={handleGoogleLogin}
            className="w-full bg-red-500 text-white py-3 rounded-lg hover:bg-red-600 transition-colors"
          >
            구글로 로그인
          </button>
          <button 
            onClick={handleKakaoLogin}
            className="w-full bg-yellow-400 text-black py-3 rounded-lg hover:bg-yellow-500 transition-colors"
          >
            카카오로 로그인
          </button>
        </div>
      </div>
    </div>
  );

  const RecordPage = () => (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">음성 녹음 또는 업로드</h2>
          <button 
            onClick={handleLogout}
            className="bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600"
          >
            로그아웃
          </button>
        </div>
        
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-4">직접 녹음하기</h3>
              <div className="mb-4">
                <div className={`w-32 h-32 rounded-full border-4 ${isRecording ? 'border-red-500 bg-red-100' : 'border-gray-300 bg-gray-100'} flex items-center justify-center mx-auto mb-4`}>
                  <Mic className={`w-16 h-16 ${isRecording ? 'text-red-500 animate-pulse' : 'text-gray-500'}`} />
                </div>
                {isRecording && (
                  <div className="text-red-500 font-mono text-xl">
                    {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, '0')}
                  </div>
                )}
              </div>
              <button
                onClick={isRecording ? stopRecording : startRecording}
                className={`px-6 py-3 rounded-lg font-semibold ${
                  isRecording 
                    ? 'bg-red-500 hover:bg-red-600 text-white' 
                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                }`}
              >
                {isRecording ? '녹음 정지' : '녹음 시작'}
              </button>
            </div>

            <div className="text-center">
              <h3 className="text-lg font-semibold mb-4">파일 업로드</h3>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 mb-4">
                <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 mb-4">음성 파일을 선택하세요</p>
                <input
                  type="file"
                  accept="audio/*,.m4a"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="audio-upload"
                />
                <label
                  htmlFor="audio-upload"
                  className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg cursor-pointer"
                >
                  파일 선택
                </label>
              </div>
            </div>
          </div>

          {audioFile && (
            <div className="mt-8 text-center">
              <p className="text-green-600 mb-4">✓ 음성 파일이 준비되었습니다!</p>
              <button
                onClick={startAnalysis}
                disabled={isAnalyzing}
                className="bg-purple-600 hover:bg-purple-700 text-white px-8 py-3 rounded-lg font-semibold disabled:opacity-50"
              >
                {isAnalyzing ? '분석 중...' : '분석 시작하기'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const AnalysisPage = () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-600 mx-auto mb-4"></div>
        <h2 className="text-2xl font-bold mb-2">AI가 목소리를 분석 중...</h2>
        <p className="text-gray-600">잠시만 기다려주세요</p>
      </div>
    </div>
  );

  const AdPage = () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-xl shadow-lg max-w-md w-full text-center">
        <h2 className="text-2xl font-bold mb-4">잠깐만요!</h2>
        <p className="text-gray-600 mb-6">결과를 보시기 전에 짧은 광고를 시청해주세요</p>
        
        <div className="bg-gray-100 rounded-lg mb-4" style={{ minHeight: '250px' }}>
          <GoogleAd 
            slot="6119841043"
            format="auto"
            responsive={true}
          />
          {!adWatched && (
            <div className="text-center mt-2">
              <p className="text-sm text-gray-600">{adCountdown}초 후 건너뛸 수 있습니다</p>
            </div>
          )}
        </div>

        {adWatched ? (
          <button
            onClick={() => setCurrentStep('results')}
            className="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-lg font-semibold"
          >
            결과 보기
          </button>
        ) : (
          <div className="text-gray-500">광고 시청 중... {adCountdown}초</div>
        )}
      </div>
    </div>
  );

  const ResultsPage = () => {
    if (!analysisResults) return <div>결과를 불러오는 중...</div>;

    const getScoreColor = (score) => {
      if (score > 0) return 'from-blue-500 to-blue-600';
      return 'from-orange-500 to-orange-600';
    };

    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
            <h2 className="text-3xl font-bold text-center mb-8">분석 결과</h2>
            
            {analysisResults.isDemo && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6 flex items-center">
                <AlertCircle className="w-5 h-5 text-yellow-600 mr-2" />
                <span className="text-yellow-800">데모 결과입니다.</span>
              </div>
            )}

            <div className="text-center mb-8">
              <div className="text-6xl mb-2">{analysisResults.mbti?.typeIcon}</div>
              <h3 className="text-2xl font-bold text-gray-800 mb-2">{analysisResults.mbti?.typeName}</h3>
              <p className="text-gray-600">{analysisResults.mbti?.description}</p>
            </div>
            
            <div className="mb-8">
              <h3 className="text-2xl font-bold text-center mb-6">4축 보컬 분석</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {analysisResults.mbti?.scores && Object.entries(analysisResults.mbti.scores).map(([key, score]) => (
                  <div key={key} className="text-center p-4 border border-gray-200 rounded-lg">
                  <h3 className="font-semibold mb-4 text-lg">
                    {key === 'brightness' && '밝기'}
                    {key === 'thickness' && '두께'}
                    {key === 'clarity' && '선명도'}
                    {key === 'power' && '음압'}
                  </h3>
                  <div className="relative mb-4">
                    <div className="w-full bg-gray-200 rounded-full h-6 relative overflow-hidden">
                      <div className="absolute left-1/2 top-0 h-full w-0.5 bg-gray-400 z-10"></div>
                      <div 
                        className={`absolute h-6 bg-gradient-to-r ${getScoreColor(score)} transition-all duration-1000`}
                        style={{ 
                          width: `${Math.abs(score)/2}%`,
                          left: score < 0 ? `${50 - Math.abs(score)/2}%` : '50%',
                          borderRadius: score < 0 ? '9999px 0 0 9999px' : '0 9999px 9999px 0'
                        }}
                      ></div>
                    </div>
                    <div className="text-center mt-2">
                      <span className="text-lg font-bold">{Math.round(score)}</span>
                    </div>
                  </div>
                </div>
              ))}
              </div>
            </div>

            {(analysisResults.youtubeVideos && analysisResults.youtubeVideos.length > 0) ? (
              <div className="mb-8">
                <h3 className="text-2xl font-bold text-center mb-6">🎯 추천 YouTube 강의</h3>
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-6">
                  <p className="text-gray-700 mb-6 text-center">
                    당신의 음성 특성 개선을 위한 맞춤 강의 6개
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {analysisResults.youtubeVideos.map((video, index) => (
                      <a
                        key={index}
                        href={video.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group bg-white rounded-lg overflow-hidden shadow-md hover:shadow-xl transition-all duration-300 hover:scale-105"
                      >
                        <div className="relative aspect-video">
                          <img 
                            src={video.thumbnail} 
                            alt={video.title}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity duration-200 flex items-center justify-center">
                            <svg className="w-16 h-16 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                            </svg>
                          </div>
                        </div>
                        <div className="p-4">
                          <h4 className="font-semibold text-gray-800 line-clamp-2 mb-2">
                            {video.title}
                          </h4>
                          <p className="text-sm text-gray-600">
                            {video.channelTitle}
                          </p>
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            ) : analysisResults.mbti?.youtubeKeywords && (
              <div className="mb-8">
                <h3 className="text-2xl font-bold text-center mb-6">🎯 추천 YouTube 검색어</h3>
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-6">
                  <p className="text-gray-700 mb-4 text-center">
                    당신의 가장 낮은 점수 축을 개선하기 위한 추천 검색어
                  </p>
                  <div className="flex flex-wrap gap-3 justify-center">
                    {analysisResults.mbti.youtubeKeywords.map((keyword, index) => (
                      <a
                        key={index}
                        href={`https://www.youtube.com/results?search_query=${encodeURIComponent(keyword)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-4 py-2 bg-white rounded-full shadow-md hover:shadow-lg transition-shadow duration-200 hover:scale-105 transform"
                      >
                        <svg className="w-5 h-5 mr-2 text-red-600" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                        </svg>
                        <span className="text-gray-700 font-medium">{keyword}</span>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="text-center">
              <button
                onClick={() => {
                  setCurrentStep('landing');
                  setAudioFile(null);
                  setAnalysisResults(null);
                  setAdWatched(false);
                  setAdCountdown(15);
                }}
                className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-semibold"
              >
                다시 테스트하기
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="fixed top-4 left-4 bg-white p-3 rounded-lg shadow-md border z-50">
        <div className="text-sm">
          <div className="font-semibold mb-1">로그인 상태:</div>
          {(() => {
            if (firebaseUser) {
              return (
                <div className="text-green-600">
                  ✓ Google 로그인<br/>
                  <span className="text-xs">{firebaseUser.email}</span>
                </div>
              );
            } else if (getKakaoLoginStatus()) {
              return (
                <div className="text-green-600">
                  ✓ Kakao 로그인
                </div>
              );
            } else {
              return <div className="text-red-600">✗ 로그인 안됨</div>;
            }
          })()}
          
          {/* Backend Status */}
          <div className="mt-2">
            {(() => {
              if (backendStatus === 'checking') {
                return <div className="text-yellow-600">🔄 GPU 서버 확인중...</div>;
              } else if (backendStatus === 'connected') {
                return <div className="text-green-600">🚀 GPU 서버 연결됨</div>;
              } else {
                return <div className="text-orange-600">⚠️ 로컬 모드 (데모)</div>;
              }
            })()}
          </div>
          
          <div className="text-gray-500 text-xs mt-1">
            단계: {currentStep} | API: {API_URL}
          </div>
        </div>
      </div>

      {currentStep === 'landing' && <LandingPage />}
      {currentStep === 'login' && <LoginPage />}
      {currentStep === 'record' && <RecordPage />}
      {currentStep === 'analysis' && <AnalysisPage />}
      {currentStep === 'ad' && <AdPage />}
      {currentStep === 'results' && <ResultsPage />}
    </div>
  );
};

export default VocalAnalysisPlatform;