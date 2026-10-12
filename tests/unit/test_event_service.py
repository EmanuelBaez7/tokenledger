from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.db.models import Price
from app.services.cost_calculator import CostCalculator, UnknownModelPriceError
from app.services.events import EventService


def test_event_service_creates_event_successfully() -> None:
    mock_event_repo = MagicMock()
    mock_price_repo = MagicMock()
    mock_event_repo.add.side_effect = lambda e: e

    # Return a price
    mock_price = Price(
        id=1,
        provider="anthropic",
        model="claude-3-haiku-20240307",
        input_per_mtok_usd=Decimal("3.00"),
        output_per_mtok_usd=Decimal("15.00"),
        effective_from=date(2024, 1, 1),
    )
    mock_price_repo.get_current.return_value = mock_price

    service = EventService(
        event_repo=mock_event_repo,
        price_repo=mock_price_repo,
        cost_calculator=CostCalculator(),
    )

    event = service.create_event(
        provider="anthropic",
        model="claude-3-haiku-20240307",
        input_tokens=1000,
        output_tokens=500,
        feature="summarization",
        customer="cust_1",
        latency_ms=200,
        status="ok",
    )

    assert event.provider == "anthropic"
    assert event.model == "claude-3-haiku-20240307"
    assert event.input_tokens == 1000
    assert event.output_tokens == 500
    assert event.cost_usd == Decimal("0.01050000")
    assert event.feature == "summarization"
    assert event.customer == "cust_1"
    assert event.latency_ms == 200
    assert event.status == "ok"

    # Verify repository calls and commit
    mock_price_repo.get_current.assert_called_once_with(
        provider="anthropic",
        model="claude-3-haiku-20240307",
        at_date=datetime.now(UTC).date(),
    )
    mock_event_repo.add.assert_called_once_with(event)
    mock_event_repo.session.commit.assert_called_once()


def test_event_service_raises_unknown_model_price_error_when_no_price() -> None:
    mock_event_repo = MagicMock()
    mock_price_repo = MagicMock()
    mock_price_repo.get_current.return_value = None

    service = EventService(
        event_repo=mock_event_repo,
        price_repo=mock_price_repo,
        cost_calculator=CostCalculator(),
    )

    with pytest.raises(UnknownModelPriceError) as exc_info:
        service.create_event(
            provider="anthropic",
            model="unknown-model",
            input_tokens=100,
            output_tokens=50,
            feature="summarization",
        )

    assert exc_info.value.model == "unknown-model"
    assert exc_info.value.provider == "anthropic"
    mock_event_repo.add.assert_not_called()
