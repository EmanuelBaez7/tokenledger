from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import Event
from app.repositories.events import EventRepository


def add_daily_events(session: Session) -> None:
    session.add_all(
        [
            Event(
                provider="openai",
                model="synthetic",
                feature="chat",
                input_tokens=10,
                output_tokens=5,
                cost_usd=Decimal(cost),
                created_at=timestamp,
            )
            for timestamp, cost in [
                (datetime(2026, 4, 2, 0, 1, tzinfo=UTC), "1.00000000"),
                (datetime(2026, 4, 1, 23, 59, tzinfo=UTC), "9.00000000"),
                (
                    datetime(2026, 4, 2, 1, 0, tzinfo=timezone(timedelta(hours=2))),
                    "2.00000000",
                ),
            ]
        ]
    )
    session.commit()


def test_daily_repository_groups_in_utc_and_sorts_by_date(db_session: Session) -> None:
    add_daily_events(db_session)
    db_session.execute(text("SET LOCAL TIME ZONE 'Pacific/Honolulu'"))
    rows = EventRepository(db_session).aggregate("day")
    assert [(r.key, r.total_cost_usd, r.calls) for r in rows] == [
        ("2026-04-01", Decimal("11.00000000"), 2),
        ("2026-04-02", Decimal("1.00000000"), 1),
    ]
    assert rows[0].total_input_tokens == 20
    assert rows[0].total_output_tokens == 10


def test_daily_repository_date_filter_is_inclusive(db_session: Session) -> None:
    add_daily_events(db_session)
    rows = EventRepository(db_session).aggregate(
        "day", date(2026, 4, 1), date(2026, 4, 1)
    )
    assert len(rows) == 1
    assert rows[0].key == "2026-04-01"
    assert rows[0].total_cost_usd == Decimal("11.00000000")
