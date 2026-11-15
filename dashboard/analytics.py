"""Exact, deterministic analytics independent of Streamlit and the API client."""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from dashboard.formatting import short_date

CostItems = list[dict[str, Any]]
ZERO = Decimal("0")


@dataclass(frozen=True)
class Period:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("La fecha inicial debe ser anterior o igual a la final.")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def previous(self) -> "Period":
        return Period(
            self.start - timedelta(days=self.days), self.start - timedelta(days=1)
        )


@dataclass(frozen=True)
class DailyPoint:
    day: date
    cost: Decimal
    calls: int
    input_tokens: int
    output_tokens: int
    rolling_mean: Decimal | None
    is_spike: bool

    @property
    def spike_label(self) -> str:
        if self.rolling_mean is None:
            return "Historial insuficiente"
        if self.rolling_mean == 0:
            return "Sin base para pico"
        return "Sí" if self.is_spike else "No"


def percent_change(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return ZERO if current == 0 else None
    return (current - previous) / previous * Decimal("100")


def daily_series(
    items: CostItems, period: Period, *, spike_period: Period | None = None
) -> list[DailyPoint]:
    by_day: dict[date, dict[str, Any]] = {}
    for item in items:
        day = date.fromisoformat(item["key"])
        if day in by_day or not period.start <= day <= period.end:
            raise ValueError(
                "La serie diaria contiene fechas duplicadas o fuera del periodo."
            )
        by_day[day] = item
    active = spike_period or period
    result: list[DailyPoint] = []
    candidates: list[tuple[Decimal, int]] = []
    for offset in range(period.days):
        day = period.start + timedelta(days=offset)
        row = by_day.get(day, {})
        cost = Decimal(row.get("total_cost_usd", "0"))
        history_cost = (
            sum((point.cost for point in result[-7:]), ZERO) if offset >= 7 else None
        )
        # Scale by seven to compare exact excesses without rounding the mean.
        if (
            active.start <= day <= active.end
            and history_cost is not None
            and history_cost > 0
            and cost * 14 > history_cost * 3
        ):
            candidates.append((cost * 7 - history_cost, offset))
        result.append(
            DailyPoint(
                day,
                cost,
                int(row.get("calls", 0)),
                int(row.get("total_input_tokens", 0)),
                int(row.get("total_output_tokens", 0)),
                history_cost / 7 if history_cost is not None else None,
                False,
            )
        )
    active_cost = sum(
        (p.cost for p in result if active.start <= p.day <= active.end), ZERO
    )
    minimum = active_cost * Decimal("0.05") * 7
    selected = sorted(
        ((excess, i) for excess, i in candidates if excess >= minimum),
        key=lambda candidate: (-candidate[0], candidate[1]),
    )[:3]
    for _, i in selected:
        result[i] = replace(result[i], is_spike=True)
    return result


def detail_rows(items: CostItems) -> CostItems:
    total = sum((Decimal(item["total_cost_usd"]) for item in items), ZERO)
    return [
        dict(
            item,
            total_cost_usd=Decimal(item["total_cost_usd"]),
            share_percent=Decimal(item["total_cost_usd"]) / total * 100
            if total
            else ZERO,
            cost_per_call=Decimal(item["total_cost_usd"]) / item["calls"]
            if item["calls"]
            else ZERO,
        )
        for item in items
    ]


def daily_rows(points: list[DailyPoint]) -> CostItems:
    items = [
        {
            "key": p.day.isoformat(),
            "date_label": short_date(p.day, year=True),
            "total_cost_usd": p.cost,
            "calls": p.calls,
            "total_input_tokens": p.input_tokens,
            "total_output_tokens": p.output_tokens,
            "rolling_mean": p.rolling_mean,
            "spike_label": p.spike_label,
        }
        for p in points
    ]
    return detail_rows(items)


def select_rows(
    items: CostItems,
    search: str = "",
    sort_by: str = "total_cost_usd",
    descending: bool = True,
) -> CostItems:
    allowed = {
        "key",
        "total_cost_usd",
        "share_percent",
        "calls",
        "cost_per_call",
        "total_input_tokens",
        "total_output_tokens",
    }
    if sort_by not in allowed:
        raise ValueError("Columna de orden no válida.")
    query = search.casefold()
    selected = [
        row
        for row in items
        if query in row["key"].casefold()
        or query in row.get("date_label", "").casefold()
    ]
    return sorted(
        sorted(selected, key=lambda row: row["key"]),
        key=lambda row: row[sort_by],
        reverse=descending,
    )


def leading_item(items: CostItems) -> dict[str, Any] | None:
    return min(
        items, key=lambda r: (-Decimal(r["total_cost_usd"]), r["key"]), default=None
    )


def observations(
    features: CostItems, customers: CostItems, points: list[DailyPoint]
) -> tuple[str, ...]:
    total = sum((Decimal(r["total_cost_usd"]) for r in features), ZERO)
    if total == 0:
        return (
            "No hubo gasto en el periodo. Amplía el rango para comparar actividad.",
        )
    notes = []
    for rows, label in ((features, "La feature"), (customers, "El cliente")):
        leader = leading_item(rows)
        if leader is not None:
            share = Decimal(leader["total_cost_usd"]) / total * 100
            notes.append(
                f"{label} {leader['key']} concentra el {share:.1f}% del gasto."
            )
    peaks = [p for p in points if p.is_spike]
    if peaks:
        peak = min(peaks, key=lambda p: (-(p.cost - (p.rolling_mean or ZERO)), p.day))
        excess = peak.cost - (peak.rolling_mean or ZERO)
        notes.append(
            f"El {short_date(peak.day)} registró el mayor exceso: "
            f"${excess:,.4f} por encima de su media previa."
        )
    else:
        notes.append("Ningún día cumplió los umbrales de pico de este periodo.")
    return tuple(notes)
