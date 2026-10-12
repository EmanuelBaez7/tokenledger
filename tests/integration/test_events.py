import uuid
from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Event, Price
from app.db.session import get_session
from app.main import app

TEST_API_KEY = "test-secret-integration-key-xyz"


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Isolate API_KEY for tests without relying on .env."""
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    from app.core.config import get_settings

    get_settings.cache_clear()
    return TEST_API_KEY


@pytest.fixture
def client(
    db_session: Session,
    api_key: str,
) -> Generator[TestClient, None, None]:
    """Test client configured to use the test database session and test API key."""

    def override_get_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_create_event_happy_path_with_manual_cost_verification(
    client: TestClient,
    db_session: Session,
    api_key: str,
) -> None:
    # 1. Seed price in test DB: input 3.00, output 15.00
    price = Price(
        provider="anthropic",
        model="claude-3-haiku-20240307",
        input_per_mtok_usd=Decimal("3.00"),
        output_per_mtok_usd=Decimal("15.00"),
        effective_from=date(2024, 1, 1),
    )
    db_session.add(price)
    db_session.commit()

    # 2. Post event: 1000 input, 500 output -> manual cost:
    #    1000/1M*3.00 + 500/1M*15.00 = 0.003 + 0.0075 = 0.01050000
    payload = {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "input_tokens": 1000,
        "output_tokens": 500,
        "feature": "document_summary",
        "customer": "customer_abc",
        "latency_ms": 250,
        "status": "ok",
    }

    response = client.post(
        "/v1/events",
        json=payload,
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 201
    data = response.json()

    # Verify response structure and serialized string cost
    assert data["cost_usd"] == "0.01050000"
    assert isinstance(data["cost_usd"], str)
    assert not isinstance(data["cost_usd"], float)
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-3-haiku-20240307"
    assert data["input_tokens"] == 1000
    assert data["output_tokens"] == 500
    assert data["feature"] == "document_summary"
    assert data["customer"] == "customer_abc"
    assert data["latency_ms"] == 250
    assert data["status"] == "ok"
    assert "id" in data
    assert "created_at" in data

    # Verify persisted record in PostgreSQL test DB
    event_uuid = uuid.UUID(data["id"])
    persisted = db_session.get(Event, event_uuid)
    assert persisted is not None
    assert persisted.cost_usd == Decimal("0.01050000")
    assert persisted.feature == "document_summary"
    assert persisted.customer == "customer_abc"


def test_create_event_401_missing_key(client: TestClient) -> None:
    payload = {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "input_tokens": 100,
        "output_tokens": 50,
        "feature": "chat",
    }
    response = client.post("/v1/events", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data.get("code") == "unauthorized"


def test_create_event_401_invalid_key(client: TestClient) -> None:
    payload = {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "input_tokens": 100,
        "output_tokens": 50,
        "feature": "chat",
    }
    response = client.post(
        "/v1/events",
        json=payload,
        headers={"X-API-Key": "invalid-wrong-key"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data.get("code") == "unauthorized"


def test_create_event_422_unknown_model_price(
    client: TestClient,
    api_key: str,
) -> None:
    payload = {
        "provider": "openai",
        "model": "non-existent-gpt-model",
        "input_tokens": 100,
        "output_tokens": 50,
        "feature": "chat",
    }
    response = client.post(
        "/v1/events",
        json=payload,
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("code") == "unknown_model_price"
    assert data.get("model") == "non-existent-gpt-model"
    assert "non-existent-gpt-model" in data.get("message", "")


def test_create_event_422_negative_tokens(
    client: TestClient,
    api_key: str,
) -> None:
    payload = {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "input_tokens": -10,
        "output_tokens": 50,
        "feature": "chat",
    }
    response = client.post(
        "/v1/events",
        json=payload,
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422


def test_create_event_422_extra_field_cost_usd(
    client: TestClient,
    api_key: str,
) -> None:
    payload = {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "input_tokens": 100,
        "output_tokens": 50,
        "feature": "chat",
        "cost_usd": "0.01050000",
    }
    response = client.post(
        "/v1/events",
        json=payload,
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422


def test_create_event_422_extra_field_id_and_created_at(
    client: TestClient,
    api_key: str,
) -> None:
    payload = {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "input_tokens": 100,
        "output_tokens": 50,
        "feature": "chat",
        "id": str(uuid.uuid4()),
        "created_at": "2026-01-01T00:00:00Z",
    }
    response = client.post(
        "/v1/events",
        json=payload,
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422


def test_health_remains_public_without_auth(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_http_exception_string_detail_format(client: TestClient) -> None:
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert data.get("code") == "error"
    assert "detail" in data
    assert "message" in data
