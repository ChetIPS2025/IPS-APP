"""Estimates module (Phase 2B)."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

try:
    from app.components.record_modal import (
        build_modal_cache,
        clear_edit_modes,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        status_pill_html as modal_status_pill_html,
    )
    from app.pages.estimate_builder_ui import (
        render_cost_builder_tab,
        render_equipment_tab,
        render_labor_tab,
        render_markups_tab,
        render_materials_tab,
        render_other_costs_tab,
        render_proposal_preview_tab,
        render_subcontractors_tab,
        render_summary_tab,
        render_travel_tab,
    )
    from app.pages._core._data import (
        ACTIVE_ESTIMATE_KEY,
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        customer_location_select_options,
        get_estimate,
        load_assets,
        load_estimates,
        load_inventory,
        load_jobs,
        lookup_options,
        persist_estimate,
    )
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from app.pages._core._crud import is_demo_id
    from app.pages._core._session import select_key
    from app.services.estimates_service import (
        approve_estimate_and_job,
        can_approve_estimates,
        estimate_status_approvable,
        estimate_visible_in_active_view,
        estimate_visible_in_approved_view,
        estimate_visible_in_rejected_view,
    )
    from app.auth import current_role
    from app.styles import inject_estimates_module_css
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_edit_modes,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        status_pill_html as modal_status_pill_html,
    )
    from pages.estimate_builder_ui import (  # type: ignore
        render_cost_builder_tab,
        render_equipment_tab,
        render_labor_tab,
        render_markups_tab,
        render_materials_tab,
        render_other_costs_tab,
        render_proposal_preview_tab,
        render_subcontractors_tab,
        render_summary_tab,
        render_travel_tab,
    )
    from pages._core._data import (  # type: ignore
        ACTIVE_ESTIMATE_KEY,
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        customer_location_select_options,
        get_estimate,
        load_assets,
        load_estimates,
        load_inventory,
        load_jobs,
        lookup_options,
        persist_estimate,
    )
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from pages._core._crud import is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.estimates_service import (  # type: ignore
        approve_estimate_and_job,
        can_approve_estimates,
        estimate_status_approvable,
        estimate_visible_in_active_view,
        estimate_visible_in_approved_view,
        estimate_visible_in_rejected_view,
    )
    from auth import current_role  # type: ignore
    from styles import inject_estimates_module_css  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_SEL = select_key("estimates")
_MOD = "estimates"
_TABLE_KEY = "estimates_list"
_ESTIMATES_MODAL_KEY = "ips_estimates_detail_modal_id"
_ESTIMATES_CACHE_KEY = "_ips_estimates_modal_by_id"
_NEW_CUST_PREV = "est_new_cust_prev"
_ESTIMATE_TABS = [
    "Overview",
    "Cost Builder",
    "Materials",
    "Labor",
    "Equipment",
    "Travel",
    "Subcontractors",
    "Markups",
    "Summary",
    "Proposal Preview",
    "Attachments",
    "Notes",
    "Activity",
]
_ESTIMATE_COLS = [0.35, 1.0, 2.5, 1.6, 1.0, 1.0, 1.0, 1.0, 1.15]
_ESTIMATE_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("ESTIMATE #", None),
    ("PROJECT / DESCRIPTION", None),
    ("CUSTOMER", "customer"),
    ("LINKED JOB", None),
    ("STATUS", "status"),
    ("ESTIMATE DATE", None),
    ("TOTAL", None),
    ("ACTIONS", None),
]
_ESTIMATE_FILTER_FIELDS = ["customer", "status"]
_ESTIMATE_VIEW_FILTER_KEY = "est_view_filter"
_PENDING_APPROVE_KEY = "est_pending_approve_id"
_ESTIMATE_VIEW_OPTIONS = (
    "Active Estimates",
    "Approved / Converted",
    "Rejected",
    "All Estimates",
)
_NEW_ESTIMATE_DIALOG_KEY = "ips_est_new_dialog_open"
_BUILD_MODE_PREFIX = "est_build_mode_"
SELECTED_ESTIMATE_KEY = "selected_estimate_id"
SHOW_ESTIMATE_MODAL_KEY = "show_estimate_detail_modal"
_ALL_ESTIMATE_IDS_KEY = "_ips_estimates_visible_ids"


def _default_estimate_date_range() -> tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today


def _as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _normalize_estimate_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Draft",
        "draft": "Draft",
        "pending": "Pending",
        "sent": "Sent",
        "approved": "Approved",
        "awarded": "Awarded",
        "rejected": "Rejected",
        "expired": "Expired",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "Draft"


def _estimate_number(row: dict) -> str:
    val = str(row.get("estimate_number") or row.get("number") or "").strip()
    return val or "—"


def _estimate_project(row: dict) -> str:
    for key in ("project_name", "project_description", "description"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _estimate_customer(row: dict) -> str:
    for key in ("customer_name", "customer"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _estimate_created_by(row: dict) -> str:
    val = str(row.get("created_by") or row.get("created_by_name") or "").strip()
    return val or "—"


def _estimate_job(row: dict) -> str:
    val = str(row.get("job_number") or row.get("linked_job") or "").strip()
    return val if val and val != "—" else "—"


def _estimate_total_cost(row: dict) -> str:
    val = row.get("total_cost")
    if val in (None, ""):
        val = row.get("subtotal")
    return fmt_currency(val)


def _estimate_customer_price(row: dict) -> str:
    for key in ("customer_price", "total", "proposal_total", "final_bid"):
        val = row.get(key)
        if val not in (None, ""):
            try:
                if float(val) != 0 or key in ("customer_price", "proposal_total", "final_bid"):
                    return fmt_currency(val)
            except (TypeError, ValueError):
                continue
    return fmt_currency(0)


def _inventory_options() -> list[tuple[str, dict]]:
    try:
        from app.services.estimate_builder_helpers import inventory_options_as_select
    except ImportError:
        from services.estimate_builder_helpers import inventory_options_as_select  # type: ignore
    return inventory_options_as_select()


def _pricing_guide_options() -> list[tuple[str, dict]]:
    try:
        from app.services.estimate_builder_helpers import pricing_guide_options_as_select
    except ImportError:
        from services.estimate_builder_helpers import pricing_guide_options_as_select  # type: ignore
    return pricing_guide_options_as_select()


def _asset_options() -> list[tuple[str, dict]]:
    try:
        from app.services.estimate_builder_helpers import asset_options_as_select
    except ImportError:
        from services.estimate_builder_helpers import asset_options_as_select  # type: ignore
    return asset_options_as_select()


def _vendor_options() -> list[str]:
    vendors: set[str] = set()
    for item in load_inventory():
        v = str(item.get("vendor") or "").strip()
        if v and v != "—":
            vendors.add(v)
    return sorted(vendors)


def _job_select_options(customer_name: str) -> list[tuple[str, str]]:
    cid = customer_id_for_name(customer_name)
    out: list[tuple[str, str]] = [("— None —", "")]
    for job in load_jobs():
        if cid and str(job.get("customer_id") or "") != cid:
            jcust = str(job.get("customer_name") or job.get("customer") or "")
            if jcust != customer_name:
                continue
        label = str(job.get("job_number") or job.get("id") or "")
        proj = str(job.get("project_name") or job.get("job_name") or "")
        if proj:
            label = f"{label} — {proj}"
        out.append((label, str(job.get("id") or "")))
    return out


def _build_mode_key(est: dict) -> str:
    rk = record_session_key(est, "id", "estimate_number")
    return f"{_BUILD_MODE_PREFIX}{rk}"


def _set_estimate_build_mode(est: dict) -> None:
    st.session_state[_build_mode_key(est)] = True
    rk = record_session_key(est, "id", "estimate_number")
    set_view_mode(_MOD, rk)


def _persist_markup_settings(data: dict, row_id: str) -> tuple[bool, str]:
    est = get_estimate(row_id) or {}
    ok, msg = persist_estimate(
        {
            "estimate_number": est.get("estimate_number"),
            "project_name": est.get("project_name"),
            "customer": est.get("customer"),
            "customer_id": est.get("customer_id") or customer_id_for_name(str(est.get("customer") or "")),
            **data,
        },
        row_id=row_id,
    )
    return ok, msg


def _estimate_status_pill_html(status: str) -> str:
    cls_map = {
        "Draft": "ips-estimate-status-draft",
        "Pending": "ips-estimate-status-pending",
        "Sent": "ips-estimate-status-sent",
        "Approved": "ips-estimate-status-approved",
        "Awarded": "ips-estimate-status-awarded",
        "Rejected": "ips-estimate-status-rejected",
        "Expired": "ips-estimate-status-expired",
        "Cancelled": "ips-estimate-status-cancelled",
    }
    cls = cls_map.get(status, "ips-estimate-status-draft")
    return f'<span class="ips-estimate-status-pill {cls}">{html.escape(status)}</span>'


_ESTIMATE_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("customer", _estimate_customer),
    ("status", lambda r: _normalize_estimate_status(r.get("status"))),
]


def _estimate_select_key(estimate_id: str) -> str:
    return f"estimate_select_{estimate_id}"


def _clear_estimate_selection(estimate_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_ESTIMATE_KEY] = None
    st.session_state[SHOW_ESTIMATE_MODAL_KEY] = False
    ids = list(estimate_ids or [])
    for eid in ids:
        st.session_state[_estimate_select_key(eid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("estimate_select_"):
            st.session_state[key] = False


def _on_estimate_checkbox_change(estimate_id: str, all_estimate_ids: list[str]) -> None:
    key = _estimate_select_key(estimate_id)
    if st.session_state.get(key):
        for eid in all_estimate_ids:
            if eid != estimate_id:
                st.session_state[_estimate_select_key(eid)] = False
        st.session_state[SELECTED_ESTIMATE_KEY] = estimate_id
        st.session_state[SHOW_ESTIMATE_MODAL_KEY] = True
        cache = st.session_state.get(_ESTIMATES_CACHE_KEY) or {}
        estimate = cache.get(estimate_id) if isinstance(cache, dict) else None
        _open_estimates_detail_modal(estimate_id, estimate)
    elif st.session_state.get(SELECTED_ESTIMATE_KEY) == estimate_id:
        st.session_state[SELECTED_ESTIMATE_KEY] = None
        st.session_state[SHOW_ESTIMATE_MODAL_KEY] = False


def _render_custom_estimates_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No estimates match your filters.")
        st.session_state[_ALL_ESTIMATE_IDS_KEY] = []
        return []

    all_estimate_ids = [
        str(e.get("id") or "").strip() for e in filtered if str(e.get("id") or "").strip()
    ]
    st.session_state[_ALL_ESTIMATE_IDS_KEY] = all_estimate_ids

    with st.container(key="estimates_table_wrap"):
        st.markdown('<div class="ips-estimates-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_ESTIMATE_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _ESTIMATE_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-estimates-header-row ips-estimates-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-estimates-header-row ips-estimates-cell",
                    )

        for est in filtered:
            eid = str(est.get("id") or "").strip()
            if not eid:
                continue

            est_no = _estimate_number(est)
            project = _estimate_project(est)
            customer = _estimate_customer(est)
            status = _normalize_estimate_status(est.get("status"))
            est_date = fmt_date(est.get("estimate_date"))
            job_no = _estimate_job(est)
            total = _estimate_customer_price(est)

            cols = st.columns(_ESTIMATE_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_estimate_select_key(eid),
                    label_visibility="collapsed",
                    on_change=_on_estimate_checkbox_change,
                    args=(eid, all_estimate_ids),
                )

            with cols[1]:
                st.markdown(
                    f'<div class="ips-estimates-number">{html.escape(est_no)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<div class="ips-estimates-title">{html.escape(project)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-estimates-cell">{html.escape(customer)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-muted">{html.escape(job_no)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(_estimate_status_pill_html(status), unsafe_allow_html=True)

            with cols[6]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-muted">{html.escape(est_date)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[7]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-number">{html.escape(total)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[8]:
                if _can_show_approve_job(est):
                    if st.button(
                        "Approve Job",
                        key=f"est_row_approve_{eid}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        st.session_state[_PENDING_APPROVE_KEY] = eid
                        st.rerun()
                elif estimate_visible_in_approved_view(est):
                    st.markdown(
                        '<span class="ips-est-approve-done">Job Approved</span>',
                        unsafe_allow_html=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    return all_estimate_ids


def _contact_label_for_estimate(est: dict) -> str:
    ccid = str(est.get("customer_contact_id") or "").strip()
    if not ccid:
        return "—"
    cid = customer_id_for_name(str(est.get("customer") or ""))
    for label, contact_id in customer_contact_select_options(cid):
        if contact_id == ccid:
            return label
    return "—"


def _customer_location_select(
    *,
    customer_name: str,
    session_key: str,
    prev_customer_key: str,
    initial_location_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust

    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox("Location", ["— Select customer first —"], disabled=True, key=session_key)
        return ""

    pairs = customer_location_select_options(cid)
    if not pairs:
        st.warning("Add a customer location before assigning contacts/jobs.")
        st.selectbox("Location", ["— No locations —"], disabled=True, key=session_key)
        return ""

    labels = ["— Select location —", *[label for label, _ in pairs]]
    ids = ["", *[loc_id for _, loc_id in pairs]]
    if session_key not in st.session_state and initial_location_id:
        try:
            st.session_state[session_key] = ids.index(initial_location_id)
        except ValueError:
            st.session_state[session_key] = 0
    idx = st.selectbox(
        "Location",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=session_key,
    )
    return str(ids[int(idx)])


def _customer_contact_select(
    *,
    customer_name: str,
    location_id: str,
    session_key: str,
    prev_customer_key: str,
    prev_location_key: str,
    initial_contact_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    loc_id = str(location_id or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust
    if st.session_state.get(prev_location_key) != loc_id:
        st.session_state.pop(session_key, None)
        st.session_state[prev_location_key] = loc_id

    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox("Contact", ["— Select customer first —"], disabled=True, key=session_key)
        return ""
    if not loc_id:
        st.selectbox("Contact", ["— Select location first —"], disabled=True, key=session_key)
        return ""

    pairs = customer_contact_select_options(cid, loc_id)
    if not pairs:
        st.selectbox("Contact", ["— No contacts for this location —"], disabled=True, key=session_key)
        return ""

    labels = ["— Select contact —", *[label for label, _ in pairs]]
    ids = ["", *[contact_id for _, contact_id in pairs]]

    if session_key not in st.session_state and initial_contact_id:
        try:
            st.session_state[session_key] = ids.index(initial_contact_id)
        except ValueError:
            st.session_state[session_key] = 0

    idx = st.selectbox(
        "Contact",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=session_key,
    )
    return str(ids[int(idx)])


def _apply_estimate_view_filter(rows: list[dict], view_filter: str) -> list[dict]:
    vf = str(view_filter or "Active Estimates").strip()
    if vf == "All Estimates":
        return rows
    if vf == "Approved / Converted":
        return [r for r in rows if estimate_visible_in_approved_view(r)]
    if vf == "Rejected":
        return [r for r in rows if estimate_visible_in_rejected_view(r)]
    return [r for r in rows if estimate_visible_in_active_view(r)]


def _can_show_approve_job(est: dict) -> bool:
    if not can_approve_estimates(current_role()):
        return False
    eid = str(est.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return False
    return estimate_status_approvable(est.get("status")) and not estimate_visible_in_approved_view(est)


def _render_approve_confirmation_panel(rows_by_id: dict[str, dict]) -> None:
    eid = str(st.session_state.get(_PENDING_APPROVE_KEY) or "").strip()
    if not eid:
        return
    est = rows_by_id.get(eid)
    if not est:
        st.session_state.pop(_PENDING_APPROVE_KEY, None)
        return

    st.markdown('<div class="ips-est-approve-panel">', unsafe_allow_html=True)
    st.markdown("**Approve this estimate and activate the linked job?**")
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.caption("Estimate #")
        st.write(_estimate_number(est))
    with c2:
        st.caption("Project")
        st.write(_estimate_project(est))
    with c3:
        st.caption("Customer")
        st.write(_estimate_customer(est))
    with c4:
        st.caption("Total")
        st.write(_estimate_customer_price(est))
    st.caption(f"Linked job: **{_estimate_job(est)}**")
    b1, b2, _ = st.columns([1, 1, 3], gap="small")
    with b1:
        if st.button("Approve Job", key=f"est_confirm_approve_{eid}", type="primary", use_container_width=True):
            res = approve_estimate_and_job(eid)
            if res.ok:
                try:
                    from app.services.phase2_modules_service import clear_all_data_caches
                except ImportError:
                    from services.phase2_modules_service import clear_all_data_caches  # type: ignore
                clear_all_data_caches()
                st.session_state.pop(_PENDING_APPROVE_KEY, None)
                st.success(res.message or "Estimate approved and linked job activated.")
                st.rerun()
            st.error(res.message or "Could not approve estimate.")
    with b2:
        if st.button("Cancel", key=f"est_confirm_cancel_{eid}", use_container_width=True):
            st.session_state.pop(_PENDING_APPROVE_KEY, None)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _filter_rows(
    rows: list[dict],
    *,
    q: str,
    date_range: tuple[date, date] | None,
    view_filter: str,
) -> list[dict]:
    out = _apply_estimate_view_filter(rows, view_filter)
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in _estimate_number(r).lower()
            or ql in _estimate_project(r).lower()
            or ql in _estimate_customer(r).lower()
            or ql in _estimate_created_by(r).lower()
            or ql in _normalize_estimate_status(r.get("status")).lower()
        ]
    if date_range and len(date_range) == 2:
        start, end = date_range
        filtered_range: list[dict] = []
        for row in out:
            est_date = _as_date(row.get("estimate_date"))
            if est_date is None or (start <= est_date <= end):
                filtered_range.append(row)
        out = filtered_range
    return apply_column_filters(out, _TABLE_KEY, _ESTIMATE_COLUMN_FILTER_SPECS)


def _clear_estimates_detail_modal() -> None:
    estimate_ids = st.session_state.get(_ALL_ESTIMATE_IDS_KEY) or []
    _clear_estimate_selection([str(eid) for eid in estimate_ids])
    clear_edit_modes(_MOD)
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_ESTIMATES_MODAL_KEY,
        module=_MOD,
    )


def _open_estimates_detail_modal(estimate_id: str, estimate: dict | None = None) -> None:
    open_record_modal(
        estimate_id,
        estimate,
        session_select_key=_SEL,
        modal_key=_ESTIMATES_MODAL_KEY,
        module=_MOD,
        id_fields=("id", "estimate_number"),
    )
    if estimate:
        st.session_state[ACTIVE_ESTIMATE_KEY] = str(estimate.get("id") or "")


def _seed_estimate_edit_form(est: dict) -> None:
    eid = str(est.get("id") or "")
    st.session_state[f"est_edit_num_{eid}"] = str(est.get("estimate_number") or "")
    st.session_state[f"est_edit_proj_{eid}"] = str(est.get("project_name") or "")
    st.session_state[f"est_edit_cust_{eid}"] = str(est.get("customer") or "")
    st.session_state[f"est_edit_status_{eid}"] = str(est.get("status") or "Draft")
    st.session_state[f"est_edit_desc_{eid}"] = str(est.get("description") or est.get("scope_of_work") or "")
    st.session_state[f"est_edit_notes_{eid}"] = str(est.get("notes") or "")
    st.session_state[f"est_edit_est_date_{eid}"] = _as_date(est.get("estimate_date")) or date.today()
    st.session_state[f"est_edit_exp_date_{eid}"] = _as_date(est.get("expiration_date")) or (date.today() + timedelta(days=30))
    st.session_state.pop(f"est_edit_contact_{eid}", None)
    st.session_state.pop(f"est_edit_location_{eid}", None)
    st.session_state.pop(f"est_edit_job_{eid}", None)
    st.session_state.pop(f"est_edit_cust_prev_{eid}", None)
    st.session_state.pop(f"est_edit_loc_prev_{eid}", None)


def _set_estimate_view_mode(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    set_view_mode(_MOD, rk)


def _set_estimate_edit_mode(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    set_edit_mode(_MOD, rk)
    _seed_estimate_edit_form(est)


def _render_estimate_edit_form(est: dict) -> None:
    eid = str(est.get("id") or "")
    rk = record_session_key(est, "id", "estimate_number")
    if f"est_edit_num_{eid}" not in st.session_state:
        _seed_estimate_edit_form(est)

    render_edit_form_header("Edit Estimate")

    if is_demo_id(eid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Estimate #", key=f"est_edit_num_{eid}")
        st.text_input("Project", key=f"est_edit_proj_{eid}")
        st.selectbox(
            "Customer",
            customer_filter_options(include_names={str(est.get("customer") or "")}),
            key=f"est_edit_cust_{eid}",
        )
        cust_name = str(st.session_state.get(f"est_edit_cust_{eid}") or est.get("customer") or "")
        location_id = _customer_location_select(
            customer_name=cust_name,
            session_key=f"est_edit_location_{eid}",
            prev_customer_key=f"est_edit_cust_prev_{eid}",
            initial_location_id=str(est.get("customer_location_id") or ""),
        )
        contact_id = _customer_contact_select(
            customer_name=cust_name,
            location_id=location_id,
            session_key=f"est_edit_contact_{eid}",
            prev_customer_key=f"est_edit_cust_prev_{eid}",
            prev_location_key=f"est_edit_loc_prev_{eid}",
            initial_contact_id=str(est.get("customer_contact_id") or ""),
        )
        st.selectbox("Status", lookup_options("estimate_statuses"), key=f"est_edit_status_{eid}")
        st.date_input("Estimate date", key=f"est_edit_est_date_{eid}")
        st.date_input("Expiration date", key=f"est_edit_exp_date_{eid}")
    with ec2:
        job_opts = _job_select_options(cust_name)
        job_labels = [label for label, _ in job_opts]
        job_ids = [jid for _, jid in job_opts]
        cur_job = str(est.get("job_id") or "")
        if f"est_edit_job_{eid}" not in st.session_state and cur_job in job_ids:
            st.session_state[f"est_edit_job_{eid}"] = job_ids.index(cur_job)
        elif f"est_edit_job_{eid}" not in st.session_state:
            st.session_state[f"est_edit_job_{eid}"] = 0
        st.selectbox(
            "Linked job (optional)",
            range(len(job_labels)),
            format_func=lambda i: job_labels[i],
            key=f"est_edit_job_{eid}",
        )
    st.text_area("Description / scope summary", key=f"est_edit_desc_{eid}", height=90)
    st.text_area("Notes", key=f"est_edit_notes_{eid}", height=70)

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"est_edit_cancel_{eid}",
        save_key=f"est_edit_save_{eid}",
    )
    if cancelled:
        st.rerun()
    if saved:
        cust_name = str(st.session_state.get(f"est_edit_cust_{eid}") or "")
        job_opts = _job_select_options(cust_name)
        job_idx = int(st.session_state.get(f"est_edit_job_{eid}") or 0)
        job_id = job_opts[job_idx][1] if job_opts else ""
        ok, msg = persist_estimate(
            {
                "estimate_number": st.session_state.get(f"est_edit_num_{eid}"),
                "project_name": st.session_state.get(f"est_edit_proj_{eid}"),
                "customer": cust_name,
                "customer_id": customer_id_for_name(cust_name) or None,
                "customer_location_id": location_id or None,
                "customer_contact_id": contact_id or None,
                "job_id": job_id or None,
                "status": st.session_state.get(f"est_edit_status_{eid}"),
                "estimate_date": str(st.session_state.get(f"est_edit_est_date_{eid}")),
                "expiration_date": str(st.session_state.get(f"est_edit_exp_date_{eid}")),
                "description": st.session_state.get(f"est_edit_desc_{eid}"),
                "notes": st.session_state.get(f"est_edit_notes_{eid}"),
            },
            row_id=eid,
        )
        if ok:
            set_view_mode(_MOD, rk)
            st.success(msg or "Estimate saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save estimate.")


def _render_estimate_detail_tabs(est: dict) -> None:
    eid = str(est.get("id") or "")
    en = safe_value(est.get("estimate_number"))
    status = safe_value(est.get("status"))
    customer = safe_value(est.get("customer"))
    inv_opts = _inventory_options()
    pg_opts = _pricing_guide_options()
    asset_opts = _asset_options()
    vendor_opts = _vendor_options()

    if st.session_state.get(_build_mode_key(est)):
        st.info("Build mode — add materials, labor, equipment, travel, and review totals in the tabs below.")

    (
        tab_overview,
        tab_cost_builder,
        tab_materials,
        tab_labor,
        tab_equipment,
        tab_travel,
        tab_subcontractors,
        tab_markups,
        tab_summary,
        tab_proposal,
        tab_attachments,
        tab_notes,
        tab_activity,
    ) = st.tabs(_ESTIMATE_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Estimate #', en)}"
            f"{detail_field_html('Project', est.get('project_name'))}"
            f"{detail_field_html('Customer', customer)}"
            f"{detail_field_html('Contact', _contact_label_for_estimate(est))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"{detail_field_html('Estimate date', fmt_date(est.get('estimate_date')))}"
            f"{detail_field_html('Expiration', fmt_date(est.get('expiration_date')))}"
            f"{detail_field_html('Linked Job', est.get('job_number'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Estimate Summary", overview_html), unsafe_allow_html=True)

        margin_pct = f"{float(est.get('gross_margin_percent') or 0):.1f}%"
        fin_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Total cost', _estimate_total_cost(est))}"
            f"{detail_field_html('Customer price', _estimate_customer_price(est))}"
            f"{detail_field_html('Tax', fmt_currency(est.get('tax')))}"
            f"{detail_field_html('Gross profit', fmt_currency(est.get('gross_profit')))}"
            f"{detail_field_html('Margin %', margin_pct)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Financial Summary", fin_html), unsafe_allow_html=True)
        scope = safe_value(est.get("description") or est.get("scope_of_work"), "No scope entered.")
        st.markdown(dialog_card_html("Scope", f"<p style='margin:0;font-size:0.875rem;'>{html.escape(scope)}</p>"), unsafe_allow_html=True)

    with tab_cost_builder:
        render_cost_builder_tab(
            est,
            pricing_guide_options=pg_opts,
            inventory_options=inv_opts,
            asset_options=asset_opts,
            vendor_options=vendor_opts,
            on_saved=lambda: None,
        )

    with tab_materials:
        render_materials_tab(est, pricing_guide_options=pg_opts, inventory_options=inv_opts)

    with tab_labor:
        render_labor_tab(est)

    with tab_equipment:
        render_equipment_tab(est, asset_options=asset_opts)

    with tab_travel:
        render_travel_tab(est)

    with tab_subcontractors:
        render_subcontractors_tab(est, vendor_options=vendor_opts)
        render_other_costs_tab(est)

    with tab_markups:
        render_markups_tab(est, persist_fn=_persist_markup_settings)

    with tab_summary:
        render_summary_tab(est)

    with tab_proposal:
        render_proposal_preview_tab(est)

    with tab_attachments:
        placeholder_html("Estimate attachments will appear here when connected to document storage.")

    with tab_notes:
        notes_text = safe_value(est.get("notes") or est.get("description"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Estimate activity history will appear here when connected to Supabase.")


def render_estimate_detail_dialog(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    eid = str(est.get("id") or "")
    en = safe_value(est.get("estimate_number"))
    project = safe_value(est.get("project_name"))
    status = safe_value(est.get("status"))
    customer = safe_value(est.get("customer"))
    total = fmt_currency(est.get("total"))
    linked_job = str(est.get("job_id") or est.get("job_number") or "").strip()

    render_modal_shell()
    render_modal_header(title=en, subtitle=project, status=status)

    show_approve_job = eid and not is_demo_id(eid) and not is_edit_mode(_MOD, rk) and _can_show_approve_job(est)

    btn1, btn2, btn3 = st.columns(3, gap="small")
    with btn1:
        if st.button("Edit", key=f"estimates_modal_edit_{rk}", use_container_width=True):
            _set_estimate_edit_mode(est)
            st.rerun()
    with btn2:
        if st.button("Build Estimate", key=f"estimates_modal_build_{rk}", use_container_width=True):
            _set_estimate_build_mode(est)
            st.rerun()
    with btn3:
        if show_approve_job:
            if st.button(
                "Approve Job",
                key=f"estimates_modal_approve_job_{rk}",
                type="primary",
                use_container_width=True,
            ):
                st.session_state[_PENDING_APPROVE_KEY] = eid
                st.rerun()

    if eid and show_approve_job and not is_edit_mode(_MOD, rk):
        st.caption(
            "Approves the estimate and activates the linked job. "
            "The estimate will move to **Approved / Converted** and leave the active list."
        )

    render_modal_meta_grid(
        [
            ("Customer", customer),
            ("Total", total),
            ("Status", status),
            ("Linked Job", safe_value(est.get("job_number"))),
        ]
    )

    if is_edit_mode(_MOD, rk):
        _render_estimate_edit_form(est)
    else:
        _render_estimate_detail_tabs(est)


@st.dialog("Estimate Details", width="large", on_dismiss=_clear_estimates_detail_modal)
def _show_estimates_detail_modal() -> None:
    est = get_modal_record(
        cache_key=_ESTIMATES_CACHE_KEY,
        modal_key=_ESTIMATES_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not est:
        sel = str(st.session_state.get(_ESTIMATES_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
        est = get_estimate(sel) if sel else None
    if not est:
        render_missing_record(_clear_estimates_detail_modal, close_key="estimates_modal_missing_close")
        return
    st.session_state[ACTIVE_ESTIMATE_KEY] = str(est.get("id") or "")
    render_estimate_detail_dialog(est)


@st.dialog("New Estimate", width="large")
def _show_new_estimate_dialog() -> None:
    customers = customer_filter_options()
    nc1, nc2 = st.columns(2)
    with nc1:
        st.text_input("Estimate # (auto if blank)", key="est_new_num")
        st.text_input("Project name", key="est_new_proj")
        st.selectbox("Customer", customers, key="est_new_cust")
        new_cust = str(st.session_state.get("est_new_cust") or "")
        new_location_id = _customer_location_select(
            customer_name=new_cust,
            session_key="est_new_location",
            prev_customer_key=_NEW_CUST_PREV,
        )
        new_contact_id = _customer_contact_select(
            customer_name=new_cust,
            location_id=new_location_id,
            session_key="est_new_contact",
            prev_customer_key=_NEW_CUST_PREV,
            prev_location_key="est_new_loc_prev",
        )
    with nc2:
        st.date_input("Estimate date", value=date.today(), key="est_new_est_date")
        st.date_input("Expiration date", value=date.today() + timedelta(days=30), key="est_new_exp_date")
        st.selectbox("Status", lookup_options("estimate_statuses"), index=0, key="est_new_status")
        st.caption("A linked job in **Estimate Pending** status is created automatically when you save.")
    st.text_area("Description / scope summary", key="est_new_desc", height=80)
    st.text_area("Notes", key="est_new_notes", height=60)

    sb1, sb2 = st.columns(2)
    with sb1:
        if st.button("Save Draft", key="est_save_new", type="primary", use_container_width=True):
            ok, msg = persist_estimate(
                {
                    "estimate_number": st.session_state.get("est_new_num"),
                    "project_name": st.session_state.get("est_new_proj"),
                    "customer": new_cust,
                    "customer_id": customer_id_for_name(new_cust) or None,
                    "customer_location_id": new_location_id or None,
                    "customer_contact_id": new_contact_id or None,
                    "status": st.session_state.get("est_new_status") or "Draft",
                    "estimate_date": str(st.session_state.get("est_new_est_date")),
                    "expiration_date": str(st.session_state.get("est_new_exp_date")),
                    "description": st.session_state.get("est_new_desc"),
                    "notes": st.session_state.get("est_new_notes"),
                }
            )
            if ok:
                st.session_state[_NEW_ESTIMATE_DIALOG_KEY] = False
                st.success(msg or "Estimate saved.")
                st.rerun()
            st.error(msg or "Could not save estimate.")
    with sb2:
        if st.button("Cancel", key="est_cancel_new", use_container_width=True):
            st.session_state[_NEW_ESTIMATE_DIALOG_KEY] = False
            st.rerun()


def _export_estimates_csv(rows: list[dict]) -> str:
    import csv
    from io import StringIO

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["Estimate #", "Project", "Customer", "Linked Job", "Status", "Estimate Date", "Total"]
    )
    for row in rows:
        writer.writerow(
            [
                _estimate_number(row),
                _estimate_project(row),
                _estimate_customer(row),
                _estimate_job(row),
                _normalize_estimate_status(row.get("status")),
                fmt_date(row.get("estimate_date")),
                _estimate_customer_price(row).replace("$", ""),
            ]
        )
    return buf.getvalue()


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("estimates"):
        return
    inject_estimates_module_css()
    st.markdown('<div class="ips-estimates-page"></div>', unsafe_allow_html=True)
    rows = load_estimates()
    filter_options = build_filter_options(rows, _ESTIMATE_COLUMN_FILTER_SPECS)

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Estimates", "Create, review, price, and send customer proposals.")
    with act_r:
        exp_col, add_col = st.columns(2, gap="small")
        with exp_col:
            if st.button("Export", key="est_export", use_container_width=True):
                st.session_state["est_export_ready"] = True
        with add_col:
            if st.button("+ New Estimate", key="est_new", type="primary", use_container_width=True):
                st.session_state[_NEW_ESTIMATE_DIALOG_KEY] = True

    if st.session_state.get(_NEW_ESTIMATE_DIALOG_KEY):
        _show_new_estimate_dialog()

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([2, 1.2, 1, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search estimates...",
                key="est_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "View",
                list(_ESTIMATE_VIEW_OPTIONS),
                key=_ESTIMATE_VIEW_FILTER_KEY,
                label_visibility="collapsed",
            )
        with c3:
            st.date_input(
                "Date range",
                value=_default_estimate_date_range(),
                key="est_filter_dates",
                label_visibility="collapsed",
            )
        with c4:
            if st.button("Clear", key="est_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _ESTIMATE_FILTER_FIELDS,
                    extra_keys=["est_search", _ESTIMATE_VIEW_FILTER_KEY],
                )
                st.session_state["est_filter_dates"] = _default_estimate_date_range()
                st.session_state[_ESTIMATE_VIEW_FILTER_KEY] = "Active Estimates"
                st.session_state.pop(_PENDING_APPROVE_KEY, None)
                st.rerun()

    layout_filter_bar(_filters)

    date_range = st.session_state.get("est_filter_dates")
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        date_range = _default_estimate_date_range()

    view_filter = str(st.session_state.get(_ESTIMATE_VIEW_FILTER_KEY) or "Active Estimates")

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("est_search") or "").strip(),
        date_range=date_range,
        view_filter=view_filter,
    )

    rows_by_id = {str(r.get("id") or ""): r for r in rows if str(r.get("id") or "").strip()}
    _render_approve_confirmation_panel(rows_by_id)

    if st.session_state.pop("est_export_ready", False):
        st.download_button(
            "Download CSV",
            data=_export_estimates_csv(filtered),
            file_name="estimates_export.csv",
            mime="text/csv",
            key="est_export_download",
        )

    st.caption(f"{len(filtered)} estimate(s)")

    build_modal_cache(filtered, cache_key=_ESTIMATES_CACHE_KEY)
    _render_custom_estimates_table(filtered, filter_options=filter_options)

    selected_estimate_id = st.session_state.get(SELECTED_ESTIMATE_KEY)
    if selected_estimate_id and st.session_state.get(SHOW_ESTIMATE_MODAL_KEY):
        _show_estimates_detail_modal()
