#!/usr/bin/env python3
"""Idempotent seed: I-beam and related structural steel (Carbon Steel)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.pricing_guide_i_beam import (
    i_beam_alias_pairs,
    i_beam_catalog_items,
    i_beam_price_review_items,
    i_beam_source_row_count,
)
from app.services.catalog_import_service import find_matching_pricing_item
from app.services.pricing_guide_service import (
    cached_pricing_guide_rows,
    clear_pricing_guide_cache,
    save_pricing_item,
)


def main() -> int:
    items = i_beam_catalog_items()
    existing = cached_pricing_guide_rows(include_inactive=True)
    created = updated = flagged = 0
    for row in items:
        payload = {k: v for k, v in row.items() if not str(k).startswith("_")}
        if row.get("_requires_price_review"):
            flagged += 1
        match = find_matching_pricing_item(payload, existing)
        row_id = str(match.get("id") or "") if match else None
        ok, msg = save_pricing_item(payload, row_id=row_id, changed_by="seed_i_beam")
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
    aliases = i_beam_alias_pairs()
    review = i_beam_price_review_items()
    print(
        f"I-beam seed complete: {created} created, {updated} updated, "
        f"{flagged} flagged for price verification, "
        f"{len(aliases)} alias pair(s), "
        f"{i_beam_source_row_count()} source rows -> {len(items)} catalog items."
    )
    if aliases:
        print("BEAM/I-BEAM alias pairs (separate catalog records, cross-referenced in notes):")
        for entry in aliases:
            print(
                f"  - {entry['shape_key']}: {entry['beam_item_code']} / {entry['ibeam_item_code']} "
                f"@ ${float(entry['price']):.2f}"
            )
    if review:
        print("Price verification flagged (active price unchanged):")
        for entry in review:
            print(f"  - {entry['item_code']}: ${float(entry['active_price']):.2f} — {entry['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
