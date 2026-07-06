#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WEB_VENV_DIR="${WEB_VENV_DIR:-$HOME/nas_private/stt-venv}"

echo "Setting up Silver Voice web/API runtime on NAS"
echo "Project : $ROOT_DIR"
echo "Venv    : $WEB_VENV_DIR"

if [[ ! -d "$WEB_VENV_DIR" ]]; then
  python3 -m venv "$WEB_VENV_DIR"
fi

# shellcheck disable=SC1091
source "$WEB_VENV_DIR/bin/activate"

python3 -m pip install --upgrade pip
python3 -m pip install \
  fastapi==0.115.6 \
  "uvicorn[standard]==0.34.0" \
  sqlalchemy==2.0.36 \
  "psycopg[binary]==3.2.3" \
  pydantic-settings==2.6.1 \
  "python-jose[cryptography]==3.3.0" \
  "passlib[bcrypt]==1.7.4" \
  python-multipart==0.0.20 \
  celery==5.4.0 \
  redis==5.2.1 \
  boto3==1.35.89 \
  python-json-logger==2.0.7 \
  email-validator==2.2.0 \
  httpx==0.28.1 \
  requests==2.32.5

if command -v npm >/dev/null 2>&1; then
  npm install
else
  echo "npm was not found. Install Node.js 20+ or ask the NAS admin to enable it." >&2
  exit 1
fi

echo "NAS web/API setup complete."
