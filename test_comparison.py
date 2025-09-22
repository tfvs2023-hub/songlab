"""
폰 vs 스튜디오 분석 비교 테스트
"""

import os
import sys

import soundfile as sf

from recording_detector import RecordingDetector
from vocal_analyzer_lite import VocalAnalyzerLite
from vocal_analyzer_studio import VocalAnalyzerStudio


def compare_analysis(file_path):
    print(f"\n{'='*70}")
    print(f"분석 파일: {file_path}")
    print(f"{'='*70}")

    # 오디오 파일 읽기
    audio_data, sr = sf.read(file_path)

    # 바이트로 변환
    import io

    buffer = io.BytesIO()
    sf.write(buffer, audio_data, sr, format="WAV")
    audio_bytes = buffer.getvalue()

    # 1. 녹음 환경 감지
    detector = RecordingDetector()
    detection = detector.detect_environment(audio_bytes)

    print(f"\n🔍 녹음 환경 감지:")
    print(f"환경: {detection['environment'].upper()}")
    print(f"신뢰도: {detection['confidence']:.2f}")
    print(f"스튜디오 점수: {detection['studio_score']:.2f}")
    print(f"판별 근거: {detection['reason']}")

    # 2. Lite 엔진 분석
    lite_analyzer = VocalAnalyzerLite()
    lite_result = lite_analyzer.analyze(audio_bytes)

    # 3. Studio 엔진 분석
    studio_analyzer = VocalAnalyzerStudio()
    studio_result = studio_analyzer.analyze(audio_bytes)

    # 4. 결과 비교
    print(f"\n📊 분석 결과 비교:")
    print("-" * 70)
    print(f"{'축':<12} {'Lite (폰용)':<15} {'Studio (스튜디오용)':<20} {'차이':<10}")
    print("-" * 70)

    lite_scores = lite_result["scores"]
    studio_scores = studio_result["scores"]

    for axis in ["brightness", "thickness", "loudness", "clarity"]:
        lite_val = lite_scores[axis]
        studio_val = studio_scores[axis]
        diff = studio_val - lite_val

        axis_name = {
            "brightness": "밝기",
            "thickness": "두께",
            "loudness": "음압",
            "clarity": "선명도",
        }[axis]

        print(
            f"{axis_name:<12} {lite_val:+6.1f}         {studio_val:+6.1f}              {diff:+6.1f}"
        )

    print("-" * 70)
    print(
        f"{'신뢰도':<12} {lite_result['confidence']:6.2f}         {studio_result['confidence']:6.2f}              {studio_result['confidence']-lite_result['confidence']:+6.2f}"
    )

    # 5. 품질 메타데이터 비교
    print(f"\n📈 품질 메타데이터 비교:")
    print("-" * 50)
    print(f"{'지표':<20} {'Lite':<12} {'Studio':<12}")
    print("-" * 50)

    lite_quality = lite_result["quality"]
    studio_quality = studio_result["quality"]

    print(
        f"{'LUFS':<20} {lite_quality['lufs']:6.1f}      {studio_quality['lufs']:6.1f}"
    )
    print(f"{'SNR':<20} {lite_quality['snr']:6.1f}      {studio_quality['snr']:6.1f}")
    print(
        f"{'클리핑 %':<20} {lite_quality['clipping_percent']:6.3f}      {studio_quality['clipping_percent']:6.3f}"
    )
    print(
        f"{'무음 %':<20} {lite_quality['silence_percent']:6.1f}      {studio_quality['silence_percent']:6.1f}"
    )

    # 6. 추천 엔진
    print(f"\n🎯 추천 분석 엔진:")
    if detection["environment"] == "studio":
        print("✅ Studio 엔진 추천 - 고품질 녹음에 최적화")
        recommended = studio_result
    elif detection["environment"] == "phone":
        print("✅ Lite 엔진 추천 - 폰 녹음에 최적화")
        recommended = lite_result
    else:
        # 신뢰도가 높은 쪽 선택
        if studio_result["confidence"] > lite_result["confidence"]:
            print("✅ Studio 엔진 추천 - 더 높은 신뢰도")
            recommended = studio_result
        else:
            print("✅ Lite 엔진 추천 - 더 높은 신뢰도")
            recommended = lite_result

    print(f"\n🏆 최종 추천 결과:")
    final_scores = recommended["scores"]
    print(f"밝기: {final_scores['brightness']:+6.1f}")
    print(f"두께: {final_scores['thickness']:+6.1f}")
    print(f"음압: {final_scores['loudness']:+6.1f}")
    print(f"선명도: {final_scores['clarity']:+6.1f}")
    print(f"신뢰도: {recommended['confidence']:.2f}")
    print(f"엔진: {recommended['engine'].upper()}")

    return {
        "detection": detection,
        "lite_result": lite_result,
        "studio_result": studio_result,
        "recommended": recommended,
    }


if __name__ == "__main__":
    file_path = (
        r"C:\Users\user\Desktop\FULL\female4\long_tones\forte\f4_long_forte_a.wav"
    )
    results = compare_analysis(file_path)
