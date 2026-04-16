from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

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
            padding: 10px 12px 14px 12px;
            margin-bottom: 8px;
        }
        .ips-tt-wrap { }
        .ips-tt-row-over {
            border-left: 4px solid #f87171 !important;
            background: rgba(248, 113, 113, 0.12) !important;
            border-radius: 6px;
            padding-left: 8px !important;
        }
        .ips-tt-day-head {
            color: #9fb6d9 !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            text-align: center !important;
            margin-bottom: 4px !important;
        }
        .ips-tt-metric {
            color: #e2e8f0 !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        .ips-tt-job-badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.02em;
            color: #f8fafc !important;
            background: var(--badge, #334155);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 6px;
            padding: 3px 8px;
            margin-bottom: 6px;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ips-tt-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
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


def render() -> None:
    render_header("Time Tracking", subtitle="Weekly calendar — log hours by employee and job")

    _inject_tt_styles()
    try:
        from ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

    pm_row1, pm_row2 = st.columns([4, 1])
    with pm_row1:
        st.caption(
            "For a **foreman-style crew grid** (all employees × jobs, one day at a time), "
            "use **PM Matrix Time Entry** in the sidebar."
        )
    with pm_row2:
        if st.button("Open PM Matrix", key="tt_open_pm_matrix", use_container_width=True):
            st.session_state[IPS_NAV_PENDING_KEY] = "PM Matrix Time Entry"
            st.rerun()

    role = current_role()
    can_edit = role in TT_EDIT_ROLES

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
    if cnav1.button("◀ Previous week", use_container_width=True):
        st.session_state["tt_week_start"] = week_start - timedelta(days=7)
        st.rerun()
    if cnav2.button("Next week ▶", use_container_width=True):
        st.session_state["tt_week_start"] = week_start + timedelta(days=7)
        st.rerun()
    if cnav3.button("This week", use_container_width=True):
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

    emp_choices = {f"{e.get('name', '')} ({str(e.get('id'))[:8]})": str(e.get("id")) for e in active_employees if e.get("id")}
    emp_label_list = sorted(emp_choices.keys(), key=str.casefold)
    filt_emp = cnav4.multiselect(
        "Filter employees",
        options=emp_label_list,
        default=emp_label_list,
        help="Restrict which rows are shown.",
    )
    show_emp_ids = {emp_choices[lb] for lb in filt_emp} if filt_emp else set(emp_choices.values())

    job_opts = ["(All jobs)"] + job_labels_sorted
    filt_job = cnav5.selectbox(
        "Filter job (new entries default)",
        options=job_opts,
        index=0,
        help="When not “All”, new time lines default to this job; existing lines for other jobs still show.",
    )
    default_job_label = None if filt_job == "(All jobs)" else filt_job

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
        st.warning("No employees match the filter. Adjust filters or add employees (**People** → Employees).")
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
            if st.button("← Back to week", use_container_width=True, key="tt_entry_view_back"):
                st.session_state.pop("tt_entry_view_id", None)
                st.rerun()
            st.divider()

    te_ed = st.session_state.get("tt_entry_edit_id")
    if te_ed and can_edit:
        er = fetch_one("time_entries", {"id": te_ed})
        if not er:
            st.session_state.pop("tt_entry_edit_id", None)
        else:
            st.subheader("Edit time entry")
            cur_jid = str(er.get("job_id") or "")
            cur_label = next(
                (lb for lb, j in job_label_to_id.items() if j == cur_jid),
                job_labels_sorted[0] if job_labels_sorted else "",
            )
            j_ix = job_labels_sorted.index(cur_label) if cur_label in job_labels_sorted else 0
            jp = st.selectbox("Job", job_labels_sorted, index=j_ix, key="tt_flat_edit_job")
            hrs = st.number_input(
                "Hours",
                min_value=0.0,
                max_value=24.0,
                value=float(er.get("hours") or 0),
                step=0.5,
                format="%.2f",
                key="tt_flat_edit_h",
            )
            note = st.text_input("Notes", value=str(er.get("notes") or ""), key="tt_flat_edit_n")
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("Save changes", type="primary", use_container_width=True, key="tt_flat_edit_sv"):
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
                            st.session_state.pop("tt_entry_edit_id", None)
                            st.success("Updated.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Save failed: {exc}")
            with bc2:
                if st.button("Cancel", use_container_width=True, key="tt_flat_edit_ca"):
                    st.session_state.pop("tt_entry_edit_id", None)
                    st.rerun()
            st.divider()

    if not entries_df.empty and "id" in entries_df.columns:
        st.subheader("Time entries (this week)")
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
            st.session_state.pop("tt_entry_edit_id", None)
            st.rerun()
        if actions.get("edit") and sel and len(sel) == 1 and can_edit:
            st.session_state["tt_entry_edit_id"] = str(sel[0])
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

    # —— Editable grid ——
    day_col_totals = [0.0] * 7
    uid = current_profile().get("id")
    ts_now = datetime.now(timezone.utc).isoformat()

    for emp in visible_emps:
        eid = str(emp.get("id"))
        row_h = sum_employee_week_hours(grid_rows, eid, days)
        over = row_h > ot_threshold

        row_container = st.container(border=True)
        with row_container:
            h0, *hday, hlast = st.columns([1.4] + [1.0] * 7 + [0.7])
            with h0:
                if over:
                    st.markdown(
                        f'<p class="ips-tt-row-over ips-tt-metric">{emp.get("name", "")} — {row_h:.1f} h (over {ot_threshold:g} h)</p>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f'<p class="ips-tt-metric">{emp.get("name", "")}</p>', unsafe_allow_html=True)
                st.caption(f"{row_h:.1f} h / week")
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
                wd = d.isoformat()
                with hday[di]:
                    st.markdown(
                        f'<div class="ips-tt-day-head">{d.strftime("%a %m/%d")}</div>',
                        unsafe_allow_html=True,
                    )
                    ents_all = idx.get((eid, wd), [])
                    ents_show = [e for e in ents_all if not fj_id or str(e.get("job_id")) == fj_id]
                    day_sum = sum(float(e.get("hours", 0) or 0) for e in ents_show)
                    day_col_totals[di] += day_sum

                    for ent in ents_show:
                        _render_entry_editor(ent, job_labels_sorted, job_label_to_id, ordered_job_ids)

                    _render_new_entry_form(
                        eid,
                        wd,
                        job_labels_sorted,
                        job_label_to_id,
                        default_job_label,
                    )
            with hlast:
                st.caption("Σ")
                st.markdown(f'<p class="ips-tt-metric">{row_h:.1f}</p>', unsafe_allow_html=True)

    # Footer totals row
    st.markdown("##### Week totals")
    f0, *fday, fl = st.columns([1.4] + [1.0] * 7 + [0.7])
    with f0:
        st.markdown("**Day Σ**")
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
    with st.expander("⚡ Quick actions", expanded=False):
        st.caption("Copy **from the previous calendar day** into the day you select (Monday uses the prior Sunday).")
        dest_pick = st.selectbox("Destination day", day_labels, key=f"tt_qdest_{eid}")
        if st.button("Copy previous day → selected day", key=f"tt_cpday_{eid}", use_container_width=True):
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

        st.divider()
        if st.button("Copy entire previous week (replaces this week)", key=f"tt_cpw_{eid}", use_container_width=True):
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

        st.divider()
        st.caption("Fill one job across Mon–Sun (upserts hours per day).")
        fill_j = st.selectbox("Job", job_labels_sorted, key=f"tt_fillj_{eid}")
        fill_h = st.number_input("Hours per day", 0.0, 24.0, 8.0, step=0.5, key=f"tt_fillh_{eid}")
        fill_n = st.text_input("Notes (optional)", "", key=f"tt_filln_{eid}")
        if st.button("Fill selected job Mon–Sun", key=f"tt_fill_{eid}", use_container_width=True):
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

        st.divider()
        st.caption("Delete every **time_entries** row for this employee in this week.")
        confirm = st.checkbox("I understand entries will be removed", key=f"tt_clr_{eid}")
        if st.button("Clear week", key=f"tt_clrb_{eid}", disabled=not confirm, use_container_width=True):
            try:
                delete_employee_week(eid, week_start, week_end)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _render_entry_editor(
    ent: dict,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    ordered_job_ids: list[str],
) -> None:
    te_id = str(ent.get("id"))
    cur_jid = str(ent.get("job_id") or "")
    cur_label = next((lb for lb, j in job_label_to_id.items() if j == cur_jid), job_labels_sorted[0] if job_labels_sorted else "")
    with st.container(border=True):
        st.markdown(_job_badge_html(cur_label, cur_jid, ordered_job_ids), unsafe_allow_html=True)
        j_ix = job_labels_sorted.index(cur_label) if cur_label in job_labels_sorted else 0
        job_pick = st.selectbox(
            "Job",
            job_labels_sorted,
            index=j_ix,
            key=f"tt_job_{te_id}",
            label_visibility="collapsed",
        )
        hrs = st.number_input(
            "Hrs",
            min_value=0.0,
            max_value=24.0,
            value=float(ent.get("hours", 0) or 0),
            step=0.5,
            format="%.2f",
            key=f"tt_h_{te_id}",
            label_visibility="collapsed",
        )
        note = st.text_input(
            "Notes",
            value=str(ent.get("notes") or ""),
            key=f"tt_n_{te_id}",
            label_visibility="collapsed",
            placeholder="Notes",
        )
        b1, b2 = st.columns(2)
        if b1.button("Save", key=f"tt_sv_{te_id}", use_container_width=True):
            new_jid = job_label_to_id.get(job_pick)
            if not new_jid:
                st.error("Pick a job.")
                st.stop()
            payload = {
                "job_id": new_jid,
                "hours": float(hrs or 0),
                "notes": str(note).strip(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                update_rows("time_entries", payload, {"id": te_id})
                st.success("Updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Save failed: {exc}")
        if b2.button("✕", key=f"tt_del_{te_id}", use_container_width=True):
            try:
                delete_rows("time_entries", {"id": te_id})
                st.rerun()
            except Exception as exc:
                st.error(f"Delete failed: {exc}")


def _render_new_entry_form(
    employee_id: str,
    work_date_iso: str,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    default_job_label: str | None,
) -> None:
    if not job_labels_sorted:
        return
    d0 = 0
    if default_job_label and default_job_label in job_labels_sorted:
        d0 = job_labels_sorted.index(default_job_label)
    with st.expander("+ Log time", expanded=False):
        job_pick = st.selectbox("Job", job_labels_sorted, index=d0, key=f"tt_newj_{employee_id}_{work_date_iso}")
        hrs = st.number_input("Hours", min_value=0.0, max_value=24.0, value=0.0, step=0.5, key=f"tt_newh_{employee_id}_{work_date_iso}")
        note = st.text_input("Notes", value="", key=f"tt_newn_{employee_id}_{work_date_iso}")
        if st.button("Add entry", key=f"tt_add_{employee_id}_{work_date_iso}"):
            jid = job_label_to_id.get(job_pick)
            if not jid:
                st.error("Invalid job.")
                st.stop()
            if float(hrs or 0) <= 0:
                st.error("Enter hours greater than zero.")
                st.stop()
            payload = {
                "employee_id": employee_id,
                "job_id": jid,
                "work_date": work_date_iso[:10],
                "hours": float(hrs),
                "notes": str(note).strip(),
                "created_by": current_profile().get("id"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                insert_row("time_entries", payload)
                st.rerun()
            except Exception as exc:
                st.error(f"Could not add (duplicate job for this day?): {exc}")


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
