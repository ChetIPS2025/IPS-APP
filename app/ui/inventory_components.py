"""Inventory list page — shared layout, badges, and summary visuals."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

IPS_INVENTORY_PAGE_STYLES_KEY = "ips_inventory_page_styles_v3"

_STOCK_PILL: dict[str, tuple[str, str]] = {
    "in stock": ("#15803d", "#dcfce7"),
    "low stock": ("#b45309", "#fef3c7"),
    "out of stock": ("#b91c1c", "#fee2e2"),
    "on order": ("#1d4ed8", "#dbeafe"),
    "discontinued": ("#64748b", "#f1f5f9"),
}

_TAB_ICONS: dict[str, str] = {
    "Overview": "▦",
    "Stock History": "↕",
    "Transactions": "⇄",
    "Purchase Orders": "🛒",
    "Vendors": "🏢",
    "Notes": "📝",
    "Attachments": "📎",
}

_PKG_ICON_SVG = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8z" '
    'stroke="#2563eb" stroke-width="1.6" stroke-linejoin="round"/>'
    '<path d="M3.3 7.7 12 12.5l8.7-4.8M12 22V12.5" stroke="#2563eb" stroke-width="1.6" stroke-linecap="round"/>'
    "</svg>"
)


def inject_inventory_page_styles() -> None:
    try:
        from app.ui.clean_table import inject_clean_table_css
    except ImportError:
        from ui.clean_table import inject_clean_table_css  # type: ignore
    inject_clean_table_css()
    if st.session_state.get(IPS_INVENTORY_PAGE_STYLES_KEY):
        return
    st.session_state[IPS_INVENTORY_PAGE_STYLES_KEY] = True
    try:
        from app.ui.page_shell import inject_ips_dashboard_layout
    except ImportError:
        from ui.page_shell import inject_ips_dashboard_layout  # type: ignore
    inject_ips_dashboard_layout()
    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.ips-inventory-page) .block-container {
            max-width: 1680px !important;
            padding-top: 0.35rem !important;
        }

        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-header-anchor),
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-filter-anchor),
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-table-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 0.65rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-header-anchor) > div {
            padding: 0.9rem 1rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-filter-anchor) > div {
            padding: 0.65rem 0.75rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-table-anchor) > div {
            padding: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-filter-anchor) input,
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-filter-anchor) [data-baseweb="select"] > div {
            border-radius: 10px !important;
            border-color: #e5eaf2 !important;
            min-height: 2.35rem !important;
            font-size: 0.8125rem !important;
        }

        /* Header actions */
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-header-anchor)
        div[data-testid="column"]:has(.ips-inv-hdr-actions) .stDownloadButton button,
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-header-anchor)
        div[data-testid="column"]:has(.ips-inv-hdr-actions) .stButton > button {
            border-radius: 10px !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            min-height: 2.35rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-header-anchor)
        div[data-testid="column"]:has(.ips-inv-hdr-actions) .stDownloadButton button {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            color: #374151 !important;
        }

        .ips-inv-header-inner {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            min-width: 0;
        }
        .ips-inv-header-icon {
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 10px;
            background: #2563eb;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            box-shadow: 0 1px 2px rgba(37, 99, 235, 0.25);
        }
        .ips-inv-header-icon svg path { stroke: #ffffff !important; }
        .ips-inv-header-title {
            margin: 0;
            font-size: 1.25rem;
            font-weight: 700;
            color: #111827;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }
        .ips-inv-header-sub {
            margin: 0.2rem 0 0;
            font-size: 0.8125rem;
            color: #6b7280;
            font-weight: 400;
        }

        /* Table */
        .ips-inv-table-head-row {
            background: #ffffff;
            border-bottom: 1px solid #e5eaf2;
            padding: 0.55rem 0.65rem 0.45rem;
            margin: 0 !important;
        }
        .ips-inv-th {
            color: #6b7280 !important;
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.3;
        }
        .ips-inv-th .sort {
            opacity: 0.5;
            font-size: 0.58rem;
            margin-left: 0.15rem;
            vertical-align: middle;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-table-anchor)
        div[data-testid="stHorizontalBlock"]:has(.ips-inv-row-selected) {
            background: #eff6ff !important;
            box-shadow: inset 4px 0 0 #2563eb !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-table-anchor)
        div[data-testid="stHorizontalBlock"]:has(.ips-inv-table-row) {
            border-bottom: 1px solid #f1f5f9 !important;
            padding: 0.1rem 0.35rem !important;
            margin: 0 !important;
            align-items: center !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-table-anchor)
        div[data-testid="stHorizontalBlock"]:has(.ips-inv-table-row) > div {
            padding: 0.38rem 0.4rem !important;
            font-size: 0.8125rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-table-anchor)
        div[data-testid="column"]:has(.ips-inv-link-anchor) .stButton > button {
            background: #ffffff !important;
            border: none !important;
            box-shadow: none !important;
            color: #2563eb !important;
            font-weight: 600 !important;
            font-size: 0.8125rem !important;
            padding: 0.15rem 0 !important;
            min-height: auto !important;
            justify-content: flex-start !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-table-anchor)
        div[data-testid="column"]:has(.ips-inv-act-anchor) .stButton > button {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 8px !important;
            min-height: 1.85rem !important;
            padding: 0.12rem 0.35rem !important;
            font-size: 0.85rem !important;
            color: #374151 !important;
        }
        .ips-inv-cell-desc {
            color: #111827;
            font-weight: 600;
            font-size: 0.8125rem;
            line-height: 1.3;
        }
        .ips-inv-cell-muted {
            color: #374151;
            font-size: 0.8125rem;
            font-weight: 500;
        }
        .ips-inv-cell-total {
            color: #111827;
            font-weight: 600;
            font-size: 0.8125rem;
        }

        /* Inline detail (inside table card — mirrors mockup) */
        .ips-inv-detail-inline {
            border-top: 1px solid #e5eaf2;
            padding: 0.85rem 0.75rem 1rem;
            margin-top: 0.15rem;
            background: #ffffff;
        }
        .ips-inv-detail-head-row {
            display: flex;
            flex-wrap: wrap;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.75rem 1rem;
            padding-bottom: 0.65rem;
            border-bottom: 1px solid #f1f5f9;
            margin-bottom: 0.5rem;
        }
        .ips-inv-detail-head-left { flex: 1 1 12rem; min-width: 0; }
        .ips-inv-detail-head-mid { flex: 1 1 20rem; min-width: 0; }
        .ips-inv-detail-head-right { flex: 0 0 auto; min-width: 11rem; }
        .ips-inv-detail-id-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        .ips-inv-detail-id {
            margin: 0;
            font-size: 1.125rem;
            font-weight: 700;
            color: #111827;
            letter-spacing: -0.02em;
        }
        .ips-inv-detail-name {
            margin: 0.35rem 0 0.1rem;
            font-size: 0.9375rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.3;
        }
        .ips-inv-detail-cat {
            margin: 0;
            font-size: 0.8125rem;
            color: #6b7280;
            font-weight: 500;
        }
        .ips-inv-detail-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 1.25rem 1.5rem;
            align-items: flex-start;
            padding: 0.25rem 0;
        }
        .ips-inv-detail-stats .stat {
            min-width: 4.5rem;
        }
        .ips-inv-detail-stats .k {
            display: block;
            font-size: 0.68rem;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 0.15rem;
        }
        .ips-inv-detail-stats .v {
            display: block;
            font-size: 0.875rem;
            font-weight: 700;
            color: #111827;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div:has(.ips-inv-det-actions) .stButton > button[kind="secondary"] {
            background: #ffffff !important;
            border: 1px solid #2563eb !important;
            color: #2563eb !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.8125rem !important;
            min-height: 2.2rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div:has(.ips-inv-det-actions) .stButton > button[kind="primary"] {
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.8125rem !important;
            min-height: 2.2rem !important;
        }

        /* Tabs — Streamlit buttons styled as mockup tabs */
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div:has(.ips-inv-tab-picker) {
            border-bottom: 1px solid #e5eaf2;
            margin: 0.5rem 0 0.75rem;
            padding-bottom: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-inv-tab-picker) {
            gap: 0.15rem !important;
            flex-wrap: wrap !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="column"]:has(.ips-inv-tab-cell) .stButton > button {
            background: #ffffff !important;
            border: none !important;
            box-shadow: none !important;
            color: #6b7280 !important;
            font-weight: 600 !important;
            font-size: 0.8125rem !important;
            padding: 0.45rem 0.55rem 0.5rem !important;
            min-height: auto !important;
            border-radius: 0 !important;
            border-bottom: 2px solid transparent !important;
            width: 100% !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="column"]:has(.ips-inv-tab-cell-active) .stButton > button {
            color: #2563eb !important;
            font-weight: 700 !important;
            border-bottom: 2px solid #2563eb !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="column"]:has(.ips-inv-tab-cell) .stButton > button:hover {
            color: #2563eb !important;
            background: #ffffff !important;
        }
        /* Search icon hint */
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-filter-anchor)
        div[data-testid="column"]:has(.ips-inv-search-cell) input {
            padding-left: 2rem !important;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' stroke='%239ca3af' stroke-width='2'%3E%3Ccircle cx='7' cy='7' r='5'/%3E%3Cpath d='M11 11l3 3'/%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: 0.65rem center !important;
        }

        .ips-inv-summary-card {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 12px;
            padding: 0.75rem 0.85rem;
            height: 100%;
            box-sizing: border-box;
        }
        .ips-inv-summary-card h4 {
            margin: 0 0 0.55rem;
            font-size: 0.875rem;
            font-weight: 700;
            color: #111827;
        }
        .ips-inv-kv { width: 100%; border-collapse: collapse; }
        .ips-inv-kv td {
            padding: 0.32rem 0;
            font-size: 0.78rem;
            vertical-align: middle;
            border-bottom: 1px solid #f8fafc;
        }
        .ips-inv-kv tr:last-child td { border-bottom: none; }
        .ips-inv-kv td.k {
            color: #6b7280;
            width: 46%;
            font-weight: 500;
        }
        .ips-inv-kv td.v {
            color: #111827;
            font-weight: 600;
            text-align: right;
        }
        .ips-inv-kv td.v.warn { color: #dc2626 !important; font-weight: 700 !important; }

        .ips-inv-usage-wrap {
            border: 1px solid #f1f5f9;
            border-radius: 8px;
            padding: 0.35rem 0.5rem 0.25rem;
            background: #ffffff;
            margin-bottom: 0.5rem;
        }
        .ips-inv-usage-metrics {
            display: flex;
            gap: 1.5rem;
            font-size: 0.78rem;
            color: #374151;
            margin-top: 0.35rem;
        }
        .ips-inv-usage-metrics strong { color: #111827; font-weight: 700; }
        .ips-inv-usage-empty {
            text-align: center;
            color: #94a3b8;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 2rem 0.5rem;
            border: 1px dashed #e5eaf2;
            border-radius: 8px;
        }

        .ips-inv-txn-section {
            margin-top: 0.85rem;
            padding-top: 0.65rem;
            border-top: 1px solid #f1f5f9;
        }
        .ips-inv-txn-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        .ips-inv-txn-head h4 {
            margin: 0;
            font-size: 0.875rem;
            font-weight: 700;
            color: #111827;
        }
        .ips-inv-txn-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
        }
        .ips-inv-txn-table thead th {
            text-align: left;
            color: #9ca3af;
            font-weight: 700;
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            padding: 0.45rem 0.5rem;
            border-bottom: 1px solid #e5eaf2;
            background: #ffffff;
        }
        .ips-inv-txn-table tbody td {
            padding: 0.5rem 0.5rem;
            border-bottom: 1px solid #f1f5f9;
            color: #374151;
            font-weight: 500;
        }
        .ips-inv-txn-table tbody tr:last-child td { border-bottom: none; }
        .ips-inv-txn-qty-neg { color: #dc2626; font-weight: 600; }
        .ips-inv-txn-qty-pos { color: #15803d; font-weight: 600; }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-filter-anchor)
        div[data-testid="column"]:last-child .stButton > button {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            color: #374151 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_inventory_header_inner_html() -> str:
    icon_svg = _PKG_ICON_SVG.replace('stroke="#2563eb"', 'stroke="#ffffff"')
    return (
        '<motion.div class="ips-inv-header-inner">'
        f'<motion.div class="ips-inv-header-icon">{icon_svg}</motion.div>'
        "<div>"
        '<p class="ips-inv-header-title">Inventory</p>'
        '<p class="ips-inv-header-sub">Track and manage all inventory items and stock levels.</p>'
        "</motion.div></div>"
    ).replace("<motion.", "<").replace("</motion.", "</")


def table_header_html(label: str, *, sortable: bool = True) -> str:
    sort = '<span class="sort">⇅</span>' if sortable else ""
    return f'<p class="ips-inv-th">{html.escape(label)}{sort}</p>'


def stock_status_badge_html(status: str) -> str:
    key = str(status or "").strip().lower()
    fg, bg = _STOCK_PILL.get(key, ("#64748b", "#f1f5f9"))
    label = str(status or "").strip() or "—"
    return (
        f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;'
        f"font-size:0.68rem;font-weight:700;color:{fg};background:{bg};"
        f'white-space:nowrap;line-height:1.2;">{html.escape(label)}</span>'
    )


def detail_stats_row_html(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<motion.div class="stat"><span class="k">{html.escape(k)}</span>'
        f'<span class="v">{html.escape(v or "—")}</span></motion.div>'
        for k, v in items
    )
    return f'<motion.div class="ips-inv-detail-stats">{cells}</motion.div>'.replace("<motion.", "<").replace(
        "</motion.", "</"
    )


def tab_bar_html(tabs: tuple[str, ...], active: str) -> str:
    parts = ['<motion.div class="ips-inv-tab-bar">']
    for tab in tabs:
        cls = "ips-inv-tab-active" if tab == active else "ips-inv-tab-inactive"
        ico = _TAB_ICONS.get(tab, "")
        parts.append(
            f'<span class="{cls}"><span class="ips-inv-tab-ico">{html.escape(ico)}</span>'
            f"{html.escape(tab)}</span>"
        )
    parts.append("</motion.div>")
    return "".join(parts).replace("<motion.", "<").replace("</motion.", "</")


def summary_card_html(
    title: str,
    rows: list[tuple[str, str]],
    *,
    value_class: dict[str, str] | None = None,
    badge_html: dict[str, str] | None = None,
) -> str:
    vc = value_class or {}
    badges = badge_html or {}
    body = ""
    for k, v in rows:
        cls = vc.get(k, "")
        cls_attr = f' class="v {cls}"' if cls else ' class="v"'
        val = badges.get(k, html.escape(v or "—"))
        body += f"<tr><td class=\"k\">{html.escape(k)}</td><td{cls_attr}>{val}</td></tr>"
    return (
        f'<motion.div class="ips-inv-summary-card">'
        f"<h4>{html.escape(title)}</h4>"
        f'<table class="ips-inv-kv"><tbody>{body}</tbody></table>'
        "</motion.div>"
    ).replace("<motion.", "<").replace("</motion.", "</")


def transactions_table_html(rows: list[dict[str, str]]) -> str:
    if not rows:
        return '<p class="ips-inv-usage-empty" style="padding:1rem;">No transactions recorded.</p>'
    hdr = (
        "<thead><tr>"
        "<th>Date</th><th>Type</th><th>Reference</th><th>Qty</th>"
        "<th>Unit Cost</th><th>Total Cost</th><th>Performed By</th>"
        "</tr></thead>"
    )
    body_parts: list[str] = []
    for r in rows:
        qty = r.get("Qty", "")
        qty_cls = ""
        if str(qty).startswith("-"):
            qty_cls = "ips-inv-txn-qty-neg"
        elif str(qty).startswith("+"):
            qty_cls = "ips-inv-txn-qty-pos"
        body_parts.append(
            "<tr>"
            f"<td>{html.escape(r.get('Date', '—'))}</td>"
            f"<td>{html.escape(r.get('Type', '—'))}</td>"
            f"<td>{html.escape(r.get('Reference', '—'))}</td>"
            f'<td class="{qty_cls}">{html.escape(qty)}</td>'
            f"<td>{html.escape(r.get('Unit Cost', '—'))}</td>"
            f"<td>{html.escape(r.get('Total Cost', '—'))}</td>"
            f"<td>{html.escape(r.get('Performed By', '—'))}</td>"
            "</tr>"
        )
    return f'<table class="ips-inv-txn-table">{hdr}<tbody>{"".join(body_parts)}</tbody></table>'


def usage_line_chart_html(daily_values: list[float], *, days: int = 28) -> str:
    if not daily_values:
        return ""
    w, h = 400, 120
    pad_l, pad_r, pad_t, pad_b = 28, 8, 8, 22
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    mx = max(daily_values) or 1.0
    n = len(daily_values)
    pts: list[str] = []
    for i, v in enumerate(daily_values):
        x = pad_l + (i / max(n - 1, 1)) * inner_w
        y = pad_t + inner_h - (float(v) / mx) * inner_h
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    today = date.today()
    labels = [(today - timedelta(days=(days - 1 - i))).strftime("%b %d") for i in range(n)]
    x_labels = ""
    step = max(1, n // 5)
    for i in range(0, n, step):
        x = pad_l + (i / max(n - 1, 1)) * inner_w
        x_labels += (
            f'<text x="{x:.0f}" y="{h - 4}" text-anchor="middle" '
            f'font-size="9" fill="#9ca3af">{html.escape(labels[i])}</text>'
        )
    grid = ""
    for g in range(5):
        gy = pad_t + (g / 4) * inner_h
        gv = mx * (1 - g / 4)
        grid += (
            f'<line x1="{pad_l}" y1="{gy:.0f}" x2="{w - pad_r}" y2="{gy:.0f}" stroke="#f1f5f9" stroke-width="1"/>'
            f'<text x="4" y="{gy + 3:.0f}" font-size="8" fill="#9ca3af">{gv:.0f}</text>'
        )
    return (
        f'<motion.div class="ips-inv-usage-wrap">'
        f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" preserveAspectRatio="none" aria-hidden="true">'
        f"{grid}"
        f'<polyline fill="none" stroke="#2563eb" stroke-width="2" points="{poly}"/>'
        f'<polygon fill="rgba(37,99,235,0.1)" points="{poly} {w - pad_r},{pad_t + inner_h} {pad_l},{pad_t + inner_h}"/>'
        f"{x_labels}"
        "</svg></motion.div>"
    ).replace("<motion.", "<").replace("</motion.", "</")
