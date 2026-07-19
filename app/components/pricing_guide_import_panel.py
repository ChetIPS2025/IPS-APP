"""Lazy CSV/image import workflow for Pricing Guide."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from app.services.catalog_import_service import parse_catalog_csv
from app.services.catalog_image_review_service import (
    DECISION_APPROVE,
    DECISION_PENDING,
    DECISION_REPLACE,
    DECISION_SKIP,
    ImportImageReviewRow,
    build_import_image_review,
    import_catalog_with_review,
)
from app.services.item_images import ITEM_IMAGE_UPLOAD_TYPES
from app.services.pricing_guide_directory_service import invalidate_pricing_guide_directory_cache
from app.services.pricing_guide_service import clear_pricing_guide_cache
from app.ui.streamlit_perf import fragment, fragment_rerun

_IMPORT_OPEN_KEY = "ips_pg_import_open"
_MAX_IMPORT_REVIEW_ROWS = 500
_MAX_IMPORT_IMAGE_BYTES_PER_FILE = 5 * 1024 * 1024
_MAX_IMPORT_TOTAL_IMAGE_BYTES = 50 * 1024 * 1024
_IMPORT_REVIEW_PAGE_SIZE = 10


@dataclass
class CatalogImportReviewState:
    import_id: str
    row_count: int
    current_page: int = 1
    decisions: dict[int, str] = field(default_factory=dict)
    review_metadata: list[dict[str, Any]] = field(default_factory=list)
    image_references: dict[int, str] = field(default_factory=dict)
    total_image_bytes: int = 0


def clear_import_review_state() -> None:
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("pg_import_"):
            del st.session_state[key]
    st.session_state.pop("pg_import_review_state", None)


def _store_review_state(review: list[Any], *, csv_row_count: int) -> None:
    meta: list[dict[str, Any]] = []
    blob_cache: dict[str, bytes] = {}
    total_bytes = 0
    for r in review:
        meta.append(
            {
                "row_index": r.row_index,
                "description": r.description,
                "model_number": r.model_number,
                "item_number": r.item_number,
                "sku": r.sku,
                "item_class": r.item_class,
                "match_filename": r.match_filename,
                "match_field": r.match_field,
                "confidence": r.confidence,
                "decision": r.decision,
                "existing_approved": r.existing_approved,
                "row": r.row,
            }
        )
        if r.suggested_bytes:
            size = len(r.suggested_bytes)
            if size <= _MAX_IMPORT_IMAGE_BYTES_PER_FILE and total_bytes + size <= _MAX_IMPORT_TOTAL_IMAGE_BYTES:
                blob_cache[str(r.row_index)] = r.suggested_bytes
                total_bytes += size
        st.session_state[f"pg_import_decision_{r.row_index}"] = r.decision
    st.session_state["pg_import_review_meta"] = meta
    st.session_state["pg_import_image_blobs"] = blob_cache
    st.session_state["pg_import_review_state"] = CatalogImportReviewState(
        import_id=str(st.session_state.get("pg_import_id") or "review"),
        row_count=csv_row_count,
        total_image_bytes=total_bytes,
    )


def render_pricing_guide_import_panel(*, can_import: bool) -> None:
    if not can_import:
        return
    st.markdown("**Import Catalog CSV**")
    if not st.session_state.get(_IMPORT_OPEN_KEY):
        if st.button("Open Import", key="pg_import_open"):
            st.session_state[_IMPORT_OPEN_KEY] = True
            fragment_rerun()
        return
    if st.button("Close Import", key="pg_import_close"):
        st.session_state[_IMPORT_OPEN_KEY] = False
        clear_import_review_state()
        fragment_rerun()
        return
    _render_import_controls()


@fragment
def _render_import_controls() -> None:
    from app.perf_debug import perf_span

    st.caption(
        "Imports Pricing Guide, Inventory, and Asset records from CSV. "
        "Item photos require manual review — nothing is auto-attached from cropped thumbnails."
    )
    uploaded = st.file_uploader(
        "CSV file",
        type=["csv"],
        key="pg_csv_upload",
        label_visibility="collapsed",
    )
    image_uploads = st.file_uploader(
        "Candidate item images (optional — match by model #, item #, SKU, then description)",
        type=list(ITEM_IMAGE_UPLOAD_TYPES),
        accept_multiple_files=True,
        key="pg_csv_images",
    )
    if uploaded is None:
        return

    with perf_span("pricing_guide.import.parse"):
        text = uploaded.getvalue().decode("utf-8-sig", errors="replace")
        image_files: list[tuple[str, bytes]] = []
        total_image_bytes = 0
        for f in image_uploads or []:
            blob = f.getvalue()
            size = len(blob)
            if size > _MAX_IMPORT_IMAGE_BYTES_PER_FILE:
                st.warning(f"Skipped oversized image ({size // (1024 * 1024)} MB limit per file).")
                continue
            if total_image_bytes + size > _MAX_IMPORT_TOTAL_IMAGE_BYTES:
                st.warning("Total uploaded image size limit reached; remaining files were skipped.")
                break
            image_files.append((str(getattr(f, "name", "") or "image.jpg"), blob))
            total_image_bytes += size

    c1, c2 = st.columns(2)
    with c1:
        prepare = st.button("Prepare Import Review", key="pg_csv_prepare", type="primary")
    with c2:
        if st.button("Clear Review", key="pg_csv_clear_review"):
            clear_import_review_state()
            fragment_rerun()

    if prepare:
        rows = parse_catalog_csv(text)
        if not rows:
            st.error("No valid rows found in CSV.")
            return
        if len(rows) > _MAX_IMPORT_REVIEW_ROWS:
            st.warning(
                f"This CSV has {len(rows)} rows (limit {_MAX_IMPORT_REVIEW_ROWS} for interactive review). "
                "Confirm to continue with chunked metadata review."
            )
            if not st.checkbox("I understand — continue with large import review", key="pg_import_large_confirm"):
                return
        with perf_span("pricing_guide.import.review"):
            review = build_import_image_review(rows, image_files or None)
        st.session_state["pg_import_csv_text"] = text
        st.session_state["pg_import_id"] = str(hash(text) & 0xFFFF_FFFF)
        _store_review_state(review, csv_row_count=len(rows))
        fragment_rerun()

    meta = st.session_state.get("pg_import_review_meta")
    if not meta:
        return
    _render_import_review_pagination(meta, text_key="pg_import_csv_text")


@fragment
def _render_import_review_pagination(meta: list[dict[str, Any]], *, text_key: str) -> None:
    total = len(meta)
    page_size = _IMPORT_REVIEW_PAGE_SIZE
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = int(st.session_state.get("pg_import_review_page") or 1)
    page = max(1, min(page, total_pages))
    st.session_state["pg_import_review_page"] = page
    start = (page - 1) * page_size
    batch = meta[start : start + page_size]
    blobs: dict[str, bytes] = st.session_state.get("pg_import_image_blobs") or {}

    pending = approved = replaced = skipped = 0
    for entry in meta:
        idx = int(entry["row_index"])
        decision = str(st.session_state.get(f"pg_import_decision_{idx}") or entry.get("decision") or DECISION_PENDING)
        if decision == DECISION_PENDING:
            pending += 1
        elif decision == DECISION_APPROVE:
            approved += 1
        elif decision == DECISION_REPLACE:
            replaced += 1
        else:
            skipped += 1

    st.markdown("### Image review (required before photos are saved)")
    st.caption(
        f"{total} catalog row(s) · page {page}/{total_pages} · "
        f"pending {pending} · approved {approved} · replace {replaced} · skipped {skipped}"
    )
    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if page > 1 and st.button("Previous page", key="pg_import_prev"):
            st.session_state["pg_import_review_page"] = page - 1
            fragment_rerun()
    with nav3:
        if page < total_pages and st.button("Next page", key="pg_import_next"):
            st.session_state["pg_import_review_page"] = page + 1
            fragment_rerun()

    for entry in batch:
        idx = int(entry["row_index"])
        decision_key = f"pg_import_decision_{idx}"
        if decision_key not in st.session_state:
            st.session_state[decision_key] = str(entry.get("decision") or DECISION_SKIP)
        with st.container(border=True):
            left, mid, right = st.columns([2.2, 1.2, 1.3])
            with left:
                st.markdown(f"**{str(entry.get('description') or '')[:120]}**")
                st.caption(
                    f"Class: {entry.get('item_class')} · "
                    f"Model: {entry.get('model_number') or '—'} · "
                    f"Item #: {entry.get('item_number') or '—'} · "
                    f"SKU: {entry.get('sku') or '—'}"
                )
                if entry.get("existing_approved"):
                    st.info("Existing approved photo — will not be overwritten.")
            with mid:
                blob = blobs.get(str(idx))
                if blob:
                    st.image(blob, caption=entry.get("match_filename") or "Suggested", use_container_width=True)
                else:
                    st.caption("No suggested image")
            with right:
                options = [DECISION_PENDING, DECISION_APPROVE, DECISION_SKIP, DECISION_REPLACE]
                if entry.get("existing_approved"):
                    options = [DECISION_SKIP]
                current = str(st.session_state.get(decision_key) or entry.get("decision") or DECISION_PENDING)
                if current not in options:
                    current = options[0]
                choice = st.selectbox(
                    "Decision",
                    options,
                    index=options.index(current),
                    key=f"pg_import_decision_select_{idx}",
                    disabled=bool(entry.get("existing_approved")),
                )
                st.session_state[decision_key] = choice
                if choice == DECISION_REPLACE:
                    repl = st.file_uploader(
                        "Replacement image",
                        type=list(ITEM_IMAGE_UPLOAD_TYPES),
                        key=f"pg_import_replace_{idx}",
                        label_visibility="collapsed",
                    )
                    if repl is not None:
                        rb = repl.getvalue()
                        if len(rb) <= _MAX_IMPORT_IMAGE_BYTES_PER_FILE:
                            st.session_state[f"pg_import_replace_bytes_{idx}"] = rb
                            st.session_state[f"pg_import_replace_name_{idx}"] = str(
                                getattr(repl, "name", "") or "replacement.jpg"
                            )

    if pending > 0:
        st.warning(f"{pending} row(s) still have a Pending image decision.")
    if st.button("Import Catalog + Approved Images", key="pg_csv_import", type="primary", disabled=pending > 0):
        from app.perf_debug import perf_span

        csv_text = str(st.session_state.get(text_key) or "")
        review_rows: list[ImportImageReviewRow] = []
        for entry in meta:
            idx = int(entry["row_index"])
            decision = str(st.session_state.get(f"pg_import_decision_{idx}") or DECISION_SKIP)
            suggested_bytes = blobs.get(str(idx))
            replace_bytes = st.session_state.get(f"pg_import_replace_bytes_{idx}")
            replace_name = str(st.session_state.get(f"pg_import_replace_name_{idx}") or "")
            review_rows.append(
                ImportImageReviewRow(
                    row_index=idx,
                    row=dict(entry.get("row") or {}),
                    description=str(entry.get("description") or ""),
                    model_number=str(entry.get("model_number") or ""),
                    item_number=str(entry.get("item_number") or ""),
                    sku=str(entry.get("sku") or ""),
                    item_class=str(entry.get("item_class") or ""),
                    match_filename=str(entry.get("match_filename") or ""),
                    match_field=str(entry.get("match_field") or ""),
                    confidence=str(entry.get("confidence") or "none"),
                    suggested_bytes=suggested_bytes if isinstance(suggested_bytes, (bytes, bytearray)) else None,
                    decision=decision,
                    replace_filename=replace_name,
                    replace_bytes=replace_bytes if isinstance(replace_bytes, (bytes, bytearray)) else None,
                    existing_approved=bool(entry.get("existing_approved")),
                )
            )
        with perf_span("pricing_guide.import.persist"):
            result, _img = import_catalog_with_review(csv_text, review_rows)
        if result.ok:
            st.success(result.message)
            if result.errors:
                for err in result.errors[:20]:
                    st.warning(err)
            clear_import_review_state()
            st.session_state[_IMPORT_OPEN_KEY] = False
            invalidate_pricing_guide_directory_cache()
            clear_pricing_guide_cache()
            try:
                from app.pages._core._data import (
                    _bump_assets_catalog_data_version,
                    _bump_inventory_catalog_data_version,
                )

                _bump_inventory_catalog_data_version()
                _bump_assets_catalog_data_version()
            except Exception:
                pass
            st.rerun()
        else:
            st.error(result.message)
