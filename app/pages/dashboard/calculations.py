"""Dashboard KPI and aggregate calculations (pure functions, no I/O)."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

from .utils import (
    _KIT_REPL_HOT_THRESHOLD,
    _KIT_REPL_WINDOW_DAYS,
    asset_is_out,
    dash_kf,
    days_out_value,
    is_open_job,
    is_pending_estimate,
    job_status_bucket,
    kit_line_short_qty,
    norm_status,
)

try:
    from app.services.daily_work_packages import dashboard_dwp_snapshot, repeated_eod_delay_reasons
except ImportError:
    from services.daily_work_packages import dashboard_dwp_snapshot, repeated_eod_delay_reasons  # type: ignore


def count_awarded_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if job_status_bucket((j or {}).get("status")) == "awarded")


def count_bidding_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if job_status_bucket((j or {}).get("status")) == "bidding")


def count_active_employees(employees: list[dict]) -> int:
    rows = employees or []
    if not rows:
        return 0
    has_is_active = any(isinstance(r, dict) and "is_active" in r for r in rows)
    if not has_is_active:
        return len(rows)
    return sum(1 for r in rows if bool((r or {}).get("is_active", False)))


def count_open_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if isinstance(j, dict) and is_open_job(j))


def count_active_jobs(jobs: list[dict]) -> int:
    """Jobs not in a terminal closed/cancelled state."""
    return count_open_jobs(jobs)


def count_pending_estimates(estimates: list[dict]) -> int:
    return sum(1 for e in (estimates or []) if isinstance(e, dict) and is_pending_estimate(e))


def count_draft_estimates(estimates: list[dict]) -> int:
    draft_tokens = frozenset({"draft", "open", "pending", ""})
    return sum(
        1
        for e in (estimates or [])
        if norm_status((e or {}).get("status")) in draft_tokens
        or not str((e or {}).get("status") or "").strip()
    )


def count_awarded_jobs_this_month(jobs: list[dict], *, today: date | None = None) -> int:
    """Count awarded jobs updated or created in the current calendar month."""
    today = today or date.today()
    ym = today.strftime("%Y-%m")
    try:
        n = 0
        for j in jobs or []:
            if job_status_bucket((j or {}).get("status")) != "awarded":
                continue
            raw = str((j or {}).get("updated_at") or (j or {}).get("created_at") or "")[:7]
            if raw == ym:
                n += 1
        return n
    except Exception:
        return count_awarded_jobs(list(jobs or []))


def count_low_stock(inv_rows: list[dict]) -> int:
    if not inv_rows:
        return 0
    try:
        df_inv = pd.DataFrame(inv_rows)
        if "is_active" in df_inv.columns:
            df_inv = df_inv[df_inv["is_active"] != False]  # noqa: E712
        qoh = pd.to_numeric(df_inv.get("quantity_on_hand", 0), errors="coerce").fillna(0)
        rp = pd.to_numeric(df_inv.get("reorder_point", 0), errors="coerce").fillna(0)
        return int((qoh <= rp).sum())
    except Exception:
        return 0


def low_stock_display_df(inv_rows: list[dict]) -> pd.DataFrame | None:
    if not inv_rows:
        return None
    try:
        df_inv = pd.DataFrame(inv_rows)
        if "is_active" in df_inv.columns:
            df_inv = df_inv[df_inv["is_active"] != False]  # noqa: E712
        qoh = pd.to_numeric(df_inv.get("quantity_on_hand", 0), errors="coerce").fillna(0)
        rp = pd.to_numeric(df_inv.get("reorder_point", 0), errors="coerce").fillna(0)
        low_df = df_inv.loc[qoh <= rp, :].copy()
        if low_df.empty:
            return None
        try:
            from app.ui.catalog_inventory_display import prepare_catalog_inventory_display_df
        except ImportError:
            from ui.catalog_inventory_display import prepare_catalog_inventory_display_df  # type: ignore
        return prepare_catalog_inventory_display_df(low_df)
    except Exception:
        return None


def count_checked_out_assets(assets: list[dict]) -> int:
    return sum(
        1
        for a in (assets or [])
        if str((a or {}).get("status") or "").strip() == "Checked Out"
        or str((a or {}).get("current_holder_employee_id") or "").strip()
    )


def count_open_job_tasks(job_tasks: list[dict]) -> int:
    terminal = frozenset({"done", "complete", "completed", "cancelled", "canceled"})
    return sum(
        1
        for t in (job_tasks or [])
        if norm_status((t or {}).get("status")) not in terminal
    )


def labor_hours_for_date(time_entries: list[dict], *, work_date: str) -> float:
    total = 0.0
    for row in time_entries or []:
        if str((row or {}).get("work_date") or "")[:10] != work_date:
            continue
        try:
            total += float((row or {}).get("hours") or 0)
        except (TypeError, ValueError):
            pass
    return total


def count_pending_pos(po_rows: list[dict]) -> int:
    pending = frozenset({"pending", "open", "submitted", "draft"})
    return sum(
        1
        for p in po_rows or []
        if norm_status((p or {}).get("status")) in pending
    )


def count_unread_company_updates(
    updates: list[dict],
    reads: list[dict],
    *,
    user_id: str,
) -> int:
    read_uids = {
        str(r.get("update_id") or "")
        for r in (reads or [])
        if str(r.get("user_id") or "") == user_id
    }
    n = 0
    for u in updates or []:
        uid = str((u or {}).get("id") or "").strip()
        if uid and uid not in read_uids and bool((u or {}).get("is_active", True)):
            n += 1
    return n


def todo_open_overdue_counts(todos: list[dict], *, today: date | None = None) -> tuple[int, int]:
    from .todo_logic import dedupe_todos, is_terminal_todo_status

    today = today or date.today()
    deduped = dedupe_todos([t for t in (todos or []) if isinstance(t, dict)])
    open_n = 0
    overdue_n = 0
    for t in deduped:
        if is_terminal_todo_status((t or {}).get("status")):
            continue
        open_n += 1
        ds = str((t or {}).get("due_date") or "").strip()[:10]
        if ds:
            try:
                if date.fromisoformat(ds) < today:
                    overdue_n += 1
            except ValueError:
                pass
    return open_n, overdue_n


def who_has_what_counts(assets: list[dict], *, overdue_days: int = 7) -> tuple[int, int, int]:
    rows = [a for a in (assets or []) if isinstance(a, dict) and asset_is_out(a)]
    n_out = len(rows)
    n_overdue = 0
    n_on_job = 0
    for r in rows:
        if str(r.get("assigned_job_id") or "").strip():
            n_on_job += 1
        dv = days_out_value(r.get("last_checkout_at"))
        if dv is not None and dv > overdue_days:
            n_overdue += 1
    return n_out, n_overdue, n_on_job


def kit_theft_metrics(
    assets: list[dict],
    kit_items: list[dict],
    replacements: list[dict],
) -> dict[str, int | float]:
    trailers = {
        str(a.get("id") or "").strip(): a
        for a in (assets or [])
        if isinstance(a, dict) and str(a.get("asset_type") or "").strip().lower() == "tool trailer"
    }
    if not trailers:
        return {"short_lines": 0, "replacements_90d": 0, "hot_items": 0, "missing_value": 0.0}
    tids = set(trailers.keys())
    lines = [
        it
        for it in (kit_items or [])
        if isinstance(it, dict)
        and str(it.get("parent_asset_id") or "").strip() in tids
        and bool((it or {}).get("is_active", True))
    ]
    now = datetime.now(timezone.utc).date()
    start = now - timedelta(days=_KIT_REPL_WINDOW_DAYS)
    repl_90: list[dict] = []
    for r in replacements or []:
        if not isinstance(r, dict):
            continue
        ds = str(r.get("replacement_date") or "").strip()[:10]
        if not ds:
            continue
        try:
            d = datetime.fromisoformat(ds).date()
        except ValueError:
            continue
        if d >= start:
            repl_90.append(r)
    c_item = Counter(str(r.get("kit_item_id") or "").strip() for r in repl_90 if str(r.get("kit_item_id") or "").strip())
    return {
        "short_lines": sum(1 for it in lines if kit_line_short_qty(it) > 0.0001),
        "replacements_90d": len(repl_90),
        "hot_items": sum(1 for v in c_item.values() if v >= _KIT_REPL_HOT_THRESHOLD),
        "missing_value": sum(kit_line_short_qty(it) * dash_kf(it.get("replacement_cost")) for it in lines),
    }


def task_progress_snapshot(
    *,
    today: date,
    packages: list[dict],
    package_tasks: list[dict],
    tasks: list[dict],
    photo_rows: list[dict],
    executions: list[dict],
) -> tuple[dict[str, Any], list[tuple[str, int]]]:
    ts = dashboard_dwp_snapshot(
        today=today,
        packages=list(packages or []),
        package_tasks=list(package_tasks or []),
        tasks=list(tasks or []),
        photo_rows=list(photo_rows or []),
    )
    repeat = repeated_eod_delay_reasons(
        packages=list(packages or []),
        executions=list(executions or []),
        today=today,
    )
    return ts, repeat


def margin_percentage(revenue: float, cost: float) -> float | None:
    if revenue <= 0:
        return None
    return max(-100.0, min(100.0, ((revenue - cost) / revenue) * 100.0))


def material_totals(rows: list[dict], *, amount_key: str = "amount") -> float:
    return sum(dash_kf((r or {}).get(amount_key)) for r in (rows or []) if isinstance(r, dict))


def revenue_totals(rows: list[dict], *, amount_key: str = "amount") -> float:
    return material_totals(rows, amount_key=amount_key)
