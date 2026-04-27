from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st
from auth import current_profile, current_role
from branding import render_header
from data_cache import fetch_table_for_session

try:
    from app.db import delete_rows_admin, fetch_table_admin, insert_row_admin, update_rows_admin
except ImportError:
    from db import delete_rows_admin, fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore

try:
    from app.services.job_service import job_number_display, job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from services.job_service import job_number_display, job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

try:
    from app.ui import IPS_NAV_PENDING_KEY, role_can_open_page
except ImportError:
    from ui import IPS_NAV_PENDING_KEY, role_can_open_page  # type: ignore


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


def count_low_stock_items(items: list[dict]) -> int:
    n = 0
    for r in items or []:
        if not isinstance(r, dict):
            continue
        try:
            qoh = float(r.get("quantity_on_hand") or 0)
            reorder = float(r.get("reorder_point") or 0)
        except Exception:
            continue
        if reorder > 0 and qoh <= reorder:
            n += 1
    return n


def count_open_todos(todos: list[dict]) -> int:
    return sum(1 for t in todos or [] if str((t or {}).get("status") or "Open").strip() != "Complete")


def _render_low_stock_alerts(items: list[dict]) -> None:
    rows: list[dict] = []
    for r in items or []:
        if not isinstance(r, dict):
            continue
        try:
            qoh = float(r.get("quantity_on_hand") or 0)
            reorder = float(r.get("reorder_point") or 0)
        except Exception:
            continue
        if reorder <= 0 or qoh > reorder:
            continue
        rows.append(
            {
                "Item": str(r.get("item_name") or "").strip() or "—",
                "SKU": str(r.get("sku") or "").strip() or "—",
                "Category": str(r.get("category") or "").strip() or "—",
                "On Hand": qoh,
                "Reorder": reorder,
                "Status": "Low",
            }
        )
    with st.container(border=True):
        st.markdown("##### Low Stock Alerts")
        if not rows:
            st.caption("No low-stock inventory items.")
            return
        st.dataframe(pd.DataFrame(rows).head(12), use_container_width=True, hide_index=True, height=320)


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


def _low_stock_rows(inventory_items: list[dict], *, limit: int = 12) -> list[dict]:
    rows: list[dict] = []
    for item in inventory_items or []:
        if not isinstance(item, dict):
            continue
        qoh = _dash_kf(item.get("quantity_on_hand"))
        reorder = _dash_kf(item.get("reorder_point"))
        if qoh <= reorder:
            rows.append(item)
    rows.sort(key=lambda r: (_dash_kf(r.get("quantity_on_hand")) - _dash_kf(r.get("reorder_point")), str(r.get("item_name") or "")))
    return rows[:limit]


def _low_stock_display_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Item": str(r.get("item_name") or "").strip() or "—",
                "SKU": str(r.get("sku") or "").strip() or "—",
                "Category": str(r.get("category") or "").strip() or "—",
                "On Hand": r.get("quantity_on_hand") if r.get("quantity_on_hand") not in (None, "") else 0,
                "Reorder": r.get("reorder_point") if r.get("reorder_point") not in (None, "") else 0,
            }
            for r in rows
        ]
    )


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

