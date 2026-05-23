"""Mobile-friendly inventory QR scan action page."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile, current_role, is_authenticated
    from app.mobile_ui import ensure_narrow_viewport_detected
    from app.services.inventory_service import (
        INVENTORY_TXN_TYPES,
        generate_inventory_qr_value,
        get_inventory_item_by_qr,
        record_inventory_transaction,
    )
    from app.services.job_service import build_job_dropdown_label_maps, sort_jobs_by_number_then_name
    from app.services.repository import fetch_rows
    from app.styles import inject_inventory_qr_scan_css
    from app.utils.formatting import fmt_currency
    from app.utils.phone_helpers import format_phone_display, is_valid_phone, normalize_phone
except ImportError:
    from auth import current_profile, current_role, is_authenticated  # type: ignore
    from mobile_ui import ensure_narrow_viewport_detected  # type: ignore
    from services.inventory_service import (  # type: ignore
        INVENTORY_TXN_TYPES,
        generate_inventory_qr_value,
        get_inventory_item_by_qr,
        record_inventory_transaction,
    )
    from services.job_service import build_job_dropdown_label_maps, sort_jobs_by_number_then_name  # type: ignore
    from services.repository import fetch_rows  # type: ignore
    from styles import inject_inventory_qr_scan_css  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore
    from utils.phone_helpers import format_phone_display, is_valid_phone, normalize_phone  # type: ignore

_ACTION_LABELS: dict[str, str] = {
    "check_out": "Check Out",
    "check_in": "Check In",
    "issue_to_job": "Sign Out / Issue to Job",
    "return_from_job": "Return From Job",
    "consume_on_job": "Consume On Job",
}

_JOB_REQUIRED = frozenset({"issue_to_job", "return_from_job", "consume_on_job"})


def _first_query_param(name: str) -> str:
    try:
        v = st.query_params.get(name)
    except Exception:
        return ""
    if isinstance(v, list):
        return str(v[0]).strip() if v else ""
    return str(v or "").strip()


def capture_inventory_qr_from_query() -> None:
    """Persist QR params through login/navigation."""
    if _first_query_param("qr") != "inventory":
        return
    st.session_state["_ips_qr_inventory_page"] = True
    sku = _first_query_param("sku")
    token = _first_query_param("token")
    item_id = _first_query_param("item_id")
    if sku:
        st.session_state["_ips_qr_inv_sku"] = sku
    if token:
        st.session_state["_ips_qr_inv_token"] = token
    if item_id:
        st.session_state["_ips_qr_inv_item_id"] = item_id


def _profile_phone() -> str:
    prof = current_profile() or {}
    for key in ("phone_number", "phone", "mobile"):
        val = str(prof.get(key) or "").strip()
        if val:
            return val
    return ""


def _profile_name() -> str:
    prof = current_profile() or {}
    return str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()


def _profile_user_id() -> str | None:
    prof = current_profile() or {}
    uid = str(prof.get("id") or "").strip()
    return uid or None


def _active_job_options() -> tuple[list[str], dict[str, str]]:
    rows, _ = fetch_rows("jobs", limit=5000)
    inactive = frozenset({"completed", "closed", "cancelled", "inactive"})
    active = [
        j for j in rows
        if str(j.get("status") or "").strip().lower() not in inactive
    ]
    active = sort_jobs_by_number_then_name(active)
    _, label_to_id, labels = build_job_dropdown_label_maps(active)
    return ["— None —"] + labels, label_to_id


def _load_item_from_query() -> tuple[dict[str, Any] | None, str]:
    sku = _first_query_param("sku") or str(st.session_state.get("_ips_qr_inv_sku") or "")
    token = _first_query_param("token") or str(st.session_state.get("_ips_qr_inv_token") or "")
    item_id = _first_query_param("item_id") or str(st.session_state.get("_ips_qr_inv_item_id") or "")
    result = get_inventory_item_by_qr(sku=sku or None, item_id=item_id or None, token=token or None)
    if not result.ok:
        return None, str(result.error or "Invalid or expired inventory QR code.")
    return result.data, ""


def _can_submit() -> bool:
    role = str(current_role() or "viewer").lower()
    return role != "viewer"


def render_inventory_qr_action_page() -> None:
    """Minimal mobile page for inventory QR actions."""
    ensure_narrow_viewport_detected()
    inject_inventory_qr_scan_css()
    st.markdown('<span class="ips-inv-qr-scan-scope" aria-hidden="true"></span>', unsafe_allow_html=True)

    st.markdown("## IPS Inventory Scan")
    st.caption("Scan a labeled inventory QR code to check out, check in, or issue material.")

    if not is_authenticated():
        st.warning("Sign in to record inventory actions, or continue after login with this same QR link.")
        st.stop()

    if not _can_submit():
        st.error("Your role cannot submit inventory actions. Ask an admin for access.")
        st.stop()

    item, err = _load_item_from_query()
    if err or not item:
        st.error(err or "Invalid or expired inventory QR code.")
        st.stop()

    iid = str(item.get("id") or "")
    name = str(item.get("name") or item.get("item_name") or "—")
    sku = str(item.get("sku") or "—")
    unit = str(item.get("unit") or "EA")
    qoh = float(item.get("qty_on_hand") or item.get("quantity_on_hand") or 0)
    q_out = float(item.get("quantity_checked_out") or 0)
    q_alloc = float(item.get("quantity_allocated") or 0)
    status = str(item.get("status") or "—")

    st.markdown(
        f'<div class="ips-inv-qr-item-card">'
        f'<div class="ips-inv-qr-item-title">{html.escape(name)}</div>'
        f'<div class="ips-inv-qr-item-meta">SKU: {html.escape(sku)} · Unit: {html.escape(unit)} · Status: {html.escape(status)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.metric("On Hand", f"{qoh:g}")
    with c2:
        st.metric("Checked Out", f"{q_out:g}")
    with c3:
        st.metric("Allocated", f"{q_alloc:g}")

    scan_url = generate_inventory_qr_value(item)
    with st.expander("Scan link", expanded=False):
        st.code(scan_url or "—", language=None)

    prof_name = _profile_name()
    prof_phone = _profile_phone()
    job_labels, job_map = _active_job_options()

    action_keys = [k for k in INVENTORY_TXN_TYPES if k != "adjustment"]
    action_labels = [_ACTION_LABELS.get(k, k) for k in action_keys]

    with st.form("inv_qr_action_form", clear_on_submit=False):
        action_label = st.selectbox("Action", action_labels, key="inv_qr_action")
        action = action_keys[action_labels.index(action_label)]

        job_pick = st.selectbox("Job", job_labels, key="inv_qr_job")
        qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=0.25, format="%.4f", key="inv_qr_qty")

        st.markdown("**Contact (required if profile phone is missing)**")
        name_val = st.text_input(
            "Name",
            value=prof_name,
            key="inv_qr_name",
            disabled=bool(prof_name),
        )
        phone_val = st.text_input(
            "Phone number",
            value=prof_phone,
            key="inv_qr_phone",
            placeholder="(337) 555-0100",
        )
        st.caption("Phone is taken from your profile or entered here — it is not auto-detected from your device.")

        notes = st.text_area("Notes", key="inv_qr_notes", height=72, placeholder="Optional")
        allow_over = False
        if str(current_role() or "").lower() == "admin":
            allow_over = st.checkbox("Allow quantity over on-hand (admin)", key="inv_qr_over")

        submit = st.form_submit_button("Submit Inventory Action", type="primary", use_container_width=True)

    if not submit:
        return

    if action in _JOB_REQUIRED:
        job_label = str(job_pick or "").strip()
        if not job_label or job_label.startswith("—"):
            st.error("Select a job for this action.")
            st.stop()
        job_id = job_map.get(job_label)
        if not job_id:
            st.error("Invalid job selection.")
            st.stop()
    else:
        job_label = str(job_pick or "").strip()
        job_id = job_map.get(job_label) if job_label and not job_label.startswith("—") else None

    qv = float(qty or 0)
    if qv <= 0:
        st.error("Quantity must be greater than zero.")
        st.stop()

    actor_name = prof_name or str(name_val or "").strip()
    if not actor_name:
        st.error("Name is required.")
        st.stop()

    phone_norm = normalize_phone(phone_val or prof_phone)
    if not is_valid_phone(phone_norm):
        st.error("Enter a valid phone number.")
        st.stop()

    phone_verified = bool(prof_phone and normalize_phone(prof_phone) == phone_norm)

    result = record_inventory_transaction({
        "inventory_id": iid,
        "transaction_type": action,
        "quantity": qv,
        "job_id": job_id,
        "unit": unit,
        "scanned_by_user_id": _profile_user_id(),
        "scanned_by_name": actor_name,
        "scanned_by_phone": phone_norm,
        "phone_verified": phone_verified,
        "source": "qr_scan",
        "notes": notes,
        "allow_overdraw": allow_over,
    })

    if not result.ok:
        st.error(result.error or "Could not record transaction.")
        st.stop()

    data = result.data or {}
    st.success("Inventory action recorded.")
    st.markdown(
        f"**Action:** {_ACTION_LABELS.get(action, action)}  \n"
        f"**Quantity:** {qv:g} {html.escape(unit)}  \n"
        f"**Previous on hand:** {float(data.get('previous_quantity') or 0):g}  \n"
        f"**New on hand:** {float(data.get('new_quantity') or 0):g}  \n"
        f"**Recorded by:** {html.escape(actor_name)}  \n"
        f"**Phone:** {html.escape(format_phone_display(phone_norm))}"
    )
