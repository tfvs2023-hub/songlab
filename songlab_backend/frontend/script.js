// SongLab Frontend JavaScript - API 연동 및 광고 시스템
class SongLabApp {
    constructor() {
        this.currentSession = null;
        this.currentUser = null;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.recordingChunks = [];
        this.recordingTimer = null;
        
        this.init();
    }

    // 초기화
    async init() {
        this.setupEventListeners();
        await this.checkLoginStatus();
        await this.loadAuthUrls();
        this.setupDragAndDrop();
    }

    // 이벤트 리스너 설정
    setupEventListeners() {
        // 파일 업로드
        document.getElementById('file-input').addEventListener('change', this.handleFileSelect.bind(this));
        document.getElementById('analyze-btn').addEventListener('click', this.startAnalysis.bind(this));
        
        // 결과보기
        document.getElementById('show-result-btn').addEventListener('click', this.showResult.bind(this));
        
        // 녹음 기능
        document.getElementById('record-btn').addEventListener('click', this.startRecording.bind(this));
        document.getElementById('stop-recording').addEventListener('click', this.stopRecording.bind(this));
        
        // 로그인
        document.getElementById('kakao-login').addEventListener('click', this.kakaoLogin.bind(this));
        document.getElementById('google-login').addEventListener('click', this.googleLogin.bind(this));
        document.getElementById('logout-btn').addEventListener('click', this.logout.bind(this));
        
        // 액션 버튼들
        document.getElementById('share-btn').addEventListener('click', this.shareResult.bind(this));
        document.getElementById('retry-btn').addEventListener('click', this.resetAnalysis.bind(this));
        
        // 광고 관련
        document.getElementById('skip-ad').addEventListener('click', this.skipAd.bind(this));
    }

