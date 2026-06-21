import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.services import runtime_capabilities
from app.services.runtime_capabilities import ML_UNAVAILABLE_MESSAGE, detect_ml_runtime

client = TestClient(app)


def test_system_capabilities_reports_ml_runtime_state() -> None:
    response = client.get("/api/v1/system/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["ml_runtime_available"], bool)
    assert isinstance(payload["missing_packages"], list)
    assert isinstance(payload["message"], str)


def test_detect_ml_runtime_reports_missing_packages() -> None:
    installed = {"torch": object()}

    capability = detect_ml_runtime(installed.get)

    assert capability.available is False
    assert capability.missing_packages == ("transformers",)
    assert capability.message == ML_UNAVAILABLE_MESSAGE


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/active-learning/training-runs", {}),
        ("/api/v1/active-learning/prediction-runs", {}),
        ("/api/v1/active-learning/coreset-runs", {}),
    ],
)
def test_active_learning_creation_requires_ml_runtime(
    path: str,
    payload: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def override_get_db():
        yield None

    monkeypatch.setattr(runtime_capabilities, "find_spec", lambda _name: None)
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app, raise_server_exceptions=False)
    try:
        response = test_client.post(path, json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == ML_UNAVAILABLE_MESSAGE


def test_ml_dependencies_are_optional() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]

    core_dependencies = project["dependencies"]
    ml_dependencies = project["optional-dependencies"]["ml"]

    assert not any(item.startswith("torch") for item in core_dependencies)
    assert not any(item.startswith("transformers") for item in core_dependencies)
    assert any(item.startswith("torch") for item in ml_dependencies)
    assert any(item.startswith("transformers") for item in ml_dependencies)
