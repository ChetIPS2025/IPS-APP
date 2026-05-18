"""Estimates list page — shared layout, badges, and summary visuals."""

from __future__ import annotations

import html
from decimal import Decimal
from typing import Any

import streamlit as st

IPS_ESTIMATES_PAGE_STYLES_KEY = "ips_estimates_page_styles_v3"

_STATUS_STYLES: dict[str, tuple[str, str, str]] = {
    "approved": ("#dcfce7", "#166534", "#bbf7d0"),
    "accepted": ("#dcfce7", "#166534", "#bbf7d0"),
    "awarded": ("#dcfce7", "#166534", "#bbf7d0"),
    "po_received": ("#dcfce7", "#166534", "#bbf7d0"),
    "draft": ("#f1f5f9", "#475569", "#e2e8f0"),
    "sent": ("#dbeafe", "#1d4ed8", "#bfdbfe"),
    "submitted": ("#dbeafe", "#1d4ed8", "#bfdbfe"),
    "pending": ("#ffedd5", "#c2410c", "#fed7aa"),
    "rejected": ("#fee2e2", "#dc2626", "#fecaca"),
}


def inject_estimates_page_styles() -> None:
    if st.session_state.get(IPS_ESTIMATES_PAGE_STYLES_KEY):
        return
    st.session_state[IPS_ESTIMATES_PAGE_STYLES_KEY] = True
    try:
        from app.ui.page_shell import inject_ips_dashboard_layout
    except ImportError:
        from ui.page_shell import inject_ips_dashboard_layout  # type: ignore
    inject_ips_dashboard_layout()
    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.ips-estimates-page) .block-container {
            max-width: 1680px !important;
            padding-top: 0.35rem !important;
        }

        /* ----- Header card ----- */
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-header-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 0.65rem !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-header-anchor) > div {
            padding: 0.9rem 1rem 0.95rem !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-header-anchor)
        div[data-testid="column"]:has(.ips-est-hdr-actions) {
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }
        .ips-est-header-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .ips-est-header-left {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            min-width: 0;
        }
        .ips-est-header-icon {
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
        .ips-est-header-icon svg { display: block; }
        .ips-est-header-title {
            margin: 0;
            font-size: 1.25rem;
            font-weight: 700;
            color: #111827;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }
        .ips-est-header-sub {
            margin: 0.2rem 0 0;
            font-size: 0.8125rem;
            color: #6b7280;
            font-weight: 400;
            line-height: 1.4;
        }

        /* ----- Filter strip ----- */
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-filter-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 0.65rem !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-filter-anchor) > div {
            padding: 0.65rem 0.75rem !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-filter-anchor) input,
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-filter-anchor) [data-baseweb="select"] > div {
            border-radius: 10px !important;
            border-color: #e5eaf2 !important;
            min-height: 2.35rem !important;
            font-size: 0.8125rem !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-filter-anchor)
        div[data-testid="column"]:has(.ips-est-date-pop) [data-testid="stPopover"] button {
            width: 100% !important;
            border-radius: 10px !important;
            border: 1px solid #e5eaf2 !important;
            background: #fff !important;
            color: #374151 !important;
            font-size: 0.8125rem !important;
            font-weight: 500 !important;
            min-height: 2.35rem !important;
            justify-content: flex-start !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor)
        .ips-est-thead-bar {
            background: #f9fafb;
            border-bottom: 1px solid #e5eaf2;
            padding: 0.5rem 0.75rem 0.4rem;
            margin: 0;
        }
        /* ----- Table card ----- */
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 0.65rem !important;
            overflow: hidden !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor) > div {
            padding: 0 !important;
        }
        .ips-est-table-head {
            display: grid;
            grid-template-columns: 1fr 2fr 1.2fr 1fr 1fr 0.9fr 0.85fr 1fr 0.7fr;
            gap: 0.35rem;
            padding: 0.55rem 0.75rem 0.45rem;
            background: #f9fafb;
            border-bottom: 1px solid #e5eaf2;
        }
        .ips-est-th {
            color: #6b7280;
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin: 0;
            line-height: 1.3;
        }
        .ips-est-th .sort { opacity: 0.45; font-size: 0.62rem; margin-left: 0.12rem; }

        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor)
        div[data-testid="stHorizontalBlock"]:has(.ips-est-row-selected) {
            background: #eff6ff !important;
            box-shadow: inset 3px 0 0 #2563eb !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor)
        div[data-testid="stHorizontalBlock"]:has(.ips-est-table-row) {
            border-bottom: 1px solid #f1f5f9 !important;
            padding: 0.15rem 0.35rem !important;
            margin: 0 !important;
            align-items: center !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor)
        div[data-testid="stHorizontalBlock"]:has(.ips-est-table-row) > div {
            padding: 0.35rem 0.4rem !important;
            font-size: 0.8125rem !important;
        }
        /* Quote # link style */
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor)
        div[data-testid="column"]:has(.ips-est-quote-anchor) .stButton > button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #2563eb !important;
            font-weight: 600 !important;
            font-size: 0.8125rem !important;
            padding: 0.2rem 0 !important;
            min-height: auto !important;
            justify-content: flex-start !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor)
        div[data-testid="column"]:has(.ips-est-quote-anchor) .stButton > button:hover {
            text-decoration: underline !important;
            background: transparent !important;
        }
        /* Sort header buttons → look like labels */
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor)
        div[data-testid="column"]:has(.ips-est-sort-anchor) .stButton > button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #6b7280 !important;
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
            padding: 0 !important;
            min-height: auto !important;
        }
        /* Action icon buttons */
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-table-anchor)
        div[data-testid="column"]:has(.ips-est-act-anchor) .stButton > button {
            background: transparent !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 8px !important;
            min-height: 1.85rem !important;
            padding: 0.15rem 0.35rem !important;
            font-size: 0.9rem !important;
        }

        .ips-est-project-title {
            color: #111827;
            font-weight: 600;
            font-size: 0.8125rem;
            line-height: 1.3;
        }
        .ips-est-project-desc {
            color: #9ca3af;
            font-size: 0.75rem;
            line-height: 1.35;
            margin-top: 0.12rem;
        }
        .ips-est-cell-muted { color: #374151; font-size: 0.8125rem; }
        .ips-est-cell-total { color: #111827; font-weight: 600; font-size: 0.8125rem; }

        /* ----- Detail panel ----- */
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-top: 3px solid #2563eb !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06) !important;
            margin-bottom: 0.65rem !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) > div {
            padding: 0.85rem 1rem 1rem !important;
        }
        .ips-est-detail-head {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            align-items: flex-start;
            justify-content: space-between;
            padding-bottom: 0.65rem;
            border-bottom: 1px solid #f1f5f9;
            margin-bottom: 0.5rem;
        }
        .ips-est-detail-id-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        .ips-est-detail-title {
            margin: 0;
            font-size: 1.125rem;
            font-weight: 700;
            color: #111827;
            letter-spacing: -0.02em;
        }
        .ips-est-detail-project {
            margin: 0.35rem 0 0.15rem;
            font-size: 0.9375rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.3;
        }
        .ips-est-detail-customer {
            margin: 0;
            font-size: 0.8125rem;
            color: #6b7280;
        }
        .ips-est-detail-meta-row {
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
        }

        .ips-est-summary-card {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 12px;
            padding: 0.75rem 0.85rem;
            height: 100%;
            box-sizing: border-box;
        }
        .ips-est-summary-card h4 {
            margin: 0 0 0.55rem;
            font-size: 0.8125rem;
            font-weight: 700;
            color: #111827;
        }
        .ips-est-kv { width: 100%; border-collapse: collapse; }
        .ips-est-kv td {
            padding: 0.28rem 0;
            font-size: 0.8125rem;
            vertical-align: top;
            border: none;
        }
        .ips-est-kv td.k { color: #6b7280; font-weight: 500; width: 48%; }
        .ips-est-kv td.v { color: #111827; font-weight: 600; text-align: right; }
        .ips-est-kv tr.ips-est-grand td {
            padding-top: 0.45rem;
            border-top: 1px solid #e5eaf2;
            font-weight: 700;
        }
        .ips-est-kv tr.ips-est-grand td.v { font-size: 0.9375rem; color: #111827; }

        .ips-est-donut-wrap {
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .ips-est-donut {
            width: 108px;
            height: 108px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .ips-est-donut-legend { flex: 1; min-width: 150px; }
        .ips-est-donut-legend .row {
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            font-size: 0.78rem;
            padding: 0.2rem 0;
            color: #374151;
        }
        .ips-est-donut-legend .dot {
            display: inline-block;
            width: 0.5rem;
            height: 0.5rem;
            border-radius: 50%;
            margin-right: 0.35rem;
            vertical-align: middle;
        }
        .ips-est-donut-total {
            margin-top: 0.4rem;
            padding-top: 0.4rem;
            border-top: 1px solid #e5eaf2;
            font-weight: 700;
            font-size: 0.8125rem;
            color: #111827;
            display: flex;
            justify-content: space-between;
        }

        .ips-est-meta-block .lbl {
            font-size: 0.68rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        .ips-est-meta-block .val {
            font-size: 0.8125rem;
            color: #111827;
            font-weight: 600;
            margin-top: 0.15rem;
        }

        .ips-est-line-items-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0.85rem 0 0.45rem;
        }
        .ips-est-line-items-head h4 {
            margin: 0;
            font-size: 0.875rem;
            font-weight: 700;
            color: #111827;
        }
        .ips-est-line-items-head span {
            color: #2563eb;
            font-size: 0.8125rem;
            font-weight: 600;
        }
        .ips-est-view-all-link {
            color: #2563eb;
            font-size: 0.8125rem;
            font-weight: 600;
            text-decoration: none;
        }
        .ips-est-view-all-link:hover { text-decoration: underline; }

        .ips-est-status-pill {
            display: inline-block;
            padding: 0.18rem 0.55rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            line-height: 1.2;
            white-space: nowrap;
            border: 1px solid transparent;
        }

        section[data-testid="stMain"]:has(.ips-estimates-page) .stTabs [data-baseweb="tab-list"] {
            gap: 0.25rem !important;
            border-bottom: 1px solid #e5eaf2 !important;
            background: transparent !important;
            padding: 0 0 0.15rem !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page) .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            color: #6b7280 !important;
            font-weight: 600 !important;
            font-size: 0.8125rem !important;
            padding: 0.5rem 0.7rem !important;
            border-radius: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page) .stTabs [aria-selected="true"] {
            color: #2563eb !important;
            border-bottom: 2px solid #2563eb !important;
            background: transparent !important;
        }

        /* Header action buttons in header card */
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-header-anchor)
        div[data-testid="column"]:has(.ips-est-hdr-actions) .stDownloadButton button,
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-header-anchor)
        div[data-testid="column"]:has(.ips-est-hdr-actions) .stButton > button {
            border-radius: 10px !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            min-height: 2.35rem !important;
        }
        section[data-testid="stMain"]:has(.ips-estimates-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-header-anchor)
        div[data-testid="column"]:has(.ips-est-hdr-actions) .stDownloadButton button {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            color: #374151 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_DOC_ICON_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<path d="M8 2h8l4 4v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" stroke="#fff" stroke-width="1.5"/>'
    '<path d="M14 2v6h6M9 13h6M9 17h4" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>'
    "</svg>"
)


def render_estimates_header_left_html() -> None:
    st.markdown(
        f"""
        <motion.div class="ips-est-header-left">
          <motion.div class="ips-est-header-icon">{_DOC_ICON_SVG}</motion.div>
          <div>
            <p class="ips-est-header-title">Estimates</p>
            <p class="ips-est-header-sub">Create, review, and manage all project estimates.</p>
          </div>
        </motion.div>
        """.replace("<motion.", "<").replace("</motion.", "</"),
        unsafe_allow_html=True,
    )


def estimate_status_badge_html(status: Any) -> str:
    raw = str(status or "").strip() or "-"
    key = raw.lower().replace(" ", "_")
    bg, fg, border = _STATUS_STYLES.get(key, ("#f1f5f9", "#475569", "#e2e8f0"))
    label = raw.replace("_", " ").title() if raw != "-" else "-"
    return (
        f'<span class="ips-est-status-pill" style="background:{bg};color:{fg};border-color:{border};">'
        f"{html.escape(label)}</span>"
    )


def summary_card_html(*, title: str, rows: list[tuple[str, str]], grand_row: tuple[str, str] | None = None) -> str:
    body_parts: list[str] = []
    for k, v in rows:
        if not k:
            continue
        body_parts.append(
            f"<tr><td class='k'>{html.escape(k)}</td><td class='v'>{html.escape(v)}</td></tr>"
        )
    if grand_row:
        gk, gv = grand_row
        body_parts.append(
            f"<tr class='ips-est-grand'><td class='k'>{html.escape(gk)}</td>"
            f"<td class='v'>{html.escape(gv)}</td></tr>"
        )

    body = "".join(body_parts)
    return (
        f'<div class="ips-est-summary-card">'
        f"<h4>{html.escape(title)}</h4>"
        f"<table class='ips-est-kv'>{body}</table>"
        f"</div>"
    )


def donut_chart_html(
    segments: list[tuple[str, float, str]],
    *,
    total_label: str = "Total",
) -> str:
    amounts = [max(0.0, float(a or 0)) for _, a, _ in segments]
    total = sum(amounts)
    if total <= 0:
        return (
            '<div class="ips-est-donut-wrap">'
            '<div class="ips-est-donut" style="background:#e5eaf2;"></div>'
            '<p style="color:#6b7280;font-size:0.78rem;margin:0;">No breakdown data</p></div>'
        )
    pct = [a / total * 100.0 for a in amounts]
    gradient_parts: list[str] = []
    start = 0.0
    for p, (_, _, color) in zip(pct, segments):
        end = start + p
        gradient_parts.append(f"{color} {start:.2f}% {end:.2f}%")
        start = end
    gradient = f"conic-gradient({', '.join(gradient_parts)})"
    legend = "".join(
        f'<div class="row"><span><span class="dot" style="background:{html.escape(c)};"></span>'
        f"{html.escape(lbl)}</span><span>{html.escape(_money_short(amt))} "
        f"({(amt / total * 100):.0f}%)</span></div>"
        for lbl, amt, c in segments
        if amt > 0 or total > 0
    )
    return (
        f'<div class="ips-est-donut-wrap">'
        f'<div class="ips-est-donut" style="background:{gradient};"></div>'
        f'<div class="ips-est-donut-legend">{legend}'
        f'<div class="ips-est-donut-total"><span>{html.escape(total_label)}</span>'
        f"<span>{html.escape(_money_short(total))}</span></div></div></div>"
    )


def _money_short(val: float) -> str:
    try:
        d = Decimal(str(val)).quantize(Decimal("0.01"))
        return f"${d:,.2f}"
    except Exception:
        return "$0.00"


def meta_block_html(label: str, value: str) -> str:
    return (
        f'<div class="ips-est-meta-block">'
        f'<div class="lbl">{html.escape(label)}</div>'
        f'<div class="val">{html.escape(value or "-")}</div></div>'
    )


def date_range_button_label(d_from: Any, d_to: Any) -> str:
    """Plain text for date popover trigger (mockup single field)."""

    def _fmt(d: Any) -> str:
        if d is None:
            return ""
        try:
            return d.strftime("%b %d, %Y")
        except Exception:
            return str(d)[:10]

    a, b = _fmt(d_from), _fmt(d_to)
    if a and b:
        return f"{a} – {b}"
    if a:
        return f"From {a}"
    if b:
        return f"Until {b}"
    return "Date range"


def table_column_header_html() -> str:
    cols = [
        "Estimate #",
        "Project / Description",
        "Customer",
        "Estimate Date",
        "Expiration Date",
        "Total",
        "Status",
        "Created By",
        "Actions",
    ]
    cells = "".join(
        f'<span class="ips-est-th">{html.escape(c)}<span class="sort"> ↕</span></span>'
        for c in cols
    )
    return f'<div class="ips-est-thead-bar ips-est-table-head">{cells}</div>'


def date_range_label_html(d_from, d_to) -> str:
    def _fmt(d):
        if d is None:
            return ""
        try:
            return d.strftime("%b %d, %Y")
        except Exception:
            return str(d)[:10]

    a, b = _fmt(d_from), _fmt(d_to)
    if a and b:
        text = f"{a} – {b}"
    elif a:
        text = f"From {a}"
    elif b:
        text = f"Until {b}"
    else:
        text = "Date range"
    return (
        f'<span class="ips-est-date-range-label">'
        f'<span aria-hidden="true">📅</span> {html.escape(text)}</span>'
    )


def render_estimates_header_html() -> None:
    render_estimates_header_left_html()
