import librosa
import numpy as np
import crepe
from scipy import signal
from typing import Dict, Tuple, List, Optional
import warnings
warnings.filterwarnings('ignore')

class VocalAnalyzer:
    """
    CREPE + 딥러닝 기반 고정밀 음성 분석 엔진
    4축 보컬 MBTI 분석: Brightness, Thickness, Clarity, Power
    """
    
    def __init__(self):
        self.sample_rate = 22050
        self.hop_length = 512
        self.n_fft = 2048
        
    def analyze_audio(self, audio_path: str) -> Dict:
        """
        메인 분석 함수
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            Dict: 완전한 분석 결과
        """
        try:
            # 1. 오디오 로드 및 전처리 (30초 제한)
            audio_data, sr = self.load_and_preprocess(audio_path)
            
            # 2. 기본 음향 특성 추출
            features = self.extract_acoustic_features(audio_data, sr)
            
            # 3. CREPE 기반 고정밀 피치 분석
            pitch_features = self.extract_pitch_features(audio_data, sr)
            
            # 4. 4축 MBTI 점수 계산
            mbti_scores = self.calculate_mbti_scores(features, pitch_features)
            
            # 5. 음역대 분석
            vocal_range = self.analyze_vocal_range(pitch_features)
            
            # 6. 최종 결과 생성
            result = self.generate_result(mbti_scores, vocal_range, features)
            
            return result
            
        except Exception as e:
            return {
                'error': True,
                'message': f'분석 중 오류 발생: {str(e)}',
                'mbti': self.get_default_result()
            }
    
    def load_and_preprocess(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """고급 보컬 특화 전처리"""
        # librosa로 로드 (30초 제한으로 속도 최적화)
        audio, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True, duration=30)
        
        # 1. DC 성분 제거
        audio = audio - np.mean(audio)
        
        # 2. 고주파 노이즈 제거 (8kHz 로우패스 필터)
        from scipy import signal
        nyquist = sr // 2
        low_cutoff = 8000 / nyquist
        b, a = signal.butter(5, low_cutoff, btype='low')
        audio = signal.filtfilt(b, a, audio)
        
        # 3. 정규화
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio)) * 0.95
            
        return audio, sr
    
    def extract_acoustic_features(self, audio: np.ndarray, sr: int) -> Dict:
        """기본 음향 특성 추출"""
        # STFT 계산
        stft = librosa.stft(audio, n_fft=self.n_fft, hop_length=self.hop_length)
        magnitude = np.abs(stft)
        
        # 스펙트럴 특성들
        features = {
            'stft_magnitude': magnitude,
            'spectral_centroids': librosa.feature.spectral_centroid(y=audio, sr=sr)[0],
            'spectral_bandwidth': librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0],
            'spectral_rolloff': librosa.feature.spectral_rolloff(y=audio, sr=sr)[0],
            'zero_crossing_rate': librosa.feature.zero_crossing_rate(audio)[0],
            'rms_energy': librosa.feature.rms(y=audio)[0],
            'mfcc': librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13),
            'chroma': librosa.feature.chroma_stft(S=magnitude, sr=sr),
        }
        
        # 하모닉/퍼커시브 분리
        harmonic, percussive = librosa.effects.hpss(audio)
        features['harmonic'] = harmonic
        features['percussive'] = percussive
        
        return features
    
    def extract_pitch_features(self, audio: np.ndarray, sr: int) -> Dict:
        """CREPE 기반 고정밀 피치 분석"""
        # 오디오 길이 제한 (30초)
        max_length = 30 * sr
        if len(audio) > max_length:
            audio = audio[:max_length]
        
        # CREPE로 피치 추출 (최적화: small 모델 사용)
        time, frequency, confidence, activation = crepe.predict(
            audio, sr, 
            model_capacity='small',  # 속도 최적화
            viterbi=False,          # 속도 최적화
            step_size=50            # 50ms 간격
        )
        
        # 신뢰도 기반 필터링 (0.7 이상)
        valid_indices = confidence > 0.7
        valid_frequencies = frequency[valid_indices]
        valid_confidences = confidence[valid_indices]
        valid_times = time[valid_indices]
        
        pitch_features = {}
        
        if len(valid_frequencies) > 0:
            # 기본 피치 통계
            pitch_features['fundamental_freq'] = np.mean(valid_frequencies)
            pitch_features['pitch_std'] = np.std(valid_frequencies)
            pitch_features['pitch_range'] = np.max(valid_frequencies) - np.min(valid_frequencies)
            pitch_features['avg_confidence'] = np.mean(valid_confidences)
            
            # 피치 안정성 (변동계수)
            if pitch_features['fundamental_freq'] > 0:
                pitch_features['pitch_stability'] = 1 - (pitch_features['pitch_std'] / pitch_features['fundamental_freq'])
            else:
                pitch_features['pitch_stability'] = 0
                
            # 비브라토 감지
            pitch_features['vibrato_rate'] = self.detect_vibrato(valid_frequencies, valid_times)
            
        else:
            # 유효한 피치가 없는 경우 기본값
            pitch_features = {
                'fundamental_freq': 200,
                'pitch_std': 50,
                'pitch_range': 100,
                'avg_confidence': 0.3,
                'pitch_stability': 0.3,
                'vibrato_rate': 0
            }
            
        pitch_features['raw_frequency'] = frequency
        pitch_features['raw_confidence'] = confidence
        pitch_features['raw_time'] = time
        
        return pitch_features
    
    def detect_vibrato(self, frequencies: np.ndarray, times: np.ndarray) -> float:
        """비브라토 감지"""
        if len(frequencies) < 10:
            return 0
            
        # 주파수 변화율 계산
        freq_diff = np.diff(frequencies)
        time_diff = np.diff(times)
        
        # 진동 주기 분석
        vibrato_candidates = []
        for i in range(1, len(freq_diff) - 1):
            if freq_diff[i-1] * freq_diff[i+1] < 0:  # 방향 전환점
                vibrato_candidates.append(time_diff[i])
        
        if len(vibrato_candidates) > 2:
            avg_period = np.mean(vibrato_candidates)
            vibrato_rate = 1 / avg_period if avg_period > 0 else 0
            return min(vibrato_rate, 10)  # 최대 10Hz
        
        return 0
    
    def calculate_mbti_scores(self, features: Dict, pitch_features: Dict) -> Dict:
        """4축 MBTI 점수 계산"""
        
        # 1. BRIGHTNESS (밝기): 고주파 에너지 비율
        brightness = self.calculate_brightness(features['stft_magnitude'], self.sample_rate)
        
        # 2. THICKNESS (두께): 하모닉스 풍부도 + 저주파 에너지
        thickness = self.calculate_thickness(features)
        
        # 3. CLARITY (선명도): 피치 안정성 + 스펙트럴 선명도
        clarity = self.calculate_clarity(pitch_features, features)
        
        # 4. POWER (파워): 음압 레벨 + 다이나믹 레인지
        power = self.calculate_power(features)
        
        return {
            'brightness': brightness,
            'thickness': thickness, 
            'clarity': clarity,
            'power': power
        }
    
    def calculate_brightness(self, magnitude: np.ndarray, sr: int) -> float:
        """밝기 계산: 고주파 에너지 비율"""
        freq_bins = librosa.fft_frequencies(sr=sr, n_fft=self.n_fft)
        
        # 주파수 대역 분할
        low_freq_mask = freq_bins < 2000    # 2kHz 이하
        mid_freq_mask = (freq_bins >= 2000) & (freq_bins < 4000)  # 2-4kHz
        high_freq_mask = freq_bins >= 4000  # 4kHz 이상
        
        # 각 대역별 에너지
        low_energy = np.mean(magnitude[low_freq_mask, :])
        mid_energy = np.mean(magnitude[mid_freq_mask, :])  
        high_energy = np.mean(magnitude[high_freq_mask, :])
        
        total_energy = low_energy + mid_energy + high_energy
        
        if total_energy > 0:
            # 고주파 + 중간주파 비율
            brightness_ratio = (mid_energy + high_energy * 1.5) / total_energy
            brightness = brightness_ratio * 100
        else:
            brightness = 50
            
        return np.clip(brightness, 0, 100)
    
    def calculate_thickness(self, features: Dict) -> float:
        """두께 계산: 하모닉스 풍부도 + 스펙트럴 특성"""
        # 하모닉/퍼커시브 비율
        harmonic_energy = np.sum(np.abs(features['harmonic']))
        total_energy = harmonic_energy + np.sum(np.abs(features['percussive']))
        
        if total_energy > 0:
            harmonic_ratio = harmonic_energy / total_energy
        else:
            harmonic_ratio = 0.5
            
        # 스펙트럴 센트로이드 (낮을수록 두꺼움)
        avg_centroid = np.mean(features['spectral_centroids'])
        centroid_thickness = max(0, (3000 - avg_centroid) / 3000)
        
        # 저주파 에너지 비율
        magnitude = features['stft_magnitude']
        freq_bins = librosa.fft_frequencies(sr=self.sample_rate, n_fft=self.n_fft)
        low_freq_mask = freq_bins < 800  # 800Hz 이하
        
        low_energy = np.mean(magnitude[low_freq_mask, :])
        total_spec_energy = np.mean(magnitude)
        
        if total_spec_energy > 0:
            low_freq_ratio = low_energy / total_spec_energy
        else:
            low_freq_ratio = 0.3
            
        # 종합 두께 점수
        thickness = (harmonic_ratio * 40 + centroid_thickness * 30 + low_freq_ratio * 30) * 1.2
        
        return np.clip(thickness, 0, 100)
    
    def calculate_clarity(self, pitch_features: Dict, features: Dict) -> float:
        """선명도 계산: 피치 안정성 + 스펙트럴 선명도"""
        # 피치 안정성 점수
        pitch_stability = pitch_features.get('pitch_stability', 0) * 100
        
        # 피치 신뢰도
        avg_confidence = pitch_features.get('avg_confidence', 0) * 100
        
        # 스펙트럴 대역폭 (좁을수록 선명)
        avg_bandwidth = np.mean(features['spectral_bandwidth'])
        bandwidth_clarity = max(0, (2500 - avg_bandwidth) / 2500) * 100
        
        # 비브라토 페널티 (비브라토가 강하면 선명도 감소)
        vibrato_penalty = min(30, pitch_features.get('vibrato_rate', 0) * 5)
        
        # 종합 선명도
        clarity = (pitch_stability * 0.4 + avg_confidence * 0.3 + bandwidth_clarity * 0.3) - vibrato_penalty
        
        return np.clip(clarity, 0, 100)
    
    def calculate_power(self, features: Dict) -> float:
        """파워 계산: 음압 레벨 + 다이나믹 레인지"""
        # RMS 에너지
        rms_values = features['rms_energy']
        avg_rms = np.mean(rms_values)
        max_rms = np.max(rms_values)
        
        # 다이나믹 레인지
        dynamic_range = max_rms - np.min(rms_values)
        
        # RMS 기반 파워 (일반적으로 0.01-0.5 범위)
        power_from_rms = min(100, avg_rms * 200)
        
        # 다이나믹 레인지 보너스
        dynamic_bonus = min(25, dynamic_range * 100)
        
        # 스펙트럴 롤오프 (높을수록 파워풀)
        avg_rolloff = np.mean(features['spectral_rolloff'])
        rolloff_bonus = min(20, (avg_rolloff - 2000) / 100)
        
        power = power_from_rms + dynamic_bonus + rolloff_bonus
        
        return np.clip(power, 0, 100)
    
    def analyze_vocal_range(self, pitch_features: Dict) -> Dict:
        """음역대 분석"""
        frequencies = pitch_features.get('raw_frequency', [])
        confidences = pitch_features.get('raw_confidence', [])
        
        # 신뢰도 높은 피치만 사용
        valid_freqs = frequencies[confidences > 0.8]
        
        if len(valid_freqs) > 5:
            # 현재 최고음 (95퍼센타일)
            current_high = np.percentile(valid_freqs, 95)
            current_note = self.freq_to_note(current_high)
            
            # 잠재 최고음 추정 (현재 + 반음 2-3개)
            potential_freq = current_high * (2 ** (2.5/12))  # 반음 2.5개 위
            potential_note = self.freq_to_note(potential_freq)
        else:
            current_note = "C4"
            potential_note = "D4"
            
        return {
            'current': current_note,
            'potential': potential_note
        }
    
    def freq_to_note(self, frequency: float) -> str:
        """주파수를 음표로 변환"""
        if frequency <= 0:
            return "C4"
            
        A4 = 440
        C0 = A4 * np.power(2, -4.75)
        
        if frequency > C0:
            h = round(12 * np.log2(frequency / C0))
            octave = h // 12
            n = h % 12
            notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            return f"{notes[n]}{octave}"
        return "C0"
    
    def generate_result(self, mbti_scores: Dict, vocal_range: Dict, features: Dict) -> Dict:
        """최종 결과 생성"""
        # MBTI 타입 결정
        mbti_code = self.determine_mbti_type(mbti_scores)
        mbti_info = self.get_mbti_info(mbti_code)
        
        # 장단점 분석
        pros_cons = self.analyze_pros_cons(mbti_scores, mbti_code)
        
        # 추천곡 생성
        recommended_songs = self.get_recommended_songs(mbti_code)
        
        return {
            'mbti': {
                'typeCode': mbti_code,
                'typeName': mbti_info['name'],
                'typeIcon': mbti_info['icon'],
                'description': mbti_info['description'],
                'scores': {
                    'brightness': round(mbti_scores['brightness'], 1),
                    'thickness': round(mbti_scores['thickness'], 1),
                    'clarity': round(mbti_scores['clarity'], 1),
                    'power': round(mbti_scores['power'], 1)
                },
                'currentNote': vocal_range['current'],
                'potentialNote': vocal_range['potential'],
                'pros': pros_cons['pros'],
                'cons': pros_cons['cons'],
                'recommendedSongs': recommended_songs
            },
            'success': True
        }
    
    def determine_mbti_type(self, scores: Dict) -> str:
        """4축 점수로 MBTI 타입 결정"""
        code = ''
        code += 'B' if scores['brightness'] > 50 else 'D'  # Bright/Dark
        code += 'T' if scores['thickness'] > 50 else 'L'   # Thick/Light
        code += 'C' if scores['clarity'] > 50 else 'H'     # Clear/Hazy
        code += 'P' if scores['power'] > 50 else 'S'       # Powerful/Soft
        return code
    
    def get_mbti_info(self, mbti_code: str) -> Dict:
        """MBTI 타입별 상세 정보"""
        types = {
            'BTCP': {
                'name': '크리스털 디바',
                'icon': '💎',
                'description': '맑고 강렬한 고음역대의 소유자. 크리스털처럼 투명하면서도 파워풀한 음성으로 듣는 이를 사로잡습니다.'
            },
            'BTCS': {
                'name': '실버 벨',
                'icon': '🔔', 
                'description': '은방울 같은 청아한 음색의 소유자. 맑고 부드러우면서도 풍성한 하모닉스가 특징입니다.'
            },
            'BTHP': {
                'name': '파워 소프라노',
                'icon': '⚡',
                'description': '강력한 고음 발성의 소유자. 오페라 가수 같은 웅장하고 드라마틱한 음성이 특징입니다.'
            },
            'BTHS': {
                'name': '엔젤 보이스', 
                'icon': '👼',
                'description': '천사의 목소리. 부드럽고 따뜻하면서도 신비로운 매력을 지닌 음성입니다.'
            },
            'BLCP': {
                'name': '레이저 보컬',
                'icon': '🔦',
                'description': '정확하고 예리한 음성의 소유자. 레이저처럼 직진하는 명확한 발성이 특징입니다.'
            },
            'BLCS': {
                'name': '클리어 톤',
                'icon': '✨',
                'description': '맑고 투명한 음색의 소유자. 물방울처럼 깨끗하고 순수한 음성이 매력적입니다.'
            },
            'BLHP': {
                'name': '하이 텐션',
                'icon': '🎺',
                'description': '에너지 넘치는 고음역의 소유자. 밝고 활기찬 음성으로 분위기를 끌어올립니다.'
            },
            'BLHS': {
                'name': '스위트 멜로디',
                'icon': '🍯',
                'description': '꿀같이 달콤한 음색의 소유자. 부드럽고 감미로운 음성으로 마음을 따뜻하게 합니다.'
            },
            'DTCP': {
                'name': '메탈 보이스',
                'icon': '🤘',
                'description': '강철 같은 음성의 소유자. 묵직하고 강렬한 저음으로 강한 인상을 남깁니다.'
            },
            'DTCS': {
                'name': '다크 나이트',
                'icon': '🌙',
                'description': '어둠의 기사 같은 신비로운 음성. 깊고 풍부한 저음이 매혹적입니다.'
            },
            'DTHP': {
                'name': '썬더 보컬',
                'icon': '⚡',
                'description': '천둥 같은 폭발적인 음성의 소유자. 강력한 저음으로 압도적인 존재감을 보입니다.'
            },
            'DTHS': {
                'name': '벨벳 보이스',
                'icon': '🎭',
                'description': '벨벳처럼 부드러운 음성의 소유자. 깊고 따뜻한 중저음이 감성적입니다.'
            },
            'DLCP': {
                'name': '샤프 슈터',
                'icon': '🎯',
                'description': '정확한 음정의 저음 전문가. 날카롭고 명확한 저음 발성이 특징입니다.'
            },
            'DLCS': {
                'name': '미스틱 보이스',
                'icon': '🔮',
                'description': '신비로운 음색의 소유자. 몽환적이면서도 깊이 있는 음성이 매력적입니다.'
            },
            'DLHP': {
                'name': '파워 레인저',
                'icon': '💪',
                'description': '강력한 중저음의 소유자. 파워레인저처럼 힘있고 안정감 있는 음성입니다.'
            },
            'DLHS': {
                'name': '허스키 보이스',
                'icon': '🐺',
                'description': '매력적인 허스키톤의 소유자. 거칠면서도 부드러운 독특한 음색이 인상적입니다.'
            }
        }
        
        return types.get(mbti_code, {
            'name': '미분류 보이스',
            'icon': '❓',
            'description': '고유한 특성을 가진 음성입니다.'
        })
    
    def analyze_pros_cons(self, scores: Dict, mbti_code: str) -> Dict:
        """장단점 분석"""
        pros = []
        cons = []
        
        # 점수 기반 장점
        if scores['brightness'] > 70:
            pros.append("밝고 화사한 음색")
        elif scores['brightness'] < 30:
            pros.append("깊이 있는 저음역")
            
        if scores['thickness'] > 70:
            pros.append("풍부한 하모닉스")
        elif scores['thickness'] < 30:
            pros.append("깔끔한 음색")
            
        if scores['clarity'] > 70:
            pros.append("정확한 음정")
        
        if scores['power'] > 70:
            pros.append("강력한 음압")
            
        # 점수 기반 개선점
        if scores['clarity'] < 40:
            cons.append("음정 정확도 연습")
            
        if scores['power'] < 40:
            cons.append("호흡법 및 성량 강화")
            
        if scores['brightness'] < 30 and scores['thickness'] < 30:
            cons.append("음역대 확장 연습")
            
        # 기본값 설정
        if not pros:
            pros = ["개성 있는 음색", "잠재력 풍부"]
        if not cons:
            cons = ["꾸준한 연습", "다양한 장르 도전"]
            
        return {'pros': pros, 'cons': cons}
    
    def get_recommended_songs(self, mbti_code: str) -> List[str]:
        """MBTI별 추천곡"""
        recommendations = {
            'BTCP': ['IU - Through the Night', '태연 - I', 'Adele - Hello'],
            'BTCS': ['이소라 - 제발', '성시경 - 너의 모든 순간', 'John Legend - All of Me'],
            'BTHP': ['소향 - 마음을 드려요', 'Whitney Houston - I Will Always Love You'],
            'BTHS': ['박효신 - 눈의 꽃', 'Celine Dion - My Heart Will Go On'],
            'BLCP': ['아이유 - 밤편지', 'Ed Sheeran - Perfect'],
            'BLCS': ['볼빨간사춘기 - 우주를 줄게', 'Taylor Swift - Cardigan'],
            'BLHP': ['BTS - Dynamite', 'Bruno Mars - Uptown Funk'],
            'BLHS': ['이하이 - 누구 없소', 'Billie Eilish - Ocean Eyes'],
            'DTCP': ['임창정 - 소주 한 잔', 'Johnny Cash - Hurt'],
            'DTCS': ['김범수 - 하루', 'Sam Smith - Stay With Me'],
            'DTHP': ['거미 - You Are My Everything', 'John Legend - Ordinary People'],
            'DTHS': ['나얼 - 기억의 습작', 'Frank Sinatra - Fly Me to the Moon'],
            'DLCP': ['폴킴 - 모든 날, 모든 순간', 'Ed Sheeran - Thinking Out Loud'],
            'DLCS': ['크러쉬 - Beautiful', 'Daniel Caesar - Best Part'],
            'DLHP': ['윤종신 - 좋니', 'John Mayer - Gravity'],
            'DLHS': ['헤이즈 - 돌아오지마', 'Amy Winehouse - Valerie']
        }
        
        return recommendations.get(mbti_code, ['다양한 장르의 곡들을 시도해보세요!'])
    
    def get_default_result(self) -> Dict:
        """오류 시 기본 결과"""
        return {
            'typeCode': 'BLHS',
            'typeName': '스위트 멜로디',  
            'typeIcon': '🍯',
            'description': '분석 중 오류가 발생했습니다. 다시 시도해주세요.',
            'scores': {
                'brightness': 50,
                'thickness': 50,
                'clarity': 50,
                'power': 50
            },
            'currentNote': 'C4',
            'potentialNote': 'D4',
            'pros': ['다시 분석해주세요'],
            'cons': ['파일을 다시 업로드해주세요'],
            'recommendedSongs': ['다시 시도해주세요']
        }