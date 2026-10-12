import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_fails_when_api_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("api_key", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_succeeds_with_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("api_key", raising=False)
    settings = Settings(API_KEY="test-api-key", _env_file=None)
    assert settings.API_KEY == "test-api-key"
    assert "postgresql" in settings.DATABASE_URL
