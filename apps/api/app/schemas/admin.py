from pydantic import BaseModel


class OverviewStatsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    correction_count: int
    failure_rate: float
    correction_rate: float
    average_confidence: float
    average_processing_ms: float


class ModelComparisonRow(BaseModel):
    model_version_id: str | None
    version_name: str
    completed_jobs: int
    average_confidence: float
    average_processing_ms: float
    correction_rate: float

