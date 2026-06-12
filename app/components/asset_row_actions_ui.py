"""Per-row action menu for asset tables."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st

try:
    from app.components.asset_actions import open_asset_action_confirm
    from app.pages._core._crud import is_demo_id
    from app.services.asset_classification_service import tracking_type_label
    from app.services.asset_kits_service import get_tool_trailers
    from app.services.serialized_tool_service import assign_tool_to_trailer, is_serialized_tool_asset
except ImportError:
    from components.asset_actions import open_asset_action_confirm  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.asset_classification_service import tracking_type_label  # type: ignore
    from services.asset_kits_service import get_tool_trailers  # type: ignore
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
    """Popover menu: View, Edit, Change Type, Move to Trailer, History, Delete."""
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return

    st.markdown(
        '<span class="asset-row-actions-menu" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(
        "Actions",
        help="Row actions",
        type="secondary",
        key=f"{key_prefix}_menu_{aid}",
    ):
        st.markdown(
            '<span class="asset-row-actions-panel" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if on_view and st.button("View", key=f"{key_prefix}_view_{aid}", use_container_width=True):
            on_view(asset)
            st.rerun()

        if on_edit and st.button("Edit", key=f"{key_prefix}_edit_{aid}", use_container_width=True):
            on_edit(asset)
            st.rerun()

        if on_change_type and st.button("Change Type", key=f"{key_prefix}_ctype_{aid}", use_container_width=True):
            on_change_type(asset)
            st.rerun()

        st.markdown("**Move to Trailer**")
        labels, mapping = _trailer_labels()
        pick = st.selectbox(
            "Trailer",
            labels,
            key=f"{key_prefix}_trailer_sel_{aid}",
            label_visibility="collapsed",
        )
        if st.button("Assign trailer", key=f"{key_prefix}_trailer_go_{aid}", use_container_width=True):
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
                st.info("Move to Trailer works for Serialized Tools. Use Change Type or Equipment kit contents for other items.")

        if on_history and st.button("History", key=f"{key_prefix}_hist_{aid}", use_container_width=True):
            on_history(asset)
            st.rerun()

        if not is_demo_id(aid) and st.button("Delete", key=f"{key_prefix}_del_{aid}", use_container_width=True):
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
