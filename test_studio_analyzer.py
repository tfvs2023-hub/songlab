"""
Studio 엔진으로 오디오 파일 분석 테스트
"""

import os
import sys

import soundfile as sf

from vocal_analyzer_studio import VocalAnalyzerStudio


def test_studio_analyze(file_path):
    print(f"\n{'='*60}")
    print(f"Studio 분석 파일: {file_path}")
    print(f"{'='*60}")

    # 분석기 초기화
    analyzer = VocalAnalyzerStudio()

    # 오디오 파일 읽기
    audio_data, sr = sf.read(file_path)

    # 바이트로 변환
    import io

    buffer = io.BytesIO()
    sf.write(buffer, audio_data, sr, format="WAV")
    audio_bytes = buffer.getvalue()

    # 분석 수행
    result = analyzer.analyze(audio_bytes)

    # 결과 출력
    print("\n🎼 4축 분석 결과 (Studio Engine):")
    print("-" * 40)
    scores = result["scores"]
    print(
        f"✨ 밝기 (Brightness):  {scores['brightness']:+6.1f} {'🌟' if scores['brightness'] > 0 else '🌙'}"
    )
    print(
        f"🎯 두께 (Thickness):   {scores['thickness']:+6.1f} {'🔴' if scores['thickness'] > 0 else '⚪'}"
    )
    print(
        f"🔊 음압 (Loudness):    {scores['loudness']:+6.1f} {'💪' if scores['loudness'] > 0 else '🍃'}"
    )
    print(
        f"💎 선명도 (Clarity):   {scores['clarity']:+6.1f} {'✅' if scores['clarity'] > 0 else '⚠️'}"
    )

    # 신뢰도
    confidence = result["confidence"]
    print(f"\n🎯 신뢰도: {confidence:.2f}")
    if confidence > 0.8:
        print("   → 매우 높은 신뢰도 ⭐")
    elif confidence > 0.6:
        print("   → 높은 신뢰도 ✅")
    elif confidence > 0.3:
        print("   → 보통 신뢰도 ⚠️")
    else:
        print("   → 낮은 신뢰도 ❌")

    # 품질 메타데이터
    print("\n📈 품질 메타데이터 (Studio):")
    print("-" * 40)
    quality = result["quality"]
    print(f"LUFS: {quality['lufs']:.1f} dB")
    print(f"SNR: {quality['snr']:.1f} dB")
    print(f"클리핑: {quality['clipping_percent']:.3f}%")
    print(f"무음: {quality['silence_percent']:.1f}%")
    print(f"Dynamic Range: {quality.get('dynamic_range', 0):.1f} dB")

    # 고급 피처
    if "features_summary" in result:
        print("\n🔬 고급 피처 분석:")
        print("-" * 40)
        fs = result["features_summary"]
        print(f"HNR: {fs.get('hnr', 0):.1f} dB")
        print(f"Jitter: {fs.get('jitter', 0):.3f}%")
        print(f"Shimmer: {fs.get('shimmer', 0):.3f}%")
        print(f"F1: {fs.get('f1', 0):.0f} Hz")
        print(f"F2: {fs.get('f2', 0):.0f} Hz")
        print(f"F3: {fs.get('f3', 0):.0f} Hz")
        print(f"피치 평균: {fs.get('pitch_mean', 0):.0f} Hz")

    # 품질 평가
    print("\n💡 Studio 품질 평가:")
    if quality["snr"] < 40:
        print("⚠️ SNR이 스튜디오 기준보다 낮음 (40dB 권장)")
    else:
        print("✅ 우수한 SNR")
    if quality["clipping_percent"] > 0.1:
        print("⚠️ 클리핑 감지 - 매우 엄격한 기준")
    else:
        print("✅ 클리핑 없음")
    if quality.get("dynamic_range", 20) < 20:
        print("⚠️ Dynamic Range가 낮음")
    else:
        print("✅ 양호한 Dynamic Range")

    assert result is not None


if __name__ == "__main__":
    file_path = (
        r"C:\Users\user\Desktop\FULL\female4\long_tones\forte\f4_long_forte_a.wav"
    )
    result = test_studio_analyze(file_path)
