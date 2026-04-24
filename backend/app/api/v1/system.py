from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.system import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", app_name=settings.app_name, environment=settings.app_env)


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ready", app_name=settings.app_name, environment=settings.app_env)
