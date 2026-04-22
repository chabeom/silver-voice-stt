from typing import Any

from pydantic import BaseModel


class SegmentResult(BaseModel):
    segment_index: int
    start_sec: float
    end_sec: float
    text: str
    normalized_text: str
    confidence: float
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    tokens_json: list[dict[str, Any]] | None = None
    is_low_confidence: bool


class InferenceResult(BaseModel):
    language: str
    full_text: str
    normalized_text: str
    average_confidence: float
    low_confidence_ratio: float
    duration: float
    segments: list[SegmentResult]
    processed_audio_path: str | None = None

