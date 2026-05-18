"""Dashboard page — Coastal-style executive layout."""

from __future__ import annotations

try:
    from app.auth import current_profile, current_role
except ImportError:
    from auth import current_profile, current_role  # type: ignore

from .coastal_layout import render_coastal_dashboard
from .services import DashboardContext, load_dashboard_tables


def render() -> None:
    prof = current_profile()
    sk = str(prof.get("id") or "anonymous")
    ctx = DashboardContext(
        session_key=sk,
        use_admin=current_role() in {"admin", "manager"},
        role=current_role(),
        user_id=str(prof.get("id") or "").strip(),
    )
    tables = load_dashboard_tables(ctx)
    render_coastal_dashboard(ctx, tables)