_TODO_STATUSES = ("Open", "In Progress", "Complete")
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
        st.markdown("##### To-Do List")

        # Filters
        f1, f2 = st.columns([1.2, 1.8], gap="small")
        scope = f1.selectbox("Filter", ["My tasks", "All open tasks", "Completed"], key="dash_todo_scope")
        show_completed = scope == "Completed"

        id_to_label, ordered_ids = _profiles_for_todo_assign(session_key, use_admin=use_admin)
        assignee_pick = None
        if scope == "My tasks" and me:
            assignee_pick = me

        # Fetch todos (prefer admin for office roles; falls back through db helper if needed)
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

        rows: list[dict] = []
        for t in todos or []:
            if not isinstance(t, dict):
                continue
            status = str(t.get("status") or "Open").strip() or "Open"
            if show_completed:
                if status != "Complete":
                    continue
            else:
                if status == "Complete":
                    continue
            if assignee_pick and str(t.get("assigned_to") or "").strip() != assignee_pick:
                continue
            rows.append(t)

        # Sort: urgent first, then due date
        rows.sort(
            key=lambda r: (
                _todo_priority_rank(str(r.get("priority") or "Normal")),
                _todo_due_sort_key(r.get("due_date")),
                str(r.get("created_at") or ""),
            )
        )

        # Add task UI
        with st.expander("Add task", expanded=False):
            title = st.text_input("Title", key="dash_todo_add_title")
            desc = st.text_area("Description", key="dash_todo_add_desc", height=72)
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
                insert_row_admin("todos", payload)
                st.success("Task added.")
                st.rerun()

        if not rows:
            st.caption("No tasks to show.")
            return

        st.caption("Urgent tasks sort first. Completed tasks are hidden by default.")

        for t in rows:
            tid = str(t.get("id") or "").strip()
            if not tid:
                continue
            title = str(t.get("title") or "").strip() or "—"
            priority = str(t.get("priority") or "Normal").strip() or "Normal"
            status = str(t.get("status") or "Open").strip() or "Open"
            due = str(t.get("due_date") or "").strip() or "—"
            assigned_to = str(t.get("assigned_to") or "").strip()
            assigned_lbl = id_to_label.get(assigned_to, "—")

            r1, r2, r3, r4, r5 = st.columns([0.55, 3.4, 1.1, 1.3, 1.7], gap="small")
            with r1:
                done = st.checkbox(" ", value=False, key=f"todo_done_{tid}")
            with r2:
                st.markdown(f"**{title}**")
                if status and status != "Open":
                    st.caption(status)
            with r3:
                st.caption(priority)
            with r4:
                st.caption(due)
            with r5:
                st.caption(assigned_lbl)

            if done and status != "Complete":
                update_rows_admin(
                    "todos",
                    {"status": "Complete", "completed_at": datetime.utcnow().isoformat()},
                    {"id": tid},
                )
                st.rerun()

            with st.expander("Edit / details", expanded=False):
                et = st.text_input("Title", value=title, key=f"todo_edit_title_{tid}")
                ed = st.text_area("Description", value=str(t.get("description") or ""), key=f"todo_edit_desc_{tid}", height=72)
                c1, c2, c3 = st.columns(3, gap="small")
                # date_input can't take an arbitrary string; keep it optional via text to avoid crash
                due_s = c1.text_input("Due date (YYYY-MM-DD)", value="" if due == "—" else due, key=f"todo_edit_due_{tid}")
                epri = c2.selectbox("Priority", list(_TODO_PRIORITIES), index=max(0, list(_TODO_PRIORITIES).index(priority)) if priority in _TODO_PRIORITIES else 1, key=f"todo_edit_pri_{tid}")
                estat = c3.selectbox("Status", list(_TODO_STATUSES), index=max(0, list(_TODO_STATUSES).index(status)) if status in _TODO_STATUSES else 0, key=f"todo_edit_status_{tid}")
                assignee_opts = ["— Unassigned —"] + [id_to_label[i] for i in ordered_ids]
                cur_assignee_lbl = id_to_label.get(assigned_to, "— Unassigned —") if assigned_to else "— Unassigned —"
                assignee_label = st.selectbox("Assigned to", assignee_opts, index=max(0, assignee_opts.index(cur_assignee_lbl)) if cur_assignee_lbl in assignee_opts else 0, key=f"todo_edit_asg_{tid}")
                new_assigned_to = None
                if assignee_label and not assignee_label.startswith("—"):
                    for pid, lbl in id_to_label.items():
                        if lbl == assignee_label:
                            new_assigned_to = pid
                            break

                b1, b2 = st.columns(2, gap="small")
                with b1:
                    if st.button("Save", type="primary", use_container_width=True, key=f"todo_save_{tid}"):
                        payload: dict = {
                            "title": str(et or "").strip() or "—",
                            "description": str(ed or "").strip() or None,
                            "priority": str(epri or "Normal").strip() or "Normal",
                            "status": str(estat or "Open").strip() or "Open",
                            "assigned_to": new_assigned_to,
                        }
                        ds = str(due_s or "").strip()
                        payload["due_date"] = ds if ds else None
                        if payload["status"] == "Complete":
                            payload["completed_at"] = datetime.utcnow().isoformat()
                        update_rows_admin("todos", payload, {"id": tid})
                        st.success("Saved.")
                        st.rerun()
                with b2:
                    if st.button("Delete", type="secondary", use_container_width=True, key=f"todo_del_{tid}"):
                        delete_rows_admin("todos", {"id": tid})
                        st.success("Deleted.")
                        st.rerun()


