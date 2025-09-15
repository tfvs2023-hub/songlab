"""
CPP (Cepstral Peak Prominence) 포함 성대내전 지표 완전 분석
"""

import numpy as np
import librosa
import soundfile as sf
import io
import subprocess
import tempfile
import os
from scipy.signal import find_peaks
from scipy.stats import entropy

def convert_m4a_to_wav(m4a_path):
    """M4A를 WAV로 변환"""
    try:
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        cmd = [
            'ffmpeg', '-i', m4a_path,
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            temp_wav_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return None
            
        return temp_wav_path
        
    except Exception as e:
        print(f"Conversion error: {e}")
        return None

def calculate_cpp(audio, sr):
    """CPP (Cepstral Peak Prominence) 계산"""
    try:
        # 짧은 프레임으로 분할하여 CPP 계산
        frame_length = 2048
        hop_length = 512
        cpp_values = []
        
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i+frame_length]
            
            # 윈도잉
            frame = frame * np.hanning(len(frame))
            
            # FFT
            fft = np.fft.fft(frame)
            log_spectrum = np.log(np.abs(fft) + 1e-10)
            
            # Cepstrum 계산
            cepstrum = np.fft.ifft(log_spectrum).real
            
            # 피치 범위 내에서 피크 찾기 (2ms ~ 20ms 범위, 즉 50Hz ~ 500Hz)
            min_quefrency = int(sr * 0.002)  # 2ms
            max_quefrency = int(sr * 0.02)   # 20ms
            
            if max_quefrency < len(cepstrum):
                pitch_cepstrum = cepstrum[min_quefrency:max_quefrency]
                
                if len(pitch_cepstrum) > 0:
                    # 피크 찾기
                    peaks, _ = find_peaks(pitch_cepstrum, height=0)
                    
                    if len(peaks) > 0:
                        # 가장 높은 피크
                        max_peak_idx = peaks[np.argmax(pitch_cepstrum[peaks])]
                        max_peak_value = pitch_cepstrum[max_peak_idx]
                        
                        # 주변 평균과의 차이 (Prominence)
                        surrounding_start = max(0, max_peak_idx - 10)
                        surrounding_end = min(len(pitch_cepstrum), max_peak_idx + 10)
                        surrounding_mean = np.mean(np.concatenate([
                            pitch_cepstrum[surrounding_start:max_peak_idx],
                            pitch_cepstrum[max_peak_idx+1:surrounding_end]
                        ]))
                        
                        cpp = max_peak_value - surrounding_mean
                        cpp_values.append(cpp)
        
        return np.mean(cpp_values) if cpp_values else 0.0
        
    except Exception as e:
        print(f"CPP calculation error: {e}")
        return 0.0

