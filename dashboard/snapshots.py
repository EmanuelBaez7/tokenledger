"""Consistent report snapshots from a single daily query and current dimensions."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

import httpx

from dashboard.analytics import (
    CostItems,
    DailyPoint,
    Period,
    daily_rows,
    daily_series,
    observations,
)
from dashboard.data import (
    ApiError,
    DashboardMetrics,
    MissingConfigurationError,
    calculate_totals,
    fetch_costs,
)
from dashboard.demo import DemoEvent, aggregate_demo, load_demo_events

Source = Literal["api", "demo"]
MIN_DATE = date(2000, 1, 1)
MAX_DATE = date(2100, 12, 31)


@dataclass(frozen=True)
class SourceConfig:
    options: tuple[Source, ...]
    selected: Source
    locked: bool
    base_url: str = ""
    api_key: str = field(default="", repr=False)

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> "SourceConfig":
        source = env.get("DASHBOARD_DATA_SOURCE", "api")
        if source not in {"api", "demo"}:
            raise MissingConfigurationError(
                "La fuente de datos no es válida. "
                "Configura DASHBOARD_DATA_SOURCE como api o demo."
            )
        base = env.get("API_BASE_URL", "").strip()
        key = env.get("API_KEY", "")
        if source == "demo" or not base or not key:
            return cls(("demo",), "demo", True, base, key)
        return cls(("api", "demo"), "api", False, base, key)


@dataclass(frozen=True)
class ReportSnapshot:
    source: Source
    period: Period
    features: CostItems
    customers: CostItems
    models: CostItems
    current_days: list[DailyPoint]
    previous_days: list[DailyPoint]
    metrics: DashboardMetrics
    previous_metrics: DashboardMetrics | None
    has_events: bool
    observations: tuple[str, ...]


def load_report(
    source: Source,
    period: Period,
    *,
    today: date,
    base_url: str = "",
    api_key: str = "",
    client: httpx.Client | None = None,
    events: list[DemoEvent] | None = None,
) -> ReportSnapshot:
    if period.start < MIN_DATE or period.end > min(MAX_DATE, today):
        raise ApiError(
            "El periodo no es válido. "
            "Elige fechas desde 2000 hasta hoy y pulsa Aplicar."
        )
    history_start = max(MIN_DATE, period.previous.start - timedelta(days=7))
    demo_events = load_demo_events() if source == "demo" and events is None else events
    if source == "api" and (not base_url or not api_key):
        raise MissingConfigurationError(
            "Falta la configuración de API. "
            "Selecciona demo o configura API_BASE_URL y API_KEY."
        )

    def fetch(group: str, start: date | None, end: date | None) -> CostItems:
        if source == "demo":
            return aggregate_demo(
                demo_events or [], group, today=today, date_from=start, date_to=end
            )
        return fetch_costs(
            group,
            date_from=start,
            date_to=end,
            base_url=base_url,
            api_key=api_key,
            client=client,
        )

    features = sorted(
        fetch("feature", period.start, period.end),
        key=lambda r: (-Decimal(r["total_cost_usd"]), r["key"]),
    )
    customers = fetch("customer", period.start, period.end)
    models = fetch("model", period.start, period.end)
    raw_daily = fetch("day", history_start, period.end)
    try:
        points = daily_series(
            raw_daily, Period(history_start, period.end), spike_period=period
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise ApiError(
            "La serie diaria de la API no es válida. Pulsa Reintentar."
        ) from exc
    current = [p for p in points if period.start <= p.day <= period.end]
    previous = [p for p in points if period.previous.start <= p.day < period.start]
    metrics = replace(
        calculate_totals(daily_rows(current)),
        top_feature=calculate_totals(features).top_feature,
    )
    for dimension in (features, customers, models):
        totals = calculate_totals(dimension)
        if (
            totals.total_cost_usd,
            totals.total_calls,
            totals.total_input_tokens,
            totals.total_output_tokens,
        ) != (
            metrics.total_cost_usd,
            metrics.total_calls,
            metrics.total_input_tokens,
            metrics.total_output_tokens,
        ):
            raise ApiError(
                "Los datos cambiaron durante la consulta y los totales no coinciden. "
                "Pulsa Reintentar para cargar un periodo consistente."
            )
    has_events = any(p.calls for p in points)
    if not has_events:
        has_events = bool(fetch("feature", None, None))
    return ReportSnapshot(
        source,
        period,
        features,
        customers,
        models,
        current,
        previous,
        metrics,
        calculate_totals(daily_rows(previous))
        if period.previous.start >= MIN_DATE
        else None,
        has_events,
        observations(features, customers, current),
    )
