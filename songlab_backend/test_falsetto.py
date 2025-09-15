"""
가성 비브라토 파일 - 3개 지표 성대내전 분석
"""

import numpy as np
import librosa
import soundfile as sf
from scipy.stats import entropy

def analyze_falsetto_adduction(audio_file):
    """가성 파일 성대내전 분석"""
    
    print("=" * 60)
    print("🎭 가성 비브라토 - 성대내전 분석")
    print("=" * 60)
    
    try:
        # 오디오 로드
        audio_data, sr = sf.read(audio_file)
        print(f"🎵 파일: {audio_file.split('\\')[-1]}")
        print(f"   길이: {len(audio_data)/sr:.1f}초, 샘플링: {sr}Hz")
        
        # 모노 변환
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        print("\n🔍 3개 핵심 지표 분석 중...")
        
        # 1. Spectral Tilt (스펙트럼 기울기)
        print("\n🎯 1. Spectral Tilt (스펙트럼 기울기)")
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
            tilt_score = np.clip(30 - np.log10(tilt_ratio + 0.1) * 15, -50, 50)
        else:
            tilt_ratio = 0
            tilt_score = -50
            
        print(f"   저주파/고주파 비율: {tilt_ratio:.3f}")
        print(f"   점수: {tilt_score:.1f} (-50~50)")
        
        # 2. Spectral Entropy (스펙트럼 무질서도)
        print("\n🎯 2. Spectral Entropy (스펙트럼 무질서도)")
        D_entropy = librosa.stft(audio_data, n_fft=1024, hop_length=256)
        magnitude_entropy = np.abs(D_entropy)
        
        # 각 프레임별 스펙트럼 엔트로피
        entropies = []
        for i in range(magnitude_entropy.shape[1]):
            spectrum = magnitude_entropy[:, i]
            if np.sum(spectrum) > 1e-10:
                spectrum_norm = spectrum / np.sum(spectrum)
                spectrum_norm = spectrum_norm[spectrum_norm > 1e-10]
                if len(spectrum_norm) > 1:
                    ent = entropy(spectrum_norm)
                    entropies.append(ent)
        
        if entropies:
            entropy_mean = np.mean(entropies)
            entropy_score = np.clip(40 - entropy_mean * 8, -50, 50)
        else:
            entropy_mean = 0
            entropy_score = 0
            
        print(f"   평균 엔트로피: {entropy_mean:.4f} (낮을수록 좋음)")
        print(f"   점수: {entropy_score:.1f} (-50~50)")
        
        # 3. Formant Bandwidth (포먼트 선명도)
        print("\n🎯 3. Formant Bandwidth (포먼트 선명도)")
        # 첫 번째 포먼트 추정
        formants = librosa.feature.spectral_centroid(y=audio_data, sr=sr)[0]
        formant_mean = np.mean(formants)
        
        # 스펙트럴 롤오프로 대역폭 추정
        rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=sr, roll_percent=0.85)[0]
        rolloff_mean = np.mean(rolloff)
        
        # 대역폭 계산
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
        print(f"   점수: {bandwidth_score:.1f} (-50~50)")
        
        # 종합 결과
        print("\n" + "=" * 60)
        print("📊 종합 성대내전 분석")
        print("=" * 60)
        
        # 3개 지표 조합
        combined_score = (tilt_score + entropy_score + bandwidth_score) / 3
        
        print(f"\n🎯 3개 지표 결과:")
        print(f"   Spectral Tilt:     {tilt_score:6.1f}")
        print(f"   Spectral Entropy:  {entropy_score:6.1f}")
        print(f"   Formant Bandwidth: {bandwidth_score:6.1f}")
        print(f"   ─────────────────────────")
        print(f"   평균 점수:         {combined_score:6.1f}")
        
        # 평가
        if combined_score > 30:
            evaluation = "매우 좋음 (완벽한 성대접촉)"
        elif combined_score > 20:
            evaluation = "좋음 (프로 수준)"
        elif combined_score > 10:
            evaluation = "양호 (안정적)"
        elif combined_score > 0:
            evaluation = "보통 (평균적)"
        elif combined_score > -20:
            evaluation = "나쁨 (허스키함)"
        else:
            evaluation = "매우 나쁨 (심각한 공기누설)"
        
        print(f"   평가: {evaluation}")
        
        # 비교 분석
        print("\n" + "=" * 60)
        print("📈 다른 보컬과 비교")
        print("=" * 60)
        
        print(f"\n파일                    | 3개지표평균 | 평가")
        print("-" * 55)
        print(f"김범수-DearLove        |    20.1     | 좋음(프로수준)")
        print(f"kakaotalk              |    14.6     | 양호(안정적)")
        print(f"가성_가성비브라토       |    {combined_score:5.1f}     | {evaluation[:6]}")
        
        # 가성 특성 분석
        print(f"\n💡 가성(Falsetto) 특성:")
        print(f"   - 가성은 성대가 부분적으로만 접촉")
        print(f"   - 일반적으로 진성보다 낮은 성대내전 점수")
        print(f"   - 비브라토는 F0 변동으로 점수에 영향 가능")
        
        if combined_score < 10:
            print(f"   → 예상대로 가성 특성을 잘 반영한 결과")
        else:
            print(f"   → 가성치고는 높은 점수 (혼성 또는 강한 가성)")
        
        return {
            'tilt_score': tilt_score,
            'entropy_score': entropy_score,
            'bandwidth_score': bandwidth_score,
            'combined_score': combined_score,
            'evaluation': evaluation
        }
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    audio_file = r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav"
    results = analyze_falsetto_adduction(audio_file)