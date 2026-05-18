"""Pure helper functions for the Jobs module (no Streamlit IO, no DB calls)."""
from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from .constants import (
    COLUMNS_HIDDEN_FROM_TABLE,
    JOB_STATUS_COLORS,
    KEY_EDIT_ID,
    KEY_JOB_MODE,
    KEY_SELECTED_ID,
    KEY_VIEW_MODE,
)


# ---------------------------------------------------------------------------
# Cell display helpers
# ---------------------------------------------------------------------------

def cell_str(val: Any) -> str:
    """Normalise a DataFrame cell to a clean string (handles None / NaN)."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def money_cell(v: Any) -> str:
    """Compact dollar amount for table cells (returns '' for zero/missing)."""
    try:
        if v is None or str(v).strip() == "":
            return ""
        fv = float(v)
        if fv == 0:
            return ""
        return f"${fv:,.0f}"
    except Exception:
        return ""


def money_detail(v: Any) -> str:
    """Full 2-decimal dollar string for detail views."""
    try:
        if v is None or str(v).strip() == "":
            return "—"
        return f"${float(v):,.2f}"
    except Exception:
        return "—"


def card_text(v: Any, fallback: str = "—") -> str:
    s = cell_str(v)
    return s if s else fallback


def status_badge_html(status: Any) -> str:
    label = card_text(status)
    color = JOB_STATUS_COLORS.get(label.strip().lower(), "#64748b")
    return (
        '<span class="ips-status-badge" '
        f'style="--ips-status-color:{html.escape(color)};">{html.escape(label)}</span>'
    )


def render_cell_with_tooltip(container: Any, value: Any, max_len: int = 20) -> None:
    """Single-line cell with native tooltip; max_len accepted but not used (kept for call-site compat)."""
    _ = max_len
    txt = str(value or "").strip()
    if not txt:
        container.markdown(
            '<span class="ips-job-list-cell" style="color:#111827;">—</span>',
            unsafe_allow_html=True,
        )
        return
    container.markdown(
        f'<span class="ips-job-list-cell" title="{html.escape(txt, quote=True)}" '
        f'style="color:#111827;">{html.escape(txt)}</span>',
        unsafe_allow_html=True,
    )


def render_job_name_cell(container: Any, raw: Any, *, max_len: int = 40) -> None:
    """Job name cell — identical logic to render_cell_with_tooltip (kept separate for semantic clarity)."""
    _ = max_len
    render_cell_with_tooltip(container, raw)


def render_money_cell_html(container: Any, raw: Any) -> None:
    amt = money_cell(raw)
    aw_title = ""
    if raw is not None and str(raw).strip() != "":
        aw_title = f' title="{html.escape(str(raw).strip(), quote=True)}"'
    container.markdown(
        f'<span class="ips-job-list-cell ips-job-money-cell"{aw_title} '
        f'style="color:#111827;">{html.escape(amt)}</span>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------

def visible_columns(columns: list[str]) -> list[str]:
    """Strip internal-only columns before rendering the table."""
    return [c for c in columns if c not in COLUMNS_HIDDEN_FROM_TABLE]


def text_snippet(text: str, *, max_len: int = 600) -> str:
    t = (text or "").strip()
    return t if len(t) <= max_len else t[: max_len - 1] + "…"


def safe_date_value(value: Any) -> Any:
    if value is None or str(value).strip() == "":
        return None
    return value


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------

def clear_job_mode() -> None:
    """Return to list view and wipe all job-edit session keys."""
    st.session_state[KEY_VIEW_MODE] = "list"
    st.session_state[KEY_SELECTED_ID] = None
    st.session_state.pop(KEY_JOB_MODE, None)
    st.session_state.pop(KEY_EDIT_ID, None)
    st.session_state.pop("job_number_manual_input", None)


def sync_job_mode_from_view_state() -> None:
    """Keep legacy ``job_mode`` / ``job_edit_id`` in sync with ``job_view_mode``."""
    from auth import current_role  # local to avoid circular at import time

    jvm = str(st.session_state.get(KEY_VIEW_MODE) or "list").strip().lower()
    sid = str(st.session_state.get(KEY_SELECTED_ID) or "").strip()
    can_edit = current_role() in {"admin", "manager"}
    if jvm == "create" and can_edit:
        st.session_state[KEY_JOB_MODE] = "add"
    elif jvm == "edit" and sid and (can_edit or current_role() == "employee"):
        st.session_state[KEY_JOB_MODE] = "edit"
        st.session_state[KEY_EDIT_ID] = sid
    elif jvm == "edit" and not sid:
        st.session_state[KEY_VIEW_MODE] = "list"
        st.session_state[KEY_JOB_MODE] = None


def migrate_legacy_session() -> None:
    """Promote old ``job_mode`` / ``job_edit_id`` keys to the new ``job_view_mode`` schema."""
    jvm = str(st.session_state.get(KEY_VIEW_MODE) or "list").strip().lower()
    if jvm not in ("list", "create"):
        return
    legacy_mode = str(st.session_state.get(KEY_JOB_MODE) or "").strip().lower()
    legacy_id = str(st.session_state.get(KEY_EDIT_ID) or "").strip()
    if legacy_mode in ("edit", "view") and legacy_id:
        st.session_state[KEY_VIEW_MODE] = legacy_mode
        st.session_state[KEY_SELECTED_ID] = legacy_id
    elif legacy_mode == "add":
        st.session_state[KEY_VIEW_MODE] = "create"
        st.session_state[KEY_SELECTED_ID] = None


def job_detail_display_number(row: dict[str, Any] | None, *, has_job_number_column: bool) -> str:
    """Human-facing job number for headers."""
    if not row:
        return ""
    if has_job_number_column:
        jn = str(row.get("job_number") or "").strip()
        if jn:
            return jn
    for k in ("job_id", "id"):
        v = str(row.get(k) or "").strip()
        if v:
            return v
    return ""
