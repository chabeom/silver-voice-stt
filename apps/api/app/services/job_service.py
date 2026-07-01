import difflib
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import AudioJob, Correction, ModelVersion, Transcript, TranscriptSegment
from app.services.audit import record_audit_log

logger = logging.getLogger(__name__)

ACTIVE_JOB_STATUSES = {"queued", "preprocessing", "running", "postprocessing"}


def get_transcript_confidence_metadata(transcript: Transcript) -> dict:
    raw_result = transcript.raw_result_json or {}
    return {
        "average_raw_confidence": raw_result.get("average_raw_confidence"),
        "average_calibrated_confidence": raw_result.get(
            "average_calibrated_confidence",
            transcript.average_confidence,
        ),
        "calibration_applied": bool(raw_result.get("calibration_applied", False)),
    }


def get_segment_confidence_metadata(transcript: Transcript, segment_index: int, confidence: float) -> dict:
    raw_result = transcript.raw_result_json or {}
    for segment in raw_result.get("segments", []):
        if int(segment.get("segment_index", -1)) != segment_index:
            continue
        return {
            "raw_confidence": segment.get("raw_confidence", segment.get("confidence")),
            "calibrated_confidence": segment.get("calibrated_confidence", confidence),
        }
    return {"raw_confidence": None, "calibrated_confidence": confidence}


def get_transcript_diarization_metadata(transcript: Transcript) -> dict:
    raw_result = transcript.raw_result_json or {}
    return {
        "diarization_applied": bool(raw_result.get("diarization_applied", False)),
        "speaker_count": int(raw_result.get("speaker_count", 0)),
    }


def get_segment_diarization_metadata(transcript: Transcript, segment_index: int) -> dict:
    raw_result = transcript.raw_result_json or {}
    for segment in raw_result.get("segments", []):
        if int(segment.get("segment_index", -1)) != segment_index:
            continue
        return {
            "speaker_label": segment.get("speaker_label"),
            "speaker_display_name": segment.get("speaker_display_name"),
            "speaker_confidence": segment.get("speaker_confidence"),
        }
    return {
        "speaker_label": None,
        "speaker_display_name": None,
        "speaker_confidence": None,
    }


def get_active_model_version(db: Session) -> ModelVersion | None:
    return db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1))


def build_diff(original_text: str, corrected_text: str) -> dict:
    diff = difflib.ndiff(original_text.split(), corrected_text.split())
    return {"changes": [line for line in diff if line.startswith(("- ", "+ "))]}


def enqueue_transcription_job(
    job_id: str,
    enable_noise_reduction: bool,
    enable_speaker_diarization: bool = False,
    expected_speakers: int | None = None,
) -> str:
    from app.tasks.stt_tasks import process_audio_job

    task = process_audio_job.delay(
        job_id=job_id,
        enable_noise_reduction=enable_noise_reduction,
        enable_speaker_diarization=enable_speaker_diarization,
        expected_speakers=expected_speakers,
    )
    return task.id


def list_user_jobs(
    db: Session,
    *,
    user_id: str,
    page: int,
    page_size: int,
    status_filter: str | None,
) -> tuple[list[AudioJob], int]:
    filters = [AudioJob.user_id == user_id]
    if status_filter:
        filters.append(AudioJob.status == status_filter)
    query = select(AudioJob).where(*filters).order_by(AudioJob.created_at.desc())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return items, total


def get_job_for_user(db: Session, *, job_id: str, user_id: str | None = None) -> AudioJob | None:
    filters = [AudioJob.id == job_id]
    if user_id:
        filters.append(AudioJob.user_id == user_id)
    return db.scalar(
        select(AudioJob)
        .where(*filters)
        .options(
            joinedload(AudioJob.transcript).joinedload(Transcript.segments),
            joinedload(AudioJob.corrections),
            joinedload(AudioJob.model_version),
        )
    )


def delete_job_record(db: Session, *, job: AudioJob, user_id: str) -> None:
    record_audit_log(
        db,
        actor_user_id=user_id,
        target_type="audio_job",
        target_id=job.id,
        action="job_deleted",
        metadata={"original_filename": job.original_filename, "status": job.status},
    )
    db.delete(job)
    db.commit()


def save_correction(
    db: Session,
    *,
    job: AudioJob,
    user_id: str,
    corrected_text: str,
    environment_metadata: dict | None,
) -> Correction:
    transcript = job.transcript
    if not transcript:
        raise ValueError("Transcript is not available")

    correction = Correction(
        job_id=job.id,
        transcript_id=transcript.id,
        user_id=user_id,
        model_version_id=job.model_version_id,
        original_text=transcript.normalized_text,
        corrected_text=corrected_text,
        average_confidence=transcript.average_confidence,
        diff_json=build_diff(transcript.normalized_text, corrected_text),
        environment_metadata_json=environment_metadata or {},
    )
    db.add(correction)
    db.flush()
    transcript.normalized_text = corrected_text
    transcript.updated_at = datetime.now(timezone.utc)

    record_audit_log(
        db,
        actor_user_id=user_id,
        target_type="correction",
        target_id=correction.id,
        action="correction_saved",
        metadata={"job_id": job.id},
    )
    db.commit()
    db.refresh(correction)
    logger.info("correction_saved", extra={"job_id": job.id, "user_id": user_id})
    return correction


def save_transcription_result(
    db: Session,
    *,
    job: AudioJob,
    result: dict,
    processing_ms: int,
    processed_object_key: str | None = None,
) -> Transcript:
    transcript = job.transcript or Transcript(job_id=job.id, full_text="", normalized_text="")
    transcript.language = result.get("language", "ko")
    transcript.full_text = result["full_text"]
    transcript.normalized_text = result["normalized_text"]
    transcript.average_confidence = result["average_confidence"]
    transcript.low_confidence_ratio = result["low_confidence_ratio"]
    transcript.total_duration = result["duration"]
    transcript.processing_ms = processing_ms
    transcript.raw_result_json = result
    db.add(transcript)
    db.flush()

    db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == transcript.id).delete()
    segments = []
    for item in result["segments"]:
        segments.append(
            TranscriptSegment(
                transcript_id=transcript.id,
                segment_index=item["segment_index"],
                start_sec=item["start_sec"],
                end_sec=item["end_sec"],
                text=item["text"],
                normalized_text=item["normalized_text"],
                confidence=item["confidence"],
                avg_logprob=item.get("avg_logprob"),
                no_speech_prob=item.get("no_speech_prob"),
                tokens_json=item.get("tokens_json"),
                is_low_confidence=item["is_low_confidence"],
            )
        )
    db.add_all(segments)

    job.status = "completed"
    job.progress = 1.0
    job.average_confidence = result["average_confidence"]
    job.completed_at = datetime.now(timezone.utc)
    if processed_object_key:
        job.processed_object_key = processed_object_key

    record_audit_log(
        db,
        actor_user_id=job.user_id,
        target_type="audio_job",
        target_id=job.id,
        action="job_completed",
        metadata={
            "average_confidence": result["average_confidence"],
            "processing_ms": processing_ms,
        },
    )
    db.commit()
    db.refresh(transcript)
    return transcript
