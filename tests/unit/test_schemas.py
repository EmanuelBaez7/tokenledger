import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.schemas import EventCreate, EventResponse


def test_event_create_valid_minimal() -> None:
    data = {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "input_tokens": 100,
        "output_tokens": 50,
        "feature": "summarization",
    }
    event = EventCreate(**data)
    assert event.provider == "anthropic"
    assert event.model == "claude-3-haiku-20240307"
    assert event.input_tokens == 100
    assert event.output_tokens == 50
    assert event.feature == "summarization"
    assert event.customer is None
    assert event.latency_ms is None
    assert event.status == "ok"


def test_event_create_valid_full() -> None:
    data = {
        "provider": "openai",
        "model": "gpt-4o",
        "input_tokens": 0,
        "output_tokens": 0,
        "feature": "chat",
        "customer": "cust_12345",
        "latency_ms": 120,
        "status": "error",
    }
    event = EventCreate(**data)
    assert event.provider == "openai"
    assert event.customer == "cust_12345"
    assert event.latency_ms == 120
    assert event.status == "error"


def test_event_create_forbids_extra_fields() -> None:
    # id, created_at, and cost_usd must be rejected
    base_data = {
        "provider": "anthropic",
        "model": "claude-3-haiku-20240307",
        "input_tokens": 100,
        "output_tokens": 50,
        "feature": "summarization",
    }

    with pytest.raises(ValidationError):
        EventCreate(**base_data, cost_usd="0.01")

    with pytest.raises(ValidationError):
        EventCreate(**base_data, id=str(uuid.uuid4()))

    with pytest.raises(ValidationError):
        EventCreate(**base_data, created_at="2026-01-01T00:00:00Z")

    with pytest.raises(ValidationError):
        EventCreate(**base_data, unexpected_field="foo")


def test_event_create_invalid_provider() -> None:
    with pytest.raises(ValidationError):
        EventCreate(
            provider="cohere",
            model="command-r",
            input_tokens=10,
            output_tokens=10,
            feature="chat",
        )


def test_event_create_model_length_validation() -> None:
    # Model cannot be empty
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="",
            input_tokens=10,
            output_tokens=10,
            feature="chat",
        )

    # Model max length is 128
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="a" * 129,
            input_tokens=10,
            output_tokens=10,
            feature="chat",
        )


def test_event_create_negative_tokens() -> None:
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=-1,
            output_tokens=10,
            feature="chat",
        )

    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=10,
            output_tokens=-1,
            feature="chat",
        )


def test_event_create_feature_validation() -> None:
    # Feature cannot be empty
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=10,
            output_tokens=10,
            feature="",
        )

    # Feature max 64 chars
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=10,
            output_tokens=10,
            feature="x" * 65,
        )

    # Feature cannot have leading or trailing whitespace
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=10,
            output_tokens=10,
            feature=" chat",
        )

    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=10,
            output_tokens=10,
            feature="chat ",
        )


def test_event_create_customer_length_validation() -> None:
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=10,
            output_tokens=10,
            feature="chat",
            customer="c" * 129,
        )


def test_event_create_latency_validation() -> None:
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=10,
            output_tokens=10,
            feature="chat",
            latency_ms=-1,
        )


def test_event_create_status_validation() -> None:
    with pytest.raises(ValidationError):
        EventCreate(
            provider="openai",
            model="gpt-4o",
            input_tokens=10,
            output_tokens=10,
            feature="chat",
            status="unknown",
        )


def test_event_response_serializes_cost_usd_as_string() -> None:
    from datetime import UTC, datetime

    event_id = uuid.uuid4()
    now = datetime.now(UTC)

    # Instantiate with Decimal
    resp = EventResponse(
        id=event_id,
        created_at=now,
        provider="anthropic",
        model="claude-3-haiku-20240307",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=Decimal("0.01050000"),
        feature="summarization",
        customer=None,
        latency_ms=150,
        status="ok",
    )

    assert resp.cost_usd == "0.01050000"
    assert isinstance(resp.cost_usd, str)
    assert not isinstance(resp.cost_usd, float)

    # Verify JSON dump
    dumped = resp.model_dump(mode="json")
    assert dumped["cost_usd"] == "0.01050000"
    assert isinstance(dumped["cost_usd"], str)


def test_event_response_with_str_cost_usd() -> None:
    from datetime import UTC, datetime

    resp = EventResponse(
        id=uuid.uuid4(),
        created_at=datetime.now(UTC),
        provider="anthropic",
        model="claude-3-haiku-20240307",
        input_tokens=1000,
        output_tokens=500,
        cost_usd="0.01050000",
        feature="summarization",
        customer=None,
        latency_ms=150,
        status="ok",
    )
    assert resp.cost_usd == "0.01050000"
