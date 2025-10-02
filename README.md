# SongLab PyWorld Vocal Analyzer

pyworld와 CREPE를 활용해 발성 지표를 계산하고, YouTube/OpenAI API 헬퍼로 확장 가능한 실험 환경을 제공합니다.

## 주요 기능
- **Vocal Analysis (`analysis.py`)**: 모노 음성 파일에서 포먼트·흉성/두성 비율·명료도·파워 추출
- **YouTube Helper (`youtube_client.py`)**: YouTube Data API v3로 영상 검색
- **OpenAI Helper (`openai_client.py`)**: OpenAI Responses API로 요약/텍스트 생성
- **Integration Example (`integration_example.py`)**: YouTube 검색 결과를 요약하는 샘플 워크플로

## 설치
```bash
python -m venv .venv
.\.venv\Scripts\activate        # PowerShell 기준
pip install -r requirements.txt
```

## 환경 변수 설정 (API 키 붙여넣기)
1. `.env.example`을 `.env`로 복사합니다.
   ```powershell
   copy .env.example .env
   ```
2. 새로 생성된 `.env` 파일을 열어 아래와 같이 키를 붙여넣습니다.
   ```env
   YOUTUBE_API_KEY=발급받은_유튜브_API키
   OPENAI_API_KEY=발급받은_OpenAI_API키
   ```
   → `python-dotenv`가 자동으로 `.env`를 로드하므로, 별도 코드 수정 없이 바로 사용할 수 있습니다.

(필요하면 PowerShell에서 임시로 환경 변수를 지정할 수도 있습니다.)
```powershell
$env:YOUTUBE_API_KEY="YOUR_YT_KEY"
$env:OPENAI_API_KEY="YOUR_OPENAI_KEY"
```

## 사용 예시
### 1. 발성 분석
```bash
python analysis.py assets/sample.wav --sample-rate 16000 --frame-period 5.0
```

### 2. YouTube + OpenAI 요약
```python
from integration_example import summarize_top_youtube_video

summary = summarize_top_youtube_video("belting vocal lesson")
print(summary)
```
> 실제 실행에는 API 키가 필요하며, CREPE 최초 실행 시 모델 다운로드 시간이 발생할 수 있습니다.

## 지표 계산 요약
- **Formant**: pyworld `cheaptrick` 스펙트럼으로 90~5000 Hz 피크 탐색
- **Chest-Head Ratio**: 80~500 Hz vs 500~3000 Hz 에너지 비율
- **Clarity**: `1 - 평균 aperiodicity`
- **Power**: 전체 RMS → dB 변환

## 주의사항
- 입력 음성은 모노(WAV/FLAC)를 권장하며, 녹음 품질에 따라 값이 달라질 수 있습니다.
- YouTube API는 할당량 제한이 있으니 필요한 범위에서 사용하세요.
- OpenAI 호출 시 과금이 발생할 수 있으니 모델/토큰 사용량을 확인하세요.
