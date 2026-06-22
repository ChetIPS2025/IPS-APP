"""Estimate ↔ job approval workflow: auto-create pending jobs and approve linked jobs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, FrozenSet

try:
    from app.services.job_from_estimate import (
        CreateJobFromEstimateResult,
        _JOB_COLLISION_COLUMNS,
        _as_json_dict,
        _build_job_notes,
        _existing_job_for_estimate,
        _fetch_estimate_row_for_create,
        _fallback_job_name,
        _jobs_has_customer_contact_column,
        _jobs_has_customer_location_column,
        _location_text_from_customer_location,
        _normalize_job_number_key,
        _patch_estimate_row,
        _resolve_customer_id_for_estimate,
        _safe_location,
        estimate_quote_to_job_number,
        get_estimate_description,
        fetch_jobs_by_exact_job_number,
        job_number_conflict_is_reclaimable,
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
        job_number_conflict_is_reclaimable,
        renumber_estimate_quote_for_job_collision,
        resolve_job_number_collisions,
        _JOB_COLLISION_COLUMNS,
        _normalize_job_number_key,
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
JOB_AWARD_SYNC_STATUSES: FrozenSet[str] = frozenset({"Awarded", "Active"})

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


def estimate_visible_in_draft_view(row: dict[str, Any]) -> bool:
    return _norm_status(row.get("status")) == "draft"


def estimate_visible_in_sent_view(row: dict[str, Any]) -> bool:
    return _norm_status(row.get("status")) in {"sent", "submitted"}


def estimate_visible_in_archived_view(row: dict[str, Any]) -> bool:
    return row.get("archived_from_estimates") is True


def can_revise_approved_estimates(role: str | None) -> bool:
    """Same roles that may approve estimates may revise approved pricing/details."""
    return can_approve_estimates(role)


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


def _fetch_job_row(job_id: str) -> dict[str, Any] | None:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    rows = fetch_by_match_admin(
        "jobs",
        {"id": jid},
        columns=_JOB_COLLISION_COLUMNS,
        limit=1,
    )
    return rows[0] if rows else None


def _linked_estimate_row_for_job(job: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve an existing estimate linked by ``jobs.estimate_id`` or ``estimates.job_id``."""
    jid = str(job.get("id") or "").strip()
    eid = str(job.get("estimate_id") or "").strip()
    if eid:
        row = _fetch_estimate_row_for_create(eid)
        if row:
            return row
    if jid:
        rows = fetch_by_match_admin("estimates", {"job_id": jid}, limit=5)
        if rows:
            return rows[0]
    return None


def _estimate_financial_totals(row: dict[str, Any]) -> tuple[float, float]:
    """Return (customer_price, internal_cost) for a linked estimate row."""
    try:
        from app.services.estimate_revision_service import _estimate_customer_price
    except ImportError:
        from services.estimate_revision_service import _estimate_customer_price  # type: ignore

    customer_price = float(_estimate_customer_price(row) or 0)
    internal_cost = 0.0
    eid = str(row.get("id") or "").strip()
    if eid:
        try:
            from app.services.estimate_costing_service import calculate_estimate_totals
        except ImportError:
            from services.estimate_costing_service import calculate_estimate_totals  # type: ignore
        try:
            totals = calculate_estimate_totals(eid)
            internal_cost = float(totals.get("total_cost") or 0)
        except Exception:
            pass
    return customer_price, internal_cost


