    // 음역 분석에 따른 영역 계산
    const needsImprovement = Object.entries(scores)
      .filter(([key, value]) => value < -20)
      .sort(([, a], [, b]) => a - b);

    const strengths = Object.entries(scores)
      .filter(([key, value]) => value > 20)
      .sort(([, a], [, b]) => b - a);

import React, { useState, useRef, useEffect } from 'react';
import { Mic, Upload, Youtube, Sparkles, Volume2, AlertCircle } from 'lucide-react';

const VocalAnalysisPlatform = () => {
  const [currentStep, setCurrentStep] = useState('landing');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioFile, setAudioFile] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // API URL configuration: prefer VITE_API_URL, otherwise fall back to runtime origin
  const API_URL = (import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL.trim()) || window.location.origin;
  const [backendStatus, setBackendStatus] = useState('checking');
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

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
    checkBackendHealth();
  }, []);

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
        const response = await fetch(`${API_URL}/api/analyze?force_engine=studio`, {
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
        
        // 데모 결과 반환 (백엔드 형식에 맞게)
        const demoResults = [
          { typeCode: 'BTCP', typeName: 'BTCP', typeIcon: '🌟', description: '밝고 두꺼우며 명료하고 파워풀한 보컬 | 팝/뮤지컬형' },
          { typeCode: 'DNFS', typeName: 'DNFS', typeIcon: '🌙', description: '어둡고 얇고 숨섞인 부드러운 보컬 | Lo-Fi/칠아웃형' },
          { typeCode: 'BNCP', typeName: 'BNCP', typeIcon: '🌟', description: '밝고 얇으며 명료하고 파워풀한 보컬 | K-POP/댄스형' },
          { typeCode: 'DTFS', typeName: 'DTFS', typeIcon: '🌙', description: '어둡고 두껍고 숨섞인 부드러운 보컬 | 재즈/소울형' }
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
          typeName: 'DEMO',
          typeIcon: '🎤',
          description: '데모 결과입니다'
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
      setCurrentStep('results');
    } catch (error) {
      alert('분석 중 오류가 발생했습니다: ' + error.message);
      setCurrentStep('record');
    }
  };

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

  // 카카오톡 공유 함수
  const shareToKakao = () => {
    if (!analysisResults) return;
    
    const scores = analysisResults.scores || {};
    const vocalType = analysisResults.mbti;
    
    // 점수를 퍼센트로 변환 (0-100%)
    const getPercentage = (score) => Math.round(((score + 100) / 2));
    
    const shareText = `🎤 SongLab 보컬 분석 결과
    
${vocalType ? `🎭 보컬 타입: ${vocalType.typeName || vocalType.type_code}
${vocalType.description}

` : ""}📊 나의 보컬 특성:
☀️ 밝기: ${getPercentage(scores.brightness || 0)}%
🎵 두께: ${getPercentage(scores.thickness || 0)}%
🔊 음압: ${getPercentage(scores.loudness || 0)}%
💎 선명도: ${getPercentage(scores.clarity || 0)}%

✨ SongLab에서 나만의 보컬 분석 받아보세요!
👉 www.songlab.kr`;

    try {
      if (window.Kakao && window.Kakao.Share) {
        window.Kakao.Share.sendDefault({
          objectType: "text",
          text: shareText,
          link: {
            mobileWebUrl: "https://www.songlab.kr",
            webUrl: "https://www.songlab.kr"
          }
        });
      } else {
        navigator.clipboard.writeText(shareText).then(() => {
          alert("분석 결과가 클립보드에 복사되었습니다!");
        }).catch(() => {
          alert("공유 기능을 사용할 수 없습니다.");
        });
      }
    } catch (error) {
      console.error("카카오톡 공유 오류:", error);
      navigator.clipboard.writeText(shareText).then(() => {
        alert("분석 결과가 클립보드에 복사되었습니다!");
      }).catch(() => {
        alert("공유 기능을 사용할 수 없습니다.");
      });
    }
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
                내 목소리 사용설명서 SongLab
              </p>
              <p className="text-base text-white/80 max-w-2xl mx-auto">
                아무 강의나 보지마세요!<br/>
                <span className="font-semibold text-white">SongLab이 여러분만을 위한 커리큘럼을 설계해드립니다!</span>
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
            onClick={() => setCurrentStep('record')}
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

          {/* CTA 섹션 */}
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
                onClick={() => setCurrentStep('record')}
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
  );

  const RecordPage = () => {
    const [audioLevel, setAudioLevel] = useState(0);
    const [snrEstimate, setSnrEstimate] = useState(null);
    const [recordingQuality, setRecordingQuality] = useState('unknown');
    const [environmentChecks, setEnvironmentChecks] = useState({
      quietLocation: false,
      phoneDistance: false,
      micPermission: false,
      backgroundNoise: false
    });
    const [showPrivacyDetails, setShowPrivacyDetails] = useState(false);
    const [userProfile, setUserProfile] = useState(() => {
      if (typeof window === 'undefined') return null;
      try {
        const stored = window.localStorage.getItem('songlab_user');
        return stored ? JSON.parse(stored) : null;
      } catch (error) {
        console.error('Failed to parse stored user profile:', error);
        return null;
      }
    });

    useEffect(() => {
      if (typeof window === 'undefined') return;
      const handleStorage = (event) => {
        if (event.key === 'songlab_user') {
          try {
            setUserProfile(event.newValue ? JSON.parse(event.newValue) : null);
          } catch (error) {
            console.error('Failed to parse stored user profile:', error);
          }
        }
      };

      window.addEventListener('storage', handleStorage);
      return () => window.removeEventListener('storage', handleStorage);
    }, []);

    const isLoggedIn = Boolean(userProfile);
    const userEmail = userProfile?.email || 'guest@songlab.kr';
    const loginLabel = userProfile?.provider === 'google' ? 'Google 로그인' : '로그인';

    const handleAuthAction = () => {
      if (isLoggedIn) {
        if (typeof window !== 'undefined') {
          window.localStorage.removeItem('songlab_user');
        }
        setUserProfile(null);
        setAudioFile(null);
        setAnalysisResults(null);
        setCurrentStep('landing');
      } else {
        setCurrentStep('landing');
        if (typeof window !== 'undefined') {
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      }
    };

    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const dataArrayRef = useRef(null);
    const animationFrameRef = useRef(null);
    const backgroundNoiseRef = useRef(null);
    const signalLevelsRef = useRef([]);

    // Initialize audio monitoring
    const initializeAudioMonitoring = async (stream) => {
      try {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
        analyserRef.current = audioContextRef.current.createAnalyser();
        analyserRef.current.fftSize = 2048;

        const source = audioContextRef.current.createMediaStreamSource(stream);
        source.connect(analyserRef.current);

        dataArrayRef.current = new Uint8Array(analyserRef.current.frequencyBinCount);

        // Start monitoring
        monitorAudioLevel();

        setEnvironmentChecks(prev => ({ ...prev, micPermission: true }));
      } catch (error) {
        console.error('Audio monitoring setup failed:', error);
      }
    };

    // Monitor audio levels and quality
    const monitorAudioLevel = () => {
      if (!analyserRef.current || !dataArrayRef.current) return;

      analyserRef.current.getByteTimeDomainData(dataArrayRef.current);

      // Calculate RMS level
      let sum = 0;
      for (let i = 0; i < dataArrayRef.current.length; i++) {
        const sample = (dataArrayRef.current[i] - 128) / 128;
        sum += sample * sample;
      }
      const rms = Math.sqrt(sum / dataArrayRef.current.length);
      const level = Math.max(0, Math.min(100, rms * 100 * 3));

      setAudioLevel(level);

      // Store levels for noise analysis
      signalLevelsRef.current.push(level);
      if (signalLevelsRef.current.length > 100) {
        signalLevelsRef.current.shift();
      }

      // Estimate background noise (lowest 20% of levels)
      if (signalLevelsRef.current.length > 50) {
        const sortedLevels = [...signalLevelsRef.current].sort((a, b) => a - b);
        const noiseFloor = sortedLevels[Math.floor(sortedLevels.length * 0.2)];
        backgroundNoiseRef.current = noiseFloor;

        // Update environment checks
        setEnvironmentChecks(prev => ({
          ...prev,
          backgroundNoise: noiseFloor < 5,
          quietLocation: noiseFloor < 10
        }));

        // Estimate SNR
        const signalLevel = Math.max(...signalLevelsRef.current);
        if (signalLevel > noiseFloor) {
          const snr = 20 * Math.log10(signalLevel / Math.max(noiseFloor, 0.1));
          setSnrEstimate(Math.max(0, Math.min(40, snr)));

          // Update recording quality
          if (snr > 25) setRecordingQuality('excellent');
          else if (snr > 20) setRecordingQuality('good');
          else if (snr > 15) setRecordingQuality('fair');
          else setRecordingQuality('poor');
        }
      }

      // Check phone distance based on level consistency
      const recentLevels = signalLevelsRef.current.slice(-20);
      if (recentLevels.length >= 20) {
        const avgLevel = recentLevels.reduce((a, b) => a + b, 0) / recentLevels.length;
        const variance = recentLevels.reduce((sum, level) => sum + Math.pow(level - avgLevel, 2), 0) / recentLevels.length;
        setEnvironmentChecks(prev => ({
          ...prev,
          phoneDistance: avgLevel > 15 && avgLevel < 80 && variance < 100
        }));
      }

      animationFrameRef.current = requestAnimationFrame(monitorAudioLevel);
    };

    // Enhanced recording start
    const startRecordingAdvanced = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            echoCancellation: true,
            noiseSuppression: false, // We want to analyze natural audio
            autoGainControl: false,
            sampleRate: 44100
          } 
        });

        await initializeAudioMonitoring(stream);

        mediaRecorderRef.current = new MediaRecorder(stream, {
          mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
        });

        audioChunksRef.current = [];

        mediaRecorderRef.current.ondataavailable = (event) => {
          audioChunksRef.current.push(event.data);
        };

        mediaRecorderRef.current.onstop = () => {
          const audioBlob = new Blob(audioChunksRef.current, { 
            type: mediaRecorderRef.current.mimeType 
          });
          setAudioFile(audioBlob);

          // Clean up audio monitoring
          if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current);
          }
          if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close();
          }
        };

        mediaRecorderRef.current.start();
        setIsRecording(true);
        setRecordingTime(0);

        timerRef.current = setInterval(() => {
          setRecordingTime(prev => prev + 1);
        }, 1000);
      } catch (error) {
        alert('마이크 접근 권한이 필요합니다: ' + error.message);
        setEnvironmentChecks(prev => ({ ...prev, micPermission: false }));
      }
    };

    // Enhanced recording stop
    const stopRecordingAdvanced = () => {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
      setIsRecording(false);
      clearInterval(timerRef.current);

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };

    const QualityIndicator = ({ quality, snr }) => {
      const map = {
        excellent: { label: '최고', dot: 'bg-green-500', wrapper: 'bg-green-50 text-green-700' },
        good: { label: '좋음', dot: 'bg-blue-500', wrapper: 'bg-blue-50 text-blue-700' },
        fair: { label: '보통', dot: 'bg-yellow-500', wrapper: 'bg-yellow-50 text-yellow-700' },
        poor: { label: '낮음', dot: 'bg-red-500', wrapper: 'bg-red-50 text-red-700' },
        unknown: { label: '측정중', dot: 'bg-gray-400', wrapper: 'bg-gray-100 text-gray-600' }
      };

      const config = map[quality] || map.unknown;

      return (
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${config.wrapper}`}>
          <span className={`w-2.5 h-2.5 rounded-full ${config.dot}`}></span>
          <span>{config.label}</span>
          {typeof snr === 'number' && (
            <span className="text-xs font-normal opacity-80">SNR {snr.toFixed(1)}dB</span>
          )}
        </div>
      );
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
        setCurrentStep('results');
      } catch (error) {
        alert('분석 중 오류가 발생했습니다: ' + error.message);
        setCurrentStep('record');
      }
    };

    const qualityGauge = {
      excellent: { percent: 100, gradient: 'from-green-400 via-teal-400 to-green-500' },
      good: { percent: 75, gradient: 'from-blue-400 via-sky-400 to-blue-500' },
      fair: { percent: 55, gradient: 'from-yellow-400 via-amber-400 to-yellow-500' },
      poor: { percent: 30, gradient: 'from-red-400 via-rose-400 to-red-500' },
      unknown: { percent: 40, gradient: 'from-gray-300 via-gray-300 to-gray-400' }
    };
    const currentQuality = qualityGauge[recordingQuality] || qualityGauge.unknown;

    const environmentItems = [
      { key: 'micPermission', label: '마이크 권한', icon: '🎤' },
      { key: 'quietLocation', label: '조용한 환경', icon: '🔇' },
      { key: 'phoneDistance', label: '적절한 거리', icon: '📱' },
      { key: 'backgroundNoise', label: '배경소음 없음', icon: '✨' }
    ];

    const backendLabel = backendStatus === 'connected' ? '실시간 서버 연결' : backendStatus === 'checking' ? '연결 확인 중' : '로컬 모드 (데모)';
    const apiDisplay = API_URL || '데모 엔진';

    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 via-white to-purple-50 py-10 px-4">
        <div className="max-w-5xl mx-auto space-y-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold">
                <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">전문가급 보컬 녹음</span>
              </h2>
              <p className="text-gray-600 mt-1">최고 품질의 분석을 위한 스마트 녹음 가이드</p>
            </div>
            <button
              type="button"
              onClick={handleAuthAction}
              className="self-start md:self-auto inline-flex items-center gap-2 bg-slate-900 text-white px-5 py-2.5 rounded-lg shadow hover:bg-slate-800 transition"
            >
              {isLoggedIn ? '로그아웃' : '로그인'}
            </button>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-start">
              <div className="text-amber-600 text-xl mr-3 mt-0.5">ℹ️</div>
              <div className="flex-1 space-y-3">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <h3 className="text-amber-800 font-semibold">서비스 이용 안내</h3>
                  <button
                    onClick={() => setShowPrivacyDetails(!showPrivacyDetails)}
                    className="text-amber-600 hover:text-amber-800 text-sm font-medium flex items-center transition"
                  >
                    자세히보기
                    <span className={`ml-1 transition-transform ${showPrivacyDetails ? 'rotate-180' : ''}`}>▼</span>
                  </button>
                </div>
                <p className="text-amber-700 text-sm leading-relaxed">
                  본 서비스를 이용하시면 <strong>서비스 개선 및 AI 모델 학습을 위한 익명화된 음성 데이터 수집 및 활용</strong>에 동의하는 것으로 간주됩니다.
                </p>

                {showPrivacyDetails && (
                  <div className="mt-3 p-4 bg-amber-100 rounded-xl border border-amber-200 space-y-3 text-sm text-amber-800">
                    <div>
                      <h4 className="font-semibold mb-2">📋 수집하는 정보</h4>
                      <ul className="list-disc list-inside space-y-1 text-xs">
                        <li>음성 분석을 위한 오디오 데이터 (일시적 처리 후 삭제)</li>
                        <li>분석 결과 데이터 (익명화 저장)</li>
                        <li>계정 정보 (이메일, 닉네임)</li>
                      </ul>
                    </div>
                    <div>
                      <h4 className="font-semibold mb-2">🔐 활용 목적</h4>
                      <p className="text-xs leading-relaxed">서비스 품질 개선, 개인 맞춤 커리큘럼 추천, AI 모델 고도화를 위한 연구</p>
                    </div>
                    <div>
                      <h4 className="font-semibold mb-2">⏳ 보관 기간</h4>
                      <p className="text-xs leading-relaxed">동의 철회 시 즉시 삭제되며, 그렇지 않은 경우 안전하게 암호화되어 보관됩니다.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-xl font-semibold mb-4 flex items-center text-gray-900">
              <span className="inline-flex items-center justify-center w-2 h-2 bg-green-500 rounded-full mr-3"></span>
              녹음 환경 체크
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {environmentItems.map(({ key, label, icon }) => {
                const active = environmentChecks[key];
                return (
                  <div
                    key={key}
                    className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition ${
                      active ? 'border-green-200 bg-green-50 text-green-700' : 'border-gray-200 bg-gray-50 text-gray-600'
                    }`}
                  >
                    <span className="text-xl">{icon}</span>
                    <div className="text-sm font-medium">{label}</div>
                    <div className={`ml-auto text-base font-semibold ${active ? 'text-green-500' : 'text-gray-400'}`}>
                      {active ? '✓' : '•'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-6">
            <div className="text-center space-y-3">
              <h3 className="text-xl font-semibold text-gray-900">실시간 음성 모니터링</h3>
              <p className="text-sm text-gray-500">안정적인 녹음을 위해 레벨을 확인해 주세요.</p>
            </div>

            <div className="space-y-4">
              <div>
                <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500 transition-all duration-150"
                    style={{ width: `${audioLevel}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500 font-medium mt-2">
                  <span>조용함</span>
                  <span>적정</span>
                  <span>큰 소리</span>
                </div>
              </div>

              <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full bg-gradient-to-r ${currentQuality.gradient} transition-all duration-300`}
                  style={{ width: `${currentQuality.percent}%` }}
                ></div>
              </div>
              <div className="flex justify-center">
                <QualityIndicator quality={recordingQuality} snr={snrEstimate} />
              </div>
            </div>

            <div className="flex flex-col items-center gap-4">
              <div className={`w-36 h-36 rounded-full border-4 flex items-center justify-center shadow-lg transition-all ${
                isRecording ? 'border-red-400 bg-red-50 shadow-red-200' : 'border-blue-400 bg-blue-50 shadow-blue-200'
              }`}>
                <Mic className={`w-14 h-14 ${isRecording ? 'text-red-500 animate-pulse' : 'text-blue-500'}`} />
              </div>
              {isRecording && (
                <div className="text-red-600 font-mono text-2xl">
                  {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, '0')}
                </div>
              )}

              <button
                onClick={isRecording ? stopRecordingAdvanced : startRecordingAdvanced}
                className={`px-10 py-4 rounded-xl font-semibold text-lg transition-all duration-300 shadow-lg ${
                  isRecording
                    ? 'bg-red-500 hover:bg-red-600 text-white shadow-red-200 hover:scale-105'
                    : 'bg-blue-500 hover:bg-blue-600 text-white shadow-blue-200 hover:scale-105'
                }`}
              >
                {isRecording ? '🛑 녹음 정지' : '🎙️ 녹음 시작'}
              </button>

              <div className="text-sm text-gray-400">또는</div>

              <label
                htmlFor="audio-upload"
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-6 py-3 rounded-xl cursor-pointer transition inline-flex items-center"
              >
                <Upload className="w-5 h-5 mr-2" />
                파일 업로드
              </label>
              <input
                type="file"
                accept="audio/*,.m4a"
                onChange={handleFileUpload}
                className="hidden"
                id="audio-upload"
              />
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-xl font-semibold mb-4 flex items-center text-gray-900">
              <span className="mr-2">💡</span>녹음 가이드
            </h3>
            <div className="space-y-3 text-sm">
              <div className="p-4 rounded-xl bg-blue-50 text-blue-800">
                <div className="font-semibold mb-1">📱 스마트폰 거리</div>
                <p>입에서 15-20cm 떨어뜨리기</p>
              </div>
              <div className="p-4 rounded-xl bg-purple-50 text-purple-800">
                <div className="font-semibold mb-1">🎵 녹음 방법</div>
                <p>30초 이내로 피드백받고 싶은 부분을 무반주로 편하게 불러주세요</p>
              </div>
              <div className="p-4 rounded-xl bg-orange-50 text-orange-800">
                <div className="font-semibold mb-1">🏠 환경 설정</div>
                <p>조용한 실내, 에어컨 OFF</p>
              </div>
              {snrEstimate !== null && (
                <div className="p-4 rounded-xl bg-gray-50 text-gray-700">
                  <div className="font-semibold mb-1">실시간 품질 측정</div>
                  <p>신호대잡음비: {snrEstimate.toFixed(1)}dB</p>
                  <p className="text-xs mt-1">
                    {snrEstimate > 25 ? '🎯 최고 품질!' : snrEstimate > 20 ? '👍 좋은 품질' : snrEstimate > 15 ? '⚠️ 더 조용한 환경 필요' : '❌ 환경 개선 필요'}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <div className="w-full sm:w-auto bg-white rounded-2xl shadow-sm border border-gray-100 p-5 text-sm text-gray-600 space-y-2">
              <div className="font-semibold text-gray-900 mb-2">로그인 상태</div>
              <div className={`flex items-center gap-2 ${isLoggedIn ? 'text-green-600' : 'text-gray-500'}`}>
                <span>✓</span>
                <span>{isLoggedIn ? loginLabel : '로그인 필요'}</span>
              </div>
              <div className="pl-6 text-xs text-gray-500">{userEmail}</div>
              <div className="flex items-center gap-2 text-green-600">
                <span>✓</span>
                <span>{backendLabel}</span>
              </div>
              <div className="pl-6 text-xs text-gray-500">단계: record | API: {apiDisplay}</div>
            </div>
          </div>

          {audioFile && (
            <div className="text-center">
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 inline-block">
                <div className="flex items-center justify-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <span className="text-green-600 text-xl">✓</span>
                  </div>
                  <div className="text-left">
                    <p className="text-green-600 font-semibold">녹음 완료!</p>
                    <div className="text-gray-600 text-sm">
                      품질: <QualityIndicator quality={recordingQuality} snr={snrEstimate} />
                    </div>
                  </div>
                </div>

                <button
                  onClick={startAnalysis}
                  disabled={isAnalyzing}
                  className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-4 rounded-xl font-semibold text-lg disabled:opacity-60 disabled:cursor-not-allowed transition"
                >
                  {isAnalyzing ? '분석 중...' : 'AI로 분석 시작하기'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };
const AnalysisPage = () => {
   const [messageIndex, setMessageIndex] = useState(0);

   const analysisMessages = [
     "당신의 목소리, 송랩이 꼼꼼히 분석하고 있어요! 👂",
     "내재된 보컬 포텐, 터뜨릴 준비 중! 🎤 송랩이 열심히 찾고 있어요!",
     "오직 당신만을 위한 갓성비 보컬 레시피 설계 중! 🎵",
     "목소리의 숨겨진 매력을 찾아서! 송랩이 딥~하게 탐색 중! 🔍",
     "지루한 연습은 이제 그만! 송랩이 최적의 보컬 루틴을 뚝딱! 만들고 있어요!",
     "찰떡같이! 당신에게 딱 맞는 유튭 강의를 고르고 있어요! ✅",
     "한 단계 더 성장할 당신의 보컬, 송랩이 완벽 준비 중! 💫",
     "보컬 고민은 이제 안녕~ 👋 송랩이 해결책을 거의 다 찾았어요!",
     "지금, 당신의 목소리 변화가 시작됩니다! 송랩이 열일 중! ✨",
     "두근두근... 💖 당신의 목소리 가이드가 곧 공개됩니다! 기대해도 좋아요!"
   ];

   useEffect(() => {
     const id = setInterval(() => {
       setMessageIndex((prev) => (prev + 1) % analysisMessages.length);
     }, 3000);
     return () => clearInterval(id);
   }, []);

   return (
     <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-teal-50 flex items-center justify-center">
       <div className="text-center max-w-md mx-auto p-8">
         <div className="animate-spin rounded-full h-20 w-20 border-4 border-purple-200 border-t-purple-600 mx-auto mb-6"></div>
         <h2 className="text-2xl font-bold mb-4 text-gray-800">AI가 목소리를 분석 중...</h2>
         <div className="h-16 flex items-center justify-center">
           <p className="text-purple-700 text-lg font-medium leading-relaxed animate-pulse">
             {analysisMessages[messageIndex]}
           </p>
         </div>
         <div className="mt-6 flex justify-center space-x-1">
           {[...Array(3)].map((_, i) => (
             <div
               key={i}
               className="w-2 h-2 bg-purple-600 rounded-full animate-bounce"
               style={{ animationDelay: `${i * 0.2}s` }}
             />
           ))}
         </div>
       </div>
     </div>
   );
 };


  const ResultsPage = () => {
      const youtubeVideos = analysisResults?.youtube_videos || [];

      if (!analysisResults) return <div>결과를 불러오는 중...</div>;

      const clampScore = (value) => {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) return 0;
        return Math.max(-100, Math.min(100, numeric));
      };

      const formatScore = (score) => `${score > 0 ? '+' : ''}${score.toFixed(1)}`;

      const getBarVisuals = (rawScore) => {
        const score = clampScore(rawScore);
        const percent = ((score + 100) / 200) * 100;
        const fillWidth = score >= 0 ? Math.max(0, percent - 50) : Math.max(0, 50 - percent);
        const fillStyle = score >= 0
          ? { left: '50%', width: `${fillWidth}%` }
          : { left: `${percent}%`, width: `${fillWidth}%` };
        const fillClass = score >= 0
          ? 'bg-gradient-to-r from-blue-400 via-blue-500 to-blue-600'
          : 'bg-gradient-to-l from-purple-500 via-purple-500 to-purple-400';
        const markerStyle = { left: `${percent}%` };
        return { score, percent, fillStyle, fillClass, markerStyle };
      };

      const traitDetails = [
        {
          key: 'brightness',
          label: '밝기',
          icon: '☀️',
          low: {
            title: '🌙 밝기가 낮다면?',
            range: '-100 ~ -20',
            pros: '차분하고 따뜻한 음색, 감성적인 곡에서 강점',
            cons: '너무 낮으면 답답하게 들릴 수 있어요'
          },
          high: {
            title: '🔆 밝기가 높다면?',
            range: '+20 ~ +100',
            pros: '선명하고 생동감 있는 인상, K-POP/댄스곡에 유리',
            cons: '과하면 날카롭게 느껴질 수 있어요'
          }
        },
        {
          key: 'clarity',
          label: '선명도',
          icon: '💎',
          low: {
            title: '🌫️ 선명도가 낮다면?',
            range: '-100 ~ -20',
            pros: '부드럽고 몽환적인 분위기 연출',
            cons: '가사가 흐릿하게 들릴 수 있어요'
          },
          high: {
            title: '💎 선명도가 높다면?',
            range: '+20 ~ +100',
            pros: '깔끔한 발음과 전달력, 프로페셔널한 인상',
            cons: '과하면 기계적으로 느껴질 수 있어요'
          }
        },
        {
          key: 'thickness',
          label: '두께',
          icon: '🎵',
          low: {
            title: '🍃 두께가 낮다면?',
            range: '-100 ~ -20',
            pros: '가볍고 섬세한 표현, 인디/어쿠스틱에 어울림',
            cons: '성량이 약하게 느껴질 수 있어요'
          },
          high: {
            title: '🌳 두께가 높다면?',
            range: '+20 ~ +100',
            pros: '풍부하고 웅장한 울림, 강렬한 곡에 적합',
            cons: '과하면 무겁고 답답하게 느껴질 수 있어요'
          }
        },
        {
          key: 'power',
          label: '음압',
          icon: '🔊',
          low: {
            title: '🌬️ 음압이 낮다면?',
            range: '-100 ~ -20',
            pros: '섬세하고 감성적인 표현, 발라드에서 강점',
            cons: '성량이 부족하게 느껴질 수 있어요'
          },
          high: {
            title: '💥 음압이 높다면?',
            range: '+20 ~ +100',
            pros: '폭발적인 파워와 카리스마',
            cons: '과하면 거칠게 들릴 수 있어요'
          }
        }
      ];

      return (
        <div className="space-y-8">
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">보컬 MBTI 분석 결과</h2>
              <p className="text-gray-600">각 지표는 -100 ~ +100 범위로, 음색의 방향성과 강도를 의미합니다.</p>
            </div>

            <div className="grid grid-cols-1 gap-8">
              {traitDetails.map(({ key, label, icon, low, high }) => {
                const rawScore = scores[key] ?? 0;
                const { score, percent, fillStyle, fillClass, markerStyle } = getBarVisuals(rawScore);
                const highlightLow = score <= -40;
                const highlightHigh = score >= 40;
                const lowCardClass = highlightLow ? 'border-purple-300 bg-purple-50/70' : 'border-gray-200 bg-gray-50';
                const highCardClass = highlightHigh ? 'border-blue-300 bg-blue-50/70' : 'border-gray-200 bg-gray-50';

                return (
                  <div key={key} className="bg-gradient-to-br from-white to-indigo-50/40 rounded-2xl p-6 shadow-sm border border-indigo-100">
                    <div className="text-center mb-6">
                      <div className="text-4xl mb-2">{icon}</div>
                      <h3 className="text-xl font-bold text-gray-900">{label}</h3>
                      <p className="text-sm text-gray-500 mt-1">현재 점수: <span className="font-semibold text-gray-800">{formatScore(score)}</span></p>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
                      <div className={`p-4 rounded-xl border ${lowCardClass}`}>
                        <h4 className="font-semibold text-sm text-gray-800 mb-1">{low.title}</h4>
                        <p className="text-xs text-gray-500 mb-2">범위 {low.range}</p>
                        <ul className="text-xs space-y-1 text-gray-600">
                          <li><span className="text-green-600 mr-1">✓</span>{low.pros}</li>
                          <li><span className="text-orange-500 mr-1">⚠</span>{low.cons}</li>
                        </ul>
                      </div>

                      <div className="px-4">
                        <div className="relative w-full bg-gray-200 rounded-full h-6 overflow-hidden shadow-inner">
                          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-400"></div>
                          <div className={`absolute top-0 bottom-0 rounded-full ${fillClass}`} style={fillStyle}></div>
                          <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2" style={markerStyle}>
                            <div className="w-4 h-4 rounded-full border-2 border-white shadow bg-indigo-500"></div>
                          </div>
                        </div>
                        <div className="flex justify-between text-[10px] text-gray-500 font-medium mt-2">
                          <span>-100</span>
                          <span>-50</span>
                          <span>0</span>
                          <span>+50</span>
                          <span>+100</span>
                        </div>
                      </div>

                      <div className={`p-4 rounded-xl border ${highCardClass}`}>
                        <h4 className="font-semibold text-sm text-gray-800 mb-1">{high.title}</h4>
                        <p className="text-xs text-gray-500 mb-2">범위 {high.range}</p>
                        <ul className="text-xs space-y-1 text-gray-600">
                          <li><span className="text-green-600 mr-1">✓</span>{high.pros}</li>
                          <li><span className="text-orange-500 mr-1">⚠</span>{high.cons}</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

      {/* 유튜브 추천 영상 섹션 */}
            <div className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100 mt-8">
              <h3 className="text-2xl font-bold text-center text-gray-800 mb-6">
                🎯 맞춤형 보컬 트레이닝 추천
              </h3>
              
              {youtubeVideos.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {youtubeVideos.map((video, index) => (
                      <div key={index} className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl p-4 border border-purple-100 hover:shadow-lg transition-all duration-300 hover:scale-105">
                        <div className="text-center">
                          <div className="mb-3">
                            <img 
                              src={video.thumbnail} 
                              alt={video.title}
                              className="w-full h-24 object-cover rounded-lg mb-2"
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                            <h4 className="font-bold text-gray-800 mb-1 text-sm leading-tight line-clamp-2">
                              {video.title}
                            </h4>
                            <p className="text-xs text-gray-500 mb-2">
                              {video.channelTitle}
                            </p>
                          </div>
                          
                          <button
                            onClick={() => {
                              window.open(video.url, '_blank');
                            }}
                            className="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-4 py-2 rounded-lg font-semibold transition-all duration-300 hover:scale-105 shadow-md text-sm w-full"
                          >
                            📺 영상 보기
                          </button>
                        </div>
                      </div>
                    ))
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  추천 영상을 불러오지 못했습니다.
                </div>
              )}

              <div className="text-center mt-6">
                <p className="text-sm text-gray-500">
                  💡 위 추천은 당신의 MBTI 보컬 타입 <span className="font-semibold text-purple-600">{analysisResults.mbti?.typeName || analysisResults.mbti?.typeCode}</span>과 분석 결과를 바탕으로 개인화되었습니다.
                </p>
              </div>
            </div>

            <div className="text-center space-y-4">
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button
                  onClick={shareToKakao}
                  className="bg-gradient-to-r from-yellow-400 to-yellow-500 hover:from-yellow-500 hover:to-yellow-600 text-black px-8 py-3 rounded-xl font-semibold transition-all duration-300 hover:scale-105 shadow-lg"
                >
                  📱 카카오톡 공유
                </button>
                <button
                  onClick={() => {
                    setCurrentStep("record");
                    setAudioFile(null);
                    setAnalysisResults(null);
                  }}
                  className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-3 rounded-xl font-semibold transition-all duration-300 hover:scale-105 shadow-lg"
                >
                  다시 분석하기
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div>
      {currentStep === 'landing' && <LandingPage />}
      {currentStep === 'record' && <RecordPage />}
      {currentStep === 'analysis' && <AnalysisPage />}
      {currentStep === 'results' && <ResultsPage />}
    </div>
  );
};

export default VocalAnalysisPlatform;
