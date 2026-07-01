#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

DATASET_ROOT="${DATASET_ROOT:-$HOME/nas_private/025.고령자 근현대 경험 기반 스토리 구술 데이터/3.개방데이터/1.데이터/Training}"
OUTPUT_DIR="${OUTPUT_DIR:-reports/label_validation/large-v3-full}"
MODEL_NAME="${MODEL_NAME:-openai/whisper-large-v3}"
TRANSCRIPT_MODE="${TRANSCRIPT_MODE:-full}"
CER_THRESHOLD="${CER_THRESHOLD:-0.5}"
WER_THRESHOLD="${WER_THRESHOLD:-}"
LIMIT="${LIMIT:-}"
BATCH_SIZE="${BATCH_SIZE:-4}"
BACKGROUND="${BACKGROUND:-0}"
RUN_NAME="${RUN_NAME:-label-validation-$(date +%Y%m%d-%H%M%S)}"

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/services/training_pipeline"
mkdir -p "$OUTPUT_DIR" logs/validation

ARGS=(
  "$REPO_ROOT/services/training_pipeline/scripts/validate_aihub_labels_with_whisper.py"
  "--dataset-root" "$DATASET_ROOT"
  "--output-dir" "$OUTPUT_DIR"
  "--model-name" "$MODEL_NAME"
  "--transcript-mode" "$TRANSCRIPT_MODE"
  "--cer-threshold" "$CER_THRESHOLD"
  "--batch-size" "$BATCH_SIZE"
)

if [[ -n "$WER_THRESHOLD" ]]; then
  ARGS+=("--wer-threshold" "$WER_THRESHOLD")
fi
if [[ -n "$LIMIT" ]]; then
  ARGS+=("--limit" "$LIMIT")
fi

if [[ "$BACKGROUND" == "1" ]]; then
  LOG_PATH="$REPO_ROOT/logs/validation/$RUN_NAME.log"
  ERR_PATH="$REPO_ROOT/logs/validation/$RUN_NAME.err.log"
  "$PYTHON_BIN" "${ARGS[@]}" >"$LOG_PATH" 2>"$ERR_PATH" &
  PID=$!
  echo "Label validation started in the background."
  echo "PID: $PID"
  echo "stdout log: $LOG_PATH"
  echo "stderr log: $ERR_PATH"
  echo "Watch log: tail -f \"$LOG_PATH\""
else
  "$PYTHON_BIN" "${ARGS[@]}"
fi
