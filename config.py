"""
Vocal Analysis Project Configuration
모든 설정 및 기준값을 이곳에서 관리합니다.
"""

# Lite 엔진 분석을 위한 기준 통계 (평균, 표준편차)
# 이 값을 조정하여 각 축의 점수 민감도를 튜닝할 수 있습니다.
LITE_ENGINE_REF_STATS = {
    "midhi_ratio": (0.3, 0.15),
    "spectral_centroid": (1500, 500),
    "low_ratio": (0.2, 0.1),
    "h1_h2": (5, 3),
    "rms_mean": (0.05, 0.02),
    "rms_std": (0.01, 0.005),
    "cpp_rel": (15, 5),
    "zcr": (0.05, 0.02),
    "pitch_dropout": (0.2, 0.1),
}

# 추가적인 설정값들을 여기에 정의할 수 있습니다.
TARGET_LUFS = -23.0
