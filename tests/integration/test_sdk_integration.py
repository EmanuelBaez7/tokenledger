"""Integration tests for TokenLedger SDK tracking events into the test server."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.seed import seed_prices
from app.main import app
from sdk.tokenledger import TokenLedger

TEST_API_KEY = "test-secret-integration-key-xyz"


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Isolate API_KEY for tests without relying on .env."""
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    from app.core.config import get_settings

    get_settings.cache_clear()
    return TEST_API_KEY


def test_sdk_track_event_persists_and_appears_in_costs(
    db_session: Session,
    api_key: str,
) -> None:
    """The SDK sends an event in background, flush waits, and /v1/costs reflects it."""
    # 1. Seed prices so POST /v1/events finds a valid rate
    seed_prices(db_session)

    # 2. Use TestClient(app) as injected http_client
    test_client = TestClient(app)

    sdk = TokenLedger(
        base_url="http://testserver",
        api_key=api_key,
        timeout=5.0,
        http_client=test_client,
    )

    # 3. Fake Anthropic LLM call
    fake_response = SimpleNamespace(
        model="claude-3-haiku-20240307",
        usage=SimpleNamespace(input_tokens=10_000, output_tokens=2_000),
    )

    resp = sdk.track(
        lambda: fake_response,
        provider="anthropic",
        feature="sdk_feature_test",
        customer="sdk_cust_test",
    )
    assert resp is fake_response

    # 4. Wait for background worker to deliver the event
    sdk.flush(timeout=5.0)
    sdk.close()

    # 5. Query /v1/costs and verify the event is aggregated
    response = test_client.get(
        "/v1/costs",
        params={"group_by": "feature"},
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    items = response.json()

    # Find our feature
    item = next(
        (it for it in items if it["key"] == "sdk_feature_test"),
        None,
    )
    assert item is not None, f"Feature 'sdk_feature_test' not found in {items}"
    assert item["calls"] == 1
    assert item["total_input_tokens"] == 10_000
    assert item["total_output_tokens"] == 2_000
    # claude-3-haiku-20240307 price: in 0.25/Mtok, out 1.25/Mtok
    # cost = 10000/1M * 0.25 + 2000/1M * 1.25 = 0.0025 + 0.0025 = 0.00500000
    assert item["total_cost_usd"] == "0.00500000"
