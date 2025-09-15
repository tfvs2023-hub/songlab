"""
Energy Distribution 가중치 튜닝 - 원하는 결과 도출
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

def extract_all_features(audio, sr):
    """모든 필요한 특징 추출"""
    try:
        # STFT 계산
        D = librosa.stft(audio, n_fft=4096, hop_length=1024)
        magnitude = np.abs(D)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
        
        # 주파수 대역별 에너지
        fundamental_band = (freqs >= 80) & (freqs <= 250)
        low_harmonic = (freqs >= 250) & (freqs <= 600)
        mid_harmonic = (freqs >= 600) & (freqs <= 1200)
        high_harmonic = (freqs >= 1200) & (freqs <= 2400)
        formant_band = (freqs >= 2400) & (freqs <= 4800)
        
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
        
        if not energy_data:
            return None
        
        # 평균 계산
        avg_fund = np.mean([d['fundamental'] for d in energy_data])
        avg_low_harm = np.mean([d['low_harmonic'] for d in energy_data])
        avg_mid_harm = np.mean([d['mid_harmonic'] for d in energy_data])
        avg_high_harm = np.mean([d['high_harmonic'] for d in energy_data])
        avg_formant = np.mean([d['formant'] for d in energy_data])
        
        # 추가 특징들
        # ZCR (허스키함 감지)
        zcr = librosa.feature.zero_crossing_rate(audio, frame_length=2048, hop_length=512)[0]
        zcr_mean = np.mean(zcr)
        
        # Spectral Entropy (노이즈 감지)
        D_entropy = librosa.stft(audio, n_fft=1024, hop_length=256)
        magnitude_entropy = np.abs(D_entropy)
        entropies = []
        for i in range(magnitude_entropy.shape[1]):
            spectrum = magnitude_entropy[:, i]
            if np.sum(spectrum) > 1e-10:
                spectrum_norm = spectrum / np.sum(spectrum)
                spectrum_norm = spectrum_norm[spectrum_norm > 1e-10]
                if len(spectrum_norm) > 1:
                    from scipy.stats import entropy
                    ent = entropy(spectrum_norm)
                    entropies.append(ent)
        
        entropy_mean = np.mean(entropies) if entropies else 0
        
        # Spectral Centroid (음색 밝기)
        spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        centroid_mean = np.mean(spectral_centroid)
        
        return {
            'fundamental_ratio': avg_fund,
            'low_harmonic_ratio': avg_low_harm,
            'mid_harmonic_ratio': avg_mid_harm,
            'high_harmonic_ratio': avg_high_harm,
            'formant_ratio': avg_formant,
            'low_freq_power': avg_fund + avg_low_harm,
            'high_freq_power': avg_high_harm + avg_formant,
            'zcr_mean': zcr_mean,
            'entropy_mean': entropy_mean,
            'centroid_mean': centroid_mean,
            'sr': sr
        }
        
    except Exception as e:
        print(f"Feature extraction error: {e}")
        return None

def calculate_adduction_score(features, method="v1"):
    """다양한 방법으로 성대내전 점수 계산"""
    
    if not features:
        return 0, "error"
    
    low_power = features['low_freq_power']
    high_power = features['high_freq_power']
    zcr = features['zcr_mean']
    entropy = features['entropy_mean']
    centroid = features['centroid_mean']
    sr = features['sr']
    
    if method == "v1":
        # 원래 방법 (기본)
        if low_power > 0.35:
            score = 30 + (low_power - 0.35) * 40
            voice_type = "chest_voice"
        elif high_power > 0.45:
            score = -10 - (high_power - 0.45) * 60
            voice_type = "falsetto"
        else:
            score = (low_power - high_power) * 50
            voice_type = "mixed_voice"
            
    elif method == "v2":
        # 허스키함 패널티 추가
        base_score = (low_power - high_power) * 60
        
        # ZCR 패널티 (허스키함)
        zcr_penalty = zcr * 1000  # 높은 ZCR = 허스키함
        
        # 엔트로피 패널티 (노이즈)
        entropy_penalty = max(0, (entropy - 3.5) * 10)
        
        score = base_score - zcr_penalty - entropy_penalty
        
        if score > 20:
            voice_type = "chest_voice"
        elif score > -10:
            voice_type = "mixed_voice"
        else:
            voice_type = "falsetto"
            
    elif method == "v3":
        # 샘플링 레이트 정규화 + 허스키함 보정
        
        # 샘플링 레이트 보정 (16kHz는 불리)
        sr_factor = sr / 44100  # 44kHz 기준으로 정규화
        
        # 기본 점수
        base_score = (low_power - high_power) * 50 * sr_factor
        
        # 허스키함 보정 (ZCR + Entropy)
        breathiness = (zcr * 500) + max(0, (entropy - 3.0) * 5)
        
        score = base_score - breathiness
        
        if score > 15:
            voice_type = "chest_voice"
        elif score > -15:
            voice_type = "mixed_voice"
        else:
            voice_type = "falsetto"
            
    elif method == "v4":
        # 세밀한 가중치 조합
        
        # 주파수 대역별 가중 점수
        fund_score = features['fundamental_ratio'] * 60
        low_harm_score = features['low_harmonic_ratio'] * 40
        mid_harm_score = features['mid_harmonic_ratio'] * 20
        high_harm_score = features['high_harmonic_ratio'] * -30
        formant_score = features['formant_ratio'] * -40
        
        base_score = fund_score + low_harm_score + mid_harm_score + high_harm_score + formant_score
        
        # 허스키함 큰 패널티
        breathiness_penalty = (zcr * 800) + (max(0, entropy - 3.0) * 15)
        
        score = base_score - breathiness_penalty
        
        if score > 10:
            voice_type = "chest_voice"
        elif score > -20:
            voice_type = "mixed_voice"
        else:
            voice_type = "falsetto"
            
    elif method == "v5":
        # 극단적 보정 (kakaotalk과 가성 구분 강화)
        
        # 저주파 우위 점수
        low_dominance = low_power / (high_power + 0.1)  # 비율로 계산
        
        base_score = np.log(low_dominance + 0.1) * 30
        
        # 매우 강한 허스키함 패널티
        severe_breathiness = (zcr * 1500) + (max(0, entropy - 2.5) * 25)
        
        score = base_score - severe_breathiness
        
        if score > 5:
            voice_type = "chest_voice"
        elif score > -25:
            voice_type = "mixed_voice"  
        else:
            voice_type = "falsetto"
    
    return np.clip(score, -50, 50), voice_type

def test_all_weighting_methods():
    """모든 가중치 방법 테스트"""
    
    print("=" * 80)
    print("🔧 Energy Distribution 가중치 튜닝 - 5가지 방법 비교")
    print("=" * 80)
    
    # 테스트 파일들
    files = [
        (r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav", "김범수"),
        (r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a", "kakaotalk"),
        (r"C:\Users\user\Desktop\vocals_extracted\로이킴_로이킴 - As Is_보컬.wav", "로이킴"),
        (r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav", "가성비브라토")
    ]
    
    # 각 파일의 특징 추출
    all_features = {}
    
    for audio_file, name in files:
        print(f"\n🎵 {name} 특징 추출 중...")
        
        try:
            # 오디오 로드
            if audio_file.endswith('.m4a'):
                wav_path = convert_m4a_to_wav(audio_file)
                if wav_path:
                    audio_data, sr = sf.read(wav_path)
                    os.unlink(wav_path)
                else:
                    audio_data, sr = sf.read(audio_file)
            else:
                audio_data, sr = sf.read(audio_file)
            
            # 모노 변환
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # 처음 30초만
            max_samples = 30 * sr
            if len(audio_data) > max_samples:
                audio_data = audio_data[:max_samples]
            
            # 특징 추출
            features = extract_all_features(audio_data, sr)
            all_features[name] = features
            
            if features:
                print(f"   ✅ 성공 - SR: {sr}Hz, 저주파파워: {features['low_freq_power']:.3f}")
            else:
                print(f"   ❌ 실패")
                
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            all_features[name] = None
    
    # 5가지 방법으로 점수 계산
    methods = ["v1", "v2", "v3", "v4", "v5"]
    method_names = [
        "기본 (원래)",
        "허스키함 패널티",
        "SR정규화+보정", 
        "세밀한 가중치",
        "극단적 보정"
    ]
    
    print("\n" + "=" * 80)
    print("📊 5가지 방법 비교 결과")
    print("=" * 80)
    
    # 헤더 출력
    print(f"\n{'방법':<15} | {'김범수':<8} | {'kakatalk':<8} | {'로이킴':<8} | {'가성비브':<8} | 순서")
    print("-" * 80)
    
    for i, method in enumerate(methods):
        method_name = method_names[i]
        scores = []
        
        for name in ["김범수", "kakaotalk", "로이킴", "가성비브라토"]:
            if all_features.get(name):
                score, voice_type = calculate_adduction_score(all_features[name], method)
                scores.append((name, score))
            else:
                scores.append((name, 0))
        
        # 점수순 정렬 (높은 순)
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
        ranking = " > ".join([f"{s[0]}({s[1]:.1f})" for s in sorted_scores])
        
        print(f"{method_name:<15} | {scores[0][1]:<8.1f} | {scores[1][1]:<8.1f} | {scores[2][1]:<8.1f} | {scores[3][1]:<8.1f} | {ranking[:50]}")
    
    # 이상적인 순서 체크
    print(f"\n💡 이상적인 순서: 김범수(35-40) > kakaotalk(20-30) > 로이킴(-10~-20) > 가성비브(-20~-30)")
    
    # 각 방법별 상세 결과
    print(f"\n" + "=" * 80)
    print("🎯 방법별 상세 분석")
    print("=" * 80)
    
    for i, method in enumerate(methods):
        print(f"\n📈 방법 {i+1}: {method_names[i]}")
        
        for name in ["김범수", "kakaotalk", "로이킴", "가성비브라토"]:
            if all_features.get(name):
                score, voice_type = calculate_adduction_score(all_features[name], method)
                
                # 평가
                if score > 25:
                    eval_text = "매우좋음"
                elif score > 10:
                    eval_text = "좋음"
                elif score > -10:
                    eval_text = "보통"
                elif score > -25:
                    eval_text = "나쁨"
                else:
                    eval_text = "매우나쁨"
                
                print(f"   {name:<10}: {score:6.1f}점 ({voice_type:<12}) - {eval_text}")
        
        # 순서가 맞는지 체크
        scores_only = []
        for name in ["김범수", "kakaotalk", "로이킴", "가성비브라토"]:
            if all_features.get(name):
                score, _ = calculate_adduction_score(all_features[name], method)
                scores_only.append(score)
        
        if len(scores_only) == 4:
            # 이상적: 김범수 > kakaotalk > 로이킴 > 가성
            correct_order = (scores_only[0] > scores_only[1] > scores_only[2] > scores_only[3])
            reasonable_gaps = (
                scores_only[0] > 25 and  # 김범수 높음
                20 <= scores_only[1] <= 35 and  # kakaotalk 중간
                -25 <= scores_only[2] <= -5 and  # 로이킴 낮음
                scores_only[3] <= -15  # 가성 매우낮음
            )
            
            if correct_order and reasonable_gaps:
                print(f"   ✅ 이상적인 결과!")
            elif correct_order:
                print(f"   ⚠️ 순서는 맞지만 점수 범위 조정 필요")
            else:
                print(f"   ❌ 순서가 틀림")

if __name__ == "__main__":
    test_all_weighting_methods()