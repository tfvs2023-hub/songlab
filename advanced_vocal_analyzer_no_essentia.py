"""
Advanced 4-Axis Vocal Analysis System (Essentia 없이)
- Brightness (밝기): Torchaudio spectral features + Praat formants
- Thickness (음색 두께): Torchaudio harmonic analysis
- Adduction (성대 내전): Praat HNR + Jitter/Shimmer  
- SPL (음압): Torchaudio RMS + PyLoudnorm LUFS
"""

import numpy as np
import torch
import torchaudio
import torchaudio.transforms as T
import torchaudio.functional as F
from typing import Dict, Tuple, Optional
import parselmouth
from parselmouth.praat import call
import pyloudnorm as pyln
import soundfile as sf
import warnings
warnings.filterwarnings('ignore')


class AdvancedVocalAnalyzerNoEssentia:
    """
    고급 4축 보컬 분석기 (Essentia 제외 버전)
    """
    
    def __init__(self, sample_rate: int = 22050):
        self.sr = sample_rate
        self.setup_processors()
    
    def setup_processors(self):
        """Torchaudio 프로세서 초기화"""
        
        # Torchaudio transforms
        self.mel_transform = T.MelSpectrogram(
            sample_rate=self.sr,
            n_fft=2048,
            n_mels=128,
            hop_length=512
        )
        
        self.spectral_centroid = T.SpectralCentroid(sample_rate=self.sr)
        
        # Loudness meter
        self.loudness_meter = pyln.Meter(self.sr)
    
    def analyze_audio(self, audio_data: bytes) -> Dict[str, float]:
        """
        4축 보컬 분석 메인 함수
        """
        try:
            # 오디오 로드 및 전처리
            audio = self._load_and_preprocess(audio_data)
            
            # 4축 분석 수행 (Essentia 없이)
            brightness = self._analyze_brightness_torch(audio)
            thickness = self._analyze_thickness_torch(audio)
            adduction = self._analyze_adduction(audio)
            spl = self._analyze_spl(audio)
            
            # 성별 추론 및 잠재적 고음력 계산
            gender = self._infer_gender(brightness, thickness, spl, audio)
            potential_high_note = self._calculate_potential_high_note(gender, brightness, thickness, adduction, spl)
            
            return {
                'brightness': float(brightness),
                'thickness': float(thickness), 
                'adduction': float(adduction),
                'spl': float(spl),
                'gender': gender,
                'potential_high_note': potential_high_note
            }
            
        except Exception as e:
            print(f"Analysis error: {e}")
            return self._get_fallback_scores()
    
    def _load_and_preprocess(self, audio_data: bytes) -> np.ndarray:
        """오디오 데이터 로드 및 고급 전처리"""
        
        import io
        audio_buffer = io.BytesIO(audio_data)
        audio, sr = sf.read(audio_buffer)
        
        # 모노 변환
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # 리샘플링
        if sr != self.sr:
            import resampy
            audio = resampy.resample(audio, sr, self.sr)
        
        # 1. 노이즈 제거 (Spectral Subtraction)
        audio = self._remove_noise(audio)
        
        # 2. 무음 구간 제거 (Trim Silence)
        audio = self._trim_silence(audio, top_db=20)
        
        # 3. MR 제거 (Vocal Isolation)
        audio = self._remove_mr(audio)
        
        # 4. 정규화
        audio = audio / (np.max(np.abs(audio)) + 1e-8)
        
        return audio
    
    def _remove_noise(self, audio: np.ndarray) -> np.ndarray:
        """스펙트럼 차감법으로 노이즈 제거"""
        try:
            # STFT 변환
            audio_tensor = torch.FloatTensor(audio)
            stft = torch.stft(
                audio_tensor,
                n_fft=2048,
                hop_length=512,
                window=torch.hann_window(2048),
                return_complex=True
            )
            
            magnitude = torch.abs(stft)
            phase = torch.angle(stft)
            
            # 노이즈 추정 (첫 0.5초를 노이즈로 가정)
            noise_frames = int(0.5 * self.sr / 512)  # 0.5초에 해당하는 프레임 수
            if magnitude.shape[1] > noise_frames:
                noise_spectrum = torch.mean(magnitude[:, :noise_frames], dim=1, keepdim=True)
                
                # 스펙트럼 차감 (alpha=2.0)
                clean_magnitude = magnitude - 2.0 * noise_spectrum
                clean_magnitude = torch.maximum(clean_magnitude, 0.1 * magnitude)  # 과도한 차감 방지
            else:
                clean_magnitude = magnitude
            
            # 역변환
            clean_stft = clean_magnitude * torch.exp(1j * phase)
            clean_audio = torch.istft(
                clean_stft,
                n_fft=2048,
                hop_length=512,
                window=torch.hann_window(2048)
            )
            
            return clean_audio.numpy()
            
        except Exception as e:
            print(f"Noise removal error: {e}")
            return audio
    
    def _trim_silence(self, audio: np.ndarray, top_db: int = 20) -> np.ndarray:
        """무음 구간 제거 (에너지 기반)"""
        try:
            frame_length = 2048
            hop_length = 512
            
            # 프레임별 에너지 계산
            energy = []
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i+frame_length]
                frame_energy = np.sum(frame**2)
                energy.append(frame_energy)
            
            if len(energy) == 0:
                return audio
                
            energy = np.array(energy)
            energy_db = 10 * np.log10(energy + 1e-10)
            
            # 임계값 계산
            max_energy_db = np.max(energy_db)
            threshold = max_energy_db - top_db
            
            # 유효한 프레임 찾기
            valid_frames = energy_db > threshold
            if not np.any(valid_frames):
                return audio
            
            # 시작과 끝 지점 계산
            valid_indices = np.where(valid_frames)[0]
            start_frame = valid_indices[0]
            end_frame = valid_indices[-1]
            
            start_sample = start_frame * hop_length
            end_sample = min((end_frame + 1) * hop_length + frame_length, len(audio))
            
            return audio[start_sample:end_sample]
            
        except Exception as e:
            print(f"Silence trimming error: {e}")
            return audio
    
    def _remove_mr(self, audio: np.ndarray) -> np.ndarray:
        """MR 제거 (보컬 분리) - Center Channel Extraction"""
        try:
            # 스테레오가 아니면 그대로 반환
            if len(audio.shape) == 1:
                return audio
                
            # 이미 모노로 변환된 상태이므로, 
            # 여기서는 주파수 도메인에서 보컬 강조 처리
            
            # STFT 변환
            audio_tensor = torch.FloatTensor(audio)
            stft = torch.stft(
                audio_tensor,
                n_fft=2048,
                hop_length=512,
                window=torch.hann_window(2048),
                return_complex=True
            )
            
            magnitude = torch.abs(stft)
            phase = torch.angle(stft)
            
            # 보컬 주파수 대역 강조 (80Hz - 8000Hz)
            freqs = torch.linspace(0, self.sr // 2, magnitude.shape[0])
            vocal_mask = torch.ones_like(magnitude)
            
            # 80Hz 이하 약화 (저음 악기)
            low_freq_mask = freqs < 80
            vocal_mask[low_freq_mask, :] *= 0.3
            
            # 8000Hz 이상 약화 (고음 노이즈)
            high_freq_mask = freqs > 8000
            vocal_mask[high_freq_mask, :] *= 0.5
            
            # 보컬 주파수 대역 (200-2000Hz) 강조
            vocal_freq_mask = (freqs >= 200) & (freqs <= 2000)
            vocal_mask[vocal_freq_mask, :] *= 1.2
            
            # 마스크 적용
            enhanced_magnitude = magnitude * vocal_mask
            
            # 역변환
            enhanced_stft = enhanced_magnitude * torch.exp(1j * phase)
            enhanced_audio = torch.istft(
                enhanced_stft,
                n_fft=2048,
                hop_length=512,
                window=torch.hann_window(2048)
            )
            
            return enhanced_audio.numpy()
            
        except Exception as e:
            print(f"MR removal error: {e}")
            return audio
    
    def _analyze_brightness_torch(self, audio: np.ndarray) -> float:
        """
        밝기 분석: Torchaudio + Praat
        """
        try:
            # 1. Torchaudio - Spectral Centroid
            audio_tensor = torch.FloatTensor(audio).unsqueeze(0)
            
            # 더 안전한 spectral centroid 계산
            window = torch.hann_window(2048)
            stft = torch.stft(
                audio_tensor.squeeze(), 
                n_fft=2048, 
                hop_length=512,
                window=window,
                return_complex=True
            )
            magnitude = torch.abs(stft)
            
            # Spectral centroid 수동 계산
            freqs = torch.linspace(0, self.sr // 2, magnitude.shape[0])
            freqs = freqs.unsqueeze(1)  # [freq_bins, 1]
            
            # 각 프레임별 spectral centroid 계산
            centroids = []
            for t in range(magnitude.shape[1]):
                mag_frame = magnitude[:, t]
                if mag_frame.sum() > 1e-10:  # 무음이 아닌 경우만
                    centroid = torch.sum(freqs.squeeze() * mag_frame) / torch.sum(mag_frame)
                    if not torch.isnan(centroid) and not torch.isinf(centroid):
                        centroids.append(centroid.item())
            
            if centroids:
                centroid_mean = np.mean(centroids)
            else:
                centroid_mean = 2000  # 기본값
            
            # Spectral centroid 정규화 (1000-4000Hz 기준)
            spectral_brightness = (centroid_mean - 2500) / 25
            
            # 2. Praat - Formant Analysis
            sound = parselmouth.Sound(audio, sampling_frequency=self.sr)
            
            try:
                formant = sound.to_formant_burg()
                duration = sound.duration
                mid_time = duration / 2
                
                f1 = call(formant, "Get value at time", 1, mid_time, "Hertz", "Linear")
                f2 = call(formant, "Get value at time", 2, mid_time, "Hertz", "Linear")
                
                # NaN 체크
                if (not np.isnan(f1) and not np.isnan(f2) and 
                    f1 > 0 and f2 > 0 and f1 < 2000 and f2 < 4000):
                    formant_brightness = (f2 / f1 - 1.5) * 50
                else:
                    formant_brightness = 0
            except:
                formant_brightness = 0
            
            # 가중 평균
            brightness = 0.6 * spectral_brightness + 0.4 * formant_brightness
            
            # NaN 체크 및 범위 제한
            if np.isnan(brightness) or np.isinf(brightness):
                brightness = 0.0
            
            return float(np.clip(brightness, -100, 100))
            
        except Exception as e:
            print(f"Brightness analysis error: {e}")
            return 0.0
    
    def _analyze_thickness_torch(self, audio: np.ndarray) -> float:
        """
        음색 두께 분석: Torchaudio 기반
        """
        try:
            audio_tensor = torch.FloatTensor(audio)
            
            # 1. Mel spectrogram energy distribution
            mel_spec = self.mel_transform(audio_tensor)
            
            # 저주파 vs 고주파 에너지 비율
            low_freq_energy = torch.mean(mel_spec[:32, :])
            high_freq_energy = torch.mean(mel_spec[64:, :])
            freq_balance = (low_freq_energy - high_freq_energy) * 30
            
            # 2. Spectral rolloff (Torchaudio)
            stft = torch.stft(
                audio_tensor, 
                n_fft=2048, 
                hop_length=512, 
                return_complex=True
            )
            magnitude = torch.abs(stft)
            
            # Spectral complexity 추정
            spectral_variance = torch.var(magnitude, dim=0).mean()
            complexity_score = torch.log(1 + spectral_variance * 10).item() * 20
            
            # 3. Harmonic 추정 (FFT 피크 분석)
            fft = torch.fft.rfft(audio_tensor)
            fft_mag = torch.abs(fft)
            
            # 상위 피크 찾기
            peaks, _ = torch.topk(fft_mag, 20)
            harmonic_richness = (peaks[1:].mean() / (peaks[0] + 1e-8)).item() * 50
            
            # 가중 평균
            thickness = 0.4 * freq_balance + 0.3 * complexity_score + 0.3 * harmonic_richness
            
            return float(np.clip(thickness, -100, 100))
            
        except Exception as e:
            print(f"Thickness analysis error: {e}")
            return 0.0
    
    def _analyze_adduction(self, audio: np.ndarray) -> float:
        """
        성대 내전 정도 분석: Praat (핵심!)
        """
        try:
            sound = parselmouth.Sound(audio, sampling_frequency=self.sr)
            
            # 1. HNR (Harmonic-to-Noise Ratio)
            harmonicity = sound.to_harmonicity()
            hnr_values = harmonicity.values
            hnr_mean = np.mean(hnr_values[~np.isnan(hnr_values)])
            hnr_score = min((hnr_mean - 5) * 10, 50)
            
            # 2. Jitter
            try:
                pitch = sound.to_pitch()
                jitter_local = call(pitch, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
                jitter_score = max(50 - jitter_local * 1000, -50)
            except:
                jitter_score = 0
            
            # 3. Shimmer
            try:
                shimmer_local = call(sound, "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
                shimmer_score = max(50 - shimmer_local * 100, -50)
            except:
                shimmer_score = 0
            
            # 가중 평균
            adduction = 0.5 * hnr_score + 0.25 * jitter_score + 0.25 * shimmer_score
            
            return float(np.clip(adduction, -100, 100))
            
        except Exception as e:
            print(f"Adduction analysis error: {e}")
            return 0.0
    
    def _analyze_spl(self, audio: np.ndarray) -> float:
        """
        음압/소리 세기 분석: RMS + LUFS
        """
        try:
            # 1. RMS Energy
            rms_energy = np.sqrt(np.mean(audio**2))
            rms_db = 20 * np.log10(rms_energy + 1e-8)
            rms_score = (rms_db + 60) * 100 / 60
            
            # 2. LUFS
            try:
                if len(audio) / self.sr >= 0.4:
                    lufs = self.loudness_meter.integrated_loudness(audio)
                    lufs_score = (lufs + 50) * 100 / 40
                else:
                    lufs_score = rms_score
            except:
                lufs_score = rms_score
            
            # 3. Dynamic Range
            peak_level = 20 * np.log10(np.max(np.abs(audio)) + 1e-8)
            dynamic_range = peak_level - rms_db
            dynamic_score = min(dynamic_range * 5, 50)
            
            # 가중 평균
            spl = 0.6 * rms_score + 0.3 * lufs_score + 0.1 * dynamic_score
            
            return float(np.clip(spl, -100, 100))
            
        except Exception as e:
            print(f"SPL analysis error: {e}")
            return 0.0
    
    def _infer_gender(self, brightness: float, thickness: float, spl: float, audio: np.ndarray) -> str:
        """성별 추론"""
        try:
            sound = parselmouth.Sound(audio, sampling_frequency=self.sr)
            pitch = sound.to_pitch()
            f0_values = pitch.selected_array['frequency']
            f0_values = f0_values[f0_values != 0]
            
            if len(f0_values) > 0:
                avg_f0 = np.mean(f0_values)
                
                if avg_f0 > 180:
                    return 'female'
                elif avg_f0 < 130:
                    return 'male'
                else:
                    gender_score = 0
                    if brightness > 10: gender_score += 1
                    if thickness < 0: gender_score += 1  
                    if spl < 20: gender_score += 1
                    return 'female' if gender_score >= 2 else 'male'
            else:
                gender_score = 0
                if brightness > 10: gender_score += 1
                if thickness < 0: gender_score += 1
                if spl < 20: gender_score += 1
                return 'female' if gender_score >= 2 else 'male'
                
        except:
            return 'unknown'
    
    def _calculate_potential_high_note(self, gender: str, brightness: float, thickness: float, adduction: float, spl: float) -> str:
        """성별별 잠재적 고음력 계산 (대중가요 기준)"""
        
        if gender == 'male':
            base_notes = ['A4', 'A#4', 'B4', 'C5', 'C#5', 'D5', 'D#5', 'E5', 'F5']
            base_idx = 4  # C#5 기준
        elif gender == 'female':
            base_notes = ['C5', 'C#5', 'D5', 'D#5', 'E5', 'F5', 'F#5', 'G5', 'G#5', 'A5']
            base_idx = 5  # F5 기준
        else:
            return 'E5'
        
        adjustment = 0
        
        # 밝기
        if brightness > 50:
            adjustment += 3
        elif brightness > 20:
            adjustment += 2
        elif brightness > 0:
            adjustment += 1
        elif brightness < -40:
            adjustment -= 2
        
        # 두께
        if -10 <= thickness <= 20:
            adjustment += 1
        elif thickness < -30:
            adjustment += 2
        elif thickness > 50:
            adjustment -= 2
            
        # 성대 내전 (가장 중요)
        if adduction > 60:
            adjustment += 3
        elif adduction > 30:
            adjustment += 2
        elif adduction > 0:
            adjustment += 1
        elif adduction < -30:
            adjustment -= 2
            
        # SPL
        if 30 <= spl <= 70:
            adjustment += 1
        elif spl > 80:
            adjustment -= 1
        elif spl < 10:
            adjustment -= 1
        
        final_idx = max(0, min(len(base_notes) - 1, base_idx + adjustment))
        
        return base_notes[final_idx]

    def _get_fallback_scores(self) -> Dict[str, float]:
        """분석 실패시 기본값"""
        return {
            'brightness': 0.0,
            'thickness': 0.0,
            'adduction': 0.0,
            'spl': 0.0,
            'gender': 'unknown',
            'potential_high_note': 'E5'
        }


# 테스트
if __name__ == "__main__":
    analyzer = AdvancedVocalAnalyzerNoEssentia()
    print("Advanced Vocal Analyzer (No Essentia) - Ready!")