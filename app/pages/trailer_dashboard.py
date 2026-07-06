"""Mobile Tool Trailer Dashboard — opens when a trailer QR code is scanned."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile
    from app.components.kit_audit_item_ui import clear_audit_item_photos, render_audit_item_fields
    from app.pages._core._data import load_jobs
    from app.services.asset_kits_service import get_asset_kit_items
    from app.services.assets_service import get_asset_image_url, upload_asset_image
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
    from app.services.trailer_dashboard_service import (
        INSPECTION_CHECKLIST,
        REQUEST_PRIORITIES,
        add_tool_to_trailer,
        complete_spot_audit,
        create_trailer_tool_request,
        get_trailer_dashboard_summary,
        get_trailer_history,
        get_trailer_inventory_items,
        list_trailer_photos,
        remove_tool_from_trailer,
        report_broken_trailer_tool,
        save_trailer_inspection,
        select_spot_audit_items,
        transfer_trailer,
        upload_trailer_photo,
    )
    from app.utils.formatting import fmt_date
except ImportError:
    from auth import current_profile  # type: ignore
    from components.kit_audit_item_ui import clear_audit_item_photos, render_audit_item_fields  # type: ignore
    from pages._core._data import load_jobs  # type: ignore
    from services.asset_kits_service import get_asset_kit_items  # type: ignore
    from services.assets_service import get_asset_image_url, upload_asset_image  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore
    from services.trailer_dashboard_service import (  # type: ignore
        INSPECTION_CHECKLIST,
        REQUEST_PRIORITIES,
        add_tool_to_trailer,
        complete_spot_audit,
        create_trailer_tool_request,
        get_trailer_dashboard_summary,
        get_trailer_history,
        get_trailer_inventory_items,
        list_trailer_photos,
        remove_tool_from_trailer,
        report_broken_trailer_tool,
        save_trailer_inspection,
        select_spot_audit_items,
        transfer_trailer,
        upload_trailer_photo,
    )
    from utils.formatting import fmt_date  # type: ignore

_VIEW_KEY = "_trailer_dash_view"
_AUDIT_SAMPLE_KEY = "_trailer_audit_sample"


def _sk(trailer_id: str, suffix: str) -> str:
    return f"trl_{suffix}_{trailer_id}"


def _profile_name() -> str:
    prof = current_profile() or {}
    return str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()


def _profile_phone() -> str:
    prof = current_profile() or {}
    for key in ("phone_number", "phone", "mobile"):
        val = str(prof.get(key) or "").strip()
        if val:
            return val
    return ""


def _profile_user_id() -> str | None:
    uid = str((current_profile() or {}).get("id") or "").strip()
    return uid or None


def _profile_employee_id() -> str | None:
    uid = str((current_profile() or {}).get("employee_id") or "").strip()
    return uid or None


def _set_view(trailer_id: str, view: str) -> None:
    st.session_state[_VIEW_KEY] = view
    if view != "audit":
        st.session_state.pop(_AUDIT_SAMPLE_KEY, None)


def _upload_photo(trailer_id: str, uploaded_file: Any) -> tuple[str, str]:
    if uploaded_file is None:
        return "", ""
    result = upload_asset_image(trailer_id, uploaded_file, uploaded_by=_profile_user_id())
    if not result.ok or not isinstance(result.data, dict):
        return "", ""
    return (
        str(result.data.get("image_path") or result.data.get("photo_path") or ""),
        str(result.data.get("image_url") or result.data.get("photo_url") or ""),
    )


def _job_options() -> tuple[list[str], dict[str, str]]:
    jobs = sort_jobs_by_number_then_name([j for j in load_jobs() if j.get("id")])
    labels = [job_row_select_label(j) for j in jobs]
    mapping = {job_row_select_label(j): str(j.get("id") or "") for j in jobs}
    return labels, mapping


def _render_back(trailer_id: str, label: str = "← Dashboard") -> None:
    if st.button(label, key=_sk(trailer_id, "back_home"), use_container_width=True):
        _set_view(trailer_id, "home")
        st.rerun()


def _render_summary_cards(summary: dict[str, Any]) -> None:
    cards = [
        ("Trailer Status", summary.get("trailer_status")),
        ("Assigned Job", summary.get("assigned_job_label")),
        ("Assigned Supervisor", summary.get("assigned_supervisor")),
        ("Last Audit", summary.get("last_audit")),
        (
            "Inventory Summary",
            f"{summary.get('inventory_present', 0)}/{summary.get('inventory_total', 0)} present"
            + (f" · {summary.get('inventory_missing', 0)} missing" if summary.get("inventory_missing") else ""),
        ),
    ]
    st.markdown('<div class="ips-trailer-dash-cards">', unsafe_allow_html=True)
    for label, value in cards:
        st.markdown(
            f'<div class="ips-trailer-dash-card">'
            f'<div class="ips-trailer-dash-card-label">{html.escape(str(label))}</div>'
            f'<div class="ips-trailer-dash-card-value">{html.escape(str(value or "—"))}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_quick_actions(trailer_id: str) -> None:
    actions = [
        ("Perform Audit", "audit", "primary"),
        ("View Inventory", "inventory", "secondary"),
        ("Request New Tools", "request", "secondary"),
        ("Report Broken Tool", "broken", "secondary"),
        ("Add Tool", "add", "secondary"),
        ("Remove Tool", "remove", "secondary"),
        ("Trailer Inspection", "inspection", "secondary"),
        ("Photos", "photos", "secondary"),
        ("History", "history", "secondary"),
        ("Transfer Trailer", "transfer", "secondary"),
    ]
    st.markdown("#### Quick Actions")
    for i in range(0, len(actions), 2):
        c1, c2 = st.columns(2, gap="small")
        for col, (label, view, kind) in zip((c1, c2), actions[i : i + 2]):
            with col:
                btn_type = "primary" if kind == "primary" else "secondary"
                if st.button(label, key=_sk(trailer_id, f"qa_{view}"), type=btn_type, use_container_width=True):
                    if view == "audit":
                        st.session_state[_AUDIT_SAMPLE_KEY] = select_spot_audit_items(trailer_id)
                    _set_view(trailer_id, view)
                    st.rerun()


def _render_home(asset: dict[str, Any], summary: dict[str, Any]) -> None:
    trailer_id = str(asset.get("id") or "")
    image_url = get_asset_image_url(asset)
    if image_url:
        st.markdown(
            f'<img class="ips-trailer-dash-hero" src="{html.escape(image_url, quote=True)}" alt="Trailer" />',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="ips-trailer-dash-title">{html.escape(str(summary.get("trailer_name") or "Tool Trailer"))}</div>'
        f'<div class="ips-trailer-dash-sub">{html.escape(str(summary.get("trailer_number") or ""))}</div>',
        unsafe_allow_html=True,
    )
    _render_summary_cards(summary)
    _render_quick_actions(trailer_id)


def _render_inventory(trailer_id: str) -> None:
    _render_back(trailer_id)
    st.markdown("### Inventory")
    items = get_trailer_inventory_items(trailer_id)
    if not items:
        st.info("No tools assigned to this trailer yet.")
        return
    for it in items:
        serial = str(it.get("serial_number") or "").strip()
        sn = f" · S/N {html.escape(serial)}" if serial else ""
        st.markdown(
            f'<div class="ips-trailer-inv-row">'
            f'<strong>{html.escape(str(it.get("item_name") or "—"))}</strong>{sn}<br/>'
            f'<span class="ips-trailer-muted">Qty {it.get("quantity_actual")}/{it.get("quantity_expected")} · '
            f'{html.escape(str(it.get("condition") or "—"))} · {html.escape(str(it.get("status") or "—"))}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_audit(asset: dict[str, Any]) -> None:
    trailer_id = str(asset.get("id") or "")
    _render_back(trailer_id)
    st.markdown("### Perform Audit")
    st.caption(
        "Randomly selected tools — set status and condition for each item, attach photo proof, "
        "then complete the audit. Missing items require a note instead of a photo."
    )

    sample: list[dict[str, Any]] = st.session_state.get(_AUDIT_SAMPLE_KEY) or []
    if not sample:
        sample = select_spot_audit_items(trailer_id)
        st.session_state[_AUDIT_SAMPLE_KEY] = sample

    if not sample:
        st.warning("No inventory items on this trailer to audit.")
        return

    summary = get_trailer_dashboard_summary(trailer_id, asset)
    prof_name = _profile_name()
    prof_phone = _profile_phone()
    user_id = _profile_user_id()

    supervisor = st.text_input(
        "Supervisor",
        value=prof_name or summary.get("assigned_supervisor") or "",
        key=_sk(trailer_id, "audit_supervisor"),
    )
    phone = st.text_input("Phone", value=prof_phone, key=_sk(trailer_id, "audit_phone"))
    audit_notes = st.text_area("Audit notes (optional)", height=60, key=_sk(trailer_id, "audit_notes"))

    st.divider()
    audit_lines: list[dict[str, Any]] = []
    for idx, it in enumerate(sample):
        st.markdown(f"#### Item {idx + 1}")
        line = render_audit_item_fields(
            it,
            trailer_id=trailer_id,
            key_prefix=_sk(trailer_id, "audit"),
            uploaded_by=user_id,
            show_quantity=True,
        )
        audit_lines.append(line)
        st.divider()

    if st.button("Complete Audit", type="primary", key=_sk(trailer_id, "audit_submit"), use_container_width=True):
        if not str(supervisor or "").strip():
            st.error("Supervisor name is required.")
            return

        result = complete_spot_audit(
            trailer_id,
            {
                "performed_by_name": supervisor,
                "performed_by_phone": phone,
                "performed_by_user_id": user_id,
                "performed_by_employee_id": _profile_employee_id(),
                "assigned_supervisor_name": supervisor,
                "job_id": asset.get("assigned_job_id"),
                "notes": audit_notes,
            },
            audit_lines,
        )
        if result.ok:
            clear_audit_item_photos(trailer_id, [str(i.get("id") or "") for i in sample])
            st.success("Audit saved.")
            _set_view(trailer_id, "home")
            st.rerun()
        else:
            st.error(result.error or "Could not save audit.")


def _render_request(trailer_id: str, asset: dict[str, Any]) -> None:
    _render_back(trailer_id)
    st.markdown("### Request New Tools")
    items = get_trailer_inventory_items(trailer_id)
    tool_names = [str(i.get("item_name") or "") for i in items if i.get("item_name")]
    custom = "— Other (type below) —"
    prof_name = _profile_name()

    with st.form(_sk(trailer_id, "request_form")):
        pick = st.selectbox("Tool", [custom, *tool_names] if tool_names else [custom])
        custom_name = st.text_input("Tool name (if other)")
        qty = st.number_input("Quantity", min_value=1.0, value=1.0, step=1.0)
        priority = st.selectbox("Priority", REQUEST_PRIORITIES, index=1)
        reason = st.text_area("Reason", height=80)
        submit = st.form_submit_button("Submit Request", type="primary", use_container_width=True)

    if not submit:
        return
    tool = custom_name.strip() if pick == custom else pick
    if not tool:
        st.error("Tool name is required.")
        return
    if not str(reason or "").strip():
        st.error("Reason is required.")
        return

    kit_item = next((i for i in items if str(i.get("item_name") or "") == tool), None)
    result = create_trailer_tool_request(
        trailer_id,
        {
            "tool_name": tool,
            "kit_item_id": kit_item.get("id") if kit_item else None,
            "quantity": qty,
            "priority": priority,
            "reason": reason,
            "job_id": asset.get("assigned_job_id"),
            "requested_by_name": prof_name or "Supervisor",
            "requested_by_phone": _profile_phone(),
            "requested_by_user_id": _profile_user_id(),
            "requested_by_employee_id": _profile_employee_id(),
        },
    )
    if result.ok:
        st.success("Tool request submitted.")
        _set_view(trailer_id, "home")
        st.rerun()
    else:
        st.error(result.error or "Could not submit request.")


def _render_broken(trailer_id: str) -> None:
    _render_back(trailer_id)
    st.markdown("### Report Broken Tool")
    items = get_trailer_inventory_items(trailer_id)
    if not items:
        st.warning("No tools on this trailer.")
        return
    labels = [str(i.get("item_name") or "Tool") for i in items]
    prof_name = _profile_name()

    with st.form(_sk(trailer_id, "broken_form")):
        pick_idx = st.selectbox("Tool", range(len(labels)), format_func=lambda i: labels[i])
        problem = st.text_input("Problem")
        notes = st.text_area("Notes", height=70)
        photo = st.file_uploader("Required photo", type=["png", "jpg", "jpeg", "webp"])
        submit = st.form_submit_button("Submit Report", type="primary", use_container_width=True)

    if not submit:
        return
    item = items[pick_idx]
    if not str(problem or "").strip():
        st.error("Problem description is required.")
        return
    photo_path, photo_url = _upload_photo(trailer_id, photo)
    if not photo_path and not photo_url:
        st.error("Photo is required.")
        return

    result = report_broken_trailer_tool(
        trailer_id,
        {
            "tool_name": item.get("item_name"),
            "kit_item_id": item.get("id"),
            "child_asset_id": item.get("child_asset_id"),
            "problem": problem,
            "notes": notes,
            "photo_path": photo_path,
            "photo_url": photo_url,
            "reported_by_name": prof_name or "Supervisor",
            "reported_by_phone": _profile_phone(),
            "reported_by_user_id": _profile_user_id(),
            "reported_by_employee_id": _profile_employee_id(),
        },
    )
    if result.ok:
        st.success("Broken tool reported. Maintenance request created.")
        _set_view(trailer_id, "home")
        st.rerun()
    else:
        st.error(result.error or "Could not submit report.")


def _render_add_tool(trailer_id: str) -> None:
    _render_back(trailer_id)
    st.markdown("### Add Tool")
    with st.form(_sk(trailer_id, "add_form")):
        name = st.text_input("Tool name")
        qty = st.number_input("Quantity", min_value=1.0, value=1.0)
        serial = st.text_input("Serial number (optional)")
        notes = st.text_input("Notes (optional)")
        submit = st.form_submit_button("Add Tool", type="primary", use_container_width=True)
    if submit:
        if not str(name or "").strip():
            st.error("Tool name is required.")
            return
        result = add_tool_to_trailer(
            trailer_id,
            {
                "tool_name": name,
                "quantity": qty,
                "serial_number": serial,
                "notes": notes,
                "performed_by_name": _profile_name(),
            },
        )
        if result.ok:
            st.success("Tool added.")
            _set_view(trailer_id, "inventory")
            st.rerun()
        else:
            st.error(result.error or "Could not add tool.")


def _render_remove_tool(trailer_id: str) -> None:
    _render_back(trailer_id)
    st.markdown("### Remove Tool")
    items = get_asset_kit_items(trailer_id)
    if not items:
        st.info("No tools to remove.")
        return
    labels = [str(i.get("item_name") or "Tool") for i in items]
    pick_idx = st.selectbox("Tool to remove", range(len(labels)), format_func=lambda i: labels[i])
    notes = st.text_input("Reason / notes")
    if st.button("Remove Tool", type="primary", key=_sk(trailer_id, "remove_btn"), use_container_width=True):
        result = remove_tool_from_trailer(
            trailer_id,
            str(items[pick_idx].get("id") or ""),
            performed_by_name=_profile_name(),
            notes=notes,
        )
        if result.ok:
            st.success("Tool removed.")
            _set_view(trailer_id, "inventory")
            st.rerun()
        else:
            st.error(result.error or "Could not remove tool.")


def _render_inspection(trailer_id: str, asset: dict[str, Any]) -> None:
    _render_back(trailer_id)
    st.markdown("### Trailer Inspection")
    prof_name = _profile_name()
    with st.form(_sk(trailer_id, "insp_form")):
        st.caption("Check each item; photo required to submit.")
        checks: dict[str, bool] = {}
        for field, label in INSPECTION_CHECKLIST:
            checks[field] = st.checkbox(label, value=False)
        photo = st.file_uploader("Required photo", type=["png", "jpg", "jpeg", "webp"])
        notes = st.text_area("Notes", height=60)
        submit = st.form_submit_button("Save Inspection", type="primary", use_container_width=True)

    if not submit:
        return
    photo_path, photo_url = _upload_photo(trailer_id, photo)
    if not photo_path and not photo_url:
        st.error("Photo is required.")
        return

    payload = {
        **checks,
        "photo_path": photo_path,
        "photo_url": photo_url,
        "notes": notes,
        "job_id": asset.get("assigned_job_id"),
        "performed_by_name": prof_name or "Supervisor",
        "performed_by_phone": _profile_phone(),
        "performed_by_user_id": _profile_user_id(),
        "performed_by_employee_id": _profile_employee_id(),
    }
    result = save_trailer_inspection(trailer_id, payload)
    if result.ok:
        st.success("Inspection saved.")
        _set_view(trailer_id, "home")
        st.rerun()
    else:
        st.error(result.error or "Could not save inspection.")


def _render_photos(trailer_id: str) -> None:
    _render_back(trailer_id)
    st.markdown("### Photos")
    caption = st.text_input("Caption (optional)", key=_sk(trailer_id, "photo_cap"))
    upload = st.file_uploader("Upload photo", type=["png", "jpg", "jpeg", "webp"], key=_sk(trailer_id, "photo_up"))
    if st.button("Upload", key=_sk(trailer_id, "photo_btn"), use_container_width=True):
        if upload is None:
            st.error("Select a photo first.")
        else:
            result = upload_trailer_photo(
                trailer_id,
                upload,
                uploaded_by=_profile_user_id(),
                caption=caption,
            )
            if result.ok:
                st.success("Photo uploaded.")
                st.rerun()
            else:
                st.error(result.error or "Upload failed.")

    photos = list_trailer_photos(trailer_id)
    if not photos:
        st.caption("No photos yet.")
        return
    for row in photos:
        url = str(row.get("photo_url") or "").strip()
        when = fmt_date(row.get("created_at"))
        cap = str(row.get("caption") or "").strip()
        if url:
            st.markdown(f"**{html.escape(when)}** — {html.escape(cap or 'Trailer photo')}", unsafe_allow_html=True)
            st.markdown(
                f'<img class="ips-trailer-dash-hero" src="{html.escape(url, quote=True)}" alt="Trailer photo" />',
                unsafe_allow_html=True,
            )


def _render_history(trailer_id: str) -> None:
    _render_back(trailer_id)
    st.markdown("### History")
    events = get_trailer_history(trailer_id)
    if not events:
        st.caption("No activity recorded yet.")
        return
    for ev in events:
        kind = html.escape(str(ev.get("kind") or "Event"))
        when = html.escape(fmt_date(ev.get("when")))
        title = html.escape(str(ev.get("title") or ""))
        detail = html.escape(str(ev.get("detail") or ""))
        detail_html = f'<br/><span class="ips-trailer-muted">{detail}</span>' if detail else ""
        st.markdown(
            f'<div class="ips-trailer-history-row">'
            f'<span class="ips-trailer-history-kind">{kind}</span> '
            f'<span class="ips-trailer-muted">{when}</span><br/>'
            f"<strong>{title}</strong>{detail_html}"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_transfer(trailer_id: str) -> None:
    _render_back(trailer_id)
    st.markdown("### Transfer Trailer")
    job_labels, job_map = _job_options()
    supervisor = st.text_input("Assigned supervisor", value=_profile_name())
    phone = st.text_input("Supervisor phone", value=_profile_phone())
    job_pick = st.selectbox("Assigned job", ["— None —", *job_labels])
    notes = st.text_area("Transfer notes", height=60)
    if st.button("Save Transfer", type="primary", key=_sk(trailer_id, "transfer_btn"), use_container_width=True):
        jid = job_map.get(job_pick) if job_pick != "— None —" else ""
        result = transfer_trailer(
            trailer_id,
            {
                "assigned_to_name": supervisor,
                "supervisor_name": supervisor,
                "assigned_to_phone": phone,
                "job_id": jid or None,
                "notes": notes,
                "performed_by_name": _profile_name(),
                "performed_by_phone": phone,
            },
        )
        if result.ok:
            st.success("Trailer assignment updated.")
            _set_view(trailer_id, "home")
            st.rerun()
        else:
            st.error(result.error or "Could not transfer trailer.")


def render_trailer_dashboard(asset: dict[str, Any]) -> None:
    """Render the field-optimized tool trailer dashboard for a scanned kit/trailer asset."""
    try:
        from app.styles import inject_trailer_dashboard_css
    except ImportError:
        from styles import inject_trailer_dashboard_css  # type: ignore

    inject_trailer_dashboard_css()
    st.markdown('<span class="ips-trailer-dash-scope" aria-hidden="true"></span>', unsafe_allow_html=True)

    trailer_id = str(asset.get("id") or "").strip()
    if not trailer_id:
        st.error("Invalid trailer.")
        return

    if st.session_state.get(_VIEW_KEY) is None:
        st.session_state[_VIEW_KEY] = "home"

    view = str(st.session_state.get(_VIEW_KEY) or "home")
    summary = get_trailer_dashboard_summary(trailer_id, asset)

    st.markdown("## Tool Trailer Dashboard")

    if view == "home":
        _render_home(asset, summary)
    elif view == "inventory":
        _render_inventory(trailer_id)
    elif view == "audit":
        _render_audit(asset)
    elif view == "request":
        _render_request(trailer_id, asset)
    elif view == "broken":
        _render_broken(trailer_id)
    elif view == "add":
        _render_add_tool(trailer_id)
    elif view == "remove":
        _render_remove_tool(trailer_id)
    elif view == "inspection":
        _render_inspection(trailer_id, asset)
    elif view == "photos":
        _render_photos(trailer_id)
    elif view == "history":
        _render_history(trailer_id)
    elif view == "transfer":
        _render_transfer(trailer_id)
    else:
        _render_home(asset, summary)
