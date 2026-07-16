"""Tab-scoped CSS injection for the Assets page."""

from __future__ import annotations

import streamlit as st

from app.components.assets_css_blocks import (
    LAYOUT_EQUIPMENT_CSS,
    LAYOUT_SHELL_CSS,
    MODULE_EQUIPMENT_CSS,
    MODULE_SERIALIZED_CSS,
    MODULE_SHARED_CSS,
    PAGE_CHROME_CSS,
    PAGE_DETAIL_CSS,
    PAGE_EQUIPMENT_CSS,
    PAGE_HAND_TOOLS_CSS,
    PAGE_SERIALIZED_CSS,
)
from app.ui.css_inject import inject_css_once

_EQUIPMENT_TAB = "Equipment"
_SERIALIZED_TAB = "Serialized Tools"
_HAND_TOOLS_TAB = "Small Tools"


def _inject_sidebar_css(style_id: str, css: str) -> None:
    if not css.strip():
        return
    inject_css_once(style_id)
    with st.sidebar:
        st.markdown(
            f'<style id="{style_id}">\n{css}\n</style>',
            unsafe_allow_html=True,
        )


def inject_assets_shell_css() -> None:
    """Shared page chrome — filter bar, header actions, tabs container."""
    from app.ui.clean_table import inject_clean_table_css
    from app.ui.page_shell import inject_ips_dashboard_layout

    inject_clean_table_css()
    inject_ips_dashboard_layout()
    _inject_sidebar_css(
        "ips-assets-shell-v1",
        "\n\n".join((LAYOUT_SHELL_CSS, PAGE_CHROME_CSS)),
    )


def inject_assets_equipment_css() -> None:
    _inject_sidebar_css(
        "ips-assets-equipment-v1",
        "\n\n".join(
            (
                LAYOUT_EQUIPMENT_CSS,
                MODULE_EQUIPMENT_CSS,
                PAGE_EQUIPMENT_CSS,
            )
        ),
    )


def inject_assets_serialized_css() -> None:
    _inject_sidebar_css(
        "ips-assets-serialized-v1",
        "\n\n".join((MODULE_SERIALIZED_CSS, PAGE_SERIALIZED_CSS)),
    )


def inject_assets_hand_tools_css() -> None:
    _inject_sidebar_css("ips-assets-hand-tools-v1", PAGE_HAND_TOOLS_CSS)


def inject_assets_shared_module_css() -> None:
    _inject_sidebar_css("ips-assets-module-shared-v1", MODULE_SHARED_CSS)


def inject_assets_detail_css() -> None:
    _inject_sidebar_css("ips-assets-detail-v1", PAGE_DETAIL_CSS)


def inject_assets_page_css(active_tab: str, *, detail_open: bool = False) -> None:
    """Inject only the CSS bundles needed for the active Assets tab."""
    inject_assets_shell_css()
    inject_assets_shared_module_css()

    tab = str(active_tab or _EQUIPMENT_TAB).strip()
    if tab == _EQUIPMENT_TAB:
        inject_assets_equipment_css()
    elif tab == _SERIALIZED_TAB:
        inject_assets_serialized_css()
    elif tab == _HAND_TOOLS_TAB:
        inject_assets_hand_tools_css()
    else:
        inject_assets_equipment_css()

    if detail_open:
        inject_assets_detail_css()


__all__ = [
    "inject_assets_detail_css",
    "inject_assets_page_css",
    "inject_assets_shell_css",
]
