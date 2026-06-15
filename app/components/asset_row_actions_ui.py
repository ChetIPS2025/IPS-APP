"""Per-row action menu for asset tables — matches Jobs Actions popover layout."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st

try:
    from app.components.asset_actions import open_asset_action_confirm
    from app.pages._core._crud import is_demo_id
    from app.services.asset_classification_service import tracking_type_label
    from app.services.asset_kits_service import get_tool_trailers
    from app.services.assets_service import can_manage_asset_actions
    from app.services.serialized_tool_service import assign_tool_to_trailer, is_serialized_tool_asset
except ImportError:
    from components.asset_actions import open_asset_action_confirm  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.asset_classification_service import tracking_type_label  # type: ignore
    from services.asset_kits_service import get_tool_trailers  # type: ignore
    from services.assets_service import can_manage_asset_actions  # type: ignore
    from services.serialized_tool_service import assign_tool_to_trailer, is_serialized_tool_asset  # type: ignore

ASSET_OPEN_ACTIVITY_KEY = "ast_open_activity_id"


def _trailer_labels() -> tuple[list[str], dict[str, str]]:
    labels = ["— Select trailer —"]
    mapping: dict[str, str] = {"— Select trailer —": ""}
    for trailer in get_tool_trailers():
        number = str(trailer.get("asset_number") or "").strip()
        name = str(trailer.get("asset_name") or trailer.get("name") or "Trailer").strip()
        label = f"{number} · {name}" if number else name
        labels.append(label)
        mapping[label] = str(trailer.get("id") or "")
    return labels, mapping


def _actions_divider() -> None:
    st.markdown('<hr class="asset-row-actions-divider" aria-hidden="true">', unsafe_allow_html=True)


def _action_button(
    *,
    marker: str,
    label: str,
    key: str,
    tone: str = "default",
) -> bool:
    st.markdown(
        f'<span class="asset-row-action-marker asset-row-action-{marker} '
        f'asset-row-action-tone-{tone}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    return st.button(label, key=key, use_container_width=True)


def render_asset_row_actions(
    asset: dict[str, Any],
    *,
    key_prefix: str = "ast_row",
    on_view: Callable[[dict[str, Any]], None] | None = None,
    on_edit: Callable[[dict[str, Any]], None] | None = None,
    on_change_type: Callable[[dict[str, Any]], None] | None = None,
    on_history: Callable[[dict[str, Any]], None] | None = None,
    on_after_change: Callable[[], None] | None = None,
) -> None:
    """Popover: view, edit, assign trailer, change type, history, and delete."""
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return

    asset_key = "".join(ch if ch.isalnum() else "_" for ch in aid) or "asset"
    can_manage = can_manage_asset_actions()
    show_manage = can_manage and (on_change_type is not None or not is_demo_id(aid))

    st.markdown(
        '<span class="asset-row-actions-menu asset-actions-button" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(
        "Actions",
        help="Row actions",
        type="primary",
        key=f"{key_prefix}_menu_{aid}",
    ):
        st.markdown(
            '<span class="asset-row-actions-panel" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        if on_view and _action_button(
            marker="view",
            label="View Asset Details",
            key=f"{key_prefix}_view_{asset_key}",
        ):
            on_view(asset)
            st.rerun()

        if on_edit and can_manage and _action_button(
            marker="edit",
            label="Edit Asset",
            key=f"{key_prefix}_edit_{asset_key}",
        ):
            on_edit(asset)
            st.rerun()

        if show_manage:
            _actions_divider()

            if on_change_type and _action_button(
                marker="change-type",
                label="Change Type",
                key=f"{key_prefix}_ctype_{asset_key}",
            ):
                on_change_type(asset)
                st.rerun()

            st.markdown(
                '<div class="asset-row-actions-section">'
                '<span class="asset-row-action-marker asset-row-action-assign-section" aria-hidden="true"></span>'
                '<p class="asset-row-actions-section-title">Assign Asset</p>'
                "</div>",
                unsafe_allow_html=True,
            )
            labels, mapping = _trailer_labels()
            st.markdown(
                '<span class="asset-row-actions-trailer-select" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            pick = st.selectbox(
                "Select trailer",
                labels,
                key=f"{key_prefix}_trailer_sel_{asset_key}",
                label_visibility="visible",
            )
            if _action_button(
                marker="assign",
                label="Assign Asset",
                key=f"{key_prefix}_trailer_go_{asset_key}",
            ):
                trailer_id = mapping.get(pick, "")
                if not trailer_id:
                    st.error("Select a Tool Trailer.")
                elif is_serialized_tool_asset(asset):
                    result = assign_tool_to_trailer(aid, trailer_id)
                    if result.ok:
                        if on_after_change:
                            on_after_change()
                        st.success("Tool assigned to trailer.")
                        st.rerun()
                    else:
                        st.error(result.error or "Could not assign trailer.")
                else:
                    st.info(
                        "Move to Trailer works for Serialized Tools. "
                        "Use Change Type or Equipment kit contents for other items."
                    )

        if on_history and _action_button(
            marker="history",
            label="Activity History",
            key=f"{key_prefix}_hist_{asset_key}",
        ):
            on_history(asset)
            st.rerun()

        if can_manage and not is_demo_id(aid):
            _actions_divider()
            if _action_button(
                marker="delete",
                label="Delete Asset",
                key=f"{key_prefix}_del_{asset_key}",
                tone="danger",
            ):
                open_asset_action_confirm(aid, "delete")
                if on_view:
                    on_view(asset)
                st.rerun()


def render_asset_activity_snippet(asset: dict[str, Any]) -> None:
    """Compact activity lines for History row action or Activity tab."""
    lines: list[str] = []
    tab = tracking_type_label(asset)
    lines.append(f"Assets tab: {tab}")
    for label, key in (
        ("Last checkout", "last_checkout_at"),
        ("Last check-in", "last_checkin_at"),
        ("Last seen", "last_seen_at"),
        ("Last audit", "last_audited_at"),
        ("Acquired", "acquired_date"),
    ):
        val = str(asset.get(key) or "").strip()
        if val and val not in {"—", "None"}:
            lines.append(f"{label}: {val[:19]}")
    status = str(asset.get("status") or "").strip()
    if status:
        lines.append(f"Status: {status}")
    if not lines:
        st.caption("No activity recorded yet.")
        return
    for line in lines:
        st.markdown(f"- {line}")


__all__ = [
    "ASSET_OPEN_ACTIVITY_KEY",
    "render_asset_activity_snippet",
    "render_asset_row_actions",
]
