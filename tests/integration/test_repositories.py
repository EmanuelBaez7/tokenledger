from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Event, Price
from app.repositories.events import (
    AggregatedCost,
    EventRepository,
    InvalidGroupByError,
)
from app.repositories.prices import PriceRepository


def test_event_repository_add(db_session: Session) -> None:
    repo = EventRepository(db_session)
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=Decimal("0.01050000"),
        latency_ms=250,
        feature="summarization",
        customer="acme-corp",
    )
    saved = repo.add(event)
    db_session.commit()

    assert saved.id is not None
    assert saved.created_at is not None

    found = db_session.scalar(select(Event).where(Event.id == saved.id))
    assert found is not None
    assert found.feature == "summarization"
    assert found.customer == "acme-corp"
    assert found.cost_usd == Decimal("0.01050000")


def test_aggregate_by_feature(db_session: Session) -> None:
    repo = EventRepository(db_session)
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.00100000"),
            feature="chat",
            customer="c1",
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=200,
            output_tokens=100,
            cost_usd=Decimal("0.00200000"),
            feature="chat",
            customer="c2",
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=300,
            output_tokens=150,
            cost_usd=Decimal("0.00500000"),
            feature="summarize",
            customer="c1",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    results = repo.aggregate(group_by="feature")

    assert len(results) == 2
    assert all(isinstance(r, AggregatedCost) for r in results)
    # Ordered by total_cost_usd desc: summarize (0.005) then chat (0.003)
    assert results[0].key == "summarize"
    assert results[0]["key"] == "summarize"
    assert results[0].total_cost_usd == Decimal("0.00500000")
    assert results[0].total_input_tokens == 300
    assert results[0].total_output_tokens == 150
    assert results[0].calls == 1

    assert results[1].key == "chat"
    assert results[1].total_cost_usd == Decimal("0.00300000")
    assert results[1].total_input_tokens == 300
    assert results[1].total_output_tokens == 150
    assert results[1].calls == 2


def test_aggregate_by_customer(db_session: Session) -> None:
    repo = EventRepository(db_session)
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.00100000"),
            feature="chat",
            customer="cust-alpha",
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=400,
            output_tokens=200,
            cost_usd=Decimal("0.00800000"),
            feature="search",
            customer="cust-beta",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    results = repo.aggregate(group_by="customer")

    assert len(results) == 2
    assert results[0].key == "cust-beta"
    assert results[0].total_cost_usd == Decimal("0.00800000")
    assert results[0].calls == 1
    assert results[1].key == "cust-alpha"
    assert results[1].total_cost_usd == Decimal("0.00100000")
    assert results[1].calls == 1


def test_aggregate_by_model(db_session: Session) -> None:
    repo = EventRepository(db_session)
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.00200000"),
            feature="chat",
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=200,
            output_tokens=100,
            cost_usd=Decimal("0.00600000"),
            feature="search",
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.00300000"),
            feature="chat",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    results = repo.aggregate(group_by="model")

    assert len(results) == 2
    assert results[0].key == "gpt-4o"
    assert results[0].total_cost_usd == Decimal("0.00900000")
    assert results[0].total_input_tokens == 300
    assert results[0].total_output_tokens == 150
    assert results[0].calls == 2

    assert results[1].key == "claude-3-5-sonnet"
    assert results[1].total_cost_usd == Decimal("0.00200000")
    assert results[1].total_input_tokens == 100
    assert results[1].total_output_tokens == 50
    assert results[1].calls == 1


def test_aggregate_customer_null_grouped_as_unassigned(db_session: Session) -> None:
    repo = EventRepository(db_session)
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.00200000"),
            feature="chat",
            customer=None,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=150,
            output_tokens=75,
            cost_usd=Decimal("0.00300000"),
            feature="summarize",
            customer=None,
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=50,
            output_tokens=25,
            cost_usd=Decimal("0.00100000"),
            feature="chat",
            customer="assigned-customer",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    results = repo.aggregate(group_by="customer")

    assert len(results) == 2
    assert results[0].key == "unassigned"
    assert results[0].total_cost_usd == Decimal("0.00500000")
    assert results[0].total_input_tokens == 250
    assert results[0].total_output_tokens == 125
    assert results[0].calls == 2

    assert results[1].key == "assigned-customer"
    assert results[1].total_cost_usd == Decimal("0.00100000")
    assert results[1].calls == 1


