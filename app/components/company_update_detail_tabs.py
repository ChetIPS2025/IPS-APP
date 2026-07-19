"""Conditional detail tabs for Company Update modal."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlparse

import streamlit as st

from app.components.company_updates_permissions import CompanyUpdatesPermissions
from app.components.record_modal import detail_field_html, dialog_card_html, placeholder_html
from app.components.tabs import render_tabs
from app.components.company_updates_feed import priority_for_form
from app.services.company_update_detail_service import get_company_update_banner_preview
from app.services.company_updates_directory_service import (
    normalize_update_audience,
    normalize_update_category,
    normalize_update_status,
)

_COMPANY_UPDATE_DETAIL_TAB_KEY = "ips_company_update_detail_tab"
_DETAIL_TABS = (
    "Overview",
    "Audience",
    "Attachments",
    "Event Details",
    "Read Status",
    "Notes",
    "Activity",
)


def _category_pill_html(category: str) -> str:
    cls_map = {
        "Announcement": "ips-update-category-announcement",
        "Safety Alert": "ips-update-category-safety-alert",
        "Event": "ips-update-category-event",
        "HR Update": "ips-update-category-hr-update",
        "Project Update": "ips-update-category-project-update",
        "General": "ips-update-category-general",
    }
    cls = cls_map.get(category, "ips-update-category-general")
    return f'<span class="ips-update-pill {cls}">{html.escape(category)}</span>'


def _status_pill_html(status: str) -> str:
    cls_map = {
        "Published": "ips-update-status-published",
        "Draft": "ips-update-status-draft",
        "Scheduled": "ips-update-status-scheduled",
        "Archived": "ips-update-status-archived",
    }
    cls = cls_map.get(status, "ips-update-status-published")
    return f'<span class="ips-update-pill {cls}">{html.escape(status)}</span>'


def _safe_attachment_href(url: str) -> str | None:
    text = str(url or "").strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        return None
    return text


@st.dialog("Banner image", width="large")
def _show_banner_preview_dialog(url: str, caption: str = "") -> None:
    st.image(url, use_container_width=True)
    if caption:
        st.caption(caption)


def _render_banner_preview(update: dict[str, Any]) -> None:
    url = get_company_update_banner_preview(update)
    if not url:
        return
    caption = str(update.get("banner_caption") or "").strip()
    alt = html.escape(caption or str(update.get("title") or "Update banner"))
    st.markdown(
        f'<figure class="ips-cu-banner-figure">'
        f'<img class="ips-cu-banner-detail" src="{html.escape(url)}" alt="{alt}" loading="lazy" />'
        f"</figure>",
        unsafe_allow_html=True,
    )
    if st.button("View full size", key=f"cu_banner_full_{update.get('id')}"):
        _show_banner_preview_dialog(url, caption)


def render_company_update_detail_tabs(
    update: dict[str, Any],
    *,
    permissions: CompanyUpdatesPermissions,
    default_tab: str = "Overview",
) -> None:
    category = normalize_update_category(update.get("category"))
    status = normalize_update_status(update.get("status"), is_active=update.get("is_active"))
    audience = normalize_update_audience(update.get("audience") or update.get("visibility"))
    is_pinned = bool(update.get("pinned") or update.get("is_pinned"))

    if default_tab in _DETAIL_TABS and st.session_state.get(_COMPANY_UPDATE_DETAIL_TAB_KEY) != default_tab:
        st.session_state.setdefault(_COMPANY_UPDATE_DETAIL_TAB_KEY, default_tab)

    active_tab = render_tabs(
        list(_DETAIL_TABS),
        session_key=_COMPANY_UPDATE_DETAIL_TAB_KEY,
        default=default_tab if default_tab in _DETAIL_TABS else "Overview",
    )

    if active_tab == "Overview":
        _render_banner_preview(update)
        body = str(update.get("body") or "").strip() or "No message body."
        body_html = (
            '<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(body)}"
            "</p>"
        )
        overview_html = (
            '<div class="ips-detail-grid">'
            f"{detail_field_html('Title', update.get('title'))}"
            f'{detail_field_html("Category", category, html_value=_category_pill_html(category))}'
            f'{detail_field_html("Status", status, html_value=_status_pill_html(status))}'
            f"{detail_field_html('Created By', update.get('created_by_display'))}"
            f"{detail_field_html('Created', update.get('created_display'))}"
            f"{detail_field_html('Priority', priority_for_form(update.get('priority')))}"
            f"{detail_field_html('Pinned', 'Yes' if is_pinned else 'No')}"
            "</div>"
        )
        st.markdown(dialog_card_html("Overview", overview_html), unsafe_allow_html=True)
        st.markdown(dialog_card_html("Content", body_html), unsafe_allow_html=True)

    elif active_tab == "Audience":
        audience_html = (
            '<div class="ips-detail-grid">'
            f"{detail_field_html('Audience', audience)}"
            f"{detail_field_html('Departments / Roles', update.get('departments') or '—')}"
            "</div>"
        )
        st.markdown(dialog_card_html("Audience", audience_html), unsafe_allow_html=True)

    elif active_tab == "Attachments":
        attachment_url = _safe_attachment_href(str(update.get("attachment_url") or ""))
        attachment_name = str(update.get("attachment_file_name") or "").strip()
        if attachment_url:
            label = attachment_name or "Download attachment"
            st.markdown(
                dialog_card_html(
                    "Attachments",
                    f'<a href="{html.escape(attachment_url)}" target="_blank" rel="noopener noreferrer">'
                    f"{html.escape(label)}</a>",
                ),
                unsafe_allow_html=True,
            )
        else:
            placeholder_html("No attachments for this update.")

    elif active_tab == "Event Details":
        if category == "Event" or update.get("event_date") or update.get("event_at"):
            event_html = (
                '<div class="ips-detail-grid">'
                f"{detail_field_html('Event Date', update.get('event_date_display'))}"
                f"{detail_field_html('Location', update.get('event_location') or update.get('location') or '—')}"
                "</div>"
            )
            st.markdown(dialog_card_html("Event Details", event_html), unsafe_allow_html=True)
        else:
            st.caption("No event details for this update.")

    elif active_tab == "Read Status":
        read_flag = "Unread" if update.get("is_new") else "Read"
        st.markdown(
            dialog_card_html(
                "Read Status",
                f'<div class="ips-detail-grid">{detail_field_html("Your Status", read_flag)}</div>',
            ),
            unsafe_allow_html=True,
        )
        if permissions.can_view_read_receipts:
            placeholder_html("Read receipts and viewer history will appear here when connected to Supabase.")
        else:
            st.caption("Your read status is shown above.")

    elif active_tab == "Notes":
        notes = str(update.get("notes") or "").strip()
        if notes:
            st.markdown(
                dialog_card_html(
                    "Notes",
                    f'<p style="margin:0;white-space:pre-wrap;">{html.escape(notes)}</p>',
                ),
                unsafe_allow_html=True,
            )
        else:
            placeholder_html("Notes will appear here when added.")

    elif active_tab == "Activity":
        placeholder_html("Created and updated activity will appear here when connected to Supabase.")
