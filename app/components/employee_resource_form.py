"""Employee Resource add/edit form with stable per-resource session seeding."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from app.components.employee_resources_permissions import EmployeeResourcesPermissions
from app.services.employee_resources_service import (
    RESOURCE_TYPES,
    ROLE_VISIBILITY_OPTIONS,
    save_employee_resource,
    validate_employee_resource_payload,
)
from app.services.employee_resources_cache import employee_resources_data_version
from app.ui.streamlit_perf import ips_app_rerun

_DELIVERY_LINK = "link"
_DELIVERY_FILE = "file"
_DELIVERY_LABELS = {
    _DELIVERY_LINK: "Link",
    _DELIVERY_FILE: "File path (storage key)",
}
_DELIVERY_OPTIONS = [_DELIVERY_LABELS[_DELIVERY_LINK], _DELIVERY_LABELS[_DELIVERY_FILE]]


def seed_employee_resource_form(resource: dict[str, Any] | None) -> str:
    """Seed widget state once per resource id and data version; return stable form key."""
    form_key = "new" if not resource else str(resource.get("id") or "new")
    version = employee_resources_data_version()
    seed_marker = f"ips_er_form_seeded_{form_key}_v{version}"
    if st.session_state.get(seed_marker):
        return form_key

    prior_keys = [k for k in st.session_state.keys() if str(k).startswith("ips_er_form_")]
    for key in prior_keys:
        st.session_state.pop(key, None)

    prefix = f"ips_er_form_{form_key}_"
    if resource:
        delivery = _DELIVERY_FILE if str(resource.get("resource_type") or "").lower() == "file" else _DELIVERY_LINK
        st.session_state[f"{prefix}title"] = str(resource.get("title") or "")
        st.session_state[f"{prefix}category"] = (
            resource.get("category") if resource.get("category") in RESOURCE_TYPES else RESOURCE_TYPES[0]
        )
        st.session_state[f"{prefix}desc"] = str(resource.get("description") or "")
        st.session_state[f"{prefix}delivery"] = _DELIVERY_LABELS[delivery]
        st.session_state[f"{prefix}url"] = str(resource.get("url") or "")
        st.session_state[f"{prefix}path"] = str(resource.get("file_path") or "")
        roles = [r.strip() for r in str(resource.get("visible_to_roles") or "").split(",") if r.strip()]
        st.session_state[f"{prefix}roles"] = roles or list(ROLE_VISIBILITY_OPTIONS)
        st.session_state[f"{prefix}sort"] = int(resource.get("sort_order") or 0)
        st.session_state[f"{prefix}active"] = bool(resource.get("is_active", True))
    else:
        st.session_state[f"{prefix}title"] = ""
        st.session_state[f"{prefix}category"] = RESOURCE_TYPES[0]
        st.session_state[f"{prefix}desc"] = ""
        st.session_state[f"{prefix}delivery"] = _DELIVERY_LABELS[_DELIVERY_LINK]
        st.session_state[f"{prefix}url"] = ""
        st.session_state[f"{prefix}path"] = ""
        st.session_state[f"{prefix}roles"] = list(ROLE_VISIBILITY_OPTIONS)
        st.session_state[f"{prefix}sort"] = 0
        st.session_state[f"{prefix}active"] = True

    st.session_state[seed_marker] = True
    return form_key


def clear_employee_resource_form_state(form_key: str | None = None) -> None:
    keys = [k for k in st.session_state.keys() if str(k).startswith("ips_er_form_")]
    for key in keys:
        if form_key and not str(key).startswith(f"ips_er_form_{form_key}_") and not str(key).startswith(
            f"ips_er_form_seeded_{form_key}_"
        ):
            continue
        st.session_state.pop(key, None)


def _delivery_from_label(label: str) -> str:
    if label == _DELIVERY_LABELS[_DELIVERY_FILE]:
        return _DELIVERY_FILE
    return _DELIVERY_LINK


def render_employee_resource_form(
    resource: dict[str, Any] | None,
    *,
    permissions: EmployeeResourcesPermissions,
    on_saved: Callable[[str], None],
    on_cancel: Callable[[], None],
) -> None:
    from app.perf_debug import perf_span

    _ = permissions
    form_key = seed_employee_resource_form(resource)
    prefix = f"ips_er_form_{form_key}_"

    with perf_span("employee_resources.admin.form"):
        title = st.text_input("Title", key=f"{prefix}title")
        category = st.selectbox("Resource type", RESOURCE_TYPES, key=f"{prefix}category")
        description = st.text_area("Description", key=f"{prefix}desc")
        delivery_label = st.radio(
            "Attachment",
            _DELIVERY_OPTIONS,
            horizontal=True,
            key=f"{prefix}delivery",
        )
        delivery = _delivery_from_label(str(delivery_label))
        if delivery == _DELIVERY_LINK:
            link_url = st.text_input("URL", key=f"{prefix}url")
            storage_key = ""
        else:
            link_url = ""
            storage_key = st.text_input(
                "Storage file path",
                key=f"{prefix}path",
                help="Administrative storage path (no local upload on this form).",
            )
        roles = st.multiselect("Visible to roles", list(ROLE_VISIBILITY_OPTIONS), key=f"{prefix}roles")
        sort_order = st.number_input("Sort order", min_value=0, key=f"{prefix}sort")
        is_active = st.checkbox("Active", key=f"{prefix}active")

        c1, c2 = st.columns(2)
        with c1:
            save = st.button("Save resource", type="primary", use_container_width=True, key=f"{prefix}save")
        with c2:
            cancel = st.button("Cancel", use_container_width=True, key=f"{prefix}cancel")

    if cancel:
        on_cancel()
        return

    if not save:
        return

    payload: dict[str, Any] = {
        "title": str(title or "").strip(),
        "category": category,
        "description": str(description or "").strip(),
        "visible_to_roles": ",".join(str(r).strip() for r in roles if str(r).strip()),
        "sort_order": int(sort_order),
        "is_active": bool(is_active),
    }
    if delivery == _DELIVERY_LINK:
        payload["resource_type"] = "link"
        payload["url"] = str(link_url or "").strip()
    else:
        payload["resource_type"] = "file"
        payload["file_path"] = str(storage_key or "").strip()
        path = payload["file_path"]
        payload["file_name"] = path.split("/")[-1] if path else ""

    errors = validate_employee_resource_payload(payload)
    if errors:
        st.error(errors[0])
        return

    with perf_span("employee_resources.save"):
        result = save_employee_resource(payload, row_id=str(resource.get("id")) if resource else None)

    if not result.ok:
        st.error(str(result.error or "Could not save resource."))
        return

    saved_id = str(resource.get("id") or "") if resource else ""
    if not saved_id and isinstance(result.data, dict):
        saved_id = str(result.data.get("id") or "")
    clear_employee_resource_form_state(form_key)
    on_saved(saved_id)
    st.success("Resource saved.")
    ips_app_rerun()
