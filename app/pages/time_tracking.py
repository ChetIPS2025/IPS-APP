from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

try:
    from mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected
except ImportError:
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected  # type: ignore

from auth import current_profile, current_role
from branding import render_header
from db import delete_rows, fetch_one, fetch_table, insert_row, update_rows

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_TIME_ENTRIES,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_TIME_ENTRIES,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )

try:
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

try:
    from services.time_grid_service import (
        copy_employee_day_to_day,
        copy_employee_previous_week_to_current,
        delete_employee_week,
        fetch_time_entries_between,
        fill_employee_job_across_week,
        index_by_employee_date,
        monday_of_week,
        sum_employee_week_hours,
        week_dates,
    )
except ImportError:
    from app.services.time_grid_service import (  # type: ignore
        copy_employee_day_to_day,
        copy_employee_previous_week_to_current,
        delete_employee_week,
        fetch_time_entries_between,
        fill_employee_job_across_week,
        index_by_employee_date,
        monday_of_week,
        sum_employee_week_hours,
        week_dates,
    )

TT_EDIT_ROLES = frozenset({"admin", "estimator", "project_manager"})

_OT_THRESHOLD_DEFAULT = 40.0

# Fast entry / autosave session keys (stable across reruns)
TT_AUTOSAVE_KEY = "tt_autosave_enabled"
TT_DEFAULT_HOURS_KEY = "tt_default_hours_for_new_rows"
TT_JOB_LABEL_TO_ID_KEY = "_tt_job_label_to_id_for_callbacks"
TT_EDIT_ID_KEY = "tt_entry_edit_id"
TT_FAST_ENTRY_KEY = "tt_fast_entry_mode"


def _tt_fast_entry() -> bool:
    return bool(st.session_state.get(TT_FAST_ENTRY_KEY, False))


def _week_grid_column_ratios(*, fast: bool) -> list[float]:
    """10 columns: employee (fixed-narrow) + quick-actions + Mon–Sun + Σ.

    Nested ``st.columns`` inside the employee cell breaks Streamlit row layout and
    stacks all day editors under Monday; QA must be its own top-level column.
    """
    if fast:
        return [0.4, 0.22] + [1.8] * 7 + [0.34]
    return [0.5, 0.24] + [1.5] * 7 + [0.36]


def _hours_step(*, fast: bool) -> float:
    """Whole-hour steps in fast mode for quicker keyboard / spinner entry."""
    return 1.0 if fast else 0.5


