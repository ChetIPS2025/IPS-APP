from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone
from typing import Any, NamedTuple

import pandas as pd
import streamlit as st

try:
    from mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected
except ImportError:
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected  # type: ignore

from auth import current_profile, current_role
try:
    from app.ui.compact_forms import field_marker
    from app.ui.page_shell import render_page_header
except ImportError:
    from ui.compact_forms import field_marker  # type: ignore
    from ui.page_shell import render_page_header  # type: ignore
from db import delete_rows, fetch_one, fetch_table, fetch_table_admin, insert_row, update_rows

try:
    from db import fetch_jobs_with_order_fallback
except ImportError:
    from app.db import fetch_jobs_with_order_fallback  # type: ignore

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
    from services.job_service import (
        build_job_dropdown_label_maps,
        job_row_select_label,
        sort_jobs_by_number_then_name,
    )
except ImportError:
    from app.services.job_service import (  # type: ignore
        build_job_dropdown_label_maps,
        job_row_select_label,
        sort_jobs_by_number_then_name,
    )

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
        upsert_time_entry,
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
        upsert_time_entry,
        week_dates,
    )

TT_EDIT_ROLES = frozenset({"admin", "manager", "pm", "employee"})

_OT_THRESHOLD_DEFAULT = 40.0

# Fast entry / autosave session keys (stable across reruns)
TT_AUTOSAVE_KEY = "tt_autosave_enabled"
TT_DEFAULT_HOURS_KEY = "tt_default_hours_for_new_rows"
TT_JOB_LABEL_TO_ID_KEY = "_tt_job_label_to_id_for_callbacks"
TT_EDIT_ID_KEY = "tt_entry_edit_id"
TT_FAST_ENTRY_KEY = "tt_fast_entry_mode"
# Single Quick Actions popup: which employee id has it open (None = closed)
TT_OPEN_EMPLOYEE_POPUP_KEY = "tt_open_employee_popup"

# Non-job time (no job_id): category list + selectbox sentinel
TT_NON_JOB_SENTINEL = "(Non-job — category below)"
NON_JOB_CATEGORY_OPTIONS = ["", "SHOP", "ADMIN", "TRAINING", "SAFETY", "PTO", "HOLIDAY", "TRAVEL"]
NON_JOB_CODE_COLORS: dict[str, str] = {
    "SHOP": "#64748b",
    "ADMIN": "#2563eb",
    "TRAINING": "#9333ea",
    "SAFETY": "#ea580c",
    "PTO": "#16a34a",
    "HOLIDAY": "#0d9488",
    "TRAVEL": "#ca8a04",
}


def _build_work_item_options(
    *,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
) -> list[dict[str, str]]:
    """
    Combined Work Item dropdown options:
    - {"type":"job","id":<job_id>,"label":<job_label>}
    - {"type":"non_job","code":<code>,"label":"NON-JOB — <code>"}
    """
    out: list[dict[str, str]] = []
    for lb in job_labels_sorted:
        jid = str(job_label_to_id.get(lb) or "").strip()
        if not jid:
            continue
        out.append({"type": "job", "id": jid, "label": str(lb)})
    for code in NON_JOB_CATEGORY_OPTIONS:
        c = str(code or "").strip()
        if not c:
            continue
        out.append({"type": "non_job", "code": c, "label": f"NON-JOB — {c}"})
    return out


def _work_item_index_for_entry(work_item_options: list[dict[str, str]], *, ent: dict) -> int:
    jid = str(ent.get("job_id") or "").strip()
    nj = str(ent.get("non_job_code") or "").strip()
    if jid:
        for i, opt in enumerate(work_item_options):
            if opt.get("type") == "job" and str(opt.get("id") or "") == jid:
                return i
        return 0
    if nj:
        for i, opt in enumerate(work_item_options):
            if opt.get("type") == "non_job" and str(opt.get("code") or "") == nj:
                return i
        return 0
    return 0


def _work_item_display(*, job_id: str, non_job_code: str, job_id_to_label: dict[str, str]) -> str:
    jid = str(job_id or "").strip()
    nj = str(non_job_code or "").strip()
    if jid:
        return str(job_id_to_label.get(jid) or "?").strip() or "?"
    if nj:
        return f"NON-JOB — {nj}"
    return "—"


class _TTFiltersResult(NamedTuple):
    show_emp_ids: set[str]
    default_job_label: str | None
    ot_threshold: float
    active_employees: list[dict]
    job_label_to_id: dict[str, str]
    job_labels_sorted: list[str]
    job_id_to_label: dict[str, str]


class _TTWeekDataResult(NamedTuple):
    grid_rows: list
    idx: dict
    visible_emps: list[dict]
    week_total: float
    emp_id_to_name: dict[str, str]


def _tt_fast_entry() -> bool:
    """Legacy fast-entry layout disabled; simplified timesheet always uses standard density."""
    return False


_TT_CLOSED_JOB_STATUSES = frozenset(
    {"closed", "complete", "completed", "cancelled", "archived", "close", "done"}
)


def _tt_entry_time_type(ent: dict) -> str:
    s = str(ent.get("time_type") or "").strip().upper()
    if s in ("OT", "O/T", "O-T"):
        return "OT"
    return "ST"


def _tt_time_type_label(ent: dict) -> str:
    return "O/T" if _tt_entry_time_type(ent) == "OT" else "S/T"


def _tt_job_is_active_open(j: dict) -> bool:
    st = str(j.get("status") or j.get("job_status") or "").strip().lower()
    if not st:
        return True
    return st not in _TT_CLOSED_JOB_STATUSES


def _tt_load_jobs_rows(*, limit: int = 5000) -> list[dict[str, Any]]:
    """
    Jobs for time-entry pickers: prefer service-role reads for office roles (RLS-safe),
    then anon, then column/order fallbacks.
    """
    role = current_role()
    prefer_admin = role in ("admin", "manager")

    def _try_table(use_admin: bool) -> list[dict[str, Any]]:
        fn = fetch_table_admin if use_admin else fetch_table
        for ob in ("job_number", "job_name", None):
            try:
                r = list(fn("jobs", columns="*", limit=limit, order_by=ob) or [])
            except Exception:
                r = []
            if r:
                return sort_jobs_by_number_then_name(r)
        return []

    if prefer_admin:
        out = _try_table(True)
        if out:
            return out
    out = _try_table(False)
    if out:
        return out
    for use_ad in (prefer_admin, True, False):
        try:
            r = list(fetch_jobs_with_order_fallback(limit=limit, use_admin=use_ad) or [])
        except Exception:
            r = []
        if r:
            return sort_jobs_by_number_then_name(r)
    return []


def _tt_day_column_totals(
    idx: dict[tuple[str, str], list[dict]],
    days: list[date],
    show_emp_ids: set[str],
    fj_id: str | None,
) -> list[float]:
    out = [0.0] * len(days)
    for di, d in enumerate(days):
        wd = d.isoformat()
        for eid in show_emp_ids:
            for ent in idx.get((str(eid), wd), []):
                if fj_id:
                    jid = str(ent.get("job_id") or "").strip()
                    if jid and jid != fj_id:
                        continue
                out[di] += float(ent.get("hours") or 0)
    return out


def _tt_emp_hours_breakdown_for_week(
    eid: str, days: list[date], idx: dict[tuple[str, str], list[dict]], fj_id: str | None
) -> tuple[float, float, float]:
    st_sum = 0.0
    ot_sum = 0.0
    for d in days:
        wd = d.isoformat()
        for ent in idx.get((eid, wd), []):
            if fj_id:
                jid = str(ent.get("job_id") or "").strip()
                if jid and jid != fj_id:
                    continue
            h = float(ent.get("hours") or 0)
            if _tt_entry_time_type(ent) == "OT":
                ot_sum += h
            else:
                st_sum += h
    return st_sum + ot_sum, st_sum, ot_sum


def _tt_emp_hours_breakdown_for_day(
    eid: str, d: date, idx: dict[tuple[str, str], list[dict]], fj_id: str | None
) -> tuple[float, float, float]:
    st_sum = 0.0
    ot_sum = 0.0
    wd = d.isoformat()
    for ent in idx.get((eid, wd), []):
        if fj_id:
            jid = str(ent.get("job_id") or "").strip()
            if jid and jid != fj_id:
                continue
        h = float(ent.get("hours") or 0)
        if _tt_entry_time_type(ent) == "OT":
            ot_sum += h
        else:
            st_sum += h
    return st_sum + ot_sum, st_sum, ot_sum


def _tt_qa_day_key(eid: str) -> str:
    return f"tt_qa_day_{eid}"


def _tt_init_qa_day(eid: str, days: list[date], today: date) -> None:
    k = _tt_qa_day_key(eid)
    if k not in st.session_state:
        st.session_state[k] = (today if today in days else days[0]).isoformat()


def _tt_render_qa_context_heading(emp_name: str, d: date, today: date) -> None:
    if d == today:
        day_part = f"Today — {d.strftime('%a %m/%d')}"
    else:
        day_part = d.strftime("%a %m/%d")
    safe_n = html.escape(str(emp_name or "—").strip())
    safe_d = html.escape(day_part)
    st.markdown(
        f'<p class="ips-tt-qa-context"><strong>Editing:</strong> {safe_n} — {safe_d}</p>',
        unsafe_allow_html=True,
    )


