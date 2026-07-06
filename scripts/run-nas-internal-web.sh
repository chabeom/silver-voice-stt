#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WEB_VENV_DIR="${WEB_VENV_DIR:-$HOME/nas_private/stt-venv}"
if [[ -f "$WEB_VENV_DIR/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$WEB_VENV_DIR/bin/activate"
fi

if ! curl -fsS "http://127.0.0.1:9001/health" >/dev/null; then
  cat >&2 <<'EOF'
STT inference API is not reachable at http://127.0.0.1:9001/health.
Start it first in another NAS terminal:

  cd ~/nas_private/nas_training_bundle
  source ~/nas_private/stt-venv/bin/activate
  bash scripts/run-nas-inference-api.sh

EOF
  exit 1
fi

export PYTHONPATH="$ROOT_DIR/apps/api:$ROOT_DIR/services/stt_inference:$ROOT_DIR/services/training_pipeline:${PYTHONPATH:-}"

export ENVIRONMENT="${ENVIRONMENT:-nas-internal}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$ROOT_DIR/silver_voice_nas.db}"
export STORAGE_BACKEND="${STORAGE_BACKEND:-local}"
export LOCAL_STORAGE_PATH="${LOCAL_STORAGE_PATH:-$ROOT_DIR/apps/api/storage}"
export CELERY_TASK_ALWAYS_EAGER="${CELERY_TASK_ALWAYS_EAGER:-true}"

export DEFAULT_MODEL_VERSION="${DEFAULT_MODEL_VERSION:-whisper-medium-forced-v1-trip}"
export STT_MODEL_BACKEND="${STT_MODEL_BACKEND:-nas-api}"
export STT_REMOTE_API_URL="${STT_REMOTE_API_URL:-http://127.0.0.1:9001/transcribe}"
export STT_REMOTE_TIMEOUT_SECONDS="${STT_REMOTE_TIMEOUT_SECONDS:-1200}"
export STT_REMOTE_CHUNK_SECONDS="${STT_REMOTE_CHUNK_SECONDS:-30}"
export STT_REMOTE_CHUNK_OVERLAP_SECONDS="${STT_REMOTE_CHUNK_OVERLAP_SECONDS:-0}"
export STT_REMOTE_MIN_CHUNK_RMS="${STT_REMOTE_MIN_CHUNK_RMS:-0.0005}"
export STT_REMOTE_MAX_NEW_TOKENS="${STT_REMOTE_MAX_NEW_TOKENS:-256}"
export STT_MOCK_MODE="${STT_MOCK_MODE:-false}"

JUPYTER_USER="${JUPYTERHUB_USER:-${USER:-s202110742}}"
export API_CORS_ORIGINS="${API_CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000,http://61.81.98.88:8000}"
export NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-/user/$JUPYTER_USER/proxy/8000/api/v1}"

mkdir -p "$ROOT_DIR/logs" "$LOCAL_STORAGE_PATH"

run_api() {
  echo "Starting API on http://0.0.0.0:8000"
  echo "STT remote API: $STT_REMOTE_API_URL"
  python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
}

run_web() {
  echo "Starting web on http://0.0.0.0:3000"
  echo "Frontend API base: $NEXT_PUBLIC_API_BASE_URL"
  npm --workspace apps/web run dev -- --hostname 0.0.0.0 --port 3000
}

case "${1:-all}" in
  api)
    run_api
    ;;
  web)
    run_web
    ;;
  all)
    run_api > "$ROOT_DIR/logs/nas-internal-api.log" 2>&1 &
    API_PID=$!
    trap 'kill "$API_PID" 2>/dev/null || true' EXIT
    echo "API log: $ROOT_DIR/logs/nas-internal-api.log"
    sleep 2
    run_web
    ;;
  *)
    echo "Usage: bash scripts/run-nas-internal-web.sh [all|api|web]" >&2
    exit 2
    ;;
esac