def _sync_linked_job_row(
    *,
    estimate_id: str,
    estimate_row: dict[str, Any],
    job: dict[str, Any],
    proposed_jn: str = "",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Ensure an existing/reused job is linked to the estimate and shows as Estimate Pending
    until the estimate is approved.
    """
    jid = str(job.get("id") or "").strip()
    if not jid:
        return job
    updates: dict[str, Any] = {}
    if str(job.get("estimate_id") or "").strip() != estimate_id:
        updates["estimate_id"] = estimate_id
    if not estimate_status_already_approved(estimate_row.get("status")):
        if _norm_status(job.get("status")) != _norm_status(JOB_STATUS_ESTIMATE_PENDING):
            updates["status"] = JOB_STATUS_ESTIMATE_PENDING
    proposed = str(proposed_jn or "").strip()
    if proposed:
        cur_key = _normalize_job_number_key(job.get("job_number"))
        new_key = _normalize_job_number_key(proposed)
        if cur_key != new_key and (
            not cur_key
            or job_number_conflict_is_reclaimable(job, estimate_id=estimate_id)
            or str(job.get("estimate_id") or "").strip() == estimate_id
        ):
            updates["job_number"] = proposed
    src = payload or {}
    quote_number = str(
        estimate_row.get("quote_number")
        or estimate_row.get("estimate_number")
        or src.get("source_estimate_number")
        or ""
    ).strip()
    if quote_number:
        updates.setdefault("source_estimate_number", quote_number[:120])
    for key in ("job_name", "location", "notes"):
        val = src.get(key)
        if val not in (None, ""):
            updates[key] = val
    if src.get("awarded_amount") is not None:
        updates["awarded_amount"] = src.get("awarded_amount")
    if updates:
        try:
            update_rows_admin("jobs", updates, {"id": jid})
            job = {**job, **updates}
        except Exception as exc:
            _LOG.warning("Could not sync linked job %s for estimate %s: %s", jid, estimate_id, exc)
    refreshed = _fetch_job_row(jid)
    return refreshed or job


def _link_estimate_to_job(estimate_id: str, job: dict[str, Any], row: dict[str, Any]) -> None:
    jid = str(job.get("id") or "").strip()
    if not jid:
        return
    ej = _as_json_dict(row.get("estimate_json"))
    ej["job_id"] = jid
    patch: dict[str, Any] = {
        "job_id": jid,
        "estimate_json": ej,
        "updated_at": _utc_now_iso(),
    }
    _patch_estimate_row(estimate_id, patch)


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

    _, has_job_number_column = fetch_jobs_for_job_database(limit=1, admin_read=True)
    ej = _as_json_dict(row.get("estimate_json"))
    proposed_jn = (
        _resolve_job_number(row, ej, has_job_number_column=has_job_number_column)
        if has_job_number_column
        else ""
    )

    existing = _existing_job_for_estimate(eid, row)
    if existing:
        synced = _sync_linked_job_row(
            estimate_id=eid,
            estimate_row=row,
            job=existing,
            proposed_jn=proposed_jn,
        )
        _link_estimate_to_job(eid, synced, row)
        jn = job_number_display(synced.get("job_number"))
        jid = str(synced.get("id") or "")
        return CreateJobFromEstimateResult(
            ok=True,
            message=f"Linked to existing job {jn or jid}.",
            job=synced,
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

    customer_location_id = str(row.get("customer_location_id") or ej.get("customer_location_id") or "").strip()
    site_loc = _location_text_from_customer_location(customer_location_id) if customer_location_id else ""
    merged_location = site_loc or _safe_location(ej)

    cust_row = fetch_by_match_admin("customers", {"id": customer_id}, columns="customer_name", limit=1)
    customer_name = str((cust_row[0] if cust_row else {}).get("customer_name") or row.get("customer_name") or "").strip()

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
                    inserted = _sync_linked_job_row(
                        estimate_id=eid,
                        estimate_row=row,
                        job=dict(collision_job or hits[0]),
                        proposed_jn=proposed_jn,
                        payload=payload,
                    )
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

    try:
        _link_estimate_to_job(eid, inserted, row)
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


def ensure_linked_pending_job_for_estimate(
    estimate_id: str,
    *,
    estimate_row: dict[str, Any] | None = None,
) -> CreateJobFromEstimateResult:
    """
    Ensure the estimate has a linked job in Estimate Pending status (create or sync).

    Safe to call after insert or update when the estimate has a customer.
    """
    return create_pending_job_from_estimate(estimate_id, estimate_row=estimate_row)


def auto_create_linked_job_after_estimate_insert(
    estimate_id: str,
    *,
    estimate_row: dict[str, Any] | None = None,
) -> CreateJobFromEstimateResult:
    """Called after a new estimate row is inserted."""
    return ensure_linked_pending_job_for_estimate(estimate_id, estimate_row=estimate_row)


def approve_estimate_and_sync_job(
    estimate_id: str,
    *,
    approved_by: str | None = None,
) -> ApproveEstimateResult:
    """Approve estimate and sync its linked job (create job first if missing)."""
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

    sync = sync_estimate_job_links_and_financials(
        estimate_id=eid,
        job_id=jid,
        estimate_row=row,
        job_row=job,
        approved_by=actor,
        job_status=JOB_STATUS_AFTER_ESTIMATE_APPROVAL,
        persist_job=True,
        estimate_activity=("Estimate approved", f"Job {job_number_display(job.get('job_number'))}"),
        job_activity=("Job approved from estimate", str(row.get("quote_number") or "")),
    )
    if not sync.ok:
        return ApproveEstimateResult(
            ok=False,
            message=sync.error or "Could not sync estimate and job.",
            error_code="sync_failed",
            job=job,
        )

    data = sync.data if isinstance(sync.data, dict) else {}
    updated_est = data.get("estimate") or _fetch_estimate_row_for_create(eid)
    updated_job = data.get("job") or job
    jn = job_number_display(updated_job.get("job_number") if isinstance(updated_job, dict) else None)
    return ApproveEstimateResult(
        ok=True,
        message=f"Estimate approved and linked job {jn or jid} activated.",
        estimate=updated_est,
        job=updated_job,
    )


def sync_estimate_job_links_and_financials(
    *,
    estimate_id: str = "",
    job_id: str = "",
    estimate_row: dict[str, Any] | None = None,
    job_row: dict[str, Any] | None = None,
    approved_by: str | None = None,
    job_status: str | None = None,
    persist_job: bool = False,
    skip_if_no_estimate: bool = False,
    skip_if_no_job: bool = False,
    estimate_activity: tuple[str, str] | None = None,
    job_activity: tuple[str, str] | None = None,
) -> ServiceResult:
    """
    Shared sync: approve linked estimate (when eligible), ensure bidirectional links,
    and align job financial fields with estimate totals.

    Returns ``job_patch`` in ``data`` for callers that merge job updates (Jobs page award flow).
    When ``persist_job`` is True, writes the job patch immediately (Estimates page approve flow).
    """
    eid = str(estimate_id or "").strip()
    jid = str(job_id or "").strip()
    est = estimate_row
    job = job_row

    if est is None and eid:
        est = _fetch_estimate_row_for_create(eid)
    if job is None and jid:
        job = _fetch_job_row(jid)
    if est is None and job:
        est = _linked_estimate_row_for_job(job)
        if est and not eid:
            eid = str(est.get("id") or "").strip()
    if job is None and est and eid:
        job = _existing_job_for_estimate(eid, est)
        if job and not jid:
            jid = str(job.get("id") or "").strip()

    if skip_if_no_estimate and not est:
        return ServiceResult(ok=True, data={"skipped": True, "reason": "no_linked_estimate"})
    if skip_if_no_job and not job:
        return ServiceResult(ok=True, data={"skipped": True, "reason": "no_linked_job"})

    if not est:
        return ServiceResult(ok=False, error="Estimate not found.")
    if not job:
        return ServiceResult(ok=False, error="Linked job not found.")

    if not eid:
        eid = str(est.get("id") or "").strip()
    if not jid:
        jid = str(job.get("id") or "").strip()
    if not eid or not jid:
        return ServiceResult(ok=False, error="Estimate and job must both have ids.")

    if _norm_status(est.get("status")) in ESTIMATE_STATUSES_TERMINAL_NEGATIVE:
        return ServiceResult(
            ok=False,
            error=f"Linked estimate cannot be approved (status {est.get('status')!r}).",
        )

    actor = str(approved_by or current_user_profile_id() or "").strip() or None
    now = _utc_now_iso()
    customer_price, internal_cost = _estimate_financial_totals(est)

    already_approved = (
        estimate_status_already_approved(est.get("status"))
        or est.get("archived_from_estimates") is True
    )

    if not already_approved:
        if not estimate_status_approvable(est.get("status")):
            return ServiceResult(
                ok=False,
                error=f"Linked estimate status {est.get('status')!r} is not eligible for approval.",
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
            return ServiceResult(ok=False, error=f"Could not approve linked estimate: {exc}")
        if estimate_activity:
            _log_estimate_activity(eid, estimate_activity[0], details=estimate_activity[1], actor_id=actor)
        est = _fetch_estimate_row_for_create(eid) or est

    if str(est.get("job_id") or "").strip() != jid:
        _link_estimate_to_job(eid, job, est)

    job_patch: dict[str, Any] = {
        "estimate_id": eid,
        "updated_at": now,
    }
    if job_status:
        job_patch["status"] = job_status
    if customer_price > 0:
        job_patch["awarded_amount"] = round(customer_price, 2)
    if internal_cost > 0:
        job_patch["estimated_cost"] = round(internal_cost, 2)
    try:
        from app.services.job_financial_ui import apply_projected_financials_to_job_payload
    except ImportError:
        from services.job_financial_ui import apply_projected_financials_to_job_payload  # type: ignore
    projected = apply_projected_financials_to_job_payload({**job, **job_patch})
    job_patch["projected_gross_profit"] = projected["projected_gross_profit"]
    job_patch["projected_margin_pct"] = projected["projected_margin_pct"]
    if actor:
        job_patch.setdefault("approved_by", actor)
    job_patch.setdefault("approved_at", now)

    filtered_patch = filter_payload_to_table("jobs", job_patch)
    if persist_job and filtered_patch:
        try:
            update_rows_admin("jobs", filtered_patch, {"id": jid})
        except Exception as exc:
            return ServiceResult(ok=False, error=f"Could not update linked job: {exc}")

    quote = str(est.get("quote_number") or est.get("estimate_number") or "").strip()
    if job_activity:
        action, details = job_activity[0], (job_activity[1] if len(job_activity) > 1 else "") or quote
        _log_job_activity(jid, action, details=details, actor_id=actor)
    elif quote:
        _log_job_activity(jid, "Job synced with linked estimate", details=quote, actor_id=actor)

    updated_est = _fetch_estimate_row_for_create(eid) or est
    updated_job_rows = fetch_by_match_admin("jobs", {"id": jid}, limit=1)
    updated_job = updated_job_rows[0] if updated_job_rows else {**job, **filtered_patch}

    return ServiceResult(
        ok=True,
        data={
            "estimate_id": eid,
            "job_id": jid,
            "estimate": updated_est,
            "job": updated_job,
            "job_patch": filtered_patch,
            "customer_price": customer_price,
            "internal_cost": internal_cost,
            "estimate_approved": not already_approved,
            "quote_number": quote,
        },
    )


def award_job_and_sync_estimate(
    job_id: str,
    *,
    new_status: str,
    approved_by: str | None = None,
    job_row: dict[str, Any] | None = None,
) -> ServiceResult:
    """
    When a job is set to Awarded/Active, approve its linked estimate (if any) and return
    job column updates for the caller to merge. Preserves Awarded vs Active from the Jobs UI.
    """
    try:
        from app.services.jobs_service import normalize_job_status
    except ImportError:
        from services.jobs_service import normalize_job_status  # type: ignore

    status = normalize_job_status(new_status)
    if status not in JOB_AWARD_SYNC_STATUSES:
        return ServiceResult(ok=True, data={"skipped": True, "reason": "status_not_awarded"})

    jid = str(job_id or "").strip()
    job = job_row or _fetch_job_row(jid)
    if not job:
        return ServiceResult(ok=False, error="Job not found.")
    if not jid:
        jid = str(job.get("id") or "").strip()

    jn = job_number_display(job.get("job_number"))
    return sync_estimate_job_links_and_financials(
        job_id=jid,
        job_row=job,
        approved_by=approved_by,
        persist_job=False,
        skip_if_no_estimate=True,
        estimate_activity=("Estimate approved from job", f"Job {jn or jid} set to {status}"),
        job_activity=("Job synced with linked estimate", ""),
    )


# Backward-compatible aliases
approve_estimate_and_job = approve_estimate_and_sync_job
sync_linked_estimate_on_job_award = award_job_and_sync_estimate


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


def backfill_estimate_missing_linked_job(row: dict[str, Any]) -> dict[str, Any] | None:
    """
    Create or re-link a pending job when an estimate has a customer but no job_id.

    Safe for list-load repair of rows saved before auto-link ran or blocked by stale J numbers.
    """
    eid = str(row.get("id") or "").strip()
    if not eid or str(row.get("job_id") or "").strip():
        return None
    if not str(row.get("customer_id") or "").strip():
        return None
    if not estimate_status_approvable(row.get("status")):
        return None
    quote = str(row.get("quote_number") or row.get("estimate_number") or "").strip()
    if not quote:
        return None
    result = ensure_linked_pending_job_for_estimate(eid, estimate_row=row)
    if not result.ok or not result.job:
        _LOG.info(
            "Linked job backfill skipped for estimate %s (%s): %s",
            eid,
            quote,
            result.message,
        )
        return None
    return result.job


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
        if not job:
            repaired = backfill_estimate_missing_linked_job(r)
            if repaired:
                job = repaired
                jid = str(repaired.get("id") or "").strip()
                if jid:
                    by_id[jid] = repaired
                    by_est[str(r.get("id") or "")] = repaired
                    r["job_id"] = jid
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
