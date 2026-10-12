from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol, runtime_checkable

ONE_MILLION = Decimal("1000000")
EIGHT_DECIMAL_PLACES = Decimal("0.00000001")


class CostCalculationError(Exception):
    """Base domain exception for cost calculation errors."""


class UnknownModelPriceError(CostCalculationError):
    """Raised when no price rate is found for a model."""

    def __init__(self, model: str, provider: str | None = None) -> None:
        self.model = model
        self.provider = provider
        message = f"No price found for model '{model}'"
        if provider:
            message += f" (provider: '{provider}')"
        super().__init__(message)


class UnsupportedProviderError(CostCalculationError):
    """Raised when no strategy is registered for the specified provider."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"Unsupported provider: '{provider}'")


@runtime_checkable
class PriceProtocol(Protocol):
    """Protocol for model price information."""

    input_per_mtok_usd: Decimal
    output_per_mtok_usd: Decimal


@dataclass(frozen=True)
class ModelPrice:
    """In-memory representation of model pricing rates."""

    input_per_mtok_usd: Decimal
    output_per_mtok_usd: Decimal


@runtime_checkable
class CostStrategy(Protocol):
    """Strategy interface for provider cost calculation."""

    def calculate(
        self,
        input_tokens: int,
        output_tokens: int,
        input_per_mtok: Decimal,
        output_per_mtok: Decimal,
    ) -> Decimal:
        """Calculate the cost in USD rounded to 8 decimal places."""
        ...


class BaseMTokCostStrategy:
    """Standard cost calculation strategy based on tokens per million."""

    def calculate(
        self,
        input_tokens: int,
        output_tokens: int,
        input_per_mtok: Decimal,
        output_per_mtok: Decimal,
    ) -> Decimal:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts cannot be negative")

        if isinstance(input_per_mtok, float) or isinstance(output_per_mtok, float):
            raise TypeError("Price rates must be Decimal instances, never float")

        input_cost = (Decimal(input_tokens) / ONE_MILLION) * input_per_mtok
        output_cost = (Decimal(output_tokens) / ONE_MILLION) * output_per_mtok
        total = input_cost + output_cost

        return total.quantize(EIGHT_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


class AnthropicCostStrategy(BaseMTokCostStrategy):
    """Cost strategy for Anthropic LLM models."""


class OpenAICostStrategy(BaseMTokCostStrategy):
    """Cost strategy for OpenAI LLM models."""


PriceLookup = (
    Mapping[tuple[str, str], PriceProtocol] | Callable[[str, str], PriceProtocol | None]
)


class CostCalculator:
    """Context that coordinates provider strategies to calculate LLM call costs."""

    def __init__(
        self,
        strategies: Mapping[str, CostStrategy] | None = None,
        prices: PriceLookup | None = None,
    ) -> None:
        self._strategies: dict[str, CostStrategy] = (
            dict(strategies)
            if strategies is not None
            else {
                "anthropic": AnthropicCostStrategy(),
                "openai": OpenAICostStrategy(),
            }
        )
        self._prices = prices

    def calculate(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        price: PriceProtocol | None = None,
        input_per_mtok: Decimal | None = None,
        output_per_mtok: Decimal | None = None,
    ) -> Decimal:
        """Calculate the cost for a given provider, model, and token usage."""
        if provider not in self._strategies:
            raise UnsupportedProviderError(provider)

        strategy = self._strategies[provider]

        in_rate: Decimal
        out_rate: Decimal

        if price is not None:
            in_rate = price.input_per_mtok_usd
            out_rate = price.output_per_mtok_usd
        elif input_per_mtok is not None and output_per_mtok is not None:
            in_rate = input_per_mtok
            out_rate = output_per_mtok
        elif self._prices is not None:
            resolved_price: PriceProtocol | None = None
            if callable(self._prices):
                resolved_price = self._prices(provider, model)
            elif isinstance(self._prices, Mapping):
                resolved_price = self._prices.get((provider, model))

            if resolved_price is None:
                raise UnknownModelPriceError(model=model, provider=provider)

            in_rate = resolved_price.input_per_mtok_usd
            out_rate = resolved_price.output_per_mtok_usd
        else:
            raise UnknownModelPriceError(model=model, provider=provider)

        return strategy.calculate(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_per_mtok=in_rate,
            output_per_mtok=out_rate,
        )

    calculate_cost = calculate
