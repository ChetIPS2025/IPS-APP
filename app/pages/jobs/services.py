"""Business-logic layer for the Jobs module.

All create / update / delete operations live here.
UI calls these functions; they call the DB layer.
"""
from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger(__name__)

try:
    from app.db import insert_row, insert_row_admin, update_rows_admin
except ImportError:
    from db import insert_row, insert_row_admin, update_rows_admin  # type: ignore

try:
    from services.delete_safety import delete_job_row_if_no_costing
except ImportError:
    from app.services.delete_safety import delete_job_row_if_no_costing  # type: ignore

try:
    from services.job_from_estimate import create_job_from_estimate
except ImportError:
    from app.services.job_from_estimate import create_job_from_estimate  # type: ignore

from .queries import admin_read, bump_data_version


def create_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a new job row and bump the cache version."""
    fn = insert_row_admin if admin_read() else insert_row
    try:
        result = fn("jobs", payload)
        bump_data_version()
        return result
    except Exception as exc:
        _LOG.exception("create_job failed")
        raise RuntimeError(f"Could not create job: {exc}") from exc


def update_job(job_id: str, payload: dict[str, Any]) -> None:
    """Update an existing job row and bump the cache version."""
    try:
        update_rows_admin("jobs", payload, {"id": str(job_id).strip()})
        bump_data_version()
    except Exception as exc:
        _LOG.exception("update_job failed (id=%s)", job_id)
        raise RuntimeError(f"Could not update job: {exc}") from exc


def delete_jobs(job_ids: list[str], *, is_admin: bool) -> tuple[int, list[str]]:
    """Delete multiple jobs; skip those that have costing data.

    Returns (success_count, list_of_error_messages).
    """
    n_ok = 0
    errors: list[str] = []
    for jid in job_ids:
        try:
            delete_job_row_if_no_costing(str(jid), admin_read=is_admin)
            n_ok += 1
        except RuntimeError as exc:
            errors.append(f"{jid[:8]}… — {exc!s}")
        except Exception as exc:
            errors.append(f"Could not delete job {jid}: {exc}")
    if n_ok:
        bump_data_version()
    return n_ok, errors


def convert_estimate_to_job(estimate_id: str):  # returns service result object
    """Thin wrapper so the UI doesn't import the service directly."""
    result = create_job_from_estimate(str(estimate_id).strip())
    if result.ok:
        bump_data_version()
    return result
