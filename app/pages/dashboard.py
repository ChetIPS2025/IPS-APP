from __future__ import annotations

import html
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st
from auth import current_profile, current_role
from branding import render_header
from data_cache import clear_session_table_cache, fetch_table_for_session

try:
    from app.db import create_signed_url, delete_rows_admin, fetch_table_admin, insert_row_admin, update_rows_admin
except ImportError:
    from db import create_signed_url, delete_rows_admin, fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore

try:
    from app.services.job_service import job_number_display, job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from services.job_service import job_number_display, job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

try:
    from app.ui import IPS_NAV_PENDING_KEY, role_can_open_page
except ImportError:
    from ui import IPS_NAV_PENDING_KEY, role_can_open_page  # type: ignore

try:
    from app.ui.modal import inject_ips_modal_styles
except ImportError:
    from ui.modal import inject_ips_modal_styles  # type: ignore

try:
    from app.services import task_photos as _dash_task_photos
except ImportError:
    import services.task_photos as _dash_task_photos  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme as _dash_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme as _dash_field_light_theme  # type: ignore

try:
    from app.services.daily_work_packages import dashboard_dwp_snapshot, repeated_eod_delay_reasons
except ImportError:
    from services.daily_work_packages import dashboard_dwp_snapshot, repeated_eod_delay_reasons  # type: ignore


def _render_task_progress_dashboard(*, today: date, session_key: str, use_admin: bool) -> None:
    try:
        tasks = fetch_table_for_session(
            "job_tasks",
            session_key=session_key,
            limit=12000,
            order_by="planned_date",
            use_admin=use_admin,
        )
    except Exception:
        tasks = []
    try:
        packages = fetch_table_for_session(
            "daily_work_packages",
            session_key=session_key,
            limit=12000,
            order_by="work_date",
            use_admin=use_admin,
        )
    except Exception:
        packages = []
    try:
        package_tasks = fetch_table_for_session(
            "daily_work_package_tasks",
            session_key=session_key,
            limit=24000,
            order_by=None,
            use_admin=use_admin,
        )
    except Exception:
        package_tasks = []
    try:
        executions = fetch_table_for_session(
            "supervisor_daily_execution",
            session_key=session_key,
            limit=12000,
            order_by="updated_at",
            use_admin=use_admin,
        )
    except Exception:
        executions = []
    tp_new: list[dict[str, Any]] = []
    try:
        tp_new = fetch_table_for_session(
            "task_photos",
            session_key=session_key,
            limit=12000,
            order_by="created_at",
            use_admin=use_admin,
        )
    except Exception:
        tp_new = []
    try:
        task_photo_rows_legacy = fetch_table_for_session(
            "job_task_photos",
            session_key=session_key,
            limit=12000,
            order_by="created_at",
            use_admin=use_admin,
        )
    except Exception:
        task_photo_rows_legacy = []
    task_photo_rows: list[dict[str, Any]] = []
    for r in tp_new or []:
        if isinstance(r, dict):
            task_photo_rows.append({**r, "storage_path": str(r.get("file_url") or r.get("storage_path") or "")})
    task_photo_rows.extend([x for x in (task_photo_rows_legacy or []) if isinstance(x, dict)])
    ts = dashboard_dwp_snapshot(
        today=today,
        packages=list(packages or []),
        package_tasks=list(package_tasks or []),
        tasks=list(tasks or []),
        photo_rows=list(task_photo_rows or []),
    )
    repeat = repeated_eod_delay_reasons(packages=list(packages or []), executions=list(executions or []), today=today)
    _dash_field_light_theme()
    with st.container(border=True):
        st.markdown("##### Daily work packages (tasks)")
        st.caption(
            "Metrics only count tasks on a **Daily Work Package** dated today (idle jobs are excluded). "
            "Run **`sql/055_daily_work_packages_workflow.sql`** and **`sql/053_task_photos.sql`** as needed."
        )
        c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")
        c1.metric("Work packages today", f"{ts.get('work_packages_today', 0):,}")
        c2.metric("Tasks assigned today", f"{ts.get('tasks_assigned_today', 0):,}")
        c3.metric("Tasks completed today", f"{ts.get('tasks_completed_today', 0):,}")
        c4.metric("Blocked tasks", f"{ts.get('blocked', 0):,}")
        c5.metric("High priority open", f"{ts.get('high_priority_open', 0):,}")
        c6.metric("Missing after photos", f"{ts.get('missing_after_photo', 0):,}")
        if repeat:
            st.caption("Repeat shift delay reasons (14d): " + " · ".join(f"{a} ({b}×)" for a, b in repeat[:6])[:400])
        c_open1, c_open2 = st.columns(2, gap="small")
        with c_open1:
            if role_can_open_page(current_role(), "Work & Plan (Supervisor)") and st.button(
                "Work & Plan (Supervisor)", key="dash_tasks_super_open", use_container_width=True
            ):
                st.session_state[IPS_NAV_PENDING_KEY] = "Work & Plan (Supervisor)"
                st.rerun()
        with c_open2:
            if role_can_open_page(current_role(), "Assign Tasks (PM)") and st.button(
                "Assign Tasks (PM)", key="dash_tasks_pm_open", use_container_width=True
            ):
                st.session_state[IPS_NAV_PENDING_KEY] = "Assign Tasks (PM)"
                st.rerun()


