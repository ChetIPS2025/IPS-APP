"""Move assets between Equipment, Serialized Tools, and Small Tools tabs."""

from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from app.services.asset_classification_service import (
        TRACKING_TAB_LABELS,
        TRACKING_TYPES,
        reclassify_asset,
        reclassify_assets_bulk,
        resolve_tracking_type,
        tracking_type_label,
    )
    from app.services.asset_kits_service import asset_is_kit
    from app.services.small_hand_tool_service import STORAGE_TYPES
except ImportError:
    from services.asset_classification_service import (  # type: ignore
        TRACKING_TAB_LABELS,
        TRACKING_TYPES,
        reclassify_asset,
        reclassify_assets_bulk,
        resolve_tracking_type,
        tracking_type_label,
    )
    from services.asset_kits_service import asset_is_kit  # type: ignore
    from services.small_hand_tool_service import STORAGE_TYPES  # type: ignore

_BULK_MOVE_TARGET_KEY = "ast_bulk_move_target"
_BULK_MOVE_CONFIRM_KEY = "ast_bulk_move_confirm"

_BUCKET_HELP = (
    "**Equipment** — large rentable assets (trailers, generators, pressure washers). "
    "**Serialized Tools** — individual tools tracked by serial number. "
    "**Small Tools** — quantity-tracked hand tools without serial numbers."
)


def _asset_label(asset: dict[str, Any]) -> str:
    name = str(asset.get("asset_name") or asset.get("name") or "—").strip()
    number = str(asset.get("asset_number") or "").strip()
    if number and number != "—":
        return f"{number} · {name}"
    return name


def _clear_bulk_move_state() -> None:
    st.session_state.pop(_BULK_MOVE_TARGET_KEY, None)
    st.session_state[_BULK_MOVE_CONFIRM_KEY] = False


