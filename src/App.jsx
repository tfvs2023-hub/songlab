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

  useEffect(() => {
    initializeKakao();
    setKakaoStatusUpdateCallback(forceStatusUpdate);
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
        const response = await fetch('http://localhost:8001/api/analyze', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) throw new Error('분석 서버 오류');

        const result = await response.json();
        return result;
      } catch (fetchError) {
        console.log('백엔드 서버 연결 실패, 데모 모드로 전환');
        
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
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-teal-500 flex items-center justify-center">
      <div className="text-center text-white p-8">
        <div className="mb-8">
          <Sparkles className="w-16 h-16 mx-auto mb-4 animate-pulse" />
          <h1 className="text-5xl font-bold mb-4">SongLab</h1>
          <p className="text-xl mb-8">당신의 목소리를 분석하고 맞춤 보컬 강의를 추천해드려요</p>
        </div>
        
        <div className="grid grid-cols-2 gap-4 mb-8 max-w-md mx-auto text-sm">
          <div className="bg-white/20 p-3 rounded-lg">
            <Volume2 className="w-6 h-6 mx-auto mb-2" />
            <div>밝기 분석</div>
          </div>
          <div className="bg-white/20 p-3 rounded-lg">
            <div className="w-6 h-6 mx-auto mb-2 bg-white/30 rounded"></div>
            <div>두께 분석</div>
          </div>
          <div className="bg-white/20 p-3 rounded-lg">
            <div className="w-6 h-6 mx-auto mb-2 bg-white/30 rounded"></div>
            <div>선명도 분석</div>
          </div>
          <div className="bg-white/20 p-3 rounded-lg">
            <div className="w-6 h-6 mx-auto mb-2 bg-white/30 rounded"></div>
            <div>음압 분석</div>
          </div>
        </div>

        <button 
          onClick={handleLoginClick}
          className="bg-white text-purple-600 px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-100 transition-all transform hover:scale-105"
        >
          무료로 테스트해보기
        </button>
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
          <div className="text-gray-500 text-xs mt-1">
            단계: {currentStep}
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