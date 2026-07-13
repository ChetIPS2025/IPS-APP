"""Catalog import image review — manual approve / replace / skip before attach."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.catalog_import_service import (
    find_matching_asset_item,
    find_matching_inventory_item,
    find_matching_pricing_item,
    import_catalog_csv,
    normalize_item_class,
    _fetch_all,
)
from app.services.item_images import (
    IMAGE_STATUS_APPROVED,
    IMAGE_STATUS_MISSING,
    build_uploaded_image_index,
    find_image_match_for_row,
    is_image_approved,
    persist_item_image,
    save_approved_local_image,
)
DECISION_PENDING = "pending"
DECISION_APPROVE = "approve"
DECISION_SKIP = "skip"
DECISION_REPLACE = "replace"

REVIEW_DECISIONS = (DECISION_PENDING, DECISION_APPROVE, DECISION_SKIP, DECISION_REPLACE)


@dataclass
class ImportImageReviewRow:
    row_index: int
    row: dict[str, Any]
    description: str
    model_number: str
    item_number: str
    sku: str
    item_class: str
    match_filename: str = ""
    match_field: str = ""
    confidence: str = "none"
    suggested_bytes: bytes | None = None
    decision: str = DECISION_PENDING
    replace_filename: str = ""
    replace_bytes: bytes | None = None
    existing_approved: bool = False


@dataclass
class ImageReviewApplyResult:
    ok: bool
    message: str
    attached: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def build_import_image_review(
    rows: list[dict[str, Any]],
    image_files: list[tuple[str, bytes]] | None = None,
    *,
    pricing_rows: list[dict[str, Any]] | None = None,
) -> list[ImportImageReviewRow]:
    """Build per-row image review entries with suggested matches (never auto-approved)."""
    index = build_uploaded_image_index(image_files or [])
    pg_existing = pricing_rows if pricing_rows is not None else _fetch_all("pricing_guide_items")
    out: list[ImportImageReviewRow] = []

    for idx, row in enumerate(rows, start=1):
        desc = str(row.get("description") or "").strip()
        pg_match = find_matching_pricing_item(row, pg_existing)
        approved = is_image_approved(pg_match) if pg_match else False
        review = ImportImageReviewRow(
            row_index=idx,
            row=dict(row),
            description=desc,
            model_number=str(row.get("model_number") or "").strip(),
            item_number=str(row.get("item_number") or "").strip(),
            sku=str(row.get("sku") or "").strip(),
            item_class=normalize_item_class(row.get("item_class")),
            existing_approved=approved,
        )
        if approved:
            review.decision = DECISION_SKIP
            out.append(review)
            continue

        match = find_image_match_for_row(row, index)
        if match:
            review.match_filename = match.filename
            review.match_field = match.matched_field
            review.confidence = match.confidence
            review.suggested_bytes = match.data
            review.decision = DECISION_PENDING
        else:
            review.decision = DECISION_SKIP
        out.append(review)
    return out


def _image_bytes_for_review(entry: ImportImageReviewRow) -> tuple[bytes, str] | None:
    if entry.decision == DECISION_SKIP or entry.existing_approved:
        return None
    if entry.decision == DECISION_REPLACE and entry.replace_bytes:
        name = entry.replace_filename or entry.match_filename or "replacement.jpg"
        return entry.replace_bytes, name
    if entry.decision == DECISION_APPROVE:
        if entry.replace_bytes:
            name = entry.replace_filename or entry.match_filename or "approved.jpg"
            return entry.replace_bytes, name
        if entry.suggested_bytes:
            name = entry.match_filename or "approved.jpg"
            return entry.suggested_bytes, name
    return None


def apply_import_image_decisions(
    review_rows: list[ImportImageReviewRow],
    *,
    changed_by: str = "",
) -> ImageReviewApplyResult:
    """Attach only manually approved/replaced images after catalog import."""
    pg_rows = _fetch_all("pricing_guide_items")
    inv_rows = _fetch_all("inventory_items")
    ast_rows = _fetch_all("assets")
    result = ImageReviewApplyResult(ok=True, message="Image review applied.")

    for entry in review_rows:
        if entry.existing_approved:
            result.skipped += 1
            continue
        hit = _image_bytes_for_review(entry)
        if not hit:
            result.skipped += 1
            continue

        data, filename = hit
        row = entry.row
        pg_existing = find_matching_pricing_item(row, pg_rows)
        if not pg_existing or is_image_approved(pg_existing):
            result.skipped += 1
            continue

        pid = str(pg_existing.get("id") or "")
        if not pid:
            continue

        svc = persist_item_image(
            table="pricing_guide_items",
            record_id=pid,
            entity_type="pricing_guide",
            image_bytes=data,
            filename=filename,
            existing=pg_existing,
            uploaded_by=changed_by or "import-review",
            image_status=IMAGE_STATUS_APPROVED,
        )
        if not svc.ok:
            result.errors.append(f"Row {entry.row_index} PG: {svc.error}")
            continue
        result.attached += 1

        item_class = normalize_item_class(row.get("item_class"))
        if item_class == "Inventory":
            inv_existing = None
            if pg_existing.get("linked_inventory_id"):
                inv_existing = next(
                    (r for r in inv_rows if str(r.get("id")) == str(pg_existing.get("linked_inventory_id"))),
                    None,
                )
            if not inv_existing:
                inv_existing = find_matching_inventory_item(row, inv_rows)
            if inv_existing and not is_image_approved(inv_existing):
                iid = str(inv_existing.get("id") or "")
                persist_item_image(
                    table="inventory_items",
                    record_id=iid,
                    entity_type="inventory",
                    image_bytes=data,
                    filename=filename,
                    existing=inv_existing,
                    uploaded_by=changed_by or "import-review",
                    image_status=IMAGE_STATUS_APPROVED,
                )
                save_approved_local_image(row, data, filename, item_class="Inventory")
        elif item_class == "Asset":
            ast_existing = None
            if pg_existing.get("linked_asset_id"):
                ast_existing = next(
                    (r for r in ast_rows if str(r.get("id")) == str(pg_existing.get("linked_asset_id"))),
                    None,
                )
            if not ast_existing:
                ast_existing = find_matching_asset_item(row, ast_rows)
            if ast_existing and not is_image_approved(ast_existing):
                aid = str(ast_existing.get("id") or "")
                persist_item_image(
                    table="assets",
                    record_id=aid,
                    entity_type="assets",
                    image_bytes=data,
                    filename=filename,
                    existing=ast_existing,
                    uploaded_by=changed_by or "import-review",
                    image_status=IMAGE_STATUS_APPROVED,
                )
                save_approved_local_image(row, data, filename, item_class="Asset")

    if result.errors:
        result.message = f"Applied with {len(result.errors)} warning(s)."
    else:
        result.message = f"Approved images attached: {result.attached}. Skipped: {result.skipped}."
    return result


def import_catalog_with_review(
    csv_text: str,
    review_rows: list[ImportImageReviewRow],
    *,
    changed_by: str = "",
):
    """Import catalog data first, then attach only approved images."""
    catalog_result = import_catalog_csv(
        csv_text,
        changed_by=changed_by,
        attach_images=False,
        include_local_image_folder=False,
    )
    if not catalog_result.ok:
        return catalog_result, None

    image_result = apply_import_image_decisions(review_rows, changed_by=changed_by)
    catalog_result.images_attached = image_result.attached
    catalog_result.images_skipped = image_result.skipped
    if image_result.errors:
        catalog_result.errors.extend(image_result.errors)
    catalog_result.message = (
        f"{catalog_result.message} "
        f"Approved images attached: {image_result.attached}."
    )
    return catalog_result, image_result
