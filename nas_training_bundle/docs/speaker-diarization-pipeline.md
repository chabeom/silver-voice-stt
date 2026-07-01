# NAS Speaker Diarization Training Pipeline

이 문서는 NAS 학습번들 안에서 화자분리를 적용한 뒤, 분리된 고령자 발화 manifest로 Whisper 학습을 실행하는 절차입니다.

## 1. 역할

화자분리는 한 음성 파일 안에 질문자와 답변자가 같이 들어 있을 때 `SPEAKER_00`, `SPEAKER_01`처럼 말한 사람을 구간별로 나누는 단계입니다.

주의할 점은 화자분리가 나이와 성별을 직접 판별하지는 않는다는 것입니다. 이 번들의 기본값은 가장 오래 말한 화자를 고령자 답변자로 가정하고 `target-speaker=longest`를 사용합니다. 실제 학습 전에는 생성된 `reports`와 일부 WAV 파일을 직접 확인하는 것이 좋습니다.

## 2. Hugging Face 준비

`pyannote/speaker-diarization-community-1` 모델을 사용하려면 Hugging Face 토큰이 필요합니다.

1. Hugging Face 계정에 로그인합니다.
2. `pyannote/speaker-diarization-community-1` 모델 페이지에서 사용 조건에 동의합니다.
3. NAS JupyterLab Terminal에서 토큰을 설정합니다.

```bash
read -s -p "HF token: " HF_TOKEN
export HF_TOKEN
echo
```

## 3. 샘플 1개로 화자분리 테스트

```bash
cd ~/nas_private/nas_training_bundle
LIMIT=1 bash scripts/prepare-nas-speaker-diarization.sh
```

기본 입력 데이터 경로는 아래입니다.

```text
~/nas_private/sample_data
```

기본 출력 경로는 아래입니다.

```text
~/nas_private/processed/sample_diarized_manifest
```

## 4. 전체 화자분리 manifest 생성

샘플 테스트 결과가 정상이라면 전체 데이터를 처리합니다.

```bash
bash scripts/prepare-nas-speaker-diarization.sh
```

결과 폴더에는 다음 파일들이 생성됩니다.

```text
clips/
reports/
diarization.jsonl
train.jsonl
valid.jsonl
test.jsonl
dataset_summary.json
```

## 5. 화자분리 manifest로 학습

화자분리 결과를 사용해서 소량 테스트 학습을 먼저 실행합니다.

```bash
MAX_TRAIN_SAMPLES=100 \
MAX_EVAL_SAMPLES=20 \
MANIFEST_DIR="$HOME/nas_private/processed/sample_diarized_manifest" \
OUTPUT_DIR="$HOME/nas_private/models/whisper-ko-elderly-diarized-test" \
bash scripts/train-nas-whisper-gpu.sh
```

문제가 없으면 전체 학습을 백그라운드로 실행합니다.

```bash
BACKGROUND=1 \
MANIFEST_DIR="$HOME/nas_private/processed/sample_diarized_manifest" \
OUTPUT_DIR="$HOME/nas_private/models/whisper-ko-elderly-diarized-v1" \
bash scripts/train-nas-whisper-gpu.sh
```

로그 확인:

```bash
tail -f logs/training/*.log
```

## 6. 옵션

데이터 경로를 바꾸고 싶으면 `DATASET_ROOT`를 지정합니다.

```bash
DATASET_ROOT="$HOME/nas_private/my_aihub_data" \
bash scripts/prepare-nas-speaker-diarization.sh
```

화자 수를 바꾸고 싶으면 `NUM_SPEAKERS`를 지정합니다.

```bash
NUM_SPEAKERS=2 bash scripts/prepare-nas-speaker-diarization.sh
```

GPU 대신 CPU로 화자분리를 테스트해야 하면 `DIARIZATION_DEVICE=cpu`를 지정할 수 있습니다. 다만 매우 느립니다.

```bash
DIARIZATION_DEVICE=cpu LIMIT=1 bash scripts/prepare-nas-speaker-diarization.sh
```
