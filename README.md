# SongLab PyWorld Vocal Analyzer

이 프로젝트는 pyworld와 CREPE를 조합해 발성 분석을 수행합니다. 모노 음성 파일을 입력하면 다음 네 가지 지표를 계산합니다.

- **Formant (F1/F2/F3)**: pyworld의 `cheaptrick` 스펙트럼 엔벨로프에서 추정한 첫 세 포먼트(Hz)
- **Chest-Head Ratio**: 저주파(흉성) 대비 중·고주파(두성) 에너지 비율
- **Clarity**: pyworld aperiodicity로부터 계산한 조화 비율(값이 높을수록 명료)
- **Power**: 전체 RMS 레벨(dB)

CREPE는 F0(기본 주파수)와 발성 구간을 더 정확히 추출하며, pyworld는 스펙트럼 기반 포먼트·에너지 분석을 담당합니다.

## 설치

```bash
python -m venv .venv
.\.venv\Scripts\activate        # PowerShell 기준
pip install -r requirements.txt
```

## 사용법

```bash
python analysis.py path/to/vocal.wav \
    --sample-rate 16000 \
    --frame-period 5.0 \
    --confidence-threshold 0.5
```

옵션 설명:
- `--sample-rate`: 분석 전 리샘플링할 목표 샘플레이트 (기본 16000 Hz)
- `--frame-period`: CREPE 스텝/pyworld 프레임 간격(ms)
- `--confidence-threshold`: CREPE 신뢰도 하한 (미만일 경우 무성 구간 처리)

실행 결과는 콘솔에 `지표: 값` 형태로 출력됩니다. 값이 `nan`이면 해당 지표를 신뢰하기 어려운 경우(포먼트 미검출, 무성 구간 등)입니다.

## 지표 계산 요약
- **Formant**: 90~5000 Hz 구간에서 상위 3개의 스펙트럼 피크를 찾아 평균
- **Chest-Head Ratio**: 80~500 Hz vs 500~3000 Hz 대역 에너지 합 비율 평균
- **Clarity**: 무성 성분(aperiodicity)을 0~1 범위로 제한한 후 `1 - 평균 aperiodicity`
- **Power**: 파형 RMS → dB 변환

## 참고 및 주의사항
- 입력은 모노 음성 파일(WAV/FLAC 등)을 권장합니다. 다채널 파일은 평균하여 사용합니다.
- 녹음 품질, 마이크, 발성 내용에 따라 지표 편차가 발생할 수 있습니다.
- CREPE는 TensorFlow 없이 동작하지만, 첫 실행 시 모델 다운로드가 발생할 수 있습니다.
- 스펙트럼 분석은 발성 구간이 충분히 길어야 안정적인 값을 제공합니다.
