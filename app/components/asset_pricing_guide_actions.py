"""Asset detail modal — pricing guide link actions."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.action_styles import success_solid_button
    from app.pages._core._crud import is_demo_id
    from app.services.assets_service import (
        asset_include_in_pricing_guide,
        can_manage_asset_actions,
        clear_assets_cache,
        set_asset_include_in_pricing_guide,
    )
    from app.services.pricing_guide_service import (
        cached_pricing_guide_rows,
        link_asset_to_pricing_item,
        save_pricing_item,
    )
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.action_styles import success_solid_button  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.assets_service import (  # type: ignore
        asset_include_in_pricing_guide,
        can_manage_asset_actions,
        clear_assets_cache,
        set_asset_include_in_pricing_guide,
    )
    from services.pricing_guide_service import (  # type: ignore
        cached_pricing_guide_rows,
        link_asset_to_pricing_item,
        save_pricing_item,
    )
    from utils.formatting import fmt_currency  # type: ignore


def _confirm_state_key(asset_id: str, action: str) -> str:
    return f"confirm_{action}_asset_pg_{asset_id}"


def _resolve_linked_pricing_item(asset: dict[str, Any]) -> dict[str, Any] | None:
    aid = str(asset.get("id") or "").strip()
    pricing_item_id = str(asset.get("pricing_guide_id") or asset.get("pricing_item_id") or "").strip()
    rows = cached_pricing_guide_rows(include_inactive=True)
    if pricing_item_id:
        linked = next((r for r in rows if str(r.get("id")) == pricing_item_id), None)
        if linked:
            return linked
    return next(
        (
            r
            for r in rows
            if str(r.get("linked_asset_id") or r.get("asset_id") or "") == aid
        ),
        None,
    )


def _asset_pricing_options() -> list[tuple[str, str]]:
    return [
        (f"{r.get('description')} — {r.get('item_type')}", str(r.get("id")))
        for r in cached_pricing_guide_rows(include_inactive=True)
        if r.get("item_class") == "Asset" and str(r.get("id") or "").strip()
    ]


def _asset_pricing_cost(asset: dict[str, Any]) -> float:
    hourly = float(asset.get("hourly_rate") or 0)
    daily = float(asset.get("daily_rate") or asset.get("rental_daily_rate") or 0)
    return hourly or (daily / 8.0 if daily else 0.0)


def _create_pricing_item_from_asset(asset: dict[str, Any]) -> tuple[bool, str]:
    aid = str(asset.get("id") or "").strip()
    cost = _asset_pricing_cost(asset)
    ok, msg = save_pricing_item(
        {
            "item_type": "Equipment",
            "item_class": "Asset",
            "description": str(asset.get("asset_name") or asset.get("name") or "Equipment"),
            "category": str(asset.get("category") or "Equipment"),
            "unit": "HR",
            "default_cost": cost,
            "default_markup_percent": 0.0,
            "default_sell_price": cost,
            "asset_id": aid,
            "linked_asset_id": aid,
            "equipment_type": str(asset.get("category") or asset.get("asset_type") or ""),
            "is_active": asset.get("is_active") is not False,
        }
    )
    if not ok:
        return False, msg
    pid = next(
        (
            str(r.get("id"))
            for r in cached_pricing_guide_rows(include_inactive=True)
            if str(r.get("linked_asset_id") or r.get("asset_id") or "") == aid
        ),
        "",
    )
    if pid:
        link_asset_to_pricing_item(aid, pid)
    set_asset_include_in_pricing_guide(aid, True)
    return True, msg


def _render_confirm_link_card(*, asset_id: str, options: list[tuple[str, str]]) -> None:
    confirm_key = _confirm_state_key(asset_id, "link")
    st.markdown(
        f'<div class="ips-confirm-card">'
        f'<div class="ips-confirm-title">Link to Pricing Guide</div>'
        f'<div class="ips-confirm-text">Choose a pricing guide item to link with this asset.</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    labels = [label for label, _ in options]
    pick = st.selectbox("Equipment pricing item", labels, key=f"asset_pg_pick_{asset_id}")
    id_map = {label: pid for label, pid in options}
    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"asset_pg_link_cancel_{asset_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        if success_solid_button("Confirm Link", f"asset_pg_link_confirm_{asset_id}", use_container_width=True):
            ok, msg = link_asset_to_pricing_item(asset_id, id_map.get(pick, ""))
            if ok:
                set_asset_include_in_pricing_guide(asset_id, True)
                st.session_state.pop(confirm_key, None)
                st.success(msg)
                st.rerun()
            st.error(msg)


def render_asset_pricing_guide_actions(
    asset: dict[str, Any],
    *,
    on_change: Callable[[], None] | None = None,
) -> None:
    """Render pricing guide link status and actions using Asset Actions styling."""
    aid = str(asset.get("id") or "").strip()
    if not aid or is_demo_id(aid):
        return

    asset_key = "".join(ch if ch.isalnum() else "_" for ch in aid) or "asset"
    include = asset_include_in_pricing_guide(asset)
    linked = _resolve_linked_pricing_item(asset) if include else None

    with st.container(key=f"asset_pg_actions_{asset_key}"):
        st.markdown('<span class="ips-asset-actions-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-asset-actions-title">Pricing Guide</p>', unsafe_allow_html=True)

        if not include:
            st.markdown(
                '<p class="ips-inventory-pg-status">Not included on Pricing Guide. '
                "This asset is tracked in Assets only.</p>",
                unsafe_allow_html=True,
            )
            if not can_manage_asset_actions():
                st.caption("Only admin, manager, or supervisor can change pricing guide settings.")
                return
            if success_solid_button("Include on Pricing Guide", f"asset_pg_enable_{asset_key}", use_container_width=False):
                result = set_asset_include_in_pricing_guide(aid, True)
                if result.ok:
                    clear_assets_cache()
                    if on_change:
                        on_change()
                    st.rerun()
                st.error(result.error or "Could not update asset.")
            return

        if linked:
            desc = html.escape(str(linked.get("description") or "Pricing item"))
            item_type = html.escape(str(linked.get("item_type") or ""))
            rate = fmt_currency(linked.get("default_cost"))
            sell = fmt_currency(linked.get("default_sell_price"))
            st.markdown(
                f'<p class="ips-inventory-pg-status">Linked: <strong>{desc}</strong>'
                f"{f' ({item_type})' if item_type else ''}"
                f"<br><span>Rate {rate}/hr · Sell {sell}</span></p>",
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            '<p class="ips-inventory-pg-status">Included on Pricing Guide, but no item is linked yet.</p>',
            unsafe_allow_html=True,
        )

        if not can_manage_asset_actions():
            st.caption("Only admin, manager, or supervisor can link pricing guide items.")
            return

        if st.session_state.get(_confirm_state_key(aid, "link")):
            options = _asset_pricing_options()
            if not options:
                st.caption("No asset-class pricing guide items are available to link.")
                if st.button("Close", key=f"asset_pg_link_close_{aid}"):
                    st.session_state.pop(_confirm_state_key(aid, "link"), None)
                    st.rerun()
                return
            _render_confirm_link_card(asset_id=aid, options=options)
            return

        action_specs: list[tuple[str, str, str]] = [
            ("create", "Create Pricing Item", f"open_pg_create_{asset_key}"),
        ]
        options = _asset_pricing_options()
        if options:
            action_specs.append(("link", "Link to Pricing Guide", f"open_pg_link_{asset_key}"))

        cols = st.columns(len(action_specs), gap="small")
        for col, (action, label, suffix) in zip(cols, action_specs):
            with col:
                if not success_solid_button(label, suffix, use_container_width=False):
                    continue
                if action == "create":
                    ok, msg = _create_pricing_item_from_asset(asset)
                    if ok:
                        st.success(msg)
                        if on_change:
                            on_change()
                        st.rerun()
                    st.error(msg)
                elif action == "link":
                    st.session_state[_confirm_state_key(aid, "link")] = True
                    st.rerun()
