"""
Energy Distribution만 사용한 성대내전 분석 (신뢰할 만한 지표만)
"""

import numpy as np
import librosa
import soundfile as sf
import subprocess
import tempfile
import os

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

def test_energy_only_method(audio_file):
    """Energy Distribution만 사용한 분석"""
    
    print("=" * 70)
    print("🎯 Energy Distribution 전용 성대내전 분석")
    print("=" * 70)
    
    try:
        # 오디오 로드 (M4A 지원)
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
    # 3개 파일로 테스트
    files = [
        r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav",  # 진성
        r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a",      # 진성(허스키)
        r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav"                    # 가성
    ]
    
    results = []
    for audio_file in files:
        print(f"\n{'='*10} {audio_file.split('\\')[-1]} {'='*10}")
        result = test_energy_only_method(audio_file)
        if result:
            results.append({
                'file': audio_file.split('\\')[-1],
                'voice_type': result['voice_type'],
                'score': result['adduction_score'],
                'low_power': result['low_freq_power'],
                'high_power': result['high_freq_power']
            })
            print("✅ 분석 완료!")
        print("\n")
    
    # 최종 비교
    if results:
        print("=" * 70)
        print("🏆 최종 비교 결과")
        print("=" * 70)
        
        print(f"\n{'파일':<25} | {'음성타입':<12} | {'점수':<6} | {'저주파':<6} | {'고주파':<6} | 평가")
        print("-" * 80)
        
        for r in results:
            if r['score'] > 10:
                evaluation = "진성"
            elif r['score'] > -10:
                evaluation = "혼성"
            else:
                evaluation = "가성"
                
            print(f"{r['file']:<25} | {r['voice_type']:<12} | {r['score']:<6.1f} | {r['low_power']:<6.3f} | {r['high_power']:<6.3f} | {evaluation}")