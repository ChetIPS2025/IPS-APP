"""Estimates module (Phase 2B)."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

try:
    from app.components.record_modal import (
        build_modal_cache,
        clear_edit_modes,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        status_pill_html as modal_status_pill_html,
    )
    from app.pages.estimate_builder_ui import (
        render_cost_builder_tab,
        render_markups_tab,
        render_proposal_preview_tab,
        render_scope_of_work_tab,
        render_summary_tab,
    )
    from app.pages._core._data import (
        ACTIVE_ESTIMATE_KEY,
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        customer_location_select_options,
        get_estimate,
        load_assets,
        load_estimates,
        load_inventory,
        load_jobs,
        lookup_options,
        persist_estimate,
    )
    from app.components.estimate_actions import render_estimate_action_buttons
    from app.components.estimates_page_layout import (
        close_estimates_filter_bar_shell,
        inject_estimates_page_layout_css,
        render_estimates_filter_bar_shell,
        render_estimates_summary_cards,
    )
    from app.components.headers import render_page_brand_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from app.components.table_pagination import (
        paginate_rows,
        render_table_pagination_footer,
        render_table_pagination_header,
        reset_table_page,
    )
    from app.pages._core._crud import is_demo_id
    from app.pages._core._session import select_key
    from app.services.estimates_service import (
        approve_estimate_and_sync_job,
        begin_approved_estimate_revision,
        cancel_approved_estimate_revision,
        complete_approved_estimate_revision,
        can_approve_estimates,
        can_revise_approved_estimates,
        estimate_status_approvable,
        estimate_visible_in_active_view,
        estimate_visible_in_approved_view,
        estimate_visible_in_archived_view,
        estimate_visible_in_draft_view,
        estimate_visible_in_rejected_view,
        estimate_visible_in_sent_view,
    )
    from app.auth import current_role
    from app.components.quote_job_number_autofill import (
        clear_new_estimate_number_state,
        linked_job_number_preview,
        sync_new_estimate_number,
    )
    from app.styles import inject_estimates_module_css
    from app.utils.formatting import fmt_currency, fmt_date
    from app.services.estimate_expiration_service import (
        default_expiration_date,
        effective_expiration_date,
        ensure_estimate_expiration_persisted,
        format_effective_expiration,
        format_estimate_date,
    )
except ImportError:
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_edit_modes,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        status_pill_html as modal_status_pill_html,
    )
    from pages.estimate_builder_ui import (  # type: ignore
        render_cost_builder_tab,
        render_markups_tab,
        render_proposal_preview_tab,
        render_scope_of_work_tab,
        render_summary_tab,
    )
    from pages._core._data import (  # type: ignore
        ACTIVE_ESTIMATE_KEY,
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        customer_location_select_options,
        get_estimate,
        load_assets,
        load_estimates,
        load_inventory,
        load_jobs,
        lookup_options,
        persist_estimate,
    )
    from components.estimate_actions import render_estimate_action_buttons  # type: ignore
    from components.estimates_page_layout import (  # type: ignore
        close_estimates_filter_bar_shell,
        inject_estimates_page_layout_css,
        render_estimates_filter_bar_shell,
        render_estimates_summary_cards,
    )
    from components.headers import render_page_brand_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from components.table_pagination import (  # type: ignore
        paginate_rows,
        render_table_pagination_footer,
        render_table_pagination_header,
        reset_table_page,
    )
    from pages._core._crud import is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.estimates_service import (  # type: ignore
        approve_estimate_and_sync_job,
        begin_approved_estimate_revision,
        cancel_approved_estimate_revision,
        complete_approved_estimate_revision,
        can_approve_estimates,
        can_revise_approved_estimates,
        estimate_status_approvable,
        estimate_visible_in_active_view,
        estimate_visible_in_approved_view,
        estimate_visible_in_archived_view,
        estimate_visible_in_draft_view,
        estimate_visible_in_rejected_view,
        estimate_visible_in_sent_view,
    )
    from auth import current_role  # type: ignore
    from components.quote_job_number_autofill import (  # type: ignore
        clear_new_estimate_number_state,
        linked_job_number_preview,
        sync_new_estimate_number,
    )
    from styles import inject_estimates_module_css  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore
    from services.estimate_expiration_service import (  # type: ignore
        default_expiration_date,
        effective_expiration_date,
        ensure_estimate_expiration_persisted,
        format_effective_expiration,
        format_estimate_date,
    )

_SEL = select_key("estimates")
_MOD = "estimates"
_TABLE_KEY = "estimates_list"
_ESTIMATES_MODAL_KEY = "ips_estimates_detail_modal_id"
_ESTIMATES_CACHE_KEY = "_ips_estimates_modal_by_id"
_NEW_CUST_PREV = "est_new_cust_prev"


def _est_new_num_edited() -> None:
    st.session_state["est_new_num_manual"] = True


_ESTIMATE_TABS = [
    "Overview",
    "Scope of Work",
    "Cost Builder",
    "Markups",
    "Summary",
    "Proposal Preview",
    "Attachments",
    "Notes",
    "Activity",
]
_ESTIMATE_COLS = [0.35, 1.05, 2.2, 1.55, 1.05, 1.05, 1.15, 0.95, 1.15]
_ESTIMATE_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("ESTIMATE #", None),
    ("PROJECT / DESCRIPTION", None),
    ("CUSTOMER", "customer"),
    ("LINKED JOB", None),
    ("STATUS", "status"),
    ("ESTIMATE DATE", None),
    ("TOTAL", None),
    ("ACTIONS", None),
]
_PENDING_APPROVE_KEY = "est_pending_approve_id"
_NEW_ESTIMATE_DIALOG_KEY = "ips_est_new_dialog_open"
_BUILD_MODE_PREFIX = "est_build_mode_"
_REVISE_MODE_PREFIX = "est_revise_mode_"
_REVISE_SNAPSHOT_PREFIX = "est_revise_snapshot_"
_REVISE_BEGIN_CONFIRM_PREFIX = "est_revise_begin_confirm_"
_REVISE_COMPLETE_CONFIRM_PREFIX = "est_revise_complete_confirm_"
_REVISE_CANCEL_CONFIRM_PREFIX = "est_revise_cancel_confirm_"
SELECTED_ESTIMATE_KEY = "selected_estimate_id"
SHOW_ESTIMATE_MODAL_KEY = "show_estimate_detail_modal"
_ALL_ESTIMATE_IDS_KEY = "_ips_estimates_visible_ids"
_COST_BUILDER_OPTS_CACHE_KEY = "_ips_cost_builder_select_opts"


def _as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _normalize_estimate_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Draft",
        "draft": "Draft",
        "pending": "Pending",
        "sent": "Sent",
        "approved": "Approved",
        "awarded": "Awarded",
        "rejected": "Rejected",
        "expired": "Expired",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "Draft"


def _estimate_number(row: dict) -> str:
    val = str(row.get("estimate_number") or row.get("number") or "").strip()
    return val or "—"


def _estimate_row_label(row: dict, key: str) -> str:
    val = str(row.get(key) or "").strip()
    return val if val and val != "—" else ""


def _estimate_project(row: dict) -> str:
    """Project name only for list/export (not scope, proposal, or notes)."""
    try:
        from app.services.phase2_modules_service import estimate_project_title
    except ImportError:
        from services.phase2_modules_service import estimate_project_title  # type: ignore
    return estimate_project_title(row)


def _estimate_customer(row: dict) -> str:
    for key in ("customer_name", "customer"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _estimate_created_by(row: dict) -> str:
    val = str(row.get("created_by") or row.get("created_by_name") or "").strip()
    return val or "—"


def _estimate_job(row: dict) -> str:
    """Linked job label only when a real job row is linked (not a Q→J preview)."""
    for key in ("job_number", "linked_job_number"):
        val = _estimate_row_label(row, key)
        if val and val not in {"—", "-", "— None —"}:
            return val
    linked = row.get("linked_job")
    if isinstance(linked, dict):
        try:
            from app.utils.formatters import job_display_label
        except ImportError:
            from utils.formatters import job_display_label  # type: ignore
        label = job_display_label(linked.get("job_number"), linked.get("job_name"))
        if label:
            return label
    if str(row.get("job_id") or "").strip():
        return _estimate_row_label(row, "job_number") or "—"
    return "—"


def _estimate_total_cost(row: dict) -> str:
    val = row.get("total_cost")
    if val in (None, ""):
        val = row.get("subtotal")
    if val not in (None, ""):
        try:
            if float(val) != 0:
                return fmt_currency(val)
        except (TypeError, ValueError):
            pass
    return _estimate_customer_price_from_builder(row, field="total_cost")


def _estimate_stored_customer_price(row: dict) -> float:
    for key in ("customer_price", "total", "grand_total", "proposal_total", "final_bid"):
        val = row.get(key)
        if val in (None, ""):
            continue
        try:
            amount = float(val)
        except (TypeError, ValueError):
            continue
        if amount != 0 or key in ("customer_price", "proposal_total", "final_bid"):
            return amount
    return 0.0


def _estimate_live_customer_price_amount(row: dict) -> float:
    eid = str(row.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return 0.0
    try:
        from app.services.estimate_costing_service import calculate_estimate_totals
    except ImportError:
        from services.estimate_costing_service import calculate_estimate_totals  # type: ignore
    try:
        return float(calculate_estimate_totals(eid).get("customer_price") or 0)
    except Exception:
        return 0.0


def _estimate_rollups_are_stale(row: dict) -> bool:
    live = _estimate_live_customer_price_amount(row)
    if live <= 0:
        return False
    stored = _estimate_stored_customer_price(row)
    return stored <= 0 or abs(stored - live) > 0.01


def _estimate_customer_price_from_builder(row: dict, *, field: str = "customer_price") -> str:
    """Use live Cost Builder totals when the estimate row rollup is still zero."""
    eid = str(row.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return fmt_currency(0)
    try:
        from app.services.estimate_costing_service import calculate_estimate_totals
    except ImportError:
        from services.estimate_costing_service import calculate_estimate_totals  # type: ignore
    try:
        totals = calculate_estimate_totals(eid)
        amount = float(totals.get(field) or totals.get("customer_price") or 0)
        if amount > 0:
            return fmt_currency(amount)
    except Exception:
        pass
    return fmt_currency(0)


def _estimate_customer_price(row: dict) -> str:
    stored = _estimate_stored_customer_price(row)
    live = _estimate_live_customer_price_amount(row)
    if live > 0 and (stored <= 0 or abs(stored - live) > 0.01):
        return fmt_currency(live)
    if stored > 0:
        return fmt_currency(stored)
    return fmt_currency(live) if live > 0 else fmt_currency(0)


def _estimate_customer_price_amount(row: dict) -> float:
    stored = _estimate_stored_customer_price(row)
    if stored > 0:
        return stored
    live = _estimate_live_customer_price_amount(row)
    return live if live > 0 else 0.0


def _sync_estimate_rollups_if_stale(estimate_id: str) -> None:
    """Persist Cost Builder totals when list/modal row is out of date."""
    eid = str(estimate_id or "").strip()
    if not eid or is_demo_id(eid):
        return
    est_row = get_estimate(eid) or {}
    if not _estimate_rollups_are_stale(est_row):
        return
    live = _estimate_live_customer_price_amount(est_row)
    sync_key = f"_est_rollups_synced_{eid}"
    if st.session_state.get(sync_key) == live:
        return
    try:
        from app.services.estimate_costing_service import recalculate_and_save_estimate_totals
    except ImportError:
        from services.estimate_costing_service import recalculate_and_save_estimate_totals  # type: ignore
    try:
        if recalculate_and_save_estimate_totals(eid).ok:
            st.session_state[sync_key] = live
            try:
                from app.pages._core._data import clear_estimates_list_cache, clear_catalog_session_datasets
            except ImportError:
                from pages._core._data import clear_estimates_list_cache, clear_catalog_session_datasets  # type: ignore
            clear_estimates_list_cache()
            clear_catalog_session_datasets()
    except Exception:
        pass


def _sync_stale_estimate_rollups(rows: list[dict], *, max_sync: int = 5) -> dict[str, dict]:
    """Refresh at most ``max_sync`` stale estimate totals per page load (not per table row)."""
    refreshed: dict[str, dict] = {}
    synced = 0
    for est in rows:
        if synced >= max_sync:
            break
        eid = str(est.get("id") or "").strip()
        if not eid or not _estimate_rollups_are_stale(est):
            continue
        _sync_estimate_rollups_if_stale(eid)
        fresh_row = get_estimate(eid)
        if fresh_row:
            refreshed[eid] = fresh_row
        synced += 1
    return refreshed


def _apply_estimate_row_refreshes(rows: list[dict], refreshed: dict[str, dict]) -> list[dict]:
    if not refreshed:
        return rows
    out: list[dict] = []
    for row in rows:
        eid = str(row.get("id") or "").strip()
        out.append(refreshed[eid] if eid and eid in refreshed else row)
    return out


def _on_estimate_cost_builder_saved(estimate_id: str) -> None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    st.session_state.pop(f"_est_rollups_synced_{eid}", None)
    _refresh_estimate_modal_cache(eid)
    try:
        from app.services.phase2_modules_service import clear_all_data_caches
    except ImportError:
        from services.phase2_modules_service import clear_all_data_caches  # type: ignore
    clear_all_data_caches()
    _clear_cost_builder_options_cache()


def _inventory_options() -> list[tuple[str, dict]]:
    try:
        from app.services.estimate_builder_helpers import inventory_options_as_select
    except ImportError:
        from services.estimate_builder_helpers import inventory_options_as_select  # type: ignore
    return inventory_options_as_select()


def _pricing_guide_options() -> list[tuple[str, dict]]:
    try:
        from app.services.estimate_builder_helpers import pricing_guide_options_as_select
    except ImportError:
        from services.estimate_builder_helpers import pricing_guide_options_as_select  # type: ignore
    return pricing_guide_options_as_select()


def _asset_options() -> list[tuple[str, dict]]:
    try:
        from app.services.estimate_builder_helpers import asset_options_as_select
    except ImportError:
        from services.estimate_builder_helpers import asset_options_as_select  # type: ignore
    return asset_options_as_select()


def _vendor_options() -> list[str]:
    vendors: set[str] = set()
    for item in load_inventory():
        v = str(item.get("vendor") or "").strip()
        if v and v != "—":
            vendors.add(v)
    return sorted(vendors)


def _clear_cost_builder_options_cache() -> None:
    st.session_state.pop(_COST_BUILDER_OPTS_CACHE_KEY, None)


def _cost_builder_option_lists() -> tuple[
    list[tuple[str, dict]],
    list[tuple[str, dict]],
    list[tuple[str, dict]],
    list[str],
]:
    """Load pricing/inventory/asset/vendor picklists once per session (Cost Builder only)."""
    cached = st.session_state.get(_COST_BUILDER_OPTS_CACHE_KEY)
    if isinstance(cached, dict):
        return (
            list(cached.get("pg") or []),
            list(cached.get("inv") or []),
            list(cached.get("asset") or []),
            list(cached.get("vendor") or []),
        )
    opts = {
        "pg": _pricing_guide_options(),
        "inv": _inventory_options(),
        "asset": _asset_options(),
        "vendor": _vendor_options(),
    }
    st.session_state[_COST_BUILDER_OPTS_CACHE_KEY] = opts
    return opts["pg"], opts["inv"], opts["asset"], opts["vendor"]


def _job_select_options(customer_name: str) -> list[tuple[str, str]]:
    cid = customer_id_for_name(customer_name)
    out: list[tuple[str, str]] = [("— None —", "")]
    for job in load_jobs():
        if cid and str(job.get("customer_id") or "") != cid:
            jcust = str(job.get("customer_name") or job.get("customer") or "")
            if jcust != customer_name:
                continue
        label = str(job.get("job_number") or job.get("id") or "")
        proj = str(job.get("project_name") or job.get("job_name") or "")
        if proj:
            label = f"{label} — {proj}"
        out.append((label, str(job.get("id") or "")))
    return out


def _build_mode_key(est: dict) -> str:
    rk = record_session_key(est, "id", "estimate_number")
    return f"{_BUILD_MODE_PREFIX}{rk}"


def _revise_mode_key(est: dict) -> str:
    rk = record_session_key(est, "id", "estimate_number")
    return f"{_REVISE_MODE_PREFIX}{rk}"


def _revise_snapshot_session_key(eid: str) -> str:
    return f"{_REVISE_SNAPSHOT_PREFIX}{eid}"


def _is_in_revise_mode(est: dict) -> bool:
    return bool(st.session_state.get(_revise_mode_key(est)))


def _approved_estimate_editing_locked(est: dict) -> bool:
    return estimate_visible_in_approved_view(est) and not _is_in_revise_mode(est)


def _get_revise_baseline(est: dict) -> dict | None:
    eid = str(est.get("id") or "").strip()
    snap = st.session_state.get(_revise_snapshot_session_key(eid))
    return snap if isinstance(snap, dict) else None


def _enter_revise_mode(est: dict, snapshot: dict) -> None:
    eid = str(est.get("id") or "").strip()
    st.session_state[_revise_mode_key(est)] = True
    st.session_state[_revise_snapshot_session_key(eid)] = snapshot
    rk = record_session_key(est, "id", "estimate_number")
    set_view_mode(_MOD, rk)


def _exit_revise_mode(est: dict) -> None:
    eid = str(est.get("id") or "").strip()
    st.session_state.pop(_revise_mode_key(est), None)
    st.session_state.pop(_revise_snapshot_session_key(eid), None)
    for suffix in ("begin_note", "complete_note", "update_job"):
        st.session_state.pop(f"est_revise_{suffix}_{eid}", None)
    st.session_state.pop(_REVISE_BEGIN_CONFIRM_PREFIX + eid, None)
    st.session_state.pop(_REVISE_COMPLETE_CONFIRM_PREFIX + eid, None)
    st.session_state.pop(_REVISE_CANCEL_CONFIRM_PREFIX + eid, None)


def _set_estimate_build_mode(est: dict) -> None:
    if _approved_estimate_editing_locked(est):
        return
    st.session_state[_build_mode_key(est)] = True
    rk = record_session_key(est, "id", "estimate_number")
    set_view_mode(_MOD, rk)


def _persist_estimate_partial(data: dict, row_id: str) -> tuple[bool, str]:
    """Merge tab saves without clearing scope, notes, or project fields."""
    est = get_estimate(row_id) or {}
    proj = str(est.get("project_name") or "").strip()
    if proj == "—":
        proj = ""
    ok, msg = persist_estimate(
        {
            "estimate_number": est.get("estimate_number"),
            "project_name": proj,
            "customer": est.get("customer"),
            "customer_id": est.get("customer_id") or customer_id_for_name(str(est.get("customer") or "")),
            **data,
        },
        row_id=row_id,
    )
    return ok, msg



def _persist_scope_of_work(data: dict, row_id: str) -> tuple[bool, str]:
    """Persist scope fields via dedicated patch (also mirrors into estimate_json)."""
    est = get_estimate(row_id) or {"id": row_id}
    try:
        from app.estimate.persistence import patch_estimate_job_scope
        from app.services.repository import clear_all_data_caches
    except ImportError:
        from estimate.persistence import patch_estimate_job_scope  # type: ignore
        from services.repository import clear_all_data_caches  # type: ignore
    ok, err = patch_estimate_job_scope(
        row_id,
        est,
        scope_of_work=str(data.get("scope_of_work") or ""),
        customer_responsibilities=str(data.get("customer_responsibilities") or ""),
    )
    if ok:
        clear_all_data_caches()
        return True, "Scope of work saved."
    return False, err or "Could not save scope of work."


def _on_estimate_scope_saved(eid: str) -> None:
    _refresh_estimate_modal_cache(eid)
    st.session_state.pop(f"est_sow_seeded_{eid}", None)


def _estimate_status_pill_html(status: str) -> str:
    cls_map = {
        "Draft": "ips-estimate-status-draft",
        "Pending": "ips-estimate-status-pending",
        "Sent": "ips-estimate-status-sent",
        "Approved": "ips-estimate-status-approved",
        "Awarded": "ips-estimate-status-awarded",
        "Rejected": "ips-estimate-status-rejected",
        "Expired": "ips-estimate-status-expired",
        "Cancelled": "ips-estimate-status-cancelled",
    }
    cls = cls_map.get(status, "ips-estimate-status-draft")
    return f'<span class="ips-estimate-status-pill {cls}">{html.escape(status)}</span>'


_ESTIMATE_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("customer", _estimate_customer),
    ("status", lambda r: _normalize_estimate_status(r.get("status"))),
]
_ESTIMATES_DEFAULT_VIEW = "Active Estimates"
_ESTIMATES_VIEW_OPTIONS = [
    "Active Estimates",
    "All Estimates",
    "Draft Estimates",
    "Sent Estimates",
    "Approved Estimates",
    "Rejected / Lost Estimates",
    "Archived Estimates",
]
_ESTIMATE_BAR_FILTER_FIELDS = ["customer", "status"]


def _estimate_select_key(estimate_id: str) -> str:
    return f"estimate_select_{estimate_id}"


def _clear_estimate_selection(estimate_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_ESTIMATE_KEY] = None
    st.session_state[SHOW_ESTIMATE_MODAL_KEY] = False
    ids = list(estimate_ids or [])
    for eid in ids:
        st.session_state[_estimate_select_key(eid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("estimate_select_"):
            st.session_state[key] = False


def _on_estimate_checkbox_change(estimate_id: str, all_estimate_ids: list[str]) -> None:
    key = _estimate_select_key(estimate_id)
    if st.session_state.get(key):
        for eid in all_estimate_ids:
            if eid != estimate_id:
                st.session_state[_estimate_select_key(eid)] = False
        st.session_state[SELECTED_ESTIMATE_KEY] = estimate_id
        st.session_state[SHOW_ESTIMATE_MODAL_KEY] = True
        cache = st.session_state.get(_ESTIMATES_CACHE_KEY) or {}
        estimate = cache.get(estimate_id) if isinstance(cache, dict) else None
        _open_estimates_detail_modal(estimate_id, estimate)
    elif st.session_state.get(SELECTED_ESTIMATE_KEY) == estimate_id:
        st.session_state[SELECTED_ESTIMATE_KEY] = None
        st.session_state[SHOW_ESTIMATE_MODAL_KEY] = False


def _render_custom_estimates_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No estimates match your filters.")
        st.session_state[_ALL_ESTIMATE_IDS_KEY] = []
        return []

    all_estimate_ids = [
        str(e.get("id") or "").strip() for e in filtered if str(e.get("id") or "").strip()
    ]
    st.session_state[_ALL_ESTIMATE_IDS_KEY] = all_estimate_ids

    with st.container(key="estimates_table_wrap"):
        st.markdown('<div class="ips-estimates-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_ESTIMATE_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _ESTIMATE_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-estimates-header-row ips-estimates-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-estimates-header-row ips-estimates-cell",
                    )

        for est in filtered:
            eid = str(est.get("id") or "").strip()
            if not eid:
                continue

            est_no = _estimate_number(est)
            project = _estimate_project(est)
            customer = _estimate_customer(est)
            status = _normalize_estimate_status(est.get("status"))
            est_date = fmt_date(est.get("estimate_date"))
            job_no = _estimate_job(est)
            total = _estimate_customer_price(est)

            cols = st.columns(_ESTIMATE_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_estimate_select_key(eid),
                    label_visibility="collapsed",
                    on_change=_on_estimate_checkbox_change,
                    args=(eid, all_estimate_ids),
                )

            with cols[1]:
                st.markdown(
                    f'<div class="ips-estimates-number">{html.escape(est_no)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<div class="ips-estimates-title">{html.escape(project)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-estimates-cell">{html.escape(customer)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-muted">{html.escape(job_no)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(_estimate_status_pill_html(status), unsafe_allow_html=True)

            with cols[6]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-muted">{html.escape(est_date)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[7]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-number">{html.escape(total)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[8]:
                if _can_show_approve_job(est):
                    if st.button(
                        "Approve Job",
                        key=f"est_row_approve_{eid}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        st.session_state[_PENDING_APPROVE_KEY] = eid
                        st.rerun()
                elif estimate_visible_in_approved_view(est):
                    st.markdown(
                        '<span class="ips-est-approve-done">Job Approved</span>',
                        unsafe_allow_html=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    return all_estimate_ids


def _contact_label_for_estimate(est: dict) -> str:
    ccid = str(est.get("customer_contact_id") or "").strip()
    if not ccid:
        return "—"
    cid = customer_id_for_name(str(est.get("customer") or ""))
    for label, contact_id in customer_contact_select_options(cid):
        if contact_id == ccid:
            return label
    return "—"


def _customer_location_select(
    *,
    customer_name: str,
    session_key: str,
    prev_customer_key: str,
    initial_location_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust

    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox("Location", ["— Select customer first —"], disabled=True, key=session_key)
        return ""

    pairs = customer_location_select_options(cid)
    if not pairs:
        st.warning("Add a customer location before assigning contacts/jobs.")
        st.selectbox("Location", ["— No locations —"], disabled=True, key=session_key)
        return ""

    labels = ["— Select location —", *[label for label, _ in pairs]]
    ids = ["", *[loc_id for _, loc_id in pairs]]
    if session_key not in st.session_state and initial_location_id:
        try:
            st.session_state[session_key] = ids.index(initial_location_id)
        except ValueError:
            st.session_state[session_key] = 0
    idx = st.selectbox(
        "Location",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=session_key,
    )
    return str(ids[int(idx)])


def _customer_contact_select(
    *,
    customer_name: str,
    location_id: str,
    session_key: str,
    prev_customer_key: str,
    prev_location_key: str,
    initial_contact_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    loc_id = str(location_id or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust
    if st.session_state.get(prev_location_key) != loc_id:
        st.session_state.pop(session_key, None)
        st.session_state[prev_location_key] = loc_id

    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox("Contact", ["— Select customer first —"], disabled=True, key=session_key)
        return ""
    if not loc_id:
        st.selectbox("Contact", ["— Select location first —"], disabled=True, key=session_key)
        return ""

    pairs = customer_contact_select_options(cid, loc_id)
    if not pairs:
        st.selectbox("Contact", ["— No contacts for this location —"], disabled=True, key=session_key)
        return ""

    labels = ["— Select contact —", *[label for label, _ in pairs]]
    ids = ["", *[contact_id for _, contact_id in pairs]]

    if session_key not in st.session_state and initial_contact_id:
        try:
            st.session_state[session_key] = ids.index(initial_contact_id)
        except ValueError:
            st.session_state[session_key] = 0

    idx = st.selectbox(
        "Contact",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=session_key,
    )
    return str(ids[int(idx)])


def _apply_estimate_view_filter(rows: list[dict], view_filter: str) -> list[dict]:
    vf = str(view_filter or _ESTIMATES_DEFAULT_VIEW).strip()
    if vf in {"Approved / Converted", "Approved Estimates"}:
        return [r for r in rows if estimate_visible_in_approved_view(r)]
    if vf in {"Rejected", "Rejected / Lost Estimates"}:
        return [r for r in rows if estimate_visible_in_rejected_view(r)]
    if vf == "All Estimates":
        return rows
    if vf == "Draft Estimates":
        return [r for r in rows if estimate_visible_in_draft_view(r)]
    if vf == "Sent Estimates":
        return [r for r in rows if estimate_visible_in_sent_view(r)]
    if vf == "Archived Estimates":
        return [r for r in rows if estimate_visible_in_archived_view(r)]
    return [r for r in rows if estimate_visible_in_active_view(r)]


def _can_revise_approved_estimate() -> bool:
    return can_revise_approved_estimates(current_role())


def _estimates_summary_counts(rows: list[dict]) -> dict[str, float | int | bool]:
    counts: dict[str, float | int | bool] = {
        "total": len(rows),
        "active": 0,
        "draft": 0,
        "sent": 0,
        "approved": 0,
        "total_customer_value": 0.0,
        "has_any_value": False,
    }
    for row in rows:
        if estimate_visible_in_active_view(row):
            counts["active"] += 1
        if estimate_visible_in_draft_view(row):
            counts["draft"] += 1
        if estimate_visible_in_sent_view(row):
            counts["sent"] += 1
        if estimate_visible_in_approved_view(row):
            counts["approved"] += 1
        amount = _estimate_customer_price_amount(row)
        if amount > 0:
            counts["has_any_value"] = True
            counts["total_customer_value"] = float(counts["total_customer_value"]) + amount
    return counts


def _can_show_approve_job(est: dict) -> bool:
    if not can_approve_estimates(current_role()):
        return False
    eid = str(est.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return False
    return estimate_status_approvable(est.get("status")) and not estimate_visible_in_approved_view(est)


def _render_approve_confirmation_panel(rows_by_id: dict[str, dict]) -> None:
    eid = str(st.session_state.get(_PENDING_APPROVE_KEY) or "").strip()
    if not eid:
        return
    est = rows_by_id.get(eid)
    if not est:
        st.session_state.pop(_PENDING_APPROVE_KEY, None)
        return

    st.markdown('<div class="ips-est-approve-panel">', unsafe_allow_html=True)
    st.markdown("**Approve this estimate and activate the linked job?**")
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.caption("Estimate #")
        st.write(_estimate_number(est))
    with c2:
        st.caption("Project")
        st.write(_estimate_project(est))
    with c3:
        st.caption("Customer")
        st.write(_estimate_customer(est))
    with c4:
        st.caption("Total")
        st.write(_estimate_customer_price(est))
    st.caption(f"Linked job: **{_estimate_job(est)}**")
    b1, b2, _ = st.columns([1, 1, 3], gap="small")
    with b1:
        if st.button("Approve Job", key=f"est_confirm_approve_{eid}", type="primary", use_container_width=True):
            res = approve_estimate_and_sync_job(eid)
            if res.ok:
                try:
                    from app.services.phase2_modules_service import clear_all_data_caches
                except ImportError:
                    from services.phase2_modules_service import clear_all_data_caches  # type: ignore
                clear_all_data_caches()
                st.session_state.pop(_PENDING_APPROVE_KEY, None)
                st.success(res.message or "Estimate approved and linked job activated.")
                st.rerun()
            st.error(res.message or "Could not approve estimate.")
    with b2:
        if st.button("Cancel", key=f"est_confirm_cancel_{eid}", use_container_width=True):
            st.session_state.pop(_PENDING_APPROVE_KEY, None)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _filter_rows(
    rows: list[dict],
    *,
    q: str,
    date_range: tuple[date, date] | None,
    view_filter: str,
) -> list[dict]:
    out = _apply_estimate_view_filter(rows, view_filter)
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in _estimate_number(r).lower()
            or ql in _estimate_project(r).lower()
            or ql in _estimate_customer(r).lower()
            or ql in _estimate_created_by(r).lower()
            or ql in _normalize_estimate_status(r.get("status")).lower()
        ]
    if date_range and len(date_range) == 2:
        start, end = date_range
        filtered_range: list[dict] = []
        for row in out:
            est_date = _as_date(row.get("estimate_date"))
            if est_date is None or (start <= est_date <= end):
                filtered_range.append(row)
        out = filtered_range
    return apply_column_filters(out, _TABLE_KEY, _ESTIMATE_COLUMN_FILTER_SPECS)


def _clear_estimates_detail_modal() -> None:
    estimate_ids = st.session_state.get(_ALL_ESTIMATE_IDS_KEY) or []
    _clear_estimate_selection([str(eid) for eid in estimate_ids])
    clear_edit_modes(_MOD)
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_ESTIMATES_MODAL_KEY,
        module=_MOD,
    )


def _open_estimates_detail_modal(estimate_id: str, estimate: dict | None = None) -> None:
    open_record_modal(
        estimate_id,
        estimate,
        session_select_key=_SEL,
        modal_key=_ESTIMATES_MODAL_KEY,
        module=_MOD,
        id_fields=("id", "estimate_number"),
    )
    if estimate:
        st.session_state[ACTIVE_ESTIMATE_KEY] = str(estimate.get("id") or "")


def _refresh_estimate_modal_cache(estimate_id: str) -> None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    fresh = get_estimate(eid)
    if not fresh:
        return
    cache = st.session_state.get(_ESTIMATES_CACHE_KEY)
    if isinstance(cache, dict):
        cache = dict(cache)
        cache[eid] = fresh
        st.session_state[_ESTIMATES_CACHE_KEY] = cache


def _estimate_expiration_display(est: dict) -> str:
    return format_effective_expiration(est)


def _mark_edit_expiration_manual(eid: str) -> None:
    st.session_state[f"est_edit_exp_manual_{eid}"] = True


def _mark_new_expiration_manual() -> None:
    st.session_state["est_new_exp_manual"] = True


def _sync_edit_expiration_from_estimate_date(eid: str) -> None:
    est_key = f"est_edit_est_date_{eid}"
    exp_key = f"est_edit_exp_date_{eid}"
    manual_key = f"est_edit_exp_manual_{eid}"
    prev_key = f"est_edit_est_date_prev_{eid}"
    est_d = st.session_state.get(est_key)
    if not isinstance(est_d, date):
        est_d = _as_date(est_d)
    prev = st.session_state.get(prev_key)
    if isinstance(prev, str):
        prev = _as_date(prev)
    if est_d and est_d != prev and not st.session_state.get(manual_key):
        default_exp = default_expiration_date(est_d)
        if default_exp:
            st.session_state[exp_key] = default_exp
    if est_d:
        st.session_state[prev_key] = est_d


def _sync_new_expiration_from_estimate_date() -> None:
    est_d = st.session_state.get("est_new_est_date")
    if not isinstance(est_d, date):
        est_d = _as_date(est_d)
    prev = st.session_state.get("est_new_est_date_prev")
    if isinstance(prev, str):
        prev = _as_date(prev)
    if est_d and est_d != prev and not st.session_state.get("est_new_exp_manual"):
        default_exp = default_expiration_date(est_d)
        if default_exp:
            st.session_state["est_new_exp_date"] = default_exp
    if est_d:
        st.session_state["est_new_est_date_prev"] = est_d


def _seed_estimate_edit_form(est: dict) -> None:
    eid = str(est.get("id") or "")
    st.session_state[f"est_edit_num_{eid}"] = str(est.get("estimate_number") or "")
    proj = _estimate_project(est)
    st.session_state[f"est_edit_proj_{eid}"] = "" if proj == "—" else proj
    st.session_state[f"est_edit_cust_{eid}"] = str(est.get("customer") or "")
    st.session_state[f"est_edit_status_{eid}"] = str(est.get("status") or "Draft")
    st.session_state[f"est_edit_notes_{eid}"] = str(est.get("notes") or "")
    st.session_state.pop(f"est_sow_seeded_{eid}", None)
    est_d = _as_date(est.get("estimate_date")) or date.today()
    exp_d = effective_expiration_date(est) or default_expiration_date(est_d) or (date.today() + timedelta(days=30))
    st.session_state[f"est_edit_est_date_{eid}"] = est_d
    st.session_state[f"est_edit_exp_date_{eid}"] = exp_d
    st.session_state[f"est_edit_exp_manual_{eid}"] = bool(est.get("expiration_manual_override"))
    st.session_state[f"est_edit_est_date_prev_{eid}"] = est_d
    st.session_state.pop(f"est_edit_contact_{eid}", None)
    st.session_state.pop(f"est_edit_location_{eid}", None)
    st.session_state.pop(f"est_edit_job_{eid}", None)
    st.session_state.pop(f"est_edit_cust_prev_{eid}", None)
    st.session_state.pop(f"est_edit_loc_prev_{eid}", None)


def _set_estimate_view_mode(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    set_view_mode(_MOD, rk)


def _set_estimate_edit_mode(est: dict) -> None:
    if _approved_estimate_editing_locked(est):
        return
    rk = record_session_key(est, "id", "estimate_number")
    set_edit_mode(_MOD, rk)
    _seed_estimate_edit_form(est)


def _render_estimate_edit_form(est: dict) -> None:
    eid = str(est.get("id") or "")
    rk = record_session_key(est, "id", "estimate_number")
    if f"est_edit_num_{eid}" not in st.session_state:
        _seed_estimate_edit_form(est)

    render_edit_form_header("Edit Estimate")

    if is_demo_id(eid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    _sync_edit_expiration_from_estimate_date(eid)

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Estimate #", key=f"est_edit_num_{eid}")
        st.text_input("Project", key=f"est_edit_proj_{eid}")
        st.selectbox(
            "Customer",
            customer_filter_options(include_names={str(est.get("customer") or "")}),
            key=f"est_edit_cust_{eid}",
        )
        cust_name = str(st.session_state.get(f"est_edit_cust_{eid}") or est.get("customer") or "")
        location_id = _customer_location_select(
            customer_name=cust_name,
            session_key=f"est_edit_location_{eid}",
            prev_customer_key=f"est_edit_cust_prev_{eid}",
            initial_location_id=str(est.get("customer_location_id") or ""),
        )
        contact_id = _customer_contact_select(
            customer_name=cust_name,
            location_id=location_id,
            session_key=f"est_edit_contact_{eid}",
            prev_customer_key=f"est_edit_cust_prev_{eid}",
            prev_location_key=f"est_edit_loc_prev_{eid}",
            initial_contact_id=str(est.get("customer_contact_id") or ""),
        )
        st.selectbox("Status", lookup_options("estimate_statuses"), key=f"est_edit_status_{eid}", disabled=_is_in_revise_mode(est))
        st.date_input("Estimate date", key=f"est_edit_est_date_{eid}")
        st.date_input(
            "Expiration date",
            key=f"est_edit_exp_date_{eid}",
            on_change=_mark_edit_expiration_manual,
            args=(eid,),
        )
        if st.session_state.get(f"est_edit_exp_manual_{eid}"):
            if st.button("Reset expiration to estimate date + 30 days", key=f"est_edit_exp_reset_{eid}"):
                st.session_state[f"est_edit_exp_manual_{eid}"] = False
                est_d = st.session_state.get(f"est_edit_est_date_{eid}")
                if not isinstance(est_d, date):
                    est_d = _as_date(est_d)
                default_exp = default_expiration_date(est_d) if est_d else None
                if default_exp:
                    st.session_state[f"est_edit_exp_date_{eid}"] = default_exp
                st.rerun()
        else:
            st.caption("Expiration follows estimate date + 30 days until you change it.")
    with ec2:
        job_opts = _job_select_options(cust_name)
        job_labels = [label for label, _ in job_opts]
        job_ids = [jid for _, jid in job_opts]
        cur_job = str(est.get("job_id") or "")
        if f"est_edit_job_{eid}" not in st.session_state and cur_job in job_ids:
            st.session_state[f"est_edit_job_{eid}"] = job_ids.index(cur_job)
        elif f"est_edit_job_{eid}" not in st.session_state:
            st.session_state[f"est_edit_job_{eid}"] = 0
        st.selectbox(
            "Linked job (optional)",
            range(len(job_labels)),
            format_func=lambda i: job_labels[i],
            key=f"est_edit_job_{eid}",
        )
    st.caption("Use the **Scope of Work** tab for long-form scope text.")
    st.text_area("Notes", key=f"est_edit_notes_{eid}", height=70)

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"est_edit_cancel_{eid}",
        save_key=f"est_edit_save_{eid}",
    )
    if cancelled:
        st.rerun()
    if saved:
        cust_name = str(st.session_state.get(f"est_edit_cust_{eid}") or "")
        job_opts = _job_select_options(cust_name)
        job_idx = int(st.session_state.get(f"est_edit_job_{eid}") or 0)
        job_id = job_opts[job_idx][1] if job_opts else ""
        status_val = st.session_state.get(f"est_edit_status_{eid}")
        if _is_in_revise_mode(est):
            status_val = est.get("status") or "Approved"
        ok, msg = persist_estimate(
            {
                "estimate_number": st.session_state.get(f"est_edit_num_{eid}"),
                "project_name": str(st.session_state.get(f"est_edit_proj_{eid}") or "").strip(),
                "customer": cust_name,
                "customer_id": customer_id_for_name(cust_name) or None,
                "customer_location_id": location_id or None,
                "customer_contact_id": contact_id or None,
                "job_id": job_id or None,
                "status": status_val,
                "estimate_date": str(st.session_state.get(f"est_edit_est_date_{eid}")),
                "expiration_date": str(st.session_state.get(f"est_edit_exp_date_{eid}")),
                "expiration_manual_override": bool(st.session_state.get(f"est_edit_exp_manual_{eid}")),
                "notes": st.session_state.get(f"est_edit_notes_{eid}"),
            },
            row_id=eid,
        )
        if ok:
            _refresh_estimate_modal_cache(eid)
            set_view_mode(_MOD, rk)
            st.success(msg or "Estimate saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save estimate.")


def _render_estimate_detail_tabs(est: dict) -> None:
    eid = str(est.get("id") or "")
    en = safe_value(est.get("estimate_number"))
    status = safe_value(est.get("status"))
    customer = safe_value(est.get("customer"))

    if st.session_state.get(_build_mode_key(est)):
        st.info("Build mode — add lines and review totals in Cost Builder.")

    editing_locked = _approved_estimate_editing_locked(est)

    (
        tab_overview,
        tab_scope,
        tab_cost_builder,
        tab_markups,
        tab_summary,
        tab_proposal,
        tab_attachments,
        tab_notes,
        tab_activity,
    ) = st.tabs(_ESTIMATE_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Estimate #', en)}"
            f"{detail_field_html('Project', _estimate_project(est))}"
            f"{detail_field_html('Customer', customer)}"
            f"{detail_field_html('Contact', _contact_label_for_estimate(est))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"{detail_field_html('Estimate date', format_estimate_date(est))}"
            f"{detail_field_html('Expiration', _estimate_expiration_display(est))}"
            f"{detail_field_html('Linked Job', est.get('job_number'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Estimate Summary", overview_html), unsafe_allow_html=True)

        try:
            from app.services.estimate_costing_service import calculate_estimate_totals
        except ImportError:
            from services.estimate_costing_service import calculate_estimate_totals  # type: ignore
        overview_totals = (
            calculate_estimate_totals(eid) if eid and not is_demo_id(eid) else {}
        )
        margin_pct = f"{float(overview_totals.get('gross_margin_percent') or est.get('gross_margin_percent') or 0):.1f}%"
        fin_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Total cost', fmt_currency(overview_totals.get('total_cost') or est.get('total_cost') or est.get('subtotal')))}"
            f"{detail_field_html('Customer price', fmt_currency(overview_totals.get('customer_price') or _estimate_stored_customer_price(est)))}"
            f"{detail_field_html('Tax', fmt_currency(overview_totals.get('tax_amount') or est.get('tax')))}"
            f"{detail_field_html('Gross profit', fmt_currency(overview_totals.get('gross_profit') or est.get('gross_profit')))}"
            f"{detail_field_html('Margin %', margin_pct)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Financial Summary", fin_html), unsafe_allow_html=True)
        st.caption("Open the **Scope of Work** tab to view or edit the full project scope.")

    with tab_scope:
        if editing_locked:
            placeholder_html("This estimate is approved. Use **Revise Approved Estimate** to edit scope.")
        elif eid and not is_demo_id(eid):
            render_scope_of_work_tab(
                est,
                persist_fn=_persist_scope_of_work,
                on_saved=lambda: _on_estimate_scope_saved(eid),
            )
        else:
            placeholder_html("Save this estimate to edit scope of work.")

    with tab_cost_builder:
        if editing_locked:
            placeholder_html("This estimate is approved. Use **Revise Approved Estimate** to adjust pricing lines.")
        elif eid and not is_demo_id(eid):
            _sync_estimate_rollups_if_stale(eid)
            fresh = get_estimate(eid)
            if fresh:
                est = fresh
            pg_opts, inv_opts, asset_opts, vendor_opts = _cost_builder_option_lists()
            render_cost_builder_tab(
                est,
                pricing_guide_options=pg_opts,
                inventory_options=inv_opts,
                asset_options=asset_opts,
                vendor_options=vendor_opts,
                on_saved=lambda: _on_estimate_cost_builder_saved(eid),
            )

    with tab_markups:
        if editing_locked:
            placeholder_html("This estimate is approved. Use **Revise Approved Estimate** to change markups.")
        else:
            render_markups_tab(est)

    with tab_summary:
        render_summary_tab(est)

    with tab_proposal:
        render_proposal_preview_tab(est)

    with tab_attachments:
        placeholder_html("Estimate attachments will appear here when connected to document storage.")

    with tab_notes:
        notes_text = safe_value(est.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Estimate activity history will appear here when connected to Supabase.")


def _render_estimate_revision_panel(est: dict) -> None:
    """Explicit approved-estimate revision workflow (protects linked job contract until applied)."""
    eid = str(est.get("id") or "").strip()
    if not eid or is_demo_id(eid) or not estimate_visible_in_approved_view(est):
        return
    if not _can_revise_approved_estimate():
        st.caption("This estimate is approved. Contact an administrator or estimator if changes are needed.")
        return

    baseline = _get_revise_baseline(est)
    in_revise = _is_in_revise_mode(est)
    rev_no = int(est.get("revision_number") or 1)

    if in_revise and baseline:
        approved_price = _safe_float_revision(baseline.get("approved_customer_price"))
        current_price = _estimate_customer_price_amount(est)
        job_awarded = _safe_float_revision((baseline.get("job") or {}).get("awarded_amount"))
        st.markdown(
            f'<div class="ips-est-revision-banner">'
            f"<strong>Revision in progress</strong> — approved Rev {rev_no} values are protected. "
            f"Approved customer price: <strong>{html.escape(fmt_currency(approved_price))}</strong>"
            f"{f' · Linked job contract: <strong>{html.escape(fmt_currency(job_awarded))}</strong>' if job_awarded > 0 else ''}"
            f"{f' · Current working total: <strong>{html.escape(fmt_currency(current_price))}</strong>' if abs(current_price - approved_price) > 0.01 else ''}"
            f"</div>",
            unsafe_allow_html=True,
        )

        if st.session_state.get(_REVISE_COMPLETE_CONFIRM_PREFIX + eid):
            st.markdown("**Complete this revision?**")
            st.caption(
                "Saving records a new revision snapshot. The linked job contract stays unchanged unless you opt in below."
            )
            st.text_area(
                "Completion note",
                key=f"est_revise_complete_note_{eid}",
                placeholder="What changed and why…",
                height=70,
            )
            st.checkbox(
                "Update linked job contract value to the new customer price",
                key=f"est_revise_update_job_{eid}",
            )
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("Confirm Complete Revision", key=f"est_revise_complete_ok_{eid}", type="primary", use_container_width=True):
                    note = str(st.session_state.get(f"est_revise_complete_note_{eid}") or "").strip()
                    update_job = bool(st.session_state.get(f"est_revise_update_job_{eid}"))
                    result = complete_approved_estimate_revision(
                        eid,
                        note=note,
                        update_job_contract=update_job,
                    )
                    if result.ok:
                        try:
                            from app.services.phase2_modules_service import clear_all_data_caches
                        except ImportError:
                            from services.phase2_modules_service import clear_all_data_caches  # type: ignore
                        clear_all_data_caches()
                        _refresh_estimate_modal_cache(eid)
                        _exit_revise_mode(est)
                        msg = "Revision completed."
                        if result.error:
                            msg = f"{msg} {result.error}"
                        st.success(msg)
                        st.rerun()
                    st.error(result.error or "Could not complete revision.")
            with c2:
                if st.button("Back", key=f"est_revise_complete_back_{eid}", use_container_width=True):
                    st.session_state.pop(_REVISE_COMPLETE_CONFIRM_PREFIX + eid, None)
                    st.rerun()
            return

        if st.session_state.get(_REVISE_CANCEL_CONFIRM_PREFIX + eid):
            st.warning(
                "Cancel revision? Approved estimate totals on this record will be restored. "
                "Cost Builder line edits are not automatically reverted."
            )
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("Confirm Cancel Revision", key=f"est_revise_cancel_ok_{eid}", use_container_width=True):
                    result = cancel_approved_estimate_revision(eid, baseline_snapshot=baseline)
                    if result.ok:
                        try:
                            from app.services.phase2_modules_service import clear_all_data_caches
                        except ImportError:
                            from services.phase2_modules_service import clear_all_data_caches  # type: ignore
                        clear_all_data_caches()
                        _refresh_estimate_modal_cache(eid)
                        _exit_revise_mode(est)
                        st.info("Revision cancelled. Linked job contract was not changed.")
                        st.rerun()
                    st.error(result.error or "Could not cancel revision.")
            with c2:
                if st.button("Keep revising", key=f"est_revise_cancel_back_{eid}", use_container_width=True):
                    st.session_state.pop(_REVISE_CANCEL_CONFIRM_PREFIX + eid, None)
                    st.rerun()
            return

        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("Complete Revision", key=f"est_revise_complete_open_{eid}", type="primary", use_container_width=True):
                st.session_state[_REVISE_COMPLETE_CONFIRM_PREFIX + eid] = True
                st.rerun()
        with c2:
            if st.button("Cancel Revision", key=f"est_revise_cancel_open_{eid}", use_container_width=True):
                st.session_state[_REVISE_CANCEL_CONFIRM_PREFIX + eid] = True
                st.rerun()
        return

    st.caption(
        "This estimate is approved and locked. Start an explicit revision to adjust pricing or details. "
        "The linked job contract value stays pinned until you complete the revision and choose to update it."
    )

    if st.session_state.get(_REVISE_BEGIN_CONFIRM_PREFIX + eid):
        st.markdown("**Start revising this approved estimate?**")
        st.caption(
            "A snapshot of the approved estimate and linked job contract will be saved before any edits."
        )
        st.text_area(
            "Revision reason",
            key=f"est_revise_begin_note_{eid}",
            placeholder="Describe why this approved estimate needs to change…",
            height=70,
        )
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("Start Revision", key=f"est_revise_begin_ok_{eid}", type="primary", use_container_width=True):
                note = str(st.session_state.get(f"est_revise_begin_note_{eid}") or "").strip()
                result = begin_approved_estimate_revision(eid, note=note)
                if result.ok and isinstance(result.data, dict):
                    snapshot = result.data.get("snapshot")
                    if isinstance(snapshot, dict):
                        _enter_revise_mode(est, snapshot)
                        st.session_state.pop(_REVISE_BEGIN_CONFIRM_PREFIX + eid, None)
                        st.success("Revision started. You can now edit this estimate.")
                        st.rerun()
                st.error(result.error or "Could not start revision.")
        with c2:
            if st.button("Back", key=f"est_revise_begin_back_{eid}", use_container_width=True):
                st.session_state.pop(_REVISE_BEGIN_CONFIRM_PREFIX + eid, None)
                st.rerun()
        return

    if st.button("Revise Approved Estimate", key=f"est_revise_open_{eid}", type="primary", use_container_width=False):
        st.session_state[_REVISE_BEGIN_CONFIRM_PREFIX + eid] = True
        st.rerun()


def _safe_float_revision(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _render_estimate_actions_panel(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    if is_edit_mode(_MOD, rk):
        return
    eid = str(est.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return

    def _after_action() -> None:
        _clear_estimates_detail_modal()

    _render_estimate_revision_panel(est)
    render_estimate_action_buttons(est, on_approve=_after_action, on_delete=_after_action)


def render_estimate_detail_dialog(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    eid = str(est.get("id") or "")
    if eid and not is_demo_id(eid):
        ensure_estimate_expiration_persisted(eid)
    if eid and not is_demo_id(eid) and _estimate_rollups_are_stale(est):
        _sync_estimate_rollups_if_stale(eid)
    fresh = get_estimate(eid) if eid else None
    if fresh:
        est = fresh
    en = safe_value(est.get("estimate_number"))
    project = _estimate_project(est)
    status = safe_value(est.get("status"))
    customer = safe_value(est.get("customer"))
    total = _estimate_customer_price(est)
    linked_job = str(est.get("job_id") or est.get("job_number") or "").strip()

    render_modal_shell()
    render_modal_header(title=en, subtitle=project, status=status)

    editing_locked = _approved_estimate_editing_locked(est)
    if editing_locked:
        st.caption("Approved estimate — locked until you start a revision.")
    else:
        btn1, btn2 = st.columns(2, gap="small")
        with btn1:
            if st.button("Edit", key=f"estimates_modal_edit_{rk}", use_container_width=True):
                _set_estimate_edit_mode(est)
                st.rerun()
        with btn2:
            label = "Build Estimate" if not _is_in_revise_mode(est) else "Open Cost Builder"
            if st.button(label, key=f"estimates_modal_build_{rk}", use_container_width=True):
                _set_estimate_build_mode(est)
                st.rerun()

    render_modal_meta_grid(
        [
            ("Customer", customer),
            ("Total", total),
            ("Status", status),
            ("Linked Job", safe_value(est.get("job_number"))),
        ]
    )

    if is_edit_mode(_MOD, rk):
        _render_estimate_edit_form(est)
    else:
        _render_estimate_actions_panel(est)
        _render_estimate_detail_tabs(est)


@st.dialog("Estimate Details", width="large", on_dismiss=_clear_estimates_detail_modal)
def _show_estimates_detail_modal() -> None:
    sel = str(st.session_state.get(_ESTIMATES_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
    est = get_estimate(sel) if sel else None
    if not est:
        est = get_modal_record(
            cache_key=_ESTIMATES_CACHE_KEY,
            modal_key=_ESTIMATES_MODAL_KEY,
            session_select_key=_SEL,
        )
    if not est:
        render_missing_record(_clear_estimates_detail_modal, close_key="estimates_modal_missing_close")
        return
    st.session_state[ACTIVE_ESTIMATE_KEY] = str(est.get("id") or "")
    render_estimate_detail_dialog(est)


@st.dialog("New Estimate", width="large")
def _show_new_estimate_dialog() -> None:
    clear_new_estimate_number_state()
    if "est_new_est_date" not in st.session_state:
        st.session_state["est_new_est_date"] = date.today()
    if "est_new_exp_manual" not in st.session_state:
        st.session_state["est_new_exp_manual"] = False
    if "est_new_exp_date" not in st.session_state:
        st.session_state["est_new_exp_date"] = default_expiration_date(st.session_state["est_new_est_date"])
    if "est_new_est_date_prev" not in st.session_state:
        st.session_state["est_new_est_date_prev"] = st.session_state["est_new_est_date"]

    _sync_new_expiration_from_estimate_date()

    customers = customer_filter_options()
    nc1, nc2 = st.columns(2)
    with nc2:
        st.date_input("Estimate date", key="est_new_est_date")
        st.date_input(
            "Expiration date",
            key="est_new_exp_date",
            on_change=_mark_new_expiration_manual,
        )
        if st.session_state.get("est_new_exp_manual"):
            if st.button("Reset expiration to estimate date + 30 days", key="est_new_exp_reset"):
                st.session_state["est_new_exp_manual"] = False
                est_d = st.session_state.get("est_new_est_date")
                if not isinstance(est_d, date):
                    est_d = _as_date(est_d)
                default_exp = default_expiration_date(est_d) if est_d else None
                if default_exp:
                    st.session_state["est_new_exp_date"] = default_exp
                st.rerun()
        else:
            st.caption("Expiration follows estimate date + 30 days until you change it.")
        st.selectbox("Status", lookup_options("estimate_statuses"), index=0, key="est_new_status")
        st.caption("A linked job in **Active** status is created automatically when you save.")
    with nc1:
        sync_new_estimate_number()
        st.text_input(
            "Estimate #",
            key="est_new_num",
            on_change=_est_new_num_edited,
        )
        linked_job_no = linked_job_number_preview(str(st.session_state.get("est_new_num") or ""))
        st.text_input("Linked Job #", value=linked_job_no, disabled=True)
        st.text_input("Project name", key="est_new_proj")
        st.selectbox("Customer", customers, key="est_new_cust")
        new_cust = str(st.session_state.get("est_new_cust") or "")
        new_location_id = _customer_location_select(
            customer_name=new_cust,
            session_key="est_new_location",
            prev_customer_key=_NEW_CUST_PREV,
        )
        new_contact_id = _customer_contact_select(
            customer_name=new_cust,
            location_id=new_location_id,
            session_key="est_new_contact",
            prev_customer_key=_NEW_CUST_PREV,
            prev_location_key="est_new_loc_prev",
        )
    st.text_area(
        "Scope of Work",
        key="est_new_sow",
        height=120,
        placeholder="Full scope for this estimate (optional — can edit later in Scope of Work tab).",
    )
    st.text_area("Notes", key="est_new_notes", height=60)

    sb1, sb2 = st.columns(2)
    with sb1:
        if st.button("Save Draft", key="est_save_new", type="primary", use_container_width=True):
            quote_num = str(st.session_state.get("est_new_num") or "").strip()
            ok, msg = persist_estimate(
                {
                    "estimate_number": quote_num,
                    "project_name": str(st.session_state.get("est_new_proj") or "").strip(),
                    "customer": new_cust,
                    "customer_id": customer_id_for_name(new_cust) or None,
                    "customer_location_id": new_location_id or None,
                    "customer_contact_id": new_contact_id or None,
                    "status": st.session_state.get("est_new_status") or "Draft",
                    "estimate_date": str(st.session_state.get("est_new_est_date")),
                    "expiration_date": str(st.session_state.get("est_new_exp_date")),
                    "expiration_manual_override": bool(st.session_state.get("est_new_exp_manual")),
                    "scope_of_work": st.session_state.get("est_new_sow"),
                    "notes": st.session_state.get("est_new_notes"),
                }
            )
            if ok:
                st.session_state[_NEW_ESTIMATE_DIALOG_KEY] = False
                clear_new_estimate_number_state()
                st.success(msg or "Estimate saved.")
                st.rerun()
            st.error(msg or "Could not save estimate.")
    with sb2:
        if st.button("Cancel", key="est_cancel_new", use_container_width=True):
            st.session_state[_NEW_ESTIMATE_DIALOG_KEY] = False
            clear_new_estimate_number_state()
            st.rerun()


def _export_estimates_csv(rows: list[dict]) -> str:
    import csv
    from io import StringIO

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["Estimate #", "Project", "Customer", "Linked Job", "Status", "Estimate Date", "Total"]
    )
    for row in rows:
        writer.writerow(
            [
                _estimate_number(row),
                _estimate_project(row),
                _estimate_customer(row),
                _estimate_job(row),
                _normalize_estimate_status(row.get("status")),
                fmt_date(row.get("estimate_date")),
                _estimate_customer_price(row).replace("$", ""),
            ]
        )
    return buf.getvalue()


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("estimates"):
        return
    inject_estimates_module_css()
    inject_estimates_page_layout_css()
    st.markdown('<div class="ips-estimates-page"></div>', unsafe_allow_html=True)
    rows = load_estimates()
    filter_options = build_filter_options(rows, _ESTIMATE_COLUMN_FILTER_SPECS)

    def _est_export() -> None:
        if st.button("Export", key="est_export", use_container_width=True):
            st.session_state["est_export_ready"] = True

    def _est_new() -> None:
        if st.button("+ New Estimate", key="est_new", type="primary", use_container_width=True):
            clear_new_estimate_number_state()
            st.session_state[_NEW_ESTIMATE_DIALOG_KEY] = True

    render_page_brand_header(
        "Estimates",
        "Create, review, price, and send customer proposals.",
        actions=[_est_export, _est_new],
    )

    if st.session_state.get(_NEW_ESTIMATE_DIALOG_KEY):
        _show_new_estimate_dialog()

    def _filters() -> None:
        c1, c2, c3 = st.columns([3.2, 2.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search estimate #, project, customer, status…",
                key="estimates_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "View",
                _ESTIMATES_VIEW_OPTIONS,
                key="estimates_view",
                label_visibility="collapsed",
            )
        with c3:
            if st.button("Clear", key="estimates_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _ESTIMATE_BAR_FILTER_FIELDS,
                    extra_keys=["estimates_search", "estimates_view"],
                )
                st.session_state["estimates_view"] = _ESTIMATES_DEFAULT_VIEW
                reset_table_page(_TABLE_KEY)
                _clear_estimate_selection(st.session_state.get(_ALL_ESTIMATE_IDS_KEY))
                st.rerun()

    render_estimates_filter_bar_shell()
    layout_filter_bar(_filters)
    close_estimates_filter_bar_shell()

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("estimates_search") or "").strip(),
        date_range=None,
        view_filter=str(st.session_state.get("estimates_view") or _ESTIMATES_DEFAULT_VIEW),
    )

    summary = _estimates_summary_counts(filtered)
    render_estimates_summary_cards(
        total=int(summary["total"]),
        active=int(summary["active"]),
        draft=int(summary["draft"]),
        sent=int(summary["sent"]),
        approved=int(summary["approved"]),
        total_customer_value=float(summary["total_customer_value"]),
        has_value_data=bool(summary.get("has_any_value")),
    )

    rows_by_id = {str(r.get("id") or ""): r for r in rows if str(r.get("id") or "").strip()}
    _render_approve_confirmation_panel(rows_by_id)

    if st.session_state.pop("est_export_ready", False):
        st.download_button(
            "Download CSV",
            data=_export_estimates_csv(filtered),
            file_name="estimates_export.csv",
            mime="text/csv",
            key="est_export_download",
        )

    build_modal_cache(filtered, cache_key=_ESTIMATES_CACHE_KEY)
    refreshed = _sync_stale_estimate_rollups(filtered, max_sync=5)
    filtered = _apply_estimate_row_refreshes(filtered, refreshed)
    render_table_pagination_header(len(filtered), _TABLE_KEY, item_label="estimate")
    page_rows, _, _, _ = paginate_rows(filtered, _TABLE_KEY)
    _render_custom_estimates_table(page_rows, filter_options=filter_options)
    render_table_pagination_footer(len(filtered), _TABLE_KEY)

    selected_estimate_id = st.session_state.get(SELECTED_ESTIMATE_KEY)
    if selected_estimate_id and st.session_state.get(SHOW_ESTIMATE_MODAL_KEY):
        _show_estimates_detail_modal()
