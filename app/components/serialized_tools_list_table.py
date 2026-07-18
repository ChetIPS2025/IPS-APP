"""HTML serialized-tools table with click bridge (fast fragment reruns)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.components.assets_list_table import asset_status_pill_html
from app.services.catalog_images import catalog_thumbnail_html
from app.ui.streamlit_perf import fragment_rerun, ips_app_rerun

SERIALIZED_TOOLS_TABLE_LAST_ACTION_KEY = "serialized_tools_list_last_action"


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
    "model": 100,
    "serial": 100,
    "trailer": 130,
    "job": 110,
    "status": 112,
    "condition": 90,
}


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def _tool_link_html(row_id: str, label: str, *, bridge_key: str = "") -> str:
    rid = html.escape(str(row_id or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    bridge_attr = (
        f' data-bridge-key="{html.escape(bridge_key, quote=True)}"' if bridge_key else ""
    )
    return (
        f'<button type="button" class="ips-row-open-link ips-dash-est-link ips-inventory-desc-link '
        f'ips-inventory-open-link ips-assets-open-link ips-serialized-tool-open-link" '
        f'data-st-action="open" data-row-id="{rid}"{bridge_attr} title="{title}">{text}</button>'
    )


def _tool_thumb_link_html(row_id: str, thumb_asset: dict[str, Any], *, bridge_key: str = "") -> str:
    rid = html.escape(str(row_id or "").strip(), quote=True)
    thumb = catalog_thumbnail_html(
        thumb_asset,
        kind="asset",
        css_class="ips-inventory-thumb-img",
        cell_class="ips-inventory-image-cell",
        alt="Tool image",
    )
    bridge_attr = (
        f' data-bridge-key="{html.escape(bridge_key, quote=True)}"' if bridge_key else ""
    )
    return (
        f'<button type="button" class="ips-inventory-thumb-cell-link ips-inventory-open-link '
        f'ips-assets-open-link ips-serialized-tool-open-link" data-st-action="open" '
        f'data-row-id="{rid}"{bridge_attr} title="View tool" aria-label="View tool">{thumb}</button>'
    )


def build_serialized_tools_html_table(
    rows: list[dict[str, Any]],
    *,
    is_row_selected: Callable[[str], bool],
) -> str:
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;'
            f'max-width:{SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in SERIALIZED_TOOLS_TABLE_HEADERS
    ]

    body_rows: list[str] = []
    for row_idx, row in enumerate(rows):
        row_id = str(row.get("_row_id") or "").strip()
        if not row_id:
            continue

        bridge_key = serialized_tools_bridge_button_key(row)
        name = str(row.get("_display_name") or "—").strip() or "—"
        model_no = str(row.get("_display_model") or "—").strip() or "—"
        serial = str(row.get("_display_serial") or "—").strip() or "—"
        trailer = str(row.get("_display_trailer") or "—").strip() or "—"
        job_label = str(row.get("_display_job") or "—").strip() or "—"
        status = str(row.get("_display_status") or "—").strip() or "—"
        condition = str(row.get("_display_condition") or "—").strip() or "—"
        thumb_asset = row.get("_thumb_asset") if isinstance(row.get("_thumb_asset"), dict) else row
        checked = " checked" if is_row_selected(row_id) else ""

        select_cell = (
            f'<input type="checkbox" class="ips-serialized-tool-row-select" '
            f'data-st-action="select" data-row-id="{html.escape(row_id, quote=True)}" '
            f'aria-label="Select tool"{checked} />'
        )
        name_inner = _tool_link_html(row_id, name, bridge_key=bridge_key)

        row_parity = "even" if row_idx % 2 else "odd"
        cells = [
            ("select", "center", _cell_wrapper(select_cell, align="center")),
            (
                "image",
                "center",
                _cell_wrapper(
                    _tool_thumb_link_html(row_id, thumb_asset, bridge_key=bridge_key),
                    extra_class="ips-inventory-image-td",
                    align="center",
                ),
            ),
            ("name", "left", _cell_wrapper(name_inner, extra_class="ips-dash-est-desc-cell")),
            (
                "model",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-text-cell">{html.escape(model_no)}</span>'
                ),
            ),
            (
                "serial",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-text-cell">{html.escape(serial)}</span>'
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

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;'
                f'max-width:{SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity} ips-serialized-tool-row" '
            f'data-row-id="{html.escape(row_id, quote=True)}" '
            f'data-bridge-key="{html.escape(bridge_key, quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX.values())
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table ips-serialized-tools-html-table" '
        f'style="min-width:{min_width}px;">'
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


def render_serialized_tools_table_open_buttons(
    rows: list[dict[str, Any]],
    *,
    open_row_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    """Hidden Streamlit buttons — HTML name clicks trigger these via the bridge script."""
    with st.container(key="serialized_tools_open_button_harness"):
        for row in rows:
            row_id = str(row.get("_row_id") or "").strip()
            if not row_id:
                continue
            bridge_key = serialized_tools_bridge_button_key(row)

            def _open(_row_id: str = row_id, _row: dict = row) -> None:
                open_row_fn(_row_id, _row)

            st.button(
                "Open tool",
                key=bridge_key,
                type="tertiary",
                on_click=_open,
            )


def render_serialized_tools_table_bridge(
    *,
    component_key: str = "ips_serialized_tools_list_bridge",
    hook_key: str = "ipsSerializedToolsList::action",
) -> str | None:
    from app.ui.clean_table import _components_html

    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const wrapSel = ".st-key-assets_small_tools_table_wrap";
  const openSel = wrapSel + " [data-st-action='open'][data-row-id]";
  const selectSel = wrapSel + " [data-st-action='select'][data-row-id]";

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

  function openRow(id) {{
    if (!id) return;
    sendValue("open:" + id);
  }}

  function bindTargets() {{
    const wrap = doc.querySelector(wrapSel);
    if (!wrap) return;
    wrap.querySelectorAll(openSel).forEach(function (el) {{
      if (el.dataset.ipsStOpenBound === "1") return;
      el.dataset.ipsStOpenBound = "1";
      function onActivate(e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = el.getAttribute("data-row-id");
        openRow(id);
      }}
      el.addEventListener("click", onActivate, true);
      el.addEventListener("keydown", function (e) {{
        if (e.key === "Enter" || e.key === " ") onActivate(e);
      }}, true);
    }});
    wrap.querySelectorAll(selectSel).forEach(function (el) {{
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

  if (!doc.ipsSerializedToolsTableDocClick) {{
    doc.ipsSerializedToolsTableDocClick = true;
    doc.addEventListener("click", function (e) {{
      const t = e.target;
      if (!t || !t.closest) return;
      const wrap = doc.querySelector(wrapSel);
      if (!wrap || !wrap.contains(t)) return;
      const link = t.closest("[data-st-action='open'][data-row-id]");
      if (link && wrap.contains(link)) {{
        e.preventDefault();
        e.stopPropagation();
        openRow(link.getAttribute("data-row-id"));
      }}
    }}, true);
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
) -> None:
    st.markdown(
        '<span class="ips-serialized-tools-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = render_serialized_tools_table_bridge(
        component_key=component_key,
        hook_key=hook_key,
    )
    apply_serialized_tools_table_bridge_action(
        picked,
        row_by_id,
        last_action_key=last_action_key,
        open_row_fn=open_row_fn,
        select_row_fn=select_row_fn,
    )
