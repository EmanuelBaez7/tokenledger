"""Altair charts; the only presentation boundary that converts money to float."""

import json
import textwrap
from decimal import Decimal

import altair as alt

from dashboard.analytics import ZERO, CostItems
from dashboard.formatting import MONTHS_ES, short_date
from dashboard.snapshots import ReportSnapshot


def trend_chart(report: ReportSnapshot, *, compare: bool) -> alt.LayerChart:
    show_previous = compare and report.previous_metrics is not None
    values = []
    for index, point in enumerate(report.current_days):
        value = {
            "day": point.day.isoformat(),
            "day_label": short_date(point.day),
            "cost": float(point.cost),
            "label": f"${point.cost:,.8f}",
            "is_spike": point.is_spike,
            "last": index == len(report.current_days) - 1,
        }
        if show_previous:
            prior = report.previous_days[index]
            value.update(
                previous_day=short_date(prior.day),
                previous_cost=float(prior.cost),
                previous_label=f"${prior.cost:,.8f}",
            )
        values.append(value)
    tooltips = [
        alt.Tooltip("day_label:N", title="Fecha"),
        alt.Tooltip("label:N", title="Costo"),
    ]
    if show_previous:
        tooltips += [
            alt.Tooltip("previous_day:N", title="Fecha anterior"),
            alt.Tooltip("previous_label:N", title="Costo anterior"),
        ]
    base = alt.Chart(alt.Data(values=values)).encode(
        x=alt.X(
            "day:T",
            title=None,
            scale=alt.Scale(type="utc", range=[0, alt.ExprRef(expr="width - 108")]),
            axis=alt.Axis(
                grid=False,
                labelExpr=(
                    "utcdate(datum.value) + ' ' + "
                    f"{json.dumps(MONTHS_ES)}[utcmonth(datum.value)]"
                ),
                tickCount=6,
            ),
        ),
        tooltip=tooltips,
    )
    current = base.mark_line(strokeWidth=2.5).encode(
        color=alt.value("blue"),
        y=alt.Y(
            "cost:Q",
            title="Costo diario (USD)",
            scale=alt.Scale(zero=True),
            axis=alt.Axis(format="$,.2f", tickCount=5, grid=True, gridOpacity=0.35),
        ),
    )
    layers = []
    if show_previous:
        layers.append(
            base.mark_line(strokeDash=[5, 4], strokeWidth=1.5).encode(
                y="previous_cost:Q", color=alt.value("gray")
            )
        )
    peaks = base.transform_filter(alt.datum.is_spike)
    markers = peaks.mark_point(
        filled=True, opacity=1, size=90, shape="triangle-up"
    ).encode(y="cost:Q", color=alt.value("orange"))
    labels = peaks.mark_text(dy=-14, fontSize=14).encode(
        y="cost:Q", text=alt.value("Pico"), color=alt.value("gray")
    )
    end = base.transform_filter(alt.datum.last)
    current_above = (
        not show_previous
        or report.current_days[-1].cost >= report.previous_days[-1].cost
    )
    endpoint_labels = [
        end.mark_text(
            align="left",
            dx=6,
            dy=-7 if current_above else 7,
            fontSize=13,
        ).encode(y="cost:Q", text=alt.value("Actual"), color=alt.value("blue"))
    ]
    if show_previous:
        endpoint_labels.append(
            end.mark_text(
                align="left",
                dx=6,
                dy=7 if current_above else -7,
                fontSize=13,
            ).encode(
                y="previous_cost:Q",
                text=alt.value("Periodo anterior"),
                color=alt.value("gray"),
            )
        )
    return (
        alt.layer(*layers, current, markers, labels, *endpoint_labels)
        .properties(height=240)
        .configure_view(stroke=None)
        .configure_axis(
            labelFontSize=13, titleFontSize=14, titleFontWeight=500, domain=False
        )
    )


def distribution_chart(items: CostItems) -> alt.LayerChart:
    rows = sorted(items, key=lambda r: (-Decimal(r["total_cost_usd"]), r["key"]))
    total = sum((Decimal(r["total_cost_usd"]) for r in rows), ZERO)
    denominator = total or Decimal("1")
    values = [
        {
            "rank": index,
            "key": row["key"],
            "key_lines": "\n".join(textwrap.wrap(row["key"], width=16)),
            "cost": float(Decimal(row["total_cost_usd"])),
            "label": (
                f"${Decimal(row['total_cost_usd']):,.4f} · "
                f"{Decimal(row['total_cost_usd']) / denominator * 100:.1f}%"
            ),
            "bar_color": "orange" if index == 0 else "blue",
        }
        for index, row in enumerate(rows)
    ]
    max_lines = max((v["key_lines"].count("\n") + 1 for v in values), default=1)
    base = alt.Chart(alt.Data(values=values)).encode(
        y=alt.Y("rank:O", sort=list(range(len(values))), axis=None),
        tooltip=[
            alt.Tooltip("key:N", title="Nombre"),
            alt.Tooltip("label:N", title="Costo y participación"),
        ],
    )
    bars = base.mark_bar(size=8, cornerRadiusEnd=2).encode(
        x=alt.X("cost:Q", scale=alt.Scale(zero=True), axis=None, stack=None),
        color=alt.Color(
            "bar_color:N",
            legend=None,
            scale=alt.Scale(domain=["orange", "blue"], range=["orange", "blue"]),
        ),
    )
    names = base.mark_text(
        align="left",
        baseline="bottom",
        dy=-12 - (max_lines - 1) * 18,
        font="IBM Plex Mono",
        fontSize=14,
        lineHeight=18,
        lineBreak="\n",
    ).encode(x=alt.value(0), text=alt.Text("key_lines:N"), color=alt.value("gray"))
    amounts = base.mark_text(
        align="left",
        baseline="top",
        dy=10,
        font="IBM Plex Sans",
        fontSize=14,
    ).encode(x=alt.value(0), text="label:N", color=alt.value("gray"))
    return alt.layer(bars, names, amounts).properties(
        height=alt.Step(72 + (max_lines - 1) * 36),
        autosize=alt.AutoSizeParams(type="fit-x", contains="padding"),
    )
