"""Employee Resources — workforce forms/documents with admin CRUD."""

from __future__ import annotations

import streamlit as st

from app.components.employee_resource_form import (
    clear_employee_resource_form_state,
    render_employee_resource_form,
)
from app.components.employee_resources_admin_table import (
    admin_manage_query_key,
    admin_select_query_key,
    build_employee_resources_admin_html_table,
)
from app.components.employee_resources_directory import render_employee_resources_directory
from app.components.employee_resources_permissions import (
    EmployeeResourcesPermissions,
    load_employee_resources_permissions,
)
from app.components.headers import render_page_header
from app.components.table_pagination import (
    render_table_pagination_footer,
    render_table_pagination_header,
    reset_table_page,
)
from app.components.tabs import render_tabs
from app.pages._core._access import begin_module
from app.services.employee_resources_service import (
    ADMIN_RESOURCES_DEFAULT_PAGE_SIZE,
    delete_employee_resource,
    get_employee_resource_detail,
    get_employee_resource_open_target,
    list_employee_resources_admin_page,
)
from app.styles import inject_employee_portal_css
from app.ui.streamlit_perf import fragment, fragment_rerun, ips_app_rerun

_VIEW_KEY = "ips_employee_resources_view"
_ADMIN_TABLE_KEY = "employee_resources_admin"
_ADMIN_SEARCH_KEY = "ips_er_admin_search"
_ADMIN_CATEGORY_KEY = "ips_er_admin_category"
_ADMIN_STATUS_KEY = "ips_er_admin_status"
_ADMIN_SELECTED_KEY = "ips_er_admin_selected"
_ADMIN_FORM_MODE_KEY = "ips_er_admin_form_mode"
_ADMIN_DELETE_CONFIRM_KEY = "ips_er_admin_delete_confirm"
_ADMIN_FILTER_SNAPSHOT_KEY = "_ips_er_admin_filter_snapshot"


def _clear_admin_selection() -> None:
    st.session_state.pop(_ADMIN_SELECTED_KEY, None)
    st.session_state.pop(_ADMIN_FORM_MODE_KEY, None)
    st.session_state.pop(_ADMIN_DELETE_CONFIRM_KEY, None)
    if admin_select_query_key() in st.query_params:
        del st.query_params[admin_select_query_key()]
    if admin_manage_query_key() in st.query_params:
        del st.query_params[admin_manage_query_key()]


def _capture_admin_select_query() -> None:
    if str(st.query_params.get(admin_manage_query_key()) or "") != "1":
        return
    selected = str(st.query_params.get(admin_select_query_key()) or "").strip()
    if selected:
        st.session_state[_ADMIN_SELECTED_KEY] = selected
        st.session_state[_VIEW_KEY] = "Manage Resources"
    if admin_select_query_key() in st.query_params:
        del st.query_params[admin_select_query_key()]


@st.dialog("Employee Resource", width="large")
def _show_resource_form_dialog(
    resource: dict | None,
    permissions: EmployeeResourcesPermissions,
) -> None:
    def _on_saved(_saved_id: str) -> None:
        st.session_state.pop(_ADMIN_FORM_MODE_KEY, None)
        st.session_state.pop(_ADMIN_SELECTED_KEY, None)

    def _on_cancel() -> None:
        st.session_state.pop(_ADMIN_FORM_MODE_KEY, None)
        clear_employee_resource_form_state()
        st.rerun()

    render_employee_resource_form(
        resource,
        permissions=permissions,
        on_saved=_on_saved,
        on_cancel=_on_cancel,
    )


