"""Quick Add Tool dialog — manual entry, photo, receipt, and bulk import."""

from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from app.services.asset_kits_service import get_tool_trailers
    from app.services.quick_add_tool_service import (
        TOOL_KIND_LABELS,
        TOOL_KINDS,
        analyze_tool_photos,
        attach_tool_photo,
        attach_tool_photos_bundle,
        attach_tool_receipt,
        bulk_import_tools,
        parse_bulk_import_file,
        quick_add_tool,
    )
    from app.services.serialized_tool_service import MILWAUKEE_TOOL_TYPES
    from app.services.small_hand_tool_service import HAND_TOOL_CATEGORIES, STORAGE_TYPES
    from app.services.tool_intake_ai_service import (
        extract_tool_from_photo,
        load_tool_ai_config,
        ocr_tool_receipt,
        search_tool_by_image,
        tool_ai_status,
    )
    from app.ui.ips_modal_form import ensure_modal_styles, modal_wide_marker
except ImportError:
    from services.asset_kits_service import get_tool_trailers  # type: ignore
    from services.quick_add_tool_service import (  # type: ignore
        TOOL_KIND_LABELS,
        TOOL_KINDS,
        analyze_tool_photos,
        attach_tool_photo,
        attach_tool_photos_bundle,
        attach_tool_receipt,
        bulk_import_tools,
        parse_bulk_import_file,
        quick_add_tool,
    )
    from services.serialized_tool_service import MILWAUKEE_TOOL_TYPES  # type: ignore
    from services.small_hand_tool_service import HAND_TOOL_CATEGORIES, STORAGE_TYPES  # type: ignore
    from services.tool_intake_ai_service import (  # type: ignore
        extract_tool_from_photo,
        load_tool_ai_config,
        ocr_tool_receipt,
        search_tool_by_image,
        tool_ai_status,
    )
    from ui.ips_modal_form import ensure_modal_styles, modal_wide_marker  # type: ignore

QUICK_ADD_OPEN_KEY = "ips_quick_add_tool_open"

_METHOD_TABS = ("Manual entry", "Tool photo", "Receipt", "Bulk import")

TOOL_PHOTO_UPLOAD_TYPES: tuple[str, ...] = ("jpg", "jpeg", "png", "webp", "heic", "heif", "pdf")
TOOL_PHOTO_UPLOAD_CAPTION = "JPG, JPEG, PNG, WEBP, HEIC, HEIF, PDF"
TOOL_PHOTO_UPLOAD_HELP = (
    "Upload one or more photos or PDFs. All originals are kept as source evidence. "
    "The default table thumbnail comes from your uploads; catalog product images are optional suggestions."
)

_QAT_PHOTO_ANALYSIS_KEY = "qat_p_analysis"
_QAT_PHOTO_UPLOAD_META_KEY = "qat_p_upload_meta"
_QAT_PHOTO_PRIMARY_CHOICE_KEY = "qat_p_primary_choice"
_PRIMARY_UPLOAD_CHOICE = "upload"


class _CachedUpload:
    """Streamlit UploadedFile stand-in persisted across reruns."""

    def __init__(self, data: bytes, name: str) -> None:
        self._data = data
        self.name = name
        self.type = ""

    def getvalue(self) -> bytes:
        return self._data


def open_quick_add_tool_dialog() -> None:
    st.session_state[QUICK_ADD_OPEN_KEY] = True


def close_quick_add_tool_dialog() -> None:
    st.session_state.pop(QUICK_ADD_OPEN_KEY, None)


def _trailer_options() -> tuple[list[str], dict[str, str]]:
    labels = ["— None —"]
    label_to_id: dict[str, str] = {"— None —": ""}
    for trailer in get_tool_trailers():
        number = str(trailer.get("asset_number") or "").strip()
        name = str(trailer.get("asset_name") or trailer.get("name") or "Trailer").strip()
        label = f"{number} · {name}" if number else name
        labels.append(label)
        label_to_id[label] = str(trailer.get("id") or "")
    return labels, label_to_id


