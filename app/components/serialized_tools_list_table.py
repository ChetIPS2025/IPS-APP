"""HTML serialized-tools table with native detail links (field mode uses expand bridge)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.components.assets_list_table import asset_detail_href, asset_status_pill_html
from app.services.catalog_images import catalog_thumbnail_html
from app.ui.streamlit_perf import fragment_rerun, ips_app_rerun

SERIALIZED_TOOLS_TABLE_LAST_ACTION_KEY = "serialized_tools_list_last_action"


def serialized_tool_detail_href(row: dict[str, Any]) -> str:
    """Native Asset Detail URL for a serialized tool or kit-item row."""
    detail_id = str(row.get("_detail_asset_id") or row.get("id") or "").strip()
    if not detail_id:
        return "#"
    tab = str(row.get("_detail_tab") or "").strip()
    if not tab and str(row.get("row_type") or "") == "kit_item":
        child_id = str(row.get("child_asset_id") or "").strip()
        if not child_id:
            tab = "kit"
            detail_id = str(row.get("parent_asset_id") or detail_id).strip()
    return asset_detail_href(detail_id, tab=tab)


def serialized_tools_bridge_button_key(row: dict[str, Any]) -> str:
    raw = str(row.get("_row_id") or row.get("id") or "tool").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw) or "tool"
    return f"st_bridge_open_{safe}"


SERIALIZED_TOOLS_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("select", ""),
    ("image", "IMAGE"),
    ("name", "TOOL"),
    ("model", "MODEL #"),
    ("serial", "SERIAL"),
    ("trailer", "TRAILER"),
    ("job", "JOB"),
    ("status", "STATUS"),
    ("condition", "CONDITION"),
)

SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "select": 44,
    "image": 68,
    "name": 220,
    "model": 160,
    "serial": 120,
    "trailer": 130,
    "job": 110,
    "status": 112,
    "condition": 96,
}


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def _tool_link_html(row: dict[str, Any], label: str) -> str:
    text = html.escape(label)
    title = html.escape(label, quote=True)
    href = html.escape(serialized_tool_detail_href(row), quote=True)
    asset_id = html.escape(str(row.get("_detail_asset_id") or row.get("id") or "").strip(), quote=True)
    return (
        f'<a class="ips-row-open-link ips-dash-est-link ips-inventory-desc-link '
        f'ips-assets-open-link ips-serialized-tool-open-link" href="{href}" target="_self" '
        f'data-asset-id="{asset_id}" title="{title}">{text}</a>'
    )


def _tool_thumb_link_html(row: dict[str, Any], thumb_asset: dict[str, Any]) -> str:
    href = html.escape(serialized_tool_detail_href(row), quote=True)
    asset_id = html.escape(str(row.get("_detail_asset_id") or row.get("id") or "").strip(), quote=True)
    thumb = catalog_thumbnail_html(
        thumb_asset,
        kind="asset",
        css_class="ips-inventory-thumb-img",
        cell_class="ips-inventory-image-cell",
        alt="Tool image",
    )
    return (
        f'<a class="ips-inventory-thumb-cell-link ips-assets-open-link ips-serialized-tool-open-link" '
        f'href="{href}" target="_self" data-asset-id="{asset_id}" '
        f'title="View tool" aria-label="View tool">{thumb}</a>'
    )


def build_serialized_tools_html_table(
    rows: list[dict[str, Any]],
    *,
    field_mode: bool = False,
    is_row_selected: Callable[[str], bool] | None = None,
) -> str:
    active_headers = (
        SERIALIZED_TOOLS_TABLE_HEADERS
        if field_mode
        else tuple(h for h in SERIALIZED_TOOLS_TABLE_HEADERS if h[0] != "select")
    )
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX.items()
        if not field_mode or key != "select" or field_mode
    ]
    if not field_mode:
        col_parts = [
            f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
            for key, px in SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX.items()
            if key != "select"
        ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;'
            f'max-width:{SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in active_headers
    ]

    body_rows: list[str] = []
    for row_idx, row in enumerate(rows):
        row_id = str(row.get("_row_id") or "").strip()
        if not row_id:
            continue

        name = str(row.get("_display_name") or "—").strip() or "—"
        name_label = name if name != "—" else "View tool"
        model_no = str(row.get("_display_model") or "—").strip() or "—"
        serial = str(row.get("_display_serial") or "—").strip() or "—"
        trailer = str(row.get("_display_trailer") or "—").strip() or "—"
        job_label = str(row.get("_display_job") or "—").strip() or "—"
        status = str(row.get("_display_status") or "—").strip() or "—"
        condition = str(row.get("_display_condition") or "—").strip() or "—"
        thumb_asset = row.get("_thumb_asset") if isinstance(row.get("_thumb_asset"), dict) else row
        name_inner = _tool_link_html(row, name_label)

        row_parity = "even" if row_idx % 2 else "odd"
        cells: list[tuple[str, str, str]] = []
        if field_mode:
            checked = ""
            if is_row_selected is not None:
                checked = " checked" if is_row_selected(row_id) else ""
            select_cell = (
                f'<input type="checkbox" class="ips-serialized-tool-row-select" '
                f'data-st-action="select" data-row-id="{html.escape(row_id, quote=True)}" '
                f'aria-label="Select tool"{checked} />'
            )
            cells.append(("select", "center", _cell_wrapper(select_cell, align="center")))
        cells.extend(
            [
                (
                    "image",
                    "center",
                    _cell_wrapper(
                        _tool_thumb_link_html(row, thumb_asset),
                        extra_class="ips-inventory-image-td",
                        align="center",
                    ),
                ),
                ("name", "left", _cell_wrapper(name_inner, extra_class="ips-dash-est-desc-cell")),
                (
                    "model",
                    "left",
                    _cell_wrapper(
                        f'<span class="ips-inventory-text-cell ips-serialized-tool-text-cell">'
                        f"{html.escape(model_no)}</span>"
                    ),
                ),
                (
                    "serial",
                    "left",
                    _cell_wrapper(
                        f'<span class="ips-inventory-text-cell ips-serialized-tool-text-cell">'
                        f"{html.escape(serial)}</span>"
                    ),
                ),
                (
                    "trailer",
                    "left",
                    _cell_wrapper(
                        f'<span class="ips-inventory-muted">{html.escape(trailer)}</span>'
                    ),
                ),
                (
                    "job",
                    "left",
                    _cell_wrapper(
                        f'<span class="ips-inventory-muted">{html.escape(job_label)}</span>'
                    ),
                ),
                (
                    "status",
                    "center",
                    _cell_wrapper(
                        asset_status_pill_html(status),
                        extra_class="ips-dash-est-status-cell",
                        align="center",
                    ),
                ),
                (
                    "condition",
                    "left",
                    _cell_wrapper(
                        f'<span class="ips-inventory-muted">{html.escape(condition)}</span>'
                    ),
                ),
            ]
        )

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;'
                f'max-width:{SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        expand_attr = ' data-asset-action="expand"' if field_mode else ""
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity} ips-serialized-tool-row{expand_attr}" '
            f'data-row-id="{html.escape(row_id, quote=True)}" '
            f'data-asset-id="{html.escape(str(row.get("_detail_asset_id") or row_id), quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(
        px
        for key, px in SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX.items()
        if field_mode or key != "select"
    )
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table ips-assets-html-equipment-table ips-serialized-tools-html-table" '
        f'style="width:100%;min-width:{min_width}px;">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def handle_serialized_tools_table_action(
    raw: str,
    row_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_row_fn: Callable[[str, dict[str, Any]], None],
    select_row_fn: Callable[[str, bool], None],
) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(last_action_key) or ""):
        return
    st.session_state[last_action_key] = val

    if val.startswith("select:"):
        payload = val.split(":", 2)
        if len(payload) < 3:
            return
        row_id = payload[1].strip()
        checked = payload[2].strip().lower() in {"1", "true", "yes", "on"}
        if row_id not in row_by_id:
            return
        select_row_fn(row_id, checked)
        if checked:
            ips_app_rerun()
        else:
            fragment_rerun()
        return

    row_id = val.split(":", 1)[1].strip() if val.startswith("open:") else val
    if not row_id:
        return
    row = row_by_id.get(row_id)
    if not row:
        return
    open_row_fn(row_id, row)
    ips_app_rerun()


def render_serialized_tools_table_bridge(
    *,
    component_key: str = "ips_serialized_tools_list_bridge",
    hook_key: str = "ipsSerializedToolsList::action",
    field_mode: bool = False,
) -> str | None:
    from app.ui.clean_table import _components_html

    if not field_mode:
        return None

    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const selectSel = ".ips-serialized-tools-html-table [data-st-action='select'][data-row-id]";

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
    doc.querySelectorAll(selectSel).forEach(function (el) {{
      if (el.dataset.ipsStSelectBound === "1") return;
      el.dataset.ipsStSelectBound = "1";
      el.addEventListener("change", function (e) {{
        e.stopPropagation();
        const id = el.getAttribute("data-row-id");
        if (!id) return;
        sendValue("select:" + id + ":" + (el.checked ? "1" : "0"));
      }}, true);
    }});
  }}

  if (!doc.ipsSerializedToolsTableRegistry) doc.ipsSerializedToolsTableRegistry = {{}};
  doc.ipsSerializedToolsTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsSerializedToolsTableBindObserver) {{
    doc.ipsSerializedToolsTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsSerializedToolsTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsSerializedToolsTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
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


def apply_serialized_tools_table_bridge_action(
    picked: str | None,
    row_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_row_fn: Callable[[str, dict[str, Any]], None],
    select_row_fn: Callable[[str, bool], None],
) -> bool:
    raw = str(picked or "").strip()
    if not raw:
        return False
    handle_serialized_tools_table_action(
        raw,
        row_by_id,
        last_action_key=last_action_key,
        open_row_fn=open_row_fn,
        select_row_fn=select_row_fn,
    )
    return raw.startswith("open:")


def render_serialized_tools_table_bridge_legacy(
    row_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_serialized_tools_list_bridge",
    hook_key: str = "ipsSerializedToolsList::action",
    last_action_key: str = SERIALIZED_TOOLS_TABLE_LAST_ACTION_KEY,
    open_row_fn: Callable[[str, dict[str, Any]], None],
    select_row_fn: Callable[[str, bool], None],
    field_mode: bool = False,
) -> None:
    if not field_mode:
        return
    st.markdown(
        '<span class="ips-serialized-tools-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = render_serialized_tools_table_bridge(
        component_key=component_key,
        hook_key=hook_key,
        field_mode=field_mode,
    )
    apply_serialized_tools_table_bridge_action(
        picked,
        row_by_id,
        last_action_key=last_action_key,
        open_row_fn=open_row_fn,
        select_row_fn=select_row_fn,
    )
