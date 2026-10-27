import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.cost_calculator import UnknownModelPriceError

logger = logging.getLogger(__name__)


def format_error_payload(
    code: str,
    message: str,
    details: Any = None,
) -> dict[str, Any]:
    """Format unified JSON error structure."""
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details is not None:
        payload["details"] = details
    return payload


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions with unified error payload."""
    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code", "http_error"))
        message = str(exc.detail.get("message", "An error occurred"))
        details = exc.detail.get("details")
    else:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            code = "unauthorized"
        elif exc.status_code == status.HTTP_404_NOT_FOUND:
            code = "not_found"
        else:
            code = "http_error"
        message = str(exc.detail) if exc.detail else "An error occurred"
        details = None

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_payload(code=code, message=message, details=details),
        headers=exc.headers,
    )


async def unknown_model_price_handler(
    request: Request, exc: UnknownModelPriceError
) -> JSONResponse:
    """Handle domain error when model price is missing."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=format_error_payload(
            code="unknown_model_price",
            message=str(exc),
            details={"model": exc.model},
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors without leaking sensitive data."""
    details = []
    for err in exc.errors():
        loc = err.get("loc", ())
        if len(loc) > 1 and loc[0] in ("body", "query", "path", "header"):
            field = ".".join(str(part) for part in loc[1:])
        elif len(loc) > 0:
            field = ".".join(str(part) for part in loc)
        else:
            field = "body"

        details.append(
            {
                "field": field,
                "message": err.get("msg", "Invalid value"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=format_error_payload(
            code="validation_error",
            message="Request validation failed",
            details=details,
        ),
    )


async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Log the exception without request data and return a safe error response."""
    logger.error(
        "Unhandled server exception", exc_info=(type(exc), exc, exc.__traceback__)
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_payload(
            code="internal_error", message="Internal server error"
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all unified exception handlers on the FastAPI application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(UnknownModelPriceError, unknown_model_price_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