def analyze_all_indicators_fixed(audio_file):
    """수정된 전체 성대내전 지표 분석"""
    
    print("=" * 70)
    print("🔬 성대내전 지표 완전 분석 (수정 버전)")
    print("=" * 70)
    
    try:
        # M4A 변환 시도
        if audio_file.endswith('.m4a'):
            print("🔄 M4A → WAV 변환 중...")
            wav_path = convert_m4a_to_wav(audio_file)
            
            if not wav_path:
                print("📁 soundfile로 직접 로드...")
                audio_data, sr = sf.read(audio_file)
            else:
                audio_data, sr = sf.read(wav_path)
                os.unlink(wav_path)
        else:
            audio_data, sr = sf.read(audio_file)
        
        print(f"🎵 파일: {audio_file.split('\\')[-1]}")
        print(f"   길이: {len(audio_data)/sr:.1f}초, 샘플링: {sr}Hz")
        
        # 모노 변환
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 처음 30초만 분석 (속도 향상)
        max_samples = 30 * sr
        if len(audio_data) > max_samples:
            audio_data = audio_data[:max_samples]
            print("   (처음 30초만 분석)")
        
        print("\n" + "=" * 70)
        print("📊 지표별 분석 결과")
        print("=" * 70)
        
        results = {}
        
        # 1. CPP (Cepstral Peak Prominence) - 새로 추가!
        print("\n🎯 1. CPP (Cepstral Peak Prominence)")
        try:
            cpp_value = calculate_cpp(audio_data, sr)
            # CPP는 높을수록 좋음 (성대 접촉 품질 높음)
            cpp_score = np.clip(cpp_value * 500 + 10, -50, 50)
            print(f"   원시값: {cpp_value:.6f} (높을수록 좋음)")
            print(f"   정규화: {cpp_score:.1f} (-50~50)")
            results['CPP'] = {'raw': cpp_value, 'normalized': cpp_score}
        except Exception as e:
            print(f"   오류: {e}")
            results['CPP'] = {'raw': 0, 'normalized': 0}
        
        # 2. Zero Crossing Rate
        print("\n🎯 2. Zero Crossing Rate (ZCR)")
        try:
            zcr = librosa.feature.zero_crossing_rate(audio_data, frame_length=2048, hop_length=512)[0]
            zcr_mean = np.mean(zcr)
            # ZCR이 낮을수록 깨끗한 음성
            zcr_score = np.clip(50 - zcr_mean * 2000, -50, 50)
            print(f"   원시값: {zcr_mean:.6f} (낮을수록 좋음)")
            print(f"   정규화: {zcr_score:.1f} (-50~50)")
            results['ZCR'] = {'raw': zcr_mean, 'normalized': zcr_score}
        except Exception as e:
            print(f"   오류: {e}")
            results['ZCR'] = {'raw': 0, 'normalized': 0}
        
        # 3. Spectral Tilt (수정됨)
        print("\n🎯 3. Spectral Tilt (스펙트럼 기울기)")
        try:
            # 스펙트로그램으로 계산
            D = librosa.stft(audio_data, n_fft=2048, hop_length=512)
            magnitude = np.abs(D)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            
            # 주파수별 평균 에너지
            mean_magnitude = np.mean(magnitude, axis=1)
            
            # 저주파 vs 고주파 에너지 비율
            low_mask = (freqs >= 50) & (freqs <= 1000)
            high_mask = (freqs >= 1000) & (freqs <= 4000)
            
            low_energy = np.sum(mean_magnitude[low_mask])
            high_energy = np.sum(mean_magnitude[high_mask])
            
            if high_energy > 0:
                tilt_ratio = low_energy / high_energy
                # 성대 접촉이 좋으면 고주파 에너지가 많아짐
                tilt_score = np.clip(30 - np.log10(tilt_ratio + 0.1) * 15, -50, 50)
            else:
                tilt_score = -50
                
            print(f"   저주파/고주파 비율: {tilt_ratio:.3f}")
            print(f"   정규화: {tilt_score:.1f} (-50~50)")
            results['Spectral_Tilt'] = {'raw': tilt_ratio, 'normalized': tilt_score}
        except Exception as e:
            print(f"   오류: {e}")
            results['Spectral_Tilt'] = {'raw': 0, 'normalized': 0}
        
        # 4. Spectral Entropy (수정됨)
        print("\n🎯 4. Spectral Entropy (스펙트럼 무질서도)")
        try:
            D = librosa.stft(audio_data, n_fft=1024, hop_length=256)
            magnitude = np.abs(D)
            
            # 각 프레임별 스펙트럼 엔트로피
            entropies = []
            for i in range(magnitude.shape[1]):
                spectrum = magnitude[:, i]
                if np.sum(spectrum) > 1e-10:
                    spectrum_norm = spectrum / np.sum(spectrum)
                    spectrum_norm = spectrum_norm[spectrum_norm > 1e-10]
                    if len(spectrum_norm) > 1:
                        ent = entropy(spectrum_norm)
                        entropies.append(ent)
            
            if entropies:
                entropy_mean = np.mean(entropies)
                # 엔트로피가 낮을수록 깨끗한 음성
                entropy_score = np.clip(40 - entropy_mean * 8, -50, 50)
            else:
                entropy_mean = 0
                entropy_score = 0
                
            print(f"   원시값: {entropy_mean:.4f} (낮을수록 좋음)")
            print(f"   정규화: {entropy_score:.1f} (-50~50)")
            results['Spectral_Entropy'] = {'raw': entropy_mean, 'normalized': entropy_score}
        except Exception as e:
            print(f"   오류: {e}")
            results['Spectral_Entropy'] = {'raw': 0, 'normalized': 0}
        
        # 5. Pitch Stability (F0 안정성)
        print("\n🎯 5. Pitch Stability (F0 안정성)")
        try:
            # YIN 피치 추정
            f0 = librosa.yin(audio_data, fmin=80, fmax=400, sr=sr, frame_length=2048)
            # NaN 제거
            valid_f0 = f0[~np.isnan(f0)]
            
            if len(valid_f0) > 10:
                f0_std = np.std(valid_f0)
                f0_mean = np.mean(valid_f0)
                f0_cv = f0_std / f0_mean if f0_mean > 0 else 1.0
                
                # 변동계수가 낮을수록 안정적
                stability_score = np.clip(50 - f0_cv * 1000, -50, 50)
                print(f"   F0 평균: {f0_mean:.1f} Hz")
                print(f"   F0 표준편차: {f0_std:.2f}")
                print(f"   변동계수: {f0_cv:.4f} (낮을수록 좋음)")
            else:
                stability_score = -50
                f0_cv = 1.0
                print(f"   피치 추정 실패")
            
            print(f"   정규화: {stability_score:.1f} (-50~50)")
            results['Pitch_Stability'] = {'raw': f0_cv, 'normalized': stability_score}
        except Exception as e:
            print(f"   오류: {e}")
            results['Pitch_Stability'] = {'raw': 0, 'normalized': 0}
        
        # 6. Formant Bandwidth (포먼트 대역폭)
        print("\n🎯 6. Formant Bandwidth (포먼트 선명도)")
        try:
            # 첫 번째 포먼트 추정
            formants = librosa.feature.spectral_centroid(y=audio_data, sr=sr)[0]
            formant_mean = np.mean(formants)
            
            # 스펙트럴 롤오프로 대역폭 추정
            rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=sr, roll_percent=0.85)[0]
            rolloff_mean = np.mean(rolloff)
            
            # 대역폭이 적당하면 선명함 (너무 넓거나 좁으면 안 좋음)
            bandwidth = rolloff_mean - formant_mean
            if 1000 < bandwidth < 3000:
                bandwidth_score = 30
            elif 500 < bandwidth < 4000:
                bandwidth_score = 10
            else:
                bandwidth_score = -20
                
            print(f"   스펙트럴 중심: {formant_mean:.1f} Hz")
            print(f"   롤오프: {rolloff_mean:.1f} Hz")
            print(f"   추정 대역폭: {bandwidth:.1f} Hz")
            print(f"   정규화: {bandwidth_score:.1f} (-50~50)")
            results['Formant_Bandwidth'] = {'raw': bandwidth, 'normalized': bandwidth_score}
        except Exception as e:
            print(f"   오류: {e}")
            results['Formant_Bandwidth'] = {'raw': 0, 'normalized': 0}
        
        # 종합 비교
        print("\n" + "=" * 70)
        print("📈 지표별 성대내전 점수 비교")
        print("=" * 70)
        
        print(f"\n{'지표':<20} | {'원시값':<15} | {'정규화점수':<10} | 평가")
        print("-" * 70)
        
        for name, data in results.items():
            raw_val = data['raw']
            norm_val = data['normalized']
            
            # 평가 등급
            if norm_val > 30:
                grade = "매우 좋음"
            elif norm_val > 10:
                grade = "좋음"
            elif norm_val > -10:
                grade = "보통"
            elif norm_val > -30:
                grade = "나쁨"
            else:
                grade = "매우 나쁨"
                
            print(f"{name:<20} | {raw_val:<15.6f} | {norm_val:<10.1f} | {grade}")
        
        # 가중치 조합 비교
        print("\n" + "=" * 70)
        print("⚖️ 가중치 조합 비교")
        print("=" * 70)
        
        # 모든 점수 추출
        all_scores = [data['normalized'] for data in results.values()]
        
        # 6개 균등 가중치
        equal_weight_score = np.mean(all_scores)
        
        # 상위 4개
        top4_scores = sorted(all_scores, reverse=True)[:4]
        top4_score = np.mean(top4_scores)
        
        # CPP + ZCR + Spectral_Tilt 조합
        cpp_zcr_tilt = np.mean([
            results['CPP']['normalized'],
            results['ZCR']['normalized'],
            results['Spectral_Tilt']['normalized']
        ])
        
        print(f"6개 균등 가중치:              {equal_weight_score:.1f}")
        print(f"상위 4개 평균:                {top4_score:.1f}")
        print(f"CPP+ZCR+Spectral_Tilt:       {cpp_zcr_tilt:.1f}")
        
        print("\n💡 김범수는 깨끗한 음성이므로 +20 이상이 나와야 정상!")
        print("💡 허스키한 음성은 -20 이하가 나와야 정상!")
        
        return results
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 두 파일 비교
    files = [
        r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav",
        r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a"
    ]
    
    for audio_file in files:
        print(f"\n{'='*10} {audio_file.split('\\')[-1]} {'='*10}")
        results = analyze_all_indicators_fixed(audio_file)
        if results:
            print("✅ 분석 완료!")
        print("\n")