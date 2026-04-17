"""PM matrix time entry: helpers for job × employee × day grids (public.time_entries)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

try:
    from db import fetch_table_admin
    from db_time_tracking import delete_time_entry_by_natural_key, fetch_jobs_for_matrix_rows
except ImportError:
    from app.db import fetch_table_admin  # type: ignore
    from app.db_time_tracking import (  # type: ignore
        delete_time_entry_by_natural_key,
        fetch_jobs_for_matrix_rows,
    )

try:
    from services.time_grid_service import (
        delete_time_entries_by_ids,
        fetch_time_entries_for_date,
        upsert_time_entry,
    )
except ImportError:
    from app.services.time_grid_service import (  # type: ignore
        delete_time_entries_by_ids,
        fetch_time_entries_for_date,
        upsert_time_entry,
    )


def fetch_weekly_entries(week_start: date, week_end: date) -> list[dict[str, Any]]:
    try:
        from services.time_grid_service import fetch_time_entries_between
    except ImportError:
        from app.services.time_grid_service import fetch_time_entries_between  # type: ignore
    return fetch_time_entries_between(week_start, week_end)


def fetch_active_employees() -> list[dict[str, Any]]:
    try:
        from db_time_tracking import fetch_active_employees as _fetch_active
    except ImportError:
        from app.db_time_tracking import fetch_active_employees as _fetch_active  # type: ignore

    return _fetch_active()


def fetch_jobs_ordered() -> list[dict[str, Any]]:
    try:
        from services.job_service import sort_jobs_by_number_then_name
    except ImportError:
        from app.services.job_service import sort_jobs_by_number_then_name  # type: ignore
    try:
        jobs = fetch_table_admin("jobs", limit=5000, order_by="job_number")
    except Exception:
        return []
    return sort_jobs_by_number_then_name(jobs)


def fetch_jobs_for_pm_matrix() -> list[dict[str, Any]]:
    """Active / open jobs for matrix rows; see :func:`db_time_tracking.fetch_jobs_for_matrix_rows`."""
    return fetch_jobs_for_matrix_rows()


def index_day_job_emp_notes(entries: list[dict], work_date: date) -> dict[tuple[str, str], str]:
    """(job_id, employee_id) -> notes text for rows matching work_date."""
    wd = work_date.isoformat()[:10]
    out: dict[tuple[str, str], str] = {}
    for e in entries:
        if str(e.get("work_date") or "")[:10] != wd:
            continue
        jid = str(e.get("job_id") or "")
        eid = str(e.get("employee_id") or "")
        if not jid or not eid:
            continue
        out[(jid, eid)] = str(e.get("notes") or "")
    return out


def index_day_job_emp_hours(entries: list[dict], work_date: date) -> dict[tuple[str, str], float]:
    """(job_id, employee_id) -> hours for rows matching work_date."""
    wd = work_date.isoformat()[:10]
    out: dict[tuple[str, str], float] = {}
    for e in entries:
        if str(e.get("work_date") or "")[:10] != wd:
            continue
        jid = str(e.get("job_id") or "")
        eid = str(e.get("employee_id") or "")
        if not jid or not eid:
            continue
        out[(jid, eid)] = float(e.get("hours", 0) or 0)
    return out


def build_matrix_dataframe(
    *,
    job_rows: list[tuple[str, str]],
    employees: list[dict[str, Any]],
    hours_index: dict[tuple[str, str], float],
) -> pd.DataFrame:
    """Columns: Job, one per employee label, Row Σ."""
    cols: dict[str, list] = {"Job": [lbl for _, lbl in job_rows]}
    for e in employees:
        eid = str(e.get("id"))
        lab = _emp_label(e)
        cols[lab] = [float(hours_index.get((jid, eid), 0.0)) for jid, _ in job_rows]
    df = pd.DataFrame(cols)
    emp_cols = [c for c in df.columns if c != "Job"]
    df["Row Σ"] = df[emp_cols].sum(axis=1)
    return df


def employee_display_labels(employees: list[dict]) -> list[str]:
    """Column titles for matrix (must match :func:`build_matrix_dataframe`)."""
    return [_emp_label(e) for e in employees]


def _emp_label(e: dict) -> str:
    name = str(e.get("name") or "").strip() or "(no name)"
    eid = str(e.get("id") or "")
    tail = eid[:8] if len(eid) >= 8 else eid
    return f"{name} [{tail}]"


def apply_matrix_cell_saves(
    *,
    before: pd.DataFrame,
    after: pd.DataFrame,
    job_rows: list[tuple[str, str]],
    employees: list[dict[str, Any]],
    work_date: date,
    created_by,
    updated_at_iso: str,
    notes_index: dict[tuple[str, str], str] | None = None,
) -> int:
    """
    Compare hour columns before/after; upsert non-zero, delete zero/blank.
    Returns number of cells written (upsert + delete).
    """
    after = after.reindex(columns=list(before.columns))
    emp_labels = [_emp_label(e) for e in employees]
    eid_by_label = {lab: str(e.get("id")) for lab, e in zip(emp_labels, employees)}
    job_id_by_row_idx = {i: job_rows[i][0] for i in range(len(job_rows))}

    n = 0
    for ri in range(len(job_rows)):
        jid = job_id_by_row_idx[ri]
        for lab in emp_labels:
            if lab not in before.columns or lab not in after.columns:
                continue
            try:
                v0 = float(before.iloc[ri][lab] or 0)
            except (TypeError, ValueError):
                v0 = 0.0
            try:
                v1 = float(after.iloc[ri][lab] or 0)
            except (TypeError, ValueError):
                v1 = 0.0
            if abs(v0 - v1) < 1e-6:
                continue
            eid = eid_by_label.get(lab)
            if not eid:
                continue
            if v1 <= 0:
                _delete_cell(eid, jid, work_date)
                n += 1
            else:
                note = ""
                if notes_index is not None:
                    note = notes_index.get((jid, eid), "") or ""
                upsert_time_entry(
                    employee_id=eid,
                    job_id=jid,
                    work_date=work_date,
                    hours=min(v1, 999.99),
                    notes=note,
                    created_by=created_by,
                    updated_at_iso=updated_at_iso,
                )
                n += 1
    return n


def _delete_cell(employee_id: str, job_id: str, work_date: date) -> None:
    delete_time_entry_by_natural_key(
        employee_id=employee_id,
        job_id=job_id,
        work_date=work_date,
    )


def copy_previous_day_to_selected(
    *,
    dest_date: date,
    created_by,
    updated_at_iso: str,
) -> int:
    """Copy all time_entries from the previous calendar day onto dest_date (replaces dest)."""
    src_date = dest_date - timedelta(days=1)
    return copy_day_to_day(
        from_date=src_date,
        to_date=dest_date,
        created_by=created_by,
        updated_at_iso=updated_at_iso,
    )


def copy_day_to_day(
    *,
    from_date: date,
    to_date: date,
    created_by,
    updated_at_iso: str,
) -> int:
    src = fetch_time_entries_for_date(from_date)
    delete_all_entries_for_work_date(to_date)
    for row in src:
        upsert_time_entry(
            employee_id=str(row.get("employee_id")),
            job_id=str(row.get("job_id")),
            work_date=to_date,
            hours=float(row.get("hours", 0) or 0),
            notes=str(row.get("notes") or ""),
            created_by=created_by,
            updated_at_iso=updated_at_iso,
        )
    return len(src)


def fill_row_across_employees(
    *,
    job_id: str,
    work_date: date,
    hours: float,
    employees: list[dict[str, Any]],
    notes_index: dict[tuple[str, str], str] | None,
    created_by,
    updated_at_iso: str,
) -> int:
    """Set the same hours for every active employee on this job × day (preserves existing notes per cell)."""
    n = 0
    h = float(hours or 0)
    for e in employees:
        eid = str(e.get("id") or "")
        if not eid:
            continue
        note = ""
        if notes_index is not None:
            note = notes_index.get((job_id, eid), "") or ""
        if h <= 0:
            _delete_cell(eid, job_id, work_date)
        else:
            upsert_time_entry(
                employee_id=eid,
                job_id=job_id,
                work_date=work_date,
                hours=min(h, 999.99),
                notes=note,
                created_by=created_by,
                updated_at_iso=updated_at_iso,
            )
        n += 1
    return n


def fill_column_down_jobs(
    *,
    employee_id: str,
    work_date: date,
    hours: float,
    job_rows: list[tuple[str, str]],
    notes_index: dict[tuple[str, str], str] | None,
    created_by,
    updated_at_iso: str,
) -> int:
    """Set the same hours for every job row for one employee × day."""
    n = 0
    h = float(hours or 0)
    for jid, _ in job_rows:
        note = ""
        if notes_index is not None:
            note = notes_index.get((jid, employee_id), "") or ""
        if h <= 0:
            _delete_cell(employee_id, jid, work_date)
        else:
            upsert_time_entry(
                employee_id=employee_id,
                job_id=jid,
                work_date=work_date,
                hours=min(h, 999.99),
                notes=note,
                created_by=created_by,
                updated_at_iso=updated_at_iso,
            )
        n += 1
    return n


def upsert_matrix_cell_full(
    *,
    employee_id: str,
    job_id: str,
    work_date: date,
    hours: float,
    notes: str,
    created_by,
    updated_at_iso: str,
) -> None:
    """Set hours + notes for one cell; zero hours deletes the row."""
    h = float(hours or 0)
    if h <= 0:
        _delete_cell(employee_id, job_id, work_date)
    else:
        upsert_time_entry(
            employee_id=employee_id,
            job_id=job_id,
            work_date=work_date,
            hours=min(h, 999.99),
            notes=(notes or "").strip(),
            created_by=created_by,
            updated_at_iso=updated_at_iso,
        )


def weekly_hours_by_employee(week_entries: list[dict], employee_id: str, week_start: date, week_end: date) -> float:
    ws = week_start.isoformat()[:10]
    we = week_end.isoformat()[:10]
    eid = str(employee_id)
    total = 0.0
    for e in week_entries:
        if str(e.get("employee_id")) != eid:
            continue
        d = str(e.get("work_date") or "")[:10]
        if ws <= d <= we:
            total += float(e.get("hours", 0) or 0)
    return total


def delete_all_entries_for_work_date(work_date: date) -> int:
    rows = fetch_time_entries_for_date(work_date)
    ids = [str(r.get("id")) for r in rows if r.get("id")]
    delete_time_entries_by_ids(ids)
    return len(ids)


def column_totals_row(df: pd.DataFrame, emp_labels: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for lab in emp_labels:
        if lab in df.columns:
            out[lab] = float(pd.to_numeric(df[lab], errors="coerce").fillna(0).sum())
    out["grand"] = float(sum(out.values()))
    return out