    // 드래그 앤 드롭 설정
    setupDragAndDrop() {
        const uploadArea = document.getElementById('upload-area');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
        });

        uploadArea.addEventListener('drop', this.handleDrop.bind(this), false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleDrop(e) {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    // 파일 선택 처리
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.handleFile(file);
        }
    }

    // 파일 처리
    handleFile(file) {
        // 파일 검증
        if (!this.validateFile(file)) {
            return;
        }

        this.currentFile = file;
        this.displayFileInfo(file);
    }

    // 파일 검증
    validateFile(file) {
        const maxSize = 50 * 1024 * 1024; // 50MB
        const allowedTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/x-m4a', 'audio/mp4'];
        
        if (file.size > maxSize) {
            this.showError('파일 크기가 50MB를 초과합니다.');
            return false;
        }
        
        if (!allowedTypes.some(type => file.type.includes(type.split('/')[1]))) {
            this.showError('지원하지 않는 파일 형식입니다. WAV, MP3, M4A 파일만 지원합니다.');
            return false;
        }
        
        return true;
    }

    // 파일 정보 표시
    displayFileInfo(file) {
        const fileInfo = document.getElementById('file-info');
        const fileName = document.getElementById('file-name');
        const fileSize = document.getElementById('file-size');
        
        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);
        fileInfo.classList.remove('hidden');
    }

    // 파일 크기 포맷팅
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 분석 시작
    async startAnalysis() {
        if (!this.currentFile) {
            this.showError('파일을 선택해주세요.');
            return;
        }

        this.showLoading('음성을 분석 중입니다...');

        try {
            const formData = new FormData();
            formData.append('file', this.currentFile);

            // 인증 헤더 추가
            const headers = {};
            if (this.currentUser) {
                headers['Authorization'] = `Bearer ${localStorage.getItem('songlab_token')}`;
            }

            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData,
                headers: headers
            });

            const result = await response.json();

            if (response.ok) {
                if (result.status === 'analysis_completed') {
                    this.currentSession = result.session_id;
                    this.showAnalysisComplete();
                } else {
                    this.showError(result.detail || '분석 중 오류가 발생했습니다.');
                }
            } else {
                this.showError(result.detail || '분석 실패');
            }
        } catch (error) {
            console.error('분석 오류:', error);
            this.showError('네트워크 오류가 발생했습니다.');
        } finally {
            this.hideLoading();
        }
    }

    // 분석 완료 표시
    showAnalysisComplete() {
        document.getElementById('upload-area').classList.add('hidden');
        document.getElementById('result-section').classList.remove('hidden');
        document.getElementById('analysis-complete').classList.remove('hidden');
    }

    // 결과보기 (광고 포함)
    async showResult() {
        if (!this.currentSession) {
            this.showError('세션 정보가 없습니다.');
            return;
        }

        try {
            const headers = {};
            if (this.currentUser) {
                headers['Authorization'] = `Bearer ${localStorage.getItem('songlab_token')}`;
            }

            const response = await fetch(`/analyze/result/${this.currentSession}`, {
                headers: headers
            });

            const result = await response.json();

            if (response.ok) {
                if (result.status === 'show_ad_first') {
                    // 광고 먼저 표시
                    this.showAdvertisement(result.advertisement, result.next_endpoint);
                } else {
                    // 광고 없으면 바로 결과 표시
                    this.displayFinalResult(result);
                }
            } else {
                this.showError(result.detail || '결과 조회 실패');
            }
        } catch (error) {
            console.error('결과 조회 오류:', error);
            this.showError('결과를 불러올 수 없습니다.');
        }
    }

    // 광고 표시
    showAdvertisement(adData, nextEndpoint) {
        const adModal = document.getElementById('ad-modal');
        const adContainer = document.getElementById('ad-container');
        const adTimer = document.getElementById('ad-timer');
        const skipBtn = document.getElementById('skip-ad');

        // 광고 내용 표시
        if (adData.type === 'adsense') {
            adContainer.innerHTML = adData.content;
            // AdSense 스크립트 재실행
            if (window.adsbygoogle && window.adsbygoogle.push) {
                window.adsbygoogle.push({});
            }
        } else {
            adContainer.innerHTML = adData.content;
            
            // 클릭 이벤트 추가
            if (adData.click_url) {
                adContainer.style.cursor = 'pointer';
                adContainer.addEventListener('click', () => {
                    window.open(adData.click_url, '_blank');
                });
            }
        }

        // 모달 표시
        adModal.classList.remove('hidden');

        // 5초 카운트다운
        let timeLeft = 5;
        const countdown = setInterval(() => {
            adTimer.textContent = timeLeft;
            timeLeft--;

            if (timeLeft < 0) {
                clearInterval(countdown);
                skipBtn.classList.remove('hidden');
            }
        }, 1000);

        // 광고 건너뛰기 이벤트
        const skipHandler = async () => {
            clearInterval(countdown);
            adModal.classList.add('hidden');
            skipBtn.removeEventListener('click', skipHandler);
            
            // 최종 결과 가져오기
            await this.getFinalResult(nextEndpoint);
        };

        skipBtn.addEventListener('click', skipHandler);

        // 5초 후 자동으로 건너뛰기 버튼 활성화
        setTimeout(() => {
            if (!skipBtn.classList.contains('hidden')) {
                skipHandler();
            }
        }, 8000);
    }

    // 광고 건너뛰기
    skipAd() {
        document.getElementById('ad-modal').classList.add('hidden');
    }

    // 최종 결과 가져오기
    async getFinalResult(endpoint) {
        try {
            const headers = {};
            if (this.currentUser) {
                headers['Authorization'] = `Bearer ${localStorage.getItem('songlab_token')}`;
            }

            const response = await fetch(endpoint, { headers });
            const result = await response.json();

            if (response.ok) {
                this.displayFinalResult(result);
            } else {
                this.showError('최종 결과를 불러올 수 없습니다.');
            }
        } catch (error) {
            console.error('최종 결과 조회 오류:', error);
            this.showError('네트워크 오류가 발생했습니다.');
        }
    }

    // 최종 결과 표시
    displayFinalResult(result) {
        const mbti = result.mbti;

        // 기본 정보
        document.getElementById('mbti-name').textContent = mbti.typeName;
        document.getElementById('mbti-code').textContent = this.extractTypeCode(mbti);
        document.getElementById('mbti-desc').textContent = mbti.typeDesc;

        // 점수 바 애니메이션
        this.animateScores(mbti.scores);

        // 음역대 정보
        document.getElementById('current-note').textContent = mbti.currentNote || '분석 중';
        document.getElementById('potential-note').textContent = mbti.potentialNote || '분석 중';

        // 장점/단점
        this.displayList('pros-list', mbti.pros || []);
        this.displayList('cons-list', mbti.cons || []);

        // 추천곡
        this.displaySongs(mbti.topSongs || []);

        // 결과 섹션 표시
        document.getElementById('analysis-complete').classList.add('hidden');
        document.getElementById('final-result').classList.remove('hidden');
    }

    // MBTI 코드 추출
    extractTypeCode(mbti) {
        if (mbti.scores) {
            const scores = mbti.scores;
            let code = '';
            code += scores.brightness < 0 ? 'D' : 'B';
            code += scores.thickness > 0 ? 'K' : 'N';
            code += scores.clarity > 0 ? 'C' : 'R';
            code += scores.power > 0 ? 'S' : 'W';
            return code;
        }
        return '----';
    }

    // 점수 바 애니메이션
    animateScores(scores) {
        const scoreItems = ['brightness', 'thickness', 'clarity', 'power'];
        
        scoreItems.forEach(item => {
            const score = scores[item] || 0;
            const bar = document.getElementById(`${item}-bar`);
            const scoreText = document.getElementById(`${item}-score`);
            
            // 점수 텍스트 업데이트
            scoreText.textContent = `${score > 0 ? '+' : ''}${score}`;
            
            // 바 너비 계산 (0~100%)
            const width = Math.abs(score);
            
            // 색상 설정
            if (score > 0) {
                bar.className = 'score-fill positive';
            } else {
                bar.className = 'score-fill negative';
            }
            
            // 애니메이션
            setTimeout(() => {
                bar.style.width = `${width}%`;
            }, 500);
        });
    }

    // 리스트 표시
    displayList(elementId, items) {
        const list = document.getElementById(elementId);
        list.innerHTML = '';
        
        items.slice(0, 3).forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            list.appendChild(li);
        });
    }

    // 추천곡 표시
    displaySongs(songs) {
        const container = document.getElementById('songs-list');
        container.innerHTML = '';
        
        songs.slice(0, 4).forEach(song => {
            const tag = document.createElement('span');
            tag.className = 'song-tag';
            tag.textContent = song;
            container.appendChild(tag);
        });
    }

    // 녹음 시작
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.recordingChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                this.recordingChunks.push(event.data);
            };
            
            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.recordingChunks, { type: 'audio/wav' });
                const file = new File([blob], 'recording.wav', { type: 'audio/wav' });
                this.handleFile(file);
                this.currentFile = file;
            };
            
            this.mediaRecorder.start();
            this.isRecording = true;
            
            // UI 업데이트
            document.getElementById('record-btn').classList.add('hidden');
            document.getElementById('recording-controls').classList.remove('hidden');
            
            // 타이머 시작
            this.startRecordingTimer();
            
        } catch (error) {
            console.error('녹음 오류:', error);
            this.showError('마이크 접근 권한이 필요합니다.');
        }
    }

    // 녹음 중지
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // 스트림 정지
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            // UI 업데이트
            document.getElementById('record-btn').classList.remove('hidden');
            document.getElementById('recording-controls').classList.add('hidden');
            
            // 타이머 정지
            if (this.recordingTimer) {
                clearInterval(this.recordingTimer);
                this.recordingTimer = null;
            }
        }
    }

    // 녹음 타이머
    startRecordingTimer() {
        let seconds = 0;
        const timerElement = document.getElementById('recording-time');
        
        this.recordingTimer = setInterval(() => {
            seconds++;
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            timerElement.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }, 1000);
    }

    // 로그인 상태 확인
    async checkLoginStatus() {
        const token = localStorage.getItem('songlab_token');
        if (token) {
            try {
                const response = await fetch('/auth/me', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (response.ok) {
                    const user = await response.json();
                    this.showUserInfo(user);
                } else {
                    localStorage.removeItem('songlab_token');
                }
            } catch (error) {
                localStorage.removeItem('songlab_token');
            }
        }
    }

    // OAuth URL 로드
    async loadAuthUrls() {
        try {
            const response = await fetch('/auth/urls');
            this.authUrls = await response.json();
        } catch (error) {
            console.error('OAuth URL 로드 실패:', error);
        }
    }

    // 카카오 로그인
    kakaoLogin() {
        if (this.authUrls && this.authUrls.kakao_login_url) {
            window.location.href = this.authUrls.kakao_login_url;
        }
    }

    // 구글 로그인
    googleLogin() {
        if (this.authUrls && this.authUrls.google_login_url) {
            window.location.href = this.authUrls.google_login_url;
        }
    }

    // 로그아웃
    logout() {
        localStorage.removeItem('songlab_token');
        this.currentUser = null;
        this.hideUserInfo();
    }

    // 사용자 정보 표시
    showUserInfo(user) {
        this.currentUser = user;
        
        document.getElementById('user-name').textContent = user.name;
        if (user.profile_image) {
            document.getElementById('user-avatar').src = user.profile_image;
        }
        
        document.getElementById('auth-buttons').classList.add('hidden');
        document.getElementById('user-info').classList.remove('hidden');
    }

    // 사용자 정보 숨기기
    hideUserInfo() {
        document.getElementById('auth-buttons').classList.remove('hidden');
        document.getElementById('user-info').classList.add('hidden');
    }

    // 결과 공유
    shareResult() {
        if (navigator.share) {
            navigator.share({
                title: 'SongLab 보컬 분석 결과',
                text: `내 보컬 MBTI는 ${document.getElementById('mbti-name').textContent}입니다!`,
                url: window.location.href
            });
        } else {
            // 폴백: 클립보드에 복사
            const text = `내 보컬 MBTI는 ${document.getElementById('mbti-name').textContent}입니다! ${window.location.href}`;
            navigator.clipboard.writeText(text).then(() => {
                this.showSuccess('링크가 클립보드에 복사되었습니다!');
            });
        }
    }

    // 분석 재시작
    resetAnalysis() {
        this.currentSession = null;
        this.currentFile = null;
        
        document.getElementById('file-input').value = '';
        document.getElementById('file-info').classList.add('hidden');
        document.getElementById('result-section').classList.add('hidden');
        document.getElementById('upload-area').classList.remove('hidden');
    }

    // 로딩 표시
    showLoading(message = '처리 중...') {
        document.getElementById('loading-text').textContent = message;
        document.getElementById('loading-overlay').classList.remove('hidden');
    }

    // 로딩 숨기기
    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }

    // 에러 메시지 표시
    showError(message) {
        alert(`❌ ${message}`);
    }

    // 성공 메시지 표시
    showSuccess(message) {
        alert(`✅ ${message}`);
    }
}

// OAuth 콜백 처리
function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    
    if (code) {
        const provider = window.location.pathname.includes('kakao') ? 'kakao' : 'google';
        
        fetch(`/auth/${provider}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        })
        .then(response => response.json())
        .then(result => {
            if (result.access_token) {
                localStorage.setItem('songlab_token', result.access_token);
                window.location.href = '/';
            } else {
                alert('로그인 실패: ' + (result.detail || '알 수 없는 오류'));
                window.location.href = '/';
            }
        })
        .catch(error => {
            console.error('OAuth 콜백 처리 오류:', error);
            alert('로그인 처리 중 오류 발생');
            window.location.href = '/';
        });
    }
}

// 앱 초기화
document.addEventListener('DOMContentLoaded', () => {
    // OAuth 콜백 페이지인지 확인
    if (window.location.pathname.includes('/auth/') && window.location.pathname.includes('/callback')) {
        handleOAuthCallback();
    } else {
        // 메인 앱 실행
        window.songLabApp = new SongLabApp();
    }
});

// 서비스 워커 등록 (PWA)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}