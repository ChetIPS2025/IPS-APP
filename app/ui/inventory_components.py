"""Inventory list page — shared layout, badges, and summary visuals."""

from __future__ import annotations

import html

import streamlit as st

IPS_INVENTORY_PAGE_STYLES_KEY = "ips_inventory_page_styles_v1"

_STOCK_PILL: dict[str, tuple[str, str]] = {
    "in stock": ("#16a34a", "#dcfce7"),
    "low stock": ("#d97706", "#fef3c7"),
    "out of stock": ("#dc2626", "#fee2e2"),
    "on order": ("#2563eb", "#dbeafe"),
    "discontinued": ("#64748b", "#f1f5f9"),
}

_PKG_ICON_SVG = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8z" '
    'stroke="#2563eb" stroke-width="1.6" stroke-linejoin="round"/>'
    '<path d="M3.3 7.7 12 12.5l8.7-4.8M12 22V12.5" stroke="#2563eb" stroke-width="1.6" stroke-linecap="round"/>'
    "</svg>"
)


def inject_inventory_page_styles() -> None:
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
        section[data-testid="stMain"]:has(.ips-inventory-page) {
            background: #f4f6f9 !important;
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
            margin-bottom: 0.5rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-header-anchor) > div {
            padding: 0.75rem 0.9rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-filter-anchor) > div {
            padding: 0.55rem 0.7rem 0.6rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-table-anchor) > div {
            padding: 0.2rem 0.55rem 0.35rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-detail-anchor) {
            background: #ffffff !important;
            border: 1px solid #93c5fd !important;
            border-radius: 16px !important;
            box-shadow: 0 1px 4px rgba(37, 99, 235, 0.1) !important;
            margin-bottom: 0.5rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-inv-detail-anchor) > div {
            padding: 0.85rem 0.95rem 0.95rem !important;
        }
        .ips-inv-header-inner {
            display: flex;
            align-items: flex-start;
            gap: 0.65rem;
            min-width: 0;
        }
        .ips-inv-header-icon {
            width: 2.4rem;
            height: 2.4rem;
            border-radius: 10px;
            background: #eff6ff;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .ips-inv-header-icon svg { display: block; }
        .ips-inv-header-title {
            margin: 0;
            font-size: 1.15rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.2;
        }
        .ips-inv-header-sub {
            margin: 0.1rem 0 0;
            font-size: 0.8125rem;
            color: #6b7280;
            font-weight: 500;
        }
        .ips-inv-th {
            color: #9ca3af !important;
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin: 0 !important;
            padding: 0.5rem 0 0.4rem !important;
            border-bottom: 1px solid #e5eaf2;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-inv-row-selected) {
            background: #eff6ff !important;
            border-left: 4px solid #2563eb !important;
            border-radius: 0 4px 4px 0 !important;
            margin: 0 -0.4rem !important;
            padding: 0.12rem 0 0.12rem 0.4rem !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-inv-row-marker):not(:has(.ips-inv-row-selected)) {
            border-bottom: 1px solid #f3f4f6;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page) .ips-inv-link-btn button {
            color: #2563eb !important;
            font-weight: 600 !important;
            font-size: 0.8125rem !important;
            padding: 0 !important;
            min-height: 1.35rem !important;
            height: auto !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }
        section[data-testid="stMain"]:has(.ips-inventory-page) .ips-inv-action-btn button {
            min-height: 1.65rem !important;
            padding: 0.1rem 0.35rem !important;
            font-size: 0.9rem !important;
            border-radius: 6px !important;
        }
        .ips-inv-muted-cell {
            font-size: 0.8rem;
            color: #6b7280;
            font-weight: 500;
        }
        .ips-inv-detail-id {
            margin: 0;
            font-size: 1.25rem;
            font-weight: 800;
            color: #111827;
            line-height: 1.2;
            display: inline-block;
            margin-right: 0.5rem;
        }
        .ips-inv-detail-name {
            margin: 0.2rem 0 0;
            font-size: 0.9rem;
            color: #4b5563;
            font-weight: 600;
        }
        .ips-inv-detail-cat {
            margin: 0.15rem 0 0;
            font-size: 0.78rem;
            color: #6b7280;
            font-weight: 500;
        }
        .ips-inv-meta-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.35rem 0.75rem;
            font-size: 0.78rem;
        }
        .ips-inv-meta-grid .k { color: #6b7280; font-weight: 600; }
        .ips-inv-meta-grid .v { color: #111827; font-weight: 600; }
        .ips-inv-summary-card {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 12px;
            padding: 0.7rem 0.8rem;
            height: 100%;
            box-sizing: border-box;
        }
        .ips-inv-summary-card h4 {
            margin: 0 0 0.5rem;
            font-size: 0.84rem;
            font-weight: 700;
            color: #111827;
        }
        .ips-inv-kv { width: 100%; border-collapse: collapse; }
        .ips-inv-kv td {
            padding: 0.28rem 0;
            font-size: 0.78rem;
            vertical-align: middle;
        }
        .ips-inv-kv td.k {
            color: #6b7280;
            width: 44%;
            font-weight: 500;
        }
        .ips-inv-kv td.v {
            color: #111827;
            font-weight: 600;
        }
        .ips-inv-kv td.v.warn { color: #dc2626; font-weight: 700; }
        .ips-inv-tab-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 0.15rem 0.35rem;
            border-bottom: 1px solid #e5eaf2;
            margin: 0.65rem 0 0.75rem;
            padding-bottom: 0;
        }
        .ips-inv-tab-active {
            display: inline-block;
            padding: 0.35rem 0.55rem 0.5rem;
            font-size: 0.8rem;
            font-weight: 700;
            color: #2563eb;
            border-bottom: 2px solid #2563eb;
            margin-bottom: -1px;
        }
        .ips-inv-tab-inactive {
            display: inline-block;
            padding: 0.35rem 0.55rem 0.5rem;
            font-size: 0.8rem;
            font-weight: 600;
            color: #6b7280;
        }
        .ips-inv-usage-chart {
            width: 100%;
            height: 72px;
            margin: 0.25rem 0 0.5rem;
        }
        .ips-inv-usage-empty {
            text-align: center;
            color: #94a3b8;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 1.25rem 0.5rem;
            border: 1px dashed #e5eaf2;
            border-radius: 8px;
            margin: 0.25rem 0 0.5rem;
        }
        .ips-inv-txn-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            margin: 0.5rem 0 0.35rem;
        }
        .ips-inv-txn-head h4 {
            margin: 0;
            font-size: 0.84rem;
            font-weight: 700;
            color: #111827;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_inventory_header_inner_html() -> str:
    return (
        '<motion.div class="ips-inv-header-inner">'
        f'<motion.div class="ips-inv-header-icon">{_PKG_ICON_SVG}</motion.div>'
        "<div>"
        '<p class="ips-inv-header-title">Inventory</p>'
        '<p class="ips-inv-header-sub">Track and manage all inventory items and stock levels.</p>'
        "</motion.div></div>"
    ).replace("<motion.", "<").replace("</motion.", "</")


def table_header_html(label: str) -> str:
    return f'<p class="ips-inv-th">{html.escape(label)}</p>'


def stock_status_badge_html(status: str) -> str:
    key = str(status or "").strip().lower()
    fg, bg = _STOCK_PILL.get(key, ("#64748b", "#f1f5f9"))
    label = str(status or "").strip() or "—"
    return (
        f'<span style="display:inline-block;padding:3px 9px;border-radius:999px;'
        f"font-size:0.68rem;font-weight:700;color:{fg};background:{bg};"
        f'white-space:nowrap;">{html.escape(label)}</span>'
    )


def summary_card_html(title: str, rows: list[tuple[str, str]], *, value_class: dict[str, str] | None = None) -> str:
    vc = value_class or {}
    body = ""
    for k, v in rows:
        cls = vc.get(k, "")
        cls_attr = f' class="v {cls}"' if cls else ' class="v"'
        body += f"<tr><td class=\"k\">{html.escape(k)}</td><td{cls_attr}>{html.escape(v or '—')}</td></tr>"
    return (
        f'<motion.div class="ips-inv-summary-card">'
        f"<h4>{html.escape(title)}</h4>"
        f'<table class="ips-inv-kv"><tbody>{body}</tbody></table>'
        "</motion.div>"
    ).replace("<motion.", "<").replace("</motion.", "</")


def detail_meta_grid_html(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div><span class="k">{html.escape(k)}</span> '
        f'<span class="v">{html.escape(v or "—")}</span></motion.div>'
        for k, v in items
    )
    return f'<motion.div class="ips-inv-meta-grid">{cells}</motion.div>'.replace("<motion.", "<").replace("</motion.", "</")


def usage_sparkline_svg(daily_values: list[float], *, width: int = 320, height: int = 72) -> str:
    if not daily_values or all(v == 0 for v in daily_values):
        return ""
    mx = max(daily_values) or 1.0
    n = len(daily_values)
    pad = 4
    inner_w = width - pad * 2
    inner_h = height - pad * 2
    pts: list[str] = []
    for i, v in enumerate(daily_values):
        x = pad + (i / max(n - 1, 1)) * inner_w
        y = pad + inner_h - (float(v) / mx) * inner_h
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    return (
        f'<svg class="ips-inv-usage-chart" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none" aria-hidden="true">'
        f'<polyline fill="none" stroke="#2563eb" stroke-width="2" points="{poly}"/>'
        f'<polygon fill="rgba(37,99,235,0.08)" points="{poly} {width - pad},{height - pad} {pad},{height - pad}"/>'
        "</svg>"
    )
