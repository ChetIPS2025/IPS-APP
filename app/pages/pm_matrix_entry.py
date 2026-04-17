"""PM Matrix Time Entry — foreman-style crew timesheet: jobs × employees × hours for one day in a week."""

from __future__ import annotations

import hashlib
import io
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st

from auth import current_profile, current_role

try:
    from branding import render_header
except ImportError:
    from app.branding import render_header  # type: ignore

try:
    from db_time_tracking import fetch_time_entries_for_week
except ImportError:
    from app.db_time_tracking import fetch_time_entries_for_week  # type: ignore

try:
    from services.job_service import job_row_select_label
    from services.pm_matrix_service import (
        apply_matrix_cell_saves,
        build_matrix_dataframe,
        column_totals_row,
        copy_previous_day_to_selected,
        delete_all_entries_for_work_date,
        employee_display_labels,
        fetch_active_employees,
        fetch_jobs_for_pm_matrix,
        fill_column_down_jobs,
        fill_row_across_employees,
        index_day_job_emp_hours,
        index_day_job_emp_notes,
        upsert_matrix_cell_full,
        weekly_hours_by_employee,
    )
    from services.time_grid_service import monday_of_week, week_dates
except ImportError:
    from app.services.job_service import job_row_select_label  # type: ignore
    from app.services.pm_matrix_service import (  # type: ignore
        apply_matrix_cell_saves,
        build_matrix_dataframe,
        column_totals_row,
        copy_previous_day_to_selected,
        delete_all_entries_for_work_date,
        employee_display_labels,
        fetch_active_employees,
        fetch_jobs_for_pm_matrix,
        fill_column_down_jobs,
        fill_row_across_employees,
        index_day_job_emp_hours,
        index_day_job_emp_notes,
        upsert_matrix_cell_full,
        weekly_hours_by_employee,
    )
    from app.services.time_grid_service import monday_of_week, week_dates  # type: ignore

PM_EDIT_ROLES = frozenset({"admin", "estimator", "project_manager"})
_OT_DEFAULT = 40.0
_INTENSITY_CAP_HOURS = 12.0  # scale color intensity up to this many hours per cell


