import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_silver_voice.db"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = "apps/api/test-storage"
os.environ["STT_MOCK_MODE"] = "true"

from app.main import app


@pytest.fixture(autouse=True)
def _patch_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.jobs.enqueue_transcription_job",
        lambda job_id, enable_noise_reduction, enable_speaker_diarization=False, expected_speakers=None: "test-task-id",
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