def _render_ai_status() -> None:
    status = tool_ai_status()
    parts: list[str] = []
    for label, key in (("Vision", "vision"), ("OCR", "ocr"), ("Image search", "image_search")):
        row = status.get(key) or {}
        prov = str(row.get("provider") or "—")
        ready = "ready" if row.get("ready") else "not configured"
        parts.append(f"{label}: {prov} ({ready})")
    st.caption("AI providers — " + " · ".join(parts))


def _apply_scan_to_photo_fields(prefix: str, parsed: dict[str, Any], *, kind: str) -> None:
    if parsed.get("tool_name"):
        st.session_state[f"{prefix}_photo_name"] = parsed["tool_name"]
    if parsed.get("manufacturer"):
        st.session_state[f"{prefix}_photo_mfr"] = parsed["manufacturer"]
    if kind == "serialized":
        if parsed.get("serial_number"):
            st.session_state[f"{prefix}_photo_serial"] = parsed["serial_number"]
        if parsed.get("model"):
            st.session_state[f"{prefix}_photo_model"] = parsed["model"]


def _photo_upload_tuples(photos: list[Any] | None) -> list[tuple[bytes, str]]:
    tuples: list[tuple[bytes, str]] = []
    for photo in photos or []:
        raw = photo.getvalue()
        name = str(getattr(photo, "name", "") or "upload")
        if raw:
            tuples.append((raw, name))
    return tuples


def _cached_photo_uploads(prefix: str) -> list[_CachedUpload]:
    meta = st.session_state.get(f"{prefix}_{_QAT_PHOTO_UPLOAD_META_KEY}") or []
    uploads: list[_CachedUpload] = []
    for row in meta:
        if not isinstance(row, dict):
            continue
        data = row.get("file_bytes") or b""
        name = str(row.get("file_name") or "upload")
        if data:
            uploads.append(_CachedUpload(data, name))
    return uploads


def _primary_choice_options(analysis: dict[str, Any]) -> list[tuple[str, str, bytes | None]]:
    """Return (choice_id, label, thumbnail_bytes) for primary image picker."""
    options: list[tuple[str, str, bytes | None]] = [
        (
            _PRIMARY_UPLOAD_CHOICE,
            str(analysis.get("preview_source_label") or "Best uploaded photo"),
            analysis.get("preview_bytes"),
        )
    ]
    for suggestion in analysis.get("product_suggestions") or []:
        if not isinstance(suggestion, dict):
            continue
        sid = str(suggestion.get("id") or "")
        if not sid:
            continue
        options.append(
            (
                sid,
                str(suggestion.get("source_label") or "Product suggestion"),
                suggestion.get("preview_bytes"),
            )
        )
    return options


def _resolve_primary_from_analysis(analysis: dict[str, Any], choice_id: str) -> tuple[bytes | None, str, str]:
    if choice_id == _PRIMARY_UPLOAD_CHOICE:
        return (
            analysis.get("preview_bytes"),
            str(analysis.get("preview_filename") or "preview.jpg"),
            str(analysis.get("preview_source_label") or "Uploaded photo"),
        )
    for suggestion in analysis.get("product_suggestions") or []:
        if not isinstance(suggestion, dict):
            continue
        if str(suggestion.get("id") or "") == choice_id:
            return (
                suggestion.get("preview_bytes"),
                str(suggestion.get("preview_filename") or "product-preview.jpg"),
                str(suggestion.get("source_label") or "Product suggestion"),
            )
    return (
        analysis.get("preview_bytes"),
        str(analysis.get("preview_filename") or "preview.jpg"),
        str(analysis.get("preview_source_label") or "Uploaded photo"),
    )


