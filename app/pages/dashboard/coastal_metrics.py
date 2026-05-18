"""Coastal dashboard KPI and panel metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .utils import dash_kf, is_open_job, is_pending_estimate, job_status_bucket, norm_status, row_ts


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
    return d is not None and start <= d <= end


_PAID = frozenset({"paid", "approved"})


@dataclass
class TrendDelta:
    value: float
    pct: float | None
    direction: str


@dataclass
class CoastalMetrics:
    total_sales: float = 0.0
    sales_trend: TrendDelta = field(default_factory=lambda: TrendDelta(0, None, "flat"))
    open_invoices: int = 0
    open_invoices_amount: float = 0.0
    invoices_trend: TrendDelta = field(default_factory=lambda: TrendDelta(0, None, "flat"))
    prior_period_label: str = ""
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


def format_period_range(start: date, end: date) -> str:
    return f"{start.strftime('%b')} {start.day}, {start.year} - {end.strftime('%b')} {end.day}, {end.year}"


def time_ago_from_ts(ts_str: str) -> str:
    if not ts_str:
        return ""
    try:
        s = str(ts_str).strip().replace("Z", "+00:00")
        if "T" in s:
            dt = datetime.fromisoformat(s[:19])
        else:
            dt = datetime.fromisoformat(s[:10])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        sec = max(0, int((now - dt).total_seconds()))
        if sec < 3600:
            return f"{max(1, sec // 60)}m ago"
        if sec < 86400:
            return f"{sec // 3600}h ago"
        if sec < 604800:
            return f"{sec // 86400}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return ""


def _trend(cur: float, prev: float) -> TrendDelta:
    delta = cur - prev
    pct = (delta / prev * 100.0) if prev > 0 else (100.0 if cur > 0 else 0.0)
    direction = "flat" if abs(delta) < 0.01 else ("up" if delta > 0 else "down")
    return TrendDelta(delta, pct, direction)


def _estimate_amount(row: dict) -> float:
    for k in ("final_bid", "proposal_total", "total", "amount"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return dash_kf(v)
    return 0.0


def _row_date(row: dict) -> date | None:
    ts = row_ts(row)
    if ts:
        return safe_date(ts[:10])
    return safe_date(row.get("created_at") or row.get("expense_date") or row.get("work_date"))


def _low_stock_count(inv_rows: list[dict]) -> int:
    n = 0
    for r in inv_rows or []:
        if not isinstance(r, dict) or r.get("is_active", True) is False:
            continue
        qoh = dash_kf(r.get("quantity_on_hand"))
        rp = dash_kf(r.get("reorder_point"))
        if rp > 0 and qoh <= rp:
            n += 1
    return n


def _assets_checked_out(assets: list[dict]) -> int:
    return sum(
        1
        for a in assets or []
        if isinstance(a, dict)
        and (
            str(a.get("status") or "").strip() == "Checked Out"
            or str(a.get("current_holder_employee_id") or "").strip()
        )
    )


def _job_status_group(status: Any) -> str:
    s = norm_status(status)
    if s in ("complete", "completed", "closed"):
        return "Completed"
    if "hold" in s:
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
    date_start: date,
    date_end: date,
) -> CoastalMetrics:
    span = max(1, (date_end - date_start).days + 1)
    prev_end = date_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    m = CoastalMetrics(prior_period_label=format_period_range(prev_start, prev_end))
    sales_cur = sales_prev = 0.0
    sales_month: dict[str, float] = {}
    sales_month_prev: dict[str, float] = {}
    cat = {"Labor": 0.0, "Materials": 0.0, "Equipment": 0.0, "Other": 0.0}

    for e in estimates or []:
        if not isinstance(e, dict):
            continue
        amt = _estimate_amount(e)
        if amt <= 0:
            continue
        ts = _row_date(e)
        if ts and in_range(ts, date_start, date_end):
            sales_cur += amt
            sales_month[ts.strftime("%Y-%m")] = sales_month.get(ts.strftime("%Y-%m"), 0.0) + amt
            tl = norm_status(e.get("estimate_type") or e.get("category") or "")
            if "labor" in tl:
                cat["Labor"] += amt
            elif "equip" in tl:
                cat["Equipment"] += amt
            elif "material" in tl:
                cat["Materials"] += amt
            else:
                cat["Other"] += amt
        elif ts and in_range(ts, prev_start, prev_end):
            sales_prev += amt
            sales_month_prev[ts.strftime("%Y-%m")] = sales_month_prev.get(ts.strftime("%Y-%m"), 0.0) + amt

    for ex in expenses or []:
        if not isinstance(ex, dict):
            continue
        amt = dash_kf(ex.get("amount"))
        stt = norm_status(ex.get("status"))
        ts = _row_date(ex)
        if stt in _PAID and ts and in_range(ts, date_start, date_end):
            sales_cur += amt
            sales_month[ts.strftime("%Y-%m")] = sales_month.get(ts.strftime("%Y-%m"), 0.0) + amt
            ck = str(ex.get("category") or "Other").lower()
            if "material" in ck:
                cat["Materials"] += amt
            elif "equip" in ck:
                cat["Equipment"] += amt
            elif "labor" in ck or "sub" in ck:
                cat["Labor"] += amt
            else:
                cat["Other"] += amt
        elif stt in _PAID and ts and in_range(ts, prev_start, prev_end):
            sales_prev += amt

    m.total_sales = sales_cur
    m.sales_trend = _trend(sales_cur, sales_prev)
    m.sales_by_month = sales_month
    m.sales_by_month_prev = sales_month_prev
    m.category_breakdown = cat

    open_n = 0
    open_amt = 0.0
    new_unpaid_cur = new_unpaid_prev = 0.0
    for ex in expenses or []:
        if not isinstance(ex, dict):
            continue
        amt = dash_kf(ex.get("amount"))
        stt = norm_status(ex.get("status"))
        if stt not in _PAID:
            open_n += 1
            open_amt += amt
        ts = _row_date(ex)
        if stt not in _PAID and ts:
            if in_range(ts, date_start, date_end):
                new_unpaid_cur += amt
            elif in_range(ts, prev_start, prev_end):
                new_unpaid_prev += amt
    m.open_invoices = open_n
    m.open_invoices_amount = open_amt
    m.invoices_trend = _trend(new_unpaid_cur, new_unpaid_prev)

    active = sum(1 for j in jobs or [] if isinstance(j, dict) and is_open_job(j))
    m.active_jobs = active
    new_open_jobs_cur = sum(
        1
        for j in jobs or []
        if isinstance(j, dict)
        and is_open_job(j)
        and (d := _row_date(j))
        and in_range(d, date_start, date_end)
    )
    new_open_jobs_prev = sum(
        1
        for j in jobs or []
        if isinstance(j, dict)
        and is_open_job(j)
        and (d := _row_date(j))
        and in_range(d, prev_start, prev_end)
    )
    m.jobs_trend = _trend(float(new_open_jobs_cur), float(new_open_jobs_prev))

    open_est = sum(1 for e in estimates or [] if isinstance(e, dict) and is_pending_estimate(e))
    m.open_estimates = open_est
    new_pending_cur = sum(
        1
        for e in estimates or []
        if isinstance(e, dict)
        and is_pending_estimate(e)
        and (d := _row_date(e))
        and in_range(d, date_start, date_end)
    )
    new_pending_prev = sum(
        1
        for e in estimates or []
        if isinstance(e, dict)
        and is_pending_estimate(e)
        and (d := _row_date(e))
        and in_range(d, prev_start, prev_end)
    )
    m.estimates_trend = _trend(float(new_pending_cur), float(new_pending_prev))

    inv_val = 0.0
    for r in inv_rows or []:
        if isinstance(r, dict) and r.get("is_active", True) is not False:
            inv_val += dash_kf(r.get("quantity_on_hand")) * dash_kf(r.get("unit_cost"))
    m.inventory_value = inv_val
    m.inventory_trend = TrendDelta(0.0, None, "flat")

    status_counts = {"Not Started": 0, "In Progress": 0, "On Hold": 0, "Completed": 0}
    for j in jobs or []:
        if isinstance(j, dict):
            status_counts[_job_status_group(j.get("status"))] += 1
    m.job_status_breakdown = status_counts

    today = date.today()
    aging = {"Current (0-30)": 0.0, "31-60 Days": 0.0, "61-90 Days": 0.0, "90+ Days": 0.0}
    for ex in expenses or []:
        if not isinstance(ex, dict) or norm_status(ex.get("status")) in _PAID:
            continue
        amt = dash_kf(ex.get("amount"))
        ts = _row_date(ex) or today
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

    events: list[dict[str, Any]] = []
    for ex in expenses or []:
        if isinstance(ex, dict):
            ts = row_ts(ex) or str(ex.get("expense_date") or "")
            inv = str(ex.get("invoice_number") or ex.get("id") or "")[:12]
            events.append({
                "ts": ts,
                "icon": "💳",
                "color": "#dbeafe",
                "title": f"Invoice #{inv} {str(ex.get('status') or 'updated').lower()}",
                "desc": str(ex.get("vendor") or "Expense")[:48],
                "age": time_ago_from_ts(ts),
            })
    for e in estimates or []:
        if isinstance(e, dict):
            ts = row_ts(e)
            events.append({
                "ts": ts,
                "icon": "📄",
                "color": "#ede9fe",
                "title": f"Estimate {str(e.get('quote_number') or 'updated')}",
                "desc": str(e.get("status") or "Estimate")[:48],
                "age": time_ago_from_ts(ts),
            })
    for j in jobs or []:
        if isinstance(j, dict):
            ts = row_ts(j)
            events.append({
                "ts": ts,
                "icon": "🔧",
                "color": "#ffedd5",
                "title": str(j.get("job_name") or "Job updated")[:40],
                "desc": f"Status: {str(j.get('status') or '—')}",
                "age": time_ago_from_ts(ts),
            })
    for te in time_entries or []:
        if isinstance(te, dict):
            ts = row_ts(te) or str(te.get("work_date") or "")
            events.append({
                "ts": ts,
                "icon": "⏱",
                "color": "#dcfce7",
                "title": f"Time entry — {dash_kf(te.get('hours')):.1f} hours",
                "desc": str(te.get("work_date") or "")[:16],
                "age": time_ago_from_ts(ts),
            })
    events.sort(key=lambda x: str(x.get("ts") or ""), reverse=True)
    m.activity = events[:12]

    dl: list[dict[str, Any]] = []
    for j in jobs or []:
        if not isinstance(j, dict) or not is_open_job(j):
            continue
        due = safe_date(j.get("target_completion_date") or j.get("end_date") or j.get("due_date"))
        if not due:
            continue
        jn = str(j.get("job_number") or "").strip()
        name = str(j.get("job_name") or "—").strip()
        dl.append({
            "due": due,
            "days_left": (due - today).days,
            "label": f"{jn} — {name}" if jn else name,
        })
    dl.sort(key=lambda x: x["due"])
    m.deadlines = dl[:10]
    return m


def customers_map(customers: list[dict]) -> dict[str, str]:
    return {
        str(c.get("id") or ""): str(c.get("customer_name") or c.get("name") or "—").strip() or "—"
        for c in (customers or [])
        if isinstance(c, dict) and c.get("id")
    }
