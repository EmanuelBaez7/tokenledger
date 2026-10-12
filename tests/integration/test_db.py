import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Event, Price
from app.db.session import get_session


def test_insert_and_read_event(db_session: Session) -> None:
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=150,
        output_tokens=75,
        cost_usd=Decimal("0.00157500"),
        latency_ms=120,
        feature="chat",
        customer="cust-1",
    )
    db_session.add(event)
    db_session.commit()

    saved = db_session.scalar(select(Event).where(Event.id == event.id))
    assert saved is not None
    assert isinstance(saved.id, uuid.UUID)
    assert saved.created_at is not None
    assert saved.created_at.tzinfo is not None
    assert saved.provider == "anthropic"
    assert saved.model == "claude-3-5-sonnet"
    assert saved.input_tokens == 150
    assert saved.output_tokens == 75
    assert saved.cost_usd == Decimal("0.00157500")
    assert saved.latency_ms == 120
    assert saved.feature == "chat"
    assert saved.customer == "cust-1"
    assert saved.status == "ok"


def test_insert_and_read_price(db_session: Session) -> None:
    price = Price(
        provider="openai",
        model="gpt-4o",
        input_per_mtok_usd=Decimal("2.500000"),
        output_per_mtok_usd=Decimal("10.000000"),
        effective_from=date(2024, 1, 1),
    )
    db_session.add(price)
    db_session.commit()

    saved = db_session.scalar(select(Price).where(Price.id == price.id))
    assert saved is not None
    assert isinstance(saved.id, int)
    assert saved.provider == "openai"
    assert saved.model == "gpt-4o"
    assert saved.input_per_mtok_usd == Decimal("2.500000")
    assert saved.output_per_mtok_usd == Decimal("10.000000")
    assert saved.effective_from == date(2024, 1, 1)


def test_event_rejects_negative_input_tokens(db_session: Session) -> None:
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=-1,
        output_tokens=50,
        cost_usd=Decimal("0.00100000"),
        feature="chat",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_event_rejects_negative_output_tokens(db_session: Session) -> None:
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=100,
        output_tokens=-5,
        cost_usd=Decimal("0.00100000"),
        feature="chat",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_event_rejects_invalid_status(db_session: Session) -> None:
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.00100000"),
        feature="chat",
        status="invalid_status",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_event_rejects_invalid_provider(db_session: Session) -> None:
    event = Event(
        provider="invalid_provider",
        model="claude-3-5-sonnet",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.00100000"),
        feature="chat",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_event_rejects_negative_cost(db_session: Session) -> None:
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("-0.00010000"),
        feature="chat",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_event_rejects_negative_latency(db_session: Session) -> None:
    event = Event(
        provider="anthropic",
        model="claude-3-5-sonnet",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.00100000"),
        latency_ms=-10,
        feature="chat",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_price_rejects_negative_input_price(db_session: Session) -> None:
    price = Price(
        provider="openai",
        model="gpt-4o",
        input_per_mtok_usd=Decimal("-1.000000"),
        output_per_mtok_usd=Decimal("10.000000"),
        effective_from=date(2024, 1, 1),
    )
    db_session.add(price)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_price_rejects_negative_output_price(db_session: Session) -> None:
    price = Price(
        provider="openai",
        model="gpt-4o",
        input_per_mtok_usd=Decimal("2.500000"),
        output_per_mtok_usd=Decimal("-1.000000"),
        effective_from=date(2024, 1, 1),
    )
    db_session.add(price)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_price_rejects_duplicate_provider_model_effective_from(
    db_session: Session,
) -> None:
    p1 = Price(
        provider="openai",
        model="gpt-4o",
        input_per_mtok_usd=Decimal("2.500000"),
        output_per_mtok_usd=Decimal("10.000000"),
        effective_from=date(2024, 1, 1),
    )
    db_session.add(p1)
    db_session.commit()

    p2 = Price(
        provider="openai",
        model="gpt-4o",
        input_per_mtok_usd=Decimal("3.000000"),
        output_per_mtok_usd=Decimal("12.000000"),
        effective_from=date(2024, 1, 1),
    )
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_get_session_yields_session() -> None:
    generator = get_session()
    session = next(generator)
    assert isinstance(session, Session)
    # Complete generator to close session
    with pytest.raises(StopIteration):
        next(generator)
