from datetime import date
from typing import Literal

from app.repositories.events import AggregatedCost, EventRepository

GroupByDimension = Literal["feature", "customer", "model"]


class InvalidDateRangeError(ValueError):
    """Raised when date_from is after date_to."""

    def __init__(self, date_from: date, date_to: date) -> None:
        self.date_from = date_from
        self.date_to = date_to
        super().__init__(
            f"'from' date ({date_from}) cannot be after 'to' date ({date_to})"
        )


class ReportService:
    """Domain service for generating aggregated cost reports."""

    def __init__(self, event_repo: EventRepository) -> None:
        self.event_repo = event_repo

    def get_costs(
        self,
        group_by: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[AggregatedCost]:
        """Aggregate event costs by dimension with optional date filters."""
        if date_from is not None and date_to is not None and date_from > date_to:
            raise InvalidDateRangeError(date_from=date_from, date_to=date_to)

        return self.event_repo.aggregate(
            group_by=group_by,
            date_from=date_from,
            date_to=date_to,
        )
