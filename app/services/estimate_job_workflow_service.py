"""Estimate ↔ job approval workflow: auto-create pending jobs and approve linked jobs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, FrozenSet

try:
    from app.services.job_from_estimate import (
        CreateJobFromEstimateResult,
        _as_json_dict,
        _build_job_notes,
        _existing_job_for_estimate,
        _fetch_estimate_row_for_create,
        _fallback_job_name,
        _jobs_has_customer_contact_column,
        _jobs_has_customer_location_column,
        _location_text_from_customer_location,
        _patch_estimate_row,
        _resolve_customer_id_for_estimate,
        _safe_location,
        estimate_quote_to_job_number,
        get_estimate_description,
        fetch_jobs_by_exact_job_number,
        renumber_estimate_quote_for_job_collision,
        resolve_job_number_collisions,
    )
    from app.services.job_schema import fetch_jobs_for_job_database
    from app.services.job_service import job_number_display, next_job_number
    from app.services.repository import ServiceResult, filter_payload_to_table, update_row
except ImportError:
    from services.job_from_estimate import (  # type: ignore
        CreateJobFromEstimateResult,
        _as_json_dict,
        _build_job_notes,
        _existing_job_for_estimate,
        _fetch_estimate_row_for_create,
        _fallback_job_name,
        _jobs_has_customer_contact_column,
        _jobs_has_customer_location_column,
        _location_text_from_customer_location,
        _patch_estimate_row,
        _resolve_customer_id_for_estimate,
        _safe_location,
        estimate_quote_to_job_number,
        get_estimate_description,
        fetch_jobs_by_exact_job_number,
        renumber_estimate_quote_for_job_collision,
        resolve_job_number_collisions,
    )
    from services.job_schema import fetch_jobs_for_job_database  # type: ignore
    from services.job_service import job_number_display, next_job_number  # type: ignore
    from services.repository import ServiceResult, filter_payload_to_table, update_row  # type: ignore

try:
    from db import delete_rows_admin, fetch_by_match_admin, fetch_one, insert_row_admin, update_rows_admin
except ImportError:
    from app.db import (  # type: ignore
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_one,
        insert_row_admin,
        update_rows_admin,
    )

_LOG = logging.getLogger(__name__)

JOB_STATUS_ESTIMATE_PENDING = "Estimate Pending"
JOB_STATUS_AFTER_ESTIMATE_APPROVAL = "Active"

ESTIMATE_STATUSES_APPROVABLE: FrozenSet[str] = frozenset({"draft", "pending", "sent"})
ESTIMATE_STATUSES_ALREADY_APPROVED: FrozenSet[str] = frozenset(
    {"approved", "awarded", "accepted", "po_received"}
)
ESTIMATE_STATUSES_TERMINAL_NEGATIVE: FrozenSet[str] = frozenset(
    {"rejected", "cancelled", "canceled", "expired"}
)

ESTIMATE_VIEW_ACTIVE_STATUSES: FrozenSet[str] = frozenset({"draft", "pending", "sent"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_status(status: object) -> str:
    return str(status or "").strip().lower().replace("_", " ")


def estimate_status_approvable(status: object) -> bool:
    return _norm_status(status) in ESTIMATE_STATUSES_APPROVABLE


def estimate_status_already_approved(status: object) -> bool:
    s = _norm_status(status)
    return s in ESTIMATE_STATUSES_ALREADY_APPROVED


def estimate_is_archived(row: dict[str, Any]) -> bool:
    if row.get("archived_from_estimates") is True:
        return True
    return estimate_status_already_approved(row.get("status"))


def estimate_visible_in_active_view(row: dict[str, Any]) -> bool:
    if estimate_is_archived(row):
        return False
    return _norm_status(row.get("status")) in ESTIMATE_VIEW_ACTIVE_STATUSES


def estimate_visible_in_approved_view(row: dict[str, Any]) -> bool:
    if row.get("archived_from_estimates") is True:
        return True
    s = _norm_status(row.get("status"))
    return s in ESTIMATE_STATUSES_ALREADY_APPROVED


def estimate_visible_in_rejected_view(row: dict[str, Any]) -> bool:
    return _norm_status(row.get("status")) in ESTIMATE_STATUSES_TERMINAL_NEGATIVE


def can_approve_estimates(role: str | None) -> bool:
    r = str(role or "").strip().lower()
    return r in {"admin", "supervisor", "manager", "project manager", "pm", "estimator"}


def current_user_profile_id() -> str | None:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    try:
        prof = current_profile() or {}
        uid = str(prof.get("id") or prof.get("user_id") or "").strip()
        return uid or None
    except Exception:
        return None


def _log_estimate_activity(estimate_id: str, action: str, *, details: str = "", actor_id: str | None = None) -> None:
    payload = {
        "estimate_id": estimate_id,
        "activity_type": action[:200],
        "description": details[:4000] or action[:200],
        "created_by": actor_id,
        "created_at": _utc_now_iso(),
    }
    try:
        filtered = filter_payload_to_table("estimate_activity_log", payload)
        if filtered:
            insert_row_admin("estimate_activity_log", filtered)
    except Exception as exc:
        _LOG.debug("estimate_activity_log skipped: %s", exc)


def _log_job_activity(job_id: str, action: str, *, details: str = "", actor_id: str | None = None) -> None:
    payload = {
        "job_id": job_id,
        "activity_type": action[:200],
        "description": details[:4000] or action[:200],
        "created_by": actor_id,
        "created_at": _utc_now_iso(),
    }
    try:
        filtered = filter_payload_to_table("job_activity_log", payload)
        if filtered:
            insert_row_admin("job_activity_log", filtered)
    except Exception as exc:
        _LOG.debug("job_activity_log skipped: %s", exc)


def _job_name_from_estimate(row: dict[str, Any], ej: dict[str, Any], customer_name: str) -> str:
    project = str(row.get("project_name") or "").strip()
    if project:
        return project[:500]
    short = get_estimate_description(row)
    if short:
        return short[:500]
    return _fallback_job_name(row, ej, customer_name).strip() or "Estimate job"


def _resolve_job_number(row: dict[str, Any], ej: dict[str, Any], *, has_job_number_column: bool) -> str:
    if not has_job_number_column:
        return ""
    qraw = str(row.get("quote_number") or row.get("estimate_number") or ej.get("quote_number") or "").strip()
    proposed = estimate_quote_to_job_number(qraw)
    if proposed:
        return proposed
    return str(next_job_number()).strip()


@dataclass
class ApproveEstimateResult:
    ok: bool
    message: str
    estimate: dict[str, Any] | None = None
    job: dict[str, Any] | None = None
    error_code: str | None = None


def create_pending_job_from_estimate(
    estimate_id: str,
    *,
    estimate_row: dict[str, Any] | None = None,
) -> CreateJobFromEstimateResult:
    """Create a draft/estimate-pending job linked to the estimate (no approval required)."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return CreateJobFromEstimateResult(ok=False, message="Invalid estimate id.", error_code="invalid_id")

    row = estimate_row or _fetch_estimate_row_for_create(eid)
    if not row:
        return CreateJobFromEstimateResult(ok=False, message="Estimate not found.", error_code="not_found")

    existing = _existing_job_for_estimate(eid, row)
    if existing:
        jid = str(existing.get("id") or "")
        if jid and not str(row.get("job_id") or "").strip():
            _patch_estimate_row(eid, {"job_id": jid})
        jn = job_number_display(existing.get("job_number"))
        return CreateJobFromEstimateResult(
            ok=True,
            message=f"Linked to existing job {jn or jid}.",
            job=existing,
            error_code="duplicate",
        )

    customer_id = _resolve_customer_id_for_estimate(row)
    if not customer_id:
        return CreateJobFromEstimateResult(
            ok=False,
            message="Choose a customer on the estimate before creating a linked job.",
            error_code="no_customer",
        )

    if not str(row.get("customer_id") or "").strip():
        _patch_estimate_row(eid, {"customer_id": customer_id})

    ej = _as_json_dict(row.get("estimate_json"))
    customer_location_id = str(row.get("customer_location_id") or ej.get("customer_location_id") or "").strip()
    site_loc = _location_text_from_customer_location(customer_location_id) if customer_location_id else ""
    merged_location = site_loc or _safe_location(ej)

    cust_row = fetch_by_match_admin("customers", {"id": customer_id}, columns="customer_name", limit=1)
    customer_name = str((cust_row[0] if cust_row else {}).get("customer_name") or row.get("customer_name") or "").strip()

    _, has_job_number_column = fetch_jobs_for_job_database(limit=1, admin_read=True)
    quote_number = str(row.get("quote_number") or row.get("estimate_number") or ej.get("quote_number") or "").strip()

    inserted: dict[str, Any] | None = None
    payload: dict[str, Any] = {
        "customer_id": customer_id,
        "job_name": _job_name_from_estimate(row, ej, customer_name),
        "location": merged_location,
        "status": JOB_STATUS_ESTIMATE_PENDING,
        "estimate_id": eid,
        "project_manager": "",
        "supervisor": "",
        "start_date": None,
        "target_completion_date": None,
        "completed_date": None,
        "awarded_amount": float(row.get("customer_price") or row.get("total") or 0),
        "notes": _build_job_notes(row, ej),
        "source_estimate_number": quote_number[:120],
    }
    if _jobs_has_customer_contact_column():
        cc = row.get("customer_contact_id") or ej.get("customer_contact_id")
        if cc:
            payload["customer_contact_id"] = str(cc)
    if _jobs_has_customer_location_column():
        payload["customer_location_id"] = customer_location_id or None

    if has_job_number_column:
        proposed_jn = _resolve_job_number(row, ej, has_job_number_column=True)
        if proposed_jn:
            hits = fetch_jobs_by_exact_job_number(proposed_jn)
            linked_job_id = str(row.get("job_id") or "").strip() or None
            if hits:
                outcome, collision_job = resolve_job_number_collisions(
                    hits,
                    estimate_id=eid,
                    proposed_jn=proposed_jn,
                    linked_job_id=linked_job_id,
                )
                if outcome == "reuse":
                    inserted = dict(collision_job or hits[0])
                elif outcome == "blocked":
                    pair = renumber_estimate_quote_for_job_collision(
                        eid,
                        quote_number=quote_number,
                        exclude_job_id=str((collision_job or hits[0]).get("id") or "").strip() or None,
                    )
                    if not pair:
                        hit = collision_job or hits[0]
                        return CreateJobFromEstimateResult(
                            ok=False,
                            message=f"Job number {proposed_jn!r} is already in use.",
                            error_code="job_number_taken",
                            job=hit,
                        )
                    quote_number, proposed_jn = pair
                    payload["job_number"] = proposed_jn
                    payload["source_estimate_number"] = quote_number[:120]
                    row["quote_number"] = quote_number
                    ej["quote_number"] = quote_number
                    try:
                        inserted = insert_row_admin("jobs", payload)
                    except Exception as exc:
                        return CreateJobFromEstimateResult(
                            ok=False,
                            message=f"Could not create linked job: {exc}",
                            error_code="insert_failed",
                        )
                else:
                    payload["job_number"] = proposed_jn
                    try:
                        inserted = insert_row_admin("jobs", payload)
                    except Exception as exc:
                        return CreateJobFromEstimateResult(
                            ok=False,
                            message=f"Could not create linked job: {exc}",
                            error_code="insert_failed",
                        )
            else:
                payload["job_number"] = proposed_jn
                try:
                    inserted = insert_row_admin("jobs", payload)
                except Exception as exc:
                    return CreateJobFromEstimateResult(
                        ok=False,
                        message=f"Could not create linked job: {exc}",
                        error_code="insert_failed",
                    )
        else:
            try:
                inserted = insert_row_admin("jobs", payload)
            except Exception as exc:
                return CreateJobFromEstimateResult(
                    ok=False,
                    message=f"Could not create linked job: {exc}",
                    error_code="insert_failed",
                )
    else:
        try:
            inserted = insert_row_admin("jobs", payload)
        except Exception as exc:
            return CreateJobFromEstimateResult(
                ok=False,
                message=f"Could not create linked job: {exc}",
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
        "updated_at": _utc_now_iso(),
    }
    try:
        _patch_estimate_row(eid, est_update)
    except Exception as exc:
        return CreateJobFromEstimateResult(
            ok=False,
            message=f"Job created but linking to estimate failed: {exc}",
            job=inserted,
            error_code="link_failed",
        )

    jn = job_number_display(inserted.get("job_number"))
    actor = current_user_profile_id()
    _log_estimate_activity(eid, "Linked job auto-created", details=jn or new_id, actor_id=actor)
    _log_job_activity(new_id, "Job created from estimate", details=quote_number, actor_id=actor)

    msg = f"Created linked job {jn or new_id} (Estimate Pending)."
    return CreateJobFromEstimateResult(ok=True, message=msg, job=inserted)


