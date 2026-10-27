"""Demo data seed script for TokenLedger.

Writes ~300 synthetic events directly into the database using the session,
PriceRepository, CostCalculator, and EventRepository — not the API — so that
created_at can be set to historical dates.

Usage:
    uv run python -m scripts.seed_demo [--yes] [--allow-remote]

Flags:
    --yes            Skip confirmation prompt and insert immediately.
    --allow-remote   Allow execution against a non-local DATABASE_URL.
"""

from __future__ import annotations

import argparse
import random
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEED = 42
TARGET_EVENT_COUNT = 300
WINDOW_DAYS = 14

FEATURES = ["resumen", "traduccion", "chat", "clasificacion"]
CUSTOMERS = ["acme", "globex", "initech", "umbrella", "hooli"]

# Models from prices.seed.yaml — both providers
MODELS_CONFIG: list[dict[str, str]] = [
    {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
    {"provider": "anthropic", "model": "claude-3-haiku-20240307"},
    {"provider": "openai", "model": "gpt-4o"},
    {"provider": "openai", "model": "gpt-4o-mini"},
]

# Error event rate (~3%)
ERROR_RATE = 0.03

# ---------------------------------------------------------------------------
# Story weights — these create the narrative:
#   • "traduccion" is the most expensive feature (heavy output tokens)
#   • "globex" is the top-spending customer (higher weight + spike day)
# ---------------------------------------------------------------------------

FEATURE_WEIGHTS = {
    "resumen": 20,
    "traduccion": 35,  # most calls + heaviest output
    "chat": 25,
    "clasificacion": 20,
}

CUSTOMER_WEIGHTS = {
    "acme": 15,
    "globex": 35,  # top customer
    "initech": 20,
    "umbrella": 15,
    "hooli": 10,
    None: 5,  # events without customer
}

# Token ranges by feature — traduccion has many output tokens
TOKEN_RANGES: dict[str, dict[str, tuple[int, int]]] = {
    "resumen": {"input": (500, 3_000), "output": (100, 600)},
    "traduccion": {"input": (1_000, 5_000), "output": (800, 4_500)},  # heavy output
    "chat": {"input": (200, 2_000), "output": (100, 1_000)},
    "clasificacion": {"input": (300, 1_500), "output": (20, 200)},
}

# Day index (0 = oldest, 13 = today) for globex spike
GLOBEX_SPIKE_DAY = 10  # ~4 days before "today"
GLOBEX_SPIKE_MULTIPLIER = 4  # extra events for globex on spike day


# ---------------------------------------------------------------------------
# Pure generation function (no DB access)
# ---------------------------------------------------------------------------


@dataclass
class RawEvent:
    """Raw event data before writing to the database."""

    provider: str
    model: str
    feature: str
    customer: str | None
    input_tokens: int
    output_tokens: int
    status: str
    latency_ms: int | None
    created_at: datetime  # UTC, historical


def generate_demo_events(rng: random.Random, now: datetime) -> list[RawEvent]:
    """Generate synthetic demo events without touching the database.

    Args:
        rng: Seeded Random instance for reproducibility.
        now: Reference UTC datetime; no event will be in the future.

    Returns:
        List of RawEvent dataclasses ready to be persisted.
    """
    events: list[RawEvent] = []

    feature_population = list(FEATURE_WEIGHTS.keys())
    feature_weights_vals = list(FEATURE_WEIGHTS.values())

    customer_population = list(CUSTOMER_WEIGHTS.keys())
    customer_weights_vals = list(CUSTOMER_WEIGHTS.values())

    # Build per-day event counts with a slightly growing trend
    # and a spike on GLOBEX_SPIKE_DAY for globex
    base_per_day = TARGET_EVENT_COUNT // WINDOW_DAYS  # ~21 base events/day

    for day_idx in range(WINDOW_DAYS):
        # Slightly increasing trend: scale from 0.8x to 1.2x
        trend_factor = 0.8 + 0.4 * day_idx / (WINDOW_DAYS - 1)
        day_count = max(1, int(base_per_day * trend_factor))

        # Compute the date for this day (oldest first)
        days_ago = WINDOW_DAYS - 1 - day_idx
        day_start = (now - timedelta(days=days_ago)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start.replace(hour=23, minute=59, second=59)
        # Never exceed 'now'
        if day_end > now:
            day_end = now

        for _ in range(day_count):
            feature = rng.choices(
                feature_population, weights=feature_weights_vals, k=1
            )[0]
            customer = rng.choices(
                customer_population, weights=customer_weights_vals, k=1
            )[0]
            model_cfg = rng.choice(MODELS_CONFIG)

            is_error = rng.random() < ERROR_RATE

            if is_error:
                input_tokens = 0
                output_tokens = 0
                status = "error"
                latency_ms = None
            else:
                tok_range = TOKEN_RANGES[feature]
                input_tokens = rng.randint(*tok_range["input"])
                output_tokens = rng.randint(*tok_range["output"])
                status = "ok"
                latency_ms = rng.randint(100, 3_000)

            # Random timestamp within the day (never in the future)
            day_range_seconds = int((day_end - day_start).total_seconds())
            if day_range_seconds <= 0:
                ts = day_start
            else:
                ts = day_start + timedelta(seconds=rng.randint(0, day_range_seconds))

            events.append(
                RawEvent(
                    provider=model_cfg["provider"],
                    model=model_cfg["model"],
                    feature=feature,
                    customer=customer,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    status=status,
                    latency_ms=latency_ms,
                    created_at=ts,
                )
            )

        # Add globex spike events on spike day
        if day_idx == GLOBEX_SPIKE_DAY:
            spike_model = MODELS_CONFIG[0]  # sonnet (most expensive)
            for _ in range(int(base_per_day * GLOBEX_SPIKE_MULTIPLIER)):
                tok_range = TOKEN_RANGES["traduccion"]
                input_tokens = rng.randint(*tok_range["input"])
                output_tokens = rng.randint(*tok_range["output"])
                day_range_seconds = int((day_end - day_start).total_seconds())
                ts = (
                    day_start + timedelta(seconds=rng.randint(0, day_range_seconds))
                    if day_range_seconds > 0
                    else day_start
                )
                events.append(
                    RawEvent(
                        provider=spike_model["provider"],
                        model=spike_model["model"],
                        feature="traduccion",
                        customer="globex",
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        status="ok",
                        latency_ms=rng.randint(200, 2_000),
                        created_at=ts,
                    )
                )

    return events


# ---------------------------------------------------------------------------
# Database insertion helpers
# ---------------------------------------------------------------------------


def _check_host_is_local(database_url: str, allow_remote: bool) -> None:
    """Abort if DATABASE_URL points to a non-local host and --allow-remote is absent."""
    try:
        parsed = urllib.parse.urlparse(database_url)
        host = (parsed.hostname or "").lower()
    except Exception:
        host = ""

    local_hosts = {"localhost", "127.0.0.1", "db"}
    if host not in local_hosts and not allow_remote:
        print(
            f"ERROR: DATABASE_URL apunta a '{host}', que no parece ser local.\n"
            "Pasa --allow-remote si realmente quieres insertar en una base remota.",
            file=sys.stderr,
        )
        sys.exit(1)


@dataclass
class SeedSummary:
    """Exact costs for this insertion, independent of existing database events."""

    inserted: int
    total_cost: Decimal
    feature_costs: dict[str, Decimal]
    customer_costs: dict[str, Decimal]


def _insert_events(session: Session, raw_events: list[RawEvent]) -> SeedSummary:
    """Insert events and collect exact costs for the final summary."""
    from app.db.models import Event
    from app.repositories.events import EventRepository
    from app.repositories.prices import PriceRepository
    from app.services.cost_calculator import CostCalculator

    price_repo = PriceRepository(session)
    event_repo = EventRepository(session)
    calculator = CostCalculator()

    total_cost = Decimal("0")
    inserted = 0
    feature_costs: dict[str, Decimal] = {}
    customer_costs: dict[str, Decimal] = {}

    for raw in raw_events:
        if raw.status == "error":
            cost_usd = Decimal("0")
        else:
            price = price_repo.get_current(raw.provider, raw.model, raw.created_at)
            if price is None:
                print(
                    f"ERROR: No hay precio para {raw.provider}/{raw.model} "
                    f"en {raw.created_at.date()}.\n"
                    "Ejecuta primero: uv run python -m app.db.seed",
                    file=sys.stderr,
                )
                sys.exit(1)
            cost_usd = calculator.calculate(
                provider=raw.provider,
                model=raw.model,
                input_tokens=raw.input_tokens,
                output_tokens=raw.output_tokens,
                price=price,
            )

        event = Event(
            created_at=raw.created_at,
            provider=raw.provider,
            model=raw.model,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            cost_usd=cost_usd,
            latency_ms=raw.latency_ms,
            feature=raw.feature,
            customer=raw.customer,
            status=raw.status,
        )
        event_repo.add(event)
        feature_costs[raw.feature] = (
            feature_costs.get(raw.feature, Decimal("0")) + cost_usd
        )
        customer = raw.customer or "unassigned"
        customer_costs[customer] = customer_costs.get(customer, Decimal("0")) + cost_usd
        total_cost += cost_usd
        inserted += 1

    session.commit()
    return SeedSummary(inserted, total_cost, feature_costs, customer_costs)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _print_summary(
    raw_events: list[RawEvent],
    summary: SeedSummary,
) -> None:
    """Print a human-readable summary after insertion."""
    feature_counts: dict[str, int] = {}
    customer_counts: dict[str, int] = {}
    for ev in raw_events:
        feature_counts[ev.feature] = feature_counts.get(ev.feature, 0) + 1
        key = ev.customer or "unassigned"
        customer_counts[key] = customer_counts.get(key, 0) + 1

    top_feature_by_cost = max(summary.feature_costs, key=summary.feature_costs.get)
    top_customer_by_cost = max(summary.customer_costs, key=summary.customer_costs.get)

    top_feature = max(feature_counts, key=lambda k: feature_counts[k])
    top_customer = max(customer_counts, key=lambda k: customer_counts[k])

    print("\n✅ Seed de demo completado")
    print(f"   Eventos insertados : {summary.inserted}")
    print(f"   Gasto total        : ${summary.total_cost:.8f}")
    print(f"   Top feature por costo : {top_feature_by_cost}")
    print(f"   Top customer por costo: {top_customer_by_cost}")
    print(f"   Top feature por llamadas : {top_feature}")
    print(f"   Top customer por llamadas: {top_customer}")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Seed demo events into TokenLedger DB."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow execution against a non-local DATABASE_URL.",
    )
    args = parser.parse_args(argv)

    # Import here so the module is importable without a running DB
    from app.core.config import get_settings
    from app.db.session import SessionLocal

    settings = get_settings()
    _check_host_is_local(settings.DATABASE_URL, allow_remote=args.allow_remote)

    rng = random.Random(SEED)
    now = datetime.now(UTC)
    raw_events = generate_demo_events(rng, now)

    print(f"Se van a insertar {len(raw_events)} eventos de demostración.")
    if not args.yes:
        answer = input("¿Continuar? [s/N]: ").strip().lower()
        if answer not in {"s", "si", "sí", "y", "yes"}:
            print("Abortado.")
            sys.exit(0)

    with SessionLocal() as session:
        summary = _insert_events(session, raw_events)

    _print_summary(raw_events, summary)


if __name__ == "__main__":
    main()
