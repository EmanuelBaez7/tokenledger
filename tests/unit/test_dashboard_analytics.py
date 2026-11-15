from datetime import date, timedelta
from decimal import Decimal

import pytest

from dashboard.analytics import (
    Period,
    daily_series,
    detail_rows,
    observations,
    percent_change,
)


def row(key: str, cost: str, calls: int = 1) -> dict[str, object]:
    return {
        "key": key,
        "total_cost_usd": cost,
        "calls": calls,
        "total_input_tokens": 10 * calls,
        "total_output_tokens": 5 * calls,
    }


def test_period_comparison_uses_equal_inclusive_lengths() -> None:
    current = Period(date(2026, 3, 1), date(2026, 3, 14))
    assert current.days == 14
    assert current.previous == Period(date(2026, 2, 15), date(2026, 2, 28))
    with pytest.raises(ValueError):
        Period(date(2026, 3, 2), date(2026, 3, 1))


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [
        ("12", "10", Decimal("20")),
        ("0", "10", Decimal("-100")),
        ("0", "0", Decimal("0")),
        ("10", "0", None),
    ],
)
def test_percent_change_handles_zero_base(
    current: str, previous: str, expected: Decimal | None
) -> None:
    assert percent_change(Decimal(current), Decimal(previous)) == expected


def test_spikes_use_only_seven_previous_days_with_strict_threshold() -> None:
    rows = [row(f"2026-04-{d:02d}", "2") for d in range(1, 8)]
    rows.extend([row("2026-04-08", "3"), row("2026-04-09", "10")])
    series = daily_series(rows, Period(date(2026, 4, 1), date(2026, 4, 10)))
    assert series[7].rolling_mean == Decimal("2")
    assert not series[7].is_spike
    assert series[8].is_spike
    assert series[9].cost == 0 and series[9].calls == 0
    assert series[0].rolling_mean is None


def test_zero_baseline_is_not_a_spike() -> None:
    series = daily_series(
        [row("2026-04-08", "10")], Period(date(2026, 4, 1), date(2026, 4, 8))
    )
    assert series[-1].rolling_mean == 0
    assert not series[-1].is_spike
    assert series[-1].spike_label == "Sin base para pico"


@pytest.mark.parametrize(("last_cost", "marked"), [("36", True), ("36.01", False)])
def test_spike_excess_threshold_includes_exact_five_percent(
    last_cost: str, marked: bool
) -> None:
    history = Period(date(2026, 4, 1), date(2026, 4, 9))
    active = Period(date(2026, 4, 8), history.end)
    rows = [row(f"2026-04-{d:02d}", "2") for d in range(1, 8)]
    rows += [row("2026-04-08", "4"), row("2026-04-09", last_cost)]
    series = daily_series(rows, history, spike_period=active)
    assert series[7].is_spike is marked


def test_spike_limit_ranks_by_excess_and_breaks_ties_by_date() -> None:
    start = date(2026, 4, 1)
    costs = {7: "8", 15: "12", 23: "10", 31: "8", 39: "9"}
    rows = [
        row(
            (start + timedelta(days=i)).isoformat(),
            costs.get(i, "6" if 8 <= i < 15 else "1"),
        )
        for i in range(40)
    ]
    series = daily_series(rows, Period(start, start + timedelta(days=39)))
    assert [(p.day - start).days for p in series if p.is_spike] == [7, 23, 39]
    assert series[15].spike_label == series[31].spike_label == "No"
    notes = observations([row("traduccion", "117")], [row("globex", "65")], series)
    assert "globex" in notes[1]
    assert "24 abr" in notes[2] and "$9.0000" in notes[2]


def test_detail_rows_use_exact_shares_and_weighted_rates() -> None:
    rows = detail_rows([row("a", "0.1", 2), row("b", "0.2", 8)])
    assert sum(r["total_cost_usd"] for r in rows) == Decimal("0.3")
    assert rows[0]["cost_per_call"] == Decimal("0.05")
    assert sum(r["share_percent"] for r in rows) == Decimal("100")