def _norm_status(v) -> str:
    return " ".join(str(v or "").strip().split()).casefold()


_AWARDED_STATUS_TOKENS = {
    "awarded",
    "won",
    "active",
}

_BIDDING_STATUS_TOKENS = {
    "bidding",
    "estimating",
    "proposal",
    "quoted",
    # Job Database lifecycle (pre-award / in-flight work) — title-cased in DB, matched case-insensitively
    "draft",
    "submitted",
    "approved",
    "scheduled",
    "in progress",
    "on hold",
}


def _job_status_bucket(status_value) -> str | None:
    """
    Centralized job status normalization + classification.

    - trims whitespace and compares case-insensitively
    - treats substring matches as valid (handles inconsistent status text)
    - returns: "awarded" | "bidding" | None
    """
    s = _norm_status(status_value)
    if not s:
        return None
    if s in _AWARDED_STATUS_TOKENS or any(tok in s for tok in _AWARDED_STATUS_TOKENS):
        return "awarded"
    if s in _BIDDING_STATUS_TOKENS or any(tok in s for tok in _BIDDING_STATUS_TOKENS):
        return "bidding"
    return None


def count_awarded_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if _job_status_bucket((j or {}).get("status")) == "awarded")


def count_bidding_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if _job_status_bucket((j or {}).get("status")) == "bidding")


def count_active_employees(employees: list[dict]) -> int:
    rows = employees or []
    if not rows:
        return 0
    has_is_active = any(isinstance(r, dict) and "is_active" in r for r in rows)
    if not has_is_active:
        return len(rows)
    return sum(1 for r in rows if bool((r or {}).get("is_active", False)))


