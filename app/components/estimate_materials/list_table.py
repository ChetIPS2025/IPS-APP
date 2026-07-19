"""HTML table for paginated Estimate Materials saved lines."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

from app.utils.formatting import fmt_currency

_NAV_QUERY_KEY = "ips_nav"


def material_detail_href(estimate_id: str, line_id: str) -> str:
    params = {
        _NAV_QUERY_KEY: "estimates",
        "estimate_detail": str(estimate_id or "").strip(),
        "estimate_tab": "Materials",
        "material_detail": str(line_id or "").strip(),
    }
    return "?" + urlencode(params)


def material_line_link_html(estimate_id: str, line_id: str, label: str) -> str:
    text = html.escape(str(label or "—"))
    href = html.escape(material_detail_href(estimate_id, line_id), quote=True)
    return (
        f'<a class="ips-est-mat-line-link" href="{href}" target="_self">{text}</a>'
    )


def build_estimate_material_lines_html(
    rows: list[dict[str, Any]],
    *,
    estimate_id: str,
) -> str:
    if not rows:
        return ""
    headers = [
        "Item #",
        "Description",
        "Category",
        "Quantity",
        "Unit",
        "Unit Cost",
        "Cost",
        "Markup %",
        "Customer Price",
    ]
    head = "".join(f'<th class="ips-est-mat-th">{html.escape(h)}</th>' for h in headers)
    body = ""
    eid = html.escape(str(estimate_id or ""), quote=True)
    for row in rows:
        lid = str(row.get("id") or "").strip()
        item_no = str(row.get("item_number") or row.get("sku") or "—")
        if lid:
            item_cell = material_line_link_html(estimate_id, lid, item_no)
            desc_label = str(row.get("description") or "—")
            desc_cell = material_line_link_html(estimate_id, lid, desc_label)
        else:
            item_cell = html.escape(item_no)
            desc_cell = html.escape(str(row.get("description") or "—"))
        markup = row.get("markup_percent")
        markup_txt = f"{float(markup):.2f}" if markup is not None else "—"
        cells = [
            item_cell,
            desc_cell,
            html.escape(str(row.get("category") or "—")),
            html.escape(str(row.get("quantity") or row.get("qty") or "")),
            html.escape(str(row.get("unit") or "")),
            html.escape(fmt_currency(row.get("unit_cost"))),
            html.escape(fmt_currency(row.get("cost_total") or row.get("total_cost"))),
            html.escape(markup_txt),
            html.escape(fmt_currency(row.get("price_total"))),
        ]
        tds = "".join(f'<td class="ips-est-mat-td">{c}</td>' for c in cells)
        body += f'<tr data-estimate-id="{eid}">{tds}</tr>'
    return (
        f'<div class="ips-est-mat-table-wrap"><table class="ips-est-mat-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


__all__ = [
    "build_estimate_material_lines_html",
    "material_detail_href",
    "material_line_link_html",
]