def _render_photo_review(prefix: str, analysis: dict[str, Any]) -> None:
    extracted = analysis.get("extracted") or {}
    upload_count = int(analysis.get("upload_count") or 0)
    choice_key = f"{prefix}_{_QAT_PHOTO_PRIMARY_CHOICE_KEY}"
    options = _primary_choice_options(analysis)
    if choice_key not in st.session_state:
        st.session_state[choice_key] = _PRIMARY_UPLOAD_CHOICE
    current_choice = str(st.session_state.get(choice_key) or _PRIMARY_UPLOAD_CHOICE)
    if current_choice not in {opt[0] for opt in options}:
        st.session_state[choice_key] = _PRIMARY_UPLOAD_CHOICE
        current_choice = _PRIMARY_UPLOAD_CHOICE

    primary_bytes, _, primary_label = _resolve_primary_from_analysis(analysis, current_choice)

    with st.container(border=True):
        st.markdown("##### Review before save")
        st.caption(
            f"**Source files:** {upload_count} upload(s) will be saved to Documents as evidence/history."
        )
        if primary_bytes:
            st.image(primary_bytes, caption=f"**Primary image** (tables & detail) — {primary_label}", width=220)
        else:
            st.caption("Primary image will be generated from your uploads on save.")

        suggestions = [opt for opt in options if opt[0] != _PRIMARY_UPLOAD_CHOICE]
        if suggestions:
            st.markdown("**Product suggestions** (optional — approve one to replace the default upload preview)")
            cols = st.columns(min(len(suggestions), 3))
            for idx, (sid, label, thumb) in enumerate(suggestions):
                with cols[idx % len(cols)]:
                    if thumb:
                        st.image(thumb, width=140)
                    if st.button(
                        "Use as primary",
                        key=f"{prefix}_approve_{sid}",
                        use_container_width=True,
                        type="primary" if current_choice == sid else "secondary",
                    ):
                        st.session_state[choice_key] = sid
                        st.rerun()
                    st.caption(label)
        else:
            st.caption("No catalog product images found for this model/name. The upload preview will be used.")

        choice_labels = {opt[0]: opt[1] for opt in options}
        st.radio(
            "Primary image source",
            options=[opt[0] for opt in options],
            format_func=lambda key: choice_labels.get(key, key),
            key=choice_key,
            horizontal=True,
        )

        conf = float(extracted.get("confidence") or 0)
        if conf > 0:
            st.caption(f"AI confidence: {conf:.0%}")
        if extracted.get("notes"):
            st.caption(str(extracted["notes"]))


def _apply_scan_to_receipt_fields(prefix: str, parsed: dict[str, Any]) -> None:
    if parsed.get("tool_name"):
        st.session_state[f"{prefix}_rcpt_name"] = parsed["tool_name"]
    if parsed.get("serial_number"):
        st.session_state[f"{prefix}_rcpt_serial"] = parsed["serial_number"]
    cost = float(parsed.get("unit_cost") or 0)
    if cost > 0:
        st.session_state[f"{prefix}_rcpt_cost"] = cost


def _render_kind_help(kind: str) -> None:
    if kind == "serialized":
        st.caption("Individual tools tracked by serial number — drills, impacts, grinders, saws, batteries.")
    elif kind == "small":
        st.caption("Quantity-tracked hand tools without serial numbers — wrenches, pliers, sockets, clamps.")
    else:
        st.caption("Consumables and stock items — cut-off wheels, drill bits, gloves, fasteners.")


