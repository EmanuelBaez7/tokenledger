from datetime import UTC, datetime, timedelta
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.data import (
    ApiConnectionError,
    ApiError,
    MissingConfigurationError,
    UnauthorizedError,
    calculate_totals,
    fetch_costs,
    prepare_chart_data,
    prepare_table_data,
)

# Page configuration
st.set_page_config(
    page_title="TokenLedger — Dashboard",
    page_icon="📊",
    layout="wide",
)


def render_horizontal_bar_chart(
    chart_data: list[dict[str, Any]], key_name: str
) -> None:
    """Render horizontal bar chart with labels and accent color for the highest bar."""
    if not chart_data:
        st.info("Sin gasto en este rango.")
        return

    df = pd.DataFrame(chart_data)
    keys_order = df["key"].tolist()

    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            y=alt.Y(
                "key:N",
                sort=keys_order,
                title=None,
                axis=alt.Axis(labelLimit=200, labelFontSize=12),
            ),
            x=alt.X(
                "total_cost_usd:Q",
                title="Costo total (USD)",
                axis=alt.Axis(format="$.4f", titleFontSize=12),
            ),
            color=alt.condition(
                alt.datum.is_top,
                alt.value("#F59E0B"),  # Accent color (highest cost)
                alt.value("#2563EB"),  # Primary color
            ),
            tooltip=[
                alt.Tooltip("key:N", title=key_name),
                alt.Tooltip("total_cost_label:N", title="Costo total"),
                alt.Tooltip("calls:Q", title="Llamadas"),
            ],
        )
    )

    text = (
        alt.Chart(df)
        .mark_text(
            align="left",
            baseline="middle",
            dx=6,
            color="#0F172A",
            fontWeight="bold",
            fontSize=11,
        )
        .encode(
            y=alt.Y("key:N", sort=keys_order),
            x=alt.X("total_cost_usd:Q"),
            text=alt.Text("total_cost_label:N"),
        )
    )

    chart = (bars + text).properties(height=max(180, len(chart_data) * 44))
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    st.title("TokenLedger")
    st.caption("Observabilidad y control de costos de llamadas a LLMs")

    # 1. Filtros (rango de fechas, por defecto los últimos 14 días)
    today = datetime.now(UTC).date()
    default_from = today - timedelta(days=13)
    default_to = today

    st.markdown("### Filtros")
    date_selection = st.date_input(
        "Rango de fechas",
        value=(default_from, default_to),
        max_value=today,
        help="Selecciona el rango de fechas para consultar costos y uso de tokens.",
    )

    if isinstance(date_selection, tuple) and len(date_selection) == 2:
        start_date, end_date = date_selection
    elif isinstance(date_selection, tuple) and len(date_selection) == 1:
        start_date = end_date = date_selection[0]
    elif isinstance(date_selection, list) and len(date_selection) == 2:
        start_date, end_date = date_selection[0], date_selection[1]
    elif isinstance(date_selection, list) and len(date_selection) == 1:
        start_date = end_date = date_selection[0]
    else:
        start_date, end_date = default_from, default_to

    if start_date > end_date:
        st.error(
            "La fecha inicial ('desde') no puede ser posterior "
            "a la fecha final ('hasta')."
        )
        st.stop()

    # 2. Obtención de datos y manejo de estados
    try:
        with st.spinner("Consultando costos y eventos..."):
            feature_items = fetch_costs(
                group_by="feature",
                date_from=start_date,
                date_to=end_date,
            )
            customer_items = fetch_costs(
                group_by="customer",
                date_from=start_date,
                date_to=end_date,
            )
    except MissingConfigurationError:
        st.error("Configuración requerida: falta la variable de entorno `API_KEY`.")
        st.info(
            "Define `API_KEY` en tu archivo `.env` o en tus "
            "variables de entorno para continuar."
        )
        st.stop()
    except UnauthorizedError:
        st.error("La API rechazó las credenciales. Revisa `API_KEY`.")
        st.stop()
    except ApiConnectionError:
        st.error("No se pudo conectar con la API.")
        if st.button("Reintentar"):
            st.rerun()
        st.stop()
    except ApiError as exc:
        st.error(f"Error devuelto por la API: {exc}")
        if st.button("Reintentar"):
            st.rerun()
        st.stop()

    # Estado sin datos
    has_range_data = bool(feature_items or customer_items)
    if not has_range_data:
        # Verificar si hay eventos en general sin filtro de fechas
        try:
            global_events = fetch_costs(group_by="feature")
        except Exception:
            global_events = []

        if not global_events:
            st.info(
                "Aún no hay eventos. Ejecuta `python scripts/seed_demo.py` "
                "o envía uno con el SDK."
            )
            st.stop()
        else:
            st.info("Sin gasto en este rango.")

    # 3. Métricas principales
    metrics = calculate_totals(feature_items)
    st.markdown("### Métricas generales")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Gasto total",
            value=f"${metrics.total_cost_usd:.4f}",
        )
    with col2:
        st.metric(
            label="Número de llamadas",
            value=f"{metrics.total_calls:,}",
        )
    with col3:
        avg_cost_str = (
            f"${metrics.average_cost_per_call:.6f}" if metrics.total_calls > 0 else "—"
        )
        st.metric(
            label="Costo medio por llamada",
            value=avg_cost_str,
        )
    with col4:
        st.metric(
            label="Feature más cara",
            value=metrics.top_feature or "—",
        )

    st.divider()

    # 4. Gráficos y tablas en dos columnas
    col_feat, col_cust = st.columns(2)

    with col_feat:
        st.subheader("Gasto por Feature")
        chart_features = prepare_chart_data(feature_items)
        render_horizontal_bar_chart(chart_features, key_name="Feature")

        st.markdown("##### Totales por Feature")
        table_features = prepare_table_data(feature_items)
        if table_features:
            df_feat = pd.DataFrame(table_features).rename(
                columns={
                    "key": "Feature",
                    "total_cost_usd": "Costo (USD)",
                    "calls": "Llamadas",
                    "total_input_tokens": "Tokens entrada",
                    "total_output_tokens": "Tokens salida",
                }
            )
            st.dataframe(df_feat, use_container_width=True, hide_index=True)

    with col_cust:
        st.subheader("Gasto por Customer")
        chart_customers = prepare_chart_data(customer_items)
        render_horizontal_bar_chart(chart_customers, key_name="Customer")

        st.markdown("##### Totales por Customer")
        table_customers = prepare_table_data(customer_items)
        if table_customers:
            df_cust = pd.DataFrame(table_customers).rename(
                columns={
                    "key": "Customer",
                    "total_cost_usd": "Costo (USD)",
                    "calls": "Llamadas",
                    "total_input_tokens": "Tokens entrada",
                    "total_output_tokens": "Tokens salida",
                }
            )
            st.dataframe(df_cust, use_container_width=True, hide_index=True)

    # 5. Pie de página
    st.divider()
    st.caption(
        "TokenLedger v0.1 · [GitHub Repository](https://github.com/EmanuelBaez7/tokenledger)"
    )


if __name__ == "__main__":
    main()
