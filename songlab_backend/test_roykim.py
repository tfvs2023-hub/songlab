"""
로이킴 - As Is 보컬 분석 (Energy Distribution 방법)
"""

import numpy as np
import librosa
import soundfile as sf

def analyze_energy_distribution_refined(audio, sr):
    """개선된 Energy Distribution 분석"""
    try:
        # STFT 계산 (더 높은 해상도)
        D = librosa.stft(audio, n_fft=4096, hop_length=1024)
        magnitude = np.abs(D)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
        
        # 더 세밀한 주파수 대역 분할
        fundamental_band = (freqs >= 80) & (freqs <= 250)   # 기본주파수 (F0)
        low_harmonic = (freqs >= 250) & (freqs <= 600)     # 저차 배음
        mid_harmonic = (freqs >= 600) & (freqs <= 1200)    # 중차 배음
        high_harmonic = (freqs >= 1200) & (freqs <= 2400)  # 고차 배음
        formant_band = (freqs >= 2400) & (freqs <= 4800)   # 포먼트 영역
        
        # 각 프레임별 에너지 비율 계산
        energy_data = []
        for i in range(magnitude.shape[1]):
            spectrum = magnitude[:, i]
            
            fund_energy = np.sum(spectrum[fundamental_band])
            low_harm_energy = np.sum(spectrum[low_harmonic])
            mid_harm_energy = np.sum(spectrum[mid_harmonic])
            high_harm_energy = np.sum(spectrum[high_harmonic])
            formant_energy = np.sum(spectrum[formant_band])
            
            total_energy = (fund_energy + low_harm_energy + mid_harm_energy + 
                          high_harm_energy + formant_energy)
            
            if total_energy > 1e-10:
                energy_data.append({
                    'fundamental': fund_energy / total_energy,
                    'low_harmonic': low_harm_energy / total_energy,
                    'mid_harmonic': mid_harm_energy / total_energy,
                    'high_harmonic': high_harm_energy / total_energy,
                    'formant': formant_energy / total_energy
                })
        
        if energy_data:
            # 평균 에너지 분포 계산
            avg_fund = np.mean([d['fundamental'] for d in energy_data])
            avg_low_harm = np.mean([d['low_harmonic'] for d in energy_data])
            avg_mid_harm = np.mean([d['mid_harmonic'] for d in energy_data])
            avg_high_harm = np.mean([d['high_harmonic'] for d in energy_data])
            avg_formant = np.mean([d['formant'] for d in energy_data])
            
            # MR 제거 보컬 전용 성대내전 점수 계산
            
            # 기본주파수 + 저차배음 비율 (진성의 특징)
            low_freq_power = avg_fund + avg_low_harm
            
            # 고차배음 + 포먼트 비율 (가성의 특징)  
            high_freq_power = avg_high_harm + avg_formant
            
            # MR 제거 보컬 전용 임계값 (더 관대하게)
            if low_freq_power > 0.35:  # 저주파 에너지 35% 이상 = 진성
                voice_type = "chest_voice"
                base_score = 30
                adduction_score = base_score + (low_freq_power - 0.35) * 40
                
            elif high_freq_power > 0.45:  # 고주파 에너지 45% 이상 = 가성
                voice_type = "falsetto"
                base_score = -10
                adduction_score = base_score - (high_freq_power - 0.45) * 60
                
            else:  # 중간 영역 = 혼성
                voice_type = "mixed_voice"
                # 저주파 선호도에 따라 점수
                adduction_score = (low_freq_power - high_freq_power) * 50
            
            return {
                'fundamental_ratio': avg_fund,
                'low_harmonic_ratio': avg_low_harm, 
                'mid_harmonic_ratio': avg_mid_harm,
                'high_harmonic_ratio': avg_high_harm,
                'formant_ratio': avg_formant,
                'low_freq_power': low_freq_power,
                'high_freq_power': high_freq_power,
                'voice_type': voice_type,
                'adduction_score': np.clip(adduction_score, -50, 50)
            }
        else:
            return None
            
    except Exception as e:
        print(f"Energy analysis error: {e}")
        return None

