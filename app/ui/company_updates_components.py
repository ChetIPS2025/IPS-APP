"""Company Updates page — layout, KPI cards, feed cards, and sidebar widgets."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

import streamlit as st

IPS_CU_PAGE_STYLES_KEY = "ips_company_updates_page_styles_v2"
PAGE_MARKER = "ips-company-updates-page"

DISPLAY_TABS: tuple[str, ...] = (
    "All Updates",
    "Announcements",
    "Safety Alerts",
    "Events",
    "HR Updates",
    "Project Updates",
)

TAB_TO_CATEGORIES: dict[str, frozenset[str] | None] = {
    "All Updates": None,
    "Announcements": frozenset({"General", "Policy"}),
    "Safety Alerts": frozenset({"Safety", "Urgent"}),
    "Events": frozenset({"Schedule"}),
    "HR Updates": frozenset({"HR / Payroll"}),
    "Project Updates": frozenset({"Equipment", "Training"}),
}

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

_CATEGORY_ICON: dict[str, tuple[str, str]] = {
    "Announcements": ("#dbeafe", "#2563eb"),
    "Safety Alerts": ("#fee2e2", "#dc2626"),
    "Events": ("#dcfce7", "#16a34a"),
    "HR Updates": ("#f3e8ff", "#7c3aed"),
    "Project Updates": ("#ffedd5", "#ea580c"),
    "General": ("#dbeafe", "#2563eb"),
}

_SORT_OPTIONS: tuple[str, ...] = ("Newest First", "Oldest First", "Priority")


def display_category(raw: str) -> str:
    c = str(raw or "").strip()
    return _CATEGORY_DISPLAY.get(c, c or "Announcements")


def display_department(display_cat: str) -> str:
    return {
        "HR Updates": "HR Department",
        "Safety Alerts": "Safety Department",
        "Events": "Events Team",
        "Announcements": "Corporate Communications",
        "Project Updates": "Operations",
    }.get(display_cat, "IPS Communications")


# KPI icon SVGs (mockup: purple megaphone, green bell, orange calendar, blue doc)
_KPI_SVG_UNREAD = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<path d="M12 3L4 8v5c0 4.4 3.6 8 8 8s8-3.6 8-8V8l-8-5z" stroke="#7c3aed" stroke-width="1.6"/>'
    '<path d="M9 18c0 1.7 1.3 3 3 3s3-1.3 3-3" stroke="#7c3aed" stroke-width="1.6"/></svg>'
)
_KPI_SVG_PINNED = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<path d="M12 3a2 2 0 0 1 2 2v1h2v2h-2v9l3 2v1H7v-1l3-2V8H8V6h2V5a2 2 0 0 1 2-2z" stroke="#16a34a" stroke-width="1.5"/></svg>'
)
_KPI_SVG_EVENTS = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<rect x="4" y="5" width="16" height="15" rx="2" stroke="#ea580c" stroke-width="1.5"/>'
    '<path d="M8 3v4M16 3v4M4 10h16" stroke="#ea580c" stroke-width="1.5"/></svg>'
)
_KPI_SVG_ALL = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<path d="M8 2h8l4 4v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" stroke="#2563eb" stroke-width="1.5"/>'
    '<path d="M14 2v6h6M9 13h6M9 17h4" stroke="#2563eb" stroke-width="1.5" stroke-linecap="round"/></svg>'
)

KPI_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("unread", "#ede9fe", _KPI_SVG_UNREAD, "Unread Updates"),
    ("pinned", "#dcfce7", _KPI_SVG_PINNED, "Pinned Updates"),
    ("events", "#ffedd5", _KPI_SVG_EVENTS, "Upcoming Events"),
    ("all", "#dbeafe", _KPI_SVG_ALL, "All Updates"),
)


def inject_company_updates_page_styles() -> None:
    if st.session_state.get(IPS_CU_PAGE_STYLES_KEY):
        return
    st.session_state[IPS_CU_PAGE_STYLES_KEY] = True
    try:
        from app.ui.page_shell import inject_ips_dashboard_layout
    except ImportError:
        from ui.page_shell import inject_ips_dashboard_layout  # type: ignore
    inject_ips_dashboard_layout()
    p = PAGE_MARKER
    st.markdown(
        f"""
        <style>
        section[data-testid="stMain"]:has(.{p}) .block-container {{
            max-width: 1680px !important;
            padding-top: 0.5rem !important;
        }}
        section[data-testid="stMain"]:has(.{p}) .ips-cu-header-flat {{
            margin-bottom: 1rem;
        }}
        .ips-cu-page-title {{
            margin: 0;
            font-size: 1.5rem;
            font-weight: 700;
            color: #111827;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }}
        .ips-cu-page-sub {{
            margin: 0.35rem 0 0;
            font-size: 0.875rem;
            color: #6b7280;
            line-height: 1.45;
            max-width: 52rem;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-hdr-actions) {{
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }}

        /* KPI row */
        section[data-testid="stMain"]:has(.{p}) .ips-cu-kpi-row {{
            margin-bottom: 0.65rem;
        }}
        .ips-cu-kpi-card {{
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 10px;
            padding: 0.9rem 1rem 0.7rem;
            box-shadow: none;
            height: 100%;
            box-sizing: border-box;
        }}
        .ips-cu-kpi-top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.5rem;
        }}
        .ips-cu-kpi-icon {{
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}
        .ips-cu-kpi-icon svg {{ display: block; }}
        .ips-cu-kpi-value {{
            font-size: 1.65rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.1;
            margin: 0.35rem 0 0.1rem;
        }}
        .ips-cu-kpi-label {{
            font-size: 0.8125rem;
            font-weight: 600;
            color: #374151;
            margin: 0;
        }}
        .ips-cu-kpi-link {{
            display: inline-block;
            margin-top: 0.55rem;
            font-size: 0.8125rem;
            font-weight: 600;
            color: #2563eb;
            text-decoration: none;
        }}
        .ips-cu-kpi-link:hover {{ text-decoration: underline; }}

        /* Main feed panel */
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-cu-feed-panel) {{
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 10px !important;
            box-shadow: none !important;
            margin-bottom: 0.65rem !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-cu-feed-panel) > div {{
            padding: 0.75rem 0.85rem 0.85rem !important;
        }}

        /* Tabs */
        section[data-testid="stMain"]:has(.{p}) .ips-cu-tab-bar {{
            border-bottom: 1px solid #e5eaf2;
            margin-bottom: 0.65rem;
            padding-bottom: 0.15rem;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-tab-active) .stButton > button {{
            color: #2563eb !important;
            border-bottom: 2px solid #2563eb !important;
            border-radius: 0 !important;
            background: transparent !important;
            border-top: none !important;
            border-left: none !important;
            border-right: none !important;
            box-shadow: none !important;
            font-weight: 600 !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-tab-cell) .stButton > button {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #6b7280 !important;
            font-weight: 500 !important;
            border-radius: 0 !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-cu-feed-toolbar) {{
            margin-bottom: 0.5rem !important;
        }}

        /* Feed cards */
        .ips-cu-feed-card-wrap {{
            margin-bottom: 0.65rem;
        }}
        .ips-cu-feed-card {{
            display: flex;
            gap: 0.85rem;
            align-items: flex-start;
            border: 1px solid #e5eaf2;
            border-radius: 10px;
            padding: 0.85rem 0.75rem 0.85rem 1rem;
            background: #ffffff;
            transition: border-color 0.12s ease;
        }}
        .ips-cu-feed-card:hover {{
            border-color: #d1d5db;
        }}
        .ips-cu-feed-inner {{
            display: flex;
            gap: 0.85rem;
            align-items: flex-start;
            flex: 1;
            min-width: 0;
        }}
        .ips-cu-feed-card.urgent {{
            border-left: 4px solid #ef4444;
        }}
        .ips-cu-feed-avatar {{
            width: 2.75rem;
            height: 2.75rem;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.15rem;
            flex-shrink: 0;
        }}
        .ips-cu-feed-body {{ flex: 1; min-width: 0; }}
        .ips-cu-feed-title-row {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-bottom: 0.25rem;
        }}
        .ips-cu-feed-title {{
            margin: 0;
            font-size: 0.98rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.3;
        }}
        .ips-cu-pin-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.2rem;
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: #15803d;
            background: #ecfdf5;
            border: 1px solid #bbf7d0;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            margin-bottom: 0.35rem;
        }}
        .ips-cu-feed-preview {{
            margin: 0.2rem 0 0.45rem;
            font-size: 0.8125rem;
            color: #4b5563;
            line-height: 1.45;
        }}
        .ips-cu-feed-meta {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.75rem;
            color: #6b7280;
        }}
        .ips-cu-cat-pill {{
            display: inline-block;
            padding: 0.12rem 0.5rem;
            border-radius: 999px;
            font-size: 0.68rem;
            font-weight: 600;
            border: 1px solid transparent;
        }}
        .ips-cu-feed-actions {{
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 0.65rem;
            padding-top: 0.1rem;
            min-width: 3.5rem;
        }}
        .ips-cu-menu-dots {{
            color: #9ca3af;
            font-size: 1.15rem;
            line-height: 1;
            letter-spacing: 0.05em;
            user-select: none;
        }}
        .ips-cu-status-new {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            font-size: 0.75rem;
            font-weight: 600;
            color: #2563eb;
        }}
        .ips-cu-status-new .dot {{
            width: 0.45rem;
            height: 0.45rem;
            border-radius: 999px;
            background: #2563eb;
        }}
        .ips-cu-status-read {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
            color: #16a34a;
        }}

        /* Sidebar widgets */
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-cu-sidebar-widget) {{
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 10px !important;
            box-shadow: none !important;
            margin-bottom: 0.65rem !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-cu-sidebar-widget) > div {{
            padding: 0.75rem 0.85rem !important;
        }}
        .ips-cu-widget-head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.55rem;
        }}
        .ips-cu-widget-title {{
            margin: 0;
            font-size: 0.9rem;
            font-weight: 700;
            color: #111827;
        }}
        .ips-cu-widget-link {{
            font-size: 0.78rem;
            font-weight: 600;
            color: #2563eb;
            text-decoration: none;
        }}
        .ips-cu-widget-link:hover {{ text-decoration: underline; }}
        .ips-cu-event-row {{
            display: flex;
            gap: 0.65rem;
            padding: 0.45rem 0;
            border-bottom: 1px solid #f1f5f9;
        }}
        .ips-cu-event-row:last-child {{ border-bottom: none; }}
        .ips-cu-event-date {{
            width: 2.65rem;
            text-align: center;
            flex-shrink: 0;
            background: #faf5ff;
            border: 1px solid #e9d5ff;
            border-radius: 8px;
            padding: 0.25rem 0.2rem;
        }}
        .ips-cu-event-date .mo {{
            font-size: 0.58rem;
            font-weight: 700;
            color: #7c3aed;
            text-transform: uppercase;
        }}
        .ips-cu-event-date .dy {{
            font-size: 1rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.1;
        }}
        .ips-cu-event-title {{
            font-size: 0.8125rem;
            font-weight: 600;
            color: #111827;
            margin: 0 0 0.12rem;
        }}
        .ips-cu-event-sub {{
            font-size: 0.72rem;
            color: #6b7280;
            margin: 0;
        }}
        .ips-cu-quick-link {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #f1f5f9;
            font-size: 0.8125rem;
            color: #374151;
            text-decoration: none;
        }}
        .ips-cu-quick-link:last-child {{ border-bottom: none; }}
        .ips-cu-quick-link:hover {{ color: #2563eb; }}
        .ips-cu-recent-row {{
            display: flex;
            gap: 0.5rem;
            align-items: flex-start;
            padding: 0.4rem 0;
            border-bottom: 1px solid #f1f5f9;
        }}
        .ips-cu-recent-row:last-child {{ border-bottom: none; }}
        .ips-cu-recent-ico {{
            width: 1.65rem;
            height: 1.65rem;
            border-radius: 8px;
            background: #eff6ff;
            color: #2563eb;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            flex-shrink: 0;
        }}
        .ips-cu-recent-title {{
            font-size: 0.78rem;
            font-weight: 600;
            color: #111827;
            margin: 0;
            line-height: 1.3;
        }}
        .ips-cu-recent-date {{
            font-size: 0.68rem;
            color: #9ca3af;
            margin: 0.1rem 0 0;
        }}

        /* Pagination */
        .ips-cu-pagination {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 0.65rem;
            margin-top: 0.35rem;
            padding-top: 0.55rem;
            border-top: 1px solid #f1f5f9;
        }}
        .ips-cu-pagination-info {{
            font-size: 0.78rem;
            color: #6b7280;
            margin: 0;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-page-btn) .stButton > button {{
            min-width: 2rem !important;
            min-height: 2rem !important;
            padding: 0.2rem 0.45rem !important;
            border-radius: 8px !important;
            font-size: 0.78rem !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-page-active) .stButton > button {{
            background: #2563eb !important;
            border-color: #2563eb !important;
            color: #fff !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-menu-col) .stButton > button {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #9ca3af !important;
            font-size: 1.2rem !important;
            min-height: auto !important;
            padding: 0.15rem 0.25rem !important;
            letter-spacing: 0.08em !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-kpi-link-btn) .stButton > button {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #2563eb !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            min-height: auto !important;
            padding: 0.35rem 0 0 !important;
            justify-content: flex-start !important;
            text-align: left !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-kpi-link-btn) .stButton > button:hover {{
            text-decoration: underline !important;
            background: transparent !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-feed-item) {{
            align-items: flex-start !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-feed-menu-col) {{
            margin-top: 0.15rem !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-cu-toolbar-row) {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-cu-toolbar-row) > div {{
            padding: 0 0 0.5rem 0 !important;
        }}
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-hdr-actions) .stButton > button[kind="secondary"],
        section[data-testid="stMain"]:has(.{p})
        div[data-testid="column"]:has(.ips-cu-hdr-actions) [data-testid="stPopover"] > button {{
            background: #fff !important;
            border: 1px solid #e5eaf2 !important;
            color: #374151 !important;
            font-weight: 600 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_marker() -> None:
    st.markdown(
        f'<span class="{PAGE_MARKER}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )



def render_page_header_html() -> None:
    st.markdown(
        """
        <div>
          <p class="ips-cu-page-title">Company Updates</p>
          <p class="ips-cu-page-sub">Stay informed with the latest company news, announcements and important updates.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )



def kpi_stat_card_html(
    *,
    icon_svg: str,
    icon_bg: str,
    value: int | str,
    label: str,
) -> str:
    return (
        f'<div class="ips-cu-kpi-card">'
        f'<div class="ips-cu-kpi-top">'
        f'<div class="ips-cu-kpi-icon" style="background:{html.escape(icon_bg)};">'
        f"{icon_svg}</div></div>"
        f'<p class="ips-cu-kpi-value">{html.escape(str(value))}</p>'
        f'<p class="ips-cu-kpi-label">{html.escape(label)}</p>'
        f"</div>"
    )


def _cat_pill_style(display_cat: str) -> tuple[str, str, str]:
    styles = {
        "Announcements": ("#dbeafe", "#1d4ed8", "#bfdbfe"),
        "Safety Alerts": ("#fee2e2", "#b91c1c", "#fecaca"),
        "Events": ("#dcfce7", "#15803d", "#bbf7d0"),
        "HR Updates": ("#f3e8ff", "#6d28d9", "#e9d5ff"),
        "Project Updates": ("#ffedd5", "#c2410c", "#fed7aa"),
    }
    return styles.get(display_cat, ("#f1f5f9", "#475569", "#e2e8f0"))


def _avatar_glyph(display_cat: str) -> str:
    return {
        "Announcements": "📢",
        "Safety Alerts": "⚠",
        "Events": "📅",
        "HR Updates": "👥",
        "Project Updates": "🏗",
    }.get(display_cat, "📋")


def feed_card_html(
    *,
    title: str,
    preview: str,
    display_cat: str,
    date_label: str,
    department: str,
    is_pinned: bool,
    is_read: bool,
    urgent: bool,
) -> str:
    bg, fg, border = _cat_pill_style(display_cat)
    av_bg, _ = _CATEGORY_ICON.get(display_cat, ("#e0e7ff", "#2563eb"))
    glyph = _avatar_glyph(display_cat)
    pin_row = (
        '<div class="ips-cu-pin-badge">&#128204; PINNED</div>' if is_pinned else ""
    )
    status = (
        '<div class="ips-cu-status-read"><span>✓</span> Read</div>'
        if is_read
        else '<div class="ips-cu-status-new"><span class="dot"></span> New</div>'
    )
    urgent_cls = " urgent" if urgent else ""
    return (
        f'<div class="ips-cu-feed-card{urgent_cls}">'
        f"{pin_row}"
        f'<div class="ips-cu-feed-inner">'
        f'<div class="ips-cu-feed-avatar" style="background:{html.escape(av_bg)};">{glyph}</div>'
        f'<div class="ips-cu-feed-body">'
        f'<p class="ips-cu-feed-title">{html.escape(title)}</p>'
        f'<p class="ips-cu-feed-preview">{html.escape(preview)}</p>'
        f'<div class="ips-cu-feed-meta">'
        f'<span class="ips-cu-cat-pill" style="background:{bg};color:{fg};border-color:{border};">'
        f"{html.escape(display_cat)}</span>"
        f"<span>{html.escape(date_label)}</span>"
        f"<span>· {html.escape(department)}</span>"
        f"</div></div>"
        f'<div class="ips-cu-feed-actions">{status}'
        f'<span class="ips-cu-menu-dots" aria-hidden="true">&#8943;</span></div>'
        f"</div></div>"
    )


def upcoming_events_widget_html(events: list[dict[str, str]]) -> str:
    rows = ""
    for ev in events[:5]:
        rows += (
            f'<div class="ips-cu-event-row">'
            f'<div class="ips-cu-event-date">'
            f'<div class="mo">{html.escape(ev.get("month", ""))}</div>'
            f'<div class="dy">{html.escape(ev.get("day", ""))}</div>'
            f"</div>"
            f"<div>"
            f'<p class="ips-cu-event-title">{html.escape(ev.get("title", "—"))}</p>'
            f'<p class="ips-cu-event-sub">{html.escape(ev.get("time", ""))}'
            f'{(" · " + html.escape(ev.get("location", ""))) if ev.get("location") else ""}</p>'
            f"</div></div>"
        )
    if not rows:
        rows = '<p style="margin:0;font-size:0.78rem;color:#9ca3af;">No upcoming events scheduled.</p>'
    return (
        f'<div class="ips-cu-widget-head">'
        f'<p class="ips-cu-widget-title">Upcoming Events</p>'
        f'<span class="ips-cu-widget-link">View Calendar</span></div>'
        f"{rows}"
    )


def quick_links_widget_html() -> str:
    links = (
        ("📘", "Company Handbook"),
        ("🦺", "Safety Procedures"),
        ("📋", "HR Policies"),
        ("🎓", "Training Portal"),
    )
    body = "".join(
        f'<div class="ips-cu-quick-link"><span>{html.escape(ico)} {html.escape(lbl)}</span>'
        f'<span style="color:#9ca3af;">›</span></div>'
        for ico, lbl in links
    )
    return f'<p class="ips-cu-widget-title" style="margin-bottom:0.55rem;">Quick Links</p>{body}'


def recent_updates_widget_html(items: list[dict[str, str]]) -> str:
    rows = ""
    for it in items[:5]:
        rows += (
            f'<div class="ips-cu-recent-row">'
            f'<div class="ips-cu-recent-ico">📄</div>'
            f"<div>"
            f'<p class="ips-cu-recent-title">{html.escape(it.get("title", "—"))}</p>'
            f'<p class="ips-cu-recent-date">{html.escape(it.get("date", ""))}</p>'
            f"</div></div>"
        )
    if not rows:
        rows = '<p style="margin:0;font-size:0.78rem;color:#9ca3af;">No recent updates.</p>'
    return (
        f'<div class="ips-cu-widget-head">'
        f'<p class="ips-cu-widget-title">Recent Updates</p>'
        f'<span class="ips-cu-widget-link">View All</span></div>'
        f"{rows}"
    )


def pagination_info_html(start: int, end: int, total: int) -> str:
    if total <= 0:
        return '<p class="ips-cu-pagination-info">No updates to display</p>'
    return (
        f'<p class="ips-cu-pagination-info">Showing {start} to {end} of {total} updates</p>'
    )


def parse_event_date(raw: Any) -> tuple[str, str, str] | None:
    """Return (month_abbr, day_str, iso) from expires_at or created_at."""
    if raw is None or str(raw).strip() == "":
        return None
    s = str(raw).strip()
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s[:10] + "T12:00:00")
        return (dt.strftime("%b").upper(), dt.strftime("%d").lstrip("0") or "0", s[:10])
    except Exception:
        return None
