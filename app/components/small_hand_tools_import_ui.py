"""Bulk CSV import dialog for Small Hand Tools on the Assets page."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.services.small_hand_tool_import_service import (
    bulk_import_hand_tools,
    hand_tool_csv_template_bytes,
    parse_hand_tool_csv,
    validate_hand_tool_import_rows,
)
HAND_TOOL_IMPORT_OPEN_KEY = "ips_hand_tool_import_open"
_HAND_TOOL_IMPORT_VALID_KEY = "_ips_hand_tool_import_valid"
_HAND_TOOL_IMPORT_INVALID_KEY = "_ips_hand_tool_import_invalid"
_HAND_TOOL_IMPORT_FILE_KEY = "_ips_hand_tool_import_file_name"


def open_hand_tool_import_dialog() -> None:
    st.session_state[HAND_TOOL_IMPORT_OPEN_KEY] = True
    st.session_state.pop(_HAND_TOOL_IMPORT_VALID_KEY, None)
    st.session_state.pop(_HAND_TOOL_IMPORT_INVALID_KEY, None)
    st.session_state.pop(_HAND_TOOL_IMPORT_FILE_KEY, None)


def close_hand_tool_import_dialog() -> None:
    st.session_state.pop(HAND_TOOL_IMPORT_OPEN_KEY, None)
    st.session_state.pop(_HAND_TOOL_IMPORT_VALID_KEY, None)
    st.session_state.pop(_HAND_TOOL_IMPORT_INVALID_KEY, None)
    st.session_state.pop(_HAND_TOOL_IMPORT_FILE_KEY, None)


def _preview_rows(valid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(v.get("_preview") or {}) for v in valid]


def render_hand_tool_import_dialog() -> None:
    st.markdown("### Import Small Hand Tools")
    st.caption(
        "Counted/audited tools — not checkout items. Required columns: **tool_name**, **expected_qty**. "
        "If **actual_qty** is blank, it defaults to **expected_qty**."
    )

    uploaded = st.file_uploader(
        "CSV or XLSX file",
        type=["csv", "xlsx", "xls"],
        key="ht_import_file",
    )

    if uploaded is not None:
        file_sig = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get(_HAND_TOOL_IMPORT_FILE_KEY) != file_sig:
            try:
                parsed = parse_hand_tool_csv(uploaded.getvalue(), uploaded.name)
                valid, invalid = validate_hand_tool_import_rows(parsed)
                st.session_state[_HAND_TOOL_IMPORT_VALID_KEY] = valid
                st.session_state[_HAND_TOOL_IMPORT_INVALID_KEY] = invalid
                st.session_state[_HAND_TOOL_IMPORT_FILE_KEY] = file_sig
            except Exception as exc:
                st.error(f"Could not read file: {exc}")
                st.session_state[_HAND_TOOL_IMPORT_VALID_KEY] = []
                st.session_state[_HAND_TOOL_IMPORT_INVALID_KEY] = []
                st.session_state[_HAND_TOOL_IMPORT_FILE_KEY] = None

    valid = list(st.session_state.get(_HAND_TOOL_IMPORT_VALID_KEY) or [])
    invalid = list(st.session_state.get(_HAND_TOOL_IMPORT_INVALID_KEY) or [])

    if uploaded is not None and st.session_state.get(_HAND_TOOL_IMPORT_FILE_KEY):
        st.markdown(f"**{len(valid)}** valid row(s) · **{len(invalid)}** row(s) with issues")
        if valid:
            st.markdown("##### Ready to import")
            st.dataframe(_preview_rows(valid), use_container_width=True, hide_index=True)
        if invalid:
            st.markdown("##### Rows with missing or invalid fields")
            st.dataframe(invalid, use_container_width=True, hide_index=True)

    confirm_disabled = not valid
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            f"Confirm import ({len(valid)})",
            type="primary",
            key="ht_import_confirm",
            use_container_width=True,
            disabled=confirm_disabled,
        ):
            result = bulk_import_hand_tools(valid)
            if result.ok:
                data = result.data or {}
                st.session_state["ht_import_success_message"] = str(
                    data.get("message") or f"Imported {data.get('created', 0)} tool(s)."
                )
                for err in (data.get("errors") or [])[:5]:
                    st.warning(str(err))
                close_hand_tool_import_dialog()
                st.rerun()
            st.error(result.error or "Import failed.")
    with c2:
        if st.button("Cancel", key="ht_import_cancel", use_container_width=True):
            close_hand_tool_import_dialog()
            st.rerun()


@st.dialog("Import Small Hand Tools", width="large", on_dismiss=close_hand_tool_import_dialog)
def show_hand_tool_import_dialog() -> None:
    render_hand_tool_import_dialog()


__all__ = [
    "HAND_TOOL_IMPORT_OPEN_KEY",
    "hand_tool_csv_template_bytes",
    "open_hand_tool_import_dialog",
    "render_hand_tool_import_dialog",
    "show_hand_tool_import_dialog",
]
