"""Company Updates module (Phase 2C)."""

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

try:
    from app.components.cards import render_metric_card
    from app.components.headers import render_page_header
    from app.components.tabs import render_tabs
    from app.pages._core._data import (
        demo_update_metrics,
        load_company_updates,
        load_upcoming_events,
        lookup_options,
        persist_company_update,
    )
    from app.pages._core._crud import apply_persist_feedback
    from app.styles import inject_global_css
    from app.utils.constants import UPDATE_CATEGORIES
except ImportError:
    from components.cards import render_metric_card  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages._core._data import (  # type: ignore
        demo_update_metrics,
        load_company_updates,
        load_upcoming_events,
        lookup_options,
        persist_company_update,
    )
    from pages._core._crud import apply_persist_feedback  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import UPDATE_CATEGORIES  # type: ignore

_TAB_KEY = "ips_company_updates_cat"
_SORT_OPTS = ("Newest First", "Oldest First", "Title A–Z")

_QUICK_LINKS = [
    ("📘", "Company Handbook"),
    ("🦺", "Safety Procedures"),
    ("👥", "HR Policies"),
    ("🎓", "Training Portal"),
]


def _sort_updates(rows: list[dict], sort: str) -> list[dict]:
    out = list(rows)
    if sort == "Oldest First":
        return sorted(out, key=lambda u: str(u.get("date") or ""))
    if sort == "Title A–Z":
        return sorted(out, key=lambda u: str(u.get("title") or "").lower())
    return sorted(out, key=lambda u: str(u.get("date") or ""), reverse=True)


def _update_card_html(u: dict) -> str:
    pinned = bool(u.get("pinned"))
    pin = '<span class="ips-status-pill ips-status-active" style="font-size:0.62rem;margin-right:0.35rem;">PINNED</span>' if pinned else ""
    new_dot = '<span style="color:#2563eb;font-size:0.7rem;font-weight:700;">● New</span>' if u.get("is_new") else ""
    cat = html.escape(str(u.get("category") or ""))
    title = html.escape(str(u.get("title") or ""))
    body = html.escape(str(u.get("body") or ""))
    date_s = html.escape(str(u.get("date") or ""))
    cls = "ips-update-card pinned" if pinned else "ips-update-card"
    ot = "d" + "iv"
    return (
        f'<{ot} class="{cls}">'
        f"{pin}<p class=\"ips-update-card-title\">{title}</p>"
        f"<p style='margin:0;font-size:0.8125rem;color:#475569;'>{body}</p>"
        f'<p class="ips-update-card-meta">{cat} · {date_s} {new_dot}</p>'
        f"</{ot}>"
    )


def _event_date_block(iso: str) -> str:
    try:
        d = datetime.strptime(str(iso)[:10], "%Y-%m-%d")
        return f"{d.strftime('%b').upper()}<br>{d.day}"
    except ValueError:
        return "—"


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("company_updates"):
        return
    metrics = demo_update_metrics()

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        render_page_header(
            "Company Updates",
            "Stay informed with the latest company news, announcements, and important updates.",
        )
    with hdr_r:
        if st.button("+ New Update", key="cu_new", type="primary", use_container_width=True):
            st.session_state["ips_cu_form"] = True

    if st.session_state.get("ips_cu_form"):
        with st.expander("New company update", expanded=True):
            st.text_input("Title", key="cu_new_title")
            st.text_area("Message", key="cu_new_body", height=100)
            st.selectbox("Category", lookup_options("update_categories"), key="cu_new_cat")
            st.checkbox("Pin to top", key="cu_new_pinned")
            if st.button("Publish", key="cu_save_new", type="primary"):
                ok, msg = persist_company_update(
                    {
                        "title": st.session_state.get("cu_new_title"),
                        "body": st.session_state.get("cu_new_body"),
                        "category": st.session_state.get("cu_new_cat"),
                        "pinned": st.session_state.get("cu_new_pinned"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_cu_form",)):
                    st.rerun()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Unread Updates", str(metrics.get("unread", 0)), delta="View all")
    with m2:
        render_metric_card("Pinned Updates", str(metrics.get("pinned", 0)), delta="View all")
    with m3:
        render_metric_card("Upcoming Events", str(metrics.get("events", 0)), delta="View calendar")
    with m4:
        render_metric_card("All Updates", str(metrics.get("all", 0)), delta="View all")

    main, side = st.columns([2.1, 1])

    with main:
        cats = ["All Updates", *lookup_options("update_categories")]
        cat = render_tabs(cats, session_key=_TAB_KEY, default="All Updates")
        ctrl_l, ctrl_r = st.columns([1, 1.2])
        with ctrl_l:
            sort = st.selectbox("Sort by", _SORT_OPTS, key="cu_sort", label_visibility="collapsed")
        with ctrl_r:
            st.text_input("Search updates", placeholder="Search updates…", key="cu_search", label_visibility="collapsed")

        updates = load_company_updates(category=cat)
        q = str(st.session_state.get("cu_search") or "").strip().lower()
        if q:
            updates = [
                u
                for u in updates
                if q in str(u.get("title", "")).lower() or q in str(u.get("body", "")).lower()
            ]
        updates = _sort_updates(updates, sort)[:8]

        for u in updates:
            st.markdown(_update_card_html(u), unsafe_allow_html=True)

        st.caption(f"Showing 1 to {min(len(updates), 8)} of {metrics.get('all', len(updates))} updates")

    with side:
        st.markdown("**Upcoming Events**")
        events = load_upcoming_events()
        ot = "d" + "iv"
        for ev in events:
            st.markdown(
                f'<{ot} class="ips-event-block">'
                f'<{ot} class="ips-event-date">{_event_date_block(str(ev.get("date") or ""))}</{ot}>'
                f"<{ot}><strong>{html.escape(str(ev.get('title') or ''))}</strong><br>"
                f"{html.escape(str(ev.get('time') or ''))} · {html.escape(str(ev.get('location') or ''))}</{ot}>"
                f"</{ot}>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("**Quick Links**")
        for icon, label in _QUICK_LINKS:
            st.markdown(
                f'<p class="ips-quick-link"><span>{icon} {html.escape(label)}</span><span>›</span></p>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("**Recent Updates**")
        recent = _sort_updates(load_company_updates(), "Newest First")[:4]
        for u in recent:
            st.caption(f"• {u.get('title')} — {u.get('date')}")
