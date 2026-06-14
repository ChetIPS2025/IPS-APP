"""Job Details — Materials / Inventory Used section."""

from __future__ import annotations

import html
from datetime import date, datetime, time, timezone
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile, current_role, is_authenticated
    from app.pages._core._data import load_employees, load_inventory
    from app.services.inventory_service import get_inventory_transactions, list_inventory
    from app.services.job_materials_service import (
        add_manual_job_material,
        add_pricing_guide_job_material,
        fetch_job_materials,
        issue_inventory_to_job,
        job_material_line_total,
        job_materials_total,
        list_pricing_guide_job_options,
        resolve_inventory_by_scan_code,
    )
    from app.services.tasks_service import get_tasks_by_job
    from app.ui import IPS_NAV_PENDING_KEY
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from auth import current_profile, current_role, is_authenticated  # type: ignore
    from pages._core._data import load_employees, load_inventory  # type: ignore
    from services.inventory_service import get_inventory_transactions, list_inventory  # type: ignore
    from services.job_materials_service import (  # type: ignore
        add_manual_job_material,
        add_pricing_guide_job_material,
        fetch_job_materials,
        issue_inventory_to_job,
        job_material_line_total,
        job_materials_total,
        list_pricing_guide_job_options,
        resolve_inventory_by_scan_code,
    )
    from services.tasks_service import get_tasks_by_job  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_USAGE_SOURCE_LABELS = {
    "pricing_guide": "Pricing Guide",
    "qr_scan": "Scan / lookup",
    "manual_inventory": "Inventory",
    "manual_entry": "Manual entry",
}

def _txn_action_label(txn_type: str) -> str:
    try:
        from app.services.inventory_service import inventory_action_label
    except ImportError:
        from services.inventory_service import inventory_action_label  # type: ignore
    return inventory_action_label(txn_type)


def _profile_employee_id() -> str | None:
    prof = current_profile() or {}
    em = str(prof.get("email") or "").strip().lower()
    if not em:
        return None
    try:
        from app.db import fetch_table_admin
    except ImportError:
        from db import fetch_table_admin  # type: ignore
    try:
        rows = fetch_table_admin("employees", columns="id,email", limit=5000)
    except Exception:
        return None
    for row in rows:
        if str(row.get("email") or "").strip().lower() == em:
            return str(row.get("id") or "") or None
    return None


def _profile_display_name() -> str:
    prof = current_profile() or {}
    return str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()


def _subjob_options(job_id: str) -> tuple[list[str], dict[str, str]]:
    tasks = get_tasks_by_job(job_id, include_closed=True) or []
    labels: list[str] = ["— No subjob —"]
    label_to_id: dict[str, str] = {}
    for task in tasks:
        title = str(task.get("title") or task.get("task_name") or "Subjob").strip()
        tid = str(task.get("id") or "").strip()
        if not tid:
            continue
        label = title
        n = 2
        while label in label_to_id and label_to_id[label] != tid:
            label = f"{title} ({n})"
            n += 1
        labels.append(label)
        label_to_id[label] = tid
    return labels, label_to_id


def _employee_select_options() -> tuple[list[str], dict[str, str]]:
    labels: list[str] = ["— Select employee —"]
    label_to_id: dict[str, str] = {"— Select employee —": ""}
    for emp in load_employees() or []:
        lbl = str(emp.get("name") or "").strip()
        eid_s = str(emp.get("id") or "").strip()
        if not lbl or not eid_s:
            continue
        unique = lbl
        n = 2
        while unique in label_to_id and label_to_id[unique] != eid_s:
            unique = f"{lbl} ({n})"
            n += 1
        labels.append(unique)
        label_to_id[unique] = eid_s
    return labels, label_to_id


def _combine_used_at(use_date: date, use_time: time) -> datetime:
    return datetime.combine(use_date, use_time, tzinfo=timezone.utc)


