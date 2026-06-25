#!/usr/bin/env python3
"""Idempotent seed: plate materials (Stainless Steel, Aluminum, Carbon Steel)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.pricing_guide_plate import (
    plate_catalog_items,
    plate_duplicate_price_review,
    plate_source_row_count,
)
from app.services.catalog_import_service import find_matching_pricing_item
from app.services.pricing_guide_service import (
    cached_pricing_guide_rows,
    clear_pricing_guide_cache,
    save_pricing_item,
)


def main() -> int:
    items = plate_catalog_items()
    existing = cached_pricing_guide_rows(include_inactive=True)
    created = updated = 0
    for row in items:
        payload = {k: v for k, v in row.items() if not str(k).startswith("_")}
        match = find_matching_pricing_item(payload, existing)
        row_id = str(match.get("id") or "") if match else None
        ok, msg = save_pricing_item(payload, row_id=row_id, changed_by="seed_plate")
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
    review = plate_duplicate_price_review()
    print(
        f"Plate seed complete: {created} created, {updated} updated, "
        f"{plate_source_row_count()} source rows -> {len(items)} catalog items."
    )
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
