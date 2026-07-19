"""HTML line tables for read-only Estimate Cost Builder categories."""

from __future__ import annotations

import html
from typing import Any, Callable

from app.utils.formatting import fmt_currency


def _table_html(headers: list[str], body_rows: list[list[str]]) -> str:
    if not body_rows:
        return ""
    head = "".join(f'<th class="ips-est-li-th">{html.escape(h)}</th>' for h in headers)
    body = ""
    for cells in body_rows:
        tds = "".join(f'<td class="ips-est-li-td">{c}</td>' for c in cells)
        body += f"<tr>{tds}</tr>"
    return (
        f'<div class="ips-est-line-table-wrap"><table class="ips-est-line-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def build_estimate_material_lines_html(rows: list[dict[str, Any]], *, eid: str) -> str:
    body: list[list[str]] = []
    for row in rows:
        rid = html.escape(str(row.get("id") or ""), quote=True)
        body.append(
            [
                f'<a class="ips-ecb-line-action" href="#" data-ecb-action="select" '
                f'data-ecb-category="materials" data-ecb-line-id="{rid}" '
                f'data-ecb-estimate-id="{html.escape(eid, quote=True)}">'
                f"{html.escape(str(row.get('sku') or '—'))}</a>",
                html.escape(str(row.get("description") or "—")),
                html.escape(str(row.get("quantity") or row.get("qty") or "")),
                html.escape(fmt_currency(row.get("unit_cost"))),
                html.escape(fmt_currency(row.get("cost_total"))),
                html.escape(fmt_currency(row.get("price_total"))),
            ]
        )
    return _table_html(["SKU", "Description", "Qty", "Unit Cost", "Cost", "Price"], body)


def build_estimate_equipment_lines_html(rows: list[dict[str, Any]], *, eid: str) -> str:
    body = []
    for row in rows:
        rid = html.escape(str(row.get("id") or ""), quote=True)
        body.append(
            [
                f'<a class="ips-ecb-line-action" href="#" data-ecb-action="select" '
                f'data-ecb-category="equipment" data-ecb-line-id="{rid}" '
                f'data-ecb-estimate-id="{html.escape(eid, quote=True)}">'
                f"{html.escape(str(row.get('equipment_name') or '—'))}</a>",
                html.escape(f"{row.get('duration', 0)} {row.get('duration_unit', '')}"),
                html.escape(fmt_currency(row.get("cost_total"))),
                html.escape(fmt_currency(row.get("price_total"))),
            ]
        )
    return _table_html(["Equipment", "Duration", "Cost", "Price"], body)


def build_estimate_travel_lines_html(rows: list[dict[str, Any]], *, eid: str) -> str:
    body = []
    for row in rows:
        rid = html.escape(str(row.get("id") or ""), quote=True)
        body.append(
            [
                f'<a class="ips-ecb-line-action" href="#" data-ecb-action="select" '
                f'data-ecb-category="travel" data-ecb-line-id="{rid}" '
                f'data-ecb-estimate-id="{html.escape(eid, quote=True)}">'
                f"{html.escape(str(row.get('travel_type') or '—'))}</a>",
                html.escape(str(row.get("description") or "—")),
                html.escape(fmt_currency(row.get("cost_total"))),
                html.escape(fmt_currency(row.get("price_total"))),
            ]
        )
    return _table_html(["Type", "Description", "Cost", "Price"], body)


def build_estimate_subcontractor_lines_html(rows: list[dict[str, Any]], *, eid: str) -> str:
    body = []
    for row in rows:
        rid = html.escape(str(row.get("id") or ""), quote=True)
        body.append(
            [
                f'<a class="ips-ecb-line-action" href="#" data-ecb-action="select" '
                f'data-ecb-category="subcontractors" data-ecb-line-id="{rid}" '
                f'data-ecb-estimate-id="{html.escape(eid, quote=True)}">'
                f"{html.escape(str(row.get('subcontractor_name') or row.get('vendor') or '—'))}</a>",
                html.escape(str(row.get("description") or "—")),
                html.escape(fmt_currency(row.get("cost_total"))),
                html.escape(fmt_currency(row.get("price_total"))),
            ]
        )
    return _table_html(["Vendor", "Description", "Cost", "Price"], body)


def build_estimate_other_cost_lines_html(rows: list[dict[str, Any]], *, eid: str) -> str:
    body = []
    for row in rows:
        rid = html.escape(str(row.get("id") or ""), quote=True)
        body.append(
            [
                f'<a class="ips-ecb-line-action" href="#" data-ecb-action="select" '
                f'data-ecb-category="other_costs" data-ecb-line-id="{rid}" '
                f'data-ecb-estimate-id="{html.escape(eid, quote=True)}">'
                f"{html.escape(str(row.get('description') or '—'))}</a>",
                html.escape(str(row.get("category") or "—")),
                html.escape(fmt_currency(row.get("cost_total"))),
                html.escape(fmt_currency(row.get("price_total"))),
            ]
        )
    return _table_html(["Description", "Category", "Cost", "Price"], body)


LINE_HTML_BUILDERS: dict[str, Callable[..., str]] = {
    "materials": build_estimate_material_lines_html,
    "equipment": build_estimate_equipment_lines_html,
    "travel": build_estimate_travel_lines_html,
    "subcontractors": build_estimate_subcontractor_lines_html,
    "other_costs": build_estimate_other_cost_lines_html,
}
