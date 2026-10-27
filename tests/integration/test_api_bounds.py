from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import Price
from app.db.session import get_session
from app.main import app


@pytest.fixture
def bounds_client(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    settings = Settings(API_KEY="bounds-key", _env_file=None)

    def override_session() -> Generator[Session, None, None]:
        yield db_session

    monkeypatch.setitem(app.dependency_overrides, get_session, override_session)
    monkeypatch.setitem(app.dependency_overrides, get_settings, lambda: settings)
    with TestClient(
        app, headers={"X-API-Key": settings.API_KEY}, raise_server_exceptions=False
    ) as client:
        yield client


@pytest.fixture
def price(db_session: Session) -> Price:
    price = Price(
        provider="anthropic",
        model="bounds-model",
        input_per_mtok_usd=Decimal("1"),
        output_per_mtok_usd=Decimal("1"),
        effective_from=date(2000, 1, 1),
    )
    db_session.add(price)
    db_session.commit()
    return price


@pytest.mark.parametrize("field", ["input_tokens", "output_tokens"])
@pytest.mark.parametrize("tokens", [2147483647, 2147483648])
def test_event_token_integer_bounds(
    bounds_client: TestClient, price: Price, field: str, tokens: int
) -> None:
    payload = {
        "provider": price.provider,
        "model": price.model,
        "input_tokens": 1,
        "output_tokens": 1,
        "feature": "bounds",
    }
    payload[field] = tokens
    response = bounds_client.post("/v1/events", json=payload)
    if tokens == 2147483647:
        assert response.status_code == 201
        assert response.json()[field] == tokens
    else:
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"
        assert response.json()["details"][0]["field"] == field


def test_event_cost_overflow_returns_domain_error(
    bounds_client: TestClient, price: Price, db_session: Session
) -> None:
    price.input_per_mtok_usd = Decimal("99999999.999999")
    db_session.commit()
    response = bounds_client.post(
        "/v1/events",
        json={
            "provider": price.provider,
            "model": price.model,
            "input_tokens": 2147483647,
            "output_tokens": 0,
            "feature": "bounds",
        },
    )
    assert response.status_code == 422
    assert response.json() == {
        "code": "cost_out_of_range",
        "message": "Calculated cost must be between 0 and 999999.99999999 USD",
    }


@pytest.mark.parametrize("field", ["from", "to"])
@pytest.mark.parametrize(
    "value,expected_status",
    [
        ("1999-12-31", 422),
        ("2000-01-01", 200),
        ("2100-12-31", 200),
        ("2101-01-01", 422),
        ("9999-12-31", 422),
    ],
)
def test_report_date_bounds(
    bounds_client: TestClient, field: str, value: str, expected_status: int
) -> None:
    response = bounds_client.get(
        "/v1/costs", params={"group_by": "feature", field: value}
    )
    assert response.status_code == expected_status
    if expected_status == 422:
        assert response.json()["code"] == "validation_error"
        assert response.json()["details"][0]["field"] == field
    else:
        assert response.json() == []
