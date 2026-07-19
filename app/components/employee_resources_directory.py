"""Employee-facing Employee Resources directory — filters, cards, pagination."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from app.components.table_pagination import (
    page_key,
    page_size_key,
    render_table_pagination_footer,
    render_table_pagination_header,
    reset_table_page,
)
from app.services.employee_resources_service import (
    EMPLOYEE_RESOURCES_DEFAULT_PAGE_SIZE,
    EmployeeResourcesPage,
    get_employee_resource_open_target,
    is_safe_direct_link,
    list_employee_resources_page,
)
from app.ui.streamlit_perf import fragment, fragment_rerun

_TABLE_KEY = "employee_resources_list"
_SEARCH_KEY = "ips_er_search"
_CATEGORY_KEY = "ips_er_category"
_OPEN_QUERY_KEY = "er_open"
_NAV_QUERY_KEY = "ips_nav"
_FILTER_SNAPSHOT_KEY = "_ips_er_filter_snapshot"


def open_resource_query_key() -> str:
    return _OPEN_QUERY_KEY


def open_resource_href(resource_id: str) -> str:
    params = {
        _NAV_QUERY_KEY: "employee_resources",
        _OPEN_QUERY_KEY: str(resource_id or "").strip(),
    }
    return "?" + urlencode(params)


def build_resource_cards_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    parts: list[str] = []
    for row in rows:
        rid = str(row.get("id") or "")
        title = html.escape(str(row.get("title") or "Resource"))
        category = html.escape(str(row.get("category") or "Document"))
        desc = html.escape(str(row.get("description") or ""))
        action = ""
        if is_safe_direct_link(row):
            url = html.escape(str(row.get("url") or ""), quote=True)
            action = (
                f'<a class="ips-ep-open-link" href="{url}" target="_blank" '
                f'rel="noopener noreferrer">Open resource</a>'
            )
        else:
            href = html.escape(open_resource_href(rid), quote=True)
            action = (
                f'<a class="ips-ep-open-link" href="{href}" target="_self">Open resource</a>'
            )
        parts.append(
            f"""
<div class="ips-ep-card ips-ep-resource-card">
  <div class="ips-ep-card-head"><strong>{title}</strong><span class="ips-ep-tag">{category}</span></div>
  <p class="ips-ep-muted">{desc}</p>
  <div class="ips-ep-card-actions">{action}</div>
</div>
"""
        )
    return "".join(parts)


def _capture_open_query(*, role: str, user_id: str) -> None:
    from app.perf_debug import perf_span

    requested = str(st.query_params.get(_OPEN_QUERY_KEY) or "").strip()
    if not requested:
        return
    with perf_span("employee_resources.open_target"):
        result = get_employee_resource_open_target(requested, role=role, user_id=user_id)
    if _OPEN_QUERY_KEY in st.query_params:
        del st.query_params[_OPEN_QUERY_KEY]
    if not result.ok:
        st.error(str(result.error or "Could not open this resource."))
        return
    data = result.data if isinstance(result.data, dict) else {}
    url = str(data.get("url") or "").strip()
    if url:
        st.link_button("Open resource", url, use_container_width=True)
    else:
        st.error("Could not open this resource.")


@fragment
def render_employee_resources_directory(
    *,
    role: str,
    user_id: str,
) -> None:
    from app.perf_debug import perf_span

    search = str(st.session_state.get(_SEARCH_KEY) or "").strip()
    category = str(st.session_state.get(_CATEGORY_KEY) or "").strip()
    snapshot = st.session_state.get(_FILTER_SNAPSHOT_KEY)
    current_snapshot = (search, category)
    if snapshot != current_snapshot:
        reset_table_page(_TABLE_KEY)
        st.session_state[_FILTER_SNAPSHOT_KEY] = current_snapshot

    page = max(1, int(st.session_state.get(page_key(_TABLE_KEY), 1)))
    page_size = max(
        10,
        min(
            200,
            int(st.session_state.get(page_size_key(_TABLE_KEY), EMPLOYEE_RESOURCES_DEFAULT_PAGE_SIZE)),
        ),
    )

    fc1, fc2, fc3 = st.columns([2.2, 1.2, 0.6])
    with fc1:
        st.text_input("Search resources", key=_SEARCH_KEY, placeholder="Title, description, category…")
    with fc2:
        cats_placeholder = st.session_state.get("_ips_er_category_options") or [""]
        options = [""] + [c for c in cats_placeholder if c]
        idx = options.index(category) if category in options else 0
        st.selectbox("Category", options, index=idx, key=_CATEGORY_KEY, format_func=lambda x: x or "All categories")
    with fc3:
        if st.button("Clear", key="ips_er_clear_filters", use_container_width=True):
            st.session_state[_SEARCH_KEY] = ""
            st.session_state[_CATEGORY_KEY] = ""
            reset_table_page(_TABLE_KEY)
            fragment_rerun()

    categories = [category] if category else None
    with perf_span("employee_resources.list_query"):
        directory: EmployeeResourcesPage = list_employee_resources_page(
            role=role,
            search=search,
            categories=categories,
            page=page,
            page_size=page_size,
        )
    st.session_state["_ips_er_category_options"] = directory.categories

    if directory.warning:
        st.info(directory.warning)

    page, page_size, _ = render_table_pagination_header(
        directory.total_count,
        _TABLE_KEY,
        default_page_size=EMPLOYEE_RESOURCES_DEFAULT_PAGE_SIZE,
        item_label="resource",
    )
    if page != directory.page or page_size != directory.page_size:
        directory = list_employee_resources_page(
            role=role,
            search=search,
            categories=categories,
            page=page,
            page_size=page_size,
        )

    if not directory.rows:
        st.info("No employee resources are currently available for your role.")
    else:
        with perf_span("employee_resources.cards_html"):
            st.markdown(build_resource_cards_html(directory.rows), unsafe_allow_html=True)

    render_table_pagination_footer(directory.total_count, _TABLE_KEY)
    _capture_open_query(role=role, user_id=user_id)
