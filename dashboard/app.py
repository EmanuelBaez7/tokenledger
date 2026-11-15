"""TokenLedger's single-screen cost dashboard."""

import os
from datetime import UTC, datetime, timedelta

import streamlit as st

from dashboard.analytics import CostItems, Period, daily_rows, detail_rows, select_rows
from dashboard.charts import distribution_chart, trend_chart
from dashboard.data import DashboardError
from dashboard.exports import EXCEL_NOTE, csv_bytes, excel_bytes
from dashboard.formatting import short_range
from dashboard.loading import clear_report_cache, load_cached_report
from dashboard.snapshots import ReportSnapshot, Source, SourceConfig
from dashboard.theme import stylesheet
from dashboard.views import (
    help_html,
    kpi_html,
    ledger_html,
    message_html,
    skeleton_html,
    text,
)

st.set_page_config(
    page_title="TokenLedger", layout="wide", initial_sidebar_state="auto"
)
DIMENSIONS = ("feature", "customer", "model", "day")
TABS = ("Por feature", "Por customer", "Por modelo", "Tendencia diaria")
SORT_OPTIONS = {
    "Costo": "total_cost_usd",
    "Nombre / fecha": "key",
    "% del total": "share_percent",
    "Llamadas": "calls",
    "Costo por llamada": "cost_per_call",
    "Tokens entrada": "total_input_tokens",
    "Tokens salida": "total_output_tokens",
}


def _help(message: str) -> None:
    st.markdown(help_html(message), unsafe_allow_html=True)


def _filters(config: SourceConfig) -> tuple[Source, Period, bool]:
    today = datetime.now(UTC).date()
    if st.session_state.get("tl-source") not in config.options:
        st.session_state["tl-source"] = config.selected
    with st.sidebar:
        st.header("Filtros")
        with st.container(key="tl-filters", border=False):
            source = st.selectbox(
                "Fuente de datos",
                config.options,
                format_func=lambda value: "Demo" if value == "demo" else "API",
                disabled=config.locked,
                key="tl-source",
            )
            preset = st.selectbox(
                "Periodo",
                ("7 días", "14 días", "30 días", "Personalizado"),
                index=1,
                key="tl-preset",
            )
            custom = ()
            if preset == "Personalizado":
                custom = st.date_input(
                    "Rango personalizado",
                    value=(today - timedelta(days=13), today),
                    min_value=datetime(2000, 1, 1).date(),
                    max_value=today,
                    format="DD/MM/YYYY",
                    key="tl-custom",
                )
            compare = st.toggle(
                "Comparar con el periodo anterior", value=True, key="tl-compare"
            )
            applied = st.button("Aplicar", width="stretch")
        if config.locked:
            _help(
                "Demo fijada por el entorno."
                if os.getenv("DASHBOARD_DATA_SOURCE") == "demo"
                else "Configura API_BASE_URL y API_KEY para usar la API."
            )
    if preset == "Personalizado":
        if not isinstance(custom, (tuple, list)) or len(custom) != 2:
            raise ValueError("Selecciona fecha inicial y final y pulsa Aplicar.")
        period = Period(custom[0], custom[1])
    else:
        period = Period(today - timedelta(days=int(preset.split()[0]) - 1), today)
    if applied or "_tl_filters" not in st.session_state:
        st.session_state["_tl_filters"] = (source, period, compare)
    selected, period, compare = st.session_state["_tl_filters"]
    if selected not in config.options:
        selected = config.selected
        st.session_state["_tl_filters"] = (selected, period, compare)
    return selected, period, compare


def _tables(report: ReportSnapshot) -> dict[str, CostItems]:
    return {
        "feature": detail_rows(report.features),
        "customer": detail_rows(report.customers),
        "model": detail_rows(report.models),
        "day": daily_rows(report.current_days),
    }


def _selection(rows: CostItems, dimension: str) -> CostItems:
    default = "Nombre / fecha" if dimension == "day" else "Costo"
    order = st.session_state.get(
        f"tl-order-{dimension}", "Ascendente" if dimension == "day" else "Descendente"
    )
    sort = st.session_state.get(f"tl-sort-{dimension}", default)
    return select_rows(
        rows,
        st.session_state.get(f"tl-search-{dimension}", ""),
        SORT_OPTIONS[sort],
        order == "Descendente",
    )


def _export(report: ReportSnapshot, tables: dict[str, CostItems]) -> None:
    with st.popover("Exportar", width="stretch"):
        _help(
            "Excel: periodo completo. CSV: todas las coincidencias "
            "de búsqueda y orden activo."
        )
        st.download_button(
            "Exportar Excel",
            excel_bytes(report, generated_at=datetime.now(UTC)),
            file_name="tokenledger.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            on_click="ignore",
            width="stretch",
        )
        _help(EXCEL_NOTE)
        for dimension, label in zip(DIMENSIONS, TABS, strict=True):
            st.download_button(
                f"Exportar CSV · {label.lower()}",
                csv_bytes(_selection(tables[dimension], dimension), dimension),
                file_name=f"tokenledger-{dimension}.csv",
                mime="text/csv",
                on_click="ignore",
                width="stretch",
            )


