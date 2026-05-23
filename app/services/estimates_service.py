"""
Estimates module — Supabase reads/writes and costing helpers.
"""

from __future__ import annotations

from app.services.estimate_costing_service import (
    DURATION_UNITS,
    LABOR_ROLE_TYPES,
    TRAVEL_TYPES,
    add_estimate_equipment,
    add_estimate_labor,
    add_estimate_material,
    add_estimate_other_cost,
    add_estimate_subcontractor,
    add_estimate_travel,
    calculate_estimate_totals,
    clear_estimate_cache,
    delete_estimate_equipment,
    delete_estimate_labor,
    delete_estimate_material,
    delete_estimate_other_cost,
    delete_estimate_subcontractor,
    delete_estimate_travel,
    get_default_terms,
    get_estimate_bundle,
    get_estimate_equipment,
    get_estimate_labor,
    get_estimate_materials,
    get_estimate_other_costs,
    get_estimate_subcontractors,
    get_estimate_travel,
    normalize_equipment_line,
    normalize_labor_line,
    normalize_material_line,
    normalize_other_cost_line,
    normalize_subcontractor_line,
    normalize_travel_line,
    recalculate_and_save_estimate_totals,
    update_estimate_equipment,
    update_estimate_labor,
    update_estimate_material,
    update_estimate_other_cost,
    update_estimate_subcontractor,
    update_estimate_travel,
)
from app.services.phase2_modules_service import (
    delete_estimate,
    delete_estimate_line_item,
    list_estimate_materials,
    list_estimates,
    normalize_estimate,
    save_estimate,
    save_estimate_line_item,
)
from app.services.proposal_pdf_service import (
    generate_estimate_proposal_pdf,
    generate_estimate_proposal_pdf_by_id,
)

__all__ = [
    "DURATION_UNITS",
    "LABOR_ROLE_TYPES",
    "TRAVEL_TYPES",
    "add_estimate_equipment",
    "add_estimate_labor",
    "add_estimate_material",
    "add_estimate_other_cost",
    "add_estimate_subcontractor",
    "add_estimate_travel",
    "calculate_estimate_totals",
    "clear_estimate_cache",
    "delete_estimate",
    "delete_estimate_equipment",
    "delete_estimate_labor",
    "delete_estimate_line_item",
    "delete_estimate_material",
    "delete_estimate_other_cost",
    "delete_estimate_subcontractor",
    "delete_estimate_travel",
    "generate_estimate_proposal_pdf",
    "generate_estimate_proposal_pdf_by_id",
    "get_default_terms",
    "get_estimate_bundle",
    "get_estimate_equipment",
    "get_estimate_labor",
    "get_estimate_materials",
    "get_estimate_other_costs",
    "get_estimate_subcontractors",
    "get_estimate_travel",
    "list_estimate_materials",
    "list_estimates",
    "normalize_equipment_line",
    "normalize_estimate",
    "normalize_labor_line",
    "normalize_material_line",
    "normalize_other_cost_line",
    "normalize_subcontractor_line",
    "normalize_travel_line",
    "recalculate_and_save_estimate_totals",
    "save_estimate",
    "save_estimate_line_item",
    "update_estimate_equipment",
    "update_estimate_labor",
    "update_estimate_material",
    "update_estimate_other_cost",
    "update_estimate_subcontractor",
    "update_estimate_travel",
]
