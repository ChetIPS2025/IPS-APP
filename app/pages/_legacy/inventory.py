from __future__ import annotations

import base64
import html
import urllib.parse
import pandas as pd
import streamlit as st

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
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
    from app.ui.streamlit_perf import ips_app_rerun
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
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore
    from ui.streamlit_perf import ips_app_rerun  # type: ignore
    from table_actions import (  # type: ignore
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )

_TABLE = "inventory_items"
_DELETE_CONFIRM_PREFIX = "inventory_delete"
_INV_DATA_VERSION_KEY = "inv_data_version"
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


def render() -> None:
    msg = st.session_state.pop("inventory_success", None)
    if msg:
        st.success(msg)

    can_edit = current_role() == "admin"

    st.session_state.setdefault("inventory_selected_id", None)
    st.session_state.setdefault("inventory_detail_collapsed", False)

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
            _clear_inv_checkbox_keys()
            pid = st.session_state.get("inventory_panel_id")
            sel = st.session_state.get("inventory_selected_id")
            if sel and str(sel) in {str(x) for x in pending}:
                st.session_state.pop("inventory_selected_id", None)
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

    # Legacy bulk-deactivate flag (detail panel uses direct update).
    if st.session_state.pop("_inv_do_deactivate", False) and can_edit:
        iid = str(st.session_state.get("inventory_selected_id") or "").strip()
        if iid:
            try:
                update_rows_admin(_TABLE, {"is_active": False}, {"id": iid})
                _bump_inventory_data_version()
                st.session_state["inventory_success"] = "Inventory item deactivated."
            except Exception as exc:
                st.error(f"Could not deactivate: {exc}")
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

    try:
        from app.pages.inventory_list_view import render_inventory_list_page
    except ImportError:
        from pages.inventory_list_view import render_inventory_list_page  # type: ignore

    render_inventory_list_page(
        df=df,
        rows=rows,
        can_edit=can_edit,
        data_version=int(st.session_state.get(_INV_DATA_VERSION_KEY, 0)),
        bump_data_version=_bump_inventory_data_version,
    )

    if can_edit:
        with st.expander("Admin: QR code tools", expanded=False):
            q1, q2 = st.columns(2, gap="small")
            with q1:
                if st.button(
                    "Generate missing QR codes",
                    use_container_width=True,
                    key="inv_btn_backfill_qr",
                    help="Assigns a unique INV-* QR to every item missing qr_code_value.",
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
                    help="Re-uploads QR PNGs using APP_BASE_URL. Reprint labels after running.",
                ):
                    try:
                        n = _regenerate_qr_pngs_current_app_url()
                        st.success(f"Regenerated {n} QR image(s). Reprint any physical labels.")
                    except Exception as exc:
                        st.error(f"Regenerate failed: {exc}")
                    _bump_inventory_data_version()
                    ips_app_rerun()

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
