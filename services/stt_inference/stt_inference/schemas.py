from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SegmentResult(BaseModel):
    segment_index: int
    start_sec: float
    end_sec: float
    text: str
    normalized_text: str
    confidence: float
    raw_confidence: float
    calibrated_confidence: float
    speaker_label: str | None = None
    speaker_display_name: str | None = None
    speaker_confidence: float | None = None
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    tokens_json: list[dict[str, Any]] | None = None
    is_low_confidence: bool


class InferenceResult(BaseModel):
    language: str
    full_text: str
    normalized_text: str
    average_confidence: float
    average_raw_confidence: float
    average_calibrated_confidence: float
    calibration_applied: bool
    diarization_applied: bool
    speaker_count: int
    speaker_turns: list[dict[str, Any]] | None = None
    low_confidence_ratio: float
    duration: float
    segments: list[SegmentResult]
    processed_audio_path: str | None = None
