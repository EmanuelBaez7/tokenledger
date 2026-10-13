import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["anthropic", "openai"]
    model: str = Field(min_length=1, max_length=128)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    feature: str = Field(min_length=1, max_length=64)
    customer: str | None = Field(default=None, max_length=128)
    status: Literal["ok", "error"] = "ok"

    @field_validator("feature")
    @classmethod
    def validate_feature(cls, v: str) -> str:
        if v != v.strip():
            raise ValueError("feature cannot contain leading or trailing whitespace")
        return v


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: str
    latency_ms: int | None = None
    feature: str
    customer: str | None = None
    status: str

    @field_validator("cost_usd", mode="before")
    @classmethod
    def serialize_cost_usd(cls, v: Any) -> str:
        if isinstance(v, Decimal):
            return f"{v:.8f}"
        return str(v)


class CostReportItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    total_cost_usd: str
    total_input_tokens: int
    total_output_tokens: int
    calls: int

    @field_validator("total_cost_usd", mode="before")
    @classmethod
    def serialize_total_cost_usd(cls, v: Any) -> str:
        if isinstance(v, Decimal):
            return f"{v:.8f}"
        return str(v)
