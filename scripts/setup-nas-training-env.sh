#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$REPO_ROOT"

echo "== Verifying CUDA PyTorch before installing non-torch dependencies =="
"$PYTHON_BIN" - <<'PY'
import torch

print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("device count:", torch.cuda.device_count())
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available. Fix nvidia-smi/PyTorch CUDA before setup.")
PY

echo
echo "== Installing training dependencies without replacing torch =="
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r services/training_pipeline/requirements-nas-gpu.txt

echo
echo "NAS training environment is ready."
