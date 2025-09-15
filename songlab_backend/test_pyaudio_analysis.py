"""
PyAudioAnalysis로 성대내전 관련 특징 추출
"""

import numpy as np
import soundfile as sf
import subprocess
import tempfile
import os
from pyAudioAnalysis import audioBasicIO
from pyAudioAnalysis import ShortTermFeatures
import warnings
warnings.filterwarnings('ignore')

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

def extract_voice_quality_features(audio_file):
    """PyAudioAnalysis로 음성 품질 특징 추출"""
    
    print("=" * 70)
    print("🔬 PyAudioAnalysis 음성 품질 분석")
    print("=" * 70)
    
    try:
        # 오디오 로드 (M4A 지원)
        if audio_file.endswith('.m4a'):
            print("🔄 M4A → WAV 변환 중...")
            wav_path = convert_m4a_to_wav(audio_file)
            
            if not wav_path:
                print("📁 soundfile로 직접 로드...")
                audio_data, sr = sf.read(audio_file)
                
                # WAV 파일로 임시 저장 (PyAudioAnalysis 때문에)
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_wav_path = temp_wav.name
                temp_wav.close()
                
                sf.write(temp_wav_path, audio_data, sr)
                wav_path = temp_wav_path
            
        else:
            wav_path = audio_file
        
        print(f"🎵 파일: {audio_file.split('\\')[-1]}")
        
        # PyAudioAnalysis로 오디오 로드
        [Fs, x] = audioBasicIO.read_audio_file(wav_path)
        print(f"   길이: {len(x)/Fs:.1f}초, 샘플링: {Fs}Hz")
        
        # 모노 변환
        if x.ndim > 1:
            x = np.mean(x, axis=1)
        
        # 처음 30초만 분석
        max_samples = int(30 * Fs)
        if len(x) > max_samples:
            x = x[:max_samples]
            print("   (처음 30초만 분석)")
        
        # Short-term features 추출
        print("\n🔍 Short-term features 추출 중...")
        
        # 윈도우 크기 설정 (50ms 윈도우, 25ms 스텝)
        win = 0.050
        step = 0.025
        
        # 특징 추출
        [f, f_names] = ShortTermFeatures.feature_extraction(x, Fs, win * Fs, step * Fs)
        
        print(f"   추출된 특징 수: {len(f_names)}")
        print(f"   프레임 수: {f.shape[1]}")
        
        # 성대내전 관련 특징들 선별
        relevant_features = {
            'zcr': None,                    # Zero Crossing Rate
            'energy': None,                 # Energy
            'entropy': None,                # Spectral Entropy
            'spectral_centroid': None,      # Spectral Centroid
            'spectral_rolloff': None,       # Spectral Rolloff
            'spectral_flux': None,          # Spectral Flux
            'mfcc_1': None,                 # 1st MFCC
            'mfcc_2': None,                 # 2nd MFCC
            'chroma_1': None,               # 1st Chroma
            'harmonic_ratio': None,         # Harmonic Ratio (HNR과 유사)
        }
        
        # 특징 매핑
        for i, name in enumerate(f_names):
            if 'zcr' in name.lower():
                relevant_features['zcr'] = np.mean(f[i, :])
            elif 'energy' in name.lower():
                relevant_features['energy'] = np.mean(f[i, :])
            elif 'spectral_entropy' in name.lower():
                relevant_features['entropy'] = np.mean(f[i, :])
            elif 'spectral_centroid' in name.lower():
                relevant_features['spectral_centroid'] = np.mean(f[i, :])
            elif 'spectral_rolloff' in name.lower():
                relevant_features['spectral_rolloff'] = np.mean(f[i, :])
            elif 'spectral_flux' in name.lower():
                relevant_features['spectral_flux'] = np.mean(f[i, :])
            elif 'mfcc_1' in name.lower():
                relevant_features['mfcc_1'] = np.mean(f[i, :])
            elif 'mfcc_2' in name.lower():
                relevant_features['mfcc_2'] = np.mean(f[i, :])
            elif 'chroma_1' in name.lower():
                relevant_features['chroma_1'] = np.mean(f[i, :])
            elif 'harmonic' in name.lower():
                relevant_features['harmonic_ratio'] = np.mean(f[i, :])
        
        print("\n" + "=" * 70)
        print("📊 성대내전 관련 특징 분석")
        print("=" * 70)
        
        print(f"\n🎯 추출된 특징들:")
        for feature_name, value in relevant_features.items():
            if value is not None:
                print(f"   {feature_name:<20}: {value:.6f}")
            else:
                print(f"   {feature_name:<20}: 추출 실패")
        
        # 성대내전 점수 계산 (PyAudioAnalysis 특징 기반)
        print(f"\n🎯 성대내전 점수 계산:")
        
        adduction_score = 0
        valid_features = 0
        
        # ZCR (낮을수록 좋음)
        if relevant_features['zcr'] is not None:
            zcr_score = np.clip(30 - relevant_features['zcr'] * 10000, -30, 30)
            adduction_score += zcr_score
            valid_features += 1
            print(f"   ZCR 기여: {zcr_score:.1f}")
        
        # Spectral Entropy (낮을수록 좋음)
        if relevant_features['entropy'] is not None:
            entropy_score = np.clip(30 - relevant_features['entropy'] * 50, -30, 30)
            adduction_score += entropy_score
            valid_features += 1
            print(f"   Entropy 기여: {entropy_score:.1f}")
        
        # Harmonic Ratio (높을수록 좋음, HNR과 유사)
        if relevant_features['harmonic_ratio'] is not None:
            harmonic_score = np.clip(relevant_features['harmonic_ratio'] * 100 - 10, -30, 30)
            adduction_score += harmonic_score
            valid_features += 1
            print(f"   Harmonic Ratio 기여: {harmonic_score:.1f}")
        
        # Energy (적당한 값이 좋음)
        if relevant_features['energy'] is not None:
            if 0.1 < relevant_features['energy'] < 0.8:
                energy_score = 15
            elif 0.05 < relevant_features['energy'] < 1.0:
                energy_score = 5
            else:
                energy_score = -10
            adduction_score += energy_score
            valid_features += 1
            print(f"   Energy 기여: {energy_score:.1f}")
        
        # Spectral Flux (낮을수록 안정적)
        if relevant_features['spectral_flux'] is not None:
            flux_score = np.clip(20 - relevant_features['spectral_flux'] * 1000, -20, 20)
            adduction_score += flux_score
            valid_features += 1
            print(f"   Spectral Flux 기여: {flux_score:.1f}")
        
        if valid_features > 0:
            final_score = adduction_score / valid_features
        else:
            final_score = 0
        
        print(f"   최종 점수: {final_score:.1f} (-50~50)")
        print(f"   사용된 특징 수: {valid_features}")
        
        # 평가
        if final_score > 20:
            evaluation = "매우 좋음 (완벽한 성대접촉)"
        elif final_score > 10:
            evaluation = "좋음 (안정적 진성)"
        elif final_score > 0:
            evaluation = "보통 (평균적)"
        elif final_score > -15:
            evaluation = "나쁨 (허스키함)"
        else:
            evaluation = "매우 나쁨 (심각한 허스키함)"
        
        print(f"   평가: {evaluation}")
        
        # 임시 파일 정리
        if audio_file.endswith('.m4a') and wav_path != audio_file:
            try:
                os.unlink(wav_path)
            except:
                pass
        
        return {
            'features': relevant_features,
            'adduction_score': final_score,
            'evaluation': evaluation,
            'valid_features': valid_features
        }
        
    except Exception as e:
        print(f"❌ PyAudioAnalysis 분석 오류: {str(e)}")
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
    
    all_results = []
    for audio_file in files:
        print(f"\n{'='*10} {audio_file.split('\\')[-1]} {'='*10}")
        result = extract_voice_quality_features(audio_file)
        if result:
            all_results.append({
                'file': audio_file.split('\\')[-1],
                'score': result['adduction_score'],
                'evaluation': result['evaluation'],
                'valid_features': result['valid_features']
            })
            print("✅ 분석 완료!")
        print("\n")
    
    # 최종 비교
    if all_results:
        print("=" * 70)
        print("🏆 PyAudioAnalysis 최종 비교")
        print("=" * 70)
        
        print(f"\n{'파일':<30} | {'점수':<6} | {'특징수':<5} | 평가")
        print("-" * 70)
        
        for r in all_results:
            print(f"{r['file']:<30} | {r['score']:<6.1f} | {r['valid_features']:<5} | {r['evaluation']}")
        
        print(f"\n💡 PyAudioAnalysis vs Energy Distribution 비교:")
        print(f"   김범수: PyAudio={all_results[0]['score']:.1f} vs Energy=38.5")
        print(f"   가성:   PyAudio={all_results[2]['score']:.1f} vs Energy=1.6")