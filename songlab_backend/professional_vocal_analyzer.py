"""
전문 보컬 분석기 - 전역 선명도/밝기/거침 분석
목표 파이프라인 완전 구현
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

class ProfessionalVocalAnalyzer:
    def __init__(self):
        self.target_sr = 16000
        self.chunk_duration = 10  # seconds
        self.num_chunks = 12
        self.top_chunks = 6
        
        # 기준값 (Z-score 정규화용)
        self.reference_stats = {
            'cpp': {'mean': 9.5, 'std': 2.5},
            'hnr': {'mean': 19.0, 'std': 6.0},
            'spectral_tilt': {'mean': -8.0, 'std': 4.0},
            'spectral_flatness': {'mean': 0.25, 'std': 0.15},
            'f0_confidence': {'mean': 0.65, 'std': 0.2},
            'aperiodicity': {'mean': 0.3, 'std': 0.2}
        }
    
    def convert_m4a_simple(self, m4a_path):
        """간단한 M4A 변환"""
        try:
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav_path = temp_wav.name
            temp_wav.close()
            
            cmd = ['ffmpeg', '-i', m4a_path, '-ac', '1', '-ar', '16000', temp_wav_path, '-y']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return None
            return temp_wav_path
        except:
            return None
    
    def preprocess_audio(self, audio_file):
        """전처리: 모노, 16kHz, 간단한 정규화"""
        try:
            print("🔧 전처리 중...")
            
            # 파일 로드
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
            
            # 16kHz 리샘플링
            if sr != self.target_sr:
                audio = librosa.resample(y=audio, orig_sr=sr, target_sr=self.target_sr)
                sr = self.target_sr
            
            # 간단한 정규화 (-23 LUFS 대신)
            rms = np.sqrt(np.mean(audio**2))
            if rms > 0:
                audio = audio / (rms * 10)  # 대략적인 라우드니스 매칭
            
            print(f"   ✅ 완료: {len(audio)/sr:.1f}초, {sr}Hz")
            return audio, sr
            
        except Exception as e:
            print(f"   ❌ 전처리 오류: {e}")
            return None, None
    
    def energy_zcr_vad(self, audio, sr):
        """Energy+ZCR 하이브리드 VAD"""
        try:
            frame_length = int(0.02 * sr)  # 20ms
            hop_length = int(0.01 * sr)    # 10ms
            
            # Energy
            energy = []
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i+frame_length]
                energy.append(np.sum(frame**2))
            
            # ZCR
            zcr = []
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i+frame_length]
                zero_crossings = np.sum(np.abs(np.diff(np.sign(frame)))) / 2
                zcr.append(zero_crossings / frame_length)
            
            energy = np.array(energy)
            zcr = np.array(zcr)
            
            # 임계값
            energy_threshold = np.percentile(energy, 25)
            zcr_threshold = 0.15
            
            # 유성 판정
            voiced = (energy > energy_threshold) & (zcr < zcr_threshold)
            voiced_ratio = np.mean(voiced)
            
            print(f"   📊 유성 비율: {voiced_ratio:.1%}")
            
            # 신뢰도
            confidence = "High" if voiced_ratio >= 0.25 else "Low"
            if voiced_ratio < 0.2:
                print(f"   ⚠️ 유성 비율 낮음 - 신뢰도: {confidence}")
            
            return voiced, voiced_ratio, confidence
            
        except Exception as e:
            print(f"   ❌ VAD 오류: {e}")
            return np.ones(len(audio) // hop_length, dtype=bool), 1.0, "Low"
    
    def extract_representative_chunks(self, audio, sr):
        """대표 샘플 추출 - 균등 간격 12개 → 상위 6개"""
        try:
            print("🎯 대표 샘플 추출 중...")
            
            total_duration = len(audio) / sr
            chunk_samples = self.chunk_duration * sr
            
            chunks = []
            for i in range(self.num_chunks):
                # 균등 간격
                start_time = i * total_duration / self.num_chunks
                start_sample = int(start_time * sr)
                end_sample = min(start_sample + chunk_samples, len(audio))
                
                if end_sample - start_sample < sr:  # 1초 미만 스킵
                    continue
                
                chunk_audio = audio[start_sample:end_sample]
                
                # F0 confidence (자기상관 기반)
                f0_conf = self.calculate_f0_confidence_simple(chunk_audio, sr)
                
                # RMS 정규화
                rms_norm = np.sqrt(np.mean(chunk_audio**2))
                
                # 점수 = 0.7·F0conf + 0.3·RMS
                score = 0.7 * f0_conf + 0.3 * rms_norm
                
                chunks.append({
                    'start_time': start_time,
                    'audio': chunk_audio,
                    'f0_conf': f0_conf,
                    'rms_norm': rms_norm,
                    'score': score
                })
            
            # 상위 6개 선택
            chunks.sort(key=lambda x: x['score'], reverse=True)
            top_chunks = chunks[:self.top_chunks]
            
            print(f"   ✅ {len(chunks)}개 중 상위 {len(top_chunks)}개 선택")
            for i, chunk in enumerate(top_chunks[:3]):
                print(f"      #{i+1}: Score={chunk['score']:.3f} (F0={chunk['f0_conf']:.3f}, RMS={chunk['rms_norm']:.3f})")
            
            return top_chunks
            
        except Exception as e:
            print(f"   ❌ 청크 추출 오류: {e}")
            return []
    
    def calculate_f0_confidence_simple(self, audio, sr):
        """간단한 F0 confidence (자기상관)"""
        try:
            # 자기상관
            autocorr = np.correlate(audio, audio, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # 정규화
            if autocorr[0] > 0:
                autocorr = autocorr / autocorr[0]
            else:
                return 0.3
            
            # 피치 범위 (50-500Hz)
            min_period = sr // 500
            max_period = sr // 50
            
            if max_period >= len(autocorr):
                max_period = len(autocorr) - 1
            
            if min_period >= max_period:
                return 0.3
            
            # 최대 피크
            search_range = autocorr[min_period:max_period]
            if len(search_range) == 0:
                return 0.3
            
            max_corr = np.max(search_range)
            return max(0.1, min(1.0, max_corr))
            
        except:
            return 0.3
    
    def extract_light_features(self, chunk_audio, sr):
        """라이트 특징 세트 추출"""
        try:
            features = {}
            
            # 1. CPP (간이 버전 - 켑스트럼 피크)
            features['cpp'] = self.calculate_cpp_light(chunk_audio, sr)
            
            # 2. HNR (자기상관 기반)
            features['hnr'] = self.calculate_hnr_autocorr(chunk_audio, sr)
            
            # 3. Spectral Tilt (300Hz-3kHz 선형회귀)
            features['spectral_tilt'] = self.calculate_spectral_tilt(chunk_audio, sr)
            
            # 4. Spectral Flatness
            features['spectral_flatness'] = self.calculate_spectral_flatness(chunk_audio, sr)
            
            # 5. F0 confidence
            features['f0_confidence'] = self.calculate_f0_confidence_simple(chunk_audio, sr)
            
            # 6. Aperiodicity proxy (간단한 변동성)
            features['aperiodicity'] = self.calculate_aperiodicity_proxy(chunk_audio, sr)
            
            # 보조: Spectral centroid, rolloff
            features['spectral_centroid'] = self.calculate_spectral_centroid(chunk_audio, sr)
            features['spectral_rolloff'] = self.calculate_spectral_rolloff(chunk_audio, sr)
            
            return features
            
        except Exception as e:
            print(f"   ❌ 특징 추출 오류: {e}")
            return {}
    
    def calculate_cpp_light(self, audio, sr):
        """간이 CPP - 켑스트럼 피크 prominence"""
        try:
            # 40ms 윈도우
            frame_length = int(0.04 * sr)
            if len(audio) < frame_length:
                return 6.0
            
            # 윈도잉
            windowed = audio[:frame_length] * np.hanning(frame_length)
            
            # FFT → 로그 스펙트럼 → 켑스트럼
            fft = np.fft.fft(windowed)
            log_spectrum = np.log(np.abs(fft) + 1e-10)
            cepstrum = np.fft.ifft(log_spectrum).real
            
            # 피치 범위 (2-20ms quefrency, 50-500Hz)
            min_q = int(sr * 0.002)  # 2ms
            max_q = int(sr * 0.02)   # 20ms
            
            if max_q >= len(cepstrum):
                max_q = len(cepstrum) - 1
            
            if min_q >= max_q:
                return 6.0
            
            pitch_cepstrum = cepstrum[min_q:max_q]
            
            # 최대 피크와 주변 평균의 차이
            max_peak = np.max(pitch_cepstrum)
            mean_level = np.mean(pitch_cepstrum)
            
            cpp = (max_peak - mean_level) * 1000  # dB 스케일
            return max(0, min(20, cpp))
            
        except:
            return 6.0
    
    def calculate_hnr_autocorr(self, audio, sr):
        """자기상관 기반 HNR"""
        try:
            # 자기상관
            autocorr = np.correlate(audio, audio, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            if len(autocorr) < 2 or autocorr[0] <= 0:
                return 12.0
            
            # 정규화
            autocorr = autocorr / autocorr[0]
            
            # 피치 범위에서 최대 피크
            min_period = sr // 400  # 400Hz
            max_period = sr // 80   # 80Hz
            
            if max_period >= len(autocorr):
                max_period = len(autocorr) - 1
            
            if min_period >= max_period:
                return 12.0
            
            search_range = autocorr[min_period:max_period]
            if len(search_range) == 0:
                return 12.0
            
            max_corr = np.max(search_range)
            noise_level = 1 - max_corr
            
            if noise_level <= 0.01:
                return 25.0
            
            hnr = 10 * np.log10(max_corr / noise_level)
            return max(0, min(30, hnr))
            
        except:
            return 12.0
    
    def calculate_spectral_tilt(self, audio, sr):
        """300Hz-3kHz 직선 회귀 기울기"""
        try:
            # FFT
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1/sr)
            magnitude = np.abs(fft) + 1e-10
            
            # 300-3000Hz 범위
            mask = (freqs >= 300) & (freqs <= 3000)
            
            if np.sum(mask) < 10:
                return -6.0
            
            freq_range = freqs[mask]
            mag_range = magnitude[mask]
            
            # 로그 스케일 선형 회귀
            log_mag = 20 * np.log10(mag_range)
            log_freq = np.log10(freq_range)
            
            slope, _, _, _, _ = linregress(log_freq, log_mag)
            
            # dB/octave 변환
            db_per_octave = slope * np.log10(2)
            
            return max(-20, min(5, db_per_octave))
            
        except:
            return -6.0
    
    def calculate_spectral_flatness(self, audio, sr):
        """Spectral Flatness (geometric/arithmetic mean)"""
        try:
            fft = np.fft.rfft(audio)
            magnitude = np.abs(fft) + 1e-10
            
            # Geometric mean / Arithmetic mean
            geometric_mean = np.exp(np.mean(np.log(magnitude)))
            arithmetic_mean = np.mean(magnitude)
            
            flatness = geometric_mean / arithmetic_mean
            return min(1.0, max(0.0, flatness))
            
        except:
            return 0.3
    
    def calculate_aperiodicity_proxy(self, audio, sr):
        """비주기성 대리 지표 (RMS 변동성)"""
        try:
            frame_length = int(0.01 * sr)  # 10ms 프레임
            
            if len(audio) < frame_length * 3:
                return 0.2
            
            # 프레임별 RMS
            rms_values = []
            for i in range(0, len(audio) - frame_length, frame_length):
                frame = audio[i:i+frame_length]
                rms = np.sqrt(np.mean(frame**2))
                rms_values.append(rms)
            
            if len(rms_values) < 2:
                return 0.2
            
            # 변동 계수 (coefficient of variation)
            mean_rms = np.mean(rms_values)
            std_rms = np.std(rms_values)
            
            if mean_rms > 0:
                cv = std_rms / mean_rms
                return min(1.0, max(0.0, cv))
            else:
                return 0.2
            
        except:
            return 0.2
    
    def calculate_spectral_centroid(self, audio, sr):
        """Spectral Centroid"""
        try:
            centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            return np.mean(centroid)
        except:
            return 1500.0
    
    def calculate_spectral_rolloff(self, audio, sr):
        """Spectral Rolloff (85%)"""
        try:
            rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr, roll_percent=0.85)[0]
            return np.mean(rolloff)
        except:
            return 3500.0
    
    def aggregate_features(self, all_features):
        """특징 집계 - mean, p90, IQR"""
        try:
            print("📊 특징 집계 중...")
            
            aggregated = {}
            feature_names = ['cpp', 'hnr', 'spectral_tilt', 'spectral_flatness', 
                           'f0_confidence', 'aperiodicity', 'spectral_centroid', 'spectral_rolloff']
            
            for name in feature_names:
                values = [f.get(name, 0) for f in all_features if name in f and not np.isnan(f.get(name, 0))]
                
                if values:
                    aggregated[f'{name}_mean'] = np.mean(values)
                    aggregated[f'{name}_p90'] = np.percentile(values, 90)
                    aggregated[f'{name}_iqr'] = np.percentile(values, 75) - np.percentile(values, 25)
                else:
                    # 기본값
                    defaults = {'cpp': 7, 'hnr': 15, 'spectral_tilt': -8, 'spectral_flatness': 0.3,
                              'f0_confidence': 0.5, 'aperiodicity': 0.3, 'spectral_centroid': 1500, 'spectral_rolloff': 3500}
                    default_val = defaults.get(name, 0)
                    aggregated[f'{name}_mean'] = default_val
                    aggregated[f'{name}_p90'] = default_val
                    aggregated[f'{name}_iqr'] = 0
            
            print(f"   ✅ {len(feature_names)}개 특징 집계 완료")
            return aggregated
            
        except Exception as e:
            print(f"   ❌ 특징 집계 오류: {e}")
            return {}
    
    def apply_source_correction(self, features, source_hint="unknown"):
        """소스 보정 테이블 적용"""
        try:
            print(f"🔧 소스 보정 적용: {source_hint}")
            
            # 보정 테이블
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
                applied = 0
                for key, correction in correction_table.items():
                    if key in features:
                        old_value = features[key]
                        features[key] += correction
                        print(f"   {key}: {old_value:.2f} → {features[key]:.2f} ({correction:+.2f})")
                        applied += 1
                
                if applied == 0:
                    print("   보정 적용된 항목 없음")
            else:
                print("   알려진 소스 아님 - 보정 생략")
            
            return features
            
        except Exception as e:
            print(f"   ❌ 소스 보정 오류: {e}")
            return features
    
    def calculate_final_clarity_score(self, features):
        """최종 선명도 점수 계산"""
        try:
            print("🎯 최종 점수 계산 중...")
            
            # Z-score 정규화
            z_scores = {}
            core_features = ['cpp', 'hnr', 'spectral_tilt', 'spectral_flatness', 'f0_confidence', 'aperiodicity']
            
            for feature in core_features:
                mean_key = f'{feature}_mean'
                if mean_key in features:
                    ref = self.reference_stats[feature]
                    z_scores[feature] = (features[mean_key] - ref['mean']) / ref['std']
                else:
                    z_scores[feature] = 0
            
            # 선명도 공식
            clarity_z = (z_scores['cpp'] + 
                        z_scores['hnr'] - 
                        z_scores['spectral_tilt'] - 
                        z_scores['spectral_flatness'] + 
                        0.5 * z_scores['f0_confidence'] - 
                        0.5 * z_scores['aperiodicity'])
            
            # 0-100 선형 매핑 (z-score -3~+3을 0~100으로)
            clarity_score = np.clip((clarity_z + 3) * 100 / 6, 0, 100)
            
            # 가성/숨섞임 하드캡
            hnr_mean = features.get('hnr_mean', 15)
            if hnr_mean < 10:
                clarity_score = min(clarity_score, 60)
                print("   ⚠️ 낮은 HNR - 선명도 캐핑 적용 (60 이하)")
            
            # 등급화
            if clarity_score >= 70:
                grade = "High"
            elif clarity_score >= 40:
                grade = "Medium"
            else:
                grade = "Low"
            
            # 보조 태그
            tilt_mean = features.get('spectral_tilt_mean', -8)
            centroid_mean = features.get('spectral_centroid_mean', 1500)
            
            brightness = "밝음" if (tilt_mean > -6 and centroid_mean > 1800) else "어두움"
            
            aperiodicity_mean = features.get('aperiodicity_mean', 0.3)
            roughness = "거림" if (aperiodicity_mean > 0.4 or hnr_mean < 12) else "부드러움"
            
            results = {
                'clarity_score': clarity_score,
                'clarity_grade': grade,
                'brightness_tag': brightness,
                'roughness_tag': roughness,
                'z_scores': z_scores,
                'core_features': {k: features.get(f'{k}_mean', 0) for k in core_features}
            }
            
            print(f"   ✅ 선명도: {clarity_score:.1f} ({grade})")
            print(f"   🏷️ 태그: {brightness}, {roughness}")
            print(f"   📊 주요 특징: CPP={results['core_features']['cpp']:.1f}, HNR={results['core_features']['hnr']:.1f}")
            
            return results
            
        except Exception as e:
            print(f"   ❌ 최종 점수 계산 오류: {e}")
            return {}
    
    def analyze_vocal_file(self, audio_file, source_hint="unknown"):
        """메인 분석 함수"""
        print("=" * 70)
        print("🎤 전문 보컬 분석기 - 전역 품질 분석")
        print("=" * 70)
        filename = audio_file.split('/')[-1].split('\\')[-1]
        print(f"📁 파일: {filename}")
        
        # 1. 전처리
        audio, sr = self.preprocess_audio(audio_file)
        if audio is None:
            print("❌ 전처리 실패")
            return None
        
        # 2. VAD
        voiced_frames, voiced_ratio, vad_confidence = self.energy_zcr_vad(audio, sr)
        
        # 3. 대표 샘플 추출
        chunks = self.extract_representative_chunks(audio, sr)
        if not chunks:
            print("❌ 대표 샘플 추출 실패")
            return None
        
        # 4. 라이트 특징 추출
        print("🔍 라이트 특징 추출 중...")
        all_features = []
        for i, chunk in enumerate(chunks):
            features = self.extract_light_features(chunk['audio'], sr)
            if features:
                all_features.append(features)
        
        if not all_features:
            print("❌ 특징 추출 실패")
            return None
        
        print(f"   ✅ {len(all_features)}개 청크에서 특징 추출 완료")
        
        # 5. 특징 집계
        aggregated_features = self.aggregate_features(all_features)
        if not aggregated_features:
            print("❌ 특징 집계 실패")
            return None
        
        # 6. 소스 보정
        corrected_features = self.apply_source_correction(aggregated_features, source_hint)
        
        # 7. 최종 스코어링
        results = self.calculate_final_clarity_score(corrected_features)
        if not results:
            print("❌ 최종 점수 계산 실패")
            return None
        
        # 신뢰도 정보 추가
        results['confidence_info'] = {
            'vad_confidence': vad_confidence,
            'voiced_ratio': voiced_ratio,
            'num_chunks_used': len(chunks),
            'audio_duration': len(audio) / sr
        }
        
        return results

def test_professional_analyzer():
    """전문 분석기 테스트"""
    
    analyzer = ProfessionalVocalAnalyzer()
    
    # 테스트 파일들
    test_files = [
        (r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a", "kakaotalk"),
        (r"C:\Users\user\Desktop\vocals_extracted\로이킴_로이킴 - As Is_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav", "unknown")
    ]
    
    results_summary = []
    
    for audio_file, source_hint in test_files:
        result = analyzer.analyze_vocal_file(audio_file, source_hint)
        
        if result:
            filename = audio_file.split('/')[-1].split('\\')[-1]
            results_summary.append({
                'file': filename[:25],
                'clarity_score': result['clarity_score'],
                'grade': result['clarity_grade'],
                'brightness': result['brightness_tag'],
                'roughness': result['roughness_tag'],
                'confidence': result['confidence_info']['vad_confidence'],
                'voiced_ratio': result['confidence_info']['voiced_ratio']
            })
            print("✅ 분석 완료!")
        else:
            print("❌ 분석 실패!")
        print()
    
    # 최종 비교
    if results_summary:
        print("=" * 80)
        print("🏆 최종 비교 결과")
        print("=" * 80)
        
        print(f"\n{'파일':<27} | {'선명도':<6} | {'등급':<6} | {'밝기':<6} | {'거침':<8} | {'신뢰도':<6} | 유성%")
        print("-" * 85)
        
        for r in results_summary:
            print(f"{r['file']:<27} | {r['clarity_score']:<6.1f} | {r['grade']:<6} | {r['brightness']:<6} | {r['roughness']:<8} | {r['confidence']:<6} | {r['voiced_ratio']:<5.1%}")
        
        print(f"\n💡 예상 순서: 김범수 > kakaotalk > 로이킴 > 가성")
        sorted_results = sorted(results_summary, key=lambda x: x['clarity_score'], reverse=True)
        actual_order = " > ".join([r['file'].split('_')[0][:8] for r in sorted_results])
        print(f"💡 실제 순서: {actual_order}")

if __name__ == "__main__":
    test_professional_analyzer()