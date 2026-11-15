"""Generate the versioned, database-free dashboard demo fixture once.

Usage: uv run python -m scripts.generate_dashboard_demo
"""

import json
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import yaml

from app.services.cost_calculator import CostCalculator, ModelPrice
from scripts.seed_demo import SEED, WINDOW_DAYS, generate_demo_events

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "dashboard/demo_data/events.json"
WINDOW_COUNTS = (100, 89, 79, 70, 62)  # Latest to earliest, ~12–13% growth.
HISTORICAL_SAMPLE_OFFSET = 519  # Keeps the same spending leaders across windows.
DAILY_DEVIATIONS = (0, 7, -13, 22, -19, 12, -6, -21, 19, -11, 10, -3, 21, -18)


def build_events() -> list[dict[str, object]]:
    prices = yaml.load(
        (ROOT / "prices.seed.yaml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    rates = {
        (p["provider"], p["model"]): ModelPrice(
            Decimal(p["input_per_mtok_usd"]), Decimal(p["output_per_mtok_usd"])
        )
        for p in prices
    }
    calculator = CostCalculator()
    anchor = datetime(2026, 4, 30, 18, tzinfo=UTC)
    result = []
    for window, count in enumerate(WINDOW_COUNTS):
        generated = generate_demo_events(
            random.Random(SEED + window),
            anchor - timedelta(days=WINDOW_DAYS * window),
            include_spike=window == 0,
        )
        sample_offset = HISTORICAL_SAMPLE_OFFSET if window else 100
        priced_events: list[tuple[Decimal, dict[str, object]]] = []
        for event in random.Random(SEED + sample_offset + window).sample(
            generated, count
        ):
            cost = calculator.calculate(
                provider=event.provider,
                model=event.model,
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                price=rates[event.provider, event.model],
            )
            priced_events.append(
                (
                    cost,
                    {
                        "days_ago": (anchor.date() - event.created_at.date()).days,
                        "provider": event.provider,
                        "model": event.model,
                        "feature": event.feature,
                        "customer": event.customer,
                        "input_tokens": event.input_tokens,
                        "output_tokens": event.output_tokens,
                        "cost_usd": f"{cost:.8f}",
                    },
                )
            )
        if window:
            # Vary daily spending by redistributing whole calls within the window.
            deviations = list(DAILY_DEVIATIONS)
            random.Random(SEED + window).shuffle(deviations)
            average = sum((cost for cost, _ in priced_events), Decimal(0)) / WINDOW_DAYS
            # The first window has no preceding week to anchor its spike baseline.
            targets = (
                [average] * WINDOW_DAYS
                if window == len(WINDOW_COUNTS) - 1
                else [average * (100 + deviation) / 100 for deviation in deviations]
            )
            day_totals = [Decimal(0)] * WINDOW_DAYS
            for cost, event in sorted(priced_events, key=lambda pair: -pair[0]):
                day = min(range(WINDOW_DAYS), key=lambda i: day_totals[i] - targets[i])
                day_totals[day] += cost
                event["days_ago"] = WINDOW_DAYS * window + day
        result.extend(event for _, event in priced_events)
    return sorted(result, key=lambda e: e["days_ago"])


def main() -> None:
    DESTINATION.parent.mkdir(exist_ok=True)
    events = build_events()
    lines = ",\n".join(json.dumps(event, ensure_ascii=False) for event in events)
    DESTINATION.write_text(
        '{"schema_version": 1, "events": [\n' + lines + "\n]}\n", encoding="utf-8"
    )
    print(
        f"Generated {len(events)} synthetic dashboard events without database access."
    )


if __name__ == "__main__":
    main()
