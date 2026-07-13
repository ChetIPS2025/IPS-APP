"""Reusable record detail modal shell (Jobs-style) for list pages."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.components.clickable_table import clear_modal_selection_state
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
    """Clear modal selection and edit mode without rerun (for dialog ``on_dismiss``)."""
    clear_edit_modes(module)
    clear_modal_selection_state(
        module,
        table_key=table_key,
        session_select_key=session_select_key,
        modal_key=modal_key,
    )


def modal_dismiss_handler(
    *,
    module: str,
    table_key: str,
    session_select_key: str,
    modal_key: str,
) -> Callable[[], None]:
    """Return an ``on_dismiss`` callback that clears modal/table state."""

    def _dismiss() -> None:
        clear_record_modal(
            table_key=table_key,
            session_select_key=session_select_key,
            modal_key=modal_key,
            module=module,
        )

    return _dismiss


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
        "available": "active",
        "assigned": "active",
        "checked out": "pending",
        "in shop": "pending",
        "maintenance": "pending",
        "retired": "draft",
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


def compact_meta_card_html(label: str, value: object) -> str:
    return (
        f'<div class="ips-compact-meta-card">'
        f'<div class="ips-compact-meta-label">{html.escape(label)}</div>'
        f'<div class="ips-compact-meta-value">{html.escape(safe_value(value))}</div>'
        f"</div>"
    )


def render_compact_modal_meta_grid(cards: list[tuple[str, object]]) -> None:
    body = "".join(compact_meta_card_html(label, value) for label, value in cards)
    st.markdown(f'<div class="ips-compact-meta-grid">{body}</div>', unsafe_allow_html=True)


def render_compact_modal_header(
    *,
    title: str,
    subtitle: str = "",
    status: object | None = None,
    module: str,
    record_key: str,
    on_edit: Callable[[], None] | None = None,
    key_prefix: str | None = None,
    extra_actions: Callable[[list[Any]], None] | None = None,
    extra_action_slots: int = 3,
) -> None:
    """Compact view-mode header: title/subtitle left, status pill + Edit right."""
    if is_edit_mode(module, record_key):
        return

    subtitle_html = (
        f'<div class="ips-compact-detail-subtitle">{html.escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    status_html = status_pill_html(status) if status not in (None, "") else ""
    status_in_title = bool(extra_actions and status_html)
    title_status_html = (
        f'<div class="ips-compact-detail-title-row">'
        f'<h2 class="ips-compact-detail-title">{html.escape(title)}</h2>'
        f'<div class="ips-compact-detail-status">{status_html}</div>'
        f"</div>"
        if status_in_title
        else f'<h2 class="ips-compact-detail-title">{html.escape(title)}</h2>'
    )

    st.markdown('<div class="ips-compact-detail-header">', unsafe_allow_html=True)
    title_ratio = 3.4 if extra_actions else 5.4
    actions_ratio = 4.6 if extra_actions else 2.1
    title_col, actions_col = st.columns([title_ratio, actions_ratio], gap="small", vertical_alignment="center")
    with title_col:
        st.markdown(
            f'<div class="ips-compact-detail-main">'
            f"<div>"
            f"{title_status_html}"
            f"{subtitle_html}"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with actions_col:
        prefix = key_prefix or f"{module}_modal_{record_key}"

        def _edit() -> None:
            if on_edit:
                on_edit()
            else:
                set_edit_mode(module, record_key)

        if extra_actions:
            st.markdown(
                '<span class="ips-compact-detail-actions-row-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            slot_count = max(1, min(int(extra_action_slots or 1), 4))
            action_ratios = [0.72] + [1.0] * slot_count
            action_cols = st.columns(action_ratios, gap="small", vertical_alignment="center")
            edit_col, *action_slot_cols = action_cols
            with edit_col:
                st.button("Edit", key=f"{prefix}_edit", type="primary", on_click=_edit)
            extra_actions(action_slot_cols)
        else:
            pill_col, edit_col = st.columns([1.15, 1], gap="small", vertical_alignment="center")
            with pill_col:
                if status_html:
                    st.markdown(
                        f'<div class="ips-compact-detail-actions">{status_html}</div>',
                        unsafe_allow_html=True,
                    )
            with edit_col:
                st.button("Edit", key=f"{prefix}_edit", type="primary", on_click=_edit)
    st.markdown("</div>", unsafe_allow_html=True)


def render_modal_shell(*, wide: bool = True, compact: bool = False) -> None:
    cls = "ips-dialog-shell ips-modal-wide" if wide else "ips-dialog-shell"
    if compact:
        cls += " ips-compact-detail-modal"
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


def render_modal_edit_button(
    *,
    module: str,
    record_key: str,
    on_edit: Callable[[], None] | None = None,
    key_prefix: str | None = None,
) -> None:
    """Show a single compact Edit button in view mode (dialog X handles close)."""
    if is_edit_mode(module, record_key):
        return

    prefix = key_prefix or f"{module}_modal_{record_key}"
    st.markdown('<span class="ips-dialog-actions" aria-hidden="true"></span>', unsafe_allow_html=True)

    def _edit() -> None:
        if on_edit:
            on_edit()
        else:
            set_edit_mode(module, record_key)

    _action_left, action_right = st.columns([8, 1], gap="small")
    with action_right:
        st.button("Edit", key=f"{prefix}_edit", type="primary", on_click=_edit)


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
    save_label: str = "Save Changes",
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
        saved = st.button(save_label, key=save_key, type="primary")
    return cancelled, saved


def render_missing_record(on_close: Callable[[], None] | None = None, *, close_key: str = "modal_missing_close") -> None:
    st.warning("That record could not be loaded.")
    _ = on_close, close_key
