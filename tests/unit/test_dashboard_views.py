from dataclasses import replace
from datetime import date

from dashboard.analytics import Period, detail_rows, select_rows
from dashboard.snapshots import load_report
from dashboard.theme import PALETTES, stylesheet
from dashboard.views import kpi_html, ledger_html


def test_spend_kpi_contains_comparison_and_customer_card_matches_leader() -> None:
    report = load_report(
        "demo", Period(date(2026, 4, 17), date(2026, 4, 30)), today=date(2026, 4, 30)
    )
    with_comparison = kpi_html(report, compare=True)
    spend_card = with_comparison.split("</article>", 1)[0]
    assert "Gasto total" in spend_card and "Antes $" in spend_card
    assert ("↑ +" in spend_card or "↓ −" in spend_card) and "%" in spend_card
    assert "Variación de gasto" not in with_comparison
    customer_card = with_comparison.split("<h2>Cliente más caro</h2>", 1)[1]
    assert "globex" in customer_card and "% del gasto" in customer_card
    assert "Antes $" not in kpi_html(report, compare=False)


def test_kpi_and_ledger_escape_every_untrusted_label() -> None:
    report = load_report(
        "demo", Period(date(2026, 4, 17), date(2026, 4, 30)), today=date(2026, 4, 30)
    )
    malicious = '"><img src=x onerror=alert(1)>'
    report = replace(report, customers=[dict(report.customers[0], key=malicious)])
    output = kpi_html(report, compare=True)
    assert "<img" not in output and "&lt;img" in output
    items = detail_rows(
        [
            {
                "key": malicious,
                "total_cost_usd": "0.1",
                "calls": 1,
                "total_input_tokens": 1,
                "total_output_tokens": 0,
            }
        ]
    )
    output = ledger_html(items, items, "feature")
    assert "<img" not in output and "&lt;img" in output
    assert 'data-total-cost="0.10000000"' in output


def test_ledger_caps_rendering_but_keeps_full_period_totals() -> None:
    items = detail_rows(
        [
            {
                "key": f"item-{n}",
                "total_cost_usd": "0.1",
                "calls": 1,
                "total_input_tokens": 1,
                "total_output_tokens": 0,
            }
            for n in range(150)
        ]
    )
    selected = select_rows(items, sort_by="key")
    output = ledger_html(selected, items, "feature")
    assert output.count("<tr>") == 102
    assert "Mostrando 100 de 150" in output
    assert 'data-total-cost="15.00000000"' in output
    filtered = ledger_html(selected[:2], items, "feature")
    assert 'data-total-cost="15.00000000"' in filtered
    assert "incluye filas no visibles" in filtered.lower()


def test_control_borders_and_focus_have_sufficient_contrast() -> None:
    def luminance(color: str) -> float:
        channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
            for v in channels
        ]
        return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    for palette in PALETTES.values():
        for token, threshold in (
            ("control", 3),
            ("brand", 3),
            ("text", 4.5),
            ("muted", 4.5),
            ("accent", 4.5),
            ("up", 4.5),
            ("down", 4.5),
        ):
            for surface in ("background", "surface"):
                a, b = sorted((luminance(palette[token]), luminance(palette[surface])))
                assert (b + 0.05) / (a + 0.05) >= threshold
    css = stylesheet()
    assert "font-variant-numeric: tabular-nums" in css
    assert "border-bottom: 3px double" in css
    assert "768px" not in css
    assert "<script" not in css
