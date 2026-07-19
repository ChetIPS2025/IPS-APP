"""Kit CSV and checklist exports (version-cached)."""

from __future__ import annotations

import csv
import io
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.asset_kits_service import kit_data_version

from app.components.asset_kit.state import kit_item_row_label


def export_kit_csv(items: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "Item",
            "Type",
            "Expected Qty",
            "Actual Qty",
            "Condition",
            "Status",
            "Unit Value",
            "Total Value",
            "Assigned To",
            "Serial",
        ]
    )
    for it in items:
        w.writerow(
            [
                it.get("item_name"),
                it.get("item_type"),
                it.get("quantity_expected"),
                it.get("quantity_actual"),
                it.get("condition"),
                it.get("status"),
                it.get("unit_value"),
                it.get("total_value"),
                it.get("assigned_to_name"),
                it.get("serial_number"),
            ]
        )
    return buf.getvalue().encode("utf-8")


def print_checklist_text(asset: dict, items: list[dict]) -> str:
    lines = [
        f"KIT CHECKLIST — {asset.get('asset_name') or ''} ({asset.get('asset_number') or ''})",
        f"Supervisor: {asset.get('assigned_to_name') or asset.get('operator') or '—'}",
        "",
        "Item | Serial | Exp | Act | Status | Condition",
        "-" * 72,
    ]
    for it in items:
        lines.append(
            f"{kit_item_row_label(it, items)} | {it.get('serial_number') or '—'} | "
            f"{it.get('quantity_expected')} | {it.get('quantity_actual')} | "
            f"{it.get('status')} | {it.get('condition')}"
        )
    return "\n".join(lines)


def get_kit_export_bytes(
    asset: dict,
    items: list[dict],
    *,
    export_kind: str,
) -> bytes:
    """Cache export bytes by kit data version — full kit list (not filtered)."""
    aid = str(asset.get("id") or "").strip()
    version = kit_data_version(aid)
    cache_key = f"kit_exports_{aid}_{export_kind}_v{version}"

    def _load() -> bytes:
        if export_kind == "csv":
            return export_kit_csv(items)
        return print_checklist_text(asset, items).encode("utf-8")

    return page_data_cache_get(cache_key, _load)
