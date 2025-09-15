"""
김범수 - Dear Love 보컬 분석
"""

from voice_analyzer import VoiceAnalyzer
import soundfile as sf
import io

def test_kimbeomsu():
    """김범수 보컬 분석"""
    
    print("=" * 60)
    print("🎤 김범수 - Dear Love 보컬 분석")
    print("=" * 60)
    
    # 오디오 파일 경로
    audio_file = r"C:\Users\user\Desktop\vocals_extracted\김범수_김범수 - Dear Love_보컬.wav"
    
    # 분석기 초기화
    analyzer = VoiceAnalyzer()
    print("✅ 분석기 초기화 완료")
    
    try:
        # 오디오 로드
        audio_data, sr = sf.read(audio_file)
        print(f"🎵 오디오 로드 완료: {len(audio_data)/sr:.1f}초, {sr}Hz")
        
        # 바이트로 변환
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sr, format='wav')
        audio_bytes = audio_buffer.getvalue()
        
        # 고급 분석 수행
        print("\n🔍 4축 분석 수행중...")
        results = analyzer.get_advanced_results(audio_bytes)
        
        # 결과 출력
        print("\n" + "="*60)
        print("📈 김범수 보컬 분석 결과")
        print("="*60)
        
        print("\n[4축 분석]")
        print(f"🌟 밝기 (Brightness):     {results['brightness']:+6.1f}")
        print(f"🎭 두께 (Thickness):      {results['thickness']:+6.1f}")
        print(f"🎯 성대내전 (Adduction):   {results['adduction']:+6.1f}")
        print(f"📢 음압 (SPL):           {results['spl']:+6.1f}")
        
        print("\n[추론 결과]")
        print(f"👤 성별:                 {results['gender']}")
        print(f"🎵 잠재적 고음력:         {results['potential_high_note']}")
        
        # 상세 수치 분석
        print("\n" + "="*60)
        print("📊 상세 수치 분석")
        print("="*60)
        
        brightness = results['brightness']
        thickness = results['thickness']
        adduction = results['adduction']
        spl = results['spl']
        
        # 음압 분석
        print(f"\n🔊 음압 (SPL): {spl:+.1f}")
        if spl > 80:
            print("   → 매우 강한 음압 (프로페셔널)")
        elif spl > 60:
            print("   → 강한 음압 (숙련자)")
        elif spl > 40:
            print("   → 적정 음압 (일반적)")
        else:
            print("   → 약한 음압")
        
        # 성대내전 분석
        print(f"\n🎯 성대내전: {adduction:+.1f}")
        if adduction > 50:
            print("   → 매우 우수한 성대 밀착 (프로 수준)")
        elif adduction > 20:
            print("   → 양호한 성대 밀착 (안정적)")
        elif adduction > 0:
            print("   → 보통 수준")
        elif adduction > -50:
            print("   → 약간 허스키함")
        else:
            print("   → 매우 허스키함 (공기 누설)")
        
        # 주파수 분석
        note_freqs = {
            'A4': 440, 'A#4': 466, 'B4': 494,
            'C5': 523, 'C#5': 554, 'D5': 587,
            'D#5': 622, 'E5': 659, 'F5': 698
        }
        
        print(f"\n🎵 음역대:")
        if results['gender'] == 'male':
            print(f"   기본음 (F0): ~110Hz (남성 기준)")
        else:
            print(f"   기본음 (F0): ~220Hz (여성 기준)")
        
        high_note = results['potential_high_note']
        if high_note in note_freqs:
            print(f"   잠재 고음: {high_note} (~{note_freqs[high_note]}Hz)")
        
        # 김범수 특성 분석
        print("\n" + "="*60)
        print("💡 김범수 보컬 특성 분석")
        print("="*60)
        
        print(f"\n🎯 종합 평가:")
        
        # 밝기
        if brightness > 20:
            print(f"   밝기: 매우 밝은 톤 ({brightness:+.1f})")
        elif brightness > 0:
            print(f"   밝기: 밝은 톤 ({brightness:+.1f})")
        elif brightness > -20:
            print(f"   밝기: 중간 톤 ({brightness:+.1f})")
        else:
            print(f"   밝기: 어두운 톤 ({brightness:+.1f})")
        
        # 두께
        if thickness > 50:
            print(f"   두께: 매우 두꺼운 음색 ({thickness:+.1f})")
        elif thickness > 20:
            print(f"   두께: 두꺼운 음색 ({thickness:+.1f})")
        elif thickness > 0:
            print(f"   두께: 적당한 두께 ({thickness:+.1f})")
        else:
            print(f"   두께: 얇은 음색 ({thickness:+.1f})")
        
        print(f"\n📍 김범수 보컬의 특징:")
        
        # 강점 분석
        scores = {
            '밝기': brightness,
            '두께': thickness,
            '성대내전': adduction,
            '음압': spl
        }
        
        best_feature = max(scores, key=scores.get)
        print(f"   최고 강점: {best_feature} ({scores[best_feature]:+.1f})")
        
        worst_feature = min(scores, key=scores.get)
        if scores[worst_feature] < 20:
            print(f"   개선 영역: {worst_feature} ({scores[worst_feature]:+.1f})")
        
        # 다른 파일들과 비교
        print("\n" + "="*60)
        print("📊 다른 보컬과 비교")
        print("="*60)
        print("\n파일           | 밝기   | 두께   | 성대내전 | 음압   | 성별 | 고음력")
        print("-" * 75)
        print("상일2          | -25.2  | +100.0 |  +11.9   | +82.8  | 여성 | D#5")
        print("딧토2          |  -15.2 | +100.0 | -100.0   | +75.0  | 여성 | C#5")
        print(f"김범수-DearLove | {brightness:+6.1f} | {thickness:+6.1f} | {adduction:+7.1f} | {spl:+6.1f} | {results['gender'][:2]} | {high_note}")
        
        print("\n✅ 김범수 보컬 분석 완료!")
        print("="*60)
        
        return results
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = test_kimbeomsu()