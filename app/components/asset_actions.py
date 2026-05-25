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


def render_asset_action_buttons(
    asset: dict,
    *,
    on_retire: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> None:
    """Render compact Asset Actions row with inline confirmation panels."""
    aid = str(asset.get("id") or "").strip()
    if not aid or is_demo_id(aid):
        return

    if not can_manage_asset_actions():
        st.caption("Only admin, manager, or supervisor can change assets.")
        return

    asset_key = "".join(ch if ch.isalnum() else "_" for ch in aid) or "asset"
    show_retire = not _is_retired(asset)

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
            return

    action_specs: list[tuple[str, Any, str, str]] = []
    if show_retire:
        action_specs.append(("retire", warning_solid_button, "Retire Asset", f"open_retire_{asset_key}"))
    action_specs.append(("delete", danger_solid_button, "Delete Asset", f"open_delete_{asset_key}"))

    with st.container(key=f"asset_actions_{asset_key}"):
        st.markdown('<span class="ips-asset-actions-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-asset-actions-title">Asset Actions</p>', unsafe_allow_html=True)
        cols = st.columns(len(action_specs), gap="small")
        for col, (action, btn_fn, label, suffix) in zip(cols, action_specs):
            with col:
                if btn_fn(label, suffix, use_container_width=False):
                    st.session_state[_confirm_state_key(aid, action)] = True
                    st.rerun()


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
