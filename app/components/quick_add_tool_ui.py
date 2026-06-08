"""Quick Add Tool dialog — manual entry, photo, receipt, and bulk import."""

from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from app.services.asset_kits_service import get_tool_trailers
    from app.services.quick_add_tool_service import (
        TOOL_KIND_LABELS,
        TOOL_KINDS,
        attach_tool_photo,
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
        attach_tool_photo,
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
    if kind == "serialized":
        if parsed.get("serial_number"):
            st.session_state[f"{prefix}_photo_serial"] = parsed["serial_number"]
        if parsed.get("model"):
            st.session_state[f"{prefix}_photo_model"] = parsed["model"]


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
    photo = st.file_uploader(
        "Tool photo",
        type=["jpg", "jpeg", "png", "webp"],
        key=f"{prefix}_photo",
        help="Upload a photo, then Scan photo to autofill fields (requires TOOL_VISION_API_KEY).",
    )
    scan_col, search_col = st.columns(2)
    cfg = load_tool_ai_config()
    with scan_col:
        if st.button(
            "Scan photo",
            key=f"{prefix}_scan",
            use_container_width=True,
            disabled=photo is None or not cfg.vision_ready,
        ):
            try:
                parsed = extract_tool_from_photo(photo.getvalue(), photo.name, kind_hint=kind)
                _apply_scan_to_photo_fields(prefix, parsed, kind=kind)
                conf = float(parsed.get("confidence") or 0)
                st.success(f"Photo scanned ({conf:.0%} confidence). Review fields below.")
                if parsed.get("notes"):
                    st.caption(parsed["notes"])
            except Exception as exc:
                st.error(str(exc))
    with search_col:
        if st.button(
            "Match from image",
            key=f"{prefix}_img_search",
            use_container_width=True,
            disabled=photo is None or not cfg.image_search_ready,
        ):
            try:
                parsed = search_tool_by_image(photo.getvalue(), photo.name)
                _apply_scan_to_photo_fields(prefix, parsed, kind=kind)
                st.success("Image match applied. Review fields below.")
            except Exception as exc:
                st.error(str(exc))
    if photo is None:
        st.caption("Upload a tool photo to enable Scan photo and Match from image.")
    elif not cfg.vision_ready:
        st.caption("Set TOOL_VISION_API_KEY or OPENAI_API_KEY to enable Scan photo.")

    name = st.text_input("Tool name *", key=f"{prefix}_photo_name")
    if kind == "serialized":
        serial = st.text_input("Serial number *", key=f"{prefix}_photo_serial")
        model = st.text_input("Model", key=f"{prefix}_photo_model")
    else:
        serial = ""
        model = ""
        st.caption("Photos are stored on Serialized Tool assets. Small Tools and Inventory save without a photo for now.")
    if st.button("Save with photo", type="primary", key=f"{prefix}_photo_save", use_container_width=True):
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
        photo = st.session_state.get(f"{prefix}_photo")
        tool_id = str((result.data or {}).get("id") or "")
        if photo is not None and tool_id:
            photo_result = attach_tool_photo(tool_id, photo, uploaded_by=uploaded_by)
            if not photo_result.ok:
                st.warning(photo_result.error or "Tool saved; photo upload failed.")
        st.success(f"Added to {TOOL_KIND_LABELS[kind]}.")
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
