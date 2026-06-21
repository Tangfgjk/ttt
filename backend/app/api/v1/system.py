from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.system import HealthResponse, SystemCapabilitiesResponse
from app.services.runtime_capabilities import detect_ml_runtime

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", app_name=settings.app_name, environment=settings.app_env)


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ready", app_name=settings.app_name, environment=settings.app_env)


@router.get("/capabilities", response_model=SystemCapabilitiesResponse)
async def system_capabilities() -> SystemCapabilitiesResponse:
    capability = detect_ml_runtime()
    return SystemCapabilitiesResponse(
        ml_runtime_available=capability.available,
        missing_packages=list(capability.missing_packages),
        message=capability.message,
    )
