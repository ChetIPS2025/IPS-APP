from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import html as _html
import pandas as pd
import streamlit as st

try:
    from app.ui.page_shell import render_page_header
except ImportError:
    from ui.page_shell import render_page_header  # type: ignore
from auth import current_role
from db import (
    fetch_by_match_admin,
    fetch_one,
    fetch_table,
    fetch_table_admin,
    update_rows_admin,
)

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        inject_table_action_styles,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        inject_table_action_styles,
    )

try:
    from services.delete_safety import delete_estimate_unlink_first
except ImportError:
    from app.services.delete_safety import delete_estimate_unlink_first  # type: ignore

try:
    from services.job_service import job_number_display
except ImportError:
    from app.services.job_service import job_number_display  # type: ignore

from app.utils.formatters import job_display_label

try:
    from services.estimate_import_customer_match import (
        PLACEHOLDER,
        build_sorted_customer_names,
        classify_import_customer_matches,
        name_to_customer_id_map,
        resolve_picked_customer_id,
    )
except ImportError:
    from app.services.estimate_import_customer_match import (  # type: ignore
        PLACEHOLDER,
        build_sorted_customer_names,
        classify_import_customer_matches,
        name_to_customer_id_map,
        resolve_picked_customer_id,
    )

from pages.estimate_editor import (
    blank_estimate,
    coalesce_imported_estimate,
    ensure_state,
    insert_imported_estimate,
    merge_estimate_row_scalar_fields_into_editor,
    parse_estimate_json_bytes,
    render_estimate_editor,
)
from app.estimate.defaults import merge_estimate_narrative_scalars_from_row
from app.estimate.job_scope import ensure_scope_widgets_bound

# ─────────────────────────────────────────────────────────────────────────────
# Estimates list — Jobs-style table with clickable rows and inline detail panel
# ─────────────────────────────────────────────────────────────────────────────

_ESTIMATES_STYLES_KEY = "est_page_styles_v3"

_EST_STATUS_COLORS: dict[str, str] = {
    "draft": "#64748b",
    "sent": "#2563eb",
    "submitted": "#2563eb",
    "in review": "#f59e0b",
    "approved": "#16a34a",
    "accepted": "#16a34a",
    "awarded": "#16a34a",
    "rejected": "#dc2626",
    "declined": "#dc2626",
    "converted": "#7c3aed",
    "po_received": "#7c3aed",
    "closed": "#7c3aed",
}

# Column weights: Est# | Description | Customer | Job# | Status | Created | Updated | Total | View | Edit | Del
_EST_COL_WEIGHTS = [1.05, 2.4, 1.6, 1.0, 1.0, 1.0, 1.0, 1.1, 0.45, 0.45, 0.45]