def _render_qa_toggle_button(eid: str) -> None:
    st.markdown(
        '<span class="ips-tt-quick-actions-col ips-time-controls" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    open_e = st.session_state.get(TT_OPEN_EMPLOYEE_POPUP_KEY)
    if st.button(
        "⚡",
        key=f"tt_qa_toggle_{eid}",
        use_container_width=True,
        type="secondary",
        help="Quick Actions: copy day/week, fill week, edit lines for the selected day",
    ):
        if open_e == eid:
            st.session_state[TT_OPEN_EMPLOYEE_POPUP_KEY] = None
        else:
            st.session_state[TT_OPEN_EMPLOYEE_POPUP_KEY] = eid
        st.rerun()


def _week_grid_column_ratios(*, fast: bool) -> list[float]:
    """9 columns: wider employee name column + Mon–Sun + Σ (ratios are relative weights)."""
    if fast:
        return [2.6] + [1.1] * 7 + [0.32]
    return [2.6] + [1.05] * 7 + [0.34]


def _employee_name_display_html(nm: str) -> str:
    """First line / second line at first space; no mid-word breaks (CSS keep-all). HTML-escaped."""
    raw = str(nm or "").strip()
    if not raw:
        return ""
    parts = raw.split(" ", 1)
    esc = html.escape
    if len(parts) == 2:
        a, b = parts[0].strip(), parts[1].strip()
        body = f"{esc(a)}<br>{esc(b)}"
    else:
        body = esc(raw)
    return f'<div class="ips-tt-emp-name-inner">{body}</div>'


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
    wk, hk, nk = f"work_item_{te_id}", f"tt_h_{te_id}", f"tt_n_{te_id}"
    if wk not in st.session_state:
        return False, None
    wi = st.session_state.get(wk)
    if not isinstance(wi, dict):
        return False, "Invalid work item selection."
    hrs = float(st.session_state.get(hk) or 0)
    note = str(st.session_state.get(nk) or "").strip()
    tt_lbl = str(st.session_state.get(f"tt_tt_{te_id}") or "S/T")
    tt_db = "OT" if tt_lbl == "O/T" else "ST"
    wi_type = str(wi.get("type") or "").strip()
    if wi_type == "job":
        new_jid = str(wi.get("id") or "").strip()
        if not new_jid:
            return False, "Pick a valid work item."
        payload = {"job_id": new_jid, "non_job_code": None}
        snap_work = ("job", new_jid)
    elif wi_type == "non_job":
        code = str(wi.get("code") or "").strip()
        if not code:
            return False, "Pick a valid work item."
        payload = {"job_id": None, "non_job_code": code}
        snap_work = ("non_job", code)
    else:
        return False, "Pick a valid work item."
    payload.update(
        {
            "hours": hrs,
            "notes": note,
            "time_type": tt_db,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    try:
        update_rows("time_entries", payload, {"id": te_id})
    except Exception as exc:
        return False, str(exc)
    snap_k = f"tt_row_snap_{te_id}"
    st.session_state[snap_k] = (snap_work, hrs, note, tt_db)
    return True, None


def _maybe_autosave_entry(te_id: str) -> None:
    if not st.session_state.get(TT_AUTOSAVE_KEY):
        return
    jm = st.session_state.get(TT_JOB_LABEL_TO_ID_KEY)
    if not isinstance(jm, dict):
        return
    wk = f"work_item_{te_id}"
    hk = f"tt_h_{te_id}"
    nk = f"tt_n_{te_id}"
    if wk not in st.session_state:
        return
    wi = st.session_state.get(wk)
    hrs = float(st.session_state.get(hk) or 0)
    note = str(st.session_state.get(nk) or "").strip()
    if not isinstance(wi, dict):
        return
    tt_lbl = str(st.session_state.get(f"tt_tt_{te_id}") or "S/T")
    tt_db = "OT" if tt_lbl == "O/T" else "ST"
    wi_type = str(wi.get("type") or "").strip()
    if wi_type == "job":
        candidate_work = ("job", str(wi.get("id") or "").strip())
    elif wi_type == "non_job":
        candidate_work = ("non_job", str(wi.get("code") or "").strip())
    else:
        return
    candidate = (candidate_work, hrs, note, tt_db)
    snap_k = f"tt_row_snap_{te_id}"
    prev = st.session_state.get(snap_k)
    if prev is not None and len(prev) == 3:
        prev = (prev[0], prev[1], prev[2], "ST")
    if prev == candidate:
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


def _init_row_snap_from_ent(
    te_id: str,
    ent: dict,
    work_item_snap: tuple[str, str],
) -> None:
    snap_k = f"tt_row_snap_{te_id}"
    if snap_k not in st.session_state:
        tt0 = "OT" if _tt_entry_time_type(ent) == "OT" else "ST"
        st.session_state[snap_k] = (
            work_item_snap,
            float(ent.get("hours", 0) or 0),
            str(ent.get("notes") or "").strip(),
            tt0,
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


def _non_job_badge_html(code: str) -> str:
    c = NON_JOB_CODE_COLORS.get(str(code).strip(), "#64748b")
    lab = html.escape(str(code).strip()[:24])
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
            color: #cbd5e1 !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            text-align: center !important;
            margin-bottom: 0 !important;
            letter-spacing: 0.03em;
        }
        .ips-tt-day-sum {
            text-align: center !important;
            font-size: 10px !important;
            color: #94a3b8 !important;
            margin-bottom: 4px !important;
            font-variant-numeric: tabular-nums !important;
        }
        .ips-tt-qa-context {
            font-size: 0.82rem !important;
            margin: 0.1rem 0 0.4rem 0 !important;
            color: #e2e8f0 !important;
        }
        .ips-tt-day-block-selected {
            margin-top: 2px !important;
            padding: 2px 4px 4px 4px !important;
            border-radius: 6px !important;
            outline: 1px solid rgba(56, 189, 248, 0.55) !important;
            background: rgba(56, 189, 248, 0.06) !important;
        }
        .ips-tt-day-block {
            margin-top: 2px !important;
            min-height: 0 !important;
        }
        /* Quick Actions — compact popup (desktop max width; mobile near-full width) */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-quick-popup) {
            max-width: 380px !important;
            width: min(92vw, 420px) !important;
            box-sizing: border-box !important;
            padding: 12px !important;
            border-radius: 12px !important;
            margin: 0 0 0.35rem 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-quick-popup) [data-testid="stHorizontalBlock"] {
            gap: 0.35rem !important;
            flex-wrap: wrap !important;
        }
        @media (max-width: 768px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-quick-popup) {
                max-width: 420px !important;
            }
        }
        /* Simple labor entry cards */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-simple-entry) [data-testid="stElementContainer"] {
            margin-bottom: 0.1rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-simple-entry) {
            padding: 0.45rem 0.55rem 0.5rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-simple-entry) [data-testid="stFormSubmitButton"] {
            align-self: flex-end !important;
            margin-top: 0.15rem !important;
        }
        /* Table “Edit Entry” — compact strip above grid */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-edit-mini-popup) {
            max-width: 280px !important;
            width: 100% !important;
            padding: 8px 10px 10px 10px !important;
            margin: 0 0 8px 0 !important;
            border-radius: 8px !important;
        }
        @media (max-width: 768px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-edit-mini-popup) {
                max-width: 100% !important;
            }
        }
        p.ips-tt-edit-mini-title {
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            margin: 0 0 0.15rem 0 !important;
            color: #e2e8f0 !important;
        }
        p.ips-tt-edit-mini-sub {
            font-size: 0.72rem !important;
            margin: 0 0 0.45rem 0 !important;
            color: #94a3b8 !important;
            line-height: 1.25 !important;
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
        /* Quick actions — small trigger, tight panel */
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) {
            max-width: 20rem !important;
            padding: 0.35rem 0.5rem 0.5rem 0.5rem !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) [data-testid="stVerticalBlock"] > div {
            gap: 0.25rem !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) button {
            min-height: 1.3rem !important;
            max-height: 1.65rem !important;
            padding: 0.06rem 0.35rem !important;
            font-size: 0.7rem !important;
            border-radius: 4px !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 1.28rem !important;
            font-size: 0.75rem !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) [data-testid="stNumberInput"] input,
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) [data-testid="stTextInput"] input {
            min-height: 1.25rem !important;
            font-size: 0.75rem !important;
            padding: 0.05rem 0.25rem !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) label[data-testid="stWidgetLabel"] {
            font-size: 0.68rem !important;
            margin-bottom: 0 !important;
        }
        button[data-testid="stBaseButton-popover"][kind="tertiary"],
        button[kind="tertiary"][data-testid="stBaseButton-popover"] {
            min-height: 1.35rem !important;
            max-height: 1.55rem !important;
            padding: 0.1rem 0.35rem !important;
            font-size: 0.75rem !important;
            opacity: 0.92;
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
        .ips-tt-nj-sep {
            color: #64748b !important;
            font-size: 10px !important;
            font-weight: 600 !important;
            margin: 0.2rem 0 0.3rem 0 !important;
            letter-spacing: 0.08em;
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
        .ips-tt-week-hdr-title { display: block; color: #cbd5e1 !important; font-size: 10px !important; }
        .ips-tt-wh-dow { display: block; color: #e2e8f0 !important; font-size: 11px !important; }
        .ips-tt-wh-date { display: block; font-size: 10px !important; font-weight: 600 !important; opacity: 0.9; }
        .ips-tt-emp-cell {
            padding: 4px 4px 6px 2px;
            line-height: 1.25;
            min-width: 0;
        }
        .ips-tt-emp-name {
            font-size: 0.92rem !important;
            font-weight: 700 !important;
            color: #f1f5f9 !important;
            margin: 0 0 4px 0 !important;
            line-height: 1.2 !important;
            max-width: 100% !important;
        }
        .ips-tt-emp-name .ips-tt-emp-name-inner {
            max-width: 100%;
            white-space: normal;
            word-break: keep-all;
            overflow-wrap: normal;
            line-height: 1.2;
        }
        .ips-tt-emp-total {
            font-size: 0.72rem !important;
            font-weight: 500 !important;
            color: #94a3b8 !important;
            margin: 0 !important;
            line-height: 1.3 !important;
        }
        /* Employee header: name column + quick-actions column (scoped — do not target the 9-col week row) */
        div[data-testid="column"]:has(span.ips-tt-emp-header-scope) {
            min-width: 0 !important;
        }
        div[data-testid="column"]:has(span.ips-tt-quick-actions-col) {
            display: flex !important;
            justify-content: flex-end !important;
            align-items: flex-start !important;
            padding-top: 2px !important;
            min-width: 0 !important;
        }
        div[data-testid="column"]:has(span.ips-tt-quick-actions-col) button[data-testid="stBaseButton-popover"] {
            min-height: 2rem !important;
            min-width: 2rem !important;
        }

        /* Full-width employee cards (narrow / stacked layout) */
        .ips-time-card {
            width: 100%;
            box-sizing: border-box;
        }
        .ips-time-row {
            display: block;
            width: 100%;
        }
        .ips-time-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            justify-content: flex-end;
        }

        @media (max-width: 768px) {
            .ips-time-row,
            .ips-time-card {
                width: 100%;
                display: block;
            }
            .ips-tt-sheet-narrow .ips-tt-emp-name,
            .ips-time-name {
                font-size: 16px !important;
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
            }
            .ips-tt-sheet-narrow .ips-tt-emp-name .ips-tt-emp-name-inner {
                word-break: keep-all !important;
                overflow-wrap: normal !important;
            }
            div[data-testid="column"]:has(span.ips-tt-quick-actions-col) {
                justify-content: flex-start !important;
                margin-top: 4px;
                padding-top: 0 !important;
            }
            [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) .stButton > button,
            [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-empty) .stButton > button {
                min-height: 44px !important;
                padding: 0.4rem 0.65rem !important;
                font-size: 0.85rem !important;
            }
            [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) [data-testid="stNumberInput"] input,
            [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) [data-testid="stTextInput"] input {
                min-height: 44px !important;
            }
        }

        /* —— Spreadsheet / Excel-like weekly grid (IPS dark theme) —— */
        span.ips-tt-sheet-row { display: none !important; }

        /* Header row: strong band + grid lines */
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) {
            background: linear-gradient(180deg, rgba(51, 65, 85, 0.92) 0%, rgba(30, 41, 59, 0.88) 100%) !important;
            border: 1px solid rgba(148, 163, 184, 0.5) !important;
            border-radius: 3px 3px 0 0 !important;
            margin-bottom: 0 !important;
            padding: 0 !important;
            box-shadow: inset 0 -2px 0 rgba(15, 23, 42, 0.5);
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) > div[data-testid="column"] {
            border-right: 1px solid rgba(71, 85, 105, 0.75) !important;
            padding: 6px 5px 7px 5px !important;
            align-self: stretch !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) > div[data-testid="column"]:first-child {
            background: rgba(15, 23, 42, 0.35) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) > div[data-testid="column"]:last-child {
            border-right: none !important;
            background: rgba(15, 23, 42, 0.28) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) .ips-tt-week-hdr-day,
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) .ips-tt-week-hdr-sum {
            color: #f1f5f9 !important;
            font-weight: 800 !important;
            letter-spacing: 0.06em !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) .ips-tt-wh-dow {
            color: #cbd5e1 !important;
            font-size: 10px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) .ips-tt-wh-date {
            color: #e2e8f0 !important;
            font-size: 11px !important;
        }

        /* Data rows: zebra + hover + column lines + sticky employee/total tint */
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row.ips-tt-zebra-0) {
            background: rgba(22, 32, 48, 0.72) !important;
            border-left: 1px solid rgba(71, 85, 105, 0.65) !important;
            border-right: 1px solid rgba(71, 85, 105, 0.65) !important;
            margin-top: -1px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row.ips-tt-zebra-1) {
            background: rgba(17, 26, 39, 0.78) !important;
            border-left: 1px solid rgba(71, 85, 105, 0.65) !important;
            border-right: 1px solid rgba(71, 85, 105, 0.65) !important;
            margin-top: -1px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row):hover {
            background: rgba(59, 130, 246, 0.14) !important;
            box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.35) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row) > div[data-testid="column"] {
            border-right: 1px solid rgba(71, 85, 105, 0.55) !important;
            padding: 4px 4px 5px 4px !important;
            align-self: stretch !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row) > div[data-testid="column"]:first-child {
            background: rgba(30, 41, 59, 0.65) !important;
            border-right: 1px solid rgba(100, 116, 139, 0.45) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row) > div[data-testid="column"]:last-child {
            background: rgba(30, 41, 59, 0.5) !important;
            border-right: none !important;
            border-left: 1px solid rgba(100, 116, 139, 0.35) !important;
        }

        /* Remove heavy “card” chrome around whole employee row */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-sheet-row) {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            padding: 0 !important;
            margin-bottom: 0 !important;
        }

        /* Footer totals row */
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-footer-row) {
            background: rgba(51, 65, 85, 0.55) !important;
            border: 1px solid rgba(148, 163, 184, 0.45) !important;
            border-top: 2px solid rgba(100, 116, 139, 0.55) !important;
            border-radius: 0 0 3px 3px !important;
            margin-top: -1px !important;
            padding: 2px 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-footer-row) > div[data-testid="column"] {
            border-right: 1px solid rgba(71, 85, 105, 0.55) !important;
            padding: 5px 4px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-footer-row) > div[data-testid="column"]:first-child {
            background: rgba(15, 23, 42, 0.4) !important;
            font-weight: 700 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-footer-row) > div[data-testid="column"]:last-child {
            border-right: none !important;
            background: rgba(15, 23, 42, 0.35) !important;
        }

        /* Day sub-header (sum line) — spreadsheet sublabel */
        .ips-tt-day-head {
            background: rgba(15, 23, 42, 0.45) !important;
            border: 1px solid rgba(71, 85, 105, 0.4) !important;
            border-radius: 2px 2px 0 0 !important;
            padding: 3px 4px !important;
            margin-bottom: 0 !important;
        }
        .ips-tt-day-sum {
            background: rgba(15, 23, 42, 0.35) !important;
            border: 1px solid rgba(71, 85, 105, 0.4) !important;
            border-top: none !important;
            border-radius: 0 0 2px 2px !important;
            padding: 2px 4px 3px 4px !important;
            margin-bottom: 4px !important;
            font-variant-numeric: tabular-nums !important;
        }

        /* Day “cells”: flat, grid-like, not floating cards */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) {
            border-radius: 2px !important;
            border: 1px solid rgba(71, 85, 105, 0.65) !important;
            background: rgba(15, 23, 42, 0.55) !important;
            box-shadow: none !important;
            padding: 4px 4px 5px 4px !important;
            margin-top: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell):focus-within {
            box-shadow: inset 0 0 0 2px rgba(59, 130, 246, 0.65) !important;
            background: rgba(15, 23, 42, 0.75) !important;
            border-color: rgba(96, 165, 250, 0.45) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) input:focus,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) textarea:focus,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) [data-baseweb="select"]:focus-within {
            outline: 2px solid rgba(59, 130, 246, 0.9) !important;
            outline-offset: 0px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-empty) {
            background: rgba(15, 23, 42, 0.25) !important;
            border: 1px dashed rgba(100, 116, 139, 0.45) !important;
            min-height: 2.75rem !important;
            text-align: center !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-empty) button {
            font-size: 0.76rem !important;
            min-height: 1.45rem !important;
            padding: 0.15rem 0.45rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-sheet-narrow.ips-tt-zebra-0) {
            background: rgba(22, 32, 48, 0.5) !important;
            border: 1px solid rgba(71, 85, 105, 0.5) !important;
            border-radius: 3px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-sheet-narrow.ips-tt-zebra-1) {
            background: rgba(17, 26, 39, 0.55) !important;
            border: 1px solid rgba(71, 85, 105, 0.5) !important;
            border-radius: 3px !important;
        }
        /* Spacing between full-width employee week rows (desktop sheet) */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-sheet-emp-card) {
            margin-bottom: 10px !important;
            padding: 8px 10px 10px 10px !important;
            border-radius: 8px !important;
        }

        /* ── Weekly Timecard Grid (new compact design) ── */
        .ips-wc-col-hdr {
            font-size: 9px !important;
            font-weight: 700 !important;
            color: #64748b !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin: 0 0 2px 0 !important;
            padding: 0 !important;
            line-height: 1.1 !important;
        }
        .ips-wc-day-lbl {
            font-size: 11px !important;
            font-weight: 700 !important;
            color: #cbd5e1 !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.3 !important;
        }
        .ips-wc-day-date {
            font-size: 10px !important;
            color: #64748b !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
        }
        .ips-wc-day-today {
            color: #38bdf8 !important;
        }
        /* Compact card */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) {
            padding: 8px 10px 10px 10px !important;
            margin-bottom: 8px !important;
            border-radius: 8px !important;
        }
        /* Compact inputs inside timecard cards */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) [data-testid="stNumberInput"] input {
            min-height: 1.45rem !important;
            font-size: 0.8rem !important;
            padding: 0.04rem 0.28rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) [data-testid="stTextInput"] input {
            min-height: 1.45rem !important;
            font-size: 0.8rem !important;
            padding: 0.04rem 0.28rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 1.45rem !important;
            font-size: 0.8rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) label[data-testid="stWidgetLabel"] {
            display: none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) button {
            min-height: 1.45rem !important;
            padding: 0.08rem 0.3rem !important;
            font-size: 0.74rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) [data-testid="stElementContainer"] {
            margin-bottom: 0.08rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) [data-testid="stVerticalBlock"] > div {
            gap: 0.15rem !important;
        }
        /* Day separator between days within a card */
        div[data-testid="stHorizontalBlock"]:has(span.ips-wc-day-sep) {
            border-top: 1px solid rgba(71, 85, 105, 0.45) !important;
            margin-top: 0.15rem !important;
            padding-top: 0.25rem !important;
        }
        /* Add row subtle style */
        div[data-testid="stHorizontalBlock"]:has(span.ips-wc-add-row) {
            border-top: 1px dashed rgba(100, 116, 139, 0.3) !important;
            margin-top: 0.08rem !important;
            padding-top: 0.18rem !important;
            opacity: 0.85;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-wc-add-row):hover {
            opacity: 1.0;
        }
        /* Entries expander compact */
        div[data-testid="stExpander"]:has(span.ips-wc-entries-expander) {
            margin-top: 0.4rem !important;
        }
        @media (max-width: 768px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) {
                padding: 6px 6px 8px 6px !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) [data-testid="stNumberInput"] input,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) [data-testid="stTextInput"] input {
                min-height: 2rem !important;
                font-size: 0.85rem !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-wc-card) button {
                min-height: 2rem !important;
                font-size: 0.8rem !important;
            }
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
        jid = str(e.get("job_id") or "").strip()
        nj = str(e.get("non_job_code") or "").strip()
        if fj_id and jid != fj_id:
            continue
        tid = e.get("id")
        if not tid:
            continue
        if jid:
            job_disp = job_id_to_label.get(jid, jid[:8] + "…" if len(jid) > 8 else jid)
        elif nj:
            job_disp = nj
        else:
            job_disp = "—"
        out.append(
            {
                "id": tid,
                "employee": emp_id_to_name.get(eid, eid[:8] + "…" if len(eid) > 8 else eid),
                "work_date": str(e.get("work_date") or "")[:10],
                "job": job_disp,
                "type": _tt_time_type_label(e),
                "hours": float(e.get("hours") or 0),
                "notes": str(e.get("notes") or ""),
            }
        )
    return out


