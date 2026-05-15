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


from app.utils.formatters import job_display_label


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
    Falls back to ``Job {id}…`` when name/number are missing so rows are never dropped from pickers.
    """
    num = job_number_display(j.get("job_number"))
    name = str(j.get("job_name") or "").strip()
    jid = str(j.get("id") or "").strip()
    if num and name:
        return f"{num} — {name}"
    if num:
        return num
    if name:
        return name
    if jid:
        return f"Job {jid[:8]}…"
    return "—"


def build_job_dropdown_label_maps(
    jobs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    """
    Build unique labels for every job row with an ``id``.

    Returns ``(options, label_to_id, labels_sorted)`` where each option is
    ``{"id": "<uuid>", "label": "<unique label>"}`` and ``labels_sorted`` is the
    lexicographic sort of labels for stable selectboxes.
    """
    rows = [j for j in (jobs or []) if isinstance(j, dict) and str(j.get("id") or "").strip()]
    rows = sort_jobs_by_number_then_name(rows)
    label_to_id: dict[str, str] = {}
    options: list[dict[str, Any]] = []
    used: set[str] = set()
    for j in rows:
        jid = str(j.get("id")).strip()
        base = job_row_select_label(j)
        label = base
        n = 0
        while label in used:
            n += 1
            short = jid[:8]
            if base and base != "—":
                label = f"{base} ·{short}" + (f" ({n})" if n > 1 else "")
            else:
                label = f"Job {short}" + (f" ({n})" if n > 1 else "")
        used.add(label)
        label_to_id[label] = jid
        options.append({"id": jid, "label": label})
    labels_sorted = sorted(label_to_id.keys(), key=str.casefold)
    return options, label_to_id, labels_sorted


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
