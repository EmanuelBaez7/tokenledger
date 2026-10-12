from decimal import Decimal

import pytest

from app.services.cost_calculator import (
    AnthropicCostStrategy,
    CostCalculator,
    CostStrategy,
    ModelPrice,
    OpenAICostStrategy,
    UnknownModelPriceError,
    UnsupportedProviderError,
)


def test_calculate_cost_exact_example() -> None:
    """(a) with input price 3.00 and output 15.00,

    1000 input tokens and 500 output tokens give exactly Decimal('0.01050000').
    """
    calculator = CostCalculator()
    cost = calculator.calculate(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=1000,
        output_tokens=500,
        input_per_mtok=Decimal("3.00"),
        output_per_mtok=Decimal("15.00"),
    )
    assert cost == Decimal("0.01050000")


def test_calculate_cost_with_model_price_object() -> None:
    """Test calculate accepts a PriceProtocol / ModelPrice object."""
    calculator = CostCalculator()
    price = ModelPrice(
        input_per_mtok_usd=Decimal("3.00"),
        output_per_mtok_usd=Decimal("15.00"),
    )
    cost = calculator.calculate(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=1000,
        output_tokens=500,
        price=price,
    )
    assert cost == Decimal("0.01050000")


def test_zero_tokens_gives_zero() -> None:
    """(b) zero tokens gives zero."""
    calculator = CostCalculator()
    cost = calculator.calculate(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=0,
        output_tokens=0,
        input_per_mtok=Decimal("3.00"),
        output_per_mtok=Decimal("15.00"),
    )
    assert cost == Decimal("0.00000000")
    assert cost == 0


def test_unknown_model_raises_domain_error() -> None:
    """(c) unknown model raises domain error."""
    calculator = CostCalculator()
    with pytest.raises(UnknownModelPriceError) as exc_info:
        calculator.calculate(
            provider="anthropic",
            model="unknown-model-xyz",
            input_tokens=1000,
            output_tokens=500,
        )

    assert "unknown-model-xyz" in str(exc_info.value)
    assert exc_info.value.model == "unknown-model-xyz"
    assert exc_info.value.provider == "anthropic"


def test_unknown_model_when_price_is_none() -> None:
    """Explicitly passing price=None raises UnknownModelPriceError."""
    calculator = CostCalculator()
    with pytest.raises(UnknownModelPriceError):
        calculator.calculate(
            provider="anthropic",
            model="unknown-model",
            input_tokens=100,
            output_tokens=50,
            price=None,
        )


def test_result_is_decimal_never_float() -> None:
    """(d) the result is Decimal, never float."""
    calculator = CostCalculator()
    cost = calculator.calculate(
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        input_per_mtok=Decimal("2.50"),
        output_per_mtok=Decimal("10.00"),
    )
    assert isinstance(cost, Decimal)
    assert not isinstance(cost, float)


def test_strategies_implement_protocol() -> None:
    """Ensure provider strategies implement CostStrategy protocol."""
    anthropic_strategy = AnthropicCostStrategy()
    openai_strategy = OpenAICostStrategy()

    assert isinstance(anthropic_strategy, CostStrategy)
    assert isinstance(openai_strategy, CostStrategy)

    res_anthropic = anthropic_strategy.calculate(
        input_tokens=1000,
        output_tokens=500,
        input_per_mtok=Decimal("3.00"),
        output_per_mtok=Decimal("15.00"),
    )
    assert res_anthropic == Decimal("0.01050000")

    res_openai = openai_strategy.calculate(
        input_tokens=1000,
        output_tokens=500,
        input_per_mtok=Decimal("2.50"),
        output_per_mtok=Decimal("10.00"),
    )
    # (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
    # = 0.0025 + 0.0050 = 0.00750000
    assert res_openai == Decimal("0.00750000")


def test_calculator_with_prices_catalog() -> None:
    """Test CostCalculator initialized with a prices catalog."""
    prices = {
        ("openai", "gpt-4o"): ModelPrice(
            input_per_mtok_usd=Decimal("2.50"),
            output_per_mtok_usd=Decimal("10.00"),
        )
    }
    calculator = CostCalculator(prices=prices)

    cost = calculator.calculate(
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
    )
    assert cost == Decimal("0.00750000")

    with pytest.raises(UnknownModelPriceError):
        calculator.calculate(
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500,
        )


def test_unsupported_provider_raises_error() -> None:
    """Unsupported provider raises UnsupportedProviderError."""
    calculator = CostCalculator()
    with pytest.raises(UnsupportedProviderError):
        calculator.calculate(
            provider="cohere",
            model="command-r",
            input_tokens=100,
            output_tokens=100,
            input_per_mtok=Decimal("1.00"),
            output_per_mtok=Decimal("2.00"),
        )


def test_negative_tokens_raises_value_error() -> None:
    """Negative tokens must raise ValueError."""
    calculator = CostCalculator()
    with pytest.raises(ValueError, match="negative"):
        calculator.calculate(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=-10,
            output_tokens=50,
            input_per_mtok=Decimal("3.00"),
            output_per_mtok=Decimal("15.00"),
        )


def test_float_price_rejected() -> None:
    """Passing float prices instead of Decimal raises TypeError."""
    calculator = CostCalculator()
    with pytest.raises(TypeError, match="Decimal"):
        calculator.calculate(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
            input_per_mtok=3.0,  # type: ignore[arg-type]
            output_per_mtok=15.0,  # type: ignore[arg-type]
        )


def test_rounding_half_up() -> None:
    """Test rounding at 8 decimal places with ROUND_HALF_UP."""
    # input_tokens = 15, rate = 0.001 -> 15 / 1_000_000 * 0.001 = 0.000000015
    # With ROUND_HALF_UP at 8 decimals, 0.000000015 rounds up to 0.00000002
    calculator = CostCalculator()
    cost = calculator.calculate(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=15,
        output_tokens=0,
        input_per_mtok=Decimal("0.001"),
        output_per_mtok=Decimal("0"),
    )
    assert cost == Decimal("0.00000002")
