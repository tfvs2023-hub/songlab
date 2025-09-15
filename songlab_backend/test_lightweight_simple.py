"""
경량 보컬 분석기 - 간소화 버전 (FFmpeg 라우드니스 처리 제외)
"""

import numpy as np
import librosa
import soundfile as sf
import subprocess
import tempfile
import os
from scipy.stats import linregress
import warnings
warnings.filterwarnings('ignore')

def convert_m4a_to_wav(m4a_path):
    """M4A를 WAV로 변환 (간단 버전)"""
    try:
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        cmd = [
            'ffmpeg', '-i', m4a_path,
            '-ac', '1',  # 모노
            '-ar', '16000',  # 16kHz
            temp_wav_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return None
            
        return temp_wav_path
        
    except Exception as e:
        return None

def simple_preprocess(audio_file):
    """간단한 전처리"""
    try:
        if audio_file.endswith('.m4a'):
            wav_path = convert_m4a_to_wav(audio_file)
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
        if sr != 16000:
            audio = librosa.resample(y=audio, orig_sr=sr, target_sr=16000)
            sr = 16000
        
        # 간단한 정규화
        audio = audio / (np.max(np.abs(audio)) + 1e-10)
        
        return audio, sr
        
    except Exception as e:
        print(f"전처리 오류: {e}")
        return None, None

def extract_representative_chunks(audio, sr, num_chunks=12, top_chunks=6, chunk_duration=10):
    """대표 샘플 추출"""
    try:
        total_duration = len(audio) / sr
        chunk_samples = chunk_duration * sr
        
        chunks = []
        for i in range(num_chunks):
            start_time = i * total_duration / num_chunks
            start_sample = int(start_time * sr)
            end_sample = min(start_sample + chunk_samples, len(audio))
            
            if end_sample - start_sample < sr:  # 1초 미만이면 스킵
                continue
            
            chunk_audio = audio[start_sample:end_sample]
            
            # 간단한 품질 점수 (RMS + 피치 안정성)
            rms = np.sqrt(np.mean(chunk_audio ** 2))
            
            # 자기상관으로 피치 안정성 추정
            autocorr = np.correlate(chunk_audio, chunk_audio, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            if len(autocorr) > sr//50:  # 20Hz 이하 확인
                max_corr = np.max(autocorr[sr//400:sr//50])  # 50-400Hz 범위
                pitch_stability = max_corr / (autocorr[0] + 1e-10)
            else:
                pitch_stability = 0.1
            
            score = 0.7 * pitch_stability + 0.3 * rms
            
            chunks.append({
                'audio': chunk_audio,
                'score': score,
                'rms': rms,
                'pitch_stability': pitch_stability
            })
        
        # 상위 chunks 선택
        chunks.sort(key=lambda x: x['score'], reverse=True)
        return chunks[:top_chunks]
        
    except Exception as e:
        print(f"청크 추출 오류: {e}")
        return []

def calculate_light_features(audio, sr):
    """경량 특징 추출"""
    try:
        features = {}
        
        # 1. 간단한 HNR (자기상관 기반)
        autocorr = np.correlate(audio, audio, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        if len(autocorr) > sr//50:
            max_corr = np.max(autocorr[sr//400:sr//50])
            noise_level = 1 - max_corr / (autocorr[0] + 1e-10)
            hnr = 10 * np.log10((max_corr + 1e-10) / (noise_level + 1e-10))
            features['hnr'] = max(0, min(30, hnr))
        else:
            features['hnr'] = 10.0
        
        # 2. Spectral Tilt (300Hz-3kHz)
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1/sr)
        magnitude = np.abs(fft) + 1e-10
        
        mask = (freqs >= 300) & (freqs <= 3000)
        if np.sum(mask) > 10:
            freq_range = freqs[mask]
            mag_range = magnitude[mask]
            log_mag = 20 * np.log10(mag_range)
            log_freq = np.log10(freq_range)
            
            slope, _, _, _, _ = linregress(log_freq, log_mag)
            features['spectral_tilt'] = slope * np.log10(2)  # dB/octave
        else:
            features['spectral_tilt'] = -5.0
        
        # 3. Spectral Flatness
        geometric_mean = np.exp(np.mean(np.log(magnitude)))
        arithmetic_mean = np.mean(magnitude)
        features['spectral_flatness'] = geometric_mean / (arithmetic_mean + 1e-10)
        
        # 4. ZCR (간접적인 노이즈 지표)
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        features['zcr'] = np.mean(zcr)
        
        # 5. Spectral Centroid
        centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        features['spectral_centroid'] = np.mean(centroid)
        
        return features
        
    except Exception as e:
        print(f"특징 추출 오류: {e}")
        return {}

def calculate_clarity_score(all_features, source_hint="unknown"):
    """선명도 점수 계산"""
    try:
        # 특징들의 평균 계산
        feature_means = {}
        feature_names = ['hnr', 'spectral_tilt', 'spectral_flatness', 'zcr', 'spectral_centroid']
        
        for name in feature_names:
            values = [f.get(name, 0) for f in all_features if name in f]
            feature_means[name] = np.mean(values) if values else 0
        
        # 소스 보정
        if source_hint == "kakaotalk":
            feature_means['hnr'] -= 1.0  # 카톡은 HNR 낮게 보정
            feature_means['spectral_flatness'] += 0.02
        
        # 선명도 계산 (경험적 공식)
        hnr_score = (feature_means['hnr'] - 15) * 2  # HNR 15dB 기준
        tilt_score = -(feature_means['spectral_tilt'] + 8) * 3  # Tilt -8 기준  
        flatness_score = -(feature_means['spectral_flatness'] - 0.25) * 100  # 0.25 기준
        zcr_score = -(feature_means['zcr'] - 0.1) * 200  # 0.1 기준
        
        clarity = hnr_score + tilt_score + flatness_score + zcr_score
        
        # 0-100 범위로 정규화
        clarity_score = np.clip(clarity + 50, 0, 100)
        
        # 가성/허스키 캐핑
        if feature_means['hnr'] < 10:
            clarity_score = min(clarity_score, 60)
        
        # 등급 매기기
        if clarity_score >= 70:
            grade = "High"
        elif clarity_score >= 40:
            grade = "Medium"
        else:
            grade = "Low"
        
        # 태그
        brightness = "밝음" if feature_means['spectral_tilt'] > -6 else "어두움"
        roughness = "거침" if feature_means['zcr'] > 0.15 or feature_means['hnr'] < 12 else "부드러움"
        
        return {
            'clarity_score': clarity_score,
            'grade': grade,
            'brightness': brightness,
            'roughness': roughness,
            'raw_features': feature_means
        }
        
    except Exception as e:
        print(f"점수 계산 오류: {e}")
        return {}

def analyze_vocal_simple(audio_file, source_hint="unknown"):
    """간단한 보컬 분석"""
    
    filename = audio_file.split('/')[-1].split('\\')[-1]
    print(f"\n🎤 {filename} 분석 중...")
    
    # 1. 전처리
    audio, sr = simple_preprocess(audio_file)
    if audio is None:
        print("❌ 전처리 실패")
        return None
    
    print(f"   📊 길이: {len(audio)/sr:.1f}초, SR: {sr}Hz")
    
    # 2. 대표 청크 추출
    chunks = extract_representative_chunks(audio, sr)
    if not chunks:
        print("❌ 청크 추출 실패")
        return None
    
    print(f"   🎯 상위 {len(chunks)}개 청크 선택")
    
    # 3. 특징 추출
    all_features = []
    for chunk in chunks:
        features = calculate_light_features(chunk['audio'], sr)
        if features:
            all_features.append(features)
    
    if not all_features:
        print("❌ 특징 추출 실패")
        return None
    
    # 4. 점수 계산
    result = calculate_clarity_score(all_features, source_hint)
    
    if result:
        print(f"   ✅ 선명도: {result['clarity_score']:.1f} ({result['grade']})")
        print(f"   🏷️ 태그: {result['brightness']}, {result['roughness']}")
        
        # 주요 특징 출력
        features = result['raw_features']
        print(f"   📈 HNR: {features.get('hnr', 0):.1f}dB")
        print(f"   📉 Spectral Tilt: {features.get('spectral_tilt', 0):.1f}dB/oct")
        print(f"   📊 Flatness: {features.get('spectral_flatness', 0):.3f}")
    
    return result

def test_all_vocals():
    """모든 보컬 테스트"""
    
    print("=" * 70)
    print("🎤 경량 보컬 분석기 - 간소화 테스트")
    print("=" * 70)
    
    test_files = [
        (r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a", "kakaotalk"),
        (r"C:\Users\user\Desktop\vocals_extracted\로이킴_로이킴 - As Is_보컬.wav", "unknown"),
        (r"C:\Users\user\Documents\소리 녹음\가성_가성비브라토.wav", "unknown")
    ]
    
    results = []
    
    for audio_file, source_hint in test_files:
        result = analyze_vocal_simple(audio_file, source_hint)
        if result:
            filename = audio_file.split('/')[-1].split('\\')[-1]
            results.append({
                'file': filename[:20],
                'score': result['clarity_score'],
                'grade': result['grade'],
                'brightness': result['brightness'],
                'roughness': result['roughness']
            })
    
    # 최종 결과
    if results:
        print("\n" + "=" * 70)
        print("🏆 최종 결과")
        print("=" * 70)
        
        print(f"\n{'파일':<22} | {'선명도':<6} | {'등급':<6} | {'밝기':<6} | {'거침':<6}")
        print("-" * 65)
        
        for r in results:
            print(f"{r['file']:<22} | {r['score']:<6.1f} | {r['grade']:<6} | {r['brightness']:<6} | {r['roughness']:<6}")
        
        print(f"\n💡 예상 순서: 김범수 > kakaotalk > 로이킴 > 가성")
        sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
        actual_order = " > ".join([r['file'][:10] for r in sorted_results])
        print(f"💡 실제 순서: {actual_order}")

if __name__ == "__main__":
    test_all_vocals()