def _manual_form(kind: str, *, prefix: str, trailer_id: str) -> None:
    if kind == "serialized":
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Tool name *", key=f"{prefix}_name", placeholder="M18 FUEL Hammer Drill")
            serial = st.text_input("Serial number *", key=f"{prefix}_serial")
            asset_num = st.text_input("Asset #", key=f"{prefix}_asset_num")
            tool_type = st.selectbox("Tool type", MILWAUKEE_TOOL_TYPES, key=f"{prefix}_tool_type")
        with c2:
            mfr = st.text_input("Manufacturer", value="Milwaukee", key=f"{prefix}_mfr")
            model = st.text_input("Model", key=f"{prefix}_model")
            st.text_input("Notes", key=f"{prefix}_notes")
        payload = {
            "tool_name": name,
            "serial_number": serial,
            "asset_number": asset_num,
            "asset_type": tool_type,
            "category": "Tool",
            "manufacturer": mfr,
            "model": model,
            "notes": st.session_state.get(f"{prefix}_notes"),
        }
    elif kind == "small":
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Tool name *", key=f"{prefix}_name", placeholder="TEKTON Combination Wrench Set")
            category = st.selectbox("Category", HAND_TOOL_CATEGORIES, key=f"{prefix}_cat")
            qty = st.number_input("Quantity on hand", min_value=0.0, value=1.0, step=1.0, key=f"{prefix}_qty")
        with c2:
            expected = st.number_input("Quantity expected", min_value=0.0, value=1.0, step=1.0, key=f"{prefix}_exp")
            storage = st.selectbox("Storage type", STORAGE_TYPES, key=f"{prefix}_storage")
            location = st.text_input("Storage location", key=f"{prefix}_loc")
        payload = {
            "tool_name": name,
            "category": category,
            "quantity": qty,
            "quantity_expected": expected,
            "storage_type": storage,
            "storage_location": location,
        }
    else:
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Item name *", key=f"{prefix}_name", placeholder="Cut-off wheels 4.5 in")
            category = st.text_input("Category", value="Consumables", key=f"{prefix}_cat")
            qty = st.number_input("Quantity on hand", min_value=0.0, value=0.0, step=1.0, key=f"{prefix}_qty")
        with c2:
            unit_cost = st.number_input("Unit cost", min_value=0.0, value=0.0, step=0.01, key=f"{prefix}_cost")
            vendor = st.text_input("Vendor", key=f"{prefix}_vendor")
            location = st.text_input("Storage location", key=f"{prefix}_loc")
        payload = {
            "tool_name": name,
            "category": category,
            "quantity": qty,
            "unit_cost": unit_cost,
            "vendor": vendor,
            "storage_location": location,
        }

    if st.button("Save tool", type="primary", key=f"{prefix}_save", use_container_width=True):
        result = quick_add_tool(kind, payload, trailer_id=trailer_id)
        if result.ok:
            st.success(f"Added to {TOOL_KIND_LABELS[kind]}.")
            close_quick_add_tool_dialog()
            try:
                from app.services.assets_service import clear_assets_cache
            except ImportError:
                from services.assets_service import clear_assets_cache  # type: ignore
            clear_assets_cache()
            st.rerun()
        else:
            st.error(result.error or "Could not save tool.")


