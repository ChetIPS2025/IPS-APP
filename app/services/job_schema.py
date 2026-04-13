"""
Jobs table — columns the **Job Database** page uses on ``public.jobs``.

There is **no** ``description`` column; long text is ``notes``. The ``job_number`` column is
added by ``sql/005_jobs_job_number.sql``; databases that have not run it have no
``job_number`` — :func:`fetch_jobs_for_job_database` then omits it from SELECT/INSERT.

**Canonical columns read/written by Job Database**

These match :data:`JOBS_JOB_DATABASE_COLUMNS` (minus optional ``job_number``):

- ``id`` (uuid, PK) — required for selection/delete; not shown as a grid column
- ``customer_id`` (uuid, FK → customers)
- ``customer_contact_id`` (uuid, nullable, FK → customer_contacts) — **optional** (migration 016)
- ``job_number`` (text) — **optional** (migration 005); new rows use ``J#####`` via
  :mod:`services.shared_sequence` (same counter as quote numbers ``Q#####``)
- ``job_name`` (text)
- ``location`` (text)
- ``status`` (text) — use for open/closed lifecycle (many schemas have no ``is_active`` on ``jobs``)
- ``estimate_id`` (uuid, nullable, FK → estimates)
- ``project_manager``, ``supervisor`` (text)
- ``start_date``, ``target_completion_date``, ``completed_date`` (date or text)
- ``awarded_amount`` (numeric)
- ``notes`` (text)

**Overview grid** may also show joined fields (not on ``jobs``): ``customer_name``,
``estimate_label`` — see :data:`JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER`.
"""

from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger(__name__)

try:
    from db import fetch_table
except ImportError:
    from app.db import fetch_table  # type: ignore

# All columns this page SELECTs, INSERTs, or UPDATEs (real app usage only).
JOBS_JOB_DATABASE_COLUMNS: tuple[str, ...] = (
    "id",
    "customer_id",
    "customer_contact_id",
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

JOBS_JOB_DATABASE_COLUMNS_NO_JOB_NUMBER: tuple[str, ...] = tuple(
    c for c in JOBS_JOB_DATABASE_COLUMNS if c != "job_number"
)

JOBS_JOB_DATABASE_COLUMNS_NO_CONTACT: tuple[str, ...] = tuple(
    c for c in JOBS_JOB_DATABASE_COLUMNS if c != "customer_contact_id"
)

JOBS_JOB_DATABASE_COLUMNS_NO_CONTACT_NO_JOB_NUMBER: tuple[str, ...] = tuple(
    c for c in JOBS_JOB_DATABASE_COLUMNS_NO_JOB_NUMBER if c != "customer_contact_id"
)

# Job Database overview: ``jobs`` columns + joined labels (only columns present are shown).
# ``job_number`` is prepended only when :func:`fetch_jobs_for_job_database` reports it exists.
JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER: tuple[str, ...] = (
    "job_name",
    "customer_name",
    "customer_id",
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
) -> list[dict[str, Any]]:
    """
    Load ``jobs`` rows using only real columns — never ``description`` (use ``notes``).

    Sorting: ``job_name`` first, then ``status``, then unordered if the API rejects ordering.
    """
    last_err: Exception | None = None
    for order_by in ("job_name", "status", None):
        try:
            return fetch_table(
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


def fetch_jobs_for_job_database(limit: int = 5000) -> tuple[list[dict[str, Any]], bool]:
    """
    Load jobs for the Job Database UI.

    Returns ``(rows, has_job_number_column)``. If selecting ``job_number`` fails (column
    missing), retries with
    :data:`JOBS_JOB_DATABASE_COLUMNS_NO_JOB_NUMBER`. Does **not** select ``is_active``;
    use ``status`` in the app for job lifecycle when that column exists.

    Ordering uses :func:`_fetch_jobs_rows` (``job_name``, then ``status``, then no ``order_by``).
    """
    variants: list[tuple[str, ...]] = [
        JOBS_JOB_DATABASE_COLUMNS,
        JOBS_JOB_DATABASE_COLUMNS_NO_CONTACT,
        JOBS_JOB_DATABASE_COLUMNS_NO_JOB_NUMBER,
        JOBS_JOB_DATABASE_COLUMNS_NO_CONTACT_NO_JOB_NUMBER,
    ]
    last_err: Exception | None = None
    for cols in variants:
        try:
            rows = _fetch_jobs_rows(columns_sql=_columns_sql(cols), limit=limit)
            has_jn = "job_number" in cols
            return list(rows), has_jn
        except Exception as exc:
            last_err = exc
            _LOG.warning("jobs query failed for columns %s: %s", cols, exc)
    if last_err is not None:
        raise last_err
    return [], False
