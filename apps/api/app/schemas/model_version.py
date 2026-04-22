from datetime import datetime

from pydantic import BaseModel


class ModelVersionResponse(BaseModel):
    id: str
    version_name: str
    model_family: str
    locale: str
    source_path: str
    description: str
    metrics_json: dict | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

