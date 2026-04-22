import json
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import CurrentUser, DbSession, StorageDep
from app.models import AudioJob
from app.schemas.job import UploadResponse
from app.services.audit import record_audit_log
from app.services.audio_validation import validate_audio_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/audio", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    db: DbSession,
    storage: StorageDep,
    user: CurrentUser,
    file: UploadFile = File(...),
    upload_source: str = Form(default="file"),
    metadata_json: str | None = Form(default=None),
) -> AudioJob:
    raw_bytes = await file.read()
    validate_audio_upload(file, len(raw_bytes))
    object_key = f"{user.id}/{uuid4()}-{file.filename}"
    storage.upload_bytes(object_key=object_key, data=raw_bytes, content_type=file.content_type or "application/octet-stream")

    job = AudioJob(
        user_id=user.id,
        original_filename=file.filename or "audio.bin",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(raw_bytes),
        upload_source=upload_source,
        storage_bucket=storage.settings.minio_bucket,
        storage_object_key=object_key,
        upload_metadata_json=json.loads(metadata_json) if metadata_json else {},
        status="uploaded",
        progress=0.0,
    )
    db.add(job)
    db.flush()
    record_audit_log(db, actor_user_id=user.id, target_type="audio_job", target_id=job.id, action="upload", metadata={"filename": job.original_filename})
    db.commit()
    db.refresh(job)
    return job
