#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

DATASET_ROOT="${DATASET_ROOT:-$HOME/nas_private/025.고령자 근현대 경험 기반 스토리 구술 데이터/3.개방데이터/1.데이터/Training}"
OUTPUT_DIR="${OUTPUT_DIR:-processed/modern_story_forced_answer_v1}"
VALIDATION_REPORT="${VALIDATION_REPORT:-reports/label_validation/large-v3-full/label_validation.jsonl}"
VALIDATION_PASSED_ONLY="${VALIDATION_PASSED_ONLY:-1}"
MAX_VALIDATION_CER="${MAX_VALIDATION_CER:-}"
MAX_VALIDATION_WER="${MAX_VALIDATION_WER:-}"
TARGET_ROLE="${TARGET_ROLE:-answer}"
DEVICE="${DEVICE:-cuda}"
LIMIT="${LIMIT:-}"
UROMAN_PATH="${UROMAN_PATH:-}"
MIN_SEGMENT_SECONDS="${MIN_SEGMENT_SECONDS:-0.5}"
MAX_SEGMENT_SECONDS="${MAX_SEGMENT_SECONDS:-30.0}"
MAX_TEXT_CHARS="${MAX_TEXT_CHARS:-220}"
PADDING_SECONDS="${PADDING_SECONDS:-0.12}"

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/services/training_pipeline"

ARGS=(
  services/training_pipeline/scripts/prepare_forced_aligned_aihub_dataset.py
  --dataset-root "$DATASET_ROOT"
  --output-dir "$OUTPUT_DIR"
  --target-role "$TARGET_ROLE"
  --device "$DEVICE"
  --min-segment-seconds "$MIN_SEGMENT_SECONDS"
  --max-segment-seconds "$MAX_SEGMENT_SECONDS"
  --max-text-chars "$MAX_TEXT_CHARS"
  --padding-seconds "$PADDING_SECONDS"
)

if [[ -n "$VALIDATION_REPORT" ]]; then
  ARGS+=("--validation-report" "$VALIDATION_REPORT")
fi
if [[ "$VALIDATION_PASSED_ONLY" == "1" ]]; then
  ARGS+=("--validation-passed-only")
fi
if [[ -n "$MAX_VALIDATION_CER" ]]; then
  ARGS+=("--max-validation-cer" "$MAX_VALIDATION_CER")
fi
if [[ -n "$MAX_VALIDATION_WER" ]]; then
  ARGS+=("--max-validation-wer" "$MAX_VALIDATION_WER")
fi
if [[ -n "$LIMIT" ]]; then
  ARGS+=("--limit" "$LIMIT")
fi
if [[ -n "$UROMAN_PATH" ]]; then
  ARGS+=("--uroman-path" "$UROMAN_PATH")
fi

"$PYTHON_BIN" "${ARGS[@]}"
