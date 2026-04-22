from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, health, jobs, models, uploads
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.services.storage import StorageService

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    StorageService().ensure_bucket()
    yield


app = FastAPI(title=settings.project_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

