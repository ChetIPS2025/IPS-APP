"""Shared HTML assets equipment table (aligned with inventory list design)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from app.ui.streamlit_perf import fragment_rerun, ips_app_rerun

from app.services.catalog_images import catalog_thumbnail_html
from app.services.phase2_modules_service import asset_is_rentable
from app.services.status_maps import normalize_asset_status
from app.utils.formatting import fmt_date
ASSETS_TABLE_LAST_ACTION_KEY = "assets_list_last_action"
_ASSETS_NAV_QUERY_KEY = "ips_nav"
_ASSETS_NAV_SLUG = "assets"


def asset_detail_href(asset_id: str, *, tab: str = "") -> str:
    aid = str(asset_id or "").strip()
    if not aid:
        return "#"

    params: dict[str, str] = {
        _ASSETS_NAV_QUERY_KEY: _ASSETS_NAV_SLUG,
        "asset_detail": aid,
    }
    tab_val = str(tab or "").strip()
    if tab_val:
        params["asset_tab"] = tab_val
    return "?" + urlencode(params)


def assets_bridge_button_key(asset: dict[str, Any]) -> str:
    raw = str(asset.get("id") or asset.get("asset_number") or "asset").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw) or "asset"
    return f"ast_bridge_open_{safe}"


ASSETS_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("image", "IMAGE"),
    ("name", "ASSET NAME"),
    ("number", "ASSET #"),
    ("category", "CATEGORY"),
    ("location", "LOCATION"),
    ("status", "STATUS"),
    ("assigned", "ASSIGNED TO"),
    ("service", "NEXT SERVICE DUE"),
)

ASSETS_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "image": 68,
    "name": 220,
    "number": 96,
    "category": 128,
    "location": 120,
    "status": 112,
    "assigned": 128,
    "service": 120,
}


def asset_name(asset: dict[str, Any]) -> str:
    for key in ("asset_name", "name", "description"):
        val = str(asset.get(key) or "").strip()
        if val:
            return val
    return "—"


def asset_number(asset: dict[str, Any]) -> str:
    for key in ("asset_number", "asset_id", "asset_no"):
        val = str(asset.get(key) or "").strip()
        if val:
            return val
    return "—"


def asset_category(asset: dict[str, Any]) -> str:
    return str(asset.get("category") or "").strip() or "—"


def asset_location(asset: dict[str, Any]) -> str:
    for key in ("location_name", "location"):
        val = str(asset.get(key) or "").strip()
        if val:
            return val
    return "—"


def asset_assigned_to(asset: dict[str, Any]) -> str:
    for key in ("current_operator", "assigned_to_name", "assigned_to", "operator"):
        val = str(asset.get(key) or "").strip()
        if val and val != "—":
            return val
    return "—"


def asset_next_service(asset: dict[str, Any]) -> str:
    for key in ("next_service_due", "next_service", "service_due"):
        val = asset.get(key)
        if val not in (None, ""):
            formatted = fmt_date(val)
            if formatted != "—":
                return formatted
    return "—"


def asset_status_pill_html(status: str) -> str:
    tone_map = {
        "Available": "ips-inventory-status-in-stock",
        "In Service": "ips-inventory-status-in-stock",
        "Active": "ips-inventory-status-in-stock",
        "Out for Repair": "ips-inventory-status-low-stock",
        "Maintenance Due": "ips-inventory-status-low-stock",
        "Needs Serial": "ips-inventory-status-low-stock",
        "Assigned": "ips-inventory-status-on-order",
        "Checked Out": "ips-inventory-status-on-order",
        "Overdue": "ips-inventory-status-out-of-stock",
        "Down": "ips-inventory-status-out-of-stock",
        "Out of Service": "ips-inventory-status-out-of-stock",
        "Lost": "ips-inventory-status-out-of-stock",
        "Retired": "ips-inventory-status-discontinued",
        "Sold": "ips-inventory-status-discontinued",
    }
    cls = tone_map.get(status, "ips-inventory-status-in-stock")
    return f'<span class="ips-inventory-status-pill {cls}">{html.escape(status)}</span>'


def _asset_rentable_badge_html(asset: dict[str, Any]) -> str:
    if not asset_is_rentable(asset):
        return ""
    return '<span class="ips-asset-rental-badge" title="Rental equipment">RENTAL</span>'


def _asset_link_html(
    aid: str,
    label: str,
    *,
    extra_class: str = "",
) -> str:
    asset_id = html.escape(str(aid or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    href = html.escape(asset_detail_href(aid), quote=True)
    cls = (
        "ips-row-open-link ips-dash-est-link ips-inventory-desc-link "
        f"ips-assets-open-link {extra_class}"
    ).strip()
    return (
        f'<a class="{html.escape(cls)}" href="{href}" target="_self" '
        f'data-asset-id="{asset_id}" '
        f'title="{title}">{text}</a>'
    )


def _asset_thumb_link_html(
    aid: str,
    asset: dict[str, Any],
) -> str:
    asset_id = html.escape(str(aid or "").strip(), quote=True)
    href = html.escape(asset_detail_href(aid), quote=True)
    thumb = catalog_thumbnail_html(
        asset,
        kind="asset",
        css_class="ips-inventory-thumb-img",
        cell_class="ips-inventory-image-cell",
        alt="Asset image",
    )
    return (
        f'<a class="ips-inventory-thumb-cell-link ips-assets-open-link" '
        f'href="{href}" target="_self" data-asset-id="{asset_id}" '
        f'title="View asset" aria-label="View asset">{thumb}</a>'
    )


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def build_assets_html_table(
    rows: list[dict[str, Any]],
    *,
    field_mode: bool = False,
    expanded_asset_id: str = "",
) -> str:
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in ASSETS_TABLE_COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{ASSETS_TABLE_COL_WIDTHS_PX[key]}px;max-width:{ASSETS_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in ASSETS_TABLE_HEADERS
    ]

    body_rows: list[str] = []
    for row_idx, asset in enumerate(rows):
        aid = str(asset.get("id") or "").strip()
        if not aid:
            continue

        name = asset_name(asset)
        name_label = name if name and name != "—" else "View asset"
        number = asset_number(asset)
        category = asset_category(asset)
        location = asset_location(asset)
        status = normalize_asset_status(asset.get("status"))
        assigned = asset_assigned_to(asset)
        next_service = asset_next_service(asset)
        rentable_badge = _asset_rentable_badge_html(asset)
        name_inner = _asset_link_html(
            aid,
            name_label,
            extra_class="ips-dash-est-desc-link",
        )
        if rentable_badge:
            name_inner += f'<div class="ips-assets-name-badges">{rentable_badge}</div>'

        row_parity = "even" if row_idx % 2 else "odd"
        expanded = field_mode and expanded_asset_id == aid

        cells = [
            (
                "image",
                "center",
                _cell_wrapper(
                    _asset_thumb_link_html(aid, asset),
                    extra_class="ips-inventory-image-td",
                    align="center",
                ),
            ),
            (
                "name",
                "left",
                _cell_wrapper(name_inner, extra_class="ips-dash-est-desc-cell"),
            ),
            (
                "number",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-text-cell">{html.escape(number)}</span>',
                ),
            ),
            (
                "category",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-text-cell">{html.escape(category)}</span>',
                ),
            ),
            (
                "location",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-text-cell">{html.escape(location)}</span>',
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
                "assigned",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-muted">{html.escape(assigned)}</span>',
                ),
            ),
            (
                "service",
                "left",
                _cell_wrapper(
                    f'<span class="ips-inventory-muted">{html.escape(next_service)}</span>',
                ),
            ),
        ]

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{ASSETS_TABLE_COL_WIDTHS_PX[key]}px;max-width:{ASSETS_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        expand_attr = ' data-asset-action="expand"' if field_mode else ""
        expanded_cls = " ips-inventory-row-expanded" if expanded else ""
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity}{expanded_cls}" '
            f'data-asset-id="{html.escape(aid, quote=True)}" data-row-id="{html.escape(aid, quote=True)}"'
            f'{expand_attr}>'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(ASSETS_TABLE_COL_WIDTHS_PX.values())
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table ips-assets-html-equipment-table" '
        f'style="min-width:{min_width}px;">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def handle_assets_table_action(
    raw: str,
    assets_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_asset_fn: Callable[[str, dict[str, Any]], None],
    on_expand_fn: Callable[[str, dict[str, Any]], None] | None = None,
) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(last_action_key) or ""):
        return
    st.session_state[last_action_key] = val

    if val.startswith("expand:"):
        asset_id = val.split(":", 1)[1].strip()
        asset = assets_by_id.get(asset_id)
        if asset and on_expand_fn is not None:
            on_expand_fn(asset_id, asset)
            fragment_rerun()
        return

    asset_id = val.split(":", 1)[1].strip() if val.startswith("open:") else val
    if not asset_id:
        return
    asset = assets_by_id.get(asset_id)
    if not asset:
        return
    open_asset_fn(asset_id, asset)
    ips_app_rerun()


def render_assets_table_open_buttons(
    assets: list[dict[str, Any]],
    *,
    open_asset_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    """Hidden Streamlit buttons — HTML name clicks trigger these via the bridge script."""
    with st.container(key="assets_open_button_harness"):
        for asset in assets:
            aid = str(asset.get("id") or "").strip()
            if not aid:
                continue
            bridge_key = assets_bridge_button_key(asset)

            def _open(_aid: str = aid, _asset: dict = asset) -> None:
                open_asset_fn(_aid, _asset)

            st.button(
                "Open asset",
                key=bridge_key,
                type="tertiary",
                on_click=_open,
            )


def render_assets_table_bridge(
    *,
    component_key: str = "ips_assets_list_bridge",
    hook_key: str = "ipsAssetsList::action",
) -> str | None:
    """Field-mode row expand bridge; asset name/thumbnail links use native query navigation."""
    from app.ui.clean_table import _components_html

    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const wrapSel = ".st-key-assets_table_wrap";
  const rowSel = ".ips-assets-html-equipment-table tbody tr[data-row-id]";

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

  function isInteractive(target) {{
    return !!(target && target.closest && target.closest(
      "button, [role='button'], input, select, textarea, label, a, "
      + "[data-testid='stButton'], [data-testid='stPopover'], [data-testid='stCheckbox']"
    ));
  }}

  function rowExpandMode(row) {{
    return !!(row && row.getAttribute("data-asset-action") === "expand");
  }}

  if (!doc.ipsAssetsTableDocClick) {{
    doc.ipsAssetsTableDocClick = true;
    doc.addEventListener("click", function (e) {{
      const t = e.target;
      if (!t || !t.closest) return;
      const wrap = doc.querySelector(wrapSel);
      if (!wrap || !wrap.contains(t)) return;

      if (isInteractive(t)) return;
      const row = t.closest(rowSel);
      if (!row || !wrap.contains(row)) return;
      const id = row.getAttribute("data-row-id") || row.getAttribute("data-asset-id");
      if (!id) return;
      if (!rowExpandMode(row)) return;
      e.preventDefault();
      e.stopPropagation();
      sendValue("expand:" + id);
    }}, true);
  }}

  if (!doc.ipsAssetsTableRegistry) doc.ipsAssetsTableRegistry = {{}};
  doc.ipsAssetsTableRegistry[hookKey] = {{ fieldMode: true }};
  try {{
    w.postMessage({{ type: "streamlit:componentReady", apiVersion: 1 }}, "*");
  }} catch (err) {{}}
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )


def apply_assets_table_bridge_action(
    action: str | None,
    assets_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str = ASSETS_TABLE_LAST_ACTION_KEY,
    open_asset_fn: Callable[[str, dict[str, Any]], None],
    on_expand_fn: Callable[[str, dict[str, Any]], None] | None = None,
) -> bool:
    raw = str(action or "").strip()
    if not raw:
        return False
    handle_assets_table_action(
        raw,
        assets_by_id,
        last_action_key=last_action_key,
        open_asset_fn=open_asset_fn,
        on_expand_fn=on_expand_fn,
    )
    return raw.startswith("open:")


def render_assets_table_bridge_legacy(
    assets_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_assets_list_bridge",
    hook_key: str = "ipsAssetsList::action",
    last_action_key: str = ASSETS_TABLE_LAST_ACTION_KEY,
    open_asset_fn: Callable[[str, dict[str, Any]], None],
    on_expand_fn: Callable[[str, dict[str, Any]], None] | None = None,
    field_mode: bool = False,
) -> None:
    st.markdown(
        '<span class="ips-assets-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = render_assets_table_bridge(
        component_key=component_key,
        hook_key=hook_key,
    )
    apply_assets_table_bridge_action(
        picked,
        assets_by_id,
        last_action_key=last_action_key,
        open_asset_fn=open_asset_fn,
        on_expand_fn=on_expand_fn,
    )
