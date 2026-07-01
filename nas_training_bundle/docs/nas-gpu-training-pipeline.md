# NAS GPU Training Pipeline

이 문서는 JupyterLab 컨테이너에서 RTX GPU가 정상 연결된 뒤, Silver Voice 한국어 STT 학습을 실행하는 최소 절차입니다.

## 1. GPU 확인

NAS/JupyterLab 터미널에서 프로젝트 루트로 이동한 뒤 실행합니다.

```bash
bash scripts/check-nas-gpu.sh
```

정상 상태라면 `nvidia-smi` 표가 출력되고, PyTorch 확인 결과가 아래처럼 나와야 합니다.

```text
cuda available: True
device count: 1
```

`Failed to initialize NVML` 또는 `cuda available: False`가 나오면 학습을 시작하지 말고 관리자에게 GPU passthrough/NVIDIA Container Toolkit 설정을 다시 확인 요청해야 합니다.

## 2. 학습 의존성 설치

NAS JupyterLab 이미지에 이미 CUDA용 PyTorch가 설치되어 있으므로 `torch`를 다시 설치하지 않습니다.

```bash
bash scripts/setup-nas-training-env.sh
```

이 스크립트는 `services/training_pipeline/requirements-nas-gpu.txt`만 설치합니다. 기존 `services/training_pipeline/requirements.txt`는 로컬 CPU 환경용 `torch` 조건이 들어 있으므로 NAS GPU 환경에서는 바로 설치하지 않는 편이 안전합니다.

## 3. 학습 실행

기본값은 `training data/processed/modern_story_school_manifest`를 사용하고, 모델은 `openai/whisper-small`로 시작합니다.

```bash
bash scripts/train-nas-whisper-gpu.sh
```

백그라운드에서 돌리고 싶으면 아래처럼 실행합니다.

```bash
BACKGROUND=1 bash scripts/train-nas-whisper-gpu.sh
```

로그 확인:

```bash
tail -f logs/training/*.log
```

## 4. 주요 옵션

샘플만 빠르게 테스트:

```bash
MAX_TRAIN_SAMPLES=100 MAX_EVAL_SAMPLES=20 bash scripts/train-nas-whisper-gpu.sh
```

더 큰 모델로 학습:

```bash
MODEL_NAME=openai/whisper-medium bash scripts/train-nas-whisper-gpu.sh
```

기존 LoRA 어댑터를 이어서 업데이트:

```bash
LORA_ADAPTER_PATH=models/whisper-ko-elderly-modern-story-school-v2 \
OUTPUT_DIR=models/whisper-ko-elderly-nas-gpu-v3 \
bash scripts/train-nas-whisper-gpu.sh
```

## 5. 결과 위치

학습된 LoRA 어댑터와 결과 파일은 기본적으로 아래에 저장됩니다.

```text
models/whisper-ko-elderly-nas-gpu/
```

성능 기록은 아래 파일에 누적됩니다.

```text
models/training_history.csv
models/training_history.jsonl
```
