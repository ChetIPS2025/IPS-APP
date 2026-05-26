"""Shared pagination helpers for large Streamlit catalog tables."""

from __future__ import annotations

import streamlit as st

DEFAULT_CATALOG_PAGE_SIZE = 75
_PAGE_SIZE_OPTIONS = (50, 75, 100, 150)
_PAGINATION_CSS_KEY = "_ips_table_pagination_css"


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


def _inject_pagination_css() -> None:
    if st.session_state.get(_PAGINATION_CSS_KEY):
        return
    st.session_state[_PAGINATION_CSS_KEY] = True
    st.markdown(
        """
<style id="ips-table-pagination-v1">
[class*="st-key-"][class*="_pg_footer"] {
  margin-top: 0.75rem;
  padding-top: 0.25rem;
}
[class*="st-key-"][class*="_pg_footer"] [data-testid="stButton"] > button {
  background: #1d4ed8 !important;
  background-color: #1d4ed8 !important;
  color: #ffffff !important;
  border: 1px solid #1e40af !important;
  border-radius: 8px !important;
  font-weight: 700 !important;
  min-height: 2.5rem !important;
  box-shadow: none !important;
}
[class*="st-key-"][class*="_pg_footer"] [data-testid="stButton"] > button:hover:not(:disabled) {
  background: #1e40af !important;
  background-color: #1e40af !important;
  border-color: #1e3a8a !important;
  color: #ffffff !important;
}
[class*="st-key-"][class*="_pg_footer"] [data-testid="stButton"] > button:disabled {
  background: #94a3b8 !important;
  background-color: #94a3b8 !important;
  border-color: #94a3b8 !important;
  color: #f8fafc !important;
  opacity: 1 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_table_pagination_header(
    total: int,
    table_key: str,
    *,
    item_label: str = "row",
) -> tuple[int, int, int]:
    """Render count caption and rows-per-page selector above the table."""
    page, page_size, total_pages = pagination_meta(total, table_key)

    c1, c2 = st.columns([2.2, 1], gap="small")
    with c1:
        st.caption(
            f"{total:,} {item_label}{'' if total == 1 else 's'}"
            + (f" · page {page} of {total_pages}" if total_pages > 1 else "")
        )
    with c2:
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


def render_table_pagination_footer(total: int, table_key: str) -> None:
    """Render solid Previous/Next controls below the table."""
    page, _, total_pages = pagination_meta(total, table_key)
    if total_pages <= 1:
        return

    _inject_pagination_css()
    with st.container(key=f"{table_key}_pg_footer"):
        st.markdown(
            '<span class="ips-table-pagination-footer-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        _, prev_col, next_col, _ = st.columns([2.5, 1, 1, 2.5], gap="small")
        with prev_col:
            if st.button(
                "Previous",
                key=f"{table_key}_pg_prev",
                type="primary",
                disabled=page <= 1,
                use_container_width=True,
            ):
                st.session_state[page_key(table_key)] = max(1, page - 1)
                st.rerun()
        with next_col:
            if st.button(
                "Next",
                key=f"{table_key}_pg_next",
                type="primary",
                disabled=page >= total_pages,
                use_container_width=True,
            ):
                st.session_state[page_key(table_key)] = min(total_pages, page + 1)
                st.rerun()


def render_table_pagination_controls(
    total: int,
    table_key: str,
    *,
    item_label: str = "row",
) -> tuple[int, int, int]:
    """Backward-compatible alias for header-only pagination controls."""
    return render_table_pagination_header(total, table_key, item_label=item_label)