def _row_ts(row: dict) -> str:
    for k in ("updated_at", "modified_at", "created_at"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _recent_jobs_rows(jobs: list[dict], *, limit: int = 12) -> list[dict]:
    if not jobs:
        return []
    rows = sorted(jobs, key=_row_ts, reverse=True)
    return rows[:limit]


def _recent_estimates_rows(estimates: list[dict], *, limit: int = 12) -> list[dict]:
    if not estimates:
        return []
    rows = sorted(estimates, key=_row_ts, reverse=True)
    return rows[:limit]


def _jobs_display_df(rows: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for j in rows:
        if not isinstance(j, dict):
            continue
        jn = job_number_display(j.get("job_number"))
        out.append(
            {
                "Job #": jn or "—",
                "Name": str(j.get("job_name") or "").strip() or "—",
                "Status": str(j.get("status") or "").strip() or "—",
            }
        )
    return pd.DataFrame(out)


# Days out for dashboard "Who Has What" (match tool_dashboard overdue rule).
_DASH_OUT_OVERDUE_DAYS = 7
_KIT_REPL_WINDOW_DAYS = 90
_KIT_REPL_HOT_THRESHOLD = 3


def _dash_kf(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        s = str(v).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def _kit_line_short_qty(it: dict) -> float:
    exp = _dash_kf((it or {}).get("quantity"))
    qoh = (it or {}).get("quantity_on_hand")
    if qoh is not None and str(qoh).strip() != "":
        return max(0.0, exp - _dash_kf(qoh))
    return max(0.0, _dash_kf((it or {}).get("missing_count")))


def _render_kit_theft_alerts_dashboard(
    assets: list[dict],
    kit_items: list[dict],
    replacements: list[dict],
    *,
    role: str,
) -> None:
    """Tool trailer kit lines: shortages, replacement churn, estimated missing value."""
    if not role_can_open_page(role, "Asset Database"):
        return
    trailers = {
        str(a.get("id") or "").strip(): a
        for a in (assets or [])
        if isinstance(a, dict) and str(a.get("asset_type") or "").strip().lower() == "tool trailer"
    }
    if not trailers:
        return
    tids = set(trailers.keys())
    lines = [
        it
        for it in (kit_items or [])
        if isinstance(it, dict)
        and str(it.get("parent_asset_id") or "").strip() in tids
        and bool((it or {}).get("is_active", True))
    ]
    now = datetime.now(timezone.utc).date()
    start = now - timedelta(days=_KIT_REPL_WINDOW_DAYS)
    repl_90: list[dict] = []
    for r in replacements or []:
        if not isinstance(r, dict):
            continue
        ds = str(r.get("replacement_date") or "").strip()[:10]
        if not ds:
            continue
        try:
            d = datetime.fromisoformat(ds).date()
        except ValueError:
            continue
        if d >= start:
            repl_90.append(r)
    n_repl_90 = len(repl_90)
    c_item = Counter(str(r.get("kit_item_id") or "").strip() for r in repl_90 if str(r.get("kit_item_id") or "").strip())
    n_hot = sum(1 for _k, v in c_item.items() if v >= _KIT_REPL_HOT_THRESHOLD)
    n_short_lines = sum(1 for it in lines if _kit_line_short_qty(it) > 0.0001)
    miss_val = sum(_kit_line_short_qty(it) * _dash_kf(it.get("replacement_cost")) for it in lines)

    with st.container(border=True):
        st.markdown("##### Kit theft / audit signals")
        st.caption(
            f"Tool trailer kit lines only. **Hot items** = ≥{_KIT_REPL_HOT_THRESHOLD} replacement rows in the last "
            f"{_KIT_REPL_WINDOW_DAYS} days. Missing value uses shortage × replacement cost."
        )
        m1, m2, m3, m4 = st.columns(4, gap="small")
        m1.metric("Kit lines with shortage", f"{n_short_lines:,}")
        m2.metric(f"Replacements ({_KIT_REPL_WINDOW_DAYS}d)", f"{n_repl_90:,}")
        m3.metric("Hot kit items (90d)", f"{n_hot:,}")
        m4.metric("Est. missing value", f"${miss_val:,.0f}")
        if n_short_lines or n_hot:
            st.warning("Review **Asset Database** → open a **Tool Trailer** → **Tool Kits** → **Count / Audit Kit**.")
        if role_can_open_page(role, "Asset Database"):
            if st.button("Open Asset Database", key="dash_kit_open_adb", help="Manage trailers and kit audits"):
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Database"
                st.rerun()


def _parse_co_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _days_out_value(last_co: Any) -> float | None:
    dt = _parse_co_ts(last_co)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def _asset_is_out(row: dict) -> bool:
    stt = str((row or {}).get("status") or "").strip()
    holder = str((row or {}).get("current_holder_employee_id") or "").strip()
    return stt == "Checked Out" or bool(holder)


def _render_who_has_what_dashboard(
    assets: list[dict],
    jobs: list[dict],
    employees: list[dict],
    *,
    role: str,
) -> None:
    """Summary of assets that are checked out or have a holder (see assets table)."""
    rows = [a for a in (assets or []) if isinstance(a, dict) and _asset_is_out(a)]
    jobs_sorted = sort_jobs_by_number_then_name(list(jobs or []))
    job_by_id = {str(j.get("id")): j for j in jobs_sorted if j.get("id")}
    emp_id_to_name = {
        str(e["id"]): str(e.get("name") or "").strip() or "—"
        for e in (employees or [])
        if isinstance(e, dict) and e.get("id")
    }

    n_out = len(rows)
    n_overdue = 0
    n_on_job = 0
    for r in rows:
        if str(r.get("assigned_job_id") or "").strip():
            n_on_job += 1
        dv = _days_out_value(r.get("last_checkout_at"))
        if dv is not None and dv > _DASH_OUT_OVERDUE_DAYS:
            n_overdue += 1

    with st.container(border=True):
        st.markdown("##### Who Has What")
        st.caption("Tools and assets with **Checked Out** status or an assigned holder.")

        m1, m2, m3 = st.columns(3, gap="small")
        m1.metric("Checked out tools", f"{n_out:,}")
        m2.metric("Overdue tools", f"{n_overdue:,}")
        m3.metric("Assigned to jobs", f"{n_on_job:,}")

        if not rows:
            st.caption("Nothing checked out or held right now.")
        else:
            disp: list[dict] = []
            for r in rows:
                eid = str(r.get("current_holder_employee_id") or "").strip()
                holder = emp_id_to_name.get(eid) or str(r.get("assigned_employee") or "").strip() or "—"
                jid = r.get("assigned_job_id")
                jl = "—"
                if jid and str(jid).strip() in job_by_id:
                    jl = job_row_select_label(job_by_id[str(jid).strip()])
                co = _parse_co_ts(r.get("last_checkout_at"))
                co_s = co.strftime("%Y-%m-%d %H:%M") if co else "—"
                dv = _days_out_value(r.get("last_checkout_at"))
                days_s = f"{int(dv)} d" if dv is not None and dv >= 1.0 else (f"{dv:.1f} d" if dv is not None else "—")
                disp.append(
                    {
                        "Tool / asset": str(r.get("asset_name") or "—").strip() or "—",
                        "Holder": holder,
                        "Job": jl,
                        "Checked out": co_s,
                        "Days out": days_s,
                        "Status": str(r.get("status") or "").strip() or "—",
                    }
                )
            df = pd.DataFrame(disp)
            df["_sort"] = [_days_out_value(x.get("last_checkout_at")) for x in rows]
            df = df.sort_values(by="_sort", ascending=False, na_position="last").drop(
                columns=["_sort"], errors="ignore"
            )
            st.dataframe(df, use_container_width=True, hide_index=True, height=min(420, 44 + 36 * len(df)))

        if role_can_open_page(role, "Who Has What"):
            if st.button("View all", key="dash_whw_view_all", help="Open the full Who Has What page"):
                st.session_state[IPS_NAV_PENDING_KEY] = "Who Has What"
                st.rerun()


def _estimates_display_df(rows: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for e in rows:
        if not isinstance(e, dict):
            continue
        ts = _row_ts(e)
        ts_disp = ts[:19].replace("T", " ") if ts else "—"
        try:
            if "T" in ts and len(ts) >= 10:
                ts_disp = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts_disp = ts[:16] if ts else "—"
        out.append(
            {
                "Quote": str(e.get("quote_number") or "").strip() or "—",
                "Status": str(e.get("status") or "").strip() or "—",
                "Updated": ts_disp,
            }
        )
    return pd.DataFrame(out)

_TODO_STATUSES = ("Open", "In Progress", "Pending", "Waiting", "Complete", "Closed")
_TODO_VIEW_OPTIONS = ("Active Tasks", "Completed Tasks", "All Tasks")
_TODO_TERMINAL_STATUS_SLUGS = frozenset({"complete", "completed", "closed"})
_TODO_PRIORITIES = ("Low", "Normal", "High", "Urgent")
_TODO_PRIORITY_RANK = {"Urgent": 0, "High": 1, "Normal": 2, "Low": 3}


def _todo_priority_rank(v: str) -> int:
    return int(_TODO_PRIORITY_RANK.get(str(v or "Normal").strip().title(), 9))


def _todo_due_sort_key(v) -> tuple[int, str]:
    """None due dates sort last."""
    if v is None or str(v).strip() == "":
        return (1, "9999-12-31")
    s = str(v).strip()
    return (0, s)


def _todo_status_slug(status: Any) -> str:
    return str(status or "").strip().lower()


def _todo_is_terminal(status: Any) -> bool:
    """Hide from Active view when status is Complete/Completed/Closed (case-insensitive)."""
    return _todo_status_slug(status) in _TODO_TERMINAL_STATUS_SLUGS


def _todo_sort_rows(rows: list[dict]) -> list[dict]:
    rows.sort(
        key=lambda r: (
            _todo_priority_rank(str(r.get("priority") or "Normal")),
            _todo_due_sort_key(r.get("due_date")),
            str(r.get("created_at") or ""),
        )
    )
    return rows


def _todo_filter_for_view(todos: list[dict], view: str) -> tuple[list[dict], int]:
    """
    Filter todos for the selected view. Returns (display_rows, active_count).

    Active = any status except Complete/Completed/Closed; missing status counts as active.
    """
    valid = [t for t in (todos or []) if isinstance(t, dict) and str(t.get("id") or "").strip()]
    active_count = sum(1 for t in valid if not _todo_is_terminal(t.get("status")))
    view_l = str(view or _TODO_VIEW_OPTIONS[0]).strip()
    if view_l == "Completed Tasks":
        shown = [t for t in valid if _todo_is_terminal(t.get("status"))]
    elif view_l == "All Tasks":
        shown = list(valid)
    else:
        shown = [t for t in valid if not _todo_is_terminal(t.get("status"))]
    return _todo_sort_rows(shown), active_count


def _todo_dedupe_by_id(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        tid = str(r.get("id") or "").strip()
        if not tid or tid in seen:
            continue
        seen.add(tid)
        out.append(r)
    return out


def _todo_apply_search(rows: list[dict], q: str, id_to_label: dict[str, str]) -> list[dict]:
    qq = str(q or "").strip().lower()
    if not qq:
        return list(rows)
    out: list[dict] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        aid = str(r.get("assigned_to") or "").strip()
        blob = " ".join(
            [
                str(r.get("title") or ""),
                str(r.get("description") or ""),
                str(r.get("status") or ""),
                str(r.get("priority") or ""),
                id_to_label.get(aid, ""),
            ]
        ).lower()
        if qq in blob:
            out.append(r)
    return out


_TODO_LIST_CSS_KEY = "dash_todo_list_css_v4"


def _inject_todo_list_css() -> None:
    if st.session_state.get(_TODO_LIST_CSS_KEY):
        return
    st.session_state[_TODO_LIST_CSS_KEY] = True
    st.markdown(
        """
        <style>
        .ips-todo-sep {
          border: none;
          border-top: 1px solid #e2e8f0;
          margin: 0.35rem 0 0.45rem 0;
        }
        .ips-todo-title {
          font-weight: 700;
          font-size: 0.92rem;
          color: #0f172a;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 100%;
          margin: 0 !important;
          line-height: 1.25 !important;
        }
        .ips-todo-ellipsis {
          display: inline-block;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 0.78rem;
          color: #334155;
        }
        .ips-todo-badge {
          display: inline-block;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.03em;
          text-transform: uppercase;
          padding: 2px 7px;
          border-radius: 6px;
          border: 1px solid rgba(15, 23, 42, 0.12);
          line-height: 1.2;
          white-space: nowrap;
        }
        .ips-todo-badge-pri-low, .ips-todo-badge-pri-normal {
          background: #e2e8f0;
          color: #1e3a5f;
          border-color: #94a3b8;
        }
        .ips-todo-badge-pri-high {
          background: #fef3c7;
          color: #92400e;
          border-color: #fcd34d;
        }
        .ips-todo-badge-pri-urgent {
          background: #fee2e2;
          color: #991b1b;
          border-color: #f87171;
        }
        .ips-todo-badge-st-open {
          background: #dbeafe;
          color: #1e40af;
          border-color: #93c5fd;
        }
        .ips-todo-badge-st-in_progress {
          background: #ffedd5;
          color: #9a3412;
          border-color: #fdba74;
        }
        .ips-todo-badge-st-pending {
          background: #ede9fe;
          color: #5b21b6;
          border-color: #c4b5fd;
        }
        .ips-todo-badge-st-waiting {
          background: #f1f5f9;
          color: #475569;
          border-color: #cbd5e1;
        }
        .ips-todo-badge-st-terminal {
          background: #dcfce7;
          color: #166534;
          border-color: #86efac;
        }
        .ips-todo-badge-st-default {
          background: #f1f5f9;
          color: #334155;
          border-color: #cbd5e1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _todo_pri_badge_html(priority: str) -> str:
    p = str(priority or "Normal").strip().title()
    slug = str(priority or "normal").strip().lower().replace(" ", "_")
    if slug in ("urgent",):
        cls = "ips-todo-badge ips-todo-badge-pri-urgent"
    elif slug in ("high",):
        cls = "ips-todo-badge ips-todo-badge-pri-high"
    else:
        cls = "ips-todo-badge ips-todo-badge-pri-normal"
    return f'<span class="{cls}">{html.escape(p)}</span>'


def _todo_status_badge_html(status: str) -> str:
    s = str(status or "Open").strip()
    slug = _todo_status_slug(s).replace(" ", "_")
    if _todo_is_terminal(s):
        cls = "ips-todo-badge ips-todo-badge-st-terminal"
    elif slug in ("open",):
        cls = "ips-todo-badge ips-todo-badge-st-open"
    elif slug in ("in_progress",):
        cls = "ips-todo-badge ips-todo-badge-st-in_progress"
    elif slug in ("waiting",):
        cls = "ips-todo-badge ips-todo-badge-st-waiting"
    elif slug in ("pending",):
        cls = "ips-todo-badge ips-todo-badge-st-pending"
    else:
        cls = "ips-todo-badge ips-todo-badge-st-default"
    return f'<span class="{cls}">{html.escape(s)}</span>'


def _todo_trunc(s: str, n: int) -> str:
    t = str(s or "").strip()
    return t if len(t) <= n else (t[: max(0, n - 1)] + "…")


@st.dialog("Task details", width="small")
def _dash_todo_view_dialog(*, row: dict[str, Any], id_to_label: dict[str, str]) -> None:
    inject_ips_modal_styles()
    tid = str(row.get("id") or "").strip()
    st.markdown(f"### {html.escape(str(row.get('title') or '—'))}")
    aid = str(row.get("assigned_to") or "").strip()
    st.markdown(
        "<p style='font-size:0.82rem;color:#475569;margin:0 0 0.5rem 0'>"
        f"<strong>Status</strong> {html.escape(str(row.get('status') or 'Open'))} · "
        f"<strong>Priority</strong> {html.escape(str(row.get('priority') or 'Normal'))} · "
        f"<strong>Due</strong> {html.escape(str(row.get('due_date') or '—'))} · "
        f"<strong>Assigned</strong> {html.escape(id_to_label.get(aid, '—'))}"
        "</p>",
        unsafe_allow_html=True,
    )
    desc = str(row.get("description") or "").strip()
    if desc:
        st.markdown("**Description**")
        st.markdown(f"<div style='white-space:pre-wrap;font-size:0.9rem;color:#1e293b'>{html.escape(desc)}</div>", unsafe_allow_html=True)
    else:
        st.caption("No description.")
    if st.button("Close", use_container_width=True, key=f"dash_todo_dlg_view_close_{tid}"):
        st.session_state.pop("dash_todo_dlg_view", None)
        st.rerun()


@st.dialog("Edit task", width="small")
def _dash_todo_edit_dialog(
    *,
    row: dict[str, Any],
    id_to_label: dict[str, str],
    ordered_ids: list[str],
    me: str,
) -> None:
    inject_ips_modal_styles()
    tid = str(row.get("id") or "").strip()
    title = str(row.get("title") or "").strip() or "—"
    priority = str(row.get("priority") or "Normal").strip() or "Normal"
    status = str(row.get("status") or "Open").strip() or "Open"
    due = str(row.get("due_date") or "").strip() or "—"
    assigned_to = str(row.get("assigned_to") or "").strip()
    assignee_opts = ["— Unassigned —"] + [id_to_label[i] for i in ordered_ids]
    cur_assignee_lbl = id_to_label.get(assigned_to, "— Unassigned —") if assigned_to else "— Unassigned —"
    st.markdown(f"### {html.escape(title)}")

    with st.form(f"dash_todo_edit_f_{tid}", clear_on_submit=False):
        et = st.text_input("Title", value=title, key=f"dash_todo_ed_title_{tid}")
        ed = st.text_area("Description", value=str(row.get("description") or ""), height=88, key=f"dash_todo_ed_desc_{tid}")
        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            due_s = st.text_input("Due date (YYYY-MM-DD)", value="" if due == "—" else due, key=f"dash_todo_ed_due_{tid}")
        with c2:
            epri = st.selectbox(
                "Priority",
                list(_TODO_PRIORITIES),
                index=max(0, list(_TODO_PRIORITIES).index(priority)) if priority in _TODO_PRIORITIES else 1,
                key=f"dash_todo_ed_pri_{tid}",
            )
        with c3:
            status_ix = list(_TODO_STATUSES).index(status) if status in _TODO_STATUSES else 0
            estat = st.selectbox("Status", list(_TODO_STATUSES), index=status_ix, key=f"dash_todo_ed_stat_{tid}")
        st.selectbox(
            "Assigned to",
            assignee_opts,
            index=max(0, assignee_opts.index(cur_assignee_lbl)) if cur_assignee_lbl in assignee_opts else 0,
            key=f"dash_todo_ed_asg_{tid}",
        )
        save = st.form_submit_button("Save", type="primary", use_container_width=True)
    if st.button("Cancel", type="secondary", use_container_width=True, key=f"dash_todo_ed_cancel_{tid}"):
        st.session_state.pop("dash_todo_dlg_edit", None)
        st.rerun()

    if save:
        et = str(st.session_state.get(f"dash_todo_ed_title_{tid}") or "").strip()
        ed = str(st.session_state.get(f"dash_todo_ed_desc_{tid}") or "").strip()
        due_s = str(st.session_state.get(f"dash_todo_ed_due_{tid}") or "").strip()
        epri = str(st.session_state.get(f"dash_todo_ed_pri_{tid}") or "Normal").strip()
        estat = str(st.session_state.get(f"dash_todo_ed_stat_{tid}") or "Open").strip()
        assignee_label = str(st.session_state.get(f"dash_todo_ed_asg_{tid}") or "")
        new_assigned_to = None
        if assignee_label and not assignee_label.startswith("—"):
            for pid, lbl in id_to_label.items():
                if lbl == assignee_label:
                    new_assigned_to = pid
                    break
        new_status = str(estat or "Open").strip() or "Open"
        payload: dict[str, Any] = {
            "title": et or "—",
            "description": ed or None,
            "priority": str(epri or "Normal").strip() or "Normal",
            "status": new_status,
            "assigned_to": new_assigned_to,
        }
        ds = str(due_s or "").strip()
        payload["due_date"] = ds if ds else None
        if _todo_is_terminal(new_status):
            payload["completed_at"] = datetime.now(timezone.utc).isoformat()
        else:
            payload["completed_at"] = None
        try:
            update_rows_admin("todos", payload, {"id": tid})
            clear_session_table_cache()
            st.session_state.pop("dash_todo_dlg_edit", None)
            st.success("Saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


@st.dialog("Delete task?", width="small")
def _dash_todo_delete_dialog(*, tid: str, title: str) -> None:
    inject_ips_modal_styles()
    st.markdown(f"Permanently delete **{html.escape(title)}**?")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Delete", type="primary", use_container_width=True, key=f"dash_todo_del_go_{tid}"):
            try:
                delete_rows_admin("todos", {"id": tid})
                clear_session_table_cache()
                st.session_state.pop("dash_todo_dlg_del", None)
                st.success("Deleted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with c2:
        if st.button("Cancel", type="secondary", use_container_width=True, key=f"dash_todo_del_no_{tid}"):
            st.session_state.pop("dash_todo_dlg_del", None)
            st.rerun()


def _profiles_for_todo_assign(session_key: str, *, use_admin: bool) -> tuple[dict[str, str], list[str]]:
    """Return (id->label, ordered_ids) for assigned_to choices."""
    try:
        profs = fetch_table_for_session(
            "profiles",
            session_key=session_key,
            limit=5000,
            order_by="email",
            use_admin=use_admin,
        )
    except Exception:
        profs = []
    id_to_label: dict[str, str] = {}
    ordered: list[str] = []
    for p in profs or []:
        pid = str((p or {}).get("id") or "").strip()
        if not pid:
            continue
        email = str((p or {}).get("email") or "").strip()
        nm = str((p or {}).get("full_name") or "").strip()
        label = nm or email or pid[:8] + "…"
        id_to_label[pid] = label
        ordered.append(pid)
    return id_to_label, ordered


def _render_todo_list(*, session_key: str, use_admin: bool) -> None:
    prof = current_profile()
    me = str(prof.get("id") or "").strip()

    with st.container(border=True):
        _inject_todo_list_css()
        id_to_label, ordered_ids = _profiles_for_todo_assign(session_key, use_admin=use_admin)

        try:
            todos = fetch_table_for_session(
                "todos",
                session_key=session_key,
                limit=2000,
                order_by="created_at",
                use_admin=use_admin,
            )
        except Exception:
            todos = []

        raw_list = [t for t in (todos or []) if isinstance(t, dict) and str(t.get("id") or "").strip()]
        valid_todos = _todo_dedupe_by_id(raw_list)
        active_count = sum(1 for t in valid_todos if not _todo_is_terminal(t.get("status")))

        h1, h2, h3 = st.columns([1.35, 1.25, 1], gap="small")
        with h1:
            st.markdown(f"##### To-Do List ({active_count})")
        with h2:
            st.text_input(
                "Search",
                key="dash_todo_search_q",
                placeholder="Search…",
                label_visibility="collapsed",
            )
        with h3:
            view = st.selectbox(
                "Show",
                list(_TODO_VIEW_OPTIONS),
                key="dash_todo_view",
                label_visibility="collapsed",
            )

        rows_base, _ = _todo_filter_for_view(valid_todos, view)
        q = str(st.session_state.get("dash_todo_search_q") or "")
        rows = _todo_apply_search(rows_base, q, id_to_label)

        with st.expander("Add task", expanded=False):
            title = st.text_input("Title", key="dash_todo_add_title")
            desc = st.text_area("Description", key="dash_todo_add_desc", height=64)
            c1, c2, c3 = st.columns(3, gap="small")
            due = c1.date_input("Due date", value=None, key="dash_todo_add_due")
            priority = c2.selectbox("Priority", list(_TODO_PRIORITIES), index=1, key="dash_todo_add_pri")
            status = c3.selectbox("Status", list(_TODO_STATUSES), index=0, key="dash_todo_add_status")
            assignee_opts = ["— Unassigned —"] + [id_to_label[i] for i in ordered_ids]
            assignee_label = st.selectbox("Assigned to", assignee_opts, key="dash_todo_add_assignee")
            assigned_to = None
            if assignee_label and not assignee_label.startswith("—"):
                for pid, lbl in id_to_label.items():
                    if lbl == assignee_label:
                        assigned_to = pid
                        break

            if st.button("Add task", type="primary", use_container_width=True, key="dash_todo_add_btn"):
                t = str(title or "").strip()
                if not t:
                    st.error("Title is required.")
                    st.stop()
                payload = {
                    "title": t,
                    "description": str(desc or "").strip() or None,
                    "priority": str(priority or "Normal").strip() or "Normal",
                    "status": str(status or "Open").strip() or "Open",
                    "created_by": me or None,
                    "assigned_to": assigned_to,
                }
                if due is not None:
                    payload["due_date"] = str(due)
                if _todo_is_terminal(payload["status"]):
                    payload["completed_at"] = datetime.now(timezone.utc).isoformat()
                insert_row_admin("todos", payload)
                clear_session_table_cache()
                st.success("Task added.")
                st.rerun()

        if not rows:
            if view == "Completed Tasks":
                st.caption("No completed tasks.")
            elif view == "All Tasks":
                st.caption("No tasks.")
            else:
                st.caption("No active tasks.")
        else:
            st.caption("Urgent / high priority sort first · row actions for details, edit, or delete.")
            for idx, t in enumerate(rows):
                tid = str(t.get("id") or "").strip()
                if not tid:
                    continue
                if idx:
                    st.markdown('<hr class="ips-todo-sep" />', unsafe_allow_html=True)
                title = str(t.get("title") or "").strip() or "—"
                priority = str(t.get("priority") or "Normal").strip() or "Normal"
                status = str(t.get("status") or "Open").strip() or "Open"
                due = str(t.get("due_date") or "").strip() or "—"
                assigned_to = str(t.get("assigned_to") or "").strip()
                assigned_lbl = id_to_label.get(assigned_to, "—")
                is_terminal = _todo_is_terminal(status)
                title_esc = html.escape(_todo_trunc(title, 80))
                full_title_esc = html.escape(title)
                asg_esc = html.escape(_todo_trunc(assigned_lbl, 28))
                asg_full_esc = html.escape(assigned_lbl)

                with st.container(border=False):
                    c1, c2, c3, c4, c5, c6 = st.columns([2.15, 0.9, 0.72, 1.05, 0.95, 1.2], gap="small")
                    with c1:
                        st.markdown(
                            f'<p class="ips-todo-title" title="{full_title_esc}">{title_esc}</p>',
                            unsafe_allow_html=True,
                        )
                    with c2:
                        st.markdown(_todo_pri_badge_html(priority), unsafe_allow_html=True)
                    with c3:
                        st.caption(due if due != "—" else "—")
                    with c4:
                        st.markdown(
                            f'<span class="ips-todo-ellipsis" title="{asg_full_esc}">{asg_esc}</span>',
                            unsafe_allow_html=True,
                        )
                    with c5:
                        st.markdown(_todo_status_badge_html(status), unsafe_allow_html=True)
                    with c6:
                        a1, a2, a3, a4 = st.columns(4, gap="small")
                        with a1:
                            if st.button("View", key=f"dash_todo_v_{tid}", help="Details"):
                                st.session_state["dash_todo_dlg_view"] = tid
                                st.rerun()
                        with a2:
                            if st.button("Edit", key=f"dash_todo_e_{tid}", help="Edit task"):
                                st.session_state["dash_todo_dlg_edit"] = tid
                                st.rerun()
                        with a3:
                            if is_terminal:
                                if st.button("Reopen", key=f"dash_todo_c_{tid}", help="Mark not complete"):
                                    update_rows_admin(
                                        "todos",
                                        {"status": "Open", "completed_at": None},
                                        {"id": tid},
                                    )
                                    clear_session_table_cache()
                                    st.rerun()
                            else:
                                if st.button("Done", key=f"dash_todo_c_{tid}", help="Mark complete"):
                                    update_rows_admin(
                                        "todos",
                                        {
                                            "status": "Complete",
                                            "completed_at": datetime.now(timezone.utc).isoformat(),
                                        },
                                        {"id": tid},
                                    )
                                    clear_session_table_cache()
                                    st.rerun()
                        with a4:
                            if st.button("Del", key=f"dash_todo_d_{tid}", help="Delete task"):
                                st.session_state["dash_todo_dlg_del"] = tid
                                st.rerun()

        by_id = {str(x.get("id")): x for x in valid_todos if str(x.get("id") or "").strip()}
        v = str(st.session_state.get("dash_todo_dlg_view") or "").strip()
        e = str(st.session_state.get("dash_todo_dlg_edit") or "").strip()
        d = str(st.session_state.get("dash_todo_dlg_del") or "").strip()
        if v and v in by_id:
            _dash_todo_view_dialog(row=dict(by_id[v]), id_to_label=id_to_label)
        elif e and e in by_id:
            _dash_todo_edit_dialog(
                row=dict(by_id[e]),
                id_to_label=id_to_label,
                ordered_ids=ordered_ids,
                me=me,
            )
        elif d and d in by_id:
            _dash_todo_delete_dialog(tid=d, title=str(by_id[d].get("title") or "—"))


def render() -> None:
    render_header(
        "IPS Dashboard",
        subtitle="Industrial Plant Solutions, LLC",
        help_text="A simple snapshot for office + field: jobs, low stock, checked-out tools, and your to-dos.",
    )

    sk = str(current_profile().get("id") or "anonymous")
    use_admin = current_role() in {"admin", "manager"}
    _lim = 5000
    try:
        jobs = fetch_table_for_session(
            "jobs", session_key=sk, limit=_lim, order_by="job_number", use_admin=use_admin
        )
    except Exception:
        jobs = []
    try:
        estimates = fetch_table_for_session(
            "estimates", session_key=sk, limit=_lim, order_by="quote_number", use_admin=use_admin
        )
    except Exception:
        estimates = []
    try:
        employees = fetch_table_for_session(
            "employees", session_key=sk, limit=_lim, order_by="name", use_admin=use_admin
        )
    except Exception:
        employees = []
    try:
        assets = fetch_table_for_session(
            "assets", session_key=sk, limit=_lim, order_by="asset_name", use_admin=use_admin
        )
    except Exception:
        assets = []
    inv_rows: list[dict] = []
    if role_can_open_page(current_role(), "Inventory"):
        try:
            inv_rows = fetch_table_for_session(
                "inventory_items",
                session_key=sk,
                limit=12000,
                order_by="item_name",
                use_admin=use_admin,
            )
        except Exception:
            inv_rows = []

    low_n = 0
    if inv_rows:
        try:
            df_inv = pd.DataFrame(inv_rows)
            if "is_active" in df_inv.columns:
                df_inv = df_inv[df_inv["is_active"] != False]  # noqa: E712
            qoh = pd.to_numeric(df_inv.get("quantity_on_hand", 0), errors="coerce").fillna(0)
            rp = pd.to_numeric(df_inv.get("reorder_point", 0), errors="coerce").fillna(0)
            low_n = int((qoh <= rp).sum())
        except Exception:
            low_n = 0
    out_n = sum(
        1
        for a in (assets or [])
        if str((a or {}).get("status") or "").strip() == "Checked Out"
        or str((a or {}).get("current_holder_employee_id") or "").strip()
    )
    try:
        todos = fetch_table_for_session("todos", session_key=sk, limit=2000, order_by="created_at", use_admin=use_admin)
        open_todos = sum(
            1
            for t in (todos or [])
            if isinstance(t, dict) and not _todo_is_terminal((t or {}).get("status"))
        )
    except Exception:
        open_todos = 0

    _dash_field_light_theme()
    with st.container(border=True):
        st.markdown("##### Operations snapshot")
        m3, m4, m5 = st.columns(3, gap="small")
        m3.metric("Low stock items", f"{low_n:,}")
        m4.metric("Checked out tools", f"{out_n:,}")
        m5.metric("Open to-dos", f"{open_todos:,}")

    _render_task_progress_dashboard(today=date.today(), session_key=sk, use_admin=use_admin)

    _render_who_has_what_dashboard(
        list(assets or []),
        list(jobs or []),
        list(employees or []),
        role=current_role(),
    )

    # Low stock alerts (keep simple; details belong on Inventory page).
    if inv_rows and low_n > 0:
        try:
            df_inv2 = pd.DataFrame(inv_rows)
            if "is_active" in df_inv2.columns:
                df_inv2 = df_inv2[df_inv2["is_active"] != False]  # noqa: E712
            qoh2 = pd.to_numeric(df_inv2.get("quantity_on_hand", 0), errors="coerce").fillna(0)
            rp2 = pd.to_numeric(df_inv2.get("reorder_point", 0), errors="coerce").fillna(0)
            low_df = df_inv2.loc[qoh2 <= rp2, :].copy()
            show_cols = [c for c in ("item_name", "sku", "category", "quantity_on_hand", "reorder_point") if c in low_df.columns]
            if show_cols:
                disp = low_df[show_cols].copy()
                disp = disp.rename(
                    columns={
                        "item_name": "Item",
                        "quantity_on_hand": "On Hand",
                        "reorder_point": "Reorder",
                        "unit_cost": "Unit Cost",
                        "qr_code_value": "QR Code",
                    }
                )
                with st.container(border=True):
                    st.markdown("##### Low Stock Alerts")
                    st.caption("Items at or below reorder point (based on current on-hand vs reorder settings).")
                    st.dataframe(disp, use_container_width=True, hide_index=True, height=min(360, 44 + 30 * len(disp)))
        except Exception:
            pass

    _render_todo_list(session_key=sk, use_admin=use_admin)

    st.markdown("##### Recent jobs")
    rj = _recent_jobs_rows(list(jobs or []))
    if not rj:
        st.caption("No jobs loaded yet.")
    else:
        st.dataframe(_jobs_display_df(rj), use_container_width=True, hide_index=True, height=320)
