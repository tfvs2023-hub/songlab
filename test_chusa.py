"""
일반인추사닮.wav 파일 테스트 스크립트
"""

from advanced_vocal_analyzer_no_essentia import AdvancedVocalAnalyzerNoEssentia
import soundfile as sf
import sys
import os

def test_chusa_audio():
    """일반인추사닮.wav 분석"""
    
    audio_file = r"C:\Users\user\Downloads\일반인추사닮.wav"
    
    print("=" * 60)
    print("🎤 일반인추사닮.wav 고급 4축 보컬 분석")
    print("=" * 60)
    
    try:
        # 분석기 초기화
        print("📊 분석기 초기화...")
        analyzer = AdvancedVocalAnalyzerNoEssentia()
        
        # 오디오 파일 로드
        print(f"🎵 오디오 로드: {audio_file}")
        audio_data, sr = sf.read(audio_file)
        print(f"   샘플링레이트: {sr}Hz, 길이: {len(audio_data)/sr:.1f}초")
        
        # WAV 데이터를 bytes로 변환
        import io
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sr, format='wav')
        audio_bytes = audio_buffer.getvalue()
        
        # 분석 수행
        print("\n🔍 4축 분석 수행중...")
        results = analyzer.analyze_audio(audio_bytes)
        
        # 결과 출력
        print("\n" + "="*60)
        print("📈 분석 결과")
        print("="*60)
        
        # 4축 점수
        print("\n[4축 분석]")
        print(f"🌟 밝기 (Brightness):     {results['brightness']:+6.1f}")
        print(f"🎭 두께 (Thickness):      {results['thickness']:+6.1f}")
        print(f"🎯 성대내전 (Adduction):   {results['adduction']:+6.1f}")
        print(f"📢 음압 (SPL):           {results['spl']:+6.1f}")
        
        # 성별 및 고음력
        print("\n[추론 결과]")
        print(f"👤 성별:                 {results['gender']}")
        print(f"🎵 잠재적 고음력:         {results['potential_high_note']}")
        
        # 3개 파일 비교 테이블
        print("\n" + "="*60)
        print("📊 3개 파일 비교 분석")
        print("="*60)
        
        # 비교표 출력
        print("\n파일명           | 밝기   | 두께   | 성대내전 | 음압   | 성별 | 고음력")
        print("-" * 70)
        print("상일2.wav       | -26.3  | +100.0 |  -100.0  | +81.8  | 여성 | C5")
        print("발성만.wav      |  -9.2  | +100.0 |   -86.9  | +78.2  | 여성 | C#5")
        print(f"일반인추사닮.wav | {results['brightness']:+6.1f} | {results['thickness']:+6.1f} | {results['adduction']:+7.1f} | {results['spl']:+6.1f} | {results['gender'][:2]} | {results['potential_high_note']}")
        
        # 순위 분석
        print("\n" + "="*60)
        print("🏆 항목별 순위 분석")
        print("="*60)
        
        brightness = results['brightness']
        thickness = results['thickness'] 
        adduction = results['adduction']
        spl = results['spl']
        
        print(f"\n📍 밝기 순위 (높을수록 밝음)")
        brightness_scores = [
            ("일반인추사닮", brightness),
            ("발성만", -9.2),
            ("상일2", -26.3)
        ]
        brightness_scores.sort(key=lambda x: x[1], reverse=True)
        for i, (name, score) in enumerate(brightness_scores, 1):
            print(f"   {i}위: {name} ({score:+.1f})")
        
        print(f"\n📍 성대내전 순위 (높을수록 좋음)")
        adduction_scores = [
            ("일반인추사닮", adduction),
            ("발성만", -86.9),
            ("상일2", -100.0)
        ]
        adduction_scores.sort(key=lambda x: x[1], reverse=True)
        for i, (name, score) in enumerate(adduction_scores, 1):
            print(f"   {i}위: {name} ({score:+.1f})")
        
        print(f"\n📍 음압 순위 (높을수록 강함)")
        spl_scores = [
            ("일반인추사닮", spl),
            ("상일2", 81.8),
            ("발성만", 78.2)
        ]
        spl_scores.sort(key=lambda x: x[1], reverse=True)
        for i, (name, score) in enumerate(spl_scores, 1):
            print(f"   {i}위: {name} ({score:+.1f})")
        
        # 고음력 비교
        print(f"\n📍 잠재적 고음력")
        high_notes = [
            ("일반인추사닮", results['potential_high_note']),
            ("발성만", "C#5"),
            ("상일2", "C5")
        ]
        # 음표를 숫자로 변환해서 정렬
        note_values = {"C5": 60, "C#5": 61, "D5": 62, "D#5": 63, "E5": 64, "F5": 65}
        high_notes.sort(key=lambda x: note_values.get(x[1], 60), reverse=True)
        for i, (name, note) in enumerate(high_notes, 1):
            print(f"   {i}위: {name} ({note})")
        
        # 일반인추사닮 특성 분석
        print("\n" + "="*60)
        print("💡 일반인추사닮.wav 특성 분석")
        print("="*60)
        
        print(f"\n🎯 종합 평가:")
        
        # 성별 분석
        gender = results['gender']
        if gender == 'male':
            print(f"   성별: 남성으로 분석됨")
        elif gender == 'female':
            print(f"   성별: 여성으로 분석됨")
        else:
            print(f"   성별: 판별 어려움")
        
        # 밝기 특성
        if brightness > 0:
            print(f"   밝기: 밝은 톤 ({brightness:+.1f}) - 다른 파일들보다 밝음")
        elif brightness > -15:
            print(f"   밝기: 중간 톤 ({brightness:+.1f}) - 균형잡힌 특성")
        else:
            print(f"   밝기: 어두운 톤 ({brightness:+.1f})")
        
        # 성대내전 특성
        if adduction > -50:
            print(f"   성대내전: 다른 파일들보다 우수 ({adduction:+.1f})")
        else:
            print(f"   성대내전: 개선 필요 ({adduction:+.1f})")
        
        # 고음 잠재력
        high_note = results['potential_high_note']
        print(f"   잠재적 고음력: {high_note}")
        
        # 개선 제안
        print(f"\n📚 개선 제안:")
        suggestions = []
        
        if brightness < 10:
            suggestions.append("• 밝기 개선: 앞쪽 공명 강화, 미소 발성 연습")
        if thickness < 20:
            suggestions.append("• 두께 보강: 복식호흡 강화, 성대 접촉 개선")
        if adduction < 0:
            suggestions.append("• 성대내전 개선: HNR 높이기, 안정적인 발성 연습")
        if spl < 40:
            suggestions.append("• 음압 강화: 호흡 지원 강화, 다이나믹 연습")
        
        if suggestions:
            for s in suggestions:
                print(s)
        else:
            print("• 전반적으로 좋은 상태입니다!")
        
        print("\n✅ 일반인추사닮.wav 분석 완료!")
        print("="*60)
        
        return results
        
    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = test_chusa_audio()