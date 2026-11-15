from pathlib import Path
from typing import Any

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.analytics import Period
from dashboard.data import ApiError, fetch_costs
from dashboard.snapshots import ReportSnapshot, Source


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"null",
        b"{}",
        b'["invalid"]',
        b"[{}]",
        b'[{"key": "x", "total_cost_usd": "NaN", "calls": 1, '
        b'"total_input_tokens": 0, "total_output_tokens": 0}]',
        b'[{"key": "x", "total_cost_usd": "1", "calls": true, '
        b'"total_input_tokens": 0, "total_output_tokens": 0}]',
    ],
)
def test_invalid_api_body_raises_dashboard_error(body: bytes) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    ) as client:
        with pytest.raises(ApiError, match="respuesta inválida"):
            fetch_costs(
                "feature", base_url="http://test", api_key="synthetic", client=client
            )


def run_dashboard(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[httpx.Response],
    *,
    retry: bool = False,
) -> AppTest:
    from dashboard import loading
    from dashboard.snapshots import load_report

    monkeypatch.setenv("DASHBOARD_DATA_SOURCE", "api")
    monkeypatch.setenv("API_BASE_URL", "http://test")
    monkeypatch.setenv("API_KEY", "synthetic")
    iterator = iter(responses)
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: next(iterator))
    ) as client:

        def fetch(source: Source, period: Period, **kwargs: Any) -> ReportSnapshot:
            return load_report(source, period, client=client, **kwargs)

        monkeypatch.setattr(loading, "load_report", fetch)
        app = AppTest.from_file(
            Path(__file__).resolve().parents[2] / "dashboard/app.py", default_timeout=15
        ).run()
        if retry:
            next(x for x in app.button if x.label == "Reintentar").click().run()
    assert not app.exception
    return app


@pytest.mark.parametrize("failed_query", [1, 2, 3, 4, 5])
def test_dashboard_api_failure_never_shows_empty_state(
    monkeypatch: pytest.MonkeyPatch, failed_query: int
) -> None:
    responses = [httpx.Response(200, json=[]) for _ in range(failed_query - 1)]
    responses.append(httpx.Response(503))
    app = run_dashboard(monkeypatch, responses)
    markup = "".join(x.value for x in app.markdown)
    assert 'role="alert"' in markup
    assert "No se pudieron cargar los datos" in markup
    assert (
        "Aún no hay eventos" not in markup and "Sin gasto en este rango" not in markup
    )
    assert [x.label for x in app.button].count("Reintentar") == 1


def test_dashboard_real_empty_state_has_module_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = run_dashboard(monkeypatch, [httpx.Response(200, json=[]) for _ in range(5)])
    markup = "".join(x.value for x in app.markdown)
    assert "Aún no hay eventos" in markup
    assert "uv run python -m scripts.seed_demo" in markup
    assert 'role="alert"' not in markup


def test_retry_reloads_after_api_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    app = run_dashboard(
        monkeypatch,
        [httpx.Response(503)] + [httpx.Response(200, json=[]) for _ in range(5)],
        retry=True,
    )
    markup = "".join(x.value for x in app.markdown)
    assert 'role="alert"' not in markup
    assert "uv run python -m scripts.seed_demo" in markup


@pytest.mark.parametrize("body", [b"not json", b"null", b"[{}]"])
def test_dashboard_invalid_response_offers_retry(
    monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    app = run_dashboard(monkeypatch, [httpx.Response(200, content=body)])
    markup = "".join(x.value for x in app.markdown)
    assert "respuesta inválida" in markup and 'role="alert"' in markup
    assert any(x.label == "Reintentar" for x in app.button)
    assert "Aún no hay eventos" not in markup
