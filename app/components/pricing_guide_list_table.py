"""Shared HTML pricing guide catalog table (aligned with inventory list design)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from app.services.pricing_guide_images import get_pricing_guide_image_url
from app.services.pricing_guide_service import class_pill_html
from app.utils.formatting import fmt_currency

PG_TABLE_LAST_ACTION_KEY = "pg_list_last_action"
_PRICING_DETAIL_QUERY_KEY = "pricing_detail"
_PRICING_DETAIL_TAB_QUERY_KEY = "pricing_tab"
_NAV_QUERY_KEY = "ips_nav"


def pricing_guide_detail_query_key() -> str:
    return _PRICING_DETAIL_QUERY_KEY


def pricing_guide_detail_tab_query_key() -> str:
    return _PRICING_DETAIL_TAB_QUERY_KEY


def pricing_guide_detail_href(item_id: str, *, tab: str = "") -> str:
    """Same-app URL to open Pricing Guide details (?ips_nav=pricing_guide&pricing_detail=<id>)."""
    pid = str(item_id or "").strip()
    params: dict[str, str] = {_NAV_QUERY_KEY: "pricing_guide", _PRICING_DETAIL_QUERY_KEY: pid}
    tab_val = str(tab or "").strip()
    if tab_val:
        params[_PRICING_DETAIL_TAB_QUERY_KEY] = tab_val
    return "?" + urlencode(params)


def pg_bridge_button_key(row: dict[str, Any]) -> str:
    raw = str(row.get("id") or row.get("item_code") or "pg").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw) or "pg"
    return f"pg_bridge_open_{safe}"


PG_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("image", "IMAGE"),
    ("desc", "DESCRIPTION"),
    ("class", "CLASS"),
    ("category", "CATEGORY"),
    ("unit", "UNIT"),
    ("cost", "COST"),
    ("markup", "MARKUP %"),
    ("sell", "SELL PRICE"),
    ("vendor", "VENDOR"),
    ("status", "STATUS"),
)

PG_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "image": 68,
    "desc": 220,
    "class": 104,
    "category": 120,
    "unit": 72,
    "cost": 96,
    "markup": 88,
    "sell": 104,
    "vendor": 128,
    "status": 100,
}


def pg_description(row: dict[str, Any]) -> str:
    for key in ("item", "description", "item_name", "name"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def pg_item_class(row: dict[str, Any]) -> str:
    return str(row.get("item_class") or "Non-Inventory").strip() or "Non-Inventory"


def pg_category(row: dict[str, Any]) -> str:
    return str(row.get("category") or "").strip() or "—"


def pg_unit(row: dict[str, Any]) -> str:
    return str(row.get("unit") or "").strip() or "—"


def pg_vendor(row: dict[str, Any]) -> str:
    return str(row.get("vendor") or "").strip() or "—"


def pg_status(row: dict[str, Any]) -> str:
    return str(row.get("status") or "Active").strip() or "Active"


def pg_status_pill_html(status: str) -> str:
    cls_map = {
        "Active": "ips-pg-status-active",
        "Inactive": "ips-pg-status-inactive",
    }
    cls = cls_map.get(status, "ips-pg-status-active")
    return f'<span class="ips-pg-status-pill {cls}">{html.escape(status)}</span>'


def _pg_link_html(
    rid: str,
    label: str,
    *,
    extra_class: str = "",
) -> str:
    text = html.escape(label)
    title = html.escape(label, quote=True)
    href = html.escape(pricing_guide_detail_href(str(rid or "").strip()), quote=True)
    cls = (
        "ips-row-open-link ips-dash-est-link ips-inventory-desc-link ips-pg-open-link "
        f"{extra_class}"
    ).strip()
    aria = html.escape(f"Open Pricing Guide item details for {label}", quote=True)
    return (
        f'<a class="{html.escape(cls)}" href="{href}" target="_self" '
        f'aria-label="{aria}" title="{title}">{text}</a>'
    )


def _pg_thumb_link_html(
    rid: str,
    row: dict[str, Any],
) -> str:
    item = str(row.get("item") or row.get("description") or "item").strip()
    aria = html.escape(f"Open pricing item {item}", quote=True)
    href = html.escape(pricing_guide_detail_href(str(rid or "").strip()), quote=True)
    image_url = get_pricing_guide_image_url(row)
    if image_url:
        inner = (
            f'<img class="pricing-thumb table-image-preview ips-pg-thumb-img ips-inventory-thumb-img" '
            f'src="{html.escape(image_url, quote=True)}" alt="" aria-hidden="true" />'
        )
    else:
        inner = (
            '<span class="pricing-thumb table-image-preview ips-pg-thumb-placeholder '
            'ips-inventory-thumb-placeholder" aria-hidden="true">—</span>'
        )
    return (
        f'<a class="ips-inventory-thumb-cell-link ips-pg-thumb-cell-link ips-pg-open-link" '
        f'href="{href}" target="_self" title="View item" aria-label="{aria}">{inner}</a>'
    )


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def build_pricing_guide_html_table(rows: list[dict[str, Any]]) -> str:
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in PG_TABLE_COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{PG_TABLE_COL_WIDTHS_PX[key]}px;max-width:{PG_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in PG_TABLE_HEADERS
    ]

    body_rows: list[str] = []
    for row_idx, row in enumerate(rows):
        rid = str(row.get("id") or "").strip()
        if not rid:
            continue

        description = pg_description(row)
        desc_label = description if description and description != "—" else "View item"
        item_class = pg_item_class(row)
        category = pg_category(row)
        unit = pg_unit(row)
        default_cost = fmt_currency(row.get("default_cost"))
        markup = f"{float(row.get('markup_pct') or 0):.1f}%"
        sell_price = fmt_currency(row.get("customer_price"))
        vendor = pg_vendor(row)
        status = pg_status(row)
        row_parity = "even" if row_idx % 2 else "odd"

        cells = [
            (
                "image",
                "center",
                _cell_wrapper(
                    _pg_thumb_link_html(rid, row),
                    extra_class="ips-inventory-image-td",
                    align="center",
                ),
            ),
            (
                "desc",
                "left",
                _cell_wrapper(
                    _pg_link_html(
                        rid,
                        desc_label,
                        extra_class="ips-dash-est-desc-link",
                    ),
                    extra_class="ips-dash-est-desc-cell",
                ),
            ),
            (
                "class",
                "left",
                _cell_wrapper(class_pill_html(item_class), extra_class="ips-pg-class-cell"),
            ),
            (
                "category",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-text-cell">{html.escape(category)}</span>',
                ),
            ),
            (
                "unit",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-muted">{html.escape(unit)}</span>',
                ),
            ),
            (
                "cost",
                "right",
                _cell_wrapper(
                    f'<span class="ips-inventory-money-cell">{html.escape(default_cost)}</span>',
                    align="right",
                ),
            ),
            (
                "markup",
                "right",
                _cell_wrapper(
                    f'<span class="ips-inventory-money-cell">{html.escape(markup)}</span>',
                    align="right",
                ),
            ),
            (
                "sell",
                "right",
                _cell_wrapper(
                    f'<span class="ips-inventory-money-cell">{html.escape(sell_price)}</span>',
                    align="right",
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
            (
                "status",
                "center",
                _cell_wrapper(
                    pg_status_pill_html(status),
                    extra_class="ips-dash-est-status-cell",
                    align="center",
                ),
            ),
        ]

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{PG_TABLE_COL_WIDTHS_PX[key]}px;max-width:{PG_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity}" '
            f'data-pg-id="{html.escape(rid, quote=True)}" data-row-id="{html.escape(rid, quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(PG_TABLE_COL_WIDTHS_PX.values())
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table ips-pg-html-catalog-table" '
        f'style="min-width:{min_width}px;">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def handle_pricing_guide_table_action(
    raw: str,
    rows_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_item_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(last_action_key) or ""):
        return
    st.session_state[last_action_key] = val

    row_id = val.split(":", 1)[1].strip() if val.startswith("open:") else val
    if not row_id:
        return
    row = rows_by_id.get(row_id)
    if not row:
        return
    open_item_fn(row_id, row)
    from app.ui.streamlit_perf import ips_app_rerun
    ips_app_rerun()


def render_pricing_guide_table_open_buttons(
    rows: list[dict[str, Any]],
    *,
    open_item_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    with st.container(key="pricing_guide_open_button_harness"):
        for row in rows:
            rid = str(row.get("id") or "").strip()
            if not rid:
                continue
            bridge_key = pg_bridge_button_key(row)

            def _open(_rid: str = rid, _row: dict = row) -> None:
                open_item_fn(_rid, _row)

            st.button(
                "Open item",
                key=bridge_key,
                type="tertiary",
                on_click=_open,
            )


def render_pricing_guide_table_bridge(
    *,
    component_key: str = "ips_pricing_guide_list_bridge",
    hook_key: str = "ipsPgList::action",
) -> str | None:
    from app.ui.clean_table import _components_html
    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const wrapSel = ".st-key-pricing_guide_table_wrap";
  const openSel = wrapSel + " [data-pg-action='open'][data-pg-id]";
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

  function openItem(id, bridgeKey) {{
    if (!id) return;
    if (bridgeKey && clickBridgeButton(bridgeKey)) return;
    sendValue("open:" + id);
  }}

  function isInteractive(target) {{
    return !!(target && target.closest && target.closest(
      "button, [role='button'], input, select, textarea, label, a, [data-testid='stButton'], [data-testid='stPopover'], [data-testid='stCheckbox']"
    ));
  }}

  function bindTargets() {{
    doc.querySelectorAll(openSel).forEach(function (link) {{
      if (link.dataset.ipsPgOpenBound === "1") return;
      link.dataset.ipsPgOpenBound = "1";
      link.addEventListener("click", function (e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-pg-id") || link.getAttribute("data-row-id");
        openItem(id, link.getAttribute("data-bridge-key") || "");
      }});
    }});
    doc.querySelectorAll(rowSel).forEach(function (row) {{
      if (row.dataset.ipsPgRowBound === "1") return;
      row.dataset.ipsPgRowBound = "1";
      row.addEventListener("click", function (e) {{
        if (isInteractive(e.target)) return;
        const id = row.getAttribute("data-row-id") || row.getAttribute("data-pg-id");
        if (!id) return;
        e.preventDefault();
        e.stopPropagation();
        openItem(id, row.getAttribute("data-bridge-key") || "");
      }}, true);
    }});
  }}

  if (!doc.ipsPgTableDocClick) {{
    doc.ipsPgTableDocClick = true;
    doc.addEventListener("click", function (e) {{
      const t = e.target;
      if (!t || !t.closest) return;
      const wrap = doc.querySelector(wrapSel);
      if (!wrap || !wrap.contains(t)) return;
      const link = t.closest("[data-pg-action='open'][data-pg-id]");
      if (link && wrap.contains(link)) {{
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-pg-id") || link.getAttribute("data-row-id");
        openItem(id, link.getAttribute("data-bridge-key") || "");
        return;
      }}
      if (isInteractive(t)) return;
      const row = t.closest("tbody tr[data-row-id]");
      if (!row || !wrap.contains(row)) return;
      const id = row.getAttribute("data-row-id") || row.getAttribute("data-pg-id");
      if (!id) return;
      e.preventDefault();
      e.stopPropagation();
      openItem(id, row.getAttribute("data-bridge-key") || "");
    }}, true);
  }}

  if (!doc.ipsPgTableRegistry) doc.ipsPgTableRegistry = {{}};
  doc.ipsPgTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsPgTableBindObserver) {{
    doc.ipsPgTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsPgTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsPgTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
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


def apply_pricing_guide_table_bridge_action(
    action: str | None,
    rows_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str = PG_TABLE_LAST_ACTION_KEY,
    open_item_fn: Callable[[str, dict[str, Any]], None],
) -> bool:
    raw = str(action or "").strip()
    if not raw:
        return False
    handle_pricing_guide_table_action(
        raw,
        rows_by_id,
        last_action_key=last_action_key,
        open_item_fn=open_item_fn,
    )
    return raw.startswith("open:")


def render_pricing_guide_table_bridge_legacy(
    rows_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_pricing_guide_list_bridge",
    hook_key: str = "ipsPgList::action",
    last_action_key: str = PG_TABLE_LAST_ACTION_KEY,
    open_item_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    st.markdown(
        '<span class="ips-pg-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = render_pricing_guide_table_bridge(
        component_key=component_key,
        hook_key=hook_key,
    )
    apply_pricing_guide_table_bridge_action(
        picked,
        rows_by_id,
        last_action_key=last_action_key,
        open_item_fn=open_item_fn,
    )
