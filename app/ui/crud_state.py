from __future__ import annotations

import streamlit as st


def view_key(entity: str) -> str:
    return f"{entity}_view"


def mode_key(entity: str) -> str:
    return f"{entity}_mode"


def edit_id_key(entity: str) -> str:
    return f"{entity}_edit_id"


def selected_id_key(entity: str) -> str:
    return f"{entity}_selected_id"


def init_crud_state(entity: str, *, default_view: str = "list") -> None:
    st.session_state.setdefault(view_key(entity), default_view)


def get_view(entity: str, *, default: str = "list") -> str:
    return str(st.session_state.get(view_key(entity), default) or default)


def set_view(entity: str, value: str) -> None:
    st.session_state[view_key(entity)] = value


def get_mode(entity: str) -> str | None:
    raw = st.session_state.get(mode_key(entity))
    return str(raw) if raw is not None else None


def set_mode(entity: str, value: str | None) -> None:
    if value is None:
        st.session_state.pop(mode_key(entity), None)
    else:
        st.session_state[mode_key(entity)] = value


def get_edit_id(entity: str) -> str | None:
    raw = st.session_state.get(edit_id_key(entity))
    s = str(raw or "").strip()
    return s or None


def set_edit_id(entity: str, value: str | None) -> None:
    if value is None:
        st.session_state.pop(edit_id_key(entity), None)
    else:
        st.session_state[edit_id_key(entity)] = str(value)


def clear_crud_state(entity: str) -> None:
    st.session_state.pop(mode_key(entity), None)
    st.session_state.pop(edit_id_key(entity), None)
    st.session_state.pop(selected_id_key(entity), None)