def auto_create_linked_job_after_estimate_insert(
    estimate_id: str,
    *,
    estimate_row: dict[str, Any] | None = None,
) -> CreateJobFromEstimateResult:
    """Called after a new estimate row is inserted."""
    row = estimate_row
    if row is None:
        row = _fetch_estimate_row_for_create(estimate_id)
    if row and str(row.get("job_id") or "").strip():
        return CreateJobFromEstimateResult(ok=True, message="Estimate already has a linked job.")
    return create_pending_job_from_estimate(estimate_id, estimate_row=row)


def approve_estimate_and_job(
    estimate_id: str,
    *,
    approved_by: str | None = None,
) -> ApproveEstimateResult:
    """Approve estimate and activate its linked job (create job first if missing)."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return ApproveEstimateResult(ok=False, message="Invalid estimate id.", error_code="invalid_id")

    row = _fetch_estimate_row_for_create(eid)
    if not row:
        return ApproveEstimateResult(ok=False, message="Estimate not found.", error_code="not_found")

    status = _norm_status(row.get("status"))
    if estimate_status_already_approved(row.get("status")) or row.get("archived_from_estimates") is True:
        job = _existing_job_for_estimate(eid, row)
        return ApproveEstimateResult(
            ok=True,
            message="This estimate is already approved.",
            estimate=row,
            job=job,
            error_code="already_approved",
        )

    if status in ESTIMATE_STATUSES_TERMINAL_NEGATIVE:
        return ApproveEstimateResult(
            ok=False,
            message=f"Cannot approve an estimate with status {row.get('status')!r}.",
            error_code="bad_status",
        )

    if not estimate_status_approvable(row.get("status")):
        return ApproveEstimateResult(
            ok=False,
            message=f"Estimate status {row.get('status')!r} is not eligible for approval.",
            error_code="bad_status",
        )

    actor = str(approved_by or current_user_profile_id() or "").strip() or None
    now = _utc_now_iso()

    job = _existing_job_for_estimate(eid, row)
    if not job:
        created = create_pending_job_from_estimate(eid, estimate_row=row)
        if not created.ok or not created.job:
            return ApproveEstimateResult(
                ok=False,
                message=created.message or "Could not create linked job for approval.",
                error_code=created.error_code or "job_create_failed",
            )
        job = created.job
        row = _fetch_estimate_row_for_create(eid) or row

    jid = str(job.get("id") or "")
    if not jid:
        return ApproveEstimateResult(ok=False, message="Linked job is missing an id.", error_code="no_job")

    job_update = filter_payload_to_table(
        "jobs",
        {
            "status": JOB_STATUS_AFTER_ESTIMATE_APPROVAL,
            "estimate_id": eid,
            "approved_at": now,
            "approved_by": actor,
            "updated_at": now,
        },
    )
    try:
        update_rows_admin("jobs", job_update, {"id": jid})
    except Exception as exc:
        return ApproveEstimateResult(
            ok=False,
            message=f"Could not update linked job: {exc}",
            error_code="job_update_failed",
            job=job,
        )

    est_update = filter_payload_to_table(
        "estimates",
        {
            "status": "Approved",
            "job_id": jid,
            "approved_at": now,
            "approved_by": actor,
            "converted_to_job_at": now,
            "archived_from_estimates": True,
            "updated_at": now,
        },
    )
    try:
        update_rows_admin("estimates", est_update, {"id": eid})
    except Exception as exc:
        return ApproveEstimateResult(
            ok=False,
            message=f"Job updated but estimate approval failed: {exc}",
            error_code="estimate_update_failed",
            job=job,
        )

    updated_est = _fetch_estimate_row_for_create(eid)
    updated_job = fetch_by_match_admin("jobs", {"id": jid}, limit=1)
    job_row = updated_job[0] if updated_job else job

    _log_estimate_activity(eid, "Estimate approved", details=f"Job {job_number_display(job_row.get('job_number'))}", actor_id=actor)
    _log_job_activity(jid, "Job approved from estimate", details=str(row.get("quote_number") or ""), actor_id=actor)

    jn = job_number_display(job_row.get("job_number"))
    return ApproveEstimateResult(
        ok=True,
        message=f"Estimate approved and linked job {jn or jid} activated.",
        estimate=updated_est,
        job=job_row,
    )


def rollback_estimate_if_job_link_failed(estimate_id: str) -> None:
    """Best-effort cleanup when estimate was inserted but job link failed."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    try:
        delete_rows_admin("estimates", {"id": eid})
    except Exception as exc:
        _LOG.warning("Could not rollback estimate %s after job failure: %s", eid, exc)


