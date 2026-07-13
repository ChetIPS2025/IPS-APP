#!/usr/bin/env python3
"""Idempotent seed: building materials, tools, and electrical catalog items."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.pricing_guide_misc_catalog import (
    misc_catalog_items,
    misc_catalog_source_row_count,
)
from app.services.catalog_import_service import find_matching_pricing_item
from app.services.pricing_guide_service import (
    clear_pricing_guide_cache,
    save_pricing_item,
)


def _pricing_rows_for_matching() -> list[dict]:
    """All pricing guide rows (including asset-linked rows hidden from PG list views)."""
    from app.db import fetch_table_admin
    rows = list(fetch_table_admin("pricing_guide_items", limit=10000) or [])
    return [r for r in rows if isinstance(r, dict)]


def main() -> int:
    items = misc_catalog_items()
    clear_pricing_guide_cache()
    existing = _pricing_rows_for_matching()
    created = updated = 0
    for row in items:
        payload = {k: v for k, v in row.items() if not str(k).startswith("_")}
        match = find_matching_pricing_item(payload, existing)
        row_id = str(match.get("id") or "") if match else None
        ok, msg = save_pricing_item(
            payload,
            row_id=row_id,
            changed_by="seed_misc_catalog",
        )
        if not ok:
            print(f"FAIL {payload.get('item_code')}: {msg}", file=sys.stderr)
            return 1
        if row_id:
            updated += 1
        else:
            created += 1
            if match is None:
                existing.append({"id": payload.get("id"), **payload})

    clear_pricing_guide_cache()
    print(
        "Misc catalog seed complete: "
        f"{created} created, {updated} updated, "
        f"{misc_catalog_source_row_count()} source rows -> {len(items)} catalog items."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
