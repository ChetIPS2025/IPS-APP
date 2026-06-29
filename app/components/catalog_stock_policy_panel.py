"""Pricing Guide detail — stock policy controls (mandatory vs optional inventory)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.action_styles import success_solid_button
    from app.pages._core._crud import is_demo_id
    from app.services.catalog_stock_policy_service import (
        STOCK_POLICIES,
        STOCK_POLICY_LABELS,
        linked_inventory_quantity,
        normalize_stock_policy,
        save_pricing_stock_settings,
        stock_policy_label,
    )
except ImportError:
    from components.action_styles import success_solid_button  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.catalog_stock_policy_service import (  # type: ignore
        STOCK_POLICIES,
        STOCK_POLICY_LABELS,
        linked_inventory_quantity,
        normalize_stock_policy,
        save_pricing_stock_settings,
        stock_policy_label,
    )


def _draft_key(item_id: str, field: str) -> str:
    return f"pg_stock_{field}_{item_id}"


def _policy_options() -> list[str]:
    return [STOCK_POLICY_LABELS[p] for p in STOCK_POLICIES]


def _policy_from_label(label: str) -> str:
    for key, text in STOCK_POLICY_LABELS.items():
        if text == label:
            return key
    return normalize_stock_policy(label)


def render_catalog_stock_policy_panel(
    row: dict[str, Any],
    *,
    can_manage: bool,
    on_change: Callable[[], None] | None = None,
) -> None:
    """Render stock policy + default reorder controls for a pricing guide item."""
    pid = str(row.get("id") or "").strip()
    if not pid or is_demo_id(pid):
        return

    current_policy = normalize_stock_policy(row.get("stock_policy"))
    current_rp = float(row.get("default_reorder_point") or 0)
    current_qty = linked_inventory_quantity(row)
    labels = _policy_options()
    default_label = STOCK_POLICY_LABELS[current_policy]

    with st.container():
        st.markdown('<p class="ips-catalog-presence-title">Inventory Stock Policy</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="ips-inventory-pg-status">'
            "<strong>Mandatory</strong> items always have a linked inventory record and trigger reorder when low. "
            "<strong>Optional</strong> items only appear in inventory when you have extras on hand. "
            "<strong>Not stocked</strong> items are pricing-only.</p>",
            unsafe_allow_html=True,
        )

        policy_label = st.selectbox(
            "Stock policy",
            labels,
            index=labels.index(default_label) if default_label in labels else 0,
            key=_draft_key(pid, "policy"),
            disabled=not can_manage,
        )
        policy = _policy_from_label(policy_label)
        reorder = st.number_input(
            "Default reorder point",
            min_value=0.0,
            value=current_rp,
            step=1.0,
            key=_draft_key(pid, "reorder"),
            disabled=not can_manage or policy == "none",
            help="When on-hand quantity is at or below this level, mandatory items appear in Needs reorder.",
        )
        qty_on_hand = 0.0
        if policy != "none":
            qty_on_hand = float(
                st.number_input(
                    "Quantity on hand",
                    min_value=0.0,
                    value=current_qty,
                    step=1.0,
                    key=_draft_key(pid, "qty"),
                    disabled=not can_manage,
                    help=(
                        "For optional extras, enter what you have left from jobs — "
                        "inventory is created automatically when quantity is greater than zero."
                    ),
                )
            )

        if not can_manage:
            st.caption(f"Current policy: {stock_policy_label(current_policy)}")
            if current_policy != "none":
                st.caption(f"Quantity on hand: {current_qty:g}")
            return

        unchanged = (
            policy == current_policy
            and float(reorder) == current_rp
            and (policy == "none" or float(qty_on_hand) == float(current_qty))
        )
        if success_solid_button(
            "Save Stock Policy",
            f"pg_stock_save_{pid}",
            use_container_width=False,
            disabled=unchanged,
        ):
            result = save_pricing_stock_settings(
                row,
                stock_policy=policy,
                default_reorder_point=float(reorder),
                quantity_on_hand=float(qty_on_hand) if policy != "none" else None,
                ensure_inventory=True,
            )
            if result.ok:
                st.success(str((result.data or {}).get("message") or "Stock policy saved."))
                if on_change:
                    on_change()
                st.rerun()
            else:
                st.error(result.error or "Could not save stock policy.")
