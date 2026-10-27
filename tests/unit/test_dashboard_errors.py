from typing import Any

import httpx
import pytest

from dashboard.data import ApiError, fetch_costs


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


class DashboardStopped(Exception):
    pass


def run_dashboard(
    monkeypatch: pytest.MonkeyPatch, responses: list[httpx.Response]
) -> Any:
    import runpy
    import sys
    from functools import partial
    from unittest.mock import MagicMock

    ui = MagicMock()
    ui.stop.side_effect = DashboardStopped
    ui.button.return_value = False
    for module in ("streamlit", "altair", "pandas"):
        monkeypatch.setitem(
            sys.modules, module, ui if module == "streamlit" else MagicMock()
        )
    main = runpy.run_path("dashboard/app.py")["main"]
    iterator = iter(responses)
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: next(iterator))
    ) as client:
        monkeypatch.setitem(
            main.__globals__,
            "fetch_costs",
            partial(
                fetch_costs, base_url="http://test", api_key="synthetic", client=client
            ),
        )
        with pytest.raises(DashboardStopped):
            main()
    return ui


@pytest.mark.parametrize("failed_query", [1, 2, 3])
def test_dashboard_api_failure_never_shows_empty_state(
    monkeypatch: pytest.MonkeyPatch, failed_query: int
) -> None:
    responses = [httpx.Response(200, json=[]) for _ in range(failed_query - 1)]
    responses.append(httpx.Response(503))
    ui = run_dashboard(monkeypatch, responses)
    ui.error.assert_called_once()
    ui.button.assert_called_once_with("Reintentar")
    assert not ui.info.called


def test_dashboard_real_empty_state_has_module_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ui = run_dashboard(monkeypatch, [httpx.Response(200, json=[]) for _ in range(3)])
    ui.info.assert_called_once_with(
        "Aún no hay eventos. Ejecuta `uv run python -m scripts.seed_demo` "
        "o envía uno con el SDK."
    )
    ui.error.assert_not_called()


@pytest.mark.parametrize("body", [b"not json", b"null", b"[{}]"])
def test_dashboard_invalid_response_offers_retry(
    monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    ui = run_dashboard(monkeypatch, [httpx.Response(200, content=body)])
    ui.error.assert_called_once_with(
        "La API devolvió una respuesta inválida de costos."
    )
    ui.button.assert_called_once_with("Reintentar")
    ui.info.assert_not_called()
