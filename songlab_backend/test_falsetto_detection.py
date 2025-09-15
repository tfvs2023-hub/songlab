"""
가성/진성 구분 3가지 방법 테스트
"""

import numpy as np
import librosa
import soundfile as sf
import parselmouth
from parselmouth.praat import call

def method1_hnr_fixed(audio, sr):
    """방법 1: HNR 계산 문제 해결"""
    try:
        # 원본 샘플링 레이트 유지 (리샘플링 안 함)
        sound = parselmouth.Sound(audio, sampling_frequency=sr)
        
        # HNR 계산 (더 관대한 설정)
        harmonicity = sound.to_harmonicity(
            time_step=0.01,  # 10ms 간격
            minimum_pitch=75,  # 더 낮은 최소 피치
            silence_threshold=0.1,
            periods_per_window=1.0
        )
        
        hnr_values = harmonicity.values
        valid_hnr = hnr_values[~np.isnan(hnr_values)]
        
        if len(valid_hnr) > 0:
            hnr_mean = np.mean(valid_hnr)
            hnr_std = np.std(valid_hnr)
            
            # 가성/진성 구분 기준
            if hnr_mean < 5:  # 낮은 HNR = 가성 가능성
                voice_type = "falsetto_suspected"
                adduction_score = max(-30, hnr_mean * 5 - 10)
            else:  # 높은 HNR = 진성
                voice_type = "chest_voice"
                adduction_score = min(40, (hnr_mean - 5) * 8)
                
            return {
                'hnr_mean': hnr_mean,
                'hnr_std': hnr_std,
                'voice_type': voice_type,
                'adduction_score': adduction_score,
                'method': 'HNR_Fixed'
            }
        else:
            return {'hnr_mean': 0, 'voice_type': 'unknown', 'adduction_score': 0, 'method': 'HNR_Fixed'}
            
    except Exception as e:
        print(f"HNR 계산 오류: {e}")
        return {'hnr_mean': 0, 'voice_type': 'error', 'adduction_score': 0, 'method': 'HNR_Fixed'}

def method2_zcr_spectral_slope(audio, sr):
    """방법 2: ZCR + Spectral Slope 조합"""
    try:
        # ZCR 계산
        zcr = librosa.feature.zero_crossing_rate(audio, frame_length=1024, hop_length=512)[0]
        zcr_mean = np.mean(zcr)
        
        # Spectral Slope 계산
        D = librosa.stft(audio, n_fft=1024, hop_length=512)
        magnitude = np.abs(D)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
        
        # 각 프레임별 spectral slope
        slopes = []
        for i in range(magnitude.shape[1]):
            spectrum = magnitude[:, i]
            if np.sum(spectrum) > 1e-10:
                # 로그 스케일로 변환
                log_spectrum = np.log(spectrum + 1e-10)
                log_freqs = np.log(freqs + 1e-10)
                
                # 선형 회귀로 기울기 계산
                slope = np.polyfit(log_freqs[1:], log_spectrum[1:], 1)[0]
                slopes.append(slope)
        
        slope_mean = np.mean(slopes) if slopes else 0
        
        # 가성/진성 구분
        # 가성: 높은 ZCR, 완만한 기울기 (고주파 에너지 상대적으로 많음)
        # 진성: 낮은 ZCR, 급한 기울기 (저주파 에너지 많음)
        
        if zcr_mean > 0.02 and slope_mean > -3:  # 가성 특징
            voice_type = "falsetto"
            adduction_score = -20 - (zcr_mean - 0.02) * 1000
        elif zcr_mean < 0.01 and slope_mean < -5:  # 진성 특징
            voice_type = "chest_voice"  
            adduction_score = 30 - zcr_mean * 2000
        else:  # 중간 영역
            voice_type = "mixed_voice"
            adduction_score = 10 - zcr_mean * 500
        
        return {
            'zcr_mean': zcr_mean,
            'slope_mean': slope_mean,
            'voice_type': voice_type,
            'adduction_score': np.clip(adduction_score, -50, 50),
            'method': 'ZCR_Spectral_Slope'
        }
        
    except Exception as e:
        print(f"ZCR+Slope 계산 오류: {e}")
        return {'zcr_mean': 0, 'slope_mean': 0, 'voice_type': 'error', 'adduction_score': 0, 'method': 'ZCR_Spectral_Slope'}

