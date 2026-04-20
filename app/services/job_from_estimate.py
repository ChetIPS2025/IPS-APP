"""
Create a Job Database row from an approved / awarded estimate.

**Architecture:** this is the **estimate → job** conversion path only. The resulting row is
the **costing / work** record (``jobs.id`` / ``job_number``); the estimate stays a quote and
is linked via ``estimate_id``. Time, job costing, and PO expenses should key off ``job_id``.

Quote numbers (``Q#####``) map to ``J#####`` when ``job_number`` exists; see
:func:`estimate_quote_to_job_number`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, FrozenSet

try:
    from db import (
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        insert_row_admin,
        update_rows_admin,
    )
except ImportError:
    from app.db import (  # type: ignore
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        insert_row_admin,
        update_rows_admin,
    )

try:
    from services.job_schema import (
        JOB_SOURCE_TYPE_ESTIMATE,
        fetch_jobs_for_job_database,
    )
    from services.job_service import job_number_display, next_job_number
except ImportError:
    from app.services.job_schema import (  # type: ignore
        JOB_SOURCE_TYPE_ESTIMATE,
        fetch_jobs_for_job_database,
    )
    from app.services.job_service import job_number_display, next_job_number  # type: ignore


# --- Status gate (workflow rule) ---
# Estimates should stay on the Estimates page until accepted by the customer.
# Only allow job creation once the estimate is customer-approved / accepted.
ESTIMATE_STATUSES_ALLOWED_FOR_JOB_CREATION: FrozenSet[str] | None = frozenset(
    {
        "approved",
        "accepted",
        "awarded",
        "po_received",
    }
)

# Only for :func:`create_job_from_estimate` — standalone jobs use the Job Database form default/status.
JOB_STATUS_AFTER_ESTIMATE_CONVERSION = "Awarded"


def estimate_status_allows_job_creation(status: str | None) -> bool:
    """Return whether an estimate ``status`` may use **Create Job from Estimate**."""
    allowed = ESTIMATE_STATUSES_ALLOWED_FOR_JOB_CREATION
    if allowed is None:
        return True
    s = (status or "").strip().lower()
    return s in allowed


def _as_json_dict(val: Any) -> dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _truthy_job_received(row: dict[str, Any]) -> bool:
    v = row.get("job_received")
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        try:
            return float(v) != 0.0
        except (TypeError, ValueError):
            return False
    s = str(v).strip().lower()
    return s in ("true", "1", "yes", "t")


def _jobs_has_customer_contact_column() -> bool:
    try:
        fetch_table("jobs", columns="id,customer_contact_id", limit=1)
        return True
    except Exception:
        return False


def _jobs_has_customer_location_column() -> bool:
    try:
        fetch_table("jobs", columns="id,customer_location_id", limit=1)
        return True
    except Exception:
        return False


def _location_text_from_customer_location(location_id: str | None) -> str:
    lid = str(location_id or "").strip()
    if not lid:
        return ""
    try:
        loc_row = fetch_one("customer_locations", {"id": lid})
    except Exception:
        loc_row = None
    if not loc_row:
        return ""
    try:
        from services.customer_locations import location_display_name_city_state
    except ImportError:
        from app.services.customer_locations import location_display_name_city_state  # type: ignore

    label = location_display_name_city_state(loc_row)
    if label:
        return label[:2000]
    parts = [loc_row.get("address"), loc_row.get("city"), loc_row.get("state"), loc_row.get("zip")]
    return ", ".join(str(p).strip() for p in parts if p and str(p).strip())[:2000]


def _fetch_estimate_row_for_create(estimate_id: str) -> dict[str, Any] | None:
    """
    Load the estimate row by primary key ``id``.

    Admin/estimator use service-role reads first (same as the Estimates list); falls back to the
    user client so the row is found whenever it appears in the grid.
    """
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    try:
        from auth import current_role

        admin_read = current_role() in {"admin", "estimator"}
    except Exception:
        admin_read = False
    if admin_read:
        try:
            rows = fetch_by_match_admin("estimates", {"id": eid}, limit=1)
            if rows:
                return rows[0]
        except Exception:
            pass
    try:
        rows = fetch_by_match("estimates", {"id": eid}, limit=1)
        if rows:
            return rows[0]
    except Exception:
        pass
    return fetch_one("estimates", {"id": eid})


def estimate_quote_to_job_number(quote_number: str) -> str:
    """
    Map an estimate **quote_number** (e.g. ``Q26025`` or ``26025``) to a related **job_number**
    (``J26025``). Leading alphabetic prefix is replaced with ``J``; otherwise ``J`` is prepended.

    Used only for estimate-to-job conversion — standalone jobs keep ``next_job_number()``.
    """
    q = str(quote_number or "").strip()
    if not q:
        return ""
    first = q[:1]
    if first.isalpha():
        return ("J" + q[1:])[:120]
    return ("J" + q)[:120]


def estimate_description_value(estimate_row: dict[str, Any]) -> str:
    """
    Short label for an estimate (same field as **Estimate Description** in the editor).

    Prefer DB column, then ``estimate_json`` scalars, then legacy ``job`` / ``job_name`` keys.
    Does not read ``scope_of_work`` (long proposal text).
    """
    est_json = estimate_row.get("estimate_json") or {}
    est_json = est_json if isinstance(est_json, dict) else {}
    return str(
        estimate_row.get("estimate_description")
        or est_json.get("estimate_description")
        or estimate_row.get("job")
        or est_json.get("job")
        or estimate_row.get("job_name")
        or est_json.get("job_name")
        or ""
    ).strip()


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


def _fallback_job_name(row: dict[str, Any], ej: dict[str, Any], customer_name: str) -> str:
    """
    Job name when no short **Estimate Description** (or legacy job/job_name) is set.

    Prefers import title, then customer + quote / quote alone. Uses first line of
    ``scope_of_work`` only when nothing else is available.
    """
    meta = _as_json_dict(ej.get("import_meta"))
    vendor_title = str(meta.get("title") or meta.get("project_name") or "").strip()
    quote = str(row.get("quote_number") or ej.get("quote_number") or "").strip()

    if len(vendor_title) >= 3:
        return vendor_title[:500]
    parts = [p for p in (customer_name.strip(), quote) if p]
    if parts:
        return " — ".join(parts)[:500]
    if quote:
        return quote[:500]
    scope = str(row.get("scope_of_work") or ej.get("scope_of_work") or "").strip()
    first_line = scope.split("\n")[0].strip() if scope else ""
    if len(first_line) >= 8:
        return first_line[:500]
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


def create_job_from_estimate(
    estimate_id: str,
    *,
    mark_job_received: bool = False,
) -> CreateJobFromEstimateResult:
    """
    Insert a ``jobs`` row linked to the estimate, then set ``estimates.job_id`` and mirror
    ``job_id`` inside ``estimate_json``.

    Does not create a second job if the estimate already references a job or a job row already
    points at this estimate (duplicate), or if the estimate is already marked ``job_received``.

    When ``mark_job_received`` is True, also sets ``estimates.job_received`` to True (Estimates
    list **Job Received** action).

    The inserted job row uses ``status`` = :data:`JOB_STATUS_AFTER_ESTIMATE_CONVERSION` so it is
    immediately valid for costing / PO workflows (standalone creates are unchanged).
    """
    eid = str(estimate_id or "").strip()
    if not eid:
        return CreateJobFromEstimateResult(ok=False, message="Invalid estimate id.", error_code="invalid_id")

    row = _fetch_estimate_row_for_create(eid)
    if not row:
        return CreateJobFromEstimateResult(ok=False, message="Estimate not found.", error_code="not_found")

    if _truthy_job_received(row):
        return CreateJobFromEstimateResult(
            ok=False,
            message="This estimate is already marked as job received.",
            error_code="job_received",
        )

    status_raw = row.get("status")
    if not estimate_status_allows_job_creation(str(status_raw)):
        return CreateJobFromEstimateResult(
            ok=False,
            message=(
                f"Creating a job from this estimate is not allowed while status is {status_raw!r}. "
                "Change status to an accepted/customer-approved state first (approved/accepted/awarded/po_received), or relax "
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
    customer_location_id_raw = row.get("customer_location_id") or ej.get("customer_location_id")
    customer_location_id = str(customer_location_id_raw).strip() if customer_location_id_raw else ""
    if not customer_id:
        return CreateJobFromEstimateResult(
            ok=False,
            message="Choose a customer on the estimate before creating a job.",
            error_code="no_customer",
        )

    cust_row = None
    try:
        from auth import current_role as _cust_role

        if _cust_role() in {"admin", "estimator"}:
            crows = fetch_by_match_admin("customers", {"id": customer_id}, columns="customer_name", limit=1)
            cust_row = crows[0] if crows else None
    except Exception:
        pass
    if not cust_row:
        cust_row = fetch_one("customers", {"id": customer_id}, columns="customer_name")
    customer_name = str((cust_row or {}).get("customer_name") or "").strip()

    short_name = estimate_description_value(row)
    if short_name:
        job_name = short_name[:500]
    else:
        job_name = _fallback_job_name(row, ej, customer_name).strip() or "Awarded job"

    _, has_job_number_column = fetch_jobs_for_job_database(limit=1, admin_read=True)

    awarded = row.get("proposal_total")
    if awarded is None:
        awarded = row.get("final_bid")
    try:
        awarded_f = float(awarded or 0)
    except (TypeError, ValueError):
        awarded_f = 0.0

    site_loc = _location_text_from_customer_location(customer_location_id) if customer_location_id else ""
    merged_location = site_loc or _safe_location(ej)

    payload: dict[str, Any] = {
        "customer_id": customer_id,
        "job_name": job_name,
        "location": merged_location,
        # Estimate-converted jobs start as Awarded so they are ready for costing (not Draft).
        "status": JOB_STATUS_AFTER_ESTIMATE_CONVERSION,
        "estimate_id": eid,
        "source_type": JOB_SOURCE_TYPE_ESTIMATE,
        "project_manager": "",
        "supervisor": "",
        "start_date": None,
        "target_completion_date": None,
        "completed_date": None,
        "awarded_amount": awarded_f,
        "notes": _build_job_notes(row, ej),
    }
    if _jobs_has_customer_contact_column():
        cc = row.get("customer_contact_id") or ej.get("customer_contact_id")
        if cc:
            payload["customer_contact_id"] = str(cc)

    if _jobs_has_customer_location_column():
        payload["customer_location_id"] = customer_location_id or None

    proposed_jn = ""
    inserted: dict[str, Any] | None = None
    skip_insert = False

    if has_job_number_column:
        qraw = str(row.get("quote_number") or ej.get("quote_number") or "").strip()
        proposed_jn = estimate_quote_to_job_number(qraw)
        if not proposed_jn:
            proposed_jn = str(next_job_number()).strip()
        payload["job_number"] = proposed_jn

        hits = fetch_by_match_admin(
            "jobs",
            {"job_number": proposed_jn},
            columns="id,job_number,job_name,estimate_id,customer_id",
            limit=10,
        )
        if hits:
            hit0 = hits[0]
            hest = str(hit0.get("estimate_id") or "").strip()
            if hest == eid:
                inserted = dict(hit0)
                skip_insert = True
            else:
                return CreateJobFromEstimateResult(
                    ok=False,
                    message=(
                        f"Job number {proposed_jn!r} is already in use by another job. "
                        "Resolve the conflict or adjust the estimate quote number."
                    ),
                    error_code="job_number_taken",
                    job=hit0,
                )

    if not skip_insert:
        try:
            inserted = insert_row_admin("jobs", payload)
        except Exception as exc:
            return CreateJobFromEstimateResult(
                ok=False,
                message=f"Could not create job: {exc}",
                error_code="insert_failed",
            )

    if not inserted:
        return CreateJobFromEstimateResult(ok=False, message="Job insert returned no row.", error_code="insert_failed")

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
    if mark_job_received:
        est_update["job_received"] = True
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
    if skip_insert:
        msg = f"Using existing job {jn or new_id} linked to this estimate."
    else:
        msg = (
            f"Created job {jn or new_id} and linked it to this estimate."
            if jn
            else f"Created job and linked it to this estimate ({new_id})."
        )
    if mark_job_received:
        msg += " Estimate marked as job received."
    return CreateJobFromEstimateResult(ok=True, message=msg, job=inserted)
