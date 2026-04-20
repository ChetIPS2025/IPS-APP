from __future__ import annotations

import html

import streamlit as st

_DEF_SPACER = [4, 1, 1]


def modal_subtitle(text: str) -> None:
    st.markdown(
        f'<p class="ips-modal-subtitle">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )


def modal_hint(text: str) -> None:
    st.markdown(
        f'<p class="ips-modal-hint">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )


def modal_header(*, subtitle: str | None = None, hint: str | None = None) -> None:
    if subtitle:
        modal_subtitle(subtitle)
    if hint:
        modal_hint(hint)


def modal_footer(*, cancel_key: str, save_key: str, save_label: str = "Save") -> tuple[bool, bool]:
    st.divider()
    sp, fc, fs = st.columns(_DEF_SPACER, gap="small")
    with sp:
        st.empty()
    with fc:
        cancel = st.button("Cancel", type="secondary", use_container_width=True, key=cancel_key)
    with fs:
        save = st.button(save_label, type="primary", use_container_width=True, key=save_key)
    return cancel, save
