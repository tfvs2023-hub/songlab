"""
상일2.wav 파일 테스트 스크립트
"""

import os
import sys

import soundfile as sf

from advanced_vocal_analyzer_no_essentia import AdvancedVocalAnalyzerNoEssentia


def test_sangil_audio():
    """상일2.wav 분석"""

    audio_file = r"C:\Users\user\Downloads\상일2.wav"

    print("=" * 60)
    print("🎤 상일2.wav 고급 4축 보컬 분석")
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

        # 상세 해석
        print("\n" + "=" * 60)
        print("💡 상세 분석")
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

        # 성대내전 해석 (핵심!)
        adduction = results["adduction"]
        print(f"\n📍 성대내전 ({adduction:+.1f})")
        if adduction > 50:
            print("   → 매우 우수: 프로페셔널한 발성 기법")
            print("   → HNR이 높고 음성이 매우 안정적")
        elif adduction > 20:
            print("   → 양호: 안정적인 발성")
            print("   → 일반적으로 좋은 보컬 테크닉")
        elif adduction > -20:
            print("   → 보통: 평균적인 발성")
            print("   → 더 많은 연습으로 개선 가능")
        else:
            print("   → 개선 필요: 발성 기법 연습 권장")
            print("   → 호흡 지원과 성대 접촉 개선 필요")

        # 음압 해석
        spl = results["spl"]
        print(f"\n📍 음압 ({spl:+.1f})")
        if spl > 50:
            print("   → 매우 강함: 파워풀한 음량")
        elif spl > 20:
            print("   → 강함: 적당한 파워와 존재감")
        elif spl > -20:
            print("   → 보통: 평균적인 음량")
        else:
            print("   → 약함: 음량 보강 필요")

        # 종합 평가
        print("\n" + "=" * 60)
        print("🏆 종합 평가")
        print("=" * 60)

        gender = results["gender"]
        high_note = results["potential_high_note"]

        print(f"\n성별: {gender}")
        print(f"잠재적 최고음: {high_note}")

        if gender == "male":
            if high_note >= "E5":
                print("→ 남성 기준 매우 우수한 고음 잠재력!")
                print("→ 전문 보컬리스트 수준의 음역대 가능")
            elif high_note >= "C5":
                print("→ 남성 기준 좋은 고음 잠재력")
                print("→ 대중가요 대부분 소화 가능")
            else:
                print("→ 고음 개발 여지 있음")
                print("→ 훈련으로 충분히 확장 가능")
        else:  # female
            if high_note >= "G5":
                print("→ 여성 기준 매우 우수한 고음 잠재력!")
                print("→ 전문 보컬리스트 수준")
            elif high_note >= "F5":
                print("→ 여성 기준 좋은 고음 잠재력")
                print("→ 대중가요 대부분 소화 가능")
            else:
                print("→ 고음 개발 여지 있음")
                print("→ 훈련으로 충분히 확장 가능")

        # 개선 제안
        print("\n📚 개선 제안:")
        suggestions = []

        if brightness < -20:
            suggestions.append("• 밝기 개선: 앞쪽 공명 연습, 미소 짓듯이 발성")
        if thickness < -20:
            suggestions.append("• 두께 보강: 복식호흡 강화, 성대 접촉 개선")
        if adduction < 30:
            suggestions.append("• 성대내전 개선: HNR 높이기, 안정적인 발성 연습")
        if spl < 20:
            suggestions.append("• 음압 강화: 호흡 지원 강화, 다이나믹 연습")

        if suggestions:
            for s in suggestions:
                print(s)
        else:
            print("• 현재 매우 좋은 상태입니다!")

        print("\n✅ 분석 완료!")
        print("=" * 60)

        return results

    except Exception as e:
        print(f"❌ 분석 오류: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    # conda 환경 활성화 메시지
    print("\n💡 실행 방법:")
    print("conda activate vocal-analyzer-advanced")
    print("python test_sangil.py\n")

    # 분석 실행
    results = test_sangil_audio()
