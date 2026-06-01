"""
Jobs table — columns the **Job Database** page uses on ``public.jobs``.

**Architecture:** jobs are the **costing / work** records (time entries, job costing, PO
expenses, materials usage key off ``jobs.id``). Estimates are **quotes / proposals** only;
``estimate_id`` is optional and links a converted or manually attached quote.

There is **no** ``description`` column; long text is ``notes``. The ``job_number`` column is
added by ``sql/005_jobs_job_number.sql``; databases that have not run it have no
``job_number`` — :func:`fetch_jobs_for_job_database` then omits it from SELECT/INSERT.

**Canonical columns read/written by Job Database**

These match :data:`JOBS_JOB_DATABASE_COLUMNS` (minus optional ``job_number`` / ``source_type``):

- ``id`` (uuid, PK) — required for selection/delete; not shown as a grid column
- ``customer_id`` (uuid, FK → customers)
- ``customer_contact_id`` (uuid, nullable, FK → customer_contacts) — **optional** (migration 016)
- ``customer_location_id`` (uuid, nullable, FK → customer_locations) — **optional** (migration 024)
- ``job_number`` (text) — **optional** (migration 005); new rows use ``JYY###`` via
  :mod:`services.shared_sequence` (same yearly counter as quote numbers ``QYY###``)
- ``job_name`` (text)
- ``location`` (text)
- ``status`` (text) — use for open/closed lifecycle (many schemas have no ``is_active`` on ``jobs``)
- ``estimate_id`` (uuid, nullable, FK → estimates)
- ``project_manager``, ``supervisor`` (text)
- ``start_date``, ``target_completion_date``, ``completed_date`` (date or text)
- ``awarded_amount`` (numeric)
- ``notes`` (text)
- ``source_type`` (text) — **optional** (migration 022): ``estimate`` | ``standalone``

**Overview grid** may also show joined fields (not on ``jobs``): ``customer_name``,
``estimate_label`` — see :data:`JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER`.
"""

from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger(__name__)

try:
    from db import fetch_jobs_with_order_fallback, fetch_table, fetch_table_admin
except ImportError:
    from app.db import fetch_jobs_with_order_fallback, fetch_table, fetch_table_admin  # type: ignore

JOB_SOURCE_TYPE_ESTIMATE = "estimate"
JOB_SOURCE_TYPE_STANDALONE = "standalone"

# Core columns (always expected once the jobs table exists).
JOBS_JOB_DATABASE_COLUMNS_CORE: tuple[str, ...] = (
    "id",
    "customer_id",
    "customer_contact_id",
    "customer_location_id",
    "job_number",
    "job_name",
    "location",
    "status",
    "estimate_id",
    "project_manager",
    "supervisor",
    "start_date",
    "target_completion_date",
    "completed_date",
    "awarded_amount",
    "notes",
)

# Includes ``source_type`` when migration ``022_jobs_source_type.sql`` has been applied.
JOBS_JOB_DATABASE_COLUMNS: tuple[str, ...] = JOBS_JOB_DATABASE_COLUMNS_CORE + ("source_type",)

JOBS_JOB_DATABASE_COLUMNS_NO_JOB_NUMBER: tuple[str, ...] = tuple(
    c for c in JOBS_JOB_DATABASE_COLUMNS if c != "job_number"
)

JOBS_JOB_DATABASE_COLUMNS_NO_CONTACT: tuple[str, ...] = tuple(
    c for c in JOBS_JOB_DATABASE_COLUMNS if c != "customer_contact_id"
)

JOBS_JOB_DATABASE_COLUMNS_NO_CONTACT_NO_JOB_NUMBER: tuple[str, ...] = tuple(
    c for c in JOBS_JOB_DATABASE_COLUMNS_NO_JOB_NUMBER if c != "customer_contact_id"
)


