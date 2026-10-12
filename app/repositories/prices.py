from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Price


class PriceRepository:
    """Repository for retrieving LLM pricing rates."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_current(
        self,
        provider: str,
        model: str,
        at_date: date | datetime,
    ) -> Price | None:
        """Get the most recent effective price on or before at_date."""
        target_date = at_date.date() if isinstance(at_date, datetime) else at_date

        stmt = (
            select(Price)
            .where(
                Price.provider == provider,
                Price.model == model,
                Price.effective_from <= target_date,
            )
            .order_by(Price.effective_from.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()
