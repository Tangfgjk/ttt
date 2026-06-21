from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str


class SystemCapabilitiesResponse(BaseModel):
    ml_runtime_available: bool
    missing_packages: list[str]
    message: str
