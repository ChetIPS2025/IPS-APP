"""
Company Updates feed for Dashboard and other summary surfaces.

Company Updates = human announcements everyone should see (safety meetings,
policy changes, schedule changes, shop notices, new procedures, urgent alerts).

Keep separate from Recent Activity, which is automated system events
(inventory moves, tool check-in/out, scans).
"""

from __future__ import annotations

import html
from typing import Any

_CATEGORY_ICONS: dict[str, str] = {
    "HR Updates": "👥",
    "HR Update": "👥",
    "Safety Alerts": "⚠️",
    "Safety Alert": "⚠️",
    "Events": "📅",
    "Event": "📅",
    "Announcements": "📢",
    "Announcement": "📢",
    "Project Updates": "🏗️",
    "Project Update": "🏗️",
    "General": "📋",
}


def _category_icon(category: str) -> str:
    return _CATEGORY_ICONS.get(str(category or "").strip(), "📋")


def _snippet(body: str, *, max_len: int = 110) -> str:
    text = " ".join(str(body or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


# Human announcement categories shown on the Dashboard (not project/system logs).
DASHBOARD_ANNOUNCEMENT_CATEGORIES: frozenset[str] = frozenset(
    {
        "Announcement",
        "Announcements",
        "Safety Alert",
        "Safety Alerts",
        "Event",
        "Events",
        "HR Update",
        "HR Updates",
        "General",
    }
)


def _normalize_dashboard_category(raw: object) -> str:
    text = str(raw or "").strip().lower()
    if "announcement" in text:
        return "Announcement"
    if "safety" in text:
        return "Safety Alert"
    if "event" in text:
        return "Event"
    if "hr" in text:
        return "HR Update"
    if "project" in text:
        return "Project Update"
    return "General"


def dashboard_update_visible(row: dict[str, Any]) -> bool:
    """True when a human announcement should appear on the Dashboard card."""
    if not str(row.get("title") or "").strip():
        return False
    status = str(row.get("status") or "").strip().lower().replace("_", " ")
    if status in {"draft", "archived", "scheduled", "inactive"}:
        return False
    if row.get("is_active") is False:
        return False
    category = _normalize_dashboard_category(row.get("category"))
    if category == "Project Update":
        return False
    if category not in DASHBOARD_ANNOUNCEMENT_CATEGORIES:
        return category == "General"
    return True


def sort_dashboard_updates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pinned first, then newest by date."""
    by_date = sorted(
        rows,
        key=lambda row: str(row.get("date") or row.get("created_at") or ""),
        reverse=True,
    )
    return sorted(by_date, key=lambda row: not bool(row.get("pinned")))


def company_updates_feed_html(
    rows: list[dict[str, Any]],
    *,
    empty_message: str = "No company announcements right now.",
) -> str:
    """Return HTML list of recent company updates for a compact dashboard panel."""
    if not rows:
        return f'<p class="ips-panel-empty">{html.escape(empty_message)}</p>'

    ot = "d" + "iv"
    parts: list[str] = [f'<{ot} class="ips-dash-updates-feed">']
    for row in rows:
        title = html.escape(str(row.get("title") or "Untitled"))
        category = html.escape(str(row.get("category") or "General"))
        date_label = html.escape(str(row.get("date") or "")[:10] or "—")
        icon = html.escape(_category_icon(str(row.get("category") or "")))
        body = html.escape(_snippet(str(row.get("body") or "")))
        pinned = (
            f'<span class="ips-dash-update-pinned">{html.escape("Pinned")}</span>'
            if row.get("pinned")
            else ""
        )
        parts.append(
            f'<{ot} class="ips-dash-update-item">'
            f'<{ot} class="ips-dash-update-icon">{icon}</{ot}>'
            f"<{ot}>"
            f'<{ot} class="ips-dash-update-head">'
            f'<span class="ips-dash-update-title">{title}</span>'
            f"{pinned}"
            f'<span class="ips-dash-update-date">{date_label}</span>'
            f"</{ot}>"
            f'<{ot} class="ips-dash-update-meta">{category}</{ot}>'
            f'<p class="ips-dash-update-body">{body}</p>'
            f"</{ot}>"
            f"</{ot}>"
        )
    parts.append(f"</{ot}>")
    return "".join(parts)
