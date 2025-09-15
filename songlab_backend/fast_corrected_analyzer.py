"""
빠른 교정 보컬 분석기 - Parselmouth 없이
"""

import numpy as np
import librosa
import soundfile as sf
from scipy import signal
from scipy.stats import linregress
import subprocess
import tempfile
import os
import warnings
warnings.filterwarnings('ignore')

class FastCorrectedAnalyzer:
    def __init__(self):
        self.sr = 22050
        self.n_fft = 2048
        self.hop_length = 256
        
        # 정규화 통계
        self.reference_stats = {
            'cpp_med': {'mean': 15.0, 'std': 5.0},
            'hnr_med': {'mean': 12.0, 'std': 4.0},
            'tilt_med': {'mean': -8.0, 'std': 3.0},
            'flatness_med': {'mean': 0.3, 'std': 0.1},
            'f0conf_mean': {'mean': 0.8, 'std': 0.15},
            'entropy_norm_med': {'mean': 0.6, 'std': 0.1},
            'h1h2_med': {'mean': 5.0, 'std': 3.0}
        }
    
    def analyze_vocal_file(self, audio_file, source_hint='unknown'):
        """빠른 분석"""
        filename = os.path.basename(audio_file)
        print(f"\n🎤 {filename[:30]} 분석 중...")
        
        try:
            # 전처리
            audio = self.preprocess_fast(audio_file)
            if audio is None:
                return {'error': '전처리 실패'}
            
            print(f"   📊 길이: {len(audio)/self.sr:.1f}초")
            
            # 빠른 특징 추출
            features = self.extract_features_fast(audio)
            
            # 소스 보정
            features = self.apply_source_correction(features, source_hint)
            
            # 스코어링
            score, grade, characteristics = self.calculate_score_fast(features)
            
            result = {
                'clarity_score': score,
                'grade': grade,
                'characteristics': characteristics,
                'raw_features': features
            }
            
            print(f"   ✅ 선명도: {score:.1f} ({grade})")
            print(f"   🏷️ 특징: {', '.join(characteristics)}")
            
            return result
            
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            return {'error': str(e)}
    
    def preprocess_fast(self, audio_file):
        """빠른 전처리"""
        try:
            # M4A 변환
            if audio_file.endswith('.m4a'):
                wav_path = self.convert_m4a_simple(audio_file)
                if wav_path:
                    audio, sr = sf.read(wav_path)
                    os.unlink(wav_path)
                else:
                    audio, sr = sf.read(audio_file)
            else:
                audio, sr = sf.read(audio_file)
            
            # 모노 변환
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            # 22.05kHz 리샘플링
            if sr != self.sr:
                audio = librosa.resample(y=audio, orig_sr=sr, target_sr=self.sr)
            
            # 정규화
            rms = np.sqrt(np.mean(audio ** 2))
            if rms > 0:
                audio = audio * (0.1 / rms)
            
            # 대역 제한 (80-8000Hz)
            nyquist = self.sr / 2
            b, a = signal.butter(4, [80/nyquist, 8000/nyquist], btype='band')
            audio = signal.filtfilt(b, a, audio)
            
            return audio
            
        except Exception as e:
            print(f"전처리 오류: {e}")
            return None
    
    def convert_m4a_simple(self, m4a_path):
        """M4A 변환"""
        try:
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav_path = temp_wav.name
            temp_wav.close()
            
            cmd = ['ffmpeg', '-i', m4a_path, '-ac', '1', '-ar', str(self.sr), temp_wav_path, '-y']
            result = subprocess.run(cmd, capture_output=True, text=True)
            return temp_wav_path if result.returncode == 0 else None
        except:
            return None
    
    def extract_features_fast(self, audio):
        """빠른 특징 추출"""
        features = {}
        
        try:
            # STFT
            stft = librosa.stft(audio, n_fft=self.n_fft, hop_length=self.hop_length)
            magnitude = np.abs(stft)
            power = magnitude ** 2
            freqs = librosa.fft_frequencies(sr=self.sr, n_fft=self.n_fft)
            
            # 1. CPP (간단 버전)
            features['cpp_med'] = self.calculate_cpp_simple(audio)
            
            # 2. HNR (자기상관 기반)
            features['hnr_med'] = self.calculate_hnr_simple(audio)
            
            # 3. Spectral Tilt (300-3000Hz)
            features['tilt_med'] = self.calculate_tilt_simple(power, freqs)
            
            # 4. Spectral Flatness
            features['flatness_med'] = self.calculate_flatness_simple(power, freqs)
            
            # 5. F0 confidence (간단 추정)
            features['f0conf_mean'] = self.estimate_f0_confidence(audio)
            
            # 6. H1-H2 (간단 버전)
            features['h1h2_med'] = self.calculate_h1h2_simple(audio)
            
            # 7. Mel entropy
            features['entropy_norm_med'] = self.calculate_entropy_simple(audio)
            
            return features
            
        except Exception as e:
            print(f"특징 추출 오류: {e}")
            return {
                'cpp_med': 10.0, 'hnr_med': 10.0, 'tilt_med': -5.0,
                'flatness_med': 0.3, 'f0conf_mean': 0.5, 'h1h2_med': 5.0,
                'entropy_norm_med': 0.6
            }
    
    def calculate_cpp_simple(self, audio):
        """간단 CPP"""
        try:
            spectrum = np.fft.rfft(audio)
            log_spectrum = np.log(np.abs(spectrum) + 1e-10)
            cepstrum = np.fft.irfft(log_spectrum)
            
            start_idx = int(0.002 * self.sr)
            end_idx = int(0.02 * self.sr)
            
            if end_idx < len(cepstrum):
                peak = np.max(cepstrum[start_idx:end_idx])
                baseline = np.mean(cepstrum[start_idx:end_idx])
                return max(0, min(30, (peak - baseline) * 1000))
            return 10.0
        except:
            return 10.0
    
    def calculate_hnr_simple(self, audio):
        """간단 HNR"""
        try:
            autocorr = np.correlate(audio, audio, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            if len(autocorr) > self.sr//50:
                max_corr = np.max(autocorr[self.sr//400:self.sr//50])
                noise_level = 1 - max_corr / (autocorr[0] + 1e-10)
                hnr = 10 * np.log10((max_corr + 1e-10) / (noise_level + 1e-10))
                return max(0, min(30, hnr))
            return 10.0
        except:
            return 10.0
    
    def calculate_tilt_simple(self, power, freqs):
        """간단 Spectral Tilt"""
        try:
            mask = (freqs >= 300) & (freqs <= 3000)
            if np.sum(mask) < 10:
                return -5.0
            
            freq_range = freqs[mask]
            power_mean = np.mean(power[mask, :], axis=1)
            
            if np.sum(power_mean) > 0:
                log_power = 10 * np.log10(power_mean + 1e-10)
                log_freq = np.log10(freq_range + 1e-10)
                slope, _, _, _, _ = linregress(log_freq, log_power)
                return slope * np.log10(2)
            return -5.0
        except:
            return -5.0
    
    def calculate_flatness_simple(self, power, freqs):
        """간단 Spectral Flatness"""
        try:
            mask = (freqs >= 80) & (freqs <= 8000)
            if np.sum(mask) < 10:
                return 0.3
            
            power_mean = np.mean(power[mask, :], axis=1)
            if np.sum(power_mean) > 0:
                geometric_mean = np.exp(np.mean(np.log(power_mean + 1e-10)))
                arithmetic_mean = np.mean(power_mean)
                return geometric_mean / (arithmetic_mean + 1e-10)
            return 0.3
        except:
            return 0.3
    
    def estimate_f0_confidence(self, audio):
        """F0 신뢰도 추정"""
        try:
            f0 = librosa.yin(audio, fmin=80, fmax=800, frame_length=2048)
            voiced_frames = f0 > 0
            return np.sum(voiced_frames) / len(f0) if len(f0) > 0 else 0.5
        except:
            return 0.5
    
    def calculate_h1h2_simple(self, audio):
        """간단 H1-H2"""
        try:
            f0 = librosa.yin(audio, fmin=80, fmax=800, frame_length=2048)
            valid_f0 = f0[f0 > 0]
            
            if len(valid_f0) == 0:
                return 5.0
            
            median_f0 = np.median(valid_f0)
            spectrum = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1/self.sr)
            magnitude = np.abs(spectrum)
            
            h1_idx = np.argmin(np.abs(freqs - median_f0))
            h2_idx = np.argmin(np.abs(freqs - median_f0 * 2))
            
            h1_energy = magnitude[h1_idx]
            h2_energy = magnitude[h2_idx]
            
            if h2_energy > 0:
                h1h2 = 20 * np.log10((h1_energy + 1e-10) / (h2_energy + 1e-10))
                return np.clip(h1h2, -10, 20)
            return 5.0
        except:
            return 5.0
    
    def calculate_entropy_simple(self, audio):
        """간단 엔트로피"""
        try:
            mel_spec = librosa.feature.melspectrogram(y=audio, sr=self.sr, n_mels=40, 
                                                     fmin=80, fmax=8000, n_fft=self.n_fft)
            
            entropy_values = []
            for frame_idx in range(mel_spec.shape[1]):
                mel_frame = mel_spec[:, frame_idx]
                if np.sum(mel_frame) > 0:
                    p = mel_frame / np.sum(mel_frame)
                    h = -np.sum(p * np.log(p + 1e-10))
                    h_norm = h / np.log(40)
                    entropy_values.append(h_norm)
            
            return np.median(entropy_values) if entropy_values else 0.6
        except:
            return 0.6
    
    def apply_source_correction(self, features, source_hint):
        """소스 보정"""
        corrected = features.copy()
        
        if source_hint == 'kakaotalk':
            corrected['hnr_med'] -= 1.0
            corrected['tilt_med'] += 0.5
            corrected['flatness_med'] += 0.02
        elif source_hint == 'amr_nb':
            corrected['hnr_med'] -= 2.0
            corrected['entropy_norm_med'] += 0.05
        
        return corrected
    
    def calculate_score_fast(self, features):
        """빠른 스코어링"""
        try:
            # Z-score 정규화
            z_scores = {}
            for key, value in features.items():
                if key in self.reference_stats:
                    stats = self.reference_stats[key]
                    z_scores[key] = (value - stats['mean']) / stats['std']
                else:
                    z_scores[key] = 0
            
            # Clarity 계산
            clarity_raw = (
                z_scores['cpp_med'] + z_scores['hnr_med'] - z_scores['tilt_med'] - 
                z_scores['flatness_med'] + 0.5 * z_scores['f0conf_mean'] - 
                0.5 * z_scores['entropy_norm_med'] - 0.5 * z_scores['h1h2_med']
            )
            
            # 시그모이드 정규화
            clarity_score = 100 * (1 / (1 + np.exp(-clarity_raw / 2)))
            
            # Cap 규칙
            if features['h1h2_med'] > 8 or features['hnr_med'] < 10:
                clarity_score = min(clarity_score, 60)
            
            # 등급
            if clarity_score >= 70:
                grade = "High"
            elif clarity_score >= 40:
                grade = "Medium"
            else:
                grade = "Low"
            
            # 특징
            characteristics = []
            if features['tilt_med'] > -6:
                characteristics.append("밝음")
            else:
                characteristics.append("어두움")
            
            if features['hnr_med'] > 15:
                characteristics.append("깨끗함")
            elif features['hnr_med'] < 10:
                characteristics.append("거침")
            
            if features['h1h2_med'] > 8:
                characteristics.append("숨섞임")
            
            return clarity_score, grade, characteristics
            
        except:
            return 50.0, "Medium", ["분석 실패"]

def test_fast_analyzer():
    """빠른 테스트"""
    print("=" * 60)
    print("🚀 빠른 교정 분석기 테스트")
    print("=" * 60)
    
    test_files = [
        (r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a", "kakaotalk"),
        (r"C:\Users\user\Desktop\vocals_extracted\로이킴_로이킴 - As Is_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav", "unknown")
    ]
    
    analyzer = FastCorrectedAnalyzer()
    results = []
    
    for audio_file, source_hint in test_files:
        if os.path.exists(audio_file):
            result = analyzer.analyze_vocal_file(audio_file, source_hint=source_hint)
            if 'clarity_score' in result:
                filename = os.path.basename(audio_file)
                results.append({
                    'file': filename[:15],
                    'score': result['clarity_score'],
                    'grade': result['grade'],
                    'characteristics': ', '.join(result['characteristics'])
                })
    
    # 결과 출력
    if results:
        print("\n" + "=" * 70)
        print("🏆 최종 결과")
        print("=" * 70)
        
        print(f"\n{'파일':<17} | {'선명도':<6} | {'등급':<6} | {'특징'}")
        print("-" * 60)
        
        for r in results:
            print(f"{r['file']:<17} | {r['score']:<6.1f} | {r['grade']:<6} | {r['characteristics']}")
        
        print(f"\n💡 예상: 김범수 > kakaotalk > 로이킴 > 가성")
        sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
        actual = " > ".join([r['file'][:8] for r in sorted_results])
        print(f"💡 실제: {actual}")

if __name__ == "__main__":
    test_fast_analyzer()