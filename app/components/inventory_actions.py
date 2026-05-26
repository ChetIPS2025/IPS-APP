"""Inventory detail modal — deactivate and delete action buttons."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.action_styles import danger_solid_button, warning_solid_button
    from app.pages._core._crud import is_demo_id
    from app.services.inventory_service import (
        can_manage_inventory_actions,
        clear_inventory_cache,
        deactivate_inventory_item,
        delete_inventory_item,
        remove_inventory_keep_pricing_item,
    )
except ImportError:
    from components.action_styles import danger_solid_button, warning_solid_button  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.inventory_service import (  # type: ignore
        can_manage_inventory_actions,
        clear_inventory_cache,
        deactivate_inventory_item,
        delete_inventory_item,
        remove_inventory_keep_pricing_item,
    )


def _confirm_state_key(item_id: str, action: str) -> str:
    return f"confirm_{action}_inventory_{item_id}"


def _normalize_status(item: dict) -> str:
    return str(item.get("status") or "Active").strip() or "Active"


def _is_discontinued(item: dict) -> bool:
    return _normalize_status(item).lower() in {"discontinued", "inactive", "deleted", "archived"}


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
        if st.button("Cancel", key=f"inv_act_dismiss_{action}_{item_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        clicked = False
        if action in {"deactivate", "remove_keep_pricing"}:
            clicked = warning_solid_button(confirm_label, f"confirm_{action}_{item_id}", use_container_width=True)
        else:
            clicked = danger_solid_button(confirm_label, f"confirm_{action}_{item_id}", use_container_width=True)
        if clicked and confirm_fn():
            st.session_state.pop(confirm_key, None)
            st.rerun()


def render_inventory_action_buttons(
    item: dict,
    *,
    on_deactivate: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
    on_remove_keep_pricing: Callable[[], None] | None = None,
) -> None:
    """Render compact Inventory Actions row with inline confirmation panels."""
    iid = str(item.get("id") or "").strip()
    if not iid or is_demo_id(iid):
        return

    if not can_manage_inventory_actions():
        st.caption("Only admin, manager, or supervisor can change inventory items.")
        return

    item_key = "".join(ch if ch.isalnum() else "_" for ch in iid) or "inv"
    show_deactivate = not _is_discontinued(item)

    for action in ("deactivate", "remove_keep_pricing", "delete"):
        if st.session_state.get(_confirm_state_key(iid, action)):
            if action == "deactivate":
                _render_confirm_card(
                    item_id=iid,
                    action=action,
                    title="Deactivate Item",
                    message="Are you sure you want to deactivate this inventory item?",
                    confirm_label="Confirm Deactivate",
                    confirm_fn=lambda: _handle_deactivate(iid, on_deactivate),
                )
            elif action == "remove_keep_pricing":
                _render_confirm_card(
                    item_id=iid,
                    action=action,
                    title="Remove from Inventory",
                    message=(
                        "Remove this stock record from Inventory and keep the linked Pricing Guide "
                        "item as Non-Inventory for estimates. This cannot be undone."
                    ),
                    confirm_label="Confirm Remove",
                    confirm_fn=lambda: _handle_remove_keep_pricing(iid, on_remove_keep_pricing),
                )
            else:
                _render_confirm_card(
                    item_id=iid,
                    action=action,
                    title="Delete Item",
                    message="Are you sure you want to delete this inventory item? This cannot be undone.",
                    confirm_label="Confirm Delete",
                    confirm_fn=lambda: _handle_delete(iid, on_delete),
                )
            return

    action_specs: list[tuple[str, Any, str, str]] = []
    if show_deactivate:
        action_specs.append(("deactivate", warning_solid_button, "Deactivate Item", f"open_deactivate_{item_key}"))
    action_specs.append(
        (
            "remove_keep_pricing",
            warning_solid_button,
            "Remove from Inventory",
            f"open_remove_keep_pricing_{item_key}",
        )
    )
    action_specs.append(("delete", danger_solid_button, "Delete Item", f"open_delete_{item_key}"))

    with st.container(key=f"inventory_actions_{item_key}"):
        st.markdown('<span class="ips-inventory-actions-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-inventory-actions-title">Inventory Actions</p>', unsafe_allow_html=True)
        cols = st.columns(len(action_specs), gap="small")
        for col, (action, btn_fn, label, suffix) in zip(cols, action_specs):
            with col:
                if btn_fn(label, suffix, use_container_width=False):
                    st.session_state[_confirm_state_key(iid, action)] = True
                    st.rerun()


def _handle_deactivate(item_id: str, on_deactivate: Callable[[], None] | None) -> bool:
    result = deactivate_inventory_item(item_id)
    if result.ok:
        st.success("Inventory item deactivated.")
        if on_deactivate:
            on_deactivate()
        return True
    st.error(result.error or "Could not deactivate item.")
    return False


def _handle_remove_keep_pricing(
    item_id: str,
    on_remove_keep_pricing: Callable[[], None] | None,
) -> bool:
    result = remove_inventory_keep_pricing_item(item_id)
    if result.ok:
        message = "Removed from inventory."
        if isinstance(result.data, dict):
            message = str(result.data.get("message") or message)
        st.success(message)
        if on_remove_keep_pricing:
            on_remove_keep_pricing()
        return True
    st.error(result.error or "Could not remove inventory item.")
    return False


def _handle_delete(item_id: str, on_delete: Callable[[], None] | None) -> bool:
    result = delete_inventory_item(item_id)
    if result.ok:
        clear_inventory_cache()
        st.success("Inventory item deleted.")
        if on_delete:
            on_delete()
        return True
    st.error(result.error or "Could not delete item.")
    return False
