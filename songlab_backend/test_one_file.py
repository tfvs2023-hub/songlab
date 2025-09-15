"""
한 파일만 테스트 - 김범수
"""

import numpy as np
import soundfile as sf
from scipy.stats import linregress

def quick_analysis(audio_file):
    """빠른 분석"""
    
    print(f"🎤 {audio_file.split('\\')[-1]} 빠른 분석")
    
    try:
        # 오디오 로드 (처음 30초만)
        audio_data, sr = sf.read(audio_file, start=0, stop=30*44100)
        print(f"   로드: {len(audio_data)/sr:.1f}초, {sr}Hz")
        
        # 모노 변환
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 간단한 HNR
        autocorr = np.correlate(audio_data, audio_data, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        if len(autocorr) > sr//50:
            max_corr = np.max(autocorr[sr//400:sr//50])
            noise_level = 1 - max_corr / (autocorr[0] + 1e-10)
            hnr = 10 * np.log10((max_corr + 1e-10) / (noise_level + 1e-10))
            hnr = max(0, min(30, hnr))
        else:
            hnr = 10.0
        
        # FFT 기반 특징들
        fft = np.fft.rfft(audio_data)
        freqs = np.fft.rfftfreq(len(audio_data), 1/sr)
        magnitude = np.abs(fft) + 1e-10
        
        # Spectral Tilt
        mask = (freqs >= 300) & (freqs <= 3000)
        if np.sum(mask) > 10:
            freq_range = freqs[mask]
            mag_range = magnitude[mask]
            log_mag = 20 * np.log10(mag_range)
            log_freq = np.log10(freq_range)
            
            slope, _, _, _, _ = linregress(log_freq, log_mag)
            spectral_tilt = slope * np.log10(2)
        else:
            spectral_tilt = -5.0
        
        # Spectral Flatness
        geometric_mean = np.exp(np.mean(np.log(magnitude)))
        arithmetic_mean = np.mean(magnitude)
        spectral_flatness = geometric_mean / (arithmetic_mean + 1e-10)
        
        # ZCR
        import librosa
        zcr = librosa.feature.zero_crossing_rate(audio_data)[0]
        zcr_mean = np.mean(zcr)
        
        # 선명도 계산
        hnr_score = (hnr - 15) * 2
        tilt_score = -(spectral_tilt + 8) * 3
        flatness_score = -(spectral_flatness - 0.25) * 100
        zcr_score = -(zcr_mean - 0.1) * 200
        
        clarity = hnr_score + tilt_score + flatness_score + zcr_score
        clarity_score = np.clip(clarity + 50, 0, 100)
        
        print(f"   HNR: {hnr:.1f}dB")
        print(f"   Spectral Tilt: {spectral_tilt:.1f}dB/oct")
        print(f"   Spectral Flatness: {spectral_flatness:.3f}")
        print(f"   ZCR: {zcr_mean:.4f}")
        print(f"   선명도: {clarity_score:.1f}")
        
        return clarity_score
        
    except Exception as e:
        print(f"   오류: {e}")
        return 0

if __name__ == "__main__":
    files = [
        r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav",
        r"C:\Users\user\Desktop\vocals_extracted\로이킴_로이킴 - As Is_보컬.wav"
    ]
    
    for f in files:
        score = quick_analysis(f)
        print()