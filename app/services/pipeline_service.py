"""Unified quote (Q) and job (J) pipeline rows for the Pipeline page."""

from __future__ import annotations

from typing import Any

try:
    from app.services.shared_sequence import parse_number_parts, quote_number_to_job_number
except ImportError:
    from services.shared_sequence import parse_number_parts, quote_number_to_job_number  # type: ignore

PIPELINE_VIEWS: tuple[str, ...] = (
    "All Pipeline",
    "Open Quotes",
    "Approved Quotes",
    "Active Jobs",
    "All Jobs",
)

_ESTIMATE_STATUS_OPEN = frozenset({"draft", "pending", "sent"})
_ESTIMATE_STATUS_APPROVED = frozenset({"approved", "awarded"})
_JOB_ACTIVE = frozenset({"active", "on hold"})


def _norm_status(raw: object) -> str:
    return str(raw or "").strip().lower().replace("_", " ")


def _quote_number(est: dict[str, Any]) -> str:
    return str(est.get("estimate_number") or est.get("quote_number") or "").strip()


def _job_number(job: dict[str, Any]) -> str:
    return str(job.get("job_number") or "").strip()


def _project_title(row: dict[str, Any], *, fallback_keys: tuple[str, ...]) -> str:
    for key in fallback_keys:
        val = str(row.get(key) or "").strip()
        if val and val not in {"—", "-"}:
            return val
    return "—"


def _customer_label(row: dict[str, Any]) -> str:
    for key in ("customer", "customer_name"):
        val = str(row.get(key) or "").strip()
        if val and val not in {"—", "-"}:
            return val
    return "—"