def _linked_job_title_sync_payload(project_name: str) -> dict[str, Any]:
    """Job update fields for estimate project renames — never touch job_number."""
    name = str(project_name or "").strip()
    if not name:
        return {}
    try:
        from app.services.repository import table_column_names
    except ImportError:
        from services.repository import table_column_names  # type: ignore

    cols = table_column_names("jobs")
    allowed = ("job_name", "project_name", "name")
    raw: dict[str, Any] = {"job_name": name}
    if not cols or "project_name" in cols:
        raw["project_name"] = name
    if not cols or "name" in cols:
        raw["name"] = name
    payload = {k: v for k, v in raw.items() if k in allowed}
    payload = filter_payload_to_table("jobs", payload)
    payload.pop("job_number", None)
    return payload


def _resolve_linked_job_id_for_estimate(
    estimate_id: str,
    *,
    job_id: str | None = None,
) -> str:
    """Resolve the single job row to rename when an estimate project title changes."""
    jid = str(job_id or "").strip()
    if jid:
        return jid
    est = fetch_one("estimates", {"id": estimate_id}, columns="id,job_id") or {}
    jid = str(est.get("job_id") or "").strip()
    if jid:
        return jid
    job = _existing_job_for_estimate(estimate_id, est if isinstance(est, dict) else {})
    return str((job or {}).get("id") or "").strip()


