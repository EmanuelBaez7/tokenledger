import hashlib
import json
import tomllib
from datetime import date
from decimal import Decimal
from pathlib import Path

from dashboard.analytics import Period, detail_rows
from dashboard.charts import distribution_chart, trend_chart
from dashboard.snapshots import load_report
from dashboard.theme import stylesheet


def test_charts_keep_exact_data_and_respect_comparison_and_theme() -> None:
    report = load_report(
        "demo", Period(date(2026, 4, 17), date(2026, 4, 30)), today=date(2026, 4, 30)
    )
    total = report.metrics.total_cost_usd
    off = trend_chart(report, compare=False).to_dict()
    on = trend_chart(report, compare=True).to_dict()
    for spec, labels in ((off, ["Actual"]), (on, ["Actual", "Periodo anterior"])):
        encodings = [layer["encoding"] for layer in spec["layer"]]
        spike = next(
            layer["mark"] for layer in spec["layer"] if layer["mark"]["type"] == "point"
        )
        assert spike.get("opacity") == 1
        direct_labels = [e["text"]["value"] for e in encodings if "text" in e]
        assert sorted(set(direct_labels) - {"Pico"}) == labels
        assert encodings[0]["x"]["axis"]["grid"] is False
        assert "oct" in encodings[0]["x"]["axis"]["labelExpr"]
        assert any(
            encoding["y"].get("axis", {}).get("gridOpacity") == 0.35
            for encoding in encodings
        )
    assert [x["field"] for x in off["layer"][0]["encoding"]["tooltip"]] == [
        "day_label",
        "label",
    ]
    assert on["layer"][0]["mark"]["strokeDash"] == [5, 4]
    assert on["data"]["values"][0]["day_label"] == "17 abr"
    assert on["data"]["values"][0]["previous_day"] == "3 abr"
    assert "labelColor" not in on["config"]["axis"]
    assert on["layer"][0]["encoding"]["color"] == {"value": "gray"}
    assert report.metrics.total_cost_usd == total
    assert all(isinstance(p.cost, Decimal) for p in report.current_days)
    chart = distribution_chart(detail_rows(report.features)).to_dict()
    assert chart["layer"][1]["mark"]["lineBreak"] == "\n"
    assert chart["layer"][1]["mark"]["font"] == "IBM Plex Mono"
    assert chart["layer"][2]["mark"]["font"] == "IBM Plex Sans"
    model_chart = distribution_chart(detail_rows(report.models)).to_dict()
    assert chart["height"] == {"step": 72}
    assert model_chart["height"] == {"step": 108}
    assert model_chart["autosize"] == {"type": "fit-x", "contains": "padding"}


def test_dashboard_styles_inherit_the_active_browser_color_scheme() -> None:
    css = stylesheet()
    assert ".stApp{" in css
    assert "--tl-surface:light-dark(#FFFFFF,#111C2E)" in css


def test_vendored_fonts_match_verified_files_and_static_config() -> None:
    root = Path(__file__).resolve().parents[2]
    font_dir = root / "dashboard/static/fonts"
    manifest = json.loads((font_dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["assets"]) == 9
    assert manifest["sans_latin1_missing"] == manifest["sans_pi_covers"] == "↑↓"
    for item in manifest["assets"]:
        content = (font_dir / item["file"]).read_bytes()
        assert content[:4] == b"wOF2"
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
        assert item["weight"] in {400, 500, 600}
        if item["subset"] == "latin1":
            assert item["digit_advance"] == 600
    assert "SIL OPEN FONT LICENSE" in (font_dir / "OFL.txt").read_text()
    config = tomllib.loads((root / ".streamlit/config.toml").read_text())
    assert config["server"]["enableStaticServing"] is True
    assert config["browser"]["gatherUsageStats"] is False
    assert len(config["theme"]["fontFaces"]) == 6
