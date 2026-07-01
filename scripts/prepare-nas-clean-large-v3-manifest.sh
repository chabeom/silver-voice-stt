#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

DATASET_ROOT="${DATASET_ROOT:-$HOME/nas_private/025.고령자 근현대 경험 기반 스토리 구술 데이터/3.개방데이터/1.데이터/Training}"
OUTPUT_DIR="${OUTPUT_DIR:-processed/modern_story_clean_full_v1}"
TRANSCRIPT_MODE="${TRANSCRIPT_MODE:-full}"
MIN_DURATION_SECONDS="${MIN_DURATION_SECONDS:-1.0}"
MAX_DURATION_SECONDS="${MAX_DURATION_SECONDS:-30.0}"
MIN_TEXT_CHARS="${MIN_TEXT_CHARS:-2}"
MAX_TEXT_CHARS="${MAX_TEXT_CHARS:-260}"
MIN_CHARS_PER_SECOND="${MIN_CHARS_PER_SECOND:-0.5}"
MAX_CHARS_PER_SECOND="${MAX_CHARS_PER_SECOND:-14.0}"
VALIDATION_REPORT="${VALIDATION_REPORT:-}"
VALIDATION_PASSED_ONLY="${VALIDATION_PASSED_ONLY:-0}"
MAX_VALIDATION_CER="${MAX_VALIDATION_CER:-}"
MAX_VALIDATION_WER="${MAX_VALIDATION_WER:-}"

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/services/training_pipeline"

ARGS=(
  services/training_pipeline/scripts/prepare_aihub_dataset.py
  --dataset-root "$DATASET_ROOT"
  --output-dir "$OUTPUT_DIR"
  --transcript-mode "$TRANSCRIPT_MODE"
  --min-duration-seconds "$MIN_DURATION_SECONDS"
  --max-duration-seconds "$MAX_DURATION_SECONDS"
  --min-text-chars "$MIN_TEXT_CHARS"
  --max-text-chars "$MAX_TEXT_CHARS"
  --min-chars-per-second "$MIN_CHARS_PER_SECOND"
  --max-chars-per-second "$MAX_CHARS_PER_SECOND"
  --disable-long-audio-segmentation
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

"$PYTHON_BIN" "${ARGS[@]}"
