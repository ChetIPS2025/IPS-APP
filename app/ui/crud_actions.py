from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from app.ips_crud_list_styles import inject_ips_crud_list_styles
from app.table_actions import inject_table_action_styles


def render_standard_toolbar(
    *,
    selected_ids: list[str],
    can_add: bool,
    add_label: str = "Add",
    edit_label: str = "Edit",
    deactivate_label: str = "Deactivate",
    delete_label: str = "Delete",
    on_add: Callable[[], None] | None = None,
    on_edit: Callable[[str], None] | None = None,
    on_deactivate: Callable[[list[str]], None] | None = None,
    on_delete: Callable[[list[str]], None] | None = None,
    key_prefix: str = "crud",
) -> None:
    """IPS CRUD toolbar: summary + Add / Edit / Deactivate / Delete (matches ``ips-crud-toolbar-root`` styling)."""
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    n = len(selected_ids)
    one = n == 1
    none = n == 0

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0, b1, b2, b3 = st.columns([1.1, 1, 1, 1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b0:
            if st.button(add_label, type="primary", use_container_width=True, disabled=not can_add, key=f"{key_prefix}_add"):
                if on_add:
                    on_add()
        with b1:
            if st.button(edit_label, type="secondary", use_container_width=True, disabled=not can_add or not one, key=f"{key_prefix}_edit"):
                if on_edit and one:
                    on_edit(str(selected_ids[0]))
        with b2:
            if st.button(deactivate_label, type="secondary", use_container_width=True, disabled=not can_add or none, key=f"{key_prefix}_deactivate"):
                if on_deactivate and selected_ids:
                    on_deactivate(selected_ids)
        with b3:
            if st.button(delete_label, type="secondary", use_container_width=True, disabled=not can_add or none, key=f"{key_prefix}_delete"):
                if on_delete and selected_ids:
                    on_delete(selected_ids)
