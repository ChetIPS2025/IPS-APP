from __future__ import annotations

import base64
import html
import urllib.parse
import pandas as pd
import streamlit as st

try:
    from app.ui.catalog_inventory_display import (
        prepare_catalog_inventory_display_df,
        sanitize_catalog_inventory_export_df,
    )
except ImportError:
    from ui.catalog_inventory_display import (  # type: ignore
        prepare_catalog_inventory_display_df,
        sanitize_catalog_inventory_export_df,
    )

try:
    from app.auth import current_role
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from app.db import (
        create_signed_url,
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from app.ips_crud_list_styles import inject_ips_crud_list_styles
    from app.ui.page_shell import render_page_header, render_section_header
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
    from app.ui.streamlit_perf import fragment, inject_scroll_preserve, ips_app_rerun
    from app.table_actions import (
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from db import (  # type: ignore
        create_signed_url,
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from ips_crud_list_styles import inject_ips_crud_list_styles  # type: ignore
    from ui.page_shell import render_page_header, render_section_header  # type: ignore
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore
    from ui.streamlit_perf import fragment, inject_scroll_preserve, ips_app_rerun  # type: ignore
    from table_actions import (  # type: ignore
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )

_TABLE = "inventory_items"
_DELETE_CONFIRM_PREFIX = "inventory_delete"
_INV_DATA_VERSION_KEY = "inv_data_version"
_INV_PAGE_SIZE_DEFAULT = 75


def _inventory_qr_embed_subject(qr_code_value: str) -> str:
    """String encoded inside printed QR (full app URL when ``APP_BASE_URL`` is set)."""
    try:
        from app.config import settings
        from app.services.qr_codes import inventory_scan_link_url
    except ImportError:
        from config import settings  # type: ignore
        from services.qr_codes import inventory_scan_link_url  # type: ignore
    return inventory_scan_link_url(
        qr_code_value=qr_code_value,
        app_base_url=getattr(settings, "app_base_url", "") or "",
    )


def _qr_png_bytes_or_none(qr_code_value: str) -> bytes | None:
    try:
        from app.services.qr_codes import generate_qr_png_bytes
    except ImportError:
        from services.qr_codes import generate_qr_png_bytes  # type: ignore
    subj = _inventory_qr_embed_subject(qr_code_value)
    for cand in (subj, str(qr_code_value or "").strip()):
        if not cand:
            continue
        try:
            return generate_qr_png_bytes(cand)
        except Exception:
            continue
    return None


def _inv_qr_img_html(data: str, *, size: int = 180) -> str:
    raw = str(data or "").strip()
    if not raw:
        return ""
    png = _qr_png_bytes_or_none(raw)
    if png:
        b64 = base64.b64encode(png).decode("ascii")
        src = f"data:image/png;base64,{b64}"
    else:
        enc = urllib.parse.quote(_inventory_qr_embed_subject(raw), safe="")
        src = html.escape(f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={enc}", quote=True)
    return (
        f'<div class="ips-inv-qr-wrap"><img src="{src}" '
        f'width="{size}" height="{size}" alt="QR code"/></div>'
    )


def _inventory_label_html(*, item_name: str, sku: str, qr_value: str, item_id: str) -> str:
    """Printable label: item name, QR (full scan URL), human-readable ``INV-*`` code."""
    _ = sku  # signature kept for callers; label layout uses name + QR + scan code only.
    nm = html.escape(str(item_name or "").strip() or "—")
    qv = html.escape(str(qr_value or "").strip() or "—")
    qr_block = _inv_qr_img_html(str(qr_value or "").strip(), size=240)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Inventory label</title>"
        "<style>body{font-family:system-ui,sans-serif;padding:16px;color:#111;} "
        ".code{font-size:1.25rem;font-weight:700;letter-spacing:0.02em;margin-top:8px;} "
        "h1{font-size:1.1rem;}</style></head><body>"
        f"<h1>{nm}</h1>"
        f"{qr_block}"
        f'<p class="code">{qv}</p>'
        f"<p style='font-size:0.75rem;color:#555;margin-top:16px;'>Item id: {html.escape(str(item_id or '')[:36])}</p>"
        "</body></html>"
    )


def _sync_qr_image_to_storage(item_id: str, qr_value: str) -> None:
    """Upload PNG for scan deep-link (or raw code) to storage and set ``qr_code_image_url`` when possible."""
    rid = str(item_id or "").strip()
    qv = str(qr_value or "").strip()
    if not rid or not qv:
        return
    png = _qr_png_bytes_or_none(qv)
    if not png:
        return
    path = f"inventory/qr/{rid}.png"
    try:
        upload_bytes_admin(path, png, content_type="image/png")
        update_rows_admin(_TABLE, {"qr_code_image_url": path}, {"id": rid})
    except Exception:
        pass


def _qr_value_in_use(*, value: str, exclude_item_id: str | None) -> bool:
    v = str(value or "").strip()
    if not v:
        return False
    rows = fetch_by_match_admin(_TABLE, {"qr_code_value": v}, limit=5)
    if not rows:
        return False
    if exclude_item_id is None:
        return True
    ex = str(exclude_item_id).strip()
    for r in rows:
        if str(r.get("id") or "").strip() != ex:
            return True
    return False


def _allocate_unique_qr(*, item_id: str, preferred: str | None, exclude_item_id: str | None) -> str:
    try:
        from app.services.qr_codes import allocate_unique_inventory_qr_value
    except ImportError:
        from services.qr_codes import allocate_unique_inventory_qr_value  # type: ignore
    return allocate_unique_inventory_qr_value(
        fetch_by_match_admin=fetch_by_match_admin,
        item_id=item_id,
        preferred=preferred,
        exclude_item_id=exclude_item_id,
    )


_PLACEHOLDER_THUMB = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _signed_url_for_inventory_image(image_url: str | None) -> str | None:
    """Return a URL ``st.image`` can load: HTTPS as-is, else storage path → signed URL."""
    s = str(image_url or "").strip()
    if not s:
        return None
    if s.startswith("http://") or s.startswith("https://"):
        return s
    try:
        u = create_signed_url(s, expires_in=3600)
        return u or None
    except Exception:
        return None


def _thumb_display_url(image_url: str | None) -> str:
    """URL for dataframe ImageColumn (never empty — use tiny placeholder)."""
    return _signed_url_for_inventory_image_cached(str(image_url or "").strip()) or _PLACEHOLDER_THUMB


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_inventory_items_df(data_version: int) -> list[dict]:
    """Cached inventory list; bump ``inv_data_version`` after writes."""
    return fetch_table_admin(_TABLE, limit=5000, order_by="item_name")


@st.cache_data(ttl=3300, show_spinner=False)
def _signed_url_for_inventory_image_cached(image_url: str) -> str | None:
    s = str(image_url or "").strip()
    if not s:
        return None
    return _signed_url_for_inventory_image(s)


def _bump_inventory_data_version() -> None:
    st.session_state[_INV_DATA_VERSION_KEY] = int(st.session_state.get(_INV_DATA_VERSION_KEY, 0)) + 1
    try:
        _fetch_inventory_items_df.clear()
        _signed_url_for_inventory_image_cached.clear()
    except Exception:
        pass
    try:
        from app.data_cache import clear_session_table_cache
    except ImportError:
        from data_cache import clear_session_table_cache  # type: ignore
    try:
        clear_session_table_cache()
    except Exception:
        pass


def _clear_inv_checkbox_keys() -> None:
    for k in list(st.session_state.keys()):
        if str(k).startswith("inv_select_"):
            del st.session_state[k]


def _inv_thumb_html(image_url: str | None, *, size: int = 36) -> str:
    raw = str(image_url or "").strip()
    url = _signed_url_for_inventory_image_cached(raw) if raw else None
    if not url:
        return '<p style="font-size:1.35rem;margin:0;line-height:1;">📦</p>'
    esc = html.escape(url, quote=True)
    return (
        f'<img src="{esc}" width="{size}" height="{size}" loading="lazy" '
        f'decoding="async" alt="" style="object-fit:cover;border-radius:4px;display:block;"/>'
    )


def _upload_item_image_from_upload(item_id: str, uploaded) -> str | None:
    """Resize upload, push to storage, return storage path for ``image_url``."""
    if uploaded is None:
        return None
    raw = uploaded.getvalue()
    if not raw:
        return None
    try:
        from app.services.inventory_images import inventory_item_image_storage_path, resize_inventory_image_bytes
    except ImportError:
        from services.inventory_images import (  # type: ignore
            inventory_item_image_storage_path,
            resize_inventory_image_bytes,
        )
    jpeg, ctype = resize_inventory_image_bytes(raw)
    path = inventory_item_image_storage_path(item_id)
    upload_bytes_admin(path, jpeg, content_type=ctype)
    return path


def _backfill_missing_qr_codes() -> int:
    """Assign ``qr_code_value`` (+ optional PNG) for rows missing a QR value."""
    rows = fetch_table_admin(_TABLE, columns="id,qr_code_value", limit=20000, order_by="item_name")
    n = 0
    for r in rows or []:
        if str(r.get("qr_code_value") or "").strip():
            continue
        rid = str(r.get("id") or "").strip()
        if not rid:
            continue
        try:
            from app.services.qr_codes import inventory_qr_from_item_id
        except ImportError:
            from services.qr_codes import inventory_qr_from_item_id  # type: ignore
        qv = _allocate_unique_qr(
            item_id=rid,
            preferred=inventory_qr_from_item_id(rid),
            exclude_item_id=rid,
        )
        update_rows_admin(_TABLE, {"qr_code_value": qv}, {"id": rid})
        _sync_qr_image_to_storage(rid, qv)
        n += 1
    return n


def _regenerate_qr_pngs_current_app_url() -> int:
    """Re-upload QR PNGs in storage using the current ``APP_BASE_URL`` (scan URL in the image updates)."""
    try:
        from app.config import settings
    except ImportError:
        from config import settings  # type: ignore
    base = str(getattr(settings, "app_base_url", "") or "").strip()
    if not base:
        raise RuntimeError(
            "APP_BASE_URL is not set. Set it to your live app URL (no trailing slash), then retry."
        )
    rows = fetch_table_admin(_TABLE, columns="id,qr_code_value", limit=20000, order_by="item_name")
    n = 0
    for r in rows or []:
        rid = str(r.get("id") or "").strip()
        qv = str(r.get("qr_code_value") or "").strip()
        if not rid or not qv:
            continue
        _sync_qr_image_to_storage(rid, qv)
        n += 1
    return n


def _clear_panel() -> None:
    st.session_state.pop("inventory_panel_mode", None)
    st.session_state.pop("inventory_panel_id", None)


def _inv_add_dialog_on_dismiss() -> None:
    _clear_panel()


def _inv_edit_dialog_on_dismiss() -> None:
    st.session_state["inventory_edit_popup_open"] = False
    st.session_state["editing_inventory_id"] = None


@st.dialog("Add inventory item", width="large", on_dismiss=_inv_add_dialog_on_dismiss)
def _inventory_add_dialog() -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add inventory item")

    if str(st.session_state.get("inv_f_cat") or "").strip().lower() == "materials":
        st.session_state.setdefault("inv_add_cat", "Materials")

    with st.container(border=True):
        with st.form("inv_add_item_form_v1", clear_on_submit=True):
            name = st.text_input("Item Name", key="inv_add_name")
            sku_add = st.text_input(
                "SKU (optional)",
                key="inv_add_sku",
                help="Alternate lookup on **Scan Inventory** if QR is not used.",
            )
            c1, c2 = st.columns(2, gap="small")
            category = c1.text_input("Category", key="inv_add_cat")
            unit = c2.text_input("Unit", value="EA", key="inv_add_unit")

            r1, r2, r3 = st.columns(3, gap="small")
            qty = r1.number_input(
                "Quantity on Hand", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="inv_add_qty"
            )
            reorder = r2.number_input(
                "Reorder Point", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="inv_add_reorder"
            )
            unit_cost = r3.number_input(
                "Unit Cost",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                key="inv_add_cost",
            )

            v1, v2 = st.columns(2, gap="small")
            vendor = v1.text_input("Vendor", key="inv_add_vendor")
            storage_location = v2.text_input("Storage Location", key="inv_add_loc")

            notes = st.text_area("Notes", key="inv_add_notes", height=72)
            img_add = st.file_uploader(
                "Item Image",
                type=["png", "jpg", "jpeg"],
                key="inv_img_add",
                help="Optional thumbnail (resized on upload). PNG or JPEG.",
            )
            qr_scan = st.text_input(
                "QR scan code (optional)",
                key="inv_add_qr",
                help="Unique value for **Scan Inventory**; leave blank to auto-assign after save.",
            )
            is_active = st.checkbox("Active", value=True, key="inv_add_active")

            submitted = st.form_submit_button(
                "Create item", type="primary", use_container_width=True
            )

    if st.button("Cancel", type="secondary", use_container_width=True, key="inv_add_cancel_dlg"):
        _clear_panel()
        ips_app_rerun()

    if submitted:
        t = str(name or "").strip()
        if not t:
            st.error("Item Name is required.")
            return
        qr_t = str(qr_scan or "").strip()
        payload = {
            "item_name": t,
            "category": str(category or "").strip(),
            "unit": str(unit or "").strip() or "EA",
            "quantity_on_hand": float(qty or 0),
            "reorder_point": float(reorder or 0),
            "unit_cost": float(unit_cost) if float(unit_cost or 0) > 0 else None,
            "vendor": str(vendor or "").strip(),
            "storage_location": str(storage_location or "").strip(),
            "notes": str(notes or "").strip(),
            "is_active": bool(is_active),
        }
        if qr_t:
            if _qr_value_in_use(value=qr_t, exclude_item_id=None):
                st.error("That QR code value is already in use. Choose another or leave blank to auto-generate.")
                return
            payload["qr_code_value"] = qr_t
        sku_t = str(sku_add or "").strip()
        if sku_t:
            payload["sku"] = sku_t
        try:
            row = insert_row_admin(_TABLE, payload)
        except Exception as exc:
            if "sku" in str(exc).lower():
                st.error(
                    f"Could not save: {exc} — run migration **`sql/028_inventory_sku_txn_created_by.sql`** if SKU column is missing."
                )
            else:
                st.error(f"Could not save: {exc}")
            return
        rid = str(row.get("id") or "")
        if rid:
            qv = str(row.get("qr_code_value") or "").strip()
            if not qv:
                try:
                    from app.services.qr_codes import inventory_qr_from_item_id
                except ImportError:
                    from services.qr_codes import inventory_qr_from_item_id  # type: ignore
                qv = _allocate_unique_qr(
                    item_id=rid,
                    preferred=inventory_qr_from_item_id(rid),
                    exclude_item_id=rid,
                )
                update_rows_admin(_TABLE, {"qr_code_value": qv}, {"id": rid})
            else:
                qv = str(row.get("qr_code_value") or "").strip()
            _sync_qr_image_to_storage(rid, qv)
        if rid and img_add is not None:
            try:
                pth = _upload_item_image_from_upload(rid, img_add)
                if pth:
                    update_rows_admin(_TABLE, {"image_url": pth}, {"id": rid})
            except Exception as exc:
                if "image_url" in str(exc).lower() or "column" in str(exc).lower():
                    st.warning(
                        "Image was not saved — run migration **`sql/035_inventory_image_url.sql`** "
                        f"then try again. ({exc})"
                    )
                else:
                    st.warning(f"Image upload skipped: {exc}")
        _clear_panel()
        _bump_inventory_data_version()
        st.session_state["inventory_success"] = "Inventory item added."
        ips_app_rerun()


@st.dialog("Edit inventory item", width="large", on_dismiss=_inv_edit_dialog_on_dismiss)
def _inventory_edit_dialog(row: dict) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    rid = str(row.get("id") or "")
    pk = f"inv_ed_{rid}"
    st.markdown("### Edit inventory item")
    st.caption(f"ID `{rid[:8]}…`")

    with st.container(border=True):
        with st.form(f"inv_edit_item_form_{rid}", clear_on_submit=False):
            name = st.text_input("Item Name", value=str(row.get("item_name") or ""), key=f"{pk}_name")
            sku_ed = st.text_input(
                "SKU (optional)",
                value=str(row.get("sku") or ""),
                key=f"{pk}_sku",
                help="Alternate lookup on **Scan Inventory**.",
            )
            c1, c2 = st.columns(2, gap="small")
            category = c1.text_input("Category", value=str(row.get("category") or ""), key=f"{pk}_cat")
            unit = c2.text_input("Unit", value=str(row.get("unit") or "EA"), key=f"{pk}_unit")

            r1, r2, r3 = st.columns(3, gap="small")
            qty = r1.number_input(
                "Quantity on Hand",
                min_value=0.0,
                value=float(row.get("quantity_on_hand") or 0),
                step=1.0,
                format="%.2f",
                key=f"{pk}_qty",
            )
            reorder = r2.number_input(
                "Reorder Point",
                min_value=0.0,
                value=float(row.get("reorder_point") or 0),
                step=1.0,
                format="%.2f",
                key=f"{pk}_reorder",
            )
            uc_val = row.get("unit_cost")
            try:
                uc_default = float(uc_val) if uc_val is not None and str(uc_val).strip() != "" else 0.0
            except (TypeError, ValueError):
                uc_default = 0.0
            unit_cost = r3.number_input(
                "Unit Cost",
                min_value=0.0,
                value=uc_default,
                step=0.01,
                format="%.2f",
                key=f"{pk}_cost",
            )

            v1, v2 = st.columns(2, gap="small")
            vendor = v1.text_input("Vendor", value=str(row.get("vendor") or ""), key=f"{pk}_vendor")
            storage_location = v2.text_input(
                "Storage Location", value=str(row.get("storage_location") or ""), key=f"{pk}_loc"
            )

            notes = st.text_area("Notes", value=str(row.get("notes") or ""), height=72, key=f"{pk}_notes")
            st.caption("Item photo")
            img_existing = _signed_url_for_inventory_image(str(row.get("image_url") or "").strip())
            if img_existing:
                st.image(img_existing, width=80)
            else:
                st.markdown('<p style="font-size:2rem;margin:0;line-height:1;">📦</p>', unsafe_allow_html=True)
            img_ed = st.file_uploader(
                "Item Image",
                type=["png", "jpg", "jpeg"],
                key=f"inv_img_{rid}",
                help="Upload a new image to replace the thumbnail (resized on save).",
            )
            qr_in = st.text_input(
                "QR scan code",
                value=str(row.get("qr_code_value") or "").strip(),
                key=f"{pk}_qr",
                help="Printed / scanned value for **Scan Inventory**.",
            )
            is_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")

            submitted = st.form_submit_button(
                "Save",
                type="primary",
                use_container_width=True,
            )

        with st.expander("QR Label / Code", expanded=False):
            qr_cur = str(row.get("qr_code_value") or "").strip()
            if qr_cur:
                st.caption("Label preview")
                st.markdown(_inv_qr_img_html(qr_cur), unsafe_allow_html=True)
                html_doc = _inventory_label_html(
                    item_name=str(row.get("item_name") or ""),
                    sku=str(row.get("sku") or ""),
                    qr_value=qr_cur,
                    item_id=rid,
                )
                st.download_button(
                    "Print QR label (HTML)",
                    data=html_doc.encode("utf-8"),
                    file_name=f"inventory_label_{rid[:8]}.html",
                    mime="text/html",
                    key=f"{pk}_dl_lbl",
                )
                png = _qr_png_bytes_or_none(qr_cur)
                if png:
                    st.download_button(
                        "Download QR (PNG)",
                        data=png,
                        file_name=f"inventory_qr_{rid[:8]}.png",
                        mime="image/png",
                        key=f"{pk}_dl_png",
                    )
            if st.button("Generate new QR code", key=f"{pk}_qrgen", help="Assigns a new unique scan code"):
                try:
                    nv = _allocate_unique_qr(
                        item_id=str(row.get("id") or ""),
                        preferred=None,
                        exclude_item_id=str(row.get("id") or ""),
                    )
                    update_rows_admin(_TABLE, {"qr_code_value": nv}, {"id": row["id"]})
                    _sync_qr_image_to_storage(str(row.get("id") or ""), nv)
                except Exception as exc:
                    st.error(f"Could not update QR: {exc}")
                    return
                ips_app_rerun()

    if st.button("Cancel", type="secondary", use_container_width=True, key=f"{pk}_cancel_dlg"):
        st.session_state["inventory_edit_popup_open"] = False
        st.session_state["editing_inventory_id"] = None
        st.session_state["selected_inventory_ids"] = []
        _clear_inv_checkbox_keys()
        clear_selected_ids(TABLE_KEY_INVENTORY)
        _clear_panel()
        ips_app_rerun()

    if submitted:
        t = str(name or "").strip()
        if not t:
            st.error("Item Name is required.")
            return
        qr_t = str(qr_in or "").strip()
        old_qr = str(row.get("qr_code_value") or "").strip()
        if qr_t and qr_t != old_qr and _qr_value_in_use(value=qr_t, exclude_item_id=str(row.get("id") or "")):
            st.error("That QR code value is already used by another item.")
            return
        payload = {
            "item_name": t,
            "category": str(category or "").strip(),
            "unit": str(unit or "").strip() or "EA",
            "quantity_on_hand": float(qty or 0),
            "reorder_point": float(reorder or 0),
            "unit_cost": float(unit_cost) if float(unit_cost or 0) > 0 else None,
            "vendor": str(vendor or "").strip(),
            "storage_location": str(storage_location or "").strip(),
            "notes": str(notes or "").strip(),
            "is_active": bool(is_active),
            "qr_code_value": qr_t or None,
            "sku": str(sku_ed or "").strip() or None,
        }
        try:
            update_rows_admin(_TABLE, payload, {"id": row["id"]})
        except Exception as exc:
            if "sku" in str(exc).lower():
                st.error(
                    f"Could not update: {exc} — apply **`sql/028_inventory_sku_txn_created_by.sql`** for SKU support."
                )
            else:
                st.error(f"Could not update: {exc}")
            return
        final_qr = str(qr_t or old_qr or "").strip()
        if not final_qr:
            try:
                from app.services.qr_codes import inventory_qr_from_item_id
            except ImportError:
                from services.qr_codes import inventory_qr_from_item_id  # type: ignore
            final_qr = _allocate_unique_qr(
                item_id=str(row.get("id") or ""),
                preferred=inventory_qr_from_item_id(str(row.get("id") or "")),
                exclude_item_id=str(row.get("id") or ""),
            )
            update_rows_admin(_TABLE, {"qr_code_value": final_qr}, {"id": row["id"]})
        _sync_qr_image_to_storage(str(row.get("id") or ""), final_qr)
        if img_ed is not None:
            try:
                pth = _upload_item_image_from_upload(str(row.get("id") or ""), img_ed)
                if pth:
                    update_rows_admin(_TABLE, {"image_url": pth}, {"id": row["id"]})
            except Exception as exc:
                if "image_url" in str(exc).lower() or "column" in str(exc).lower():
                    st.warning(
                        "Image was not saved — run **`sql/035_inventory_image_url.sql`**. "
                        f"({exc})"
                    )
                else:
                    st.warning(f"Image upload skipped: {exc}")
        st.session_state["inventory_edit_mode"] = False
        st.session_state["editing_inventory_id"] = None
        st.session_state["selected_inventory_ids"] = []
        _clear_inv_checkbox_keys()
        clear_selected_ids(TABLE_KEY_INVENTORY)
        _clear_panel()
        st.session_state["inventory_success"] = "Inventory item updated."
        st.session_state["inventory_edit_popup_open"] = False
        st.session_state["editing_inventory_id"] = None
        _bump_inventory_data_version()
        ips_app_rerun()


def _render_inventory_action_bar(
    *, df_all: pd.DataFrame, visible_df: pd.DataFrame, can_edit: bool, selected_key: str
) -> None:
    """
    Materials-style bar (same sizing/spacing), extended with export/select-all/clear.

    Selection is stored in ``session_state[selected_key]`` and mirrored via ``TABLE_KEY_INVENTORY``.
    """
    inject_ips_crud_list_styles()
    inject_table_action_styles()

    sel = [str(x) for x in (st.session_state.get(selected_key) or []) if str(x).strip()]
    n = len(sel)
    one = n == 1
    none = n == 0

    # Export data (selected rows from currently loaded table)
    exp_ok = bool(not df_all.empty and "id" in df_all.columns and n >= 1)
    csv_bytes = b""
    if exp_ok:
        sub = df_all[df_all["id"].astype(str).isin([str(x) for x in sel])]
        csv_bytes = sanitize_catalog_inventory_export_df(sub).to_csv(index=False).encode("utf-8")

    vis_ids: list[str] = []
    if not visible_df.empty and "id" in visible_df.columns:
        vis_ids = visible_df["id"].astype(str).tolist()
    sel_set = {str(x) for x in sel}
    vis_set = set(vis_ids)
    all_visible_selected = bool(vis_set) and sel_set == vis_set

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0, b1, b2, b3, b4, b5, b6 = st.columns([1.1, 1, 1, 1, 1, 1, 1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b0:
            if st.button(
                "Add Inventory Item",
                type="primary",
                use_container_width=True,
                disabled=not can_edit,
                key="inv_btn_add",
            ):
                st.session_state["inventory_panel_mode"] = "add"
                st.session_state["inventory_panel_id"] = None
                ips_app_rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not one,
                key="inv_btn_edit",
            ):
                st.session_state["inventory_edit_popup_open"] = True
                st.session_state["editing_inventory_id"] = str(sel[0])
                ips_app_rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="inv_btn_deactivate",
            ):
                st.session_state["_inv_do_deactivate"] = True
                ips_app_rerun()
        with b3:
            if st.button(
                "Delete",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="inv_btn_delete",
            ):
                open_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
                st.session_state["inventory_pending_delete_ids"] = [str(x) for x in sel]
                ips_app_rerun()
        with b4:
            st.download_button(
                "Export Selected",
                data=csv_bytes,
                file_name="inventory_export.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=not exp_ok,
                key="inv_btn_export",
            )
        with b5:
            if st.button(
                "Select All Visible",
                use_container_width=True,
                disabled=not vis_ids or all_visible_selected,
                key="inv_btn_sel_all",
            ):
                st.session_state[selected_key] = list(vis_ids)
                set_selected_ids(TABLE_KEY_INVENTORY, list(vis_ids))
                _clear_inv_checkbox_keys()
                st.rerun()
        with b6:
            if st.button(
                "Clear selection",
                use_container_width=True,
                disabled=none,
                key="inv_btn_clear",
            ):
                st.session_state[selected_key] = []
                _clear_inv_checkbox_keys()
                clear_selected_ids(TABLE_KEY_INVENTORY)
                st.session_state.pop("inventory_pending_delete_ids", None)
                st.rerun()
        if can_edit:
            q1, q2 = st.columns(2, gap="small")
            with q1:
                if st.button(
                    "Generate missing QR codes",
                    use_container_width=True,
                    key="inv_btn_backfill_qr",
                    help="Assigns a unique INV-* QR to every item missing qr_code_value, then uploads a PNG when storage is available.",
                ):
                    try:
                        n = _backfill_missing_qr_codes()
                        st.success(f"Generated QR codes for {n} item(s).")
                    except Exception as exc:
                        st.error(f"Backfill failed: {exc}")
                    _bump_inventory_data_version()
                    ips_app_rerun()
            with q2:
                if st.button(
                    "Regenerate QR codes (current app URL)",
                    use_container_width=True,
                    key="inv_btn_regen_qr_png",
                    help="Re-uploads QR PNGs using APP_BASE_URL so scans open the live app. Reprint labels after running.",
                ):
                    try:
                        n = _regenerate_qr_pngs_current_app_url()
                        st.success(f"Regenerated {n} QR image(s). Reprint any physical labels.")
                    except Exception as exc:
                        st.error(f"Regenerate failed: {exc}")
                    _bump_inventory_data_version()
                    ips_app_rerun()


def _render_inventory_list_body(*, df: pd.DataFrame, can_edit: bool, selected_key: str) -> None:
    """Filters → low stock banner → paginated table → action bar (runs inside ``@fragment``)."""
    inject_table_action_styles()
    st.markdown(
        """
<style>
section[data-testid="stMain"]:has(.ips-inventory-list-anchor) [data-testid="stElementContainer"] {
  margin-bottom: 0.12rem !important;
}
section[data-testid="stMain"]:has(.ips-inventory-list-anchor) [data-testid="stHorizontalBlock"] {
  gap: 0.35rem !important;
  align-items: center !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<span class="ips-inventory-list-anchor" aria-hidden="true"></span>', unsafe_allow_html=True)
    render_section_header("Inventory list", "Filter, select rows, and use the action bar below.")
    _sel_n = len([x for x in (st.session_state.get(selected_key) or []) if str(x).strip()])
    if _sel_n:
        st.caption(f"{_sel_n} row(s) selected")

    if df.empty:
        st.selectbox("Filter Category", ["All", "Materials"], key="inv_f_cat")
        st.info("No inventory items found.")
        if can_edit and st.button(
            "Add Inventory Item", type="primary", use_container_width=True, key="inv_empty_add"
        ):
            st.session_state["inventory_panel_mode"] = "add"
            st.session_state["inventory_panel_id"] = None
            ips_app_rerun()
        return

    filter_cols = st.columns([1, 2, 1], gap="small")
    categories = sorted(
        set(
            ["Materials"]
            + [
                c
                for c in df.get("category", pd.Series(dtype=str))
                .dropna()
                .astype(str)
                .unique()
                .tolist()
                if str(c).strip()
            ]
        )
    )
    filter_cols[0].selectbox("Filter Category", ["All"] + categories, key="inv_f_cat")
    filter_cols[1].text_input(
        "Search Inventory",
        placeholder="Name, SKU, QR, category, vendor, location, notes",
        key="inv_f_search",
    )
    active_options = ["All", "Active Only", "Inactive Only"]
    filter_cols[2].selectbox("Status", active_options, key="inv_f_active")

    selected_category = st.session_state.get("inv_f_cat", "All")
    search = st.session_state.get("inv_f_search", "")
    selected_active = st.session_state.get("inv_f_active", "All")

    filtered = df.copy()
    if selected_category != "All" and "category" in filtered.columns:
        sc = str(selected_category).strip().lower()
        filtered = filtered[
            filtered["category"].astype(str).str.strip().str.lower() == sc
        ]
    if selected_active == "Active Only" and "is_active" in filtered.columns:
        filtered = filtered[filtered["is_active"] == True]  # noqa: E712
    elif selected_active == "Inactive Only" and "is_active" in filtered.columns:
        filtered = filtered[filtered["is_active"] == False]  # noqa: E712
    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        filtered = filtered[mask.any(axis=1)]

    _filt_sig = (selected_category, search, selected_active)
    if st.session_state.get("inv_filter_sig") != _filt_sig:
        st.session_state["inv_filter_sig"] = _filt_sig
        st.session_state["inv_page"] = 0

    qoh_s = pd.to_numeric(filtered.get("quantity_on_hand", 0), errors="coerce").fillna(0)
    if "reorder_point" in filtered.columns:
        rp_s = pd.to_numeric(filtered["reorder_point"], errors="coerce").fillna(0)
    else:
        rp_s = pd.Series(0.0, index=filtered.index)
    low_mask = qoh_s <= rp_s
    n_low = int(low_mask.sum()) if len(filtered) else 0
    if n_low > 0:
        with st.container(border=True):
            render_section_header("Low stock alert", f"{n_low} visible item(s) at or below reorder point.")
        with st.expander("Low stock detail (visible filters)", expanded=False):
            cols_show = [c for c in ("item_name", "sku", "quantity_on_hand", "reorder_point", "vendor") if c in filtered.columns]
            if cols_show:
                sub = filtered.loc[low_mask, cols_show].copy()
                if "quantity_on_hand" in sub.columns and "reorder_point" in sub.columns:
                    qv = pd.to_numeric(sub["quantity_on_hand"], errors="coerce").fillna(0)
                    rv = pd.to_numeric(sub["reorder_point"], errors="coerce").fillna(0)
                    gap = (rv - qv).clip(lower=0)
                    sub["suggest_qty"] = gap
                    sub.loc[sub["suggest_qty"] <= 0, "suggest_qty"] = pd.NA
                if "image_url" in filtered.columns:
                    sub["image_url"] = filtered.loc[low_mask, "image_url"].map(_thumb_display_url).values
                else:
                    sub["image_url"] = _PLACEHOLDER_THUMB
                disp = prepare_catalog_inventory_display_df(
                    sub,
                    extra_hidden=frozenset(),
                )
                img_cfg = {}
                if "Photo" in disp.columns:
                    img_cfg["Photo"] = st.column_config.ImageColumn("Photo", width="small")
                st.dataframe(
                    disp,
                    use_container_width=True,
                    hide_index=True,
                    column_config=img_cfg or {},
                )
                st.caption("**Suggest qty** = shortfall to reorder point (informational).")

    if filtered.empty:
        st.warning("No inventory items match your filters.")
        if can_edit and st.button(
            "Add Inventory Item", type="primary", use_container_width=True, key="inv_filtered_empty_add"
        ):
            st.session_state["inventory_panel_mode"] = "add"
            st.session_state["inventory_panel_id"] = None
            ips_app_rerun()
        return

    page_size = int(st.session_state.get("inv_page_size", _INV_PAGE_SIZE_DEFAULT))
    page_size = max(25, min(150, page_size))
    total_rows = len(filtered)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = int(st.session_state.get("inv_page", 0))
    page = max(0, min(page, total_pages - 1))
    if page != int(st.session_state.get("inv_page", 0)):
        st.session_state["inv_page"] = page

    pg1, pg2, pg3, pg4 = st.columns([1.2, 1, 1, 2.2], gap="small")
    with pg1:
        if st.button("← Prev", key="inv_page_prev", disabled=page <= 0, use_container_width=True):
            st.session_state["inv_page"] = page - 1
            st.rerun()
    with pg2:
        if st.button(
            "Next →",
            key="inv_page_next",
            disabled=page >= total_pages - 1,
            use_container_width=True,
        ):
            st.session_state["inv_page"] = page + 1
            st.rerun()
    with pg3:
        st.caption(f"Page **{page + 1}** / **{total_pages}**")
    with pg4:
        st.caption(f"**{total_rows:,}** matching · **{page_size}** per page")

    page_df = filtered.iloc[page * page_size : (page + 1) * page_size]
    page_ids = [str(x) for x in page_df.get("id", pd.Series(dtype=str)).astype(str).tolist() if str(x).strip()]

    cur_selected = [str(x) for x in (st.session_state.get(selected_key) or []) if str(x).strip()]
    sel_set = set(cur_selected)

    # Sel | Photo | Item | SKU | On Hand | Reorder | Status
    header = st.columns([0.38, 0.55, 2.05, 1.0, 0.9, 1.1, 1.0], gap="small")
    header[0].markdown("**Sel**")
    header[1].markdown("**Photo**")
    header[2].markdown("**Item**")
    header[3].markdown("**SKU**")
    header[4].markdown("**On Hand**")
    header[5].markdown("**Reorder**")
    header[6].markdown("**Status**")

    for _, row in page_df.iterrows():
        item_id = str(row.get("id") or "").strip()
        if not item_id:
            continue
        ck_key = f"inv_select_{item_id}"
        if ck_key not in st.session_state:
            st.session_state[ck_key] = item_id in sel_set
        cols = st.columns([0.38, 0.55, 2.05, 1.0, 0.9, 1.1, 1.0], gap="small")
        with cols[0]:
            st.checkbox("", key=ck_key, label_visibility="collapsed")
        with cols[1]:
            st.markdown(_inv_thumb_html(str(row.get("image_url") or "")), unsafe_allow_html=True)
        cols[2].write(str(row.get("item_name") or "—"))
        cols[3].write(str(row.get("sku") or "—"))
        cols[4].write(str(row.get("quantity_on_hand") or "0"))
        cols[5].write(str(row.get("reorder_point") or "0"))
        cols[6].write("Active" if bool(row.get("is_active", True)) else "Inactive")

    for iid in page_ids:
        ck_key = f"inv_select_{iid}"
        if st.session_state.get(ck_key):
            sel_set.add(iid)
        else:
            sel_set.discard(iid)

    st.session_state[selected_key] = list(sel_set)
    selected_ids = list(st.session_state[selected_key])

    with st.container():
        set_selected_ids(TABLE_KEY_INVENTORY, selected_ids)
        _render_inventory_action_bar(
            df_all=df, visible_df=filtered, can_edit=can_edit, selected_key=selected_key
        )

    sel_ids = selected_ids
    if len(sel_ids) != 1:
        if st.session_state.get("inventory_edit_popup_open"):
            st.session_state["inventory_edit_popup_open"] = False
            st.session_state["editing_inventory_id"] = None


@fragment
def _render_inventory_list_fragment(*, df: pd.DataFrame, can_edit: bool, selected_key: str) -> None:
    """Isolated rerun scope for filters, table selection, and action bar."""
    inject_scroll_preserve("inventory")
    _render_inventory_list_body(df=df, can_edit=can_edit, selected_key=selected_key)


def render() -> None:
    render_page_header("Inventory", "Manage stock levels, materials, vendors, and usage.")

    msg = st.session_state.pop("inventory_success", None)
    if msg:
        st.success(msg)

    can_edit = current_role() == "admin"

    selected_key = "selected_inventory_ids"
    if selected_key not in st.session_state or not isinstance(st.session_state.get(selected_key), list):
        st.session_state[selected_key] = []

    # Ensure required session keys exist (explicitly requested by spec)
    st.session_state.setdefault("inventory_panel_mode", None)
    st.session_state.setdefault("inventory_panel_id", None)
    st.session_state.setdefault("inventory_edit_popup_open", False)
    st.session_state.setdefault("editing_inventory_id", None)

    st.session_state.setdefault(_INV_DATA_VERSION_KEY, 0)
    try:
        rows = _fetch_inventory_items_df(int(st.session_state.get(_INV_DATA_VERSION_KEY, 0)))
    except Exception:
        st.warning(
            "Inventory table is not available yet. Run migration **`sql/015_inventory_items.sql`** "
            "in the Supabase SQL editor, then refresh."
        )
        return

    df = pd.DataFrame(rows)

    if df.empty:
        _fc = str(st.session_state.get("inv_f_cat") or "All").strip()
        if _fc not in ("All", "Materials"):
            st.session_state["inv_f_cat"] = "All"

    if not df.empty and "category" in df.columns:
        _raw_cats = [
            c
            for c in df.get("category", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .unique()
            .tolist()
            if str(c).strip()
        ]
        _cat_opts = sorted(set(["Materials"] + _raw_cats))
        _cur_fc = str(st.session_state.get("inv_f_cat") or "All").strip()
        if _cur_fc != "All" and _cur_fc not in _cat_opts:
            st.session_state["inv_f_cat"] = "All"

    # --- Delete confirmation (matches Materials pattern) ---
    _del_open = destructive_confirm_open_key(_DELETE_CONFIRM_PREFIX)
    if st.session_state.get(_del_open) and not can_edit:
        close_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
        st.session_state.pop("inventory_pending_delete_ids", None)
    elif st.session_state.get(_del_open) and can_edit:
        pending = list(st.session_state.get("inventory_pending_delete_ids") or [])
        if not pending:
            close_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
            st.session_state.pop("inventory_pending_delete_ids", None)
            ips_app_rerun()

        id_to_label: dict[str, str] = {}
        for r in rows:
            rid = str(r.get("id"))
            id_to_label[rid] = str(r.get("item_name") or "").strip() or rid
        name_lines = [id_to_label.get(pid, pid[:10] + "…") for pid in pending]
        n_pending = len(pending)
        msg = (
            "Are you sure you want to delete this inventory item?"
            if n_pending == 1
            else f"Are you sure you want to delete these {n_pending} inventory items?"
        )

        def _on_confirm_delete() -> None:
            for iid in pending:
                try:
                    delete_rows_admin(_TABLE, {"id": iid})
                except Exception as exc:
                    st.error(f"Could not delete {iid}: {exc}")
            st.session_state.pop("inventory_pending_delete_ids", None)
            st.session_state[selected_key] = []
            _clear_inv_checkbox_keys()
            pid = st.session_state.get("inventory_panel_id")
            if pid and str(pid) in {str(x) for x in pending}:
                _clear_panel()
            _bump_inventory_data_version()
            st.session_state["inventory_success"] = "Inventory item(s) deleted where permitted."

        def _on_cancel_delete() -> None:
            st.session_state.pop("inventory_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=_DELETE_CONFIRM_PREFIX,
            title="Confirm Delete",
            message=msg,
            confirm_label="Confirm Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )
        return

    # --- Deactivate (matches Materials pattern) ---
    if st.session_state.pop("_inv_do_deactivate", False) and can_edit:
        sel_ids = [str(x) for x in (st.session_state.get(selected_key) or []) if str(x).strip()]
        if sel_ids:
            for iid in sel_ids:
                try:
                    update_rows_admin(_TABLE, {"is_active": False}, {"id": iid})
                except Exception as exc:
                    st.error(f"Could not deactivate {iid}: {exc}")
            st.session_state[selected_key] = []
            _clear_inv_checkbox_keys()
            _clear_panel()
            _bump_inventory_data_version()
            st.session_state["inventory_success"] = "Selected inventory items deactivated."
            ips_app_rerun()

    if current_role() in {"admin", "pm"}:
        with st.expander("Import vendor quote (adds stocked Materials rows)", expanded=False):
            st.caption(
                "Creates **inventory_items** in the **Materials** category for stock tracking. "
                "Copy into the quote catalog from **Estimate Materials** when you need estimate lines."
            )
            try:
                from app.pages.material_quote_import import render_material_quote_import_form
            except ImportError:
                from pages.material_quote_import import render_material_quote_import_form  # type: ignore
            render_material_quote_import_form(return_to_materials=False)

    # --- Panel routing ---
    panel_mode = st.session_state.get("inventory_panel_mode")
    if panel_mode == "add" and not can_edit:
        _clear_panel()
        panel_mode = None

    # Filters → low stock → table → action bar (fragment-isolated reruns).
    _render_inventory_list_fragment(df=df, can_edit=can_edit, selected_key=selected_key)

    if panel_mode == "add" and can_edit:
        _inventory_add_dialog()

    if st.session_state.get("inventory_edit_popup_open"):
        if not can_edit:
            st.session_state["inventory_edit_popup_open"] = False
            st.session_state["editing_inventory_id"] = None
            ips_app_rerun()
        eid = str(st.session_state.get("editing_inventory_id") or "").strip()
        if not eid:
            st.session_state["inventory_edit_popup_open"] = False
            ips_app_rerun()
        pr = fetch_by_match_admin(_TABLE, {"id": eid}, limit=1)
        panel_row = pr[0] if pr else None
        if not panel_row:
            st.session_state["inventory_edit_popup_open"] = False
            st.session_state["editing_inventory_id"] = None
            ips_app_rerun()
        _inventory_edit_dialog(dict(panel_row))
