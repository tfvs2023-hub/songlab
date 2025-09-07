import { signInWithGoogle, logout, auth, signInWithKakao } from './firebase';
import { useAuthState } from 'react-firebase-hooks/auth';
import React, { useState, useRef, useEffect } from 'react';
import { Mic, Upload, Play, Youtube, Sparkles, Volume2, AlertCircle } from 'lucide-react';

const VocalAnalysisPlatform = () => {
  const [currentStep, setCurrentStep] = useState('landing');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioFile, setAudioFile] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [adWatched, setAdWatched] = useState(false);
  const [adCountdown, setAdCountdown] = useState(15);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  // 키워드 매핑 (당신이 제공한 매핑)
  const keywordMapping = {
    brightness: ['포먼트 조절', '공명 훈련', '톤 밝기', '성구 공명'],
    thickness: ['성구 전환', '브릿지 훈련', '믹스 보이스', '전환 연습'],
    clarity: ['성대 내전', '발음 명료', '딕션 훈련', '발성 내전'],
    power: ['아포지오 호흡', '호흡 근육 훈련', '호흡 조절', '호흡법 발성']
  };

// 실제 음성 분석 API 호출
const analyzeAudioFile = async (audioFile) => {
  console.log('분석 시작 - 파일:', audioFile);
  setIsAnalyzing(true);
  
  try {
    const formData = new FormData();
    formData.append('file', audioFile);

    console.log('API 호출 시작 - URL: http://localhost:8001/analyze');
    // 실제 분석 API 호출 (당신의 Python 서버)
    const response = await fetch('http://localhost:8001/analyze', {
      method: 'POST',
      body: formData
    });

    console.log('API 응답 상태:', response.status, response.ok);

    if (!response.ok) {
      throw new Error('분석 서버 오류');
    }

    const result = await response.json();
    console.log('분석 결과:', result);
    
    if ((result.success || result.status === 'success') && result.mbti) {
      // -100~100 범위로 점수 변환
      const normalizedScores = {
        brightness: (result.mbti.scores.brightness - 50) * 2,
        thickness: (result.mbti.scores.thickness - 50) * 2,
        clarity: (result.mbti.scores.clarity - 50) * 2,
        power: (result.mbti.scores.power - 50) * 2
      };

      return {
        scores: normalizedScores,
        mbti: result.mbti,
        success: true
      };
    } else {
      throw new Error(result.message || '분석 실패');
    }
  } catch (error) {
    console.error('음성 분석 오류:', error);
    
    // 폴백: 가상의 결과 (개발/테스트용)
    return {
      scores: {
        brightness: Math.random() * 200 - 100,
        thickness: Math.random() * 200 - 100,
        clarity: Math.random() * 200 - 100,
        power: Math.random() * 200 - 100
      },
      mbti: {
        typeCode: 'BTCP',
        typeName: '크리스털 디바',
        typeIcon: '💎',
        description: '테스트 결과입니다'
      },
      success: true,
      isDemo: true
    };
  } finally {
    setIsAnalyzing(false);
  }
};

  // 녹음 시작
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

  // 녹음 정지
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
    setIsRecording(false);
    clearInterval(timerRef.current);
  };

  // 파일 업로드
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file && (file.type.startsWith('audio/') || file.name.endsWith('.m4a'))) {
      setAudioFile(file);
    } else {
      alert('음성 파일만 업로드 가능합니다. (mp3, wav, m4a 등)');
    }
  };

  // 분석 시작
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

  // 광고 시청
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

  // 결과 보기
  const showResults = () => {
    setCurrentStep('results');
  };

  // 점수 색상 결정
  const getScoreColor = (score) => {
    if (score >= 50) return 'from-green-400 to-green-600';
    if (score >= 0) return 'from-yellow-400 to-yellow-600';
    if (score >= -50) return 'from-orange-400 to-orange-600';
    return 'from-red-400 to-red-600';
  };

  // 가장 낮은 점수 영역 찾기
  const getWeakestArea = () => {
    if (!analysisResults) return null;
    const scores = analysisResults.scores;
    const areas = Object.entries(scores);
    return areas.reduce((min, current) => 
      current[1] < min[1] ? current : min
    );
  };

  // 랜딩 페이지
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
          onClick={() => setCurrentStep('login')}
          className="bg-white text-purple-600 px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-100 transition-all transform hover:scale-105"
        >
          무료로 테스트해보기
        </button>
      </div>
    </div>
  );

