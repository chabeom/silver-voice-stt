import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.security import decode_token
from app.core.config import get_settings
from app.api.deps import CurrentUser, DbSession, StorageDep
from app.db.session import SessionLocal
from app.models import AudioJob
from app.schemas.job import (
    CorrectionRequest,
    CorrectionResponse,
    CreateJobRequest,
    JobDetailResponse,
    JobResponse,
    PaginatedJobsResponse,
)
from app.services.audit import record_audit_log
from app.services.job_service import (
    ACTIVE_JOB_STATUSES,
    delete_job_record,
    enqueue_transcription_job,
    get_active_model_version,
    get_job_for_user,
    list_user_jobs,
    save_correction,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _build_mock_display_text(original_filename: str) -> str:
    base_name = Path(original_filename).stem.replace("_", " ").strip()
    if not base_name:
        base_name = "업로드한 음성"
    return (
        f"{base_name}에 대한 데모 결과입니다. "
        "실제 Whisper 모델을 연결하면 이 영역에 음성 인식 결과가 표시됩니다."
    )


def _looks_like_legacy_mock_text(text: str, job_id: str) -> bool:
    lowered = text.lower()
    return job_id in text or " vad " in lowered or lowered.startswith(f"{job_id.lower()} ")


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: CreateJobRequest, db: DbSession, user: CurrentUser) -> AudioJob:
    job = db.scalar(select(AudioJob).where(AudioJob.id == payload.audio_job_id, AudioJob.user_id == user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio upload not found")
    now = datetime.now(timezone.utc)
    is_stale_queued_job = (
        job.status == "queued"
        and job.progress <= 0.05
        and job.processing_started_at is not None
        and (now - job.processing_started_at) >= timedelta(seconds=15)
    )
    if job.status not in {"uploaded", "failed"} and not is_stale_queued_job:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job already queued or completed")

    if payload.model_version_id:
        model_id = payload.model_version_id
    else:
        active_model = get_active_model_version(db)
        model_id = active_model.id if active_model else None

    job.model_version_id = model_id
    job.status = "queued"
    job.progress = 0.05
    job.processing_started_at = now
    job.error_message = None
    job.task_id = enqueue_transcription_job(job.id, payload.enable_noise_reduction)
    record_audit_log(
        db,
        actor_user_id=user.id,
        target_type="audio_job",
        target_id=job.id,
        action="job_started",
        metadata={"task_id": job.task_id, "enable_noise_reduction": payload.enable_noise_reduction},
    )
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=PaginatedJobsResponse)
def list_jobs(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> PaginatedJobsResponse:
    items, total = list_user_jobs(db, user_id=user.id, page=page, page_size=page_size, status_filter=status_filter)
    return PaginatedJobsResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: DbSession, user: CurrentUser) -> AudioJob:
    job = get_job_for_user(db, job_id=job_id, user_id=user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, db: DbSession, storage: StorageDep, user: CurrentUser) -> None:
    job = get_job_for_user(db, job_id=job_id, user_id=user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status in ACTIVE_JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active jobs cannot be deleted")

    object_keys = [job.storage_object_key, job.processed_object_key]
    delete_job_record(db, job=job, user_id=user.id)
    for object_key in object_keys:
        storage.delete_file(object_key=object_key)


@router.get("/{job_id}/result", response_model=JobDetailResponse)
def get_job_result(job_id: str, db: DbSession, storage: StorageDep, user: CurrentUser) -> JobDetailResponse:
    job = get_job_for_user(db, job_id=job_id, user_id=user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    settings = get_settings()

    latest_correction = None
    if job.corrections:
        correction = sorted(job.corrections, key=lambda item: item.created_at, reverse=True)[0]
        latest_correction = {
            "id": correction.id,
            "corrected_text": correction.corrected_text,
            "created_at": correction.created_at.isoformat(),
        }

    transcript = None
    if job.transcript:
        mock_display_text = None
        if (
            settings.stt_mock_mode
            and _looks_like_legacy_mock_text(job.transcript.full_text, job.id)
        ):
            mock_display_text = _build_mock_display_text(job.original_filename)

        transcript = {
            "id": job.transcript.id,
            "job_id": job.id,
            "language": job.transcript.language,
            "full_text": mock_display_text or job.transcript.full_text,
            "normalized_text": mock_display_text or job.transcript.normalized_text,
            "average_confidence": job.transcript.average_confidence,
            "low_confidence_ratio": job.transcript.low_confidence_ratio,
            "total_duration": job.transcript.total_duration,
            "processing_ms": job.transcript.processing_ms,
            "segments": [
                {
                    "id": segment.id,
                    "segment_index": segment.segment_index,
                    "start_sec": segment.start_sec,
                    "end_sec": segment.end_sec,
                    "text": mock_display_text or segment.text,
                    "normalized_text": mock_display_text or segment.normalized_text,
                    "confidence": segment.confidence,
                    "is_low_confidence": segment.is_low_confidence,
                    "avg_logprob": segment.avg_logprob,
                    "no_speech_prob": segment.no_speech_prob,
                    "tokens_json": segment.tokens_json,
                }
                for segment in sorted(job.transcript.segments, key=lambda item: item.segment_index)
            ],
        }

    return JobDetailResponse(
        **JobResponse.model_validate(job).model_dump(),
        transcript=transcript,
        latest_correction=latest_correction,
        audio_url=storage.create_presigned_get_url(object_key=job.storage_object_key),
    )


@router.put("/{job_id}/result", response_model=CorrectionResponse)
def update_result(job_id: str, payload: CorrectionRequest, db: DbSession, user: CurrentUser) -> CorrectionResponse:
    job = get_job_for_user(db, job_id=job_id, user_id=user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not job.transcript:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transcript not ready")

    correction = save_correction(
        db,
        job=job,
        user_id=user.id,
        corrected_text=payload.corrected_text,
        environment_metadata=payload.environment_metadata,
    )
    return CorrectionResponse.model_validate(correction)


@router.get("/{job_id}/events")
async def stream_job_events(job_id: str, access_token: str = Query(...)) -> StreamingResponse:
    try:
        payload = decode_token(access_token, token_type="access")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload["sub"]

    async def event_generator():
        while True:
            with SessionLocal() as db:
                job = get_job_for_user(db, job_id=job_id, user_id=user_id)
                if not job:
                    payload = {"job_id": job_id, "status": "missing", "progress": 0.0, "error_message": "Job not found"}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break

                payload = {
                    "job_id": job.id,
                    "status": job.status,
                    "progress": job.progress,
                    "average_confidence": job.average_confidence,
                    "error_message": job.error_message,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if job.status in {"completed", "failed"}:
                    break
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