def _preview_bulk_move(
    selected_ids: list[str],
    assets_by_id: dict[str, dict[str, Any]],
    target: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (ready, blocked) asset rows for a bulk move."""
    ready: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for aid in selected_ids:
        asset = assets_by_id.get(aid) or {}
        label = _asset_label(asset)
        if asset_is_kit(asset) and target != "equipment":
            blocked.append({"id": aid, "label": label, "reason": "Tool Trailers stay on Equipment."})
            continue
        if target == "serialized":
            serial = str(asset.get("serial_number") or "").strip()
            if serial in {"", "—", "-"}:
                blocked.append(
                    {"id": aid, "label": label, "reason": "No serial number — add one before moving."}
                )
                continue
        if resolve_tracking_type(asset) == target:
            blocked.append({"id": aid, "label": label, "reason": f"Already on {TRACKING_TAB_LABELS[target]}."})
            continue
        ready.append({"id": aid, "label": label, "asset": asset})
    return ready, blocked


def render_equipment_bulk_move_toolbar(
    selected_ids: list[str],
    assets_by_id: dict[str, dict[str, Any]],
    *,
    on_clear_selection: Any | None = None,
    on_success_cache_clear: Any | None = None,
) -> None:
    """Checkbox-driven bulk move: Small Tools or Serialized Tools with confirm."""
    ids = [str(aid).strip() for aid in selected_ids if str(aid).strip()]
    count = len(ids)

    if st.session_state.get(_BULK_MOVE_CONFIRM_KEY) and st.session_state.get(_BULK_MOVE_TARGET_KEY):
        target = str(st.session_state.get(_BULK_MOVE_TARGET_KEY) or "")
        ready, blocked = _preview_bulk_move(ids, assets_by_id, target)
        tab_label = TRACKING_TAB_LABELS.get(target, target)

        st.markdown(f"#### Confirm move to {tab_label}")
        st.caption(
            "Equipment = big stuff · Serialized Tools = serial-numbered tools · "
            "Small Tools = counted hand tools · Inventory = consumables"
        )
        if ready:
            st.markdown(f"**{len(ready)}** item(s) will move:")
            for row in ready[:12]:
                st.markdown(f"- {row['label']}")
            if len(ready) > 12:
                st.caption(f"…and {len(ready) - 12} more.")
        else:
            st.warning("No selected items can be moved with this action.")

        if blocked:
            with st.expander(f"{len(blocked)} skipped", expanded=bool(blocked) and not ready):
                for row in blocked:
                    st.markdown(f"- {row['label']}: {row['reason']}")

        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            if st.button("Confirm move", key="ast_bulk_confirm", type="primary", disabled=not ready):
                result = reclassify_assets_bulk([r["id"] for r in ready], target)
                if on_success_cache_clear:
                    on_success_cache_clear()
                _clear_bulk_move_state()
                if result.ok:
                    msg = str((result.data or {}).get("message") or f"Moved to {tab_label}.")
                    st.success(msg)
                    if on_clear_selection:
                        on_clear_selection()
                    st.rerun()
                else:
                    st.error(result.error or "Could not move selected assets.")
        with c2:
            if st.button("Cancel", key="ast_bulk_cancel"):
                _clear_bulk_move_state()
                st.rerun()
        return

    if count == 0:
        st.caption(
            "Select rows with checkboxes, then move hand tools to **Small Tools** "
            "or serial-numbered Milwaukee tools to **Serialized Tools**."
        )
        return

    st.markdown(f"**{count} selected**")
    b1, b2, b3, _ = st.columns([1.4, 1.6, 1.0, 2.0])
    with b1:
        if st.button("Move to Small Tools", key="ast_bulk_small_tools", use_container_width=True):
            st.session_state[_BULK_MOVE_TARGET_KEY] = "quantity"
            st.session_state[_BULK_MOVE_CONFIRM_KEY] = True
            st.rerun()
    with b2:
        if st.button("Move to Serialized Tools", key="ast_bulk_serialized", use_container_width=True):
            st.session_state[_BULK_MOVE_TARGET_KEY] = "serialized"
            st.session_state[_BULK_MOVE_CONFIRM_KEY] = True
            st.rerun()
    with b3:
        if st.button("Clear", key="ast_bulk_clear_sel", use_container_width=True):
            _clear_bulk_move_state()
            if on_clear_selection:
                on_clear_selection()
            st.rerun()


def _linked_hand_tool_qty(asset_id: str) -> tuple[float, float]:
    try:
        from app.services.asset_classification_service import _find_hand_tool_by_source
    except ImportError:
        from services.asset_classification_service import _find_hand_tool_by_source  # type: ignore

    row = _find_hand_tool_by_source(asset_id) or {}
    on_hand = float(row.get("quantity_on_hand") or 1)
    expected = float(row.get("quantity_expected") or on_hand)
    return on_hand, expected


def seed_tracking_form_state(asset: dict[str, Any], *, prefix: str = "ast_edit") -> None:
    """Initialize session keys for tracking bucket controls."""
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return
    bucket = resolve_tracking_type(asset)
    st.session_state.setdefault(f"{prefix}_tracking_bucket_{aid}", bucket)
    on_hand, expected = _linked_hand_tool_qty(aid)
    st.session_state.setdefault(f"{prefix}_qty_on_hand_{aid}", on_hand)
    st.session_state.setdefault(f"{prefix}_qty_expected_{aid}", expected)
    st.session_state.setdefault(
        f"{prefix}_storage_type_{aid}",
        str(asset.get("storage_type") or "Warehouse"),
    )
    st.session_state.setdefault(f"{prefix}_storage_loc_{aid}", str(asset.get("location") or ""))


def render_asset_tracking_bucket_select(
    asset: dict[str, Any],
    *,
    prefix: str = "ast_edit",
    disabled: bool = False,
) -> str:
    """Select which Assets tab owns this record. Returns selected bucket key."""
    aid = str(asset.get("id") or "").strip()
    seed_tracking_form_state(asset, prefix=prefix)
    current = resolve_tracking_type(asset)

    if asset_is_kit(asset):
        st.selectbox(
            "Assets tab / tracking",
            ["equipment"],
            format_func=lambda k: TRACKING_TAB_LABELS[k],
            index=0,
            key=f"{prefix}_tracking_bucket_{aid}",
            disabled=True,
            help="Tool Trailers and kit containers always stay on Equipment.",
        )
        return "equipment"

    options = list(TRACKING_TYPES)
    try:
        index = options.index(st.session_state.get(f"{prefix}_tracking_bucket_{aid}", current))
    except ValueError:
        index = options.index(current) if current in options else 0

    selected = st.selectbox(
        "Assets tab / tracking",
        options,
        index=index,
        format_func=lambda k: TRACKING_TAB_LABELS.get(k, k),
        key=f"{prefix}_tracking_bucket_{aid}",
        disabled=disabled,
        help=_BUCKET_HELP,
    )
    return str(selected)


def _render_bucket_extra_fields(asset: dict[str, Any], bucket: str, *, prefix: str) -> None:
    aid = str(asset.get("id") or "").strip()
    if bucket == "serialized":
        serial = str(asset.get("serial_number") or "").strip()
        if serial in {"", "—", "-"}:
            st.warning("Enter a serial number below (or in Asset details) before saving as Serialized Tools.")
    elif bucket == "quantity":
        st.caption(
            "Creates or updates a Small Tools quantity record linked to this asset. "
            "The asset row is kept for history — it will no longer appear on Equipment."
        )
        q1, q2 = st.columns(2)
        with q1:
            st.number_input(
                "Quantity on hand",
                min_value=0.0,
                step=1.0,
                key=f"{prefix}_qty_on_hand_{aid}",
            )
        with q2:
            st.number_input(
                "Quantity expected",
                min_value=0.0,
                step=1.0,
                key=f"{prefix}_qty_expected_{aid}",
            )
        s1, s2 = st.columns(2)
        with s1:
            st.selectbox("Storage type", list(STORAGE_TYPES), key=f"{prefix}_storage_type_{aid}")
        with s2:
            st.text_input("Storage location", key=f"{prefix}_storage_loc_{aid}")


def reclassify_options_from_session(asset_id: str, *, prefix: str, serial_fallback: str = "") -> dict[str, Any]:
    aid = str(asset_id or "").strip()
    return {
        "serial_number": serial_fallback,
        "quantity_on_hand": float(st.session_state.get(f"{prefix}_qty_on_hand_{aid}", 1.0)),
        "quantity_expected": float(st.session_state.get(f"{prefix}_qty_expected_{aid}", 1.0)),
        "storage_type": str(st.session_state.get(f"{prefix}_storage_type_{aid}", "Warehouse")),
        "storage_location": str(st.session_state.get(f"{prefix}_storage_loc_{aid}", "")),
    }


def apply_tracking_bucket_change(
    asset: dict[str, Any],
    *,
    prefix: str = "ast_edit",
    serial_number: str = "",
    on_success_cache_clear: Any | None = None,
) -> tuple[bool, str]:
    """Reclassify when the selected bucket differs from the asset's current tab."""
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return False, "Missing asset id."

    target = str(st.session_state.get(f"{prefix}_tracking_bucket_{aid}", resolve_tracking_type(asset)))
    current = resolve_tracking_type(asset)
    if target == current:
        return True, ""

    opts = reclassify_options_from_session(aid, prefix=prefix, serial_fallback=serial_number)
    result = reclassify_asset(aid, target, **opts)
    if not result.ok:
        return False, str(result.error or "Could not reclassify asset.")

    if on_success_cache_clear:
        on_success_cache_clear()
    tab = TRACKING_TAB_LABELS.get(target, target)
    if result.data and result.data.get("unchanged"):
        return True, ""
    return True, f"Moved to {tab}."


def render_asset_reclassification_panel(asset: dict[str, Any]) -> None:
    """Show current tab; bulk moves use checkboxes on the Equipment list."""
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return

    try:
        from app.pages._core._crud import is_demo_id
    except ImportError:
        from pages._core._crud import is_demo_id  # type: ignore

    if is_demo_id(aid):
        return

    current_label = tracking_type_label(asset)
    st.markdown(f"**Assets tab:** {current_label}")
    if asset_is_kit(asset):
        st.caption("Tool Trailers and kit containers remain on Equipment.")
    else:
        st.caption(
            "To move this item, select it on the Equipment tab and use "
            "**Move to Small Tools** or **Move to Serialized Tools**. "
            "You can also change the tab under **Edit Asset**."
        )


__all__ = [
    "apply_tracking_bucket_change",
    "render_asset_reclassification_panel",
    "render_asset_tracking_bucket_select",
    "render_equipment_bulk_move_toolbar",
    "render_tracking_bucket_extra_fields",
    "seed_tracking_form_state",
]

# Public alias for edit-form quantity / storage fields.
render_tracking_bucket_extra_fields = _render_bucket_extra_fields
