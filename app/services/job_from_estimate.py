"""
Create a Job Database row from an approved / awarded estimate.

**Architecture:** this is the **estimate → job** conversion path only. The resulting row is
the **costing / work** record (``jobs.id`` / ``job_number``); the estimate stays a quote and
is linked via ``estimate_id``. Time, job costing, and PO expenses should key off ``job_id``.

Quote numbers (``QYY###``) map to ``JYY###`` when a job is linked; see
:func:`quote_number_to_job_number`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
    from services.job_schema import fetch_jobs_for_job_database
    from services.job_service import job_number_display, next_job_number
except ImportError:
    from app.services.job_schema import fetch_jobs_for_job_database  # type: ignore
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
JOB_STATUS_AFTER_ESTIMATE_CONVERSION = "Active"


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


def _patch_estimate_row(estimate_id: str, payload: dict[str, Any]) -> None:
    """Update estimate with only columns present in the live schema."""
    eid = str(estimate_id or "").strip()
    if not eid or not payload:
        return
    try:
        from app.services.repository import filter_payload_to_table

        filtered = filter_payload_to_table("estimates", payload)
    except ImportError:
        from services.repository import filter_payload_to_table  # type: ignore

        filtered = filter_payload_to_table("estimates", payload)
    if not filtered:
        return
    filtered["updated_at"] = datetime.utcnow().isoformat()
    update_rows_admin("estimates", filtered, {"id": eid})


def _resolve_customer_id_for_estimate(row: dict[str, Any]) -> str:
    cid = str(row.get("customer_id") or "").strip()
    if cid:
        return cid
    ej = _as_json_dict(row.get("estimate_json"))
    cid = str(ej.get("customer_id") or "").strip()
    if cid:
        return cid
    name = str(row.get("customer_name") or row.get("customer") or ej.get("customer") or "").strip()
    if not name:
        return ""
    try:
        rows = fetch_by_match_admin("customers", {"customer_name": name}, columns="id,customer_name", limit=5)
        if rows:
            return str(rows[0].get("id") or "").strip()
    except Exception:
        pass
    try:
        rows = fetch_table("customers", columns="id,customer_name", limit=5000, order_by="customer_name")
        needle = name.lower()
        for r in rows or []:
            if str(r.get("customer_name") or "").strip().lower() == needle:
                return str(r.get("id") or "").strip()
    except Exception:
        pass
    return ""


def _estimate_awarded_amount(row: dict[str, Any]) -> float:
    for key in ("proposal_total", "final_bid", "total", "customer_price", "grand_total"):
        val = row.get(key)
        if val in (None, ""):
            continue
        try:
            amount = float(val)
        except (TypeError, ValueError):
            continue
        if amount != 0 or key in ("proposal_total", "total", "customer_price"):
            return amount
    return 0.0


def approve_estimate_and_create_job(
    estimate_id: str,
    *,
    mark_job_received: bool = False,
) -> CreateJobFromEstimateResult:
    """
    One-click workflow: ensure customer is linked, set status to Approved if needed,
    then create the matching job (Q##### → J#####).
    """
    eid = str(estimate_id or "").strip()
    if not eid:
        return CreateJobFromEstimateResult(ok=False, message="Invalid estimate id.", error_code="invalid_id")

    row = _fetch_estimate_row_for_create(eid)
    if not row:
        return CreateJobFromEstimateResult(ok=False, message="Estimate not found.", error_code="not_found")

    existing = _existing_job_for_estimate(eid, row)
    if existing:
        jn = job_number_display(existing.get("job_number"))
        label = jn or str(existing.get("job_name") or "").strip() or "existing job"
        return CreateJobFromEstimateResult(
            ok=True,
            message=f"This estimate already has job {label}.",
            job=existing,
            error_code="duplicate",
        )

    customer_id = _resolve_customer_id_for_estimate(row)
    if not customer_id:
        return CreateJobFromEstimateResult(
            ok=False,
            message="Choose a customer on the estimate before creating a job.",
            error_code="no_customer",
        )

    if not str(row.get("customer_id") or "").strip():
        _patch_estimate_row(eid, {"customer_id": customer_id})

    if not estimate_status_allows_job_creation(str(row.get("status") or "")):
        _patch_estimate_row(eid, {"status": "Approved"})

    return create_job_from_estimate(eid, mark_job_received=mark_job_received)


def estimate_quote_to_job_number(quote_number: str) -> str:
    """
    Map an estimate **quote_number** (e.g. ``Q26208``) to a related **job_number** (``J26208``).

    Does not consume a new sequence slot — only swaps the ``Q`` prefix for ``J``.
    Standalone jobs use :func:`~app.services.job_service.next_job_number` instead.
    """
    try:
        from app.services.shared_sequence import quote_number_to_job_number
    except ImportError:
        from services.shared_sequence import quote_number_to_job_number  # type: ignore
    return quote_number_to_job_number(quote_number)


def get_estimate_description(est: dict[str, Any]) -> str:
    """
    Short label for job naming (same sources as **Estimate Description** in the editor).

    Does not use ``scope_of_work`` or other long proposal text.
    """
    raw = est.get("estimate_json")
    est_json = raw if isinstance(raw, dict) else {}
    v = (
        est.get("estimate_description")
        or est_json.get("estimate_description")
        or est.get("job")
        or est.get("job_name")
        or ""
    )
    return str(v).strip()


# Base jobs schema (002_jobs.sql); lifecycle cols (084) are optional — see db._execute_jobs_query.
_JOB_COLLISION_COLUMNS = "id,job_number,job_name,estimate_id,customer_id,status,is_deleted,deleted_at"


def _job_has_stale_estimate_link(job: dict[str, Any]) -> bool:
    """Job points at an estimate that does not reference this job (failed or replaced link)."""
    est_id = str(job.get("estimate_id") or "").strip()
    if not est_id:
        return False
    est_rows = fetch_by_match_admin("estimates", {"id": est_id}, columns="id,job_id", limit=1)
    if not est_rows:
        return True
    linked = str(est_rows[0].get("job_id") or "").strip()
    job_id = str(job.get("id") or "").strip()
    return linked != job_id


def _estimate_quote_number(row: dict[str, Any]) -> str:
    ej = _as_json_dict(row.get("estimate_json"))
    return str(
        row.get("quote_number") or row.get("estimate_number") or ej.get("quote_number") or ""
    ).strip()


def _job_matches_estimate_quote(job: dict[str, Any], quote_number: str) -> bool:
    q = str(quote_number or "").strip().upper()
    if not q:
        return False
    src = str(job.get("source_estimate_number") or "").strip().upper()
    if src == q:
        return True
    proposed = estimate_quote_to_job_number(q)
    if not proposed:
        return False
    return _normalize_job_number_key(job.get("job_number")) == _normalize_job_number_key(proposed)


def _existing_job_for_estimate(estimate_id: str, row: dict[str, Any]) -> dict[str, Any] | None:
    by_ref = fetch_by_match_admin(
        "jobs",
        {"estimate_id": estimate_id},
        columns=_JOB_COLLISION_COLUMNS,
        limit=5,
    )
    if by_ref:
        return by_ref[0]
    jid = row.get("job_id")
    if jid:
        got = fetch_by_match_admin(
            "jobs",
            {"id": jid},
            columns=_JOB_COLLISION_COLUMNS,
            limit=1,
        )
        if got:
            return got[0]
    quote_number = _estimate_quote_number(row)
    proposed = estimate_quote_to_job_number(quote_number) if quote_number else ""
    if proposed:
        for hit in fetch_jobs_by_exact_job_number(proposed):
            if _job_matches_estimate_quote(hit, quote_number) and (
                _job_has_stale_estimate_link(hit)
                or str(hit.get("estimate_id") or "").strip() in {"", estimate_id}
            ):
                return hit
    return None


_INACTIVE_JOB_STATUSES_FOR_NUMBER_RECLAIM: FrozenSet[str] = frozenset(
    {"archived", "deleted", "cancelled", "canceled", "closed", "completed"}
)


def _norm_job_status(status: object) -> str:
    return str(status or "").strip().lower().replace("_", " ")


def _normalize_job_number_key(job_number: object) -> str:
    return str(job_number or "").strip().upper()


def _job_row_is_soft_deleted(job: dict[str, Any]) -> bool:
    if job.get("is_deleted") is True:
        return True
    if str(job.get("deleted_at") or "").strip():
        return True
    return _norm_job_status(job.get("status")) in {"deleted", "archived"}


def _estimate_pending_job_is_orphan(blocking_job: dict[str, Any]) -> bool:
    """Estimate-pending rows left behind after a failed link should not block new estimates."""
    if _norm_job_status(blocking_job.get("status")) != "estimate pending":
        return False
    if not str(blocking_job.get("estimate_id") or "").strip():
        return True
    return _job_has_stale_estimate_link(blocking_job)


def fetch_jobs_by_exact_job_number(job_number: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Exact ``job_number`` match only (no partial / ilike)."""
    raw = str(job_number or "").strip()
    if not raw:
        return []
    key = _normalize_job_number_key(raw)
    hits = fetch_by_match_admin(
        "jobs",
        {"job_number": raw},
        columns=_JOB_COLLISION_COLUMNS,
        limit=limit,
    )
    return [h for h in hits if _normalize_job_number_key(h.get("job_number")) == key]


def job_number_conflict_is_reclaimable(blocking_job: dict[str, Any], *, estimate_id: str) -> bool:
    """Inactive, soft-deleted, or orphan estimate-pending jobs should not block numbering."""
    _ = estimate_id
    if _job_row_is_soft_deleted(blocking_job):
        return True
    if _estimate_pending_job_is_orphan(blocking_job):
        return True
    if _job_has_stale_estimate_link(blocking_job):
        return True
    if str(blocking_job.get("estimate_id") or "").strip():
        return False
    return _norm_job_status(blocking_job.get("status")) in _INACTIVE_JOB_STATUSES_FOR_NUMBER_RECLAIM


def reclaim_inactive_job_number(blocking_job: dict[str, Any], proposed_jn: str) -> bool:
    """Move an inactive job off ``proposed_jn`` so estimate conversion can reuse it."""
    jid = str(blocking_job.get("id") or "").strip()
    if not jid:
        return False
    old = str(blocking_job.get("job_number") or proposed_jn).strip() or proposed_jn
    archived_num = f"{old}-A{jid.replace('-', '')[:6].upper()}"[:120]
    try:
        update_rows_admin("jobs", {"job_number": archived_num}, {"id": jid})
        return True
    except Exception:
        return False


def resolve_job_number_collision(
    hit: dict[str, Any],
    *,
    estimate_id: str,
    proposed_jn: str,
    linked_job_id: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """
    Resolve a proposed job number collision.

    Returns ``(outcome, job)`` where outcome is ``reuse``, ``released``, or ``blocked``.
    """
    hid = str(hit.get("id") or "").strip()
    lid = str(linked_job_id or "").strip()
    if lid and hid == lid:
        return "reuse", hit
    hest = str(hit.get("estimate_id") or "").strip()
    eid = str(estimate_id or "").strip()
    if hest and eid and hest == eid:
        return "reuse", hit
    if _job_has_stale_estimate_link(hit):
        return "reuse", hit
    if job_number_conflict_is_reclaimable(hit, estimate_id=estimate_id):
        if reclaim_inactive_job_number(hit, proposed_jn):
            return "released", None
    return "blocked", hit


def resolve_job_number_collisions(
    hits: list[dict[str, Any]],
    *,
    estimate_id: str,
    proposed_jn: str,
    linked_job_id: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Evaluate all rows sharing ``proposed_jn``; prefer reuse, then release, else block."""
    if not hits:
        return "released", None
    for hit in hits:
        outcome, job = resolve_job_number_collision(
            hit,
            estimate_id=estimate_id,
            proposed_jn=proposed_jn,
            linked_job_id=linked_job_id,
        )
        if outcome == "reuse":
            return "reuse", job
    for hit in hits:
        outcome, job = resolve_job_number_collision(
            hit,
            estimate_id=estimate_id,
            proposed_jn=proposed_jn,
            linked_job_id=linked_job_id,
        )
        if outcome == "released":
            return "released", job
    return "blocked", hits[0]


def renumber_estimate_quote_for_job_collision(
    estimate_id: str,
    *,
    quote_number: str | None = None,
    exclude_job_id: str | None = None,
) -> tuple[str, str] | None:
    """
    Allocate the next free Q/J pair and patch the estimate quote number.

    Returns ``(quote_number, job_number)`` or None when allocation fails.
    """
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    try:
        from app.services.shared_sequence import next_available_quote_job_pair, parse_number_parts
    except ImportError:
        from services.shared_sequence import (  # type: ignore
            next_available_quote_job_pair,
            parse_number_parts,
        )

    qref = str(quote_number or "").strip()
    parts = parse_number_parts(qref)
    if parts:
        yy = int(parts[1])
        year_anchor = date(2000 + yy, 1, 1)
    else:
        year_anchor = datetime.utcnow()
    try:
        new_q, new_j = next_available_quote_job_pair(
            year_anchor,
            exclude_estimate_id=eid,
            exclude_job_id=exclude_job_id,
        )
    except ValueError:
        return None
    patch: dict[str, Any] = {
        "quote_number": new_q,
        "updated_at": datetime.utcnow().isoformat(),
    }
    try:
        _patch_estimate_row(eid, patch)
    except Exception:
        return None
    return new_q, new_j


def _fallback_job_name(row: dict[str, Any], ej: dict[str, Any], customer_name: str) -> str:
    """
    Job name when :func:`get_estimate_description` is empty.

    Prefers import title, then customer + quote, then quote alone. Does not use
    ``scope_of_work``.
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

    short_name = get_estimate_description(row)
    if short_name:
        job_name = short_name[:500]
    else:
        job_name = _fallback_job_name(row, ej, customer_name).strip() or "Awarded job"

    _, has_job_number_column = fetch_jobs_for_job_database(limit=1, admin_read=True)

    awarded_f = _estimate_awarded_amount(row)

    site_loc = _location_text_from_customer_location(customer_location_id) if customer_location_id else ""
    merged_location = site_loc or _safe_location(ej)

    try:
        from app.services.job_po_service import po_fields_from_estimate
    except ImportError:
        from services.job_po_service import po_fields_from_estimate  # type: ignore
    po_fields = po_fields_from_estimate(row)

    # source_type omitted until jobs schema includes that column (sql/022); estimate_id marks estimate-linked jobs.
    payload: dict[str, Any] = {
        "customer_id": customer_id,
        "job_name": job_name,
        "location": merged_location,
        # Estimate-converted jobs start as Awarded so they are ready for costing (not Draft).
        "status": JOB_STATUS_AFTER_ESTIMATE_CONVERSION,
        "estimate_id": eid,
        "project_manager": "",
        "supervisor": "",
        "start_date": None,
        "target_completion_date": None,
        "completed_date": None,
        "awarded_amount": awarded_f,
        "notes": _build_job_notes(row, ej),
    }
    payload.update({k: v for k, v in po_fields.items() if v not in (None, "", 0, 0.0)})
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

        hits = fetch_jobs_by_exact_job_number(proposed_jn)
        if hits:
            outcome, collision_job = resolve_job_number_collisions(
                hits,
                estimate_id=eid,
                proposed_jn=proposed_jn,
                linked_job_id=str(row.get("job_id") or "").strip() or None,
            )
            if outcome == "reuse":
                inserted = dict(collision_job or hits[0])
                skip_insert = True
            elif outcome == "blocked":
                pair = renumber_estimate_quote_for_job_collision(
                    eid,
                    quote_number=qraw,
                    exclude_job_id=str((collision_job or hits[0]).get("id") or "").strip() or None,
                )
                if pair:
                    new_q, new_j = pair
                    proposed_jn = new_j
                    payload["job_number"] = new_j
                    row["quote_number"] = new_q
                    ej["quote_number"] = new_q
                else:
                    hit0 = collision_job or hits[0]
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
