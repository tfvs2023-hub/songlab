"""
Lite 엔진 디버그 테스트
"""

import os
import sys

import numpy as np
import soundfile as sf

from vocal_analyzer_lite import VocalAnalyzerLite


def debug_analyze(file_path):
    print(f"\n분석 파일: {file_path}")

    # 오디오 파일 읽기
    audio_data, sr = sf.read(file_path)
    print(
        f"원본: Shape={audio_data.shape}, SR={sr}, Range=[{np.min(audio_data):.3f}, {np.max(audio_data):.3f}]"
    )

    # 분석기 초기화
    analyzer = VocalAnalyzerLite()

    # 전처리 테스트
    processed, quality = analyzer.preprocess(audio_data, sr)
    print(
        f"\n전처리 후: Shape={processed.shape}, Range=[{np.min(processed):.3f}, {np.max(processed):.3f}]"
    )
    print(f"품질: {quality}")

    # 피처 추출 테스트
    try:
        features = analyzer.extract_features(processed)
        print(f"\n추출된 피처:")
        for key, value in features.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.4f}")
    except Exception as e:
        print(f"피처 추출 오류: {e}")
        import traceback

        traceback.print_exc()

    # 전체 분석 테스트
    import io

    buffer = io.BytesIO()
    sf.write(buffer, audio_data, sr, format="WAV")
    audio_bytes = buffer.getvalue()

    try:
        result = analyzer.analyze(audio_bytes)
        print(f"\n최종 결과:")
        print(f"점수: {result['scores']}")
        print(f"신뢰도: {result['confidence']}")
    except Exception as e:
        print(f"분석 오류: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    file_path = (
        r"C:\Users\user\Desktop\FULL\female4\long_tones\forte\f4_long_forte_a.wav"
    )
    debug_analyze(file_path)
