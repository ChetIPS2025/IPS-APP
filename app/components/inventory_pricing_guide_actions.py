"""Inventory detail modal — pricing guide link actions."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.components.action_styles import success_solid_button
from app.pages._core._crud import is_demo_id
from app.services.inventory_service import can_manage_inventory_actions
from app.services.pricing_guide_service import (
    cached_pricing_guide_rows,
    create_pricing_item_from_inventory,
    link_inventory_to_pricing_item,
)
from app.utils.formatting import fmt_currency
def _confirm_state_key(item_id: str, action: str) -> str:
    return f"confirm_{action}_inv_pg_{item_id}"


def _resolve_linked_pricing_item(item: dict[str, Any]) -> dict[str, Any] | None:
    iid = str(item.get("id") or "").strip()
    pricing_item_id = str(item.get("pricing_guide_id") or item.get("pricing_item_id") or "").strip()
    rows = cached_pricing_guide_rows(include_inactive=True)
    if pricing_item_id:
        linked = next((r for r in rows if str(r.get("id")) == pricing_item_id), None)
        if linked:
            return linked
    return next(
        (
            r
            for r in rows
            if str(r.get("linked_inventory_id") or r.get("inventory_item_id") or "") == iid
        ),
        None,
    )


def _inventory_pricing_options() -> list[tuple[str, str]]:
    return [
        (f"{r.get('description')} — {r.get('item_type')}", str(r.get("id")))
        for r in cached_pricing_guide_rows(include_inactive=True)
        if r.get("item_class") == "Inventory" and str(r.get("id") or "").strip()
    ]


def _render_confirm_link_card(*, item_id: str, options: list[tuple[str, str]]) -> None:
    confirm_key = _confirm_state_key(item_id, "link")
    st.markdown(
        f'<div class="ips-confirm-card">'
        f'<div class="ips-confirm-title">Link to Pricing Guide</div>'
        f'<div class="ips-confirm-text">Choose a pricing guide item to link with this inventory record.</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    labels = [label for label, _ in options]
    pick = st.selectbox("Pricing item", labels, key=f"inv_pg_pick_{item_id}")
    id_map = {label: pid for label, pid in options}
    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"inv_pg_link_cancel_{item_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        if success_solid_button("Confirm Link", f"inv_pg_link_confirm_{item_id}", use_container_width=True):
            ok, msg = link_inventory_to_pricing_item(item_id, id_map.get(pick, ""))
            if ok:
                st.session_state.pop(confirm_key, None)
                st.success(msg)
                st.rerun()
            st.error(msg)


def render_inventory_pricing_guide_actions(
    item: dict[str, Any],
    *,
    on_change: Callable[[], None] | None = None,
) -> None:
    """Render pricing guide link status and actions using Inventory Actions styling."""
    iid = str(item.get("id") or "").strip()
    if not iid or is_demo_id(iid):
        return

    linked = _resolve_linked_pricing_item(item)
    item_key = "".join(ch if ch.isalnum() else "_" for ch in iid) or "inv"

    with st.container(key=f"inventory_pg_actions_{item_key}"):
        st.markdown('<span class="ips-inventory-actions-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-inventory-actions-title">Pricing Guide</p>', unsafe_allow_html=True)

        if linked:
            desc = html.escape(str(linked.get("description") or "Pricing item"))
            item_type = html.escape(str(linked.get("item_type") or ""))
            cost = fmt_currency(linked.get("default_cost"))
            sell = fmt_currency(linked.get("default_sell_price"))
            st.markdown(
                f'<p class="ips-inventory-pg-status">Linked: <strong>{desc}</strong>'
                f"{f' ({item_type})' if item_type else ''}"
                f"<br><span>Cost {cost} · Sell {sell}</span>"
                f"<br><span>Use <strong>Remove from Inventory</strong> above to keep this item on estimates without stock tracking.</span></p>",
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            '<p class="ips-inventory-pg-status">No pricing guide item linked.</p>',
            unsafe_allow_html=True,
        )

        if not can_manage_inventory_actions():
            st.caption("Only admin, manager, or supervisor can link pricing guide items.")
            return

        if st.session_state.get(_confirm_state_key(iid, "link")):
            options = _inventory_pricing_options()
            if not options:
                st.caption("No inventory-class pricing guide items are available to link.")
                if st.button("Close", key=f"inv_pg_link_close_{iid}"):
                    st.session_state.pop(_confirm_state_key(iid, "link"), None)
                    st.rerun()
                return
            _render_confirm_link_card(item_id=iid, options=options)
            return

        action_specs: list[tuple[str, str, str]] = [
            ("create", "Create Pricing Item", f"open_pg_create_{item_key}"),
        ]
        options = _inventory_pricing_options()
        if options:
            action_specs.append(("link", "Link to Pricing Guide", f"open_pg_link_{item_key}"))

        cols = st.columns(len(action_specs), gap="small")
        for col, (action, label, suffix) in zip(cols, action_specs):
            with col:
                if not success_solid_button(label, suffix, use_container_width=False):
                    continue
                if action == "create":
                    ok, msg, pid = create_pricing_item_from_inventory(item)
                    if ok and pid:
                        link_inventory_to_pricing_item(iid, pid)
                    if ok:
                        st.success(msg)
                        if on_change:
                            on_change()
                        st.rerun()
                    st.error(msg)
                elif action == "link":
                    st.session_state[_confirm_state_key(iid, "link")] = True
                    st.rerun()
