"""Shared pagination helpers for large Streamlit catalog tables."""

from __future__ import annotations

import streamlit as st

DEFAULT_CATALOG_PAGE_SIZE = 75
_PAGE_SIZE_OPTIONS = (50, 75, 100, 150)


def page_key(table_key: str) -> str:
    return f"ips_pg_page_{table_key}"


def page_size_key(table_key: str) -> str:
    return f"ips_pg_size_{table_key}"


def reset_table_page(table_key: str) -> None:
    st.session_state[page_key(table_key)] = 1


def pagination_meta(
    total: int,
    table_key: str,
    *,
    default_page_size: int = DEFAULT_CATALOG_PAGE_SIZE,
) -> tuple[int, int, int]:
    """Return (page, page_size, total_pages) and persist clamped page in session state."""
    size_raw = int(st.session_state.get(page_size_key(table_key), default_page_size))
    page_size = max(10, min(200, size_raw))
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    page = int(st.session_state.get(page_key(table_key), 1))
    page = max(1, min(page, total_pages))
    st.session_state[page_key(table_key)] = page
    return page, page_size, total_pages


def paginate_rows(
    rows: list,
    table_key: str,
    *,
    default_page_size: int = DEFAULT_CATALOG_PAGE_SIZE,
) -> tuple[list, int, int, int]:
    """Return a page slice plus (page, page_size, total_pages)."""
    page, page_size, total_pages = pagination_meta(len(rows), table_key, default_page_size=default_page_size)
    start = (page - 1) * page_size
    return rows[start : start + page_size], page, page_size, total_pages


def render_table_pagination_controls(
    total: int,
    table_key: str,
    *,
    item_label: str = "row",
) -> tuple[int, int, int]:
    """Render page controls; returns (page, page_size, total_pages)."""
    page, page_size, total_pages = pagination_meta(total, table_key)

    c1, c2, c3, c4 = st.columns([1.2, 1.0, 1.0, 1.8], gap="small")
    with c1:
        st.caption(
            f"{total:,} {item_label}{'' if total == 1 else 's'}"
            + (f" · page {page} of {total_pages}" if total_pages > 1 else "")
        )
    with c2:
        if st.button(
            "Previous",
            key=f"{table_key}_pg_prev",
            disabled=page <= 1,
            use_container_width=True,
        ):
            st.session_state[page_key(table_key)] = max(1, page - 1)
            st.rerun()
    with c3:
        if st.button(
            "Next",
            key=f"{table_key}_pg_next",
            disabled=page >= total_pages,
            use_container_width=True,
        ):
            st.session_state[page_key(table_key)] = min(total_pages, page + 1)
            st.rerun()
    with c4:
        picked = st.selectbox(
            "Rows per page",
            list(_PAGE_SIZE_OPTIONS),
            index=_PAGE_SIZE_OPTIONS.index(page_size)
            if page_size in _PAGE_SIZE_OPTIONS
            else _PAGE_SIZE_OPTIONS.index(DEFAULT_CATALOG_PAGE_SIZE),
            key=f"{table_key}_pg_size_select",
            label_visibility="collapsed",
        )
        if int(picked) != page_size:
            st.session_state[page_size_key(table_key)] = int(picked)
            reset_table_page(table_key)
            st.rerun()

    return page, page_size, total_pages
