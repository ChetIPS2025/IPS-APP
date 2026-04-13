"""
Create a Job Database row from an approved / awarded estimate.

Quote numbers (``Q#####``) and job numbers (``J#####``) use the shared sequence elsewhere;
this module only assigns ``job_number`` when the ``jobs`` table has that column (same pattern
as the Job Database page).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, FrozenSet

try:
    from db import fetch_by_match_admin, fetch_one, insert_row, update_rows_admin
except ImportError:
    from app.db import fetch_by_match_admin, fetch_one, insert_row, update_rows_admin  # type: ignore

try:
    from services.job_schema import fetch_jobs_for_job_database
    from services.job_service import job_number_display, next_job_number
except ImportError:
    from app.services.job_schema import fetch_jobs_for_job_database  # type: ignore
    from app.services.job_service import job_number_display, next_job_number  # type: ignore


# --- Status gate (easy to tighten) ---
# ``None`` = allow any estimate status (use while workflow is still evolving).
# Set to a non-``None`` frozenset to restrict, e.g. ``frozenset({"approved", "awarded", "won"})``.
ESTIMATE_STATUSES_ALLOWED_FOR_JOB_CREATION: FrozenSet[str] | None = None


def estimate_status_allows_job_creation(status: str | None) -> bool:
    """Return whether an estimate ``status`` may use **Create Job from Estimate**."""
    allowed = ESTIMATE_STATUSES_ALLOWED_FOR_JOB_CREATION
    if allowed is None:
        return True
    s = (status or "").strip().lower()
    return s in allowed


def _as_json_dict(val: Any) -> dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _existing_job_for_estimate(estimate_id: str, row: dict[str, Any]) -> dict[str, Any] | None:
    by_ref = fetch_by_match_admin(
        "jobs",
        {"estimate_id": estimate_id},
        columns="id,job_number,job_name",
        limit=5,
    )
    if by_ref:
        return by_ref[0]
    jid = row.get("job_id")
    if jid:
        got = fetch_by_match_admin(
            "jobs",
            {"id": jid},
            columns="id,job_number,job_name",
            limit=1,
        )
        if got:
            return got[0]
    return None


def _derive_job_name(row: dict[str, Any], ej: dict[str, Any], customer_name: str) -> str:
    scope = str(row.get("scope_of_work") or ej.get("scope_of_work") or "").strip()
    first_line = scope.split("\n")[0].strip() if scope else ""
    quote = str(row.get("quote_number") or ej.get("quote_number") or "").strip()
    meta = _as_json_dict(ej.get("import_meta"))
    vendor_title = str(meta.get("title") or meta.get("project_name") or "").strip()

    if len(vendor_title) >= 3:
        return vendor_title[:500]
    if len(first_line) >= 8:
        return first_line[:500]
    parts = [p for p in (customer_name.strip(), quote) if p]
    if parts:
        return " — ".join(parts)[:500]
    if quote:
        return quote[:500]
    return "Awarded job"


def _build_job_notes(row: dict[str, Any], ej: dict[str, Any]) -> str:
    chunks: list[str] = []
    scope = str(row.get("scope_of_work") or ej.get("scope_of_work") or "").strip()
    if scope:
        chunks.append("Scope of work:\n" + scope)
    exc = str(row.get("exclusions") or ej.get("exclusions") or "").strip()
    if exc:
        chunks.append("Exclusions:\n" + exc)
    add = str(row.get("additional_charges") or ej.get("additional_charges") or "").strip()
    if add:
        chunks.append("Additional charges:\n" + add)
    qn = str(row.get("quote_number") or ej.get("quote_number") or "").strip()
    if qn:
        chunks.append(f"Created from estimate quote {qn}.")
    return "\n\n".join(chunks).strip()[:20000]


def _safe_location(ej: dict[str, Any]) -> str:
    meta = _as_json_dict(ej.get("import_meta"))
    for key in ("job_site", "location", "site_address"):
        v = str(meta.get(key) or "").strip()
        if v:
            return v[:2000]
    return ""


@dataclass
class CreateJobFromEstimateResult:
    ok: bool
    message: str
    job: dict[str, Any] | None = None
    error_code: str | None = None


def create_job_from_estimate(estimate_id: str) -> CreateJobFromEstimateResult:
    """
    Insert a ``jobs`` row linked to the estimate, then set ``estimates.job_id`` and mirror
    ``job_id`` inside ``estimate_json``.

    Does not create a second job if the estimate already references a job or a job row already
    points at this estimate (duplicate).
    """
    eid = str(estimate_id or "").strip()
    if not eid:
        return CreateJobFromEstimateResult(ok=False, message="Invalid estimate id.", error_code="invalid_id")

    row = fetch_one("estimates", {"id": eid})
    if not row:
        return CreateJobFromEstimateResult(ok=False, message="Estimate not found.", error_code="not_found")

    status_raw = row.get("status")
    if not estimate_status_allows_job_creation(str(status_raw)):
        return CreateJobFromEstimateResult(
            ok=False,
            message=(
                f"Creating a job from this estimate is not allowed while status is {status_raw!r}. "
                "Change status to an approved/awarded state first (or relax "
                "ESTIMATE_STATUSES_ALLOWED_FOR_JOB_CREATION in job_from_estimate.py)."
            ),
            error_code="bad_status",
        )

    existing = _existing_job_for_estimate(eid, row)
    if existing:
        jn = job_number_display(existing.get("job_number"))
        label = jn or str(existing.get("job_name") or "").strip() or "existing job"
        return CreateJobFromEstimateResult(
            ok=False,
            message=f"This estimate already has a job: {label}",
            job=existing,
            error_code="duplicate",
        )

    ej = _as_json_dict(row.get("estimate_json"))
    customer_id = row.get("customer_id") or ej.get("customer_id")
    if not customer_id:
        return CreateJobFromEstimateResult(
            ok=False,
            message="Choose a customer on the estimate before creating a job.",
            error_code="no_customer",
        )

    cust_row = fetch_one("customers", {"id": customer_id}, columns="customer_name")
    customer_name = str((cust_row or {}).get("customer_name") or "").strip()

    job_name = _derive_job_name(row, ej, customer_name).strip() or "Awarded job"

    _, has_job_number_column = fetch_jobs_for_job_database(limit=1)

    awarded = row.get("proposal_total")
    if awarded is None:
        awarded = row.get("final_bid")
    try:
        awarded_f = float(awarded or 0)
    except (TypeError, ValueError):
        awarded_f = 0.0

    payload: dict[str, Any] = {
        "customer_id": customer_id,
        "job_name": job_name,
        "location": _safe_location(ej),
        "status": "Awarded",
        "estimate_id": eid,
        "project_manager": "",
        "supervisor": "",
        "start_date": None,
        "target_completion_date": None,
        "completed_date": None,
        "awarded_amount": awarded_f,
        "notes": _build_job_notes(row, ej),
    }
    if has_job_number_column:
        payload["job_number"] = next_job_number()

    try:
        inserted = insert_row("jobs", payload)
    except Exception as exc:
        return CreateJobFromEstimateResult(
            ok=False,
            message=f"Could not create job: {exc}",
            error_code="insert_failed",
        )

    new_id = str(inserted.get("id") or "")
    if not new_id:
        return CreateJobFromEstimateResult(ok=False, message="Job insert returned no id.", error_code="insert_failed")

    ej2 = dict(ej)
    ej2["job_id"] = new_id

    est_update: dict[str, Any] = {
        "job_id": new_id,
        "estimate_json": ej2,
        "updated_at": datetime.utcnow().isoformat(),
    }
    try:
        update_rows_admin("estimates", est_update, {"id": eid})
    except Exception as exc:
        return CreateJobFromEstimateResult(
            ok=False,
            message=f"Job was created but linking to the estimate failed: {exc}. Link it manually in Job Database.",
            job=inserted,
            error_code="link_failed",
        )

    jn = job_number_display(inserted.get("job_number") if has_job_number_column else None)
    msg = f"Created job {jn or new_id} and linked it to this estimate." if jn else f"Created job and linked it to this estimate ({new_id})."
    return CreateJobFromEstimateResult(ok=True, message=msg, job=inserted)
