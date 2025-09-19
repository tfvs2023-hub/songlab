"""
Recording Environment Detector
녹음 환경 자동 감지 (폰 vs 스튜디오)
"""

import numpy as np
import scipy.signal as signal
import soundfile as sf
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')


class RecordingDetector:
    """
    녹음 환경 자동 감지기
    폰 녹음 vs 스튜디오 녹음 판별
    """
    
    def __init__(self):
        self.phone_threshold = 0.3  # 0.3 이하면 폰, 이상이면 스튜디오
        
    def detect_environment(self, audio_data: bytes) -> Dict:
        """
        녹음 환경 감지 메인 함수
        """
        try:
            import io
            audio, sr = sf.read(io.BytesIO(audio_data))
            
            # Mono 변환
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            # 다양한 지표 계산
            indicators = self._compute_indicators(audio, sr)
            
            # 종합 점수 계산 (0: 확실한 폰, 1: 확실한 스튜디오)
            studio_score = self._compute_studio_score(indicators)
            
            # 환경 판별
            if studio_score >= 0.7:
                environment = "studio"
                confidence = studio_score
                reason = "고품질 오디오 특성 감지"
            elif studio_score <= 0.3:
                environment = "phone"
                confidence = 1 - studio_score
                reason = "모바일 녹음 특성 감지"
            else:
                environment = "unknown"
                confidence = 0.5
                reason = "애매한 품질 특성"
            
            return {
                'environment': environment,
                'confidence': float(confidence),
                'studio_score': float(studio_score),
                'reason': reason,
                'indicators': indicators
            }
            
        except Exception as e:
            return {
                'environment': 'unknown',
                'confidence': 0.0,
                'studio_score': 0.5,
                'reason': f'분석 오류: {str(e)}',
                'indicators': {}
            }
    
    def _compute_indicators(self, audio: np.ndarray, sr: int) -> Dict:
        """환경 판별 지표들 계산"""
        indicators = {}
        
        # 1. 주파수 대역폭 분석
        indicators['bandwidth'] = self._analyze_bandwidth(audio, sr)
        
        # 2. SNR 추정
        indicators['snr'] = self._estimate_snr(audio, sr)
        
        # 3. 클리핑 검출
        indicators['clipping'] = self._detect_clipping(audio)
        
        # 4. 압축 아티팩트
        indicators['compression_artifacts'] = self._detect_compression(audio, sr)
        
        # 5. 마이크 특성 분석
        indicators['mic_characteristics'] = self._analyze_mic_response(audio, sr)
        
        # 6. AGC 감지
        indicators['agc_detected'] = self._detect_agc(audio, sr)
        
        # 7. 배경 노이즈 패턴
        indicators['noise_pattern'] = self._analyze_noise_pattern(audio, sr)
        
        # 8. Dynamic Range
        indicators['dynamic_range'] = self._compute_dynamic_range(audio)
        
        return indicators
    
    def _analyze_bandwidth(self, audio: np.ndarray, sr: int) -> float:
        """유효 대역폭 분석 (0: 좁음(폰), 1: 넓음(스튜디오))"""
        # 스펙트럼 계산
        f, psd = signal.welch(audio, sr, nperseg=2048)
        
        # 90% 에너지가 포함되는 대역폭 계산
        cumsum_energy = np.cumsum(psd)
        total_energy = cumsum_energy[-1]
        
        # 5%와 95% 지점 찾기
        low_idx = np.where(cumsum_energy >= 0.05 * total_energy)[0][0]
        high_idx = np.where(cumsum_energy >= 0.95 * total_energy)[0][0]
        
        bandwidth = f[high_idx] - f[low_idx]
        
        # 정규화 (0-1)
        # 폰: ~6kHz, 스튜디오: ~15kHz+
        normalized_bw = np.clip(bandwidth / 15000, 0, 1)
        
        return float(normalized_bw)
    
    def _estimate_snr(self, audio: np.ndarray, sr: int) -> float:
        """SNR 추정 (0: 낮음(폰), 1: 높음(스튜디오))"""
        # 주파수 도메인에서 SNR 추정
        f, psd = signal.welch(audio, sr, nperseg=2048)
        
        # 고주파 노이즈 대역 (>10kHz)
        noise_band = psd[f > 10000]
        
        if len(noise_band) > 0:
            noise_floor = np.median(noise_band)
            # 주요 신호 대역 (100Hz-8kHz)
            signal_band = psd[(f > 100) & (f < 8000)]
            signal_power = np.mean(signal_band)
            
            snr_db = 10 * np.log10(signal_power / (noise_floor + 1e-10))
            
            # 정규화 (0-1)
            # 폰: ~15-25dB, 스튜디오: ~35-50dB+
            normalized_snr = np.clip((snr_db - 15) / 35, 0, 1)
        else:
            normalized_snr = 0.5
        
        return float(normalized_snr)
    
    def _detect_clipping(self, audio: np.ndarray) -> float:
        """클리핑 감지 (0: 많음(폰 가능성), 1: 적음(스튜디오))"""
        clipping_ratio = np.sum(np.abs(audio) > 0.98) / len(audio)
        
        # 클리핑이 적을수록 스튜디오 가능성 높음
        return float(1 - np.clip(clipping_ratio * 100, 0, 1))
    
    def _detect_compression(self, audio: np.ndarray, sr: int) -> float:
        """압축 아티팩트 감지 (0: 많음(폰), 1: 적음(스튜디오))"""
        # 고주파 롤오프 분석
        f, psd = signal.welch(audio, sr, nperseg=2048)
        
        # 6kHz 이후 롤오프 기울기 계산
        high_freq_idx = f > 6000
        if np.sum(high_freq_idx) > 10:
            high_f = f[high_freq_idx]
            high_psd = psd[high_freq_idx]
            
            # 로그 도메인에서 기울기 계산
            log_psd = np.log(high_psd + 1e-10)
            slope = np.polyfit(high_f, log_psd, 1)[0]
            
            # 가파른 롤오프일수록 압축 의심 (폰)
            # 자연스러운 롤오프면 스튜디오
            compression_score = np.clip(-slope / 2, 0, 1)
        else:
            compression_score = 0.5
        
        return float(compression_score)
    
    def _analyze_mic_response(self, audio: np.ndarray, sr: int) -> float:
        """마이크 응답 특성 분석 (0: 폰 마이크, 1: 스튜디오 마이크)"""
        f, psd = signal.welch(audio, sr, nperseg=2048)
        
        # 폰 마이크 특성: 2-4kHz 부스트, 저음 컷
        # 스튜디오 마이크: 더 플랫한 응답
        
        if len(f) > 100:
            # 저음 응답 (80-300Hz)
            low_response = np.mean(psd[(f >= 80) & (f <= 300)])
            
            # 중고음 응답 (2-4kHz)
            mid_high_response = np.mean(psd[(f >= 2000) & (f <= 4000)])
            
            # 고음 응답 (8-15kHz)
            high_response = np.mean(psd[(f >= 8000) & (f <= 15000)])
            
            # 폰 마이크는 중고음이 부스트되고 저음이 약함
            phone_characteristic = mid_high_response / (low_response + 1e-10)
            
            # 스튜디오 마이크는 더 균등한 응답
            studio_characteristic = high_response / (mid_high_response + 1e-10)
            
            # 정규화
            mic_score = np.clip(studio_characteristic / (phone_characteristic + 1e-10), 0, 1)
        else:
            mic_score = 0.5
        
        return float(mic_score)
    
    def _detect_agc(self, audio: np.ndarray, sr: int) -> float:
        """AGC (자동 게인 조절) 감지 (0: AGC 있음(폰), 1: AGC 없음(스튜디오))"""
        # RMS 에너지 변화 분석
        frame_size = int(0.1 * sr)  # 100ms frames
        rms_values = []
        
        for i in range(0, len(audio) - frame_size, frame_size // 2):
            frame = audio[i:i+frame_size]
            rms = np.sqrt(np.mean(frame**2))
            rms_values.append(rms)
        
        if len(rms_values) > 10:
            # AGC가 있으면 RMS 변화가 압축됨
            rms_cv = np.std(rms_values) / (np.mean(rms_values) + 1e-10)
            
            # 자연스러운 변화 vs 압축된 변화
            # 높은 변동성 = 자연스러운 녹음 (스튜디오)
            # 낮은 변동성 = AGC 있음 (폰)
            agc_score = np.clip(rms_cv * 5, 0, 1)
        else:
            agc_score = 0.5
        
        return float(agc_score)
    
    def _analyze_noise_pattern(self, audio: np.ndarray, sr: int) -> float:
        """배경 노이즈 패턴 분석 (0: 폰 노이즈, 1: 스튜디오 노이즈)"""
        # 무음 구간에서 노이즈 분석
        energy = np.abs(audio)
        noise_threshold = np.percentile(energy, 20)  # 하위 20%를 노이즈로 간주
        
        noise_samples = audio[energy < noise_threshold]
        
        if len(noise_samples) > sr * 0.1:  # 최소 0.1초의 노이즈
            # 노이즈의 스펙트럼 특성 분석
            f, noise_psd = signal.welch(noise_samples, sr, nperseg=1024)
            
            # 폰: 주로 고주파 노이즈 + 전자적 노이즈
            # 스튜디오: 더 균등한 노이즈 또는 매우 낮은 노이즈
            
            if len(f) > 50:
                # 저주파 vs 고주파 노이즈 비율
                low_noise = np.mean(noise_psd[f < 1000])
                high_noise = np.mean(noise_psd[f > 5000])
                
                # 스튜디오는 일반적으로 더 낮고 균등한 노이즈
                noise_score = np.clip(low_noise / (high_noise + 1e-10), 0, 1)
            else:
                noise_score = 0.5
        else:
            # 노이즈가 거의 없음 = 스튜디오 가능성
            noise_score = 0.9
        
        return float(noise_score)
    
    def _compute_dynamic_range(self, audio: np.ndarray) -> float:
        """Dynamic Range 계산 (0: 압축됨(폰), 1: 자연스러움(스튜디오))"""
        # Peak vs RMS 비율
        peak = np.max(np.abs(audio))
        rms = np.sqrt(np.mean(audio**2))
        
        if rms > 0:
            dr_db = 20 * np.log10(peak / rms)
            # 정규화 (10dB = 압축됨, 25dB+ = 자연스러움)
            dr_score = np.clip((dr_db - 10) / 15, 0, 1)
        else:
            dr_score = 0.0
        
        return float(dr_score)
    
    def _compute_studio_score(self, indicators: Dict) -> float:
        """종합 스튜디오 점수 계산"""
        # 가중 평균
        weights = {
            'bandwidth': 0.2,
            'snr': 0.25,
            'clipping': 0.1,
            'compression_artifacts': 0.15,
            'mic_characteristics': 0.1,
            'agc_detected': 0.1,
            'noise_pattern': 0.05,
            'dynamic_range': 0.05
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for indicator, weight in weights.items():
            if indicator in indicators:
                value = indicators[indicator]
                if not np.isnan(value) and not np.isinf(value):
                    weighted_sum += value * weight
                    total_weight += weight
        
        if total_weight > 0:
            studio_score = weighted_sum / total_weight
        else:
            studio_score = 0.5
        
        return np.clip(studio_score, 0, 1)