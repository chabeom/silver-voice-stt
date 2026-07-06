from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class InferenceSettings:
    model_backend: str = "faster-whisper"
    model_path: str = "small"
    download_root: str = "/workspace/models/cache"
    compute_type: str = "int8"
    device: str = "cpu"
    beam_size: int = 5
    best_of: int = 5
    low_confidence_threshold: float = 0.55
    confidence_calibration_path: str | None = None
    diarization_model: str = "pyannote/speaker-diarization-community-1"
    diarization_device: str = "cpu"
    diarization_hf_token: str | None = None
    mock_mode: bool = False
    remote_api_url: str = "http://127.0.0.1:9001/transcribe"
    remote_timeout_seconds: float = 900.0
    remote_chunk_seconds: float = 30.0
    remote_chunk_overlap_seconds: float = 0.0
    remote_min_chunk_rms: float = 0.0005
    remote_max_new_tokens: int = 256

    @classmethod
    def from_env(cls) -> "InferenceSettings":
        return cls(
            model_backend=os.getenv("STT_MODEL_BACKEND", "faster-whisper"),
            model_path=os.getenv("STT_MODEL_PATH", "small"),
            download_root=os.getenv("STT_DOWNLOAD_ROOT", "/workspace/models/cache"),
            compute_type=os.getenv("STT_COMPUTE_TYPE", "int8"),
            device=os.getenv("STT_DEVICE", "cpu"),
            beam_size=int(os.getenv("STT_BEAM_SIZE", "5")),
            best_of=int(os.getenv("STT_BEST_OF", "5")),
            low_confidence_threshold=float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.55")),
            confidence_calibration_path=os.getenv("STT_CONFIDENCE_CALIBRATION_PATH") or None,
            diarization_model=os.getenv(
                "STT_DIARIZATION_MODEL",
                "pyannote/speaker-diarization-community-1",
            ),
            diarization_device=os.getenv("STT_DIARIZATION_DEVICE", os.getenv("STT_DEVICE", "cpu")),
            diarization_hf_token=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or None,
            mock_mode=os.getenv("STT_MOCK_MODE", "false").lower() == "true",
            remote_api_url=os.getenv("STT_REMOTE_API_URL", "http://127.0.0.1:9001/transcribe"),
            remote_timeout_seconds=float(os.getenv("STT_REMOTE_TIMEOUT_SECONDS", "900")),
            remote_chunk_seconds=float(os.getenv("STT_REMOTE_CHUNK_SECONDS", "30")),
            remote_chunk_overlap_seconds=float(os.getenv("STT_REMOTE_CHUNK_OVERLAP_SECONDS", "0")),
            remote_min_chunk_rms=float(os.getenv("STT_REMOTE_MIN_CHUNK_RMS", "0.0005")),
            remote_max_new_tokens=int(os.getenv("STT_REMOTE_MAX_NEW_TOKENS", "256")),
        )
