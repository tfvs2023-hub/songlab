"""
김범수 보컬 - 성대내전 6개 지표 비교 테스트
"""

import numpy as np
import parselmouth
from parselmouth.praat import call
import librosa
import soundfile as sf
import io
from scipy.stats import entropy
import torch

def analyze_all_adduction_indicators(audio_file):
    """성대내전 관련 모든 지표 분석"""
    
    print("=" * 70)
    print("🔬 성대내전 지표 6개 항목 비교 분석")
    print("=" * 70)
    
    # 오디오 로드 (처음 30초만)
    audio_data, sr = sf.read(audio_file, start=0, stop=30*44100)  # 30초만 분석
    print(f"🎵 파일: {audio_file.split('\\')[-1]}")
    print(f"   길이: {len(audio_data)/sr:.1f}초, 샘플링: {sr}Hz (처음 30초 분석)")
    
    # 16kHz로 리샘플링
    if sr != 16000:
        import librosa
        audio = librosa.resample(y=audio_data, orig_sr=sr, target_sr=16000)
        sr = 16000
    else:
        audio = audio_data
    
    # Parselmouth Sound 객체 생성
    sound = parselmouth.Sound(audio, sampling_frequency=sr)
    
    print("\n" + "=" * 70)
    print("📊 지표별 분석 결과")
    print("=" * 70)
    
    results = {}
    
    # 1. HNR (Harmonic-to-Noise Ratio)
    print("\n🎯 1. HNR (Harmonic-to-Noise Ratio)")
    try:
        harmonicity = sound.to_harmonicity()
        hnr_values = harmonicity.values
        hnr_mean = np.mean(hnr_values[~np.isnan(hnr_values)])
        hnr_score = np.clip((hnr_mean - 3) * 15, -50, 50)
        print(f"   원시값: {hnr_mean:.2f} dB")
        print(f"   정규화: {hnr_score:.1f} (-50~50)")
        results['HNR'] = {'raw': hnr_mean, 'normalized': hnr_score}
    except Exception as e:
        print(f"   오류: {e}")
        results['HNR'] = {'raw': 0, 'normalized': 0}
    
    # 2. Jitter
    print("\n🎯 2. Jitter (주파수 불안정성)")
    try:
        pitch = sound.to_pitch()
        jitter_local = call(pitch, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        jitter_score = max(50 - jitter_local * 1000, -50)
        print(f"   원시값: {jitter_local:.6f} (0에 가까울수록 좋음)")
        print(f"   정규화: {jitter_score:.1f} (-50~50)")
        results['Jitter'] = {'raw': jitter_local, 'normalized': jitter_score}
    except Exception as e:
        print(f"   오류: {e}")
        results['Jitter'] = {'raw': 0, 'normalized': 0}
    
    # 3. Shimmer
    print("\n🎯 3. Shimmer (진폭 불안정성)")
    try:
        shimmer_local = call(sound, "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        shimmer_score = max(50 - shimmer_local * 100, -50)
        print(f"   원시값: {shimmer_local:.6f} (0에 가까울수록 좋음)")
        print(f"   정규화: {shimmer_score:.1f} (-50~50)")
        results['Shimmer'] = {'raw': shimmer_local, 'normalized': shimmer_score}
    except Exception as e:
        print(f"   오류: {e}")
        results['Shimmer'] = {'raw': 0, 'normalized': 0}
    
    # 4. Spectral Tilt (스펙트럼 기울기)
    print("\n🎯 4. Spectral Tilt (스펙트럼 기울기)")
    try:
        # FFT 계산
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1/sr)
        magnitude = np.abs(fft)
        
        # 저주파 (0-1000Hz) vs 고주파 (1000-4000Hz) 에너지 비율
        low_mask = (freqs >= 50) & (freqs <= 1000)
        high_mask = (freqs >= 1000) & (freqs <= 4000)
        
        low_energy = np.sum(magnitude[low_mask] ** 2)
        high_energy = np.sum(magnitude[high_mask] ** 2)
        
        if high_energy > 0:
            tilt_ratio = low_energy / high_energy
            # 성대 접촉이 좋으면 고주파 에너지가 많아짐 (tilt_ratio 낮아짐)
            tilt_score = np.clip(50 - np.log10(tilt_ratio + 0.1) * 20, -50, 50)
        else:
            tilt_score = -50
            
        print(f"   저주파/고주파 비율: {tilt_ratio:.3f}")
        print(f"   정규화: {tilt_score:.1f} (-50~50)")
        results['Spectral_Tilt'] = {'raw': tilt_ratio, 'normalized': tilt_score}
    except Exception as e:
        print(f"   오류: {e}")
        results['Spectral_Tilt'] = {'raw': 0, 'normalized': 0}
    
    # 5. Zero Crossing Rate
    print("\n🎯 5. Zero Crossing Rate (ZCR)")
    try:
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        zcr_mean = np.mean(zcr)
        # ZCR이 낮을수록 깨끗한 음성 (허스키하면 ZCR 높아짐)
        zcr_score = np.clip(50 - zcr_mean * 5000, -50, 50)
        print(f"   원시값: {zcr_mean:.6f} (낮을수록 좋음)")
        print(f"   정규화: {zcr_score:.1f} (-50~50)")
        results['ZCR'] = {'raw': zcr_mean, 'normalized': zcr_score}
    except Exception as e:
        print(f"   오류: {e}")
        results['ZCR'] = {'raw': 0, 'normalized': 0}
    
    # 6. Spectral Entropy (스펙트럼 엔트로피)
    print("\n🎯 6. Spectral Entropy (스펙트럼 무질서도)")
    try:
        # 스펙트로그램 계산
        D = librosa.stft(audio, hop_length=512, n_fft=1024)
        magnitude = np.abs(D)
        
        # 각 프레임별 스펙트럼 엔트로피 계산
        entropies = []
        for i in range(magnitude.shape[1]):
            spectrum = magnitude[:, i]
            if np.sum(spectrum) > 0:
                spectrum_norm = spectrum / np.sum(spectrum)
                # 0이 아닌 값들만으로 엔트로피 계산
                spectrum_norm = spectrum_norm[spectrum_norm > 0]
                ent = entropy(spectrum_norm)
                entropies.append(ent)
        
        if entropies:
            entropy_mean = np.mean(entropies)
            # 엔트로피가 낮을수록 깨끗한 음성 (조화로운 구조)
            entropy_score = np.clip(50 - entropy_mean * 10, -50, 50)
        else:
            entropy_mean = 0
            entropy_score = 0
            
        print(f"   원시값: {entropy_mean:.4f} (낮을수록 좋음)")
        print(f"   정규화: {entropy_score:.1f} (-50~50)")
        results['Spectral_Entropy'] = {'raw': entropy_mean, 'normalized': entropy_score}
    except Exception as e:
        print(f"   오류: {e}")
        results['Spectral_Entropy'] = {'raw': 0, 'normalized': 0}
    
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
    
    # 현재 가중치 조합과 새로운 조합 비교
    print("\n" + "=" * 70)
    print("⚖️ 가중치 조합 비교")
    print("=" * 70)
    
    # 현재 방식 (HNR + Jitter + Shimmer)
    current_score = (0.3 * results['HNR']['normalized'] + 
                    0.35 * results['Jitter']['normalized'] + 
                    0.35 * results['Shimmer']['normalized'])
    
    # 6개 균등 가중치
    all_scores = [data['normalized'] for data in results.values()]
    equal_weight_score = np.mean(all_scores)
    
    # 상위 3개만
    top3_scores = sorted(all_scores, reverse=True)[:3]
    top3_score = np.mean(top3_scores)
    
    print(f"현재 방식 (HNR+Jitter+Shimmer): {current_score:.1f}")
    print(f"6개 균등 가중치:                {equal_weight_score:.1f}")
    print(f"상위 3개 평균:                  {top3_score:.1f}")
    
    print("\n💡 김범수는 깨끗한 음성이므로 +20 이상이 나와야 정상입니다!")
    
    return results

if __name__ == "__main__":
    audio_file = r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav"
    results = analyze_all_adduction_indicators(audio_file)