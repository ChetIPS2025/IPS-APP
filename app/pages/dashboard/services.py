"""Dashboard data loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import streamlit as st

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
    expenses: list[dict] = field(default_factory=list)
    po_rows: list[dict] = field(default_factory=list)
    customers: list[dict] = field(default_factory=list)
    time_entries: list[dict] = field(default_factory=list)


@st.cache_data(ttl=45, show_spinner=False)
def _load_tables_cached(
    session_key: str,
    use_admin: bool,
    load_inventory: bool,
) -> dict:
    out: dict = {
        "jobs": q.fetch_jobs(session_key, use_admin=use_admin),
        "estimates": q.fetch_estimates(session_key, use_admin=use_admin),
        "employees": q.fetch_employees(session_key, use_admin=use_admin),
        "assets": q.fetch_assets(session_key, use_admin=use_admin),
        "time_entries": q.fetch_time_entries(session_key, use_admin=use_admin),
        "expenses": q.fetch_job_expenses(session_key, use_admin=use_admin),
        "customers": q.fetch_customers(session_key, use_admin=use_admin),
        "inv_rows": q.fetch_inventory(session_key, use_admin=use_admin) if load_inventory else [],
    }
    if not out["expenses"]:
        out["po_rows"] = q.fetch_po_expenses(session_key, use_admin=use_admin)
    else:
        out["po_rows"] = out["expenses"]
    return out


def load_dashboard_tables(ctx: DashboardContext) -> DashboardTables:
    data = _load_tables_cached(
        ctx.session_key,
        ctx.use_admin,
        role_can_open_page(ctx.role, "Inventory"),
    )
    return DashboardTables(**data)
