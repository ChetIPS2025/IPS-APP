"""Users management page — shared layout, badges, and summary visuals."""

from __future__ import annotations

import html

import streamlit as st

IPS_USERS_PAGE_STYLES_KEY = "ips_users_page_styles_v4"

_ROLE_BADGE_COLORS: dict[str, str] = {
    "administrator": "#2563eb",
    "supervisor": "#0284c7",
    "project manager": "#7c3aed",
    "field employee": "#64748b",
    "accounting": "#d97706",
    "manager": "#7c3aed",
    "admin": "#2563eb",
    "employee": "#64748b",
    "viewer": "#d97706",
}

_STATUS_COLORS: dict[str, str] = {
    "active": "#16a34a",
    "inactive": "#dc2626",
    "pending": "#d97706",
    "enabled": "#16a34a",
    "not configured": "#64748b",
}


def inject_users_page_styles() -> None:
    try:
        from app.ui.clean_table import inject_clean_table_css
    except ImportError:
        from ui.clean_table import inject_clean_table_css  # type: ignore
    inject_clean_table_css()
    if st.session_state.get(IPS_USERS_PAGE_STYLES_KEY):
        return
    st.session_state[IPS_USERS_PAGE_STYLES_KEY] = True
    try:
        from app.ui.page_shell import inject_ips_dashboard_layout
    except ImportError:
        from ui.page_shell import inject_ips_dashboard_layout  # type: ignore
    inject_ips_dashboard_layout()
    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-header-anchor),
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-filter-anchor),
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 0.5rem !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-header-anchor) > div {
            padding: 0.75rem 0.9rem !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-filter-anchor) > div {
            padding: 0.55rem 0.7rem 0.6rem !important;
        }
        /* ----- Table card ----- */
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor) > div {
            padding: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }

        /* Column header row: compact + bottom border */
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stHorizontalBlock"]:has(.ips-users-th-row) {
            background: #ffffff !important;
            border-bottom: 1px solid #e5eaf2 !important;
            margin: 0 !important;
            padding: 0.3rem 0.55rem !important;
            border-radius: 0 !important;
            min-height: 2.25rem !important;
            align-items: center !important;
            box-sizing: border-box !important;
        }

        /* Flatten nested BorderWrappers (per-row containers) */
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.ips-users-table-anchor)) {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.ips-users-table-anchor)) > div {
            padding: 0 !important;
        }

        /* ── Clean user row (CSS grid) ── */
        .usr-row {
            display: grid;
            grid-template-columns: 1.35fr 1.5fr 0.95fr 0.9fr 0.75fr 0.95fr 0.65fr;
            align-items: center;
            gap: 0 8px;
            min-height: 56px;
            padding: 5px 10px;
            background: #ffffff;
            border-bottom: 1px solid #e5eaf2;
            border-left: 4px solid transparent;
            cursor: pointer;
            box-sizing: border-box;
            transition: background 0.12s ease, border-color 0.12s ease;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap):hover .usr-row:not(.selected) {
            background: #f8fbff;
        }
        .usr-row.selected {
            background: #eef5ff;
            border-left-color: #2563eb;
        }
        .usr-name-cell {
            color: #2563eb;
            font-weight: 700;
            font-size: 0.83rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            min-width: 0;
        }
        .usr-row.selected .usr-name-cell { color: #1d4ed8; font-weight: 800; }
        .usr-cell {
            font-size: 0.83rem;
            color: #111827;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            min-width: 0;
            line-height: 1.4;
        }
        .usr-cell.email { font-weight: 500; }
        .usr-cell.muted { color: #6b7280; font-size: 0.79rem; }
        .usr-act-slot { min-height: 1px; }

        /* Row host: relative container for overlays */
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap):not(:has(.ips-users-table-anchor)) {
            position: relative !important;
            margin: 0 !important;
            padding: 0 !important;
            gap: 0 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap):not(:has(.ips-users-table-anchor))
        [data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            min-height: 0 !important;
        }

        /* Invisible full-row select button overlay */
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-row-select-btn)
        + [data-testid="stElementContainer"]:has(.stButton) {
            position: absolute !important;
            top: 0 !important; left: 0 !important;
            right: 100px !important; bottom: 0 !important;
            z-index: 1 !important;
            height: 100% !important;
            margin: 0 !important; padding: 0 !important;
            pointer-events: auto !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-row-select-btn)
        + [data-testid="stElementContainer"]:has(.stButton) .stButton,
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-row-select-btn)
        + [data-testid="stElementContainer"]:has(.stButton) .stButton > button {
            width: 100% !important; height: 100% !important;
            min-height: 56px !important;
            margin: 0 !important; padding: 0 !important;
            opacity: 0 !important;
            border: none !important; background: transparent !important;
            box-shadow: none !important; cursor: pointer !important;
        }

        /* Action buttons: absolutely positioned right */
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-actcol)
        + [data-testid="stElementContainer"] {
            position: absolute !important;
            top: 50% !important; right: 14px !important;
            transform: translateY(-50%) !important;
            z-index: 3 !important; width: 5rem !important;
            pointer-events: auto !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-actcol)
        + [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {
            gap: 0.35rem !important; min-height: unset !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-actcol)
        + [data-testid="stElementContainer"] .stButton > button,
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-actcol)
        + [data-testid="stElementContainer"] [data-testid="stPopover"] > button {
            min-width: 2rem !important; max-width: 2rem !important;
            min-height: 2rem !important; height: 2rem !important;
            padding: 0 !important; font-size: 0.9rem !important;
            border: 1px solid #e2e8f0 !important; border-radius: 6px !important;
            background: #ffffff !important; color: #374151 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-actcol)
        + [data-testid="stElementContainer"] .stButton > button:hover,
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.usr-row-wrap)
        [data-testid="stElementContainer"]:has(.usr-actcol)
        + [data-testid="stElementContainer"] [data-testid="stPopover"] > button:hover {
            background: #f8fafc !important; border-color: #cbd5e1 !important;
        }

        /* Hide helper markers */
        .usr-row-wrap, .usr-row-select-btn, .usr-actcol { display: none !important; }

        /* Zero stMarkdown margins inside table card */
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        .stMarkdown,
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-table-anchor)
        .stMarkdown p { margin: 0 !important; }

        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-detail-anchor) {
            background: #ffffff !important;
            border: 1px solid #93c5fd !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 4px rgba(37, 99, 235, 0.1) !important;
            margin-bottom: 0.5rem !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-detail-anchor) > div {
            padding: 0.85rem 0.95rem 0.95rem !important;
        }
        .ips-users-header-inner {
            display: flex;
            align-items: flex-start;
            gap: 0.65rem;
            min-width: 0;
        }
        .ips-users-header-icon {
            width: 2.4rem;
            height: 2.4rem;
            border-radius: 10px;
            background: #eff6ff;
            color: #2563eb;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }
        .ips-users-header-title {
            margin: 0;
            font-size: 1.15rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.2;
        }
        .ips-users-header-sub {
            margin: 0.1rem 0 0;
            font-size: 0.8125rem;
            color: #6b7280;
            font-weight: 500;
        }
        .ips-users-th {
            color: #9ca3af !important;
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin: 0 !important;
            padding: 0.5rem 0 0.4rem !important;
            border-bottom: 1px solid #e5eaf2;
        }
        .ips-users-th-sort {
            opacity: 0.45;
            font-size: 0.62rem;
            margin-left: 0.2rem;
            font-weight: 600;
        }
        .ips-users-email-cell {
            font-size: 0.8125rem;
            color: #374151;
            font-weight: 500;
        }
        .ips-users-muted-cell {
            font-size: 0.8rem;
            color: #6b7280;
            font-weight: 500;
        }
        .ips-users-summary-card {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 12px;
            padding: 0.7rem 0.8rem;
            height: 100%;
            box-sizing: border-box;
        }
        .ips-users-summary-card h4 {
            margin: 0 0 0.5rem;
            font-size: 0.84rem;
            font-weight: 700;
            color: #111827;
        }
        .ips-users-kv { width: 100%; border-collapse: collapse; }
        .ips-users-kv td {
            padding: 0.28rem 0;
            font-size: 0.78rem;
            vertical-align: middle;
        }
        .ips-users-kv td.k {
            color: #6b7280;
            width: 44%;
            font-weight: 500;
        }
        .ips-users-kv td.v {
            color: #111827;
            font-weight: 600;
            text-align: right;
        }
        .ips-users-kv tr.divider td {
            padding-top: 0.5rem;
            border-top: 1px solid #e5eaf2;
        }
        .ips-users-perm-list { margin: 0.35rem 0 0; padding: 0; list-style: none; }
        .ips-users-perm-list li {
            font-size: 0.78rem;
            color: #374151;
            padding: 0.28rem 0;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }
        .ips-users-perm-list .chk {
            width: 1rem;
            height: 1rem;
            border-radius: 50%;
            background: #dcfce7;
            color: #16a34a;
            font-size: 0.62rem;
            font-weight: 800;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .ips-users-perm-link {
            display: inline-block;
            margin-top: 0.55rem;
            font-size: 0.78rem;
            font-weight: 600;
            color: #2563eb;
            text-decoration: none;
        }
        .ips-users-perm-link:hover { text-decoration: underline; }
        .ips-users-detail-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
            padding-bottom: 0.65rem;
            border-bottom: 1px solid #e5eaf2;
            margin-bottom: 0.55rem;
        }
        .ips-users-detail-identity {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-width: 200px;
        }
        .ips-users-avatar {
            width: 3.25rem;
            height: 3.25rem;
            border-radius: 50%;
            background: #dbeafe;
            color: #1d4ed8;
            font-weight: 700;
            font-size: 1.05rem;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            flex-shrink: 0;
        }
        .ips-users-avatar .dot {
            position: absolute;
            bottom: 1px;
            right: 1px;
            width: 0.6rem;
            height: 0.6rem;
            border-radius: 50%;
            border: 2px solid #fff;
            background: #22c55e;
        }
        .ips-users-avatar .dot.off { background: #9ca3af; }
        .ips-users-detail-name-row {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            flex-wrap: wrap;
        }
        .ips-users-detail-title {
            margin: 0;
            font-size: 1.08rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.2;
        }
        .ips-users-detail-sub {
            margin: 0.2rem 0 0;
            font-size: 0.8rem;
            color: #6b7280;
            font-weight: 500;
        }
        .ips-users-detail-header-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.25rem;
            flex-wrap: wrap;
            padding-bottom: 0.7rem;
            border-bottom: 1px solid #e5eaf2;
            margin-bottom: 0.6rem;
        }
        .ips-users-detail-header-main {
            display: flex;
            align-items: center;
            gap: 2rem;
            flex: 1;
            min-width: 0;
            flex-wrap: wrap;
        }
        .ips-users-detail-meta-row {
            display: flex;
            align-items: flex-start;
            gap: 1.75rem;
            flex-wrap: wrap;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-filter-anchor)
        [data-testid="stTextInput"] input {
            border-radius: 8px !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-users-header-anchor)
        button[kind="secondary"] {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #374151 !important;
            font-weight: 600 !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page)
        .ips-users-overview-grid {
            margin-top: 0.15rem;
        }
        .ips-users-card-stack {
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
        }
        .ips-users-perm-summary-lbl {
            margin: 0.35rem 0 0.15rem;
            font-size: 0.72rem;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .ips-users-meta-block .ico {
            color: #9ca3af;
            font-size: 0.85rem;
            margin-bottom: 0.15rem;
        }
        .ips-users-meta-block .lbl {
            font-size: 0.68rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 600;
        }
        .ips-users-meta-block .val {
            font-size: 0.8125rem;
            color: #111827;
            font-weight: 600;
            margin-top: 0.06rem;
        }
        .ips-users-dept-pill {
            display: inline-block;
            padding: 0.14rem 0.5rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            background: #ffffff;
            color: #475569;
            border: 1px solid #e2e8f0;
            margin: 0.1rem 0.25rem 0.1rem 0;
        }
        .ips-users-audit-footer {
            margin-top: 0.55rem;
            padding-top: 0.55rem;
            border-top: 1px solid #e5eaf2;
        }
        .ips-users-audit-footer p {
            margin: 0.2rem 0;
            font-size: 0.72rem;
            color: #9ca3af;
        }
        .ips-users-audit-footer .by { color: #6b7280; font-weight: 600; }
        section[data-testid="stMain"]:has(.ips-users-page) .stTabs [data-baseweb="tab-list"] {
            gap: 0.25rem !important;
            border-bottom: 1px solid #e5eaf2 !important;
            background: #ffffff !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page) .stTabs [data-baseweb="tab"] {
            background: #ffffff !important;
            color: #6b7280 !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            padding: 0.5rem 0.7rem !important;
            border-radius: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-users-page) .stTabs [aria-selected="true"] {
            color: #2563eb !important;
            border-bottom: 2px solid #2563eb !important;
        }
        .ips-users-badge {
            display: inline-block;
            padding: 0.14rem 0.5rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            background: color-mix(in srgb, var(--ips-badge-color, #64748b) 12%, white);
            color: var(--ips-badge-color, #64748b);
            border: 1px solid color-mix(in srgb, var(--ips-badge-color, #64748b) 28%, white);
            white-space: nowrap;
        }
        .ips-users-badge.inactive {
            background: #fef2f2;
            color: #dc2626;
            border-color: #fecaca;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def role_badge_html(label: str, *, color_key: str | None = None) -> str:
    raw = str(label or "").strip() or "-"
    key = (color_key or raw).strip().lower()
    color = _ROLE_BADGE_COLORS.get(key, "#64748b")
    return (
        '<span class="ips-users-badge" '
        f'style="--ips-badge-color:{html.escape(color)};">{html.escape(raw)}</span>'
    )


def status_badge_html(status: str) -> str:
    raw = str(status or "").strip() or "-"
    key = raw.lower()
    extra = ' inactive' if key == "inactive" else ""
    color = _STATUS_COLORS.get(key, "#64748b")
    return (
        f'<span class="ips-users-badge{extra}" '
        f'style="--ips-badge-color:{html.escape(color)};">{html.escape(raw)}</span>'
    )


def render_users_header_inner_html() -> None:
    st.markdown(
        """
        <div class="ips-users-header-inner">
          <div class="ips-users-header-icon" aria-hidden="true">&#128101;</div>
          <div>
            <p class="ips-users-header-title">Users</p>
            <p class="ips-users-header-sub">Manage system users, roles, and permissions.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def table_header_html(label: str) -> str:
    return (
        f'<p class="ips-users-th">{html.escape(label)}'
        f'<span class="ips-users-th-sort">&#8693;</span></p>'
    )


def summary_card_html(
    *,
    title: str,
    rows: list[tuple[str, str]],
    divider_before: set[str] | None = None,
    html_values: dict[str, str] | None = None,
) -> str:
    div_set = divider_before or set()
    hv = html_values or {}
    body = ""
    for k, v in rows:
        if not k:
            continue
        cls = ' class="divider"' if k in div_set else ""
        v_cell = hv.get(k, html.escape(v or "—"))
        body += f"<tr{cls}><td class='k'>{html.escape(k)}</td><td class='v'>{v_cell}</td></tr>"
    return (
        f'<div class="ips-users-summary-card">'
        f"<h4>{html.escape(title)}</h4>"
        f"<table class='ips-users-kv'>{body}</table></div>"
    )


def permissions_granted_html(granted: list[str]) -> str:
    items = [
        f'<li><span class="chk">✓</span> {html.escape(p)}</li>' for p in granted if p
    ]
    return f'<ul class="ips-users-perm-list">{"".join(items)}</ul>'


def profile_identity_html(
    *,
    initials: str,
    name: str,
    status_html: str,
    role: str,
    department: str,
    active: bool,
) -> str:
    dot_cls = "" if active else " off"
    return (
        f'<div class="ips-users-detail-identity">'
        f'<div class="ips-users-avatar">{html.escape(initials)}'
        f'<span class="dot{dot_cls}"></span></div>'
        f'<div>'
        f'<div class="ips-users-detail-name-row">'
        f'<p class="ips-users-detail-title">{html.escape(name)}</p>'
        f"{status_html}"
        f"</div>"
        f'<p class="ips-users-detail-sub">{html.escape(role)} · {html.escape(department)}</p>'
        f"</div></div>"
    )


def detail_meta_row_html(*, email: str, phone: str, last_login: str) -> str:
    blocks = [
        ("✉", "Email", email),
        ("☎", "Phone", phone),
        ("🕐", "Last Login", last_login),
    ]
    inner = "".join(
        f'<div class="ips-users-meta-block">'
        f'<div class="ico">{html.escape(ico)}</div>'
        f'<div class="lbl">{html.escape(lbl)}</div>'
        f'<div class="val">{html.escape(val or "—")}</div></div>'
        for ico, lbl, val in blocks
    )
    return f'<div class="ips-users-detail-meta-row">{inner}</div>'


def audit_footer_html(*, created: str, created_by: str, updated: str, updated_by: str) -> str:
    return (
        '<div class="ips-users-audit-footer">'
        f"<p><strong>Created</strong> {html.escape(created)} · "
        f'<span class="by">{html.escape(created_by)}</span></p>'
        f"<p><strong>Last Updated</strong> {html.escape(updated)} · "
        f'<span class="by">{html.escape(updated_by)}</span></p>'
        "</div>"
    )


def detail_header_row_html(
    *,
    initials: str,
    name: str,
    status_html: str,
    role: str,
    department: str,
    active: bool,
    email: str,
    phone: str,
    last_login: str,
) -> str:
    return (
        '<div class="ips-users-detail-header-row">'
        '<div class="ips-users-detail-header-main">'
        f"{profile_identity_html(initials=initials, name=name, status_html=status_html, role=role, department=department, active=active)}"
        f"{detail_meta_row_html(email=email, phone=phone, last_login=last_login)}"
        "</div></div>"
    )


def user_info_card_html(
    *,
    rows: list[tuple[str, str]],
    html_values: dict[str, str] | None,
    created: str,
    created_by: str,
    updated: str,
    updated_by: str,
) -> str:
    card = summary_card_html(title="User Information", rows=rows, html_values=html_values)
    audit = audit_footer_html(
        created=created, created_by=created_by, updated=updated, updated_by=updated_by
    )
    return card.replace("</div>", f"{audit}</div>", 1)


def role_permissions_card_html(
    *,
    role_lbl: str,
    role_key: str,
    perm_summary: str,
    granted: list[str],
) -> str:
    return (
        f'<div class="ips-users-summary-card">'
        f"<h4>Role &amp; Permissions</h4>"
        f'<table class="ips-users-kv"><tr><td class="k">Role</td><td class="v">'
        f"{role_badge_html(role_lbl, color_key=role_key)}</td></tr></table>"
        f'<p class="ips-users-perm-summary-lbl">Permission Summary</p>'
        f"{permissions_granted_html(granted)}"
        f'<span class="ips-users-perm-link">View all permissions ›</span></div>'
    )


def dept_pills_html(departments: list[str]) -> str:
    if not departments:
        return '<p style="color:#9ca3af;font-size:0.78rem;margin:0;">No departments assigned</p>'
    return "".join(
        f'<span class="ips-users-dept-pill">{html.escape(d)}</span>' for d in departments if d
    )
