"""
Shared CSS and helpers for selectable HTML grid table rows (Jobs, Estimates, Users, etc.).

Inject via :func:`inject_clean_table_css` on every app render so row styling survives
navigation/rerun when page-local injectors use session-state guards.
"""

from __future__ import annotations

import html
import inspect
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

IPS_CLEAN_TABLE_STYLE_ID = "ips-clean-table-global-v1"

# Table scope markers (host card / list)
TABLE_SCOPE_SELECTORS = (
    ".ips-clean-table",
    ".jdb-tbl-host",
    ".ips-est-table-anchor",
    ".ips-users-table-anchor",
    ".ips-assets-table-anchor",
    ".ips-inv-table-anchor",
)

# Per-row Streamlit host markers
ROW_WRAP_SELECTORS = (
    ".ips-clean-row-wrap",
    ".job-row-wrap",
    ".ips-est-list-row-wrap",
    ".usr-row-wrap",
)

ROW_SELECT_BTN_MARKERS = (
    ".ips-clean-row-select-btn",
    ".jdb-row-select-btn",
    ".ips-est-list-row-select-btn",
    ".usr-row-select-btn",
)

ACTIONS_MARKERS = (
    ".ips-clean-actions",
    ".jdb-row-actions",
    ".ips-est-list-actcol",
    ".usr-actcol",
)

# HTML row classes (legacy aliases included)
ROW_HTML_SELECTORS = (
    ".ips-clean-row",
    ".job-row",
    ".ips-est-list-row",
    ".usr-row",
    ".est-row",
)

ROW_SELECTED_SELECTORS = (
    ".ips-clean-row.selected",
    ".ips-clean-row-selected",
    ".job-row.selected",
    ".ips-est-list-row.is-selected",
    ".usr-row.selected",
    ".ips-inv-row-selected",
)

HIDDEN_MARKERS = (
    ".ips-clean-row-wrap",
    ".ips-clean-row-select-btn",
    ".ips-clean-actions",
    ".ips-clean-click-bridge",
    ".job-row-wrap",
    ".jdb-row-actions",
    ".jdb-click-bridge",
    ".ips-est-list-row-wrap",
    ".ips-est-list-row-select-btn",
    ".ips-est-list-actcol",
    ".usr-row-wrap",
    ".usr-row-select-btn",
    ".usr-actcol",
)


def _css_join(selectors: tuple[str, ...]) -> str:
    return ",\n".join(selectors)


def _vb_has_row_wrap() -> str:
    parts = [f'div[data-testid="stVerticalBlock"]:has({s})' for s in ROW_WRAP_SELECTORS]
    return _css_join(tuple(parts))


def _table_scope_has() -> str:
    return (
        "section[data-testid=\"stMain\"] "
        f'div[data-testid="stVerticalBlockBorderWrapper"]:has({_css_join(TABLE_SCOPE_SELECTORS)})'
    )


