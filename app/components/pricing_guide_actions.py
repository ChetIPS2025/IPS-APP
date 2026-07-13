"""Pricing Guide detail modal — deactivate and delete action buttons."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.components.action_styles import danger_solid_button, warning_solid_button
from app.pages._core._crud import is_demo_id
from app.services.pricing_guide_service import clear_pricing_guide_cache, delete_pricing_item
from app.services.repository import update_row
def _confirm_state_key(item_id: str, action: str) -> str:
    return f"confirm_{action}_pricing_guide_{item_id}"


def _is_inactive(row: dict[str, Any]) -> bool:
    return row.get("is_active") is False


def _render_confirm_card(
    *,
    item_id: str,
    action: str,
    title: str,
    message: str,
    confirm_label: str,
    confirm_fn: Callable[[], bool],
) -> None:
    confirm_key = _confirm_state_key(item_id, action)
    st.markdown(
        f'<div class="ips-confirm-card">'
        f'<div class="ips-confirm-title">{html.escape(title)}</div>'
        f'<div class="ips-confirm-text">{html.escape(message)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"pg_act_dismiss_{action}_{item_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        clicked = False
        if action == "deactivate":
            clicked = warning_solid_button(confirm_label, f"confirm_{action}_{item_id}", use_container_width=True)
        else:
            clicked = danger_solid_button(confirm_label, f"confirm_{action}_{item_id}", use_container_width=True)
        if clicked and confirm_fn():
            st.session_state.pop(confirm_key, None)
            st.rerun()


def render_pricing_guide_action_buttons(
    row: dict[str, Any],
    *,
    can_manage: bool,
    on_deactivate: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> None:
    """Render compact Pricing Guide Actions row with inline confirmation panels."""
    rid = str(row.get("id") or "").strip()
    if not rid or is_demo_id(rid):
        return

    if not can_manage:
        st.caption("Only admin, manager, or supervisor can change pricing guide items.")
        return

    item_key = "".join(ch if ch.isalnum() else "_" for ch in rid) or "pg"
    show_deactivate = not _is_inactive(row)

    for action in ("deactivate", "delete"):
        if st.session_state.get(_confirm_state_key(rid, action)):
            if action == "deactivate":
                _render_confirm_card(
                    item_id=rid,
                    action=action,
                    title="Deactivate Item",
                    message="Are you sure you want to deactivate this pricing guide item?",
                    confirm_label="Confirm Deactivate",
                    confirm_fn=lambda: _handle_deactivate(rid, on_deactivate),
                )
            else:
                _render_confirm_card(
                    item_id=rid,
                    action=action,
                    title="Delete Item",
                    message="Delete this pricing guide item permanently? This cannot be undone.",
                    confirm_label="Confirm Delete",
                    confirm_fn=lambda: _handle_delete(rid, on_delete),
                )
            return

    action_specs: list[tuple[str, Any, str, str]] = []
    if show_deactivate:
        action_specs.append(("deactivate", warning_solid_button, "Deactivate Item", f"open_deactivate_{item_key}"))
    action_specs.append(("delete", danger_solid_button, "Delete Item", f"open_delete_{item_key}"))

    with st.container(key=f"pricing_guide_actions_{item_key}"):
        st.markdown('<span class="ips-inventory-actions-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-inventory-actions-title">Pricing Guide Actions</p>', unsafe_allow_html=True)
        cols = st.columns(len(action_specs), gap="small")
        for col, (action, btn_fn, label, suffix) in zip(cols, action_specs):
            with col:
                if btn_fn(label, suffix, use_container_width=False):
                    st.session_state[_confirm_state_key(rid, action)] = True
                    st.rerun()


def _handle_deactivate(item_id: str, on_deactivate: Callable[[], None] | None) -> bool:
    result = update_row("pricing_guide_items", {"is_active": False}, {"id": item_id})
    if result.ok:
        clear_pricing_guide_cache()
        st.success("Pricing item deactivated.")
        if on_deactivate:
            on_deactivate()
        return True
    st.error(result.error or "Could not deactivate pricing item.")
    return False


def _handle_delete(item_id: str, on_delete: Callable[[], None] | None) -> bool:
    ok, msg = delete_pricing_item(item_id)
    if ok:
        st.success(msg or "Pricing item deleted.")
        if on_delete:
            on_delete()
        return True
    st.error(msg or "Could not delete pricing item.")
    return False