def _money_value(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        raw = row.get(key)
        if raw in (None, ""):
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return 0.0


def _sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    for candidate in (
        str(row.get("job_number") or ""),
        str(row.get("quote_number") or ""),
        str(row.get("display_number") or ""),
    ):
        parts = parse_number_parts(candidate)
        if parts:
            _prefix, yy, seq = parts
            return (2000 + int(yy), int(seq), candidate)
    return (0, 0, str(row.get("display_number") or ""))


def _quote_stage(estimate_status: str, *, has_job: bool) -> str:
    if has_job:
        return "Awarded"
    status = _norm_status(estimate_status)
    if status in _ESTIMATE_STATUS_OPEN or status == "":
        if status == "sent":
            return "Quote — Sent"
        return "Quote — Draft"
    if status in _ESTIMATE_STATUS_APPROVED:
        return "Quote — Approved"
    if status in {"rejected", "expired", "cancelled", "canceled"}:
        return f"Quote — {status.title()}"
    label = str(estimate_status or "Draft").strip() or "Draft"
    return f"Quote — {label}"


def _job_stage(job_status: str) -> str:
    label = str(job_status or "Active").strip() or "Active"
    return f"Job — {label}"


def _index_jobs_by_estimate(jobs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for job in jobs:
        if bool(job.get("is_deleted")):
            continue
        eid = str(job.get("estimate_id") or "").strip()
        if eid:
            out[eid] = job
    return out


def _index_jobs_by_id(jobs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(job.get("id") or "").strip(): job
        for job in jobs
        if str(job.get("id") or "").strip()
    }


def build_pipeline_rows(
    estimates: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge estimates and jobs into one pipeline list.

    - Open quotes appear as ``Q`` rows.
    - Linked quote+job pairs appear once with both numbers (primary ``J``).
    - Standalone jobs (no estimate link) appear as ``J`` rows.
    """
    jobs_by_estimate = _index_jobs_by_estimate(jobs)
    jobs_by_id = _index_jobs_by_id(jobs)
    linked_job_ids: set[str] = set()
    rows: list[dict[str, Any]] = []

    for est in estimates:
        eid = str(est.get("id") or "").strip()
        if not eid:
            continue
        qnum = _quote_number(est)
        linked = jobs_by_estimate.get(eid)
        if not linked:
            jid_hint = str(est.get("job_id") or "").strip()
            if jid_hint:
                linked = jobs_by_id.get(jid_hint)
        if linked:
            jid = str(linked.get("id") or "").strip()
            if jid:
                linked_job_ids.add(jid)
            jnum = _job_number(linked) or quote_number_to_job_number(qnum)
            est_status = str(est.get("status") or "Draft")
            job_status = str(linked.get("status") or "Active")
            rows.append(
                {
                    "pipeline_key": f"pair-{eid}",
                    "record_type": "awarded",
                    "quote_number": qnum,
                    "job_number": jnum,
                    "display_number": jnum or qnum,
                    "stage": _job_stage(job_status),
                    "estimate_status": est_status,
                    "job_status": job_status,
                    "customer": _customer_label(est) if _customer_label(est) != "—" else _customer_label(linked),
                    "project": _project_title(
                        est,
                        fallback_keys=("project_name", "description", "estimate_description"),
                    ),
                    "value": _money_value(
                        linked,
                        "contract_value",
                        "awarded_amount",
                    )
                    or _money_value(est, "customer_price", "total"),
                    "estimate_id": eid,
                    "job_id": jid,
                    "has_job": True,
                }
            )
            continue

        est_status = str(est.get("status") or "Draft")
        rows.append(
            {
                "pipeline_key": f"quote-{eid}",
                "record_type": "quote",
                "quote_number": qnum,
                "job_number": "",
                "display_number": qnum,
                "stage": _quote_stage(est_status, has_job=False),
                "estimate_status": est_status,
                "job_status": "",
                "customer": _customer_label(est),
                "project": _project_title(
                    est,
                    fallback_keys=("project_name", "description", "estimate_description"),
                ),
                "value": _money_value(est, "customer_price", "total"),
                "estimate_id": eid,
                "job_id": "",
                "has_job": False,
            }
        )

    for job in jobs:
        if bool(job.get("is_deleted")):
            continue
        jid = str(job.get("id") or "").strip()
        if not jid or jid in linked_job_ids:
            continue
        if str(job.get("estimate_id") or "").strip():
            continue
        jnum = _job_number(job)
        job_status = str(job.get("status") or "Active")
        rows.append(
            {
                "pipeline_key": f"job-{jid}",
                "record_type": "job",
                "quote_number": "",
                "job_number": jnum,
                "display_number": jnum,
                "stage": _job_stage(job_status),
                "estimate_status": "",
                "job_status": job_status,
                "customer": _customer_label(job),
                "project": _project_title(job, fallback_keys=("job_name", "description", "project_name")),
                "value": _money_value(job, "contract_value", "awarded_amount"),
                "estimate_id": "",
                "job_id": jid,
                "has_job": True,
            }
        )

    rows.sort(key=_sort_key, reverse=True)
    return rows


def filter_pipeline_rows(
    rows: list[dict[str, Any]],
    *,
    view: str = "All Pipeline",
    search: str = "",
) -> list[dict[str, Any]]:
    view_norm = str(view or "All Pipeline").strip()
    out = list(rows)

    if view_norm == "Open Quotes":
        out = [
            r
            for r in out
            if r.get("record_type") == "quote"
            and _norm_status(r.get("estimate_status")) in _ESTIMATE_STATUS_OPEN | {""}
        ]
    elif view_norm == "Approved Quotes":
        out = [
            r
            for r in out
            if r.get("record_type") == "quote"
            and _norm_status(r.get("estimate_status")) in _ESTIMATE_STATUS_APPROVED
        ]
    elif view_norm == "Active Jobs":
        out = [
            r
            for r in out
            if r.get("has_job")
            and _norm_status(r.get("job_status") or "active") in _JOB_ACTIVE | {"active"}
        ]
    elif view_norm == "All Jobs":
        out = [r for r in out if r.get("has_job")]

    query = str(search or "").strip().casefold()
    if query:
        out = [
            r
            for r in out
            if query in str(r.get("quote_number") or "").casefold()
            or query in str(r.get("job_number") or "").casefold()
            or query in str(r.get("project") or "").casefold()
            or query in str(r.get("customer") or "").casefold()
            or query in str(r.get("stage") or "").casefold()
        ]
    return out


def pipeline_summary(rows: list[dict[str, Any]]) -> dict[str, int | float]:
    open_quotes = sum(
        1
        for r in rows
        if r.get("record_type") == "quote"
        and _norm_status(r.get("estimate_status")) in _ESTIMATE_STATUS_OPEN | {""}
    )
    approved_quotes = sum(
        1 for r in rows if r.get("record_type") == "quote" and _norm_status(r.get("estimate_status")) in _ESTIMATE_STATUS_APPROVED
    )
    active_jobs = sum(
        1
        for r in rows
        if r.get("has_job") and _norm_status(r.get("job_status") or "active") in _JOB_ACTIVE | {"active"}
    )
    pipeline_value = sum(float(r.get("value") or 0) for r in rows)
    return {
        "total": len(rows),
        "open_quotes": open_quotes,
        "approved_quotes": approved_quotes,
        "active_jobs": active_jobs,
        "pipeline_value": round(pipeline_value, 2),
    }
