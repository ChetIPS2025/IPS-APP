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
    PAGE_HAND_TOOLS_CSS,
)
from app.ui.css_inject import inject_css_once

_EQUIPMENT_TAB = "Equipment"
_SERIALIZED_TAB = "Serialized Tools"
_HAND_TOOLS_TAB = "Small Tools"

# Shared 8-column grid for Small Hand Tools header + data rows.
HAND_TOOLS_TABLE_GRID = (
    "minmax(320px, 3.4fr) "
    "minmax(130px, 1.1fr) "
    "minmax(80px, 0.65fr) "
    "minmax(80px, 0.65fr) "
    "minmax(150px, 1.25fr) "
    "minmax(140px, 1.1fr) "
    "minmax(120px, 0.9fr) "
    "minmax(135px, 0.9fr)"
)

# Small Hand Tools tab — unified grid, tool thumb+name column, readable headers.
HAND_TOOLS_TABLE_FIX_CSS = f"""
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_pg_header {{
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 0 0.35rem 0 !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_pg_header
[data-testid="stHorizontalBlock"] {{
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 12px !important;
  width: 100% !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_pg_header
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {{
  display: flex !important;
  justify-content: flex-end !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap {{
  --ips-hand-tools-grid: {HAND_TOOLS_TABLE_GRID};
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: auto !important;
  overflow-y: visible !important;
  -webkit-overflow-scrolling: touch !important;
  min-width: 0 !important;
  padding-right: 12px !important;
  box-sizing: border-box !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-header),
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) {{
  display: grid !important;
  grid-template-columns: var(--ips-hand-tools-grid) !important;
  column-gap: 0 !important;
  row-gap: 0 !important;
  align-items: center !important;
  min-height: 52px !important;
  width: 100% !important;
  min-width: 1180px !important;
  max-width: none !important;
  box-sizing: border-box !important;
  flex-wrap: nowrap !important;
  padding: 0 !important;
  margin: 0 !important;
  border-bottom: 1px solid #f1f5f9 !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-header) {{
  background: #f8fafc !important;
  border-bottom: 1px solid #e8edf4 !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-header) > [data-testid="column"],
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"] {{
  flex: none !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  overflow: visible !important;
  box-sizing: border-box !important;
  padding: 8px 10px !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-header) > [data-testid="column"]:last-child {{
  padding-right: 14px !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:first-child
> [data-testid="stVerticalBlock"],
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-header) > [data-testid="column"]:first-child
> [data-testid="stVerticalBlock"] {{
  display: grid !important;
  grid-template-columns: 40px minmax(0, 1fr) !important;
  align-items: center !important;
  gap: 10px !important;
  min-width: 0 !important;
  width: 100% !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-row-bridge {{
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
  pointer-events: none !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-tool-thumb {{
  grid-column: 1 !important;
  width: 40px !important;
  min-width: 40px !important;
  max-width: 40px !important;
  flex-shrink: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-tool-thumb .ips-asset-thumb-wrap,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-tool-thumb .ips-asset-thumb-img {{
  width: 36px !important;
  height: 36px !important;
  max-width: 36px !important;
  max-height: 36px !important;
  object-fit: contain !important;
  flex-shrink: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:first-child
.stButton {{
  grid-column: 2 !important;
  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  margin: 0 !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:first-child
.stButton > button {{
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  min-height: auto !important;
  height: auto !important;
  padding: 0 !important;
  margin: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #2563eb !important;
  font-weight: 700 !important;
  font-size: 0.8125rem !important;
  text-align: left !important;
  justify-content: flex-start !important;
  align-items: flex-start !important;
  white-space: normal !important;
  display: -webkit-box !important;
  -webkit-line-clamp: 2 !important;
  -webkit-box-orient: vertical !important;
  overflow: hidden !important;
  line-height: 1.25 !important;
  word-break: normal !important;
  overflow-wrap: anywhere !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:first-child
.stButton > button p,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:first-child
.stButton > button span,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:first-child
.stButton > button div {{
  color: #2563eb !important;
  font-weight: 700 !important;
  white-space: normal !important;
  display: -webkit-box !important;
  -webkit-line-clamp: 2 !important;
  -webkit-box-orient: vertical !important;
  overflow: hidden !important;
  line-height: 1.25 !important;
  text-align: left !important;
  word-break: normal !important;
  overflow-wrap: anywhere !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-tool-name-static {{
  grid-column: 2 !important;
  min-width: 0 !important;
  display: -webkit-box !important;
  -webkit-line-clamp: 2 !important;
  -webkit-box-orient: vertical !important;
  overflow: hidden !important;
  white-space: normal !important;
  line-height: 1.25 !important;
  color: #2563eb !important;
  font-weight: 700 !important;
  font-size: 0.8125rem !important;
  word-break: normal !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-header-tool {{
  grid-column: 1 / -1 !important;
  padding-left: 50px !important;
  text-align: left !important;
  justify-content: flex-start !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-header-cell,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-header-cell .ips-table-header-filter-text {{
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  line-height: 1.15 !important;
  min-width: 0 !important;
  word-break: normal !important;
  overflow-wrap: normal !important;
  font-size: 0.68rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.04em !important;
  text-transform: uppercase !important;
  color: #64748b !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-header-tool {{
  text-align: left !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-header) > [data-testid="column"]:not(:first-child)
.ips-hand-tools-header-cell {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 4px !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-header) > [data-testid="column"]
[data-testid="stHorizontalBlock"] {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 4px !important;
  min-width: 0 !important;
  width: 100% !important;
  overflow: visible !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-cell--category,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-cell--location,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-cell--storage {{
  min-width: 0 !important;
  white-space: normal !important;
  overflow: hidden !important;
  display: -webkit-box !important;
  -webkit-line-clamp: 2 !important;
  -webkit-box-orient: vertical !important;
  line-height: 1.25 !important;
  word-break: normal !important;
  overflow-wrap: anywhere !important;
  font-size: 0.8125rem !important;
  color: #334155 !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-cell--location {{
  color: #64748b !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-cell--qty {{
  text-align: center !important;
  white-space: nowrap !important;
  overflow: visible !important;
  font-size: 0.8125rem !important;
  font-variant-numeric: tabular-nums !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-cell--status {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  overflow: visible !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
.ips-hand-tools-cell--status .ips-asset-status-pill {{
  flex-shrink: 0 !important;
  white-space: nowrap !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
[data-testid="stVerticalBlock"],
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
[data-testid="stElementContainer"] {{
  width: 100% !important;
  min-width: 130px !important;
  overflow: visible !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
.stButton,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
.stPopover {{
  width: 100% !important;
  min-width: 130px !important;
}}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
[data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
button[data-testid="stBaseButton-popover"] {{
  width: 100% !important;
  min-width: 130px !important;
  white-space: nowrap !important;
}}
@media (max-width: 1279px) {{
  section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
  [data-testid="stHorizontalBlock"]:has(.small-tools-table-header),
  section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_hand_tools_table_wrap
  [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) {{
    min-width: 1180px !important;
  }}
}}
"""

# Serialized tools tab — same equipment table card + column-aligned filter row.
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
        "ips-assets-hand-tools-v6",
        "\n\n".join((PAGE_HAND_TOOLS_CSS, HAND_TOOLS_TABLE_FIX_CSS)),
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
