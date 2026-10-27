import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator


class CostRow(BaseModel):
    """Validate the API contract before data reaches metrics or charts."""

    model_config = ConfigDict(strict=True)

    key: str
    total_cost_usd: str
    total_input_tokens: int = Field(ge=0)
    total_output_tokens: int = Field(ge=0)
    calls: int = Field(ge=0)

    @field_validator("total_cost_usd")
    @classmethod
    def validate_cost(cls, value: str) -> str:
        try:
            cost = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Invalid cost") from exc
        if not cost.is_finite() or cost < 0:
            raise ValueError("Cost must be finite and non-negative")
        return value


_cost_rows = TypeAdapter(list[CostRow])


class DashboardError(Exception):
    """Base exception for dashboard data operations."""


class MissingConfigurationError(DashboardError):
    """Raised when required environment configuration is missing."""


class UnauthorizedError(DashboardError):
    """Raised when API returns 401 Unauthorized."""


class ApiConnectionError(DashboardError):
    """Raised when the dashboard cannot connect to the API."""


class ApiError(DashboardError):
    """Raised when the API returns an unexpected error."""


@dataclass(frozen=True)
class DashboardMetrics:
    """Calculated totals and key indicators for the dashboard."""

    total_cost_usd: Decimal
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    average_cost_per_call: Decimal
    top_feature: str | None


def get_api_config() -> tuple[str, str]:
    """Retrieve API_BASE_URL and API_KEY from environment."""
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise MissingConfigurationError(
            "API_KEY environment variable is not configured. Please define it."
        )
    return base_url, api_key


def fetch_costs(
    group_by: str,
    date_from: date | None = None,
    date_to: date | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Fetch cost aggregations from TokenLedger API using httpx."""
    if base_url is None or api_key is None:
        cfg_url, cfg_key = get_api_config()
        base_url = base_url or cfg_url
        api_key = api_key or cfg_key

    params: dict[str, str] = {"group_by": group_by}
    if date_from:
        params["from"] = date_from.isoformat()
    if date_to:
        params["to"] = date_to.isoformat()

    headers = {"X-API-Key": api_key}
    endpoint = f"{base_url.rstrip('/')}/v1/costs"

    try:
        if client is not None:
            response = client.get(endpoint, params=params, headers=headers)
        else:
            with httpx.Client(timeout=timeout) as default_client:
                response = default_client.get(endpoint, params=params, headers=headers)
    except (
        httpx.ConnectError,
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.RequestError,
    ) as exc:
        raise ApiConnectionError(
            "No se pudo conectar con la API. "
            "Verifica que el servicio esté activo y accesible."
        ) from exc

    if response.status_code == 401:
        raise UnauthorizedError(
            "La API rechazó las credenciales. Revisa la variable API_KEY."
        )

    if response.status_code != 200:
        raise ApiError(
            f"Error {response.status_code} devuelto por la API al consultar {endpoint}."
        )

    try:
        rows = _cost_rows.validate_python(response.json())
    except (ValueError, TypeError) as exc:
        raise ApiError("La API devolvió una respuesta inválida de costos.") from exc
    return [row.model_dump() for row in rows]


def calculate_totals(items: list[dict[str, Any]]) -> DashboardMetrics:
    """Calculate aggregated metrics across items using Decimal for exact amounts."""
    if not items:
        return DashboardMetrics(
            total_cost_usd=Decimal("0"),
            total_calls=0,
            total_input_tokens=0,
            total_output_tokens=0,
            average_cost_per_call=Decimal("0"),
            top_feature=None,
        )

    total_cost = sum(
        (Decimal(str(item.get("total_cost_usd", "0"))) for item in items),
        Decimal("0"),
    )
    total_calls = sum((int(item.get("calls", 0)) for item in items), 0)
    total_input = sum((int(item.get("total_input_tokens", 0)) for item in items), 0)
    total_output = sum((int(item.get("total_output_tokens", 0)) for item in items), 0)

    avg_cost = (total_cost / total_calls) if total_calls > 0 else Decimal("0")

    top_item = max(
        items,
        key=lambda x: Decimal(str(x.get("total_cost_usd", "0"))),
    )
    top_feature_key = str(top_item.get("key")) if top_item else None

    return DashboardMetrics(
        total_cost_usd=total_cost,
        total_calls=total_calls,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        average_cost_per_call=avg_cost,
        top_feature=top_feature_key,
    )


def get_top_feature(feature_items: list[dict[str, Any]]) -> str | None:
    """Return the key of the feature with the highest cost, or None if empty."""
    if not feature_items:
        return None
    top_item = max(
        feature_items,
        key=lambda x: Decimal(str(x.get("total_cost_usd", "0"))),
    )
    return str(top_item["key"])


def sort_by_cost_descending(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort list of cost items in descending order of total_cost_usd."""
    return sorted(
        items,
        key=lambda item: Decimal(str(item.get("total_cost_usd", "0"))),
        reverse=True,
    )


def prepare_chart_data(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform cost items for charting: converts Decimal to float only here."""
    if not items:
        return []

    sorted_items = sort_by_cost_descending(items)
    max_cost = Decimal(str(sorted_items[0].get("total_cost_usd", "0")))

    result: list[dict[str, Any]] = []
    for item in sorted_items:
        cost_decimal = Decimal(str(item.get("total_cost_usd", "0")))
        cost_float = float(cost_decimal)
        is_top = (cost_decimal == max_cost) and (max_cost > Decimal("0"))

        result.append(
            {
                "key": str(item.get("key")),
                "total_cost_usd": cost_float,
                "total_cost_label": f"${cost_decimal:.4f}",
                "calls": int(item.get("calls", 0)),
                "is_top": is_top,
            }
        )
    return result


def prepare_table_data(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform cost items for presentation in tabular dataframe."""
    if not items:
        return []

    sorted_items = sort_by_cost_descending(items)
    return [
        {
            "key": str(item.get("key")),
            "total_cost_usd": str(item.get("total_cost_usd", "0.00000000")),
            "calls": int(item.get("calls", 0)),
            "total_input_tokens": int(item.get("total_input_tokens", 0)),
            "total_output_tokens": int(item.get("total_output_tokens", 0)),
        }
        for item in sorted_items
    ]
