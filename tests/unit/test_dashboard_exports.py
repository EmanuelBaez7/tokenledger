import csv
from datetime import UTC, date, datetime
from io import BytesIO, StringIO

import pytest
from openpyxl import load_workbook

from dashboard.analytics import Period, daily_rows, detail_rows, select_rows
from dashboard.exports import EXCEL_NOTE, csv_bytes, excel_bytes, safe_text
from dashboard.snapshots import load_report


@pytest.mark.parametrize(
    "label", ["=1+1", "+SUM(A1)", "-2+3", "@cmd", "\tformula", "  =1", "\n=1"]
)
def test_formula_prefixes_are_neutralized_in_both_exports(label: str) -> None:
    row = {
        "key": label,
        "total_cost_usd": "0.1",
        "calls": 1,
        "total_input_tokens": 2,
        "total_output_tokens": 1,
    }
    rows = detail_rows([row])
    data = list(csv.reader(StringIO(csv_bytes(rows, "feature").decode("utf-8-sig"))))
    assert data[1][0] == "'" + label
    report = load_report(
        "demo", Period(date(2026, 4, 17), date(2026, 4, 30)), today=date(2026, 4, 30)
    )
    report.features[0]["key"] = label
    book = load_workbook(
        BytesIO(excel_bytes(report, generated_at=datetime(2026, 4, 30, tzinfo=UTC)))
    )
    assert book["Por feature"]["A2"].data_type == "s"
    assert book["Por feature"]["A2"].value == "'" + label


def test_csv_has_bom_and_exports_all_matches_in_active_order() -> None:
    items = detail_rows(
        [
            {
                "key": f"feature-{n:03d}",
                "total_cost_usd": "0.1",
                "calls": 1,
                "total_input_tokens": 1,
                "total_output_tokens": 0,
            }
            for n in range(150)
        ]
    )
    rows = select_rows(items, "feature-", sort_by="key", descending=True)
    data = csv_bytes(rows, "feature")
    assert data.startswith(b"\xef\xbb\xbf")
    records = list(csv.reader(StringIO(data.decode("utf-8-sig"))))
    assert len(records) == 151
    assert records[1][0] == "feature-149" and records[-1][0] == "feature-000"
    assert records[1][1] == "0.1"
    assert items[0]["key"] == "feature-000"


def test_excel_has_required_sheets_live_formulas_formats_and_safe_metadata() -> None:
    report = load_report(
        "demo", Period(date(2026, 4, 17), date(2026, 4, 30)), today=date(2026, 4, 30)
    )
    data = excel_bytes(report, generated_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC))
    book = load_workbook(BytesIO(data), data_only=False)
    assert book.sheetnames == [
        "Resumen",
        "Por feature",
        "Por customer",
        "Por modelo",
        "Tendencia diaria",
        "Metadatos",
    ]
    sheet = book["Por feature"]
    last = sheet.max_row
    assert sheet[f"B{last}"].value == f"=SUM(B2:B{last - 1})"
    assert sheet[f"E{last}"].value == f"=IF(D{last}=0,0,B{last}/D{last})"
    assert sheet[f"B{last}"].border.top.style == "thin"
    assert sheet[f"B{last}"].border.bottom.style == "double"
    assert sheet["B2"].data_type == "n" and sheet["C2"].number_format == "0.0%"
    assert sheet["E2"].number_format.endswith("0.000000")
    assert all(s.freeze_panes == "A2" for s in book)
    assert sheet.column_dimensions["A"].width >= 24
    assert book["Resumen"]["B2"].value == f"='Por feature'!B{last}"
    assert book["Resumen"]["B4"].value == "=IF(B3=0,0,B2/B3)"
    assert book["Resumen"]["A7"].value == EXCEL_NOTE
    trend = book["Tendencia diaria"]
    assert trend["A2"].value.date() == report.period.start
    assert trend["A2"].number_format == "yyyy-mm-dd"
    csv_day = csv_bytes(daily_rows(report.current_days), "day").decode("utf-8-sig")
    assert list(csv.reader(StringIO(csv_day)))[1][0] == report.period.start.isoformat()
    metadata = dict(book["Metadatos"].iter_rows(min_row=2, values_only=True))
    assert metadata["Fuente"] == "demo"
    assert metadata["Generado en UTC"] == "2026-04-30T12:00:00+00:00"
    assert book.calculation.fullCalcOnLoad
    assert "API_KEY" not in str(metadata)


def test_empty_workbook_uses_non_circular_zero_totals() -> None:
    report = load_report(
        "demo",
        Period(date(2026, 4, 17), date(2026, 4, 30)),
        today=date(2026, 4, 30),
        events=[],
    )
    book = load_workbook(
        BytesIO(excel_bytes(report, generated_at=datetime(2026, 4, 30, tzinfo=UTC)))
    )
    assert book["Por feature"]["B2"].value == "=SUM(0)"
    assert book["Por feature"]["E2"].value == "=IF(D2=0,0,B2/D2)"


def test_safe_numeric_looking_identifiers_remain_text_without_mutation() -> None:
    assert safe_text("00123") == "00123"
    assert safe_text("customer á") == "customer á"


def test_export_removes_xml_control_characters_before_formula_detection() -> None:
    assert safe_text("\x00=1+1") == "'=1+1"
    assert safe_text("customer\x01name") == "customername"


def test_export_rejects_naive_generation_timestamps() -> None:
    report = load_report(
        "demo", Period(date(2026, 4, 17), date(2026, 4, 30)), today=date(2026, 4, 30)
    )
    with pytest.raises(ValueError, match="timezone"):
        excel_bytes(report, generated_at=datetime(2026, 4, 30))
