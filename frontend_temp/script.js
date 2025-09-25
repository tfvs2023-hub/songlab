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
    // Authentication removed for demo mode: no login required
    // await this.checkLoginStatus();
    // await this.loadAuthUrls();
        this.setupDragAndDrop();

    // ensure consent banner appears if anon_id not present
    this.ensureConsentUI();

        // 런타임 API URL: 빌드 시점에 설정되지 않아도 현재 도메인을 기본값으로 사용
        this.API_URL = (window.__SONGLAB_API_URL__ && window.__SONGLAB_API_URL__.trim()) || window.location.origin;
        // Ensure anon_id is present when user gives consent; will be set by consent UI
        this.anonId = this.getCookie('anon_id') || null;
        console.info(`Using API URL: ${this.API_URL} anon_id=${this.anonId}`);
        console.info(`Using API URL: ${this.API_URL}`);
    }

    // 이벤트 리스너 설정
    setupEventListeners() {
        const byId = id => document.getElementById(id);
        const bindIf = (id, evt, handler) => {
            const node = byId(id);
            if (node && node.addEventListener) node.addEventListener(evt, handler);
        };

        // 파일 업로드
        bindIf('file-input', 'change', this.handleFileSelect.bind(this));
        bindIf('analyze-btn', 'click', this.startAnalysis.bind(this));
        // Hero CTA buttons (ensure they start analysis/upload flow without login)
        bindIf('hero-analyze', 'click', (e) => {
            e.preventDefault();
            // If a file input exists, trigger it; otherwise start analysis flow
            const fileInput = document.getElementById('file-input');
            if (fileInput) {
                fileInput.click();
            } else {
                this.startAnalysis();
            }
        });
        bindIf('hero-demo', 'click', (e) => {
            e.preventDefault();
            // Demo should navigate to demo/result page rather than forcing login
            const demoBtn = document.getElementById('hero-demo');
            if (demoBtn) {
                // If there's a demo handler elsewhere, prefer that; otherwise show a quick demo alert
                if (typeof window.showDemo === 'function') {
                    window.showDemo();
                } else {
                    alert('데모 모드: 샘플 결과를 확인합니다.');
                    window.location.href = 'result.html';
                }
            }
        });

        // 결과보기
        bindIf('show-result-btn', 'click', this.showResult.bind(this));

        // 녹음 기능
        bindIf('record-btn', 'click', this.startRecording.bind(this));
        bindIf('stop-recording', 'click', this.stopRecording.bind(this));

        // 액션 버튼들
        bindIf('share-btn', 'click', this.shareResult.bind(this));
        bindIf('retry-btn', 'click', this.resetAnalysis.bind(this));

        // 광고 및 관련 UI 제거/비활성화
        const skipAdEl = byId('skip-ad');
        if (skipAdEl && skipAdEl.remove) skipAdEl.remove();
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

    // 파일 처리: 업로드된 파일을 검증하고 UI에 표시
    handleFile(file) {
        if (!file) return;

        // Validate file (size/type)
        if (!this.validateFile(file)) {
            this.currentFile = null;
            return;
        }

        // 저장 및 UI 업데이트
        this.currentFile = file;
        this.displayFileInfo(file);
    }

    // --- anonymous consent and anon_id helpers ---
    ensureConsentUI() {
        // if consent UI already present, skip
        if (document.getElementById('consent-banner')) return;

        const banner = document.createElement('div');
        banner.id = 'consent-banner';
        banner.className = 'consent-banner';
        banner.innerHTML = `
            <div class="consent-inner">
                <div>분석 결과는 익명으로 수집됩니다. 추후 Google로 계정 연결 가능.</div>
                <div><button id="consent-accept" class="btn btn--primary">동의하고 계속하기</button></div>
            </div>`;
        document.body.appendChild(banner);

        document.getElementById('consent-accept').addEventListener('click', () => {
            const anon = this.getCookie('anon_id') || this.generateAnonId();
            this.setCookie('anon_id', anon, 365);
            this.anonId = anon;
            banner.remove();
        });
    }

    generateAnonId() {
        // simple RFC4122-like random id
        return 'anon-' + ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    }

    setCookie(name, value, days) {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=/; SameSite=Lax';
    }

    getCookie(name) {
        return document.cookie.split('; ').reduce((r, v) => {
            const parts = v.split('=');
            return parts[0] === name ? decodeURIComponent(parts.slice(1).join('=')) : r;
        }, null);
    }

    // 파일 처리
    validateFile(file) {
        const maxSize = 50 * 1024 * 1024; // 50MB
        const allowedExts = ['.wav', '.mp3', '.m4a', '.flac', '.ogg'];
        const allowedTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/x-m4a', 'audio/mp4', 'audio/ogg', 'audio/flac'];

        if (file.size > maxSize) {
            this.showError('파일 크기가 50MB를 초과합니다.');
            return false;
        }

        // 일부 브라우저/환경에서는 file.type이 비어있을 수 있으므로 파일명 확장자를 검사
        const nameOk = file.name && allowedExts.some(ext => file.name.toLowerCase().endsWith(ext));
        const typeOk = file.type && allowedTypes.some(t => file.type.includes(t.split('/')[1]));

        if (!nameOk && !typeOk) {
            this.showError('지원하지 않는 파일 형식입니다. WAV, MP3, M4A 등을 업로드 해주세요.');
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

        this.showLoading('음성을 업로드하고 있습니다...');

        try {
            const formData = new FormData();
            formData.append('file', this.currentFile);

            // 진행 상황 업데이트
            setTimeout(() => this.showLoading('CREPE AI 모델을 로딩 중...'), 1000);
            setTimeout(() => this.showLoading('음성 특성을 추출하고 있습니다...'), 3000);
            setTimeout(() => this.showLoading('보컬 MBTI를 계산하고 있습니다...'), 8000);

            // 인증 및 anon headers 추가
            const headers = {};
            if (this.currentUser) {
                headers['Authorization'] = `Bearer ${localStorage.getItem('songlab_token')}`;
            }
            if (this.anonId) {
                headers['X-Anon-Id'] = this.anonId;
            }

            // API 경로는 런타임 API_URL을 사용
            // Prevent double '/api' when API_URL already contains '/api'
            let apiEndpoint;
            if (this.API_URL && this.API_URL.endsWith('/api')) {
                apiEndpoint = `${this.API_URL}/analyze`;
            } else {
                apiEndpoint = `${this.API_URL}/api/analyze`;
            }
            const finalHeaders = Object.assign({}, headers, { 'Accept': 'application/json' });

            const response = await fetch(apiEndpoint, {
                method: 'POST',
                body: formData,
                headers: finalHeaders
            });

            const result = await response.json();

            if (response.ok) {
                if (result.status === 'analysis_completed') {
                    this.currentSession = result.session_id;
                    this.showAnalysisComplete();
                } else if ((result.status === 'success' || result.success) && result.mbti) {
                    this.currentSession = result.session_id || null;
                    this.showAnalysisComplete();
                    this.displayFinalResult(result);
                } else {
                    this.showError(this.resolveErrorMessage(result.detail, '분석 중 오류가 발생했습니다.'));
                }
            } else {
                this.showError(this.resolveErrorMessage(result.detail, '분석 실패'));
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
                this.showError(this.resolveErrorMessage(result.detail, '결과 조회 실패'));
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
                this.showError(this.resolveErrorMessage(result.detail, '최종 결과를 불러올 수 없습니다.'));
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
        this.displayYoutubeVideos(result.youtube_videos || []);

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

    // 유튜브 추천 표시
    displayYoutubeVideos(videos) {
        const section = document.getElementById('youtube-section');
        const list = document.getElementById('youtube-list');
        if (!section || !list) return;

        list.innerHTML = '';

        if (!videos || videos.length === 0) {
            section.classList.add('hidden');
            return;
        }

        videos.slice(0, 6).forEach(video => {
            const card = document.createElement('div');
            card.className = 'youtube-card';

            const thumbnail = document.createElement('img');
            thumbnail.className = 'youtube-thumbnail';
            // Validate thumbnail URL - fallback to YouTube default if invalid or unresolved
            try {
                const thumbUrl = video.thumbnail || `https://i.ytimg.com/vi/${video.videoId}/hqdefault.jpg`;
                const parsed = new URL(thumbUrl);
                // basic host check (avoid placeholder or bad hostnames)
                if (!parsed.hostname) throw new Error('invalid host');
                thumbnail.src = thumbUrl;
            } catch (e) {
                thumbnail.src = `https://i.ytimg.com/vi/${video.videoId}/hqdefault.jpg`;
            }
            thumbnail.alt = video.title || 'YouTube video thumbnail';
            card.appendChild(thumbnail);

            const meta = document.createElement('div');
            meta.className = 'youtube-meta';

            const title = document.createElement('div');
            title.className = 'youtube-title';
            title.textContent = video.title || 'YouTube 영상';
            meta.appendChild(title);

            if (video.channelTitle) {
                const channel = document.createElement('div');
                channel.className = 'youtube-channel';
                channel.textContent = video.channelTitle;
                meta.appendChild(channel);
            }

            const link = document.createElement('a');
            link.className = 'youtube-link';
            link.href = video.url || `https://www.youtube.com/watch?v=${video.videoId}`;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = 'YouTube에서 보기';
            meta.appendChild(link);

            card.appendChild(meta);
            list.appendChild(card);
        });

        section.classList.remove('hidden');
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
    // Authentication removed - app will operate without user login
    }

    // OAuth URL 로드
    async loadAuthUrls() {
    // Authentication removed - skip loading OAuth URLs
    }

    // Authentication functions removed

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

        const youtubeSection = document.getElementById('youtube-section');
        if (youtubeSection) {
            youtubeSection.classList.add('hidden');
        }
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
    resolveErrorMessage(detail, fallback) {
        if (!detail) return fallback;
        if (typeof detail === 'string') return detail;
        if (detail.message) return detail.message;
        if (detail.error) return detail.error;
        return fallback;
    }

    showError(message) {
        alert(`❌ ${message}`);
    }

    // 성공 메시지 표시
    showSuccess(message) {
        alert(`✅ ${message}`);
    }
}

// OAuth callback handling removed

// 앱 초기화
document.addEventListener('DOMContentLoaded', () => {
    // Initialize app (authentication removed)
    window.songLabApp = new SongLabApp();
});

// Service worker registration removed (PWA disabled)

// Minimal navigation and mock behaviors
document.addEventListener('DOMContentLoaded', function(){
  const start = document.getElementById('start-record');
  if(start){
    start.addEventListener('click', ()=>{
      alert('녹음을 시작합니다. (실제 녹음 기능은 데모에서 동작하지 않습니다)');
      // In real app, redirect to a recorder UI or start recording flow
      window.location.href = 'result.html';
    });
  }

  // Mock populate result values if on result page
  if(document.getElementById('brightness')){
    document.getElementById('brightness').textContent = '72';
    document.getElementById('thickness').textContent = '55';
    document.getElementById('clarity').textContent = '68';
    document.getElementById('power').textContent = '61';
    document.getElementById('video-list').innerHTML = '<ul><li><a href="https://www.youtube.com/" target="_blank">발성 연습 영상 1</a></li><li><a href="https://www.youtube.com/" target="_blank">호흡 연습 영상 2</a></li></ul>';
  }
});
