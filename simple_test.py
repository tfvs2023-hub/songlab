"""
기존 라이브러리로 간단 분석 테스트
"""

import librosa
import numpy as np
import soundfile as sf

def simple_vocal_analysis(file_path: str):
    """LibROSA로 간단한 4축 분석"""
    
    print("=" * 50)
    print("🎤 간단 보컬 분석 (LibROSA)")
    print("=" * 50)
    
    try:
        # 오디오 로드
        print(f"🎵 파일 로드: {file_path}")
        audio, sr = librosa.load(file_path, sr=22050, mono=True)
        print(f"   길이: {len(audio)/sr:.1f}초, 샘플링 레이트: {sr}Hz")
        
        # 무음 제거
        audio_trimmed, _ = librosa.effects.trim(audio, top_db=20)
        print(f"   트리밍 후: {len(audio_trimmed)/sr:.1f}초")
        
        # 기본 특징 추출
        print("\n🔍 특징 분석중...")
        
        # 1. 밝기 분석 (Spectral Centroid)
        spectral_centroid = librosa.feature.spectral_centroid(y=audio_trimmed, sr=sr)[0]
        brightness_raw = np.mean(spectral_centroid)
        brightness = (brightness_raw - 2000) / 20  # 정규화
        brightness = np.clip(brightness, -100, 100)
        
        # 2. 두께 분석 (RMS + Spectral Rolloff)
        rms = librosa.feature.rms(y=audio_trimmed)[0]
        rolloff = librosa.feature.spectral_rolloff(y=audio_trimmed, sr=sr)[0]
        thickness_rms = (np.mean(rms) - 0.1) * 200
        thickness_rolloff = (np.mean(rolloff) - 4000) / 50
        thickness = (thickness_rms + thickness_rolloff) / 2
        thickness = np.clip(thickness, -100, 100)
        
        # 3. 성대내전 추정 (Zero Crossing Rate 기반)
        zcr = librosa.feature.zero_crossing_rate(audio_trimmed)[0]
        zcr_mean = np.mean(zcr)
        # ZCR이 낮을수록 성대접촉이 좋음 (가성 추정)
        adduction = max(0, (0.1 - zcr_mean) * 1000)
        adduction = np.clip(adduction, -100, 100)
        
        # 4. 음압 분석 (RMS Energy)
        rms_db = 20 * np.log10(np.mean(rms) + 1e-8)
        spl = (rms_db + 40) * 100 / 40  # -40dB 기준 정규화
        spl = np.clip(spl, -100, 100)
        
        # 5. 성별 추정 (기본 주파수)
        pitches, magnitudes = librosa.piptrack(y=audio_trimmed, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        if pitch_values:
            avg_pitch = np.mean(pitch_values)
            if avg_pitch > 180:
                gender = 'female'
            elif avg_pitch < 130:
                gender = 'male'
            else:
                # 음색으로 추정
                gender = 'female' if brightness > 10 and thickness < 0 else 'male'
        else:
            gender = 'unknown'
        
        # 6. 잠재적 고음력 계산
        if gender == 'male':
            base_notes = ['A4', 'A#4', 'B4', 'C5', 'C#5', 'D5', 'D#5', 'E5', 'F5']
            base_idx = 4  # C#5
        else:
            base_notes = ['C5', 'C#5', 'D5', 'D#5', 'E5', 'F5', 'F#5', 'G5', 'G#5', 'A5']
            base_idx = 5  # F5
            
        adjustment = 0
        if brightness > 30: adjustment += 2
        elif brightness > 0: adjustment += 1
        if -10 <= thickness <= 20: adjustment += 1
        if adduction > 30: adjustment += 2
        if 20 <= spl <= 60: adjustment += 1
        
        final_idx = max(0, min(len(base_notes) - 1, base_idx + adjustment))
        potential_high_note = base_notes[final_idx]
        
        # 결과 출력
        print("\n📈 분석 결과:")
        print("-" * 40)
        print(f"🌟 밝기:        {brightness:+6.1f}")
        print(f"🎭 두께:        {thickness:+6.1f}")
        print(f"🎯 성대내전:     {adduction:+6.1f}")
        print(f"📢 음압:        {spl:+6.1f}")
        print(f"👤 성별:        {gender}")
        print(f"🎵 잠재고음:     {potential_high_note}")
        print("-" * 40)
        
        # 추가 정보
        if pitch_values:
            print(f"🎼 평균 피치:    {avg_pitch:.0f}Hz")
        print(f"📊 원시 데이터:")
        print(f"   Spectral Centroid: {brightness_raw:.0f}Hz")
        print(f"   RMS Energy: {np.mean(rms):.4f}")
        print(f"   Zero Crossing Rate: {zcr_mean:.4f}")
        
        return {
            'brightness': brightness,
            'thickness': thickness,
            'adduction': adduction,
            'spl': spl,
            'gender': gender,
            'potential_high_note': potential_high_note
        }
        
    except Exception as e:
        print(f"❌ 오류: {str(e)}")
        return None

if __name__ == "__main__":
    results = simple_vocal_analysis(r"C:\Users\user\Downloads\상일2.wav")
    if results:
        print(f"\n✅ 완료: {results}")