def inject_clean_table_css() -> None:
    """Inject global clean table row CSS (no session guard — safe on every rerun)."""
    tbl = _table_scope_has()
    vb_wrap = _vb_has_row_wrap()
    rows = _css_join(ROW_HTML_SELECTORS)
    selected = _css_join(ROW_SELECTED_SELECTORS)
    row_sel_markers = _css_join(ROW_SELECT_BTN_MARKERS)
    act_markers = _css_join(ACTIONS_MARKERS)
    hidden = _css_join(HIDDEN_MARKERS)

    st.markdown(
        f"""
<style id="{IPS_CLEAN_TABLE_STYLE_ID}">
/* ── Base grid row / header (ips-clean-* + legacy aliases) ── */
.ips-clean-header,
.ips-clean-row,
{_css_join(ROW_HTML_SELECTORS)} {{
    display: grid;
    align-items: center;
    column-gap: 16px;
    box-sizing: border-box;
}}
.ips-clean-row,
{rows} {{
    min-height: 60px;
    padding: 10px 16px;
    background: #ffffff;
    border-bottom: 1px solid #e5eaf2;
    border-left: 4px solid transparent;
    cursor: pointer;
    transition: background 0.12s ease, border-color 0.12s ease;
}}
.ips-clean-row:hover,
{rows}:hover {{
    background: #f8fbff;
}}
.ips-clean-row-selected,
.ips-clean-row.selected,
{selected} {{
    background: #eef5ff !important;
    border-left: 4px solid #2563eb !important;
}}
.ips-clean-link,
.job-number,
.ips-est-list-qnum,
.usr-name-cell {{
    color: #2563eb;
    font-weight: 700;
    background: transparent !important;
    border: none !important;
    text-decoration: none !important;
}}
.ips-clean-title,
.job-project {{
    font-weight: 700;
}}
.ips-clean-actions {{
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
}}
.ips-clean-action-btn,
.ips-clean-actions button {{
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    max-width: 38px !important;
    min-height: 38px !important;
    max-height: 38px !important;
    padding: 0 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    border: 1px solid #e5eaf2 !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 0.95rem !important;
    line-height: 1 !important;
}}
.ips-clean-action-btn:hover,
.ips-clean-actions button:hover {{
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
}}

/* ── Flatten nested row cards inside list tables ── */
{tbl}
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has({_css_join(TABLE_SCOPE_SELECTORS)})) {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}}
{tbl}
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has({_css_join(TABLE_SCOPE_SELECTORS)})) > div {{
    padding: 0 !important;
}}
{tbl} [data-testid="stVerticalBlock"] {{
    gap: 0 !important;
}}

/* ── Row host: single visible HTML row; overlays do not add gray bars ── */
{vb_wrap} {{
    position: relative !important;
    min-height: 60px !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}}
{vb_wrap} > [data-testid="stElementContainer"] {{
    margin: 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}

/* Invisible row-select Streamlit button: out of document flow */
{vb_wrap}
    > [data-testid="stElementContainer"]:has({row_sel_markers})
    + [data-testid="stElementContainer"]:has(.stButton) {{
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 120px !important;
    bottom: 0 !important;
    z-index: 1 !important;
    height: 60px !important;
    max-height: 60px !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    pointer-events: auto !important;
}}
{vb_wrap}
    > [data-testid="stElementContainer"]:has({row_sel_markers})
    + [data-testid="stElementContainer"]:has(.stButton) .stButton,
{vb_wrap}
    > [data-testid="stElementContainer"]:has({row_sel_markers})
    + [data-testid="stElementContainer"]:has(.stButton) .stButton > button {{
    width: 100% !important;
    height: 60px !important;
    min-height: 60px !important;
    max-height: 60px !important;
    margin: 0 !important;
    padding: 0 !important;
    opacity: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    cursor: pointer !important;
}}

/* Action column overlay (compact 38px buttons) */
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] {{
    position: absolute !important;
    top: 0 !important;
    right: 10px !important;
    width: 86px !important;
    height: 60px !important;
    max-height: 60px !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    z-index: 3 !important;
    pointer-events: none !important;
}}
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {{
    height: 60px !important;
    align-items: center !important;
    justify-content: flex-end !important;
    gap: 8px !important;
    min-height: 0 !important;
    background: transparent !important;
    pointer-events: auto !important;
}}
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] [data-testid="column"] {{
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
    padding: 0 !important;
}}
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] .stButton,
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] [data-testid="stButton"],
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] [data-testid="stPopover"] {{
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
}}
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] .stButton > button,
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] [data-testid="stPopover"] > button {{
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    max-width: 38px !important;
    min-height: 38px !important;
    max-height: 38px !important;
    padding: 0 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    border: 1px solid #e5eaf2 !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 0.95rem !important;
    line-height: 1 !important;
    color: #374151 !important;
}}
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] .stButton > button:hover,
{vb_wrap}
    > [data-testid="stElementContainer"]:has({act_markers})
    + [data-testid="stElementContainer"] [data-testid="stPopover"] > button:hover {{
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
}}

/* Suppress full-width gray bars: any stray button row inside row host */
{vb_wrap}
    > [data-testid="stElementContainer"]:has(.stButton):not(:has({act_markers})) {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}

/* Zero markdown margins inside tables */
{tbl} .stMarkdown,
{tbl} .stMarkdown p {{
    margin: 0 !important;
}}

/* Click-bridge iframe: no layout footprint */
section[data-testid="stMain"] [data-testid="stElementContainer"]:has(.ips-clean-click-bridge),
section[data-testid="stMain"] [data-testid="stElementContainer"]:has(.jdb-click-bridge) {{
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    border: none !important;
    background: transparent !important;
}}

/* Hide helper markers */
{hidden} {{
    display: none !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def _components_html(html_content: str, *, component_key: str, height: int = 0) -> Any:
    """Call ``components.html``; pass ``key`` when the installed Streamlit supports it."""
    kwargs: dict[str, Any] = {"height": height}
    if "key" in inspect.signature(components.html).parameters:
        kwargs["key"] = component_key
    try:
        return components.html(html_content, **kwargs)
    except TypeError:
        kwargs.pop("key", None)
        return components.html(html_content, **kwargs)


def render_clean_table_click_bridge(
    *,
    table_selector: str,
    row_selector: str,
    component_key: str = "ips_clean_table_click_bridge",
) -> Any:
    """
    Zero-height bridge: clicks on ``row_selector`` inside ``table_selector`` post row id.

    Row elements must expose the id via ``data-row-id`` or ``data-jid`` attribute.
    ``component_key`` must be unique per table on a page (used for Streamlit widget identity
    and the in-page click-handler registry).
    """
    key_attr = html.escape(component_key, quote=True)
    st.markdown(
        f'<span class="ips-clean-click-bridge" data-bridge-key="{key_attr}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    tbl = html.escape(table_selector, quote=True)
    row = html.escape(row_selector, quote=True)
    key_esc = html.escape(component_key, quote=True)
    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = "ipsCleanTableClick::{key_esc}";
  if (!doc.ipsCleanTableBridgeRegistry) {{
    doc.ipsCleanTableBridgeRegistry = {{}};
    doc.addEventListener("click", function (e) {{
      const t = e.target;
      if (!t || !t.closest) return;
      if (t.closest("[data-testid='stButton'], button, a, input, select, textarea, label, [data-testid='stPopover']")) return;
      const reg = doc.ipsCleanTableBridgeRegistry || {{}};
      for (const cfg of Object.values(reg)) {{
        const row = t.closest(cfg.tbl + " " + cfg.row);
        if (!row) continue;
        const id = row.getAttribute("data-row-id") || row.getAttribute("data-jid") || row.getAttribute("data-est-id");
        if (!id) continue;
        window.postMessage({{ type: "streamlit:setComponentValue", value: id }}, "*");
        return;
      }}
    }}, true);
  }}
  doc.ipsCleanTableBridgeRegistry[hookKey] = {{ tbl: "{tbl}", row: "{row}" }};
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )
