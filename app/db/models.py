import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Identity,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 8), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    feature: Mapped[str] = mapped_column(Text, nullable=False)
    customer: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    status: Mapped[str] = mapped_column(
        Text,
        server_default=text("'ok'"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "provider IN ('anthropic', 'openai')",
            name="ck_events_provider",
        ),
        CheckConstraint(
            "status IN ('ok', 'error')",
            name="ck_events_status",
        ),
        CheckConstraint(
            "input_tokens >= 0",
            name="ck_events_input_tokens",
        ),
        CheckConstraint(
            "output_tokens >= 0",
            name="ck_events_output_tokens",
        ),
        CheckConstraint(
            "cost_usd >= 0",
            name="ck_events_cost_usd",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_events_latency_ms",
        ),
        Index("ix_events_feature_created", "feature", "created_at"),
        Index("ix_events_customer_created", "customer", "created_at"),
        Index("ix_events_created", "created_at"),
    )


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(),
        primary_key=True,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    input_per_mtok_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 6),
        nullable=False,
    )
    output_per_mtok_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 6),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "provider IN ('anthropic', 'openai')",
            name="ck_prices_provider",
        ),
        CheckConstraint(
            "input_per_mtok_usd >= 0",
            name="ck_prices_input_per_mtok_usd",
        ),
        CheckConstraint(
            "output_per_mtok_usd >= 0",
            name="ck_prices_output_per_mtok_usd",
        ),
        UniqueConstraint(
            "provider",
            "model",
            "effective_from",
            name="uq_prices_provider_model_effective_from",
        ),
        Index(
            "ix_prices_current",
            "provider",
            "model",
            text("effective_from DESC"),
        ),
    )
