from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.v1 import costs_router, events_router

app = FastAPI(title="TokenLedger API")

register_error_handlers(app)
app.include_router(events_router, prefix="/v1")
app.include_router(costs_router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