def _pricing_guide_search_options(
    *,
    search: str = "",
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    rows = list_pricing_guide_job_options()
    query = str(search or "").strip().casefold()
    if query:
        filtered: list[dict[str, Any]] = []
        for row in rows:
            hay = " ".join(
                str(row.get(key) or "")
                for key in (
                    "description",
                    "item_number",
                    "sku",
                    "item_code",
                    "category",
                    "vendor",
                    "vendor_name",
                )
            ).casefold()
            if query in hay:
                filtered.append(row)
        rows = filtered
    labels: list[str] = ["— Select item —"]
    label_to_item: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_no = str(row.get("item_number") or row.get("sku") or row.get("item_code") or "—")
        desc = str(row.get("description") or "—")
        unit = str(row.get("unit") or "EA")
        cost = float(row.get("default_cost") or row.get("live_unit_cost") or 0)
        label = f"{item_no} · {desc} ({fmt_currency(cost)}/{unit})"
        n = 2
        while label in label_to_item:
            label = f"{item_no} · {desc} ({n})"
            n += 1
        labels.append(label)
        label_to_item[label] = row
    return labels, label_to_item


def _inventory_search_options(job_id: str) -> tuple[list[str], dict[str, dict[str, Any]]]:
    rows, _ = list_inventory(demo=[])
    inactive_statuses = {"discontinued", "inactive", "deleted"}
    active = [r for r in rows if str(r.get("status") or "").casefold() not in inactive_statuses]
    active.sort(key=lambda r: str(r.get("name") or r.get("item_name") or "").casefold())
    labels: list[str] = ["— Select item —"]
    label_to_item: dict[str, dict[str, Any]] = {}
    for row in active:
        sku = str(row.get("sku") or "—")
        name = str(row.get("name") or row.get("item_name") or "—")
        qoh = int(row.get("qty_on_hand") or row.get("quantity_on_hand") or 0)
        label = f"{sku} · {name} (on hand: {qoh})"
        n = 2
        while label in label_to_item:
            label = f"{sku} · {name} ({n})"
            n += 1
        labels.append(label)
        label_to_item[label] = row
    return labels, label_to_item


def _render_materials_summary(job_id: str, materials: list[dict[str, Any]]) -> None:
    total = job_materials_total(materials)
    pg_linked = sum(
        1
        for m in materials
        if m.get("pricing_guide_id") or str(m.get("usage_source") or "") == "pricing_guide"
    )
    inv_linked = sum(1 for m in materials if m.get("inventory_item_id"))
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.metric("Material cost", fmt_currency(total))
    with c2:
        st.metric("Usage lines", len(materials))
    with c3:
        st.metric("Pricing Guide", pg_linked)
    with c4:
        st.metric("From inventory", inv_linked)


def _material_row_thumbnail_html(
    row: dict[str, Any],
    *,
    inv_by_id: dict[str, dict[str, Any]],
    pg_by_id: dict[str, dict[str, Any]],
) -> str:
    try:
        from app.services.catalog_images import catalog_thumbnail_html
    except ImportError:
        from services.catalog_images import catalog_thumbnail_html  # type: ignore

    thumb_class = "ips-inventory-thumb-img ips-job-mat-thumb"
    cell_class = "ips-inventory-thumb-cell"
    iid = str(row.get("inventory_item_id") or "").strip()
    if iid and iid in inv_by_id:
        return catalog_thumbnail_html(
            inv_by_id[iid],
            kind="inventory",
            css_class=thumb_class,
            cell_class=cell_class,
            alt="Material image",
        )
    pid = str(row.get("pricing_guide_id") or "").strip()
    if pid and pid in pg_by_id:
        return catalog_thumbnail_html(
            pg_by_id[pid],
            kind="pricing_guide",
            css_class=thumb_class,
            cell_class=cell_class,
            alt="Material image",
        )
    return catalog_thumbnail_html({}, kind="inventory", css_class=thumb_class, cell_class=cell_class)


def _render_materials_table(
    materials: list[dict[str, Any]],
    *,
    subjob_labels: dict[str, str],
    employee_labels: dict[str, str],
) -> None:
    if not materials:
        st.caption("No materials recorded for this job yet.")
        return

    inv_by_id = {str(r.get("id") or ""): r for r in load_inventory() if str(r.get("id") or "")}
    pg_by_id = {str(r.get("id") or ""): r for r in list_pricing_guide_job_options(include_inactive=True) if str(r.get("id") or "")}

    head = (
        '<div class="ips-inventory-txn-head ips-job-materials-head">'
        "<span></span><span>Date</span><span>Material</span><span>Qty</span><span>Unit cost</span>"
        "<span>Total</span><span>Subjob</span><span>Employee</span><span>Source</span><span>Notes</span>"
        "</div>"
    )
    rows_html = ""
    for row in materials:
        used = row.get("used_at") or row.get("created_at")
        sub_id = str(row.get("subjob_id") or "")
        emp_id = str(row.get("employee_id") or "")
        src = _USAGE_SOURCE_LABELS.get(str(row.get("usage_source") or ""), str(row.get("usage_source") or "—"))
        thumb = _material_row_thumbnail_html(row, inv_by_id=inv_by_id, pg_by_id=pg_by_id)
        rows_html += (
            '<div class="ips-inventory-txn-row ips-job-materials-row">'
            f"<span>{thumb}</span>"
            f"<span>{html.escape(fmt_date(used))}</span>"
            f'<span>{html.escape(str(row.get("item_name") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("quantity") or ""))}</span>'
            f'<span>{html.escape(fmt_currency(row.get("unit_cost")))}</span>'
            f'<span>{html.escape(fmt_currency(job_material_line_total(row)))}</span>'
            f'<span>{html.escape(subjob_labels.get(sub_id, "—"))}</span>'
            f'<span>{html.escape(employee_labels.get(emp_id, "—"))}</span>'
            f"<span>{html.escape(src)}</span>"
            f'<span>{html.escape(str(row.get("notes") or ""))}</span>'
            "</div>"
        )
    st.markdown(f'<div class="ips-inventory-txn-table ips-job-materials-table">{head}{rows_html}</div>', unsafe_allow_html=True)


def _render_scan_activity(job_id: str) -> None:
    txns = get_inventory_transactions(job_id=job_id, limit=200)
    st.markdown("#### Scan activity")
    if not txns:
        st.caption("No inventory scan transactions linked to this job yet.")
        return
    head = (
        '<div class="ips-inventory-txn-head">'
        "<span>Date</span><span>Item</span><span>SKU</span><span>Action</span>"
        "<span>Qty</span><span>Unit</span><span>Scanned By</span><span>Notes</span>"
        "</div>"
    )
    rows_html = ""
    for row in txns:
        txn_type = str(row.get("transaction_type") or row.get("txn_type") or "")
        rows_html += (
            '<div class="ips-inventory-txn-row ips-job-inventory-txn-row">'
            f'<span>{html.escape(fmt_date(row.get("created_at")))}</span>'
            f'<span>{html.escape(str(row.get("item_name") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("sku") or "—"))}</span>'
            f'<span>{html.escape(_txn_action_label(txn_type))}</span>'
            f'<span>{html.escape(str(row.get("quantity_display") or ""))}</span>'
            f'<span>{html.escape(str(row.get("unit") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("scanned_by_name") or row.get("created_by") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("notes") or ""))}</span>'
            "</div>"
        )
    st.markdown(f'<div class="ips-inventory-txn-table">{head}{rows_html}</div>', unsafe_allow_html=True)


def _render_add_materials_form(job: dict, *, key_prefix: str) -> None:
    jid = str(job.get("id") or "").strip()
    if not jid:
        st.info("Save this job before recording materials.")
        return

    subjob_labels, subjob_map = _subjob_options(jid)
    emp_labels, emp_map = _employee_select_options()
    inv_labels, inv_map = _inventory_search_options(jid)
    default_emp = _profile_employee_id()
    default_emp_label = next((lbl for lbl, eid in emp_map.items() if eid == default_emp), "— Select employee —")

    st.markdown("#### Add material")
    meta1, meta2 = st.columns(2, gap="small")
    with meta1:
        common_used_date = st.date_input("Date used", value=date.today(), key=f"{key_prefix}_used_date")
        subjob_pick = st.selectbox("Subjob / task (optional)", subjob_labels, key=f"{key_prefix}_subjob")
    with meta2:
        common_used_time = st.time_input(
            "Time used",
            value=datetime.now().time().replace(second=0, microsecond=0),
            key=f"{key_prefix}_used_time",
        )
        emp_pick = st.selectbox(
            "Employee",
            emp_labels,
            index=emp_labels.index(default_emp_label) if default_emp_label in emp_labels else 0,
            key=f"{key_prefix}_employee",
        )
    used_at = _combine_used_at(common_used_date, common_used_time)
    subjob_id = subjob_map.get(subjob_pick) or None
    employee_id = emp_map.get(emp_pick) or default_emp or None
    common_notes = st.text_area("Notes", key=f"{key_prefix}_notes", height=68, placeholder="Optional")

    tab_pg, tab_inventory, tab_manual, tab_scan = st.tabs(
        ["Pricing Guide", "Inventory", "Manual Entry", "Scan / Lookup"]
    )

    allow_over = str(current_role() or "").lower() == "admin"

    with tab_pg:
        st.caption(
            "Add a priced catalog line to job costing. "
            "This does not reduce inventory — use **Inventory** or **Scan / Lookup** to pull stock."
        )
        pg_search = st.text_input(
            "Search Pricing Guide",
            key=f"{key_prefix}_pg_search",
            placeholder="Description, item #, SKU, category, vendor…",
        )
        pg_labels, pg_map = _pricing_guide_search_options(search=pg_search)
        with st.form(f"{key_prefix}_pg_form", clear_on_submit=False):
            item_pick = st.selectbox("Pricing Guide item", pg_labels, key=f"{key_prefix}_pg_pick")
            qty = st.number_input(
                "Quantity",
                min_value=0.0,
                value=1.0,
                step=0.25,
                format="%.4f",
                key=f"{key_prefix}_pg_qty",
            )
            submit_pg = st.form_submit_button("Add from Pricing Guide", type="primary", use_container_width=True)

        if submit_pg:
            item = pg_map.get(item_pick)
            if not item:
                st.error("Select a Pricing Guide item.")
            else:
                pid = str(item.get("id") or "").strip()
                qv = float(qty or 0)
                if qv <= 0:
                    st.error("Quantity must be greater than zero.")
                else:
                    result = add_pricing_guide_job_material(
                        job_id=jid,
                        pricing_guide_item_id=pid,
                        quantity=qv,
                        notes=common_notes,
                        subjob_id=subjob_id,
                        employee_id=employee_id,
                        used_at=used_at,
                    )
                    if result.ok:
                        st.success("Pricing Guide line added to job costing.")
                        st.rerun()
                    else:
                        st.error(result.error or "Could not add material.")

    with tab_inventory:
        st.caption("Consumable inventory — on-hand quantity decreases when material is consumed on this job.")
        with st.form(f"{key_prefix}_inv_form", clear_on_submit=False):
            item_pick = st.selectbox("Inventory item", inv_labels, key=f"{key_prefix}_inv_pick")
            qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=0.25, format="%.4f", key=f"{key_prefix}_inv_qty")
            if allow_over:
                st.checkbox("Allow quantity over on-hand (admin)", key=f"{key_prefix}_inv_over")
            submit_inv = st.form_submit_button("Add from inventory", type="primary", use_container_width=True)

        if submit_inv:
            item = inv_map.get(item_pick)
            if not item:
                st.error("Select an inventory item.")
            else:
                iid = str(item.get("id") or "").strip()
                qv = float(qty or 0)
                if qv <= 0:
                    st.error("Quantity must be greater than zero.")
                else:
                    result = issue_inventory_to_job(
                        job_id=jid,
                        inventory_item_id=iid,
                        quantity=qv,
                        transaction_type="consume_on_job",
                        notes=common_notes,
                        subjob_id=subjob_id,
                        employee_id=employee_id,
                        used_at=used_at,
                        usage_source="manual_inventory",
                        allow_overdraw=bool(st.session_state.get(f"{key_prefix}_inv_over")),
                        scanned_by_name=_profile_display_name() or None,
                        scanned_by_employee_id=employee_id,
                        source="job_materials_inventory",
                    )
                    if result.ok:
                        st.success("Material consumed — job costing updated.")
                        st.rerun()
                    else:
                        st.error(result.error or "Could not add material.")

    with tab_manual:
        st.caption("One-off material not in Pricing Guide or Inventory (field purchase, misc.).")
        with st.form(f"{key_prefix}_manual_form", clear_on_submit=True):
            name = st.text_input("Material name", key=f"{key_prefix}_manual_name")
            qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=0.25, format="%.4f", key=f"{key_prefix}_manual_qty")
            unit_cost = st.number_input("Unit cost", min_value=0.0, value=0.0, step=0.01, key=f"{key_prefix}_manual_cost")
            submit_manual = st.form_submit_button("Add manual line", type="primary", use_container_width=True)

        if submit_manual:
            result = add_manual_job_material(
                job_id=jid,
                item_name=name,
                quantity=float(qty or 0),
                unit_cost=float(unit_cost or 0),
                notes=common_notes,
                subjob_id=subjob_id,
                employee_id=employee_id,
                used_at=used_at,
                usage_source="manual_entry",
            )
            if result.ok:
                st.success("Manual material line added to job costing.")
                st.rerun()
            else:
                st.error(result.error or "Could not add material.")

    with tab_scan:
        st.caption("Scan a QR code with your device, or paste SKU / scan link below.")
        with st.form(f"{key_prefix}_scan_form", clear_on_submit=False):
            code = st.text_input(
                "Item code or QR link",
                key=f"{key_prefix}_scan_code",
                placeholder="SKU, INV-…, or scan URL",
            )
            qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=0.25, format="%.4f", key=f"{key_prefix}_scan_qty")
            if allow_over:
                st.checkbox("Allow quantity over on-hand (admin)", key=f"{key_prefix}_scan_over")
            submit_scan = st.form_submit_button("Add from scan", type="primary", use_container_width=True)

        if submit_scan:
            resolved = resolve_inventory_by_scan_code(code)
            if not resolved.ok or not resolved.data:
                st.error(resolved.error or "Could not resolve inventory item.")
            else:
                item = resolved.data
                iid = str(item.get("id") or "").strip()
                qv = float(qty or 0)
                if qv <= 0:
                    st.error("Quantity must be greater than zero.")
                else:
                    result = issue_inventory_to_job(
                        job_id=jid,
                        inventory_item_id=iid,
                        quantity=qv,
                        transaction_type="consume_on_job",
                        notes=common_notes,
                        subjob_id=subjob_id,
                        employee_id=employee_id,
                        used_at=used_at,
                        usage_source="qr_scan",
                        allow_overdraw=bool(st.session_state.get(f"{key_prefix}_scan_over")),
                        scanned_by_user_id=str((current_profile() or {}).get("id") or "") or None,
                        scanned_by_name=_profile_display_name() or None,
                        scanned_by_employee_id=employee_id,
                        source="job_materials_scan",
                    )
                    if result.ok:
                        st.success(f"Added {qv} × {item.get('name') or item.get('item_name')} to job materials.")
                        st.rerun()
                    else:
                        st.error(result.error or "Could not add material.")


