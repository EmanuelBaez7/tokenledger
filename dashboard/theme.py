"""Design tokens and local font faces for the Streamlit dashboard."""

PALETTES = {
    "light": {
        "background": "#F8FAFC",
        "surface": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#475569",
        "border": "#CBD5E1",
        "control": "#64748B",
        "brand": "#1D4ED8",
        "accent": "#B45309",
        "up": "#B91C1C",
        "down": "#166534",
    },
    "dark": {
        "background": "#0B1220",
        "surface": "#111C2E",
        "text": "#E5EAF3",
        "muted": "#9BA9BD",
        "border": "#465874",
        "control": "#7C8CA5",
        "brand": "#93B4FF",
        "accent": "#B78730",
        "up": "#FCA5A5",
        "down": "#86EFAC",
    },
}


CSS = """
.st-key-tl-shell,.st-key-tl-filters {
     font-variant-numeric:tabular-nums;
}
div p.tl-help {
     color:color-mix(in srgb, currentColor 74%, transparent);
     font-size:.875rem;
     line-height:1.5rem;
     margin:0;
}
.st-key-tl-source :is(label,input[role="combobox"]:disabled,button:disabled) {
     color:inherit;
     -webkit-text-fill-color:currentColor;
}
.st-key-tl-compare label:has([role="switch"]) > span + div {
     box-shadow:inset 0 0 0 1px var(--tl-control);
}
.st-key-tl-compare label:has([role="switch"]) > span + div > div {
     background:var(--tl-control);
}
.st-key-tl-compare label:has([role="switch"]:checked) > span + div > div {
     background:var(--tl-surface);
}
.st-key-tl-compare label:has([role="switch"]:focus-visible) > span + div {
     outline:2px solid var(--tl-brand);
     outline-offset:2px;
}
.tl-kpis {
     display:grid;
     grid-template-columns:repeat(auto-fit,minmax(min(100%,175px),1fr));
     gap:16px;
     margin:16px 0 32px;
}
.tl-kpi {
     display:grid;
     grid-template-rows:3rem auto 1fr;
     row-gap:.5rem;
     padding:16px;
     background:var(--tl-surface);
     border:1px solid var(--tl-border);
     border-radius:8px;
     min-width:0;
}
.tl-kpi h2 {
     block-size:3rem;
     display:-webkit-box;
     -webkit-box-orient:vertical;
     -webkit-line-clamp:2;
     overflow:hidden;
     overflow-wrap:anywhere;
     font-size:.875rem;
     line-height:1.5rem;
     font-weight:500;
     margin:0;
     padding:0;
     color:var(--tl-muted);
}
.tl-kpi-value {
     font-family:'IBM Plex Sans',system-ui,sans-serif;
     font-size:clamp(24px,1.8vw,32px);
     line-height:40px;
     font-weight:600;
     overflow-wrap:anywhere;
     color:var(--tl-text);
}
.tl-kpi-value>span {
     line-height:normal;
     vertical-align:baseline;
}
.tl-kpi-context {
     font-size:14px;
     line-height:24px;
     color:var(--tl-muted);
}
.tl-id {
     font-family:'IBM Plex Mono',ui-monospace,monospace;
     overflow-wrap:anywhere;
}
.tl-feature {
     font-size:18px;
}
.tl-number,.tl-num {
     font-family:'IBM Plex Sans',system-ui,sans-serif;
     font-variant-numeric: tabular-nums;
}
.tl-num {
     text-align:right;
     white-space:nowrap;
}
.tl-up {
     color:var(--tl-up);
}
 .tl-down {
     color:var(--tl-down);
}
 .tl-muted {
     color:var(--tl-muted);
}
.tl-demo {
     padding:8px 16px;
     border-left:3px solid var(--tl-brand);
     background:var(--tl-surface);
     color:var(--tl-text);
     font-size:14px;
     margin:8px 0 16px;
}
.tl-table-scroll {
     overflow:auto;
     max-height:560px;
     border-radius:4px;
}
.tl-ledger {
     border-collapse:collapse;
     border:0;
     width:100%;
     color:var(--tl-text);
     background:var(--tl-surface);
     font-size:14px;
     line-height:24px;
}
.tl-ledger th {
     text-align:left;
     color:var(--tl-muted);
     font-weight:500;
}
.tl-ledger th:not(:first-child) {
     text-align:right;
}
.tl-ledger td,.tl-ledger th {
     padding:8px 16px;
     border:0;
     border-bottom:1px solid var(--tl-border);
     vertical-align:top;
}
.tl-ledger td:first-child {
     min-width:160px;
     max-width:300px;
}
.tl-ledger tfoot td {
     border-top:1px solid var(--tl-control);
     border-bottom: 3px double var(--tl-control);
     font-weight:600;
}
.tl-ledger tfoot td:first-child {
     font-family:'IBM Plex Sans',system-ui,sans-serif;
}
.tl-share {
     display:inline-block;
     width:48px;
     height:4px;
     margin-right:8px;
     background:var(--tl-border);
     vertical-align:middle;
}
.tl-share>span {
     display:block;
     height:4px;
     background:var(--tl-brand);
}
.tl-table-note {
     font-size:14px;
     line-height:24px;
     color:var(--tl-muted);
     margin:8px 0;
}
.tl-message {
     padding:24px;
     border:1px solid var(--tl-border);
     border-radius:8px;
     color:var(--tl-text);
     background:var(--tl-surface);
}
.tl-message h2 {
     font-size:20px;
     margin:0 0 8px;
}
.tl-message p {
     margin:0;
     line-height:24px;
}
.tl-observations {
     padding:16px 0;
     border-top:1px solid var(--tl-border);
}
.tl-observations h2 {
     font-size:20px;
     margin:0 0 16px;
}
.tl-observations p {
     margin:8px 0;
     line-height:24px;
}
.tl-sr {
     position:absolute;
     width:1px;
     height:1px;
     padding:0;
     margin:-1px;
     overflow:hidden;
     clip:rect(0,0,0,0);
     white-space:nowrap;
     border:0;
}
.tl-skeleton-grid {
     display:grid;
     grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
     gap:16px;
}
.tl-skeleton {
     height:112px;
     border-radius:8px;
     background:var(--tl-border);
     opacity:.5;
}
.tl-skeleton-chart {
     height:240px;
     margin:24px 0;
}
:is(.st-key-tl-shell,.st-key-tl-filters)
 :is(button,input,[role=combobox],[role=tab],
 [role=radio]):focus-visible,
.tl-table-scroll:focus-visible {
     outline:2px solid var(--tl-brand);
     outline-offset:2px;
     box-shadow:none;
}
"""


def stylesheet() -> str:
    # Streamlit 1.65 updates color-scheme on .stApp when the menu changes theme.
    variables = ";".join(
        f"--tl-{key}:light-dark({light},{PALETTES['dark'][key]})"
        for key, light in PALETTES["light"].items()
    )
    arrows = "".join(
        f"@font-face{{font-family:'IBM Plex Sans';font-style:normal;"
        f"font-weight:{weight};font-display:swap;"
        f"src:url('app/static/fonts/IBMPlexSans-{name}-Pi.woff2') "
        "format('woff2');unicode-range:U+2191,U+2193;}"
        for weight, name in ((400, "Regular"), (500, "Medium"), (600, "SemiBold"))
    )
    return "<style>" + arrows + ".stApp{" + variables + "}" + CSS + "</style>"
