"""
Company Updates feed for Dashboard and other summary surfaces.

Connecteam-style news feed: author header, card per update, read badges,
and quick actions — separate from automated Recent Activity.
"""

from __future__ import annotations

import html
from datetime import date
from typing import Any

import streamlit as st

try:
    from app.utils.formatting import fmt_date
except ImportError:
    from utils.formatting import fmt_date  # type: ignore

_CATEGORY_DISPLAY: dict[str, str] = {
    "General": "Announcements",
    "Policy": "Announcements",
    "Safety": "Safety Alerts",
    "Urgent": "Safety Alerts",
    "Schedule": "Events",
    "HR / Payroll": "HR Updates",
    "Equipment": "Project Updates",
    "Training": "Project Updates",
}


def _display_category(raw: str) -> str:
    c = str(raw or "").strip()
    return _CATEGORY_DISPLAY.get(c, c or "Announcements")


def _display_department(display_cat: str) -> str:
    return {
        "HR Updates": "HR Department",
        "Safety Alerts": "Safety Department",
        "Events": "Events Team",
        "Announcements": "Corporate Communications",
        "Project Updates": "Operations",
    }.get(display_cat, "IPS Communications")

_DASHBOARD_READ_KEY = "ips_dash_cu_read_ids"


def _snippet(body: str, *, max_len: int = 160) -> str:
    text = " ".join(str(body or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


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


def _raw_category_for_display(normalized: str) -> str:
    return {
        "Announcement": "General",
        "Safety Alert": "Safety",
        "Event": "Schedule",
        "HR Update": "HR / Payroll",
        "Project Update": "Equipment",
        "General": "General",
    }.get(normalized, "General")


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


def _author_initials(name: str) -> str:
    parts = [p for p in str(name or "").replace(".", " ").split() if p]
    if not parts:
        return "IP"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()


def _relative_posted_label(row: dict[str, Any]) -> str:
    raw = str(row.get("date") or row.get("created_at") or "")[:10]
    if not raw:
        return "Recently"
    try:
        posted = date.fromisoformat(raw)
    except ValueError:
        return fmt_date(raw)
    delta = (date.today() - posted).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    if delta < 7:
        return f"{delta} days ago"
    return fmt_date(raw)


def _dashboard_read_ids() -> set[str]:
    raw = st.session_state.get(_DASHBOARD_READ_KEY)
    if isinstance(raw, set):
        return raw
    if isinstance(raw, list):
        return set(str(x) for x in raw)
    return set()


def _mark_dashboard_update_read(update_id: str) -> None:
    uid = str(update_id or "").strip()
    if not uid:
        return
    seen = _dashboard_read_ids()
    seen.add(uid)
    st.session_state[_DASHBOARD_READ_KEY] = seen


def _is_update_unread(row: dict[str, Any]) -> bool:
    uid = str(row.get("id") or "").strip()
    if uid and uid in _dashboard_read_ids():
        return False
    if row.get("is_new") is False:
        return False
    return True


def connecteam_feed_card_compact_html(row: dict[str, Any]) -> str:
    """Ultra-compact dashboard announcement card (max ~120px)."""
    ot = "d" + "iv"
    author = _author_label(row)
    initials = html.escape(_author_initials(author))
    title = html.escape(str(row.get("title") or "Untitled"))
    body = html.escape(_snippet(str(row.get("body") or ""), max_len=90))
    posted = html.escape(_relative_posted_label(row))
    author_esc = html.escape(author)
    is_pinned = bool(row.get("pinned"))
    is_unread = _is_update_unread(row)

    card_cls = " ips-ct-feed-card-unread" if is_unread else " ips-ct-feed-card-read"
    if is_pinned:
        card_cls += " ips-ct-feed-card-pinned"

    pin_html = (
        '<span class="ips-ct-pin ips-ct-pin-inline ips-ct-pin-badge">📌 Pinned</span>'
        if is_pinned
        else ""
    )

    return (
        f'<{ot} class="news-card ips-ct-feed-card ips-ct-feed-card-compact ips-ct-feed-card-ultra{card_cls}">'
        f'<{ot} class="news-card-head">'
        f'<{ot} class="ips-ct-avatar ips-ct-avatar-sm" aria-hidden="true">{initials}</{ot}>'
        f'<{ot} class="news-card-meta ips-ct-compact-meta">'
        f'<span class="ips-ct-author">{author_esc}</span>'
        f'<span class="ips-ct-meta">{posted}</span>'
        f"{pin_html}"
        f"</{ot}>"
        f"</{ot}>"
        f'<h4 class="news-card-title ips-ct-title ips-ct-title-compact">{title}</h4>'
        f'<p class="news-card-preview ips-ct-body ips-ct-body-compact">{body}</p>'
        f"</{ot}>"
    )


def connecteam_feed_card_html(row: dict[str, Any]) -> str:
    """Single Connecteam-style announcement card."""
    ot = "d" + "iv"
    normalized = _normalize_dashboard_category(row.get("category"))
    display_cat = _display_category(_raw_category_for_display(normalized))
    department = _display_department(display_cat)
    author = _author_label(row)
    initials = html.escape(_author_initials(author))
    title = html.escape(str(row.get("title") or "Untitled"))
    body = html.escape(_snippet(str(row.get("body") or ""), max_len=220))
    posted = html.escape(_relative_posted_label(row))
    author_esc = html.escape(author)
    is_pinned = bool(row.get("pinned"))
    is_unread = _is_update_unread(row)
    urgent = normalized == "Safety Alert" or str(row.get("priority") or "").lower() == "urgent"

    card_cls = " ips-ct-feed-card-unread" if is_unread else " ips-ct-feed-card-read"
    if is_pinned:
        card_cls += " ips-ct-feed-card-pinned"
    if urgent:
        card_cls += " ips-ct-feed-card-urgent"

    bg, fg, border = {
        "Announcements": ("#dbeafe", "#1d4ed8", "#bfdbfe"),
        "Safety Alerts": ("#fee2e2", "#b91c1c", "#fecaca"),
        "Events": ("#dcfce7", "#15803d", "#bbf7d0"),
        "HR Updates": ("#f3e8ff", "#6d28d9", "#e9d5ff"),
    }.get(display_cat, ("#f1f5f9", "#475569", "#e2e8f0"))

    status_html = (
        f'<span class="ips-ct-status ips-ct-status-new"><span class="dot"></span>New</span>'
        if is_unread
        else '<span class="ips-ct-status ips-ct-status-read">✓ Read</span>'
    )
    pin_html = (
        f'<span class="ips-ct-pin">📌 Pinned</span>' if is_pinned else ""
    )

    return (
        f'<{ot} class="ips-ct-feed-card{card_cls}">'
        f'<{ot} class="ips-ct-feed-head">'
        f'<{ot} class="ips-ct-avatar" aria-hidden="true">{initials}</{ot}>'
        f'<{ot} class="ips-ct-head-text">'
        f'<span class="ips-ct-author">{author_esc}</span>'
        f'<span class="ips-ct-meta">{posted} · {html.escape(department)}</span>'
        f"</{ot}>"
        f"{status_html}"
        f"</{ot}>"
        f'<h3 class="ips-ct-title">{title}</h3>'
        f'<p class="ips-ct-body">{body}</p>'
        f'<{ot} class="ips-ct-foot">'
        f'<span class="ips-ct-cat-pill" style="background:{bg};color:{fg};border:1px solid {border};">'
        f"{html.escape(display_cat)}</span>"
        f"{pin_html}"
        f"</{ot}>"
        f"</{ot}>"
    )


def dashboard_company_updates_feed_html(
    rows: list[dict[str, Any]],
    *,
    empty_message: str = "No company announcements right now.",
) -> str:
    if not rows:
        return f'<p class="ips-dash-cu-empty">{html.escape(empty_message)}</p>'
    ot = "d" + "iv"
    cards = "".join(
        f'<{ot} class="ips-ct-feed-card-wrap">{connecteam_feed_card_html(row)}</{ot}>'
        for row in rows
    )
    return f'<{ot} class="ips-ct-feed-stack">{cards}</{ot}>'


def _open_company_update(update_id: str) -> None:
    uid = str(update_id or "").strip()
    if not uid:
        return
    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    st.session_state["selected_update_id"] = uid
    st.session_state["show_update_detail_modal"] = True
    set_nav_slug("company_updates")
    st.rerun()


def _go_company_updates_page(*, open_new: bool = False) -> None:
    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    if open_new:
        st.session_state["ips_cu_form"] = True
    set_nav_slug("company_updates")
    st.rerun()


def _dashboard_item_key(uid: str, idx: int) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(uid or ""))[:40] or f"row_{idx}"
    return f"dashboard_cu_item_{safe}"


def render_dashboard_company_updates_section(
    rows: list[dict[str, Any]],
    *,
    empty_message: str = "No company announcements right now.",
    limit: int = 5,
) -> None:
    """Compact company news feed on the operations dashboard."""
    ot = "d" + "iv"
    display_rows = list(rows)[: max(1, int(limit))]

    with st.container(key="dashboard_company_updates"):
        hdr_l, hdr_r = st.columns([2, 1], gap="small", vertical_alignment="center")
        with hdr_l:
            st.markdown(
                f'<p class="ips-ops-news-title">Recent Company News</p>',
                unsafe_allow_html=True,
            )
        with hdr_r:
            btn_post, btn_all = st.columns(2, gap="small")
            with btn_post:
                if st.button("+ Post Update", key="ips_dash_cu_new", type="primary", use_container_width=True):
                    _go_company_updates_page(open_new=True)
            with btn_all:
                if st.button("View All", key="ips_dash_cu_all", use_container_width=True):
                    _go_company_updates_page()

        if not display_rows:
            st.markdown(
                f'<p class="ips-dash-cu-empty">{html.escape(empty_message)}</p>',
                unsafe_allow_html=True,
            )
            return

        for idx, row in enumerate(display_rows):
            uid = str(row.get("id") or "").strip()
            with st.container(key=_dashboard_item_key(uid, idx)):
                st.markdown(
                    '<span class="ips-ops-news-item-marker" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<{ot} class="ips-ct-feed-card-wrap ips-ct-feed-card-wrap-compact">'
                    f"{connecteam_feed_card_compact_html(row)}"
                    f"</{ot}>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<span class="news-footer ips-ops-news-footer-marker" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                btn_open, btn_read = st.columns(2, gap="small")
                with btn_open:
                    if uid and st.button(
                        "Open",
                        key=f"ips_dash_cu_open_{uid}",
                        type="primary",
                        use_container_width=True,
                    ):
                        _mark_dashboard_update_read(uid)
                        _open_company_update(uid)
                with btn_read:
                    if uid and _is_update_unread(row):
                        if st.button(
                            "Mark read",
                            key=f"ips_dash_cu_read_{uid}",
                            use_container_width=True,
                        ):
                            _mark_dashboard_update_read(uid)
                            st.rerun()


def company_updates_feed_html(
    rows: list[dict[str, Any]],
    *,
    empty_message: str = "No company announcements right now.",
) -> str:
    """Compact HTML feed (legacy callers)."""
    return dashboard_company_updates_feed_html(rows, empty_message=empty_message)
