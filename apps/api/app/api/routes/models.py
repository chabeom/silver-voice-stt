from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import ModelVersion
from app.schemas.model_version import ModelVersionResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelVersionResponse])
def list_models(_: CurrentUser, db: DbSession) -> list[ModelVersion]:
    return list(db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all())

