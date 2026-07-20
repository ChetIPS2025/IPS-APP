"""Authoritative Dashboard asset value breakdown across Equipment, Serialized Tools, and Small Tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.asset_classification_service import is_equipment_tab_asset
from app.services.serialized_tool_service import is_serialized_tool_asset
from app.services.small_hand_tool_service import (
    SmallHandToolsValueSummary,
    get_small_hand_tools_value_summary,
)


@dataclass(frozen=True)
class AssetValueBreakdown:
    equipment_value: float
    serialized_tools_value: float
    small_tools_value: float
    total_asset_value: float
    equipment_count: int
    serialized_tools_count: int
    small_tools_count: int
    small_tools_missing_value_count: int = 0


def _classify_catalog_assets(
    assets: list[dict[str, Any]],
) -> tuple[float, float, int, int, set[str]]:
    """Split active asset rows into Equipment and Serialized Tools subtotals."""
    from app.services.dashboard_metrics_service import _asset_row_active, _asset_row_value

    equipment_value = 0.0
    serialized_value = 0.0
    equipment_count = 0
    serialized_count = 0
    counted_asset_ids: set[str] = set()

    seen_ids: set[str] = set()
    for row in assets:
        if not isinstance(row, dict) or not _asset_row_active(row):
            continue
        asset_id = str(row.get("id") or "").strip()
        if not asset_id or asset_id in seen_ids:
            continue
        seen_ids.add(asset_id)

        value = _asset_row_value(row)
        if is_serialized_tool_asset(row):
            serialized_value += value
            serialized_count += 1
            counted_asset_ids.add(asset_id)
        elif is_equipment_tab_asset(row):
            equipment_value += value
            equipment_count += 1
            counted_asset_ids.add(asset_id)

    return (
        round(equipment_value, 2),
        round(serialized_value, 2),
        equipment_count,
        serialized_count,
        counted_asset_ids,
    )


def calculate_asset_value_breakdown(
    assets: list[dict[str, Any]],
    *,
    small_tools_summary: SmallHandToolsValueSummary,
) -> AssetValueBreakdown:
    """Combine classified asset subtotals with the Small Tools monetary aggregate."""
    equipment_value, serialized_value, equipment_count, serialized_count, _ = _classify_catalog_assets(
        assets
    )
    small_tools_value = round(float(small_tools_summary.total_value), 2)
    total_asset_value = round(equipment_value + serialized_value + small_tools_value, 2)
    return AssetValueBreakdown(
        equipment_value=equipment_value,
        serialized_tools_value=serialized_value,
        small_tools_value=small_tools_value,
        total_asset_value=total_asset_value,
        equipment_count=equipment_count,
        serialized_tools_count=serialized_count,
        small_tools_count=int(small_tools_summary.tool_type_count),
        small_tools_missing_value_count=int(small_tools_summary.missing_value_count),
    )


def compute_asset_value_breakdown(
    assets: list[dict[str, Any]],
    *,
    include_kit_items: bool = True,
) -> AssetValueBreakdown:
    """Load Small Tools value and return the full Dashboard breakdown."""
    _, _, _, _, counted_asset_ids = _classify_catalog_assets(assets)
    small_tools_summary = get_small_hand_tools_value_summary(
        excluded_asset_ids=counted_asset_ids,
        include_kit_items=include_kit_items,
    )
    return calculate_asset_value_breakdown(assets, small_tools_summary=small_tools_summary)


def asset_value_breakdown_caption(breakdown: AssetValueBreakdown) -> str:
    """Compact caption for the Dashboard Asset Value card."""
    from app.utils.formatting import fmt_currency

    return (
        f"Equipment: {fmt_currency(breakdown.equipment_value)} · "
        f"Serialized Tools: {fmt_currency(breakdown.serialized_tools_value)} · "
        f"Small Tools: {fmt_currency(breakdown.small_tools_value)}"
    )


def asset_value_breakdown_title(breakdown: AssetValueBreakdown) -> str:
    """Accessible title summarizing category counts and missing-value tools."""
    parts = [
        f"{breakdown.equipment_count} equipment",
        f"{breakdown.serialized_tools_count} serialized tools",
        f"{breakdown.small_tools_count} small tool lines",
    ]
    title = ", ".join(parts)
    if breakdown.small_tools_missing_value_count:
        title += f"; {breakdown.small_tools_missing_value_count} small tool(s) missing unit value"
    return title


__all__ = [
    "AssetValueBreakdown",
    "asset_value_breakdown_caption",
    "asset_value_breakdown_title",
    "calculate_asset_value_breakdown",
    "compute_asset_value_breakdown",
]
