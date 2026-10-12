from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.db.models import Event


class RepositoryError(Exception):
    """Base domain exception for repository errors."""


class InvalidGroupByError(RepositoryError, ValueError):
    """Raised when an invalid group_by dimension is requested."""

    def __init__(self, group_by: str) -> None:
        self.group_by = group_by
        super().__init__(
            f"Invalid group_by field '{group_by}'. "
            "Allowed fields are: 'feature', 'customer', 'model'."
        )


@dataclass(frozen=True)
class AggregatedCost:
    """Aggregated usage and cost metrics for a grouped dimension."""

    key: str
    total_cost_usd: Decimal
    total_input_tokens: int
    total_output_tokens: int
    calls: int

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


_GROUP_BY_COLUMNS: Mapping[str, ColumnElement[Any]] = {
    "feature": Event.feature,
    "customer": func.coalesce(Event.customer, "unassigned"),
    "model": Event.model,
}


class EventRepository:
    """Repository for persisting and querying LLM usage events."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: Event) -> Event:
        """Persist a new event into the database."""
        self.session.add(event)
        self.session.flush()
        return event

    def aggregate(
        self,
        group_by: str,
        date_from: date | datetime | None = None,
        date_to: date | datetime | None = None,
    ) -> list[AggregatedCost]:
        """Aggregate event costs, token usage, and calls by dimension.

        - group_by: 'feature', 'customer', or 'model'.
        - date_from: inclusive from 00:00 UTC.
        - date_to: inclusive until the end of that day (created_at < date_to + 1 day).
        - customer NULL events are grouped under 'unassigned'.
        - sums are returned as Decimal instances, never float.
        """
        if group_by not in _GROUP_BY_COLUMNS:
            raise InvalidGroupByError(group_by)

        group_column = _GROUP_BY_COLUMNS[group_by]
        key_label = group_column.label("key")
        total_cost_expr = func.coalesce(func.sum(Event.cost_usd), Decimal("0")).label(
            "total_cost_usd"
        )
        total_input_expr = func.coalesce(func.sum(Event.input_tokens), 0).label(
            "total_input_tokens"
        )
        total_output_expr = func.coalesce(func.sum(Event.output_tokens), 0).label(
            "total_output_tokens"
        )
        calls_expr = func.count(Event.id).label("calls")

        stmt = select(
            key_label,
            total_cost_expr,
            total_input_expr,
            total_output_expr,
            calls_expr,
        ).group_by(group_column)

        if date_from is not None:
            d_from = date_from.date() if isinstance(date_from, datetime) else date_from
            start_dt = datetime.combine(d_from, time.min, tzinfo=UTC)
            stmt = stmt.where(Event.created_at >= start_dt)

        if date_to is not None:
            d_to = date_to.date() if isinstance(date_to, datetime) else date_to
            end_dt = datetime.combine(d_to + timedelta(days=1), time.min, tzinfo=UTC)
            stmt = stmt.where(Event.created_at < end_dt)

        stmt = stmt.order_by(total_cost_expr.desc())

        rows = self.session.execute(stmt).all()

        return [
            AggregatedCost(
                key=str(row.key),
                total_cost_usd=(
                    row.total_cost_usd
                    if isinstance(row.total_cost_usd, Decimal)
                    else Decimal(str(row.total_cost_usd))
                ),
                total_input_tokens=int(row.total_input_tokens),
                total_output_tokens=int(row.total_output_tokens),
                calls=int(row.calls),
            )
            for row in rows
        ]
