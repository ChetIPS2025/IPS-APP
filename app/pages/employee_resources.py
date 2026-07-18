"""Employee Resources — workforce forms/documents with admin CRUD."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.auth import effective_role
from app.components.headers import render_page_header
from app.pages._core._access import begin_module
from app.services.employee_resources_service import (
    RESOURCE_TYPES,
    ROLE_VISIBILITY_OPTIONS,
    delete_employee_resource,
    list_all_employee_resources_admin,
    list_employee_resources,
    resource_open_url,
    save_employee_resource,
)
from app.styles import inject_employee_portal_css
from app.utils.formatting import fmt_date
from app.utils.permissions import normalize_role
_ADMIN_EDIT_KEY = "ips_er_admin_edit"


def _render_resource_card(row: dict[str, Any]) -> None:
    rid = str(row.get("id") or "")
    title = html.escape(str(row.get("title") or "Resource"))
    category = html.escape(str(row.get("category") or "Document"))
    desc = html.escape(str(row.get("description") or ""))
    st.markdown(
        f"""
<div class="ips-ep-card ips-ep-resource-card">
  <div class="ips-ep-card-head"><strong>{title}</strong><span class="ips-ep-tag">{category}</span></div>
  <p class="ips-ep-muted">{desc}</p>
</div>
""",
        unsafe_allow_html=True,
    )
    url = resource_open_url(row)
    if url:
        st.link_button(f"Open {row.get('title', 'resource')}", url, use_container_width=True)
    else:
        st.caption("No link or file is attached yet.")


def _render_admin_panel(rows: list[dict[str, Any]]) -> None:
    st.markdown("### Manage resources")
    edit_id = st.session_state.get(_ADMIN_EDIT_KEY)
    editing = next((r for r in rows if str(r.get("id")) == str(edit_id)), None) if edit_id else None

    with st.expander("Add or edit resource", expanded=bool(editing)):
        title = st.text_input("Title", value=str(editing.get("title") or "") if editing else "", key="er_title")
        category = st.selectbox(
            "Resource type",
            RESOURCE_TYPES,
            index=RESOURCE_TYPES.index(editing.get("category"))
            if editing and editing.get("category") in RESOURCE_TYPES
            else 0,
            key="er_category",
        )
        description = st.text_area(
            "Description",
            value=str(editing.get("description") or "") if editing else "",
            key="er_desc",
        )
        delivery = st.radio(
            "Attachment",
            ["Link", "File path (storage key)"],
            horizontal=True,
            key="er_delivery",
        )
        url_val = ""
        file_path = ""
        if editing:
            if editing.get("resource_type") == "file":
                delivery = "File path (storage key)"
                file_path = str(editing.get("file_path") or "")
            else:
                url_val = str(editing.get("url") or "")
        link_url = st.text_input("URL", value=url_val, key="er_url") if delivery == "Link" else ""
        storage_key = (
            st.text_input("Storage file path", value=file_path, key="er_path")
            if delivery != "Link"
            else ""
        )
        roles = st.multiselect(
            "Visible to roles",
            list(ROLE_VISIBILITY_OPTIONS),
            default=[r.strip() for r in str(editing.get("visible_to_roles") or "").split(",") if r.strip()]
            if editing
            else list(ROLE_VISIBILITY_OPTIONS),
            key="er_roles",
        )
        sort_order = st.number_input(
            "Sort order",
            min_value=0,
            value=int(editing.get("sort_order") or 0) if editing else 0,
            key="er_sort",
        )
        is_active = st.checkbox(
            "Active",
            value=bool(editing.get("is_active", True)) if editing else True,
            key="er_active",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            save = st.button("Save resource", type="primary", use_container_width=True)
        with c2:
            cancel = st.button("Cancel edit", use_container_width=True)
        with c3:
            if editing and st.button("Delete", use_container_width=True):
                delete_employee_resource(str(editing.get("id")))
                st.session_state.pop(_ADMIN_EDIT_KEY, None)
                st.success("Resource removed.")
                st.rerun()

        if cancel:
            st.session_state.pop(_ADMIN_EDIT_KEY, None)
            st.rerun()

        if save:
            payload: dict[str, Any] = {
                "title": title.strip(),
                "category": category,
                "description": description.strip(),
                "visible_to_roles": ",".join(roles),
                "sort_order": int(sort_order),
                "is_active": is_active,
            }
            if delivery == "Link":
                payload["resource_type"] = "link"
                payload["url"] = link_url.strip()
            else:
                payload["resource_type"] = "file"
                payload["file_path"] = storage_key.strip()
                payload["file_name"] = storage_key.strip().split("/")[-1] if storage_key.strip() else ""
            result = save_employee_resource(payload, row_id=str(editing.get("id")) if editing else None)
            if result.ok:
                st.session_state.pop(_ADMIN_EDIT_KEY, None)
                st.success("Resource saved.")
                st.rerun()
            st.error(result.error or "Could not save resource.")

    if rows:
        st.markdown("#### Existing resources")
        for row in rows:
            cols = st.columns([4, 1, 1])
            with cols[0]:
                st.write(f"**{row.get('title')}** — {row.get('category')} ({'Active' if row.get('is_active') else 'Hidden'})")
                st.caption(row.get("description") or "")
            with cols[1]:
                if st.button("Edit", key=f"er_edit_{row.get('id')}"):
                    st.session_state[_ADMIN_EDIT_KEY] = row.get("id")
                    st.rerun()
            with cols[2]:
                updated = fmt_date(str(row.get("updated_at") or row.get("created_at") or "")[:10])
                st.caption(updated or "—")


def render() -> None:
    if not begin_module("employee_resources"):
        return
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

    role = effective_role()
    rows, _used_demo = list_employee_resources(role=role)
    for row in rows:
        _render_resource_card(row)

    if normalize_role(role) == "admin":
        all_rows, _ = list_all_employee_resources_admin()
        _render_admin_panel(all_rows)
