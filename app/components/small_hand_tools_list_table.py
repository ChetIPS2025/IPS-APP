"""HTML small hand tools table with click bridge (matches Serialized Tools layout)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.services.catalog_images import CatalogImageContext, catalog_thumbnail_html

HAND_TOOLS_TABLE_LAST_ACTION_KEY = "hand_tools_list_last_action"


def hand_tools_bridge_button_key(row: dict[str, Any]) -> str:
    raw = str(row.get("id") or "tool").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw) or "tool"
    return f"ht_bridge_open_{safe}"


HAND_TOOLS_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("image", "IMAGE"),
    ("name", "TOOL"),
    ("category", "CATEGORY"),
    ("expected", "EXPECTED"),
    ("actual", "ACTUAL"),
    ("location", "LOCATION"),
    ("storage", "STORAGE"),
    ("status", "STATUS"),
    ("actions", "ACTIONS"),
)

HAND_TOOLS_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "image": 68,
    "name": 240,
    "category": 120,
    "expected": 72,
    "actual": 72,
    "location": 150,
    "storage": 120,
    "status": 112,
    "actions": 132,
}


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def _tool_link_html(row_id: str, label: str) -> str:
    text = html.escape(label)
    title = html.escape(label, quote=True)
    rid = html.escape(row_id, quote=True)
    return (
        f'<a class="ips-row-open-link ips-dash-est-link ips-inventory-desc-link '
        f'ips-assets-open-link ips-hand-tool-open-link" href="#" '
        f'data-row-id="{rid}" title="{title}">{text}</a>'
    )


def _tool_thumb_link_html(row_id: str, row: dict[str, Any], *, image_context: CatalogImageContext) -> str:
    rid = html.escape(row_id, quote=True)
    thumb = catalog_thumbnail_html(
        row,
        kind="small_tool",
        context=image_context,
        css_class="ips-inventory-thumb-img",
        cell_class="ips-inventory-image-cell",
        alt="Small tool image",
    )
    return (
        f'<a class="ips-inventory-thumb-cell-link ips-assets-open-link ips-hand-tool-open-link" '
        f'href="#" data-row-id="{rid}" title="View tool" aria-label="View tool">{thumb}</a>'
    )


def _status_pill_html(status: str) -> str:
    cls_map = {
        "Available": "ips-asset-status-available",
        "In Use": "ips-asset-status-assigned",
        "Low Stock": "ips-asset-status-maintenance-due",
        "Missing": "ips-asset-status-lost",
        "Damaged": "ips-asset-status-out-for-repair",
        "Out of Service": "ips-asset-status-retired",
        "Retired": "ips-asset-status-retired",
    }
    cls = cls_map.get(status, "ips-asset-status-available")
    return f'<span class="ips-asset-status-pill {cls}">{html.escape(status)}</span>'


def _actions_cell_html(row: dict[str, Any]) -> str:
    rid = str(row.get("id") or "").strip()
    editable = bool(row.get("editable", True))
    if not rid or not editable:
        return '<span class="ips-inventory-muted">—</span>'
    safe_rid = html.escape(rid, quote=True)
    return (
        f'<a class="ips-hand-tool-action-link ips-hand-tool-adjust-link" href="#" '
        f'data-row-id="{safe_rid}" data-st-action="adjust" title="Adjust count">Adjust count</a>'
    )


def build_hand_tools_html_table(
    rows: list[dict[str, Any]],
    *,
    image_context: CatalogImageContext,
) -> str:
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in HAND_TOOLS_TABLE_COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{HAND_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;'
            f'max-width:{HAND_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in HAND_TOOLS_TABLE_HEADERS
    ]

    body_rows: list[str] = []
    for row_idx, row in enumerate(rows):
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            continue

        name = str(row.get("tool_name") or "—").strip() or "—"
        category = str(row.get("category") or "—").strip() or "—"
        qty_exp = row.get("quantity_expected") or 0
        qty_act = row.get("quantity_on_hand") or 0
        location = str(row.get("location_display") or "—").strip() or "—"
        storage = str(row.get("storage_type") or "—").strip() or "—"
        status = str(row.get("status") or "—").strip() or "—"
        qty_short = float(qty_act) < float(qty_exp)
        actual_cls = " ips-assets-qty-short" if qty_short else ""

        row_parity = "even" if row_idx % 2 else "odd"
        cells = [
            (
                "image",
                "center",
                _cell_wrapper(
                    _tool_thumb_link_html(row_id, row, image_context=image_context),
                    extra_class="ips-inventory-image-td",
                    align="center",
                ),
            ),
            (
                "name",
                "left",
                _cell_wrapper(
                    _tool_link_html(row_id, name if name != "—" else "View tool"),
                    extra_class="ips-dash-est-desc-cell",
                ),
            ),
            (
                "category",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-text-cell ips-hand-tool-text-cell">'
                    f"{html.escape(category)}</span>"
                ),
            ),
            (
                "expected",
                "center",
                _cell_wrapper(
                    f'<span class="ips-hand-tool-qty-cell">{html.escape(f"{float(qty_exp):g}")}</span>',
                    align="center",
                ),
            ),
            (
                "actual",
                "center",
                _cell_wrapper(
                    f'<span class="ips-hand-tool-qty-cell{actual_cls}">'
                    f"<strong>{html.escape(f'{float(qty_act):g}')}</strong></span>",
                    align="center",
                ),
            ),
            (
                "location",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-muted ips-hand-tool-text-cell">'
                    f"{html.escape(location)}</span>"
                ),
            ),
            (
                "storage",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-muted ips-hand-tool-text-cell">'
                    f"{html.escape(storage)}</span>"
                ),
            ),
            (
                "status",
                "center",
                _cell_wrapper(
                    _status_pill_html(status),
                    extra_class="ips-dash-est-status-cell",
                    align="center",
                ),
            ),
            (
                "actions",
                "center",
                _cell_wrapper(_actions_cell_html(row), align="center"),
            ),
        ]

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{HAND_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;'
                f'max-width:{HAND_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity} ips-hand-tool-row" '
            f'data-row-id="{html.escape(row_id, quote=True)}" '
            f'data-bridge-key="{html.escape(hand_tools_bridge_button_key(row), quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(HAND_TOOLS_TABLE_COL_WIDTHS_PX.values())
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table ips-assets-html-equipment-table ips-hand-tools-html-table" '
        f'style="width:100%;min-width:{min_width}px;">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows) if body_rows else '<tr><td colspan=\"9\">No tools</td></tr>'}</tbody>"
        "</table>"
        "</div>"
    )


def handle_hand_tools_table_action(
    raw: str,
    row_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_row_fn: Callable[[str, dict[str, Any]], None],
    adjust_row_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(last_action_key) or ""):
        return
    st.session_state[last_action_key] = val

    action = "open"
    row_id = val
    if val.startswith("open:"):
        row_id = val.split(":", 1)[1].strip()
    elif val.startswith("adjust:"):
        action = "adjust"
        row_id = val.split(":", 1)[1].strip()

    if not row_id:
        return
    row = row_by_id.get(row_id)
    if not row:
        return
    if action == "adjust":
        adjust_row_fn(row_id, row)
        st.rerun()
    else:
        open_row_fn(row_id, row)
        st.rerun()


def render_hand_tools_table_open_buttons(
    rows: list[dict[str, Any]],
    *,
    open_row_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    with st.container(key="hand_tools_open_button_harness"):
        for row in rows:
            row_id = str(row.get("id") or "").strip()
            if not row_id:
                continue
            bridge_key = hand_tools_bridge_button_key(row)

            def _open(_row_id: str = row_id, _row: dict = row) -> None:
                open_row_fn(_row_id, _row)

            st.button("Open tool", key=bridge_key, type="tertiary", on_click=_open)


def render_hand_tools_table_open_bridge(*, component_key: str = "ips_hand_tools_open_bridge") -> str | None:
    from app.ui.clean_table import render_clean_table_click_bridge

    return render_clean_table_click_bridge(
        table_selector=".ips-hand-tools-html-table",
        row_selector=".ips-hand-tools-html-table tbody tr[data-row-id]",
        component_key=component_key,
    )


def render_hand_tools_table_bridge(
    *,
    component_key: str = "ips_hand_tools_list_bridge",
    hook_key: str = "ipsHandToolsList::action",
) -> str | None:
    from app.ui.clean_table import _components_html

    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const adjustSel = ".ips-hand-tools-html-table [data-st-action='adjust'][data-row-id]";

  function sendValue(action) {{
    const payload = {{ type: "streamlit:setComponentValue", value: action }};
    const frames = [window, window.parent, w].filter(function (f, i, arr) {{
      return f && arr.indexOf(f) === i;
    }});
    for (var i = 0; i < frames.length; i++) {{
      try {{
        if (frames[i].Streamlit && typeof frames[i].Streamlit.setComponentValue === "function") {{
          frames[i].Streamlit.setComponentValue(action);
          return;
        }}
      }} catch (err) {{}}
    }}
    for (var j = 0; j < frames.length; j++) {{
      try {{ frames[j].postMessage(payload, "*"); }} catch (err) {{}}
    }}
  }}

  function bindTargets() {{
    doc.querySelectorAll(adjustSel).forEach(function (el) {{
      if (el.dataset.ipsHtAdjustBound === "1") return;
      el.dataset.ipsHtAdjustBound = "1";
      el.addEventListener("click", function (e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = el.getAttribute("data-row-id");
        if (!id) return;
        sendValue("adjust:" + id);
      }}, true);
    }});
  }}

  if (!doc.ipsHandToolsTableRegistry) doc.ipsHandToolsTableRegistry = {{}};
  doc.ipsHandToolsTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsHandToolsTableBindObserver) {{
    doc.ipsHandToolsTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsHandToolsTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsHandToolsTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
  }}
  setTimeout(bindTargets, 0);
  setTimeout(bindTargets, 120);
  setTimeout(bindTargets, 400);
  try {{
    w.postMessage({{ type: "streamlit:componentReady", apiVersion: 1 }}, "*");
  }} catch (err) {{}}
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )


def render_hand_tools_table_bridge_legacy(
    row_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_hand_tools_list_bridge",
    hook_key: str = "ipsHandToolsList::action",
    last_action_key: str = HAND_TOOLS_TABLE_LAST_ACTION_KEY,
    open_row_fn: Callable[[str, dict[str, Any]], None],
    adjust_row_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    st.markdown(
        '<span class="ips-hand-tools-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked_open = render_hand_tools_table_open_bridge()
    if picked_open:
        row_id = str(picked_open).strip()
        row = row_by_id.get(row_id)
        if row:
            handle_hand_tools_table_action(
                row_id,
                row_by_id,
                last_action_key=last_action_key,
                open_row_fn=open_row_fn,
                adjust_row_fn=adjust_row_fn,
            )
            return
    picked = render_hand_tools_table_bridge(component_key=component_key, hook_key=hook_key)
    raw = str(picked or "").strip()
    if not raw:
        return
    handle_hand_tools_table_action(
        raw,
        row_by_id,
        last_action_key=last_action_key,
        open_row_fn=open_row_fn,
        adjust_row_fn=adjust_row_fn,
    )
