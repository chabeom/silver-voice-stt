#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "== Host =="
hostname
whoami
pwd

echo
echo "== NVIDIA devices =="
ls -l /dev/nvidia* 2>/dev/null || {
  echo "No /dev/nvidia* devices are visible in this container."
  exit 1
}

echo
echo "== nvidia-smi =="
nvidia-smi

echo
echo "== PyTorch CUDA =="
"$PYTHON_BIN" - <<'PY'
import torch

print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("device count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device name:", torch.cuda.get_device_name(0))
else:
    raise SystemExit("CUDA is still unavailable to PyTorch.")
PY
