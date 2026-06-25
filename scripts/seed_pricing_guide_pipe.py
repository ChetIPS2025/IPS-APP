#!/usr/bin/env python3
"""Idempotent seed: pipe materials (Stainless Steel, Carbon Steel, Aluminum)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.pricing_guide_pipe import (
    pipe_active_catalog_items,
    pipe_catalog_items,
    pipe_duplicate_price_review,
    pipe_requires_price_review,
    pipe_source_row_count,
)
from app.services.catalog_import_service import find_matching_pricing_item
from app.services.pricing_guide_service import (
    cached_pricing_guide_rows,
    clear_pricing_guide_cache,
    save_pricing_item,
)


def main() -> int:
    items = pipe_catalog_items()
    existing = cached_pricing_guide_rows(include_inactive=True)
    created = updated = flagged = 0
    for row in items:
        payload = {k: v for k, v in row.items() if not str(k).startswith("_")}
        if row.get("_requires_price_review"):
            flagged += 1
        match = find_matching_pricing_item(payload, existing)
        row_id = str(match.get("id") or "") if match else None
        ok, msg = save_pricing_item(payload, row_id=row_id, changed_by="seed_pipe")
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
    review = pipe_duplicate_price_review()
    missing = pipe_requires_price_review()
    active = pipe_active_catalog_items()
    print(
        f"Pipe seed complete: {created} created, {updated} updated, "
        f"{flagged} flagged inactive (missing price), "
        f"{pipe_source_row_count()} source rows -> {len(items)} catalog items "
        f"({len(active)} active priced)."
    )
    if missing:
        print("Missing-price records (inactive, not selectable in estimates):")
        for entry in missing:
            print(f"  - {entry['item_code']}: {entry['description']}")
    if review:
        print("Duplicate source prices preserved in item notes:")
        for entry in review:
            alts = ", ".join(f"${float(p):.2f}" for p in entry["alternate_source_prices"])
            print(
                f"  - {entry['item_code']}: active ${float(entry['active_price']):.2f}; "
                f"alternate source price(s): {alts}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
