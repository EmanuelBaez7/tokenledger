from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_event_service, verify_api_key
from app.api.schemas import EventCreate, EventResponse
from app.services.events import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=EventResponse,
)
def create_event(
    payload: EventCreate,
    service: Annotated[EventService, Depends(get_event_service)],
    _: Annotated[str, Depends(verify_api_key)],
) -> EventResponse:
    """Ingest a new LLM usage event, calculate its cost, and persist it."""
    event = service.create_event(
        provider=payload.provider,
        model=payload.model,
        input_tokens=payload.input_tokens,
        output_tokens=payload.output_tokens,
        feature=payload.feature,
        customer=payload.customer,
        latency_ms=payload.latency_ms,
        status=payload.status,
    )
    return EventResponse.model_validate(event)
