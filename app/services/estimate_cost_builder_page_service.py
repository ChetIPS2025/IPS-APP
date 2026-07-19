"""Estimate Cost Builder category page loading and snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.estimate_cost_cache import (
    estimate_cost_data_version,
    read_cached_totals,
    write_cached_totals,
)
from app.services.estimate_costing_service import (
    calculate_estimate_totals,
    list_estimate_equipment_lines,
    list_estimate_labor_lines,
    list_estimate_material_lines,
    list_estimate_other_cost_lines,
    list_estimate_subcontractor_lines,
    list_estimate_travel_lines,
)

_ESTIMATE_COST_LINE_PAGE_SIZE = 25

_SECTION_LOADERS = {
    "materials": list_estimate_material_lines,
    "labor": list_estimate_labor_lines,
    "equipment": list_estimate_equipment_lines,
    "travel": list_estimate_travel_lines,
    "subcontractors": list_estimate_subcontractor_lines,
    "other_costs": list_estimate_other_cost_lines,
}


@dataclass(frozen=True)
class EstimateCostBuilderSnapshot:
    estimate_id: str
    active_section: str
    totals: dict[str, float]
    section_rows: list[dict[str, Any]]
    section_total_count: int
    cost_data_version: int
    page: int = 1
    page_size: int = _ESTIMATE_COST_LINE_PAGE_SIZE
    warning: str | None = None


def _estimate_tax_rate(est: dict[str, Any]) -> float:
    return float(est.get("tax_rate") or 0)


def _read_totals_for_estimate(estimate: dict[str, Any]) -> tuple[dict[str, float], str | None]:
    eid = str(estimate.get("id") or "").strip()
    tax_rate = _estimate_tax_rate(estimate)
    cached = read_cached_totals(eid, tax_rate=tax_rate)
    if cached:
        return cached, None

    stored_price = float(estimate.get("customer_price") or estimate.get("total") or 0)
    if stored_price > 0 and float(estimate.get("total_cost") or 0) > 0:
        totals = {
            "material_cost": float(estimate.get("material_cost") or 0),
            "labor_cost": float(estimate.get("labor_cost") or 0),
            "equipment_cost": float(estimate.get("equipment_cost") or 0),
            "travel_cost": float(estimate.get("travel_cost") or 0),
            "subcontractor_cost": float(estimate.get("subcontractor_cost") or 0),
            "other_cost": float(estimate.get("other_cost") or 0),
            "total_cost": float(estimate.get("total_cost") or 0),
            "customer_price": stored_price,
            "gross_profit": float(estimate.get("gross_profit") or 0),
            "gross_margin_percent": float(estimate.get("gross_margin_percent") or 0),
            "material_markup": float(estimate.get("material_markup") or 0),
            "labor_markup": float(estimate.get("labor_markup") or 0),
            "equipment_markup": float(estimate.get("equipment_markup") or 0),
            "travel_markup": float(estimate.get("travel_markup") or 0),
            "subcontractor_markup": float(estimate.get("subcontractor_markup") or 0),
            "other_markup": float(estimate.get("other_markup") or 0),
            "total_markup": float(estimate.get("total_markup") or 0),
            "subtotal_before_tax": float(estimate.get("subtotal_before_tax") or 0),
            "taxable_subtotal": float(estimate.get("taxable_subtotal") or 0),
            "tax_amount": float(estimate.get("tax_amount") or estimate.get("tax") or 0),
        }
        write_cached_totals(eid, tax_rate=tax_rate, totals=totals)
        return totals, None

    from app.perf_debug import perf_span

    with perf_span("estimate_builder.totals_read"):
        totals = calculate_estimate_totals(eid, tax_rate=tax_rate)
    write_cached_totals(eid, tax_rate=tax_rate, totals=totals)
    warning = None
    calc_price = float(totals.get("customer_price") or 0)
    if calc_price > 0 and stored_price > 0 and abs(stored_price - calc_price) > 0.01:
        warning = "Estimate totals may be out of date."
    return totals, warning


def load_estimate_cost_builder_snapshot(
    estimate: dict[str, Any],
    *,
    section: str,
    page: int = 1,
    page_size: int = _ESTIMATE_COST_LINE_PAGE_SIZE,
) -> EstimateCostBuilderSnapshot:
    from app.perf_debug import perf_span

    eid = str(estimate.get("id") or "").strip()
    section_key = str(section or "materials").strip().lower()
    version = estimate_cost_data_version(eid)
    cache_key = f"est_cb_snapshot:{eid}:{section_key}:v{version}:p{page}:s{page_size}"

    def _build() -> EstimateCostBuilderSnapshot:
        with perf_span(f"estimate_builder.snapshot.{section_key}"):
            totals, warning = _read_totals_for_estimate(estimate)
            loader = _SECTION_LOADERS.get(section_key)
            rows: list[dict[str, Any]] = []
            total_count = 0
            if loader and section_key != "summary":
                with perf_span(f"estimate_builder.{section_key}.query"):
                    rows, total_count = loader(
                        eid,
                        page=page,
                        page_size=page_size,
                    )
            return EstimateCostBuilderSnapshot(
                estimate_id=eid,
                active_section=section_key,
                totals=totals,
                section_rows=rows,
                section_total_count=total_count,
                cost_data_version=version,
                page=page,
                page_size=page_size,
                warning=warning,
            )

    return page_data_cache_get(cache_key, _build)


__all__ = [
    "EstimateCostBuilderSnapshot",
    "load_estimate_cost_builder_snapshot",
    "_ESTIMATE_COST_LINE_PAGE_SIZE",
]
