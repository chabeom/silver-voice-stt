import os
from dataclasses import dataclass


@dataclass(slots=True)
class InferenceSettings:
    model_backend: str = "faster-whisper"
    model_path: str = "small"
    download_root: str = "/workspace/models/cache"
    compute_type: str = "int8"
    device: str = "cpu"
    beam_size: int = 5
    best_of: int = 5
    low_confidence_threshold: float = 0.55
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
            mock_mode=os.getenv("STT_MOCK_MODE", "false").lower() == "true",
        )
