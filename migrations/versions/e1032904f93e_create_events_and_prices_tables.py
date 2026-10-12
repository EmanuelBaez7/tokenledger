"""create events and prices tables

Revision ID: e1032904f93e
Revises:
Create Date: 2026-10-09 18:20:00.327603

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1032904f93e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "events",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=14, scale=8), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("customer", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'ok'"), nullable=False),
        sa.CheckConstraint(
            "provider IN ('anthropic', 'openai')", name="ck_events_provider"
        ),
        sa.CheckConstraint("status IN ('ok', 'error')", name="ck_events_status"),
        sa.CheckConstraint("cost_usd >= 0", name="ck_events_cost_usd"),
        sa.CheckConstraint("input_tokens >= 0", name="ck_events_input_tokens"),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0", name="ck_events_latency_ms"
        ),
        sa.CheckConstraint("output_tokens >= 0", name="ck_events_output_tokens"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_created", "events", ["created_at"], unique=False)
    op.create_index(
        "ix_events_customer_created",
        "events",
        ["customer", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_events_feature_created",
        "events",
        ["feature", "created_at"],
        unique=False,
    )
    op.create_table(
        "prices",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "input_per_mtok_usd", sa.Numeric(precision=14, scale=6), nullable=False
        ),
        sa.Column(
            "output_per_mtok_usd", sa.Numeric(precision=14, scale=6), nullable=False
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.CheckConstraint(
            "provider IN ('anthropic', 'openai')", name="ck_prices_provider"
        ),
        sa.CheckConstraint(
            "input_per_mtok_usd >= 0", name="ck_prices_input_per_mtok_usd"
        ),
        sa.CheckConstraint(
            "output_per_mtok_usd >= 0", name="ck_prices_output_per_mtok_usd"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "model",
            "effective_from",
            name="uq_prices_provider_model_effective_from",
        ),
    )
    op.create_index(
        "ix_prices_current",
        "prices",
        ["provider", "model", sa.literal_column("effective_from DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_prices_current", table_name="prices")
    op.drop_table("prices")
    op.drop_index("ix_events_feature_created", table_name="events")
    op.drop_index("ix_events_customer_created", table_name="events")
    op.drop_index("ix_events_created", table_name="events")
    op.drop_table("events")
