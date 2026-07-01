#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" - <<'PY'
import shutil

print("uroman command:", shutil.which("uroman") or "not found (fallback Hangul romanizer will be used)")

try:
    import torch
    print("torch:", torch.__version__)
    print("cuda available:", torch.cuda.is_available())
except Exception as exc:
    raise SystemExit(f"torch import failed: {exc}") from exc

try:
    import torchaudio
    print("torchaudio:", torchaudio.__version__)
except Exception as exc:
    raise SystemExit(
        "torchaudio import failed. Try: python3 -m pip install --no-deps torchaudio"
    ) from exc

try:
    import soundfile
    print("soundfile:", soundfile.__version__)
except Exception as exc:
    raise SystemExit("soundfile import failed. Install training requirements first.") from exc

try:
    bundle = torchaudio.pipelines.MMS_FA
    labels = bundle.get_labels()
    print("MMS_FA sample rate:", bundle.sample_rate)
    print("MMS_FA label count:", len(labels))
    print("MMS_FA first labels:", labels[:20])
except Exception as exc:
    raise SystemExit(f"MMS_FA check failed: {exc}") from exc

print("forced alignment environment looks usable.")
PY
