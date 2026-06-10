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

import streamlit as st

try:
    from app.utils.formatting import fmt_date
except ImportError:
    from utils.formatting import fmt_date  # type: ignore

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


def _author_label(row: dict[str, Any]) -> str:
    for key in ("created_by_name", "posted_by", "author_name", "author", "created_by"):
        val = str(row.get(key) or "").strip()
        if val and len(val) < 120:
            return val
    return "IPS Team"


def _display_category(category: object) -> str:
    cat = _normalize_dashboard_category(category)
    short = {
        "Safety Alert": "Safety",
        "HR Update": "HR",
        "Announcement": "Announcement",
        "Event": "Event",
        "General": "General",
        "Project Update": "Project",
    }
    return short.get(cat, cat)


def _posted_meta(row: dict[str, Any]) -> str:
    author = _author_label(row)
    date_label = fmt_date(row.get("date") or row.get("created_at"))
    category = _display_category(row.get("category"))
    return f"Posted by {author} · {date_label} · {category}"


def _split_featured_and_recent(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not rows:
        return None, []
    featured = rows[0]
    recent = rows[1:6]
    return featured, recent


def dashboard_company_updates_hero_html(
    rows: list[dict[str, Any]],
    *,
    empty_message: str = "No company announcements right now.",
) -> str:
    """Full-width featured update + recent list for the Dashboard hero section."""
    featured, recent = _split_featured_and_recent(rows)
    ot = "d" + "iv"
    if featured is None:
        return f'<p class="ips-dash-cu-empty">{html.escape(empty_message)}</p>'

    icon = html.escape(_category_icon(str(featured.get("category") or "")))
    title = html.escape(str(featured.get("title") or "Untitled"))
    body = html.escape(_snippet(str(featured.get("body") or ""), max_len=220))
    meta = html.escape(_posted_meta(featured))
    pinned = (
        f'<span class="ips-dash-cu-featured-badge">{html.escape("Important")}</span>'
        if featured.get("pinned")
        else ""
    )

    recent_html = ""
    if recent:
        items = "".join(
            f'<li class="ips-dash-cu-recent-item">'
            f'<span class="ips-dash-cu-recent-bullet" aria-hidden="true">•</span>'
            f'<span class="ips-dash-cu-recent-name">{html.escape(str(row.get("title") or "Untitled"))}</span>'
            f"</li>"
            for row in recent
        )
        recent_html = (
            f'<{ot} class="ips-dash-cu-recent">'
            f'<p class="ips-dash-cu-recent-heading">Recent Updates</p>'
            f'<ul class="ips-dash-cu-recent-list">{items}</ul>'
            f"</{ot}>"
        )

    return (
        f'<{ot} class="ips-dash-cu-body">'
        f'<{ot} class="ips-dash-cu-featured">'
        f'<{ot} class="ips-dash-cu-featured-icon">{icon}</{ot}>'
        f'<{ot} class="ips-dash-cu-featured-content">'
        f'<{ot} class="ips-dash-cu-featured-head">'
        f'<h2 class="ips-dash-cu-featured-title">{title}</h2>'
        f"{pinned}"
        f"</{ot}>"
        f'<p class="ips-dash-cu-featured-body">{body}</p>'
        f'<p class="ips-dash-cu-featured-meta">{meta}</p>'
        f"</{ot}>"
        f"</{ot}>"
        f"{recent_html}"
        f"</{ot}>"
    )


def render_dashboard_company_updates_section(
    rows: list[dict[str, Any]],
    *,
    empty_message: str = "No company announcements right now.",
) -> None:
    """Primary Dashboard communication panel — featured update, recent list, and actions."""
    ot = "d" + "iv"

    def _go_company_updates(*, open_new: bool = False) -> None:
        try:
            from app.navigation import set_nav_slug
        except ImportError:
            from navigation import set_nav_slug  # type: ignore
        if open_new:
            st.session_state["ips_cu_form"] = True
        set_nav_slug("company_updates")
        st.rerun()

    with st.container(key="dashboard_company_updates"):
        hdr_l, hdr_r = st.columns([2.35, 1.65], gap="small", vertical_alignment="center")
        with hdr_l:
            st.markdown(
                f'<{ot} class="ips-dash-cu-hero-head">'
                f'<p class="ips-dash-cu-hero-title">Company Updates</p>'
                f'<p class="ips-dash-cu-hero-subtitle">'
                f"Human announcements — safety, policy, schedule, and shop notices"
                f"</p>"
                f"</{ot}>",
                unsafe_allow_html=True,
            )
        with hdr_r:
            b_new, b_all = st.columns(2, gap="small")
            with b_new:
                if st.button(
                    "+ New Update",
                    key="ips_dash_cu_new",
                    type="primary",
                    use_container_width=True,
                ):
                    _go_company_updates(open_new=True)
            with b_all:
                if st.button("View All", key="ips_dash_cu_all", use_container_width=True):
                    _go_company_updates()

        st.markdown(
            dashboard_company_updates_hero_html(rows, empty_message=empty_message),
            unsafe_allow_html=True,
        )


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
