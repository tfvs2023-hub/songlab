"""
Advanced Voice Analyzer - 기존 VoiceAnalyzer 호환 버전
4축 고급 보컬 분석 시스템 (Praat + Torchaudio + PyLoudnorm)
기존 API 호환성 유지하면서 분석 정확도 대폭 향상
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
import io
import warnings
warnings.filterwarnings('ignore')


class VoiceAnalyzer:
    """
    고급 음성 분석기 - 기존 API 호환성 유지
    """
    
    def __init__(self):
        self.sr = 22050  # 고품질 분석을 위해 22050Hz 사용
        self.setup_processors()
        
        # 기존 API 호환을 위한 매핑
        self.axis_mapping = {
            'brightness': 'brightness',
            'thickness': 'thickness', 
            'clarity': 'adduction',  # clarity → adduction (성대내전)
            'power': 'spl'           # power → spl (음압)
        }
    
    def setup_processors(self):
        """프로세서 초기화"""
        self.mel_transform = T.MelSpectrogram(
            sample_rate=self.sr,
            n_fft=2048,
            n_mels=128,
            hop_length=512
        )
        
        self.spectral_centroid = T.SpectralCentroid(sample_rate=self.sr)
        self.loudness_meter = pyln.Meter(self.sr)
    
    def analyze_audio(self, audio_data):
        """
        기존 API 호환 메인 분석 함수
        Returns: dict with brightness, thickness, clarity, power, potential_high_note
        """
        try:
            # 고급 4축 분석 수행
            advanced_results = self._analyze_audio_advanced(audio_data)
            
            # 기존 API 형식으로 변환 + 고급 기능 추가
            legacy_results = {
                'brightness': advanced_results['brightness'],
                'thickness': advanced_results['thickness'],
                'clarity': advanced_results['adduction'],    # adduction → clarity 
                'power': advanced_results['spl'],            # spl → power
                'potential_high_note': advanced_results['potential_high_note'],  # 고음 잠재력 추가
                'gender': advanced_results['gender']         # 성별 정보도 추가
            }
            
            return legacy_results
            
        except Exception as e:
            print(f"Analysis error: {e}")
            return self._get_fallback_scores()
    
    def _analyze_audio_advanced(self, audio_data: bytes) -> Dict[str, float]:
        """고급 4축 분석 (내부 함수)"""
        try:
            # 오디오 로드 및 고급 전처리
            audio = self._load_and_preprocess(audio_data)
            
            # 4축 분석
            brightness = self._analyze_brightness(audio)
            thickness = self._analyze_thickness(audio)
            adduction = self._analyze_adduction(audio)
            spl = self._analyze_spl(audio)
            
            # 성별 추론 및 잠재적 고음력
            gender = self._infer_gender(brightness, thickness, spl, audio)
            potential_high_note = self._calculate_potential_high_note(
                gender, brightness, thickness, adduction, spl
            )
            
            return {
                'brightness': float(brightness),
                'thickness': float(thickness),
                'adduction': float(adduction),
                'spl': float(spl),
                'gender': gender,
                'potential_high_note': potential_high_note
            }
            
        except Exception as e:
            print(f"Advanced analysis error: {e}")
            return self._get_fallback_advanced()
    
    def _load_and_preprocess(self, audio_data: bytes) -> np.ndarray:
        """고급 전처리 파이프라인"""
        
        audio_buffer = io.BytesIO(audio_data)
        audio, sr = sf.read(audio_buffer)
        
        # 모노 변환
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # 리샘플링
        if sr != self.sr:
            import resampy
            audio = resampy.resample(audio, sr, self.sr)
        
        # 1. 노이즈 제거
        audio = self._remove_noise(audio)
        
        # 2. 무음 구간 제거
        audio = self._trim_silence(audio, top_db=20)
        
        # 3. MR 제거 (보컬 강조)
        audio = self._remove_mr(audio)
        
        # 4. 정규화
        audio = audio / (np.max(np.abs(audio)) + 1e-8)
        
        return audio
    
    def _remove_noise(self, audio: np.ndarray) -> np.ndarray:
        """스펙트럼 차감법 노이즈 제거"""
        try:
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
            
            # 첫 0.5초를 노이즈로 추정
            noise_frames = int(0.5 * self.sr / 512)
            if magnitude.shape[1] > noise_frames:
                noise_spectrum = torch.mean(magnitude[:, :noise_frames], dim=1, keepdim=True)
                clean_magnitude = magnitude - 2.0 * noise_spectrum
                clean_magnitude = torch.maximum(clean_magnitude, 0.1 * magnitude)
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
        """에너지 기반 무음 제거"""
        try:
            frame_length = 2048
            hop_length = 512
            
            energy = []
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i+frame_length]
                energy.append(np.sum(frame**2))
            
            if len(energy) == 0:
                return audio
                
            energy = np.array(energy)
            energy_db = 10 * np.log10(energy + 1e-10)
            
            max_energy_db = np.max(energy_db)
            threshold = max_energy_db - top_db
            
            valid_frames = energy_db > threshold
            if not np.any(valid_frames):
                return audio
            
            valid_indices = np.where(valid_frames)[0]
            start_sample = valid_indices[0] * hop_length
            end_sample = min((valid_indices[-1] + 1) * hop_length + frame_length, len(audio))
            
            return audio[start_sample:end_sample]
            
        except Exception as e:
            print(f"Silence trimming error: {e}")
            return audio
    
    def _remove_mr(self, audio: np.ndarray) -> np.ndarray:
        """MR 제거 - 보컬 주파수 대역 강조"""
        try:
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
            
            freqs = torch.linspace(0, self.sr // 2, magnitude.shape[0])
            vocal_mask = torch.ones_like(magnitude)
            
            # 80Hz 이하 약화 (저음 악기)
            low_freq_mask = freqs < 80
            vocal_mask[low_freq_mask, :] *= 0.3
            
            # 8000Hz 이상 약화
            high_freq_mask = freqs > 8000
            vocal_mask[high_freq_mask, :] *= 0.5
            
            # 보컬 주파수 200-2000Hz 강조
            vocal_freq_mask = (freqs >= 200) & (freqs <= 2000)
            vocal_mask[vocal_freq_mask, :] *= 1.2
            
            enhanced_magnitude = magnitude * vocal_mask
            
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
    
    def _analyze_brightness(self, audio: np.ndarray) -> float:
        """밝기 분석: Spectral centroid + Formant"""
        try:
            audio_tensor = torch.FloatTensor(audio).unsqueeze(0)
            
            # Spectral centroid 계산
            window = torch.hann_window(2048)
            stft = torch.stft(
                audio_tensor.squeeze(),
                n_fft=2048,
                hop_length=512,
                window=window,
                return_complex=True
            )
            magnitude = torch.abs(stft)
            
            freqs = torch.linspace(0, self.sr // 2, magnitude.shape[0])
            
            centroids = []
            for t in range(magnitude.shape[1]):
                mag_frame = magnitude[:, t]
                if mag_frame.sum() > 1e-10:
                    centroid = torch.sum(freqs * mag_frame) / torch.sum(mag_frame)
                    if not torch.isnan(centroid) and not torch.isinf(centroid):
                        centroids.append(centroid.item())
            
            if centroids:
                centroid_mean = np.mean(centroids)
            else:
                centroid_mean = 2000
            
            spectral_brightness = (centroid_mean - 2500) / 25
            
            # Praat 포먼트 분석
            try:
                sound = parselmouth.Sound(audio, sampling_frequency=self.sr)
                formant = sound.to_formant_burg()
                duration = sound.duration
                mid_time = duration / 2
                
                f1 = call(formant, "Get value at time", 1, mid_time, "Hertz", "Linear")
                f2 = call(formant, "Get value at time", 2, mid_time, "Hertz", "Linear")
                
                if (not np.isnan(f1) and not np.isnan(f2) and 
                    f1 > 0 and f2 > 0 and f1 < 2000 and f2 < 4000):
                    formant_brightness = (f2 / f1 - 1.5) * 50
                else:
                    formant_brightness = 0
            except:
                formant_brightness = 0
            
            brightness = 0.6 * spectral_brightness + 0.4 * formant_brightness
            
            if np.isnan(brightness) or np.isinf(brightness):
                brightness = 0.0
            
            return float(np.clip(brightness, -100, 100))
            
        except Exception as e:
            print(f"Brightness analysis error: {e}")
            return 0.0
    
    def _analyze_thickness(self, audio: np.ndarray) -> float:
        """두께 분석: Harmonic richness + Spectral complexity"""
        try:
            audio_tensor = torch.FloatTensor(audio)
            
            # Mel spectrogram energy distribution
            mel_spec = self.mel_transform(audio_tensor)
            low_freq_energy = torch.mean(mel_spec[:32, :])
            high_freq_energy = torch.mean(mel_spec[64:, :])
            freq_balance = (low_freq_energy - high_freq_energy) * 30
            
            # Spectral complexity
            stft = torch.stft(
                audio_tensor,
                n_fft=2048,
                hop_length=512,
                return_complex=True
            )
            magnitude = torch.abs(stft)
            spectral_variance = torch.var(magnitude, dim=0).mean()
            complexity_score = torch.log(1 + spectral_variance * 10).item() * 20
            
            # Harmonic richness
            fft = torch.fft.rfft(audio_tensor)
            fft_mag = torch.abs(fft)
            peaks, _ = torch.topk(fft_mag, 20)
            harmonic_richness = (peaks[1:].mean() / (peaks[0] + 1e-8)).item() * 50
            
            thickness = 0.4 * freq_balance + 0.3 * complexity_score + 0.3 * harmonic_richness
            
            return float(np.clip(thickness, -100, 100))
            
        except Exception as e:
            print(f"Thickness analysis error: {e}")
            return 0.0
    
    def _analyze_adduction(self, audio: np.ndarray) -> float:
        """성대내전 분석: HNR + Jitter + Shimmer"""
        try:
            sound = parselmouth.Sound(audio, sampling_frequency=self.sr)
            
            # HNR (Harmonic-to-Noise Ratio)
            harmonicity = sound.to_harmonicity()
            hnr_values = harmonicity.values
            hnr_mean = np.mean(hnr_values[~np.isnan(hnr_values)])
            hnr_score = np.clip((hnr_mean - 3) * 15, -50, 50)
            
            # Jitter
            try:
                pitch = sound.to_pitch()
                jitter_local = call(pitch, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
                jitter_score = max(50 - jitter_local * 1000, -50)
            except:
                jitter_score = 0
            
            # Shimmer
            try:
                shimmer_local = call(sound, "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
                shimmer_score = max(50 - shimmer_local * 100, -50)
            except:
                shimmer_score = 0
            
            adduction = 0.3 * hnr_score + 0.35 * jitter_score + 0.35 * shimmer_score
            
            return float(np.clip(adduction, -100, 100))
            
        except Exception as e:
            print(f"Adduction analysis error: {e}")
            return 0.0
    
    def _analyze_spl(self, audio: np.ndarray) -> float:
        """음압 분석: RMS + LUFS"""
        try:
            # RMS Energy
            rms_energy = np.sqrt(np.mean(audio**2))
            rms_db = 20 * np.log10(rms_energy + 1e-8)
            rms_score = (rms_db + 60) * 100 / 60
            
            # LUFS
            try:
                if len(audio) / self.sr >= 0.4:
                    lufs = self.loudness_meter.integrated_loudness(audio)
                    lufs_score = (lufs + 50) * 100 / 40
                else:
                    lufs_score = rms_score
            except:
                lufs_score = rms_score
            
            # Dynamic Range
            peak_level = 20 * np.log10(np.max(np.abs(audio)) + 1e-8)
            dynamic_range = peak_level - rms_db
            dynamic_score = min(dynamic_range * 5, 50)
            
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
                return 'unknown'
                
        except:
            return 'unknown'
    
    def generate_mbti_style(self, scores):
        """
        Generate voice type classification based on 4-axis scores
        """
        # Map scores to voice characteristic dimensions
        type_code = ""
        
        # Brightness: B (Bright) vs D (Dark)
        type_code += "B" if scores["brightness"] > 0 else "D"
        
        # Thickness: T (Thick) vs N (thiN)  
        type_code += "T" if scores["thickness"] > 0 else "N"
        
        # Clarity: C (Clear) vs F (Foggy/breathy)
        type_code += "C" if scores["clarity"] > 0 else "F"
        
        # Power: P (Powerful) vs S (Soft)
        type_code += "P" if scores["power"] > 0 else "S"
        
        # Define characteristics for each type
        voice_descriptions = {
            "BTCP": "밝고 두꺼우며 명료하고 파워풀한 보컬 | 팝/뮤지컬형",
            "BTCS": "밝고 두껍고 명료하지만 부드러운 보컬 | 팝/발라드형",
            "BTFP": "밝고 두껍고 숨섞인 파워풀한 보컬 | 소울/블루스형",
            "BTFS": "밝고 두껍고 숨섞인 부드러운 보컬 | R&B/네오소울형",
            "BNCP": "밝고 얇으며 명료하고 파워풀한 보컬 | K-POP/댄스형",
            "BNCS": "밝고 얇고 명료하지만 부드러운 보컬 | 어쿠스틱/포크형",
            "BNFP": "밝고 얇고 숨섞인 파워풀한 보컬 | 인디팝/드림팝형",
            "BNFS": "밝고 얇고 숨섞인 부드러운 보컬 | 보사노바/재즈형",
            "DTCP": "어둡고 두꺼우며 명료하고 파워풀한 보컬 | 록/메탈형",
            "DTCS": "어둡고 두껍고 명료하지만 부드러운 보컬 | 컨트리/블루스형",
            "DTFP": "어둡고 두껍고 숨섞인 파워풀한 보컬 | 힙합/트랩형",
            "DTFS": "어둡고 두껍고 숨섞인 부드러운 보컬 | 재즈/소울형",
            "DNCP": "어둡고 얇으며 명료하고 파워풀한 보컬 | 얼터너티브/인디록형",
            "DNCS": "어둡고 얇고 명료하지만 부드러운 보컬 | 싱어송라이터/포크형",
            "DNFP": "어둡고 얇고 숨섞인 파워풀한 보컬 | 일렉트로닉/신스팝형",
            "DNFS": "어둡고 얇고 숨섞인 부드러운 보컬 | Lo-Fi/칠아웃형"
        }
        
        # Generate training keywords based on lowest score
        # Filter out non-numeric values first
        numeric_scores = {k: v for k, v in scores.items() if isinstance(v, (int, float))}
        lowest_axis = min(numeric_scores, key=numeric_scores.get) if numeric_scores else 'brightness'
        
        keyword_map = {
            "brightness": ["포먼트 조절 보컬 레슨", "공명 훈련 발성법", "밝은 음색 만들기"],
            "thickness": ["성구 전환 연습법", "믹스 보이스 훈련", "음색 두께 조절법"],
            "clarity": ["성대 내전 발성법", "명료한 발음 훈련", "깨끗한 음색 만들기"],
            "power": ["복식 호흡법", "음압 조절 훈련", "파워풀한 발성법"]
        }
        
        return {
            "typeCode": type_code,
            "typeName": type_code,
            "typeIcon": self._get_type_icon(type_code),
            "description": voice_descriptions.get(type_code, "독특한 개성의 보컬"),
            "scores": scores,
            "youtubeKeywords": keyword_map.get(lowest_axis, ["보컬 기초 발성법"])
        }
    
    def _get_type_icon(self, type_code):
        """
        Return emoji icon based on voice type
        """
        icon_map = {
            "B": "🌟", "D": "🌙",  # Bright vs Dark
            "T": "🎸", "N": "🎹",  # Thick vs thiN
            "C": "🎯", "F": "💫",  # Clear vs Foggy
            "P": "⚡", "S": "🌊"   # Powerful vs Soft
        }
        # Return icon based on first letter (B/D)
        return icon_map.get(type_code[0], "🎤")
    
    def _calculate_potential_high_note(self, gender: str, brightness: float, thickness: float, adduction: float, spl: float) -> str:
        """잠재적 고음력 계산"""
        
        if gender == 'male':
            base_notes = ['A4', 'A#4', 'B4', 'C5', 'C#5', 'D5', 'D#5', 'E5', 'F5']
            base_idx = 4  # C#5
        elif gender == 'female':
            base_notes = ['C5', 'C#5', 'D5', 'D#5', 'E5', 'F5', 'F#5', 'G5', 'G#5', 'A5']
            base_idx = 5  # F5
        else:
            return 'E5'
        
        adjustment = 0
        
        if brightness > 50: adjustment += 3
        elif brightness > 20: adjustment += 2
        elif brightness > 0: adjustment += 1
        elif brightness < -40: adjustment -= 2
        
        if -10 <= thickness <= 20: adjustment += 1
        elif thickness < -30: adjustment += 2
        elif thickness > 50: adjustment -= 2
        
        if adduction > 60: adjustment += 3
        elif adduction > 30: adjustment += 2
        elif adduction > 0: adjustment += 1
        elif adduction < -30: adjustment -= 2
        
        if 30 <= spl <= 70: adjustment += 1
        elif spl > 80: adjustment -= 1
        elif spl < 10: adjustment -= 1
        
        final_idx = max(0, min(len(base_notes) - 1, base_idx + adjustment))
        
        return base_notes[final_idx]
    
    def _get_fallback_scores(self) -> Dict[str, float]:
        """기존 API 호환 기본값"""
        return {
            'brightness': 0.0,
            'thickness': 0.0,
            'clarity': 0.0,
            'power': 0.0
        }
    
    def _get_fallback_advanced(self) -> Dict[str, float]:
        """고급 분석 기본값"""
        return {
            'brightness': 0.0,
            'thickness': 0.0,
            'adduction': 0.0,
            'spl': 0.0,
            'gender': 'unknown',
            'potential_high_note': 'E5'
        }
    
    def get_advanced_results(self, audio_data):
        """고급 분석 결과 직접 접근 (새 기능)"""
        return self._analyze_audio_advanced(audio_data)


# 기존 호환성 확인
if __name__ == "__main__":
    analyzer = VoiceAnalyzer()
    print("Advanced Voice Analyzer - 기존 API 호환 완료!")
    print("새 기능: get_advanced_results() 메서드로 고급 분석 가능")