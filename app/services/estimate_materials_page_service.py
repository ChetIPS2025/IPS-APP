"""Estimate Materials page data: paginated lines, summary, detail, and export."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.estimate_cost_cache import estimate_cost_data_version
from app.services.estimate_costing_service import (
    get_estimate_materials,
    normalize_material_line,
    update_estimate_material,
)
from app.services.estimate_cost_builder_page_service import load_estimate_cost_builder_snapshot

_ESTIMATE_MATERIAL_PAGE_SIZE = 25
_EXPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class EstimateMaterialLinesPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    search: str


@dataclass(frozen=True)
class EstimateMaterialsSummary:
    material_cost: float
    material_markup: float
    material_price: float
    taxable_material_subtotal: float
    material_tax: float
    tax_rate: float
    customer_price: float


def normalize_estimate_material_line(row: dict[str, Any], estimate_id: str = "") -> dict[str, Any]:
    return normalize_material_line(row, estimate_id)


def _filter_material_rows(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    query = str(search or "").strip().casefold()
    if not query:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        hay = " ".join(
            str(row.get(k) or "")
            for k in ("item_number", "sku", "description", "category", "vendor")
        ).casefold()
        if query in hay:
            out.append(row)
    return out


def list_estimate_material_lines_page(
    estimate_id: str,
    *,
    search: str = "",
    page: int = 1,
    page_size: int = _ESTIMATE_MATERIAL_PAGE_SIZE,
    demo: list[dict[str, Any]] | None = None,
) -> EstimateMaterialLinesPage:
    from app.perf_debug import perf_span

    eid = str(estimate_id or "").strip()
    pg = max(1, int(page or 1))
    size = max(1, min(200, int(page_size or _ESTIMATE_MATERIAL_PAGE_SIZE)))
    version = estimate_cost_data_version(eid)
    cache_key = f"est_mat_lines:{eid}:v{version}:q{search}:p{pg}:s{size}"

    def _build() -> EstimateMaterialLinesPage:
        with perf_span("estimate_materials.list_query"):
            rows, _ = get_estimate_materials(eid, demo=demo)
            filtered = _filter_material_rows(rows, search)
            total = len(filtered)
            start = (pg - 1) * size
            page_rows = filtered[start : start + size]
            return EstimateMaterialLinesPage(
                rows=page_rows,
                total_count=total,
                page=pg,
                page_size=size,
                search=str(search or ""),
            )

    return page_data_cache_get(cache_key, _build)


def get_estimate_materials_summary(
    estimate: dict[str, Any],
    *,
    demo_materials: list[dict[str, Any]] | None = None,
) -> EstimateMaterialsSummary:
    from app.perf_debug import perf_span

    eid = str(estimate.get("id") or "").strip()
    tax_rate = float(estimate.get("tax_rate") or 0)
    version = estimate_cost_data_version(eid)
    cache_key = f"est_mat_summary:{eid}:v{version}:t{tax_rate}"

    def _build() -> EstimateMaterialsSummary:
        with perf_span("estimate_materials.summary"):
            snapshot = load_estimate_cost_builder_snapshot(estimate, section="summary")
            totals = snapshot.totals
            from app.services.estimate_costing_service import calculate_estimate_totals

            calc = calculate_estimate_totals(eid, tax_rate=tax_rate, demo_materials=demo_materials)
            material_cost = float(totals.get("material_cost") or calc.get("material_cost") or 0)
            material_markup = float(totals.get("material_markup") or calc.get("material_markup") or 0)
            material_price = material_cost + material_markup
            taxable = float(calc.get("taxable_subtotal") or totals.get("taxable_subtotal") or 0)
            materials_only_taxable = _taxable_material_subtotal(eid, demo=demo_materials)
            total_tax = float(totals.get("tax_amount") or calc.get("tax_amount") or 0)
            material_tax = 0.0
            if taxable > 0 and materials_only_taxable > 0:
                material_tax = total_tax * (materials_only_taxable / taxable)
            return EstimateMaterialsSummary(
                material_cost=material_cost,
                material_markup=material_markup,
                material_price=material_price,
                taxable_material_subtotal=materials_only_taxable,
                material_tax=material_tax,
                tax_rate=tax_rate,
                customer_price=float(totals.get("customer_price") or calc.get("customer_price") or 0),
            )

    return page_data_cache_get(cache_key, _build)


def _taxable_material_subtotal(
    estimate_id: str,
    *,
    demo: list[dict[str, Any]] | None = None,
) -> float:
    rows, _ = get_estimate_materials(estimate_id, demo=demo)
    total = 0.0
    for row in rows:
        if row.get("taxable", True):
            total += float(row.get("price_total") or 0)
    return total


def get_estimate_material_line_detail(
    estimate_id: str,
    line_id: str,
) -> dict[str, Any] | None:
    from app.perf_debug import perf_span

    eid = str(estimate_id or "").strip()
    lid = str(line_id or "").strip()
    if not eid or not lid:
        return None
    version = estimate_cost_data_version(eid)
    cache_key = f"est_mat_detail:{eid}:{lid}:v{version}"

    def _build() -> dict[str, Any] | None:
        with perf_span("estimate_materials.detail_lookup"):
            rows, _ = get_estimate_materials(eid)
            for row in rows:
                if str(row.get("id") or "") == lid:
                    return normalize_material_line(row, eid)
            return None

    return page_data_cache_get(cache_key, _build)


def update_estimate_material_line(line_id: str, payload: dict[str, Any]) -> Any:
    return update_estimate_material(line_id, payload)


def _export_cache_key(estimate_id: str, search: str) -> str:
    version = estimate_cost_data_version(estimate_id)
    return f"est_mat_export:{estimate_id}:v{version}:q{search}:s{_EXPORT_SCHEMA_VERSION}"


def clear_prepared_material_export(estimate_id: str) -> None:
    try:
        import streamlit as st

        prefix = f"est_mat_export_ready_{estimate_id}"
        for key in list(st.session_state.keys()):
            if str(key).startswith(prefix):
                st.session_state.pop(key, None)
    except Exception:
        pass


def prepare_material_export_bytes(
    estimate_id: str,
    *,
    search: str = "",
    demo: list[dict[str, Any]] | None = None,
) -> bytes:
    from app.perf_debug import perf_span

    eid = str(estimate_id or "").strip()
    cache_key = _export_cache_key(eid, search)

    def _build() -> bytes:
        with perf_span("estimate_materials.export"):
            rows, _ = get_estimate_materials(eid, demo=demo)
            filtered = _filter_material_rows(rows, search)
            buf = io.StringIO()
            fieldnames = [
                "item_number",
                "description",
                "category",
                "quantity",
                "unit",
                "unit_cost",
                "cost_total",
                "markup_percent",
                "price_total",
                "taxable",
                "vendor",
            ]
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in filtered:
                norm = normalize_material_line(row, eid)
                writer.writerow(
                    {
                        "item_number": norm.get("item_number") or norm.get("sku"),
                        "description": norm.get("description"),
                        "category": norm.get("category"),
                        "quantity": norm.get("quantity"),
                        "unit": norm.get("unit"),
                        "unit_cost": norm.get("unit_cost"),
                        "cost_total": norm.get("cost_total"),
                        "markup_percent": norm.get("markup_percent"),
                        "price_total": norm.get("price_total"),
                        "taxable": norm.get("taxable"),
                        "vendor": norm.get("vendor"),
                    }
                )
            return buf.getvalue().encode("utf-8")

    return page_data_cache_get(cache_key, _build)


def invalidate_estimate_materials_page_cache(estimate_id: str) -> None:
    clear_prepared_material_export(estimate_id)
    try:
        from app.services.estimate_cost_cache import invalidate_estimate_cost_cache

        invalidate_estimate_cost_cache(estimate_id)
    except Exception:
        pass


__all__ = [
    "EstimateMaterialLinesPage",
    "EstimateMaterialsSummary",
    "_ESTIMATE_MATERIAL_PAGE_SIZE",
    "_EXPORT_SCHEMA_VERSION",
    "clear_prepared_material_export",
    "get_estimate_material_line_detail",
    "get_estimate_materials_summary",
    "invalidate_estimate_materials_page_cache",
    "list_estimate_material_lines_page",
    "normalize_estimate_material_line",
    "prepare_material_export_bytes",
    "update_estimate_material_line",
]
