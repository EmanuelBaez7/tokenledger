"""Unit tests for scripts/seed_demo.py — pure generation function."""

from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest

from scripts.seed_demo import (
    CUSTOMERS,
    FEATURES,
    SEED,
    WINDOW_DAYS,
    RawEvent,
    generate_demo_events,
)


@pytest.fixture()
def now_utc() -> datetime:
    """Fixed UTC reference timestamp for deterministic tests."""
    return datetime(2026, 10, 20, 20, 0, 0, tzinfo=UTC)


@pytest.fixture()
def demo_events(now_utc: datetime) -> list[RawEvent]:
    rng = random.Random(SEED)
    return generate_demo_events(rng, now_utc)


# ---------------------------------------------------------------------------
# Quantity
# ---------------------------------------------------------------------------


def test_event_count_close_to_target(demo_events: list[RawEvent]) -> None:
    """Generated events should be in the range [250, 400]."""
    count = len(demo_events)
    assert 250 <= count <= 400, f"Expected ~300 events, got {count}"


def test_event_count_stable_with_same_seed(now_utc: datetime) -> None:
    """Two runs with the same seed must produce identical results."""
    rng1 = random.Random(SEED)
    rng2 = random.Random(SEED)
    events1 = generate_demo_events(rng1, now_utc)
    events2 = generate_demo_events(rng2, now_utc)
    assert len(events1) == len(events2)
    for e1, e2 in zip(events1, events2, strict=True):
        assert e1 == e2


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


def test_no_future_events(demo_events: list[RawEvent], now_utc: datetime) -> None:
    """No event should have created_at after 'now'."""
    future = [e for e in demo_events if e.created_at > now_utc]
    assert future == [], f"{len(future)} events are in the future"


def test_all_events_within_14_days(
    demo_events: list[RawEvent], now_utc: datetime
) -> None:
    """All events must fall within the last WINDOW_DAYS days."""
    from datetime import timedelta

    oldest_allowed = (now_utc - timedelta(days=WINDOW_DAYS)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    too_old = [e for e in demo_events if e.created_at < oldest_allowed]
    assert too_old == [], f"{len(too_old)} events are older than {WINDOW_DAYS} days"


def test_events_are_utc(demo_events: list[RawEvent]) -> None:
    """All timestamps must be timezone-aware (UTC)."""
    non_utc = [e for e in demo_events if e.created_at.tzinfo is None]
    assert non_utc == [], "Found events without timezone info"


# ---------------------------------------------------------------------------
# Features & customers
# ---------------------------------------------------------------------------


def test_all_features_present(demo_events: list[RawEvent]) -> None:
    """All four features must appear at least once."""
    found = {e.feature for e in demo_events}
    assert set(FEATURES) <= found


def test_all_customers_present(demo_events: list[RawEvent]) -> None:
    """All five named customers must appear at least once."""
    found = {e.customer for e in demo_events}
    for c in CUSTOMERS:
        assert c in found, f"Customer '{c}' not found in generated events"


def test_some_events_have_no_customer(demo_events: list[RawEvent]) -> None:
    """Some events should have customer=None (anonymous calls)."""
    no_customer = [e for e in demo_events if e.customer is None]
    assert len(no_customer) > 0, "Expected some events without a customer"


# ---------------------------------------------------------------------------
# Error events
# ---------------------------------------------------------------------------


def test_error_events_have_zero_tokens(demo_events: list[RawEvent]) -> None:
    """Error events must have input_tokens=0 and output_tokens=0."""
    error_events = [e for e in demo_events if e.status == "error"]
    assert len(error_events) > 0, "Expected some error events"
    for e in error_events:
        assert e.input_tokens == 0, f"Error event has non-zero input_tokens: {e}"
        assert e.output_tokens == 0, f"Error event has non-zero output_tokens: {e}"


def test_error_rate_approximately_3_percent(demo_events: list[RawEvent]) -> None:
    """Error rate should be between 1% and 7%."""
    errors = sum(1 for e in demo_events if e.status == "error")
    rate = errors / len(demo_events)
    assert 0.01 <= rate <= 0.07, (
        f"Error rate {rate:.2%} is out of expected range [1%, 7%]"
    )


# ---------------------------------------------------------------------------
# Narrative: traduccion is top feature, globex is top customer
# ---------------------------------------------------------------------------


def test_traduccion_is_most_frequent_feature(demo_events: list[RawEvent]) -> None:
    """'traduccion' should be the most frequent feature (drives highest cost)."""
    feature_counts: dict[str, int] = {}
    for e in demo_events:
        feature_counts[e.feature] = feature_counts.get(e.feature, 0) + 1
    top_feature = max(feature_counts, key=lambda k: feature_counts[k])
    assert top_feature == "traduccion", (
        f"Expected 'traduccion' to be top feature, got '{top_feature}'. "
        f"Counts: {feature_counts}"
    )


def test_globex_is_most_frequent_customer(demo_events: list[RawEvent]) -> None:
    """'globex' should be the customer with the most events."""
    customer_counts: dict[str, int] = {}
    for e in demo_events:
        key = e.customer or "unassigned"
        customer_counts[key] = customer_counts.get(key, 0) + 1
    top_customer = max(customer_counts, key=lambda k: customer_counts[k])
    assert top_customer == "globex", (
        f"Expected 'globex' to be top customer, got '{top_customer}'. "
        f"Counts: {customer_counts}"
    )


# ---------------------------------------------------------------------------
# Model coverage
# ---------------------------------------------------------------------------


def test_both_providers_present(demo_events: list[RawEvent]) -> None:
    """Events must use both anthropic and openai providers."""
    providers = {e.provider for e in demo_events}
    assert "anthropic" in providers
    assert "openai" in providers


def test_all_models_present(demo_events: list[RawEvent]) -> None:
    """All four models from prices.seed.yaml must appear."""
    expected_models = {
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307",
        "gpt-4o",
        "gpt-4o-mini",
    }
    found_models = {e.model for e in demo_events}
    assert expected_models <= found_models, (
        f"Missing models: {expected_models - found_models}"
    )


# ---------------------------------------------------------------------------
# Cost placeholder (pure function only returns RawEvent without cost_usd)
# ---------------------------------------------------------------------------


def test_raw_events_have_no_cost_field(demo_events: list[RawEvent]) -> None:
    """RawEvent is a pure data structure without a cost_usd field."""
    assert not hasattr(demo_events[0], "cost_usd"), (
        "RawEvent should not carry cost_usd — that is computed during DB insertion"
    )


def test_ok_events_have_positive_tokens(demo_events: list[RawEvent]) -> None:
    """Non-error events should have positive token counts."""
    ok_events = [e for e in demo_events if e.status == "ok"]
    zero_token = [e for e in ok_events if e.input_tokens <= 0 and e.output_tokens <= 0]
    assert zero_token == [], f"{len(zero_token)} OK events have zero tokens"
