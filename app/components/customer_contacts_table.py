"""Customer contacts HTML table."""

from __future__ import annotations

import html

from app.components.customers_directory_table import nested_contact_detail_href


def _contact_display_name(contact: dict) -> str:
    first = str(contact.get("first_name") or "").strip()
    last = str(contact.get("last_name") or "").strip()
    if first or last:
        return f"{first} {last}".strip()
    return str(contact.get("name") or contact.get("display_name") or "—").strip() or "—"


def _role_pill(role: str) -> str:
    text = html.escape(str(role or "—"))
    return f'<span class="ips-contact-role-pill">{text}</span>'


def _cell_text(value: object) -> tuple[str, str]:
    text = str(value or "—").strip() or "—"
    return html.escape(text), html.escape(text, quote=True)


def build_customer_contacts_html_table(
    contacts: list[dict],
    *,
    customer_id: str,
) -> str:
    if not contacts:
        return ""
    cid = str(customer_id or "").strip()
    head = "".join(
        f'<th class="ips-contacts-th">{html.escape(h)}</th>'
        for h in ("NAME", "TITLE", "LOCATION", "ROLE", "EMAIL", "PHONE")
    )
    body = ""
    for contact in contacts:
        ct_id = str(contact.get("id") or "").strip()
        name = _contact_display_name(contact)
        href = html.escape(nested_contact_detail_href(cid, ct_id), quote=True)
        name_cell = (
            f'<a class="ips-customers-open-link ips-contacts-name" href="{href}" '
            f'target="_self" aria-label="{html.escape(f"Open contact {name}", quote=True)}">'
            f"{html.escape(name)}</a>"
        )
        role = str(contact.get("role_type") or contact.get("display_role") or contact.get("title") or "—")
        email_text, email_title = _cell_text(contact.get("email"))
        phone_text, phone_title = _cell_text(contact.get("phone") or contact.get("mobile"))
        cells = [
            name_cell,
            html.escape(str(contact.get("title") or "—")),
            html.escape(str(contact.get("location_name") or "—")),
            _role_pill(role),
            f'<span class="ips-contacts-email" title="{email_title}">{email_text}</span>',
            f'<span class="ips-contacts-phone" title="{phone_title}">{phone_text}</span>',
        ]
        tds = "".join(f'<td class="ips-contacts-td">{c}</td>' for c in cells)
        body += f'<tr class="ips-contacts-tr">{tds}</tr>'
    return (
        f'<div class="ips-contacts-table-wrap"><table class="ips-contacts-html-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )
