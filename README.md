# SongLab PyWorld Vocal Analyzer

이 프로젝트는 pyworld를 기반으로 한 간단한 발성 분석 도구를 제공합니다. 하나의 모노 음성 파일을 입력으로 받아 아래 네 가지 핵심 지표를 계산합니다.

- **Formant (F1/F2/F3)**: 스펙트럼 엔벨로프에서 추정한 첫 세 개의 포먼트 주파수(Hz)
- **Chest-Head Ratio**: 저주파(흉성) 대 중·고주파(두성) 에너지 비율
- **Clarity**: pyworld의 aperiodicity로부터 계산한 조화/잡음 비율(1에 가까울수록 명료)
- **Power**: 전체 RMS 레벨(dB)

## 설치

```bash
python -m venv .venv
.\.venv\Scripts\activate        # PowerShell
pip install -r requirements.txt
```

## 사용법

```bash
python analysis.py path/to/vocal.wav
```

옵션:
- `--sample-rate`: 기본값 16000 Hz, 분석을 위해 자동 리샘플링
- `--frame-period`: pyworld 프레임 간격 (ms), 기본값 5.0

실행 결과는 콘솔에 키-값 형태로 출력됩니다.

## 지표 계산 요약
- **Formant**: pyworld `cheaptrick` 엔벨로프에서 90~5000 Hz 구간의 피크를 탐색하여 F1/F2/F3 평균값을 산출
- **Chest-Head Ratio**: 80~500 Hz 대역(흉성)과 500~3000 Hz 대역(두성)의 에너지 합 비율
- **Clarity**: aperiodicity 행렬을 0~1 범위로 제한한 뒤 `1 - 평균 aperiodicity`를 사용
- **Power**: 전체 파형 RMS를 dB 스케일로 변환

## 주의사항
- 입력 신호는 모노 음성 파일(WAV/FLAC 등)을 권장합니다.
- 완전히 무성음인 파일은 포먼트 및 비율 계산이 불가능합니다.
- 추정값은 마이크 특성, 녹음 환경, 발성 내용에 따라 달라집니다.
