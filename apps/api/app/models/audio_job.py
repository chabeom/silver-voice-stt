from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AudioJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audio_jobs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    model_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_versions.id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_source: Mapped[str] = mapped_column(String(20), default="file")
    storage_bucket: Mapped[str] = mapped_column(String(120))
    storage_object_key: Mapped[str] = mapped_column(String(255), unique=True)
    processed_object_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upload_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="uploaded", index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    average_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    user = relationship("User", back_populates="jobs")
    model_version = relationship("ModelVersion", back_populates="jobs")
    transcript = relationship("Transcript", back_populates="job", uselist=False, cascade="all, delete-orphan")
    corrections = relationship("Correction", back_populates="job", cascade="all, delete-orphan")
