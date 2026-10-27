from datetime import UTC, datetime
from decimal import Decimal

from app.db.models import Event
from app.repositories.events import EventRepository
from app.repositories.prices import PriceRepository
from app.services.cost_calculator import CostCalculator, UnknownModelPriceError

MAX_EVENT_COST_USD = Decimal("999999.99999999")


class CostOutOfRangeError(ValueError):
    """Raised when a calculated event cost exceeds the storage range."""

    def __init__(self) -> None:
        super().__init__(
            f"Calculated cost must be between 0 and {MAX_EVENT_COST_USD} USD"
        )


class EventService:
    """Domain service for calculating and persisting LLM usage events."""

    def __init__(
        self,
        event_repo: EventRepository,
        price_repo: PriceRepository,
        cost_calculator: CostCalculator | None = None,
    ) -> None:
        self.event_repo = event_repo
        self.price_repo = price_repo
        self.cost_calculator = cost_calculator or CostCalculator()

    def create_event(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        feature: str,
        customer: str | None = None,
        latency_ms: int | None = None,
        status: str = "ok",
    ) -> Event:
        """Find current price for model, calculate cost in USD, and persist event."""
        today_utc = datetime.now(UTC).date()
        price = self.price_repo.get_current(
            provider=provider,
            model=model,
            at_date=today_utc,
        )
        if price is None:
            raise UnknownModelPriceError(model=model, provider=provider)

        cost_usd = self.cost_calculator.calculate(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            price=price,
        )
        if not Decimal("0") <= cost_usd <= MAX_EVENT_COST_USD:
            raise CostOutOfRangeError()

        event = Event(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            feature=feature,
            customer=customer,
            status=status,
        )

        saved_event = self.event_repo.add(event)
        self.event_repo.session.commit()
        return saved_event
