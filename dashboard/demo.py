"""Versioned synthetic data source; no database or application imports."""

import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from dashboard.analytics import ZERO, CostItems
from dashboard.data import ApiError

DEMO_FILE = Path(__file__).with_name("demo_data") / "events.json"


class DemoEvent(BaseModel):
    model_config = ConfigDict(strict=True)
    days_ago: int = Field(ge=0)
    provider: str
    model: str
    feature: str
    customer: str | None
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: str

    @field_validator("cost_usd")
    @classmethod
    def validate_cost(cls, value: str) -> str:
        try:
            cost = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Invalid demo cost") from exc
        if not cost.is_finite() or cost < 0:
            raise ValueError("Invalid demo cost")
        return value


def load_demo_events(path: Path = DEMO_FILE) -> list[DemoEvent]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1 or not isinstance(
            payload.get("events"), list
        ):
            raise ValueError("Invalid demo schema")
        return [DemoEvent.model_validate(item) for item in payload["events"]]
    except (OSError, ValueError, TypeError, AttributeError, ValidationError) as exc:
        raise ApiError(
            "No se pudieron leer los datos de demo. "
            "Restaura el archivo de demostración y pulsa Reintentar."
        ) from exc


def aggregate_demo(
    events: list[DemoEvent],
    group_by: str,
    *,
    today: date,
    date_from: date | None = None,
    date_to: date | None = None,
) -> CostItems:
    if group_by not in {"feature", "customer", "model", "day"}:
        raise ValueError("Invalid demo grouping")
    groups: dict[str, dict] = {}
    for event in events:
        day = today - timedelta(days=event.days_ago)
        if (date_from and day < date_from) or (date_to and day > date_to):
            continue
        key = (
            day.isoformat()
            if group_by == "day"
            else getattr(event, group_by) or "unassigned"
        )
        row = groups.setdefault(
            key,
            {
                "key": key,
                "total_cost_usd": ZERO,
                "calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
            },
        )
        row["total_cost_usd"] += Decimal(event.cost_usd)
        row["calls"] += 1
        row["total_input_tokens"] += event.input_tokens
        row["total_output_tokens"] += event.output_tokens
    rows = [
        dict(row, total_cost_usd=f"{row['total_cost_usd']:.8f}")
        for row in groups.values()
    ]
    return sorted(
        rows,
        key=lambda r: (
            r["key"] if group_by == "day" else (-Decimal(r["total_cost_usd"]), r["key"])
        ),
    )