def _inject_estimates_page_styles() -> None:
    """Inject Jobs-matching CSS for the Estimates list and detail panel."""
    if st.session_state.get(_ESTIMATES_STYLES_KEY):
        return
    st.session_state[_ESTIMATES_STYLES_KEY] = True
    st.markdown(
        """
        <style>
        /* ─── Estimates page marker ─── */
        .ips-est-page-anchor { display: none !important; }

        /* ─── Table header row ─── */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-hdr-anchor) {
            background: #f8fafc !important;
            border: none !important;
            border-bottom: 2px solid rgba(15,23,42,0.09) !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0.25rem 0.5rem 0.2rem !important;
            margin-bottom: 1px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-hdr-anchor) [data-testid="stCaptionContainer"] p {
            color: #6b7280 !important;
            font-size: 0.7rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }

        /* ─── Data rows ─── */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) {
            background: #ffffff !important;
            border: 1px solid rgba(15,23,42,0.07) !important;
            border-left: 3px solid transparent !important;
            border-radius: 6px !important;
            margin-bottom: 2px !important;
            padding: 0.1rem 0.4rem !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
            cursor: pointer !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor):hover {
            background: #f8fafc !important;
            border-left-color: #93c5fd !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-sel) {
            background: #eff6ff !important;
            border-left-color: #2563eb !important;
        }

        /* Row text colours */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) .stMarkdown span {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) [data-testid="stCaptionContainer"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) [data-testid="stCaptionContainer"] p {
            color: #6b7280 !important;
        }

        /* nowrap column layout in rows */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            align-items: center !important;
            column-gap: 0.45rem !important;
            width: 100% !important;
            min-width: 960px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            min-width: 0 !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        /* Cell text style */
        .ips-est-cell {
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #111827 !important;
            font-size: 0.875rem;
            line-height: 1.5;
        }
        .ips-est-cell-muted { color: #6b7280 !important; font-size: 0.8rem; }
        .ips-est-cell-money {
            font-variant-numeric: tabular-nums;
            text-align: right;
        }

        /* Estimate # button styled as plain cell text */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) [data-testid="column"]:first-child .stButton > button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #0f172a !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            text-align: left !important;
            padding: 0.1rem 0.25rem !important;
            min-height: 0 !important;
            height: auto !important;
            justify-content: flex-start !important;
            width: 100% !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-sel) [data-testid="column"]:first-child .stButton > button {
            font-weight: 800 !important;
            color: #1d4ed8 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) [data-testid="column"]:first-child .stButton > button:hover {
            background: transparent !important;
            border: none !important;
        }

        /* Small action buttons inside rows */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-row-anchor) .stButton > button {
            min-height: 1.7rem !important;
            padding: 0.18rem 0.38rem !important;
            font-size: 0.78rem !important;
        }

        /* Status badge — shared with Jobs */
        .ips-est-status-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.22rem 0.52rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            line-height: 1;
            white-space: nowrap;
            background: color-mix(in srgb, var(--estc) 12%, white);
            border: 1px solid color-mix(in srgb, var(--estc) 30%, white);
            color: var(--estc);
        }

        /* ─── Detail panel — matches ips-job-edit-panel-anchor ─── */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            color: #111827 !important;
            padding: 0.75rem !important;
            margin-top: 0.2rem !important;
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) h2,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) h3,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) h4 {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) .stMarkdown span {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stCaptionContainer"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stCaptionContainer"] p {
            color: #4b5563 !important;
        }

        /* Detail panel tabs — identical to Jobs page segmented tabs */
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [role="tablist"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            align-items: center !important;
            gap: 6px !important;
            padding: 6px !important;
            margin: 0 0 0.75rem 0 !important;
            background: #d1d5db !important;
            border: none !important;
            border-bottom: none !important;
            border-radius: 10px !important;
            box-shadow: inset 0 1px 2px rgba(15,23,42,0.05) !important;
            overflow-x: auto !important;
            overflow-y: visible !important;
            scrollbar-width: thin;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [role="tablist"] button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [role="tab"] {
            flex: 0 1 auto !important;
            min-height: 0 !important;
            height: auto !important;
            min-width: 0 !important;
            margin: 0 !important;
            padding: 8px 14px !important;
            border-radius: 10px !important;
            white-space: nowrap !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #111827 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [role="tab"] p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button p {
            color: #111827 !important;
            font-weight: 500 !important;
            margin: 0 !important;
            overflow: visible !important;
            text-overflow: clip !important;
            white-space: nowrap !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [role="tab"][aria-selected="true"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-bottom-color: #cbd5e1 !important;
            box-shadow: 0 1px 3px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.04) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [role="tab"][aria-selected="true"] p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] p {
            color: #111827 !important;
            font-weight: 600 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button:hover:not([aria-selected="true"]) {
            background: rgba(255,255,255,0.42) !important;
        }

        /* Info card layout inside detail panel */
        .ips-est-info-card {
            background: #f8fafc;
            border: 1px solid rgba(15,23,42,0.08);
            border-radius: 10px;
            padding: 0.75rem 1rem 0.65rem;
            height: 100%;
        }
        .ips-est-card-title {
            color: #374151 !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            margin: 0 0 0.55rem 0 !important;
            padding-bottom: 0.4rem !important;
            border-bottom: 1px solid rgba(15,23,42,0.07) !important;
        }
        .ips-est-field-row {
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            padding: 0.2rem 0;
            border-bottom: 1px solid rgba(15,23,42,0.04);
        }
        .ips-est-field-row:last-child { border-bottom: none; }
        .ips-est-field-lbl {
            color: #6b7280;
            font-size: 0.8rem;
            font-weight: 600;
            white-space: nowrap;
            min-width: 110px;
        }
        .ips-est-field-val {
            color: #111827;
            font-size: 0.875rem;
            font-weight: 500;
            text-align: right;
            overflow-wrap: anywhere;
        }
        .ips-est-pricing-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.22rem 0;
            border-bottom: 1px solid rgba(15,23,42,0.04);
        }
        .ips-est-pricing-row:last-child { border-bottom: none; }
        .ips-est-pricing-lbl { color: #374151; font-size: 0.875rem; }
        .ips-est-pricing-val {
            color: #111827;
            font-size: 0.875rem;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
        }
        .ips-est-pricing-total {
            border-top: 2px solid rgba(15,23,42,0.12) !important;
            margin-top: 0.3rem !important;
            padding-top: 0.35rem !important;
        }
        .ips-est-pricing-total .ips-est-pricing-lbl { font-weight: 700; color: #0f172a; }
        .ips-est-pricing-total .ips-est-pricing-val { font-size: 1.05rem; color: #0f172a; }

        /* Detail hero header */
        .ips-est-hero {
            margin: 0 0 0.75rem 0;
            padding-bottom: 0.65rem;
            border-bottom: 1px solid rgba(15,23,42,0.08);
        }
        .ips-est-hero h2 {
            font-size: 1.35rem !important;
            font-weight: 800 !important;
            color: #0f172a !important;
            margin: 0 0 0.2rem 0 !important;
            line-height: 1.2 !important;
        }
        .ips-est-hero-sub {
            color: #475569;
            font-size: 0.9rem;
            margin: 0 0 0.4rem 0;
        }
        .ips-est-hero-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem 1.1rem;
            align-items: center;
            margin-top: 0.4rem;
        }
        .ips-est-hero-meta-item {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.82rem;
        }
        .ips-est-hero-meta-lbl { color: #6b7280; font-weight: 600; }
        .ips-est-hero-meta-val { color: #111827; font-weight: 500; }

        /* Scroll wrapper for table */
        div[data-testid="stVerticalBlock"]:has(.ips-est-scroll-anchor) {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            max-width: 100%;
        }

        /* Tab content text colours */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="column"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor) [data-testid="stVerticalBlock"] {
            min-width: 0 !important;
        }
        @media (max-width: 900px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor)
                div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.65rem !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-est-detail-anchor)
                div[data-testid="stHorizontalBlock"] > [data-testid="column"] {
                flex: 1 1 calc(50% - 0.65rem) !important;
                max-width: 100% !important;
                min-width: min(240px, 100%) !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _est_status_badge(status: Any) -> str:
    """Return inline HTML status pill matching Jobs page style."""
    label = str(status or "").strip() or "—"
    color = _EST_STATUS_COLORS.get(label.lower(), "#64748b")
    return (
        f'<span class="ips-est-status-badge" style="--estc:{_html.escape(color)};">'
        f"{_html.escape(label)}</span>"
    )


def _fmt_date(val: Any, *, short: bool = True) -> str:
    """Format ISO date/datetime for compact table display."""
    if val is None:
        return "—"
    s = str(val).strip()
    if not s or s.lower() in ("none", "null", "nan"):
        return "—"
    return s[:10] if short and len(s) >= 10 else s


def _money_disp(val: Any) -> str:
    """Format a numeric value as $X,XXX.XX or —."""
    if val is None:
        return "—"
    try:
        import math
        f = float(val)
        if math.isnan(f):
            return "—"
        return f"${f:,.2f}"
    except Exception:
        s = str(val).strip()
        return s if s else "—"


def _num0(val: Any) -> float:
    try:
        if val is None:
            return 0.0
        return float(val)
    except Exception:
        return 0.0


def _field_row_html(label: str, value: str) -> str:
    return (
        f'<div class="ips-est-field-row">'
        f'<span class="ips-est-field-lbl">{_html.escape(label)}</span>'
        f'<span class="ips-est-field-val">{_html.escape(value)}</span>'
        f"</div>"
    )


def _pricing_row_html(label: str, value: str, *, total: bool = False) -> str:
    extra = ' ips-est-pricing-total' if total else ''
    return (
        f'<div class="ips-est-pricing-row{extra}">'
        f'<span class="ips-est-pricing-lbl">{_html.escape(label)}</span>'
        f'<span class="ips-est-pricing-val">{_html.escape(value)}</span>'
        f"</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cached data fetchers
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_customers_list_cached(_admin: bool, _v: int) -> list[dict[str, Any]]:
    fn = fetch_table_admin if _admin else fetch_table
    return fn("customers", columns="id,customer_name", limit=5000, order_by="customer_name")


def _fetch_customers_list() -> list[dict[str, Any]]:
    from auth import current_role as _cr
    admin = _cr() in {"admin", "pm"}
    v = int(st.session_state.get("est_data_version", 0))
    return _fetch_customers_list_cached(admin, v)


def _estimates_page_admin_read() -> bool:
    """Internal roles use service-role reads so admin-written rows stay visible under RLS."""
    return current_role() in {"admin", "pm"}


def _fetch_one_estimate_row(estimate_id: str) -> dict[str, Any] | None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    if _estimates_page_admin_read():
        rows = fetch_by_match_admin("estimates", {"id": eid}, limit=1)
        return rows[0] if rows else None
    return fetch_one("estimates", {"id": eid})


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_estimates_list_rows_cached(_admin: bool, _v: int) -> list[dict[str, Any]]:
    if _admin:
        return fetch_table_admin("estimates", limit=1000, order_by="updated_at")
    return fetch_table("estimates", limit=1000, order_by="updated_at")


def _fetch_estimates_list_rows() -> list[dict[str, Any]]:
    v = int(st.session_state.get("est_data_version", 0))
    return _fetch_estimates_list_rows_cached(_estimates_page_admin_read(), v)


def _fetch_customers_for_import() -> list[dict[str, Any]]:
    """Directory rows for matching imported quotes to real customers."""
    if _estimates_page_admin_read():
        return fetch_table_admin(
            "customers",
            columns="id,customer_name",
            limit=3000,
            order_by="customer_name",
        )
    return fetch_table(
        "customers",
        columns="id,customer_name",
        limit=3000,
        order_by="customer_name",
    )


def _fetch_jobs_for_estimate_links() -> list[dict[str, Any]]:
    if _estimates_page_admin_read():
        return fetch_table_admin(
            "jobs",
            columns="id,job_number,estimate_id",
            limit=5000,
            order_by="job_number",
        )
    return fetch_table(
        "jobs",
        columns="id,job_number,estimate_id",
        limit=5000,
        order_by="job_number",
    )


def _cleanup_est_list_row_pick_keys() -> None:
    """Clear per-row list checkbox keys after Select All / Clear so widgets resync to stored IDs."""
    for k in list(st.session_state.keys()):
        if str(k).startswith("est_list_pick_"):
            st.session_state.pop(k, None)


_MONEY_LIST_COLUMNS: frozenset[str] = frozenset({"proposal_total", "final_bid"})


def _estimate_money_display(val: Any) -> str:
    """DB / saved numeric → $ with commas and exactly 2 decimal places (Decimal-safe)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"${d:,.2f}"
    except Exception:
        s = str(val).strip()
        return s[:72] + ("…" if len(s) > 72 else "")


def _estimate_money_csv(val: Any) -> str:
    """Same cents as display; plain numeric string for CSV (2 decimals, no $)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    try:
        d = Decimal(str(val).replace(",", "").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{d:.2f}"
    except Exception:
        return str(val).strip()


def _estimate_list_cell_text(val: Any, col: str | None = None) -> str:
    if col and col in _MONEY_LIST_COLUMNS:
        return _estimate_money_display(val)
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    if len(s) > 72:
        return f"{s[:69]}…"
    return s


_EDITOR_TRANSIENT_PREFIXES: tuple[str, ...] = (
    # New form-based Materials/Labor widgets (avoid stale inputs across estimates)
    "est_material_",
    "est_labor_",
    # Customer/job match helpers
    "est_customer_",
    "est_job_",
    "est_import_cust_",
    # Equipment picker/filter widgets
    "est_eq_",
)


def _reset_estimate_editor_transients(*, clear_import_hints: bool = True) -> None:
    """
    Clear editor-only transient session keys so switching between estimates (or starting a new one)
    doesn't carry over stale widget state that can feel like "double entry" on rerun.
    """
    # Known singleton keys (safe even if absent)
    for k in (
        "est_material_edit_idx",
        "est_labor_edit_idx",
        "materials_editor_db",
        "labor_editor_db",
        "equipment_editor_db",
        "estimates_import_sig",
        "estimates_import_cache",
    ):
        st.session_state.pop(k, None)

    # Prefix-based cleanup for dynamically-indexed edit-form keys.
    to_drop: list[str] = []
    for k in list(st.session_state.keys()):
        if any(str(k).startswith(p) for p in _EDITOR_TRANSIENT_PREFIXES):
            to_drop.append(str(k))
    for k in to_drop:
        st.session_state.pop(k, None)

    if clear_import_hints:
        st.session_state.pop("estimate_pending_import_pdf", None)
        st.session_state.pop("estimate_pdf_suggestions", None)


def _load_estimate_into_session(selected_id: str) -> None:
    _reset_estimate_editor_transients(clear_import_hints=True)
    row = _fetch_one_estimate_row(selected_id)
    if not row:
        return
    loaded = row.get("estimate_json") or {}
    if not isinstance(loaded, dict):
        loaded = {}
    loaded.update({
        "quote_number": row.get("quote_number", "") or "",
        "customer_id": row.get("customer_id"),
        "customer_contact_id": row.get("customer_contact_id"),
        "job_id": row.get("job_id"),
        "status": row.get("status", "draft"),
        "estimate_description": row.get("estimate_description", loaded.get("estimate_description", "")),
        "job_received": row.get("job_received", False),
        "po_number": row.get("po_number", ""),
        "po_date": str(row.get("po_date") or ""),
        "po_amount": float(row.get("po_amount", 0) or 0),
    })
    merge_estimate_narrative_scalars_from_row(row, loaded)
    merge_estimate_row_scalar_fields_into_editor(row, loaded)
    # Only fill missing numeric fields; never overwrites real saved values.
    try:
        from pages.estimate_editor import ensure_numeric_defaults
    except ImportError:
        from app.pages.estimate_editor import ensure_numeric_defaults  # type: ignore
    ensure_numeric_defaults(loaded)
    st.session_state["estimate_editor_state"] = loaded
    st.session_state["loaded_estimate_id"] = selected_id
    st.session_state["estimate_editor_quote_ready"] = True
    # Ensure editor defaults exist (does not overwrite loaded values).
    ensure_state()
    ensure_scope_widgets_bound(loaded, selected_id)


# ─────────────────────────────────────────────────────────────────────────────
# Detail panel sub-components
# ─────────────────────────────────────────────────────────────────────────────


def render_estimate_activity_feed(est_row: dict[str, Any]) -> None:
    """Recent activity card for the Overview tab."""
    lines: list[tuple[str, str]] = []
    created = _fmt_date(est_row.get("created_at"), short=False)
    updated = _fmt_date(est_row.get("updated_at"), short=False)
    status = str(est_row.get("status") or "").strip()
    qn = str(est_row.get("quote_number") or "").strip()
    if updated and updated != "—":
        lines.append(("Last updated", updated[:19]))
    if created and created != "—":
        lines.append(("Created", created[:19]))
    if status:
        lines.append(("Status", status))
    if qn:
        lines.append(("Quote #", qn))
    rows_html = "".join(_field_row_html(lbl, val) for lbl, val in lines) if lines else "<p style='color:#6b7280;font-size:0.85rem;'>No activity data available.</p>"
    st.markdown(
        f'<div class="ips-est-info-card">'
        f'<p class="ips-est-card-title">Recent Activity</p>'
        f"{rows_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_estimate_scope_summary(full_row: dict[str, Any]) -> None:
    """Scope summary card for the Overview tab."""
    scope = str(full_row.get("scope_of_work") or "").strip()
    if not scope:
        ej = full_row.get("estimate_json")
        if isinstance(ej, dict):
            scope = str(ej.get("scope_of_work") or ej.get("scope") or "").strip()
    excl = ""
    ej2 = full_row.get("estimate_json")
    if isinstance(ej2, dict):
        excl = str(ej2.get("exclusions") or "").strip()

    scope_disp = _html.escape(scope[:500] + ("…" if len(scope) > 500 else "")) if scope else "<em style='color:#9ca3af;'>No scope entered.</em>"
    excl_block = (
        f'<p class="ips-est-card-title" style="margin-top:0.5rem;">Exclusions</p>'
        f"<p style='font-size:0.85rem;color:#374151;'>{_html.escape(excl[:300])}</p>"
        if excl else ""
    )
    st.markdown(
        f'<div class="ips-est-info-card">'
        f'<p class="ips-est-card-title">Scope Summary</p>'
        f"<p style='font-size:0.875rem;color:#111827;line-height:1.55;white-space:pre-wrap;'>{scope_disp}</p>"
        f"{excl_block}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_estimate_pricing_summary(full_row: dict[str, Any]) -> None:
    """Pricing summary card for the Overview tab."""
    ej = full_row.get("estimate_json") or {}
    controls = ej.get("controls", {}) if isinstance(ej, dict) else {}

    # Compute component totals from estimate_json items
    labor_items = ej.get("labor", []) if isinstance(ej, dict) else []
    mat_items = ej.get("materials", []) if isinstance(ej, dict) else []
    eq_items = ej.get("equipment", []) if isinstance(ej, dict) else []

    # Attempt to read pre-computed totals from JSON first
    labor_total = _num0(ej.get("labor_total") if isinstance(ej, dict) else None)
    mat_total = _num0(ej.get("material_total") if isinstance(ej, dict) else None)
    eq_total = _num0(ej.get("equipment_total") if isinstance(ej, dict) else None)

    # Fall back to scanning line items if totals are zero
    if labor_total == 0 and labor_items:
        for r in labor_items:
            if isinstance(r, dict):
                labor_total += _num0(r.get("line_total") or r.get("total") or 0)
    if mat_total == 0 and mat_items:
        for r in mat_items:
            if isinstance(r, dict):
                mat_total += _num0(r.get("line_total") or r.get("total") or 0)
    if eq_total == 0 and eq_items:
        for r in eq_items:
            if isinstance(r, dict):
                eq_total += _num0(r.get("line_total") or r.get("total") or 0)

    overhead_pct = _num0(controls.get("overhead_pct") if isinstance(controls, dict) else None)
    profit_pct = _num0(controls.get("profit_pct") if isinstance(controls, dict) else None)
    tax_pct = _num0(controls.get("sales_tax_pct") if isinstance(controls, dict) else None)
    markup_pct = overhead_pct + profit_pct

    subtotal = labor_total + mat_total + eq_total
    markup_amt = subtotal * (markup_pct / 100.0) if markup_pct else 0.0
    tax_amt = (subtotal + markup_amt) * (tax_pct / 100.0) if tax_pct else 0.0
    proposal_total = _num0(full_row.get("proposal_total") or full_row.get("final_bid") or 0)
    grand = proposal_total if proposal_total else (subtotal + markup_amt + tax_amt)

    markup_label = f"Markup / Overhead ({markup_pct:.1f}%)" if markup_pct else "Markup / Overhead"
    tax_label = f"Tax ({tax_pct:.1f}%)" if tax_pct else "Tax"

    rows_html = (
        _pricing_row_html("Labor Total", _money_disp(labor_total))
        + _pricing_row_html("Material Total", _money_disp(mat_total))
        + _pricing_row_html("Equipment Total", _money_disp(eq_total))
        + _pricing_row_html("Subtotal", _money_disp(subtotal))
        + _pricing_row_html(markup_label, _money_disp(markup_amt) if markup_amt else "—")
        + _pricing_row_html(tax_label, _money_disp(tax_amt) if tax_amt else "—")
        + _pricing_row_html("Grand Total", _money_disp(grand), total=True)
    )
    st.markdown(
        f'<div class="ips-est-info-card">'
        f'<p class="ips-est-card-title">Pricing Summary</p>'
        f"{rows_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_estimate_overview_tab(
    full_row: dict[str, Any],
    *,
    customer_name: str,
    job_display: str,
) -> None:
    """Overview tab: 2-column cards (Estimate Details + Pricing Summary) + scope + activity."""
    qn = str(full_row.get("quote_number") or "").strip() or "—"
    status = str(full_row.get("status") or "").strip() or "—"
    desc = str(full_row.get("estimate_description") or "").strip()
    if not desc:
        ej = full_row.get("estimate_json")
        if isinstance(ej, dict):
            desc = str(ej.get("estimate_description") or ej.get("job") or "").strip()
    created_by = ""
    ej2 = full_row.get("estimate_json")
    if isinstance(ej2, dict):
        created_by = str(ej2.get("prepared_by_name") or ej2.get("prepared_by") or "").strip()

    details_html = (
        _field_row_html("Estimate #", qn)
        + _field_row_html("Customer", customer_name or "—")
        + _field_row_html("Job #", job_display or "—")
        + _field_row_html("Status", status)
        + _field_row_html("Description", desc or "—")
        + _field_row_html("Created By", created_by or "—")
        + _field_row_html("Created", _fmt_date(full_row.get("created_at"), short=False)[:10] if full_row.get("created_at") else "—")
        + _field_row_html("Last Updated", _fmt_date(full_row.get("updated_at"), short=False)[:10] if full_row.get("updated_at") else "—")
    )

    col_l, col_r = st.columns(2, gap="medium")
    with col_l:
        st.markdown(
            f'<div class="ips-est-info-card">'
            f'<p class="ips-est-card-title">Estimate Details</p>'
            f"{details_html}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_r:
        render_estimate_pricing_summary(full_row)

    st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

    col_bl, col_br = st.columns(2, gap="medium")
    with col_bl:
        render_estimate_scope_summary(full_row)
    with col_br:
        render_estimate_activity_feed(full_row)


# ─────────────────────────────────────────────────────────────────────────────
# Tab renderers for line-item detail tabs
# ─────────────────────────────────────────────────────────────────────────────


def _render_line_items_tab(
    items: list[dict[str, Any]],
    columns: list[str],
    *,
    empty_msg: str = "No items found.",
) -> None:
    if not items:
        st.caption(empty_msg)
        return
    import pandas as _pd
    df = _pd.DataFrame(items)
    show_cols = [c for c in columns if c in df.columns]
    if show_cols:
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def _render_labor_tab(full_row: dict[str, Any]) -> None:
    ej = full_row.get("estimate_json")
    items = ej.get("labor", []) if isinstance(ej, dict) else []
    _render_line_items_tab(
        items,
        ["classification", "headcount", "st_hours_per_day", "ot_hours_per_day", "days", "line_total"],
        empty_msg="No labor items in this estimate.",
    )


def _render_materials_tab(full_row: dict[str, Any]) -> None:
    ej = full_row.get("estimate_json")
    items = ej.get("materials", []) if isinstance(ej, dict) else []
    _render_line_items_tab(
        items,
        ["item", "description", "qty", "unit", "unit_price", "line_total"],
        empty_msg="No material items in this estimate.",
    )


def _render_equipment_tab(full_row: dict[str, Any]) -> None:
    ej = full_row.get("estimate_json")
    items = ej.get("equipment", []) if isinstance(ej, dict) else []
    _render_line_items_tab(
        items,
        ["equipment_item", "description", "qty", "days", "rate", "line_total"],
        empty_msg="No equipment items in this estimate.",
    )


def _render_financials_tab(full_row: dict[str, Any]) -> None:
    ej = full_row.get("estimate_json") or {}
    controls = ej.get("controls", {}) if isinstance(ej, dict) else {}
    travel = ej.get("travel", {}) if isinstance(ej, dict) else {}

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        render_estimate_pricing_summary(full_row)
    with col2:
        # Controls
        ctrl_html = (
            _field_row_html("Material Markup %", f"{_num0(controls.get('material_markup_pct')):.2f}%")
            + _field_row_html("Overhead %", f"{_num0(controls.get('overhead_pct')):.2f}%")
            + _field_row_html("Profit %", f"{_num0(controls.get('profit_pct')):.2f}%")
            + _field_row_html("Contingency %", f"{_num0(controls.get('contingency_pct')):.2f}%")
            + _field_row_html("Sales Tax %", f"{_num0(controls.get('sales_tax_pct')):.2f}%")
        )
        st.markdown(
            f'<div class="ips-est-info-card"><p class="ips-est-card-title">Pricing Controls</p>{ctrl_html}</div>',
            unsafe_allow_html=True,
        )

    if travel and isinstance(travel, dict):
        travel_total = _num0(travel.get("line_total") or 0)
        if travel_total:
            st.caption(f"Travel / field expenses: {_money_disp(travel_total)}")


def _render_scope_tab(full_row: dict[str, Any]) -> None:
    ej = full_row.get("estimate_json") or {}
    scope = str(full_row.get("scope_of_work") or (ej.get("scope_of_work") if isinstance(ej, dict) else "") or "").strip()
    excl = str((ej.get("exclusions") if isinstance(ej, dict) else "") or "").strip()
    addl = str((ej.get("additional_charges") if isinstance(ej, dict) else "") or "").strip()
    cust_resp = str((ej.get("customer_responsibilities") if isinstance(ej, dict) else "") or "").strip()

    if scope:
        st.markdown("**Scope of Work**")
        st.markdown(scope)
    else:
        st.caption("No scope of work entered.")

    if excl:
        st.markdown("---")
        st.markdown("**Exclusions**")
        st.markdown(excl)
    if addl:
        st.markdown("---")
        st.markdown("**Additional Charges**")
        st.markdown(addl)
    if cust_resp:
        st.markdown("---")
        st.markdown("**Customer Responsibilities**")
        st.markdown(cust_resp)


def _render_notes_tab(full_row: dict[str, Any]) -> None:
    ej = full_row.get("estimate_json") or {}
    notes = str((ej.get("notes") if isinstance(ej, dict) else "") or "").strip()
    if notes:
        st.markdown(notes)
    else:
        st.caption("No notes on this estimate.")


def _render_documents_tab(full_row: dict[str, Any]) -> None:
    """Show attached PDF source if available; otherwise placeholder."""
    source_path = str(full_row.get("source_pdf_path") or "").strip()
    if source_path:
        st.caption(f"Source file: `{source_path}`")
    else:
        st.caption("No documents attached to this estimate. Use the full editor to manage attachments.")


def _render_activity_tab(full_row: dict[str, Any]) -> None:
    lines: list[str] = []
    created = full_row.get("created_at")
    updated = full_row.get("updated_at")
    status = str(full_row.get("status") or "").strip()
    qn = str(full_row.get("quote_number") or "").strip()

    if created:
        lines.append(f"**Created** — {str(created)[:19]}")
    if updated:
        lines.append(f"**Last Updated** — {str(updated)[:19]}")
    if status:
        lines.append(f"**Current Status** — {status}")
    if qn:
        lines.append(f"**Quote #** — {qn}")

    if lines:
        for line in lines:
            st.markdown(line)
    else:
        st.caption("No activity data available.")


# ─────────────────────────────────────────────────────────────────────────────
# Detail panel
# ─────────────────────────────────────────────────────────────────────────────


def render_estimate_detail_panel(
    full_row: dict[str, Any],
    *,
    customer_name: str,
    job_display: str,
    linked_job_id: str | None,
    can_edit: bool,
    on_edit: Any,
    on_collapse: Any,
) -> None:
    """Inline detail panel rendered below the selected estimate row."""
    try:
        from services.job_from_estimate import (
            create_job_from_estimate,
            estimate_status_allows_job_creation,
        )
    except ImportError:
        from app.services.job_from_estimate import (  # type: ignore
            create_job_from_estimate,
            estimate_status_allows_job_creation,
        )

    eid = str(full_row.get("id") or "").strip()
    qn = str(full_row.get("quote_number") or "").strip() or "—"
    desc = str(full_row.get("estimate_description") or "").strip()
    if not desc:
        ej0 = full_row.get("estimate_json")
        if isinstance(ej0, dict):
            desc = str(ej0.get("estimate_description") or ej0.get("job") or "").strip()
    status = str(full_row.get("status") or "").strip()
    proposal_total = _num0(full_row.get("proposal_total") or full_row.get("final_bid") or 0)
    created_at = _fmt_date(full_row.get("created_at"))
    updated_at = _fmt_date(full_row.get("updated_at"))

    with st.container(border=True):
        st.markdown('<span class="ips-est-detail-anchor"></span>', unsafe_allow_html=True)

        # ── Hero header ─────────────────────────────────────────────────────
        hero_meta = (
            f'<div class="ips-est-hero-meta">'
            f'<span class="ips-est-hero-meta-item"><span class="ips-est-hero-meta-lbl">Customer</span>&nbsp;<span class="ips-est-hero-meta-val">{_html.escape(customer_name or "—")}</span></span>'
            f'<span class="ips-est-hero-meta-item">{_est_status_badge(status)}</span>'
            + (f'<span class="ips-est-hero-meta-item"><span class="ips-est-hero-meta-lbl">Job #</span>&nbsp;<span class="ips-est-hero-meta-val">{_html.escape(job_display)}</span></span>' if job_display else "")
            + f'<span class="ips-est-hero-meta-item"><span class="ips-est-hero-meta-lbl">Created</span>&nbsp;<span class="ips-est-hero-meta-val">{_html.escape(created_at)}</span></span>'
            + f'<span class="ips-est-hero-meta-item"><span class="ips-est-hero-meta-lbl">Updated</span>&nbsp;<span class="ips-est-hero-meta-val">{_html.escape(updated_at)}</span></span>'
            + f'<span class="ips-est-hero-meta-item"><span class="ips-est-hero-meta-lbl">Total</span>&nbsp;<span class="ips-est-hero-meta-val">{_html.escape(_money_disp(proposal_total) if proposal_total else "—")}</span></span>'
            + f"</div>"
        )
        title_html = (
            f'<div class="ips-est-hero">'
            f'<h2>{_html.escape(qn)}</h2>'
            f'<p class="ips-est-hero-sub">{_html.escape(desc or "No description")}</p>'
            f"{hero_meta}"
            f"</div>"
        )

        hdr_left, hdr_right = st.columns([3, 2], gap="small")
        with hdr_left:
            st.markdown(title_html, unsafe_allow_html=True)
        with hdr_right:
            btn_cols = st.columns(4, gap="small")
            with btn_cols[0]:
                if st.button("✏ Edit", key=f"est_detail_edit_{eid}", use_container_width=True, type="primary"):
                    on_edit(eid)
            with btn_cols[1]:
                st.button("👁 Preview", key=f"est_detail_preview_{eid}", use_container_width=True, help="Open full estimate editor for preview")
            with btn_cols[2]:
                _can_convert = bool(
                    can_edit
                    and not linked_job_id
                    and estimate_status_allows_job_creation(status)
                )
                if st.button(
                    "→ Job",
                    key=f"est_detail_convert_{eid}",
                    use_container_width=True,
                    disabled=not _can_convert,
                    help="Convert approved estimate to a Job" if _can_convert else "Only approved estimates without a linked job can be converted",
                ):
                    res = create_job_from_estimate(eid)
                    if res.ok:
                        st.success(res.message)
                        st.session_state["est_data_version"] = int(st.session_state.get("est_data_version", 0)) + 1
                        st.rerun()
                    elif res.message:
                        st.error(res.message)
            with btn_cols[3]:
                if st.button("✕ Close", key=f"est_detail_collapse_{eid}", use_container_width=True):
                    on_collapse()

        # ── Delete confirmation ──────────────────────────────────────────────
        pending_del = st.session_state.get("est_pending_delete")
        if pending_del == eid:
            st.warning("Delete this estimate permanently? Linked jobs will be preserved but unlinked.")
            dc1, dc2, _ = st.columns([1, 1, 3], gap="small")
            with dc1:
                if st.button("Confirm Delete", type="primary", key=f"est_del_confirm_{eid}", use_container_width=True):
                    try:
                        from services.delete_safety import delete_estimate_unlink_first
                    except ImportError:
                        from app.services.delete_safety import delete_estimate_unlink_first  # type: ignore
                    try:
                        delete_estimate_unlink_first(eid, admin_read=_estimates_page_admin_read())
                        st.session_state.pop("est_pending_delete", None)
                        st.session_state["selected_estimate_id"] = None
                        st.session_state["est_data_version"] = int(st.session_state.get("est_data_version", 0)) + 1
                        st.success("Estimate deleted.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not delete: {exc}")
            with dc2:
                if st.button("Cancel", key=f"est_del_cancel_{eid}", use_container_width=True):
                    st.session_state.pop("est_pending_delete", None)
                    st.rerun()

        # ── Tabs ─────────────────────────────────────────────────────────────
        tab_names = ["Overview", "Scope", "Labor", "Materials", "Equipment", "Financials", "Documents", "Notes", "Activity"]
        tabs = st.tabs(tab_names)

        with tabs[0]:
            render_estimate_overview_tab(full_row, customer_name=customer_name, job_display=job_display)
        with tabs[1]:
            _render_scope_tab(full_row)
        with tabs[2]:
            _render_labor_tab(full_row)
        with tabs[3]:
            _render_materials_tab(full_row)
        with tabs[4]:
            _render_equipment_tab(full_row)
        with tabs[5]:
            _render_financials_tab(full_row)
        with tabs[6]:
            _render_documents_tab(full_row)
        with tabs[7]:
            _render_notes_tab(full_row)
        with tabs[8]:
            _render_activity_tab(full_row)


# ─────────────────────────────────────────────────────────────────────────────
# Table row renderer
# ─────────────────────────────────────────────────────────────────────────────


def render_estimate_row(
    est_row: Any,
    *,
    idx: int,
    job_by_id: dict[str, Any],
    job_by_estimate_id: dict[str, Any],
    customer_name_by_id: dict[str, str],
    full_row_cache: dict[str, dict[str, Any]],
    can_edit: bool,
) -> None:
    """Render a single estimate table row inside a border container, and if selected, the detail panel below."""
    eid = str(est_row.get("id") or "").strip()
    if not eid:
        return

    is_sel = st.session_state.get("selected_estimate_id") == eid

    # Resolve linked job
    jid = str(est_row.get("job_id") or "").strip()
    linked_job: dict[str, Any] | None = None
    if jid and jid in job_by_id:
        linked_job = job_by_id[jid]
    elif eid in job_by_estimate_id:
        linked_job = job_by_estimate_id[eid]
    linked_job_id: str | None = str(linked_job.get("id") or "") if linked_job else None

    try:
        from app.utils.formatters import job_display_label
    except ImportError:
        from utils.formatters import job_display_label  # type: ignore

    job_display = ""
    if linked_job:
        job_display = job_display_label(linked_job.get("job_number"), linked_job.get("job_name"))

    # Customer name
    cid = str(est_row.get("customer_id") or "").strip()
    customer_name = customer_name_by_id.get(cid, "")

    # Display values
    qn = str(est_row.get("quote_number") or "").strip() or "—"
    status = str(est_row.get("status") or "").strip()
    proposal_total = _num0(est_row.get("proposal_total") or est_row.get("final_bid") or 0)
    created = _fmt_date(est_row.get("created_at"))
    updated = _fmt_date(est_row.get("updated_at"))

    # Description
    desc = str(est_row.get("estimate_description") or "").strip()
    if not desc:
        ej = est_row.get("estimate_json")
        if isinstance(ej, dict):
            desc = str(ej.get("estimate_description") or ej.get("job") or "").strip()
    if not desc:
        sow = str(est_row.get("scope_of_work") or "").strip()
        if sow:
            desc = sow.splitlines()[0].strip()
    desc_disp = desc[:55] + ("…" if len(desc) > 55 else "") if desc else "—"

    sel_cls = "ips-est-row-sel" if is_sel else ""

    with st.container(border=True):
        st.markdown(
            f'<span class="ips-est-row-anchor {sel_cls}"></span>',
            unsafe_allow_html=True,
        )
        rc = st.columns(_EST_COL_WEIGHTS, gap="small")

        # Col 0 — Estimate # (acts as click-to-select)
        with rc[0]:
            if st.button(
                qn,
                key=f"est_row_sel_{eid}_{idx}",
                use_container_width=True,
                help="Click to view details",
            ):
                if is_sel:
                    st.session_state["selected_estimate_id"] = None
                else:
                    st.session_state["selected_estimate_id"] = eid
                st.rerun()

        # Col 1 — Description
        with rc[1]:
            st.markdown(
                f'<span class="ips-est-cell" title="{_html.escape(desc, quote=True)}">{_html.escape(desc_disp)}</span>',
                unsafe_allow_html=True,
            )

        # Col 2 — Customer
        with rc[2]:
            st.markdown(
                f'<span class="ips-est-cell" title="{_html.escape(customer_name, quote=True)}">'
                f"{_html.escape(customer_name[:28] + ('…' if len(customer_name) > 28 else ''))}</span>",
                unsafe_allow_html=True,
            )

        # Col 3 — Job #
        with rc[3]:
            jdisp = job_display[:18] + ("…" if len(job_display) > 18 else "") if job_display else "—"
            st.markdown(
                f'<span class="ips-est-cell" title="{_html.escape(job_display, quote=True)}">{_html.escape(jdisp)}</span>',
                unsafe_allow_html=True,
            )

        # Col 4 — Status
        with rc[4]:
            st.markdown(_est_status_badge(status), unsafe_allow_html=True)

        # Col 5 — Created
        with rc[5]:
            st.markdown(
                f'<span class="ips-est-cell ips-est-cell-muted">{_html.escape(created)}</span>',
                unsafe_allow_html=True,
            )

        # Col 6 — Last Updated
        with rc[6]:
            st.markdown(
                f'<span class="ips-est-cell ips-est-cell-muted">{_html.escape(updated)}</span>',
                unsafe_allow_html=True,
            )

        # Col 7 — Total
        with rc[7]:
            total_str = _money_disp(proposal_total) if proposal_total else "—"
            st.markdown(
                f'<span class="ips-est-cell ips-est-cell-money">{_html.escape(total_str)}</span>',
                unsafe_allow_html=True,
            )

        # Col 8 — View
        with rc[8]:
            if st.button("👁", key=f"est_row_view_{eid}_{idx}", use_container_width=True, help="View details"):
                st.session_state["selected_estimate_id"] = eid if not is_sel else None
                st.rerun()

        # Col 9 — Edit
        with rc[9]:
            if st.button("✏", key=f"est_row_edit_{eid}_{idx}", use_container_width=True, help="Edit estimate", disabled=not can_edit):
                _load_estimate_into_session(eid)
                st.session_state["estimates_view"] = "edit"
                st.rerun()

        # Col 10 — Delete
        with rc[10]:
            if st.button("🗑", key=f"est_row_del_{eid}_{idx}", use_container_width=True, help="Delete estimate", disabled=not can_edit):
                st.session_state["selected_estimate_id"] = eid
                st.session_state["est_pending_delete"] = eid
                st.rerun()

    # ── Inline detail panel ──────────────────────────────────────────────────
    if is_sel:
        # Fetch full row (with estimate_json) if not yet cached
        if eid not in full_row_cache:
            full_row_cache[eid] = _fetch_one_estimate_row(eid) or est_row
        full_row = full_row_cache[eid]

        def _on_edit(e: str) -> None:
            _load_estimate_into_session(e)
            st.session_state["estimates_view"] = "edit"
            st.rerun()

        def _on_collapse() -> None:
            st.session_state["selected_estimate_id"] = None
            st.session_state.pop("est_pending_delete", None)
            st.rerun()

        render_estimate_detail_panel(
            full_row,
            customer_name=customer_name,
            job_display=job_display,
            linked_job_id=linked_job_id,
            can_edit=can_edit,
            on_edit=_on_edit,
            on_collapse=_on_collapse,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Table renderer
# ─────────────────────────────────────────────────────────────────────────────


def render_estimates_table(
    df: pd.DataFrame,
    *,
    job_by_id: dict[str, Any],
    job_by_estimate_id: dict[str, Any],
    customer_name_by_id: dict[str, str],
    can_edit: bool,
) -> None:
    """Render the full estimates table: header row + data rows + inline detail panel."""
    st.markdown('<span class="ips-est-scroll-anchor"></span>', unsafe_allow_html=True)

    # Header row
    with st.container(border=True):
        st.markdown('<span class="ips-est-hdr-anchor"></span>', unsafe_allow_html=True)
        hc = st.columns(_EST_COL_WEIGHTS, gap="small")
        for col_i, label in enumerate(["Estimate #", "Description", "Customer", "Job #", "Status", "Created", "Last Updated", "Total", " ", " ", " "]):
            with hc[col_i]:
                st.caption(label)

    # Per-row full-data cache (populated lazily on first expand)
    full_row_cache: dict[str, dict[str, Any]] = {}

    for idx, (_, row) in enumerate(df.iterrows()):
        render_estimate_row(
            row,
            idx=idx,
            job_by_id=job_by_id,
            job_by_estimate_id=job_by_estimate_id,
            customer_name_by_id=customer_name_by_id,
            full_row_cache=full_row_cache,
            can_edit=can_edit,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Refactored list view
# ─────────────────────────────────────────────────────────────────────────────


def _render_estimate_list() -> None:
    _inject_estimates_page_styles()
    can_edit = current_role() in {"admin", "pm"}

    # ── Data fetching ────────────────────────────────────────────────────────
    rows = _fetch_estimates_list_rows()
    job_rows = _fetch_jobs_for_estimate_links()
    job_by_id: dict[str, Any] = {str(r["id"]): r for r in job_rows if r.get("id")}
    job_by_estimate_id: dict[str, Any] = {str(r["estimate_id"]): r for r in job_rows if r.get("estimate_id")}

    customer_rows = _fetch_customers_list()
    customer_name_by_id: dict[str, str] = {
        str(c.get("id") or ""): str(c.get("customer_name") or "")
        for c in customer_rows if c.get("id")
    }

    df = pd.DataFrame(rows)

    # ── Initialise session state ──────────────────────────────────────────────
    st.session_state.setdefault("selected_estimate_id", None)

    # ── Empty state ──────────────────────────────────────────────────────────
    if df.empty:
        try:
            from app.ui.components.empty_states import render_empty_state
        except ImportError:
            from ui.components.empty_states import render_empty_state  # type: ignore
        if render_empty_state(
            "No estimates found",
            "Create a new estimate or import existing quotes to get started.",
            icon="📄",
            action_label="New estimate",
            action_key="est_list_empty_new",
        ):
            _reset_estimate_editor_transients(clear_import_hints=True)
            st.session_state["estimate_editor_state"] = blank_estimate()
            st.session_state["loaded_estimate_id"] = None
            st.session_state["estimate_editor_quote_ready"] = False
            ensure_state()
            st.session_state["estimates_view"] = "edit"
            st.rerun()
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2 = st.columns([1, 3], gap="small")
    with f1:
        status_opts = ["All"] + sorted(
            df["status"].dropna().astype(str).unique().tolist()
        ) if "status" in df.columns else ["All"]
        sel_status = st.selectbox("Status", status_opts, key="est_list_status")
    with f2:
        search = st.text_input("Search estimates", placeholder="Quote #, customer, description, status…", key="est_list_search")

    filtered = df.copy()
    if sel_status != "All" and "status" in filtered.columns:
        filtered = filtered[filtered["status"] == sel_status]
    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        filtered = filtered[mask.any(axis=1)]

    if filtered.empty:
        st.caption("No estimates match the current filter.")
        return

    st.caption(f"{len(filtered)} estimate{'s' if len(filtered) != 1 else ''}")

    # ── Table ─────────────────────────────────────────────────────────────────
    render_estimates_table(
        filtered,
        job_by_id=job_by_id,
        job_by_estimate_id=job_by_estimate_id,
        customer_name_by_id=customer_name_by_id,
        can_edit=can_edit,
    )



def _import_customer_status_short(cls: dict[str, Any] | None) -> str:
    if not cls:
        return "—"
    res = cls.get("resolution")
    if res == "valid_existing":
        return "ID in file (ok)"
    if res == "auto_single":
        return "Auto-matched"
    if res == "choose_ambiguous":
        return "Pick customer (multi)"
    if res == "choose_open":
        return "Pick customer"
    if res == "choose_required":
        return "Pick customer"
    return "—"


def _render_json_ips_estimate_import() -> None:
    st.markdown("### JSON estimate import")
    st.caption(
        "Upload **JSON** exports (same shape as Review / Save: `estimate_json`). "
        "Each file is matched to your **customer directory** using names in the JSON (or vendor metadata). "
        "Confirm the customer below, then use **Import JSON file(s) to database**. "
        "Vendor **PDF** quotes use the section above. Duplicate quote numbers are reassigned on import."
    )

    uploaded = st.file_uploader(
        "Upload JSON",
        type=["json"],
        accept_multiple_files=True,
        key="est_import_json_upload",
    )

    if not uploaded:
        st.caption("Upload one or more JSON estimate files above to preview and import.")
        return

    sig = tuple((i, f.name, len(f.getvalue())) for i, f in enumerate(uploaded))
    if st.session_state.get("estimates_import_sig") != sig:
        for k in list(st.session_state.keys()):
            if str(k).startswith("est_import_cust_"):
                st.session_state.pop(k, None)
        st.session_state["estimates_import_sig"] = sig
        cust_rows = _fetch_customers_for_import()
        cached: list[dict] = []
        for f in uploaded:
            raw = f.getvalue()
            try:
                parsed = parse_estimate_json_bytes(raw)
                merged = coalesce_imported_estimate(parsed)
                qn = str(merged.get("quote_number", "") or "").strip()
                cls = classify_import_customer_matches(merged, cust_rows)
                cid = merged.get("customer_id")
                row_has_id = bool(cid) and cls.get("resolution") == "valid_existing"
                cached.append(
                    {
                        "file": f.name,
                        "kind": "json",
                        "merged": merged,
                        "error": None,
                        "quote_number": qn or "(will assign)",
                        "has_customer_id": "yes" if row_has_id else "needs confirmation",
                        "customer_classify": cls,
                        "customer_status": _import_customer_status_short(cls),
                    }
                )
            except Exception as exc:
                cached.append(
                    {
                        "file": f.name,
                        "kind": "json",
                        "merged": None,
                        "error": str(exc),
                        "quote_number": "—",
                        "has_customer_id": f"Error: {exc}",
                        "customer_classify": None,
                        "customer_status": "—",
                    }
                )
        st.session_state["estimates_import_cache"] = cached

    rows: list[dict] = st.session_state["estimates_import_cache"]
    cust_rows = _fetch_customers_for_import()
    name_map = name_to_customer_id_map(cust_rows)
    all_names = build_sorted_customer_names(cust_rows)
    select_options = [PLACEHOLDER] + all_names

    preview_df = pd.DataFrame(
        [
            {
                "file": r["file"],
                "kind": r["kind"],
                "quote_number": r["quote_number"],
                "customer": r.get("customer_status", "—"),
            }
            for r in rows
        ]
    )
    st.dataframe(preview_df, use_container_width=True, hide_index=True)

    json_ready = [
        (i, r)
        for i, r in enumerate(rows)
        if r.get("kind") == "json" and r.get("merged") is not None and not r.get("error")
    ]

    if json_ready:
        st.markdown("##### Customer for each JSON file")
        st.caption(
            "Imports must be saved against a **real customer record**. "
            "If we found a single strong name match, the customer is pre-selected — change it if needed. "
            f"You cannot import while **{PLACEHOLDER}** is selected."
        )
        for i, r in json_ready:
            cls = r.get("customer_classify") or classify_import_customer_matches(r["merged"], cust_rows)
            st.markdown(f"**{r['file']}**")
            if cls.get("message"):
                st.info(str(cls["message"]))
            key = f"est_import_cust_{i}"
            if key not in st.session_state:
                default_name: str | None = None
                if cls.get("resolution") in ("valid_existing", "auto_single") and cls.get("customer_id"):
                    cid0 = str(cls["customer_id"])
                    default_name = next((n for n, cid in name_map.items() if cid == cid0), None)
                st.session_state[key] = default_name if default_name else PLACEHOLDER
            st.selectbox(
                "Customer directory",
                select_options,
                key=key,
                help="Pick the customer this estimate belongs to. This must match a row in Customers.",
            )

        st.markdown("##### JSON Import (direct)")
        if st.button(
            "Import JSON file(s) to database",
            type="secondary",
            use_container_width=True,
            key="est_import_json_run",
        ):
            errors: list[str] = []
            ok = 0
            notes: list[str] = []
            cust_lookup = _fetch_customers_for_import()
            nm = name_to_customer_id_map(cust_lookup)
            for i, r in json_ready:
                f = uploaded[i]
                merged = r.get("merged")
                if merged is None:
                    errors.append(f"{f.name}: nothing to import")
                    continue
                chosen = st.session_state.get(f"est_import_cust_{i}")
                cid = resolve_picked_customer_id(chosen_label=chosen, name_to_id=nm)
                if not cid:
                    errors.append(
                        f"{f.name}: choose a customer from the directory before importing "
                        f"(cannot save on {PLACEHOLDER!r})."
                    )
                    continue
                try:
                    raw = f.getvalue()
                    merged_save = dict(merged)
                    merged_save["customer_id"] = cid
                    _, suffix = insert_imported_estimate(
                        merged_save, f.name, raw, source_content_type="application/json"
                    )
                    ok += 1
                    if suffix:
                        notes.append(f"{f.name}:{suffix}")
                except Exception as exc:
                    errors.append(f"{f.name}: {exc}")
            if notes:
                for n in notes:
                    st.info(n)
            if errors:
                for e in errors:
                    st.error(e)
            if ok:
                st.success(f"Imported {ok} JSON estimate(s). Returning to list.")
                st.session_state["estimates_view"] = "list"
                st.rerun()


def _render_estimate_import() -> None:
    """PDF import then JSON import (Estimates page when ``estimates_view == \"import\"``)."""
    try:
        from services.pdf_quote_import import render_vendor_pdf_quote_section
    except ImportError:
        from app.services.pdf_quote_import import render_vendor_pdf_quote_section  # type: ignore

    st.markdown("### PDF vendor quotes")
    render_vendor_pdf_quote_section()

    st.markdown("---")
    _render_json_ips_estimate_import()


def render() -> None:
    st.markdown('<span class="ips-est-page-anchor" aria-hidden="true"></span>', unsafe_allow_html=True)

    if "estimates_view" not in st.session_state:
        st.session_state["estimates_view"] = "list"

    # Legacy session value from older builds
    if st.session_state.get("estimates_view") == "editor":
        st.session_state["estimates_view"] = "edit"

    view = st.session_state["estimates_view"]
    if view not in ("list", "import", "edit"):
        st.session_state["estimates_view"] = "list"
        view = "list"

    inject_table_action_styles()
    _inject_estimates_page_styles()

    try:
        from app.ui.page_shell import action_bar_card
    except ImportError:
        from ui.page_shell import action_bar_card  # type: ignore

    if view == "list":
        render_page_header("Estimates", "Quotes, proposals, and approvals.")
        with action_bar_card(title="Quick Actions"):
            a1, a2 = st.columns(2, gap="small")
            with a1:
                if st.button("New Estimate", type="primary", use_container_width=True, key="est_list_new"):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimate_editor_state"] = blank_estimate()
                    st.session_state["loaded_estimate_id"] = None
                    st.session_state["estimate_editor_quote_ready"] = False
                    ensure_state()
                    st.session_state["estimates_view"] = "edit"
                    st.rerun()
            with a2:
                if st.button(
                    "Import Existing Quotes",
                    type="secondary",
                    use_container_width=True,
                    key="est_list_imp",
                ):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimates_view"] = "import"
                    st.rerun()
        _render_estimate_list()

    elif view == "import":
        render_page_header("Estimates", "PDF or JSON import — return to the list when done.")
        try:
            from app.ui.page_shell import render_card
        except ImportError:
            from ui.page_shell import render_card  # type: ignore
        with render_card():
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("← Back to list", type="secondary", use_container_width=True, key="est_imp_back"):
                    st.session_state["estimates_view"] = "list"
                    st.rerun()
            with c2:
                _render_estimate_import()

    else:
        # view == "edit"
        render_page_header("Estimates", "Line items and save — Back to list when done.")
        with render_card():
            st.markdown(
                '<span class="ips-list-top-anchor ips-estimate-topbar"></span>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("← Back to list", type="secondary", use_container_width=True, key="est_ed_back"):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimates_view"] = "list"
                    st.rerun()
            with c2:
                if st.button(
                    "Import Existing Quotes",
                    type="secondary",
                    use_container_width=True,
                    key="est_ed_imp",
                ):
                    _reset_estimate_editor_transients(clear_import_hints=True)
                    st.session_state["estimates_view"] = "import"
                    st.rerun()
        eid_edit = str(st.session_state.get("loaded_estimate_id") or "").strip()
        if eid_edit:
            try:
                from app.ui.activity import render_activity_panel
            except ImportError:
                from ui.activity import render_activity_panel  # type: ignore
            erow = _fetch_one_estimate_row(eid_edit)
            if erow:
                render_activity_panel(
                    title="Estimate activity",
                    created_at=erow.get("created_at"),
                    updated_at=erow.get("updated_at"),
                    status=erow.get("status"),
                    extra_lines=[
                        ("Quote #", str(erow.get("quote_number") or "—")),
                    ],
                )
        render_estimate_editor(embedded=True)