@fragment
def _render_admin_directory_fragment(permissions: EmployeeResourcesPermissions) -> None:
    from app.perf_debug import perf_span

    search = str(st.session_state.get(_ADMIN_SEARCH_KEY) or "").strip()
    category = str(st.session_state.get(_ADMIN_CATEGORY_KEY) or "").strip()
    status = str(st.session_state.get(_ADMIN_STATUS_KEY) or "").strip()
    snapshot = st.session_state.get(_ADMIN_FILTER_SNAPSHOT_KEY)
    current = (search, category, status)
    if snapshot != current:
        reset_table_page(_ADMIN_TABLE_KEY)
        st.session_state[_ADMIN_FILTER_SNAPSHOT_KEY] = current

    fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 0.6])
    with fc1:
        st.text_input("Search", key=_ADMIN_SEARCH_KEY, placeholder="Title, description, category…")
    with fc2:
        st.selectbox(
            "Category",
            [""] + list(st.session_state.get("_ips_er_admin_category_options") or []),
            key=_ADMIN_CATEGORY_KEY,
            format_func=lambda x: x or "All categories",
        )
    with fc3:
        st.selectbox(
            "Status",
            ["", "active", "inactive"],
            key=_ADMIN_STATUS_KEY,
            format_func=lambda x: {"": "All statuses", "active": "Active", "inactive": "Hidden"}.get(x, x),
        )
    with fc4:
        if st.button("Clear", key="ips_er_admin_clear", use_container_width=True):
            st.session_state[_ADMIN_SEARCH_KEY] = ""
            st.session_state[_ADMIN_CATEGORY_KEY] = ""
            st.session_state[_ADMIN_STATUS_KEY] = ""
            reset_table_page(_ADMIN_TABLE_KEY)
            fragment_rerun()

    from app.components.table_pagination import page_key, page_size_key

    page = max(1, int(st.session_state.get(page_key(_ADMIN_TABLE_KEY), 1)))
    page_size = max(
        10,
        min(
            200,
            int(st.session_state.get(page_size_key(_ADMIN_TABLE_KEY), ADMIN_RESOURCES_DEFAULT_PAGE_SIZE)),
        ),
    )
    categories = [category] if category else None
    statuses = [status] if status else None

    with perf_span("employee_resources.admin.list_query"):
        directory = list_employee_resources_admin_page(
            search=search,
            categories=categories,
            statuses=statuses,
            page=page,
            page_size=page_size,
        )
    st.session_state["_ips_er_admin_category_options"] = directory.categories

    if directory.warning:
        st.info(directory.warning)

    page, page_size, _ = render_table_pagination_header(
        directory.total_count,
        _ADMIN_TABLE_KEY,
        default_page_size=ADMIN_RESOURCES_DEFAULT_PAGE_SIZE,
        item_label="resource",
    )
    if page != directory.page or page_size != directory.page_size:
        directory = list_employee_resources_admin_page(
            search=search,
            categories=categories,
            statuses=statuses,
            page=page,
            page_size=page_size,
        )

    if st.button("+ Add Resource", type="primary", key="ips_er_add_resource"):
        st.session_state[_ADMIN_FORM_MODE_KEY] = "add"
        st.session_state.pop(_ADMIN_SELECTED_KEY, None)
        ips_app_rerun()

    if not directory.rows:
        st.info("No employee resources have been created yet.")
    else:
        with perf_span("employee_resources.admin.table_html"):
            st.markdown(build_employee_resources_admin_html_table(directory.rows), unsafe_allow_html=True)

    render_table_pagination_footer(directory.total_count, _ADMIN_TABLE_KEY)

    selected_id = str(st.session_state.get(_ADMIN_SELECTED_KEY) or "").strip()
    selected = next((r for r in directory.rows if str(r.get("id")) == selected_id), None)
    if not selected and selected_id:
        selected = get_employee_resource_detail(selected_id, admin=True)

    if selected:
        st.markdown(f"**Selected:** {selected.get('title', 'Resource')}")
        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            if st.button("Edit", key="ips_er_admin_action_edit", use_container_width=True):
                st.session_state[_ADMIN_FORM_MODE_KEY] = "edit"
                ips_app_rerun()
        with ac2:
            if st.button("Open", key="ips_er_admin_action_open", use_container_width=True):
                _open_selected_resource(selected, permissions)
        with ac3:
            if st.button("Delete", key="ips_er_admin_action_delete", use_container_width=True):
                st.session_state[_ADMIN_DELETE_CONFIRM_KEY] = selected_id
                fragment_rerun()
        with ac4:
            if st.button("Clear", key="ips_er_admin_action_clear", use_container_width=True):
                _clear_admin_selection()
                fragment_rerun()

    confirm_id = str(st.session_state.get(_ADMIN_DELETE_CONFIRM_KEY) or "").strip()
    if confirm_id:
        st.warning("Delete this employee resource? Employees will no longer be able to access it.")
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("Confirm Delete", type="primary", key="ips_er_confirm_delete"):
                _confirm_delete(confirm_id)
        with dc2:
            if st.button("Cancel", key="ips_er_cancel_delete"):
                st.session_state.pop(_ADMIN_DELETE_CONFIRM_KEY, None)
                fragment_rerun()


def _open_selected_resource(row: dict, permissions: EmployeeResourcesPermissions) -> None:
    from app.perf_debug import perf_span

    rid = str(row.get("id") or "")
    with perf_span("employee_resources.open_target"):
        result = get_employee_resource_open_target(
            rid,
            role=permissions.role,
            user_id=permissions.user_id,
        )
    if not result.ok:
        st.error(str(result.error or "Could not open this resource."))
        return
    data = result.data if isinstance(result.data, dict) else {}
    url = str(data.get("url") or "").strip()
    if url:
        st.link_button("Open resource", url, use_container_width=True)
    else:
        st.error("Could not open this resource.")


def _confirm_delete(resource_id: str) -> None:
    from app.perf_debug import perf_span

    with perf_span("employee_resources.delete"):
        result = delete_employee_resource(resource_id)
    if not result.ok:
        st.error(str(result.error or "Could not delete resource."))
        return
    st.session_state.pop(_ADMIN_DELETE_CONFIRM_KEY, None)
    st.session_state.pop(_ADMIN_SELECTED_KEY, None)
    st.session_state.pop(_ADMIN_FORM_MODE_KEY, None)
    clear_employee_resource_form_state()
    st.success("Resource removed.")
    ips_app_rerun()


def render() -> None:
    from app.perf_debug import perf_span

    if not begin_module("employee_resources"):
        return

    with perf_span("employee_resources.page_shell"):
        inject_employee_portal_css()
        st.markdown(
            '<span class="ips-employee-resources-page" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        render_page_header(
            "Employee Resources",
            "Forms, documents, and workforce reference materials.",
            icon="📁",
        )

        permissions = load_employee_resources_permissions()
        _capture_admin_select_query()

        if permissions.is_admin:
            active_view = render_tabs(
                ["Resources", "Manage Resources"],
                session_key=_VIEW_KEY,
                default="Resources",
            )
        else:
            active_view = "Resources"

        if active_view == "Manage Resources" and permissions.can_manage:
            _render_admin_directory_fragment(permissions)
            form_mode = str(st.session_state.get(_ADMIN_FORM_MODE_KEY) or "").strip()
            if form_mode == "add":
                _show_resource_form_dialog(None, permissions)
            elif form_mode == "edit":
                edit_id = str(st.session_state.get(_ADMIN_SELECTED_KEY) or "").strip()
                resource = get_employee_resource_detail(edit_id, admin=True) if edit_id else None
                if resource:
                    _show_resource_form_dialog(resource, permissions)
                else:
                    st.session_state.pop(_ADMIN_FORM_MODE_KEY, None)
        else:
            render_employee_resources_directory(role=permissions.role, user_id=permissions.user_id)
