"""Shared HTML inventory table (inventory list page)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.services.inventory_images import inventory_thumbnail_html
    from app.utils.formatting import fmt_currency
    from app.utils.inventory_quantity import format_inventory_quantity
except ImportError:
    from services.inventory_images import inventory_thumbnail_html  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore
    from utils.inventory_quantity import format_inventory_quantity  # type: ignore

INVENTORY_TABLE_LAST_ACTION_KEY = "inventory_list_last_action"


def inventory_bridge_button_key(item: dict[str, Any]) -> str:
    raw = str(item.get("id") or item.get("sku") or "item").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw) or "item"
    return f"inv_bridge_open_{safe}"

INVENTORY_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("image", "IMAGE"),
    ("desc", "DESCRIPTION"),
    ("category", "CATEGORY"),
    ("location", "LOCATION"),
    ("qty", "QTY ON HAND"),
    ("unit", "UNIT"),
    ("unit_cost", "UNIT COST"),
    ("status", "STATUS"),
    ("vendor", "VENDOR"),
)

INVENTORY_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "image": 68,
    "desc": 240,
    "category": 140,
    "location": 128,
    "qty": 96,
    "unit": 72,
    "unit_cost": 100,
    "status": 112,
    "vendor": 140,
}


def normalize_inventory_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "In Stock",
        "in stock": "In Stock",
        "available": "In Stock",
        "low stock": "Low Stock",
        "needs reorder": "Needs Reorder",
        "out of stock": "Out of Stock",
        "depleted": "Out of Stock",
        "on order": "On Order",
        "discontinued": "Discontinued",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "In Stock"


def inventory_status_pill_html(status: str) -> str:
    cls_map = {
        "In Stock": "ips-inventory-status-in-stock",
        "Low Stock": "ips-inventory-status-low-stock",
        "Needs Reorder": "ips-inventory-status-low-stock",
        "Out of Stock": "ips-inventory-status-out-of-stock",
        "On Order": "ips-inventory-status-on-order",
        "Discontinued": "ips-inventory-status-discontinued",
    }
    cls = cls_map.get(status, "ips-inventory-status-in-stock")
    return f'<span class="ips-inventory-status-pill {cls}">{html.escape(status)}</span>'


def inventory_description(item: dict[str, Any]) -> str:
    for key in ("description", "item_name", "name"):
        val = str(item.get(key) or "").strip()
        if val:
            return val
    return "—"


def inventory_category(item: dict[str, Any]) -> str:
    return str(item.get("category") or "").strip() or "—"


def inventory_location(item: dict[str, Any]) -> str:
    for key in ("location_name", "location"):
        val = str(item.get(key) or "").strip()
        if val:
            return val
    return "—"


def inventory_vendor(item: dict[str, Any]) -> str:
    for key in ("vendor_name", "vendor"):
        val = str(item.get(key) or "").strip()
        if val:
            return val
    return "—"


def inventory_unit(item: dict[str, Any]) -> str:
    return str(item.get("unit") or "").strip() or "—"


def inventory_qty_display(item: dict[str, Any]) -> str:
    unit = inventory_unit(item)
    qty = item.get("quantity_on_hand") or item.get("qty_on_hand") or item.get("quantity")
    if unit and unit != "—":
        return format_inventory_quantity(qty, unit)
    return format_inventory_quantity(qty)


def _inventory_link_html(
    iid: str,
    label: str,
    *,
    extra_class: str = "",
    bridge_key: str = "",
) -> str:
    item_id = html.escape(str(iid or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = f"ips-row-open-link ips-dash-est-link ips-inventory-desc-link ips-inventory-open-link {extra_class}".strip()
    bridge_attr = ""
    if bridge_key:
        bridge_attr = f' data-bridge-key="{html.escape(bridge_key, quote=True)}"'
    return (
        f'<button type="button" class="{html.escape(cls)}" data-inv-action="open" '
        f'data-inventory-id="{item_id}" data-row-id="{item_id}"{bridge_attr} '
        f'title="{title}">{text}</button>'
    )


def _inventory_thumb_link_html(
    iid: str,
    item: dict[str, Any],
    *,
    bridge_key: str = "",
) -> str:
    item_id = html.escape(str(iid or "").strip(), quote=True)
    thumb = inventory_thumbnail_html(item)
    bridge_attr = ""
    if bridge_key:
        bridge_attr = f' data-bridge-key="{html.escape(bridge_key, quote=True)}"'
    return (
        f'<button type="button" class="ips-inventory-thumb-cell-link ips-inventory-open-link" '
        f'data-inv-action="open" data-inventory-id="{item_id}" data-row-id="{item_id}"{bridge_attr} '
        f'title="View item" aria-label="View item">{thumb}</button>'
    )


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def build_inventory_html_table(
    rows: list[dict[str, Any]],
    *,
    field_mode: bool = False,
    expanded_item_id: str = "",
) -> str:
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in INVENTORY_TABLE_COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{INVENTORY_TABLE_COL_WIDTHS_PX[key]}px;max-width:{INVENTORY_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in INVENTORY_TABLE_HEADERS
    ]

    body_rows: list[str] = []
    for row_idx, item in enumerate(rows):
        iid = str(item.get("id") or "").strip()
        if not iid:
            continue

        bridge_key = inventory_bridge_button_key(item)
        description = inventory_description(item)
        desc_label = description if description and description != "—" else "View item"
        category = inventory_category(item)
        location = inventory_location(item)
        qty = inventory_qty_display(item)
        unit = inventory_unit(item)
        unit_cost = fmt_currency(item.get("unit_cost"))
        status = normalize_inventory_status(item.get("status"))
        vendor = inventory_vendor(item)
        row_parity = "even" if row_idx % 2 else "odd"
        expanded = field_mode and expanded_item_id == iid

        cells = [
            (
                "image",
                "center",
                _cell_wrapper(
                    _inventory_thumb_link_html(iid, item, bridge_key=bridge_key),
                    extra_class="ips-inventory-image-td",
                    align="center",
                ),
            ),
            (
                "desc",
                "left",
                _cell_wrapper(
                    _inventory_link_html(
                        iid,
                        desc_label,
                        extra_class="ips-dash-est-desc-link",
                        bridge_key=bridge_key,
                    ),
                    extra_class="ips-dash-est-desc-cell",
                ),
            ),
            (
                "category",
                "left",
                _cell_wrapper(
                    html.escape(category),
                    extra_class="ips-inventory-text-cell",
                ),
            ),
            (
                "location",
                "left",
                _cell_wrapper(
                    html.escape(location),
                    extra_class="ips-inventory-text-cell",
                ),
            ),
            (
                "qty",
                "right",
                _cell_wrapper(
                    f'<span class="ips-inventory-qty">{html.escape(qty)}</span>',
                    extra_class="ips-inventory-qty-cell",
                    align="right",
                ),
            ),
            (
                "unit",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-muted">{html.escape(unit)}</span>',
                    extra_class="ips-inventory-unit-cell",
                ),
            ),
            (
                "unit_cost",
                "right",
                _cell_wrapper(
                    html.escape(unit_cost),
                    extra_class="ips-inventory-money-cell",
                    align="right",
                ),
            ),
            (
                "status",
                "center",
                _cell_wrapper(
                    inventory_status_pill_html(status),
                    extra_class="ips-dash-est-status-cell",
                    align="center",
                ),
            ),
            (
                "vendor",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-muted">{html.escape(vendor)}</span>',
                    extra_class="ips-inventory-vendor-cell",
                ),
            ),
        ]

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{INVENTORY_TABLE_COL_WIDTHS_PX[key]}px;max-width:{INVENTORY_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        expand_attr = ' data-inv-action="expand"' if field_mode else ""
        expanded_cls = " ips-inventory-row-expanded" if expanded else ""
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity}{expanded_cls}" '
            f'data-inventory-id="{html.escape(iid, quote=True)}" data-row-id="{html.escape(iid, quote=True)}" '
            f'data-bridge-key="{html.escape(bridge_key, quote=True)}"{expand_attr}>'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(INVENTORY_TABLE_COL_WIDTHS_PX.values())
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table" style="min-width:{min_width}px;">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def handle_inventory_table_action(
    raw: str,
    items_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_item_fn: Callable[[str, dict[str, Any]], None],
    on_expand_fn: Callable[[str, dict[str, Any]], None] | None = None,
) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(last_action_key) or ""):
        return
    st.session_state[last_action_key] = val

    if val.startswith("expand:"):
        item_id = val.split(":", 1)[1].strip()
        item = items_by_id.get(item_id)
        if item and on_expand_fn is not None:
            on_expand_fn(item_id, item)
            st.rerun()
        return

    item_id = val.split(":", 1)[1].strip() if val.startswith("open:") else val
    if not item_id:
        return
    item = items_by_id.get(item_id)
    if not item:
        return
    open_item_fn(item_id, item)
    st.rerun()


def render_inventory_table_open_buttons(
    items: list[dict[str, Any]],
    *,
    open_item_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    """Hidden Streamlit buttons — HTML link clicks trigger these via the bridge script."""
    with st.container(key="inventory_open_button_harness"):
        for item in items:
            iid = str(item.get("id") or "").strip()
            if not iid:
                continue
            bridge_key = inventory_bridge_button_key(item)

            def _open(_iid: str = iid, _item: dict = item) -> None:
                open_item_fn(_iid, _item)

            st.button(
                "Open item",
                key=bridge_key,
                type="tertiary",
                on_click=_open,
                label_visibility="collapsed",
            )


def render_inventory_table_bridge(
    *,
    component_key: str = "ips_inventory_list_bridge",
    hook_key: str = "ipsInvList::action",
    field_mode: bool = False,
) -> str | None:
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    field_mode_js = "true" if field_mode else "false"
    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const fieldMode = {field_mode_js};
  const wrapSel = ".st-key-inventory_table_wrap";
  const openSel = wrapSel + " [data-inv-action='open'][data-inventory-id]";
  const rowSel = wrapSel + " tbody tr[data-row-id]";

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

  function clickBridgeButton(bridgeKey) {{
    if (!bridgeKey) return false;
    const host = doc.querySelector(".st-key-" + bridgeKey);
    const btn = host && host.querySelector('[data-testid="stButton"] > button');
    if (!btn) return false;
    btn.click();
    return true;
  }}

  function openItem(id, action, bridgeKey) {{
    if (!id) return;
    const act = action || "open";
    if (act === "open" && bridgeKey && clickBridgeButton(bridgeKey)) return;
    sendValue(act + ":" + id);
  }}

  function isInteractive(target) {{
    return !!(target && target.closest && target.closest(
      "button:not(.ips-inventory-open-link), input, select, textarea, label, [data-inv-action]:not([data-inv-action='open'])"
    ));
  }}

  function bindTargets() {{
    const wrap = doc.querySelector(wrapSel);
    if (!wrap) return;
    wrap.querySelectorAll(openSel).forEach(function (el) {{
      if (el.dataset.ipsInvOpenBound === "1") return;
      el.dataset.ipsInvOpenBound = "1";
      function onActivate(e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = el.getAttribute("data-inventory-id") || el.getAttribute("data-row-id");
        openItem(id, "open", el.getAttribute("data-bridge-key") || "");
      }}
      el.addEventListener("click", onActivate, true);
      el.addEventListener("keydown", function (e) {{
        if (e.key === "Enter" || e.key === " ") onActivate(e);
      }}, true);
    }});
    wrap.querySelectorAll(rowSel).forEach(function (row) {{
      if (row.dataset.ipsInvRowBound === "1") return;
      row.dataset.ipsInvRowBound = "1";
      row.addEventListener("click", function (e) {{
        if (isInteractive(e.target)) return;
        const id = row.getAttribute("data-row-id") || row.getAttribute("data-inventory-id");
        if (!id) return;
        e.preventDefault();
        e.stopPropagation();
        openItem(
          id,
          fieldMode ? "expand" : "open",
          row.getAttribute("data-bridge-key") || ""
        );
      }}, true);
    }});
  }}

  if (!doc.ipsInvTableDocClick) {{
    doc.ipsInvTableDocClick = true;
    doc.addEventListener("click", function (e) {{
      const t = e.target;
      if (!t || !t.closest) return;
      const wrap = doc.querySelector(wrapSel);
      if (!wrap || !wrap.contains(t)) return;
      const link = t.closest("[data-inv-action='open'][data-inventory-id]");
      if (link && wrap.contains(link)) {{
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-inventory-id") || link.getAttribute("data-row-id");
        openItem(id, "open", link.getAttribute("data-bridge-key") || "");
        return;
      }}
      if (isInteractive(t)) return;
      const row = t.closest("tbody tr[data-row-id]");
      if (!row || !wrap.contains(row)) return;
      const id = row.getAttribute("data-row-id") || row.getAttribute("data-inventory-id");
      if (!id) return;
      e.preventDefault();
      e.stopPropagation();
      openItem(
        id,
        fieldMode ? "expand" : "open",
        row.getAttribute("data-bridge-key") || ""
      );
    }}, true);
  }}

  if (!doc.ipsInvTableRegistry) doc.ipsInvTableRegistry = {{}};
  doc.ipsInvTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsInvTableBindObserver) {{
    doc.ipsInvTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsInvTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsInvTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
  }}
  try {{
    w.postMessage({{ type: "streamlit:componentReady", apiVersion: 1 }}, "*");
  }} catch (err) {{}}
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )


def apply_inventory_table_bridge_action(
    action: str | None,
    items_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str = INVENTORY_TABLE_LAST_ACTION_KEY,
    open_item_fn: Callable[[str, dict[str, Any]], None],
    on_expand_fn: Callable[[str, dict[str, Any]], None] | None = None,
) -> bool:
    """Apply a bridge action at page level. Returns True when an open action was handled."""
    raw = str(action or "").strip()
    if not raw:
        return False
    handle_inventory_table_action(
        raw,
        items_by_id,
        last_action_key=last_action_key,
        open_item_fn=open_item_fn,
        on_expand_fn=on_expand_fn,
    )
    return raw.startswith("open:")


def render_inventory_table_bridge_legacy(
    items_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_inventory_list_bridge",
    hook_key: str = "ipsInvList::action",
    last_action_key: str = INVENTORY_TABLE_LAST_ACTION_KEY,
    open_item_fn: Callable[[str, dict[str, Any]], None],
    on_expand_fn: Callable[[str, dict[str, Any]], None] | None = None,
    field_mode: bool = False,
) -> None:
    st.markdown(
        '<span class="ips-inventory-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = render_inventory_table_bridge(
        component_key=component_key,
        hook_key=hook_key,
        field_mode=field_mode,
    )
    apply_inventory_table_bridge_action(
        picked,
        items_by_id,
        last_action_key=last_action_key,
        open_item_fn=open_item_fn,
        on_expand_fn=on_expand_fn,
    )
