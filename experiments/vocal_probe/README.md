# MERT vs AST 창법 분류 비교 실험

VocalSet의 10가지 창법(belt, breathy, inhaled, lip_trill, spoken, straight, trill, trillo, vibrato, vocal_fry)을
**가중치를 고정한 사전학습 모델 임베딩 + 로지스틱 회귀(linear probe)**로 분류해 두 모델을 비교합니다.

| 모델 | 체크포인트 | 입력 | 청크 길이 |
|---|---|---|---|
| MERT | `m-a-p/MERT-v1-95M` | 원본 파형 24kHz | 5초 |
| AST | `MIT/ast-finetuned-audioset-10-10-0.4593` | log-mel 16kHz | 10초 |

## 준비
```bash
pip install -r experiments/vocal_probe/requirements.txt
```
RTX 50 시리즈(Blackwell)는 CUDA 12.8 이상 빌드가 필요합니다. torch를 먼저
`pip install torch --index-url https://download.pytorch.org/whl/cu128` 로 설치하세요.
VocalSet(Wilkins et al., ISMIR 2018)을 Zenodo에서 받아 압축을 풀고 `FULL` 폴더 경로를 준비합니다.
(`FULL/<가수>/<컨텍스트>/<창법>/*.wav` 구조)

## 실행 (저장소 루트에서)
```bash
# 1) 임베딩 추출 — 결과는 outputs/vocal_probe/*.npz (gitignore 대상)
python experiments/vocal_probe/extract.py --model mert --data-root /path/to/VocalSet/FULL
python experiments/vocal_probe/extract.py --model ast  --data-root /path/to/VocalSet/FULL

# 2) 비교 평가
python experiments/vocal_probe/evaluate.py outputs/vocal_probe/mert.npz outputs/vocal_probe/ast.npz \
    --csv outputs/vocal_probe/scores.csv
```
- 빠른 동작 확인: `--limit 50`
- MERT-330M 비교: `--model mert --checkpoint m-a-p/MERT-v1-330M --out outputs/vocal_probe/mert330.npz`
- GPU가 있으면 자동 사용. CPU만으로도 95M/AST는 수 시간 안에 끝나는 규모입니다.

## 평가 방식
- 클립마다 청크별 임베딩을 시간 평균 → 청크 평균 → `[레이어, 차원]` 벡터 1개
  (AST는 패딩 구간 패치를 제외하고 평균)
- **가수 단위 GroupKFold(기본 5-fold)**: 테스트 가수는 학습에 절대 등장하지 않음
- 레이어별 정확도·macro-F1, 전체 레이어 평균, 최고 레이어의 창법별 recall 출력

MARBLE 논문(MERT-330M 76.9%)과는 분할·분류기 설정이 달라 수치를 그대로 비교할 수는 없고,
**같은 조건에서 MERT와 AST의 상대 비교**가 목적입니다.
