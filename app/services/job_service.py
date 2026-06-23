from __future__ import annotations

import re
from typing import Any

# Archived / estimate sub-rows (e.g. J26070-A42493B) — not primary field jobs.
_SUBJOB_STYLE_NUMBER_RE = re.compile(r"^J\d{5}-[A-Z0-9]", re.IGNORECASE)

_EXCLUDED_FIELD_JOB_STATUSES = frozenset(
    {"Deleted", "Archived", "Completed", "Closed", "Cancelled"}
)

try:
    from app.services.shared_sequence import next_job_number_string
except ImportError:
    from services.shared_sequence import next_job_number_string  # type: ignore

_JOB_LEGACY = re.compile(r"^JOB-(\d+)$", re.IGNORECASE)


def next_job_number() -> str:
    """Next job id: ``JYY###`` (same shared yearly sequence as :func:`~app.db.next_quote_number`)."""
    return next_job_number_string()


def job_number_display(value: str | None) -> str:
    """
    Format stored ``job_number`` for UI.

    Legacy ``JOB-nnnn`` maps to ``J`` + current UTC year + 3-digit sequence when possible;
    otherwise returns the stored value (``JYYNNN``).
    """
    s = str(value or "").strip()
    if not s:
        return ""
    m = _JOB_LEGACY.match(s)
    if m:
        try:
            from app.services.shared_sequence import format_job_number
        except ImportError:
            from services.shared_sequence import format_job_number  # type: ignore
        try:
            return format_job_number(int(m.group(1)))
        except ValueError:
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


def normalize_job_status_for_filter(raw: object) -> str:
    """Canonical job status labels (aligned with Jobs page filters)."""
    try:
        from app.services.jobs_service import normalize_job_status
    except ImportError:
        from services.jobs_service import normalize_job_status  # type: ignore
    return normalize_job_status(raw)


_DASHBOARD_JOB_METRIC_BUCKETS: dict[str, str] = {
    "Active": "active_jobs",
    "On Hold": "on_hold_jobs",
    "Completed": "complete_jobs",
    "Cancelled": "cancelled_jobs",
}


def dashboard_job_metrics(jobs: list[dict[str, Any]]) -> dict[str, int]:
    """Dashboard job KPI counts by normalized status."""
    out = {
        "active_jobs": 0,
        "on_hold_jobs": 0,
        "complete_jobs": 0,
        "cancelled_jobs": 0,
        # Legacy keys kept at zero for older dashboard widgets.
        "jobs_awarded": 0,
        "pending_jobs": 0,
        "draft_jobs": 0,
        "estimate_pending_jobs": 0,
    }
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if bool(job.get("is_deleted")):
            continue
        bucket = _DASHBOARD_JOB_METRIC_BUCKETS.get(normalize_job_status_for_filter(job.get("status")))
        if bucket:
            out[bucket] += 1
    return out


def is_primary_job_number(job_number: object) -> bool:
    """Exclude archived/subjob-style numbers (e.g. J26070-A42493B)."""
    num = job_number_display(job_number)
    if not num or num in {"—", "-"}:
        return True
    return _SUBJOB_STYLE_NUMBER_RE.match(num) is None


def is_job_assignable_for_field_picker(job: dict[str, Any]) -> bool:
    """Open jobs suitable for timekeeping / weekly timesheet pickers."""
    if bool(job.get("is_deleted")):
        return False
    status = normalize_job_status_for_filter(job.get("status"))
    if status in _EXCLUDED_FIELD_JOB_STATUSES:
        return False
    if not is_primary_job_number(job.get("job_number")):
        return False
    return True


def is_job_eligible_for_weekly_timesheet(job: dict[str, Any]) -> bool:
    """
    Jobs that may appear on the Weekly Timesheets picker.

    Matches the Jobs page breadth (includes completed/closed jobs for past weeks),
    but drops deleted/archived rows, estimate shells, and subjob-style numbers.
    """
    if bool(job.get("is_deleted")):
        return False
    if not str(job.get("id") or "").strip():
        return False
    status = normalize_job_status_for_filter(job.get("status"))
    if status in {"Deleted", "Archived"}:
        return False
    num = job_number_display(job.get("job_number"))
    if num and _SUBJOB_STYLE_NUMBER_RE.match(num):
        return False
    if not num and not str(job.get("job_name") or "").strip():
        return False
    return True


def load_jobs_for_select(*, limit: int = 5000, use_admin: bool | None = None) -> list[dict[str, Any]]:
    """Load jobs from Supabase with admin fallback (matches Jobs / time tracking reads)."""
    if use_admin is None:
        try:
            from app.auth import current_role
        except ImportError:
            from auth import current_role  # type: ignore
        role = str(current_role() or "").strip().lower()
        use_admin = role in {"admin", "manager", "supervisor", "project manager", "pm"}
    try:
        from app.db import fetch_jobs_with_order_fallback
    except ImportError:
        from db import fetch_jobs_with_order_fallback  # type: ignore
    try:
        rows = list(fetch_jobs_with_order_fallback(limit=limit, use_admin=bool(use_admin)) or [])
        if rows:
            return sort_jobs_by_number_then_name(rows)
    except Exception:
        pass
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore
    return sort_jobs_by_number_then_name(load_jobs())


def weekly_timesheet_job_options(*, include_customer: bool = False) -> dict[str, str]:
    """
    Label → job id map for the weekly timesheet Job selectbox.

    Loads all live jobs (service-role read), sorted by job number. Labels are kept
    unique per job id so rows are never dropped by duplicate dict keys.
    """
    _ = include_customer  # legacy kwarg; customer suffixes caused duplicate-key collisions
    jobs = load_jobs_for_select(use_admin=True)
    eligible = [j for j in jobs if is_job_eligible_for_weekly_timesheet(j)]
    if not eligible:
        eligible = [j for j in jobs if not bool(j.get("is_deleted")) and str(j.get("id") or "").strip()]
    _, label_to_id, labels = build_job_dropdown_label_maps(eligible)
    opts: dict[str, str] = {"": ""}
    for label in labels:
        jid = label_to_id.get(label) or ""
        if jid:
            opts[label] = jid
    return opts
