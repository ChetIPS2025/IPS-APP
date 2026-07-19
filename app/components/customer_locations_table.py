"""Customer locations HTML table."""

from __future__ import annotations

import html

from app.components.customers_directory_table import nested_location_detail_href


def _yes_no(val: object) -> str:
    return "Yes" if val else "No"


def build_customer_locations_html_table(
    locations: list[dict],
    *,
    customer_id: str,
) -> str:
    if not locations:
        return ""
    cid = str(customer_id or "").strip()
    head = "".join(
        f'<th class="ips-locations-th">{html.escape(h)}</th>'
        for h in ("LOCATION", "TYPE", "CITY", "STATE", "PHONE", "PRIMARY", "BILLING", "SHIPPING", "STATUS")
    )
    body = ""
    for loc in locations:
        lid = str(loc.get("id") or "").strip()
        name = str(loc.get("location_name") or loc.get("site_name") or "—").strip() or "—"
        href = html.escape(nested_location_detail_href(cid, lid), quote=True)
        name_cell = (
            f'<a class="ips-customers-open-link ips-locations-name" href="{href}" '
            f'target="_self" aria-label="{html.escape(f"Open location {name}", quote=True)}">'
            f"{html.escape(name)}</a>"
        )
        cells = [
            name_cell,
            html.escape(str(loc.get("location_type") or "Other")),
            html.escape(str(loc.get("city") or "—")),
            html.escape(str(loc.get("state") or "—")),
            html.escape(str(loc.get("phone") or "—")),
            _yes_no(loc.get("is_primary")),
            _yes_no(loc.get("is_billing")),
            _yes_no(loc.get("is_shipping")),
            html.escape(str(loc.get("status") or "Active")),
        ]
        tds = "".join(f'<td class="ips-locations-td">{c}</td>' for c in cells)
        body += f'<tr class="ips-locations-tr">{tds}</tr>'
    return (
        f'<div class="ips-locations-table-wrap"><table class="ips-locations-html-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )
