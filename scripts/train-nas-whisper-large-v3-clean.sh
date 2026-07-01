#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export MODEL_NAME="${MODEL_NAME:-openai/whisper-large-v3}"
export MANIFEST_DIR="${MANIFEST_DIR:-processed/modern_story_clean_full_v1}"
export OUTPUT_DIR="${OUTPUT_DIR:-models/whisper-large-v3-elderly-clean-full-v1}"
export TRAIN_STRATEGY="${TRAIN_STRATEGY:-lora}"
export EPOCHS="${EPOCHS:-2}"
export BATCH_SIZE="${BATCH_SIZE:-1}"
export EVAL_BATCH_SIZE="${EVAL_BATCH_SIZE:-1}"
export GRADIENT_ACCUMULATION_STEPS="${GRADIENT_ACCUMULATION_STEPS:-8}"
export LEARNING_RATE="${LEARNING_RATE:-5e-6}"
export LOGGING_STEPS="${LOGGING_STEPS:-25}"
export SAVE_TOTAL_LIMIT="${SAVE_TOTAL_LIMIT:-2}"
export MAX_LABEL_TOKENS="${MAX_LABEL_TOKENS:-440}"
export USE_FP16="${USE_FP16:-0}"
export USE_BF16="${USE_BF16:-1}"
export DISABLE_GRADIENT_CHECKPOINTING="${DISABLE_GRADIENT_CHECKPOINTING:-1}"

bash "$SCRIPT_DIR/train-nas-whisper-gpu.sh"
