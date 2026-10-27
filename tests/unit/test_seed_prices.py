from decimal import Decimal
from pathlib import Path

from app.db.seed import load_seed_prices


def test_seed_prices_preserve_decimal_text(tmp_path: Path) -> None:
    seed_file = tmp_path / "prices.yaml"
    seed_file.write_text(
        "- input_per_mtok_usd: 0.1\n  output_per_mtok_usd: 2.50\n",
        encoding="utf-8",
    )
    item = load_seed_prices(seed_file)[0]
    assert isinstance(item["input_per_mtok_usd"], str)
    assert isinstance(item["output_per_mtok_usd"], str)
    assert Decimal(item["input_per_mtok_usd"]).as_tuple() == Decimal("0.1").as_tuple()
    assert Decimal(item["output_per_mtok_usd"]).as_tuple() == Decimal("2.50").as_tuple()


def test_official_seed_has_no_float_prices() -> None:
    for item in load_seed_prices():
        for field in ("input_per_mtok_usd", "output_per_mtok_usd"):
            assert isinstance(item[field], str)
