"""
Reports — aggregated live reads from Supabase (no direct UI queries).

Each report returns ``ReportData`` with rows and an ``is_live`` flag so the UI
can show Live data vs Sample data banners.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

try:
    from app.services.repository import fetch_rows
except ImportError:
    from services.repository import fetch_rows  # type: ignore

_OPEN_ESTIMATE_STATUSES = frozenset({"draft", "pending", "sent"})
_COMPLETED_JOB_STATUSES = frozenset({"complete", "completed", "closed"})
_REJECTED_TIMEKEEPING = frozenset({"rejected", "void", "voided"})


@dataclass(frozen=True)
class ReportData:
    rows: list[dict[str, Any]]
    is_live: bool


def _safe_float(raw: object) -> float:
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def _norm_status(raw: object) -> str:
    return str(raw or "").strip().lower().replace("_", " ")


def _admin_table(table: str, *, limit: int = 20000, order_by: str | None = None) -> tuple[list[dict[str, Any]], bool]:
    """Return (rows, is_live). ``is_live`` is False when the table could not be read."""
    try:
        from app.db import fetch_table_admin
    except ImportError:
        from db import fetch_table_admin  # type: ignore
    try:
        rows = list(fetch_table_admin(table, limit=limit, order_by=order_by) or [])
        return rows, True
    except Exception:
        return [], False


def _load_jobs_live() -> tuple[list[dict[str, Any]], bool]:
    try:
        from app.services.phase2_modules_service import list_jobs
    except ImportError:
        from services.phase2_modules_service import list_jobs  # type: ignore
    rows, used_demo = list_jobs(demo=[])
    return list(rows), not used_demo


def _jobs_index(jobs: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_number: dict[str, dict[str, Any]] = {}
    for job in jobs:
        if not isinstance(job, dict):
            continue
        jid = str(job.get("id") or "").strip()
        num = str(job.get("job_number") or "").strip()
        if jid:
            by_id[jid] = job
        if num:
            by_number[num] = job
    return by_id, by_number


def _resolve_job_from_timekeeping_row(
    row: dict[str, Any],
    *,
    jobs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    jid = str(row.get("job_id") or "").strip()
    if jid and jid in jobs_by_id:
        return jobs_by_id[jid]
    label = str(row.get("job_label") or "").strip()
    if not label:
        return None
    low = label.lower()
    if low in {"— no job —", "- no job -", "no job", "none", "—", "-", "shop", "administrative"}:
        return None
    try:
        from app.services.jobs_service import resolve_job_id_from_label
    except ImportError:
        from services.jobs_service import resolve_job_id_from_label  # type: ignore
    resolved = resolve_job_id_from_label(label)
    if resolved and resolved in jobs_by_id:
        return jobs_by_id[resolved]
    for job in jobs_by_id.values():
        num = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or "").strip()
        if num and label.startswith(num):
            return job
        friendly = f"{num} — {name}" if num and name else num or name
        if friendly and label == friendly:
            return job
    return None


def _timekeeping_hours_rows() -> tuple[list[dict[str, Any]], bool]:
    rows, live = _admin_table("employee_timekeeping_days", limit=20000)
    if live and rows:
        return rows, True
    rows, err = fetch_rows("employee_timekeeping_days", limit=20000)
    return rows, err is None


def _aggregate_timekeeping_hours(
    *,
    group_by: str,
    jobs_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    """Aggregate ST/OT/DT from employee_timekeeping_days."""
    day_rows, live = _timekeeping_hours_rows()
    buckets: dict[str, dict[str, Any]] = {}

    for row in day_rows:
        if not isinstance(row, dict):
            continue
        status = _norm_status(row.get("status"))
        if status in _REJECTED_TIMEKEEPING:
            continue
        st = _safe_float(row.get("st_hours"))
        ot = _safe_float(row.get("ot_hours"))
        dt = _safe_float(row.get("dt_hours"))
        if st + ot + dt <= 0:
            continue

        if group_by == "job":
            job = _resolve_job_from_timekeeping_row(row, jobs_by_id=jobs_by_id)
            key = str(job.get("job_number") or "Unassigned") if job else "Unassigned"
            bucket = buckets.setdefault(
                key,
                {
                    "job_number": key,
                    "job_name": str(job.get("job_name") or "") if job else "",
                    "st_hours": 0.0,
                    "ot_hours": 0.0,
                    "dt_hours": 0.0,
                    "total_hours": 0.0,
                },
            )
        else:
            eid = str(row.get("employee_id") or "").strip()
            emp = employees_by_id.get(eid, {})
            key = str(emp.get("name") or row.get("employee_name") or eid or "Unknown").strip()
            bucket = buckets.setdefault(
                key,
                {
                    "employee": key,
                    "st_hours": 0.0,
                    "ot_hours": 0.0,
                    "dt_hours": 0.0,
                    "total_hours": 0.0,
                },
            )

        bucket["st_hours"] += st
        bucket["ot_hours"] += ot
        bucket["dt_hours"] += dt
        bucket["total_hours"] += st + ot + dt

    out = sorted(buckets.values(), key=lambda r: str(r.get("job_number") or r.get("employee") or ""))
    return out, live


def _aggregate_time_entries_by_job(jobs_by_id: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, live = _admin_table("time_entries", limit=50000)
    if not live:
        rows, err = fetch_rows("time_entries", limit=50000)
        live = err is None
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        jid = str(row.get("job_id") or "").strip()
        job = jobs_by_id.get(jid)
        if not job:
            continue
        hrs = _safe_float(row.get("hours"))
        if hrs <= 0:
            continue
        key = str(job.get("job_number") or jid)
        bucket = buckets.setdefault(
            key,
            {
                "job_number": key,
                "job_name": str(job.get("job_name") or ""),
                "st_hours": 0.0,
                "ot_hours": 0.0,
                "dt_hours": 0.0,
                "total_hours": 0.0,
            },
        )
        ttype = str(row.get("time_type") or "ST").strip().upper()
        if ttype == "OT":
            bucket["ot_hours"] += hrs
        elif ttype == "DT":
            bucket["dt_hours"] += hrs
        else:
            bucket["st_hours"] += hrs
        bucket["total_hours"] += hrs
    return sorted(buckets.values(), key=lambda r: str(r.get("job_number") or "")), live


def _merge_hour_buckets(primary: list[dict[str, Any]], secondary: list[dict[str, Any]], *, key_field: str) -> list[dict[str, Any]]:
    if not secondary:
        return primary
    if not primary:
        return secondary
    by_key = {str(r.get(key_field) or ""): dict(r) for r in primary}
    for row in secondary:
        key = str(row.get(key_field) or "")
        if key not in by_key:
            by_key[key] = dict(row)
            continue
        bucket = by_key[key]
        for fld in ("st_hours", "ot_hours", "dt_hours", "total_hours"):
            bucket[fld] = _safe_float(bucket.get(fld)) + _safe_float(row.get(fld))
    return sorted(by_key.values(), key=lambda r: str(r.get(key_field) or ""))


def live_labor_by_job_report() -> ReportData:
    jobs, jobs_live = _load_jobs_live()
    jobs_by_id, _ = _jobs_index(jobs)
    tk_rows, tk_live = _aggregate_timekeeping_hours(group_by="job", jobs_by_id=jobs_by_id, employees_by_id={})
    te_rows, te_live = _aggregate_time_entries_by_job(jobs_by_id)
    rows = _merge_hour_buckets(tk_rows, te_rows, key_field="job_number") if te_rows else tk_rows
    return ReportData(rows=rows, is_live=jobs_live and (tk_live or te_live))


def live_labor_by_employee_report() -> ReportData:
    jobs, jobs_live = _load_jobs_live()
    jobs_by_id, _ = _jobs_index(jobs)
    emp_rows, emp_live = _admin_table("employees", limit=5000, order_by="name")
    if not emp_live:
        emp_rows, err = fetch_rows("employees", limit=5000, order_by="name")
        emp_live = err is None
    employees_by_id = {str(e.get("id") or ""): e for e in emp_rows if e.get("id")}
    rows, tk_live = _aggregate_timekeeping_hours(
        group_by="employee",
        jobs_by_id=jobs_by_id,
        employees_by_id=employees_by_id,
    )
    return ReportData(rows=rows, is_live=jobs_live and tk_live and emp_live)


def live_job_profitability_report(*, sync_sources: bool = True) -> ReportData:
    try:
        from app.services.job_cost_transaction_service import build_job_cost_summary, sync_all_sources_for_job
    except ImportError:
        from services.job_cost_transaction_service import build_job_cost_summary, sync_all_sources_for_job  # type: ignore

    jobs, jobs_live = _load_jobs_live()
    rows: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        if sync_sources:
            try:
                sync_all_sources_for_job(jid)
            except Exception:
                pass
        summary = build_job_cost_summary(job)
        revenue = _safe_float(summary.get("contract_value"))
        cost = _safe_float(summary.get("actual_cost"))
        margin = _safe_float(summary.get("margin_pct"))
        if revenue <= 0 and cost <= 0:
            continue
        rows.append(
            {
                "job_number": str(job.get("job_number") or "—"),
                "job_name": str(job.get("job_name") or job.get("name") or "—"),
                "revenue": revenue,
                "cost": cost,
                "margin_pct": margin,
            }
        )
    rows.sort(key=lambda r: (_safe_float(r.get("revenue")), str(r.get("job_number") or "")), reverse=True)
    return ReportData(rows=rows, is_live=jobs_live)


def live_open_estimates_report() -> ReportData:
    rows, err = fetch_rows("estimates", limit=5000, order_by="estimate_date")
    live = err is None
    out: list[dict[str, Any]] = []
    for est in rows:
        if not isinstance(est, dict):
            continue
        status = _norm_status(est.get("status"))
        if status not in _OPEN_ESTIMATE_STATUSES:
            continue
        out.append(
            {
                "estimate_number": str(est.get("estimate_number") or est.get("number") or "—"),
                "customer": str(est.get("customer") or est.get("customer_name") or "—"),
                "status": str(est.get("status") or "—"),
                "total": _safe_float(est.get("customer_price") or est.get("total") or est.get("amount")),
            }
        )
    return ReportData(rows=out, is_live=live)


def live_completed_jobs_report() -> ReportData:
    jobs, live = _load_jobs_live()
    out: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        status = _norm_status(job.get("status"))
        if status not in _COMPLETED_JOB_STATUSES:
            continue
        out.append(
            {
                "job_number": str(job.get("job_number") or "—"),
                "job_name": str(job.get("job_name") or "—"),
                "customer": str(job.get("customer") or job.get("customer_name") or "—"),
                "end_date": str(job.get("end_date") or job.get("completed_at") or "")[:10],
            }
        )
    out.sort(key=lambda r: str(r.get("end_date") or ""), reverse=True)
    return ReportData(rows=out, is_live=live)


def live_inventory_value_report() -> ReportData:
    rows, err = fetch_rows("inventory_items", limit=10000, alt_tables=("inventory",))
    live = err is None
    by_cat: dict[str, dict[str, Any]] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        cat = str(item.get("category") or "Uncategorized").strip() or "Uncategorized"
        qty = _safe_float(item.get("quantity_on_hand") or item.get("qty_on_hand") or item.get("on_hand"))
        cost = _safe_float(item.get("unit_cost") or item.get("cost"))
        bucket = by_cat.setdefault(cat, {"category": cat, "sku_count": 0, "on_hand_value": 0.0})
        bucket["sku_count"] += 1
        bucket["on_hand_value"] += qty * cost
    out = sorted(by_cat.values(), key=lambda r: str(r.get("category") or ""))
    return ReportData(rows=out, is_live=live)


def live_low_stock_report() -> ReportData:
    rows, err = fetch_rows("inventory_items", limit=10000, alt_tables=("inventory",))
    live = err is None
    out: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        qty = _safe_float(item.get("quantity_on_hand") or item.get("qty_on_hand") or item.get("on_hand"))
        reorder = _safe_float(item.get("reorder_point") or item.get("reorder_level") or 10)
        status = _norm_status(item.get("status"))
        if status == "low stock" or (reorder > 0 and qty <= reorder):
            out.append(
                {
                    "sku": str(item.get("sku") or item.get("item_number") or "—"),
                    "name": str(item.get("name") or item.get("item_name") or "—"),
                    "qty_on_hand": qty,
                    "reorder_point": reorder,
                }
            )
    out.sort(key=lambda r: _safe_float(r.get("qty_on_hand")))
    return ReportData(rows=out, is_live=live)


def live_certs_expiring_report() -> ReportData:
    try:
        from app.services.phase2_modules_service import list_all_certifications, list_employees
    except ImportError:
        from services.phase2_modules_service import list_all_certifications, list_employees  # type: ignore
    employees, emp_live = list_employees(demo=[])
    cert_rows, cert_demo = list_all_certifications(demo=[], employees=employees)
    live = emp_live and not cert_demo
    out: list[dict[str, Any]] = []
    for cert in cert_rows:
        if not isinstance(cert, dict):
            continue
        status = str(cert.get("status") or "").strip()
        low = status.lower()
        if low not in {"expired", "expiring soon", "expiring"} and status:
            continue
        if not status:
            continue
        out.append(
            {
                "employee_name": str(cert.get("employee_name") or "—"),
                "cert_type": str(cert.get("cert_type") or cert.get("certification_type") or "—"),
                "expiration_date": str(cert.get("expiration_date") or "")[:10],
                "status": status,
            }
        )
    out.sort(key=lambda r: str(r.get("expiration_date") or ""))
    return ReportData(rows=out, is_live=live)


def live_asset_maintenance_report() -> ReportData:
    try:
        from app.services.phase2_modules_service import list_assets
    except ImportError:
        from services.phase2_modules_service import list_assets  # type: ignore
    assets, used_demo = list_assets(demo=[])
    live = not used_demo
    out: list[dict[str, Any]] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        due = str(
            asset.get("next_service")
            or asset.get("service_due")
            or asset.get("next_service_due")
            or asset.get("maintenance_due_date")
            or ""
        )[:10]
        if not due:
            continue
        out.append(
            {
                "asset_number": str(asset.get("asset_number") or asset.get("asset_tag") or "—"),
                "name": str(asset.get("name") or asset.get("asset_name") or "—"),
                "next_service": due,
                "status": str(asset.get("maintenance_status") or asset.get("status") or "Scheduled"),
            }
        )
    out.sort(key=lambda r: str(r.get("next_service") or ""))
    return ReportData(rows=out, is_live=live)


def live_timekeeping_summary_report(week_start: date | None = None) -> ReportData:
    ws = week_start or date.today()
    try:
        from app.services.timekeeping_service import list_timekeeping_summaries
    except ImportError:
        from services.timekeeping_service import list_timekeeping_summaries  # type: ignore
    rows, used_demo = list_timekeeping_summaries(ws, demo=[])
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "id": str(row.get("id") or row.get("employee_id") or ""),
                "name": str(row.get("name") or "—"),
                "department": str(row.get("department") or row.get("trade") or "—"),
                "st_total": _safe_float(row.get("st_total")),
                "ot_total": _safe_float(row.get("ot_total")),
                "status": str(row.get("status") or "—"),
            }
        )
    return ReportData(rows=out, is_live=not used_demo)


def fetch_report_table(table: str, *, limit: int = 500, order_by: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """Load rows for a report section with graceful error string."""
    return fetch_rows(table, limit=limit, order_by=order_by)
