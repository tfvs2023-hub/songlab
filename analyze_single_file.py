"""
단일 오디오 파일 분석 스크립트
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import soundfile as sf

from advanced_vocal_analyzer_no_essentia import \
    AdvancedVocalAnalyzerNoEssentia as AdvancedVocalAnalyzer


def analyze_file(file_path):
    print(f"\n분석 중: {file_path}")
    print("=" * 60)

    # 오디오 파일 읽기
    audio_data, sr = sf.read(file_path)

    # 분석기 초기화
    analyzer = AdvancedVocalAnalyzer()

    # 오디오 데이터를 바이트로 변환
    import io

    buffer = io.BytesIO()
    sf.write(buffer, audio_data, sr, format="WAV")
    audio_bytes = buffer.getvalue()

    # 분석 수행
    try:
        scores = analyzer.analyze_audio(audio_bytes)

        print("\n🎤 4축 보컬 분석 결과:")
        print("-" * 40)
        print(
            f"📊 밝기 (Brightness):    {scores['brightness']:+6.1f} {'🌟 밝음' if scores['brightness'] > 0 else '🌙 어두움'}"
        )
        print(
            f"📊 두께 (Thickness):     {scores['thickness']:+6.1f} {'🎯 두꺼움' if scores['thickness'] > 0 else '💨 얇음'}"
        )
        print(
            f"📊 성대내전 (Adduction): {scores['adduction']:+6.1f} {'✅ 완전' if scores['adduction'] > 0 else '⚡ 불완전'}"
        )
        print(
            f"📊 음압 (SPL):          {scores['spl']:+6.1f} {'💪 강함' if scores['spl'] > 0 else '🍃 약함'}"
        )
        print("-" * 40)

        # 성별 및 음역대
        print(f"\n🎵 추가 정보:")
        print(f"성별: {scores.get('gender', 'unknown')}")
        print(f"예상 최고음: {scores.get('potential_high_note', 'N/A')}")

        # 종합 평가
        print("\n💡 종합 평가:")
        if abs(scores["brightness"]) > 50:
            print(f"- 매우 {'밝은' if scores['brightness'] > 0 else '어두운'} 음색")
        if abs(scores["thickness"]) > 50:
            print(f"- 매우 {'두꺼운' if scores['thickness'] > 0 else '얇은'} 음색")
        if scores["adduction"] > 70:
            print("- 우수한 성대 내전 기법")
        elif scores["adduction"] < -30:
            print("- 성대 내전 개선 필요")
        if abs(scores["spl"]) > 60:
            print(f"- {'강력한 음압' if scores['spl'] > 0 else '부드러운 음압'}")

    except Exception as e:
        print(f"❌ 분석 중 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Allow passing a file path via CLI, otherwise fall back to example in repo
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = r"audio_data\test.wav"

    analyze_file(file_path)
