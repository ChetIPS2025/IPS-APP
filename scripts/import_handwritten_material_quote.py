#!/usr/bin/env python3
"""Import the handwritten material quote into an estimate or write an import template JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.estimate_material_quote_import import (
    apply_material_quote_to_estimate,
    build_handwritten_material_quote_template_json,
    build_material_quote_import_bundle,
    create_estimate_for_material_quote,
    material_quote_bundle_to_template,
)


def _print_summary(bundle) -> None:
    print(f"Template: {bundle.template_id}")
    print(f"Source rows: {bundle.source_row_count}")
    print(f"Import lines: {len(bundle.lines)}")
    print(f"Preliminary subtotal: ${bundle.preliminary_subtotal:,.2f}")
    print(f"Subtotal preliminary: {bundle.subtotal_is_preliminary}")
    if bundle.review_flags:
        print("Review flags:")
        for flag in bundle.review_flags:
            print(f"  - {flag}")
    print("Lines:")
    for line in bundle.lines:
        match = line.catalog_match_description or "— ad-hoc —"
        print(
            f"  {line.line_number:02d}. {line.description} | "
            f"qty={line.quantity} {line.unit} @ ${line.unit_cost} = ${line.total_cost} | "
            f"catalog={match}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-template",
        metavar="PATH",
        help="Write importable JSON template to PATH",
    )
    parser.add_argument(
        "--estimate-id",
        help="Apply lines to an existing estimate UUID",
    )
    parser.add_argument(
        "--create-estimate",
        action="store_true",
        help="Create a draft estimate (no customer) and import lines",
    )
    parser.add_argument(
        "--quote-number",
        default="",
        help="Optional quote number when creating a new estimate",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only; do not write or import",
    )
    args = parser.parse_args()

    bundle = build_material_quote_import_bundle()
    _print_summary(bundle)

    if args.dry_run and not args.write_template and not args.estimate_id and not args.create_estimate:
        return 0

    if args.write_template:
        path = Path(args.write_template)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_handwritten_material_quote_template_json(), encoding="utf-8")
        print(f"Wrote template: {path}")

    if args.dry_run:
        return 0

    if args.estimate_id:
        ok, msg, meta = apply_material_quote_to_estimate(args.estimate_id, bundle)
        print(msg)
        print(json.dumps(meta, indent=2))
        return 0 if ok else 1

    if args.create_estimate:
        ok, msg, estimate_id = create_estimate_for_material_quote(bundle, quote_number=args.quote_number)
        print(msg)
        if estimate_id:
            print(f"estimate_id={estimate_id}")
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
