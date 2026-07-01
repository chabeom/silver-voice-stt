#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

MANIFEST_DIR="${MANIFEST_DIR:-training data/processed/modern_story_school_manifest}"
OUTPUT_DIR="${OUTPUT_DIR:-models/whisper-ko-elderly-nas-gpu}"
MODEL_NAME="${MODEL_NAME:-openai/whisper-small}"
TRAIN_STRATEGY="${TRAIN_STRATEGY:-lora-encoder}"
EPOCHS="${EPOCHS:-1}"
BATCH_SIZE="${BATCH_SIZE:-4}"
EVAL_BATCH_SIZE="${EVAL_BATCH_SIZE:-4}"
GRADIENT_ACCUMULATION_STEPS="${GRADIENT_ACCUMULATION_STEPS:-2}"
LEARNING_RATE="${LEARNING_RATE:-1e-5}"
DATALOADER_NUM_WORKERS="${DATALOADER_NUM_WORKERS:-2}"
LOGGING_STEPS="${LOGGING_STEPS:-10}"
SAVE_TOTAL_LIMIT="${SAVE_TOTAL_LIMIT:-2}"
MAX_TRAIN_SAMPLES="${MAX_TRAIN_SAMPLES:-}"
MAX_EVAL_SAMPLES="${MAX_EVAL_SAMPLES:-}"
MAX_LABEL_TOKENS="${MAX_LABEL_TOKENS:-}"
MIN_AUDIO_SECONDS="${MIN_AUDIO_SECONDS:-0.3}"
MAX_AUDIO_SECONDS="${MAX_AUDIO_SECONDS:-}"
LORA_ADAPTER_PATH="${LORA_ADAPTER_PATH:-}"
RUN_NAME="${RUN_NAME:-nas-gpu-$(date +%Y%m%d-%H%M%S)}"
BACKGROUND="${BACKGROUND:-0}"
USE_FP16="${USE_FP16:-0}"
USE_BF16="${USE_BF16:-1}"
DISABLE_GRADIENT_CHECKPOINTING="${DISABLE_GRADIENT_CHECKPOINTING:-1}"

cd "$REPO_ROOT"

export PYTHONPATH="$REPO_ROOT/services/training_pipeline"
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

resolve_path() {
  if [[ "$1" = /* ]]; then
    printf '%s\n' "$1"
  else
    printf '%s/%s\n' "$REPO_ROOT" "$1"
  fi
}

MANIFEST_PATH="$(resolve_path "$MANIFEST_DIR")"
TRAIN_MANIFEST="$MANIFEST_PATH/train.jsonl"
VALID_MANIFEST="$MANIFEST_PATH/valid.jsonl"
TEST_MANIFEST="$MANIFEST_PATH/test.jsonl"
OUTPUT_PATH="$(resolve_path "$OUTPUT_DIR")"
LOG_DIR="$REPO_ROOT/logs/training"
LOG_PATH="$LOG_DIR/$RUN_NAME.log"
ERR_PATH="$LOG_DIR/$RUN_NAME.err.log"
TRAIN_SCRIPT="$REPO_ROOT/services/training_pipeline/scripts/train_whisper.py"
HISTORY_SCRIPT="$REPO_ROOT/services/training_pipeline/scripts/record_training_result.py"

mkdir -p "$OUTPUT_PATH" "$LOG_DIR"

if [[ "$USE_FP16" == "1" && "$USE_BF16" == "1" ]]; then
  echo "USE_FP16 and USE_BF16 cannot both be 1. Use one mixed-precision mode at a time." >&2
  exit 1
fi

if [[ ! -f "$TRAIN_MANIFEST" || ! -f "$VALID_MANIFEST" ]]; then
  echo "Manifest files were not found under: $MANIFEST_PATH" >&2
  echo "Expected train.jsonl and valid.jsonl." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import torch

print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("device count:", torch.cuda.device_count())
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available. Run scripts/check-nas-gpu.sh first.")
print("device name:", torch.cuda.get_device_name(0))
PY

ARGS=(
  "$TRAIN_SCRIPT"
  "--model-name-or-path" "$MODEL_NAME"
  "--train-manifest" "$TRAIN_MANIFEST"
  "--valid-manifest" "$VALID_MANIFEST"
  "--output-dir" "$OUTPUT_PATH"
  "--language" "korean"
  "--task" "transcribe"
  "--train-strategy" "$TRAIN_STRATEGY"
  "--batch-size" "$BATCH_SIZE"
  "--eval-batch-size" "$EVAL_BATCH_SIZE"
  "--gradient-accumulation-steps" "$GRADIENT_ACCUMULATION_STEPS"
  "--epochs" "$EPOCHS"
  "--learning-rate" "$LEARNING_RATE"
  "--logging-steps" "$LOGGING_STEPS"
  "--save-total-limit" "$SAVE_TOTAL_LIMIT"
  "--dataloader-num-workers" "$DATALOADER_NUM_WORKERS"
  "--min-audio-seconds" "$MIN_AUDIO_SECONDS"
)

if [[ -f "$TEST_MANIFEST" ]]; then
  ARGS+=("--test-manifest" "$TEST_MANIFEST")
fi
if [[ -n "$MAX_TRAIN_SAMPLES" ]]; then
  ARGS+=("--max-train-samples" "$MAX_TRAIN_SAMPLES")
fi
if [[ -n "$MAX_EVAL_SAMPLES" ]]; then
  ARGS+=("--max-eval-samples" "$MAX_EVAL_SAMPLES")
fi
if [[ -n "$MAX_LABEL_TOKENS" ]]; then
  ARGS+=("--max-label-tokens" "$MAX_LABEL_TOKENS")
fi
if [[ -n "$MAX_AUDIO_SECONDS" ]]; then
  ARGS+=("--max-audio-seconds" "$MAX_AUDIO_SECONDS")
fi
if [[ -n "$LORA_ADAPTER_PATH" ]]; then
  ARGS+=("--lora-adapter-path" "$(resolve_path "$LORA_ADAPTER_PATH")")
fi
if [[ "$USE_FP16" == "1" ]]; then
  ARGS+=("--fp16")
fi
if [[ "$USE_BF16" == "1" ]]; then
  ARGS+=("--bf16")
fi
if [[ "$DISABLE_GRADIENT_CHECKPOINTING" == "1" ]]; then
  ARGS+=("--disable-gradient-checkpointing")
fi

record_history() {
  local result_file="$OUTPUT_PATH/training_result.json"
  if [[ -f "$result_file" ]]; then
    "$PYTHON_BIN" "$HISTORY_SCRIPT" \
      --result-file "$result_file" \
      --history-csv "$REPO_ROOT/models/training_history.csv" \
      --history-jsonl "$REPO_ROOT/models/training_history.jsonl" \
      --run-name "$RUN_NAME"
  fi
}

if [[ "$BACKGROUND" == "1" ]]; then
  (
    set -euo pipefail
    "$PYTHON_BIN" "${ARGS[@]}" >"$LOG_PATH" 2>"$ERR_PATH"
    record_history >>"$LOG_PATH" 2>>"$ERR_PATH"
  ) &
  PID=$!
  echo "Training started in the background."
  echo "PID: $PID"
  echo "stdout log: $LOG_PATH"
  echo "stderr log: $ERR_PATH"
  echo "Watch log: tail -f \"$LOG_PATH\""
else
  echo "Training started in the current shell."
  echo "Log: $LOG_PATH"
  "$PYTHON_BIN" "${ARGS[@]}" 2>&1 | tee "$LOG_PATH"
  record_history
fi
