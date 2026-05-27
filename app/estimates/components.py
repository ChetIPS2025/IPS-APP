"""Streamlit rendering components for the Estimating module.

All functions are pure rendering helpers that accept pre-fetched data as
arguments — no direct DB calls here.  The page.py orchestrator is responsible
for fetching data and calling these functions.

Public API
----------
render_estimates_header()
render_estimates_filters(df)           → filtered DataFrame
render_estimates_table(df, ...)
render_estimate_detail_panel(sel, ...)
render_estimate_empty_state(...)       → True if New Estimate clicked
render_estimate_line_items(est, ...)
render_estimate_totals(totals)
inject_estimates_mobile_styles()
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.estimates.utils import (
    MONEY_LIST_COLUMNS,
    estimate_description_display,
    list_cell_text,
    money_csv,
    row_estimate_id,
    truthy_job_received,
)

# ---------------------------------------------------------------------------
# CSS injection (once per session)
# ---------------------------------------------------------------------------

_CSS_INJECTED_KEY = "_ips_estimates_mobile_css_v3"


def inject_estimates_mobile_styles() -> None:
    """Inject compact mobile/tablet-friendly styles for the estimates list."""
    if st.session_state.get(_CSS_INJECTED_KEY):
        return
    st.markdown(
        """
        <style>
        /* Estimates list: compact row spacing */
        .ips-est-row { padding: 0.15rem 0; }
        /* Approve button: green tint when done */
        .ips-est-approve-done button { background: #16a34a !important; color: #fff !important; }
        /* Inline list caption rows */
        .ips-est-list-caption { font-size: 0.75rem; color: #64748b; margin: 0; }
        /* Metrics strip: tighter on mobile */
        .ips-estimate-metrics-strip + div [data-testid="metric-container"] {
            padding: 0.25rem 0.4rem !important;
        }
        /* Card header divider */
        .ips-est-section-divider { border-top: 1px solid #e2e8f0; margin: 0.6rem 0 0.4rem 0; }
        /* Compact number inputs in line-item forms */
        @media (max-width: 768px) {
            .ips-estimate-editor-root [data-testid="stNumberInput"] input {
                font-size: 0.8rem !important;
                padding: 0.2rem 0.4rem !important;
            }
            .ips-estimate-editor-root [data-testid="stSelectbox"] > div {
                font-size: 0.8rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state[_CSS_INJECTED_KEY] = True


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def render_estimates_header() -> None:
    """Render the page header (title + subtitle)."""
    try:
        try:
            from app.ui.page_shell import render_page_header
        except ImportError:
            from ui.page_shell import render_page_header  # type: ignore
        render_page_header("Estimates", "Quotes, imports, and customer-ready proposals.")
    except Exception:
        st.title("Estimates")
        st.caption("Quotes, imports, and customer-ready proposals.")


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def render_estimates_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render status + search filters and return the filtered DataFrame.

    Uses standardised session-state keys (estimates_filter_status,
    estimates_search_query) so state survives reruns without widget drift.
    """
    if df.empty:
        return df

    if "status" in df.columns:
        statuses = ["All"] + sorted(df["status"].dropna().astype(str).unique().tolist())
        current_status = st.session_state.get("estimates_filter_status", "All")
        if current_status not in statuses:
            current_status = "All"
        selected = st.selectbox(
            "Filter Status",
            statuses,
            index=statuses.index(current_status),
            key="estimates_filter_status",
        )
        if selected != "All":
            df = df[df["status"] == selected]

    search = st.text_input(
        "Search Quote / PO Number",
        key="estimates_search_query",
        placeholder="Quote number, PO, description…",
    )
    if search.strip():
        s = search.strip().lower()
        mask = df.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        df = df[mask.any(axis=1)]

    return df


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

def render_estimate_empty_state() -> bool:
    """Render the 'No estimates found' empty state.

    Returns True if the **New estimate** action button was clicked.
    """
    try:
        try:
            from app.ui.components.empty_states import render_empty_state
        except ImportError:
            from ui.components.empty_states import render_empty_state  # type: ignore
        return render_empty_state(
            "No estimates found",
            "Create a new estimate or import existing quotes to get started.",
            icon="📄",
            action_label="New estimate",
            action_key="est_list_empty_new",
        )
    except Exception:
        st.info("No estimates found.")
        return bool(st.button("New estimate", key="est_list_empty_new_fallback"))


# ---------------------------------------------------------------------------
# Per-row helpers (not exported — used internally by render_estimates_table)
# ---------------------------------------------------------------------------

def _linked_job_display_cell(
    est_row: pd.Series,
    *,
    job_by_id: dict[str, dict],
    job_by_estimate_id: dict[str, dict],
) -> str:
    try:
        from app.utils.formatters import job_display_label
    except ImportError:
        from utils.formatters import job_display_label  # type: ignore

    jid = est_row.get("job_id")
    eid = est_row.get("id")
    if jid is not None and pd.notna(jid) and str(jid).strip():
        sj = str(jid)
        if sj in job_by_id:
            job = job_by_id[sj]
            return job_display_label(job.get("job_number"), job.get("job_name"))
    if eid is not None and pd.notna(eid):
        se = str(eid)
        if se in job_by_estimate_id:
            job = job_by_estimate_id[se]
            return job_display_label(job.get("job_number"), job.get("job_name"))
    return ""


def _linked_job_id_for_row(
    est_row: pd.Series,
    *,
    job_by_id: dict[str, dict],
    job_by_estimate_id: dict[str, dict],
) -> str | None:
    jid = est_row.get("job_id")
    eid = est_row.get("id")
    if jid is not None and pd.notna(jid) and str(jid).strip():
        return str(jid)
    if eid is not None and pd.notna(eid):
        se = str(eid)
        if se in job_by_estimate_id:
            return str(job_by_estimate_id[se].get("id"))
    return None


def _site_caption(est_row: pd.Series, *, location_by_id: dict[str, dict]) -> str:
    if "customer_location_id" not in est_row.index:
        return ""
    raw = est_row.get("customer_location_id")
    if raw is None:
        return ""
    try:
        if pd.isna(raw):
            return ""
    except Exception:
        pass
    lid = str(raw).strip()
    if not lid or lid not in location_by_id:
        return ""
    try:
        try:
            from services.customer_locations import location_display_name_city_state
        except ImportError:
            from app.services.customer_locations import location_display_name_city_state  # type: ignore
        row = location_by_id[lid]
        return location_display_name_city_state(row) if row else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Main estimates table
# ---------------------------------------------------------------------------

# Column weight presets — mobile-friendlier than the old uniform weights.
_COL_WEIGHTS = [
    0.4,   # checkbox
    1.2,   # job received / created
    1.0,   # quote #
    2.2,   # description
    1.0,   # proposal total
    0.85,  # status
    1.6,   # linked job
    0.9,   # PO #
    0.75,  # approve
    0.45,  # delete
]

_COL_HEADERS = [
    " ",
    "Job",
    "Quote",
    "Estimate Description",
    "Proposal total",
    "Status",
    "Linked job",
    "PO #",
    "Approve",
    "Del",
]


def render_estimates_table(
    df: pd.DataFrame,
    *,
    job_by_id: dict[str, dict],
    job_by_estimate_id: dict[str, dict],
    location_by_id: dict[str, dict],
    eid_to_customer: dict[str, str],
    can_edit: bool,
) -> tuple[list[str], dict]:
    """Render the estimates list table.

    Returns ``(selected_ids, actions_dict)`` — always a 2-tuple.
    ``selected_ids`` is the list of checked estimate IDs.
    ``actions_dict`` is the action-bar result dict from render_selection_action_bar.

    Handles Job Received / Approve / Delete per-row actions inline.
    """
    _empty: tuple[list[str], dict] = ([], {})

    try:
        try:
            from services.job_from_estimate import (
                create_job_from_estimate,
                estimate_status_allows_job_creation,
            )
        except ImportError:
            from app.services.job_from_estimate import (  # type: ignore
                create_job_from_estimate,
                estimate_status_allows_job_creation,
            )
    except Exception:
        create_job_from_estimate = None  # type: ignore
        estimate_status_allows_job_creation = None  # type: ignore

    try:
        try:
            from table_actions import (
                IPS_PENDING_DELETE,
                TABLE_KEY_ESTIMATES,
                clear_selected_ids,
                get_selected_ids,
                render_selection_action_bar,
                set_selected_ids,
            )
        except ImportError:
            from app.table_actions import (  # type: ignore
                IPS_PENDING_DELETE,
                TABLE_KEY_ESTIMATES,
                clear_selected_ids,
                get_selected_ids,
                render_selection_action_bar,
                set_selected_ids,
            )
    except Exception as e:
        st.error(f"Could not load table actions: {e}")
        return _empty

    try:
        try:
            from db import update_rows_admin
        except ImportError:
            from app.db import update_rows_admin  # type: ignore
    except Exception:
        update_rows_admin = None  # type: ignore

    try:
        try:
            from services.delete_safety import delete_estimate_unlink_first
        except ImportError:
            from app.services.delete_safety import delete_estimate_unlink_first  # type: ignore
    except Exception:
        delete_estimate_unlink_first = None  # type: ignore

    try:
        from app.navigation import IPS_NAV_PENDING_KEY
    except ImportError:
        try:
            from navigation import IPS_NAV_PENDING_KEY  # type: ignore
        except ImportError:
            from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

    from app.estimates.queries import is_admin_reader

    inject_estimates_mobile_styles()

    st.caption(
        "**Estimates = quotes / proposals** (pricing and approval). "
        "**Jobs = costing / field records** — create from an accepted estimate or standalone."
    )
    st.caption(
        "**Job Received** creates a linked job. Use the **action bar** below for view, edit, delete, and export."
    )

    # Job-DB navigation checkbox
    nav1, nav2 = st.columns([1.1, 3])
    with nav1:
        st.checkbox(
            "Open new job in Job Database",
            value=True,
            key="est_job_recv_open_job_db",
            help="After Job Received, navigate to the new job.",
        )
    with nav2:
        st.caption("Uncheck to stay on this list after creating a job.")

    # Column headers
    head = st.columns(_COL_WEIGHTS)
    for col_widget, label in zip(head, _COL_HEADERS):
        col_widget.caption(label)

    picked: list[str] = []

    for _, est_row in df.iterrows():
        eid = row_estimate_id(est_row)
        if not eid:
            continue

        linked_id = _linked_job_id_for_row(
            est_row, job_by_id=job_by_id, job_by_estimate_id=job_by_estimate_id
        )
        cust_id = eid_to_customer.get(eid, "")
        row_status = str(est_row.get("status") or "").strip().lower()

        rc = st.columns(_COL_WEIGHTS)

        # [0] Checkbox
        with rc[0]:
            ck = f"est_list_pick_{eid}"
            if ck not in st.session_state:
                st.session_state[ck] = eid in get_selected_ids(TABLE_KEY_ESTIMATES)
            checked = st.checkbox("Select", key=ck, label_visibility="collapsed")
            if checked:
                picked.append(eid)

        # [1] Job Received / Job Created
        with rc[1]:
            if linked_id:
                st.button(
                    "Job Created",
                    key=f"job_created_{eid}",
                    disabled=True,
                    use_container_width=True,
                    help="A job is already linked to this estimate.",
                )
            elif create_job_from_estimate and estimate_status_allows_job_creation:
                _disable_reason = _job_received_disabled_reason(
                    est_row,
                    cust_id=cust_id,
                    can_edit=can_edit,
                    estimate_status_allows_job_creation=estimate_status_allows_job_creation,
                )
                ready = not _disable_reason
                if st.button(
                    "Job Received",
                    key=f"job_received_{eid}",
                    disabled=not ready,
                    use_container_width=True,
                    help=(
                        "Create a job from this estimate."
                        if ready
                        else _disable_reason
                    ),
                ):
                    res = create_job_from_estimate(str(eid), mark_job_received=True)
                    if res.ok and res.job:
                        jid = str(res.job.get("id") or "")
                        if jid and st.session_state.get("est_job_recv_open_job_db", True):
                            st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                            st.session_state["job_view_mode"] = "edit"
                            st.session_state["selected_job_id"] = jid
                            st.session_state["job_mode"] = "edit"
                            st.session_state["job_edit_id"] = jid
                        st.success(res.message)
                        st.rerun()
                    elif res.message:
                        if res.error_code == "duplicate":
                            st.warning(res.message)
                        elif res.error_code == "job_received":
                            st.info(res.message)
                        else:
                            st.error(res.message)

        # [2] Quote number
        with rc[2]:
            st.text(list_cell_text(est_row.get("quote_number"), col="quote_number"))

        # [3] Description + optional site line
        with rc[3]:
            st.text(estimate_description_display(est_row))
            site_ln = _site_caption(est_row, location_by_id=location_by_id)
            if site_ln:
                st.caption(f"Site: {site_ln}")

        # [4] Proposal total
        with rc[4]:
            st.text(list_cell_text(est_row.get("proposal_total"), col="proposal_total"))

        # [5] Status
        with rc[5]:
            st.text(list_cell_text(est_row.get("status"), col="status"))

        # [6] Linked job
        linked_label = _linked_job_display_cell(
            est_row, job_by_id=job_by_id, job_by_estimate_id=job_by_estimate_id
        )
        with rc[6]:
            st.text(list_cell_text(linked_label))

        # [7] PO number
        with rc[7]:
            st.text(list_cell_text(est_row.get("po_number"), col="po_number"))

        # [8] Approve
        with rc[8]:
            is_approved = row_status == "approved"
            can_approve = can_edit and row_status in ["draft", "submitted"]
            approve_label = "Approved ✓" if is_approved else "Approve"
            anchor_cls = "ips-est-approve-anchor" + (" ips-est-approve-done" if is_approved else "")
            st.markdown(f'<span class="{anchor_cls}"></span>', unsafe_allow_html=True)
            if update_rows_admin and st.button(
                approve_label,
                key=f"est_row_approve_{eid}",
                type="primary" if (can_approve or is_approved) else "secondary",
                disabled=not can_approve,
                use_container_width=True,
                help=(
                    "Approve this estimate"
                    if can_approve
                    else (
                        "Already approved"
                        if is_approved
                        else "Only draft/submitted estimates can be approved"
                    )
                ),
            ):
                try:
                    update_rows_admin("estimates", {"status": "approved"}, {"id": eid})
                    from app.estimates.services import bump_estimates_cache
                    bump_estimates_cache()
                    st.success("Estimate approved.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not approve: {exc}")

        # [9] Delete
        with rc[9]:
            if st.button(
                "🗑",
                key=f"est_row_del_{eid}",
                disabled=not can_edit,
                use_container_width=True,
                help=(
                    "Delete this estimate. Linked jobs are kept but unlinked."
                    if can_edit
                    else "Only admin or pm can delete estimates."
                ),
            ):
                st.session_state[IPS_PENDING_DELETE] = {TABLE_KEY_ESTIMATES: [str(eid)]}
                st.rerun()

    set_selected_ids(TABLE_KEY_ESTIMATES, picked)

    # Export CSV — format money columns, preserve id column for action bar
    df_export = df.copy()
    for mc in MONEY_LIST_COLUMNS:
        if mc in df_export.columns:
            df_export[mc] = df_export[mc].map(money_csv)

    # Action bar (view / edit / delete / CSV export)
    def _cleanup_picks() -> None:
        for k in list(st.session_state.keys()):
            if str(k).startswith("est_list_pick_"):
                st.session_state.pop(k, None)

    try:
        actions: dict = render_selection_action_bar(
            TABLE_KEY_ESTIMATES,
            picked,
            can_view=True,
            can_edit=can_edit,
            can_delete=can_edit,
            export_df=df_export,
            visible_df=df,
            id_column="id",
            export_filename="estimates_export.csv",
            on_bulk_selection_change=_cleanup_picks,
        )
    except Exception as _act_err:
        st.warning(f"Action bar unavailable: {_act_err}")
        actions = {}

    # Delete confirmation flow
    pend = st.session_state.get(IPS_PENDING_DELETE) or {}
    if actions.get("confirm_delete") and pend.get(TABLE_KEY_ESTIMATES) and delete_estimate_unlink_first:
        from app.estimates.services import bump_estimates_cache
        for del_eid in pend[TABLE_KEY_ESTIMATES]:
            try:
                delete_estimate_unlink_first(str(del_eid), admin_read=is_admin_reader())
            except Exception as exc:
                st.error(f"Could not delete {del_eid}: {exc}")
        pend.pop(TABLE_KEY_ESTIMATES, None)
        clear_selected_ids(TABLE_KEY_ESTIMATES)
        _cleanup_picks()
        bump_estimates_cache()
        st.success("Delete completed where permitted.")
        st.rerun()

    return picked, actions


def _job_received_disabled_reason(
    est_row: pd.Series,
    *,
    cust_id: str,
    can_edit: bool,
    estimate_status_allows_job_creation: Any,
) -> str:
    if not can_edit:
        return "Only admin or pm can run this action."
    if truthy_job_received(est_row):
        return "This estimate is already marked as job received."
    if not cust_id:
        return "Choose a customer on the estimate before creating a job."
    st_raw = str(est_row.get("status") or "")
    if not estimate_status_allows_job_creation(st_raw):
        return (
            f"Status {st_raw!r} does not allow creating a job from this page. "
            "Approve the estimate first."
        )
    return ""


# ---------------------------------------------------------------------------
# Estimate detail panel (linked-job / create-job panel below the table)
# ---------------------------------------------------------------------------

def render_estimate_detail_panel(
    sel: list[str],
    *,
    df: pd.DataFrame,
    job_by_id: dict[str, dict],
    job_by_estimate_id: dict[str, dict],
    can_edit: bool,
) -> None:
    """Render the linked-job info / Create-job panel for a single selection."""
    if not (can_edit and sel and len(sel) == 1):
        return

    try:
        try:
            from app.ui.page_shell import render_card
        except ImportError:
            from ui.page_shell import render_card  # type: ignore
    except Exception:
        render_card = None  # type: ignore

    try:
        try:
            from services.job_from_estimate import create_job_from_estimate
        except ImportError:
            from app.services.job_from_estimate import create_job_from_estimate  # type: ignore
    except Exception:
        create_job_from_estimate = None  # type: ignore

    try:
        from app.navigation import IPS_NAV_PENDING_KEY
    except ImportError:
        try:
            from navigation import IPS_NAV_PENDING_KEY  # type: ignore
        except ImportError:
            from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

    try:
        try:
            from services.job_service import job_number_display
        except ImportError:
            from app.services.job_service import job_number_display  # type: ignore
    except Exception:
        job_number_display = str  # type: ignore

    try:
        from app.utils.formatters import job_display_label
    except ImportError:
        from utils.formatters import job_display_label  # type: ignore

    row_one = df[df["id"].astype(str) == str(sel[0])] if "id" in df.columns else pd.DataFrame()
    if row_one.empty:
        return

    r0 = row_one.iloc[0]
    open_jid = _linked_job_id_for_row(
        r0, job_by_id=job_by_id, job_by_estimate_id=job_by_estimate_id
    )
    qn = str(r0.get("quote_number") or "").strip()
    linked_jn = ""
    linked_jnm = ""
    if open_jid and str(open_jid) in job_by_id:
        job_row = job_by_id[str(open_jid)]
        linked_jn = job_number_display(job_row.get("job_number"))
        linked_jnm = str(job_row.get("job_name") or "").strip()

    ctx = render_card() if render_card else _noop_ctx()
    with ctx:
        st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
        if open_jid:
            jdisp = job_display_label(linked_jn, linked_jnm)
            if jdisp:
                st.markdown(f"**Linked job** · **{jdisp}**", unsafe_allow_html=True)
            else:
                st.markdown(
                    "**Linked job** · _This estimate is linked to a job but details are unavailable._",
                    unsafe_allow_html=True,
                )
            if qn:
                st.caption(f"Source estimate · {qn}")
            if st.button("Open Job", type="primary", use_container_width=True, key="est_list_open_job_btn"):
                st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                st.session_state["job_view_mode"] = "edit"
                st.session_state["selected_job_id"] = str(open_jid)
                st.session_state["job_mode"] = "edit"
                st.session_state["job_edit_id"] = str(open_jid)
                st.rerun()
        elif create_job_from_estimate:
            lc1, lc2, lc3 = st.columns([1, 1, 2], gap="small")
            with lc1:
                run_cj = st.button(
                    "Create Job from Estimate",
                    key="est_list_create_job_btn",
                    use_container_width=True,
                )
            with lc2:
                st.checkbox(
                    "Open Job Database after create",
                    value=True,
                    key="est_list_create_job_open_db",
                )
            with lc3:
                st.caption(
                    "Creates a **J#####** job once the estimate is customer-approved."
                )
            if run_cj:
                res = create_job_from_estimate(str(sel[0]))
                if res.ok and res.job:
                    st.success(res.message)
                    jid = str(res.job.get("id") or "")
                    if jid and st.session_state.get("est_list_create_job_open_db", True):
                        st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                        st.session_state["job_view_mode"] = "edit"
                        st.session_state["selected_job_id"] = jid
                        st.session_state["job_mode"] = "edit"
                        st.session_state["job_edit_id"] = jid
                    from app.estimates.services import bump_estimates_cache
                    bump_estimates_cache()
                    st.rerun()
                elif res.message:
                    if res.error_code == "duplicate":
                        st.warning(res.message)
                    else:
                        st.error(res.message)


class _noop_ctx:
    """Fallback context manager when render_card is unavailable."""
    def __enter__(self): return self
    def __exit__(self, *_): pass


# ---------------------------------------------------------------------------
# Estimate totals display (sidebar / panel)
# ---------------------------------------------------------------------------

def render_estimate_totals(totals: dict[str, Any], *, est: dict[str, Any]) -> None:
    """Render the totals summary panel in the sidebar."""
    from app.estimates.calculations import money

    with st.sidebar:
        st.markdown("#### Totals")
        qn = str(est.get("quote_number") or "—").strip() or "—"
        st.caption(f"{qn} · {est.get('status') or 'draft'}")

        rows = [
            ("Materials", totals.get("material_sell_basis", 0)),
            ("Labor", totals.get("labor_total", 0)),
            ("Equipment", totals.get("equipment_total", 0)),
            ("Travel", totals.get("travel_total", 0)),
            ("Overhead", totals.get("overhead_total", 0)),
            ("Profit", totals.get("profit_total", 0)),
            ("Contingency", totals.get("contingency_total", 0)),
            ("Tax", totals.get("sales_tax_total", 0)),
        ]
        for label, val in rows:
            st.caption(f"**{label}:** {money(val)}")
        st.markdown(f"**Proposal: {money(totals.get('proposal_total', 0))}**")


# ---------------------------------------------------------------------------
# Line-items summary component (called from within the editor context)
# ---------------------------------------------------------------------------

def render_estimate_line_items_summary(est: dict[str, Any], totals: dict[str, Any]) -> None:
    """Compact line-item summary strip (materials / labor / equipment / travel counts)."""
    from app.estimates.calculations import money

    mat_n = len(est.get("materials") or [])
    lab_n = len(est.get("labor") or [])
    eq_n = len(est.get("equipment") or [])

    cols = st.columns(4, gap="small")
    cols[0].metric("Materials", f"{mat_n} lines", delta=money(totals.get("material_sell_basis", 0)), delta_color="off")
    cols[1].metric("Labor", f"{lab_n} lines", delta=money(totals.get("labor_total", 0)), delta_color="off")
    cols[2].metric("Equipment", f"{eq_n} lines", delta=money(totals.get("equipment_total", 0)), delta_color="off")
    cols[3].metric("Travel", "—", delta=money(totals.get("travel_total", 0)), delta_color="off")
