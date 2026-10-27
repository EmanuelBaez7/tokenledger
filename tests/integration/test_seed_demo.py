"""Integration tests for scripts/seed_demo.py — database insertion and aggregation."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from scripts.seed_demo import SEED, generate_demo_events


@pytest.fixture()
def _seed_prices(db_session):
    """Ensure prices table has the 4 models from prices.seed.yaml."""
    from app.db.seed import seed_prices

    seed_prices(db_session)


@pytest.fixture()
def seeded_session(db_session, _seed_prices):
    """Session with prices pre-loaded and demo events inserted."""
    from scripts.seed_demo import _insert_events

    now = datetime(2026, 10, 20, 20, 0, 0, tzinfo=UTC)
    rng = random.Random(SEED)
    raw_events = generate_demo_events(rng, now)
    _insert_events(db_session, raw_events)
    return db_session


# ---------------------------------------------------------------------------
# Aggregation consistency
# ---------------------------------------------------------------------------


def test_feature_totals_sum_matches_global(seeded_session) -> None:
    """Sum of all feature costs must equal sum of all customer costs."""
    from app.repositories.events import EventRepository

    repo = EventRepository(seeded_session)
    feature_rows = repo.aggregate("feature")
    customer_rows = repo.aggregate("customer")

    feature_total = sum(r.total_cost_usd for r in feature_rows)
    customer_total = sum(r.total_cost_usd for r in customer_rows)

    # Both sums must be equal (same events, different dimension)
    assert feature_total == customer_total, (
        f"Feature total {feature_total} != Customer total {customer_total}"
    )

    # Both totals must be Decimal instances, never float
    assert isinstance(feature_total, Decimal)
    assert isinstance(customer_total, Decimal)


def test_feature_total_is_positive(seeded_session) -> None:
    """There should be non-zero total cost after seeding."""
    from app.repositories.events import EventRepository

    repo = EventRepository(seeded_session)
    feature_rows = repo.aggregate("feature")
    total = sum(r.total_cost_usd for r in feature_rows)
    assert total > Decimal("0"), "Total cost should be positive after seeding"


# ---------------------------------------------------------------------------
# Narrative verification
# ---------------------------------------------------------------------------


def test_traduccion_is_top_feature_by_cost(seeded_session) -> None:
    """'traduccion' must be the feature with the highest total cost."""
    from app.repositories.events import EventRepository

    repo = EventRepository(seeded_session)
    feature_rows = repo.aggregate("feature")  # ordered by cost DESC

    assert len(feature_rows) > 0, "No feature rows returned"
    assert feature_rows[0].key == "traduccion", (
        f"Expected 'traduccion' as top feature, got '{feature_rows[0].key}'. "
        f"Rows: {[(r.key, r.total_cost_usd) for r in feature_rows]}"
    )


def test_globex_is_top_customer_by_cost(seeded_session) -> None:
    """'globex' must be the customer with the highest total cost."""
    from app.repositories.events import EventRepository

    repo = EventRepository(seeded_session)
    customer_rows = repo.aggregate("customer")  # ordered by cost DESC

    assert len(customer_rows) > 0, "No customer rows returned"
    assert customer_rows[0].key == "globex", (
        f"Expected 'globex' as top customer, got '{customer_rows[0].key}'. "
        f"Rows: {[(r.key, r.total_cost_usd) for r in customer_rows]}"
    )


# ---------------------------------------------------------------------------
# Error events have cost_usd = 0
# ---------------------------------------------------------------------------


def test_error_events_have_zero_cost(seeded_session) -> None:
    """All error events must have cost_usd = 0 in the database."""
    from sqlalchemy import select

    from app.db.models import Event

    error_events = seeded_session.scalars(
        select(Event).where(Event.status == "error")
    ).all()

    assert len(error_events) > 0, "Expected some error events in the database"
    for ev in error_events:
        assert ev.cost_usd == Decimal("0"), (
            f"Error event {ev.id} has non-zero cost: {ev.cost_usd}"
        )
        assert ev.input_tokens == 0
        assert ev.output_tokens == 0


# ---------------------------------------------------------------------------
# Totals are Decimal instances
# ---------------------------------------------------------------------------


def test_aggregated_costs_are_decimal(seeded_session) -> None:
    """AggregatedCost.total_cost_usd must always be Decimal, never float."""
    from app.repositories.events import EventRepository

    repo = EventRepository(seeded_session)
    for row in repo.aggregate("feature"):
        assert isinstance(row.total_cost_usd, Decimal), (
            f"total_cost_usd for '{row.key}' is {type(row.total_cost_usd)}, not Decimal"
        )


# ---------------------------------------------------------------------------
# All features and customers appear in DB
# ---------------------------------------------------------------------------


def test_all_features_present_in_db(seeded_session) -> None:
    """All four features must appear in the DB aggregation."""
    from app.repositories.events import EventRepository

    repo = EventRepository(seeded_session)
    features = {r.key for r in repo.aggregate("feature")}
    for feat in ["resumen", "traduccion", "chat", "clasificacion"]:
        assert feat in features, f"Feature '{feat}' not found in DB"


def test_all_customers_present_in_db(seeded_session) -> None:
    """All five customers (plus 'unassigned') must appear in the DB aggregation."""
    from app.repositories.events import EventRepository

    repo = EventRepository(seeded_session)
    customers = {r.key for r in repo.aggregate("customer")}
    for cust in ["acme", "globex", "initech", "umbrella", "hooli"]:
        assert cust in customers, f"Customer '{cust}' not found in DB"
    # Anonymous events are grouped as 'unassigned'
    assert "unassigned" in customers, "Expected 'unassigned' customer group"


def test_summary_distinguishes_cost_and_call_leaders(
    db_session, _seed_prices, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts.seed_demo import RawEvent, _insert_events, _print_summary

    now = datetime(2026, 10, 20, tzinfo=UTC)
    events = [
        RawEvent("openai", "gpt-4o-mini", "frequent", "many", 1, 1, "ok", 1, now),
        RawEvent("openai", "gpt-4o-mini", "frequent", "many", 1, 1, "ok", 1, now),
        RawEvent(
            "anthropic",
            "claude-3-5-sonnet-20241022",
            "costly",
            "spender",
            10000,
            10000,
            "ok",
            1,
            now,
        ),
    ]
    summary = _insert_events(db_session, events)
    _print_summary(events, summary)
    output = capsys.readouterr().out
    assert "Top feature por costo : costly" in output
    assert "Top customer por costo: spender" in output
    assert "Top feature por llamadas : frequent" in output
    assert "Top customer por llamadas: many" in output
