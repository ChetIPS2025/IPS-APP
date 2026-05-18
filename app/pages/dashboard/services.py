"""Dashboard data loading with caching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from . import calculations as calc
from . import queries as q

try:
    from app.ui import role_can_open_page
except ImportError:
    from ui import role_can_open_page  # type: ignore


@dataclass
class DashboardContext:
    session_key: str
    use_admin: bool
    role: str
    user_id: str
    today: date = field(default_factory=date.today)


@dataclass
class DashboardTables:
    jobs: list[dict] = field(default_factory=list)
    estimates: list[dict] = field(default_factory=list)
    employees: list[dict] = field(default_factory=list)
    assets: list[dict] = field(default_factory=list)
    inv_rows: list[dict] = field(default_factory=list)
    todos: list[dict] = field(default_factory=list)
    job_tasks: list[dict] = field(default_factory=list)
    time_entries: list[dict] = field(default_factory=list)
    po_rows: list[dict] = field(default_factory=list)
    expenses: list[dict] = field(default_factory=list)
    customers: list[dict] = field(default_factory=list)
    company_updates: list[dict] = field(default_factory=list)
    company_update_reads: list[dict] = field(default_factory=list)
    kit_items: list[dict] = field(default_factory=list)
    kit_replacements: list[dict] = field(default_factory=list)
    dwp_packages: list[dict] | None = None
    dwp_package_tasks: list[dict] | None = None
    dwp_executions: list[dict] | None = None
    dwp_photo_rows: list[dict] | None = None


def load_core_tables(
    session_key: str,
    use_admin: bool,
    role: str,
    *,
    load_inventory: bool,
    load_pos: bool,
    load_company_updates: bool,
    load_kit: bool,
) -> dict[str, Any]:
    """Cached read bundle for dashboard KPIs and primary panels."""
    tables = DashboardTables()
    tables.jobs = q.fetch_jobs(session_key, use_admin=use_admin)
    tables.estimates = q.fetch_estimates(session_key, use_admin=use_admin)
    tables.employees = q.fetch_employees(session_key, use_admin=use_admin)
    tables.assets = q.fetch_assets(session_key, use_admin=use_admin)
    tables.todos = q.fetch_todos(session_key, use_admin=use_admin)
    tables.job_tasks = q.fetch_job_tasks(session_key, use_admin=use_admin)
    tables.time_entries = q.fetch_time_entries(session_key, use_admin=use_admin)
    if load_inventory:
        tables.inv_rows = q.fetch_inventory(session_key, use_admin=use_admin)
    tables.expenses = q.fetch_job_expenses(session_key, use_admin=use_admin)
    if not tables.expenses:
        tables.po_rows = q.fetch_po_expenses(session_key, use_admin=use_admin) if load_pos else []
    else:
        tables.po_rows = tables.expenses
    tables.customers = q.fetch_customers(session_key, use_admin=use_admin)
    if load_company_updates:
        tables.company_updates = q.fetch_company_updates(session_key, use_admin=use_admin)
        tables.company_update_reads = q.fetch_company_update_reads(session_key, use_admin=use_admin)
    if load_kit:
        tables.kit_items = q.fetch_asset_kit_items(session_key, use_admin=use_admin)
        tables.kit_replacements = q.fetch_asset_kit_replacements(session_key, use_admin=use_admin)
    return {
        "jobs": tables.jobs,
        "estimates": tables.estimates,
        "employees": tables.employees,
        "assets": tables.assets,
        "inv_rows": tables.inv_rows,
        "todos": tables.todos,
        "job_tasks": tables.job_tasks,
        "time_entries": tables.time_entries,
        "po_rows": tables.po_rows,
        "expenses": tables.expenses,
        "customers": tables.customers,
        "company_updates": tables.company_updates,
        "company_update_reads": tables.company_update_reads,
        "kit_items": tables.kit_items,
        "kit_replacements": tables.kit_replacements,
    }


def load_dashboard_tables(ctx: DashboardContext) -> DashboardTables:
    role = ctx.role
    data = load_core_tables(
        ctx.session_key,
        ctx.use_admin,
        role,
        load_inventory=role_can_open_page(role, "Inventory"),
        load_pos=role_can_open_page(role, "PO / Expenses"),
        load_company_updates=role_can_open_page(role, "Company Updates"),
        load_kit=role_can_open_page(role, "Asset Database"),
    )
    return DashboardTables(**data)


def load_task_progress_tables(
    session_key: str,
    use_admin: bool,
    *,
    job_tasks: list[dict] | None = None,
) -> dict[str, list[dict]]:
    """DWP snapshot tables; reuses ``job_tasks`` from core load when provided."""
    return {
        "tasks": job_tasks
        if job_tasks is not None
        else q.fetch_job_tasks(session_key, use_admin=use_admin, limit=12000),
        "packages": q.fetch_daily_work_packages(session_key, use_admin=use_admin),
        "package_tasks": q.fetch_daily_work_package_tasks(session_key, use_admin=use_admin),
        "executions": q.fetch_supervisor_daily_execution(session_key, use_admin=use_admin),
        "photo_rows": q.fetch_task_photos_merged(session_key, use_admin=use_admin),
    }


def build_kpi_specs(tables: DashboardTables, ctx: DashboardContext) -> list[dict]:
    open_todos, overdue_todos = calc.todo_open_overdue_counts(tables.todos, today=ctx.today)
    low_n = calc.count_low_stock(tables.inv_rows)
    specs: list[dict] = [
        {
            "label": "Active Jobs",
            "value": f"{calc.count_active_jobs(tables.jobs):,}",
            "key": "jobs",
            "nav_page": "Job Database",
        },
        {
            "label": "Draft Estimates",
            "value": f"{calc.count_draft_estimates(tables.estimates):,}",
            "key": "draft_est",
            "nav_page": "Estimates",
        },
        {
            "label": "Awarded (month)",
            "value": f"{calc.count_awarded_jobs_this_month(tables.jobs, today=ctx.today):,}",
            "key": "awarded",
            "nav_page": "Job Database",
        },
        {
            "label": "Open Tasks",
            "value": f"{calc.count_open_job_tasks(tables.job_tasks):,}",
            "key": "tasks",
            "nav_page": "Assign Tasks (PM)",
        },
        {"label": "Overdue Tasks", "value": f"{overdue_todos:,}", "key": "od_todo"},
        {"label": "Low Stock", "value": f"{low_n:,}", "key": "low", "nav_page": "Inventory"},
        {
            "label": "Labor Hrs Today",
            "value": f"{calc.labor_hours_for_date(tables.time_entries, work_date=ctx.today.isoformat()):.1f}",
            "key": "labor",
            "nav_page": "Time Tracking",
        },
    ]
    if role_can_open_page(ctx.role, "PO / Expenses"):
        specs.append(
            {
                "label": "Pending POs",
                "value": f"{calc.count_pending_pos(tables.po_rows):,}",
                "key": "po",
                "nav_page": "PO / Expenses",
            }
        )
    if role_can_open_page(ctx.role, "Company Updates"):
        specs.append(
            {
                "label": "Unread Updates",
                "value": f"{calc.count_unread_company_updates(tables.company_updates, tables.company_update_reads, user_id=ctx.user_id):,}",
                "key": "cu",
                "nav_page": "Company Updates",
            }
        )
    return specs


def dashboard_has_any_data(tables: DashboardTables) -> bool:
    return bool(
        tables.jobs
        or tables.estimates
        or tables.employees
        or tables.assets
        or tables.inv_rows
        or tables.todos
    )
