import logging
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_event_service
from app.core.config import Settings, get_settings
from app.main import app
from app.services.events import EventService


def test_unexpected_service_error_returns_safe_json_and_logs_exception(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    failure = RuntimeError("synthetic internal failure")
    service = MagicMock(spec=EventService)
    service.create_event.side_effect = failure
    settings = Settings(API_KEY="synthetic-private-header", _env_file=None)
    monkeypatch.setitem(app.dependency_overrides, get_settings, lambda: settings)
    monkeypatch.setitem(app.dependency_overrides, get_event_service, lambda: service)

    with (
        caplog.at_level(logging.ERROR, logger="app.api.errors"),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/v1/events",
            headers={"X-API-Key": settings.API_KEY},
            json={
                "provider": "anthropic",
                "model": "audit-model",
                "input_tokens": 1,
                "output_tokens": 1,
                "feature": "synthetic-private-body",
            },
        )

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "code": "internal_error",
        "message": "Internal server error",
    }
    assert str(failure) not in response.text
    assert any(
        record.exc_info is not None and record.exc_info[1] is failure
        for record in caplog.records
    )
    assert str(failure) in caplog.text
    assert settings.API_KEY not in caplog.text
    assert "synthetic-private-body" not in caplog.text
