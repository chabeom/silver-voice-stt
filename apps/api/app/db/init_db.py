import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import ModelVersion, User

logger = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()

    with SessionLocal() as db:
        active_model = db.scalar(select(ModelVersion).where(ModelVersion.version_name == settings.default_model_version))
        if not active_model:
            db.add(
                ModelVersion(
                    version_name=settings.default_model_version,
                    model_family=settings.stt_model_backend,
                    locale="ko-KR",
                    source_path=settings.stt_model_path,
                    description="Default MVP model for elderly Korean STT.",
                    metrics_json={"wer": None, "cer": None},
                    is_active=True,
                )
            )

        admin_user = db.scalar(select(User).where(User.email == "admin@silvervoice.example.com"))
        if not admin_user:
            db.add(
                User(
                    email="admin@silvervoice.example.com",
                    full_name="System Admin",
                    password_hash=hash_password("Admin123!"),
                    role="admin",
                )
            )
        db.commit()
        logger.info("database_initialized")
