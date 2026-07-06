from sqlalchemy import Float, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Correction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "corrections"

    job_id: Mapped[str] = mapped_column(ForeignKey("audio_jobs.id"), index=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    model_version_id: Mapped[str | None] = mapped_column(ForeignKey("model_versions.id"), nullable=True)
    original_text: Mapped[str] = mapped_column(Text)
    corrected_text: Mapped[str] = mapped_column(Text)
    average_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    diff_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    environment_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="corrections")
    job = relationship("AudioJob", back_populates="corrections")
    transcript = relationship("Transcript", back_populates="corrections")
    model_version = relationship("ModelVersion", back_populates="corrections")

