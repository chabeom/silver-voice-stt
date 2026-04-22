import csv
import io

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession, StorageDep
from app.models import AudioJob, Correction, ModelVersion, Transcript
from app.schemas.admin import ModelComparisonRow, OverviewStatsResponse
from app.schemas.job import JobDetailResponse, JobResponse
from app.services.job_service import get_job_for_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/jobs", response_model=list[JobResponse])
def list_all_jobs(
    _: AdminUser,
    db: DbSession,
    status: str | None = Query(default=None),
    model_version_id: str | None = Query(default=None),
    min_confidence: float | None = Query(default=None),
    has_correction: bool | None = Query(default=None),
    failed_only: bool = Query(default=False),
) -> list[AudioJob]:
    query = select(AudioJob).order_by(AudioJob.created_at.desc())
    if status:
        query = query.where(AudioJob.status == status)
    if model_version_id:
        query = query.where(AudioJob.model_version_id == model_version_id)
    if min_confidence is not None:
        query = query.where(AudioJob.average_confidence <= min_confidence)
    if failed_only:
        query = query.where(AudioJob.status == "failed")
    if has_correction is True:
        query = query.join(Correction, Correction.job_id == AudioJob.id)
    return list(db.scalars(query).unique().all())


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_admin_job_detail(job_id: str, _: AdminUser, db: DbSession, storage: StorageDep) -> JobDetailResponse:
    job = get_job_for_user(db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    detail = JobResponse.model_validate(job).model_dump()
    transcript = None
    if job and job.transcript:
        transcript = {
            "id": job.transcript.id,
            "job_id": job.id,
            "language": job.transcript.language,
            "full_text": job.transcript.full_text,
            "normalized_text": job.transcript.normalized_text,
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
                    "text": segment.text,
                    "normalized_text": segment.normalized_text,
                    "confidence": segment.confidence,
                    "is_low_confidence": segment.is_low_confidence,
                    "avg_logprob": segment.avg_logprob,
                    "no_speech_prob": segment.no_speech_prob,
                    "tokens_json": segment.tokens_json,
                }
                for segment in sorted(job.transcript.segments, key=lambda item: item.segment_index)
            ],
        }
    latest_correction = None
    if job and job.corrections:
        correction = sorted(job.corrections, key=lambda item: item.created_at, reverse=True)[0]
        latest_correction = {
            "id": correction.id,
            "original_text": correction.original_text,
            "corrected_text": correction.corrected_text,
            "diff_json": correction.diff_json,
            "created_at": correction.created_at.isoformat(),
        }
    return JobDetailResponse(
        **detail,
        transcript=transcript,
        latest_correction=latest_correction,
        audio_url=storage.create_presigned_get_url(object_key=job.storage_object_key),
    )


@router.get("/stats/overview", response_model=OverviewStatsResponse)
def stats_overview(_: AdminUser, db: DbSession) -> OverviewStatsResponse:
    total_jobs = db.scalar(select(func.count()).select_from(AudioJob)) or 0
    completed_jobs = db.scalar(select(func.count()).select_from(AudioJob).where(AudioJob.status == "completed")) or 0
    failed_jobs = db.scalar(select(func.count()).select_from(AudioJob).where(AudioJob.status == "failed")) or 0
    correction_count = db.scalar(select(func.count()).select_from(Correction)) or 0
    corrected_job_count = db.scalar(select(func.count(func.distinct(Correction.job_id))).select_from(Correction)) or 0
    average_confidence = db.scalar(select(func.avg(Transcript.average_confidence)).select_from(Transcript)) or 0.0
    average_processing_ms = db.scalar(select(func.avg(Transcript.processing_ms)).select_from(Transcript)) or 0.0
    return OverviewStatsResponse(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        correction_count=correction_count,
        failure_rate=(failed_jobs / total_jobs) if total_jobs else 0.0,
        correction_rate=(corrected_job_count / completed_jobs) if completed_jobs else 0.0,
        average_confidence=float(average_confidence),
        average_processing_ms=float(average_processing_ms),
    )


@router.get("/stats/model-comparison", response_model=list[ModelComparisonRow])
def stats_model_comparison(_: AdminUser, db: DbSession) -> list[ModelComparisonRow]:
    query = (
        select(
            AudioJob.model_version_id,
            ModelVersion.version_name,
            func.count(AudioJob.id).label("completed_jobs"),
            func.avg(Transcript.average_confidence).label("average_confidence"),
            func.avg(Transcript.processing_ms).label("average_processing_ms"),
            (
                func.count(func.distinct(Correction.job_id)) / func.nullif(func.count(func.distinct(AudioJob.id)), 0)
            ).label("correction_rate"),
        )
        .select_from(AudioJob)
        .join(ModelVersion, ModelVersion.id == AudioJob.model_version_id, isouter=True)
        .join(Transcript, Transcript.job_id == AudioJob.id, isouter=True)
        .join(Correction, Correction.job_id == AudioJob.id, isouter=True)
        .where(AudioJob.status == "completed")
        .group_by(AudioJob.model_version_id, ModelVersion.version_name)
        .order_by(func.count(AudioJob.id).desc())
    )
    rows = db.execute(query).all()
    return [
        ModelComparisonRow(
            model_version_id=row.model_version_id,
            version_name=row.version_name or "unassigned",
            completed_jobs=int(row.completed_jobs or 0),
            average_confidence=float(row.average_confidence or 0.0),
            average_processing_ms=float(row.average_processing_ms or 0.0),
            correction_rate=float(row.correction_rate or 0.0),
        )
        for row in rows
    ]


@router.get("/export/corrections")
def export_corrections(_: AdminUser, db: DbSession) -> StreamingResponse:
    rows = db.execute(
        select(
            Correction.id,
            Correction.job_id,
            Correction.original_text,
            Correction.corrected_text,
            Correction.average_confidence,
            Correction.created_at,
        ).order_by(Correction.created_at.desc())
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["correction_id", "job_id", "original_text", "corrected_text", "average_confidence", "created_at"])
    for row in rows:
        writer.writerow(row)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=corrections-export.csv"},
    )
