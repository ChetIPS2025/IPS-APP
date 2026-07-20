"""Purchase list used to sync small hand tools and serialized tool values."""

from __future__ import annotations

from typing import Any, Literal

from app.data.hand_tools_purchase_list_batch2 import HAND_TOOLS_PURCHASE_ITEMS_BATCH2

TrackingMode = Literal["quantity", "serialized"]

# Qty and unit prices from the Jul 2026 purchase list batch 1 (52 units, $3,590.19 total).
HAND_TOOLS_PURCHASE_ITEMS_BATCH1: tuple[dict[str, Any], ...] = (
    {
        "tool_name": 'TEKTON 1-1/8" Combination Wrench',
        "model_number": "18268",
        "category": "Wrenches",
        "qty": 1,
        "unit_value": 21.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-3/16" Combination Wrench',
        "model_number": "18269",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 23.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-3/8" Combination Wrench',
        "model_number": "WCB23035",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 34.21,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-7/16" Combination Wrench',
        "model_number": "WCB23036",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 43.94,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-5/8" Combination Wrench',
        "model_number": "WCB23041",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 59.95,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-9/16" Combination Wrench',
        "model_number": "WCB23040",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 62.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-11/16" Combination Wrench',
        "model_number": "WCB23043",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 62.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-3/4" Combination Wrench',
        "model_number": "WCB23044",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 75.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-13/16" Combination Wrench',
        "model_number": "WCB23046",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 75.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-7/8" Combination Wrench',
        "model_number": "WCB23048",
        "category": "Wrenches",
        "qty": 1,
        "unit_value": 86.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 1-15/16" Combination Wrench',
        "model_number": "WCB23049",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 90.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'TEKTON 2" Combination Wrench',
        "model_number": "WCB23050",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 90.00,
        "tracking": "quantity",
    },
    {
        "tool_name": 'Klein Tools D507-6 Adjustable Wrench, 6-1/2"',
        "model_number": "D507-6",
        "category": "Wrenches",
        "qty": 4,
        "unit_value": 25.99,
        "tracking": "quantity",
    },
    {
        "tool_name": 'Klein Tools D507-8 Adjustable Wrench, 8"',
        "model_number": "D507-8",
        "category": "Wrenches",
        "qty": 4,
        "unit_value": 29.14,
        "tracking": "quantity",
    },
    {
        "tool_name": 'AUPREX 24" Heavy-Duty Chain Pipe Wrench',
        "model_number": "",
        "category": "Wrenches",
        "qty": 2,
        "unit_value": 37.99,
        "tracking": "quantity",
    },
    {
        "tool_name": "Strong Hand Tools PG114V Pipe Pliers, 11\"",
        "model_number": "PG114V",
        "category": "Pliers",
        "qty": 4,
        "unit_value": 31.82,
        "tracking": "quantity",
    },
    {
        "tool_name": 'SUNEX 538D 1" Drive Deep Impact Socket, 1-3/16"',
        "model_number": "538D",
        "category": "Sockets",
        "qty": 1,
        "unit_value": 40.56,
        "tracking": "quantity",
    },
    {
        "tool_name": 'SUNEX 542D 1" Drive Deep Impact Socket, 1-5/16"',
        "model_number": "542D",
        "category": "Sockets",
        "qty": 1,
        "unit_value": 26.99,
        "tracking": "quantity",
    },
    {
        "tool_name": 'SUNEX 1" Drive Deep Impact Socket, 1-7/16"',
        "model_number": "",
        "category": "Sockets",
        "qty": 1,
        "unit_value": 53.98,
        "tracking": "quantity",
    },
    {
        "tool_name": "Fluke 1AC II VoltAlert Non-Contact Voltage Tester",
        "model_number": "1AC II",
        "category": "Other",
        "qty": 2,
        "unit_value": 34.98,
        "tracking": "quantity",
    },
    {
        "tool_name": 'Fox Valley 12" Easy Marker Paint Pistol',
        "model_number": "",
        "category": "Other",
        "qty": 3,
        "unit_value": 38.95,
        "tracking": "quantity",
    },
    {
        "tool_name": "JET 3/4-Ton Lever Hoist, 15' Lift",
        "model_number": "JLP-075A-15",
        "category": "Other",
        "qty": 2,
        "unit_value": 252.00,
        "tracking": "serialized",
    },
    {
        "tool_name": 'Metabo WP 13-150 Quick 6" Angle Grinder',
        "model_number": "WP 13-150",
        "category": "Other",
        "qty": 2,
        "unit_value": 199.99,
        "tracking": "serialized",
    },
    {
        "tool_name": 'DEWALT DWE402W 4-1/2" Angle Grinder',
        "model_number": "DWE402W",
        "category": "Other",
        "qty": 2,
        "unit_value": 118.00,
        "tracking": "serialized",
    },
    {
        "tool_name": 'BOSCH RH328VC 1-1/8" SDS-plus Rotary Hammer',
        "model_number": "RH328VC",
        "category": "Other",
        "qty": 1,
        "unit_value": 229.00,
        "tracking": "serialized",
    },
    {
        "tool_name": "A2L Heat Pump Manifold with Dual Gauges and Hoses",
        "model_number": "",
        "category": "Other",
        "qty": 1,
        "unit_value": 151.89,
        "tracking": "serialized",
    },
)


HAND_TOOLS_PURCHASE_ITEMS = HAND_TOOLS_PURCHASE_ITEMS_BATCH1


def purchase_items_for_batch(batch: int | str | None = None) -> tuple[dict[str, Any], ...]:
    """Return purchase rows for batch 1, batch 2, or both combined."""
    key = str(batch or "1").strip().casefold()
    if key in {"1", "batch1", "batch-1"}:
        return HAND_TOOLS_PURCHASE_ITEMS_BATCH1
    if key in {"2", "batch2", "batch-2"}:
        return HAND_TOOLS_PURCHASE_ITEMS_BATCH2
    if key in {"all", "both", "combined"}:
        return HAND_TOOLS_PURCHASE_ITEMS_BATCH1 + HAND_TOOLS_PURCHASE_ITEMS_BATCH2
    return HAND_TOOLS_PURCHASE_ITEMS_BATCH1


def hand_tools_purchase_item_count(*, batch: int | str | None = None) -> int:
    return len(purchase_items_for_batch(batch))


def hand_tools_purchase_total_qty(*, batch: int | str | None = None) -> int:
    return sum(int(item.get("qty") or 0) for item in purchase_items_for_batch(batch))


def hand_tools_purchase_total_value(*, batch: int | str | None = None) -> float:
    return round(
        sum(
            float(item.get("unit_value") or 0) * int(item.get("qty") or 0)
            for item in purchase_items_for_batch(batch)
        ),
        2,
    )
