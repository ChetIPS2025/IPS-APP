"""Customers module — company directory with sites and contacts."""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

try:
    from app.components.headers import render_page_brand_header
    from app.components.customers_list_table import (
        customer_status_pill_html,
        normalize_customer_status,
    )
    from app.components.customers_page_layout import (
        close_customers_filter_bar_shell,
        inject_customers_page_layout_css,
        render_customers_filter_bar_shell,
    )
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from app.components.table_pagination import (
        paginate_rows,
        render_table_pagination_footer,
        render_table_pagination_header,
        reset_table_page,
    )
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
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html as modal_status_pill_html,
    )
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._data import estimates_for_customer, jobs_for_customer, load_estimates, load_jobs
    from app.pages._core._session import select_key
    from app.services.customers_service import (
        CONTACT_ROLE_TYPES,
        LOCATION_TYPES,
        create_customer,
        create_customer_contact,
        create_customer_location,
        get_customer,
        get_customer_contact,
        get_customer_contacts,
        get_customer_location,
        get_customer_locations,
        get_customers,
        update_customer,
        update_customer_contact,
        update_customer_location,
    )
    from app.styles import inject_customers_module_css
    from app.ui.streamlit_perf import fragment
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from components.customers_list_table import (  # type: ignore
        customer_status_pill_html,
        normalize_customer_status,
    )
    from components.customers_page_layout import (  # type: ignore
        close_customers_filter_bar_shell,
        inject_customers_page_layout_css,
        render_customers_filter_bar_shell,
    )
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from components.table_pagination import (  # type: ignore
        paginate_rows,
        render_table_pagination_footer,
        render_table_pagination_header,
        reset_table_page,
    )
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
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html as modal_status_pill_html,
    )
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._data import estimates_for_customer, jobs_for_customer, load_estimates, load_jobs  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.customers_service import (  # type: ignore
        CONTACT_ROLE_TYPES,
        LOCATION_TYPES,
        create_customer,
        create_customer_contact,
        create_customer_location,
        get_customer,
        get_customer_contact,
        get_customer_contacts,
        get_customer_location,
        get_customer_locations,
        get_customers,
        update_customer,
        update_customer_contact,
        update_customer_location,
    )
    from styles import inject_customers_module_css  # type: ignore
    from ui.streamlit_perf import fragment  # type: ignore

_SEL = select_key("customers")
_LOC_SEL = select_key("customer_locations")
_CT_SEL = select_key("customer_contacts")

_MOD = "customers"
_LOC_MOD = "customer_locations"
_CT_MOD = "customer_contacts"

_CUSTOMERS_TABLE_KEY = "customers_list"
_LOCATIONS_TABLE_KEY = "customer_locations_list"
_CONTACTS_TABLE_KEY = "customer_contacts_list"

_CUSTOMERS_MODAL_KEY = "ips_customers_detail_modal_id"
_LOCATION_MODAL_KEY = "ips_customer_location_detail_modal_id"
_CONTACT_MODAL_KEY = "ips_customer_contact_detail_modal_id"

_CUSTOMERS_CACHE_KEY = "_ips_customers_modal_by_id"
_LOCATIONS_CACHE_KEY = "_ips_customer_locations_modal_by_id"
_CONTACTS_CACHE_KEY = "_ips_customer_contacts_modal_by_id"

_CUSTOMER_TABS = [
    "Overview",
    "Locations",
    "Contacts",
    "Jobs",
    "Estimates",
    "Documents",
    "Notes",
    "Activity",
]

_LOCATION_TABS = [
    "Overview",
    "Contacts",
    "Jobs",
    "Estimates",
    "Documents",
    "Notes",
    "Activity",
]

_CONTACT_TABS = [
    "Overview",
    "Location",
    "Linked Jobs",
    "Linked Estimates",
    "Notes",
    "Activity",
]

SELECTED_CUSTOMER_KEY = "selected_customer_id"
CUSTOMERS_MODE_KEY = "customers_mode"
CUSTOMERS_SELECTED_ID_KEY = "customers_selected_id"
SHOW_CUSTOMER_MODAL_KEY = "show_customer_detail_modal"
_CUSTOMER_LIST_COLS = [4.2, 1.0, 1.1, 1.35, 1.15]
_ALL_CUSTOMER_IDS_KEY = "_ips_customers_visible_ids"
_CUSTOMER_FILTER_SPECS: list[tuple[str, str]] = [
    ("STATUS", "status"),
]
SELECTED_CONTACT_KEY = "selected_contact_id"
SHOW_CONTACT_MODAL_KEY = "show_contact_detail_modal"
_ALL_CONTACT_IDS_KEY = "_ips_contacts_visible_ids"
_CONTACT_COLS = [0.35, 2.0, 2.0, 2.0, 1.8, 3.0, 1.5]
_CONTACT_HEADERS = ["", "NAME", "TITLE", "LOCATION", "ROLE", "EMAIL", "PHONE"]
_ALL_LOCATION_IDS_KEY = "_ips_locations_visible_ids"
_LOCATION_COLS = [0.35, 2.6, 1.4, 1.5, 0.8, 1.4, 0.9, 0.9, 0.9, 1.1]
_LOCATION_HEADERS = [
    "",
    "LOCATION",
    "TYPE",
    "CITY",
    "STATE",
    "PHONE",
    "PRIMARY",
    "BILLING",
    "SHIPPING",
    "STATUS",
]
_LOCATION_STATUS_OPTS = ["Active", "Inactive", "On Hold"]


def _customer_primary_location(row: dict) -> str:
    val = str(row.get("primary_location_name") or row.get("location_name") or "").strip()
    return val or "—"


def _customer_city(row: dict) -> str:
    val = str(row.get("primary_location_city") or row.get("city") or "").strip()
    return val or "—"


def _customer_state(row: dict) -> str:
    val = str(row.get("primary_location_state") or row.get("state") or "").strip()
    return val or "—"


_CUSTOMER_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("status", lambda c: normalize_customer_status(c.get("status"))),
]
_CUSTOMER_BAR_FILTER_FIELDS = ["status"]


def _customer_select_key(customer_id: str) -> str:
    return f"customer_select_{customer_id}"


def _customer_list_name(customer: dict) -> str:
    return (
        str(customer.get("customer_name") or customer.get("company_name") or "").strip()
        or "Unnamed Customer"
    )