def _photo_form(kind: str, *, prefix: str, trailer_id: str, uploaded_by: str | None) -> None:
    photos = st.file_uploader(
        "Tool photos & documents",
        type=list(TOOL_PHOTO_UPLOAD_TYPES),
        accept_multiple_files=True,
        key=f"{prefix}_photo",
        help=TOOL_PHOTO_UPLOAD_HELP,
    )
    st.caption(f"Accepted formats: {TOOL_PHOTO_UPLOAD_CAPTION}. Upload multiple files when helpful.")
    cfg = load_tool_ai_config()
    action_col, clear_col = st.columns(2)
    with action_col:
        analyze_clicked = st.button(
            "Analyze uploads",
            key=f"{prefix}_analyze",
            use_container_width=True,
            type="primary",
            disabled=not photos or not cfg.vision_ready,
        )
    with clear_col:
        if st.button("Clear analysis", key=f"{prefix}_clear_analysis", use_container_width=True):
            st.session_state.pop(f"{prefix}_{_QAT_PHOTO_ANALYSIS_KEY}", None)
            st.session_state.pop(f"{prefix}_{_QAT_PHOTO_UPLOAD_META_KEY}", None)
            st.session_state.pop(f"{prefix}_{_QAT_PHOTO_PRIMARY_CHOICE_KEY}", None)
            st.rerun()

    if not photos:
        st.caption("Upload one or more photos or PDFs to analyze tool details and preview image.")
    elif not cfg.vision_ready:
        st.caption("Set TOOL_VISION_API_KEY or OPENAI_API_KEY to enable Analyze uploads.")

    if analyze_clicked and photos:
        try:
            with st.spinner("Analyzing uploads and searching for product image suggestions…"):
                batch = _photo_upload_tuples(photos)
                result = analyze_tool_photos(batch, kind_hint=kind)
            if not result.ok:
                st.error(result.error or "Analysis failed.")
            else:
                st.session_state[f"{prefix}_{_QAT_PHOTO_ANALYSIS_KEY}"] = result.data or {}
                st.session_state[f"{prefix}_{_QAT_PHOTO_UPLOAD_META_KEY}"] = [
                    {"file_name": name, "file_bytes": data} for data, name in batch
                ]
                st.session_state[f"{prefix}_{_QAT_PHOTO_PRIMARY_CHOICE_KEY}"] = _PRIMARY_UPLOAD_CHOICE
                _apply_scan_to_photo_fields(prefix, (result.data or {}).get("extracted") or {}, kind=kind)
                n_suggest = len((result.data or {}).get("product_suggestions") or [])
                hint = f" {n_suggest} product suggestion(s) found." if n_suggest else ""
                st.success(f"Analysis complete — review fields and choose a primary image.{hint}")
                st.rerun()
        except Exception as exc:
            st.error(str(exc))

    analysis = st.session_state.get(f"{prefix}_{_QAT_PHOTO_ANALYSIS_KEY}")
    if analysis:
        _render_photo_review(prefix, analysis)

    scan_col, search_col = st.columns(2)
    first_photo = (photos or [None])[0]
    with scan_col:
        if st.button(
            "Re-scan first file",
            key=f"{prefix}_scan",
            use_container_width=True,
            disabled=first_photo is None or not cfg.vision_ready,
        ):
            try:
                parsed = extract_tool_from_photo(first_photo.getvalue(), first_photo.name, kind_hint=kind)
                _apply_scan_to_photo_fields(prefix, parsed, kind=kind)
                st.success(f"First file scanned ({float(parsed.get('confidence') or 0):.0%} confidence).")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with search_col:
        if st.button(
            "Match first file",
            key=f"{prefix}_img_search",
            use_container_width=True,
            disabled=first_photo is None or not cfg.image_search_ready,
        ):
            try:
                parsed = search_tool_by_image(first_photo.getvalue(), first_photo.name)
                _apply_scan_to_photo_fields(prefix, parsed, kind=kind)
                st.success("Image match applied to fields.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    name = st.text_input("Tool name *", key=f"{prefix}_photo_name")
    if kind == "serialized":
        serial = st.text_input("Serial number *", key=f"{prefix}_photo_serial")
        c1, c2 = st.columns(2)
        with c1:
            model = st.text_input("Model", key=f"{prefix}_photo_model")
        with c2:
            if f"{prefix}_photo_mfr" not in st.session_state:
                st.session_state[f"{prefix}_photo_mfr"] = "Milwaukee"
            mfr = st.text_input("Manufacturer", key=f"{prefix}_photo_mfr")
    else:
        serial = ""
        model = ""
        mfr = ""
        st.caption("Photos are stored on Serialized Tool assets. Small Tools and Inventory save without a photo for now.")

    if st.button("Save with photo", type="primary", key=f"{prefix}_photo_save", use_container_width=True):
        uploads = _cached_photo_uploads(prefix) or [p for p in (photos or []) if p is not None]
        if not uploads:
            st.error("Upload and analyze at least one photo before saving.")
            return
        if kind == "serialized":
            if not serial:
                st.error("Serial number is required for Serialized Tools.")
                return
            result = quick_add_tool(
                kind,
                {
                    "tool_name": name,
                    "serial_number": serial,
                    "model": model,
                    "manufacturer": mfr,
                    "category": "Tool",
                },
                trailer_id=trailer_id,
            )
        else:
            payload: dict[str, Any] = {"tool_name": name, "quantity": 1}
            if kind == "small":
                payload["category"] = "Other"
            else:
                payload["category"] = "Consumables"
            result = quick_add_tool(kind, payload, trailer_id=trailer_id)
        if not result.ok:
            st.error(result.error or "Could not save tool.")
            return
        tool_id = str((result.data or {}).get("id") or "")
        if tool_id and kind == "serialized":
            analysis_data = st.session_state.get(f"{prefix}_{_QAT_PHOTO_ANALYSIS_KEY}") or {}
            choice_id = str(
                st.session_state.get(f"{prefix}_{_QAT_PHOTO_PRIMARY_CHOICE_KEY}") or _PRIMARY_UPLOAD_CHOICE
            )
            preview_bytes, preview_filename, _ = _resolve_primary_from_analysis(analysis_data, choice_id)
            if not preview_bytes:
                try:
                    from app.services.tool_preview_image_service import pick_best_upload_preview
                except ImportError:
                    from services.tool_preview_image_service import pick_best_upload_preview  # type: ignore
                try:
                    batch = [(u.getvalue(), u.name) for u in uploads]
                    preview = pick_best_upload_preview(batch)
                    preview_bytes = preview.preview_bytes
                    preview_filename = preview.preview_filename
                except Exception:
                    preview_bytes = None
            photo_result = attach_tool_photos_bundle(
                tool_id,
                uploads,
                primary_preview_bytes=preview_bytes,
                primary_preview_filename=preview_filename,
                uploaded_by=uploaded_by,
            )
            if not photo_result.ok:
                st.warning(photo_result.error or "Tool saved; photo upload failed.")
            elif (photo_result.data or {}).get("source_errors"):
                for err in (photo_result.data or {}).get("source_errors") or []:
                    st.warning(str(err))
        st.success(f"Added to {TOOL_KIND_LABELS[kind]}.")
        st.session_state.pop(f"{prefix}_{_QAT_PHOTO_ANALYSIS_KEY}", None)
        st.session_state.pop(f"{prefix}_{_QAT_PHOTO_UPLOAD_META_KEY}", None)
        st.session_state.pop(f"{prefix}_{_QAT_PHOTO_PRIMARY_CHOICE_KEY}", None)
        close_quick_add_tool_dialog()
        try:
            from app.services.assets_service import clear_assets_cache
        except ImportError:
            from services.assets_service import clear_assets_cache  # type: ignore
        clear_assets_cache()
        st.rerun()


def _receipt_form(kind: str, *, prefix: str, trailer_id: str, uploaded_by: str | None) -> None:
    receipt = st.file_uploader(
        "Purchase receipt",
        type=["pdf", "jpg", "jpeg", "png"],
        key=f"{prefix}_receipt",
    )
    cfg = load_tool_ai_config()
    if st.button(
        "Read receipt",
        key=f"{prefix}_ocr",
        use_container_width=True,
        disabled=receipt is None or not cfg.ocr_ready,
    ):
        try:
            parsed = ocr_tool_receipt(receipt.getvalue(), receipt.name)
            _apply_scan_to_receipt_fields(prefix, parsed)
            st.success("Receipt read. Review fields below.")
            if parsed.get("notes"):
                st.caption(parsed["notes"])
        except Exception as exc:
            st.error(str(exc))
    elif receipt is not None and not cfg.ocr_ready:
        st.caption("Set TOOL_OCR_API_KEY or OPENAI_API_KEY to enable Read receipt.")

    name = st.text_input("Tool / item name *", key=f"{prefix}_rcpt_name")
    if kind == "serialized":
        serial = st.text_input("Serial number *", key=f"{prefix}_rcpt_serial")
    else:
        serial = ""
    cost = st.number_input("Purchase amount (optional)", min_value=0.0, value=0.0, step=0.01, key=f"{prefix}_rcpt_cost")
    if st.button("Save with receipt", type="primary", key=f"{prefix}_rcpt_save", use_container_width=True):
        payload: dict[str, Any] = {
            "tool_name": name,
            "serial_number": serial,
            "unit_cost": cost,
            "notes": f"Receipt on file — ${cost:.2f}" if cost else "Receipt on file",
        }
        if kind == "small":
            payload["category"] = st.session_state.get(f"{prefix}_cat", "Other")
            payload["quantity"] = st.session_state.get(f"{prefix}_qty", 1)
        if kind == "inventory":
            payload["category"] = "Consumables"
            payload["quantity"] = st.session_state.get(f"{prefix}_qty", 0)
        result = quick_add_tool(kind, payload, trailer_id=trailer_id)
        if not result.ok:
            st.error(result.error or "Could not save.")
            return
        receipt = st.session_state.get(f"{prefix}_receipt")
        if receipt is not None and kind == "serialized" and isinstance(result.data, dict):
            rcpt_result = attach_tool_receipt(result.data, receipt, uploaded_by=uploaded_by)
            if not rcpt_result.ok:
                st.warning(rcpt_result.error or "Saved; receipt upload failed.")
        st.success(f"Added to {TOOL_KIND_LABELS[kind]}.")
        close_quick_add_tool_dialog()
        try:
            from app.services.assets_service import clear_assets_cache
        except ImportError:
            from services.assets_service import clear_assets_cache  # type: ignore
        clear_assets_cache()
        st.rerun()


def _bulk_form(kind: str, *, prefix: str, trailer_id: str) -> None:
    st.caption(
        "Upload CSV or XLSX. Columns: tool_name, serial_number (serialized), quantity (small/inventory), "
        "category, model, manufacturer, tool_type (serialized|small|inventory), trailer_asset_number."
    )
    uploaded = st.file_uploader("Spreadsheet", type=["csv", "xlsx", "xls"], key=f"{prefix}_bulk_file")
    if uploaded and st.button("Import file", type="primary", key=f"{prefix}_bulk_go", use_container_width=True):
        rows = parse_bulk_import_file(uploaded.getvalue(), uploaded.name)
        if not rows:
            st.error("No rows found in file.")
            return
        result = bulk_import_tools(rows, default_kind=kind, default_trailer_id=trailer_id)
        if result.ok:
            data = result.data or {}
            st.success(str(data.get("message") or "Import complete."))
            for err in (data.get("errors") or [])[:5]:
                st.warning(str(err))
            close_quick_add_tool_dialog()
            try:
                from app.services.assets_service import clear_assets_cache
            except ImportError:
                from services.assets_service import clear_assets_cache  # type: ignore
            clear_assets_cache()
            st.rerun()
        else:
            st.error(result.error or "Import failed.")


def render_quick_add_tool_dialog(*, uploaded_by: str | None = None) -> None:
    """Body of the Quick Add Tool dialog (call from @st.dialog wrapper)."""
    ensure_modal_styles()
    modal_wide_marker()

    st.markdown("### Quick Add Tool")
    st.caption(
        "Equipment = big stuff · Serialized Tools = serial-numbered tools · "
        "Small Tools = counted hand tools · Inventory = consumables"
    )

    kind_labels = [TOOL_KIND_LABELS[k] for k in TOOL_KINDS]
    kind_pick = st.radio(
        "Add to",
        kind_labels,
        horizontal=True,
        key="qat_kind_radio",
    )
    kind = TOOL_KINDS[kind_labels.index(kind_pick)]
    _render_kind_help(kind)
    _render_ai_status()

    trailer_labels, trailer_map = _trailer_options()
    trailer_pick = st.selectbox(
        "Tool Trailer (optional)",
        trailer_labels,
        key="qat_trailer",
        disabled=kind == "inventory",
    )
    trailer_id = trailer_map.get(trailer_pick, "")

    tab_manual, tab_photo, tab_receipt, tab_bulk = st.tabs(list(_METHOD_TABS))
    prefix = "qat"

    with tab_manual:
        _manual_form(kind, prefix=prefix, trailer_id=trailer_id)
    with tab_photo:
        _photo_form(kind, prefix=f"{prefix}_p", trailer_id=trailer_id, uploaded_by=uploaded_by)
    with tab_receipt:
        _receipt_form(kind, prefix=f"{prefix}_r", trailer_id=trailer_id, uploaded_by=uploaded_by)
    with tab_bulk:
        _bulk_form(kind, prefix=f"{prefix}_b", trailer_id=trailer_id)

    if st.button("Cancel", key="qat_cancel", use_container_width=True):
        close_quick_add_tool_dialog()
        st.rerun()


@st.dialog("Quick Add Tool", width="large", on_dismiss=close_quick_add_tool_dialog)
def show_quick_add_tool_dialog(uploaded_by: str | None = None) -> None:
    render_quick_add_tool_dialog(uploaded_by=uploaded_by)


__all__ = [
    "QUICK_ADD_OPEN_KEY",
    "close_quick_add_tool_dialog",
    "open_quick_add_tool_dialog",
    "render_quick_add_tool_dialog",
    "show_quick_add_tool_dialog",
]
