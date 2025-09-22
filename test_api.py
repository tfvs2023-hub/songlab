"""
API 테스트 스크립트
"""

import json

import requests


def test_api(file_path, force_engine=None):
    url = "http://localhost:8002/api/analyze"

    if force_engine:
        url += f"?force_engine={force_engine}"

    with open(file_path, "rb") as f:
        files = {"file": ("audio.wav", f, "audio/wav")}

        try:
            print(f"Testing API: {url}")
            print(f"File: {file_path}")
            if force_engine:
                print(f"Force Engine: {force_engine}")

            response = requests.post(url, files=files)

            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ API 응답 성공!")
                print(f"엔진: {result['engine'].upper()}")
                print(
                    f"환경 감지: {result.get('detection', {}).get('environment', 'unknown')}"
                )

                scores = result["scores"]
                print(f"\n📊 분석 결과:")
                print(f"밝기: {scores['brightness']:+6.1f}")
                print(f"두께: {scores['thickness']:+6.1f}")
                print(f"음압: {scores['loudness']:+6.1f}")
                print(f"선명도: {scores['clarity']:+6.1f}")
                print(f"신뢰도: {result['confidence']:.2f}")

                if result["engine"] == "studio" and "extra_info" in result:
                    extra = result["extra_info"]
                    print(f"\n🔬 Studio 추가 정보:")
                    print(f"HNR: {extra.get('hnr', 0):.1f} dB")
                    print(f"Jitter: {extra.get('jitter', 0):.3f}%")
                    print(f"F1: {extra.get('formants', {}).get('f1', 0):.0f} Hz")
                    print(f"F2: {extra.get('formants', {}).get('f2', 0):.0f} Hz")

            else:
                print(f"❌ API 오류: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"❌ 연결 오류: {e}")


if __name__ == "__main__":
    # 테스트 파일 - 더 작은 파일로 변경
    test_file = (
        r"C:\Users\user\Desktop\FULL\female4\long_tones\forte\f4_long_forte_a.wav"
    )

    print("=== 자동 엔진 선택 테스트 ===")
    test_api(test_file)

    print("\n=== Studio 엔진 강제 테스트 ===")
    test_api(test_file, force_engine="studio")

    print("\n=== Lite 엔진 강제 테스트 ===")
    test_api(test_file, force_engine="lite")
