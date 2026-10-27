from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_report_service
from app.core.config import Settings, get_settings
from app.main import app
from app.services.reports import ReportService


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    settings = Settings(API_KEY="dev", _env_file=None)
    service = MagicMock(spec=ReportService)
    service.get_costs.return_value = []
    monkeypatch.setitem(app.dependency_overrides, get_settings, lambda: settings)
    monkeypatch.setitem(app.dependency_overrides, get_report_service, lambda: service)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize("api_key", [b"\xc3\xa9", b"\xe9"])
def test_non_ascii_api_key_returns_401(auth_client: TestClient, api_key: bytes) -> None:
    response = auth_client.get(
        "/v1/costs?group_by=feature", headers={b"X-API-Key": api_key}
    )
    assert response.status_code == 401
    assert response.json() == {
        "code": "unauthorized",
        "message": "Invalid or missing API key",
    }


def test_correct_short_api_key_still_works(auth_client: TestClient) -> None:
    response = auth_client.get(
        "/v1/costs?group_by=feature", headers={"X-API-Key": "dev"}
    )
    assert response.status_code == 200
    assert response.json() == []
