from __future__ import annotations

import re
from typing import Any

try:
    from app.services.shared_sequence import next_job_number_string
except ImportError:
    from services.shared_sequence import next_job_number_string  # type: ignore

_JOB_LEGACY = re.compile(r"^JOB-(\d+)$", re.IGNORECASE)


def next_job_number() -> str:
    """Next job id: ``J`` + five digits (same shared sequence as :func:`~app.db.next_quote_number`)."""
    return next_job_number_string()


def job_number_display(value: str | None) -> str:
    """
    Format stored ``job_number`` for UI: legacy ``JOB-nnnn`` maps to ``J`` + five digits; else as stored.
    """
    s = str(value or "").strip()
    if not s:
        return ""
    m = _JOB_LEGACY.match(s)
    if m:
        return f"J{int(m.group(1)):05d}"
    return s


def job_display_primary(j: dict[str, Any] | None) -> str:
    """Prefer formatted ``job_number``; fall back to ``job_name`` if missing."""
    if not j:
        return ""
    num = job_number_display(j.get("job_number"))
    if num:
        return num
    return str(j.get("job_name") or "").strip()


def job_row_select_label(j: dict[str, Any]) -> str:
    """
    Human-readable label for dropdowns: ``J00001 — Site name`` (legacy ``JOB-`` shown as ``J#####``).
    """
    num = job_number_display(j.get("job_number"))
    name = str(j.get("job_name") or "").strip()
    if num and name:
        return f"{num} — {name}"
    return num or name or "—"


def sort_jobs_by_number_then_name(jobs: list[dict]) -> list[dict]:
    """
    Sort in Python when DB order is insufficient: by job_number (lexicographic), then job_name.
    Rows with empty job_number sort after numbered rows using job_name as tie-breaker.
    """

    def key(j: dict) -> tuple:
        jn = str(j.get("job_number") or "").strip()
        jm = str(j.get("job_name") or "").strip().lower()
        # Empty job_number sorts last within same "bucket"
        return (0 if jn else 1, jn, jm)

    return sorted(jobs, key=key)


def sort_jobs_by_name(jobs: list[dict]) -> list[dict]:
    """Sort by ``job_name`` (case-insensitive), then ``id`` for stability — when ``job_number`` is unavailable."""
    return sorted(
        jobs,
        key=lambda j: (
            str(j.get("job_name") or "").strip().lower(),
            str(j.get("id") or ""),
        ),
    )