def _details(tables: dict[str, CostItems]) -> None:
    st.header("Detalle")
    for tab, dimension in zip(st.tabs(TABS), DIMENSIONS, strict=True):
        with tab:
            left, middle, right = st.columns([2, 2, 1])
            with left:
                st.text_input(
                    "Buscar",
                    key=f"tl-search-{dimension}",
                    placeholder="Nombre o identificador",
                )
            with middle:
                st.selectbox(
                    "Ordenar por",
                    list(SORT_OPTIONS),
                    index=1 if dimension == "day" else 0,
                    key=f"tl-sort-{dimension}",
                )
            with right:
                st.selectbox(
                    "Dirección",
                    ("Descendente", "Ascendente"),
                    index=1 if dimension == "day" else 0,
                    key=f"tl-order-{dimension}",
                )
            selected = _selection(tables[dimension], dimension)
            st.markdown(
                ledger_html(selected, tables[dimension], dimension),
                unsafe_allow_html=True,
            )


def _empty(report: ReportSnapshot) -> None:
    if report.has_events:
        title = "Sin gasto en este rango"
        message = (
            "No hay eventos en las fechas elegidas. Amplía el periodo "
            "o selecciona 14 días y pulsa Aplicar."
        )
    elif report.source == "api":
        title = "Aún no hay eventos"
        message = (
            "Aún no hay eventos. Ejecuta uv run python -m scripts.seed_demo "
            "o envía uno con el SDK. Después pulsa Reintentar."
        )
    else:
        title = "Los datos de demo están vacíos"
        message = "Restaura el archivo de demostración versionado y pulsa Reintentar."
    st.markdown(message_html(title, message), unsafe_allow_html=True)
    st.button("Reintentar", on_click=clear_report_cache)


def main() -> None:
    st.markdown(stylesheet(), unsafe_allow_html=True)
    try:
        config = SourceConfig.from_environment(os.environ)
        source, period, compare = _filters(config)
    except (DashboardError, ValueError) as exc:
        st.title("TokenLedger")
        st.markdown(
            message_html("Revisa los filtros", str(exc), error=True),
            unsafe_allow_html=True,
        )
        st.button("Reintentar", on_click=clear_report_cache)
        return
    with st.container(key="tl-shell"):
        header, export = st.columns([4, 1])
        with header:
            st.title("TokenLedger")
            _help(
                f"{short_range(period.start, period.end)} "
                f"· {period.days} días"
                + (
                    " · Hoy es parcial"
                    if period.end == datetime.now(UTC).date()
                    else ""
                )
                + (" · Fuente: API" if source == "api" else "")
            )
            if compare:
                previous = period.previous
                _help(
                    f"Anterior: {short_range(previous.start, previous.end)}"
                    if previous.start.year >= 2000
                    else "Historial insuficiente para comparar el periodo anterior."
                )
        if source == "demo":
            st.markdown(
                '<div class="tl-demo" role="note">'
                "Datos sintéticos de demostración</div>",
                unsafe_allow_html=True,
            )
        placeholder = st.empty()
        placeholder.markdown(skeleton_html(), unsafe_allow_html=True)
        try:
            report = load_cached_report(
                source, period, today=datetime.now(UTC).date(), config=config
            )
        except DashboardError as exc:
            placeholder.empty()
            message = (
                str(exc).replace(config.api_key, "***") if config.api_key else str(exc)
            )
            st.markdown(
                message_html("No se pudieron cargar los datos", message, error=True),
                unsafe_allow_html=True,
            )
            st.button("Reintentar", on_click=clear_report_cache)
            return
        placeholder.empty()
        if report.metrics.total_calls == 0:
            _empty(report)
            return
        tables = _tables(report)
        with export:
            _export(report, tables)
        st.markdown(kpi_html(report, compare=compare), unsafe_allow_html=True)
        st.header("Tendencia diaria")
        st.altair_chart(
            trend_chart(report, compare=compare),
            width="stretch",
            # Streamlit's native defaults use body text instead of low-contrast gray.
            theme=None,
            alt=(
                "Costo diario. "
                + (
                    "La línea discontinua representa el periodo anterior. "
                    if compare and report.previous_metrics is not None
                    else ""
                )
                + "Los triángulos indican picos. "
                "Tabla equivalente en Tendencia diaria."
            ),
        )
        for column, dimension, label in zip(
            st.columns(3),
            DIMENSIONS[:3],
            ("Gasto por feature", "Gasto por cliente", "Gasto por modelo"),
            strict=True,
        ):
            with column:
                st.header(label)
                st.altair_chart(
                    distribution_chart(tables[dimension]),
                    width="stretch",
                    theme="streamlit",
                    alt=(
                        f"{label}: nombres, costos y participación. "
                        "Tabla equivalente en Detalle."
                    ),
                )
        _details(tables)
        observations = "".join(f"<p>{text(note)}</p>" for note in report.observations)
        st.markdown(
            '<section class="tl-observations"><h2>Observaciones</h2>'
            + observations
            + "</section>",
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
