from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Price
from app.db.seed import seed_prices


def test_seed_prices_idempotency(db_session: Session) -> None:
    """Test that running seed_prices twice produces the exact same number of rows."""
    # Table should be initially empty due to fixture
    initial_count = db_session.scalar(select(func.count(Price.id)))
    assert initial_count == 0

    # First execution
    inserted_first = seed_prices(db_session)
    assert inserted_first > 0

    count_after_first = db_session.scalar(select(func.count(Price.id)))
    assert count_after_first == inserted_first

    # Second execution
    inserted_second = seed_prices(db_session)
    # on_conflict_do_nothing means 0 new rows inserted
    assert inserted_second == 0

    count_after_second = db_session.scalar(select(func.count(Price.id)))
    assert count_after_second == count_after_first

    # Verify that both providers exist
    providers = set(db_session.scalars(select(Price.provider)).all())
    assert "anthropic" in providers
    assert "openai" in providers

    # Verify rows count is at least 4 (2 models per provider)
    assert count_after_second >= 4