def _clear_customer_selection(customer_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_CUSTOMER_KEY] = None
    st.session_state[CUSTOMERS_MODE_KEY] = "list"
    st.session_state[CUSTOMERS_SELECTED_ID_KEY] = None
    st.session_state[SHOW_CUSTOMER_MODAL_KEY] = False
    ids = list(customer_ids or [])
    for cid in ids:
        st.session_state[_customer_select_key(cid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("customer_select_"):
            st.session_state[key] = False


def _open_customer_detail(customer_id: str) -> None:
    cid = str(customer_id or "").strip()
    if not cid:
        return
    st.session_state[CUSTOMERS_SELECTED_ID_KEY] = cid
    st.session_state[CUSTOMERS_MODE_KEY] = "detail"
    st.session_state[SELECTED_CUSTOMER_KEY] = cid
    st.session_state[SHOW_CUSTOMER_MODAL_KEY] = False


def _render_customers_table_column_filters(
    *,
    filter_options: dict[str, list[str]],
) -> None:
    if not _CUSTOMER_FILTER_SPECS:
        return
    st.markdown('<div class="ips-customers-table-filter-toolbar">', unsafe_allow_html=True)
    cols = st.columns(len(_CUSTOMER_FILTER_SPECS), gap="small")
    for col, (label, field) in zip(cols, _CUSTOMER_FILTER_SPECS):
        with col:
            render_table_header_cell(
                label,
                table_key=_CUSTOMERS_TABLE_KEY,
                filter_field=field,
                filter_options=filter_options.get(field, []),
                base_class="ips-customers-filter-toolbar-cell",
            )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_customers_list_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    """Customer list rows with Streamlit open buttons."""
    return _render_custom_customers_table(filtered, filter_options=filter_options)


def _render_customers_table_header_row() -> None:
    head_cols = st.columns(_CUSTOMER_LIST_COLS, gap="small")
    labels = ["CUSTOMER", "CONTACTS", "OPEN JOBS", "OPEN ESTIMATES", "STATUS"]
    aligns = ["left", "right", "right", "right", "center"]
    for col, label, align in zip(head_cols, labels, aligns):
        with col:
            st.markdown(
                f'<div class="ips-customers-native-head-cell ips-customers-native-head-{align}">'
                f"{html.escape(label)}</div>",
                unsafe_allow_html=True,
            )


def _render_custom_customers_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No customers match your filters.")
        st.session_state[_ALL_CUSTOMER_IDS_KEY] = []
        return []

    all_customer_ids = [
        str(c.get("id") or "").strip() for c in filtered if str(c.get("id") or "").strip()
    ]
    st.session_state[_ALL_CUSTOMER_IDS_KEY] = all_customer_ids

    customers_by_id = {
        str(c.get("id") or "").strip(): c
        for c in filtered
        if str(c.get("id") or "").strip()
    }

    with st.container(key="customers_table_wrap"):
        _render_customers_table_column_filters(filter_options=filter_options)
        _render_customers_table_header_row()
        for customer in filtered:
            cid = str(customer.get("id") or "").strip()
            if not cid:
                continue
            row = customers_by_id.get(cid, customer)
            name = _customer_list_name(row)
            contacts = str(row.get("contact_count") or 0)
            open_jobs = str(row.get("open_jobs") or 0)
            open_estimates = str(row.get("open_estimates") or 0)
            status = normalize_customer_status(row.get("status"))
            row_cols = st.columns(_CUSTOMER_LIST_COLS, gap="small")
            with row_cols[0]:
                if st.button(
                    name,
                    key=f"customer_open_{cid}",
                    type="tertiary",
                    use_container_width=True,
                ):
                    _open_customer_detail(cid)
                    st.rerun()
            with row_cols[1]:
                st.markdown(
                    f'<div class="ips-customers-native-cell ips-customers-native-cell-right">'
                    f'<span class="ips-customers-count-cell">{html.escape(contacts)}</span></div>',
                    unsafe_allow_html=True,
                )
            with row_cols[2]:
                st.markdown(
                    f'<div class="ips-customers-native-cell ips-customers-native-cell-right">'
                    f'<span class="ips-customers-count-cell">{html.escape(open_jobs)}</span></div>',
                    unsafe_allow_html=True,
                )
            with row_cols[3]:
                st.markdown(
                    f'<div class="ips-customers-native-cell ips-customers-native-cell-right">'
                    f'<span class="ips-customers-count-cell">{html.escape(open_estimates)}</span></div>',
                    unsafe_allow_html=True,
                )
            with row_cols[4]:
                st.markdown(
                    f'<div class="ips-customers-native-cell ips-customers-native-cell-center">'
                    f"{customer_status_pill_html(status)}</div>",
                    unsafe_allow_html=True,
                )

    return all_customer_ids


def _service_feedback(result: Any, *, success: str) -> tuple[bool, str]:
    try:
        from app.services.repository import user_facing_error
    except ImportError:
        from services.repository import user_facing_error  # type: ignore
    err = user_facing_error(result)
    if err:
        return False, err
    return True, success


def _yes_dash(value: object) -> str:
    return "Yes" if bool(value) else "—"


def _open_counts_by_customer_name(
    jobs: list[dict],
    estimates: list[dict],
) -> tuple[dict[str, int], dict[str, int]]:
    try:
        from app.services.status_maps import (
            is_estimate_open_for_customer_count,
            is_job_open_for_customer_count,
        )
    except ImportError:
        from services.status_maps import (  # type: ignore
            is_estimate_open_for_customer_count,
            is_job_open_for_customer_count,
        )

    open_jobs: dict[str, int] = {}
    open_ests: dict[str, int] = {}
    for job in jobs:
        name = str(job.get("customer") or "").strip().lower()
        if not name:
            continue
        if is_job_open_for_customer_count(job):
            open_jobs[name] = open_jobs.get(name, 0) + 1
    for est in estimates:
        name = str(est.get("customer") or "").strip().lower()
        if not name:
            continue
        if is_estimate_open_for_customer_count(est):
            open_ests[name] = open_ests.get(name, 0) + 1
    return open_jobs, open_ests


def _enrich_list_rows(rows: list[dict]) -> list[dict]:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    with perf_span("customers.enrich_list_rows"):
        jobs = load_jobs()
        estimates = load_estimates()
        open_jobs_by_name, open_ests_by_name = _open_counts_by_customer_name(jobs, estimates)
        out: list[dict] = []
        for row in rows:
            cname = str(row.get("customer_name") or row.get("company_name") or "")
            key = cname.strip().lower()
            enriched = dict(row)
            enriched["open_jobs"] = open_jobs_by_name.get(key, 0)
            enriched["open_estimates"] = open_ests_by_name.get(key, 0)
            out.append(enriched)
        return out


def _apply_customers_search_filter(rows: list[dict], q: str) -> list[dict]:
    query = str(q or "").strip()
    if not query:
        return rows
    ql = query.lower()
    return [
        r
        for r in rows
        if ql in str(r.get("customer_name") or r.get("company_name") or "").lower()
        or ql in str(r.get("customer_number") or "").lower()
        or ql in str(r.get("city") or "").lower()
        or ql in str(r.get("state") or "").lower()
        or ql in str(r.get("main_email") or "").lower()
        or ql in str(r.get("main_phone") or "").lower()
    ]


def _apply_customers_bar_status_filter(rows: list[dict], status: str) -> list[dict]:
    status_val = str(status or "All Statuses").strip()
    if not status_val or status_val == "All Statuses":
        return rows
    return [
        r
        for r in rows
        if normalize_customer_status(r.get("status")) == status_val
        or str(r.get("status") or "").strip() == status_val
    ]


def _filter_customers(
    rows: list[dict],
    *,
    q: str = "",
    bar_status: str = "All Statuses",
) -> list[dict]:
    out = _apply_customers_search_filter(rows, q)
    out = _apply_customers_bar_status_filter(out, bar_status)
    return apply_column_filters(out, _CUSTOMERS_TABLE_KEY, _CUSTOMER_COLUMN_FILTER_SPECS)


def _location_name_map(locations: list[dict]) -> dict[str, dict]:
    return {str(loc.get("id") or "").strip(): loc for loc in locations if str(loc.get("id") or "").strip()}


def _contacts_with_location_names(contacts: list[dict], locations: list[dict]) -> list[dict]:
    loc_by_id = _location_name_map(locations)
    rows: list[dict] = []
    for contact in contacts:
        row = dict(contact)
        lid = str(contact.get("location_id") or contact.get("customer_location_id") or "").strip()
        loc = loc_by_id.get(lid, {})
        loc_name = str(loc.get("location_name") or loc.get("site_name") or "").strip()
        row["location_name"] = loc_name or "—"
        row["display_name"] = _contact_display_name(row)
        row["display_role"] = _normalize_contact_role(row.get("role_type"), row.get("title"))
        row["display_phone"] = _contact_phone(row)
        row["display_status"] = str(row.get("status") or "Active").strip() or "Active"
        rows.append(row)
    return rows


def _contact_display_name(contact: dict) -> str:
    name = str(contact.get("full_name") or contact.get("contact_name") or contact.get("name") or "").strip()
    return name or "Unnamed Contact"


def _contact_phone(contact: dict) -> str:
    for key in ("phone", "mobile"):
        val = str(contact.get(key) or "").strip()
        if val:
            return val
    return "—"


def _normalize_contact_role(raw: object, title: object = None) -> str:
    s = str(raw or "").strip().lower()
    mapping = {
        "primary contact": "Primary",
        "primary": "Primary",
        "project contact": "Project",
        "project": "Project",
        "site contact": "Site",
        "site": "Site",
        "safety contact": "Safety",
        "safety": "Safety",
        "billing contact": "Billing",
        "billing": "Billing",
        "estimating contact": "Estimating",
        "estimating": "Estimating",
        "purchasing contact": "Purchasing",
        "purchasing": "Purchasing",
        "shipping contact": "Shipping",
        "shipping": "Shipping",
        "emergency contact": "Emergency",
        "emergency": "Emergency",
        "other": "Other",
    }
    if s in mapping:
        return mapping[s]
    if s and s not in ("", "—", "-"):
        label = str(raw or "").strip()
        if label.lower().endswith(" contact"):
            return label[: -len(" contact")].strip() or "Other"
        return label
    title_s = str(title or "").strip()
    if title_s and title_s.lower() not in ("—", "-", "other"):
        return title_s
    return "Other"


def _contact_role_pill_html(role: str) -> str:
    cls_map = {
        "Primary": "ips-contact-role-primary",
        "Project": "ips-contact-role-project",
        "Site": "ips-contact-role-site",
        "Safety": "ips-contact-role-safety",
        "Billing": "ips-contact-role-billing",
        "Estimating": "ips-contact-role-estimating",
        "Purchasing": "ips-contact-role-other",
        "Shipping": "ips-contact-role-other",
        "Emergency": "ips-contact-role-safety",
    }
    cls = cls_map.get(role, "ips-contact-role-other")
    return f'<span class="ips-contact-role-pill {cls}">{html.escape(role)}</span>'


def _dedupe_contacts_by_id(contacts: list[dict]) -> list[dict]:
    """One row per contact id so Streamlit checkbox keys stay unique."""
    seen: set[str] = set()
    out: list[dict] = []
    for contact in contacts:
        cid = str(contact.get("id") or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(contact)
    return out


def _contact_select_key(contact_id: str, *, scope: str = "") -> str:
    scope_s = str(scope or "").strip()
    if scope_s:
        return f"contact_select_{scope_s}_{contact_id}"
    return f"contact_select_{contact_id}"


def _customer_contact_select_key(
    customer_id: str,
    contact_id: str,
    *,
    scope: str = "",
) -> str:
    scope_s = str(scope or "").strip()
    if scope_s:
        return f"customer_{customer_id}_contact_select_{scope_s}_{contact_id}"
    return f"customer_{customer_id}_contact_select_{contact_id}"


def _selected_customer_contact_key(customer_id: str) -> str:
    return f"selected_customer_contact_id_{customer_id}"


def _show_customer_contact_detail_key(customer_id: str) -> str:
    return f"show_customer_contact_detail_{customer_id}"


def _selected_customer_location_key(customer_id: str) -> str:
    return f"selected_customer_location_id_{customer_id}"


def _show_customer_location_detail_key(customer_id: str) -> str:
    return f"show_customer_location_detail_{customer_id}"


def _inline_contact_edit_key(contact_id: str) -> str:
    return f"contact_edit_mode_{contact_id}"


def _clear_customer_contact_selection(customer_id: str, contact_ids: list[str] | None = None) -> None:
    st.session_state[_selected_customer_contact_key(customer_id)] = None
    st.session_state[_show_customer_contact_detail_key(customer_id)] = False
    ids = list(contact_ids or [])
    for cid in ids:
        st.session_state[_customer_contact_select_key(customer_id, cid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(f"customer_{customer_id}_contact_select_"):
            st.session_state[key] = False


def _on_customer_contact_checkbox_change(
    customer_id: str,
    contact_id: str,
    all_contact_ids: list[str],
    checkbox_key: str,
) -> None:
    prefix = f"customer_{customer_id}_contact_select_"
    if st.session_state.get(checkbox_key):
        for key in list(st.session_state.keys()):
            if isinstance(key, str) and key.startswith(prefix):
                st.session_state[key] = key == checkbox_key
        st.session_state[_selected_customer_contact_key(customer_id)] = contact_id
        st.session_state[_show_customer_contact_detail_key(customer_id)] = True
        st.session_state[_inline_contact_edit_key(contact_id)] = False
    elif st.session_state.get(_selected_customer_contact_key(customer_id)) == contact_id:
        st.session_state[_selected_customer_contact_key(customer_id)] = None
        st.session_state[_show_customer_contact_detail_key(customer_id)] = False
        st.session_state[_inline_contact_edit_key(contact_id)] = False


def _clear_customer_nested_detail_state(customer_id: str) -> None:
    cid = str(customer_id or "").strip()
    if not cid:
        return
    contact_ids = st.session_state.get(_ALL_CONTACT_IDS_KEY) or []
    _clear_customer_contact_selection(cid, [str(x) for x in contact_ids])
    location_ids = st.session_state.get(_ALL_LOCATION_IDS_KEY) or []
    _clear_customer_location_selection(cid, [str(x) for x in location_ids])
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and (
            key.startswith("contact_edit_mode_") or key.startswith("location_edit_mode_")
        ):
            st.session_state[key] = False


def _clear_contact_selection(contact_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_CONTACT_KEY] = None
    st.session_state[SHOW_CONTACT_MODAL_KEY] = False
    ids = list(contact_ids or [])
    for cid in ids:
        st.session_state[_contact_select_key(cid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("contact_select_"):
            st.session_state[key] = False


def _on_contact_checkbox_change(
    contact_id: str,
    all_contact_ids: list[str],
    checkbox_key: str,
) -> None:
    if st.session_state.get(checkbox_key):
        for key in list(st.session_state.keys()):
            if isinstance(key, str) and key.startswith("contact_select_"):
                st.session_state[key] = key == checkbox_key
        st.session_state[SELECTED_CONTACT_KEY] = contact_id
        st.session_state[SHOW_CONTACT_MODAL_KEY] = True
        cache = st.session_state.get(_CONTACTS_CACHE_KEY) or {}
        contact = cache.get(contact_id) if isinstance(cache, dict) else None
        _open_contact_detail_modal(contact_id, contact if isinstance(contact, dict) else None)
    elif st.session_state.get(SELECTED_CONTACT_KEY) == contact_id:
        st.session_state[SELECTED_CONTACT_KEY] = None
        st.session_state[SHOW_CONTACT_MODAL_KEY] = False


def _contacts_table_wrap_key(*, customer_id: str = "", location_id: str = "") -> str:
    if location_id:
        return f"contacts_table_wrap_loc_{location_id}"
    if customer_id:
        return f"contacts_table_wrap_cust_{customer_id}"
    return "contacts_table_wrap_main"


def _render_custom_contacts_table(
    contacts: list[dict],
    *,
    customer_id: str | None = None,
    location_id: str | None = None,
    inline: bool = False,
    table_wrap_key: str | None = None,
) -> list[str]:
    if not contacts:
        st.session_state[_ALL_CONTACT_IDS_KEY] = []
        return []

    contacts = _dedupe_contacts_by_id(contacts)

    all_contact_ids = [
        str(c.get("id") or "").strip() for c in contacts if str(c.get("id") or "").strip()
    ]
    st.session_state[_ALL_CONTACT_IDS_KEY] = all_contact_ids

    wrap_key = table_wrap_key or _contacts_table_wrap_key(
        customer_id=str(customer_id or ""),
        location_id=str(location_id or ""),
    )
    scope = wrap_key
    with st.container(key=wrap_key):
        st.markdown('<div class="ips-contacts-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_CONTACT_COLS, gap="small", vertical_alignment="center")
        for col, label in zip(header_cols, _CONTACT_HEADERS):
            with col:
                st.markdown(
                    f'<div class="ips-contacts-header-row ips-contacts-cell">'
                    f"{html.escape(label)}</div>",
                    unsafe_allow_html=True,
                )

        for contact in contacts:
            ct_id = str(contact.get("id") or "").strip()
            if not ct_id:
                continue

            name = _contact_display_name(contact)
            title = str(contact.get("title") or "—").strip() or "—"
            location = str(contact.get("location_name") or "—").strip() or "—"
            role = _normalize_contact_role(contact.get("role_type"), contact.get("title"))
            email = str(contact.get("email") or "—").strip() or "—"
            phone = _contact_phone(contact)

            cols = st.columns(_CONTACT_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                checkbox_key = (
                    _customer_contact_select_key(customer_id, ct_id, scope=scope)
                    if inline and customer_id
                    else _contact_select_key(ct_id, scope=scope)
                )
                checkbox_args = (
                    (customer_id, ct_id, all_contact_ids, checkbox_key)
                    if inline and customer_id
                    else (ct_id, all_contact_ids, checkbox_key)
                )
                checkbox_handler = (
                    _on_customer_contact_checkbox_change
                    if inline and customer_id
                    else _on_contact_checkbox_change
                )
                st.checkbox(
                    "",
                    key=checkbox_key,
                    label_visibility="collapsed",
                    on_change=checkbox_handler,
                    args=checkbox_args,
                )

            with cols[1]:
                st.markdown(
                    f'<div class="ips-contacts-name">{html.escape(name)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<div class="ips-contacts-cell">{html.escape(title)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-contacts-cell">{html.escape(location)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(_contact_role_pill_html(role), unsafe_allow_html=True)

            with cols[5]:
                st.markdown(
                    f'<div class="ips-contacts-email ips-contacts-cell">{html.escape(email)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(
                    f'<div class="ips-contacts-muted ips-contacts-cell">{html.escape(phone)}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    return all_contact_ids


def _render_contacts_table_block(
    contacts: list[dict],
    *,
    empty_caption: str,
    customer: dict | None = None,
    location_id: str = "",
    inline: bool = False,
    table_wrap_key: str | None = None,
) -> None:
    if not contacts:
        st.caption(empty_caption)
        return
    build_modal_cache(contacts, cache_key=_CONTACTS_CACHE_KEY)
    st.caption(f"{len(contacts)} contact(s)")
    customer_id = str((customer or {}).get("id") or "").strip()
    loc_id = str(location_id or "").strip()
    _render_custom_contacts_table(
        contacts,
        customer_id=customer_id or None,
        location_id=loc_id or None,
        inline=inline and bool(customer_id),
        table_wrap_key=table_wrap_key,
    )

    if inline and customer_id:
        selected_contact_id = st.session_state.get(_selected_customer_contact_key(customer_id))
        show_contact_detail = st.session_state.get(_show_customer_contact_detail_key(customer_id), False)
        if selected_contact_id and show_contact_detail:
            selected_contact = next(
                (c for c in contacts if str(c.get("id")) == str(selected_contact_id)),
                None,
            )
            if selected_contact:
                locations = get_customer_locations(customer_id)
                _render_contact_inline_detail(selected_contact, customer, locations)
        return

    if st.session_state.get(SELECTED_CONTACT_KEY) and st.session_state.get(SHOW_CONTACT_MODAL_KEY):
        _show_contact_detail_modal()



def _clear_customers_detail_modal() -> None:
    customer_ids = st.session_state.get(_ALL_CUSTOMER_IDS_KEY) or []
    active_customer_id = str(
        st.session_state.get(SELECTED_CUSTOMER_KEY)
        or st.session_state.get(_CUSTOMERS_MODAL_KEY)
        or ""
    ).strip()
    if active_customer_id:
        _clear_customer_nested_detail_state(active_customer_id)
    _clear_customer_selection([str(cid) for cid in customer_ids])
    clear_record_modal(
        table_key=_CUSTOMERS_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_CUSTOMERS_MODAL_KEY,
        module=_MOD,
    )


def _clear_location_detail_modal() -> None:
    clear_record_modal(
        table_key=_LOCATIONS_TABLE_KEY,
        session_select_key=_LOC_SEL,
        modal_key=_LOCATION_MODAL_KEY,
        module=_LOC_MOD,
    )


def _clear_contact_detail_modal() -> None:
    contact_ids = st.session_state.get(_ALL_CONTACT_IDS_KEY) or []
    _clear_contact_selection([str(cid) for cid in contact_ids])
    clear_edit_modes(_CT_MOD)
    clear_record_modal(
        table_key=_CONTACTS_TABLE_KEY,
        session_select_key=_CT_SEL,
        modal_key=_CONTACT_MODAL_KEY,
        module=_CT_MOD,
    )


def _open_customers_detail_modal(customer_id: str, customer: dict | None = None) -> None:
    open_record_modal(
        customer_id,
        customer,
        session_select_key=_SEL,
        modal_key=_CUSTOMERS_MODAL_KEY,
        module=_MOD,
        id_fields=("id", "customer_name"),
    )


def _open_location_detail_modal(location_id: str, location: dict | None = None) -> None:
    open_record_modal(
        location_id,
        location,
        session_select_key=_LOC_SEL,
        modal_key=_LOCATION_MODAL_KEY,
        module=_LOC_MOD,
        id_fields=("id", "location_name", "site_name"),
    )


def _open_contact_detail_modal(contact_id: str, contact: dict | None = None) -> None:
    open_record_modal(
        contact_id,
        contact,
        session_select_key=_CT_SEL,
        modal_key=_CONTACT_MODAL_KEY,
        module=_CT_MOD,
        id_fields=("id", "full_name", "contact_name"),
    )


def _list_display_cell(field: str, row: dict) -> str:
    if field == "status":
        return safe_value(row.get("status"))
    if field in ("is_primary", "is_billing", "is_shipping"):
        return _yes_dash(row.get(field))
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def _location_label(loc: dict) -> str:
    name = str(loc.get("location_name") or loc.get("site_name") or "—")
    city = str(loc.get("city") or "").strip()
    state = str(loc.get("state") or "").strip()
    tail = ", ".join(part for part in (city, state) if part)
    return f"{name} — {tail}" if tail else name


def _location_select_key(customer_id: str, location_id: str) -> str:
    return f"customer_{customer_id}_location_select_{location_id}"


def _inline_location_edit_key(location_id: str) -> str:
    return f"location_edit_mode_{location_id}"


def _location_display_name(location: dict) -> str:
    return str(
        location.get("location_name") or location.get("site_name") or location.get("name") or "Unnamed Location"
    ).strip()


def _location_display_type(location: dict) -> str:
    val = str(location.get("location_type") or location.get("type") or "Other").strip()
    return val or "Other"


def _location_display_status(location: dict) -> str:
    val = str(location.get("status") or "Active").strip()
    return val or "Active"


def _format_phone(value: object) -> str:
    raw = str(value or "").strip()
    if not raw or raw in {"—", "None", "null", "-"}:
        return "—"
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return raw


def _location_status_pill_html(status: str) -> str:
    key = str(status or "Active").strip().lower().replace("_", " ")
    cls_map = {
        "active": "ips-location-status-active",
        "inactive": "ips-location-status-inactive",
        "on hold": "ips-location-status-on-hold",
    }
    label = str(status or "Active").strip() or "Active"
    cls = cls_map.get(key, "ips-location-status-active")
    return f'<span class="ips-location-pill {cls}">{html.escape(label)}</span>'


def _location_flag_html(value: object) -> str:
    if value in (True, "true", "True", 1, "Yes", "yes", "Y"):
        return '<span class="ips-location-pill ips-location-flag-yes">Yes</span>'
    return '<span class="ips-location-pill ips-location-flag-no">—</span>'


def _clear_customer_location_selection(
    customer_id: str,
    location_ids: list[str] | None = None,
) -> None:
    cid = str(customer_id or "").strip()
    st.session_state[_selected_customer_location_key(cid)] = None
    st.session_state[_show_customer_location_detail_key(cid)] = False
    ids = list(location_ids or [])
    for lid in ids:
        st.session_state[_location_select_key(cid, lid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(f"customer_{cid}_location_select_"):
            st.session_state[key] = False


def _on_customer_location_checkbox_change(
    customer_id: str,
    location_id: str,
    all_location_ids: list[str],
) -> None:
    key = _location_select_key(customer_id, location_id)
    if st.session_state.get(key):
        for lid in all_location_ids:
            if lid != location_id:
                st.session_state[_location_select_key(customer_id, lid)] = False
        st.session_state[_selected_customer_location_key(customer_id)] = location_id
        st.session_state[_show_customer_location_detail_key(customer_id)] = True
        st.session_state[_inline_location_edit_key(location_id)] = False
    elif st.session_state.get(_selected_customer_location_key(customer_id)) == location_id:
        st.session_state[_selected_customer_location_key(customer_id)] = None
        st.session_state[_show_customer_location_detail_key(customer_id)] = False
        st.session_state[_inline_location_edit_key(location_id)] = False


def _jobs_table(
    jobs: list[dict],
    *,
    session_key: str,
    location_id: str = "",
) -> None:
    if location_id:
        jobs = [
            j
            for j in jobs
            if str(j.get("customer_location_id") or j.get("location_id") or "").strip() == location_id
            or str(j.get("location") or "").strip() == location_id
        ]
    if not jobs:
        st.caption("No jobs linked yet.")
        return

    columns: list[tuple[str, str]] = [
        ("job_number", "JOB #"),
        ("job_name", "PROJECT"),
    ]
    if any(j.get("location") or j.get("customer_location") or j.get("site_name") for j in jobs):
        columns.append(("location", "LOCATION"))
    if any(j.get("contact_name") or j.get("customer_contact") for j in jobs):
        columns.append(("contact_name", "CONTACT"))
    columns.extend([("status", "STATUS"), ("supervisor", "SUPERVISOR")])

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "job_number":
            return (
                f'<span style="color:#2563eb;font-weight:600">'
                f'{html.escape(str(row.get("job_number") or ""))}</span>'
            )
        if field == "location":
            val = row.get("location") or row.get("customer_location") or row.get("site_name")
            return html.escape(str(val or "—"))
        if field == "contact_name":
            val = row.get("contact_name") or row.get("customer_contact")
            return html.escape(str(val or "—"))
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        jobs,
        columns,
        row_id_key="id",
        selected_id=None,
        session_select_key=session_key,
        hide_select=True,
        cell_renderer=_cell,
    )


def _estimates_table(
    estimates: list[dict],
    *,
    session_key: str,
    location_id: str = "",
) -> None:
    if location_id:
        estimates = [
            e
            for e in estimates
            if str(e.get("customer_location_id") or e.get("location_id") or "").strip() == location_id
            or str(e.get("location") or "").strip() == location_id
        ]
    if not estimates:
        st.caption("No estimates for this scope yet.")
        return

    columns: list[tuple[str, str]] = [
        ("estimate_number", "ESTIMATE #"),
        ("project_name", "PROJECT"),
    ]
    if any(e.get("location") or e.get("customer_location") or e.get("site_name") for e in estimates):
        columns.append(("location", "LOCATION"))
    if any(e.get("contact_name") or e.get("customer_contact") for e in estimates):
        columns.append(("contact_name", "CONTACT"))
    columns.extend([("status", "STATUS"), ("total", "TOTAL")])

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "location":
            val = row.get("location") or row.get("customer_location") or row.get("site_name")
            return html.escape(str(val or "—"))
        if field == "contact_name":
            val = row.get("contact_name") or row.get("customer_contact")
            return html.escape(str(val or "—"))
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        estimates,
        columns,
        row_id_key="id",
        selected_id=None,
        session_select_key=session_key,
        hide_select=True,
        cell_renderer=_cell,
    )


# --- Customer modal ---


def _seed_customer_edit_form(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    rk = record_session_key(customer, "id", "customer_name")
    st.session_state[f"cust_edit_company_{rk}"] = str(customer.get("company_name") or customer.get("customer_name") or "")
    st.session_state[f"cust_edit_number_{rk}"] = str(customer.get("customer_number") or "")
    st.session_state[f"cust_edit_website_{rk}"] = str(customer.get("website") or "")
    st.session_state[f"cust_edit_main_phone_{rk}"] = str(customer.get("main_phone") or "")
    st.session_state[f"cust_edit_main_email_{rk}"] = str(customer.get("main_email") or "")
    st.session_state[f"cust_edit_billing_email_{rk}"] = str(customer.get("billing_email") or "")
    st.session_state[f"cust_edit_status_{rk}"] = str(customer.get("status") or "Active")
    st.session_state[f"cust_edit_notes_{rk}"] = str(customer.get("notes") or "")
    st.session_state[f"cust_edit_addr_{rk}"] = str(customer.get("address") or "")
    st.session_state[f"cust_edit_city_{rk}"] = str(customer.get("city") or "")
    st.session_state[f"cust_edit_state_{rk}"] = str(customer.get("state") or "")
    st.session_state[f"cust_edit_zip_{rk}"] = str(customer.get("zip") or "")


def _set_customer_edit_mode(customer: dict) -> None:
    rk = record_session_key(customer, "id", "customer_name")
    set_edit_mode(_MOD, rk)
    _seed_customer_edit_form(customer)


def _render_customer_edit_form(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    rk = record_session_key(customer, "id", "customer_name")
    if f"cust_edit_company_{rk}" not in st.session_state:
        _seed_customer_edit_form(customer)

    render_edit_form_header("Edit Customer")
    if is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Company name", key=f"cust_edit_company_{rk}")
        st.text_input("Customer #", key=f"cust_edit_number_{rk}")
        st.text_input("Website", key=f"cust_edit_website_{rk}")
        st.text_input("Main phone", key=f"cust_edit_main_phone_{rk}")
    with ec2:
        st.text_input("Main email", key=f"cust_edit_main_email_{rk}")
        st.text_input("Billing email", key=f"cust_edit_billing_email_{rk}")
        st.selectbox("Status", ["Active", "Inactive"], key=f"cust_edit_status_{rk}")
    st.text_area("Notes", key=f"cust_edit_notes_{rk}", height=90)

    with st.expander("Legacy address (optional)", expanded=False):
        lc1, lc2 = st.columns(2)
        with lc1:
            st.text_input("Address", key=f"cust_edit_addr_{rk}")
            st.text_input("City", key=f"cust_edit_city_{rk}")
        with lc2:
            st.text_input("State", key=f"cust_edit_state_{rk}")
            st.text_input("ZIP", key=f"cust_edit_zip_{rk}")

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"cust_edit_cancel_{rk}",
        save_key=f"cust_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        payload = {
            "company_name": st.session_state.get(f"cust_edit_company_{rk}"),
            "customer_name": st.session_state.get(f"cust_edit_company_{rk}"),
            "customer_number": st.session_state.get(f"cust_edit_number_{rk}"),
            "website": st.session_state.get(f"cust_edit_website_{rk}"),
            "main_phone": st.session_state.get(f"cust_edit_main_phone_{rk}"),
            "main_email": st.session_state.get(f"cust_edit_main_email_{rk}"),
            "billing_email": st.session_state.get(f"cust_edit_billing_email_{rk}"),
            "status": st.session_state.get(f"cust_edit_status_{rk}"),
            "notes": st.session_state.get(f"cust_edit_notes_{rk}"),
            "address": st.session_state.get(f"cust_edit_addr_{rk}"),
            "city": st.session_state.get(f"cust_edit_city_{rk}"),
            "state": st.session_state.get(f"cust_edit_state_{rk}"),
            "zip": st.session_state.get(f"cust_edit_zip_{rk}"),
        }
        ok, msg = _service_feedback(update_customer(cid, payload), success="Customer saved.")
        if ok:
            set_view_mode(_MOD, rk)
            st.success(msg)
            st.rerun()
        st.error(msg or "Could not save customer.")


def _render_add_location_form(customer: dict, *, demo: bool) -> None:
    cid = str(customer.get("id") or "")
    pk = f"cust_new_loc_{cid}"
    if demo:
        st.caption("Add locations after saving this customer to Supabase.")
        return

    add_l, _ = st.columns([1, 3])
    with add_l:
        if st.button("+ Add Location", key=f"{pk}_open_btn", use_container_width=True):
            st.session_state[f"{pk}_open"] = True
            st.rerun()

    if not st.session_state.get(f"{pk}_open"):
        return

    st.markdown('<div class="ips-locations-add-form">', unsafe_allow_html=True)
    lc1, lc2 = st.columns(2)
    with lc1:
        st.text_input("Location name", key=f"{pk}_name")
        st.selectbox("Type", LOCATION_TYPES, key=f"{pk}_type")
        st.text_input("Address line 1", key=f"{pk}_addr1")
        st.text_input("Address line 2", key=f"{pk}_addr2")
        st.text_input("City", key=f"{pk}_city")
    with lc2:
        st.text_input("State", key=f"{pk}_state")
        st.text_input("ZIP", key=f"{pk}_zip")
        st.text_input("Phone", key=f"{pk}_phone")
        st.text_input("Email", key=f"{pk}_email")
        st.selectbox("Status", _LOCATION_STATUS_OPTS, index=0, key=f"{pk}_status")
    flags = st.columns(3)
    with flags[0]:
        st.checkbox("Primary", key=f"{pk}_primary")
    with flags[1]:
        st.checkbox("Billing", key=f"{pk}_billing")
    with flags[2]:
        st.checkbox("Shipping", key=f"{pk}_shipping")
    st.text_area("Notes", key=f"{pk}_notes", height=70)
    sb1, sb2 = st.columns(2)
    with sb1:
        save = st.button("Save location", key=f"{pk}_save", type="primary", use_container_width=True)
    with sb2:
        if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
            st.session_state.pop(f"{pk}_open", None)
            st.rerun()
    if save:
        payload = {
            "location_name": st.session_state.get(f"{pk}_name"),
            "location_type": st.session_state.get(f"{pk}_type"),
            "address_line_1": st.session_state.get(f"{pk}_addr1"),
            "address_line_2": st.session_state.get(f"{pk}_addr2"),
            "city": st.session_state.get(f"{pk}_city"),
            "state": st.session_state.get(f"{pk}_state"),
            "zip": st.session_state.get(f"{pk}_zip"),
            "phone": st.session_state.get(f"{pk}_phone"),
            "email": st.session_state.get(f"{pk}_email"),
            "is_primary": st.session_state.get(f"{pk}_primary"),
            "is_billing": st.session_state.get(f"{pk}_billing"),
            "is_shipping": st.session_state.get(f"{pk}_shipping"),
            "status": st.session_state.get(f"{pk}_status"),
            "notes": st.session_state.get(f"{pk}_notes"),
        }
        ok, msg = _service_feedback(
            create_customer_location(cid, payload),
            success="Location added.",
        )
        if apply_persist_feedback(ok, msg, clear_keys=(f"{pk}_open",)):
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_custom_locations_table(locations: list[dict], *, customer_id: str) -> list[str]:
    if not locations:
        st.session_state[_ALL_LOCATION_IDS_KEY] = []
        return []

    all_location_ids = [
        str(loc.get("id") or "").strip() for loc in locations if str(loc.get("id") or "").strip()
    ]
    st.session_state[_ALL_LOCATION_IDS_KEY] = all_location_ids

    with st.container(key="locations_table_wrap"):
        st.markdown('<div class="ips-locations-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_LOCATION_COLS, gap="small", vertical_alignment="center")
        for col, label in zip(header_cols, _LOCATION_HEADERS):
            with col:
                st.markdown(
                    f'<div class="ips-locations-header-row ips-locations-cell">'
                    f"{html.escape(label)}</div>",
                    unsafe_allow_html=True,
                )

        for location in locations:
            lid = str(location.get("id") or "").strip()
            if not lid:
                continue

            name = _location_display_name(location)
            loc_type = _location_display_type(location)
            city = str(location.get("city") or "—").strip() or "—"
            state = str(location.get("state") or "—").strip() or "—"
            phone = _format_phone(location.get("phone"))
            status = _location_display_status(location)

            cols = st.columns(_LOCATION_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_location_select_key(customer_id, lid),
                    label_visibility="collapsed",
                    on_change=_on_customer_location_checkbox_change,
                    args=(customer_id, lid, all_location_ids),
                )

            with cols[1]:
                st.markdown(
                    f'<div class="ips-locations-name">{html.escape(name)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<div class="ips-locations-cell">{html.escape(loc_type)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-locations-cell">{html.escape(city)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    f'<div class="ips-locations-cell">{html.escape(state)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(
                    f'<div class="ips-locations-muted ips-locations-cell">{html.escape(phone)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(_location_flag_html(location.get("is_primary")), unsafe_allow_html=True)

            with cols[7]:
                st.markdown(_location_flag_html(location.get("is_billing")), unsafe_allow_html=True)

            with cols[8]:
                st.markdown(_location_flag_html(location.get("is_shipping")), unsafe_allow_html=True)

            with cols[9]:
                st.markdown(_location_status_pill_html(status), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    return all_location_ids


def _render_customer_locations_tab(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    demo = is_demo_id(cid)
    locations = get_customer_locations(cid)
    _render_add_location_form(customer, demo=demo)

    if not locations:
        st.caption("No locations on file for this customer.")
        return

    build_modal_cache(locations, cache_key=_LOCATIONS_CACHE_KEY)
    st.caption(f"{len(locations)} location(s)")
    _render_custom_locations_table(locations, customer_id=cid)

    selected_location_id = st.session_state.get(_selected_customer_location_key(cid))
    if st.session_state.get(_show_customer_location_detail_key(cid)) and selected_location_id:
        selected_location = next(
            (loc for loc in locations if str(loc.get("id")) == str(selected_location_id)),
            None,
        )
        if selected_location:
            _render_location_inline_detail(selected_location, customer)


def _render_add_contact_form(customer: dict, *, locations: list[dict], demo: bool) -> None:
    cid = str(customer.get("id") or "")
    pk = f"cust_new_ct_{cid}"
    if demo:
        st.caption("Add contacts after saving this customer to Supabase.")
        return

    loc_opts = [(_location_label(loc), str(loc.get("id") or "")) for loc in locations if str(loc.get("id") or "")]
    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        if not loc_opts:
            st.info("Add a customer location before creating a new contact.")
        elif not st.session_state.get(f"{pk}_open"):
            st.caption("Use Add Contact to create a contact tied to a customer location.")
    with hdr_r:
        if loc_opts and st.button("+ Add Contact", key=f"{pk}_open_btn", use_container_width=True):
            st.session_state[f"{pk}_open"] = True
            st.rerun()

    if not loc_opts:
        return

    if not st.session_state.get(f"{pk}_open"):
        return

    with st.expander("Add Contact", expanded=True):
        labels = [label for label, _ in loc_opts]
        ids = [lid for _, lid in loc_opts]
        if f"{pk}_loc" not in st.session_state:
            st.session_state[f"{pk}_loc"] = 0
        loc_idx = st.selectbox(
            "Location",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key=f"{pk}_loc",
        )
        loc_id = ids[int(loc_idx)]

        nc1, nc2 = st.columns(2)
        with nc1:
            st.text_input("Full name", key=f"{pk}_name")
            st.text_input("Title", key=f"{pk}_title")
            st.selectbox("Role", CONTACT_ROLE_TYPES, key=f"{pk}_role")
            st.text_input("Email", key=f"{pk}_email")
        with nc2:
            st.text_input("Phone", key=f"{pk}_phone")
            st.text_input("Mobile", key=f"{pk}_mobile")
            st.selectbox("Status", ["Active", "Inactive"], index=0, key=f"{pk}_status")
            st.checkbox("Primary for location", key=f"{pk}_primary")
        st.text_area("Notes", key=f"{pk}_notes", height=70)
        sb1, sb2 = st.columns(2)
        with sb1:
            save = st.button("Save contact", key=f"{pk}_save", type="primary", use_container_width=True)
        with sb2:
            if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
                st.session_state.pop(f"{pk}_open", None)
                st.rerun()
        if save:
            payload = {
                "full_name": st.session_state.get(f"{pk}_name"),
                "contact_name": st.session_state.get(f"{pk}_name"),
                "title": st.session_state.get(f"{pk}_title"),
                "role_type": st.session_state.get(f"{pk}_role"),
                "email": st.session_state.get(f"{pk}_email"),
                "phone": st.session_state.get(f"{pk}_phone"),
                "mobile": st.session_state.get(f"{pk}_mobile"),
                "status": st.session_state.get(f"{pk}_status"),
                "is_primary": st.session_state.get(f"{pk}_primary"),
                "notes": st.session_state.get(f"{pk}_notes"),
            }
            ok, msg = _service_feedback(
                create_customer_contact(cid, loc_id, payload),
                success="Contact added.",
            )
            if apply_persist_feedback(ok, msg, clear_keys=(f"{pk}_open",)):
                st.rerun()


def _inline_meta_grid(items: list[tuple[str, str]]) -> None:
    if not items:
        return
    st.markdown('<div class="ips-inline-meta-grid">', unsafe_allow_html=True)
    cols = st.columns(min(len(items), 4))
    for idx, (label, value) in enumerate(items):
        with cols[idx % len(cols)]:
            val = safe_value(value)
            st.markdown(
                f'<div class="ips-inline-meta-card">'
                f'<div class="ips-inline-meta-label">{html.escape(label)}</div>'
                f'<div class="ips-inline-meta-value">{html.escape(val)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_contact_inline_edit_form(
    contact: dict,
    *,
    customer: dict | None,
    locations: list[dict],
) -> None:
    ct_id = str(contact.get("id") or "")
    cid = str(contact.get("customer_id") or (customer or {}).get("id") or "")
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    if f"ct_edit_name_{rk}" not in st.session_state:
        _seed_contact_edit_form(contact)

    render_edit_form_header("Edit Contact")
    if is_demo_id(ct_id) or is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    loc_opts = [(_location_label(loc), str(loc.get("id") or "")) for loc in locations if str(loc.get("id") or "")]
    labels = [label for label, _ in loc_opts]
    ids = [lid for _, lid in loc_opts]
    cur_loc = str(contact.get("location_id") or contact.get("customer_location_id") or "")
    if f"ct_edit_loc_{rk}" not in st.session_state and cur_loc in ids:
        st.session_state[f"ct_edit_loc_{rk}"] = ids.index(cur_loc)
    elif f"ct_edit_loc_{rk}" not in st.session_state and ids:
        st.session_state[f"ct_edit_loc_{rk}"] = 0

    if labels:
        loc_idx = st.selectbox(
            "Location",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key=f"ct_edit_loc_{rk}",
        )
        loc_id = ids[int(loc_idx)]
    else:
        st.caption("No locations available.")
        loc_id = cur_loc

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Full name", key=f"ct_edit_name_{rk}")
        st.text_input("Title", key=f"ct_edit_title_{rk}")
        st.selectbox("Role", CONTACT_ROLE_TYPES, key=f"ct_edit_role_{rk}")
    with ec2:
        st.text_input("Email", key=f"ct_edit_email_{rk}")
        st.text_input("Phone", key=f"ct_edit_phone_{rk}")
        st.text_input("Mobile", key=f"ct_edit_mobile_{rk}")
        st.selectbox("Status", ["Active", "Inactive"], key=f"ct_edit_status_{rk}")
        st.checkbox("Primary for location", key=f"ct_edit_primary_{rk}")
    st.text_area("Notes", key=f"ct_edit_notes_{rk}", height=90)

    cancelled, saved = render_save_cancel_actions(
        module=_CT_MOD,
        record_key=rk,
        cancel_key=f"inline_ct_edit_cancel_{rk}",
        save_key=f"inline_ct_edit_save_{rk}",
    )
    if cancelled:
        st.session_state[_inline_contact_edit_key(ct_id)] = False
        st.rerun()
    if saved and loc_id:
        payload = {
            "customer_id": cid,
            "location_id": loc_id,
            "customer_location_id": loc_id,
            "full_name": st.session_state.get(f"ct_edit_name_{rk}"),
            "contact_name": st.session_state.get(f"ct_edit_name_{rk}"),
            "title": st.session_state.get(f"ct_edit_title_{rk}"),
            "role_type": st.session_state.get(f"ct_edit_role_{rk}"),
            "email": st.session_state.get(f"ct_edit_email_{rk}"),
            "phone": st.session_state.get(f"ct_edit_phone_{rk}"),
            "mobile": st.session_state.get(f"ct_edit_mobile_{rk}"),
            "is_primary": st.session_state.get(f"ct_edit_primary_{rk}"),
            "status": st.session_state.get(f"ct_edit_status_{rk}"),
            "notes": st.session_state.get(f"ct_edit_notes_{rk}"),
        }
        ok, msg = _service_feedback(update_customer_contact(ct_id, payload), success="Contact saved.")
        if ok:
            st.session_state[_inline_contact_edit_key(ct_id)] = False
            st.success(msg)
            st.rerun()
        st.error(msg or "Could not save contact.")


def _render_contact_inline_detail(
    contact: dict,
    customer: dict | None = None,
    locations: list[dict] | None = None,
) -> None:
    ct_id = str(contact.get("id") or "")
    cid = str(contact.get("customer_id") or (customer or {}).get("id") or "")
    cname = str((customer or {}).get("customer_name") or (customer or {}).get("company_name") or "")
    title = safe_value(contact.get("full_name") or contact.get("contact_name"))
    status = safe_value(contact.get("status"))
    role = _normalize_contact_role(contact.get("role_type"), contact.get("title"))
    loc_name = safe_value(contact.get("location_name"))
    lid = str(contact.get("location_id") or contact.get("customer_location_id") or "")
    location = next((loc for loc in (locations or []) if str(loc.get("id") or "") == lid), None)
    if location:
        loc_name = safe_value(location.get("location_name") or location.get("site_name"))
    editing = bool(st.session_state.get(_inline_contact_edit_key(ct_id)))

    with st.container(key=f"inline_contact_detail_{ct_id}"):
        st.markdown('<div class="ips-inline-detail-card">', unsafe_allow_html=True)
        header_l, header_r = st.columns([4, 1], vertical_alignment="center")
        with header_l:
            subtitle = f"{cname} · {loc_name}" if cname and loc_name != "—" else (cname or loc_name or "Contact")
            st.markdown(
                f'<div class="ips-inline-detail-header">'
                f'<div class="ips-inline-detail-title">{html.escape(title)}</div>'
                f'<div class="ips-inline-detail-subtitle">{html.escape(subtitle)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(modal_status_pill_html(status), unsafe_allow_html=True)
        with header_r:
            if not editing and st.button("Edit", key=f"inline_ct_edit_btn_{ct_id}", use_container_width=True):
                st.session_state[_inline_contact_edit_key(ct_id)] = True
                _seed_contact_edit_form(contact)
                st.rerun()

        if editing:
            _render_contact_inline_edit_form(
                contact,
                customer=customer,
                locations=locations or get_customer_locations(cid),
            )
        else:
            _inline_meta_grid(
                [
                    ("Title", safe_value(contact.get("title"))),
                    ("Role", role),
                    ("Location", loc_name),
                    ("Email", safe_value(contact.get("email"))),
                    ("Phone", safe_value(contact.get("phone"))),
                    ("Mobile", safe_value(contact.get("mobile"))),
                ]
            )

            if location:
                loc_html = (
                    f'<div class="ips-detail-grid">'
                    f"{detail_field_html('Location', location.get('location_name') or location.get('site_name'))}"
                    f"{detail_field_html('Type', location.get('location_type'))}"
                    f"{detail_field_html('City', location.get('city'))}"
                    f"{detail_field_html('State', location.get('state'))}"
                    f"{detail_field_html('Phone', location.get('phone'))}"
                    f"</div>"
                )
                st.markdown(dialog_card_html("Location", loc_html), unsafe_allow_html=True)

            jobs = jobs_for_customer(cname)
            contact_name = str(contact.get("full_name") or contact.get("contact_name") or "").strip().lower()
            if contact_name:
                jobs = [
                    j
                    for j in jobs
                    if str(j.get("contact_name") or j.get("customer_contact") or "").strip().lower()
                    == contact_name
                    or str(j.get("customer_contact_id") or j.get("contact_id") or "") == ct_id
                ]
            st.markdown("**Linked Jobs**")
            _jobs_table(jobs, session_key=f"_inline_ct_jobs_{ct_id}")

            ests = estimates_for_customer(cname)
            if contact_name:
                ests = [
                    e
                    for e in ests
                    if str(e.get("contact_name") or e.get("customer_contact") or "").strip().lower()
                    == contact_name
                    or str(e.get("customer_contact_id") or e.get("contact_id") or "") == ct_id
                ]
            st.markdown("**Linked Estimates**")
            _estimates_table(ests, session_key=f"_inline_ct_est_{ct_id}")

            notes_text = safe_value(contact.get("notes"), "No notes entered.")
            notes_html = (
                f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
                f"{html.escape(notes_text)}"
                f"</p>"
            )
            st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)
            placeholder_html("Contact activity history will appear here when connected to Supabase.")

        st.markdown("</div>", unsafe_allow_html=True)


def _render_location_inline_detail(location: dict, customer: dict | None = None) -> None:
    lid = str(location.get("id") or "")
    cid = str(location.get("customer_id") or (customer or {}).get("id") or "")
    title = safe_value(location.get("location_name") or location.get("site_name"))
    status = safe_value(location.get("status"))
    cname = safe_value((customer or {}).get("customer_name") or (customer or {}).get("company_name"))
    editing = bool(st.session_state.get(_inline_location_edit_key(lid)))

    with st.container(key=f"inline_location_detail_{lid}"):
        st.markdown('<div class="ips-inline-detail-card">', unsafe_allow_html=True)
        header_l, header_r = st.columns([4, 1], vertical_alignment="center")
        with header_l:
            st.markdown(
                f'<div class="ips-inline-detail-header">'
                f'<div class="ips-inline-detail-title">{html.escape(title)}</div>'
                f'<div class="ips-inline-detail-subtitle">{html.escape(cname)} · Location</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(_location_status_pill_html(status), unsafe_allow_html=True)
        with header_r:
            if not editing and st.button(
                "Edit",
                key=f"inline_loc_edit_btn_{lid}",
                use_container_width=True,
            ):
                st.session_state[_inline_location_edit_key(lid)] = True
                _seed_location_edit_form(location)
                st.rerun()

        if editing:
            _render_location_inline_edit_form(location, customer=customer)
        else:
            city_state = ", ".join(
                part
                for part in (str(location.get("city") or "").strip(), str(location.get("state") or "").strip())
                if part
            )
            _inline_meta_grid(
                [
                    ("Type", safe_value(location.get("location_type"))),
                    ("City / State", city_state or "—"),
                    ("Phone", _format_phone(location.get("phone"))),
                    ("Primary", _yes_dash(location.get("is_primary"))),
                    ("Billing", _yes_dash(location.get("is_billing"))),
                    ("Shipping", _yes_dash(location.get("is_shipping"))),
                ]
            )
            _render_location_detail_tabs(location, customer, inline_contacts=True)

        st.markdown("</div>", unsafe_allow_html=True)


def _render_customer_contacts_tab(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    demo = is_demo_id(cid)
    locations = get_customer_locations(cid)
    all_contacts = get_customer_contacts(cid)
    enriched = _contacts_with_location_names(all_contacts, locations)

    filter_labels = ["All Locations"]
    filter_ids = [""]
    for loc in locations:
        lid = str(loc.get("id") or "").strip()
        if lid:
            filter_labels.append(_location_label(loc))
            filter_ids.append(lid)

    pick_key = f"cust_ct_filter_{cid}"
    if pick_key not in st.session_state:
        st.session_state[pick_key] = 0
    pick = st.selectbox(
        "Filter by location",
        range(len(filter_labels)),
        format_func=lambda i: filter_labels[i],
        key=pick_key,
    )
    filter_loc = filter_ids[int(pick)]
    if filter_loc:
        contacts = [c for c in enriched if str(c.get("location_id") or c.get("customer_location_id") or "") == filter_loc]
    else:
        contacts = enriched
    contacts = _dedupe_contacts_by_id(contacts)

    _render_add_contact_form(customer, locations=locations, demo=demo)

    _render_contacts_table_block(
        contacts,
        empty_caption="No contacts match this filter.",
        customer=customer,
        inline=True,
    )


def _render_customer_detail_tabs(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    cname = str(customer.get("customer_name") or customer.get("company_name") or "")

    (
        tab_overview,
        tab_locations,
        tab_contacts,
        tab_jobs,
        tab_estimates,
        tab_documents,
        tab_notes,
        tab_activity,
    ) = st.tabs(_CUSTOMER_TABS)

    with tab_overview:
        status = safe_value(customer.get("status"))
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Company', customer.get('company_name') or cname)}"
            f"{detail_field_html('Customer #', customer.get('customer_number'))}"
            f"{detail_field_html('Website', customer.get('website'))}"
            f"{detail_field_html('Main Phone', customer.get('main_phone'))}"
            f"{detail_field_html('Main Email', customer.get('main_email'))}"
            f"{detail_field_html('Billing Email', customer.get('billing_email'))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"</div>"
        )
        st.markdown(dialog_card_html("Company", overview_html), unsafe_allow_html=True)
        legacy = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Address', customer.get('address'))}"
            f"{detail_field_html('City', customer.get('city'))}"
            f"{detail_field_html('State', customer.get('state'))}"
            f"{detail_field_html('ZIP', customer.get('zip'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Legacy Address", legacy), unsafe_allow_html=True)

    with tab_locations:
        _render_customer_locations_tab(customer)

    with tab_contacts:
        _render_customer_contacts_tab(customer)

    with tab_jobs:
        _jobs_table(jobs_for_customer(cname), session_key=f"_cust_jobs_{cid}")

    with tab_estimates:
        _estimates_table(estimates_for_customer(cname), session_key=f"_cust_est_{cid}")

    with tab_documents:
        placeholder_html("Customer documents will appear here when connected to Supabase.")

    with tab_notes:
        notes_text = safe_value(customer.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Customer activity history will appear here when connected to Supabase.")


@fragment
def _render_customer_detail_tabs_fragment(customer: dict) -> None:
    """Customer detail tabs — local reruns for contacts/locations edits."""
    _render_customer_detail_tabs(customer)


def render_customer_detail(customer_id: str) -> None:
    cid = str(customer_id or "").strip()
    st.markdown(
        '<span class="ips-customers-detail-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    if st.button("← Back to Customers", key="customers_detail_back", type="secondary"):
        st.session_state[CUSTOMERS_MODE_KEY] = "list"
        st.session_state[CUSTOMERS_SELECTED_ID_KEY] = None
        st.session_state[SELECTED_CUSTOMER_KEY] = None
        st.session_state[SHOW_CUSTOMER_MODAL_KEY] = False
        st.rerun()

    cache = st.session_state.get(_CUSTOMERS_CACHE_KEY) or {}
    customer = cache.get(cid) if isinstance(cache, dict) else None
    if not customer:
        customer = get_customer(cid)
    if not customer:
        st.warning("Customer not found.")
        return

    if isinstance(cache, dict):
        cache[cid] = customer
        st.session_state[_CUSTOMERS_CACHE_KEY] = cache
    st.session_state[SELECTED_CUSTOMER_KEY] = cid

    render_customer_detail_dialog(customer)


def render_customer_detail_dialog(customer: dict) -> None:
    rk = record_session_key(customer, "id", "customer_name")
    cname = safe_value(customer.get("customer_name") or customer.get("company_name"))
    status = safe_value(customer.get("status"))
    cid = str(customer.get("id") or "")

    render_modal_shell()
    render_modal_header(title=cname, subtitle="Customer", status=status)

    render_modal_edit_button(
        module=_MOD,
        record_key=rk,
        on_edit=lambda: _set_customer_edit_mode(customer),
        key_prefix=f"customers_modal_{rk}",
    )

    render_modal_meta_grid(
        [
            ("Primary Location", customer.get("primary_location_name")),
            ("City / State", f"{safe_value(customer.get('primary_location_city'), '')} / {safe_value(customer.get('primary_location_state'), '')}".strip(" /")),
            ("Locations", customer.get("location_count", 0)),
            ("Contacts", customer.get("contact_count", 0)),
            ("Open Jobs", customer.get("open_jobs", 0)),
            ("Open Estimates", customer.get("open_estimates", 0)),
        ]
    )

    if is_edit_mode(_MOD, rk):
        _render_customer_edit_form(customer)
    else:
        _render_customer_detail_tabs_fragment(customer)


@st.dialog("Customer Details", width="large", on_dismiss=_clear_customers_detail_modal)
def _show_customers_detail_modal() -> None:
    customer = get_modal_record(
        cache_key=_CUSTOMERS_CACHE_KEY,
        modal_key=_CUSTOMERS_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not customer:
        sel = str(st.session_state.get(_CUSTOMERS_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
        customer = get_customer(sel) if sel else None
    if not customer:
        render_missing_record(_clear_customers_detail_modal, close_key="customers_modal_missing_close")
        return
    render_customer_detail_dialog(customer)


# --- Location modal ---


def _seed_location_edit_form(location: dict) -> None:
    rk = record_session_key(location, "id", "location_name", "site_name")
    st.session_state[f"loc_edit_name_{rk}"] = str(location.get("location_name") or location.get("site_name") or "")
    st.session_state[f"loc_edit_type_{rk}"] = str(location.get("location_type") or "Other")
    st.session_state[f"loc_edit_addr1_{rk}"] = str(location.get("address_line_1") or location.get("address") or "")
    st.session_state[f"loc_edit_addr2_{rk}"] = str(location.get("address_line_2") or "")
    st.session_state[f"loc_edit_city_{rk}"] = str(location.get("city") or "")
    st.session_state[f"loc_edit_state_{rk}"] = str(location.get("state") or "")
    st.session_state[f"loc_edit_zip_{rk}"] = str(location.get("zip") or "")
    st.session_state[f"loc_edit_country_{rk}"] = str(location.get("country") or "USA")
    st.session_state[f"loc_edit_phone_{rk}"] = str(location.get("phone") or "")
    st.session_state[f"loc_edit_email_{rk}"] = str(location.get("email") or "")
    st.session_state[f"loc_edit_primary_{rk}"] = bool(location.get("is_primary"))
    st.session_state[f"loc_edit_billing_{rk}"] = bool(location.get("is_billing"))
    st.session_state[f"loc_edit_shipping_{rk}"] = bool(location.get("is_shipping"))
    st.session_state[f"loc_edit_status_{rk}"] = str(location.get("status") or "Active")
    st.session_state[f"loc_edit_notes_{rk}"] = str(location.get("notes") or "")


def _set_location_edit_mode(location: dict) -> None:
    rk = record_session_key(location, "id", "location_name", "site_name")
    set_edit_mode(_LOC_MOD, rk)
    _seed_location_edit_form(location)


def _render_location_inline_edit_form(location: dict, *, customer: dict | None = None) -> None:
    lid = str(location.get("id") or "")
    cid = str(location.get("customer_id") or (customer or {}).get("id") or "")
    rk = record_session_key(location, "id", "location_name", "site_name")
    if f"loc_edit_name_{rk}" not in st.session_state:
        _seed_location_edit_form(location)

    render_edit_form_header("Edit Location")
    if is_demo_id(lid) or is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    lc1, lc2 = st.columns(2)
    with lc1:
        st.text_input("Location name", key=f"loc_edit_name_{rk}")
        st.selectbox("Type", LOCATION_TYPES, key=f"loc_edit_type_{rk}")
        st.text_input("Address line 1", key=f"loc_edit_addr1_{rk}")
        st.text_input("Address line 2", key=f"loc_edit_addr2_{rk}")
        st.text_input("City", key=f"loc_edit_city_{rk}")
    with lc2:
        st.text_input("State", key=f"loc_edit_state_{rk}")
        st.text_input("ZIP", key=f"loc_edit_zip_{rk}")
        st.text_input("Phone", key=f"loc_edit_phone_{rk}")
        st.text_input("Email", key=f"loc_edit_email_{rk}")
        st.selectbox("Status", _LOCATION_STATUS_OPTS, key=f"loc_edit_status_{rk}")
    flags = st.columns(3)
    with flags[0]:
        st.checkbox("Primary", key=f"loc_edit_primary_{rk}")
    with flags[1]:
        st.checkbox("Billing", key=f"loc_edit_billing_{rk}")
    with flags[2]:
        st.checkbox("Shipping", key=f"loc_edit_shipping_{rk}")
    st.text_area("Notes", key=f"loc_edit_notes_{rk}", height=90)

    cancelled, saved = render_save_cancel_actions(
        module=_LOC_MOD,
        record_key=rk,
        cancel_key=f"inline_loc_edit_cancel_{rk}",
        save_key=f"inline_loc_edit_save_{rk}",
    )
    if cancelled:
        st.session_state[_inline_location_edit_key(lid)] = False
        st.rerun()
    if saved:
        payload = {
            "customer_id": cid,
            "location_name": st.session_state.get(f"loc_edit_name_{rk}"),
            "location_type": st.session_state.get(f"loc_edit_type_{rk}"),
            "address_line_1": st.session_state.get(f"loc_edit_addr1_{rk}"),
            "address_line_2": st.session_state.get(f"loc_edit_addr2_{rk}"),
            "city": st.session_state.get(f"loc_edit_city_{rk}"),
            "state": st.session_state.get(f"loc_edit_state_{rk}"),
            "zip": st.session_state.get(f"loc_edit_zip_{rk}"),
            "country": st.session_state.get(f"loc_edit_country_{rk}"),
            "phone": st.session_state.get(f"loc_edit_phone_{rk}"),
            "email": st.session_state.get(f"loc_edit_email_{rk}"),
            "is_primary": st.session_state.get(f"loc_edit_primary_{rk}"),
            "is_billing": st.session_state.get(f"loc_edit_billing_{rk}"),
            "is_shipping": st.session_state.get(f"loc_edit_shipping_{rk}"),
            "status": st.session_state.get(f"loc_edit_status_{rk}"),
            "notes": st.session_state.get(f"loc_edit_notes_{rk}"),
        }
        ok, msg = _service_feedback(update_customer_location(lid, payload), success="Location saved.")
        if ok:
            st.session_state[_inline_location_edit_key(lid)] = False
            st.success(msg)
            st.rerun()
        st.error(msg or "Could not save location.")


def _render_location_edit_form(location: dict) -> None:
    lid = str(location.get("id") or "")
    cid = str(location.get("customer_id") or "")
    rk = record_session_key(location, "id", "location_name", "site_name")
    if f"loc_edit_name_{rk}" not in st.session_state:
        _seed_location_edit_form(location)

    render_edit_form_header("Edit Location")
    if is_demo_id(lid) or is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    lc1, lc2 = st.columns(2)
    with lc1:
        st.text_input("Location name", key=f"loc_edit_name_{rk}")
        st.selectbox("Type", LOCATION_TYPES, key=f"loc_edit_type_{rk}")
        st.text_input("Address line 1", key=f"loc_edit_addr1_{rk}")
        st.text_input("Address line 2", key=f"loc_edit_addr2_{rk}")
        st.text_input("City", key=f"loc_edit_city_{rk}")
    with lc2:
        st.text_input("State", key=f"loc_edit_state_{rk}")
        st.text_input("ZIP", key=f"loc_edit_zip_{rk}")
        st.text_input("Country", key=f"loc_edit_country_{rk}")
        st.text_input("Phone", key=f"loc_edit_phone_{rk}")
        st.text_input("Email", key=f"loc_edit_email_{rk}")
        st.selectbox("Status", _LOCATION_STATUS_OPTS, key=f"loc_edit_status_{rk}")
    flags = st.columns(3)
    with flags[0]:
        st.checkbox("Primary", key=f"loc_edit_primary_{rk}")
    with flags[1]:
        st.checkbox("Billing", key=f"loc_edit_billing_{rk}")
    with flags[2]:
        st.checkbox("Shipping", key=f"loc_edit_shipping_{rk}")
    st.text_area("Notes", key=f"loc_edit_notes_{rk}", height=90)

    cancelled, saved = render_save_cancel_actions(
        module=_LOC_MOD,
        record_key=rk,
        cancel_key=f"loc_edit_cancel_{rk}",
        save_key=f"loc_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        payload = {
            "customer_id": cid,
            "location_name": st.session_state.get(f"loc_edit_name_{rk}"),
            "location_type": st.session_state.get(f"loc_edit_type_{rk}"),
            "address_line_1": st.session_state.get(f"loc_edit_addr1_{rk}"),
            "address_line_2": st.session_state.get(f"loc_edit_addr2_{rk}"),
            "city": st.session_state.get(f"loc_edit_city_{rk}"),
            "state": st.session_state.get(f"loc_edit_state_{rk}"),
            "zip": st.session_state.get(f"loc_edit_zip_{rk}"),
            "country": st.session_state.get(f"loc_edit_country_{rk}"),
            "phone": st.session_state.get(f"loc_edit_phone_{rk}"),
            "email": st.session_state.get(f"loc_edit_email_{rk}"),
            "is_primary": st.session_state.get(f"loc_edit_primary_{rk}"),
            "is_billing": st.session_state.get(f"loc_edit_billing_{rk}"),
            "is_shipping": st.session_state.get(f"loc_edit_shipping_{rk}"),
            "status": st.session_state.get(f"loc_edit_status_{rk}"),
            "notes": st.session_state.get(f"loc_edit_notes_{rk}"),
        }
        ok, msg = _service_feedback(update_customer_location(lid, payload), success="Location saved.")
        if ok:
            set_view_mode(_LOC_MOD, rk)
            st.success(msg)
            st.rerun()
        st.error(msg or "Could not save location.")


def _render_location_detail_tabs(
    location: dict,
    customer: dict | None,
    *,
    inline_contacts: bool = False,
) -> None:
    lid = str(location.get("id") or "")
    cid = str(location.get("customer_id") or "")
    cname = str((customer or {}).get("customer_name") or (customer or {}).get("company_name") or "")
    contacts = _contacts_with_location_names(
        get_customer_contacts(cid, location_id=lid),
        get_customer_locations(cid),
    )

    (
        tab_overview,
        tab_contacts,
        tab_jobs,
        tab_estimates,
        tab_documents,
        tab_notes,
        tab_activity,
    ) = st.tabs(_LOCATION_TABS)

    with tab_overview:
        status = safe_value(location.get("status"))
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Location', location.get('location_name') or location.get('site_name'))}"
            f"{detail_field_html('Type', location.get('location_type'))}"
            f"{detail_field_html('Address', location.get('address_line_1') or location.get('address'))}"
            f"{detail_field_html('Address 2', location.get('address_line_2'))}"
            f"{detail_field_html('City', location.get('city'))}"
            f"{detail_field_html('State', location.get('state'))}"
            f"{detail_field_html('ZIP', location.get('zip'))}"
            f"{detail_field_html('Country', location.get('country'))}"
            f"{detail_field_html('Phone', location.get('phone'))}"
            f"{detail_field_html('Email', location.get('email'))}"
            f"{detail_field_html('Primary', _yes_dash(location.get('is_primary')))}"
            f"{detail_field_html('Billing', _yes_dash(location.get('is_billing')))}"
            f"{detail_field_html('Shipping', _yes_dash(location.get('is_shipping')))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"</div>"
        )
        st.markdown(dialog_card_html("Site", overview_html), unsafe_allow_html=True)

    with tab_contacts:
        _render_contacts_table_block(
            contacts,
            empty_caption="No contacts assigned to this location.",
            customer=customer if inline_contacts else None,
            location_id=lid,
            inline=inline_contacts,
        )

    with tab_jobs:
        _jobs_table(jobs_for_customer(cname), session_key=f"_loc_jobs_{lid}", location_id=lid)

    with tab_estimates:
        _estimates_table(estimates_for_customer(cname), session_key=f"_loc_est_{lid}", location_id=lid)

    with tab_documents:
        placeholder_html("Location documents will appear here when connected to Supabase.")

    with tab_notes:
        notes_text = safe_value(location.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Location activity history will appear here when connected to Supabase.")


def render_location_detail_dialog(location: dict) -> None:
    rk = record_session_key(location, "id", "location_name", "site_name")
    title = safe_value(location.get("location_name") or location.get("site_name"))
    status = safe_value(location.get("status"))
    cid = str(location.get("customer_id") or "")
    customer = get_customer(cid) if cid else None
    cname = safe_value((customer or {}).get("customer_name"))

    render_modal_shell()
    render_modal_header(title=title, subtitle=f"{cname} · Location" if cname != "—" else "Location", status=status)

    render_modal_edit_button(
        module=_LOC_MOD,
        record_key=rk,
        on_edit=lambda: _set_location_edit_mode(location),
        key_prefix=f"location_modal_{rk}",
    )

    city_state = ", ".join(
        part for part in (str(location.get("city") or "").strip(), str(location.get("state") or "").strip()) if part
    )
    contacts = get_customer_contacts(cid, location_id=str(location.get("id") or "")) if cid else []
    render_modal_meta_grid(
        [
            ("Type", location.get("location_type")),
            ("City / State", city_state or "—"),
            ("Phone", location.get("phone")),
            ("Contacts", len(contacts)),
        ]
    )

    if is_edit_mode(_LOC_MOD, rk):
        _render_location_edit_form(location)
    else:
        _render_location_detail_tabs(location, customer)


@st.dialog("Location Details", width="large", on_dismiss=_clear_location_detail_modal)
def _show_location_detail_modal() -> None:
    location = get_modal_record(
        cache_key=_LOCATIONS_CACHE_KEY,
        modal_key=_LOCATION_MODAL_KEY,
        session_select_key=_LOC_SEL,
    )
    if not location:
        sel = str(st.session_state.get(_LOCATION_MODAL_KEY) or st.session_state.get(_LOC_SEL) or "").strip()
        location = get_customer_location(sel) if sel else None
    if not location:
        render_missing_record(_clear_location_detail_modal, close_key="location_modal_missing_close")
        return
    render_location_detail_dialog(location)


# --- Contact modal ---


def _seed_contact_edit_form(contact: dict) -> None:
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    st.session_state[f"ct_edit_name_{rk}"] = str(contact.get("full_name") or contact.get("contact_name") or "")
    st.session_state[f"ct_edit_title_{rk}"] = str(contact.get("title") or "")
    st.session_state[f"ct_edit_role_{rk}"] = str(contact.get("role_type") or contact.get("title") or "Other")
    st.session_state[f"ct_edit_email_{rk}"] = str(contact.get("email") or "")
    st.session_state[f"ct_edit_phone_{rk}"] = str(contact.get("phone") or "")
    st.session_state[f"ct_edit_mobile_{rk}"] = str(contact.get("mobile") or "")
    st.session_state[f"ct_edit_primary_{rk}"] = bool(contact.get("is_primary"))
    st.session_state[f"ct_edit_status_{rk}"] = str(contact.get("status") or "Active")
    st.session_state[f"ct_edit_notes_{rk}"] = str(contact.get("notes") or "")


def _set_contact_edit_mode(contact: dict) -> None:
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    set_edit_mode(_CT_MOD, rk)
    _seed_contact_edit_form(contact)


def _render_contact_edit_form(contact: dict, *, locations: list[dict]) -> None:
    ct_id = str(contact.get("id") or "")
    cid = str(contact.get("customer_id") or "")
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    if f"ct_edit_name_{rk}" not in st.session_state:
        _seed_contact_edit_form(contact)

    render_edit_form_header("Edit Contact")
    if is_demo_id(ct_id) or is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    loc_opts = [(_location_label(loc), str(loc.get("id") or "")) for loc in locations if str(loc.get("id") or "")]
    labels = [label for label, _ in loc_opts]
    ids = [lid for _, lid in loc_opts]
    cur_loc = str(contact.get("location_id") or contact.get("customer_location_id") or "")
    if f"ct_edit_loc_{rk}" not in st.session_state and cur_loc in ids:
        st.session_state[f"ct_edit_loc_{rk}"] = ids.index(cur_loc)
    elif f"ct_edit_loc_{rk}" not in st.session_state and ids:
        st.session_state[f"ct_edit_loc_{rk}"] = 0

    if labels:
        loc_idx = st.selectbox(
            "Location",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key=f"ct_edit_loc_{rk}",
        )
        loc_id = ids[int(loc_idx)]
    else:
        st.caption("No locations available.")
        loc_id = cur_loc

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Full name", key=f"ct_edit_name_{rk}")
        st.text_input("Title", key=f"ct_edit_title_{rk}")
        st.selectbox("Role", CONTACT_ROLE_TYPES, key=f"ct_edit_role_{rk}")
    with ec2:
        st.text_input("Email", key=f"ct_edit_email_{rk}")
        st.text_input("Phone", key=f"ct_edit_phone_{rk}")
        st.text_input("Mobile", key=f"ct_edit_mobile_{rk}")
        st.selectbox("Status", ["Active", "Inactive"], key=f"ct_edit_status_{rk}")
        st.checkbox("Primary for location", key=f"ct_edit_primary_{rk}")
    st.text_area("Notes", key=f"ct_edit_notes_{rk}", height=90)

    cancelled, saved = render_save_cancel_actions(
        module=_CT_MOD,
        record_key=rk,
        cancel_key=f"ct_edit_cancel_{rk}",
        save_key=f"ct_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved and loc_id:
        payload = {
            "customer_id": cid,
            "location_id": loc_id,
            "customer_location_id": loc_id,
            "full_name": st.session_state.get(f"ct_edit_name_{rk}"),
            "contact_name": st.session_state.get(f"ct_edit_name_{rk}"),
            "title": st.session_state.get(f"ct_edit_title_{rk}"),
            "role_type": st.session_state.get(f"ct_edit_role_{rk}"),
            "email": st.session_state.get(f"ct_edit_email_{rk}"),
            "phone": st.session_state.get(f"ct_edit_phone_{rk}"),
            "mobile": st.session_state.get(f"ct_edit_mobile_{rk}"),
            "is_primary": st.session_state.get(f"ct_edit_primary_{rk}"),
            "status": st.session_state.get(f"ct_edit_status_{rk}"),
            "notes": st.session_state.get(f"ct_edit_notes_{rk}"),
        }
        ok, msg = _service_feedback(update_customer_contact(ct_id, payload), success="Contact saved.")
        if ok:
            set_view_mode(_CT_MOD, rk)
            st.success(msg)
            st.rerun()
        st.error(msg or "Could not save contact.")


def _render_contact_detail_tabs(contact: dict, customer: dict | None, location: dict | None) -> None:
    ct_id = str(contact.get("id") or "")
    cname = str((customer or {}).get("customer_name") or contact.get("customer_name") or "")

    (
        tab_overview,
        tab_location,
        tab_jobs,
        tab_estimates,
        tab_notes,
        tab_activity,
    ) = st.tabs(_CONTACT_TABS)

    with tab_overview:
        status = safe_value(contact.get("status"))
        role = _normalize_contact_role(contact.get("role_type"), contact.get("title"))
        loc_name = safe_value((location or {}).get("location_name") or contact.get("location_name"))
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Full Name', contact.get('full_name') or contact.get('contact_name'))}"
            f"{detail_field_html('Title', contact.get('title'))}"
            f"{detail_field_html('Customer', cname)}"
            f"{detail_field_html('Location', loc_name)}"
            f'{detail_field_html("Role Type", role, html_value=_contact_role_pill_html(role))}'
            f"{detail_field_html('Email', contact.get('email'))}"
            f"{detail_field_html('Phone', contact.get('phone'))}"
            f"{detail_field_html('Mobile', contact.get('mobile'))}"
            f"{detail_field_html('Primary', _yes_dash(contact.get('is_primary')))}"
            f"{detail_field_html('Billing', _yes_dash(contact.get('is_billing_contact')))}"
            f"{detail_field_html('Site', _yes_dash(contact.get('is_site_contact')))}"
            f"{detail_field_html('Safety', _yes_dash(contact.get('is_safety_contact')))}"
            f"{detail_field_html('Estimating', _yes_dash(contact.get('is_estimating_contact')))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"</div>"
        )
        st.markdown(dialog_card_html("Contact", overview_html), unsafe_allow_html=True)

    with tab_location:
        if location:
            loc_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Location', location.get('location_name') or location.get('site_name'))}"
                f"{detail_field_html('Type', location.get('location_type'))}"
                f"{detail_field_html('City', location.get('city'))}"
                f"{detail_field_html('State', location.get('state'))}"
                f"{detail_field_html('Phone', location.get('phone'))}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Assigned Location", loc_html), unsafe_allow_html=True)
        else:
            st.caption("No location assigned.")

    with tab_jobs:
        jobs = jobs_for_customer(cname)
        contact_name = str(contact.get("full_name") or contact.get("contact_name") or "").strip().lower()
        if contact_name:
            jobs = [
                j
                for j in jobs
                if str(j.get("contact_name") or j.get("customer_contact") or "").strip().lower() == contact_name
                or str(j.get("customer_contact_id") or j.get("contact_id") or "") == ct_id
            ]
        _jobs_table(jobs, session_key=f"_ct_jobs_{ct_id}")

    with tab_estimates:
        ests = estimates_for_customer(cname)
        contact_name = str(contact.get("full_name") or contact.get("contact_name") or "").strip().lower()
        if contact_name:
            ests = [
                e
                for e in ests
                if str(e.get("contact_name") or e.get("customer_contact") or "").strip().lower() == contact_name
                or str(e.get("customer_contact_id") or e.get("contact_id") or "") == ct_id
            ]
        _estimates_table(ests, session_key=f"_ct_est_{ct_id}")

    with tab_notes:
        notes_text = safe_value(contact.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Contact activity history will appear here when connected to Supabase.")


def render_contact_detail_dialog(contact: dict) -> None:
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    title = safe_value(contact.get("full_name") or contact.get("contact_name"))
    status = safe_value(contact.get("status"))
    cid = str(contact.get("customer_id") or "")
    customer = get_customer(cid) if cid else None
    lid = str(contact.get("location_id") or contact.get("customer_location_id") or "")
    location = get_customer_location(lid) if lid else None
    cname = safe_value((customer or {}).get("customer_name"))
    loc_name = safe_value((location or {}).get("location_name") or contact.get("location_name"))

    render_modal_shell()
    render_modal_header(
        title=title,
        subtitle=f"{cname} · {loc_name}" if cname != "—" else loc_name,
        status=status,
    )

    render_modal_edit_button(
        module=_CT_MOD,
        record_key=rk,
        on_edit=lambda: _set_contact_edit_mode(contact),
        key_prefix=f"contact_modal_{rk}",
    )

    render_modal_meta_grid(
        [
            ("Role", contact.get("role_type") or contact.get("title")),
            ("Location", loc_name),
            ("Email", contact.get("email")),
            ("Phone", contact.get("phone")),
        ]
    )

    if is_edit_mode(_CT_MOD, rk):
        locations = get_customer_locations(cid) if cid else []
        _render_contact_edit_form(contact, locations=locations)
    else:
        _render_contact_detail_tabs(contact, customer, location)


@st.dialog("Contact Details", width="large", on_dismiss=_clear_contact_detail_modal)
def _show_contact_detail_modal() -> None:
    contact = get_modal_record(
        cache_key=_CONTACTS_CACHE_KEY,
        modal_key=_CONTACT_MODAL_KEY,
        session_select_key=_CT_SEL,
    )
    if not contact:
        sel = str(
            st.session_state.get(SELECTED_CONTACT_KEY)
            or st.session_state.get(_CONTACT_MODAL_KEY)
            or st.session_state.get(_CT_SEL)
            or ""
        ).strip()
        cache = st.session_state.get(_CONTACTS_CACHE_KEY) or {}
        if isinstance(cache, dict) and sel:
            contact = cache.get(sel)
        if not contact and sel:
            contact = get_customer_contact(sel)
    if not contact:
        render_missing_record(_clear_contact_detail_modal, close_key="contact_modal_missing_close")
        return
    render_contact_detail_dialog(contact)


# --- Page render ---


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("customers"):
        return

    inject_customers_module_css()
    inject_customers_page_layout_css()
    st.markdown(
        '<span class="ips-customers-page ips-module-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    if (
        st.session_state.get(CUSTOMERS_MODE_KEY) == "detail"
        and st.session_state.get(CUSTOMERS_SELECTED_ID_KEY)
    ):
        render_customer_detail(str(st.session_state[CUSTOMERS_SELECTED_ID_KEY]))
        st.stop()

    all_rows = _enrich_list_rows(get_customers())
    filter_options = build_filter_options(all_rows, _CUSTOMER_COLUMN_FILTER_SPECS)

    def _customers_new() -> None:
        if st.button("+ New Customer", key="cust_new", type="primary", use_container_width=True):
            st.session_state["ips_cust_form"] = True

    render_page_brand_header(
        "Customers",
        "Manage customer companies, locations, and contacts.",
        actions=[_customers_new],
    )

    if st.session_state.get("ips_cust_form"):
        with st.container(border=True):
            st.markdown(
                '<p class="ips-page-subtitle" style="margin:0 0 0.5rem;font-weight:600;color:#0f172a">New customer</p>',
                unsafe_allow_html=True,
            )
            nc1, nc2 = st.columns(2)
            with nc1:
                st.text_input("Company name", key="cust_new_company")
                st.text_input("Customer #", key="cust_new_number")
                st.text_input("Website", key="cust_new_website")
                st.text_input("Main phone", key="cust_new_main_phone")
            with nc2:
                st.text_input("Main email", key="cust_new_main_email")
                st.text_input("Billing email", key="cust_new_billing_email")
                st.selectbox("Status", ["Active", "Inactive"], key="cust_new_status")
            st.text_area("Notes", key="cust_new_notes")
            with st.expander("Legacy address (optional)", expanded=False):
                la1, la2 = st.columns(2)
                with la1:
                    st.text_input("Address", key="cust_new_addr")
                    st.text_input("City", key="cust_new_city")
                with la2:
                    st.text_input("State", key="cust_new_state")
                    st.text_input("ZIP", key="cust_new_zip")
            sb1, sb2 = st.columns(2)
            with sb1:
                if st.button("Save customer", key="cust_save_new", type="primary", use_container_width=True):
                    payload = {
                        "company_name": st.session_state.get("cust_new_company"),
                        "customer_name": st.session_state.get("cust_new_company"),
                        "customer_number": st.session_state.get("cust_new_number"),
                        "website": st.session_state.get("cust_new_website"),
                        "main_phone": st.session_state.get("cust_new_main_phone"),
                        "main_email": st.session_state.get("cust_new_main_email"),
                        "billing_email": st.session_state.get("cust_new_billing_email"),
                        "status": st.session_state.get("cust_new_status"),
                        "notes": st.session_state.get("cust_new_notes"),
                        "address": st.session_state.get("cust_new_addr"),
                        "city": st.session_state.get("cust_new_city"),
                        "state": st.session_state.get("cust_new_state"),
                        "zip": st.session_state.get("cust_new_zip"),
                    }
                    ok, msg = _service_feedback(create_customer(payload), success="Customer saved.")
                    if apply_persist_feedback(ok, msg, clear_keys=("ips_cust_form",)):
                        st.rerun()
            with sb2:
                if st.button("Cancel", key="cust_cancel_new", use_container_width=True):
                    st.session_state.pop("ips_cust_form", None)
                    st.rerun()

    def _filters() -> None:
        c1, c2, c3 = st.columns([3.2, 2.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search company, customer #, city, email…",
                key="cust_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Status",
                ["All Statuses", "Active", "Inactive", "Prospect", "On Hold"],
                key="cust_bar_status",
                label_visibility="collapsed",
            )
        with c3:
            if st.button("Clear", key="cust_clear", use_container_width=True):
                clear_table_filters(
                    _CUSTOMERS_TABLE_KEY,
                    _CUSTOMER_BAR_FILTER_FIELDS,
                    extra_keys=["cust_search", "cust_bar_status"],
                )
                st.session_state["cust_bar_status"] = "All Statuses"
                reset_table_page(_CUSTOMERS_TABLE_KEY)
                _clear_customer_selection(st.session_state.get(_ALL_CUSTOMER_IDS_KEY))
                st.rerun()

    render_customers_filter_bar_shell()
    layout_filter_bar(_filters)
    close_customers_filter_bar_shell()

    filtered = _filter_customers(
        all_rows,
        q=str(st.session_state.get("cust_search") or "").strip(),
        bar_status=str(st.session_state.get("cust_bar_status") or "All Statuses"),
    )

    render_table_pagination_header(len(filtered), _CUSTOMERS_TABLE_KEY, item_label="customer")
    page_rows, _, _, _ = paginate_rows(filtered, _CUSTOMERS_TABLE_KEY)

    build_modal_cache(filtered, cache_key=_CUSTOMERS_CACHE_KEY)
    _render_customers_list_table(page_rows, filter_options=filter_options)
    render_table_pagination_footer(len(filtered), _CUSTOMERS_TABLE_KEY)