def _render_employee_name_cell(*, nm: str, tot_s: str, over: bool, ot_threshold: float) -> None:
    """Employee name (first line / remainder at first space; no mid-word breaks) and muted weekly hours."""
    title_attr = html.escape(nm, quote=True)
    over_cls = " ips-tt-row-over" if over else ""
    name_inner = _employee_name_display_html(nm)
    if over:
        tot_line = html.escape(f"{tot_s} · over {ot_threshold:g} h")
    else:
        tot_line = html.escape(tot_s)
    st.markdown(
        f'<div class="ips-tt-emp-cell">'
        f'<div class="ips-tt-emp-name ips-time-name{over_cls}" title="{title_attr}">{name_inner}</div>'
        f'<p class="ips-tt-emp-total">{tot_line}</p></div>',
        unsafe_allow_html=True,
    )


def _render_employee_time_header(
    *,
    nm: str,
    tot_s: str,
    over: bool,
    ot_threshold: float,
    eid: str,
) -> None:
    """Name + weekly hours (left) and Quick Actions lightning (right); used for narrow cards and desktop sheet first column."""
    c1, c2 = st.columns([1, 0.22], gap="small")
    with c1:
        st.markdown(
            '<span class="ips-tt-emp-header-scope" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        _render_employee_name_cell(nm=nm, tot_s=tot_s, over=over, ot_threshold=ot_threshold)
    with c2:
        _render_qa_toggle_button(eid)


def _render_week_header_row(*, grid_ratios: list[float], days: list[date]) -> None:
    """One row aligned to the grid: Employee + Mon–Sun + Σ (spreadsheet header band)."""
    h0, *hday, hlast = st.columns(grid_ratios)
    with h0:
        st.markdown(
            '<span class="ips-tt-sheet-hdr-corner" aria-hidden="true"></span>'
            '<div class="ips-tt-week-hdr-cell ips-tt-week-hdr-emp">'
            '<span class="ips-tt-week-hdr-title">Employee</span></div>',
            unsafe_allow_html=True,
        )
    for di, d in enumerate(days):
        with hday[di]:
            st.markdown(
                f'<div class="ips-tt-week-hdr-day ips-tt-sheet-hdr-day">'
                f'<span class="ips-tt-wh-dow">{d.strftime("%a")}</span>'
                f'<span class="ips-tt-wh-date">{d.strftime("%b %d")}</span></div>',
                unsafe_allow_html=True,
            )
    with hlast:
        st.markdown(
            '<div class="ips-tt-week-hdr-sum ips-tt-sheet-hdr-sum">Σ</div>',
            unsafe_allow_html=True,
        )


def _tt_render_header_section() -> tuple[bool, bool]:
    """Branding, styles, viewport. Returns (can_edit, fast); fast is always False (legacy)."""
    render_page_header(
        "Time Tracking",
        "Log hours by employee, job, and day — S/T vs O/T.",
    )

    _inject_tt_styles()
    ensure_narrow_viewport_detected()

    role = current_role()
    can_edit = role in TT_EDIT_ROLES

    return can_edit, False


def _tt_render_toolbar_section(today: date) -> tuple[date, list[date], date]:
    """PM Matrix shortcut + week navigation. Returns (week_start, days, week_end)."""
    try:
        from ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

    pm_row1, pm_row2 = st.columns([4, 1])
    with pm_row1:
        st.caption("One-day crew grid: **PM Matrix Time Entry** (sidebar).")
    with pm_row2:
        if st.button("PM Matrix", key="tt_open_pm_matrix", use_container_width=False):
            st.session_state[IPS_NAV_PENDING_KEY] = "PM Matrix Time Entry"
            st.rerun()

    st.session_state.setdefault("tt_week_start", monday_of_week(today))

    week_start: date = st.session_state["tt_week_start"]
    if week_start.weekday() != 0:
        week_start = monday_of_week(week_start)
        st.session_state["tt_week_start"] = week_start

    days = week_dates(week_start)
    week_end = days[-1]

    st.markdown('<span class="ips-tt-nav-scope" aria-hidden="true"></span>', unsafe_allow_html=True)
    w1, w2, w3 = st.columns([1, 1, 1])
    with w1:
        if st.button("◀ Prev week", use_container_width=True, help="Previous week"):
            st.session_state["tt_week_start"] = week_start - timedelta(days=7)
            st.rerun()
    with w2:
        if st.button("Next week ▶", use_container_width=True, help="Next week"):
            st.session_state["tt_week_start"] = week_start + timedelta(days=7)
            st.rerun()
    with w3:
        if st.button("This week", use_container_width=True, help="Jump to this week"):
            st.session_state["tt_week_start"] = monday_of_week(today)
            st.rerun()

    return week_start, days, week_end


def _tt_render_filters_section(*, fast: bool) -> _TTFiltersResult:
    """Employee / job filters and week options (OT threshold)."""
    try:
        all_employees = fetch_table("employees", limit=5000, order_by="name")
    except Exception:
        all_employees = []
    active_employees = [e for e in all_employees if e.get("is_active", True) is not False]

    jobs = _tt_load_jobs_rows(limit=5000)
    _, job_label_to_id, job_labels_sorted = build_job_dropdown_label_maps(jobs)
    job_id_to_label = {v: k for k, v in job_label_to_id.items()}
    st.session_state[TT_JOB_LABEL_TO_ID_KEY] = job_label_to_id

    emp_choices = {f"{e.get('name', '')} ({str(e.get('id'))[:8]})": str(e.get("id")) for e in active_employees if e.get("id")}
    emp_label_list = sorted(emp_choices.keys(), key=str.casefold)
    f1, f2 = st.columns(2, gap="small")
    with f1:
        filt_emp = st.multiselect(
            "Filter employees",
            options=emp_label_list,
            default=emp_label_list,
            help=None if fast else "Restrict which rows are shown.",
        )
    with f2:
        job_opts = ["(All jobs)"] + job_labels_sorted
        filt_job = st.selectbox(
            "Filter job (new entries default)",
            options=job_opts,
            index=0,
            help=None
            if fast
            else "When not “All”, new time lines default to this job; existing lines for other jobs still show.",
        )
    show_emp_ids = {emp_choices[lb] for lb in filt_emp} if filt_emp else set(emp_choices.values())
    default_job_label = None if filt_job == "(All jobs)" else filt_job

    with st.expander("Week options", expanded=False):
        st.markdown(
            '<span class="ips-tt-week-options ips-tt-ot-scope" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        ot_threshold = st.number_input(
            "Weekly OT highlight (hours)" if fast else "Weekly hours threshold (overtime highlight)",
            min_value=0.0,
            max_value=120.0,
            value=float(st.session_state.get("tt_ot_threshold", _OT_THRESHOLD_DEFAULT)),
            step=1.0 if fast else 0.5,
            key="tt_ot_threshold_input",
        )
    st.session_state["tt_ot_threshold"] = ot_threshold

    return _TTFiltersResult(
        show_emp_ids=show_emp_ids,
        default_job_label=default_job_label,
        ot_threshold=float(ot_threshold),
        active_employees=active_employees,
        job_label_to_id=job_label_to_id,
        job_labels_sorted=job_labels_sorted,
        job_id_to_label=job_id_to_label,
    )


def _tt_render_summary_section(
    week_start: date,
    week_end: date,
    filt: _TTFiltersResult,
) -> _TTWeekDataResult | None:
    """Load week rows, OT summary strip, job legend. Returns None if no visible employees."""
    try:
        grid_rows = fetch_time_entries_between(week_start, week_end)
    except Exception as exc:
        grid_rows = []
        st.error(f"Could not load time_entries: {exc}. Run `sql/009_time_entries.sql` in Supabase.")
    idx = index_by_employee_date(grid_rows)

    visible_emps = [e for e in filt.active_employees if str(e.get("id")) in filt.show_emp_ids]
    if not visible_emps:
        st.warning("No employees match the filter. Adjust filters or add employees (**Users** → Employees).")
        return None

    def _in_week(x: dict) -> bool:
        try:
            wd = _parse_date_key(str(x.get("work_date")))
            return week_start <= wd <= week_end
        except Exception:
            return False

    week_total = sum(float(x.get("hours", 0) or 0) for x in grid_rows if _in_week(x))
    st.caption(
        f"Week **{week_start.isoformat()}** → **{week_end.isoformat()}** · "
        f"{week_total:.2f} h in loaded data"
    )

    ordered_job_ids = _ordered_job_ids_for_badges(filt.job_labels_sorted, filt.job_label_to_id)
    with st.expander("Job color key", expanded=False):
        parts = [
            _job_badge_html(lb, filt.job_label_to_id[lb], ordered_job_ids)
            for lb in filt.job_labels_sorted[:60]
            if lb in filt.job_label_to_id
        ]
        st.markdown(
            '<div class="ips-tt-legend">' + "".join(parts) + "</div>",
            unsafe_allow_html=True,
        )
        if len(filt.job_labels_sorted) > 60:
            st.caption("Showing first 60 jobs; colors repeat by job order.")

    fast = _tt_fast_entry()
    if not fast:
        st.caption(
            "Each **employee × job × day** is unique. Hours save to **time_entries**. "
            "Approved rows in **employee_time_entries** (legacy) are still included in Job Costing."
        )

    emp_id_to_name = {
        str(e.get("id")): str(e.get("name") or "").strip() or "—"
        for e in filt.active_employees
        if e.get("id")
    }

    return _TTWeekDataResult(
        grid_rows=grid_rows,
        idx=idx,
        visible_emps=visible_emps,
        week_total=week_total,
        emp_id_to_name=emp_id_to_name,
    )


def _tt_render_simple_timesheet(
    *,
    today: date,
    week_start: date,
    days: list[date],
    filt: _TTFiltersResult,
    week_data: _TTWeekDataResult,
    fj_id: str | None,
) -> tuple[list[float], list[float]]:
    """Compact per-employee entry: job + S/T|O/T + hours + save; list for selected day."""
    uid = current_profile().get("id")
    ts_now = datetime.now(timezone.utc).isoformat()
    jobs_raw = _tt_load_jobs_rows(limit=5000)
    _, row_label_to_id, all_job_labels = build_job_dropdown_label_maps(jobs_raw)
    active_ids = {str(j.get("id")) for j in jobs_raw if j.get("id") and _tt_job_is_active_open(j)}
    active_labels = [lb for lb in all_job_labels if str(row_label_to_id.get(lb) or "") in active_ids]
    if not active_labels:
        active_labels = list(all_job_labels)
    if fj_id:
        active_labels = [lb for lb in active_labels if str(row_label_to_id.get(lb) or "") == fj_id]

    if not jobs_raw:
        st.caption("**No jobs loaded** — check Supabase `jobs` table, RLS policies, and service role keys for admin/manager.")

    st.subheader("Time entry")
    wk_date_key = f"tt_simple_work_date_{week_start.isoformat()}"
    day_isos = [d.isoformat() for d in days]
    if wk_date_key not in st.session_state or st.session_state[wk_date_key] not in day_isos:
        st.session_state[wk_date_key] = (today.isoformat() if today in days else days[0].isoformat())
    _wd_col, _ = st.columns([0.28, 4], gap="small")
    with _wd_col:
        field_marker("date")
        sel_iso = st.selectbox(
            "Working date",
            day_isos,
            format_func=lambda s: date.fromisoformat(s).strftime("%a %m/%d"),
            key=wk_date_key,
            help="New lines and the lists below use this date.",
        )
    work_d = date.fromisoformat(sel_iso)
    work_iso = work_d.isoformat()

    for emp in week_data.visible_emps:
        eid = str(emp.get("id"))
        nm = str(emp.get("name", "") or "—").strip() or "—"
        wtot, wst, wot = _tt_emp_hours_breakdown_for_week(eid, days, week_data.idx, fj_id)
        _, dst, dot = _tt_emp_hours_breakdown_for_day(eid, work_d, week_data.idx, fj_id)
        row_h = sum_employee_week_hours(week_data.grid_rows, eid, days)
        over = row_h > filt.ot_threshold
        over_note = f" · over **{filt.ot_threshold:g}** h/week" if over else ""

        with st.container(border=True):
            st.markdown(
                '<span class="ips-compact-form ips-tt-simple-entry" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            st.markdown(f"**{html.escape(nm)}**")
            st.caption(
                f"{work_d.strftime('%a %m/%d')}: S/T **{dst:.2f}** h · O/T **{dot:.2f}** h · "
                f"Week: S/T **{wst:.2f}** · O/T **{wot:.2f}** · Σ **{wtot:.2f}** h{over_note}"
            )

            _sq, _ = st.columns([1.35, 4], gap="small")
            with _sq:
                field_marker("search")
                q = st.text_input(
                    "Find job",
                    value="",
                    key=f"tt_job_q_{week_start}_{eid}",
                    placeholder="Search job # or name…",
                    label_visibility="collapsed",
                )
            qn = str(q or "").strip().lower()
            job_opts = [lb for lb in active_labels if not qn or qn in lb.lower()]
            if not job_opts:
                if not active_labels:
                    job_opts = ["(No jobs found)"]
                else:
                    job_opts = ["(No jobs match search — clear filter)"]

            with st.form(key=f"tt_add_form_{week_start}_{eid}", clear_on_submit=False):
                field_marker("job")
                job_pick = st.selectbox("Job", job_opts, key=f"tt_job_pick_{week_start}_{eid}")
                c1, c2, c3 = st.columns([1.05, 0.72, 0.48], gap="small")
                with c1:
                    field_marker("time-type")
                    tt_pick = st.selectbox(
                        "Time type",
                        ["S/T", "O/T"],
                        key=f"tt_tt_pick_{week_start}_{eid}",
                        label_visibility="collapsed",
                    )
                with c2:
                    field_marker("hours")
                    hrs_in = st.number_input(
                        "Hours",
                        min_value=0.0,
                        max_value=99.0,
                        value=0.0,
                        step=0.25,
                        format="%.2f",
                        key=f"tt_hrs_add_{week_start}_{eid}",
                        label_visibility="collapsed",
                    )
                with c3:
                    submitted = st.form_submit_button(
                        "Save / Add",
                        type="primary",
                        use_container_width=False,
                    )

            if submitted:
                if job_pick.startswith("(No jobs") or job_pick.startswith("(No match") or job_pick.startswith(
                    "(No jobs match"
                ):
                    st.warning("Pick a job or clear the search filter.")
                elif not uid:
                    st.error("Not signed in; cannot save.")
                else:
                    jid = str(row_label_to_id.get(job_pick) or "").strip()
                    if not jid:
                        st.error("Could not resolve job for that label.")
                    else:
                        tt_db = "OT" if tt_pick == "O/T" else "ST"
                        try:
                            upsert_time_entry(
                                employee_id=eid,
                                job_id=jid,
                                work_date=work_d,
                                hours=float(hrs_in),
                                notes="",
                                created_by=uid,
                                updated_at_iso=ts_now,
                                non_job_code=None,
                                time_type=tt_db,
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Save failed: {exc}")

            ents = list(week_data.idx.get((eid, work_iso), []))
            if fj_id:
                ents = [e for e in ents if (not e.get("job_id")) or str(e.get("job_id")) == fj_id]

            def _sort_key(ent: dict) -> str:
                jid = str(ent.get("job_id") or "").strip()
                nj = str(ent.get("non_job_code") or "").strip()
                if jid:
                    return str(filt.job_id_to_label.get(jid, jid)).lower()
                if nj:
                    return f"non-job {nj}".lower()
                return ""

            if ents:
                st.markdown(
                    '<p class="ips-tt-field-label" style="margin-top:0.5rem;">Entries for this date</p>',
                    unsafe_allow_html=True,
                )
                for ent in sorted(ents, key=_sort_key):
                    tid = str(ent.get("id") or "")
                    if not tid:
                        continue
                    jid = str(ent.get("job_id") or "").strip()
                    nj = str(ent.get("non_job_code") or "").strip()
                    if jid:
                        jlab = html.escape(str(filt.job_id_to_label.get(jid, jid))[:80])
                    elif nj:
                        jlab = html.escape(f"NON-JOB — {nj}")
                    else:
                        jlab = "—"
                    h = float(ent.get("hours") or 0)
                    ttl = _tt_time_type_label(ent)
                    line = f"{jlab} · **{ttl}** · {h:.2f} h"
                    c_a, c_b = st.columns([5, 1])
                    with c_a:
                        st.markdown(line, unsafe_allow_html=True)
                    with c_b:
                        if st.button("✕", key=f"tt_rm_{tid}", help="Remove this line"):
                            try:
                                delete_rows("time_entries", {"id": tid})
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

    wk_st = wk_ot = 0.0
    for eid in filt.show_emp_ids:
        _, s, o = _tt_emp_hours_breakdown_for_week(str(eid), days, week_data.idx, fj_id)
        wk_st += s
        wk_ot += o
    st.caption(
        f"Week total (current filters): S/T **{wk_st:.2f}** h · O/T **{wk_ot:.2f}** h · "
        f"Σ **{wk_st + wk_ot:.2f}** h"
    )

    day_col_totals = _tt_day_column_totals(week_data.idx, days, filt.show_emp_ids, fj_id)
    grid_ratios = _week_grid_column_ratios(fast=False)
    return day_col_totals, grid_ratios


def _tt_render_grid_section(
    *,
    can_edit: bool,
    fast: bool,
    today: date,
    week_start: date,
    days: list[date],
    week_end: date,
    filt: _TTFiltersResult,
    week_data: _TTWeekDataResult,
) -> tuple[list[float], list[float]] | None:
    """Weekly timecard cards + flat table expander (or read-only pivot). Returns footer data or None."""
    fj_id = filt.job_label_to_id.get(filt.default_job_label) if filt.default_job_label else None

    if not can_edit:
        st.info("View-only mode. Sign in as admin, manager, pm, or employee to log time.")
        _render_readonly_pivot(week_data.visible_emps, days, week_data.idx, filt.job_id_to_label)
        return None

    # ── Primary UI: compact per-employee weekly timecard cards ──────────────
    result = _render_weekly_timecard_grid(
        today=today,
        week_start=week_start,
        days=days,
        filt=filt,
        week_data=week_data,
        fj_id=fj_id,
    )

    # ── Secondary: flat entries table in expander (export / bulk delete) ────
    flat_rows = _tt_flat_entry_rows(
        week_data.grid_rows,
        filt.show_emp_ids,
        fj_id,
        week_data.emp_id_to_name,
        filt.job_id_to_label,
    )
    entries_df = pd.DataFrame(flat_rows)

    # View detail popup (opened from table row select)
    tv_id = st.session_state.get("tt_entry_view_id")
    if tv_id:
        vr = fetch_one("time_entries", {"id": tv_id})
        if not vr:
            st.session_state.pop("tt_entry_view_id", None)
        else:
            with st.container(border=True):
                st.subheader("Time entry detail")
                e_nm = week_data.emp_id_to_name.get(str(vr.get("employee_id") or ""), "—")
                j_nm = filt.job_id_to_label.get(str(vr.get("job_id") or ""), "—")
                st.markdown(
                    f"**Employee:** {e_nm}  \n"
                    f"**Work date:** {vr.get('work_date') or '—'}  \n"
                    f"**Job:** {j_nm}  \n"
                    f"**Type:** {_tt_time_type_label(vr)}  \n"
                    f"**Hours:** {float(vr.get('hours') or 0):.2f}  \n"
                    f"**Notes:** {vr.get('notes') or '—'}"
                )
                if st.button("← Close", key="tt_entry_view_back"):
                    st.session_state.pop("tt_entry_view_id", None)
                    st.rerun()

    # Inline edit popup (opened from table Edit action)
    if can_edit:
        te_tbl = st.session_state.get(TT_EDIT_ID_KEY)
        if te_tbl:
            erw = fetch_one("time_entries", {"id": str(te_tbl)})
            if not erw:
                st.session_state.pop(TT_EDIT_ID_KEY, None)
            else:
                _render_minimal_table_edit_popup(
                    erw,
                    job_labels_sorted=filt.job_labels_sorted,
                    job_label_to_id=filt.job_label_to_id,
                    job_id_to_label=filt.job_id_to_label,
                    emp_id_to_name=week_data.emp_id_to_name,
                    fast=fast,
                )

    # Entries table expander (for export / bulk delete)
    n_entries = len(flat_rows)
    with st.expander(
        f"Entries table ({n_entries} rows this week) — Export / Bulk delete",
        expanded=False,
    ):
        st.markdown('<span class="ips-wc-entries-expander" aria-hidden="true"></span>', unsafe_allow_html=True)
        if not entries_df.empty and "id" in entries_df.columns:
            st.caption("Select rows to view, edit, export, or bulk-delete.")
            show_flat = [c for c in ["employee", "work_date", "job", "type", "hours", "notes"] if c in entries_df.columns]
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
        else:
            st.caption("No entries for this week matching current filters.")

    return result


def _tt_render_footer_section(day_col_totals: list[float], days: list[date], grid_ratios: list[float]) -> None:
    """Week totals row aligned to the grid (compact on narrow viewport)."""
    st.caption("Week totals")
    narrow = bool(st.session_state.get(IPS_VIEWPORT_NARROW_KEY))
    total_h = sum(day_col_totals)
    if narrow:
        st.markdown(
            f'<p class="ips-tt-metric" style="margin:0 0 0.35rem 0;">Week <strong>{total_h:.1f}</strong> h</p>',
            unsafe_allow_html=True,
        )
        with st.expander("Day totals (Mon–Sun)", expanded=False):
            for di, d in enumerate(days):
                st.markdown(f"**{d.strftime('%a %m/%d')}:** {day_col_totals[di]:.1f} h")
        return

    f0, *fday, fl = st.columns(grid_ratios)
    with f0:
        st.markdown('<span class="ips-tt-sheet-footer-row" aria-hidden="true"></span>', unsafe_allow_html=True)
        st.markdown("**Day Σ**")
    for di, d in enumerate(days):
        with fday[di]:
            st.markdown(f'<p class="ips-tt-metric">{day_col_totals[di]:.1f} h</p>', unsafe_allow_html=True)
    with fl:
        st.markdown(f'<p class="ips-tt-metric">{total_h:.1f}</p>', unsafe_allow_html=True)


def render() -> None:
    today = date.today()
    can_edit, fast = _tt_render_header_section()
    week_start, days, week_end = _tt_render_toolbar_section(today)
    filt = _tt_render_filters_section(fast=fast)
    week_data = _tt_render_summary_section(week_start, week_end, filt)
    if week_data is None:
        return
    footer = _tt_render_grid_section(
        can_edit=can_edit,
        fast=fast,
        today=today,
        week_start=week_start,
        days=days,
        week_end=week_end,
        filt=filt,
        week_data=week_data,
    )
    if footer is not None:
        day_col_totals, grid_ratios = footer
        _tt_render_footer_section(day_col_totals, days, grid_ratios)


def _render_quick_actions_popup(
    *,
    eid: str,
    emp_name: str,
    days: list[date],
    week_start: date,
    week_end: date,
    today: date,
    idx: dict,
    fj_id: str | None,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    default_job_label: str | None,
    fast: bool,
    user_id,
    ts_iso: str,
) -> None:
    """Compact Quick Actions popup: day, bulk copy/fill/clear, entries and add for selected day."""
    _tt_init_qa_day(eid, days, today)
    wd_key = _tt_qa_day_key(eid)
    try:
        cur_from_state = date.fromisoformat(str(st.session_state.get(wd_key) or "")[:10])
    except ValueError:
        cur_from_state = today if today in days else days[0]
    if cur_from_state not in days:
        cur_from_state = today if today in days else days[0]
        st.session_state[wd_key] = cur_from_state.isoformat()
    ix = days.index(cur_from_state)

    def _fmt_di(i: int) -> str:
        dd = days[i]
        if dd == today:
            return f"Today — {dd.strftime('%a %m/%d')}"
        return dd.strftime("%a %m/%d")

    with st.container(border=True):
        st.markdown(
            '<span class="ips-quick-popup ips-tt-quick-actions-col ips-time-controls" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Close",
            key=f"tt_qa_close_{eid}",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state[TT_OPEN_EMPLOYEE_POPUP_KEY] = None
            st.rerun()
        st.caption("**Quick Actions** — pick the working day below.")
        picked_ix = st.selectbox(
            "Day",
            list(range(len(days))),
            index=ix,
            format_func=_fmt_di,
            key=f"tt_qa_dpick_{eid}",
            help="Entries and Add apply to this day.",
        )
        cur_d = days[int(picked_ix)]
        st.session_state[wd_key] = cur_d.isoformat()
        wd_work = cur_d.isoformat()
        _tt_render_qa_context_heading(emp_name, cur_d, today)

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        if st.button(
            "Copy prev → day",
            key=f"tt_cpday_{eid}",
            use_container_width=True,
            help="Copy previous calendar day into the day selected above",
        ):
            dest_date = cur_d
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
        st.markdown('<p class="ips-tt-field-label">Fill week (Mon–Sun)</p>', unsafe_allow_html=True)
        fill_j = st.selectbox("Job", job_labels_sorted, key=f"tt_fillj_{eid}", label_visibility="collapsed")
        fh1, fh2 = st.columns(2, gap="small")
        with fh1:
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
        with fh2:
            st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
            fill_n = st.text_input("Notes (optional)", "", key=f"tt_filln_{eid}", label_visibility="collapsed")
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
        confirm = st.checkbox("Clear all entries this week", key=f"tt_clr_{eid}")
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

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        st.markdown('<p class="ips-tt-field-label">Lines this day</p>', unsafe_allow_html=True)
        ents_all = idx.get((eid, wd_work), [])
        ents_show = [e for e in ents_all if not fj_id or str(e.get("job_id")) == fj_id]
        if not ents_show:
            st.caption("No lines yet for this day — add below.")
        edit_tid = str(st.session_state.get(TT_EDIT_ID_KEY) or "")
        for ent in ents_show:
            if str(ent.get("id") or "") == edit_tid:
                st.caption("This line is open in the small **Edit** box above the grid.")
                continue
            _render_entry_editor(
                ent,
                job_labels_sorted,
                job_label_to_id,
                fast=fast,
                from_table_panel=False,
            )
            st.markdown('<div class="ips-tt-entry-gap"></div>', unsafe_allow_html=True)
        st.markdown('<p class="ips-tt-field-label">Add line</p>', unsafe_allow_html=True)
        _render_new_entry_form(
            eid,
            wd_work,
            job_labels_sorted,
            job_label_to_id,
            default_job_label,
            ents_show,
            fast=fast,
        )


def _render_minimal_table_edit_popup(
    ent: dict,
    *,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    job_id_to_label: dict[str, str],
    emp_id_to_name: dict[str, str],
    fast: bool,
) -> None:
    """Tiny editor for table Edit action: hours, notes, S/T vs O/T; job/non-job fixed to current row."""
    te_id = str(ent.get("id"))
    cur_jid = str(ent.get("job_id") or "").strip()
    cur_nj = str(ent.get("non_job_code") or "").strip()
    if cur_jid:
        wi_snap = ("job", cur_jid)
    else:
        wi_snap = ("non_job", cur_nj)
    wk_item = f"work_item_{te_id}"
    if cur_jid:
        lb = _job_label_for_id(job_label_to_id, cur_jid) or str(job_id_to_label.get(cur_jid, "—"))
        st.session_state[wk_item] = {"type": "job", "id": cur_jid, "label": str(lb)}
    elif cur_nj:
        code = str(cur_nj).strip()
        st.session_state[wk_item] = {"type": "non_job", "code": code, "label": f"NON-JOB — {code}"}
    _init_row_snap_from_ent(te_id, ent, wi_snap)

    autosave = bool(st.session_state.get(TT_AUTOSAVE_KEY))
    acb = _autosave_callback_factory(te_id)
    ch_as = {"on_change": acb} if autosave else {}
    hstep = _hours_step(fast=fast)

    wd = str(ent.get("work_date") or "")[:10]
    eid = str(ent.get("employee_id") or "")
    enm = str(emp_id_to_name.get(eid, "") or "").strip() or (eid[:8] + "…" if len(eid) > 8 else eid)
    sub_line = (
        f"{html.escape(wd)} · {html.escape(enm)} · "
        f"{html.escape(_work_item_display(job_id=cur_jid, non_job_code=cur_nj, job_id_to_label=job_id_to_label)[:60])}"
    )

    with st.container(border=True):
        st.markdown(
            '<span class="ips-compact-form ips-tt-edit-mini-popup" aria-hidden="true"></span>'
            '<p class="ips-tt-edit-mini-title">Edit entry</p>'
            f'<p class="ips-tt-edit-mini-sub">{sub_line}</p>',
            unsafe_allow_html=True,
        )
        tt_ix = 0 if _tt_entry_time_type(ent) == "ST" else 1
        r0 = st.columns([0.55, 0.45, 1.2], gap="small")
        with r0[0]:
            field_marker("time-type")
            st.selectbox(
                "Time type",
                ["S/T", "O/T"],
                index=tt_ix,
                key=f"tt_tt_{te_id}",
                label_visibility="collapsed",
                **ch_as,
            )
        with r0[1]:
            field_marker("hours")
            st.number_input(
                "Hrs",
                min_value=0.0,
                max_value=24.0,
                value=float(ent.get("hours", 0) or 0),
                step=hstep,
                format="%.2f",
                key=f"tt_h_{te_id}",
                label_visibility="collapsed",
                **ch_as,
            )
        with r0[2]:
            field_marker("medium")
            st.text_input(
                "Notes",
                value=str(ent.get("notes") or ""),
                key=f"tt_n_{te_id}",
                label_visibility="collapsed",
                placeholder="Notes",
                **ch_as,
            )
        b1, b2 = st.columns([0.35, 0.35], gap="small")
        with b1:
            if st.button(
                "Save",
                key=f"tt_mini_sv_{te_id}",
                use_container_width=False,
            ):
                ok, err = _persist_time_entry_row(te_id, job_label_to_id)
                if ok:
                    st.session_state.pop(TT_EDIT_ID_KEY, None)
                    st.rerun()
                elif err:
                    if err.startswith("Pick a job"):
                        st.warning(err)
                    else:
                        st.error(err)
        with b2:
            if st.button(
                "Close",
                key=f"tt_mini_close_{te_id}",
                use_container_width=False,
            ):
                st.session_state.pop(TT_EDIT_ID_KEY, None)
                st.rerun()


def _render_entry_editor(
    ent: dict,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    *,
    fast: bool,
    from_table_panel: bool = False,
) -> None:
    te_id = str(ent.get("id"))
    cur_jid = str(ent.get("job_id") or "").strip()
    cur_nj = str(ent.get("non_job_code") or "").strip()
    work_item_options = _build_work_item_options(
        job_labels_sorted=job_labels_sorted,
        job_label_to_id=job_label_to_id,
    )
    wi_ix = _work_item_index_for_entry(work_item_options, ent=ent)
    wi_ix = min(max(wi_ix, 0), len(work_item_options) - 1) if work_item_options else 0
    if cur_jid:
        wi_snap = ("job", cur_jid)
    else:
        wi_snap = ("non_job", cur_nj)
    _init_row_snap_from_ent(te_id, ent, wi_snap)

    autosave = bool(st.session_state.get(TT_AUTOSAVE_KEY))
    acb = _autosave_callback_factory(te_id)
    ch_as = {"on_change": acb} if autosave else {}

    hstep = _hours_step(fast=fast)
    del_label = "Clear" if fast else "Delete"
    del_help = "Remove this time entry" if fast else "Delete this time entry"

    def _save_del_row() -> None:
        n_action = 3 if from_table_panel else 2
        cols = st.columns(n_action, gap="small")
        with cols[0]:
            if st.button(
                "Save",
                key=f"tt_sv_{te_id}",
                use_container_width=True,
                help="Save this row",
            ):
                ok, err = _persist_time_entry_row(te_id, job_label_to_id)
                if ok:
                    st.success("Updated.")
                    if from_table_panel:
                        st.session_state.pop(TT_EDIT_ID_KEY, None)
                    st.rerun()
                elif err:
                    if err.startswith("Pick a job"):
                        st.warning(err)
                    else:
                        st.error(err)
        with cols[1]:
            if st.button(
                del_label,
                key=f"tt_del_{te_id}",
                use_container_width=True,
                help=del_help,
            ):
                try:
                    delete_rows("time_entries", {"id": te_id})
                    _clear_row_snap(te_id)
                    if from_table_panel:
                        st.session_state.pop(TT_EDIT_ID_KEY, None)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")
        if from_table_panel:
            with cols[2]:
                if st.button(
                    "Close",
                    key=f"tt_close_{te_id}",
                    use_container_width=True,
                    help="Leave edit panel without navigating away",
                ):
                    st.session_state.pop(TT_EDIT_ID_KEY, None)
                    st.rerun()

    st.markdown('<p class="ips-tt-field-label">Work Item</p>', unsafe_allow_html=True)
    st.selectbox(
        "Work Item",
        work_item_options,
        index=wi_ix,
        key=f"work_item_{te_id}",
        label_visibility="collapsed",
        format_func=lambda o: str((o or {}).get("label") or "—"),
        **ch_as,
    )
    _wi = st.session_state.get(f"work_item_{te_id}")
    if isinstance(_wi, dict) and str(_wi.get("type") or "").strip() == "non_job":
        _nj = str(_wi.get("code") or "").strip()
        if _nj:
            st.markdown(_non_job_badge_html(_nj), unsafe_allow_html=True)
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


def _render_new_entry_form(
    employee_id: str,
    work_date_iso: str,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    default_job_label: str | None,
    entries_for_day: list[dict],
    *,
    fast: bool,
) -> None:
    work_item_options = _build_work_item_options(
        job_labels_sorted=job_labels_sorted,
        job_label_to_id=job_label_to_id,
    )
    d0 = 0
    if default_job_label and default_job_label in job_label_to_id:
        djid = str(job_label_to_id.get(default_job_label) or "").strip()
        for i, opt in enumerate(work_item_options):
            if opt.get("type") == "job" and str(opt.get("id") or "") == djid:
                d0 = i
                break
    d0 = min(max(d0, 0), len(work_item_options) - 1) if work_item_options else 0

    def_h = _tt_default_hours()
    hstep = _hours_step(fast=fast)
    dup_label = "Dup" if fast else "Duplicate"
    _k_wi = f"work_item_new_{employee_id}_{work_date_iso}"
    _k_h = f"tt_newh_{employee_id}_{work_date_iso}"
    _k_n = f"tt_newn_{employee_id}_{work_date_iso}"

    def _on_add() -> None:
        wi = st.session_state.get(_k_wi)
        hrs = float(st.session_state.get(_k_h) or 0)
        note = str(st.session_state.get(_k_n) or "").strip()
        if not isinstance(wi, dict):
            st.error("Invalid work item selection.")
            st.stop()
        wi_type = str(wi.get("type") or "").strip()
        if wi_type == "job":
            jid = str(wi.get("id") or "").strip()
            if not jid:
                st.error("Invalid work item.")
                st.stop()
            payload = {"job_id": jid, "non_job_code": None}
        elif wi_type == "non_job":
            nj = str(wi.get("code") or "").strip()
            if not nj:
                st.warning("Pick a work item.")
                st.stop()
            payload = {"job_id": None, "non_job_code": nj}
        else:
            st.warning("Pick a work item.")
            st.stop()
        payload.update(
            {
                "employee_id": employee_id,
                "work_date": work_date_iso[:10],
                "hours": float(hrs),
                "notes": note,
                "created_by": current_profile().get("id"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if hrs <= 0:
            st.error("Enter hours greater than zero.")
            st.stop()
        try:
            insert_row("time_entries", payload)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not add (duplicate for this day?): {exc}")

    def _on_dup() -> None:
        src = entries_for_day[-1] if entries_for_day else None
        if src:
            sjid = str(src.get("job_id") or "").strip()
            snj = str(src.get("non_job_code") or "").strip()
            hrs = float(src.get("hours") or 0) or def_h
            note = str(src.get("notes") or "").strip()
            if sjid:
                slabel = _job_label_for_id(job_label_to_id, sjid)
                if not slabel:
                    st.error("Could not resolve job for duplicate.")
                    st.stop()
                jid = job_label_to_id.get(slabel)
                if not jid:
                    st.error("Invalid job on source row.")
                    st.stop()
                payload = {
                    "employee_id": employee_id,
                    "job_id": jid,
                    "non_job_code": None,
                    "work_date": work_date_iso[:10],
                    "hours": float(hrs),
                    "notes": note,
                    "created_by": current_profile().get("id"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            elif snj:
                payload = {
                    "employee_id": employee_id,
                    "job_id": None,
                    "non_job_code": snj,
                    "work_date": work_date_iso[:10],
                    "hours": float(hrs),
                    "notes": note,
                    "created_by": current_profile().get("id"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                st.error("Invalid source row.")
                st.stop()
        else:
            if default_job_label and default_job_label in job_label_to_id:
                jid = job_label_to_id[default_job_label]
                hrs = float(def_h)
                note = ""
                payload = {
                    "employee_id": employee_id,
                    "job_id": jid,
                    "non_job_code": None,
                    "work_date": work_date_iso[:10],
                    "hours": float(hrs),
                    "notes": note,
                    "created_by": current_profile().get("id"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                st.error("No line to copy — pick a filter job or add a row.")
                st.stop()
        if hrs <= 0:
            st.error("Hours must be greater than zero.")
            st.stop()
        try:
            insert_row("time_entries", payload)
            st.rerun()
        except Exception as exc:
            st.error(f"Duplicate not added (same line this day?): {exc}")

    st.markdown('<div class="ips-tt-new-block">', unsafe_allow_html=True)
    st.markdown('<p class="ips-tt-field-label">Work Item</p>', unsafe_allow_html=True)
    st.selectbox(
        "Work Item",
        work_item_options,
        index=d0,
        key=_k_wi,
        label_visibility="collapsed",
        format_func=lambda o: str((o or {}).get("label") or "—"),
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
            key=_k_h,
            label_visibility="collapsed",
        )
    with r2:
        st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
        st.text_input(
            "Notes",
            value="",
            key=_k_n,
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
    st.markdown("</div>", unsafe_allow_html=True)


def _render_day_column_body(
    *,
    d: date,
    eid: str,
    idx: dict,
    fj_id: str | None,
    job_id_to_label: dict[str, str],
    show_day_heading: bool,
) -> float:
    """Day cell: hours subtotal, compact job summary; selected day (Quick Actions) shown via light outline."""
    wd = d.isoformat()
    ents_all = idx.get((eid, wd), [])
    ents_show = [e for e in ents_all if not fj_id or str(e.get("job_id")) == fj_id]
    day_sum = sum(float(e.get("hours", 0) or 0) for e in ents_show)

    sel_k = _tt_qa_day_key(eid)
    sel_wd = str(st.session_state.get(sel_k) or "")[:10]
    is_sel = sel_wd == wd and str(st.session_state.get(TT_OPEN_EMPLOYEE_POPUP_KEY) or "") == eid

    if show_day_heading:
        st.markdown(
            f'<div class="ips-tt-day-head">{d.strftime("%a %m/%d")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="ips-tt-day-sum">{day_sum:.1f} h</div>',
        unsafe_allow_html=True,
    )

    parts: list[str] = []
    for e in ents_show[:6]:
        h = float(e.get("hours", 0) or 0)
        jid = str(e.get("job_id") or "").strip()
        nj = str(e.get("non_job_code") or "").strip()
        if jid:
            lab = str(job_id_to_label.get(jid) or "?")
            short = lab[:18] + ("…" if len(lab) > 18 else "")
            parts.append(f"{short} {h:.1f}h")
        elif nj:
            parts.append(f"NON-JOB — {nj} {h:.1f}h")
    summary = " · ".join(parts) if parts else ""
    if summary:
        st.caption(summary[:260] + ("…" if len(summary) > 260 else ""))

    block_cls = "ips-tt-day-block"
    if is_sel:
        block_cls += " ips-tt-day-block-selected"
    st.markdown(
        f'<div class="{block_cls}"><span class="ips-tt-day-cell ips-tt-day-summary" aria-hidden="true"></span></div>',
        unsafe_allow_html=True,
    )

    return day_sum


# ─── Weekly Timecard Grid (new compact per-employee design) ──────────────────

_WC_COL_RATIOS = [1.1, 3.2, 0.95, 0.95, 2.0, 1.5]  # day, job, st, ot, notes, action


def _wc_job_key(job_id: str | None, nj: str | None) -> str:
    """Stable, key-safe fragment derived from job_id or non_job_code."""
    if job_id:
        return "j" + job_id.replace("-", "")[:16]
    if nj:
        return "nj" + str(nj).upper().replace(" ", "")[:8]
    return "nojob"


def _group_day_entries(
    entries: list[dict],
    job_id_to_label: dict[str, str],
) -> list[dict]:
    """Combine ST and OT entries per (job/non-job code) into one dict per group."""
    groups: dict[str, dict] = {}
    for ent in entries:
        jid = str(ent.get("job_id") or "").strip()
        nj = str(ent.get("non_job_code") or "").strip()
        gk = _wc_job_key(jid or None, nj or None)
        if gk not in groups:
            if jid:
                label = str(job_id_to_label.get(jid) or jid[:24])
            elif nj:
                label = f"NON-JOB — {nj}"
            else:
                label = "—"
            groups[gk] = {
                "gk": gk,
                "job_id": jid or None,
                "nj": nj or None,
                "label": label,
                "st_id": None,
                "ot_id": None,
                "st_hrs": 0.0,
                "ot_hrs": 0.0,
                "notes": "",
            }
        g = groups[gk]
        h = float(ent.get("hours") or 0)
        n = str(ent.get("notes") or "").strip()
        if _tt_entry_time_type(ent) == "OT":
            g["ot_id"] = str(ent.get("id") or "") or None
            g["ot_hrs"] = h
            if n and not g["notes"]:
                g["notes"] = n
        else:
            g["st_id"] = str(ent.get("id") or "") or None
            g["st_hrs"] = h
            if n:
                g["notes"] = n
    return list(groups.values())


def _wc_key(eid: str, day_iso: str, gk: str, week_iso: str, field: str) -> str:
    return f"wc_{eid[:8]}_{day_iso}_{gk}_{week_iso.replace('-', '')}_{field}"


def _wc_add_key(eid: str, day_iso: str, week_iso: str, field: str) -> str:
    return f"wca_{eid[:8]}_{day_iso}_{week_iso.replace('-', '')}_{field}"


def _wc_clear_row_state(eid: str, day_iso: str, gk: str, week_iso: str) -> None:
    """Remove cached widget state for one row so it re-reads from DB on rerun."""
    for field in ["job", "st", "ot", "notes"]:
        st.session_state.pop(_wc_key(eid, day_iso, gk, week_iso, field), None)


def _wc_clear_add_row_state(eid: str, day_iso: str, week_iso: str) -> None:
    """Remove cached widget state for an add-row after successful submit."""
    for field in ["job", "st", "ot", "notes"]:
        st.session_state.pop(_wc_add_key(eid, day_iso, week_iso, field), None)


def _save_timecard_row(
    *,
    eid: str,
    d: date,
    orig_job_id: str | None,
    orig_nj: str | None,
    orig_st_id: str | None,
    orig_ot_id: str | None,
    new_job_id: str | None,
    new_nj: str | None,
    new_st_hrs: float,
    new_ot_hrs: float,
    new_notes: str,
    uid: Any,
    ts_now: str,
) -> tuple[bool, str]:
    """Upsert/delete ST and OT entries for one combined timecard row."""
    job_changed = str(orig_job_id or "") != str(new_job_id or "") or str(orig_nj or "") != str(new_nj or "")

    if job_changed:
        for tid in [orig_st_id, orig_ot_id]:
            if tid:
                try:
                    delete_rows("time_entries", {"id": tid})
                except Exception as exc:
                    return False, str(exc)
        orig_st_id = None
        orig_ot_id = None

    if new_st_hrs > 0:
        try:
            upsert_time_entry(
                employee_id=eid, job_id=new_job_id, work_date=d,
                hours=new_st_hrs, notes=new_notes, created_by=uid,
                updated_at_iso=ts_now, non_job_code=new_nj, time_type="ST",
            )
        except Exception as exc:
            return False, str(exc)
    elif orig_st_id:
        try:
            delete_rows("time_entries", {"id": orig_st_id})
        except Exception as exc:
            return False, str(exc)

    if new_ot_hrs > 0:
        try:
            upsert_time_entry(
                employee_id=eid, job_id=new_job_id, work_date=d,
                hours=new_ot_hrs, notes=new_notes, created_by=uid,
                updated_at_iso=ts_now, non_job_code=new_nj, time_type="OT",
            )
        except Exception as exc:
            return False, str(exc)
    elif orig_ot_id:
        try:
            delete_rows("time_entries", {"id": orig_ot_id})
        except Exception as exc:
            return False, str(exc)

    return True, ""


def _resolve_job_from_label(
    label: str, job_label_to_id: dict[str, str]
) -> tuple[str | None, str | None]:
    """From a selectbox label return (job_id, non_job_code)."""
    if label.startswith("NON-JOB — "):
        code = label[len("NON-JOB — "):].strip()
        return None, code or None
    jid = str(job_label_to_id.get(label) or "").strip()
    return jid or None, None


def _build_full_job_options(all_job_labels: list[str]) -> list[str]:
    """Combine job labels with NON-JOB category labels."""
    nj_labels = [f"NON-JOB — {c}" for c in NON_JOB_CATEGORY_OPTIONS if c]
    return all_job_labels + nj_labels


def _label_for_group(g: dict, job_id_to_label: dict[str, str]) -> str:
    if g["job_id"]:
        return str(job_id_to_label.get(g["job_id"]) or g.get("label") or g["job_id"][:24])
    if g["nj"]:
        return f"NON-JOB — {g['nj']}"
    return "—"


def _render_wc_col_headers() -> None:
    cols = st.columns(_WC_COL_RATIOS, gap="small")
    for col, lbl in zip(cols, ["Day", "Job / Work Item", "S/T h", "O/T h", "Notes", ""]):
        with col:
            st.markdown(f'<p class="ips-wc-col-hdr">{html.escape(lbl)}</p>', unsafe_allow_html=True)


def _render_wc_existing_row(
    *,
    eid: str,
    d: date,
    week_start: date,
    today: date,
    g: dict,
    full_job_labels: list[str],
    job_label_to_id: dict[str, str],
    job_id_to_label: dict[str, str],
    uid: Any,
    ts_now: str,
    show_day_label: bool,
) -> None:
    """One combined S/T + O/T edit row for an existing (job, day) group."""
    day_iso = d.isoformat()
    week_iso = week_start.isoformat()
    gk = g["gk"]

    # Stable widget keys
    jk = _wc_key(eid, day_iso, gk, week_iso, "job")
    stk = _wc_key(eid, day_iso, gk, week_iso, "st")
    otk = _wc_key(eid, day_iso, gk, week_iso, "ot")
    nk = _wc_key(eid, day_iso, gk, week_iso, "notes")

    # Resolve current job label and its index in the dropdown
    job_lbl = _label_for_group(g, job_id_to_label)
    if full_job_labels:
        try:
            job_idx = full_job_labels.index(job_lbl)
        except ValueError:
            # Job not in list (inactive/closed); prepend it so it's still visible
            full_job_labels = [job_lbl] + full_job_labels
            job_idx = 0
    else:
        job_idx = 0

    is_today = d == today
    day_cls = "ips-wc-day-today" if is_today else ""
    if show_day_label:
        day_html = (
            f'<p class="ips-wc-day-lbl {day_cls}">{d.strftime("%a")}</p>'
            f'<p class="ips-wc-day-date">{d.strftime("%m/%d")}</p>'
        )
    else:
        day_html = '<p class="ips-wc-day-lbl">&nbsp;</p>'

    cols = st.columns(_WC_COL_RATIOS, gap="small")
    with cols[0]:
        st.markdown(day_html, unsafe_allow_html=True)
    with cols[1]:
        sel_job = st.selectbox(
            "Job",
            full_job_labels,
            index=min(job_idx, max(0, len(full_job_labels) - 1)),
            key=jk,
            label_visibility="collapsed",
        )
    with cols[2]:
        new_st = st.number_input(
            "S/T h",
            min_value=0.0,
            max_value=24.0,
            value=g["st_hrs"],
            step=0.25,
            format="%.2f",
            key=stk,
            label_visibility="collapsed",
        )
    with cols[3]:
        new_ot = st.number_input(
            "O/T h",
            min_value=0.0,
            max_value=24.0,
            value=g["ot_hrs"],
            step=0.25,
            format="%.2f",
            key=otk,
            label_visibility="collapsed",
        )
    with cols[4]:
        new_notes = st.text_input(
            "Notes",
            value=g["notes"],
            key=nk,
            label_visibility="collapsed",
            placeholder="Notes…",
        )
    with cols[5]:
        sv_col, dl_col = st.columns([1, 1], gap="small")
        with sv_col:
            save_key = f"wcsv_{eid[:8]}_{day_iso}_{gk}_{week_iso.replace('-', '')}"
            if st.button("Save", key=save_key, use_container_width=True, type="primary"):
                cur_st = float(st.session_state.get(stk, g["st_hrs"]))
                cur_ot = float(st.session_state.get(otk, g["ot_hrs"]))
                cur_notes = str(st.session_state.get(nk, g["notes"]) or "").strip()
                cur_job_lbl = st.session_state.get(jk, sel_job)
                new_jid, new_nj = _resolve_job_from_label(str(cur_job_lbl), job_label_to_id)
                if not new_jid and not new_nj:
                    st.warning("Pick a valid job or work item.")
                else:
                    ok, err = _save_timecard_row(
                        eid=eid, d=d,
                        orig_job_id=g["job_id"], orig_nj=g["nj"],
                        orig_st_id=g["st_id"], orig_ot_id=g["ot_id"],
                        new_job_id=new_jid, new_nj=new_nj,
                        new_st_hrs=cur_st, new_ot_hrs=cur_ot,
                        new_notes=cur_notes, uid=uid, ts_now=ts_now,
                    )
                    if ok:
                        _wc_clear_row_state(eid, day_iso, gk, week_iso)
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error(err or "Save failed.")
        with dl_col:
            del_key = f"wcdel_{eid[:8]}_{day_iso}_{gk}_{week_iso.replace('-', '')}"
            if st.button("✕", key=del_key, use_container_width=True, help="Remove this row"):
                for tid in [g["st_id"], g["ot_id"]]:
                    if tid:
                        try:
                            delete_rows("time_entries", {"id": tid})
                        except Exception as exc:
                            st.error(str(exc))
                            return
                _wc_clear_row_state(eid, day_iso, gk, week_iso)
                try:
                    st.cache_data.clear()
                except Exception:
                    pass
                st.rerun()


def _render_wc_add_row(
    *,
    eid: str,
    d: date,
    week_start: date,
    today: date,
    has_existing_rows: bool,
    full_job_labels: list[str],
    job_label_to_id: dict[str, str],
    fj_default_label: str | None,
    uid: Any,
    ts_now: str,
) -> None:
    """Compact add-new-entry row at the bottom of each day section."""
    if not full_job_labels:
        return
    day_iso = d.isoformat()
    week_iso = week_start.isoformat()
    is_today = d == today

    default_lbl = fj_default_label if (fj_default_label and fj_default_label in full_job_labels) else full_job_labels[0]
    try:
        default_idx = full_job_labels.index(default_lbl)
    except ValueError:
        default_idx = 0

    jk = _wc_add_key(eid, day_iso, week_iso, "job")
    stk = _wc_add_key(eid, day_iso, week_iso, "st")
    otk = _wc_add_key(eid, day_iso, week_iso, "ot")
    nk = _wc_add_key(eid, day_iso, week_iso, "notes")

    day_cls = "ips-wc-day-today" if is_today else ""
    if not has_existing_rows:
        day_html = (
            f'<p class="ips-wc-day-lbl {day_cls}">{d.strftime("%a")}</p>'
            f'<p class="ips-wc-day-date">{d.strftime("%m/%d")}</p>'
        )
    else:
        day_html = '<p class="ips-wc-day-lbl" style="opacity:0">&nbsp;</p>'

    # Marker span for CSS day separator on add row
    st.markdown('<span class="ips-wc-add-row" aria-hidden="true"></span>', unsafe_allow_html=True)
    cols = st.columns(_WC_COL_RATIOS, gap="small")
    with cols[0]:
        st.markdown(day_html, unsafe_allow_html=True)
    with cols[1]:
        sel_job = st.selectbox(
            "Job",
            full_job_labels,
            index=default_idx,
            key=jk,
            label_visibility="collapsed",
        )
    with cols[2]:
        new_st = st.number_input(
            "S/T h", min_value=0.0, max_value=24.0, value=0.0, step=0.25,
            format="%.2f", key=stk, label_visibility="collapsed",
        )
    with cols[3]:
        new_ot = st.number_input(
            "O/T h", min_value=0.0, max_value=24.0, value=0.0, step=0.25,
            format="%.2f", key=otk, label_visibility="collapsed",
        )
    with cols[4]:
        new_notes = st.text_input(
            "Notes", value="", key=nk, label_visibility="collapsed", placeholder="Notes…",
        )
    with cols[5]:
        add_key = f"wcadd_{eid[:8]}_{day_iso}_{week_iso.replace('-', '')}"
        if st.button("＋ Add", key=add_key, use_container_width=True, type="secondary"):
            cur_st = float(st.session_state.get(stk, 0.0))
            cur_ot = float(st.session_state.get(otk, 0.0))
            cur_notes = str(st.session_state.get(nk, "") or "").strip()
            cur_job_lbl = st.session_state.get(jk, sel_job)
            if cur_st <= 0 and cur_ot <= 0:
                st.warning("Enter S/T or O/T hours.")
            else:
                new_jid, new_nj = _resolve_job_from_label(str(cur_job_lbl), job_label_to_id)
                if not new_jid and not new_nj:
                    st.warning("Pick a valid job or work item.")
                else:
                    ok = True
                    err = ""
                    if cur_st > 0:
                        try:
                            upsert_time_entry(
                                employee_id=eid, job_id=new_jid, work_date=d,
                                hours=cur_st, notes=cur_notes, created_by=uid,
                                updated_at_iso=ts_now, non_job_code=new_nj, time_type="ST",
                            )
                        except Exception as exc:
                            ok, err = False, str(exc)
                    if ok and cur_ot > 0:
                        try:
                            upsert_time_entry(
                                employee_id=eid, job_id=new_jid, work_date=d,
                                hours=cur_ot, notes=cur_notes, created_by=uid,
                                updated_at_iso=ts_now, non_job_code=new_nj, time_type="OT",
                            )
                        except Exception as exc:
                            ok, err = False, str(exc)
                    if ok:
                        _wc_clear_add_row_state(eid, day_iso, week_iso)
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error(err or "Add failed.")


def _render_employee_timecard_card(
    *,
    emp: dict,
    days: list[date],
    week_start: date,
    today: date,
    idx: dict,
    filt: _TTFiltersResult,
    fj_id: str | None,
    full_job_labels: list[str],
    job_label_to_id: dict[str, str],
    uid: Any,
    ts_now: str,
) -> None:
    """Full weekly timecard card for one employee."""
    eid = str(emp.get("id"))
    nm = str(emp.get("name", "") or "—").strip() or "—"
    week_iso = week_start.isoformat()

    # Compute weekly ST/OT totals
    wk_st = wk_ot = 0.0
    for d in days:
        for ent in idx.get((eid, d.isoformat()), []):
            if fj_id and str(ent.get("job_id") or "") != fj_id:
                continue
            h = float(ent.get("hours") or 0)
            if _tt_entry_time_type(ent) == "OT":
                wk_ot += h
            else:
                wk_st += h
    wk_total = wk_st + wk_ot

    with st.container(border=True):
        st.markdown('<span class="ips-wc-card" aria-hidden="true"></span>', unsafe_allow_html=True)

        # Card header: employee name + weekly totals + Quick Actions toggle
        h1, h2, h3 = st.columns([3, 2.5, 0.55], gap="small")
        with h1:
            st.markdown(f"**{html.escape(nm)}**")
        with h2:
            over = wk_total > filt.ot_threshold
            ot_note = f"  ⚠ >{filt.ot_threshold:g}h" if over else ""
            st.caption(
                f"Week {week_start.strftime('%b %d')}–{days[-1].strftime('%b %d')}  ·  "
                f"S/T **{wk_st:.1f}** · O/T **{wk_ot:.1f}** · Total **{wk_total:.1f}** h{ot_note}"
            )
        with h3:
            _render_qa_toggle_button(eid)

        # Column header row
        _render_wc_col_headers()

        # One section per day
        for di, d in enumerate(days):
            day_iso = d.isoformat()
            entries_for_day = list(idx.get((eid, day_iso), []))
            if fj_id:
                entries_for_day = [e for e in entries_for_day if str(e.get("job_id") or "") == fj_id]

            groups = _group_day_entries(entries_for_day, filt.job_id_to_label)

            # Thin separator between days (except first)
            if di > 0:
                sep_cols = st.columns(_WC_COL_RATIOS, gap="small")
                with sep_cols[0]:
                    st.markdown('<span class="ips-wc-day-sep" aria-hidden="true"></span>', unsafe_allow_html=True)

            is_first_row = True
            for g in groups:
                _render_wc_existing_row(
                    eid=eid, d=d, week_start=week_start, today=today,
                    g=g,
                    full_job_labels=list(full_job_labels),
                    job_label_to_id=job_label_to_id,
                    job_id_to_label=filt.job_id_to_label,
                    uid=uid, ts_now=ts_now,
                    show_day_label=is_first_row,
                )
                is_first_row = False

            _render_wc_add_row(
                eid=eid, d=d, week_start=week_start, today=today,
                has_existing_rows=bool(groups),
                full_job_labels=full_job_labels,
                job_label_to_id=job_label_to_id,
                fj_default_label=filt.default_job_label,
                uid=uid, ts_now=ts_now,
            )


def _render_weekly_timecard_grid(
    *,
    today: date,
    week_start: date,
    days: list[date],
    filt: _TTFiltersResult,
    week_data: _TTWeekDataResult,
    fj_id: str | None,
) -> tuple[list[float], list[float]]:
    """Per-employee weekly timecard cards — replaces the old single-day form."""
    uid = current_profile().get("id")
    ts_now = datetime.now(timezone.utc).isoformat()

    # Build job options (all jobs for existing rows; active + non-job for add rows)
    jobs_raw = _tt_load_jobs_rows(limit=5000)
    _, job_label_to_id, all_job_labels = build_job_dropdown_label_maps(jobs_raw)
    if not jobs_raw:
        st.caption("**No jobs loaded** — check Supabase `jobs` table and RLS policies.")

    full_job_labels = _build_full_job_options(list(all_job_labels))

    # Quick-actions popup (rendered outside the card so it floats above)
    open_emp = str(st.session_state.get(TT_OPEN_EMPLOYEE_POPUP_KEY) or "")
    if open_emp:
        matching = [e for e in week_data.visible_emps if str(e.get("id")) == open_emp]
        if matching:
            nm_qa = str(matching[0].get("name", "") or "—").strip()
            _render_quick_actions_popup(
                eid=open_emp, emp_name=nm_qa, days=days,
                week_start=week_start, week_end=days[-1], today=today,
                idx=week_data.idx, fj_id=fj_id,
                job_labels_sorted=filt.job_labels_sorted,
                job_label_to_id=filt.job_label_to_id,
                default_job_label=filt.default_job_label,
                fast=False, user_id=uid, ts_iso=ts_now,
            )

    # Render one card per employee
    for emp in week_data.visible_emps:
        _render_employee_timecard_card(
            emp=emp, days=days, week_start=week_start, today=today,
            idx=week_data.idx, filt=filt, fj_id=fj_id,
            full_job_labels=full_job_labels,
            job_label_to_id=job_label_to_id,
            uid=uid, ts_now=ts_now,
        )

    # Week grand total summary
    wk_st = wk_ot = 0.0
    for eid_k in filt.show_emp_ids:
        _, s, o = _tt_emp_hours_breakdown_for_week(str(eid_k), days, week_data.idx, fj_id)
        wk_st += s
        wk_ot += o
    st.caption(
        f"Week total (all visible employees): S/T **{wk_st:.2f}** h · "
        f"O/T **{wk_ot:.2f}** h · Σ **{wk_st + wk_ot:.2f}** h"
    )

    day_col_totals = _tt_day_column_totals(week_data.idx, days, filt.show_emp_ids, fj_id)
    grid_ratios = _week_grid_column_ratios(fast=False)
    return day_col_totals, grid_ratios


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
            st_h = sum(float(e.get("hours", 0) or 0) for e in ents if _tt_entry_time_type(e) == "ST")
            ot_h = sum(float(e.get("hours", 0) or 0) for e in ents if _tt_entry_time_type(e) == "OT")
            _labels: set[str] = set()
            for e in ents:
                jid = str(e.get("job_id") or "").strip()
                if jid:
                    _labels.add(job_id_to_label.get(jid, "?"))
                else:
                    nj = str(e.get("non_job_code") or "").strip()
                    if nj:
                        _labels.add(f"NON-JOB — {nj}")
            jobs = ", ".join(sorted(_labels))
            day_cell = f"{h:.1f} h (S/T {st_h:.1f} · O/T {ot_h:.1f})"
            if jobs:
                day_cell += f" ({jobs})"
            r[d.strftime("%a %m/%d")] = day_cell
            total += h
        r["Σ Week"] = f"{total:.1f}"
        rows.append(r)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
