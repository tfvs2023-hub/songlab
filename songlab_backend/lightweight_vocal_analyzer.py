"""
경량 보컬 분석기 - 전역 선명도/밝기/거침 분석
목표한 파이프라인 구현
"""

import numpy as np
import librosa
import soundfile as sf
import subprocess
import tempfile
import os
from scipy import signal
from scipy.stats import linregress
import warnings
warnings.filterwarnings('ignore')

class LightweightVocalAnalyzer:
    def __init__(self):
        self.target_sr = 16000
        self.target_lufs = -23
        self.chunk_duration = 10  # seconds
        self.num_chunks = 12
        self.top_chunks = 6
        
    def preprocess_audio(self, audio_file):
        """전처리: 모노, 16kHz, -23 LUFS 라우드니스 매칭"""
        try:
            print("🔧 전처리 중...")
            
            # 임시 파일 생성
            temp_processed = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_processed_path = temp_processed.name
            temp_processed.close()
            
            # FFmpeg로 전처리
            cmd = [
                'ffmpeg', '-i', audio_file,
                '-ac', '1',  # 모노
                '-ar', '16000',  # 16kHz
                '-af', f'loudnorm=I={self.target_lufs}:TP=-1.5:LRA=11',  # 라우드니스 매칭
                temp_processed_path, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"   ❌ FFmpeg 전처리 실패: {result.stderr}")
                return None
            
            # 처리된 오디오 로드
            audio, sr = sf.read(temp_processed_path)
            os.unlink(temp_processed_path)
            
            print(f"   ✅ 전처리 완료: {len(audio)/sr:.1f}초, {sr}Hz")
            return audio, sr
            
        except Exception as e:
            print(f"   ❌ 전처리 오류: {e}")
            return None, None
    
    def simple_vad(self, audio, sr):
        """간단한 VAD - 유성 구간 탐지"""
        try:
            # Energy + ZCR 하이브리드
            frame_length = int(0.02 * sr)  # 20ms
            hop_length = int(0.01 * sr)    # 10ms
            
            # RMS Energy
            rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Zero Crossing Rate
            zcr = librosa.feature.zero_crossing_rate(audio, frame_length=frame_length, hop_length=hop_length)[0]
            
            # 임계값 기반 유성 판정
            energy_threshold = np.percentile(rms, 30)  # 하위 30% 이상
            zcr_threshold = 0.1  # ZCR 10% 이하
            
            voiced = (rms > energy_threshold) & (zcr < zcr_threshold)
            voiced_ratio = np.mean(voiced)
            
            print(f"   📊 유성 비율: {voiced_ratio:.1%}")
            
            # 신뢰도 플래그
            confidence = "High"
            if voiced_ratio < 0.25:
                confidence = "Low"
                print(f"   ⚠️ 유성 비율이 낮음 - 신뢰도: {confidence}")
            
            return voiced, voiced_ratio, confidence
            
        except Exception as e:
            print(f"   ❌ VAD 오류: {e}")
            return np.ones(len(audio) // hop_length, dtype=bool), 1.0, "Low"
    
    def extract_representative_samples(self, audio, sr, voiced_frames):
        """대표 샘플 추출 - 상위 6개 10초 구간"""
        try:
            print("🎯 대표 샘플 추출 중...")
            
            total_duration = len(audio) / sr
            chunk_samples = self.chunk_duration * sr
            
            chunks = []
            for i in range(self.num_chunks):
                start_time = i * total_duration / self.num_chunks
                start_sample = int(start_time * sr)
                end_sample = min(start_sample + chunk_samples, len(audio))
                
                if end_sample - start_sample < sr:  # 1초 미만이면 스킵
                    continue
                
                chunk_audio = audio[start_sample:end_sample]
                
                # F0 confidence (간단한 자기상관 기반)
                f0_conf = self.calculate_f0_confidence(chunk_audio, sr)
                
                # RMS normalization
                rms_norm = np.sqrt(np.mean(chunk_audio ** 2))
                
                # Score 계산
                score = 0.7 * f0_conf + 0.3 * rms_norm
                
                chunks.append({
                    'start_sample': start_sample,
                    'end_sample': end_sample,
                    'audio': chunk_audio,
                    'f0_conf': f0_conf,
                    'rms_norm': rms_norm,
                    'score': score
                })
            
            # 상위 6개 선택
            chunks.sort(key=lambda x: x['score'], reverse=True)
            top_chunks = chunks[:self.top_chunks]
            
            print(f"   ✅ {len(chunks)}개 중 상위 {len(top_chunks)}개 선택")
            for i, chunk in enumerate(top_chunks[:3]):  # 상위 3개만 출력
                print(f"      #{i+1}: Score={chunk['score']:.3f} (F0={chunk['f0_conf']:.3f}, RMS={chunk['rms_norm']:.3f})")
            
            return top_chunks
            
        except Exception as e:
            print(f"   ❌ 대표 샘플 추출 오류: {e}")
            return []
    
    def calculate_f0_confidence(self, audio, sr):
        """F0 confidence 계산 (간단한 자기상관 기반)"""
        try:
            # 자기상관 계산
            autocorr = np.correlate(audio, audio, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # 피크 찾기 (80-800Hz 범위)
            min_period = sr // 800  # 800Hz
            max_period = sr // 80   # 80Hz
            
            if max_period >= len(autocorr):
                return 0.1
            
            search_range = autocorr[min_period:max_period]
            if len(search_range) == 0:
                return 0.1
            
            max_corr = np.max(search_range)
            normalized_corr = max_corr / autocorr[0] if autocorr[0] > 0 else 0
            
            return max(0.1, min(1.0, normalized_corr))
            
        except Exception as e:
            return 0.1
    
    def extract_light_features(self, chunk_audio, sr):
        """라이트 특징 추출"""
        try:
            features = {}
            
            # 1. CPP (Cepstral Peak Prominence) - 간이 버전
            features['cpp'] = self.calculate_cpp_simple(chunk_audio, sr)
            
            # 2. HNR (Harmonics-to-Noise Ratio) - 자기상관 기반
            features['hnr'] = self.calculate_hnr_simple(chunk_audio, sr)
            
            # 3. Spectral Tilt (300Hz-3kHz 직선 회귀)
            features['spectral_tilt'] = self.calculate_spectral_tilt(chunk_audio, sr)
            
            # 4. Spectral Flatness (0~1)
            features['spectral_flatness'] = self.calculate_spectral_flatness(chunk_audio, sr)
            
            # 5. F0 confidence
            features['f0_confidence'] = self.calculate_f0_confidence(chunk_audio, sr)
            
            # 6. Aperiodicity proxy (간단한 jitter 대용)
            features['aperiodicity'] = self.calculate_aperiodicity_simple(chunk_audio, sr)
            
            # 7. 보조 특징들
            features['spectral_centroid'] = self.calculate_spectral_centroid(chunk_audio, sr)
            features['spectral_rolloff'] = self.calculate_spectral_rolloff(chunk_audio, sr)
            
            return features
            
        except Exception as e:
            print(f"   ❌ 특징 추출 오류: {e}")
            return {}
    
    def calculate_cpp_simple(self, audio, sr):
        """간이 CPP 계산"""
        try:
            # 윈도우 40ms
            frame_length = int(0.04 * sr)
            
            # FFT
            fft = np.fft.fft(audio[:frame_length] * np.hanning(frame_length))
            log_spectrum = np.log(np.abs(fft) + 1e-10)
            
            # Cepstrum
            cepstrum = np.fft.ifft(log_spectrum).real
            
            # 피치 범위에서 피크 찾기 (2-20ms, 50-500Hz)
            min_quefrency = int(sr * 0.002)  # 2ms
            max_quefrency = int(sr * 0.02)   # 20ms
            
            if max_quefrency >= len(cepstrum):
                return 5.0
            
            pitch_cepstrum = cepstrum[min_quefrency:max_quefrency]
            
            if len(pitch_cepstrum) == 0:
                return 5.0
            
            # 최대 피크와 주변 평균의 차이
            max_peak = np.max(pitch_cepstrum)
            mean_around = np.mean(pitch_cepstrum)
            
            cpp = max_peak - mean_around
            return max(0, cpp * 1000)  # dB 스케일로 변환
            
        except Exception as e:
            return 5.0
    
    def calculate_hnr_simple(self, audio, sr):
        """간이 HNR 계산"""
        try:
            # 자기상관 기반 HNR
            autocorr = np.correlate(audio, audio, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            if len(autocorr) < 2:
                return 10.0
            
            # 정규화
            if autocorr[0] > 0:
                autocorr = autocorr / autocorr[0]
            else:
                return 10.0
            
            # 피크 찾기
            min_period = sr // 500
            max_period = sr // 100
            
            if max_period >= len(autocorr):
                max_period = len(autocorr) - 1
                
            if min_period >= max_period:
                return 10.0
            
            search_range = autocorr[min_period:max_period]
            
            if len(search_range) == 0:
                return 10.0
            
            max_corr = np.max(search_range)
            noise_level = 1 - max_corr
            
            if noise_level <= 0.001:
                return 30.0
                
            hnr = 10 * np.log10(max_corr / noise_level)
            return max(0, hnr)
            
        except Exception as e:
            return 10.0
    
    def calculate_spectral_tilt(self, audio, sr):
        """Spectral Tilt (300Hz-3kHz 직선 회귀)"""
        try:
            # FFT
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1/sr)
            magnitude = np.abs(fft)
            
            # 300Hz-3kHz 범위
            mask = (freqs >= 300) & (freqs <= 3000)
            
            if np.sum(mask) < 10:  # 최소 10개 점은 있어야 함
                return -5.0
            
            freq_range = freqs[mask]
            mag_range = magnitude[mask]
            
            # 로그 스케일
            log_mag = 20 * np.log10(mag_range + 1e-10)
            log_freq = np.log10(freq_range)
            
            # 선형 회귀
            slope, intercept, r_value, p_value, std_err = linregress(log_freq, log_mag)
            
            # dB/octave로 변환 (octave = log2, 우리는 log10 사용)
            db_per_octave = slope * np.log10(2)
            
            return db_per_octave
            
        except Exception as e:
            return -5.0
    
    def calculate_spectral_flatness(self, audio, sr):
        """Spectral Flatness 계산"""
        try:
            # FFT
            fft = np.fft.rfft(audio)
            magnitude = np.abs(fft) + 1e-10
            
            # Geometric mean / Arithmetic mean
            geometric_mean = np.exp(np.mean(np.log(magnitude)))
            arithmetic_mean = np.mean(magnitude)
            
            if arithmetic_mean == 0:
                return 0.5
            
            flatness = geometric_mean / arithmetic_mean
            return min(1.0, flatness)
            
        except Exception as e:
            return 0.5
    
    def calculate_aperiodicity_simple(self, audio, sr):
        """간단한 비주기성 측정"""
        try:
            # 연속된 프레임들의 RMS 변동성
            frame_length = int(0.01 * sr)  # 10ms
            
            if len(audio) < frame_length * 3:
                return 0.1
            
            frames_rms = []
            for i in range(0, len(audio) - frame_length, frame_length):
                frame = audio[i:i+frame_length]
                rms = np.sqrt(np.mean(frame**2))
                frames_rms.append(rms)
            
            if len(frames_rms) < 2:
                return 0.1
            
            # RMS의 변동 계수 (CV)
            mean_rms = np.mean(frames_rms)
            std_rms = np.std(frames_rms)
            
            if mean_rms == 0:
                return 0.1
            
            cv = std_rms / mean_rms
            return min(1.0, cv)
            
        except Exception as e:
            return 0.1
    
    def calculate_spectral_centroid(self, audio, sr):
        """Spectral Centroid 계산"""
        try:
            centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            return np.mean(centroid)
        except:
            return 1500.0
    
    def calculate_spectral_rolloff(self, audio, sr):
        """Spectral Rolloff 계산 (85%)"""
        try:
            rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr, roll_percent=0.85)[0]
            return np.mean(rolloff)
        except:
            return 3000.0
    
    def aggregate_features(self, all_features):
        """특징 집계 - mean, p90, IQR"""
        try:
            print("📊 특징 집계 중...")
            
            aggregated = {}
            
            # 모든 특징의 이름 수집
            feature_names = set()
            for features in all_features:
                feature_names.update(features.keys())
            
            for name in feature_names:
                values = [f.get(name, 0) for f in all_features if name in f]
                
                if values:
                    aggregated[f'{name}_mean'] = np.mean(values)
                    aggregated[f'{name}_p90'] = np.percentile(values, 90)
                    aggregated[f'{name}_iqr'] = np.percentile(values, 75) - np.percentile(values, 25)
                else:
                    aggregated[f'{name}_mean'] = 0
                    aggregated[f'{name}_p90'] = 0
                    aggregated[f'{name}_iqr'] = 0
            
            print(f"   ✅ {len(feature_names)}개 특징에서 {len(aggregated)}개 통계 생성")
            return aggregated
            
        except Exception as e:
            print(f"   ❌ 특징 집계 오류: {e}")
            return {}
    
    def apply_source_correction(self, features, source_hint="unknown"):
        """소스 보정 테이블 적용"""
        try:
            print(f"🔧 소스 보정 적용: {source_hint}")
            
            corrections = {
                "kakaotalk": {
                    "hnr_mean": -1.0,
                    "spectral_tilt_mean": +0.5,
                    "spectral_flatness_mean": +0.02
                },
                "instagram": {
                    "cpp_mean": -0.8
                },
                "low_quality": {
                    "hnr_mean": -2.0,
                    "spectral_flatness_mean": +0.05
                }
            }
            
            if source_hint in corrections:
                correction_table = corrections[source_hint]
                for key, correction in correction_table.items():
                    if key in features:
                        old_value = features[key]
                        features[key] += correction
                        print(f"   {key}: {old_value:.2f} → {features[key]:.2f} ({correction:+.2f})")
            
            return features
            
        except Exception as e:
            print(f"   ❌ 소스 보정 오류: {e}")
            return features
    
    def calculate_final_scores(self, features):
        """최종 스코어링"""
        try:
            print("🎯 최종 점수 계산 중...")
            
            # Z-score 정규화를 위한 기준값들 (경험적 설정)
            reference_stats = {
                'cpp_mean': {'mean': 8.0, 'std': 2.0},
                'hnr_mean': {'mean': 15.0, 'std': 5.0},
                'spectral_tilt_mean': {'mean': -8.0, 'std': 3.0},
                'spectral_flatness_mean': {'mean': 0.25, 'std': 0.1},
                'f0_confidence_mean': {'mean': 0.6, 'std': 0.2},
                'aperiodicity_mean': {'mean': 0.3, 'std': 0.2}
            }
            
            # Z-score 계산
            z_scores = {}
            for key, ref in reference_stats.items():
                if key in features:
                    z_scores[key] = (features[key] - ref['mean']) / ref['std']
                else:
                    z_scores[key] = 0
            
            # 선명도 계산
            clarity = (z_scores['cpp_mean'] + 
                      z_scores['hnr_mean'] - 
                      z_scores['spectral_tilt_mean'] - 
                      z_scores['spectral_flatness_mean'] + 
                      0.5 * z_scores['f0_confidence_mean'] - 
                      0.5 * z_scores['aperiodicity_mean'])
            
            # 0-100으로 선형 매핑 (z-score -3~+3을 0~100으로)
            clarity_score = np.clip((clarity + 3) * 100 / 6, 0, 100)
            
            # 가성/숨섞임 캡 적용
            if features.get('hnr_mean', 15) < 10:
                clarity_score = min(clarity_score, 60)
                print("   ⚠️ 낮은 HNR로 인한 선명도 캐핑 적용")
            
            # 등급화
            if clarity_score >= 70:
                grade = "High"
            elif clarity_score >= 40:
                grade = "Medium"  
            else:
                grade = "Low"
            
            # 보조 태그
            brightness_tag = "밝음" if z_scores['spectral_tilt_mean'] > 0 else "어두움"
            roughness_tag = "거침" if (z_scores['aperiodicity_mean'] > 0.5 or z_scores['hnr_mean'] < -0.5) else "부드러움"
            
            results = {
                'clarity_score': clarity_score,
                'clarity_grade': grade,
                'brightness_tag': brightness_tag,
                'roughness_tag': roughness_tag,
                'z_scores': z_scores,
                'raw_features': features
            }
            
            print(f"   ✅ 선명도: {clarity_score:.1f} ({grade})")
            print(f"   태그: {brightness_tag}, {roughness_tag}")
            
            return results
            
        except Exception as e:
            print(f"   ❌ 최종 점수 계산 오류: {e}")
            return {}
    
    def analyze_file(self, audio_file, source_hint="unknown"):
        """메인 분석 함수"""
        print("=" * 70)
        print("🎤 경량 보컬 분석기 - 전역 품질 분석")
        print("=" * 70)
        print(f"📁 파일: {audio_file.split('/')[-1].split('\\')[-1]}")
        
        # 1. 전처리
        audio, sr = self.preprocess_audio(audio_file)
        if audio is None:
            return None
        
        # 2. VAD
        voiced_frames, voiced_ratio, vad_confidence = self.simple_vad(audio, sr)
        
        # 3. 대표 샘플 추출
        chunks = self.extract_representative_samples(audio, sr, voiced_frames)
        if not chunks:
            print("❌ 대표 샘플 추출 실패")
            return None
        
        # 4. 특징 추출
        print("🔍 라이트 특징 추출 중...")
        all_features = []
        for i, chunk in enumerate(chunks):
            features = self.extract_light_features(chunk['audio'], sr)
            if features:
                all_features.append(features)
        
        if not all_features:
            print("❌ 특징 추출 실패")
            return None
        
        # 5. 특징 집계
        aggregated_features = self.aggregate_features(all_features)
        
        # 6. 소스 보정
        corrected_features = self.apply_source_correction(aggregated_features, source_hint)
        
        # 7. 최종 스코어링
        results = self.calculate_final_scores(corrected_features)
        
        # 신뢰도 추가
        results['confidence'] = vad_confidence
        results['voiced_ratio'] = voiced_ratio
        results['num_chunks_used'] = len(chunks)
        
        return results

def test_lightweight_analyzer():
    """경량 분석기 테스트"""
    
    analyzer = LightweightVocalAnalyzer()
    
    # 테스트 파일들
    test_files = [
        (r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a", "kakaotalk"),
        (r"C:\Users\user\Desktop\vocals_extracted\로이킴_로이킴 - As Is_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav", "unknown")
    ]
    
    results_summary = []
    
    for audio_file, source_hint in test_files:
        filename = audio_file.split('/')[-1].split('\\')[-1]
        print(f"\n{'='*20} {filename} {'='*20}")
        
        result = analyzer.analyze_file(audio_file, source_hint)
        
        if result:
            results_summary.append({
                'file': filename,
                'clarity_score': result['clarity_score'],
                'grade': result['clarity_grade'],
                'brightness': result['brightness_tag'],
                'roughness': result['roughness_tag'],
                'confidence': result['confidence']
            })
            print("✅ 분석 완료!")
        else:
            print("❌ 분석 실패!")
    
    # 최종 비교
    if results_summary:
        print("\n" + "=" * 70)
        print("🏆 최종 비교 결과")
        print("=" * 70)
        
        print(f"\n{'파일':<25} | {'선명도':<6} | {'등급':<6} | {'밝기':<6} | {'거침':<6} | 신뢰도")
        print("-" * 75)
        
        for r in results_summary:
            print(f"{r['file'][:24]:<25} | {r['clarity_score']:<6.1f} | {r['grade']:<6} | {r['brightness']:<6} | {r['roughness']:<6} | {r['confidence']}")

if __name__ == "__main__":
    test_lightweight_analyzer()