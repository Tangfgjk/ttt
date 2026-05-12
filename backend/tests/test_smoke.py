from app.core.config import get_settings


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.app_name
