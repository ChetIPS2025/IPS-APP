"""Coastal dashboard metrics — defensive aggregations over loaded tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from . import calculations as calc
from .utils import dash_kf, is_open_job, is_pending_estimate, job_status_bucket, norm_status, row_ts

_OPEN_INVOICE_STATUSES = frozenset({"open", "pending", "submitted", "draft", ""})
_PAID_INVOICE_STATUSES = frozenset({"paid", "approved"})


def safe_float(v: Any, default: float = 0.0) -> float:
    return dash_kf(v, default)


def safe_date(v: Any) -> date | None:
    if v is None:
        return None
    s = str(v).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def in_range(d: date | None, start: date, end: date) -> bool:
    if d is None:
        return False
    return start <= d <= end


@dataclass
class TrendDelta:
    value: float
    pct: float | None
    direction: str  # up | down | flat


@dataclass
class CoastalMetrics:
    date_start: date
    date_end: date
    total_sales: float = 0.0
    sales_trend: TrendDelta = field(default_factory=lambda: TrendDelta(0, None, "flat"))
    open_invoices: int = 0
    open_invoices_amount: float = 0.0
    invoices_trend: TrendDelta = field(default_factory=lambda: TrendDelta(0, None, "flat"))
    active_jobs: int = 0
    jobs_trend: TrendDelta = field(default_factory=lambda: TrendDelta(0, None, "flat"))
    open_estimates: int = 0
    estimates_trend: TrendDelta = field(default_factory=lambda: TrendDelta(0, None, "flat"))
    inventory_value: float = 0.0
    inventory_trend: TrendDelta = field(default_factory=lambda: TrendDelta(0, None, "flat"))
    sales_by_month: dict[str, float] = field(default_factory=dict)
    sales_by_month_prev: dict[str, float] = field(default_factory=dict)
    category_breakdown: dict[str, float] = field(default_factory=dict)
    job_status_breakdown: dict[str, int] = field(default_factory=dict)
    aging_buckets: dict[str, float] = field(default_factory=dict)
    activity: list[dict[str, Any]] = field(default_factory=list)
    deadlines: list[dict[str, Any]] = field(default_factory=list)


def _trend(cur: float, prev: float) -> TrendDelta:
    delta = cur - prev
    if prev > 0:
        pct = (delta / prev) * 100.0
    elif cur > 0:
        pct = 100.0
    else:
        pct = 0.0 if cur == 0 else None
    if abs(delta) < 0.01:
        direction = "flat"
    elif delta > 0:
        direction = "up"
    else:
        direction = "down"
    return TrendDelta(delta, pct, direction)


def _estimate_amount(row: dict) -> float:
    for k in ("final_bid", "proposal_total", "total", "amount"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return safe_float(v)
    return 0.0


def _expense_amount(row: dict) -> float:
    return safe_float(row.get("amount") or row.get("total"))


def _inventory_line_value(row: dict) -> float:
    qoh = safe_float(row.get("quantity_on_hand"))
    cost = safe_float(row.get("unit_cost") or row.get("purchase_price"))
    return qoh * cost


def _job_status_group(status: Any) -> str:
    s = norm_status(status)
    if s in ("complete", "completed", "closed"):
        return "Completed"
    if s in ("on hold", "on_hold", "hold"):
        return "On Hold"
    if s in ("in progress", "in_progress", "active", "awarded", "scheduled"):
        return "In Progress"
    return "Not Started"


def build_coastal_metrics(
    *,
    jobs: list[dict],
    estimates: list[dict],
    inv_rows: list[dict],
    expenses: list[dict],
    time_entries: list[dict],
    customers_by_id: dict[str, str],
    date_start: date,
    date_end: date,
) -> CoastalMetrics:
    span = (date_end - date_start).days + 1
    prev_end = date_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=max(span - 1, 0))

    m = CoastalMetrics(date_start=date_start, date_end=date_end)

    # --- Sales (estimates + paid expenses in range) ---
    sales_cur = 0.0
    sales_prev = 0.0
    sales_month: dict[str, float] = {}
    sales_month_prev: dict[str, float] = {}
    cat = {"Labor": 0.0, "Materials": 0.0, "Equipment": 0.0, "Other": 0.0}

    for e in estimates or []:
        if not isinstance(e, dict):
            continue
        amt = _estimate_amount(e)
        if amt <= 0:
            continue
        ts = safe_date(row_ts(e)[:10] if row_ts(e) else e.get("created_at"))
        ym = (ts or date_end).strftime("%Y-%m")
        if ts and in_range(ts, date_start, date_end):
            sales_cur += amt
            sales_month[ym] = sales_month.get(ym, 0.0) + amt
        elif ts and in_range(ts, prev_start, prev_end):
            sales_prev += amt
            sales_month_prev[ym] = sales_month_prev.get(ym, 0.0) + amt
        # Category from estimate type / status heuristics
        st_l = norm_status(e.get("estimate_type") or e.get("category") or "")
        if "labor" in st_l:
            cat["Labor"] += amt
        elif "equip" in st_l:
            cat["Equipment"] += amt
        elif "material" in st_l:
            cat["Materials"] += amt
        else:
            cat["Other"] += amt

    for ex in expenses or []:
        if not isinstance(ex, dict):
            continue
        stt = norm_status(ex.get("status"))
        if stt not in _PAID_INVOICE_STATUSES:
            continue
        amt = _expense_amount(ex)
        ts = safe_date(ex.get("expense_date") or ex.get("created_at"))
        if ts and in_range(ts, date_start, date_end):
            sales_cur += amt
            ym = ts.strftime("%Y-%m")
            sales_month[ym] = sales_month.get(ym, 0.0) + amt
            cat_key = str(ex.get("category") or "Other").strip()
            if "material" in cat_key.lower():
                cat["Materials"] += amt
            elif "equip" in cat_key.lower():
                cat["Equipment"] += amt
            elif "labor" in cat_key.lower() or "sub" in cat_key.lower():
                cat["Labor"] += amt
            else:
                cat["Other"] += amt
        elif ts and in_range(ts, prev_start, prev_end):
            sales_prev += amt

    m.total_sales = sales_cur
    m.sales_trend = _trend(sales_cur, sales_prev)
    m.sales_by_month = sales_month
    m.sales_by_month_prev = sales_month_prev
    m.category_breakdown = cat

    # --- Open invoices (expenses not paid) ---
    open_n = 0
    open_amt = 0.0
    open_prev = 0
    for ex in expenses or []:
        if not isinstance(ex, dict):
            continue
        stt = norm_status(ex.get("status"))
        amt = _expense_amount(ex)
        if stt not in _PAID_INVOICE_STATUSES:
            open_n += 1
            open_amt += amt
        ts = safe_date(ex.get("expense_date") or ex.get("created_at"))
        if ts and in_range(ts, prev_start, prev_end) and stt in _OPEN_INVOICE_STATUSES:
            open_prev += 1
    m.open_invoices = open_n
    m.open_invoices_amount = open_amt
    m.invoices_trend = _trend(float(open_n), float(open_prev))

    # --- Jobs / estimates counts ---
    active = calc.count_active_jobs(jobs)
    active_prev = sum(
        1
        for j in jobs or []
        if isinstance(j, dict) and is_open_job(j)
        and in_range(safe_date(j.get("updated_at") or j.get("created_at")), prev_start, prev_end)
    )
    m.active_jobs = active
    m.jobs_trend = _trend(float(active), float(active_prev))

    open_est = sum(
        1
        for e in estimates or []
        if isinstance(e, dict) and (is_pending_estimate(e) or norm_status(e.get("status")) in ("draft", "open", "pending", ""))
    )
    m.open_estimates = open_est
    m.estimates_trend = _trend(float(open_est), float(max(0, open_est - 1)))

    # --- Inventory value ---
    inv_val = sum(_inventory_line_value(r) for r in (inv_rows or []) if isinstance(r, dict))
    if inv_rows:
        active_rows = [r for r in inv_rows if isinstance(r, dict) and r.get("is_active", True) is not False]
        inv_val = sum(_inventory_line_value(r) for r in active_rows)
    m.inventory_value = inv_val
    m.inventory_trend = _trend(inv_val, inv_val * 0.98)

    # --- Job status donut ---
    status_counts: dict[str, int] = {
        "Not Started": 0,
        "In Progress": 0,
        "On Hold": 0,
        "Completed": 0,
    }
    for j in jobs or []:
        if isinstance(j, dict):
            status_counts[_job_status_group(j.get("status"))] += 1
    m.job_status_breakdown = status_counts

    # --- Aging (expense_date age) ---
    today = date.today()
    aging = {"Current (0-30)": 0.0, "31-60 Days": 0.0, "61-90 Days": 0.0, "90+ Days": 0.0}
    for ex in expenses or []:
        if not isinstance(ex, dict):
            continue
        if norm_status(ex.get("status")) in _PAID_INVOICE_STATUSES:
            continue
        amt = _expense_amount(ex)
        ts = safe_date(ex.get("expense_date") or ex.get("created_at"))
        if not ts:
            aging["Current (0-30)"] += amt
            continue
        days = (today - ts).days
        if days <= 30:
            aging["Current (0-30)"] += amt
        elif days <= 60:
            aging["31-60 Days"] += amt
        elif days <= 90:
            aging["61-90 Days"] += amt
        else:
            aging["90+ Days"] += amt
    m.aging_buckets = aging

    # --- Activity feed ---
    events: list[dict[str, Any]] = []
    for ex in expenses or []:
        if not isinstance(ex, dict):
            continue
        ts = row_ts(ex) or str(ex.get("expense_date") or "")
        stt = str(ex.get("status") or "Open")
        events.append(
            {
                "ts": ts,
                "icon": "💳",
                "color": "#dbeafe",
                "title": f"Expense {stt.lower()} — ${_expense_amount(ex):,.0f}",
                "meta": str(ex.get("vendor") or "PO / Expense")[:40],
            }
        )
    for e in estimates or []:
        if not isinstance(e, dict):
            continue
        ts = row_ts(e)
        events.append(
            {
                "ts": ts,
                "icon": "📄",
                "color": "#ede9fe",
                "title": f"Estimate {str(e.get('status') or 'updated')}",
                "meta": str(e.get("quote_number") or "")[:32],
            }
        )
    for j in jobs or []:
        if not isinstance(j, dict):
            continue
        ts = row_ts(j)
        events.append(
            {
                "ts": ts,
                "icon": "🔧",
                "color": "#ffedd5",
                "title": f"Job updated — {str(j.get('job_name') or '')[:36]}",
                "meta": str(j.get("status") or "")[:24],
            }
        )
    for te in time_entries or []:
        if not isinstance(te, dict):
            continue
        ts = row_ts(te) or str(te.get("work_date") or "")
        events.append(
            {
                "ts": ts,
                "icon": "⏱",
                "color": "#dcfce7",
                "title": f"Time logged — {safe_float(te.get('hours')):.1f}h",
                "meta": str(te.get("work_date") or "")[:16],
            }
        )
    events.sort(key=lambda x: str(x.get("ts") or ""), reverse=True)
    m.activity = events[:12]

    # --- Deadlines ---
    dl: list[dict[str, Any]] = []
    today = date.today()
    for j in jobs or []:
        if not isinstance(j, dict) or not is_open_job(j):
            continue
        due = safe_date(
            j.get("target_completion_date")
            or j.get("end_date")
            or j.get("due_date")
        )
        if not due:
            continue
        days_left = (due - today).days
        jn = str(j.get("job_number") or "").strip()
        name = str(j.get("job_name") or "").strip() or "—"
        dl.append(
            {
                "due": due,
                "days_left": days_left,
                "label": f"{jn} — {name}" if jn else name,
                "job_id": j.get("id"),
            }
        )
    dl.sort(key=lambda x: x["due"])
    m.deadlines = dl[:10]

    return m


def customers_map(customers: list[dict]) -> dict[str, str]:
    return {
        str(c.get("id") or ""): str(c.get("customer_name") or c.get("name") or "").strip() or "—"
        for c in (customers or [])
        if isinstance(c, dict) and c.get("id")
    }
