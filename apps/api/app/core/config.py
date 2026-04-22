from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", enable_decoding=False)

    project_name: str = "Silver Voice STT"
    environment: str = "development"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = "sqlite:///./silver_voice.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "audio-files"
    minio_secure: bool = False
    storage_backend: str = "minio"
    local_storage_path: str = "apps/api/storage"

    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    jwt_secret_key: str = "change-me-access"
    jwt_refresh_secret_key: str = "change-me-refresh"
    jwt_algorithm: str = "HS256"

    max_upload_mb: int = 100
    allowed_audio_types: List[str] = Field(
        default_factory=lambda: [
            "audio/wav",
            "audio/x-wav",
            "audio/mpeg",
            "audio/mp3",
            "audio/webm",
            "audio/mp4",
            "audio/x-m4a",
        ]
    )

    default_model_version: str = "whisper-ko-elderly-v0"
    low_confidence_threshold: float = 0.55
    stt_model_backend: str = "faster-whisper"
    stt_model_path: str = "models/whisper-ko-elderly-v0"
    stt_compute_type: str = "int8"
    stt_device: str = "cpu"
    stt_mock_mode: bool = True
    enable_noise_reduction: bool = False

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_audio_types", mode="before")
    @classmethod
    def parse_audio_types(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
