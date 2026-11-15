from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from dashboard.analytics import Period
from dashboard.data import ApiError
from dashboard.demo import aggregate_demo, load_demo_events
from dashboard.snapshots import SourceConfig, load_report


def test_demo_fixture_is_recent_exact_and_has_both_providers() -> None:
    events = load_demo_events()
    assert 350 <= len(events) <= 450
    assert {e.provider for e in events} == {"openai", "anthropic"}
    assert all(e.days_ago >= 0 for e in events)
    today = date(2026, 4, 30)
    features = aggregate_demo(events, "feature", today=date(2026, 4, 30))
    customers = aggregate_demo(events, "customer", today=today)
    assert features[0]["key"] == "traduccion"
    assert customers[0]["key"] == "globex"
    assert any(r["key"] == "unassigned" for r in customers)
    assert sum(Decimal(r["total_cost_usd"]) for r in features) == sum(
        Decimal(r["total_cost_usd"]) for r in customers
    )
    daily = aggregate_demo(events, "day", today=today, date_from=today, date_to=today)
    assert all(r["key"] == today.isoformat() for r in daily)


def test_demo_grows_between_windows_and_keeps_its_spending_story() -> None:
    today = date(2026, 4, 30)
    calls = []
    for window in range(4, -1, -1):
        end = today - timedelta(days=14 * window)
        report = load_report("demo", Period(end - timedelta(days=13), end), today=today)
        calls.append(report.metrics.total_calls)
        assert report.features[0]["key"] == "traduccion"
        assert report.customers[0]["key"] == "globex"
        if window == 0:
            assert [p.day for p in report.current_days if p.is_spike] == [
                end - timedelta(days=3)
            ]
            previous_costs = [p.cost for p in report.previous_days]
            previous_average = sum(previous_costs) / len(previous_costs)
            assert previous_average > 0
            assert (
                Decimal("0.70")
                <= min(previous_costs) / previous_average
                <= Decimal("0.85")
            )
            assert (
                Decimal("1.15")
                <= max(previous_costs) / previous_average
                <= Decimal("1.30")
            )
        else:
            assert not any(p.is_spike for p in report.current_days)
    for previous, current in zip(calls, calls[1:], strict=False):
        assert 112 * previous <= 100 * current <= 113 * previous


@pytest.mark.parametrize(
    ("env", "expected", "locked"),
    [
        ({}, ("demo",), True),
        ({"API_BASE_URL": "http://test"}, ("demo",), True),
        ({"API_KEY": "synthetic"}, ("demo",), True),
        (
            {"API_BASE_URL": "http://test", "API_KEY": "synthetic"},
            ("api", "demo"),
            False,
        ),
        (
            {
                "API_BASE_URL": "http://test",
                "API_KEY": "synthetic",
                "DASHBOARD_DATA_SOURCE": "demo",
            },
            ("demo",),
            True,
        ),
    ],
)
def test_source_options_obey_environment(
    env: dict[str, str], expected: tuple[str, ...], locked: bool
) -> None:
    config = SourceConfig.from_environment(env)
    assert config.options == expected
    assert config.locked is locked
    assert "synthetic" not in repr(config)


def test_demo_snapshot_needs_neither_network_nor_configuration() -> None:
    report = load_report(
        "demo", Period(date(2026, 4, 17), date(2026, 4, 30)), today=date(2026, 4, 30)
    )
    assert report.source == "demo"
    assert report.metrics.total_calls > 0
    assert len(report.current_days) == 14 and len(report.previous_days) == 14
    assert sum(d.cost for d in report.current_days) == report.metrics.total_cost_usd
    assert report.metrics.top_feature == "traduccion"
    assert report.customers[0]["key"] == "globex"
    assert len(report.observations) <= 3


def test_api_uses_one_daily_query_for_the_complete_history() -> None:
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        report = load_report(
            "api",
            Period(date(2026, 4, 17), date(2026, 4, 30)),
            today=date(2026, 4, 30),
            base_url="http://test",
            api_key="synthetic",
            client=client,
        )
    daily = [r for r in requests if r.url.params["group_by"] == "day"]
    assert len(daily) == 1
    assert daily[0].url.params["from"] == "2026-03-27"
    assert daily[0].url.params["to"] == "2026-04-30"
    assert not report.has_events


def test_failure_in_second_api_query_is_never_converted_to_empty() -> None:
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[]) if calls == 1 else httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ApiError):
            load_report(
                "api",
                Period(date(2026, 4, 17), date(2026, 4, 30)),
                today=date(2026, 4, 30),
                base_url="http://test",
                api_key="synthetic",
                client=client,
            )


def test_demo_aggregation_is_inclusive_and_preserves_null_customers() -> None:
    from dashboard.demo import DemoEvent

    events = [
        DemoEvent(
            days_ago=ago,
            provider="openai",
            model="synthetic",
            feature="x",
            customer=None,
            input_tokens=1,
            output_tokens=0,
            cost_usd="0.10000000",
        )
        for ago in (0, 1, 2)
    ]
    result = aggregate_demo(
        events,
        "customer",
        today=date(2026, 4, 30),
        date_from=date(2026, 4, 29),
        date_to=date(2026, 4, 30),
    )
    assert result == [
        {
            "key": "unassigned",
            "total_cost_usd": "0.20000000",
            "calls": 2,
            "total_input_tokens": 2,
            "total_output_tokens": 0,
        }
    ]


def test_generated_fixture_is_reproducible() -> None:
    import json

    from dashboard.demo import DEMO_FILE
    from scripts.generate_dashboard_demo import build_events

    assert build_events() == json.loads(DEMO_FILE.read_text(encoding="utf-8"))["events"]


def test_malformed_demo_file_has_a_typed_safe_error(tmp_path: Path) -> None:
    from dashboard.demo import load_demo_events

    path = tmp_path / "broken.json"
    path.write_text("null", encoding="utf-8")
    with pytest.raises(ApiError, match="Reintentar"):
        load_demo_events(path)


def test_inconsistent_api_totals_are_rejected_instead_of_fabricated() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        group = request.url.params["group_by"]
        rows = (
            []
            if group == "day"
            else [
                {
                    "key": "x",
                    "total_cost_usd": "1",
                    "calls": 1,
                    "total_input_tokens": 1,
                    "total_output_tokens": 1,
                }
            ]
        )
        return httpx.Response(200, json=rows)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ApiError, match="totales no coinciden"):
            load_report(
                "api",
                Period(date(2026, 4, 17), date(2026, 4, 30)),
                today=date(2026, 4, 30),
                base_url="http://test",
                api_key="synthetic",
                client=client,
            )


def test_demo_runtime_imports_no_application_and_works_without_network() -> None:
    import os
    import subprocess
    import sys

    code = """
import builtins
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name in {'app','sdk'} or name.startswith(('app.','sdk.')):
        raise AssertionError('Application import in dashboard runtime')
    return original(name,*args,**kwargs)
builtins.__import__=guarded
from datetime import date
from dashboard.analytics import Period
from dashboard.snapshots import load_report
report=load_report('demo',Period(date(2026,4,17),date(2026,4,30)),today=date(2026,4,30))
assert report.metrics.total_calls>0
"""
    env = os.environ.copy()
    for name in ("API_KEY", "API_BASE_URL", "DATABASE_URL"):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