// 로그인 페이지
const LoginPage = () => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="bg-white p-8 rounded-xl shadow-lg max-w-md w-full">
      <h2 className="text-2xl font-bold text-center mb-6">로그인</h2>
      <div className="space-y-4">
        <button 
          onClick={async () => {
            try {
              await signInWithGoogle();
            } catch (error) {
              alert('로그인 실패: ' + error.message);
            }
          }}
          className="w-full bg-red-500 text-white py-3 rounded-lg hover:bg-red-600 transition-colors"
        >
          구글로 로그인
        </button>
        <button 
          onClick={async () => {
            try {
              const result = await signInWithKakao();
              console.log('카카오 로그인 성공:', result);
              setCurrentStep('record');
            } catch (error) {
              alert('카카오 로그인 실패: ' + error.message);
            }
          }}
          className="w-full bg-yellow-400 text-black py-3 rounded-lg hover:bg-yellow-500 transition-colors"
        >
          카카오로 로그인
        </button>
      </div>
    </div>
  </div>
);

  // 녹음/업로드 페이지
  const RecordPage = () => (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-center mb-8">음성 녹음 또는 업로드</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* 녹음 섹션 */}
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

            {/* 업로드 섹션 */}
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-4">파일 업로드</h3>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 mb-4">
                <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 mb-4">음성 파일을 끌어다 놓거나 클릭하여 선택</p>
                <p className="text-xs text-gray-400 mb-4">지원 형식: MP3, WAV, M4A</p>
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
              <p className="text-sm text-gray-500 mb-4">
                파일명: {audioFile.name || '녹음된 음성'}
              </p>
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

  // 분석 중 페이지
  const AnalysisPage = () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-600 mx-auto mb-4"></div>
        <h2 className="text-2xl font-bold mb-2">AI가 목소리를 분석 중...</h2>
        <p className="text-gray-600 mb-4">밝기, 두께, 선명도, 음압을 측정하고 있습니다</p>
        <div className="w-64 bg-gray-200 rounded-full h-2 mx-auto">
          <div className="bg-purple-600 h-2 rounded-full animate-pulse" style={{width: '60%'}}></div>
        </div>
      </div>
    </div>
  );

  // 광고 페이지
  const AdPage = () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-xl shadow-lg max-w-md w-full text-center">
        <h2 className="text-2xl font-bold mb-4">잠깐만요!</h2>
        <p className="text-gray-600 mb-6">결과를 보시기 전에 짧은 광고를 시청해주세요</p>
        
        <div className="bg-gray-800 h-48 rounded-lg flex items-center justify-center mb-4">
          <div className="text-white text-center">
            <Youtube className="w-12 h-12 mx-auto mb-2" />
            <p>광고 영상</p>
            {!adWatched && (
              <p className="text-sm mt-2">{adCountdown}초 후 건너뛸 수 있습니다</p>
            )}
          </div>
        </div>

        {adWatched ? (
          <button
            onClick={showResults}
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

  // 결과 페이지
  const ResultsPage = () => {
    if (!analysisResults) return <div>결과를 불러오는 중...</div>;

    const weakestArea = getWeakestArea();
    const weaknessKeywords = weakestArea ? keywordMapping[weakestArea[0]] : [];

    // 가상의 유튜브 영상 데이터
    const getRecommendedVideos = () => {
      if (!weakestArea) return [];
      
      const sampleVideos = {
        '포먼트 조절': [
          { title: '포먼트 조절로 음색 바꾸기', channel: '보컬코치김민수', views: '15만회', duration: '8:32' },
          { title: '공명 위치 찾는 법', channel: '발성의달인', views: '23만회', duration: '12:15' }
        ],
        '성구 전환': [
          { title: '브릿지 완벽 마스터', channel: '보컬트레이너이수진', views: '45만회', duration: '15:20' },
          { title: '믹스보이스 기초부터', channel: '노래교실TV', views: '38만회', duration: '22:18' }
        ],
        '성대 내전': [
          { title: '성대 내전 훈련법', channel: '보컬의정석', views: '12만회', duration: '9:45' },
          { title: '발음 명료하게 하는 법', channel: '딕션마스터', views: '28만회', duration: '14:32' }
        ],
        '호흡 조절': [
          { title: '아포지오 호흡법 완전정복', channel: '호흡의달인', views: '67만회', duration: '18:25' },
          { title: '호흡근 강화 운동', channel: '보컬피트니스', views: '34만회', duration: '11:40' }
        ]
      };
      
      const weakness = weakestArea[1] < -50 ? 
        Object.keys(keywordMapping)[0] : // 가장 첫 번째 키워드 사용
        weaknessKeywords[0]; // 실제 약점 키워드 사용
        
      return sampleVideos[weakness] || [];
    };

    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
            <h2 className="text-3xl font-bold text-center mb-8">분석 결과</h2>
            
            {analysisResults.isDemo && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6 flex items-center">
                <AlertCircle className="w-5 h-5 text-yellow-600 mr-2" />
                <span className="text-yellow-800">데모 결과입니다. 실제 분석을 위해서는 Python 서버가 필요합니다.</span>
              </div>
            )}

            {/* MBTI 결과 */}
            <div className="text-center mb-8">
              <div className="text-6xl mb-2">{analysisResults.mbti?.typeIcon}</div>
              <h3 className="text-2xl font-bold text-gray-800 mb-2">{analysisResults.mbti?.typeName}</h3>
              <p className="text-gray-600">{analysisResults.mbti?.description}</p>
            </div>
            
            {/* 분석 결과 차트 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              {Object.entries(analysisResults.scores).map(([key, score]) => (
                <div key={key} className="text-center p-4 border border-gray-200 rounded-lg">
                  <h3 className="font-semibold mb-4 text-lg">
                    {key === 'brightness' && '밝기 (Brightness)'}
                    {key === 'thickness' && '두께 (Thickness)'}
                    {key === 'clarity' && '선명도 (Clarity)'}
                    {key === 'power' && '음압 (Power)'}
                  </h3>
                  <div className="relative mb-4">
                    <div className="w-full bg-gray-200 rounded-full h-6 relative">
                      <div className="absolute left-1/2 top-0 h-full w-0.5 bg-gray-400"></div>
                      <div 
                        className={`bg-gradient-to-r ${getScoreColor(score)} h-6 rounded-full transition-all duration-1000 relative`}
                        style={{ 
                          width: `${Math.abs(score)/2}%`,
                          marginLeft: score < 0 ? `${50 - Math.abs(score)/4}%` : '50%'
                        }}
                      >
                        <div className="absolute -top-8 left-full transform -translate-x-1/2">
                          <span className="text-sm font-bold text-gray-700">{score > 0 ? '+' : ''}{Math.round(score)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>-100</span>
                      <span>0</span>
                      <span>+100</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 개선 포인트 */}
            {weakestArea && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
                <h3 className="text-lg font-semibold text-yellow-800 mb-2">💡 우선 개선 포인트</h3>
                <p className="text-yellow-700">
                  가장 개선이 필요한 영역: <strong>{weakestArea[0]}</strong> (점수: {Math.round(weakestArea[1])})
                </p>
              </div>
            )}
          </div>

          {/* 추천 유튜브 강의 */}
          <div className="bg-white rounded-xl shadow-lg p-8">
            <h3 className="text-2xl font-bold mb-6 flex items-center">
              <Youtube className="w-8 h-8 text-red-500 mr-3" />
              맞춤 보컬 강의 추천
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {getRecommendedVideos().map((video, index) => (
                <div key={index} className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                     onClick={() => window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(video.title)}`, '_blank')}>
                  <div className="relative">
                    <div className="w-full h-40 bg-gray-200 flex items-center justify-center">
                      <Youtube className="w-12 h-12 text-red-500" />
                    </div>
                    <div className="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white px-2 py-1 rounded text-xs">
                      {video.duration}
                    </div>
                  </div>
                  
                  <div className="p-4">
                    <h4 className="font-semibold text-gray-900 mb-2 hover:text-red-600 transition-colors">
                      {video.title}
                    </h4>
                    <p className="text-sm text-gray-600 mb-1">{video.channel}</p>
                    <p className="text-xs text-gray-500">{video.views} • YouTube</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 p-4 bg-gray-50 rounded-lg">
              <h4 className="font-semibold mb-3">관련 키워드로 더 찾아보기:</h4>
              <div className="flex flex-wrap gap-2">
                {weaknessKeywords.map((keyword, index) => (
                  <button
                    key={index}
                    onClick={() => window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(keyword + ' 보컬 강의')}`, '_blank')}
                    className="bg-white border border-gray-300 hover:border-red-500 hover:text-red-600 px-3 py-1 rounded-full text-sm transition-colors"
                  >
                    #{keyword}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6 text-center">
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

  // 메인 렌더링
  return (
    <div>
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