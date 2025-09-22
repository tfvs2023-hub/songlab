"""
발성만.wav 파일 테스트 스크립트
"""

import os
import sys

import soundfile as sf

from advanced_vocal_analyzer_no_essentia import AdvancedVocalAnalyzerNoEssentia


def test_balsung_audio():
    """발성만.wav 분석"""

    audio_file = r"C:\Users\user\Downloads\발성만.wav"

    print("=" * 60)
    print("🎤 발성만.wav 고급 4축 보컬 분석")
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
        sf.write(audio_buffer, audio_data, sr, format="wav")
        audio_bytes = audio_buffer.getvalue()

        # 분석 수행
        print("\n🔍 4축 분석 수행중...")
        results = analyzer.analyze_audio(audio_bytes)

        # 결과 출력
        print("\n" + "=" * 60)
        print("📈 분석 결과")
        print("=" * 60)

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

        # 이전 결과와 비교
        print("\n" + "=" * 60)
        print("📊 상일2.wav vs 발성만.wav 비교")
        print("=" * 60)

        # 상일2.wav 결과 (참고용)
        print("\n[상일2.wav 결과]")
        print("🌟 밝기: -26.3 | 🎭 두께: +100.0 | 🎯 성대내전: -100.0 | 📢 음압: +81.8")
        print("👤 여성 | 🎵 C5")

        print("\n[발성만.wav 결과]")
        print(
            f"🌟 밝기: {results['brightness']:+.1f} | 🎭 두께: {results['thickness']:+.1f} | 🎯 성대내전: {results['adduction']:+.1f} | 📢 음압: {results['spl']:+.1f}"
        )
        print(f"👤 {results['gender']} | 🎵 {results['potential_high_note']}")

        # 차이점 분석
        brightness_diff = results["brightness"] - (-26.3)
        thickness_diff = results["thickness"] - 100.0
        adduction_diff = results["adduction"] - (-100.0)
        spl_diff = results["spl"] - 81.8

        print("\n[차이점]")
        print(f"🌟 밝기 차이:   {brightness_diff:+.1f}")
        print(f"🎭 두께 차이:   {thickness_diff:+.1f}")
        print(f"🎯 성대내전 차이: {adduction_diff:+.1f}")
        print(f"📢 음압 차이:   {spl_diff:+.1f}")

        # 상세 해석
        print("\n" + "=" * 60)
        print("💡 발성만.wav 특성 분석")
        print("=" * 60)

        # 밝기 해석
        brightness = results["brightness"]
        print(f"\n📍 밝기 ({brightness:+.1f})")
        if brightness > 30:
            print("   → 매우 밝은 음색: 경쾌하고 활발한 인상")
        elif brightness > 0:
            print("   → 밝은 음색: 친근하고 긍정적인 느낌")
        elif brightness > -30:
            print("   → 중간 밝기: 균형잡힌 톤")
        else:
            print("   → 어두운 음색: 깊고 성숙한 느낌")

        # 두께 해석
        thickness = results["thickness"]
        print(f"\n📍 두께 ({thickness:+.1f})")
        if thickness > 30:
            print("   → 매우 두꺼운 음색: 풍성하고 임팩트 강함")
        elif thickness > 0:
            print("   → 두꺼운 음색: 볼륨감 있고 안정적")
        elif thickness > -30:
            print("   → 중간 두께: 적당한 볼륨")
        else:
            print("   → 얇은 음색: 섬세하고 가벼운 느낌")

        # 성대내전 해석 (중요!)
        adduction = results["adduction"]
        print(f"\n📍 성대내전 ({adduction:+.1f})")
        if adduction > 50:
            print("   → 매우 우수: 프로페셔널한 발성 기법")
        elif adduction > 20:
            print("   → 양호: 안정적인 발성")
        elif adduction > -20:
            print("   → 보통: 평균적인 발성")
        else:
            print("   → 개선 필요: 발성 기법 연습 권장")

        # 음압 해석
        spl = results["spl"]
        print(f"\n📍 음압 ({spl:+.1f})")
        if spl > 50:
            print("   → 매우 강함: 파워풀한 음량")
        elif spl > 20:
            print("   → 강함: 적당한 파워")
        elif spl > -20:
            print("   → 보통: 평균적인 음량")
        else:
            print("   → 약함: 음량 보강 필요")

        print("\n✅ 발성만.wav 분석 완료!")
        print("=" * 60)

        return results

    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = test_balsung_audio()
