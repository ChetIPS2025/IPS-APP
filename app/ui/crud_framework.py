from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from app.branding import render_header
from app.ips_crud_list_styles import (
    IPS_CRUD_LIST_PAGE_GAP,
    IPS_CRUD_LIST_PAGE_SPLIT,
    inject_ips_crud_list_styles,
    render_crud_list_subtitle,
)


def render_crud_page(
    *,
    title: str,
    subtitle: str,
    panel_open: bool,
    main_body: Callable[[], None],
    side_body: Callable[[], None] | None = None,
    before_main: Callable[[], None] | None = None,
) -> None:
    """
    Branded CRUD shell: header, IPS list styles, subtitle, optional full-width block (e.g. delete
    confirmations), then main vs split columns when the side panel is open.
    """
    render_header(title)
    inject_ips_crud_list_styles()
    render_crud_list_subtitle(subtitle)
    if before_main is not None:
        before_main()

    if panel_open and side_body is not None:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            main_body()
        with side_col:
            side_body()
    else:
        main_body()
