"""Reusable record detail modal shell (Jobs-style) for list pages."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.clickable_table import close_modal_and_clear_selection
except ImportError:
    from components.clickable_table import close_modal_and_clear_selection  # type: ignore


def safe_value(value: object, fallback: str = "—") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def record_session_key(record: dict[str, Any], *fields: str) -> str:
    raw = ""
    for field in fields:
        raw = str(record.get(field) or "").strip()
        if raw:
            break
    if not raw:
        raw = str(record.get("id") or "record").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
    return safe or "record"


def edit_mode_key(module: str, record_key: str) -> str:
    return f"{module}_edit_mode_{record_key}"


def is_edit_mode(module: str, record_key: str) -> bool:
    return bool(st.session_state.get(edit_mode_key(module, record_key)))


def set_view_mode(module: str, record_key: str) -> None:
    st.session_state[edit_mode_key(module, record_key)] = False


def set_edit_mode(module: str, record_key: str) -> None:
    st.session_state[edit_mode_key(module, record_key)] = True


def clear_edit_modes(module: str) -> None:
    prefix = f"{module}_edit_mode_"
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(prefix):
            st.session_state.pop(key, None)


def build_modal_cache(
    records: list[dict[str, Any]],
    *,
    row_id_key: str = "id",
    cache_key: str,
) -> dict[str, dict[str, Any]]:
    cache = {
        str(rec.get(row_id_key) or "").strip(): rec
        for rec in records
        if str(rec.get(row_id_key) or "").strip()
    }
    st.session_state[cache_key] = cache
    return cache


def get_modal_record(
    *,
    cache_key: str,
    modal_key: str,
    session_select_key: str,
) -> dict[str, Any] | None:
    sel = str(st.session_state.get(modal_key) or st.session_state.get(session_select_key) or "").strip()
    cache = st.session_state.get(cache_key)
    if not sel or not isinstance(cache, dict):
        return None
    return cache.get(sel)


def open_record_modal(
    record_id: str,
    record: dict[str, Any] | None,
    *,
    session_select_key: str,
    modal_key: str,
    module: str,
    id_fields: tuple[str, ...] = ("id",),
) -> None:
    rid = str(record_id or "").strip()
    if not rid:
        return
    st.session_state[session_select_key] = rid
    st.session_state[modal_key] = rid
    if isinstance(record, dict):
        rk = record_session_key(record, *id_fields)
        st.session_state[edit_mode_key(module, rk)] = False


def clear_record_modal(
    *,
    table_key: str,
    session_select_key: str,
    modal_key: str,
    module: str,
) -> None:
    clear_edit_modes(module)
    close_modal_and_clear_selection(
        table_key=table_key,
        session_select_key=session_select_key,
        modal_key=modal_key,
    )


def show_modal_if_pending(modal_key: str, dialog_fn: Callable[[], None]) -> None:
    if str(st.session_state.get(modal_key) or "").strip():
        dialog_fn()


def status_class(status: object) -> str:
    raw = safe_value(status, "").lower()
    aliases = {
        "draft": "draft",
        "active": "active",
        "awarded": "awarded",
        "approved": "approved",
        "completed": "completed",
        "complete": "completed",
        "pending": "pending",
        "scheduled": "scheduled",
        "on hold": "pending",
        "cancelled": "danger",
        "canceled": "danger",
        "closed": "completed",
        "inactive": "draft",
    }
    slug = aliases.get(raw, "draft")
    return f"ips-pill ips-pill-{slug}"


def status_pill_html(status: object) -> str:
    label = safe_value(status)
    return f'<span class="{status_class(status)}">{html.escape(label)}</span>'


def detail_field_html(label: str, value: object, *, html_value: str | None = None) -> str:
    rendered = html_value if html_value is not None else html.escape(safe_value(value))
    return (
        f'<div class="ips-detail-field">'
        f'<span class="ips-detail-label">{html.escape(label)}</span>'
        f'<span class="ips-detail-value">{rendered}</span>'
        f"</div>"
    )


def dialog_card_html(title: str, body_html: str) -> str:
    return (
        f'<div class="ips-dialog-card">'
        f'<div class="ips-dialog-card-title">{html.escape(title)}</div>'
        f"{body_html}"
        f"</div>"
    )


def meta_card_html(label: str, value: object) -> str:
    return (
        f'<div class="ips-dialog-meta-card">'
        f'<div class="ips-dialog-meta-label">{html.escape(label)}</div>'
        f'<div class="ips-dialog-meta-value">{html.escape(safe_value(value))}</div>'
        f"</div>"
    )


def placeholder_html(message: str) -> None:
    st.markdown(
        f'<div class="ips-dialog-placeholder">{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )


def render_modal_shell(*, wide: bool = True) -> None:
    cls = "ips-dialog-shell ips-modal-wide" if wide else "ips-dialog-shell"
    st.markdown(f'<span class="{cls}" aria-hidden="true"></span>', unsafe_allow_html=True)


def render_modal_header(
    *,
    title: str,
    subtitle: str = "",
    status: object | None = None,
) -> None:
    status_block = status_pill_html(status) if status not in (None, "") else ""
    subtitle_html = (
        f'<p class="ips-dialog-subtitle">{html.escape(subtitle)}</p>' if subtitle else ""
    )
    status_col = f"<div>{status_block}</div>" if status_block else ""
    st.markdown(
        f'<div class="ips-dialog-header">'
        f'<div class="ips-dialog-title-row">'
        f"<div>"
        f'<h2 class="ips-dialog-title">{html.escape(title)}</h2>'
        f"{subtitle_html}"
        f"</div>"
        f"{status_col}"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_modal_actions(
    *,
    module: str,
    record_key: str,
    record: dict[str, Any],
    on_close: Callable[[], None],
    key_prefix: str | None = None,
) -> None:
    prefix = key_prefix or f"{module}_modal_{record_key}"
    st.markdown('<span class="ips-dialog-actions" aria-hidden="true"></span>', unsafe_allow_html=True)

    def _view() -> None:
        set_view_mode(module, record_key)

    def _edit() -> None:
        set_edit_mode(module, record_key)

    act1, act2, act3, act4 = st.columns([1, 1, 1, 1], gap="small")
    with act1:
        st.button("View", key=f"{prefix}_view", on_click=_view)
    with act2:
        st.button("Edit", key=f"{prefix}_edit", on_click=_edit)
    with act3:
        st.button("More", key=f"{prefix}_more")
    with act4:
        if st.button("Close", key=f"{prefix}_close"):
            on_close()
            st.rerun()


def render_modal_meta_grid(cards: list[tuple[str, object]]) -> None:
    body = "".join(meta_card_html(label, value) for label, value in cards)
    st.markdown(f'<div class="ips-dialog-meta-grid">{body}</div>', unsafe_allow_html=True)


def render_edit_form_header(title: str = "Edit Record") -> None:
    st.markdown(
        f'<div class="ips-edit-form-card"><div class="ips-form-section-title">{html.escape(title)}</div></div>',
        unsafe_allow_html=True,
    )


def render_save_cancel_actions(
    *,
    module: str,
    record_key: str,
    cancel_key: str,
    save_key: str,
    on_cancel: Callable[[], None] | None = None,
) -> tuple[bool, bool]:
    btn_cancel, btn_spacer, btn_save = st.columns([1, 4, 1], gap="small")
    cancelled = False
    saved = False
    with btn_cancel:
        if st.button("Cancel", key=cancel_key):
            if on_cancel:
                on_cancel()
            else:
                set_view_mode(module, record_key)
            cancelled = True
    with btn_save:
        saved = st.button("Save Changes", key=save_key, type="primary")
    return cancelled, saved


def render_missing_record(on_close: Callable[[], None], *, close_key: str = "modal_missing_close") -> None:
    st.warning("That record could not be loaded.")
    if st.button("Close", key=close_key):
        on_close()
        st.rerun()
