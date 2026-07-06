#!/usr/bin/env bash
set -euo pipefail

# Run this inside the NAS training bundle to compare the base Whisper-medium
# model against the latest medium LoRA adapter on the same held-out test set.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
DEVICE="${DEVICE:-cuda}"
MAX_SAMPLES="${MAX_SAMPLES:-20}"
BASE_MODEL="${BASE_MODEL:-openai/whisper-medium}"
ADAPTER_PATH="${ADAPTER_PATH:-models/whisper-medium-forced-answer-v1-debug}"
MANIFEST="${MANIFEST:-processed/modern_story_forced_answer_full_v1/test.jsonl}"
OUTPUT_DIR="${OUTPUT_DIR:-reports/inference_compare/medium-vs-base-$(date +%Y%m%d-%H%M%S)}"
EVAL_SCRIPT="services/training_pipeline/scripts/evaluate_whisper_manifest.py"

if [[ ! -f "$EVAL_SCRIPT" ]]; then
  echo "Missing evaluator: $EVAL_SCRIPT" >&2
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "Missing manifest: $MANIFEST" >&2
  exit 1
fi

if [[ ! -d "$ADAPTER_PATH" ]]; then
  echo "Missing adapter model directory: $ADAPTER_PATH" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "[1/2] Evaluating base model: $BASE_MODEL"
"$PYTHON" "$EVAL_SCRIPT" \
  --model-name-or-path "$BASE_MODEL" \
  --manifest "$MANIFEST" \
  --output-json "$OUTPUT_DIR/base-medium.json" \
  --prediction-manifest "$OUTPUT_DIR/base-medium-predictions.jsonl" \
  --language korean \
  --task transcribe \
  --device "$DEVICE" \
  --max-samples "$MAX_SAMPLES"

echo "[2/2] Evaluating LoRA adapter: $ADAPTER_PATH"
"$PYTHON" "$EVAL_SCRIPT" \
  --model-name-or-path "$BASE_MODEL" \
  --adapter-path "$ADAPTER_PATH" \
  --manifest "$MANIFEST" \
  --output-json "$OUTPUT_DIR/medium-lora.json" \
  --prediction-manifest "$OUTPUT_DIR/medium-lora-predictions.jsonl" \
  --language korean \
  --task transcribe \
  --device "$DEVICE" \
  --max-samples "$MAX_SAMPLES"

"$PYTHON" - "$OUTPUT_DIR/base-medium.json" "$OUTPUT_DIR/medium-lora.json" <<'PY'
import json
import sys
from pathlib import Path

base_path = Path(sys.argv[1])
lora_path = Path(sys.argv[2])
base = json.loads(base_path.read_text(encoding="utf-8"))["summary"]
lora = json.loads(lora_path.read_text(encoding="utf-8"))["summary"]

def pct(value):
    return f"{value * 100:.2f}%"

print("\n=== Inference comparison ===")
print(f"Base WER/CER : {pct(base['wer'])} / {pct(base['cer'])}")
print(f"LoRA WER/CER : {pct(lora['wer'])} / {pct(lora['cer'])}")
print(f"WER change   : {(base['wer'] - lora['wer']) * 100:.2f}%p")
print(f"CER change   : {(base['cer'] - lora['cer']) * 100:.2f}%p")
print(f"Output dir   : {base_path.parent}")
PY
