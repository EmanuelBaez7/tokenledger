from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.repositories.events import AggregatedCost
from app.services.reports import InvalidDateRangeError, ReportService


def test_report_service_delegates_to_repository() -> None:
    mock_repo = MagicMock()
    mock_repo.aggregate.return_value = [
        AggregatedCost(
            key="chat",
            total_cost_usd=Decimal("0.01050000"),
            total_input_tokens=1000,
            total_output_tokens=500,
            calls=2,
        )
    ]

    service = ReportService(event_repo=mock_repo)
    results = service.get_costs(
        group_by="feature",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 1, 31),
    )

    assert len(results) == 1
    assert results[0].key == "chat"
    assert results[0].total_cost_usd == Decimal("0.01050000")
    assert results[0].calls == 2
    mock_repo.aggregate.assert_called_once_with(
        group_by="feature",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 1, 31),
    )


def test_report_service_without_dates() -> None:
    mock_repo = MagicMock()
    mock_repo.aggregate.return_value = []

    service = ReportService(event_repo=mock_repo)
    results = service.get_costs(group_by="model")

    assert results == []
    mock_repo.aggregate.assert_called_once_with(
        group_by="model",
        date_from=None,
        date_to=None,
    )


def test_report_service_raises_when_from_after_to() -> None:
    mock_repo = MagicMock()
    service = ReportService(event_repo=mock_repo)

    with pytest.raises(InvalidDateRangeError) as exc_info:
        service.get_costs(
            group_by="feature",
            date_from=date(2024, 5, 20),
            date_to=date(2024, 5, 10),
        )

    assert exc_info.value.date_from == date(2024, 5, 20)
    assert exc_info.value.date_to == date(2024, 5, 10)
    mock_repo.aggregate.assert_not_called()
