from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    id: str
    status: str
    original_filename: str
    upload_source: str
    created_at: datetime


class CreateJobRequest(BaseModel):
    audio_job_id: str
    model_version_id: str | None = None
    enable_noise_reduction: bool = False
    enable_speaker_diarization: bool = False
    expected_speakers: int | None = Field(default=None, ge=1, le=10)


class SegmentResponse(BaseModel):
    id: str
    segment_index: int
    start_sec: float
    end_sec: float
    text: str
    normalized_text: str
    confidence: float
    raw_confidence: float | None = None
    calibrated_confidence: float | None = None
    speaker_label: str | None = None
    speaker_display_name: str | None = None
    speaker_confidence: float | None = None
    is_low_confidence: bool
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    tokens_json: dict | list | None = None

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    id: str
    job_id: str
    language: str
    full_text: str
    normalized_text: str
    average_confidence: float
    average_raw_confidence: float | None = None
    average_calibrated_confidence: float | None = None
    calibration_applied: bool = False
    diarization_applied: bool = False
    speaker_count: int = 0
    low_confidence_ratio: float
    total_duration: float
    processing_ms: int
    segments: list[SegmentResponse]


class JobResponse(BaseModel):
    id: str
    user_id: str
    model_version_id: str | None = None
    original_filename: str
    mime_type: str
    file_size_bytes: int
    upload_source: str
    status: str
    progress: float
    average_confidence: float | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobDetailResponse(JobResponse):
    transcript: TranscriptResponse | None = None
    latest_correction: dict[str, Any] | None = None
    audio_url: str | None = None


class CorrectionRequest(BaseModel):
    corrected_text: str = Field(min_length=1)
    environment_metadata: dict[str, Any] | None = None


class CorrectionResponse(BaseModel):
    id: str
    original_text: str
    corrected_text: str
    average_confidence: float | None = None
    diff_json: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedJobsResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
