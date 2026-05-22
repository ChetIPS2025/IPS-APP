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

IPS_CLEAN_TABLE_STYLE_ID = "ips-clean-table-global-v5"

# Table scope markers (host card / list)
TABLE_SCOPE_SELECTORS = (
    ".ips-clean-table",
    ".ips-data-table-anchor",
    ".jdb-tbl-host",
    ".ips-est-table-anchor",
    ".ips-users-table-anchor",
    ".ips-assets-table-anchor",
    ".ips-assets-click-table",
    ".ips-jobs-click-table",
    ".ips-inv-table-anchor",
    ".ips-time-table-anchor",
)

# Per-row Streamlit host markers
ROW_WRAP_SELECTORS = (
    ".ips-clean-row-host",
    ".ips-clean-row-wrap",
    ".job-row-wrap",
    ".ips-est-list-row-wrap",
    ".usr-row-wrap",
    ".ips-assets-row-wrap",
    ".ips-tk-row-wrap",
)

ROW_SELECT_BTN_MARKERS = (
    ".ips-clean-row-select-btn",
    ".jdb-row-select-btn",
    ".ips-est-list-row-select-btn",
    ".usr-row-select-btn",
    ".ips-assets-row-select-btn",
    ".ips-tk-row-select-btn",
)

ACTIONS_MARKERS = (
    ".ips-clean-actions",
    ".jdb-row-actions",
    ".ips-est-list-actcol",
    ".usr-actcol",
    ".ips-assets-actcol",
    ".ips-tk-actions",
)

# HTML row classes (legacy aliases included)
ROW_HTML_SELECTORS = (
    ".ips-clean-row",
    ".ips-data-row",
    ".job-row",
    ".job-row-host",
    ".ips-est-list-row",
    ".usr-row",
    ".est-row",
    ".ips-assets-row",
    ".ips-time-row",
)

ROW_SELECTED_SELECTORS = (
    ".ips-clean-row.selected",
    ".ips-clean-row-selected",
    ".ips-data-row.selected",
    ".job-row.selected",
    ".job-row-host.selected",
    ".ips-est-list-row.is-selected",
    ".usr-row.selected",
    ".ips-assets-row.selected",
    ".ips-time-row.selected",
    ".ips-inv-row-selected",
)

HIDDEN_MARKERS = (
    ".ips-clean-row-host",
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
    ".ips-assets-row-wrap",
    ".ips-assets-row-select-btn",
    ".ips-assets-actcol",
    ".ips-tk-row-wrap",
    ".ips-tk-row-select-btn",
    ".ips-tk-actions",
)


def _css_join(selectors: tuple[str, ...]) -> str:
    return ",\n".join(selectors)


def _vb_has_row_wrap() -> str:
    """Scope row-host overlay CSS to list tables only (not the whole page column)."""
    tbl = _table_scope_has()
    parts = [
        f'{tbl} div[data-testid="stVerticalBlock"]:has({s})'
        for s in ROW_WRAP_SELECTORS
    ]
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
    transition: background 0.15s ease, border-color 0.15s ease;
}}
.ips-clean-row:hover,
{rows}:hover {{
    background: #eef5ff;
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

/* Invisible row-select Streamlit button: full-row hit target under visual HTML row */
{vb_wrap} > [data-testid="stElementContainer"]:has({row_sel_markers})
    + [data-testid="stElementContainer"]:has([data-testid="stButton"]) {{
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
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
{vb_wrap}:has({act_markers})
    > [data-testid="stElementContainer"]:has({row_sel_markers})
    + [data-testid="stElementContainer"]:has([data-testid="stButton"]) {{
    right: 120px !important;
}}
{vb_wrap} > [data-testid="stElementContainer"]:has({row_sel_markers})
    + [data-testid="stElementContainer"]:has([data-testid="stButton"]) [data-testid="stButton"],
{vb_wrap} > [data-testid="stElementContainer"]:has({row_sel_markers})
    + [data-testid="stElementContainer"]:has([data-testid="stButton"]) [data-testid="stButton"] > button,
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

/* Visual HTML row sits above the invisible button and does not steal clicks */
{vb_wrap} > [data-testid="stElementContainer"]:has({rows}) {{
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 2 !important;
    pointer-events: none !important;
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
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

/* Company updates / event list cards (non-grid lists) */
.ips-update-card,
.ips-event-block {{
    cursor: pointer;
    transition: background 0.15s ease;
}}
.ips-update-card:hover,
.ips-event-block:hover {{
    background: #eef5ff;
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

  function sendValue(id) {{
    const payload = {{ type: "streamlit:setComponentValue", value: id }};
    try {{
      if (window.Streamlit && typeof window.Streamlit.setComponentValue === "function") {{
        window.Streamlit.setComponentValue(id);
      }}
    }} catch (err) {{}}
    try {{
      w.postMessage(payload, "*");
    }} catch (err) {{}}
    try {{
      window.postMessage(payload, "*");
    }} catch (err) {{}}
  }}

  function sendReady() {{
    w.postMessage({{ type: "streamlit:componentReady", apiVersion: 1 }}, "*");
  }}

  if (!doc.ipsCleanTableBridgeRegistry) {{
    doc.ipsCleanTableBridgeRegistry = {{}};
    doc.addEventListener("click", function (e) {{
      const t = e.target;
      if (!t || !t.closest) return;
      if (t.closest("[data-testid='stButton'], button, a, input, select, textarea, label, [data-testid='stPopover']")) return;
      const reg = doc.ipsCleanTableBridgeRegistry || {{}};
      for (const cfg of Object.values(reg)) {{
        const row = t.closest(cfg.row);
        if (!row) continue;
        if (cfg.tbl) {{
          const anchor = doc.querySelector(cfg.tbl);
          if (!anchor) continue;
          const scope = anchor.closest('div[data-testid="stVerticalBlockBorderWrapper"]');
          if (scope && !scope.contains(row)) continue;
        }}
        const id = row.getAttribute("data-row-id") || row.getAttribute("data-jid") || row.getAttribute("data-est-id");
        if (!id) continue;
        sendValue(id);
        return;
      }}
    }}, true);
  }}
  doc.ipsCleanTableBridgeRegistry[hookKey] = {{ tbl: "{tbl}", row: "{row}" }};
  sendReady();
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )


def apply_clean_table_row_selection(
    row_id: str,
    *,
    session_select_key: str,
    records_by_id: dict[str, dict[str, Any]],
    on_row_click: Any | None = None,
) -> None:
    """Store selected row id and rerun when selection changes."""
    rid = str(row_id or "").strip()
    if not rid or rid not in records_by_id:
        return
    prev = st.session_state.get(session_select_key)
    st.session_state[session_select_key] = rid
    if on_row_click:
        on_row_click(rid, records_by_id[rid])
    if prev != rid:
        st.rerun()
