import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.repositories.events import EventRepository
from app.repositories.prices import PriceRepository
from app.services.cost_calculator import CostCalculator
from app.services.events import EventService
from app.services.reports import ReportService


def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> str:
    """Validate X-API-Key header against settings.API_KEY."""
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthorized",
                "message": "Invalid or missing API key",
            },
        )
    return x_api_key


def get_event_service(
    session: Annotated[Session, Depends(get_session)],
) -> EventService:
    """Dependency provider for EventService."""
    event_repo = EventRepository(session)
    price_repo = PriceRepository(session)
    cost_calculator = CostCalculator()
    return EventService(
        event_repo=event_repo,
        price_repo=price_repo,
        cost_calculator=cost_calculator,
    )


def get_report_service(
    session: Annotated[Session, Depends(get_session)],
) -> ReportService:
    """Dependency provider for ReportService."""
    event_repo = EventRepository(session)
    return ReportService(event_repo=event_repo)
