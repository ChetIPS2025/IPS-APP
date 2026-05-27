"""Asset detail modal — retire and delete action buttons."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.action_styles import danger_solid_button, warning_solid_button
    from app.pages._core._crud import is_demo_id
    from app.services.assets_service import (
        can_manage_asset_actions,
        clear_assets_cache,
        delete_asset_record,
        retire_asset,
    )
except ImportError:
    from components.action_styles import danger_solid_button, warning_solid_button  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.assets_service import (  # type: ignore
        can_manage_asset_actions,
        clear_assets_cache,
        delete_asset_record,
        retire_asset,
    )


def _confirm_state_key(asset_id: str, action: str) -> str:
    return f"confirm_{action}_asset_{asset_id}"


def _normalize_status(asset: dict) -> str:
    return str(asset.get("status") or "Active").strip() or "Active"


def _is_retired(asset: dict) -> bool:
    return _normalize_status(asset).lower() in {"retired", "inactive", "disposed", "scrapped", "deleted"}


def _asset_key(asset: dict) -> str:
    aid = str(asset.get("id") or "").strip()
    return "".join(ch if ch.isalnum() else "_" for ch in aid) or "asset"


def _render_confirm_card(
    *,
    asset_id: str,
    action: str,
    title: str,
    message: str,
    confirm_label: str,
    confirm_fn: Callable[[], bool],
) -> None:
    confirm_key = _confirm_state_key(asset_id, action)
    st.markdown(
        f'<div class="ips-confirm-card">'
        f'<div class="ips-confirm-title">{html.escape(title)}</div>'
        f'<div class="ips-confirm-text">{html.escape(message)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"asset_act_dismiss_{action}_{asset_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        clicked = False
        if action == "retire":
            clicked = warning_solid_button(confirm_label, f"confirm_{action}_{asset_id}", use_container_width=True)
        else:
            clicked = danger_solid_button(confirm_label, f"confirm_{action}_{asset_id}", use_container_width=True)
        if clicked and confirm_fn():
            st.session_state.pop(confirm_key, None)
            st.rerun()


def is_asset_action_confirm_open(asset: dict) -> bool:
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return False
    return any(st.session_state.get(_confirm_state_key(aid, action)) for action in ("retire", "delete"))


def render_asset_action_confirm_panel(
    asset: dict,
    *,
    on_retire: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> bool:
    """Render inline confirmation when retire/delete is pending. Returns True if shown."""
    aid = str(asset.get("id") or "").strip()
    if not aid or is_demo_id(aid):
        return False

    for action in ("retire", "delete"):
        if st.session_state.get(_confirm_state_key(aid, action)):
            if action == "retire":
                _render_confirm_card(
                    asset_id=aid,
                    action=action,
                    title="Retire Asset",
                    message="Are you sure you want to retire this asset? It will be marked as Retired.",
                    confirm_label="Confirm Retire",
                    confirm_fn=lambda: _handle_retire(aid, on_retire),
                )
            else:
                _render_confirm_card(
                    asset_id=aid,
                    action=action,
                    title="Delete Asset",
                    message=(
                        "Delete this asset permanently? Related documents, photos, maintenance, "
                        "and inspection records will also be removed."
                    ),
                    confirm_label="Confirm Delete",
                    confirm_fn=lambda: _handle_delete(aid, on_delete),
                )
            return True
    return False


def asset_retire_delete_action_specs(asset: dict) -> list[tuple[str, Any, str, str]]:
    """Return retire/delete button specs for the current asset state."""
    if not can_manage_asset_actions():
        return []

    asset_key = _asset_key(asset)
    action_specs: list[tuple[str, Any, str, str]] = []
    if not _is_retired(asset):
        action_specs.append(("retire", warning_solid_button, "Retire Asset", f"open_retire_{asset_key}"))
    action_specs.append(("delete", danger_solid_button, "Delete Asset", f"open_delete_{asset_key}"))
    return action_specs


def open_asset_action_confirm(asset_id: str, action: str) -> None:
    st.session_state[_confirm_state_key(asset_id, action)] = True
    st.rerun()


def render_asset_action_button_row(
    asset: dict,
    *,
    layout: str = "panel",
    on_retire: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> None:
    """Render retire/delete buttons (no confirmation panel)."""
    aid = str(asset.get("id") or "").strip()
    if not aid or is_demo_id(aid):
        return

    action_specs = asset_retire_delete_action_specs(asset)
    if not action_specs:
        if layout != "header":
            st.caption("Only admin, manager, or supervisor can change assets.")
        return

    asset_key = _asset_key(asset)
    marker_class = (
        "ips-asset-actions-header-marker"
        if layout == "header"
        else "ips-asset-actions-marker"
    )
    with st.container(key=f"asset_actions_{asset_key}"):
        st.markdown(f'<span class="{marker_class}"></span>', unsafe_allow_html=True)
        if layout != "header":
            st.markdown('<p class="ips-asset-actions-title">Asset Actions</p>', unsafe_allow_html=True)
        cols = st.columns(len(action_specs), gap="small")
        for col, (action, btn_fn, label, suffix) in zip(cols, action_specs):
            with col:
                if btn_fn(label, suffix, use_container_width=False):
                    st.session_state[_confirm_state_key(aid, action)] = True
                    st.rerun()


def render_asset_action_buttons(
    asset: dict,
    *,
    layout: str = "panel",
    on_retire: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> None:
    """Render compact Asset Actions row with inline confirmation panels."""
    if render_asset_action_confirm_panel(asset, on_retire=on_retire, on_delete=on_delete):
        return
    render_asset_action_button_row(
        asset,
        layout=layout,
        on_retire=on_retire,
        on_delete=on_delete,
    )


def _handle_retire(asset_id: str, on_retire: Callable[[], None] | None) -> bool:
    result = retire_asset(asset_id)
    if result.ok:
        st.success("Asset retired.")
        if on_retire:
            on_retire()
        return True
    st.error(result.error or "Could not retire asset.")
    return False


def _handle_delete(asset_id: str, on_delete: Callable[[], None] | None) -> bool:
    result = delete_asset_record(asset_id)
    if result.ok:
        clear_assets_cache()
        st.success("Asset deleted.")
        if on_delete:
            on_delete()
        return True
    st.error(result.error or "Could not delete asset.")
    return False
