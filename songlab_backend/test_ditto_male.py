"""
딧토2.m4a 파일 테스트 - 남성 기준 재분석
"""

from voice_analyzer import VoiceAnalyzer
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

def analyze_as_male(brightness, thickness, adduction, spl):
    """남성 기준으로 잠재적 고음력 재계산"""
    
    # 남성 대중가요 기준 (A4 ~ F5)
    base_notes = ['A4', 'A#4', 'B4', 'C5', 'C#5', 'D5', 'D#5', 'E5', 'F5']
    base_idx = 4  # C#5 기준
    
    adjustment = 0
    
    # 밝기 (남성은 더 어두운 톤이 일반적)
    if brightness > 20:  # 남성 기준으로는 상당히 밝음
        adjustment += 3
    elif brightness > -10:  # 남성 평균
        adjustment += 2
    elif brightness > -30:
        adjustment += 1
    elif brightness < -50:
        adjustment -= 2
    
    # 두께 (남성은 두꺼운 음색이 일반적)
    if 0 <= thickness <= 40:  # 적당한 두께
        adjustment += 1
    elif thickness < -20:  # 얇은 음색 (고음에 유리)
        adjustment += 2
    elif thickness > 70:  # 너무 두꺼움
        adjustment -= 1
    
    # 성대내전 (남녀 공통 중요)
    if adduction > 60:
        adjustment += 3
    elif adduction > 30:
        adjustment += 2
    elif adduction > 0:
        adjustment += 1
    elif adduction < -30:
        adjustment -= 2
    
    # 음압 (남성은 더 강한 파워 기대)
    if 40 <= spl <= 80:  # 최적 범위
        adjustment += 1
    elif spl > 90:  # 너무 강함
        adjustment -= 1
    elif spl < 20:  # 너무 약함
        adjustment -= 1
    
    final_idx = max(0, min(len(base_notes) - 1, base_idx + adjustment))
    
    return base_notes[final_idx]

