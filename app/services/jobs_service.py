"""
Jobs module — Supabase reads/writes.

Schema assumptions: table ``jobs`` with columns job_number, job_name, customer_id,
status, start_date, target_completion_date, notes, supervisor (optional).
"""

from __future__ import annotations

from typing import Any

from app.services.phase2_modules_service import (
    delete_job,
    list_jobs,
    normalize_job,
    save_job,
)

__all__ = ["delete_job", "get_job_options", "list_jobs", "normalize_job", "save_job"]

_OPEN_JOB_STATUSES = frozenset(
    {"active", "awarded", "in progress", "open", "scheduled", "pending", "draft"}
)


def get_job_options(*, include_all: bool = False) -> list[dict[str, Any]]:
    """Return job dropdown options as ``{id, label}`` rows for task linking."""
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore

    opts: list[dict[str, Any]] = [{"id": None, "label": "— None —"}]
    for job in load_jobs():
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        status = str(job.get("status") or "").strip().lower()
        if not include_all and status and status not in _OPEN_JOB_STATUSES:
            continue
        num = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or "").strip()
        if num and name:
            label = f"{num} — {name}"
        elif num:
            label = num
        elif name:
            label = name
        else:
            label = jid
        opts.append({"id": jid, "label": label})
    return opts
