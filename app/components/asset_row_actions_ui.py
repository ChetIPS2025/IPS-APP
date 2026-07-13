"""Per-row action menu for asset tables — matches Jobs Actions popover layout."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from app.components.asset_actions import open_asset_action_confirm
from app.components.rental_equipment_inspection_launcher import open_rental_inspection
from app.pages._core._crud import is_demo_id
from app.services.asset_classification_service import tracking_type_label
from app.services.asset_kits_service import get_tool_trailers
from app.services.assets_service import can_manage_asset_actions
from app.services.rental_equipment_inspection_service import create_auto_inspection, is_rental_equipment
from app.services.serialized_tool_service import assign_tool_to_trailer, is_serialized_tool_asset
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


def _start_rental_inspection(asset: dict[str, Any], inspection_type: str) -> None:
    aid = str(asset.get("id") or "").strip()
    job_id = str(asset.get("assigned_job_id") or "").strip() or None
    result = create_auto_inspection(asset_id=aid, inspection_type=inspection_type, job_id=job_id)
    if result.ok:
        open_rental_inspection(
            inspection_id=str((result.data or {}).get("id") or ""),
            asset_id=aid,
            job_id=job_id,
            inspection_type=inspection_type,
        )
    else:
        st.error(result.error or f"Could not start {inspection_type} inspection.")


def render_asset_row_actions(
    asset: dict[str, Any],
    *,
    key_prefix: str = "ast_row",
    on_view: Callable[[dict[str, Any]], None] | None = None,
    on_edit: Callable[[dict[str, Any]], None] | None = None,
    on_open_tab: Callable[[dict[str, Any], str], None] | None = None,
    on_after_change: Callable[[], None] | None = None,
) -> None:
    """Popover: view, edit, assign, rental checkout, QR, history, and delete."""
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return

    asset_key = "".join(ch if ch.isalnum() else "_" for ch in aid) or "asset"
    can_manage = can_manage_asset_actions()
    rental_asset = is_rental_equipment(asset)

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
            label="View Asset",
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

        if can_manage and not is_demo_id(aid):
            _actions_divider()
            labels, mapping = _trailer_labels()
            st.markdown(
                '<span class="asset-row-actions-trailer-select" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            pick = st.selectbox(
                "Trailer",
                labels,
                key=f"{key_prefix}_trailer_sel_{asset_key}",
                label_visibility="collapsed",
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
                        "Trailer assignment works for Serialized Tools. "
                        "Use the asset detail Assignments tab for other equipment."
                    )

        if rental_asset and can_manage:
            _actions_divider()
            if _action_button(
                marker="checkout",
                label="Check Out",
                key=f"{key_prefix}_checkout_{asset_key}",
            ):
                _start_rental_inspection(asset, "checkout")
            if _action_button(
                marker="checkin",
                label="Check In",
                key=f"{key_prefix}_checkin_{asset_key}",
            ):
                _start_rental_inspection(asset, "return")

        if on_open_tab:
            _actions_divider()
            if _action_button(
                marker="print-qr",
                label="Print QR Label",
                key=f"{key_prefix}_qr_{asset_key}",
            ):
                on_open_tab(asset, "Overview")
                st.rerun()
            if _action_button(
                marker="inspection-history",
                label="Inspection History",
                key=f"{key_prefix}_insp_hist_{asset_key}",
            ):
                on_open_tab(asset, "Maintenance")
                st.rerun()
            if _action_button(
                marker="maintenance-history",
                label="Maintenance History",
                key=f"{key_prefix}_maint_hist_{asset_key}",
            ):
                on_open_tab(asset, "Maintenance")
                st.rerun()

        if can_manage and not is_demo_id(aid):
            _actions_divider()
            if _action_button(
                marker="delete",
                label="Delete",
                key=f"{key_prefix}_del_{asset_key}",
                tone="danger",
            ):
                open_asset_action_confirm(aid, "delete")
                if on_view:
                    on_view(asset)
                st.rerun()


def render_asset_activity_snippet(asset: dict[str, Any]) -> None:
    """Compact activity lines for History row action or Activity tab."""
    if not isinstance(asset, dict):
        st.info("No asset activity available.")
        return
    if not str(asset.get("id") or "").strip():
        st.info("No asset activity available.")
        return
    try:
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
    except Exception:
        lines = []
    if not lines:
        st.info("No recent activity for this asset.")
        return
    st.markdown("### Recent Activity")
    for line in lines:
        st.markdown(f"- {line}")


__all__ = [
    "ASSET_OPEN_ACTIVITY_KEY",
    "render_asset_activity_snippet",
    "render_asset_row_actions",
]
