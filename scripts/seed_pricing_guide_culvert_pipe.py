#!/usr/bin/env python3
"""Idempotent seed: culvert pipe sections."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.pricing_guide_culvert_pipe import (
    culvert_pipe_catalog_items,
    culvert_pipe_source_row_count,
)
from app.services.catalog_import_service import find_matching_pricing_item
from app.services.pricing_guide_service import (
    cached_pricing_guide_rows,
    clear_pricing_guide_cache,
    save_pricing_item,
)


def main() -> int:
    items = culvert_pipe_catalog_items()
    existing = cached_pricing_guide_rows(include_inactive=True)
    created = updated = 0
    for row in items:
        match = find_matching_pricing_item(row, existing)
        row_id = str(match.get("id") or "") if match else None
        ok, msg = save_pricing_item(row, row_id=row_id, changed_by="seed_culvert_pipe")
        if not ok:
            print(f"FAIL {row.get('item_code')}: {msg}", file=sys.stderr)
            return 1
        if row_id:
            updated += 1
        else:
            created += 1
            if match is None:
                existing.append({"id": row.get("id"), **row})

    clear_pricing_guide_cache()
    print(
        f"Culvert pipe seed complete: {created} created, {updated} updated, "
        f"{culvert_pipe_source_row_count()} source rows -> {len(items)} catalog items."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