def render_job_materials_tab(job: dict, *, key_prefix: str = "job_mat") -> None:
    """Materials / Inventory Used — costing lines, add workflow, and scan audit."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        st.caption("Save this job before recording materials.")
        return

    materials = fetch_job_materials(jid)
    subjob_labels_list, subjob_map = _subjob_options(jid)
    subjob_id_to_label = {v: k for k, v in subjob_map.items()}
    emp_labels_list, emp_map = _employee_select_options()
    emp_id_to_label = {v: k for k, v in emp_map.items() if v}

    _render_materials_summary(jid, materials)

    bc1, bc2 = st.columns([1, 1], gap="small")
    with bc2:
        if st.button("Open Job Costing", key=f"{key_prefix}_open_jc", use_container_width=True):
            st.session_state["jc_focus_job_id"] = jid
            try:
                from app.navigation import queue_pending_nav
            except ImportError:
                from navigation import queue_pending_nav  # type: ignore
            queue_pending_nav("Job Costing")
            st.rerun()

    st.markdown("#### Materials used")
    _render_materials_table(
        materials,
        subjob_labels=subjob_id_to_label,
        employee_labels=emp_id_to_label,
    )

    _render_add_materials_form(job, key_prefix=key_prefix)

    with st.expander("Inventory scan history", expanded=False):
        _render_scan_activity(jid)
