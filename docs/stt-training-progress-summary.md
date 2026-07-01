# Silver Voice STT 진행 요약

작성일: 2026-07-01

## 프로젝트 목표

본 프로젝트의 핵심 목표는 프론트엔드/백엔드 서비스 자체가 아니라, 60세 이상 고령자의 발화를 정확하게 텍스트로 변환할 수 있는 한국어 STT fine-tuning 모델을 만드는 것이다.

프론트엔드와 백엔드는 학습된 음성 모델이 실제 음성 파일에서 어느 정도 정확도로 STT를 수행하는지 확인하기 위한 테스트 플랫폼 역할을 한다.

## 진행한 작업

### 1. STT 테스트 플랫폼 구축

- 음성 파일 업로드, STT 작업 실행, 결과 확인, 관리자 분석 흐름을 포함한 프론트엔드/백엔드 구조를 점검했다.
- STT 작업 상태, 신뢰도, 결과 정정, 재학습 피드백을 다룰 수 있도록 API와 UI 구조를 확장했다.
- 추론 결과에서 단어/구간별 confidence를 표시하고, 낮은 신뢰도의 구간을 확인할 수 있는 구조를 추가했다.

### 2. 추론 및 화자분리 기능 확장

- STT 추론 파이프라인에 confidence 계산 로직을 추가했다.
- 실제 업로드 음성에서 질문자와 답변자가 섞일 수 있으므로, 화자분리 기능을 프론트엔드/백엔드 및 추론 파이프라인에서 고려하도록 구조를 추가했다.
- 향후 NAS GPU 환경에서 pyannote 기반 화자분리와 answer-only 학습 데이터를 만들 수 있도록 준비했다.

### 3. 로컬 CPU 기반 학습 파이프라인 검증

- NAS GPU 구축 전까지 로컬 노트북 CPU 환경에서 소량 학습 파이프라인을 먼저 구성했다.
- AI-Hub 데이터의 원천 음성과 라벨링 데이터를 manifest 형태로 변환하고, Whisper 계열 모델로 fine-tuning이 가능한지 확인했다.
- CPU 실험은 모델 성능 확보보다는 학습 로직과 데이터 흐름 검증 목적이었다.

### 4. NAS GPU 학습 파이프라인 구축

- NAS JupyterLab 환경에서 RTX 5090 GPU를 인식하고, PyTorch/CUDA/Transformers 기반 학습 환경을 구성했다.
- NAS에 올린 AI-Hub 데이터에서 학습용 manifest를 생성하고, LoRA 방식으로 Whisper 모델을 학습할 수 있는 스크립트를 구성했다.
- `train-nas-whisper-gpu.sh`, `setup-nas-training-env.sh`, `check-nas-gpu.sh` 등 NAS 실행용 스크립트를 정리했다.

### 5. AI-Hub 데이터 정합성 검증

- AI-Hub 고령자 근현대 경험 기반 스토리 구술 데이터의 원천 WAV와 JSON 라벨 파일을 분석했다.
- 라벨 파일 2,923개 중 실제 WAV와 매칭되는 파일은 799개였고, 원본 `openai/whisper-large-v3` 기준 CER 0.5 이하로 통과한 파일은 567개였다.
- 이 검증 결과를 통해 무작정 전체 데이터를 학습하기보다, 라벨과 음성이 어느 정도 맞는 데이터만 선별하는 방향으로 전환했다.

### 6. 기존 full-label 방식의 문제 확인

- 초기 방식은 WAV 파일 전체와 JSON 라벨 전체를 1:1로 맞추거나, 긴 텍스트를 강제로 나누어 학습하는 구조였다.
- 이 방식은 질문자와 답변자 음성이 섞이고, Whisper decoder token limit을 초과하는 문제가 있었다.
- 실제로 full-label 기반 large-v3 학습에서는 대부분의 샘플이 token filter로 제외되어 train 134개 수준까지 줄어들었다.

### 7. Forced alignment answer-only 방식 도입

- 최종 목표가 고령자 답변 발화 STT 모델이므로, 질문자 구간을 제외하고 답변자 answer 구간만 학습하도록 방향을 바꿨다.
- 라벨의 question/answer 순서를 하나의 텍스트로 이어 붙이고, 원본 WAV 전체에 대해 forced alignment를 수행해 각 answer turn의 시작/끝 시간을 추정했다.
- answer 구간만 잘라 clip으로 저장하고, 해당 answer 텍스트와 매칭한 answer-only manifest를 생성했다.
- 그 결과 약 9,394개 clip, 총 약 20.75시간 규모의 학습 후보 데이터를 만들었다.

## 주요 실험 결과

| 구분 | 기반 모델 | 방식 | Test WER | Test CER | 비고 |
| --- | --- | --- | ---: | ---: | --- |
| CPU 초기 실험 | Whisper 계열 | 로컬 CPU 소량 학습 | 약 123% | 약 94% | 파이프라인 검증 목적 |
| NAS small old split | openai/whisper-small | full-label split | 약 197% | 약 151% | 정렬 오류가 큼 |
| large-v3 baseline | openai/whisper-large-v3 | 학습 전 평가 | 약 81.2% | 약 64.9% | 100개 샘플 기준 |
| large-v3 full-label v2 | openai/whisper-large-v3 | full WAV/full label | 약 80.4% | 약 74.7% | token limit으로 학습 샘플 급감 |
| small forced-answer | openai/whisper-small | answer-only clip + LoRA | 약 64.9% | 약 44.2% | 현재까지 가장 의미 있는 개선 |

## 현재 판단

- 성능 병목은 단순히 모델 크기가 아니라, 음성과 라벨의 정렬 품질이었다.
- full WAV/full label 방식보다 forced alignment로 answer 구간만 잘라 학습하는 방식이 프로젝트 목표에 더 맞다.
- `openai/whisper-small` 기반 forced-answer 학습에서 CER이 44.19%까지 내려가면서 방향성이 검증되었다.
- 다음 단계는 같은 answer-only manifest를 기준으로 `openai/whisper-medium`, 이후 `openai/whisper-large-v3`를 비교하는 것이다.

## 다음 액션

1. medium forced-answer 학습 결과의 WER/CER를 small forced-answer 결과와 비교한다.
2. 같은 test set에서 원본 Whisper, small LoRA, medium LoRA, large-v3 LoRA를 동일 조건으로 평가한다.
3. forced alignment로 생성된 answer clip을 랜덤 청취하여 질문자 음성이 섞이는지 확인한다.
4. medium 결과가 개선되면 large-v3 answer-only LoRA 학습을 진행한다.
5. 추후 데이터가 더 확보되면 통합 모델과 주제별 LoRA adapter 모델을 비교한다.