def test_roykim_vocals():
    """로이킴 보컬 분석"""
    
    print("=" * 70)
    print("🎤 로이킴 - As Is 보컬 분석")
    print("=" * 70)
    
    try:
        audio_file = r"C:\Users\user\Desktop\vocals_extracted\로이킴_로이킴 - As Is_보컬.wav"
        
        # 오디오 로드
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
        
        print("\n🔍 에너지 분포 분석 중...")
        
        # Energy Distribution 분석
        result = analyze_energy_distribution_refined(audio_data, sr)
        
        if result:
            print("\n" + "=" * 70)
            print("📊 세밀한 주파수 에너지 분포")
            print("=" * 70)
            
            print(f"\n🎵 주파수 대역별 에너지 비율:")
            print(f"   기본주파수 (80-250Hz):     {result['fundamental_ratio']:.3f}")
            print(f"   저차 배음 (250-600Hz):     {result['low_harmonic_ratio']:.3f}")
            print(f"   중차 배음 (600-1200Hz):    {result['mid_harmonic_ratio']:.3f}")
            print(f"   고차 배음 (1200-2400Hz):   {result['high_harmonic_ratio']:.3f}")
            print(f"   포먼트 (2400-4800Hz):      {result['formant_ratio']:.3f}")
            
            print(f"\n🎯 통합 지표:")
            print(f"   저주파 파워: {result['low_freq_power']:.3f} (기본+저차배음)")
            print(f"   고주파 파워: {result['high_freq_power']:.3f} (고차배음+포먼트)")
            
            print(f"\n📈 분석 결과:")
            print(f"   음성 타입: {result['voice_type']}")
            print(f"   성대내전 점수: {result['adduction_score']:.1f} (-50~50)")
            
            # 평가
            score = result['adduction_score']
            if score > 25:
                evaluation = "매우 좋음 (강한 진성)"
            elif score > 10:
                evaluation = "좋음 (안정적 진성)"
            elif score > -10:
                evaluation = "보통 (혼성 또는 약한 진성)"
            elif score > -25:
                evaluation = "나쁨 (가성 의심)"
            else:
                evaluation = "매우 나쁨 (확실한 가성)"
                
            print(f"   종합 평가: {evaluation}")
            
            # 다른 보컬과 비교
            print("\n" + "=" * 70)
            print("📊 다른 보컬과 비교")
            print("=" * 70)
            
            print(f"\n{'파일':<25} | {'저주파파워':<8} | {'점수':<6} | 평가")
            print("-" * 65)
            print(f"김범수-DearLove        | 0.562     | 38.5   | 매우좋음")
            print(f"kakaotalk             | 0.609     | 40.4   | 매우좋음")
            print(f"가성_가성비브라토       | 0.348     | 1.6    | 혼성")
            print(f"로이킴-AsIs           | {result['low_freq_power']:.3f}     | {result['adduction_score']:5.1f}  | {evaluation[:4]}")
            
            # 로이킴 특성 분석
            print(f"\n💡 로이킴 보컬 특성:")
            
            if result['voice_type'] == 'chest_voice':
                print(f"   - 진성 위주의 안정적인 발성")
                if result['low_freq_power'] > 0.5:
                    print(f"   - 저주파 에너지가 풍부한 두꺼운 음색")
                else:
                    print(f"   - 적당한 두께의 균형잡힌 음색")
            elif result['voice_type'] == 'mixed_voice':
                print(f"   - 혼성 발성 (진성+가성 혼합)")
                print(f"   - 현대적이고 유연한 보컬 스타일")
            else:
                print(f"   - 가성 위주의 부드러운 발성")
                
            if result['mid_harmonic_ratio'] > 0.2:
                print(f"   - 중음역대가 풍부한 음색 (포근함)")
            if result['formant_ratio'] > 0.15:
                print(f"   - 고음역대가 밝은 음색 (투명함)")
            
            return result
        else:
            print("❌ 에너지 분포 분석 실패")
            return None
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_roykim_vocals()
    if result:
        print("\n✅ 로이킴 보컬 분석 완료!")