def _job_database_fetch_column_variants() -> list[tuple[str, ...]]:
    """Prefer column sets that include ``source_type``; fall back for older databases."""
    out: list[tuple[str, ...]] = []
    for base in (JOBS_JOB_DATABASE_COLUMNS, JOBS_JOB_DATABASE_COLUMNS_CORE):
        out.append(base)
        out.append(tuple(c for c in base if c != "customer_contact_id"))
        out.append(tuple(c for c in base if c != "customer_location_id"))
        out.append(tuple(c for c in base if c != "job_number"))
        out.append(
            tuple(c for c in base if c != "job_number" and c != "customer_contact_id"),
        )
        out.append(tuple(c for c in base if c != "job_number" and c != "customer_location_id"))
        out.append(
            tuple(
                c
                for c in base
                if c != "job_number" and c != "customer_contact_id" and c != "customer_location_id"
            ),
        )
    # Dedupe (preserve order)
    seen: set[tuple[str, ...]] = set()
    uniq: list[tuple[str, ...]] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq

# Job Database overview: ``jobs`` columns + joined labels (only columns present are shown).
# ``job_number`` is prepended only when :func:`fetch_jobs_for_job_database` reports it exists.
JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER: tuple[str, ...] = (
    "job_name",
    "customer_name",
    "Location",
    "customer_id",
    "source_type",
    "Quote (estimate)",
    "estimate_label",
    "status",
    "project_manager",
    "supervisor",
    "location",
    "start_date",
    "target_completion_date",
    "completed_date",
    "awarded_amount",
    "notes",
)


def _columns_sql(cols: tuple[str, ...]) -> str:
    return ", ".join(cols)


def _fetch_jobs_rows(
    *,
    columns_sql: str,
    limit: int,
    use_admin: bool,
) -> list[dict[str, Any]]:
    """
    Load ``jobs`` rows using only real columns — never ``description`` (use ``notes``).

    Sorting: ``job_name`` first, then ``status``, then unordered if the API rejects ordering.
    """
    fn = fetch_table_admin if use_admin else fetch_table
    last_err: Exception | None = None
    for order_by in ("job_name", "status", None):
        try:
            return fn(
                "jobs",
                columns=columns_sql,
                limit=limit,
                order_by=order_by,
            )
        except Exception as exc:
            last_err = exc
            _LOG.warning(
                "jobs fetch failed (order_by=%r): %s",
                order_by,
                exc,
            )
    if last_err is not None:
        raise last_err
    return []


def fetch_jobs_for_job_database(
    limit: int = 5000,
    *,
    admin_read: bool = False,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Load jobs for the Job Database UI.

    Returns ``(rows, has_job_number_column)``. If selecting ``job_number`` fails (column
    missing), retries with
    :data:`JOBS_JOB_DATABASE_COLUMNS_NO_JOB_NUMBER`. Does **not** select ``is_active``;
    use ``status`` in the app for job lifecycle when that column exists.

    ``admin_read=True`` uses the service-role client first (recommended for admin/estimator
    when RLS would hide rows from the anon client).

    If all typed column lists fail, falls back to :func:`db.fetch_jobs_with_order_fallback`
    (``select('*')``) so the grid can still populate.
    """
    variants: list[tuple[str, ...]] = _job_database_fetch_column_variants()
    last_err: Exception | None = None
    for cols in variants:
        try:
            rows = _fetch_jobs_rows(
                columns_sql=_columns_sql(cols),
                limit=limit,
                use_admin=admin_read,
            )
            has_jn = "job_number" in cols
            return list(rows), has_jn
        except Exception as exc:
            last_err = exc
            _LOG.warning("jobs query failed for columns %s: %s", cols, exc)
    try:
        relaxed = fetch_jobs_with_order_fallback(limit=limit, use_admin=admin_read)
        has_jn = bool(relaxed) and any("job_number" in (r or {}) for r in relaxed)
        return list(relaxed), has_jn
    except Exception as exc:
        last_err = exc
        _LOG.warning("jobs relaxed select('*') fetch failed: %s", exc)
    if last_err is not None:
        raise last_err
    return [], False
