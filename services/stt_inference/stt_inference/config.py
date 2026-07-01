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
        )
