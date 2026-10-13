from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Event
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


def test_get_costs_grouped_by_feature(
    client: TestClient,
    db_session: Session,
    api_key: str,
) -> None:
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=Decimal("0.01050000"),
            feature="chat",
            customer="cust-1",
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=Decimal("0.02100000"),
            feature="chat",
            customer="cust-2",
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=500,
            output_tokens=200,
            cost_usd=Decimal("0.00500000"),
            feature="summarize",
            customer="cust-1",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    response = client.get(
        "/v1/costs?group_by=feature",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Descending order: chat ($0.0315) then summarize ($0.005)
    first, second = data[0], data[1]
    assert first["key"] == "chat"
    assert first["total_cost_usd"] == "0.03150000"
    assert isinstance(first["total_cost_usd"], str)
    assert not isinstance(first["total_cost_usd"], float)
    assert first["total_input_tokens"] == 3000
    assert first["total_output_tokens"] == 1500
    assert first["calls"] == 2

    assert second["key"] == "summarize"
    assert second["total_cost_usd"] == "0.00500000"
    assert isinstance(second["total_cost_usd"], str)
    assert not isinstance(second["total_cost_usd"], float)
    assert second["total_input_tokens"] == 500
    assert second["total_output_tokens"] == 200
    assert second["calls"] == 1


def test_get_costs_grouped_by_customer_with_unassigned(
    client: TestClient,
    db_session: Session,
    api_key: str,
) -> None:
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.00200000"),
            feature="chat",
            customer=None,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=200,
            output_tokens=100,
            cost_usd=Decimal("0.00400000"),
            feature="analysis",
            customer=None,
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=50,
            output_tokens=25,
            cost_usd=Decimal("0.00100000"),
            feature="chat",
            customer="acme-corp",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    response = client.get(
        "/v1/costs?group_by=customer",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # unassigned ($0.006) then acme-corp ($0.001)
    assert data[0]["key"] == "unassigned"
    assert data[0]["total_cost_usd"] == "0.00600000"
    assert data[0]["calls"] == 2
    assert data[1]["key"] == "acme-corp"
    assert data[1]["total_cost_usd"] == "0.00100000"
    assert data[1]["calls"] == 1


def test_get_costs_grouped_by_model(
    client: TestClient,
    db_session: Session,
    api_key: str,
) -> None:
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.00200000"),
            feature="chat",
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=300,
            output_tokens=150,
            cost_usd=Decimal("0.00900000"),
            feature="chat",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    response = client.get(
        "/v1/costs?group_by=model",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["key"] == "gpt-4o"
    assert data[0]["total_cost_usd"] == "0.00900000"
    assert data[1]["key"] == "claude-3-5-sonnet"
    assert data[1]["total_cost_usd"] == "0.00200000"


def test_get_costs_date_filters_including_last_day(
    client: TestClient,
    db_session: Session,
    api_key: str,
) -> None:
    dt_before = datetime(2024, 5, 9, 23, 59, 59, tzinfo=UTC)
    dt_start = datetime(2024, 5, 10, 0, 0, 0, tzinfo=UTC)
    dt_mid = datetime(2024, 5, 11, 12, 0, 0, tzinfo=UTC)
    dt_end_day = datetime(2024, 5, 12, 23, 59, 59, 999000, tzinfo=UTC)
    dt_after = datetime(2024, 5, 13, 0, 0, 0, tzinfo=UTC)

    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=10,
            output_tokens=10,
            cost_usd=Decimal("0.00010000"),
            feature="feat-before",
            created_at=dt_before,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=20,
            output_tokens=20,
            cost_usd=Decimal("0.00020000"),
            feature="feat-range",
            created_at=dt_start,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=30,
            output_tokens=30,
            cost_usd=Decimal("0.00030000"),
            feature="feat-range",
            created_at=dt_mid,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=40,
            output_tokens=40,
            cost_usd=Decimal("0.00040000"),
            feature="feat-range",
            created_at=dt_end_day,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=50,
            output_tokens=50,
            cost_usd=Decimal("0.00050000"),
            feature="feat-after",
            created_at=dt_after,
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    response = client.get(
        "/v1/costs?group_by=feature&from=2024-05-10&to=2024-05-12",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["key"] == "feat-range"
    assert data[0]["calls"] == 3
    assert data[0]["total_cost_usd"] == "0.00090000"
    assert data[0]["total_input_tokens"] == 90
    assert data[0]["total_output_tokens"] == 90


def test_get_costs_ordered_by_cost_descending(
    client: TestClient,
    db_session: Session,
    api_key: str,
) -> None:
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.01000000"),
            feature="cheap",
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=Decimal("0.90000000"),
            feature="expensive",
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=500,
            output_tokens=250,
            cost_usd=Decimal("0.25000000"),
            feature="moderate",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    response = client.get(
        "/v1/costs?group_by=feature",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    data = response.json()
    costs = [Decimal(row["total_cost_usd"]) for row in data]
    assert costs == sorted(costs, reverse=True)
    assert [row["key"] for row in data] == ["expensive", "moderate", "cheap"]


def test_get_costs_sum_matches_global_total(
    client: TestClient,
    db_session: Session,
    api_key: str,
) -> None:
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=150,
            output_tokens=50,
            cost_usd=Decimal("0.00250000"),
            feature="chat",
            customer="c-1",
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=250,
            output_tokens=100,
            cost_usd=Decimal("0.00450000"),
            feature="chat",
            customer=None,
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=350,
            output_tokens=150,
            cost_usd=Decimal("0.00800000"),
            feature="summary",
            customer="c-2",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    expected_total_cost = sum((e.cost_usd for e in events), Decimal("0"))
    expected_input_tokens = sum(e.input_tokens for e in events)
    expected_output_tokens = sum(e.output_tokens for e in events)
    expected_calls = len(events)

    for dim in ("feature", "customer", "model"):
        response = client.get(
            f"/v1/costs?group_by={dim}",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        data = response.json()

        sum_cost = sum((Decimal(r["total_cost_usd"]) for r in data), Decimal("0"))
        sum_inputs = sum(r["total_input_tokens"] for r in data)
        sum_outputs = sum(r["total_output_tokens"] for r in data)
        sum_calls = sum(r["calls"] for r in data)

        assert sum_cost == expected_total_cost
        assert sum_inputs == expected_input_tokens
        assert sum_outputs == expected_output_tokens
        assert sum_calls == expected_calls


def test_get_costs_401_missing_api_key(client: TestClient) -> None:
    response = client.get("/v1/costs?group_by=feature")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "unauthorized"
    assert data["message"] == "Invalid or missing API key"
    assert "detail" not in data


def test_get_costs_401_invalid_api_key(client: TestClient) -> None:
    response = client.get(
        "/v1/costs?group_by=feature",
        headers={"X-API-Key": "wrong-api-key"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "unauthorized"
    assert data["message"] == "Invalid or missing API key"
    assert "detail" not in data


def test_get_costs_200_empty_list_when_no_data(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.get(
        "/v1/costs?group_by=feature",
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_get_costs_422_invalid_group_by(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.get(
        "/v1/costs?group_by=unsupported_dimension",
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert data["message"] == "Request validation failed"
    assert "detail" not in data
    assert isinstance(data["details"], list)
    assert any(
        item.get("field") == "group_by" and "message" in item
        for item in data["details"]
    )


def test_get_costs_422_missing_group_by(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.get(
        "/v1/costs",
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert data["message"] == "Request validation failed"
    assert "detail" not in data
    assert isinstance(data["details"], list)
    assert any(
        item.get("field") == "group_by" and "message" in item
        for item in data["details"]
    )


def test_get_costs_422_from_after_to(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.get(
        "/v1/costs?group_by=feature&from=2024-05-20&to=2024-05-10",
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert data["message"] == "Request validation failed"
    assert "detail" not in data
    assert isinstance(data["details"], list)
    assert any(
        item.get("field") == "from" and "message" in item for item in data["details"]
    )


def test_get_costs_422_malformed_from_date(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.get(
        "/v1/costs?group_by=feature&from=not-a-valid-date",
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert data["message"] == "Request validation failed"
    assert "detail" not in data
    assert isinstance(data["details"], list)
    assert any(
        item.get("field") == "from" and "message" in item for item in data["details"]
    )


def test_get_costs_422_malformed_to_date(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.get(
        "/v1/costs?group_by=feature&to=2024-13-45",
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert data["message"] == "Request validation failed"
    assert "detail" not in data
    assert isinstance(data["details"], list)
    assert any(
        item.get("field") == "to" and "message" in item for item in data["details"]
    )
