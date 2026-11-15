"""Presentation-only HTML. Every dynamic string crosses an explicit escape boundary."""

from decimal import Decimal
from html import escape

from dashboard.analytics import ZERO, CostItems, leading_item, percent_change
from dashboard.exports import HEADERS, LABELS
from dashboard.snapshots import ReportSnapshot


def text(value: object) -> str:
    return escape(str(value), quote=True)


def money(value: Decimal, places: int = 4) -> str:
    return f"${value:,.{places}f}"


def help_html(message: str) -> str:
    return f'<p class="tl-help">{text(message)}</p>'


def _delta(
    current: Decimal, previous: Decimal | None, *, financial: bool = True
) -> str:
    if previous is None:
        return '<span class="tl-muted">Historial insuficiente</span>'
    change = percent_change(current, previous)
    if change is None:
        return '<span class="tl-muted">Sin base comparable</span>'
    direction = "↑" if change > 0 else "↓" if change < 0 else ""
    sign = "+" if change > 0 else "−" if change < 0 else ""
    css = "tl-up" if change > 0 else "tl-down" if change < 0 else "tl-muted"
    if not financial:
        css = "tl-muted"
    return f'<span class="{css}">{direction} {sign}{abs(change):.1f}%</span>'


def kpi_html(report: ReportSnapshot, *, compare: bool) -> str:
    current = report.metrics
    previous = report.previous_metrics if compare else None
    spend = money(current.total_cost_usd)
    average = money(current.average_cost_per_call, 6) if current.total_calls else "—"
    spend_context = "Periodo seleccionado"
    if compare:
        spend_context = _delta(
            current.total_cost_usd, previous.total_cost_usd if previous else None
        )
        if previous is not None:
            spend_context += f" · Antes {money(previous.total_cost_usd)}"

    def leader_card(title: str, items: CostItems) -> tuple[str, str, str, str]:
        leader = leading_item(items)
        label = text(leader["key"]) if leader else "Sin actividad"
        cost = Decimal(leader["total_cost_usd"]) if leader else ZERO
        share = cost / current.total_cost_usd * 100 if current.total_cost_usd else ZERO
        return (
            title,
            label,
            f"{money(cost)} · {share:.1f}% del gasto",
            "tl-id tl-feature",
        )

    cards = [
        ("Gasto total", text(spend), spend_context, "tl-number"),
        (
            "Llamadas",
            f"{current.total_calls:,}",
            _delta(
                Decimal(current.total_calls),
                Decimal(previous.total_calls) if previous else None,
                financial=False,
            )
            if compare
            else "Periodo seleccionado",
            "tl-number",
        ),
        (
            "Costo por llamada",
            text(average),
            _delta(
                current.average_cost_per_call,
                previous.average_cost_per_call
                if previous and previous.total_calls
                else None,
            )
            if compare
            else "Promedio ponderado",
            "tl-number",
        ),
        leader_card("Feature más cara", report.features),
        leader_card("Cliente más caro", report.customers),
    ]
    contents = "".join(
        f'<article class="tl-kpi"><h2>{text(label)}</h2>'
        f'<div class="tl-kpi-value"><span class="{css}">{value}</span></div>'
        f'<div class="tl-kpi-context">{context}</div></article>'
        for label, value, context, css in cards
    )
    return (
        '<section class="tl-kpis" aria-label="Indicadores del periodo" '
        f'data-total-cost="{current.total_cost_usd:.8f}">{contents}</section>'
    )


