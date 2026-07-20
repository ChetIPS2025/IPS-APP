"""Tab-scoped CSS injection for the Assets page."""

from __future__ import annotations

import streamlit as st

from app.components.assets_css_blocks import (
    LAYOUT_EQUIPMENT_CSS,
    LAYOUT_SHELL_CSS,
    MODULE_EQUIPMENT_CSS,
    MODULE_SHARED_CSS,
    PAGE_CHROME_CSS,
    PAGE_DETAIL_CSS,
    PAGE_EQUIPMENT_CSS,
)
from app.ui.css_inject import inject_css_once

_EQUIPMENT_TAB = "Equipment"
_SERIALIZED_TAB = "Serialized Tools"
_HAND_TOOLS_TAB = "Small Tools"

# Small Hand Tools tab — HTML table layout (matches Serialized Tools).
HAND_TOOLS_HTML_TABLE_CSS = """
.st-key-assets_table_wrap:has(.ips-hand-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type {
  display: grid !important;
  grid-template-columns:
    68px 240px 120px 72px 72px 150px 120px 112px 132px !important;
  column-gap: 0 !important;
  row-gap: 0 !important;
  align-items: center !important;
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
  padding: 0.45rem 0.65rem !important;
  margin: 0 !important;
  background: #f8fafc !important;
  border-bottom: 1px solid #e8edf4 !important;
}
.st-key-assets_table_wrap:has(.ips-hand-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
  flex: unset !important;
  min-width: 0 !important;
  max-width: none !important;
  overflow: hidden !important;
  padding: 0 10px !important;
  box-sizing: border-box !important;
}
.st-key-assets_table_wrap:has(.ips-hand-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child,
.st-key-assets_table_wrap:has(.ips-hand-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(2),
.st-key-assets_table_wrap:has(.ips-hand-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(4),
.st-key-assets_table_wrap:has(.ips-hand-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(5),
.st-key-assets_table_wrap:has(.ips-hand-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:last-child {
  padding: 0 !important;
}
.st-key-assets_table_wrap .ips-hand-tools-html-table .ips-hand-tool-text-cell {
  display: block !important;
  min-width: 0 !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.st-key-assets_table_wrap .ips-hand-tools-html-table .ips-hand-tool-qty-cell {
  font-variant-numeric: tabular-nums !important;
  white-space: nowrap !important;
}
.st-key-assets_table_wrap .ips-hand-tools-html-table .ips-hand-tool-action-link {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0.35rem 0.65rem !important;
  border-radius: 8px !important;
  background: #2563eb !important;
  color: #ffffff !important;
  font-size: 0.75rem !important;
  font-weight: 700 !important;
  text-decoration: none !important;
  white-space: nowrap !important;
}
.st-key-assets_table_wrap .ips-hand-tools-html-table .ips-hand-tool-action-link:hover {
  background: #1d4ed8 !important;
  color: #ffffff !important;
}
.st-key-hand_tools_open_button_harness,
.st-key-hand_tools_open_button_harness [data-testid="stVerticalBlock"],
.st-key-hand_tools_open_button_harness [data-testid="stElementContainer"] {
  display: block !important;
  width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_pg_header {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 0 0.35rem 0 !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_pg_header
[data-testid="stHorizontalBlock"] {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 12px !important;
  width: 100% !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_pg_header
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
  display: flex !important;
  justify-content: flex-end !important;
}
"""

# Back-compat alias for tests.
HAND_TOOLS_TABLE_GRID = (
    "68px 240px 120px 72px 72px 150px 120px 112px 132px"
)
HAND_TOOLS_TABLE_FIX_CSS = HAND_TOOLS_HTML_TABLE_CSS

SERIALIZED_TOOLS_TAB_CSS = """
.st-key-assets_table_wrap:has(.ips-serialized-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type {
  display: grid !important;
  grid-template-columns:
    44px 68px minmax(160px, 2.2fr) minmax(160px, 1fr) minmax(100px, 0.95fr)
    minmax(110px, 1fr) minmax(100px, 0.95fr) minmax(100px, 0.85fr) minmax(90px, 0.8fr) !important;
  column-gap: 0 !important;
  row-gap: 0 !important;
  align-items: center !important;
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
  padding: 0.45rem 0.65rem !important;
  margin: 0 !important;
  background: #f8fafc !important;
  border-bottom: 1px solid #e8edf4 !important;
}
.st-key-assets_table_wrap:has(.ips-serialized-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
  flex: unset !important;
  min-width: 0 !important;
  max-width: none !important;
  overflow: hidden !important;
  padding: 0 10px !important;
  box-sizing: border-box !important;
}
.st-key-assets_table_wrap:has(.ips-serialized-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child,
.st-key-assets_table_wrap:has(.ips-serialized-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(2),
.st-key-assets_table_wrap:has(.ips-serialized-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(3),
.st-key-assets_table_wrap:has(.ips-serialized-tools-html-table)
[data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(5) {
  padding: 0 !important;
}
.st-key-assets_table_wrap .ips-serialized-tools-html-table .ips-serialized-tool-text-cell {
  display: block !important;
  min-width: 0 !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.st-key-assets_table_wrap .ips-serialized-tools-html-table .ips-serialized-tool-row-select {
  width: 16px !important;
  height: 16px !important;
  margin: 0 !important;
  cursor: pointer !important;
  accent-color: #2563eb !important;
}
.st-key-serialized_tools_open_button_harness,
.st-key-serialized_tools_open_button_harness [data-testid="stVerticalBlock"],
.st-key-serialized_tools_open_button_harness [data-testid="stElementContainer"] {
  display: block !important;
  width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
"""


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
    from app.ui.page_shell import inject_ips_dashboard_layout

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
        "ips-assets-serialized-v2",
        "\n\n".join(
            (
                LAYOUT_EQUIPMENT_CSS,
                MODULE_EQUIPMENT_CSS,
                PAGE_EQUIPMENT_CSS,
                SERIALIZED_TOOLS_TAB_CSS,
            )
        ),
    )


def inject_assets_hand_tools_css() -> None:
    _inject_sidebar_css(
        "ips-assets-hand-tools-v7",
        "\n\n".join(
            (
                LAYOUT_EQUIPMENT_CSS,
                MODULE_EQUIPMENT_CSS,
                HAND_TOOLS_HTML_TABLE_CSS,
            )
        ),
    )


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
