#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-$HOME/nas_private/stt-venv}"
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
fi

export STT_BASE_MODEL="${STT_BASE_MODEL:-openai/whisper-medium}"
export STT_ADAPTER_PATH="${STT_ADAPTER_PATH:-models/whisper-medium-forced-v1-trip}"
export STT_DEVICE="${STT_DEVICE:-cuda}"
export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9001}"

echo "Starting Silver Voice STT inference API"
echo "Base model : $STT_BASE_MODEL"
echo "Adapter    : $STT_ADAPTER_PATH"
echo "Device     : $STT_DEVICE"
echo "Address    : http://$HOST:$PORT"

python3 -m uvicorn app:app \
  --app-dir "$ROOT_DIR/services/inference_api" \
  --host "$HOST" \
  --port "$PORT"
