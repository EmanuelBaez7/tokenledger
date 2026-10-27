from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError

from app.api.deps import get_report_service, verify_api_key
from app.api.schemas import CostReportItem
from app.services.reports import InvalidDateRangeError, ReportService

router = APIRouter(prefix="/costs", tags=["costs"])
MIN_REPORT_DATE = date(2000, 1, 1)
MAX_REPORT_DATE = date(2100, 12, 31)


@router.get(
    "",
    response_model=list[CostReportItem],
)
def get_costs(
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[str, Depends(verify_api_key)],
    group_by: Annotated[Literal["feature", "customer", "model"], Query()],
    date_from: Annotated[
        date | None, Query(alias="from", ge=MIN_REPORT_DATE, le=MAX_REPORT_DATE)
    ] = None,
    date_to: Annotated[
        date | None, Query(alias="to", ge=MIN_REPORT_DATE, le=MAX_REPORT_DATE)
    ] = None,
) -> list[CostReportItem]:
    """Retrieve aggregated costs grouped by dimension with optional date range."""
    try:
        results = service.get_costs(
            group_by=group_by,
            date_from=date_from,
            date_to=date_to,
        )
    except InvalidDateRangeError as exc:
        raise RequestValidationError(
            [
                {
                    "loc": ("query", "from"),
                    "msg": str(exc),
                    "type": "value_error",
                }
            ]
        ) from exc

    return [CostReportItem.model_validate(item) for item in results]