def ledger_html(rows: CostItems, all_rows: CostItems, dimension: str) -> str:
    headers = (LABELS[dimension], *HEADERS[1:])
    fields = (
        "key",
        "total_cost_usd",
        "share_percent",
        "calls",
        "cost_per_call",
        "total_input_tokens",
        "total_output_tokens",
    )
    if dimension == "day":
        headers += ("Media de 7 días (USD)", "Pico")
        fields += ("rolling_mean", "spike_label")

    def cell(row: dict, field: str, *, is_total: bool = False) -> str:
        value = row.get(field)
        if field in {"key", "spike_label"}:
            if field == "key" and dimension == "day" and not is_total:
                value = row["date_label"]
            css = "tl-id" if field == "key" and dimension != "day" else ""
            return f'<td class="{css}">{text(value)}</td>'
        if value is None:
            label = "—"
        elif field in {"total_cost_usd", "rolling_mean"}:
            label = money(value, 8)
        elif field == "cost_per_call":
            label = money(value, 6) if row["calls"] else "—"
        elif field == "share_percent":
            if is_total:
                return f'<td class="tl-num">{value:.1f}%</td>'
            width = max(ZERO, min(Decimal("100"), value))
            return (
                '<td class="tl-num"><span class="tl-share" aria-hidden="true">'
                f'<span style="width:{width:.5f}%"></span></span>'
                f"<span>{value:.1f}%</span></td>"
            )
        else:
            label = f"{value:,}"
        return f'<td class="tl-num">{text(label)}</td>'

    body = "".join(
        "<tr>" + "".join(cell(row, f) for f in fields) + "</tr>" for row in rows[:100]
    )
    total = sum((r["total_cost_usd"] for r in all_rows), ZERO)
    calls = sum(r["calls"] for r in all_rows)
    hidden = len(rows) != len(all_rows) or len(rows) > 100
    footer_label = "Total del periodo" + (
        " (incluye filas no visibles)" if hidden else ""
    )
    footer = {
        "key": footer_label,
        "total_cost_usd": total,
        "share_percent": Decimal("100") if total else ZERO,
        "calls": calls,
        "cost_per_call": total / calls if calls else ZERO,
        "total_input_tokens": sum(r["total_input_tokens"] for r in all_rows),
        "total_output_tokens": sum(r["total_output_tokens"] for r in all_rows),
        "rolling_mean": None,
        "spike_label": "—",
    }
    footer_cells = "".join(cell(footer, f, is_total=True) for f in fields)
    notice = (
        f'<p class="tl-table-note">Mostrando 100 de {len(rows):,}</p>'
        if len(rows) > 100
        else '<p class="tl-table-note">Sin coincidencias. '
        "Cambia la búsqueda para ver filas.</p>"
        if not rows
        else ""
    )
    header = "".join(f'<th scope="col">{text(h)}</th>' for h in headers)
    note = (
        '<p class="tl-table-note">Se marcan hasta tres días con mayor exceso. '
        "El gasto debe superar 1,5 veces la media positiva de los siete días "
        "anteriores y el exceso debe ser al menos el 5% del gasto del periodo.</p>"
        if dimension == "day"
        else ""
    )
    return (
        f'{notice}<div class="tl-table-scroll" role="region" '
        f'aria-label="Detalle de {text(LABELS[dimension])}" tabindex="0">'
        f'<table class="tl-ledger" data-total-cost="{total:.8f}">'
        f'<caption class="tl-sr">Detalle por {text(LABELS[dimension])}</caption>'
        f"<thead><tr>{header}</tr></thead><tbody>{body}</tbody>"
        f"<tfoot><tr>{footer_cells}</tr></tfoot></table></div>{note}"
    )


def message_html(title: str, message: str, *, error: bool = False) -> str:
    role = "alert" if error else "status"
    return (
        f'<section class="tl-message" role="{role}">'
        f"<h2>{text(title)}</h2><p>{text(message)}</p></section>"
    )


def skeleton_html() -> str:
    return (
        '<div role="status"><p>Consultando costos…</p>'
        '<div class="tl-skeleton-grid" aria-hidden="true">'
        + ('<div class="tl-skeleton"></div>' * 5)
        + '</div><div class="tl-skeleton tl-skeleton-chart" '
        'aria-hidden="true"></div></div>'
    )
