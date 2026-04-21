"""
Safe deletion helpers for estimates and jobs.

- **Estimates:** unlink ``jobs.estimate_id`` and best-effort child rows; never delete jobs.
- **Jobs:** block when costing rows exist (time, materials, equipment, PO expenses).
"""

from __future__ import annotations

from typing import Any

try:
    from db import (
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        update_rows_admin,
    )
except ImportError:
    from app.db import (
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        update_rows_admin,
    )

_COSTING_TABLES: tuple[str, ...] = (
    "time_entries",
    "job_materials",
    "job_equipment",
    "job_expenses",
)


def _match_rows(
    table: str,
    match: dict[str, Any],
    *,
    admin_read: bool,
    limit: int = 1,
) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    try:
        return list(fn(table, match, limit=limit) or [])
    except Exception:
        try:
            return list(fetch_by_match_admin(table, match, limit=limit) or [])
        except Exception:
            return []


def job_costing_block_reason(job_id: str, *, admin_read: bool = False) -> str | None:
    """
    Return a short reason if the job must not be deleted, else ``None``.

    Checks: ``time_entries``, ``job_materials``, ``job_equipment``, ``job_expenses``.
    """
    jid = str(job_id or "").strip()
    if not jid:
        return "Invalid job id."
    for table in _COSTING_TABLES:
        if _match_rows(table, {"job_id": jid}, admin_read=admin_read, limit=1):
            return "Cannot delete job with costing data"
    return None


def partition_jobs_by_costing_guard(
    job_ids: list[str],
    *,
    admin_read: bool = False,
) -> tuple[list[str], list[tuple[str, str]]]:
    """``(ids_ok_to_delete, [(id, reason), ...])`` for jobs that are blocked."""
    ok: list[str] = []
    blocked: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in job_ids:
        jid = str(raw or "").strip()
        if not jid or jid in seen:
            continue
        seen.add(jid)
        reason = job_costing_block_reason(jid, admin_read=admin_read)
        if reason:
            blocked.append((jid, reason))
        else:
            ok.append(jid)
    return ok, blocked


def unlink_jobs_from_estimate(estimate_id: str, *, admin_read: bool = False) -> None:
    """Clear ``jobs.estimate_id`` for rows pointing at this estimate (jobs are kept)."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    rows = _match_rows("jobs", {"estimate_id": eid}, admin_read=admin_read, limit=500)
    for r in rows:
        jid = r.get("id")
        if jid:
            try:
                update_rows_admin("jobs", {"estimate_id": None}, {"id": jid})
            except Exception:
                pass


def preclean_estimate_children(estimate_id: str) -> None:
    """Best-effort removal of dependent rows (ignore missing tables)."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    for table, col in (
        ("estimate_revisions", "estimate_id"),
        ("attachments", "estimate_id"),
    ):
        try:
            delete_rows_admin(table, {col: eid})
        except Exception:
            pass


def delete_estimate_unlink_first(estimate_id: str, *, admin_read: bool = False) -> None:
    """Unlink jobs, drop common child rows, then delete the estimate."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    unlink_jobs_from_estimate(eid, admin_read=admin_read)
    preclean_estimate_children(eid)
    delete_rows_admin("estimates", {"id": eid})


def clear_estimates_pointing_at_job(job_id: str, *, admin_read: bool = False) -> None:
    """Clear ``estimates.job_id`` when it references this job (estimate rows are kept)."""
    jid = str(job_id or "").strip()
    if not jid:
        return
    rows = _match_rows("estimates", {"job_id": jid}, admin_read=admin_read, limit=500)
    for r in rows or []:
        eid = r.get("id")
        if eid:
            try:
                update_rows_admin("estimates", {"job_id": None}, {"id": eid})
            except Exception:
                pass


def delete_job_row_if_no_costing(job_id: str, *, admin_read: bool = False) -> None:
    """Raise ``RuntimeError`` if costing data exists; otherwise unlink estimates and delete the job."""
    jid = str(job_id or "").strip()
    if not jid:
        raise RuntimeError("Invalid job id.")
    reason = job_costing_block_reason(jid, admin_read=admin_read)
    if reason:
        raise RuntimeError(reason)
    clear_estimates_pointing_at_job(jid, admin_read=admin_read)
    delete_rows_admin("jobs", {"id": jid})