def test_ditto_as_male():
    """딧토2.m4a 남성 기준 분석"""
    
    print("=" * 60)
    print("🎤 딧토2.m4a - 남성 기준 재분석")
    print("=" * 60)
    
    m4a_file = r"C:\Users\user\Documents\카카오톡 받은 파일\딧토2.m4a"
    
    analyzer = VoiceAnalyzer()
    print("✅ 분석기 초기화 완료")
    
    try:
        print("🔄 M4A → WAV 변환 중...")
        wav_path = convert_m4a_to_wav(m4a_file)
        
        if not wav_path:
            print("📁 soundfile로 직접 로드...")
            audio_data, sr = sf.read(m4a_file)
        else:
            audio_data, sr = sf.read(wav_path)
            os.unlink(wav_path)
        
        print(f"🎵 오디오 로드 완료: {len(audio_data)/sr:.1f}초")
        
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sr, format='wav')
        audio_bytes = audio_buffer.getvalue()
        
        print("\n🔍 분석 수행중...")
        results = analyzer.get_advanced_results(audio_bytes)
        
        # 남성 기준 재계산
        male_high_note = analyze_as_male(
            results['brightness'],
            results['thickness'],
            results['adduction'],
            results['spl']
        )
        
        print("\n" + "="*60)
        print("📈 성별 기준 비교 분석")
        print("="*60)
        
        print("\n[원본 분석 - 여성 추론]")
        print(f"🌟 밝기:      {results['brightness']:+6.1f}")
        print(f"🎭 두께:      {results['thickness']:+6.1f}")
        print(f"🎯 성대내전:   {results['adduction']:+6.1f}")
        print(f"📢 음압:      {results['spl']:+6.1f}")
        print(f"👤 성별:      {results['gender']}")
        print(f"🎵 고음력:     {results['potential_high_note']}")
        
        print("\n[남성 기준 재분석]")
        print(f"👤 성별:      male (강제 설정)")
        print(f"🎵 고음력:     {male_high_note}")
        
        print("\n" + "="*60)
        print("📊 남성 기준 상세 수치")
        print("="*60)
        
        brightness = results['brightness']
        thickness = results['thickness']
        adduction = results['adduction']
        spl = results['spl']
        
        # 음압 (SPL) 상세 분석
        print(f"\n🔊 음압 (Sound Pressure Level): {spl:+.1f}")
        if spl > 80:
            print(f"   → 매우 강한 음압 (프로페셔널)")
        elif spl > 60:
            print(f"   → 강한 음압 (숙련자)")
        elif spl > 40:
            print(f"   → 적정 음압 (일반적)")
        elif spl > 20:
            print(f"   → 약한 음압 (개선 필요)")
        else:
            print(f"   → 매우 약한 음압 (훈련 필요)")
        
        # 주파수 범위 추정 (F0 기준)
        print(f"\n🎵 음역대 분석:")
        if results['gender'] == 'female':
            base_f0 = 220  # A3
            print(f"   기본음 (F0): ~{base_f0}Hz (여성 기준)")
        else:
            base_f0 = 110  # A2
            print(f"   기본음 (F0): ~{base_f0}Hz (남성 기준)")
        
        # 고음 주파수 변환
        note_freqs = {
            'A4': 440, 'A#4': 466, 'B4': 494,
            'C5': 523, 'C#5': 554, 'D5': 587,
            'D#5': 622, 'E5': 659, 'F5': 698
        }
        
        if male_high_note in note_freqs:
            high_freq = note_freqs[male_high_note]
            print(f"   잠재 고음: {male_high_note} (~{high_freq}Hz)")
        
        print("\n" + "="*60)
        print("💡 남성 보컬리스트로 평가")
        print("="*60)
        
        brightness = results['brightness']
        thickness = results['thickness']
        adduction = results['adduction']
        spl = results['spl']
        
        print(f"\n🎯 남성 기준 평가:")
        
        # 밝기 평가 (남성 기준)
        if brightness > 0:
            print(f"   밝기: 남성치고 매우 밝은 톤 ({brightness:+.1f})")
            print(f"        → 팝, R&B 스타일에 적합")
        elif brightness > -30:
            print(f"   밝기: 남성 평균 톤 ({brightness:+.1f})")
            print(f"        → 다양한 장르 소화 가능")
        else:
            print(f"   밝기: 전형적인 남성 저음 ({brightness:+.1f})")
            print(f"        → 발라드, 재즈에 적합")
        
        # 두께 평가 (남성 기준)  
        if thickness > 50:
            print(f"   두께: 매우 풍성한 남성 음색 ({thickness:+.1f})")
            print(f"        → 파워풀한 보컬 스타일")
        elif thickness > 0:
            print(f"   두께: 적당한 남성 음색 ({thickness:+.1f})")
        else:
            print(f"   두께: 가벼운 남성 음색 ({thickness:+.1f})")
            print(f"        → 고음 처리에 유리")
        
        # 고음력 평가 (남성 기준)
        print(f"\n   잠재적 고음력: {male_high_note}")
        
        male_high_notes = {
            'A4': '일반 남성 평균',
            'A#4': '일반 남성 평균',
            'B4': '평균 이상',
            'C5': '양호한 고음',
            'C#5': '좋은 고음 (나얼 수준)',
            'D5': '우수한 고음',
            'D#5': '매우 우수 (김범수 수준)',
            'E5': '뛰어난 고음',
            'F5': '최상급 (임재범 수준)'
        }
        
        if male_high_note in male_high_notes:
            print(f"        → {male_high_notes[male_high_note]}")
        
        # 남성 아티스트 비교
        print(f"\n📍 유사한 남성 아티스트:")
        
        if brightness > -20 and thickness > 50:
            print("   - 박효신 (밝고 두꺼운 음색)")
        elif brightness < -30 and thickness > 50:
            print("   - 이적 (어둡고 두꺼운 음색)")
        elif brightness > 0 and thickness < 30:
            print("   - 정승환 (밝고 가벼운 음색)")
        else:
            print("   - 김범수 (중간 톤)")
        
        # 성대내전 문제 (남성 기준)
        if adduction < -50:
            print(f"\n⚠️ 주의사항:")
            print(f"   성대내전 ({adduction:+.1f})이 매우 낮음")
            print(f"   → 남성 특유의 허스키함으로 해석 가능")
            print(f"   → 하지만 고음 안정성을 위해 개선 필요")
        
        print("\n✅ 남성 기준 분석 완료!")
        print("="*60)
        
        return {
            'original': results,
            'male_high_note': male_high_note
        }
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = test_ditto_as_male()