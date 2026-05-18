"""Modal/dialog wrappers."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def confirm_dialog(title: str, message: str, on_confirm: Callable[[], None], *, key: str) -> None:
    _ = title
    if st.session_state.get(key):
        st.warning(message)
        c1, c2 = st.columns(2)
        if c1.button("Confirm", key=f"{key}_yes", type="primary"):
            on_confirm()
            st.session_state[key] = False
            st.rerun()
        if c2.button("Cancel", key=f"{key}_no"):
            st.session_state[key] = False
            st.rerun()