def test_aggregate_date_filters_including_last_day(db_session: Session) -> None:
    repo = EventRepository(db_session)

    # Base dates
    dt_before = datetime(2024, 5, 9, 23, 59, 59, tzinfo=UTC)
    dt_start = datetime(2024, 5, 10, 0, 0, 0, tzinfo=UTC)
    dt_mid = datetime(2024, 5, 11, 14, 30, 0, tzinfo=UTC)
    dt_end_day = datetime(2024, 5, 12, 23, 59, 59, 999000, tzinfo=UTC)
    dt_after = datetime(2024, 5, 13, 0, 0, 0, tzinfo=UTC)

    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=10,
            output_tokens=10,
            cost_usd=Decimal("0.00010000"),
            feature="feat-before",
            created_at=dt_before,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=20,
            output_tokens=20,
            cost_usd=Decimal("0.00020000"),
            feature="feat-in-range",
            created_at=dt_start,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=30,
            output_tokens=30,
            cost_usd=Decimal("0.00030000"),
            feature="feat-in-range",
            created_at=dt_mid,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=40,
            output_tokens=40,
            cost_usd=Decimal("0.00040000"),
            feature="feat-in-range",
            created_at=dt_end_day,
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=50,
            output_tokens=50,
            cost_usd=Decimal("0.00050000"),
            feature="feat-after",
            created_at=dt_after,
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    # Query range: 2024-05-10 to 2024-05-12 inclusive of the entire end day
    results = repo.aggregate(
        group_by="feature",
        date_from=date(2024, 5, 10),
        date_to=date(2024, 5, 12),
    )

    assert len(results) == 1
    assert results[0].key == "feat-in-range"
    assert results[0].calls == 3
    assert results[0].total_cost_usd == Decimal("0.00090000")
    assert results[0].total_input_tokens == 90
    assert results[0].total_output_tokens == 90


def test_aggregate_ordered_by_cost_descending(db_session: Session) -> None:
    repo = EventRepository(db_session)
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.01000000"),
            feature="low-cost",
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=Decimal("0.50000000"),
            feature="high-cost",
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=500,
            output_tokens=250,
            cost_usd=Decimal("0.20000000"),
            feature="mid-cost",
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    results = repo.aggregate(group_by="feature")

    costs = [r.total_cost_usd for r in results]
    assert costs == sorted(costs, reverse=True)
    assert [r.key for r in results] == ["high-cost", "mid-cost", "low-cost"]


