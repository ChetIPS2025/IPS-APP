"""Estimate materials — line items and summary."""

When an estimate is loaded (``loaded_estimate_id`` / ``selected_estimate_id`` in
session state) this page renders a full estimate detail UI with:

  • Breadcrumb header
  • Estimate title / status / project / customer header with action buttons
  • Estimate info summary card (client, job, dates, prepared-by, total)
  • Horizontal navigation tabs (Overview, Materials active, Labor, Equipment, …)
  • Materials table with search, add controls, group-by, inline edit/delete
  • Right-side Materials Summary card with markup controls
  • Material Notes card and Linked Documents card

When no estimate is loaded the page falls back to the original catalog management
view so the existing workflow (import from inventory, add/edit catalog items) is
always accessible from the sidebar.
"""
from __future__ import annotations

try:
    from app.pages._import_render import load_render
except ImportError:
    from pages._import_render import load_render  # type: ignore

render = load_render("estimate_materials")

__all__ = ["render"]