def sync_linked_job_project_from_estimate(
    *,
    estimate_id: str,
    job_id: str | None = None,
    project_name: str,
) -> ServiceResult:
    """Keep linked job title in sync when estimate project name is edited."""
    eid = str(estimate_id or "").strip()
    name = str(project_name or "").strip()
    if not eid or not name:
        return ServiceResult(ok=True)
    jid = _resolve_linked_job_id_for_estimate(eid, job_id=job_id)
    if not jid:
        return ServiceResult(ok=True)
    payload = _linked_job_title_sync_payload(name)
    if not payload:
        return ServiceResult(ok=True)
    result = update_row("jobs", payload, {"id": jid})
    if not result.ok:
        _LOG.warning(
            "sync_linked_job_project_from_estimate failed estimate=%s job=%s: %s",
            eid,
            jid,
            result.error,
        )
    return result


def _linked_job_label(job: dict[str, Any]) -> str:
    for key in ("job_name", "name", "project_name"):
        val = str(job.get(key) or "").strip()
        if val and val != "—":
            return val
    return ""


def enrich_estimates_with_job_numbers(
    rows: list[dict[str, Any]],
    jobs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if jobs is None:
        try:
            from app.db import fetch_table_admin
        except ImportError:
            from db import fetch_table_admin  # type: ignore
        try:
            jobs = list(fetch_table_admin("jobs", limit=10000) or [])
        except Exception:
            jobs = []

    by_id = {str(j.get("id") or ""): j for j in jobs if isinstance(j, dict) and j.get("id")}
    by_est: dict[str, dict[str, Any]] = {}
    for j in jobs:
        if not isinstance(j, dict):
            continue
        est_ref = str(j.get("estimate_id") or "").strip()
        if est_ref:
            by_est[est_ref] = j

    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        jid = str(r.get("job_id") or "").strip()
        job = by_id.get(jid) if jid else None
        if not job:
            job = by_est.get(str(r.get("id") or ""))
        if job:
            jn = job_number_display(job.get("job_number"))
            if jn:
                r["job_number"] = jn
                r["linked_job_number"] = jn
            r.setdefault("linked_job_status", str(job.get("status") or ""))
            r["linked_job"] = job
            job_label = _linked_job_label(job)
            if job_label:
                r["linked_job_name"] = job_label
                desc = str(job.get("description") or job.get("notes") or "").strip()
                if desc and desc != job_label:
                    r["linked_job_description"] = desc
        out.append(r)
    return out
