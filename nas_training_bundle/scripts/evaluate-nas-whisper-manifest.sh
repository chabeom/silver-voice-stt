#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

MODEL_NAME="${MODEL_NAME:-openai/whisper-large-v3}"
ADAPTER_PATH="${ADAPTER_PATH:-}"
MANIFEST="${MANIFEST:-processed/modern_story_manifest_split_v1/test.jsonl}"
OUTPUT_JSON="${OUTPUT_JSON:-reports/evaluation/whisper-large-v3-baseline-test.json}"
PREDICTION_MANIFEST="${PREDICTION_MANIFEST:-}"
MAX_SAMPLES="${MAX_SAMPLES:-}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-256}"
DEVICE="${DEVICE:-cuda}"
LOCAL_FILES_ONLY="${LOCAL_FILES_ONLY:-0}"

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/services/training_pipeline"
mkdir -p "$(dirname "$OUTPUT_JSON")"

resolve_path() {
  if [[ "$1" = /* ]]; then
    printf '%s\n' "$1"
  else
    printf '%s/%s\n' "$REPO_ROOT" "$1"
  fi
}

ARGS=(
  "$REPO_ROOT/services/training_pipeline/scripts/evaluate_whisper_manifest.py"
  "--model-name-or-path" "$MODEL_NAME"
  "--manifest" "$(resolve_path "$MANIFEST")"
  "--output-json" "$(resolve_path "$OUTPUT_JSON")"
  "--device" "$DEVICE"
  "--max-new-tokens" "$MAX_NEW_TOKENS"
)

if [[ -n "$ADAPTER_PATH" ]]; then
  ARGS+=("--adapter-path" "$(resolve_path "$ADAPTER_PATH")")
fi
if [[ -n "$PREDICTION_MANIFEST" ]]; then
  ARGS+=("--prediction-manifest" "$(resolve_path "$PREDICTION_MANIFEST")")
fi
if [[ -n "$MAX_SAMPLES" ]]; then
  ARGS+=("--max-samples" "$MAX_SAMPLES")
fi
if [[ "$LOCAL_FILES_ONLY" == "1" ]]; then
  ARGS+=("--local-files-only")
fi

"$PYTHON_BIN" "${ARGS[@]}"
