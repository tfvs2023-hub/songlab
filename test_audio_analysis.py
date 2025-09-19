"""
고급 음성 분석 테스트 스크립트
WAV 파일을 직접 분석하여 4축 결과 확인
"""

from advanced_vocal_analyzer import AdvancedVocalAnalyzer
import soundfile as sf
import sys

def test_audio_file(file_path: str):
    """오디오 파일 분석 테스트"""
    
    print("=" * 60)
    print("🎤 고급 4축 보컬 분석 테스트")
    print("=" * 60)
    
    try:
        # 분석기 초기화
        print("📊 분석기 초기화...")
        analyzer = AdvancedVocalAnalyzer()
        
        # 오디오 파일 로드
        print(f"🎵 오디오 로드: {file_path}")
        audio_data, sr = sf.read(file_path)
        
        # WAV 데이터를 bytes로 변환
        import io
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sr, format='wav')
        audio_bytes = audio_buffer.getvalue()
        
        # 분석 수행
        print("🔍 4축 분석 수행중...")
        results = analyzer.analyze_audio(audio_bytes)
        
        # 결과 출력
        print("\n📈 분석 결과:")
        print("-" * 40)
        print(f"🌟 밝기 (Brightness):     {results['brightness']:+6.1f}")
        print(f"🎭 두께 (Thickness):      {results['thickness']:+6.1f}")
        print(f"🎯 성대내전 (Adduction):   {results['adduction']:+6.1f}")
        print(f"📢 음압 (SPL):           {results['spl']:+6.1f}")
        print("-" * 40)
        print(f"👤 성별 추론:             {results['gender']}")
        print(f"🎵 잠재적 고음력:          {results['potential_high_note']}")
        print("-" * 40)
        
        # 분석 해석
        print("\n💡 분석 해석:")
        
        # 밝기 해석
        brightness = results['brightness']
        if brightness > 30:
            print(f"   밝기: 매우 밝은 음색 ({brightness:+.1f}) - 경쾌하고 활발한 인상")
        elif brightness > 0:
            print(f"   밝기: 밝은 음색 ({brightness:+.1f}) - 신나는 느낌")
        elif brightness > -30:
            print(f"   밝기: 중간 음색 ({brightness:+.1f}) - 균형잡힌 톤")
        else:
            print(f"   밝기: 어두운 음색 ({brightness:+.1f}) - 깊고 성숙한 느낌")
        
        # 두께 해석
        thickness = results['thickness']
        if thickness > 30:
            print(f"   두께: 매우 두꺼운 음색 ({thickness:+.1f}) - 풍성하고 임팩트 강함")
        elif thickness > 0:
            print(f"   두께: 두꺼운 음색 ({thickness:+.1f}) - 볼륨감 있음")
        elif thickness > -30:
            print(f"   두께: 중간 두께 ({thickness:+.1f}) - 적당한 볼륨")
        else:
            print(f"   두께: 얇은 음색 ({thickness:+.1f}) - 섬세하고 가벼운 느낌")
        
        # 성대내전 해석 (중요!)
        adduction = results['adduction']
        if adduction > 50:
            print(f"   성대내전: 매우 좋음 ({adduction:+.1f}) - 프로페셔널한 발성 기법")
        elif adduction > 20:
            print(f"   성대내전: 좋음 ({adduction:+.1f}) - 안정적인 발성")
        elif adduction > -20:
            print(f"   성대내전: 보통 ({adduction:+.1f}) - 평균적인 발성")
        else:
            print(f"   성대내전: 개선 필요 ({adduction:+.1f}) - 발성 기법 연습 권장")
        
        # SPL 해석
        spl = results['spl']
        if spl > 50:
            print(f"   음압: 매우 강함 ({spl:+.1f}) - 파워풀한 음량")
        elif spl > 20:
            print(f"   음압: 강함 ({spl:+.1f}) - 적당한 파워")
        elif spl > -20:
            print(f"   음압: 보통 ({spl:+.1f}) - 평균적인 음량")
        else:
            print(f"   음압: 약함 ({spl:+.1f}) - 음량 보강 필요")
        
        # 고음력 해석
        high_note = results['potential_high_note']
        gender = results['gender']
        print(f"\n🎯 고음 잠재력 분석:")
        if gender == 'male':
            if high_note >= 'E5':
                print(f"   {high_note} - 남성 기준 우수한 고음 잠재력!")
            elif high_note >= 'C5':
                print(f"   {high_note} - 남성 기준 좋은 고음 잠재력")
            else:
                print(f"   {high_note} - 고음 개발 여지 있음")
        else:  # female
            if high_note >= 'G5':
                print(f"   {high_note} - 여성 기준 우수한 고음 잠재력!")
            elif high_note >= 'F5':
                print(f"   {high_note} - 여성 기준 좋은 고음 잠재력")
            else:
                print(f"   {high_note} - 고음 개발 여지 있음")
        
        print("\n✅ 분석 완료!")
        return results
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        return None

if __name__ == "__main__":
    # 테스트할 오디오 파일 경로
    audio_file = r"C:\Users\user\Downloads\상일2.wav"
    
    # 분석 실행
    results = test_audio_file(audio_file)
    
    if results:
        print(f"\n🔍 원시 데이터: {results}")