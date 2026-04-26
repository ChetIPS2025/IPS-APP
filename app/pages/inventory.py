from __future__ import annotations

import base64
import html
import urllib.parse
import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from app.db import (
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from app.ips_crud_list_styles import (
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
    from app.table_actions import (
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from db import (  # type: ignore
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
    from table_actions import (  # type: ignore
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
    )

_TABLE = "inventory_items"
_DELETE_CONFIRM_PREFIX = "inventory_delete"


def _qr_png_bytes_or_none(value: str) -> bytes | None:
    try:
        from app.services.qr_codes import generate_qr_png_bytes
    except ImportError:
        from services.qr_codes import generate_qr_png_bytes  # type: ignore
    try:
        return generate_qr_png_bytes(str(value or "").strip())
    except Exception:
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
        enc = urllib.parse.quote(raw, safe="")
        src = html.escape(f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={enc}", quote=True)
    return (
        f'<div class="ips-inv-qr-wrap"><img src="{src}" '
        f'width="{size}" height="{size}" alt="QR code"/></div>'
    )


def _inventory_label_html(*, item_name: str, sku: str, qr_value: str, item_id: str) -> str:
    """Simple printable label (HTML) with name, SKU, QR image, and scan value."""
    nm = html.escape(str(item_name or "").strip() or "—")
    sk = html.escape(str(sku or "").strip() or "—")
    qv = html.escape(str(qr_value or "").strip() or "—")
    qr_block = _inv_qr_img_html(str(qr_value or "").strip(), size=240)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Inventory label</title>"
        "<style>body{font-family:system-ui,sans-serif;padding:16px;color:#111;} "
        ".meta{margin:8px 0;} h1{font-size:1.1rem;}</style></head><body>"
        f"<h1>{nm}</h1>"
        f'<p class="meta"><strong>SKU:</strong> {sk}</p>'
        f'<p class="meta"><strong>QR value:</strong> {qv}</p>'
        f"{qr_block}"
        f"<p class='meta'><small>Item id: {html.escape(str(item_id or '')[:36])}</small></p>"
        "</body></html>"
    )


def _sync_qr_image_to_storage(item_id: str, qr_value: str) -> None:
    """Upload PNG for ``qr_value`` to storage and set ``qr_code_image_url`` when possible."""
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


def _money(v) -> str:
    try:
        if v is None or str(v).strip() == "":
            return "—"
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _clear_panel() -> None:
    st.session_state.pop("inventory_panel_mode", None)
    st.session_state.pop("inventory_panel_id", None)


def _render_inventory_action_bar(*, df_all: pd.DataFrame, visible_df: pd.DataFrame, can_edit: bool) -> None:
    """
    Materials-style bar (same sizing/spacing), extended with export/select-all/clear.

    Selection storage is handled by table_actions via TABLE_KEY_INVENTORY → selected_inventory_ids.
    """
    inject_ips_crud_list_styles()
    inject_table_action_styles()

    sel = get_selected_ids(TABLE_KEY_INVENTORY)
    n = len(sel)
    one = n == 1
    none = n == 0

    # Export data (selected rows from currently loaded table)
    exp_ok = bool(not df_all.empty and "id" in df_all.columns and n >= 1)
    csv_bytes = b""
    if exp_ok:
        sub = df_all[df_all["id"].astype(str).isin([str(x) for x in sel])]
        csv_bytes = sub.to_csv(index=False).encode("utf-8")

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
                st.rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not one,
                key="inv_btn_edit",
            ):
                st.session_state["inventory_panel_mode"] = "edit"
                st.session_state["inventory_panel_id"] = str(sel[0])
                st.rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="inv_btn_deactivate",
            ):
                st.session_state["_inv_do_deactivate"] = True
                st.rerun()
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
                st.rerun()
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
                set_selected_ids(TABLE_KEY_INVENTORY, list(vis_ids))
                st.rerun()
        with b6:
            if st.button(
                "Clear selection",
                use_container_width=True,
                disabled=none,
                key="inv_btn_clear",
            ):
                clear_selected_ids(TABLE_KEY_INVENTORY)
                st.session_state.pop("inventory_pending_delete_ids", None)
                st.rerun()
        if can_edit:
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
                st.rerun()


def _render_add_panel() -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Add inventory item")

        name = st.text_input("Item Name", key="inv_add_name")
        sku_add = st.text_input("SKU (optional)", key="inv_add_sku", help="Alternate lookup on **Scan Inventory** if QR is not used.")
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
        qr_scan = st.text_input(
            "QR scan code (optional)",
            key="inv_add_qr",
            help="Unique value for **Scan Inventory**; leave blank to auto-assign after save.",
        )
        is_active = st.checkbox("Active", value=True, key="inv_add_active")

        u1, u2 = st.columns(2, gap="small")
        with u1:
            if st.button("Save Inventory Item", type="primary", use_container_width=True, key="inv_add_save"):
                t = str(name or "").strip()
                if not t:
                    st.error("Item Name is required.")
                    st.stop()
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
                        st.stop()
                    payload["qr_code_value"] = qr_t
                sku_t = str(sku_add or "").strip()
                if sku_t:
                    payload["sku"] = sku_t
                try:
                    row = insert_row_admin(_TABLE, payload)
                except Exception as exc:
                    if "sku" in str(exc).lower():
                        st.error(f"Could not save: {exc} — run migration **`sql/028_inventory_sku_txn_created_by.sql`** if SKU column is missing.")
                    else:
                        st.error(f"Could not save: {exc}")
                    st.stop()
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
                _clear_panel()
                st.success("Inventory item added.")
                st.rerun()
        with u2:
            if st.button("Cancel", use_container_width=True, key="inv_add_cancel"):
                _clear_panel()
                st.rerun()


def _render_edit_panel(row: dict) -> None:
    inject_ips_crud_list_styles()
    rid = str(row.get("id") or "")
    pk = f"inv_ed_{rid}"
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Edit inventory item")
        st.caption(f"ID `{rid[:8]}…`")

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
        qr_cur = str(row.get("qr_code_value") or "").strip()
        qr_in = st.text_input(
            "QR scan code",
            value=qr_cur,
            key=f"{pk}_qr",
            help="Printed / scanned value for **Scan Inventory**.",
        )
        is_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")

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
                nv = _allocate_unique_qr(item_id=str(row.get("id") or ""), preferred=None, exclude_item_id=str(row.get("id") or ""))
                update_rows_admin(_TABLE, {"qr_code_value": nv}, {"id": row["id"]})
                _sync_qr_image_to_storage(str(row.get("id") or ""), nv)
            except Exception as exc:
                st.error(f"Could not update QR: {exc}")
                st.stop()
            st.rerun()

        u1, u2 = st.columns(2, gap="small")
        with u1:
            if st.button("Update Inventory Item", type="primary", use_container_width=True, key=f"{pk}_save"):
                t = str(name or "").strip()
                if not t:
                    st.error("Item Name is required.")
                    st.stop()
                qr_t = str(qr_in or "").strip()
                old_qr = str(row.get("qr_code_value") or "").strip()
                if qr_t and qr_t != old_qr and _qr_value_in_use(value=qr_t, exclude_item_id=str(row.get("id") or "")):
                    st.error("That QR code value is already used by another item.")
                    st.stop()
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
                        st.error(f"Could not update: {exc} — apply **`sql/028_inventory_sku_txn_created_by.sql`** for SKU support.")
                    else:
                        st.error(f"Could not update: {exc}")
                    st.stop()
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
                _clear_panel()
                st.success("Inventory item updated.")
                st.rerun()
        with u2:
            if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
                _clear_panel()
                st.rerun()


def render() -> None:
    render_header("Inventory")
    render_crud_list_subtitle(
        "Stocked supplies and consumables — managed separately from individually tracked assets."
    )
    st.caption(
        "Consumables: issue via **Scan Inventory** (QR / SKU); usage: **Inventory Usage**. "
        "Reusable tools (torque wrenches, meters, etc.) use **Tool Checkout** — they do **not** reduce quantity here."
    )

    can_edit = current_role() == "admin"

    # Ensure required session keys exist (explicitly requested by spec)
    st.session_state.setdefault("inventory_panel_mode", None)
    st.session_state.setdefault("inventory_panel_id", None)

    try:
        rows = fetch_table_admin(_TABLE, limit=5000, order_by="item_name")
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
            st.rerun()

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
            clear_selected_ids(TABLE_KEY_INVENTORY)
            pid = st.session_state.get("inventory_panel_id")
            if pid and str(pid) in {str(x) for x in pending}:
                _clear_panel()
            st.success("Inventory item(s) deleted where permitted.")

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

    # --- Deactivate (matches Materials pattern) ---
    if st.session_state.pop("_inv_do_deactivate", False) and can_edit:
        sel_ids = get_selected_ids(TABLE_KEY_INVENTORY)
        if sel_ids:
            for iid in sel_ids:
                try:
                    update_rows_admin(_TABLE, {"is_active": False}, {"id": iid})
                except Exception as exc:
                    st.error(f"Could not deactivate {iid}: {exc}")
            clear_selected_ids(TABLE_KEY_INVENTORY)
            _clear_panel()
            st.success("Selected inventory items deactivated.")
            st.rerun()

    # --- Panel routing ---
    panel_mode = st.session_state.get("inventory_panel_mode")
    panel_id = st.session_state.get("inventory_panel_id")

    if panel_mode in ("add", "edit", "view") and not can_edit:
        _clear_panel()
        panel_mode = None
        panel_id = None

    panel_row: dict | None = None
    if panel_mode in ("edit", "view") and panel_id:
        pr = fetch_by_match_admin(_TABLE, {"id": panel_id}, limit=1)
        panel_row = pr[0] if pr else None
        if not panel_row:
            _clear_panel()
            panel_mode = None
            panel_id = None

    panel_open = bool(
        (panel_mode == "add" and can_edit)
        or (panel_mode in ("edit", "view") and panel_row is not None)
    )

    # --- Main list (Materials layout) ---
    def _render_main() -> None:
        inject_table_action_styles()

        st.caption("Checkbox column on the **left**; selection is stored as **selected_inventory_ids**.")

        if df.empty:
            st.info("No inventory items found.")
            if can_edit and st.button(
                "Add Inventory Item", type="primary", use_container_width=True, key="inv_empty_add"
            ):
                st.session_state["inventory_panel_mode"] = "add"
                st.session_state["inventory_panel_id"] = None
                st.rerun()
            return

        filter_cols = st.columns([1, 2, 1], gap="small")
        categories = sorted(
            [
                c
                for c in df.get("category", pd.Series(dtype=str))
                .dropna()
                .astype(str)
                .unique()
                .tolist()
                if c.strip()
            ]
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
            filtered = filtered[filtered["category"].astype(str) == selected_category]
        if selected_active == "Active Only" and "is_active" in filtered.columns:
            filtered = filtered[filtered["is_active"] == True]  # noqa: E712
        elif selected_active == "Inactive Only" and "is_active" in filtered.columns:
            filtered = filtered[filtered["is_active"] == False]  # noqa: E712
        if search.strip():
            s = search.strip().lower()
            mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
            filtered = filtered[mask.any(axis=1)]

        qoh_s = pd.to_numeric(filtered.get("quantity_on_hand", 0), errors="coerce").fillna(0)
        if "reorder_point" in filtered.columns:
            rp_s = pd.to_numeric(filtered["reorder_point"], errors="coerce").fillna(0)
        else:
            rp_s = pd.Series(0.0, index=filtered.index)
        low_mask = qoh_s <= rp_s
        n_low = int(low_mask.sum()) if len(filtered) else 0
        if n_low > 0:
            st.warning(f"**Low stock:** {n_low} visible row(s) at or below reorder point.")
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
                    st.dataframe(sub, use_container_width=True, hide_index=True)
                    st.caption("**Suggest qty** = shortfall to reorder point (informational).")

        if filtered.empty:
            st.warning("No inventory items match your filters.")
            if can_edit and st.button(
                "Add Inventory Item", type="primary", use_container_width=True, key="inv_filtered_empty_add"
            ):
                st.session_state["inventory_panel_mode"] = "add"
                st.session_state["inventory_panel_id"] = None
                st.rerun()
            return

        # Display formatting (mirrors Materials-style minimal formatting)
        display_df = filtered.copy()
        if "sku" not in display_df.columns:
            display_df["sku"] = ""
        display_df["stock_alert"] = low_mask.map(lambda ok: "Low Stock" if ok else "")

        show_cols = [
            c
            for c in [
                "item_name",
                "sku",
                "stock_alert",
                "category",
                "unit",
                "quantity_on_hand",
                "reorder_point",
                "unit_cost",
                "vendor",
                "storage_location",
                "is_active",
            ]
            if c in display_df.columns
        ]
        if "unit_cost" in display_df.columns:
            display_df["unit_cost"] = display_df["unit_cost"].apply(_money)

        bar_ph = st.empty()
        _, _sel = render_selectable_dataframe(
            display_df,
            table_key=TABLE_KEY_INVENTORY,
            id_column="id",
            columns=show_cols,
            editor_key="inv_sel_editor",
        )
        with bar_ph.container():
            _render_inventory_action_bar(df_all=df, visible_df=filtered, can_edit=can_edit)

    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            _render_main()
        with side_col:
            if panel_mode == "add":
                _render_add_panel()
            elif panel_mode == "edit" and panel_row:
                _render_edit_panel(panel_row)
            elif panel_mode == "view" and panel_row:
                _render_edit_panel(panel_row)
    else:
        _render_main()