def test_aggregate_sum_matches_global_total(db_session: Session) -> None:
    repo = EventRepository(db_session)
    events = [
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=110,
            output_tokens=40,
            cost_usd=Decimal("0.00150000"),
            feature="chat",
            customer="cust-1",
        ),
        Event(
            provider="anthropic",
            model="claude-3-5-sonnet",
            input_tokens=220,
            output_tokens=80,
            cost_usd=Decimal("0.00300000"),
            feature="chat",
            customer=None,
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=330,
            output_tokens=120,
            cost_usd=Decimal("0.00650000"),
            feature="summarize",
            customer="cust-2",
        ),
        Event(
            provider="openai",
            model="gpt-4o",
            input_tokens=440,
            output_tokens=160,
            cost_usd=Decimal("0.00900000"),
            feature="search",
            customer=None,
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    expected_total_cost = sum((e.cost_usd for e in events), Decimal("0"))
    expected_input_tokens = sum(e.input_tokens for e in events)
    expected_output_tokens = sum(e.output_tokens for e in events)
    expected_calls = len(events)

    for dimension in ("feature", "customer", "model"):
        rows = repo.aggregate(group_by=dimension)
        sum_cost = sum((r.total_cost_usd for r in rows), Decimal("0"))
        sum_inputs = sum(r.total_input_tokens for r in rows)
        sum_outputs = sum(r.total_output_tokens for r in rows)
        sum_calls = sum(r.calls for r in rows)

        assert sum_cost == expected_total_cost
        assert sum_inputs == expected_input_tokens
        assert sum_outputs == expected_output_tokens
        assert sum_calls == expected_calls


def test_aggregate_empty_result_returns_empty_list(db_session: Session) -> None:
    repo = EventRepository(db_session)
    # 1. On empty database
    assert repo.aggregate(group_by="feature") == []

    # 2. When events exist but date range excludes all
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.00100000"),
        feature="chat",
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    db_session.add(event)
    db_session.commit()

    res = repo.aggregate(
        group_by="feature",
        date_from=date(2025, 1, 1),
        date_to=date(2025, 1, 31),
    )
    assert res == []


def test_aggregate_invalid_group_by_raises_error(db_session: Session) -> None:
    repo = EventRepository(db_session)

    with pytest.raises(InvalidGroupByError):
        repo.aggregate(group_by="provider")

    with pytest.raises(InvalidGroupByError):
        repo.aggregate(group_by="invalid_column")

    with pytest.raises(InvalidGroupByError):
        repo.aggregate(group_by="created_at; DROP TABLE events;")


def test_aggregate_sums_are_decimal_never_float(db_session: Session) -> None:
    repo = EventRepository(db_session)
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=123,
        output_tokens=456,
        cost_usd=Decimal("0.00789012"),
        feature="analysis",
    )
    db_session.add(event)
    db_session.commit()

    results = repo.aggregate(group_by="feature")
    assert len(results) == 1
    row = results[0]

    assert isinstance(row.total_cost_usd, Decimal)
    assert not isinstance(row.total_cost_usd, float)
    assert isinstance(row.total_input_tokens, int)
    assert not isinstance(row.total_input_tokens, float)
    assert isinstance(row.total_output_tokens, int)
    assert not isinstance(row.total_output_tokens, float)


def test_price_repository_get_current_effective_date(db_session: Session) -> None:
    repo = PriceRepository(db_session)

    p1 = Price(
        provider="openai",
        model="gpt-4o",
        input_per_mtok_usd=Decimal("2.500000"),
        output_per_mtok_usd=Decimal("10.000000"),
        effective_from=date(2024, 1, 1),
    )
    p2 = Price(
        provider="openai",
        model="gpt-4o",
        input_per_mtok_usd=Decimal("2.000000"),
        output_per_mtok_usd=Decimal("8.000000"),
        effective_from=date(2024, 6, 1),
    )
    p3_other_model = Price(
        provider="openai",
        model="gpt-4o-mini",
        input_per_mtok_usd=Decimal("0.150000"),
        output_per_mtok_usd=Decimal("0.600000"),
        effective_from=date(2024, 1, 1),
    )
    db_session.add_all([p1, p2, p3_other_model])
    db_session.commit()

    # 1. Before first effective date -> None
    assert repo.get_current("openai", "gpt-4o", date(2023, 12, 31)) is None

    # 2. Exactly on first effective date -> p1
    cur1 = repo.get_current("openai", "gpt-4o", date(2024, 1, 1))
    assert cur1 is not None
    assert cur1.id == p1.id
    assert cur1.input_per_mtok_usd == Decimal("2.500000")

    # 3. Between first and second effective dates -> p1
    cur_mid = repo.get_current("openai", "gpt-4o", date(2024, 5, 31))
    assert cur_mid is not None
    assert cur_mid.id == p1.id

    # 4. Exactly on second effective date -> p2
    cur2 = repo.get_current("openai", "gpt-4o", date(2024, 6, 1))
    assert cur2 is not None
    assert cur2.id == p2.id
    assert cur2.input_per_mtok_usd == Decimal("2.000000")

    # 5. After second effective date -> p2
    cur_future = repo.get_current("openai", "gpt-4o", date(2024, 12, 31))
    assert cur_future is not None
    assert cur_future.id == p2.id

    # 6. Datetime parameter support
    dt_param = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    cur_dt = repo.get_current("openai", "gpt-4o", dt_param)
    assert cur_dt is not None
    assert cur_dt.id == p2.id

    # 7. Non-existent provider or model -> None
    assert repo.get_current("anthropic", "gpt-4o", date(2024, 6, 1)) is None
    assert repo.get_current("openai", "unknown-model", date(2024, 6, 1)) is None