def render() -> None:
    render_header(
        "IPS Dashboard",
        subtitle="Industrial Plant Solutions, LLC",
        help_text="Simple operating snapshot for jobs, inventory, tools, and open tasks.",
    )

    sk = str(current_profile().get("id") or "anonymous")
    use_admin = current_role() in {"admin", "pm"}
    _lim = 5000
    try:
        customers = fetch_table_for_session(
            "customers", session_key=sk, limit=_lim, order_by="customer_name", use_admin=use_admin
        )
    except Exception:
        customers = []
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
    try:
        inventory_items = fetch_table_for_session(
            "inventory_items", session_key=sk, limit=_lim, order_by="item_name", use_admin=use_admin
        )
    except Exception:
        inventory_items = []
    kit_items_d: list[dict] = []
    repl_d: list[dict] = []
    if role_can_open_page(current_role(), "Asset Database"):
        try:
            kit_items_d = fetch_table_for_session(
                "asset_kit_items",
                session_key=sk,
                limit=15000,
                order_by="parent_asset_id",
                use_admin=use_admin,
            )
        except Exception:
            kit_items_d = []
        try:
            repl_d = fetch_table_for_session(
                "asset_kit_replacements",
                session_key=sk,
                limit=25000,
                order_by="replacement_date",
                use_admin=use_admin,
            )
        except Exception:
            repl_d = []

    low_stock = _low_stock_rows(list(inventory_items or []), limit=12)
    checked_out_tools = [a for a in (assets or []) if isinstance(a, dict) and _asset_is_out(a)]

    try:
        todos_for_metric = fetch_table_for_session(
            "todos",
            session_key=sk,
            limit=2000,
            order_by="created_at",
            use_admin=use_admin,
        )
    except Exception:
        todos_for_metric = []
    open_todos = [
        t
        for t in (todos_for_metric or [])
        if isinstance(t, dict) and str(t.get("status") or "Open").strip() != "Complete"
    ]

    with st.container(border=True):
        st.markdown('<span class="ips-dash-metrics"></span>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5, gap="small")
        c1.metric("Active Jobs", count_awarded_jobs(jobs))
        c2.metric("Jobs Bidding", count_bidding_jobs(jobs))
        c3.metric("Low Stock Items", len(low_stock))
        c4.metric("Checked Out Tools", len(checked_out_tools))
        c5.metric("Open To-Dos", len(open_todos))

    left, right = st.columns(2, gap="medium")
    with left:
        _render_todo_list(session_key=sk, use_admin=use_admin)
    with right:
        _render_who_has_what_dashboard(
            list(assets or []),
            list(jobs or []),
            list(employees or []),
            role=current_role(),
        )

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("##### Low Stock Alerts")
            if not low_stock:
                st.caption("No low stock items right now.")
            else:
                st.dataframe(_low_stock_display_df(low_stock), use_container_width=True, hide_index=True, height=320)

    with right:
        with st.container(border=True):
            st.markdown("##### Recent Jobs")
            rj = _recent_jobs_rows(list(jobs or []))
            if not rj:
                st.caption("No jobs loaded yet.")
            else:
                st.dataframe(_jobs_display_df(rj), use_container_width=True, hide_index=True, height=320)
