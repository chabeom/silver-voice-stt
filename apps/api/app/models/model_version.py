from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_versions"

    version_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    model_family: Mapped[str] = mapped_column(String(50))
    locale: Mapped[str] = mapped_column(String(20), default="ko-KR")
    source_path: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    jobs = relationship("AudioJob", back_populates="model_version")
    corrections = relationship("Correction", back_populates="model_version")

