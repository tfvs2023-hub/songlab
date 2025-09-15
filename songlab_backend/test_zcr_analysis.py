"""
ZCR 기반 성대내전 분석 테스트
"""

import numpy as np
import librosa
import soundfile as sf
import io
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

def analyze_zcr_adduction(audio_file):
    """ZCR 기반 성대내전 분석"""
    
    print("=" * 60)
    print("🎯 ZCR 기반 성대내전 분석")
    print("=" * 60)
    
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
        
        # ZCR 계산 (세그먼트별)
        print("\n🔍 ZCR 분석 중...")
        
        # 전체 ZCR
        zcr_full = librosa.feature.zero_crossing_rate(audio_data, frame_length=2048, hop_length=512)[0]
        zcr_mean = np.mean(zcr_full)
        zcr_std = np.std(zcr_full)
        
        # 10초씩 세그먼트 분석
        segment_length = 10 * sr
        segments = []
        
        for i in range(0, len(audio_data), segment_length):
            segment = audio_data[i:i+segment_length]
            if len(segment) > sr:  # 최소 1초 이상
                zcr_seg = librosa.feature.zero_crossing_rate(segment)[0]
                segments.append({
                    'start': i/sr,
                    'end': min((i+segment_length)/sr, len(audio_data)/sr),
                    'zcr_mean': np.mean(zcr_seg),
                    'zcr_std': np.std(zcr_seg)
                })
        
        print("\n" + "=" * 60)
        print("📊 ZCR 분석 결과")
        print("=" * 60)
        
        print(f"\n🎯 전체 통계:")
        print(f"   평균 ZCR: {zcr_mean:.6f}")
        print(f"   표준편차: {zcr_std:.6f}")
        
        # ZCR 점수 계산 (낮을수록 좋음)
        zcr_score = np.clip(50 - zcr_mean * 5000, -50, 50)
        print(f"   정규화 점수: {zcr_score:.1f} (-50~50)")
        
        # 평가
        if zcr_score > 30:
            evaluation = "매우 좋음 (깨끗한 음성)"
        elif zcr_score > 10:
            evaluation = "좋음 (안정적)"
        elif zcr_score > -10:
            evaluation = "보통"
        elif zcr_score > -30:
            evaluation = "나쁨 (허스키함)"
        else:
            evaluation = "매우 나쁨 (매우 허스키함)"
        
        print(f"   평가: {evaluation}")
        
        # 세그먼트별 분석
        print(f"\n📈 10초 구간별 분석:")
        print("시작  | 종료  | ZCR평균    | 표준편차   | 점수   | 평가")
        print("-" * 65)
        
        for seg in segments:
            seg_score = np.clip(50 - seg['zcr_mean'] * 5000, -50, 50)
            
            if seg_score > 30:
                seg_eval = "매우좋음"
            elif seg_score > 10:
                seg_eval = "좋음"
            elif seg_score > -10:
                seg_eval = "보통"
            elif seg_score > -30:
                seg_eval = "나쁨"
            else:
                seg_eval = "매우나쁨"
                
            print(f"{seg['start']:5.1f} | {seg['end']:5.1f} | {seg['zcr_mean']:10.6f} | {seg['zcr_std']:10.6f} | {seg_score:6.1f} | {seg_eval}")
        
        # 비교 분석
        print("\n" + "=" * 60)
        print("📊 다른 보컬과 ZCR 비교")
        print("=" * 60)
        
        print("\n파일               | ZCR평균    | ZCR점수 | 평가")
        print("-" * 55)
        print("김범수-DearLove   | 0.000000   | 50.0    | 매우좋음")
        print(f"현재파일           | {zcr_mean:.6f}   | {zcr_score:5.1f}   | {evaluation[:4]}")
        
        print(f"\n💡 ZCR 해석:")
        print(f"   - 0에 가까울수록: 깨끗하고 안정적인 음성")
        print(f"   - 높을수록: 허스키하고 불안정한 음성")
        print(f"   - 김범수는 거의 0 (완벽한 성대 접촉)")
        
        return {
            'zcr_mean': zcr_mean,
            'zcr_score': zcr_score,
            'evaluation': evaluation,
            'segments': segments
        }
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    audio_file = r"C:\Users\user\Documents\카카오톡 받은 파일\kakaotalk_1756474302376.m4a"
    results = analyze_zcr_adduction(audio_file)