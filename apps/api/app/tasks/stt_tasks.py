import logging
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from celery import Task

from app.db.session import SessionLocal
from app.models import AudioJob
from app.services.audit import record_audit_log
from app.services.job_service import save_transcription_result
from app.services.storage import StorageService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class JobTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2, "countdown": 10}
    retry_backoff = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # type: ignore[override]
        job_id = kwargs.get("job_id") or (args[0] if args else None)
        if not job_id:
            return
        with SessionLocal() as db:
            job = db.get(AudioJob, job_id)
            if not job:
                return
            job.status = "failed"
            job.progress = 1.0
            job.error_message = str(exc)
            job.retry_count += 1
            job.completed_at = datetime.now(timezone.utc)
            record_audit_log(
                db,
                actor_user_id=job.user_id,
                target_type="audio_job",
                target_id=job.id,
                action="job_failed",
                metadata={"error": str(exc), "task_id": task_id},
            )
            db.commit()
            logger.exception("stt_job_failed", extra={"job_id": job_id, "task_id": task_id})


@celery_app.task(bind=True, base=JobTask)
def process_audio_job(
    self,
    job_id: str,
    enable_noise_reduction: bool = False,
    enable_speaker_diarization: bool = False,
    expected_speakers: int | None = None,
) -> dict:
    from stt_inference.config import InferenceSettings
    from stt_inference.pipeline import run_stt_pipeline

    storage = StorageService()
    started = time.perf_counter()
    processed_key = None

    with SessionLocal() as db:
        job = db.get(AudioJob, job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        job.status = "preprocessing"
        job.progress = 0.2
        job.processing_started_at = datetime.now(timezone.utc)
        db.commit()

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = str(Path(tmp_dir) / "input_audio")
        downloaded_path = storage.download_file(object_key=job.storage_object_key, target_path=input_path)

        with SessionLocal() as db:
            job = db.get(AudioJob, job_id)
            job.status = "running"
            job.progress = 0.55
            db.commit()

        result = run_stt_pipeline(
            input_path=downloaded_path,
            settings=InferenceSettings.from_env(),
            enable_noise_reduction=enable_noise_reduction,
            enable_speaker_diarization=enable_speaker_diarization,
            expected_speakers=expected_speakers,
            job_id=job_id,
            display_name=job.original_filename,
        )

        if result.processed_audio_path:
            processed_key = f"processed/{job_id}.wav"
            storage.upload_bytes(
                object_key=processed_key,
                data=Path(result.processed_audio_path).read_bytes(),
                content_type="audio/wav",
            )

    with SessionLocal() as db:
        job = db.get(AudioJob, job_id)
        job.status = "postprocessing"
        job.progress = 0.85
        db.commit()

        transcript = save_transcription_result(
            db,
            job=job,
            result=result.model_dump(),
            processing_ms=int((time.perf_counter() - started) * 1000),
            processed_object_key=processed_key,
        )
        return {"job_id": job_id, "transcript_id": transcript.id}
