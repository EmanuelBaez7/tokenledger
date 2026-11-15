"""Pure CSV/XLSX serialization with explicit spreadsheet-injection protection."""

import csv
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO, StringIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.worksheet import Worksheet

from dashboard.analytics import CostItems, daily_rows, detail_rows
from dashboard.snapshots import ReportSnapshot

EXCEL_NOTE = "Si ve celdas vacías, pulse Habilitar edición para calcular los totales"
HEADERS = (
    "Nombre",
    "Costo (USD)",
    "% del total",
    "Llamadas",
    "Costo por llamada (USD)",
    "Tokens entrada",
    "Tokens salida",
)
FIELDS = (
    "key",
    "total_cost_usd",
    "share_percent",
    "calls",
    "cost_per_call",
    "total_input_tokens",
    "total_output_tokens",
)
LABELS = {
    "feature": "Feature",
    "customer": "Cliente",
    "model": "Modelo",
    "day": "Fecha",
}
MONEY = '"$"#,##0.00000000'
RATE = '"$"#,##0.000000'


def safe_text(value: str) -> str:
    """Keep untrusted labels as inert text, including whitespace-prefixed payloads."""
    value = "".join(
        char
        for char in value
        if char in "\t\r\n"
        or (
            ord(char) >= 32
            and not 0xD800 <= ord(char) <= 0xDFFF
            and ord(char) not in {0xFFFE, 0xFFFF}
        )
    )
    candidate = value.lstrip()
    if value.startswith(("\t", "\r", "\n")) or candidate.startswith(
        ("=", "+", "-", "@", "\t")
    ):
        return "'" + value
    return value


def csv_bytes(rows: CostItems, dimension: str) -> bytes:
    """Export all selected detail rows, independently of the UI's row limit."""
    headers = (LABELS[dimension], *HEADERS[1:])
    fields = FIELDS
    if dimension == "day":
        headers += ("Media previa de 7 días (USD)", "Pico")
        fields += ("rolling_mean", "spike_label")
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(
            [
                safe_text(row[field])
                if field in {"key", "spike_label"}
                else ""
                if row.get(field) is None
                else format(row[field], "f")
                if isinstance(row[field], Decimal)
                else row[field]
                for field in fields
            ]
        )
    return buffer.getvalue().encode("utf-8-sig")


def _style_sheet(sheet: Worksheet) -> None:
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    for cell in sheet[1]:
        cell.font = Font(name="IBM Plex Sans", bold=True, color="0F172A")
        cell.fill = PatternFill("solid", fgColor="F1F5F9")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    sheet.row_dimensions[1].height = 32
    for column in range(1, sheet.max_column + 1):
        sheet.column_dimensions[get_column_letter(column)].width = (
            32 if column == 1 else 22
        )
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="IBM Plex Sans", size=11, color="0F172A")
            cell.alignment = Alignment(
                horizontal="left" if cell.column == 1 else "right",
                vertical="top",
                wrap_text=True,
            )


def _detail_sheet(book: Workbook, title: str, dimension: str, rows: CostItems) -> int:
    sheet = book.create_sheet(title)
    sheet.append([LABELS[dimension], *HEADERS[1:]])
    if dimension == "day":
        sheet.cell(1, 8, "Media previa de 7 días (USD)")
        sheet.cell(1, 9, "Pico")
    for item in rows:
        values = [
            safe_text(item["key"]),
            item["total_cost_usd"],
            item["share_percent"] / 100,
            item["calls"],
            item["cost_per_call"],
            item["total_input_tokens"],
            item["total_output_tokens"],
        ]
        if dimension == "day":
            values[0] = date.fromisoformat(item["key"])
            values.extend([item.get("rolling_mean"), item.get("spike_label")])
        sheet.append(values)
        if dimension == "day":
            sheet.cell(sheet.max_row, 1).number_format = "yyyy-mm-dd"
    footer = len(rows) + 2
    sheet.cell(footer, 1, "Total del periodo")
    for column in ("B", "D", "F", "G"):
        sheet[f"{column}{footer}"] = (
            f"=SUM({column}2:{column}{footer - 1})" if rows else "=SUM(0)"
        )
    sheet[f"C{footer}"] = f"=IF(B{footer}=0,0,1)"
    sheet[f"E{footer}"] = f"=IF(D{footer}=0,0,B{footer}/D{footer})"
    sheet.auto_filter.ref = (
        f"A1:{get_column_letter(sheet.max_column)}{max(1, footer - 1)}"
    )
    _style_sheet(sheet)
    if dimension != "day":
        for row in range(2, footer):
            sheet.cell(row, 1).font = Font(name="IBM Plex Mono", size=11)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            if cell.column in (2, 8):
                cell.number_format = MONEY
            elif cell.column == 3:
                cell.number_format = "0.0%"
            elif cell.column == 5:
                cell.number_format = RATE
            elif cell.column in (4, 6, 7):
                cell.number_format = "#,##0"
    for cell in sheet[footer]:
        cell.border = Border(
            top=Side(style="thin", color="64748B"),
            bottom=Side(style="double", color="64748B"),
        )
        cell.font = Font(name="IBM Plex Sans", bold=True, color="0F172A")
    return footer


def excel_bytes(report: ReportSnapshot, *, generated_at: datetime) -> bytes:
    """Serialize a full report; callers supply time to keep the function pure."""
    if generated_at.tzinfo is None:
        raise ValueError("Generation timestamp must include a timezone")
    if report.source not in {"api", "demo"}:
        raise ValueError("Invalid export source")
    book = Workbook()
    timestamp = generated_at.astimezone(UTC).replace(tzinfo=None)
    book.properties.created = timestamp
    book.properties.modified = timestamp
    summary = book.active
    summary.title = "Resumen"
    summary.append(["Indicador", "Valor"])
    footer = _detail_sheet(book, "Por feature", "feature", detail_rows(report.features))
    _detail_sheet(book, "Por customer", "customer", detail_rows(report.customers))
    _detail_sheet(book, "Por modelo", "model", detail_rows(report.models))
    _detail_sheet(book, "Tendencia diaria", "day", daily_rows(report.current_days))
    summary.append(["Gasto total", f"='Por feature'!B{footer}"])
    summary.append(["Llamadas", f"='Por feature'!D{footer}"])
    summary.append(["Costo medio por llamada", "=IF(B3=0,0,B2/B3)"])
    summary.append(
        ["Feature más cara", safe_text(report.metrics.top_feature or "Sin actividad")]
    )
    summary["A7"] = EXCEL_NOTE
    _style_sheet(summary)
    summary.column_dimensions["A"].width = 78
    summary.column_dimensions["B"].width = 26
    summary.row_dimensions[7].height = 36
    summary["B2"].number_format = MONEY
    summary["B3"].number_format = "#,##0"
    summary["B4"].number_format = RATE
    metadata = book.create_sheet("Metadatos")
    for pair in [
        ("Campo", "Valor"),
        ("Desde", report.period.start),
        ("Hasta", report.period.end),
        ("Generado en UTC", generated_at.astimezone(UTC).isoformat()),
        ("Fuente", report.source),
        ("Alcance", "Periodo completo, sin búsqueda"),
    ]:
        metadata.append(pair)
    _style_sheet(metadata)
    metadata.column_dimensions["B"].width = 42
    for key in ("B2", "B3"):
        metadata[key].number_format = "yyyy-mm-dd"
    book.calculation = CalcProperties(
        calcMode="auto", fullCalcOnLoad=True, forceFullCalc=True
    )
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()