def _inject_pm_matrix_css() -> None:
    st.markdown(
        """
        <style>
        .ips-pm-toolbar {
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(71, 85, 105, 0.5);
            border-radius: 10px;
            padding: 8px 10px 10px 10px;
            margin-bottom: 8px;
        }
        .ips-pm-filters {
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid rgba(71, 85, 105, 0.4);
            border-radius: 8px;
            padding: 8px 10px;
            margin-bottom: 8px;
        }
        .ips-pm-matrix-wrap {
            background: rgba(15, 23, 42, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 10px;
            padding: 8px 10px 10px 10px;
            margin-bottom: 8px;
        }
        .ips-pm-matrix-wrap div[data-testid="stDataEditor"] {
            font-size: 12px;
        }
        .ips-pm-matrix-wrap [data-testid="stDataEditor"] thead th,
        .ips-pm-matrix-wrap [data-testid="stDataEditor"] [role="columnheader"] {
            background: rgba(30, 58, 138, 0.92) !important;
            color: #f8fafc !important;
            font-weight: 700 !important;
            border-bottom: 2px solid rgba(96, 165, 250, 0.65) !important;
        }
        .ips-pm-heatmap-wrap {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid rgba(71, 85, 105, 0.35);
            border-radius: 8px;
            padding: 8px 10px;
            margin: 8px 0 10px 0;
        }
        /* Scroll region: sticky header + first column + row hover */
        .ips-pm-heatmap-scroll {
            position: relative;
            border-radius: 8px;
            overflow: hidden;
        }
        .ips-pm-heatmap-scroll div[data-testid="stDataFrame"] {
            max-height: min(520px, 70vh);
            overflow: auto !important;
            border-radius: 6px;
        }
        .ips-pm-heatmap-scroll div[data-testid="stDataFrame"] table {
            border-collapse: separate;
            border-spacing: 0;
        }
        .ips-pm-heatmap-scroll div[data-testid="stDataFrame"] thead tr th {
            position: sticky !important;
            top: 0 !important;
            z-index: 4 !important;
            background: rgba(30, 58, 138, 0.98) !important;
            color: #f1f5f9 !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 0 rgba(96, 165, 250, 0.45);
        }
        .ips-pm-heatmap-scroll div[data-testid="stDataFrame"] thead tr th:first-child {
            left: 0 !important;
            z-index: 6 !important;
            box-shadow: 2px 2px 0 rgba(96, 165, 250, 0.35);
        }
        .ips-pm-heatmap-scroll div[data-testid="stDataFrame"] tbody tr td:first-child,
        .ips-pm-heatmap-scroll div[data-testid="stDataFrame"] thead tr th:first-child {
            position: sticky !important;
            left: 0 !important;
            z-index: 3 !important;
            background: rgba(30, 41, 59, 0.98) !important;
            color: #e2e8f0 !important;
            font-weight: 600 !important;
            box-shadow: 4px 0 12px rgba(0,0,0,0.35);
        }
        .ips-pm-heatmap-scroll div[data-testid="stDataFrame"] tbody tr:hover td {
            filter: brightness(1.12);
            box-shadow: inset 0 0 0 999px rgba(59, 130, 246, 0.14) !important;
        }
        .ips-pm-heatmap-scroll div[data-testid="stDataFrame"] tbody tr:hover td:first-child {
            background: rgba(51, 65, 85, 0.98) !important;
        }
        .ips-pm-ot {
            color: #fecaca !important;
            font-weight: 800 !important;
            font-size: 13px;
            background: rgba(127, 29, 29, 0.42);
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid rgba(248, 113, 113, 0.45);
            display: inline-block;
        }
        .ips-pm-ot-sub {
            color: #fca5a5;
            font-size: 11px;
            font-weight: 600;
            opacity: 0.95;
        }
        .ips-pm-totals-footer {
            background: rgba(30, 41, 59, 0.98);
            border: 2px solid rgba(96, 165, 250, 0.35);
            border-radius: 8px;
            padding: 10px 12px;
            margin-top: 8px;
        }
        .ips-pm-totals {
            color: #e2e8f0;
            font-size: 13px;
            font-weight: 700;
        }
        .ips-pm-grand {
            color: #f8fafc !important;
            font-size: 14px;
            font-weight: 800;
            background: rgba(30, 64, 175, 0.55);
            padding: 6px 12px;
            border-radius: 6px;
            display: inline-block;
            border: 1px solid rgba(147, 197, 253, 0.45);
        }
        .ips-pm-day-tabs label {
            font-weight: 600 !important;
        }
        div[data-testid="stDataEditor"] {
            font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _style_matrix_preview(df: pd.DataFrame, emp_labels: list[str]) -> Any:
    """Green intensity by hours; row totals in blue tint scale."""
    sub = [c for c in emp_labels if c in df.columns]
    cap = _INTENSITY_CAP_HOURS
    if sub:
        series_list = [pd.to_numeric(df[c], errors="coerce").fillna(0) for c in sub]
        if series_list:
            mx = float(pd.concat(series_list, axis=0).max())
            cap = max(_INTENSITY_CAP_HOURS, mx, 1.0)

    def cell_style(v):
        try:
            x = float(v)
            if x <= 0:
                return "background-color: rgba(15, 23, 42, 0.62); color: #64748b"
            t = min(1.0, x / cap)
            # Emerald intensity (darker → brighter with more hours)
            g = int(100 + 115 * t)
            b = int(50 + 40 * (1 - t))
            a = 0.38 + 0.48 * t
            return (
                f"background-color: rgba(6, {g}, {b}, {a:.2f}); color: #f8fafc; font-weight: 600"
            )
        except (TypeError, ValueError):
            return ""

    def row_sum_style(v):
        try:
            x = float(v)
            if x <= 0:
                return "background-color: rgba(15, 23, 42, 0.55); color: #64748b"
            t = min(1.0, x / max(cap, 8.0))
            a = 0.22 + 0.38 * t
            return f"background-color: rgba(37, 99, 235, {a:.2f}); color: #e0e7ff; font-weight: 700"
        except (TypeError, ValueError):
            return ""

    sty = df.style
    if sub:
        sty = sty.map(cell_style, subset=sub)
    if "Row Σ" in df.columns:
        sty = sty.map(row_sum_style, subset=["Row Σ"])
    num_cols = [c for c in df.columns if c != "Job"]
    if num_cols:
        sty = sty.format({c: "{:.2f}" for c in num_cols}, na_rep="")
    return sty


def _weekly_export_df(
    week_entries: list[dict],
    job_id_to_label: dict[str, str],
    emp_id_to_label: dict[str, str],
    allowed_eids: set[str],
    allowed_jids: set[str],
) -> pd.DataFrame:
    """Line-level rows for the selected week (filtered to visible matrix jobs/employees)."""
    rows = []
    for e in week_entries:
        jid = str(e.get("job_id") or "")
        eid = str(e.get("employee_id") or "")
        if allowed_eids and eid not in allowed_eids:
            continue
        if allowed_jids and jid not in allowed_jids:
            continue
        rows.append(
            {
                "work_date": str(e.get("work_date") or "")[:10],
                "job": job_id_to_label.get(jid, jid),
                "employee": emp_id_to_label.get(eid, eid),
                "hours": float(e.get("hours", 0) or 0),
                "notes": str(e.get("notes") or ""),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["work_date", "job", "employee"]).reset_index(drop=True)


def _hours_matrix_changed(before: pd.DataFrame, after: pd.DataFrame, emp_labels: list[str]) -> bool:
    for lab in emp_labels:
        if lab not in before.columns or lab not in after.columns:
            continue
        for ri in range(len(before)):
            try:
                a = float(before.iloc[ri][lab] or 0)
                b = float(after.iloc[ri][lab] or 0)
                if abs(a - b) > 1e-5:
                    return True
            except Exception:
                return True
    return False


def _line_items_df(
    day_entries: list[dict],
    job_id_to_label: dict[str, str],
    emp_id_to_label: dict[str, str],
) -> pd.DataFrame:
    rows = []
    for e in day_entries:
        jid = str(e.get("job_id") or "")
        eid = str(e.get("employee_id") or "")
        rows.append(
            {
                "Job": job_id_to_label.get(jid, jid),
                "Employee": emp_id_to_label.get(eid, eid),
                "Hours": float(e.get("hours", 0) or 0),
                "Notes": str(e.get("notes") or ""),
                "work_date": str(e.get("work_date") or "")[:10],
            }
        )
    return pd.DataFrame(rows)


def _emp_label_safe(e: dict) -> str:
    name = str(e.get("name") or "").strip() or "(no name)"
    eid = str(e.get("id") or "")
    tail = eid[:8] if len(eid) >= 8 else eid
    return f"{name} [{tail}]"


def _day_entries_from_week(week_entries: list[dict], selected_day: date) -> list[dict]:
    wd = selected_day.isoformat()[:10]
    return [e for e in week_entries if str(e.get("work_date") or "")[:10] == wd]


def _matrix_editor_key(
    week_start: date,
    selected_day: date,
    employees: list[dict],
    job_rows: list[tuple[str, str]],
) -> str:
    raw = "|".join(str(e.get("id")) for e in employees) + "||" + "|".join(j for j, _ in job_rows)
    sig = hashlib.md5(raw.encode()).hexdigest()[:10]
    return f"pm_mx_{week_start.isoformat()}_{selected_day.isoformat()}_{sig}"


def render_pm_matrix(*, can_edit: bool) -> None:
    _inject_pm_matrix_css()
    st.caption(
        "Crew timesheet: **jobs** as rows, **employees** as columns. "
        "Edits save automatically; **Save day** or **Cell notes** as needed. "
        "Blank or **0** removes the row. Heat map: **green intensity = more hours**; footer **red = week OT**."
    )

    today = date.today()
    st.session_state.setdefault("pm_week_start", monday_of_week(today))
    week_start: date = st.session_state["pm_week_start"]
    if week_start.weekday() != 0:
        week_start = monday_of_week(week_start)
        st.session_state["pm_week_start"] = week_start
    days = week_dates(week_start)
    week_end = days[-1]

    st.markdown('<div class="ips-pm-toolbar">', unsafe_allow_html=True)
    r1a, r1b, r1c, r1d, r1e = st.columns([1, 1, 1, 2.2, 1.2])
    if r1a.button("◀ Previous week", key="pm_prev_wk"):
        st.session_state["pm_week_start"] = week_start - timedelta(days=7)
        st.rerun()
    if r1b.button("Current week", key="pm_this_wk"):
        st.session_state["pm_week_start"] = monday_of_week(today)
        st.rerun()
    if r1c.button("Next week ▶", key="pm_next_wk"):
        st.session_state["pm_week_start"] = week_start + timedelta(days=7)
        st.rerun()
    r1d.markdown(
        f'<p class="ips-pm-totals" style="margin:0.55rem 0 0 0;font-size:1.05rem;">'
        f"<strong>Selected week</strong> &nbsp;·&nbsp; "
        f"{week_start.isoformat()} → {week_end.isoformat()}"
        f"</p>",
        unsafe_allow_html=True,
    )
    picked = r1e.date_input(
        "Week containing",
        value=week_start,
        label_visibility="collapsed",
        help="Pick any day; the Monday of that week is used.",
        key="pm_week_pick",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if isinstance(picked, date):
        new_mon = monday_of_week(picked)
        if new_mon != week_start:
            st.session_state["pm_week_start"] = new_mon
            st.rerun()

    employees_all = fetch_active_employees()
    jobs_all = fetch_jobs_for_pm_matrix()
    if not employees_all:
        st.warning("No active employees. Add staff under **Users** → Employees.")
        return
    if not jobs_all:
        st.warning("No jobs in **Job Database**.")
        return

    job_rows_all: list[tuple[str, str]] = []
    job_id_to_label: dict[str, str] = {}
    for j in jobs_all:
        jid = str(j.get("id") or "").strip()
        if not jid:
            continue
        lab = job_row_select_label(j)
        job_rows_all.append((jid, lab))
        job_id_to_label[jid] = lab

    emp_labels_all = employee_display_labels(employees_all)
    emp_id_to_label = {str(e.get("id")): employee_display_labels([e])[0] for e in employees_all}

    st.session_state.setdefault("pm_ot_threshold", _OT_DEFAULT)

    st.markdown('<div class="ips-pm-filters">', unsafe_allow_html=True)
    st.markdown("**Filters** — narrow the grid for faster entry (defaults: everyone / all jobs shown).")
    f1, f2, f3 = st.columns([2, 2, 1])
    with f1:
        sel_emp_labels = st.multiselect(
            "Employees in matrix",
            options=emp_labels_all,
            default=emp_labels_all,
            key="pm_filter_employees",
            help="Show a subset of the crew. Empty selection shows all.",
        )
    with f2:
        job_label_options = [lab for _, lab in job_rows_all]
        sel_job_labels = st.multiselect(
            "Jobs in matrix",
            options=job_label_options,
            default=job_label_options,
            key="pm_filter_jobs",
            help="Show a subset of jobs. Empty selection shows all.",
        )
    with f3:
        ot_threshold = st.number_input(
            "OT if week Σ > (h)",
            min_value=0.0,
            max_value=120.0,
            value=float(st.session_state.get("pm_ot_threshold", _OT_DEFAULT)),
            step=1.0,
            key="pm_ot_threshold_input",
            help="Footer highlights an employee when **Monday–Sunday total** for that person exceeds this.",
        )
        st.session_state["pm_ot_threshold"] = ot_threshold
    st.markdown("</div>", unsafe_allow_html=True)

    if not sel_emp_labels:
        sel_emp_labels = emp_labels_all
    if not sel_job_labels:
        sel_job_labels = job_label_options

    employees = [e for e in employees_all if employee_display_labels([e])[0] in set(sel_emp_labels)]
    job_rows = [(jid, lab) for jid, lab in job_rows_all if lab in set(sel_job_labels)]

    if not employees:
        st.warning("No employees match the filter.")
        return
    if not job_rows:
        st.warning("No jobs match the filter.")
        return

    emp_labels = employee_display_labels(employees)

    st.markdown('<div class="ips-pm-day-tabs">', unsafe_allow_html=True)
    day_tab_labels = [
        f"{d.strftime('%a')} {d.strftime('%m/%d')}"  # Mon … Sun
        for d in days
    ]
    day_ix = st.radio(
        "Day",
        options=list(range(7)),
        format_func=lambda i: day_tab_labels[i],
        horizontal=True,
        key="pm_day_tab",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    selected_day = days[int(day_ix)]
    st.markdown(f"**Editing:** {selected_day.strftime('%A, %B %d, %Y')}")

    try:
        week_entries = fetch_time_entries_for_week(week_start)
    except Exception as exc:
        st.error(f"Could not load time_entries for the week: {exc}")
        return

    day_entries = _day_entries_from_week(week_entries, selected_day)
    hours_index = index_day_job_emp_hours(day_entries, selected_day)
    notes_index = index_day_job_emp_notes(day_entries, selected_day)
    df_db = build_matrix_dataframe(
        job_rows=job_rows,
        employees=employees,
        hours_index=hours_index,
    )

    editor_key = _matrix_editor_key(week_start, selected_day, employees, job_rows)

    num_cols_cfg = {}
    for lab in emp_labels:
        num_cols_cfg[lab] = st.column_config.NumberColumn(
            lab, min_value=0.0, max_value=999.99, step=0.25, format="%.2f"
        )

    st.markdown('<div class="ips-pm-matrix-wrap">', unsafe_allow_html=True)
    _dis = True if not can_edit else ["Job", "Row Σ"]
    edited = st.data_editor(
        df_db,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key=editor_key,
        disabled=_dis,
        column_config={
            "Job": st.column_config.TextColumn("Job / scope", width="large"),
            "Row Σ": st.column_config.NumberColumn("Row Σ", format="%.2f"),
            **num_cols_cfg,
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)

    uid = current_profile().get("id")
    ts_iso = datetime.now(timezone.utc).isoformat()

    save_bar = st.columns([1, 1.15, 2])
    with save_bar[0]:
        save_clicked = st.button(
            "Save day",
            type="primary",
            key="pm_save_day_btn",
            use_container_width=True,
            disabled=not can_edit,
            help="Writes all cells for this day. Edits also save automatically when you leave a cell.",
        )
    with save_bar[1]:
        with st.popover("Cell notes"):
            st.caption("Optional detail for a single cell (hours are edited in the grid above).")
            pj = st.selectbox("Job", [lbl for _, lbl in job_rows], key="pm_pop_job")
            pe = st.selectbox("Employee", emp_labels, key="pm_pop_emp")
            jid_p = next(j for j, lb in job_rows if lb == pj)
            eid_p = ""
            for e in employees:
                if _emp_label_safe(e) == pe:
                    eid_p = str(e.get("id"))
                    break
            cur_note = notes_index.get((jid_p, eid_p), "") if eid_p else ""
            try:
                ri = next(i for i, (_, lb) in enumerate(job_rows) if lb == pj)
                cur_h = float(edited.iloc[ri][pe] or 0)
            except Exception:
                cur_h = float(hours_index.get((jid_p, eid_p), 0.0))
            st.markdown(f"**Hours this day:** {cur_h:.2f} (change in the matrix)")
            nk = "pm_popn_" + hashlib.md5(f"{jid_p}|{eid_p}".encode()).hexdigest()[:16]
            nt = st.text_area("Notes", value=cur_note, height=80, key=nk)
            if can_edit and st.button("Save notes", key="pm_pop_save"):
                try:
                    upsert_matrix_cell_full(
                        employee_id=eid_p,
                        job_id=jid_p,
                        work_date=selected_day,
                        hours=cur_h,
                        notes=nt,
                        created_by=uid,
                        updated_at_iso=ts_iso,
                    )
                    st.success("Notes saved.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with save_bar[2]:
        st.caption("Auto-saves when values change, or use **Save day**. **Cell notes** opens a quick editor.")

    def _do_save() -> tuple[int, bool]:
        try:
            n = apply_matrix_cell_saves(
                before=df_db,
                after=edited,
                job_rows=job_rows,
                employees=employees,
                work_date=selected_day,
                created_by=uid,
                updated_at_iso=ts_iso,
                notes_index=notes_index,
            )
            return n, True
        except Exception as exc:
            st.error(f"Save failed: {exc}")
            return 0, False

    if can_edit and save_clicked:
        n, ok = _do_save()
        if ok:
            if n > 0:
                st.success(f"Saved {n} change(s).")
                st.rerun()
            else:
                st.info("No changes to save.")

    if can_edit and _hours_matrix_changed(df_db, edited, emp_labels) and not save_clicked:
        n, ok = _do_save()
        if ok and n > 0:
            st.rerun()

    st.markdown("##### Hours map (read-only)")
    st.markdown(
        '<div class="ips-pm-heatmap-scroll"><div class="ips-pm-heatmap-wrap">',
        unsafe_allow_html=True,
    )
    try:
        st.dataframe(
            _style_matrix_preview(edited, emp_labels),
            use_container_width=True,
            height=min(520, 56 + len(edited) * 28),
        )
    except Exception:
        st.dataframe(edited, use_container_width=True, height=400)
    st.markdown("</div></div>", unsafe_allow_html=True)

    tot = column_totals_row(edited, emp_labels)

    st.markdown('<div class="ips-pm-totals-footer">', unsafe_allow_html=True)
    st.markdown("**Totals — this day** (footer shows **week Σ** Mon–Sun; OT style when week total exceeds threshold above)")
    tc0, *trest, tgl = st.columns([1.4] + [1.0] * len(emp_labels) + [1.1])
    with tc0:
        st.markdown('<span class="ips-pm-totals">Employee Σ</span>', unsafe_allow_html=True)
    for i, lab in enumerate(emp_labels):
        eid = str(employees[i].get("id"))
        wh = weekly_hours_by_employee(week_entries, eid, week_start, week_end)
        day_h = tot.get(lab, 0)
        is_ot = wh > float(ot_threshold)
        with trest[i]:
            if is_ot:
                st.markdown(
                    f'<span class="ips-pm-ot">{day_h:.2f} h</span><br/>'
                    f'<span class="ips-pm-ot-sub">Week Σ {wh:.1f} h (OT)</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span class="ips-pm-totals">{day_h:.2f} h</span><br/>'
                    f'<span style="color:#94a3b8;font-size:11px;font-weight:600;">Week Σ {wh:.1f} h</span>',
                    unsafe_allow_html=True,
                )
    with tgl:
        st.markdown(
            f'<span class="ips-pm-grand">{tot.get("grand", 0):.2f} h</span>',
            unsafe_allow_html=True,
        )
        st.caption("Day grand")
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "**Row Σ** = sum across employees for that job. **Hours map** uses darker → brighter green by hours; **Row Σ** uses blue intensity."
    )

    with st.expander("Quick-fill & notes", expanded=False):
        q1, q2 = st.columns(2)
        with q1:
            st.markdown("**Fill a job row across all employees**")
            row_job = st.selectbox("Job row", [lbl for _, lbl in job_rows], key="pm_qf_row_job")
            row_h = st.number_input("Hours", 0.0, 24.0, 8.0, 0.25, key="pm_qf_row_h")
            if can_edit and st.button("Apply row → all employees", key="pm_qf_row_btn"):
                jid = next(j for j, lb in job_rows if lb == row_job)
                try:
                    fill_row_across_employees(
                        job_id=jid,
                        work_date=selected_day,
                        hours=row_h,
                        employees=employees,
                        notes_index=notes_index,
                        created_by=uid,
                        updated_at_iso=ts_iso,
                    )
                    st.success("Row filled.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        with q2:
            st.markdown("**Fill an employee column down all jobs**")
            col_emp = st.selectbox("Employee column", emp_labels, key="pm_qf_col_emp")
            col_h = st.number_input("Hours ", 0.0, 24.0, 8.0, 0.25, key="pm_qf_col_h")
            if can_edit and st.button("Apply column → all jobs", key="pm_qf_col_btn"):
                eid = None
                for e in employees:
                    if _emp_label_safe(e) == col_emp:
                        eid = str(e.get("id"))
                        break
                if not eid:
                    st.error("Employee not found.")
                    st.stop()
                try:
                    fill_column_down_jobs(
                        employee_id=eid,
                        work_date=selected_day,
                        hours=col_h,
                        job_rows=job_rows,
                        notes_index=notes_index,
                        created_by=uid,
                        updated_at_iso=ts_iso,
                    )
                    st.success("Column filled.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        n_j = st.selectbox("Job", [lbl for _, lbl in job_rows], key="pm_note_job")
        n_e = st.selectbox("Employee", emp_labels, key="pm_note_emp")
        jid_n = next(j for j, lb in job_rows if lb == n_j)
        eid_n = ""
        for e in employees:
            if _emp_label_safe(e) == n_e:
                eid_n = str(e.get("id"))
                break
        cur_note = notes_index.get((jid_n, eid_n), "") if eid_n else ""
        try:
            ri = next(i for i, (_, lb) in enumerate(job_rows) if lb == n_j)
            cur_h = float(edited.iloc[ri][n_e] or 0)
        except Exception:
            cur_h = float(hours_index.get((jid_n, eid_n), 0.0))
        n_h = st.number_input("Hours", 0.0, 24.0, cur_h, 0.25, key="pm_note_h")
        n_t = st.text_area("Notes", value=cur_note, height=72, key="pm_note_t")
        if can_edit and st.button("Save hours + notes", key="pm_note_save"):
            try:
                upsert_matrix_cell_full(
                    employee_id=eid_n,
                    job_id=jid_n,
                    work_date=selected_day,
                    hours=n_h,
                    notes=n_t,
                    created_by=uid,
                    updated_at_iso=ts_iso,
                )
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    allowed_eids = {str(e.get("id")) for e in employees}
    allowed_jids = {j for j, _ in job_rows}
    week_export_df = _weekly_export_df(
        week_entries,
        job_id_to_label,
        emp_id_to_label,
        allowed_eids,
        allowed_jids,
    )

    st.markdown("**Export — selected day**")
    ex1, ex2, ex3 = st.columns([1, 1, 2])
    line_df = _line_items_df(day_entries, job_id_to_label, emp_id_to_label)
    csv_matrix = edited.to_csv(index=False).encode("utf-8")
    csv_lines = line_df.to_csv(index=False).encode("utf-8") if not line_df.empty else b"Job,Employee,Hours,Notes,work_date\n"
    with ex1:
        st.download_button(
            "Matrix CSV",
            data=csv_matrix,
            file_name=f"pm_matrix_{selected_day.isoformat()}.csv",
            mime="text/csv",
            key="pm_dl_csv_mx",
        )
    with ex2:
        st.download_button(
            "Line items CSV",
            data=csv_lines,
            file_name=f"pm_line_items_{selected_day.isoformat()}.csv",
            mime="text/csv",
            key="pm_dl_csv_li",
        )
    with ex3:
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as xlw:
                edited.to_excel(xlw, sheet_name="Hours matrix", index=False)
                if line_df.empty:
                    pd.DataFrame(columns=["Job", "Employee", "Hours", "Notes", "work_date"]).to_excel(
                        xlw, sheet_name="Line items", index=False
                    )
                else:
                    line_df.to_excel(xlw, sheet_name="Line items", index=False)
            st.download_button(
                "Excel (matrix + line items)",
                data=buf.getvalue(),
                file_name=f"pm_time_{selected_day.isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="pm_dl_xlsx",
            )
        except Exception as exc:
            st.caption(f"Excel export needs openpyxl: {exc}")

    st.markdown("**Export — full selected week (Mon–Sun)** — uses the same job/employee filters")
    wx1, wx2 = st.columns(2)
    week_csv = (
        week_export_df.to_csv(index=False).encode("utf-8")
        if not week_export_df.empty
        else b"work_date,job,employee,hours,notes\n"
    )
    with wx1:
        st.download_button(
            "Week CSV",
            data=week_csv,
            file_name=f"pm_week_{week_start.isoformat()}_{week_end.isoformat()}.csv",
            mime="text/csv",
            key="pm_dl_week_csv",
        )
    with wx2:
        try:
            wbuf = io.BytesIO()
            with pd.ExcelWriter(wbuf, engine="openpyxl") as xlw:
                (
                    week_export_df
                    if not week_export_df.empty
                    else pd.DataFrame(columns=["work_date", "job", "employee", "hours", "notes"])
                ).to_excel(xlw, sheet_name="Week entries", index=False)
            st.download_button(
                "Week Excel",
                data=wbuf.getvalue(),
                file_name=f"pm_week_{week_start.isoformat()}_{week_end.isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="pm_dl_week_xlsx",
            )
        except Exception as exc:
            st.caption(f"Week Excel needs openpyxl: {exc}")

    a1, a2, a3 = st.columns([1, 1, 2], gap="small")
    with a1:
        if can_edit and st.button("Copy previous day → this day", key="pm_copy_prev", use_container_width=True):
            try:
                n = copy_previous_day_to_selected(
                    dest_date=selected_day,
                    created_by=uid,
                    updated_at_iso=ts_iso,
                )
                st.success(f"Copied {n} row(s) from previous day.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with a2:
        clear_open = st.session_state.get("pm_clear_confirm_open") == str(selected_day)
        if can_edit and not clear_open:
            if st.button("Clear selected day…", key="pm_clear_btn", use_container_width=True):
                st.session_state["pm_clear_confirm_open"] = str(selected_day)
                st.rerun()
    with a3:
        if clear_open and can_edit:
            st.warning(f"This removes **all** time entries on **{selected_day.isoformat()}**.")
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button(
                    "Confirm clear",
                    type="primary",
                    use_container_width=True,
                    key="pm_clear_yes",
                ):
                    try:
                        n = delete_all_entries_for_work_date(selected_day)
                        st.session_state.pop("pm_clear_confirm_open", None)
                        st.success(f"Removed {n} entr(y/ies).")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            with c2:
                if st.button("Cancel", use_container_width=True, key="pm_clear_no"):
                    st.session_state.pop("pm_clear_confirm_open", None)
                    st.rerun()

    if not can_edit:
        st.info("View-only. Sign in as admin, estimator, or project manager to edit.")


def render() -> None:
    render_header(
        "PM Matrix Time Entry",
        subtitle="Foreman crew timesheet — all employees × jobs, one calendar day at a time",
    )
    can_edit = current_role() in PM_EDIT_ROLES
    render_pm_matrix(can_edit=can_edit)

