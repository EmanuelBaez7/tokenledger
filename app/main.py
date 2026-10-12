from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import events_router
from app.services.cost_calculator import UnknownModelPriceError

app = FastAPI(title="TokenLedger API")


@app.exception_handler(StarletteHTTPException)
def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if isinstance(exc.detail, dict):
        content = {
            "detail": exc.detail.get("message", str(exc.detail)),
            **exc.detail,
        }
    else:
        content = {
            "detail": exc.detail,
            "message": exc.detail,
            "code": "error",
        }
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


@app.exception_handler(UnknownModelPriceError)
def unknown_model_price_handler(
    request: Request, exc: UnknownModelPriceError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "code": "unknown_model_price",
            "message": str(exc),
            "model": exc.model,
            "detail": str(exc),
        },
    )


app.include_router(events_router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
