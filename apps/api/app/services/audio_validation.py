from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


def validate_audio_upload(file: UploadFile, file_size_bytes: int) -> None:
    settings = get_settings()
    allowed_types = set(settings.allowed_audio_type_list)
    allowed_suffixes = {".wav", ".mp3", ".m4a", ".webm", ".mp4"}
    suffix = Path(file.filename or "").suffix.lower()

    if file.content_type not in allowed_types or suffix not in allowed_suffixes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported audio format")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File exceeds size limit")
