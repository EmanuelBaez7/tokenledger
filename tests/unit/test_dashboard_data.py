from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest

from dashboard.data import (
    ApiConnectionError,
    DashboardMetrics,
    MissingConfigurationError,
    UnauthorizedError,
    calculate_totals,
    fetch_costs,
    get_top_feature,
    prepare_chart_data,
    prepare_table_data,
    sort_by_cost_descending,
)


def test_calculate_totals_regular_data() -> None:
    items = [
        {
            "key": "chat",
            "total_cost_usd": "0.01500000",
            "total_input_tokens": 1000,
            "total_output_tokens": 500,
            "calls": 2,
        },
        {
            "key": "summarize",
            "total_cost_usd": "0.03500000",
            "total_input_tokens": 2000,
            "total_output_tokens": 1000,
            "calls": 3,
        },
    ]

    metrics = calculate_totals(items)

    assert isinstance(metrics, DashboardMetrics)
    assert metrics.total_cost_usd == Decimal("0.05000000")
    assert not isinstance(metrics.total_cost_usd, float)
    assert metrics.total_calls == 5
    assert metrics.total_input_tokens == 3000
    assert metrics.total_output_tokens == 1500
    # Average cost: 0.05 / 5 = 0.01000000
    assert metrics.average_cost_per_call == Decimal("0.01000000")
    assert metrics.top_feature == "summarize"


def test_calculate_totals_costo_medio_con_cero_llamadas() -> None:
    items = [
        {
            "key": "failed_feature",
            "total_cost_usd": "0.00000000",
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "calls": 0,
        }
    ]

    metrics = calculate_totals(items)

    assert metrics.total_calls == 0
    assert metrics.total_cost_usd == Decimal("0.00000000")
    assert metrics.average_cost_per_call == Decimal("0")
    assert not isinstance(metrics.average_cost_per_call, float)


def test_calculate_totals_lista_vacia() -> None:
    metrics = calculate_totals([])

    assert metrics.total_cost_usd == Decimal("0")
    assert metrics.total_calls == 0
    assert metrics.total_input_tokens == 0
    assert metrics.total_output_tokens == 0
    assert metrics.average_cost_per_call == Decimal("0")
    assert metrics.top_feature is None


def test_feature_mas_cara() -> None:
    items = [
        {"key": "low_feature", "total_cost_usd": "0.00100000"},
        {"key": "high_feature", "total_cost_usd": "0.09500000"},
        {"key": "mid_feature", "total_cost_usd": "0.02000000"},
    ]

    top = get_top_feature(items)
    assert top == "high_feature"


def test_feature_mas_cara_lista_vacia() -> None:
    assert get_top_feature([]) is None


def test_orden_descendente() -> None:
    items = [
        {"key": "item_1", "total_cost_usd": "0.00500000"},
        {"key": "item_2", "total_cost_usd": "0.05000000"},
        {"key": "item_3", "total_cost_usd": "0.02000000"},
    ]

    sorted_items = sort_by_cost_descending(items)

    keys = [item["key"] for item in sorted_items]
    assert keys == ["item_2", "item_3", "item_1"]
    costs = [Decimal(item["total_cost_usd"]) for item in sorted_items]
    assert costs == sorted(costs, reverse=True)


def test_prepare_chart_data_converts_float_only_for_chart() -> None:
    items = [
        {"key": "feat_a", "total_cost_usd": "0.01000000", "calls": 1},
        {"key": "feat_b", "total_cost_usd": "0.05000000", "calls": 5},
    ]

    chart_data = prepare_chart_data(items)

    assert len(chart_data) == 2
    # Highest cost first
    assert chart_data[0]["key"] == "feat_b"
    assert isinstance(chart_data[0]["total_cost_usd"], float)
    assert chart_data[0]["total_cost_usd"] == 0.05
    assert chart_data[0]["is_top"] is True
    assert "$0.05" in chart_data[0]["total_cost_label"]

    assert chart_data[1]["key"] == "feat_a"
    assert isinstance(chart_data[1]["total_cost_usd"], float)
    assert chart_data[1]["total_cost_usd"] == 0.01
    assert chart_data[1]["is_top"] is False


def test_prepare_chart_data_lista_vacia() -> None:
    assert prepare_chart_data([]) == []


def test_prepare_table_data() -> None:
    items = [
        {
            "key": "cust_1",
            "total_cost_usd": "0.01000000",
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "calls": 2,
        }
    ]

    table_data = prepare_table_data(items)
    assert len(table_data) == 1
    row = table_data[0]
    assert row["key"] == "cust_1"
    assert row["total_cost_usd"] == "0.01000000"
    assert row["calls"] == 2
    assert row["total_input_tokens"] == 100
    assert row["total_output_tokens"] == 50


def test_prepare_table_data_lista_vacia() -> None:
    assert prepare_table_data([]) == []


def test_fetch_costs_missing_api_key_raises_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("API_KEY", raising=False)

    with pytest.raises(MissingConfigurationError) as exc_info:
        fetch_costs(group_by="feature", api_key=None)

    assert "API_KEY" in str(exc_info.value)


def test_fetch_costs_unauthorized_raises_error() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_client.get.return_value = mock_response

    with pytest.raises(UnauthorizedError) as exc_info:
        fetch_costs(
            group_by="feature",
            base_url="http://test-api:8000",
            api_key="wrong-secret-key",
            client=mock_client,
        )

    # Error message must NOT reveal the key value
    assert "wrong-secret-key" not in str(exc_info.value)
    assert "API_KEY" in str(exc_info.value)


def test_fetch_costs_connection_error_raises_error() -> None:
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    with pytest.raises(ApiConnectionError) as exc_info:
        fetch_costs(
            group_by="feature",
            base_url="http://test-api:8000",
            api_key="valid-key",
            client=mock_client,
        )

    assert "conectar" in str(exc_info.value).lower()


def test_fetch_costs_successful_request() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "key": "chat",
            "total_cost_usd": "0.01050000",
            "total_input_tokens": 1000,
            "total_output_tokens": 500,
            "calls": 2,
        }
    ]
    mock_client.get.return_value = mock_response

    data = fetch_costs(
        group_by="feature",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 1, 14),
        base_url="http://test-api:8000",
        api_key="valid-key",
        client=mock_client,
    )

    assert len(data) == 1
    assert data[0]["key"] == "chat"
    mock_client.get.assert_called_once_with(
        "http://test-api:8000/v1/costs",
        params={"group_by": "feature", "from": "2024-01-01", "to": "2024-01-14"},
        headers={"X-API-Key": "valid-key"},
    )
