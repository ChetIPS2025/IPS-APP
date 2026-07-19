"""Shared HTML customers list table (aligned with inventory list design)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.components.customers_directory_table import customer_name_link_html

CUSTOMERS_TABLE_LAST_ACTION_KEY = "customers_list_last_action"


def customer_bridge_button_key(row: dict[str, Any]) -> str:
    raw = str(row.get("id") or row.get("customer_number") or "cust").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw) or "cust"
    return f"cust_bridge_open_{safe}"


CUSTOMERS_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("avatar", ""),
    ("customer", "CUSTOMER"),
    ("contacts", "CONTACTS"),
    ("open_jobs", "OPEN JOBS"),
    ("open_estimates", "OPEN ESTIMATES"),
    ("status", "STATUS"),
)

CUSTOMERS_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "avatar": 64,
    "customer": 280,
    "contacts": 96,
    "open_jobs": 104,
    "open_estimates": 128,
    "status": 108,
}


def normalize_customer_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Active",
        "active": "Active",
        "inactive": "Inactive",
        "prospect": "Prospect",
        "on hold": "On Hold",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "Active"


def customer_name(row: dict[str, Any]) -> str:
    val = str(row.get("customer_name") or row.get("company_name") or "").strip()
    return val or "—"


def customer_initials(name: str) -> str:
    parts = [p for p in str(name or "").strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def customer_avatar_html(customer: dict[str, Any]) -> str:
    name = customer_name(customer)
    label = name if name and name != "—" else "Customer"
    initials = customer_initials(label)
    return (
        f'<span class="ips-customers-avatar-initials" aria-label="{html.escape(label)}">'
        f"{html.escape(initials)}</span>"
    )


def customer_count_cell_html(value: object) -> str:
    text = str(value if value is not None else 0)
    return (
        f'<span class="ips-customers-count-cell ips-customers-text-cell" '
        f'title="{html.escape(text, quote=True)}">{html.escape(text)}</span>'
    )


def customer_text_cell_html(value: object, *, muted: bool = False) -> str:
    text = str(value or "—").strip() or "—"
    cls = "ips-customers-muted-cell" if muted else "ips-customers-text-cell"
    return f'<span class="{cls}" title="{html.escape(text, quote=True)}">{html.escape(text)}</span>'


def customer_status_pill_html(status: str) -> str:
    cls_map = {
        "Active": "ips-customer-status-active",
        "Inactive": "ips-customer-status-inactive",
        "Prospect": "ips-customer-status-prospect",
        "On Hold": "ips-customer-status-on-hold",
    }
    cls = cls_map.get(status, "ips-customer-status-active")
    return f'<span class="ips-customer-status-pill {cls}">{html.escape(status)}</span>'


def _customer_link_html(
    cid: str,
    label: str,
    *,
    extra_class: str = "",
    bridge_key: str = "",
) -> str:
    row_id = html.escape(str(cid or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = (
        "ips-row-open-link ips-dash-est-link ips-inventory-desc-link ips-customers-open-link "
        f"{extra_class}"
    ).strip()
    bridge_attr = ""
    if bridge_key:
        bridge_attr = f' data-bridge-key="{html.escape(bridge_key, quote=True)}"'
    return (
        f'<span role="button" tabindex="0" class="{html.escape(cls)}" data-cust-action="open" '
        f'data-customer-id="{row_id}" data-row-id="{row_id}"{bridge_attr} '
        f'title="{title}">{text}</span>'
    )


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def build_customers_html_table(rows: list[dict[str, Any]]) -> str:
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in CUSTOMERS_TABLE_COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{CUSTOMERS_TABLE_COL_WIDTHS_PX[key]}px;max-width:{CUSTOMERS_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in CUSTOMERS_TABLE_HEADERS
    ]

    body_rows: list[str] = []
    for row_idx, row in enumerate(rows):
        cid = str(row.get("id") or "").strip()
        if not cid:
            continue

        bridge_key = customer_bridge_button_key(row)
        name = customer_name(row)
        desc_label = name if name and name != "—" else "Open customer"
        contacts = customer_count_cell_html(row.get("contact_count") or 0)
        open_jobs = customer_count_cell_html(row.get("open_jobs") or 0)
        open_estimates = customer_count_cell_html(row.get("open_estimates") or 0)
        status = normalize_customer_status(row.get("status"))
        row_parity = "even" if row_idx % 2 else "odd"

        cells = [
            (
                "avatar",
                "center",
                _cell_wrapper(
                    customer_avatar_html(row),
                    extra_class="ips-customers-avatar-cell",
                    align="center",
                ),
            ),
            (
                "customer",
                "left",
                _cell_wrapper(
                    customer_name_link_html(cid, desc_label),
                    extra_class="ips-dash-est-desc-cell",
                ),
            ),
            (
                "contacts",
                "right",
                _cell_wrapper(contacts, align="right"),
            ),
            (
                "open_jobs",
                "right",
                _cell_wrapper(open_jobs, align="right"),
            ),
            (
                "open_estimates",
                "right",
                _cell_wrapper(open_estimates, align="right"),
            ),
            (
                "status",
                "center",
                _cell_wrapper(
                    customer_status_pill_html(status),
                    extra_class="ips-dash-est-status-cell",
                    align="center",
                ),
            ),
        ]

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{CUSTOMERS_TABLE_COL_WIDTHS_PX[key]}px;max-width:{CUSTOMERS_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity}" '
            f'data-customer-id="{html.escape(cid, quote=True)}" data-row-id="{html.escape(cid, quote=True)}" '
            f'data-bridge-key="{html.escape(bridge_key, quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(CUSTOMERS_TABLE_COL_WIDTHS_PX.values())
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table ips-customers-html-list-table" '
        f'style="min-width:{min_width}px;">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def handle_customers_table_action(
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


def render_customers_table_open_buttons(
    rows: list[dict[str, Any]],
    *,
    open_item_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    with st.container(key="customers_open_button_harness"):
        for row in rows:
            cid = str(row.get("id") or "").strip()
            if not cid:
                continue
            bridge_key = customer_bridge_button_key(row)

            def _open(_cid: str = cid, _row: dict = row) -> None:
                open_item_fn(_cid, _row)

            st.button(
                "Open customer",
                key=bridge_key,
                type="tertiary",
                on_click=_open,
            )


def render_customers_table_bridge(
    *,
    component_key: str = "ips_customers_list_bridge",
    hook_key: str = "ipsCustList::action",
) -> str | None:
    from app.ui.clean_table import _components_html
    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const wrapSel = ".st-key-customers_table_wrap";
  const openSel = wrapSel + " [data-cust-action='open'][data-customer-id]";
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
      if (link.dataset.ipsCustOpenBound === "1") return;
      link.dataset.ipsCustOpenBound = "1";
      link.addEventListener("click", function (e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-customer-id") || link.getAttribute("data-row-id");
        openItem(id, link.getAttribute("data-bridge-key") || "");
      }});
    }});
    doc.querySelectorAll(rowSel).forEach(function (row) {{
      if (row.dataset.ipsCustRowBound === "1") return;
      row.dataset.ipsCustRowBound = "1";
      row.addEventListener("click", function (e) {{
        if (isInteractive(e.target)) return;
        const id = row.getAttribute("data-row-id") || row.getAttribute("data-customer-id");
        if (!id) return;
        e.preventDefault();
        e.stopPropagation();
        openItem(id, row.getAttribute("data-bridge-key") || "");
      }}, true);
    }});
  }}

  if (!doc.ipsCustTableDocClick) {{
    doc.ipsCustTableDocClick = true;
    doc.addEventListener("click", function (e) {{
      const t = e.target;
      if (!t || !t.closest) return;
      const wrap = doc.querySelector(wrapSel);
      if (!wrap || !wrap.contains(t)) return;
      const link = t.closest("[data-cust-action='open'][data-customer-id]");
      if (link && wrap.contains(link)) {{
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-customer-id") || link.getAttribute("data-row-id");
        openItem(id, link.getAttribute("data-bridge-key") || "");
        return;
      }}
      if (isInteractive(t)) return;
      const row = t.closest("tbody tr[data-row-id]");
      if (!row || !wrap.contains(row)) return;
      const id = row.getAttribute("data-row-id") || row.getAttribute("data-customer-id");
      if (!id) return;
      e.preventDefault();
      e.stopPropagation();
      openItem(id, row.getAttribute("data-bridge-key") || "");
    }}, true);
  }}

  if (!doc.ipsCustTableRegistry) doc.ipsCustTableRegistry = {{}};
  doc.ipsCustTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsCustTableBindObserver) {{
    doc.ipsCustTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsCustTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsCustTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
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


def apply_customers_table_bridge_action(
    action: str | None,
    rows_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str = CUSTOMERS_TABLE_LAST_ACTION_KEY,
    open_item_fn: Callable[[str, dict[str, Any]], None],
) -> bool:
    raw = str(action or "").strip()
    if not raw:
        return False
    handle_customers_table_action(
        raw,
        rows_by_id,
        last_action_key=last_action_key,
        open_item_fn=open_item_fn,
    )
    return raw.startswith("open:")


def render_customers_table_bridge_legacy(
    rows_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_customers_list_bridge",
    hook_key: str = "ipsCustList::action",
    last_action_key: str = CUSTOMERS_TABLE_LAST_ACTION_KEY,
    open_item_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    st.markdown(
        '<span class="ips-customers-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = render_customers_table_bridge(
        component_key=component_key,
        hook_key=hook_key,
    )
    apply_customers_table_bridge_action(
        picked,
        rows_by_id,
        last_action_key=last_action_key,
        open_item_fn=open_item_fn,
    )
