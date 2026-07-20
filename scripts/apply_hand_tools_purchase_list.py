#!/usr/bin/env python3
"""Apply the Jul 2026 hand-tools purchase list to Small Hand Tools and Serialized Tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.hand_tools_purchase_list import (
    hand_tools_purchase_item_count,
    hand_tools_purchase_total_qty,
    hand_tools_purchase_total_value,
)
from app.services.hand_tools_purchase_sync_service import sync_hand_tools_purchase_list


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview matches and actions without writing to the database.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full sync summary as JSON.",
    )
    args = parser.parse_args()

    print(
        f"Purchase list: {hand_tools_purchase_item_count()} line items, "
        f"{hand_tools_purchase_total_qty()} units, "
        f"${hand_tools_purchase_total_value():,.2f} extended."
    )
    if args.dry_run:
        print("Dry run — no database writes.")

    result = sync_hand_tools_purchase_list(dry_run=args.dry_run)
    summary = result.data or {}

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(
            f"Hand tools: {summary.get('hand_tools_created', 0)} created, "
            f"{summary.get('hand_tools_updated', 0)} updated."
        )
        print(
            f"Serialized tools: {summary.get('serialized_updated', 0)} asset value(s) updated; "
            f"{summary.get('serialized_not_found', 0)} line(s) unmatched."
        )
        for warning in summary.get("warnings") or []:
            print(f"WARN: {warning}")
        for err in summary.get("errors") or []:
            print(f"ERROR: {err}", file=sys.stderr)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
