from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Transcript(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transcripts"

    job_id: Mapped[str] = mapped_column(ForeignKey("audio_jobs.id"), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(20), default="ko")
    full_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    average_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    low_confidence_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    total_duration: Mapped[float] = mapped_column(Float, default=0.0)
    processing_ms: Mapped[int] = mapped_column(Integer, default=0)
    raw_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    job = relationship("AudioJob", back_populates="transcript")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan")
    corrections = relationship("Correction", back_populates="transcript")


class TranscriptSegment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transcript_segments"

    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id"), index=True)
    segment_index: Mapped[int] = mapped_column(Integer)
    start_sec: Mapped[float] = mapped_column(Float)
    end_sec: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    avg_logprob: Mapped[float | None] = mapped_column(Float, nullable=True)
    no_speech_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    is_low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)

    transcript = relationship("Transcript", back_populates="segments")