def _inject_tt_fast_compact_css() -> None:
    """Extra squeeze in Fast Entry Mode (stacked on base dense styles)."""
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) {
            padding: 2px 5px 4px 5px !important;
            margin-bottom: 4px !important;
        }
        .ips-tt-new-row { padding: 2px 4px 4px 4px !important; margin-top: 1px !important; margin-bottom: 1px !important; }
        .ips-tt-entry-gap { height: 2px !important; min-height: 2px !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stNumberInput"] input {
            min-height: 1.15rem !important;
        }
        .ips-tt-day-head { font-size: 10px !important; margin-bottom: 1px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _tt_default_hours() -> float:
    v = st.session_state.get(TT_DEFAULT_HOURS_KEY, 8.0)
    try:
        h = float(v)
    except (TypeError, ValueError):
        return 8.0
    return max(0.0, min(24.0, h))


def _job_label_for_id(job_label_to_id: dict[str, str], job_id: str) -> str | None:
    jid = str(job_id or "")
    for lb, j in job_label_to_id.items():
        if str(j) == jid:
            return lb
    return None


def _persist_time_entry_row(te_id: str, job_label_to_id: dict[str, str]) -> tuple[bool, str | None]:
    """Read widget state for one entry and update DB. Returns (ok, error_message)."""
    jk, hk, nk = f"tt_job_{te_id}", f"tt_h_{te_id}", f"tt_n_{te_id}"
    if jk not in st.session_state:
        return False, None
    job_label = st.session_state.get(jk)
    if not isinstance(job_label, str):
        return False, "Invalid job selection."
    new_jid = job_label_to_id.get(job_label)
    if not new_jid:
        return False, "Pick a valid job."
    hrs = float(st.session_state.get(hk) or 0)
    note = str(st.session_state.get(nk) or "").strip()
    payload = {
        "job_id": new_jid,
        "hours": hrs,
        "notes": note,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        update_rows("time_entries", payload, {"id": te_id})
    except Exception as exc:
        return False, str(exc)
    snap_k = f"tt_row_snap_{te_id}"
    st.session_state[snap_k] = (job_label, hrs, note)
    return True, None


def _maybe_autosave_entry(te_id: str) -> None:
    if not st.session_state.get(TT_AUTOSAVE_KEY):
        return
    jm = st.session_state.get(TT_JOB_LABEL_TO_ID_KEY)
    if not isinstance(jm, dict):
        return
    jk = f"tt_job_{te_id}"
    hk = f"tt_h_{te_id}"
    nk = f"tt_n_{te_id}"
    if jk not in st.session_state:
        return
    job_label = st.session_state.get(jk)
    hrs = float(st.session_state.get(hk) or 0)
    note = str(st.session_state.get(nk) or "").strip()
    if not isinstance(job_label, str):
        return
    candidate = (job_label, hrs, note)
    snap_k = f"tt_row_snap_{te_id}"
    if st.session_state.get(snap_k) == candidate:
        return
    ok, err = _persist_time_entry_row(te_id, jm)
    if ok:
        try:
            st.toast("Saved", icon="✓")
        except Exception:
            pass
    elif err:
        try:
            st.toast(err, icon="⚠")
        except Exception:
            pass


def _autosave_callback_factory(te_id: str):
    def _cb() -> None:
        _maybe_autosave_entry(te_id)

    return _cb


def _flat_panel_autosave_factory(entry_id: str, snap_key: str):
    """on_change for flat edit widgets (keys tt_flat_edit_*)."""

    def _cb() -> None:
        if not st.session_state.get(TT_AUTOSAVE_KEY):
            return
        jm = st.session_state.get(TT_JOB_LABEL_TO_ID_KEY)
        if not isinstance(jm, dict):
            return
        jl = st.session_state.get("tt_flat_edit_job")
        hh = float(st.session_state.get("tt_flat_edit_h") or 0)
        nn = str(st.session_state.get("tt_flat_edit_n") or "").strip()
        if not isinstance(jl, str):
            return
        cand = (jl, hh, nn)
        if st.session_state.get(snap_key) == cand:
            return
        jid = jm.get(jl)
        if not jid:
            return
        try:
            update_rows(
                "time_entries",
                {
                    "job_id": jid,
                    "hours": hh,
                    "notes": nn,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                {"id": str(entry_id)},
            )
            st.session_state[snap_key] = cand
            try:
                st.toast("Saved", icon="✓")
            except Exception:
                pass
        except Exception:
            try:
                st.toast("Save failed", icon="⚠")
            except Exception:
                pass

    return _cb


def _init_row_snap_from_ent(te_id: str, ent: dict, cur_label: str) -> None:
    snap_k = f"tt_row_snap_{te_id}"
    if snap_k not in st.session_state:
        st.session_state[snap_k] = (
            cur_label,
            float(ent.get("hours", 0) or 0),
            str(ent.get("notes") or "").strip(),
        )


def _clear_row_snap(te_id: str) -> None:
    st.session_state.pop(f"tt_row_snap_{te_id}", None)


# Consistent badge colors on dark theme (WCAG-friendly saturation)
_BADGE_PALETTE = [
    "#2563eb",
    "#16a34a",
    "#ca8a04",
    "#9333ea",
    "#db2777",
    "#0d9488",
    "#ea580c",
    "#4f46e5",
    "#0891b2",
    "#c026d3",
]


def _ordered_job_ids_for_badges(job_labels_sorted: list[str], job_label_to_id: dict[str, str]) -> list[str]:
    return [job_label_to_id[lb] for lb in job_labels_sorted if lb in job_label_to_id]


def _job_badge_color(job_id: str, ordered_ids: list[str]) -> str:
    jid = str(job_id)
    if jid in ordered_ids:
        i = ordered_ids.index(jid)
    else:
        i = abs(hash(jid)) % len(_BADGE_PALETTE)
    return _BADGE_PALETTE[i % len(_BADGE_PALETTE)]


def _job_badge_html(job_label: str, job_id: str, ordered_ids: list[str]) -> str:
    c = _job_badge_color(job_id, ordered_ids)
    lab = html.escape(job_label[:42] + ("…" if len(job_label) > 42 else ""))
    return f'<span class="ips-tt-job-badge" style="background:{c};border-color:{c}">{lab}</span>'


def _inject_tt_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"]:has(> div.ips-tt-wrap) {
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 10px;
            padding: 8px 10px 11px 10px;
            margin-bottom: 6px;
        }
        .ips-tt-wrap { }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 0 !important;
        }
        div[data-testid="stHorizontalBlock"] button p {
            white-space: nowrap !important;
        }
        div[data-testid="stHorizontalBlock"] button {
            white-space: nowrap !important;
        }
        .ips-tt-entry-gap {
            display: block;
            height: 4px;
            min-height: 4px;
        }
        hr.ips-tt-entry-sep {
            border: none;
            border-top: 1px solid rgba(100, 116, 139, 0.35);
            margin: 0.2rem 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) {
            border: 1px solid rgba(71, 85, 105, 0.45) !important;
            border-radius: 8px !important;
            padding: 4px 6px 6px 6px !important;
            margin-bottom: 6px !important;
            background: rgba(15, 23, 42, 0.55) !important;
        }
        .ips-tt-new-row {
            border: 1px dashed rgba(100, 116, 139, 0.55);
            border-radius: 6px;
            padding: 3px 5px 5px 5px;
            margin-top: 2px;
            margin-bottom: 2px;
            background: rgba(30, 41, 59, 0.35);
        }
        .ips-tt-new-block {
            margin-top: 2px;
            padding-top: 4px;
            border-top: 1px dashed rgba(100, 116, 139, 0.4);
        }
        .ips-tt-row-over {
            border-left: 4px solid #f87171 !important;
            background: rgba(248, 113, 113, 0.12) !important;
            border-radius: 6px;
            padding-left: 6px !important;
        }
        .ips-tt-day-head {
            color: #9fb6d9 !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            text-align: center !important;
            margin-bottom: 1px !important;
            letter-spacing: 0.02em;
        }
        .ips-tt-day-sum {
            text-align: center !important;
            font-size: 10px !important;
            color: #94a3b8 !important;
            margin-bottom: 3px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) {
            padding: 5px 6px 6px 6px !important;
        }
        /* Day cell row actions — compact, single-line labels */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) button {
            min-height: 1.35rem !important;
            max-height: 1.75rem !important;
            padding: 0.08rem 0.35rem !important;
            font-size: 0.72rem !important;
            border-radius: 5px !important;
            line-height: 1.1 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) button p {
            white-space: nowrap !important;
            font-size: 0.72rem !important;
            line-height: 1.1 !important;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) p {
            word-break: break-word;
        }
        /* Dense inputs: Job / Hours / Notes inside day cards */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stSelectbox"] label,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stNumberInput"] label,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stTextInput"] label {
            min-height: 0 !important;
            padding-bottom: 0 !important;
            margin-bottom: 0 !important;
            font-size: 0.68rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 1.35rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stNumberInput"] input {
            min-height: 1.32rem !important;
            height: 1.32rem !important;
            padding: 0.06rem 0.28rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stTextInput"] input {
            min-height: 1.32rem !important;
            padding: 0.06rem 0.28rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stVerticalBlock"] > div {
            gap: 0.1rem 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stHorizontalBlock"] {
            gap: 0.2rem !important;
            flex-wrap: nowrap !important;
        }
        /* Flat edit panel — same density */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) {
            padding: 6px 8px 8px 8px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 1.35rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) [data-testid="stNumberInput"] input {
            min-height: 1.32rem !important;
            padding: 0.06rem 0.28rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) [data-testid="stTextInput"] input {
            min-height: 1.32rem !important;
            padding: 0.06rem 0.28rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) button {
            min-height: 1.35rem !important;
            max-height: 1.75rem !important;
            padding: 0.08rem 0.35rem !important;
            font-size: 0.72rem !important;
            border-radius: 5px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) button p {
            white-space: nowrap !important;
            font-size: 0.72rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) [data-testid="stHorizontalBlock"] {
            gap: 0.25rem !important;
        }
        /* Top nav row — span lives in first column of same horizontal block */
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-nav-scope) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-nav-scope) [data-testid="stMultiSelect"] button {
            min-height: 1.4rem !important;
            font-size: 0.8rem !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-nav-scope) label[data-testid="stWidgetLabel"] {
            font-size: 0.72rem !important;
            margin-bottom: 0 !important;
        }
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-week-options) [data-testid="stNumberInput"] input {
            min-height: 1.35rem !important;
            font-size: 0.8rem !important;
            padding: 0.08rem 0.35rem !important;
        }
        /* Toolbar (marker span + widgets in same vertical block) */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) [data-testid="stNumberInput"] input,
        div[data-testid="stVerticalBlock"]:has(span.ips-tt-fast-toolbar-scope) [data-testid="stNumberInput"] input {
            min-height: 1.32rem !important;
            font-size: 0.78rem !important;
            padding: 0.06rem 0.3rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) label[data-testid="stWidgetLabel"],
        div[data-testid="stVerticalBlock"]:has(span.ips-tt-fast-toolbar-scope) label[data-testid="stWidgetLabel"] {
            font-size: 0.72rem !important;
            margin-bottom: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) [data-testid="stHorizontalBlock"] {
            gap: 0.2rem !important;
        }
        .ips-tt-flat-title {
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            margin: 0 0 0.2rem 0 !important;
            color: #e2e8f0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-ot-scope) [data-testid="stNumberInput"] input,
        div[data-testid="stVerticalBlock"]:has(span.ips-tt-ot-scope) [data-testid="stNumberInput"] input {
            min-height: 1.32rem !important;
            font-size: 0.8rem !important;
            padding: 0.06rem 0.3rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-ot-scope) label[data-testid="stWidgetLabel"],
        div[data-testid="stVerticalBlock"]:has(span.ips-tt-ot-scope) label[data-testid="stWidgetLabel"] {
            font-size: 0.72rem !important;
            margin-bottom: 0 !important;
        }
        /* Quick actions expander — compact buttons + inputs */
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-qa-panel) button {
            min-height: 1.35rem !important;
            max-height: 1.75rem !important;
            padding: 0.08rem 0.4rem !important;
            font-size: 0.72rem !important;
            border-radius: 5px !important;
        }
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-qa-panel) button p {
            white-space: nowrap !important;
            font-size: 0.72rem !important;
            line-height: 1.1 !important;
        }
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-qa-panel) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 1.35rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-qa-panel) [data-testid="stNumberInput"] input {
            min-height: 1.3rem !important;
            font-size: 0.78rem !important;
            padding: 0.06rem 0.28rem !important;
        }
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-qa-panel) [data-testid="stTextInput"] input {
            min-height: 1.3rem !important;
            font-size: 0.78rem !important;
            padding: 0.06rem 0.28rem !important;
        }
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-qa-panel) [data-testid="stHorizontalBlock"] {
            gap: 0.25rem !important;
        }
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-qa-panel) label[data-testid="stWidgetLabel"] {
            font-size: 0.72rem !important;
            margin-bottom: 0 !important;
        }
        .ips-tt-field-label {
            font-size: 9px !important;
            font-weight: 600 !important;
            color: #94a3b8 !important;
            margin: 0 !important;
            line-height: 1.05 !important;
            padding: 0 !important;
        }
        .ips-tt-metric {
            color: #e2e8f0 !important;
            font-size: 12px !important;
            font-weight: 600 !important;
        }
        .ips-tt-job-badge {
            display: inline-block;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.02em;
            color: #f8fafc !important;
            background: var(--badge, #334155);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 5px;
            padding: 2px 6px;
            margin-bottom: 3px;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ips-tt-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            align-items: center;
        }
        .ips-tt-week-hdr-cell, .ips-tt-week-hdr-day, .ips-tt-week-hdr-sum {
            text-align: center;
            color: #94a3b8 !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            padding: 2px 0 4px 0;
        }
        .ips-tt-week-hdr-emp { text-align: left !important; }
        .ips-tt-week-hdr-qa { min-height: 1px; opacity: 0.35; }
        .ips-tt-week-hdr-title { display: block; color: #cbd5e1 !important; font-size: 10px !important; }
        .ips-tt-wh-dow { display: block; color: #e2e8f0 !important; font-size: 11px !important; }
        .ips-tt-wh-date { display: block; font-size: 10px !important; font-weight: 600 !important; opacity: 0.9; }
        .ips-tt-emp-cell {
            padding: 2px 2px 4px 0;
            line-height: 1.25;
        }
        .ips-tt-emp-name {
            font-size: 0.95rem !important;
            font-weight: 650 !important;
            color: #f1f5f9 !important;
            margin: 0 0 2px 0 !important;
        }
        .ips-tt-emp-total {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            color: #94a3b8 !important;
        }
        button[kind="secondary"][data-testid="stBaseButton-popover"] {
            min-height: 1.5rem !important;
            padding: 0.15rem 0.45rem !important;
            font-size: 0.8rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _parse_date_key(s: str) -> date:
    return date.fromisoformat(s[:10])


def _tt_flat_entry_rows(
    grid_rows: list,
    show_emp_ids: set,
    fj_id: str | None,
    emp_id_to_name: dict[str, str],
    job_id_to_label: dict[str, str],
) -> list[dict]:
    out: list[dict] = []
    for e in grid_rows:
        eid = str(e.get("employee_id") or "")
        if show_emp_ids and eid not in show_emp_ids:
            continue
        jid = str(e.get("job_id") or "")
        if fj_id and jid != fj_id:
            continue
        tid = e.get("id")
        if not tid:
            continue
        out.append(
            {
                "id": tid,
                "employee": emp_id_to_name.get(eid, eid[:8] + "…" if len(eid) > 8 else eid),
                "work_date": str(e.get("work_date") or "")[:10],
                "job": job_id_to_label.get(jid, jid[:8] + "…" if len(jid) > 8 else (jid or "—")),
                "hours": float(e.get("hours") or 0),
                "notes": str(e.get("notes") or ""),
            }
        )
    return out


def _render_week_header_row(*, grid_ratios: list[float], days: list[date]) -> None:
    """Aligned header: employee + QA slot + Mon–Sun + Σ (matches 10-column grid)."""
    h_emp, h_qa, *hday, hlast = st.columns(grid_ratios)
    with h_emp:
        st.markdown(
            '<div class="ips-tt-week-hdr-cell ips-tt-week-hdr-emp">'
            '<span class="ips-tt-week-hdr-title">Employee</span></div>',
            unsafe_allow_html=True,
        )
    with h_qa:
        st.markdown(
            '<div class="ips-tt-week-hdr-cell ips-tt-week-hdr-qa" aria-hidden="true">\u00a0</div>',
            unsafe_allow_html=True,
        )
    for di, d in enumerate(days):
        with hday[di]:
            st.markdown(
                f'<div class="ips-tt-week-hdr-day">'
                f'<span class="ips-tt-wh-dow">{d.strftime("%a")}</span>'
                f'<span class="ips-tt-wh-date">{d.strftime("%b %d")}</span></div>',
                unsafe_allow_html=True,
            )
    with hlast:
        st.markdown(
            '<div class="ips-tt-week-hdr-sum">Σ</div>',
            unsafe_allow_html=True,
        )


def render() -> None:
    render_header("Time Tracking", subtitle="Weekly calendar — fast row entry by employee and job")

    _inject_tt_styles()
    ensure_narrow_viewport_detected()
    try:
        from ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

    role = current_role()
    can_edit = role in TT_EDIT_ROLES

    if can_edit:
        st.session_state.setdefault(TT_FAST_ENTRY_KEY, False)
        fe_l, fe_r = st.columns([1.35, 4.65], gap="small")
        with fe_l:
            st.checkbox(
                "Fast Entry Mode",
                key=TT_FAST_ENTRY_KEY,
                help="Wider day columns, compact rows, default hrs + auto-save only, less helper text.",
            )
        with fe_r:
            if not _tt_fast_entry():
                st.caption("Turn on for dense weekly entry; filters and data logic unchanged.")

    fast = _tt_fast_entry()
    if fast:
        _inject_tt_fast_compact_css()

    pm_row1, pm_row2 = st.columns([4, 1])
    with pm_row1:
        if not fast:
            st.caption(
                "For a **foreman-style crew grid** (all employees × jobs, one day at a time), "
                "use **PM Matrix Time Entry** in the sidebar."
            )
    with pm_row2:
        if st.button("PM Matrix", key="tt_open_pm_matrix", use_container_width=True, help="Open PM Matrix Time Entry"):
            st.session_state[IPS_NAV_PENDING_KEY] = "PM Matrix Time Entry"
            st.rerun()

    today = date.today()
    st.session_state.setdefault("tt_week_start", monday_of_week(today))

    week_start: date = st.session_state["tt_week_start"]
    if week_start.weekday() != 0:
        week_start = monday_of_week(week_start)
        st.session_state["tt_week_start"] = week_start

    days = week_dates(week_start)
    week_end = days[-1]

    # —— Top controls ——
    cnav1, cnav2, cnav3, cnav4, cnav5 = st.columns([1, 1, 1, 2, 2])
    with cnav1:
        st.markdown('<span class="ips-tt-nav-scope" aria-hidden="true"></span>', unsafe_allow_html=True)
        if st.button("◀ Prev week", use_container_width=True, help="Previous week"):
            st.session_state["tt_week_start"] = week_start - timedelta(days=7)
            st.rerun()
    if cnav2.button("Next week ▶", use_container_width=True, help="Next week"):
        st.session_state["tt_week_start"] = week_start + timedelta(days=7)
        st.rerun()
    if cnav3.button("This week", use_container_width=True, help="Jump to this week"):
        st.session_state["tt_week_start"] = monday_of_week(today)
        st.rerun()

    try:
        all_employees = fetch_table("employees", limit=5000, order_by="name")
    except Exception:
        all_employees = []
    active_employees = [e for e in all_employees if e.get("is_active", True) is not False]

    jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000, order_by="job_number"))
    job_label_to_id = {
        job_row_select_label(j): str(j.get("id"))
        for j in jobs
        if j.get("id") and job_row_select_label(j) and job_row_select_label(j) != "—"
    }
    job_labels_sorted = sorted(job_label_to_id.keys(), key=str.casefold)
    job_id_to_label = {v: k for k, v in job_label_to_id.items()}
    st.session_state[TT_JOB_LABEL_TO_ID_KEY] = job_label_to_id

    emp_choices = {f"{e.get('name', '')} ({str(e.get('id'))[:8]})": str(e.get("id")) for e in active_employees if e.get("id")}
    emp_label_list = sorted(emp_choices.keys(), key=str.casefold)
    filt_emp = cnav4.multiselect(
        "Filter employees",
        options=emp_label_list,
        default=emp_label_list,
        help=None if fast else "Restrict which rows are shown.",
    )
    show_emp_ids = {emp_choices[lb] for lb in filt_emp} if filt_emp else set(emp_choices.values())

    job_opts = ["(All jobs)"] + job_labels_sorted
    filt_job = cnav5.selectbox(
        "Filter job (new entries default)",
        options=job_opts,
        index=0,
        help=None
        if fast
        else "When not “All”, new time lines default to this job; existing lines for other jobs still show.",
    )
    default_job_label = None if filt_job == "(All jobs)" else filt_job

    if fast:
        with st.expander("Week options", expanded=False):
            st.markdown('<span class="ips-tt-week-options" aria-hidden="true"></span>', unsafe_allow_html=True)
            ot_threshold = st.number_input(
                "Weekly OT highlight (h)",
                min_value=0.0,
                max_value=120.0,
                value=float(st.session_state.get("tt_ot_threshold", _OT_THRESHOLD_DEFAULT)),
                step=1.0,
                key="tt_ot_threshold_input",
            )
    else:
        with st.container():
            st.markdown('<span class="ips-tt-ot-scope" aria-hidden="true"></span>', unsafe_allow_html=True)
            ot_threshold = st.number_input(
                "Weekly hours threshold (overtime highlight)",
                min_value=0.0,
                max_value=120.0,
                value=float(st.session_state.get("tt_ot_threshold", _OT_THRESHOLD_DEFAULT)),
                step=1.0,
                key="tt_ot_threshold_input",
            )
    st.session_state["tt_ot_threshold"] = ot_threshold

    # —— Load grid data ——
    try:
        grid_rows = fetch_time_entries_between(week_start, week_end)
    except Exception as exc:
        grid_rows = []
        st.error(f"Could not load time_entries: {exc}. Run `sql/009_time_entries.sql` in Supabase.")
    idx = index_by_employee_date(grid_rows)

    visible_emps = [e for e in active_employees if str(e.get("id")) in show_emp_ids]
    if not visible_emps:
        st.warning("No employees match the filter. Adjust filters or add employees (**Users** → Employees).")
        return

    # —— Summary metrics ——
    def _in_week(x: dict) -> bool:
        try:
            wd = _parse_date_key(str(x.get("work_date")))
            return week_start <= wd <= week_end
        except Exception:
            return False

    week_total = sum(float(x.get("hours", 0) or 0) for x in grid_rows if _in_week(x))
    m1, m2, m3 = st.columns(3)
    m1.metric("Week starting", week_start.isoformat())
    m2.metric("Week ending", week_end.isoformat())
    m3.metric("Total hours (visible week data)", f"{week_total:.2f}")

    ordered_job_ids = _ordered_job_ids_for_badges(job_labels_sorted, job_label_to_id)
    with st.expander("Job color key", expanded=False):
        parts = [
            _job_badge_html(lb, job_label_to_id[lb], ordered_job_ids)
            for lb in job_labels_sorted[:60]
            if lb in job_label_to_id
        ]
        st.markdown(
            '<div class="ips-tt-legend">' + "".join(parts) + "</div>",
            unsafe_allow_html=True,
        )
        if len(job_labels_sorted) > 60:
            st.caption("Showing first 60 jobs; colors repeat by job order.")

    if not fast:
        st.caption(
            "Each **employee × job × day** is unique. Hours save to **time_entries**. "
            "Approved rows in **employee_time_entries** (legacy) are still included in Job Costing."
        )

    fj_id = job_label_to_id.get(default_job_label) if default_job_label else None
    emp_id_to_name = {
        str(e.get("id")): str(e.get("name") or "").strip() or "—"
        for e in active_employees
        if e.get("id")
    }
    flat_rows = _tt_flat_entry_rows(grid_rows, show_emp_ids, fj_id, emp_id_to_name, job_id_to_label)
    entries_df = pd.DataFrame(flat_rows)

    if can_edit:
        st.session_state.setdefault(TT_DEFAULT_HOURS_KEY, 8.0)
        st.session_state.setdefault(TT_AUTOSAVE_KEY, False)
        with st.container(border=True):
            st.markdown(
                '<span class="ips-tt-fast-toolbar-scope" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            if fast:
                tb1, tb2 = st.columns([1.4, 1.25], gap="small")
                with tb1:
                    dh = st.number_input(
                        "Def hrs",
                        min_value=0.0,
                        max_value=24.0,
                        value=float(_tt_default_hours()),
                        step=_hours_step(fast=True),
                        key="tt_toolbar_default_hrs",
                        label_visibility="visible",
                    )
                    st.session_state[TT_DEFAULT_HOURS_KEY] = float(dh)
                with tb2:
                    st.checkbox("Auto-save", key=TT_AUTOSAVE_KEY)
            else:
                tb1, tb2, tb3 = st.columns([1.15, 1.35, 4.0], gap="small")
                with tb1:
                    dh = st.number_input(
                        "Default hrs",
                        min_value=0.0,
                        max_value=24.0,
                        value=float(_tt_default_hours()),
                        step=0.5,
                        key="tt_toolbar_default_hrs",
                        help="Prefills new-line hours for each day.",
                    )
                    st.session_state[TT_DEFAULT_HOURS_KEY] = float(dh)
                with tb2:
                    st.checkbox(
                        "Auto-save",
                        key=TT_AUTOSAVE_KEY,
                        help="When on, job / hours / notes save on change. Save still works for explicit commit.",
                    )
                with tb3:
                    st.caption(
                        "**Save / Del / Dup** — stable keys by entry id; one job line per employee per day."
                    )

    tv_id = st.session_state.get("tt_entry_view_id")
    if tv_id:
        vr = fetch_one("time_entries", {"id": tv_id})
        if not vr:
            st.session_state.pop("tt_entry_view_id", None)
        else:
            st.subheader("Time entry detail")
            e_nm = emp_id_to_name.get(str(vr.get("employee_id") or ""), "—")
            j_nm = job_id_to_label.get(str(vr.get("job_id") or ""), "—")
            st.markdown(f"**Employee:** {e_nm}")
            st.markdown(f"**Work date:** {vr.get('work_date') or '—'}")
            st.markdown(f"**Job:** {j_nm}")
            st.markdown(f"**Hours:** {float(vr.get('hours') or 0):.2f}")
            st.markdown(f"**Notes:** {vr.get('notes') or '—'}")
            if st.button("← Week", use_container_width=True, key="tt_entry_view_back", help="Back to week grid"):
                st.session_state.pop("tt_entry_view_id", None)
                st.rerun()
            st.divider()

    te_ed = st.session_state.get(TT_EDIT_ID_KEY)
    if te_ed and can_edit:
        er = fetch_one("time_entries", {"id": te_ed})
        if not er:
            st.session_state.pop(TT_EDIT_ID_KEY, None)
        else:
            with st.container(border=True):
                st.markdown(
                    '<span class="ips-tt-flat-panel" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<p class="ips-tt-flat-title">Edit time entry</p>',
                    unsafe_allow_html=True,
                )
                cur_jid = str(er.get("job_id") or "")
                cur_label = next(
                    (lb for lb, j in job_label_to_id.items() if j == cur_jid),
                    job_labels_sorted[0] if job_labels_sorted else "",
                )
                j_ix = job_labels_sorted.index(cur_label) if cur_label in job_labels_sorted else 0
                flat_id = str(te_ed)
                snap_flat = f"tt_row_snap_flat_{flat_id}"
                if snap_flat not in st.session_state:
                    st.session_state[snap_flat] = (
                        cur_label,
                        float(er.get("hours") or 0),
                        str(er.get("notes") or "").strip(),
                    )

                fe = _tt_fast_entry()
                ec1, ec2, ec3, ec4 = (
                    st.columns([2.85, 0.62, 1.75, 0.95], gap="small")
                    if fe
                    else st.columns([2.55, 0.58, 1.85, 0.95], gap="small")
                )
                autosave = bool(st.session_state.get(TT_AUTOSAVE_KEY))
                flat_ac = _flat_panel_autosave_factory(str(te_ed), snap_flat) if autosave else None
                ac_kw = {"on_change": flat_ac} if flat_ac else {}

                with ec1:
                    jp = st.selectbox(
                        "Job",
                        job_labels_sorted,
                        index=j_ix,
                        key="tt_flat_edit_job",
                        label_visibility="collapsed",
                        **ac_kw,
                    )
                with ec2:
                    hrs = st.number_input(
                        "Hours",
                        min_value=0.0,
                        max_value=24.0,
                        value=float(er.get("hours") or 0),
                        step=_hours_step(fast=fe),
                        format="%.2f",
                        key="tt_flat_edit_h",
                        label_visibility="collapsed",
                        **ac_kw,
                    )
                with ec3:
                    note = st.text_input(
                        "Notes",
                        value=str(er.get("notes") or ""),
                        key="tt_flat_edit_n",
                        label_visibility="collapsed",
                        placeholder="Notes",
                        **ac_kw,
                    )
                with ec4:
                    bc1, bc2 = st.columns(2, gap="small")
                    with bc1:
                        if st.button("Save", use_container_width=True, key="tt_flat_edit_sv", help="Save changes"):
                            new_jid = job_label_to_id.get(jp)
                            if not new_jid:
                                st.error("Pick a job.")
                            else:
                                payload = {
                                    "job_id": new_jid,
                                    "hours": float(hrs or 0),
                                    "notes": str(note).strip(),
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                }
                                try:
                                    update_rows("time_entries", payload, {"id": str(te_ed)})
                                    st.session_state.pop(TT_EDIT_ID_KEY, None)
                                    st.session_state.pop(snap_flat, None)
                                    st.success("Updated.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Save failed: {exc}")
                    with bc2:
                        if st.button("Cancel", use_container_width=True, key="tt_flat_edit_ca", help="Discard edits"):
                            st.session_state.pop(TT_EDIT_ID_KEY, None)
                            st.session_state.pop(snap_flat, None)
                            st.rerun()

                st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)

    if not entries_df.empty and "id" in entries_df.columns:
        st.subheader("Time entries (this week)")
        if not _tt_fast_entry():
            st.caption(
                "Action bar above the grid. Checkbox on the **left**; selection: **selected_time_entries_ids**."
            )
        show_flat = [c for c in ["employee", "work_date", "job", "hours", "notes"] if c in entries_df.columns]
        bar_ph = st.empty()
        _, sel = render_selectable_dataframe(
            entries_df,
            table_key=TABLE_KEY_TIME_ENTRIES,
            id_column="id",
            columns=show_flat,
            editor_key="tt_flat_sel_editor",
        )
        with bar_ph.container():
            actions = render_selection_action_bar(
                TABLE_KEY_TIME_ENTRIES,
                sel,
                can_view=True,
                can_edit=can_edit,
                can_delete=can_edit,
                export_df=entries_df,
                visible_df=entries_df,
                id_column="id",
                export_filename="time_entries_week_export.csv",
                view_label="View Entry",
                edit_label="Edit Entry",
                delete_label="Delete Entry",
                delete_selected_label="Delete Selected",
            )
        if actions.get("view") and sel and len(sel) == 1:
            st.session_state["tt_entry_view_id"] = str(sel[0])
            st.session_state.pop(TT_EDIT_ID_KEY, None)
            st.rerun()
        if actions.get("edit") and sel and len(sel) == 1 and can_edit:
            st.session_state[TT_EDIT_ID_KEY] = str(sel[0])
            st.session_state.pop("tt_entry_view_id", None)
            st.rerun()
        pend = st.session_state.get(IPS_PENDING_DELETE) or {}
        if actions.get("confirm_delete") and pend.get(TABLE_KEY_TIME_ENTRIES) and can_edit:
            for tid in pend[TABLE_KEY_TIME_ENTRIES]:
                try:
                    delete_rows("time_entries", {"id": tid})
                except Exception as exc:
                    st.error(f"Could not delete {tid}: {exc}")
            pend.pop(TABLE_KEY_TIME_ENTRIES, None)
            clear_selected_ids(TABLE_KEY_TIME_ENTRIES)
            st.success("Delete completed where permitted.")
            st.rerun()

    if not can_edit:
        st.info("View-only mode. Sign in as admin, estimator, or project manager to log time.")
        _render_readonly_pivot(visible_emps, days, idx, job_id_to_label)
        return

    # —— Editable grid —— weekly timesheet: header + employee rows (wide) or stacked days (narrow)
    day_col_totals = [0.0] * 7
    uid = current_profile().get("id")
    ts_now = datetime.now(timezone.utc).isoformat()
    grid_ratios = _week_grid_column_ratios(fast=fast)
    is_narrow = bool(st.session_state.get(IPS_VIEWPORT_NARROW_KEY))

    if not is_narrow:
        _render_week_header_row(grid_ratios=grid_ratios, days=days)

    for emp in visible_emps:
        eid = str(emp.get("id"))
        row_h = sum_employee_week_hours(grid_rows, eid, days)
        over = row_h > ot_threshold
        nm = str(emp.get("name", "") or "—")
        tot_s = f"{row_h:.1f} h" if fast else f"{row_h:.1f} h / week"

        def _emp_name_block() -> None:
            if over:
                st.markdown(
                    f'<div class="ips-tt-emp-cell">'
                    f'<p class="ips-tt-emp-name ips-tt-row-over">{nm}</p>'
                    f'<p class="ips-tt-emp-total">{tot_s} · over {ot_threshold:g} h</p></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="ips-tt-emp-cell">'
                    f'<p class="ips-tt-emp-name">{nm}</p>'
                    f'<p class="ips-tt-emp-total">{tot_s}</p></div>',
                    unsafe_allow_html=True,
                )

        if is_narrow:
            with st.container(border=True):
                h_top_l, h_top_r = st.columns([3.2, 1.0], gap="small")
                with h_top_l:
                    _emp_name_block()
                with h_top_r:
                    _render_quick_actions(
                        eid=eid,
                        days=days,
                        week_start=week_start,
                        week_end=week_end,
                        job_labels_sorted=job_labels_sorted,
                        job_label_to_id=job_label_to_id,
                        user_id=uid,
                        ts_iso=ts_now,
                    )
                for di, d in enumerate(days):
                    ds = _render_day_column_body(
                        d=d,
                        eid=eid,
                        idx=idx,
                        fj_id=fj_id,
                        job_labels_sorted=job_labels_sorted,
                        job_label_to_id=job_label_to_id,
                        default_job_label=default_job_label,
                        fast=fast,
                        show_day_heading=True,
                        compact=True,
                    )
                    day_col_totals[di] += ds
                st.markdown(
                    f'<p class="ips-tt-metric" style="text-align:right;margin-top:0.35rem;">Week Σ · {row_h:.1f} h</p>',
                    unsafe_allow_html=True,
                )
        else:
            row_container = st.container(border=True)
            with row_container:
                h_emp, h_qa, *hday, hlast = st.columns(grid_ratios)
                with h_emp:
                    _emp_name_block()
                with h_qa:
                    _render_quick_actions(
                        eid=eid,
                        days=days,
                        week_start=week_start,
                        week_end=week_end,
                        job_labels_sorted=job_labels_sorted,
                        job_label_to_id=job_label_to_id,
                        user_id=uid,
                        ts_iso=ts_now,
                    )
                for di, d in enumerate(days):
                    with hday[di]:
                        ds = _render_day_column_body(
                            d=d,
                            eid=eid,
                            idx=idx,
                            fj_id=fj_id,
                            job_labels_sorted=job_labels_sorted,
                            job_label_to_id=job_label_to_id,
                            default_job_label=default_job_label,
                            fast=fast,
                            show_day_heading=False,
                            compact=True,
                        )
                        day_col_totals[di] += ds
                with hlast:
                    st.caption("Σ")
                    st.markdown(f'<p class="ips-tt-metric">{row_h:.1f}</p>', unsafe_allow_html=True)

    # Footer totals row
    st.markdown("##### Week totals")
    f_emp, f_qa, *fday, fl = st.columns(grid_ratios)
    with f_emp:
        st.markdown("**Day Σ**")
    with f_qa:
        st.markdown('<span class="ips-tt-footer-qa-spacer"></span>', unsafe_allow_html=True)
    for di, d in enumerate(days):
        with fday[di]:
            st.markdown(f'<p class="ips-tt-metric">{day_col_totals[di]:.1f} h</p>', unsafe_allow_html=True)
    with fl:
        st.markdown(f'<p class="ips-tt-metric">{sum(day_col_totals):.1f}</p>', unsafe_allow_html=True)


def _render_quick_actions(
    *,
    eid: str,
    days: list[date],
    week_start: date,
    week_end: date,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    user_id,
    ts_iso: str,
) -> None:
    day_labels = [d.strftime("%a %m/%d") for d in days]
    with st.popover("⚡", help="Copy day/week, fill week, clear week"):
        st.markdown(
            '<span class="ips-tt-qa-panel" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        st.caption("Copy **previous calendar day** into selected day (Mon ← Sun).")
        qd1, qd2 = st.columns([1.55, 1.0], gap="small")
        with qd1:
            st.markdown('<p class="ips-tt-field-label">To day</p>', unsafe_allow_html=True)
            dest_pick = st.selectbox(
                "Destination day",
                day_labels,
                key=f"tt_qdest_{eid}",
                label_visibility="collapsed",
            )
        with qd2:
            st.markdown('<p class="ips-tt-field-label">\u00a0</p>', unsafe_allow_html=True)
            if st.button(
                "Copy prev → day",
                key=f"tt_cpday_{eid}",
                use_container_width=True,
                help="Copy previous calendar day into the selected day",
            ):
                di = day_labels.index(dest_pick)
                dest_date = days[di]
                from_date = dest_date - timedelta(days=1)
                try:
                    copy_employee_day_to_day(
                        employee_id=eid,
                        from_date=from_date,
                        to_date=dest_date,
                        created_by=user_id,
                        updated_at_iso=ts_iso,
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        if st.button(
            "Copy prev week",
            key=f"tt_cpw_{eid}",
            use_container_width=True,
            help="Copy entire previous calendar week into this week (replaces)",
        ):
            try:
                copy_employee_previous_week_to_current(
                    employee_id=eid,
                    dest_week_start=week_start,
                    created_by=user_id,
                    updated_at_iso=ts_iso,
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        st.caption("Fill one job across Mon–Sun (upserts hours per day).")
        fq1, fq2, fq3, fq4 = st.columns([1.85, 0.68, 1.25, 0.95], gap="small")
        with fq1:
            st.markdown('<p class="ips-tt-field-label">Job</p>', unsafe_allow_html=True)
            fill_j = st.selectbox("Job", job_labels_sorted, key=f"tt_fillj_{eid}", label_visibility="collapsed")
        with fq2:
            st.markdown('<p class="ips-tt-field-label">Hrs/d</p>', unsafe_allow_html=True)
            fill_h = st.number_input(
                "Hours per day",
                0.0,
                24.0,
                8.0,
                step=0.5,
                key=f"tt_fillh_{eid}",
                label_visibility="collapsed",
            )
        with fq3:
            st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
            fill_n = st.text_input("Notes (optional)", "", key=f"tt_filln_{eid}", label_visibility="collapsed")
        with fq4:
            st.markdown('<p class="ips-tt-field-label">\u00a0</p>', unsafe_allow_html=True)
            if st.button(
                "Fill week",
                key=f"tt_fill_{eid}",
                use_container_width=True,
                help="Fill selected job across Mon–Sun (upserts hours per day)",
            ):
                jid = job_label_to_id.get(fill_j)
                if not jid:
                    st.error("Pick a job.")
                else:
                    try:
                        fill_employee_job_across_week(
                            employee_id=eid,
                            job_id=jid,
                            week_dates=days,
                            hours_per_day=float(fill_h),
                            notes=str(fill_n).strip(),
                            created_by=user_id,
                            updated_at_iso=ts_iso,
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        st.caption("Delete every **time_entries** row for this employee in this week.")
        confirm = st.checkbox("I understand entries will be removed", key=f"tt_clr_{eid}")
        if st.button(
            "Clear week",
            key=f"tt_clrb_{eid}",
            disabled=not confirm,
            use_container_width=True,
            help="Delete all time entries for this employee this week",
        ):
            try:
                delete_employee_week(eid, week_start, week_end)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _render_entry_editor(
    ent: dict,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    *,
    fast: bool,
    compact: bool = False,
) -> None:
    te_id = str(ent.get("id"))
    cur_jid = str(ent.get("job_id") or "")
    cur_label = next(
        (lb for lb, j in job_label_to_id.items() if j == cur_jid),
        job_labels_sorted[0] if job_labels_sorted else "",
    )
    j_ix = job_labels_sorted.index(cur_label) if cur_label in job_labels_sorted else 0
    _init_row_snap_from_ent(te_id, ent, cur_label)

    autosave = bool(st.session_state.get(TT_AUTOSAVE_KEY))
    acb = _autosave_callback_factory(te_id)
    ch_as = {"on_change": acb} if autosave else {}

    hstep = _hours_step(fast=fast)
    del_label = "Clear" if fast else "Delete"
    del_help = "Remove this time entry" if fast else "Delete this time entry"

    def _save_del_row() -> None:
        b_save, b_del = st.columns(2, gap="small")
        with b_save:
            if st.button(
                "Save",
                key=f"tt_sv_{te_id}",
                use_container_width=True,
                help="Save this row",
            ):
                ok, err = _persist_time_entry_row(te_id, job_label_to_id)
                if ok:
                    st.success("Updated.")
                    st.rerun()
                elif err:
                    st.error(err)
        with b_del:
            if st.button(
                del_label,
                key=f"tt_del_{te_id}",
                use_container_width=True,
                help=del_help,
            ):
                try:
                    delete_rows("time_entries", {"id": te_id})
                    _clear_row_snap(te_id)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")

    if compact:
        st.markdown('<p class="ips-tt-field-label">Job</p>', unsafe_allow_html=True)
        st.selectbox(
            "Job",
            job_labels_sorted,
            index=j_ix,
            key=f"tt_job_{te_id}",
            label_visibility="collapsed",
            **ch_as,
        )
        ch, cn = st.columns([0.45, 1.0], gap="small")
        with ch:
            st.markdown('<p class="ips-tt-field-label">Hrs</p>', unsafe_allow_html=True)
            st.number_input(
                "Hours",
                min_value=0.0,
                max_value=24.0,
                value=float(ent.get("hours", 0) or 0),
                step=hstep,
                format="%.2f",
                key=f"tt_h_{te_id}",
                label_visibility="collapsed",
                **ch_as,
            )
        with cn:
            st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
            st.text_input(
                "Notes",
                value=str(ent.get("notes") or ""),
                key=f"tt_n_{te_id}",
                label_visibility="collapsed",
                placeholder="Notes",
                **ch_as,
            )
        _save_del_row()
    else:
        cj, ch, cn, cb = st.columns([2.2, 0.62, 1.65, 0.92], gap="small")
        with cj:
            st.markdown('<p class="ips-tt-field-label">Job</p>', unsafe_allow_html=True)
            st.selectbox(
                "Job",
                job_labels_sorted,
                index=j_ix,
                key=f"tt_job_{te_id}",
                label_visibility="collapsed",
                **ch_as,
            )
        with ch:
            st.markdown('<p class="ips-tt-field-label">Hrs</p>', unsafe_allow_html=True)
            st.number_input(
                "Hours",
                min_value=0.0,
                max_value=24.0,
                value=float(ent.get("hours", 0) or 0),
                step=hstep,
                format="%.2f",
                key=f"tt_h_{te_id}",
                label_visibility="collapsed",
                **ch_as,
            )
        with cn:
            st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
            st.text_input(
                "Notes",
                value=str(ent.get("notes") or ""),
                key=f"tt_n_{te_id}",
                label_visibility="collapsed",
                placeholder="Notes",
                **ch_as,
            )
        with cb:
            st.markdown('<p class="ips-tt-field-label">\u00a0</p>', unsafe_allow_html=True)
            _save_del_row()


def _render_new_entry_form(
    employee_id: str,
    work_date_iso: str,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    default_job_label: str | None,
    entries_for_day: list[dict],
    *,
    fast: bool,
    compact: bool = False,
) -> None:
    if not job_labels_sorted:
        return
    d0 = 0
    if default_job_label and default_job_label in job_labels_sorted:
        d0 = job_labels_sorted.index(default_job_label)

    def_h = _tt_default_hours()
    hstep = _hours_step(fast=fast)
    dup_label = "Dup" if fast else "Duplicate"

    def _on_add() -> None:
        job_pick = st.session_state.get(f"tt_newj_{employee_id}_{work_date_iso}")
        hrs = float(st.session_state.get(f"tt_newh_{employee_id}_{work_date_iso}") or 0)
        note = str(st.session_state.get(f"tt_newn_{employee_id}_{work_date_iso}") or "").strip()
        jid = job_label_to_id.get(job_pick) if isinstance(job_pick, str) else None
        if not jid:
            st.error("Invalid job.")
            st.stop()
        if hrs <= 0:
            st.error("Enter hours greater than zero.")
            st.stop()
        payload = {
            "employee_id": employee_id,
            "job_id": jid,
            "work_date": work_date_iso[:10],
            "hours": float(hrs),
            "notes": note,
            "created_by": current_profile().get("id"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            insert_row("time_entries", payload)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not add (duplicate job for this day?): {exc}")

    def _on_dup() -> None:
        src = entries_for_day[-1] if entries_for_day else None
        if src:
            sjid = str(src.get("job_id") or "")
            slabel = _job_label_for_id(job_label_to_id, sjid)
            if not slabel:
                st.error("Could not resolve job for duplicate.")
                st.stop()
            hrs = float(src.get("hours") or 0) or def_h
            note = str(src.get("notes") or "").strip()
            jid = job_label_to_id.get(slabel)
            if not jid:
                st.error("Invalid job on source row.")
                st.stop()
        else:
            if not default_job_label or default_job_label not in job_label_to_id:
                st.error("No line to copy — pick a filter job or add a row first.")
                st.stop()
            slabel = default_job_label
            jid = job_label_to_id[slabel]
            hrs = float(def_h)
            note = ""
        if hrs <= 0:
            st.error("Hours must be greater than zero.")
            st.stop()
        payload = {
            "employee_id": employee_id,
            "job_id": jid,
            "work_date": work_date_iso[:10],
            "hours": float(hrs),
            "notes": note,
            "created_by": current_profile().get("id"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            insert_row("time_entries", payload)
            st.rerun()
        except Exception as exc:
            st.error(f"Duplicate not added (same job this day?): {exc}")

    st.markdown('<div class="ips-tt-new-block">', unsafe_allow_html=True)
    st.markdown(
        '<p class="ips-tt-field-label">New entry</p>' if fast else '<p class="ips-tt-field-label">Add row</p>',
        unsafe_allow_html=True,
    )
    if compact:
        st.markdown('<p class="ips-tt-field-label">Job</p>', unsafe_allow_html=True)
        st.selectbox(
            "Job",
            job_labels_sorted,
            index=d0,
            key=f"tt_newj_{employee_id}_{work_date_iso}",
            label_visibility="collapsed",
        )
        r1, r2 = st.columns([0.45, 1.0], gap="small")
        with r1:
            st.markdown('<p class="ips-tt-field-label">Hrs</p>', unsafe_allow_html=True)
            st.number_input(
                "Hours",
                min_value=0.0,
                max_value=24.0,
                value=float(def_h),
                step=hstep,
                key=f"tt_newh_{employee_id}_{work_date_iso}",
                label_visibility="collapsed",
            )
        with r2:
            st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
            st.text_input(
                "Notes",
                value="",
                key=f"tt_newn_{employee_id}_{work_date_iso}",
                label_visibility="collapsed",
                placeholder="Notes",
            )
        ba, bd = st.columns(2, gap="small")
        with ba:
            if st.button(
                "Add",
                key=f"tt_add_{employee_id}_{work_date_iso}",
                use_container_width=True,
                help="Add time entry",
            ):
                _on_add()
        with bd:
            dup_key = f"tt_dup_{employee_id}_{work_date_iso}"
            if st.button(
                dup_label,
                key=dup_key,
                use_container_width=True,
                help="Copy last line this day (or filter job + default hours)",
            ):
                _on_dup()
    else:
        nj1, nj2, nj3, nj4 = st.columns([2.15, 0.62, 1.55, 0.95], gap="small")
        with nj1:
            st.markdown('<p class="ips-tt-field-label">Job</p>', unsafe_allow_html=True)
            st.selectbox(
                "Job",
                job_labels_sorted,
                index=d0,
                key=f"tt_newj_{employee_id}_{work_date_iso}",
                label_visibility="collapsed",
            )
        with nj2:
            st.markdown('<p class="ips-tt-field-label">Hrs</p>', unsafe_allow_html=True)
            st.number_input(
                "Hours",
                min_value=0.0,
                max_value=24.0,
                value=float(def_h),
                step=hstep,
                key=f"tt_newh_{employee_id}_{work_date_iso}",
                label_visibility="collapsed",
            )
        with nj3:
            st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
            st.text_input(
                "Notes",
                value="",
                key=f"tt_newn_{employee_id}_{work_date_iso}",
                label_visibility="collapsed",
                placeholder="Notes",
            )
        with nj4:
            st.markdown('<p class="ips-tt-field-label">\u00a0</p>', unsafe_allow_html=True)
            ba, bd = st.columns(2, gap="small")
            with ba:
                if st.button(
                    "Add",
                    key=f"tt_add_{employee_id}_{work_date_iso}",
                    use_container_width=True,
                    help="Add time entry",
                ):
                    _on_add()
            with bd:
                dup_key = f"tt_dup_{employee_id}_{work_date_iso}"
                if st.button(
                    dup_label,
                    key=dup_key,
                    use_container_width=True,
                    help="Copy last line this day (or filter job + default hours)",
                ):
                    _on_dup()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_day_column_body(
    *,
    d: date,
    eid: str,
    idx: dict,
    fj_id: str | None,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    default_job_label: str | None,
    fast: bool,
    show_day_heading: bool,
    compact: bool = False,
) -> float:
    """Day cell: sum + bordered card with editors / add form. Returns visible day hours sum."""
    wd = d.isoformat()
    ents_all = idx.get((eid, wd), [])
    ents_show = [e for e in ents_all if not fj_id or str(e.get("job_id")) == fj_id]
    day_sum = sum(float(e.get("hours", 0) or 0) for e in ents_show)
    if show_day_heading:
        st.markdown(
            f'<div class="ips-tt-day-head">{d.strftime("%a %m/%d")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="ips-tt-day-sum">{day_sum:.1f} h</div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(
            '<span class="ips-tt-day-card" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if not ents_show and not job_labels_sorted:
            st.caption("—")
        for ei, ent in enumerate(ents_show):
            if ei:
                st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
            _render_entry_editor(
                ent,
                job_labels_sorted,
                job_label_to_id,
                fast=fast,
                compact=compact,
            )
        if job_labels_sorted:
            if ents_show:
                st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
            _render_new_entry_form(
                eid,
                wd,
                job_labels_sorted,
                job_label_to_id,
                default_job_label,
                ents_show,
                fast=fast,
                compact=compact,
            )
    return day_sum


def _render_readonly_pivot(
    visible_emps: list[dict],
    days: list[date],
    idx: dict[tuple[str, str], list[dict]],
    job_id_to_label: dict[str, str],
) -> None:
    rows = []
    for emp in visible_emps:
        eid = str(emp.get("id"))
        r: dict = {"Employee": emp.get("name", "")}
        total = 0.0
        for d in days:
            wd = d.isoformat()
            ents = idx.get((eid, wd), [])
            h = sum(float(e.get("hours", 0) or 0) for e in ents)
            jobs = ", ".join(
                sorted({job_id_to_label.get(str(e.get("job_id")), "?") for e in ents if e.get("job_id")})
            )
            r[d.strftime("%a %m/%d")] = f"{h:.1f} h" + (f" ({jobs})" if jobs else "")
            total += h
        r["Σ Week"] = f"{total:.1f}"
        rows.append(r)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
