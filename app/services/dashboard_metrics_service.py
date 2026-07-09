"""Live dashboard KPIs and chart data from estimates, jobs, and inventory."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

_OPEN_ESTIMATE_STATUSES = frozenset({"draft", "pending", "sent"})
_SENT_ESTIMATE_STATUSES = frozenset({"sent", "pending"})
_AWARDED_JOB_STATUSES = frozenset({"active", "complete", "completed"})


def _norm_status(raw: object) -> str:
    return str(raw or "").strip().lower().replace("_", " ")


def _parse_iso_date(raw: object) -> date | None:
    text = str(raw or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _money(row: dict[str, Any], *keys: str) -> float:
    for key in keys:
        raw = row.get(key)
        if raw in (None, ""):
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return 0.0


def _estimate_amount(est: dict[str, Any]) -> float:
    return _money(est, "customer_price", "total", "amount", "subtotal")


def _job_amount(job: dict[str, Any]) -> float:
    return _money(job, "contract_value", "awarded_amount", "customer_price", "total")


def _inventory_on_hand_value(items: list[dict[str, Any]]) -> float:
    total = 0.0
    for item in items:
        if not isinstance(item, dict):
            continue
        qty = _money(item, "qty_on_hand", "quantity_on_hand", "on_hand")
        cost = _money(item, "unit_cost", "cost")
        total += qty * cost
    return round(total, 2)


def _inventory_item_active(item: dict[str, Any]) -> bool:
    if item.get("is_active") is False:
        return False
    status = _norm_status(item.get("status"))
    if status in {"discontinued", "inactive", "deleted", "archived"}:
        return False
    return True


def _total_active_inventory_value(items: list[dict[str, Any]]) -> float:
    """Sum quantity_on_hand × unit_cost for active inventory SKUs."""
    total = 0.0
    active_count = 0
    for item in items:
        if not isinstance(item, dict) or not _inventory_item_active(item):
            continue
        active_count += 1
        qty = _money(item, "quantity_on_hand", "qty_on_hand", "on_hand")
        cost = _money(item, "unit_cost", "cost")
        total += qty * cost
    return round(total, 2)


def _asset_row_active(row: dict[str, Any]) -> bool:
    status = _norm_status(row.get("status"))
    if status in {"retired", "deleted", "inactive", "disposed", "scrapped"}:
        return False
    if row.get("is_active") is False:
        return False
    return True


def _asset_row_value(row: dict[str, Any]) -> float:
    """Prefer purchase cost, then replacement/current value fields."""
    return _money(
        row,
        "purchase_cost",
        "purchase_price",
        "replacement_value",
        "current_value",
        "value",
    )


def _total_active_asset_value(assets: list[dict[str, Any]]) -> float:
    """Sum asset values for active equipment records."""
    total = 0.0
    for row in assets:
        if not isinstance(row, dict) or not _asset_row_active(row):
            continue
        total += _asset_row_value(row)
    return round(total, 2)


def _row_in_period(row: dict[str, Any], start: date, end: date, *date_keys: str) -> bool:
    for key in date_keys:
        d = _parse_iso_date(row.get(key))
        if d and start <= d <= end:
            return True
    return False


def _period_delta_pct(current: float, previous: float) -> tuple[str, str]:
    """Return (caption, trend) where trend is up/down/flat."""
    if previous <= 0 and current <= 0:
        return "No change vs prior period", "flat"
    if previous <= 0:
        return "New activity this period", "up"
    pct = ((current - previous) / previous) * 100.0
    if abs(pct) < 0.5:
        return "Flat vs prior period", "flat"
    direction = "up" if pct > 0 else "down"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}% vs prior period", direction


def job_status_overview(jobs: list[dict[str, Any]]) -> dict[str, int]:
    """Job counts by normalized status for the dashboard donut chart."""
    try:
        from app.services.job_service import normalize_job_status_for_filter
    except ImportError:
        from services.job_service import normalize_job_status_for_filter  # type: ignore

    counts: dict[str, int] = {}
    for job in jobs:
        if not isinstance(job, dict) or bool(job.get("is_deleted")):
            continue
        label = normalize_job_status_for_filter(job.get("status"))
        counts[label] = counts.get(label, 0) + 1
    return counts


def compute_dashboard_kpis(
    estimates: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    assets: list[dict[str, Any]] | None = None,
    *,
    period_start: date | None = None,
    period_end: date | None = None,
) -> dict[str, Any]:
    """Build dashboard KPI dict including job metrics and period comparisons."""
    try:
        from app.services.job_service import dashboard_job_metrics
    except ImportError:
        from services.job_service import dashboard_job_metrics  # type: ignore

    end = period_end or date.today()
    start = period_start or end.replace(day=1)
    prev_end = start - timedelta(days=1)
    span_days = max(1, (end - start).days + 1)
    prev_start = prev_end - timedelta(days=span_days - 1)

    def _period_sales(rows: list[dict[str, Any]], ps: date, pe: date) -> float:
        total = 0.0
        for job in rows:
            if bool(job.get("is_deleted")):
                continue
            st = _norm_status(job.get("status"))
            if st not in _AWARDED_JOB_STATUSES:
                continue
            if _row_in_period(job, ps, pe, "start_date", "awarded_date", "created_at", "updated_at"):
                total += _job_amount(job)
        if total <= 0:
            for est in estimates:
                st = _norm_status(est.get("status"))
                if st not in {"approved", "awarded"}:
                    continue
                if _row_in_period(est, ps, pe, "estimate_date", "created_at", "updated_at"):
                    total += _estimate_amount(est)
        return round(total, 2)

    def _open_quotes_value() -> float:
        return round(
            sum(
                _estimate_amount(e)
                for e in estimates
                if _norm_status(e.get("status")) in _SENT_ESTIMATE_STATUSES
            ),
            2,
        )

    def _open_estimates_count() -> int:
        return sum(1 for e in estimates if _norm_status(e.get("status")) in _OPEN_ESTIMATE_STATUSES)

    total_sales = _period_sales(jobs, start, end)
    prev_sales = _period_sales(jobs, prev_start, prev_end)
    sales_caption, sales_trend = _period_delta_pct(total_sales, prev_sales)

    open_invoices = _open_quotes_value()
    open_est = _open_estimates_count()
    inv_value = _inventory_on_hand_value(inventory)
    asset_rows = list(assets or [])
    total_inventory_value = _total_active_inventory_value(inventory)
    total_asset_value = _total_active_asset_value(asset_rows)
    active_inventory_count = sum(
        1 for item in inventory if isinstance(item, dict) and _inventory_item_active(item)
    )
    active_asset_count = sum(
        1 for row in asset_rows if isinstance(row, dict) and _asset_row_active(row)
    )

    prev_open = sum(
        _estimate_amount(e)
        for e in estimates
        if _norm_status(e.get("status")) in _SENT_ESTIMATE_STATUSES
        and _row_in_period(e, prev_start, prev_end, "estimate_date", "created_at")
    )
    quotes_caption, quotes_trend = _period_delta_pct(open_invoices, prev_open)

    return {
        "total_sales": total_sales,
        "open_invoices": open_invoices,
        "open_estimates": open_est,
        "inventory_value": inv_value,
        "total_inventory_value": total_inventory_value,
        "total_asset_value": total_asset_value,
        "sales_caption": sales_caption,
        "sales_trend": sales_trend,
        "quotes_caption": quotes_caption if open_invoices else "No sent quotes outstanding",
        "quotes_trend": quotes_trend if open_invoices else "flat",
        "estimates_caption": f"{open_est} open quote{'s' if open_est != 1 else ''}",
        "estimates_trend": "flat",
        "inventory_caption": f"{len(inventory)} SKU{'s' if len(inventory) != 1 else ''} tracked",
        "inventory_trend": "flat",
        "total_inventory_caption": (
            f"{active_inventory_count} active SKU{'s' if active_inventory_count != 1 else ''}"
        ),
        "total_inventory_trend": "flat",
        "total_asset_caption": (
            f"{active_asset_count} active asset{'s' if active_asset_count != 1 else ''}"
        ),
        "total_asset_trend": "flat",
        **dashboard_job_metrics(jobs),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "has_live_data": bool(estimates or jobs or inventory or asset_rows),
    }


def sales_overview_series(
    estimates: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    *,
    period_start: date,
    period_end: date,
    bucket_count: int = 5,
) -> tuple[list[str], dict[str, list[float]]]:
    """Weekly buckets of awarded job / approved estimate value for line chart."""
    span = max(1, (period_end - period_start).days + 1)
    bucket_days = max(1, span // bucket_count)
    labels: list[str] = []
    this_period: list[float] = []
    prev_end = period_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    last_period: list[float] = []

    for i in range(bucket_count):
        b_start = period_start + timedelta(days=i * bucket_days)
        b_end = min(period_end, b_start + timedelta(days=bucket_days - 1))
        labels.append(b_start.strftime("%b %d"))
        this_period.append(_bucket_sales(estimates, jobs, b_start, b_end))
        p_start = prev_start + timedelta(days=i * bucket_days)
        p_end = min(prev_end, p_start + timedelta(days=bucket_days - 1))
        last_period.append(_bucket_sales(estimates, jobs, p_start, p_end))

    if not any(this_period) and not any(last_period):
        return [], {}
    return labels, {"This Period": this_period, "Last Period": last_period}


def _bucket_sales(
    estimates: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    start: date,
    end: date,
) -> float:
    total = 0.0
    for job in jobs:
        if bool(job.get("is_deleted")):
            continue
        if _norm_status(job.get("status")) not in _AWARDED_JOB_STATUSES:
            continue
        if _row_in_period(job, start, end, "start_date", "awarded_date", "created_at"):
            total += _job_amount(job)
    for est in estimates:
        if _norm_status(est.get("status")) not in {"approved", "awarded"}:
            continue
        if _row_in_period(est, start, end, "estimate_date", "created_at"):
            total += _estimate_amount(est)
    return round(total, 2)


def sales_by_category(
    estimates: list[dict[str, Any]],
    *,
    period_start: date,
    period_end: date,
) -> dict[str, float]:
    """Roll up estimate cost buckets for approved work in the period."""
    buckets = {
        "Labor": 0.0,
        "Materials": 0.0,
        "Equipment": 0.0,
        "Subcontractors": 0.0,
        "Other": 0.0,
    }
    for est in estimates:
        if _norm_status(est.get("status")) not in {"approved", "awarded", "sent", "draft", "pending"}:
            continue
        if not _row_in_period(est, period_start, period_end, "estimate_date", "created_at", "updated_at"):
            continue
        labor = _money(est, "labor_total", "labor_cost")
        materials = _money(est, "material_total", "material_cost")
        equipment = _money(est, "equipment_total", "equipment_cost")
        subs = _money(est, "subcontractor_cost", "subcontractor_total")
        buckets["Labor"] += labor
        buckets["Materials"] += materials
        buckets["Equipment"] += equipment
        buckets["Subcontractors"] += subs
        categorized = labor + materials + equipment + subs
        total_amt = _estimate_amount(est)
        if total_amt > categorized:
            buckets["Other"] += total_amt - categorized

    out = {k: round(v, 2) for k, v in buckets.items() if v > 0}
    if not out:
        total = sum(_estimate_amount(e) for e in estimates if _open_or_awarded(_norm_status(e.get("status"))))
        if total > 0:
            return {"Open Pipeline": round(total, 2)}
    return out


def _open_or_awarded(status: str) -> bool:
    return status in _OPEN_ESTIMATE_STATUSES | {"approved", "awarded"}


def open_quotes_aging_bars(
    estimates: list[dict[str, Any]],
    *,
    today: date | None = None,
) -> list[tuple[str, float, str]]:
    """Age buckets for sent/pending quotes (replaces demo aging invoices)."""
    ref = today or date.today()
    buckets = [
        ("0–14 days", 0.0, "#22c55e"),
        ("15–30 days", 0.0, "#f59e0b"),
        ("31–60 days", 0.0, "#f97316"),
        ("60+ days", 0.0, "#ef4444"),
    ]
    for est in estimates:
        st = _norm_status(est.get("status"))
        if st not in _SENT_ESTIMATE_STATUSES:
            continue
        est_d = _parse_iso_date(est.get("estimate_date") or est.get("created_at"))
        if not est_d:
            continue
        age = (ref - est_d).days
        amount = _estimate_amount(est)
        if age <= 14:
            buckets[0] = (buckets[0][0], buckets[0][1] + amount, buckets[0][2])
        elif age <= 30:
            buckets[1] = (buckets[1][0], buckets[1][1] + amount, buckets[1][2])
        elif age <= 60:
            buckets[2] = (buckets[2][0], buckets[2][1] + amount, buckets[2][2])
        else:
            buckets[3] = (buckets[3][0], buckets[3][1] + amount, buckets[3][2])
    return [(label, round(val, 2), color) for label, val, color in buckets if val > 0]


def upcoming_deadlines(
    estimates: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    *,
    today: date | None = None,
    limit: int = 6,
) -> list[dict[str, str]]:
    """Upcoming estimate expirations and job end dates."""
    ref = today or date.today()
    items: list[tuple[date, dict[str, str]]] = []

    for est in estimates:
        exp = _parse_iso_date(est.get("expiration_date"))
        if not exp or exp < ref:
            continue
        st = _norm_status(est.get("status"))
        if st in {"approved", "awarded", "cancelled", "declined"}:
            continue
        num = str(est.get("estimate_number") or est.get("number") or "Quote").strip()
        days = (exp - ref).days
        level = "danger" if days <= 7 else ("warn" if days <= 14 else "ok")
        items.append(
            (
                exp,
                {
                    "title": f"{num} — Quote expiration",
                    "date": exp.isoformat(),
                    "badge": f"{days} day{'s' if days != 1 else ''}",
                    "level": level,
                },
            )
        )

    for job in jobs:
        if bool(job.get("is_deleted")):
            continue
        end = _parse_iso_date(job.get("end_date"))
        if not end or end < ref:
            continue
        if _norm_status(job.get("status")) not in {"active", "on hold"}:
            continue
        num = str(job.get("job_number") or job.get("job_name") or "Job").strip()
        days = (end - ref).days
        level = "danger" if days <= 7 else ("warn" if days <= 14 else "ok")
        items.append(
            (
                end,
                {
                    "title": f"{num} — Scheduled completion",
                    "date": end.isoformat(),
                    "badge": f"{days} day{'s' if days != 1 else ''}",
                    "level": level,
                },
            )
        )

    items.sort(key=lambda x: x[0])
    return [row for _, row in items[:limit]]
