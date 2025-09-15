"""
정확한 보컬 분석기 - MR 분리 보컬 최적화
모든 설정을 스펙에 맞게 교정
"""

import numpy as np
import librosa
import soundfile as sf
import parselmouth
from scipy import signal
from scipy.stats import linregress
import subprocess
import tempfile
import os
import warnings
warnings.filterwarnings('ignore')

class CorrectedVocalAnalyzer:
    def __init__(self):
        # 파라미터 프리셋
        self.sr = 22050  # 22.05 kHz 고정
        self.n_fft = 2048
        self.hop_length = 256
        self.window = 'hann'
        
        # 대역 제한
        self.hp_freq = 80    # High-pass
        self.lp_freq = 8000  # Low-pass (브릭월)
        
        # Tilt 분석 대역
        self.tilt_low = 300
        self.tilt_high = 3000
        
        # Mel 필터
        self.n_mels = 40
        self.mel_low = 80
        self.mel_high = 8000
        
        # VAD 설정
        self.vad_win_ms = 20
        self.vad_hop_ms = 10
        self.voiced_threshold = 0.2  # 유성 비율 20% 미만이면 Low confidence
        
        # F0 설정 (성별별)
        self.f0_settings = {
            'male': {'floor': 60, 'ceiling': 450},
            'female': {'floor': 100, 'ceiling': 700}
        }
        
        # 정규화 통계 (z-score용)
        self.reference_stats = {
            'cpp_med': {'mean': 15.0, 'std': 5.0},
            'hnr_med': {'mean': 12.0, 'std': 4.0},
            'tilt_med': {'mean': -8.0, 'std': 3.0},
            'flatness_med': {'mean': 0.3, 'std': 0.1},
            'f0conf_mean': {'mean': 0.8, 'std': 0.15},
            'entropy_norm_med': {'mean': 0.6, 'std': 0.1},
            'h1h2_med': {'mean': 5.0, 'std': 3.0}
        }
    
    def analyze_vocal_file(self, audio_file, gender='auto', source_hint='unknown'):
        """메인 분석 함수"""
        
        filename = os.path.basename(audio_file)
        print(f"\n🎤 {filename} 분석 중...")
        
        try:
            # 0. 공통 전처리
            audio, voiced_segments = self.preprocess_audio(audio_file)
            if audio is None:
                return {'error': '전처리 실패'}
            
            # 유성 비율 체크
            voiced_ratio = sum(len(seg) for seg in voiced_segments) / len(audio)
            low_confidence = voiced_ratio < self.voiced_threshold
            
            print(f"   📊 길이: {len(audio)/self.sr:.1f}초, 유성 비율: {voiced_ratio:.1%}")
            if low_confidence:
                print("   ⚠️ Low confidence (유성 비율 < 20%)")
            
            # 성별 자동 추정
            if gender == 'auto':
                gender = self.estimate_gender(audio)
            
            # 1. F0 분석 (교정된 Praat 설정)
            f0_result = self.analyze_f0_corrected(audio, gender)
            
            # 2. 경량 지표 세트 추출
            features = self.extract_light_features(audio, voiced_segments, f0_result)
            
            # 3. 소스별 보정
            features_corrected = self.apply_source_correction(features, source_hint)
            
            # 4. 최종 스코어링
            clarity_score, grade, characteristics = self.calculate_final_clarity(features_corrected, low_confidence)
            
            result = {
                'clarity_score': clarity_score,
                'grade': grade,
                'characteristics': characteristics,
                'voiced_ratio': voiced_ratio,
                'low_confidence': low_confidence,
                'gender': gender,
                'raw_features': features_corrected
            }
            
            print(f"   ✅ 선명도: {clarity_score:.1f} ({grade})")
            print(f"   🏷️ 특징: {', '.join(characteristics)}")
            
            return result
            
        except Exception as e:
            print(f"   ❌ 분석 오류: {e}")
            return {'error': str(e)}
    
    def preprocess_audio(self, audio_file):
        """0. 공통 전처리"""
        try:
            # M4A 변환 (필요시)
            if audio_file.endswith('.m4a'):
                wav_path = self.convert_m4a_simple(audio_file)
                if wav_path:
                    audio, sr = sf.read(wav_path)
                    os.unlink(wav_path)
                else:
                    audio, sr = sf.read(audio_file)
            else:
                audio, sr = sf.read(audio_file)
            
            # 스테레오 → 모노
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            # 22.05 kHz 리샘플링
            if sr != self.sr:
                audio = librosa.resample(y=audio, orig_sr=sr, target_sr=self.sr)
            
            # 라우드니스 매칭 (-23 LUFS) - 간단 버전
            rms = np.sqrt(np.mean(audio ** 2))
            if rms > 0:
                target_rms = 0.1  # 대략 -23 LUFS 상당
                audio = audio * (target_rms / rms)
            
            # 대역 제한 (80-8000 Hz 브릭월 FIR)
            nyquist = self.sr / 2
            low = self.hp_freq / nyquist
            high = self.lp_freq / nyquist
            
            b, a = signal.butter(4, [low, high], btype='band')
            audio = signal.filtfilt(b, a, audio)
            
            # 간단 VAD (유성 구간 검출)
            voiced_segments = self.simple_vad(audio)
            
            return audio, voiced_segments
            
        except Exception as e:
            print(f"전처리 오류: {e}")
            return None, []
    
    def convert_m4a_simple(self, m4a_path):
        """M4A → WAV 변환"""
        try:
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav_path = temp_wav.name
            temp_wav.close()
            
            cmd = [
                'ffmpeg', '-i', m4a_path,
                '-ac', '1', '-ar', str(self.sr),
                temp_wav_path, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return temp_wav_path if result.returncode == 0 else None
            
        except:
            return None
    
    def simple_vad(self, audio):
        """간단 VAD (에너지 + ZCR 하이브리드)"""
        try:
            win_samples = int(self.vad_win_ms * self.sr / 1000)
            hop_samples = int(self.vad_hop_ms * self.sr / 1000)
            
            voiced_segments = []
            
            for i in range(0, len(audio) - win_samples, hop_samples):
                frame = audio[i:i + win_samples]
                
                # 에너지
                energy = np.sum(frame ** 2)
                
                # ZCR
                zcr = np.sum(np.diff(np.sign(frame)) != 0) / len(frame)
                
                # 간단한 임계값 (경험적)
                if energy > 0.001 and zcr < 0.3:  # 유성음 조건
                    voiced_segments.append((i, i + win_samples))
            
            return voiced_segments
            
        except:
            return [(0, len(audio))]  # 실패시 전체 구간
    
    def estimate_gender(self, audio):
        """성별 자동 추정"""
        try:
            # 간단한 F0 추정으로 성별 판단
            f0 = librosa.yin(audio, fmin=60, fmax=700, frame_length=2048)
            valid_f0 = f0[f0 > 0]
            
            if len(valid_f0) > 0:
                median_f0 = np.median(valid_f0)
                return 'female' if median_f0 > 180 else 'male'
            else:
                return 'male'  # 기본값
                
        except:
            return 'male'
    
    def analyze_f0_corrected(self, audio, gender):
        """1. 교정된 F0 분석"""
        try:
            # Praat 설정
            settings = self.f0_settings[gender]
            
            # Praat Sound 객체 생성
            sound = parselmouth.Sound(audio, self.sr)
            
            # 교정된 파라미터로 F0 추출
            pitch = sound.to_pitch(
                time_step=0.01,
                pitch_floor=settings['floor'],
                pitch_ceiling=settings['ceiling'],
                voicing_threshold=0.6,
                octave_cost=0.01,
                octave_jump_cost=0.35,
                voiced_unvoiced_cost=0.2
            )
            
            # 결과 추출
            f0_values = pitch.selected_array['frequency']
            voiced_frames = f0_values > 0
            confidence = np.sum(voiced_frames) / len(f0_values) if len(f0_values) > 0 else 0
            
            # 고신뢰도 프레임만 (conf ≥ 0.7)
            high_conf_mask = confidence >= 0.7
            
            return {
                'f0_values': f0_values,
                'voiced_frames': voiced_frames,
                'confidence': confidence,
                'high_conf_mask': high_conf_mask,
                'pitch_object': pitch
            }
            
        except Exception as e:
            print(f"F0 분석 오류: {e}")
            # 백업: pYIN 사용
            try:
                settings = self.f0_settings[gender]
                f0 = librosa.yin(audio, 
                                fmin=settings['floor'], 
                                fmax=settings['ceiling'], 
                                frame_length=2048)
                voiced_frames = f0 > 0
                confidence = np.sum(voiced_frames) / len(f0) if len(f0) > 0 else 0
                
                return {
                    'f0_values': f0,
                    'voiced_frames': voiced_frames,
                    'confidence': confidence,
                    'high_conf_mask': confidence >= 0.7,
                    'pitch_object': None
                }
            except:
                return {
                    'f0_values': np.array([]),
                    'voiced_frames': np.array([]),
                    'confidence': 0.0,
                    'high_conf_mask': False,
                    'pitch_object': None
                }
    
    def extract_light_features(self, audio, voiced_segments, f0_result):
        """2. 경량 지표 세트 추출"""
        features = {}
        
        try:
            # 유성 구간만 추출
            voiced_audio = []
            for start, end in voiced_segments:
                voiced_audio.extend(audio[start:end])
            
            if len(voiced_audio) == 0:
                voiced_audio = audio  # 백업
            
            voiced_audio = np.array(voiced_audio)
            
            # STFT 계산
            stft = librosa.stft(voiced_audio, n_fft=self.n_fft, hop_length=self.hop_length, window=self.window)
            magnitude = np.abs(stft)
            power = magnitude ** 2
            freqs = librosa.fft_frequencies(sr=self.sr, n_fft=self.n_fft)
            
            # 1. CPP (Cepstral Peak Prominence)
            features['cpp_med'] = self.calculate_cpp_light(voiced_audio)
            
            # 2. HNR (Harmonics-to-Noise Ratio)
            features['hnr_med'] = self.calculate_hnr_corrected(voiced_audio, f0_result)
            
            # 3. Spectral Tilt (300-3000 Hz, 안전 레시피)
            features['tilt_med'] = self.calculate_spectral_tilt_safe(power, freqs)
            
            # 4. Spectral Flatness (median, 80-8000 Hz)
            features['flatness_med'] = self.calculate_spectral_flatness_safe(power, freqs)
            
            # 5. F0 confidence (mean)
            features['f0conf_mean'] = f0_result['confidence']
            
            # 6. H1-H2
            features['h1h2_med'] = self.calculate_h1h2(voiced_audio, f0_result)
            
            # 7. Mel-entropy (H_norm)
            features['entropy_norm_med'] = self.calculate_mel_entropy_norm(voiced_audio)
            
            return features
            
        except Exception as e:
            print(f"특징 추출 오류: {e}")
            # 기본값 반환
            return {
                'cpp_med': 10.0,
                'hnr_med': 10.0,
                'tilt_med': -5.0,
                'flatness_med': 0.3,
                'f0conf_mean': 0.5,
                'h1h2_med': 5.0,
                'entropy_norm_med': 0.6
            }
    
    def calculate_cpp_light(self, audio):
        """CPP 계산 (경량 버전)"""
        try:
            # 케프스트럼 계산
            spectrum = np.fft.rfft(audio)
            log_spectrum = np.log(np.abs(spectrum) + 1e-10)
            cepstrum = np.fft.irfft(log_spectrum)
            
            # 2-20ms 범위에서 피크 찾기
            start_idx = int(0.002 * self.sr)  # 2ms
            end_idx = int(0.02 * self.sr)     # 20ms
            
            if end_idx < len(cepstrum):
                peak_value = np.max(cepstrum[start_idx:end_idx])
                baseline = np.mean(cepstrum[start_idx:end_idx])
                cpp = peak_value - baseline
                return max(0, min(30, cpp * 1000))  # 0-30 범위로 스케일링
            else:
                return 10.0
                
        except:
            return 10.0
    
    def calculate_hnr_corrected(self, audio, f0_result):
        """HNR 계산 (교정된 버전)"""
        try:
            if f0_result['pitch_object'] is not None:
                # Praat으로 HNR 계산
                harmonicity = f0_result['pitch_object'].to_harmonicity()
                hnr_values = harmonicity.values
                hnr_values = hnr_values[~np.isnan(hnr_values)]
                
                if len(hnr_values) > 0:
                    return np.median(hnr_values)
            
            # 백업: 자기상관 기반 HNR
            autocorr = np.correlate(audio, audio, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            if len(autocorr) > self.sr//50:
                max_corr = np.max(autocorr[self.sr//400:self.sr//50])
                noise_level = 1 - max_corr / (autocorr[0] + 1e-10)
                hnr = 10 * np.log10((max_corr + 1e-10) / (noise_level + 1e-10))
                return max(0, min(30, hnr))
            else:
                return 10.0
                
        except:
            return 10.0
    
    def calculate_spectral_tilt_safe(self, power, freqs):
        """Spectral Tilt 계산 (안전 레시피)"""
        try:
            # 300-3000 Hz 대역 마스크
            mask = (freqs >= self.tilt_low) & (freqs <= self.tilt_high)
            
            if np.sum(mask) < 10:
                return -5.0
            
            freq_range = freqs[mask]
            
            # 프레임별 기울기 계산
            tilt_values = []
            
            for frame_idx in range(power.shape[1]):
                power_frame = power[mask, frame_idx]
                
                if np.sum(power_frame) > 0:
                    log_power = 10 * np.log10(power_frame + 1e-10)
                    log_freq = np.log10(freq_range + 1e-10)
                    
                    slope, _, _, _, _ = linregress(log_freq, log_power)
                    tilt_db_oct = slope * np.log10(2)  # dB/octave
                    tilt_values.append(tilt_db_oct)
            
            # Median 반환
            if len(tilt_values) > 0:
                return np.median(tilt_values)
            else:
                return -5.0
                
        except:
            return -5.0
    
    def calculate_spectral_flatness_safe(self, power, freqs):
        """Spectral Flatness 계산 (80-8000 Hz)"""
        try:
            mask = (freqs >= self.mel_low) & (freqs <= self.mel_high)
            
            if np.sum(mask) < 10:
                return 0.3
            
            flatness_values = []
            
            for frame_idx in range(power.shape[1]):
                power_frame = power[mask, frame_idx]
                
                if np.sum(power_frame) > 0:
                    geometric_mean = np.exp(np.mean(np.log(power_frame + 1e-10)))
                    arithmetic_mean = np.mean(power_frame)
                    flatness = geometric_mean / (arithmetic_mean + 1e-10)
                    flatness_values.append(flatness)
            
            if len(flatness_values) > 0:
                return np.median(flatness_values)
            else:
                return 0.3
                
        except:
            return 0.3
    
    def calculate_h1h2(self, audio, f0_result):
        """H1-H2 계산"""
        try:
            if len(f0_result['f0_values']) == 0:
                return 5.0
            
            # F0가 있는 프레임들의 H1-H2 계산
            valid_f0 = f0_result['f0_values'][f0_result['voiced_frames']]
            
            if len(valid_f0) == 0:
                return 5.0
            
            median_f0 = np.median(valid_f0)
            
            # 스펙트럼에서 H1, H2 추정
            spectrum = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1/self.sr)
            magnitude = np.abs(spectrum)
            
            # H1 (기본 주파수) 에너지
            h1_idx = np.argmin(np.abs(freqs - median_f0))
            h1_energy = magnitude[h1_idx]
            
            # H2 (2배 주파수) 에너지
            h2_freq = median_f0 * 2
            h2_idx = np.argmin(np.abs(freqs - h2_freq))
            h2_energy = magnitude[h2_idx]
            
            if h2_energy > 0:
                h1h2 = 20 * np.log10((h1_energy + 1e-10) / (h2_energy + 1e-10))
                return np.clip(h1h2, -10, 20)
            else:
                return 5.0
                
        except:
            return 5.0
    
    def calculate_mel_entropy_norm(self, audio):
        """Mel-entropy 계산 (정규화)"""
        try:
            # Mel 필터뱅크
            mel_filters = librosa.filters.mel(sr=self.sr, n_fft=self.n_fft, 
                                             n_mels=self.n_mels, 
                                             fmin=self.mel_low, 
                                             fmax=self.mel_high)
            
            # STFT
            stft = librosa.stft(audio, n_fft=self.n_fft, hop_length=self.hop_length)
            power = np.abs(stft) ** 2
            
            # Mel 스펙트로그램
            mel_spec = mel_filters @ power
            
            entropy_values = []
            
            for frame_idx in range(mel_spec.shape[1]):
                mel_frame = mel_spec[:, frame_idx]
                
                if np.sum(mel_frame) > 0:
                    # 확률 분포로 정규화
                    p = mel_frame / np.sum(mel_frame)
                    # 엔트로피 계산
                    h = -np.sum(p * np.log(p + 1e-10))
                    # 정규화 (0-1 범위)
                    h_norm = h / np.log(self.n_mels)
                    entropy_values.append(h_norm)
            
            if len(entropy_values) > 0:
                return np.median(entropy_values)
            else:
                return 0.6
                
        except:
            return 0.6
    
    def apply_source_correction(self, features, source_hint):
        """3. 소스별 보정 (지표 단위로만)"""
        corrected = features.copy()
        
        if source_hint == 'kakaotalk':
            corrected['hnr_med'] -= 1.0
            corrected['tilt_med'] += 0.5
            corrected['flatness_med'] += 0.02
        elif source_hint == 'amr_nb':
            corrected['hnr_med'] -= 2.0
            corrected['entropy_norm_med'] += 0.05
        
        return corrected
    
    def calculate_final_clarity(self, features, low_confidence):
        """4. 최종 스코어링"""
        try:
            # Z-score 정규화
            z_scores = {}
            for key, value in features.items():
                if key in self.reference_stats:
                    stats = self.reference_stats[key]
                    z_scores[key] = (value - stats['mean']) / stats['std']
                else:
                    z_scores[key] = 0
            
            # Clarity 원시 점수
            clarity_raw = (
                z_scores['cpp_med'] + 
                z_scores['hnr_med'] - 
                z_scores['tilt_med'] - 
                z_scores['flatness_med'] +
                0.5 * z_scores['f0conf_mean'] - 
                0.5 * z_scores['entropy_norm_med'] - 
                0.5 * z_scores['h1h2_med']
            )
            
            # 시그모이드 정규화
            clarity_sigmoid = 100 * (1 / (1 + np.exp(-clarity_raw / 2)))
            
            # Cap 규칙 (가성/숨섞임)
            cap = 100
            if features['h1h2_med'] > 8 or features['hnr_med'] < 10:
                cap = 60
            
            clarity_score = min(clarity_sigmoid, cap)
            
            # 등급 매기기
            if clarity_score >= 70:
                grade = "High"
            elif clarity_score >= 40:
                grade = "Medium"
            else:
                grade = "Low"
            
            # 특징 태그
            characteristics = []
            if features['tilt_med'] > -6:
                characteristics.append("밝음")
            else:
                characteristics.append("어두움")
            
            if features['hnr_med'] > 15:
                characteristics.append("깨끗함")
            elif features['hnr_med'] < 10:
                characteristics.append("거침")
            else:
                characteristics.append("보통")
            
            if features['h1h2_med'] > 8:
                characteristics.append("숨섞임")
            
            if low_confidence:
                characteristics.append("Low confidence")
            
            return clarity_score, grade, characteristics
            
        except Exception as e:
            print(f"스코어링 오류: {e}")
            return 50.0, "Medium", ["분석 실패"]

def test_corrected_analyzer():
    """교정된 분석기 테스트"""
    
    print("=" * 70)
    print("🎤 교정된 보컬 분석기 테스트")
    print("=" * 70)
    
    test_files = [
        (r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a", "kakaotalk"),
        (r"C:\Users\user\Desktop\vocals_extracted\로이킴_로이킴 - As Is_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav", "unknown")
    ]
    
    analyzer = CorrectedVocalAnalyzer()
    results = []
    
    for audio_file, source_hint in test_files:
        if os.path.exists(audio_file):
            result = analyzer.analyze_vocal_file(audio_file, source_hint=source_hint)
            if 'clarity_score' in result:
                filename = os.path.basename(audio_file)
                results.append({
                    'file': filename[:20],
                    'score': result['clarity_score'],
                    'grade': result['grade'],
                    'characteristics': ', '.join(result['characteristics']),
                    'voiced_ratio': result['voiced_ratio']
                })
    
    # 최종 결과
    if results:
        print("\n" + "=" * 80)
        print("🏆 최종 결과")
        print("=" * 80)
        
        print(f"\n{'파일':<22} | {'선명도':<6} | {'등급':<6} | {'유성비율':<8} | {'특징'}")
        print("-" * 80)
        
        for r in results:
            print(f"{r['file']:<22} | {r['score']:<6.1f} | {r['grade']:<6} | {r['voiced_ratio']:<8.1%} | {r['characteristics']}")
        
        print(f"\n💡 예상 순서: 김범수 > kakaotalk > 로이킴 > 가성")
        sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
        actual_order = " > ".join([r['file'][:10] for r in sorted_results])
        print(f"💡 실제 순서: {actual_order}")

if __name__ == "__main__":
    test_corrected_analyzer()