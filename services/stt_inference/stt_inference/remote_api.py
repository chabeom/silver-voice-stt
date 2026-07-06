from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from stt_inference.config import InferenceSettings


REMOTE_BACKENDS = {"nas-api", "remote-api", "http-api"}


def is_remote_backend(model_backend: str) -> bool:
    return model_backend.strip().lower() in REMOTE_BACKENDS


def transcribe_with_remote_api(
    *,
    input_path: str,
    settings: InferenceSettings,
    display_name: str | None = None,
) -> dict[str, Any]:
    audio_path = Path(input_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found for remote STT: {audio_path}")

    data = {
        "chunk_seconds": str(settings.remote_chunk_seconds),
        "chunk_overlap_seconds": str(settings.remote_chunk_overlap_seconds),
        "min_chunk_rms": str(settings.remote_min_chunk_rms),
        "max_new_tokens": str(settings.remote_max_new_tokens),
    }
    filename = display_name or audio_path.name
    with audio_path.open("rb") as file:
        response = requests.post(
            settings.remote_api_url,
            files={"file": (filename, file, "audio/wav")},
            data=data,
            timeout=settings.remote_timeout_seconds,
        )

    if response.status_code >= 400:
        raise RuntimeError(
            "Remote STT API failed "
            f"({response.status_code}): {response.text[:1000]}"
        )

    result = response.json()
    if not isinstance(result, dict) or "segments" not in result:
        raise RuntimeError("Remote STT API returned an invalid response without segments.")
    return result
