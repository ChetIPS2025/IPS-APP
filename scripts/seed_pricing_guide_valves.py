#!/usr/bin/env python3
"""Idempotent seed: valves and Y-strainers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.pricing_guide_valves import (
    valves_active_catalog_items,
    valves_catalog_items,
    valves_source_row_count,
)
from app.services.catalog_import_service import find_matching_pricing_item
from app.services.pricing_guide_service import (
    cached_pricing_guide_rows,
    clear_pricing_guide_cache,
    save_pricing_item,
)


def main() -> int:
    items = valves_catalog_items()
    existing = cached_pricing_guide_rows(include_inactive=True)
    created = updated = 0
    for row in items:
        payload = {k: v for k, v in row.items() if not str(k).startswith("_")}
        match = find_matching_pricing_item(payload, existing)
        row_id = str(match.get("id") or "") if match else None
        ok, msg = save_pricing_item(payload, row_id=row_id, changed_by="seed_valves")
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
    active = valves_active_catalog_items()
    print(
        f"Valves seed complete: {created} created, {updated} updated, "
        f"{valves_source_row_count()} source rows -> {len(items)} catalog items "
        f"({len(active)} active priced)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
