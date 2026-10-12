from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import Price
from app.db.session import SessionLocal

DEFAULT_SEED_FILE = Path(__file__).resolve().parents[2] / "prices.seed.yaml"


def load_seed_prices(yaml_path: Path | str = DEFAULT_SEED_FILE) -> list[dict[str, Any]]:
    """Load and parse the seed YAML file."""
    path = Path(yaml_path)
    if not path.is_file():
        raise FileNotFoundError(f"Seed file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        raise ValueError("Seed YAML must contain a list of price entries")

    return data


def seed_prices(
    session: Session,
    yaml_path: Path | str = DEFAULT_SEED_FILE,
) -> int:
    """Seed prices table idempotently from a YAML file.

    Inserts missing prices into the database. If a row with the same
    (provider, model, effective_from) already exists, it is ignored without failure.

    Returns the number of newly inserted rows.
    """
    prices_data = load_seed_prices(yaml_path)
    inserted_count = 0

    for item in prices_data:
        raw_effective_from = item["effective_from"]
        if isinstance(raw_effective_from, str):
            effective_from_date = date.fromisoformat(raw_effective_from)
        elif isinstance(raw_effective_from, date):
            effective_from_date = raw_effective_from
        else:
            raise ValueError(f"Invalid effective_from format: {raw_effective_from}")

        stmt = (
            pg_insert(Price)
            .values(
                provider=str(item["provider"]),
                model=str(item["model"]),
                input_per_mtok_usd=Decimal(str(item["input_per_mtok_usd"])),
                output_per_mtok_usd=Decimal(str(item["output_per_mtok_usd"])),
                effective_from=effective_from_date,
            )
            .on_conflict_do_nothing(
                index_elements=["provider", "model", "effective_from"]
            )
            .returning(Price.id)
        )
        result = session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            inserted_count += 1

    session.commit()
    return inserted_count


def main() -> None:
    """CLI entry point to execute the seed."""
    with SessionLocal() as session:
        inserted = seed_prices(session)
        print(f"Prices seeded successfully. Inserted rows: {inserted}")


if __name__ == "__main__":
    main()
