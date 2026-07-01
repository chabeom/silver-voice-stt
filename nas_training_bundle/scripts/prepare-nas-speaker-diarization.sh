#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

DATASET_ROOT="${DATASET_ROOT:-$HOME/nas_private/sample_data}"
OUTPUT_DIR="${OUTPUT_DIR:-$HOME/nas_private/processed/sample_diarized_manifest}"
LIMIT="${LIMIT:-}"
NUM_SPEAKERS="${NUM_SPEAKERS:-2}"
DIARIZATION_DEVICE="${DIARIZATION_DEVICE:-cuda}"
TARGET_SPEAKER="${TARGET_SPEAKER:-longest}"

cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT/services/training_pipeline"

if [[ -z "${HF_TOKEN:-}" && -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  echo "HF_TOKEN is required. Accept the pyannote model conditions and export your Hugging Face token." >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c "import pyannote.audio" >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install -r services/training_pipeline/requirements-speaker-diarization.txt
fi

ARGS=(
  services/training_pipeline/scripts/prepare_speaker_diarized_aihub_dataset.py
  --dataset-root "$DATASET_ROOT"
  --output-dir "$OUTPUT_DIR"
  --device "$DIARIZATION_DEVICE"
  --num-speakers "$NUM_SPEAKERS"
  --target-speaker "$TARGET_SPEAKER"
)

if [[ -n "$LIMIT" ]]; then
  ARGS+=("--limit" "$LIMIT")
fi

"$PYTHON_BIN" "${ARGS[@]}"