def method3_energy_distribution(audio, sr):
    """방법 3: 주파수별 에너지 분포 분석"""
    try:
        # STFT 계산
        D = librosa.stft(audio, n_fft=2048, hop_length=512)
        magnitude = np.abs(D)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
        
        # 주파수 대역별 에너지
        low_band = (freqs >= 80) & (freqs <= 300)    # 저주파 (성대 진동)
        mid_band = (freqs >= 300) & (freqs <= 1000)  # 중주파 (포먼트)
        high_band = (freqs >= 1000) & (freqs <= 4000) # 고주파 (배음)
        
        # 각 프레임별 에너지 비율 계산
        energy_ratios = []
        for i in range(magnitude.shape[1]):
            spectrum = magnitude[:, i]
            
            low_energy = np.sum(spectrum[low_band])
            mid_energy = np.sum(spectrum[mid_band])
            high_energy = np.sum(spectrum[high_band])
            
            total_energy = low_energy + mid_energy + high_energy
            
            if total_energy > 1e-10:
                low_ratio = low_energy / total_energy
                mid_ratio = mid_energy / total_energy
                high_ratio = high_energy / total_energy
                
                energy_ratios.append({
                    'low': low_ratio,
                    'mid': mid_ratio,
                    'high': high_ratio
                })
        
        if energy_ratios:
            avg_low = np.mean([r['low'] for r in energy_ratios])
            avg_mid = np.mean([r['mid'] for r in energy_ratios])
            avg_high = np.mean([r['high'] for r in energy_ratios])
            
            # 가성/진성 구분
            # 진성: 저주파 에너지 높음
            # 가성: 중/고주파 에너지 상대적으로 높음
            
            if avg_low > 0.4:  # 저주파 에너지가 40% 이상
                voice_type = "chest_voice"
                adduction_score = 20 + (avg_low - 0.4) * 50
            elif avg_high > 0.3:  # 고주파 에너지가 30% 이상
                voice_type = "falsetto"
                adduction_score = -10 - (avg_high - 0.3) * 100
            else:
                voice_type = "mixed_voice"
                adduction_score = 5
                
            return {
                'low_ratio': avg_low,
                'mid_ratio': avg_mid,
                'high_ratio': avg_high,
                'voice_type': voice_type,
                'adduction_score': np.clip(adduction_score, -50, 50),
                'method': 'Energy_Distribution'
            }
        else:
            return {'voice_type': 'error', 'adduction_score': 0, 'method': 'Energy_Distribution'}
            
    except Exception as e:
        print(f"Energy Distribution 계산 오류: {e}")
        return {'voice_type': 'error', 'adduction_score': 0, 'method': 'Energy_Distribution'}

def test_all_methods(audio_file):
    """3가지 방법 모두 테스트"""
    
    print("=" * 70)
    print("🔬 가성/진성 구분 3가지 방법 테스트")
    print("=" * 70)
    
    try:
        # 오디오 로드
        audio_data, sr = sf.read(audio_file)
        print(f"🎵 파일: {audio_file.split('\\')[-1]}")
        print(f"   길이: {len(audio_data)/sr:.1f}초, 샘플링: {sr}Hz")
        
        # 모노 변환
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        print("\n" + "=" * 70)
        print("📊 3가지 방법 분석 결과")
        print("=" * 70)
        
        # 방법 1: HNR 수정
        print("\n🎯 방법 1: HNR 계산 개선")
        result1 = method1_hnr_fixed(audio_data, sr)
        print(f"   HNR 평균: {result1.get('hnr_mean', 0):.2f} dB")
        print(f"   음성 타입: {result1.get('voice_type', 'unknown')}")
        print(f"   성대내전 점수: {result1.get('adduction_score', 0):.1f}")
        
        # 방법 2: ZCR + Spectral Slope
        print("\n🎯 방법 2: ZCR + Spectral Slope")
        result2 = method2_zcr_spectral_slope(audio_data, sr)
        print(f"   ZCR 평균: {result2.get('zcr_mean', 0):.6f}")
        print(f"   Spectral Slope: {result2.get('slope_mean', 0):.3f}")
        print(f"   음성 타입: {result2.get('voice_type', 'unknown')}")
        print(f"   성대내전 점수: {result2.get('adduction_score', 0):.1f}")
        
        # 방법 3: Energy Distribution
        print("\n🎯 방법 3: 주파수 에너지 분포")
        result3 = method3_energy_distribution(audio_data, sr)
        print(f"   저주파 비율: {result3.get('low_ratio', 0):.3f}")
        print(f"   중주파 비율: {result3.get('mid_ratio', 0):.3f}")
        print(f"   고주파 비율: {result3.get('high_ratio', 0):.3f}")
        print(f"   음성 타입: {result3.get('voice_type', 'unknown')}")
        print(f"   성대내전 점수: {result3.get('adduction_score', 0):.1f}")
        
        # 종합 결과
        print("\n" + "=" * 70)
        print("📈 종합 비교")
        print("=" * 70)
        
        results = [result1, result2, result3]
        
        print(f"\n{'방법':<20} | {'음성타입':<15} | {'점수':<6} | 평가")
        print("-" * 60)
        
        for result in results:
            method = result.get('method', 'Unknown')
            voice_type = result.get('voice_type', 'unknown')
            score = result.get('adduction_score', 0)
            
            if score > 20:
                evaluation = "진성"
            elif score > -10:
                evaluation = "혼성"
            else:
                evaluation = "가성"
                
            print(f"{method:<20} | {voice_type:<15} | {score:<6.1f} | {evaluation}")
        
        return results
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 3개 파일로 테스트
    files = [
        r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav",  # 진성
        r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a",      # 진성(허스키)
        r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav"                    # 가성
    ]
    
    for audio_file in files:
        print(f"\n{'='*10} {audio_file.split('\\')[-1]} {'='*10}")
        results = test_all_methods(audio_file)
        if results:
            print("✅ 분석 완료!")
        print("\n")