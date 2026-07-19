"""Dashboard snapshot loading, caching, and KPI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get

__all__ = [
    "DashboardSnapshot",
    "clear_dashboard_snapshot_cache",
    "dashboard_data_version_token",
    "load_dashboard_snapshot",
    "revenue_kpi_label",
]

_REMINDER_PROJECTION_COLUMNS = (
    "id,title,status,priority,assignee_name,assigned_to,assigned_to_email,"
    "assignee_email,assigned_to_employee_id,assignee_id,job_id,job_label,"
    "linked_job,due_date,created_at,updated_at"
)


@dataclass(frozen=True)
class DashboardSnapshot:
    period_start: date
    period_end: date
    active_jobs: int
    open_estimates: int
    employees_working_today: int
    my_todo_count: int
    open_invoices: float
    period_revenue: float
    inventory_value: float
    asset_value: float
    is_live: bool
    warnings: tuple[str, ...] = ()


def revenue_kpi_label(start: date, end: date, *, today: date | None = None) -> str:
    """Return a KPI card label that matches the selected reporting period."""
    ref = today or date.today()
    week_start = ref - timedelta(days=ref.weekday())
    week_end = week_start + timedelta(days=6)
    month_start = ref.replace(day=1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

    if start == week_start and end == week_end:
        return "Revenue This Week"
    if start == month_start and end in {month_end, ref}:
        return "Revenue This Month"
    return "Revenue for Period"


def dashboard_data_version_token() -> str:
    from app.pages._core._data import (
        assets_catalog_data_version,
        estimates_catalog_data_version,
        inventory_catalog_data_version,
        jobs_catalog_data_version,
        tasks_catalog_data_version,
        timekeeping_catalog_data_version,
    )

    return ":".join(
        str(part)
        for part in (
            jobs_catalog_data_version(),
            assets_catalog_data_version(),
            tasks_catalog_data_version(),
            estimates_catalog_data_version(),
            inventory_catalog_data_version(),
            timekeeping_catalog_data_version(),
        )
    )


def _profile_cache_id(profile: dict[str, Any]) -> str:
    for key in ("id", "employee_id", "email"):
        val = str(profile.get(key) or "").strip()
        if val:
            return val
    return "anonymous"


def _snapshot_cache_key(
    *,
    period_start: date,
    period_end: date,
    profile: dict[str, Any],
    role: str,
) -> str:
    from app.utils.view_as import view_as_mode

    user_id = _profile_cache_id(profile)
    role_key = str(role or "").strip().casefold()
    view_as = view_as_mode() if role_key else "default"
    version = dashboard_data_version_token()
    return (
        f"dashboard_snapshot:{period_start.isoformat()}:{period_end.isoformat()}:"
        f"{user_id}:{role_key}:{view_as}:{version}"
    )


def clear_dashboard_snapshot_cache(*, user_id: str | None = None) -> None:
    from app.pages._core.page_data_cache import (
        clear_dashboard_page_data_cache,
        clear_page_data_cache_prefix,
        clear_timekeeping_summaries_page_data_cache,
    )

    del user_id  # reserved for targeted invalidation; prefix clear covers all users
    clear_page_data_cache_prefix("dashboard_snapshot:")
    clear_page_data_cache_prefix("dashboard_panel_")
    clear_page_data_cache_prefix("dashboard_employees_today:")
    clear_page_data_cache_prefix("dashboard_todo_count:")
    clear_page_data_cache_prefix("dashboard_reminder_projection:")
    clear_dashboard_page_data_cache()
    clear_timekeeping_summaries_page_data_cache()


def _load_reminder_projections_uncached() -> list[dict[str, Any]]:
    from app.pages._core._data import _DEMO_TASKS
    from app.services.phase2_modules_service import list_reminder_task_projections

    rows, _used = list_reminder_task_projections(demo=list(_DEMO_TASKS))
    return rows


def _cached_reminder_projections() -> list[dict[str, Any]]:
    from app.pages._core._data import tasks_catalog_data_version

    cache_key = f"dashboard_reminder_projection:{tasks_catalog_data_version()}"
    return page_data_cache_get(cache_key, _load_reminder_projections_uncached)


def _count_todo_uncached(*, profile: dict[str, Any], role: str) -> int:
    from app.perf_debug import perf_span
    from app.services.management_reminders_service import count_dashboard_reminders

    with perf_span("dashboard.todo_count"):
        return count_dashboard_reminders(
            profile=profile,
            role=role,
            projections=_cached_reminder_projections(),
        )


def _count_employees_today_uncached(*, work_date: date) -> int:
    from app.perf_debug import perf_span
    from app.services.timekeeping_service import count_employees_working_on_date

    with perf_span("dashboard.employees_today"):
        count, _live = count_employees_working_on_date(work_date)
        return count


def _employees_today_cached(work_date: date) -> int:
    from app.pages._core._data import timekeeping_catalog_data_version

    cache_key = (
        f"dashboard_employees_today:{work_date.isoformat()}:"
        f"{timekeeping_catalog_data_version()}"
    )
    return page_data_cache_get(
        cache_key,
        lambda: _count_employees_today_uncached(work_date=work_date),
    )


def _todo_count_cached(*, profile: dict[str, Any], role: str) -> int:
    cache_key = (
        f"dashboard_todo_count:{_profile_cache_id(profile)}:"
        f"{str(role or '').casefold()}:{dashboard_data_version_token()}"
    )
    return page_data_cache_get(
        cache_key,
        lambda: _count_todo_uncached(profile=profile, role=role),
    )


def _load_dashboard_snapshot_uncached(
    *,
    period_start: date,
    period_end: date,
    profile: dict[str, Any],
    role: str,
    today: date,
) -> DashboardSnapshot:
    from app.perf_debug import perf_span

    warnings: list[str] = []

    with perf_span("dashboard.snapshot"):
        kpis: dict[str, Any] = {}
        with perf_span("dashboard.jobs_kpi"):
            try:
                from app.pages._core._data import load_dashboard_kpis

                kpis = load_dashboard_kpis(period_start=period_start, period_end=period_end)
            except Exception:
                warnings.append("Some job and estimate KPIs could not be loaded.")
                kpis = {}

        employees_today = 0
        try:
            employees_today = _employees_today_cached(today)
        except Exception:
            warnings.append("Employees working today is temporarily unavailable.")

        todo_count = 0
        try:
            todo_count = _todo_count_cached(profile=profile, role=role)
        except Exception:
            warnings.append("To-do count is temporarily unavailable.")

        is_live = bool(kpis.get("is_live"))
        if not is_live and not warnings:
            pass
        elif not is_live:
            warnings = tuple(dict.fromkeys(warnings))

        return DashboardSnapshot(
            period_start=period_start,
            period_end=period_end,
            active_jobs=int(kpis.get("active_jobs") or 0),
            open_estimates=int(kpis.get("open_estimates") or 0),
            employees_working_today=employees_today,
            my_todo_count=todo_count,
            open_invoices=float(kpis.get("open_invoices") or 0),
            period_revenue=float(kpis.get("total_sales") or 0),
            inventory_value=float(kpis.get("total_inventory_value") or 0),
            asset_value=float(kpis.get("total_asset_value") or 0),
            is_live=is_live,
            warnings=tuple(warnings),
        )


def load_dashboard_snapshot(
    *,
    period_start: date,
    period_end: date,
    profile: dict[str, Any],
    role: str,
    today: date | None = None,
    force_refresh: bool = False,
) -> DashboardSnapshot:
    """Load a user-aware dashboard KPI snapshot (cached per session)."""
    from app.perf_debug import perf_span

    ref_today = today or date.today()
    cache_key = _snapshot_cache_key(
        period_start=period_start,
        period_end=period_end,
        profile=profile,
        role=role,
    )

    if force_refresh:
        from app.pages._core.page_data_cache import clear_page_data_cache_key

        clear_page_data_cache_key(cache_key)

    with perf_span("dashboard.snapshot"):
        return page_data_cache_get(
            cache_key,
            lambda: _load_dashboard_snapshot_uncached(
                period_start=period_start,
                period_end=period_end,
                profile=profile,
                role=role,
                today=ref_today,
            ),
        )
