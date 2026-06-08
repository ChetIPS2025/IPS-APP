"""
Field-facing vocabulary for the three stock-tracking domains.

Inventory (consumables): consumed, used, restocked, adjusted.
Serialized tools / assets: checked out, checked in, assigned, returned.
Small tools (quantity-counted): counted, moved, audited, missing, adjusted.

Never use checkout/check-in language for inventory.
Never use consumed/used language for serialized tool possession.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Inventory — consumables / materials
# ---------------------------------------------------------------------------

INVENTORY_USE_ON_JOB_LABEL = "Use on Job"
INVENTORY_USE_IN_SHOP_LABEL = "Use in Shop"
INVENTORY_ADJUST_LABEL = "Adjust stock"

INVENTORY_ACTION_LABELS: dict[str, str] = {
    "consume_on_job": "Used on job",
    "CONSUME": "Used on job",
    "shop_use": "Used in shop",
    "SHOP": "Used in shop",
    "issue_to_job": "Used on job",
    "TO_JOB": "Used on job",
    "check_out": "Used in shop",
    "OUT": "Used in shop",
    "check_in": "Restocked",
    "IN": "Restocked",
    "return_from_job": "Restocked",
    "RETURN": "Restocked",
    "adjustment": "Adjusted",
    "ADJUST": "Adjusted",
}

# ---------------------------------------------------------------------------
# Serialized tools / checkout assets
# ---------------------------------------------------------------------------

SERIALIZED_TOOL_ACTION_LABELS: dict[str, str] = {
    "CHECK_OUT": "Checked out",
    "check_out": "Checked out",
    "CHECK_IN": "Checked in",
    "check_in": "Checked in",
    "ASSIGN": "Assigned",
    "assign": "Assigned",
    "assigned": "Assigned",
    "RETURN": "Returned",
    "return": "Returned",
    "returned": "Returned",
    "REASSIGN": "Reassigned",
    "reassign": "Reassigned",
}

# ---------------------------------------------------------------------------
# Small tools — quantity-counted hand tools
# ---------------------------------------------------------------------------

SMALL_TOOL_ACTION_LABELS: dict[str, str] = {
    "count": "Counted",
    "counted": "Counted",
    "move": "Moved",
    "moved": "Moved",
    "audit": "Audited",
    "audited": "Audited",
    "missing": "Missing",
    "adjust": "Adjusted",
    "adjusted": "Adjusted",
    "remove": "Removed",
    "removed": "Removed",
}


def inventory_action_label(txn_type: str) -> str:
    """Human label for an inventory transaction (consumables only)."""
    key = str(txn_type or "").strip()
    if not key:
        return "—"
    return INVENTORY_ACTION_LABELS.get(key, INVENTORY_ACTION_LABELS.get(key.lower(), key))


def serialized_tool_action_label(txn_type: str) -> str:
    """Human label for a serialized tool / asset possession event."""
    key = str(txn_type or "").strip()
    if not key:
        return "—"
    return SERIALIZED_TOOL_ACTION_LABELS.get(key, SERIALIZED_TOOL_ACTION_LABELS.get(key.lower(), key))


def small_tool_action_label(action: str) -> str:
    """Human label for a small-tool count / audit / move event."""
    key = str(action or "").strip()
    if not key:
        return "—"
    return SMALL_TOOL_ACTION_LABELS.get(key, SMALL_TOOL_ACTION_LABELS.get(key.lower(), key))


__all__ = [
    "INVENTORY_ACTION_LABELS",
    "INVENTORY_ADJUST_LABEL",
    "INVENTORY_USE_IN_SHOP_LABEL",
    "INVENTORY_USE_ON_JOB_LABEL",
    "SERIALIZED_TOOL_ACTION_LABELS",
    "SMALL_TOOL_ACTION_LABELS",
    "inventory_action_label",
    "serialized_tool_action_label",
    "small_tool_action_label",
]
