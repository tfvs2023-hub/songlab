"""
오디오 파일 일부 구간 분석 테스트
"""

import os
import sys

import numpy as np
import soundfile as sf

from recording_detector import RecordingDetector
from vocal_analyzer_lite import VocalAnalyzerLite
from vocal_analyzer_studio import VocalAnalyzerStudio


def analyze_segment(file_path, start_time=None, duration=30):
    """
    오디오 파일의 특정 구간 분석
    start_time: None이면 중간 지점부터 시작
    duration: 분석할 길이 (초)
    """
    print(f"\n{'='*70}")
    print(f"분석 파일: {file_path}")
    print(f"{'='*70}")

    # 오디오 파일 읽기
    audio_data, sr = sf.read(file_path)
    total_duration = len(audio_data) / sr

    print(f"전체 길이: {total_duration:.1f}초")

    # 시작 시점 결정 (None이면 중간점)
    if start_time is None:
        start_time = max(0, (total_duration - duration) / 2)

    # 구간 추출
    start_sample = int(start_time * sr)
    end_sample = int((start_time + duration) * sr)
    end_sample = min(end_sample, len(audio_data))

    if len(audio_data.shape) > 1:
        segment = audio_data[start_sample:end_sample]
    else:
        segment = audio_data[start_sample:end_sample]

    actual_duration = len(segment) / sr
    print(
        f"분석 구간: {start_time:.1f}s ~ {start_time + actual_duration:.1f}s ({actual_duration:.1f}초)"
    )

    # 바이트로 변환
    import io

    buffer = io.BytesIO()
    sf.write(buffer, segment, sr, format="WAV")
    audio_bytes = buffer.getvalue()

    # 1. 녹음 환경 감지
    detector = RecordingDetector()
    detection = detector.detect_environment(audio_bytes)

    print(f"\n🔍 녹음 환경 감지:")
    print(f"환경: {detection['environment'].upper()}")
    print(f"신뢰도: {detection['confidence']:.2f}")
    print(f"스튜디오 점수: {detection['studio_score']:.2f}")
    print(f"판별 근거: {detection['reason']}")

    # 환경 감지 세부사항
    if "indicators" in detection:
        indicators = detection["indicators"]
        print(f"\n🔬 감지 지표:")
        print(f"대역폭: {indicators.get('bandwidth', 0):.2f}")
        print(f"SNR: {indicators.get('snr', 0):.2f}")
        print(f"압축 아티팩트: {indicators.get('compression_artifacts', 0):.2f}")
        print(f"AGC 감지: {indicators.get('agc_detected', 0):.2f}")

    # 2. 적절한 엔진 선택 및 분석
    if detection["environment"] == "studio" or detection["studio_score"] > 0.5:
        print(f"\n🎼 Studio 엔진으로 분석:")
        analyzer = VocalAnalyzerStudio()
        result = analyzer.analyze(audio_bytes)

        # Studio 고급 피처 출력
        if "features_summary" in result:
            fs = result["features_summary"]
            print(f"\n🔬 고급 피처:")
            print(f"HNR: {fs.get('hnr', 0):.1f} dB")
            print(f"Jitter: {fs.get('jitter', 0):.3f}%")
            print(f"Shimmer: {fs.get('shimmer', 0):.3f}%")
            print(f"F1: {fs.get('f1', 0):.0f} Hz")
            print(f"F2: {fs.get('f2', 0):.0f} Hz")
            print(f"피치: {fs.get('pitch_mean', 0):.0f} Hz")
    else:
        print(f"\n📱 Lite 엔진으로 분석:")
        analyzer = VocalAnalyzerLite()
        result = analyzer.analyze(audio_bytes)

    # 결과 출력
    print(f"\n📊 4축 분석 결과:")
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
    if confidence > 0.7:
        print("   → 높은 신뢰도 ✅")
    elif confidence > 0.3:
        print("   → 보통 신뢰도 ⚠️")
    else:
        print("   → 낮은 신뢰도 ❌")

    # 품질 메타데이터
    print(f"\n📈 품질 메타데이터:")
    print("-" * 40)
    quality = result["quality"]
    print(f"LUFS: {quality['lufs']:.1f} dB")
    print(f"SNR: {quality['snr']:.1f} dB")
    print(f"클리핑: {quality['clipping_percent']:.3f}%")
    print(f"무음: {quality['silence_percent']:.1f}%")
    if "dynamic_range" in quality:
        print(f"Dynamic Range: {quality['dynamic_range']:.1f} dB")

    # 보컬 타입
    print(f"\n🎤 보컬 타입:")
    type_code = ""
    type_code += "B" if scores["brightness"] > 0 else "D"
    type_code += "T" if scores["thickness"] > 0 else "L"
    type_code += "S" if scores["loudness"] > 0 else "W"
    type_code += "C" if scores["clarity"] > 0 else "R"
    print(f"   {type_code} 타입")

    # 특징 설명
    characteristics = []
    if abs(scores["brightness"]) > 30:
        characteristics.append("밝은 음색" if scores["brightness"] > 0 else "어두운 음색")
    if abs(scores["thickness"]) > 30:
        characteristics.append("두꺼운 음색" if scores["thickness"] > 0 else "얇은 음색")
    if abs(scores["loudness"]) > 30:
        characteristics.append("강한 음압" if scores["loudness"] > 0 else "부드러운 음압")
    if abs(scores["clarity"]) > 30:
        characteristics.append("선명한 발성" if scores["clarity"] > 0 else "부드러운 발성")

    if characteristics:
        print(f"   특징: {', '.join(characteristics)}")

    return result


if __name__ == "__main__":
    file_path = r"C:\Users\user\Downloads\일반인추사닮.wav"

    # 파일 존재 확인
    if not os.path.exists(file_path):
        print(f"파일을 찾을 수 없습니다: {file_path}")
        sys.exit(1)

    # 중간 30초 분석
    result = analyze_segment(file_path, start_time=None, duration=30)
