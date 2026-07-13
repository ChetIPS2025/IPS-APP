"""Pricing Guide detail modal — unified catalog table presence controls."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.components.action_styles import success_solid_button
from app.pages._core._crud import is_demo_id
from app.services.catalog_presence_service import apply_catalog_presence, resolve_catalog_presence
def _confirm_state_key(item_id: str) -> str:
    return f"confirm_catalog_presence_{item_id}"


def _draft_state_key(item_id: str, field: str) -> str:
    return f"catalog_presence_{field}_{item_id}"


def _resync_state_key(item_id: str) -> str:
    return f"catalog_presence_resync_{item_id}"


def _reset_draft_keys(item_id: str) -> None:
    for field in ("pg", "inv", "ast"):
        st.session_state.pop(_draft_state_key(item_id, field), None)


def _fresh_pricing_row(row: dict[str, Any]) -> dict[str, Any]:
    pid = str(row.get("id") or "").strip()
    if not pid:
        return row
    from app.services.pricing_guide_service import cached_pricing_guide_rows
    return next(
        (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid),
        row,
    )


def _sync_draft_from_presence(item_id: str, presence: dict[str, Any]) -> None:
    st.session_state[_draft_state_key(item_id, "pg")] = bool(presence.get("pricing_guide"))
    st.session_state[_draft_state_key(item_id, "inv")] = bool(presence.get("inventory"))
    st.session_state[_draft_state_key(item_id, "ast")] = bool(presence.get("assets"))


def _render_confirm_card(
    *,
    item_id: str,
    message: str,
    on_confirm: Callable[[], bool],
) -> None:
    confirm_key = _confirm_state_key(item_id)
    st.markdown(
        f'<div class="ips-confirm-card">'
        f'<div class="ips-confirm-title">Apply Catalog Presence</div>'
        f'<div class="ips-confirm-text">{html.escape(message)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"catalog_presence_cancel_{item_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        if success_solid_button("Confirm Changes", f"catalog_presence_confirm_{item_id}", use_container_width=True):
            if on_confirm():
                st.session_state.pop(confirm_key, None)
                st.rerun()


def _build_confirm_message(
    *,
    current: dict[str, Any],
    pricing_guide: bool,
    inventory: bool,
    assets: bool,
) -> str | None:
    parts: list[str] = []
    if not pricing_guide and current.get("pricing_guide"):
        parts.append("Hide this item from the Pricing Guide and estimates.")
    if not inventory and current.get("inventory"):
        label = str(current.get("inventory_label") or "linked stock record")
        parts.append(f"Remove the Inventory record ({label}) and stop tracking stock.")
    if not assets and current.get("assets"):
        label = str(current.get("asset_label") or "linked fleet record")
        parts.append(
            f"Remove the Assets record ({label}). Related photos, maintenance, and inspection data may be deleted."
        )
    if not parts:
        return None
    return " ".join(parts)


def _schedule_presence_resync(item_id: str, *, on_change: Callable[[], None] | None) -> None:
    st.session_state[_resync_state_key(item_id)] = True
    if on_change:
        on_change()


def _prepare_draft_state(row: dict[str, Any], item_id: str) -> dict[str, Any]:
    if st.session_state.pop(_resync_state_key(item_id), False):
        _reset_draft_keys(item_id)
    fresh_row = _fresh_pricing_row(row)
    presence = resolve_catalog_presence(fresh_row)
    if _draft_state_key(item_id, "pg") not in st.session_state:
        _sync_draft_from_presence(item_id, presence)
    return presence


def render_catalog_presence_panel(
    row: dict[str, Any],
    *,
    can_manage: bool,
    on_change: Callable[[], None] | None = None,
) -> None:
    """Render Pricing Guide / Inventory / Assets presence toggles."""
    pid = str(row.get("id") or "").strip()
    if not pid or is_demo_id(pid):
        return

    item_key = "".join(ch if ch.isalnum() else "_" for ch in pid) or "pg"
    presence = _prepare_draft_state(row, pid)

    with st.container(key=f"catalog_presence_{item_key}"):
        st.markdown('<span class="ips-catalog-presence-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-catalog-presence-title">Catalog Presence</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="ips-inventory-pg-status">Choose which catalogs this item appears in. '
            "The Pricing Guide row always exists; toggling it controls estimate visibility.</p>",
            unsafe_allow_html=True,
        )

        pricing_guide = st.checkbox(
            "Pricing Guide",
            key=_draft_state_key(pid, "pg"),
            disabled=not can_manage,
            help="When off, this item is hidden from the Pricing Guide list and estimates.",
        )
        inventory = st.checkbox(
            "Inventory",
            key=_draft_state_key(pid, "inv"),
            disabled=not can_manage,
            help="Creates or removes a stock record linked to this pricing item.",
        )
        assets = st.checkbox(
            "Assets",
            key=_draft_state_key(pid, "ast"),
            disabled=not can_manage,
            help="Creates or removes a fleet record linked to this pricing item.",
        )

        status_bits: list[str] = []
        if presence.get("inventory_label"):
            status_bits.append(f"Inventory: {presence['inventory_label']}")
        if presence.get("asset_label"):
            status_bits.append(f"Assets: {presence['asset_label']}")
        if status_bits:
            st.caption(" · ".join(status_bits))

        if not can_manage:
            st.caption("Only admin, manager, or supervisor can change catalog presence.")
            return

        confirm_key = _confirm_state_key(pid)
        if st.session_state.get(confirm_key):
            message = str(st.session_state.get(f"{confirm_key}_message") or "Apply these catalog changes?")

            def _apply() -> bool:
                result = apply_catalog_presence(
                    row,
                    pricing_guide=bool(st.session_state.get(_draft_state_key(pid, "pg"))),
                    inventory=bool(st.session_state.get(_draft_state_key(pid, "inv"))),
                    assets=bool(st.session_state.get(_draft_state_key(pid, "ast"))),
                )
                if result.ok:
                    message_text = str((result.data or {}).get("message") or "Catalog presence updated.")
                    st.success(message_text)
                    _schedule_presence_resync(pid, on_change=on_change)
                    return True
                st.error(result.error or "Could not update catalog presence.")
                return False

            _render_confirm_card(item_id=pid, message=message, on_confirm=_apply)
            return

        unchanged = (
            bool(pricing_guide) == bool(presence.get("pricing_guide"))
            and bool(inventory) == bool(presence.get("inventory"))
            and bool(assets) == bool(presence.get("assets"))
        )
        if success_solid_button(
            "Apply Catalog Presence",
            f"catalog_presence_apply_{item_key}",
            use_container_width=False,
            disabled=unchanged,
        ):
            confirm_message = _build_confirm_message(
                current=presence,
                pricing_guide=bool(pricing_guide),
                inventory=bool(inventory),
                assets=bool(assets),
            )
            if confirm_message:
                st.session_state[confirm_key] = True
                st.session_state[f"{confirm_key}_message"] = confirm_message
                st.rerun()
            else:
                result = apply_catalog_presence(
                    row,
                    pricing_guide=bool(pricing_guide),
                    inventory=bool(inventory),
                    assets=bool(assets),
                )
                if result.ok:
                    message_text = str((result.data or {}).get("message") or "Catalog presence updated.")
                    st.success(message_text)
                    _schedule_presence_resync(pid, on_change=on_change)
                    st.rerun()
                st.error(result.error or "Could not update catalog presence.")
