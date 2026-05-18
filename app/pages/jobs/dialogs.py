"""Job form panel (create / edit) for the Jobs module.

``render_job_form_panel`` is the only public entry point; everything else is private.
"""
from __future__ import annotations

import html
import logging
from datetime import date as _date, timedelta as _td
from typing import Any

import pandas as pd
import streamlit as st

from auth import current_role

try:
    from app.db import (
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        insert_row_admin,
        update_rows_admin,
    )
except ImportError:
    from db import (  # type: ignore
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        insert_row_admin,
        update_rows_admin,
    )

try:
    from app.db import create_signed_url
except ImportError:
    from db import create_signed_url  # type: ignore

try:
    from app.services.job_service import job_row_select_label, next_job_number
except ImportError:
    from services.job_service import job_row_select_label, next_job_number  # type: ignore

try:
    from app.services.job_weekly_timesheets import generate_unsigned_timesheet_for_job_week
except ImportError:
    from services.job_weekly_timesheets import generate_unsigned_timesheet_for_job_week  # type: ignore

try:
    from app.services.customer_contacts import (
        contact_option_label,
        inject_contact_picker_styles,
        render_contact_detail_preview,
        render_contact_quick_add_when_empty,
    )
except ImportError:
    from services.customer_contacts import (  # type: ignore
        contact_option_label,
        inject_contact_picker_styles,
        render_contact_detail_preview,
        render_contact_quick_add_when_empty,
    )

from .constants import JOB_STATUSES
from .queries import admin_read, bump_data_version, fetch_contacts_for_job_database, fetch_contact_by_id, fetch_estimate_by_id
from .utils import card_text, clear_job_mode

_LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Estimate display helpers
# ---------------------------------------------------------------------------

def _money_detail(v: Any) -> str:
    try:
        if v is None or str(v).strip() == "":
            return "—"
        return f"${float(v):,.2f}"
    except Exception:
        return "—"


def _estimate_total(row: dict[str, Any]) -> str:
    for key in ("proposal_total", "final_bid"):
        if key not in row:
            continue
        raw = row.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        try:
            fv = float(raw)
            if fv != 0 or key == "proposal_total":
                return _money_detail(fv)
        except Exception:
            continue
    return "—"


def _merge_estimate_detail(*, estimate_id: str, estimate_detail: dict[str, Any] | None) -> dict[str, Any]:
    full = fetch_estimate_by_id(estimate_id) or {}
    base = dict(estimate_detail or {})
    return {**full, **base}


def _estimate_contact_display(det: dict[str, Any]) -> str:
    cid = str(det.get("customer_contact_id") or "").strip()
    if not cid:
        return "—"
    row = fetch_contact_by_id(cid)
    if not row:
        return f"Contact id `{cid[:8]}…`"
    return str(contact_option_label(row)).strip() or "—"


def _customer_display_name(
    customer_id: str | None,
    customers: list[dict[str, Any]],
    name_by_id: dict[str, str],
) -> str:
    cid = str(customer_id or "").strip()
    if not cid:
        return ""
    n = name_by_id.get(cid)
    if n:
        return str(n).strip()
    for c in customers:
        if str(c.get("id") or "").strip() == cid:
            return str(c.get("customer_name") or "").strip()
    return ""


def _linked_estimate_id(estimate_options: dict[str, Any], linked_label: str) -> str | None:
    """Map selectbox label → estimate UUID, or None for standalone jobs."""
    if not str(linked_label or "").strip():
        return None
    raw = estimate_options.get(linked_label)
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def build_estimate_options(
    *,
    estimates: list[dict[str, Any]],
    estimate_label_map: dict[str, str],
    selected_job: dict[str, Any] | None,
    estimate_detail: dict[str, Any] | None,
    customers: list[dict[str, Any]],
    customer_name_by_id: dict[str, str],
) -> dict[str, Any]:
    """Build {label: estimate_id} dict for the job form selector."""
    opts: dict[str, Any] = {"": None}
    for e in estimates:
        eid = str(e.get("id") or "").strip()
        if not eid:
            continue
        lab = estimate_label_map.get(eid)
        if lab:
            opts[lab] = eid
    if selected_job and selected_job.get("estimate_id"):
        _leid = str(selected_job["estimate_id"])
        existing_ids = {str(v) for v in opts.values() if v is not None}
        if _leid not in existing_ids:
            lab = estimate_label_map.get(_leid)
            if not lab and estimate_detail:
                qn = str(estimate_detail.get("quote_number") or "").strip()
                cn = _customer_display_name(estimate_detail.get("customer_id"), customers, customer_name_by_id)
                est_st = str(estimate_detail.get("status") or "").strip()
                lab = f"{qn} | {cn} | {est_st}" if (qn or cn or est_st) else f"Estimate ({_leid[:8]}…)"
            elif not lab:
                lab = f"Estimate ({_leid[:8]}…)"
            opts[lab] = _leid
    return opts


# ---------------------------------------------------------------------------
# Estimate summary overview block (edit mode only)
# ---------------------------------------------------------------------------

def _render_estimate_summary_overview(
    *,
    selected_job: dict[str, Any],
    estimate_options: dict[str, Any],
    estimate_detail: dict[str, Any] | None,
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    customers: list[dict[str, Any]],
    customer_name_by_id: dict[str, str],
    can_edit: bool,
) -> str:
    try:
        from app.ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from ui import IPS_NAV_PENDING_KEY  # type: ignore

    jid = str(selected_job.get("id") or "").strip()
    eid = str(selected_job.get("estimate_id") or "").strip()

    with st.container(border=True):
        st.markdown('<span class="ips-job-estimate-summary-host"></span>', unsafe_allow_html=True)
        st.markdown("#### Estimate Summary")

        if not eid:
            st.markdown(
                "<p style='margin:0 0 0.5rem 0;font-weight:700;color:#111827;'>No estimate linked to this job.</p>",
                unsafe_allow_html=True,
            )
            st.caption("Pick a quote below, then click **Update Job** to save the link.")
        else:
            det = _merge_estimate_detail(estimate_id=eid, estimate_detail=estimate_detail)
            qn = str(estimate_quote_by_id.get(eid) or det.get("quote_number") or "").strip()
            name_hint = str(det.get("estimate_description") or "").strip()
            title_line = html.escape(qn) if qn else f"Estimate `{html.escape(eid[:8])}…`"
            if name_hint and len(name_hint) <= 120:
                title_line += f" · <span style='font-weight:600'>{html.escape(name_hint)}</span>"
            elif name_hint:
                title_line += f" · <span style='font-weight:600'>{html.escape(name_hint[:117])}…</span>"
            st_txt = str(det.get("status") or "").strip()
            cust = _customer_display_name(det.get("customer_id"), customers, customer_name_by_id)
            po_amt = _money_detail(det.get("po_amount"))
            po_num = str(det.get("po_number") or "").strip()
            po_lbl = f"PO amount ({html.escape(po_num)})" if po_num else "PO / quote amount"
            prop = _money_detail(det.get("proposal_total")) if det.get("proposal_total") not in (None, "") else "—"
            fin = _money_detail(det.get("final_bid")) if det.get("final_bid") not in (None, "") else "—"
            tot = _estimate_total(det)
            awarded = _money_detail(selected_job.get("awarded_amount"))
            contact_disp = html.escape(_estimate_contact_display(det))
            card_html = (
                f"<div class='ips-jes-card'>"
                f"<p style='margin:0 0 0.65rem 0;font-size:0.95rem;color:#111827;'><strong>Linked quote</strong> · {title_line}</p>"
                f"<div class='ips-jes-grid'>"
                f"<div><span class='ips-jes-lbl'>Status</span><span class='ips-jes-val'>{html.escape(st_txt) if st_txt else '—'}</span></div>"
                f"<div><span class='ips-jes-lbl'>Estimate total</span><span class='ips-jes-val'>{html.escape(tot)}</span></div>"
                f"<div><span class='ips-jes-lbl'>Proposal</span><span class='ips-jes-val'>{html.escape(prop)}</span></div>"
                f"<div><span class='ips-jes-lbl'>Final bid</span><span class='ips-jes-val'>{html.escape(fin)}</span></div>"
                f"<div><span class='ips-jes-lbl'>{po_lbl}</span><span class='ips-jes-val'>{html.escape(po_amt)}</span></div>"
                f"<div><span class='ips-jes-lbl'>Awarded (job)</span><span class='ips-jes-val'>{html.escape(awarded)}</span></div>"
                f"<div><span class='ips-jes-lbl'>Customer</span><span class='ips-jes-val'>{html.escape(cust) if cust else '—'}</span></div>"
                f"<div><span class='ips-jes-lbl'>Contact (on quote)</span><span class='ips-jes-val'>{contact_disp}</span></div>"
                f"</div></div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)

        b_open, b_rm = st.columns([1, 1], gap="small")
        with b_open:
            if eid and st.button("Open estimate", type="primary", use_container_width=True, key=f"job_ov_open_est_{jid}"):
                try:
                    from app.pages import estimates as _estimates_page
                except ImportError:
                    import pages.estimates as _estimates_page  # type: ignore
                _estimates_page._load_estimate_into_session(eid)
                if str(st.session_state.get("loaded_estimate_id") or "").strip() == eid:
                    st.session_state["estimates_view"] = "edit"
                    st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
                    st.rerun()
                st.warning("Could not open that estimate (missing or no access).")
        with b_rm:
            if eid and can_edit:
                with st.popover("Unlink estimate", use_container_width=True):
                    st.caption("Removes the link from this job only. The estimate is **not** deleted.")
                    if st.button("Remove linked estimate", type="primary", key=f"job_ov_unlink_est_{jid}"):
                        update_rows_admin("jobs", {"estimate_id": None}, {"id": selected_job["id"]})
                        bump_data_version()
                        st.success("Link removed. You can attach a different quote below.")
                        st.rerun()

        estimate_labels = [""] + [k for k in estimate_options.keys() if k]
        current_estimate_label = ""
        if selected_job.get("estimate_id"):
            _seid = str(selected_job["estimate_id"])
            current_estimate_label = estimate_label_map.get(_seid, "")
            if not current_estimate_label:
                for lab, eid_opt in estimate_options.items():
                    if lab and str(eid_opt) == _seid:
                        current_estimate_label = lab
                        break
        _lbl = "Link estimate" if not eid else "Linked estimate (change)"
        linked_estimate = st.selectbox(
            _lbl,
            estimate_labels,
            index=estimate_labels.index(current_estimate_label) if current_estimate_label in estimate_labels else 0,
            disabled=not can_edit,
            key="job_form_linked_estimate",
            help="Leave blank for a standalone job. Pick a quote to link this job to an estimate.",
        )
        if not eid:
            if st.button("Link estimate", type="secondary", use_container_width=True, key=f"job_ov_link_hint_{jid}"):
                st.info("Choose a quote in **Link estimate** above, then click **Update Job** at the bottom of the form.")
    return linked_estimate


# ---------------------------------------------------------------------------
# Weekly timesheets expander (edit mode only)
# ---------------------------------------------------------------------------

def _render_weekly_timesheets_expander(*, selected_job: dict[str, Any], can_edit: bool) -> None:
    with st.expander("Weekly Timesheets", expanded=False):
        st.caption("Generate a customer-facing weekly timesheet PDF and share a secure signing link.")
        jid = str(selected_job.get("id") or "").strip()
        if not jid:
            st.caption("Select a job.")
            return

        today = _date.today()
        default_ws = today - _td(days=today.weekday() + 7)
        week_start = st.date_input("Week start (Mon)", value=default_ws, key=f"jwt_week_{jid}")
        summary = st.text_area(
            "Work summary / notes (optional)",
            key=f"jwt_summary_{jid}",
            height=72,
            placeholder="Optional summary shown on the PDF.",
        )
        if st.button(
            "Generate unsigned PDF",
            type="primary",
            use_container_width=True,
            disabled=not can_edit,
            key=f"jwt_gen_{jid}",
        ):
            try:
                row = generate_unsigned_timesheet_for_job_week(
                    job_id=jid,
                    week_start=week_start,
                    work_summary=str(summary or "").strip(),
                )
            except Exception as exc:
                st.error(f"Could not generate: {exc}")
                st.stop()
            st.success("Generated.")
            st.session_state[f"jwt_last_row_{jid}"] = row
            st.rerun()

        try:
            rows = fetch_by_match_admin(
                "job_weekly_timesheets",
                {"job_id": jid},
                columns="id,week_start,week_end,status,unsigned_pdf_url,signed_pdf_url,sent_at,signed_at,sign_token,sign_token_expires_at",
                limit=200,
            )
        except Exception:
            rows = []

        if not rows:
            st.caption("No weekly timesheets yet. Run migration `sql/031_job_weekly_timesheets.sql`.")
            return

        rows = sorted(rows, key=lambda r: str(r.get("week_start") or ""), reverse=True)
        latest = rows[0]
        st.markdown("**Latest**")
        up = str(latest.get("unsigned_pdf_url") or "").strip()
        sp = str(latest.get("signed_pdf_url") or "").strip()
        token = str(latest.get("sign_token") or "").strip()
        unsigned_link = create_signed_url(up, expires_in=3600) if up else ""
        signed_link = create_signed_url(sp, expires_in=3600) if sp else ""
        sign_link = f"?tsign={token}" if token else ""
        st.caption(
            f"Week {str(latest.get('week_start') or '')} → {str(latest.get('week_end') or '')} · "
            f"Status **{str(latest.get('status') or '')}**"
        )
        a1, a2, a3 = st.columns(3, gap="small")
        with a1:
            if unsigned_link:
                st.link_button("Open unsigned", unsigned_link, use_container_width=True)
            else:
                st.button("Open unsigned", use_container_width=True, disabled=True)
        with a2:
            if sign_link:
                st.link_button("Open sign page", sign_link, use_container_width=True)
            else:
                st.button("Open sign page", use_container_width=True, disabled=True)
        with a3:
            if signed_link:
                st.link_button("Open signed", signed_link, use_container_width=True)
            else:
                st.button("Open signed", use_container_width=True, disabled=True)

        st.markdown("**History**")
        table = []
        for r in rows[:30]:
            t = str(r.get("sign_token") or "").strip()
            table.append({
                "Week": f"{str(r.get('week_start') or '')} → {str(r.get('week_end') or '')}",
                "Status": str(r.get("status") or ""),
                "Sent": str(r.get("sent_at") or "")[:19],
                "Signed": str(r.get("signed_at") or "")[:19],
                "Sign link": (f"?tsign={t}" if t else "—"),
                "Token expires": str(r.get("sign_token_expires_at") or "")[:19],
            })
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
        st.caption("Use **Open sign page** above, or copy any **Sign link** into an email.")


# ---------------------------------------------------------------------------
# Email settings expander (edit mode only)
# ---------------------------------------------------------------------------

def _render_email_settings_expander(*, selected_job: dict[str, Any], can_edit: bool) -> None:
    with st.expander("Email settings", expanded=False):
        st.caption("Configure customer/internal recipients and enable automatic updates for this job.")
        try:
            from app.services.email_notifications import fetch_job_email_settings_row, upsert_job_email_settings
        except ImportError:
            from services.email_notifications import fetch_job_email_settings_row, upsert_job_email_settings  # type: ignore

        jid = str(selected_job.get("id") or "").strip()
        row = fetch_job_email_settings_row(jid, admin=admin_read()) or {}
        cust = row.get("customer_recipients") or []
        internal = row.get("internal_recipients") or []
        cc = row.get("cc_recipients") or []

        with st.form(f"job_email_settings_form_{jid}", clear_on_submit=False):
            c1, c2 = st.columns(2, gap="small")
            with c1:
                cust_in = st.text_area("Customer recipients", value=", ".join([str(x) for x in cust if str(x).strip()]), height=68, placeholder="email1@customer.com, email2@customer.com", key=f"job_email_cust_{jid}")
                internal_in = st.text_area("Internal IPS recipients", value=", ".join([str(x) for x in internal if str(x).strip()]), height=68, placeholder="ops@ips.com, pm@ips.com", key=f"job_email_internal_{jid}")
            with c2:
                cc_in = st.text_area("CC recipients", value=", ".join([str(x) for x in cc if str(x).strip()]), height=68, placeholder="optional CC list", key=f"job_email_cc_{jid}")
                notes_email = st.text_area("Email notes", value=str(row.get("notes") or ""), height=68, placeholder="Optional", key=f"job_email_notes_{jid}")
            t1, t2 = st.columns(2, gap="small")
            with t1:
                enable_daily = st.checkbox("Enable daily update emails", value=bool(row.get("enable_daily_update_emails", False)), key=f"job_email_enable_daily_{jid}")
                enable_weekly = st.checkbox("Enable weekly Friday update emails", value=bool(row.get("enable_weekly_friday_update_emails", False)), key=f"job_email_enable_weekly_{jid}")
            with t2:
                enable_safety = st.checkbox("Enable safety item update emails", value=bool(row.get("enable_safety_item_update_emails", False)), key=f"job_email_enable_safety_{jid}", help="Framework toggle (requires safety status source to be configured).")
                enable_budget = st.checkbox("Enable budget/PO alerts", value=bool(row.get("enable_budget_po_alerts", False)), key=f"job_email_enable_budget_{jid}")
            is_active = st.checkbox("Email settings active", value=bool(row.get("is_active", True)), key=f"job_email_is_active_{jid}")
            save_email = st.form_submit_button("Save email settings", type="primary", use_container_width=True, disabled=not can_edit)

        if save_email:
            try:
                upsert_job_email_settings(
                    jid,
                    customer_recipients=cust_in,
                    internal_recipients=internal_in,
                    cc_recipients=cc_in,
                    enable_daily=enable_daily,
                    enable_weekly_friday=enable_weekly,
                    enable_safety=enable_safety,
                    enable_budget_po_alerts=enable_budget,
                    is_active=is_active,
                    notes=notes_email,
                )
            except Exception as exc:
                st.error(f"Could not save: {exc}")
            else:
                st.success("Saved.")
                st.rerun()


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def render_job_form_panel(
    *,
    mode: str,
    can_edit: bool,
    selected_job: dict[str, Any] | None,
    jobs: list[dict[str, Any]],
    has_job_number_column: bool,
    has_customer_location_column: bool,
    customers: list[dict[str, Any]],
    estimates: list[dict[str, Any]],
    customer_name_by_id: dict[str, str],
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    estimate_detail: dict[str, Any] | None = None,
    show_main_heading: bool = True,
) -> None:
    """Full-width job create / edit form with section tabs (Overview / Tasks / Cost)."""
    with st.container(border=True):
        st.markdown('<span class="ips-job-edit-panel-anchor"></span>', unsafe_allow_html=True)
        if show_main_heading:
            st.markdown(f"### {'Add Job' if mode == 'add' else 'Edit Job'}")
        if mode == "add":
            st.caption(
                "Standalone job — **no estimate required**. Leave **Linked estimate** empty, "
                "or pick a quote only if you are attaching this job to an existing estimate."
            )

        use_job_tabs = mode == "edit" and bool(selected_job)
        _job_detail_panel = "Overview"
        edit_jid = ""
        jl = ""
        admin_rd = admin_read()
        can_tasks = can_edit or (current_role() == "employee")

        if use_job_tabs and selected_job:
            edit_jid = str(selected_job.get("id") or "").strip()
            jl = job_row_select_label(selected_job)
            try:
                from app.pages.job_database_job_tasks import render_job_cost_tab, render_job_tasks_tab
            except ImportError:
                from pages.job_database_job_tasks import render_job_cost_tab, render_job_tasks_tab  # type: ignore

            st.session_state.setdefault("job_db_detail_panel", "Overview")
            st.radio(
                "Job sections",
                ["Overview", "Tasks", "Cost"],
                horizontal=True,
                key="job_db_detail_panel",
                label_visibility="collapsed",
            )
            _job_detail_panel = str(st.session_state.get("job_db_detail_panel") or "Overview").strip()

            if _job_detail_panel == "Tasks":
                render_job_tasks_tab(job_id=edit_jid, job_label=jl, can_edit_tasks=can_tasks, admin_read=admin_rd)
            elif _job_detail_panel == "Cost":
                render_job_cost_tab(job_id=edit_jid, job_row=selected_job)

        if (not use_job_tabs) or _job_detail_panel == "Overview":
            linked_estimate = ""
            estimate_options = build_estimate_options(
                estimates=estimates,
                estimate_label_map=estimate_label_map,
                selected_job=selected_job,
                estimate_detail=estimate_detail,
                customers=customers,
                customer_name_by_id=customer_name_by_id,
            )
            if use_job_tabs and selected_job:
                linked_estimate = _render_estimate_summary_overview(
                    selected_job=selected_job,
                    estimate_options=estimate_options,
                    estimate_detail=estimate_detail,
                    estimate_label_map=estimate_label_map,
                    estimate_quote_by_id=estimate_quote_by_id,
                    customers=customers,
                    customer_name_by_id=customer_name_by_id,
                    can_edit=can_edit,
                )

            customer_options: dict[str, str] = {}
            for c in customers:
                nm = str(c.get("customer_name") or "").strip()
                cid_c = str(c.get("id") or "").strip()
                if nm and cid_c:
                    customer_options[nm] = cid_c

            def current_value(field_name: str, default: Any = "") -> Any:
                if selected_job:
                    v = selected_job.get(field_name, default)
                    return "" if v is None else v
                return default

            _ro = not can_edit

            st.markdown("#### Customer & job")
            c1, c2 = st.columns(2, gap="small")
            cust_keys = [""] + sorted(customer_options.keys())
            selected_cust_name = ""
            if selected_job:
                scid = str(selected_job.get("customer_id") or "").strip()
                if scid:
                    selected_cust_name = _customer_display_name(scid, customers, customer_name_by_id)
                    if selected_cust_name and selected_cust_name not in customer_options:
                        customer_options[selected_cust_name] = scid
                        cust_keys = [""] + sorted(customer_options.keys())
            cust_index = cust_keys.index(selected_cust_name) if selected_cust_name in cust_keys else 0
            customer_name = c1.selectbox("Customer", cust_keys, index=cust_index, disabled=_ro, key="job_form_customer")
            job_name = c2.text_input("Job Name", value=current_value("job_name"), disabled=_ro, key="job_form_job_name")

            selected_contact_id: str | None = None
            selected_customer_location_id: str | None = None
            cust_uuid = customer_options.get(customer_name) if customer_name else None

            if has_customer_location_column:
                try:
                    from services.customer_locations import fetch_locations_for_customer, location_option_label
                except ImportError:
                    from app.services.customer_locations import fetch_locations_for_customer, location_option_label  # type: ignore

                if cust_uuid:
                    loc_rows = fetch_locations_for_customer(str(cust_uuid), admin_read=admin_rd, include_inactive=False)
                    cur_lid = str(current_value("customer_location_id") or "").strip()
                    if cur_lid:
                        have = {str(r.get("id") or "") for r in loc_rows}
                        if cur_lid not in have:
                            orphan = fetch_one("customer_locations", {"id": cur_lid})
                            if orphan:
                                loc_rows = [orphan] + list(loc_rows)
                    labels = ["(none)"] + [location_option_label(r) for r in loc_rows]
                    lids: list[str | None] = [None] + [str(r["id"]) for r in loc_rows if r.get("id")]
                    try:
                        lix = lids.index(cur_lid) if cur_lid else 0
                    except ValueError:
                        lix = 0
                    lix = min(max(lix, 0), len(labels) - 1)
                    loc_pick = st.selectbox(
                        "Job site",
                        options=list(range(len(labels))),
                        index=lix,
                        format_func=lambda i: labels[i],
                        disabled=_ro,
                        key=f"job_form_custloc_{cust_uuid}",
                        help="Optional: saved customer site from the Customers tab. Contacts are filtered by site.",
                    )
                    selected_customer_location_id = lids[int(loc_pick)]
                else:
                    st.caption("Select a customer to choose a job site.")

            if cust_uuid:
                inject_contact_picker_styles()
                loc_scope = str(selected_customer_location_id or "").strip() or None
                contacts = fetch_contacts_for_job_database(str(cust_uuid), loc_scope)
                cur_ct = str(current_value("customer_contact_id") or "").strip()
                if cur_ct:
                    cids = {str(c.get("id") or "") for c in contacts}
                    if cur_ct not in cids:
                        orphan = fetch_contact_by_id(cur_ct)
                        if orphan:
                            contacts = [orphan] + contacts
                if not contacts:
                    st.caption("No contacts found for this customer / site.")
                    render_contact_quick_add_when_empty(
                        customer_id=str(cust_uuid),
                        key_prefix="job",
                        disabled=_ro,
                        customer_location_id=loc_scope,
                    )
                    selected_contact_id = None
                else:
                    by_id = {str(c.get("id") or ""): c for c in contacts}
                    chosen_id: str | None = cur_ct if cur_ct in by_id else None
                    if chosen_id is None:
                        primary = next((c for c in contacts if c.get("is_primary")), None)
                        if primary and primary.get("id"):
                            chosen_id = str(primary["id"])
                        elif len(contacts) == 1 and contacts[0].get("id"):
                            chosen_id = str(contacts[0]["id"])
                    ct_labels = ["(none)"] + [contact_option_label(c) for c in contacts]
                    ct_ids: list[str | None] = [None] + [str(c["id"]) for c in contacts]
                    try:
                        ct_idx = ct_ids.index(str(chosen_id)) if chosen_id else 0
                    except ValueError:
                        ct_idx = 0
                        chosen_id = None
                    ct_idx = min(max(ct_idx, 0), len(ct_labels) - 1)
                    loc_key = loc_scope or "none"
                    ct_sel = st.selectbox(
                        "Contact",
                        options=list(range(len(ct_labels))),
                        index=ct_idx,
                        format_func=lambda i: ct_labels[i],
                        disabled=_ro,
                        key=f"job_form_contact_{cust_uuid}_{loc_key}",
                        help="Optional: primary contact for this job (site + company-wide contacts).",
                    )
                    selected_contact_id = ct_ids[int(ct_sel)]
                    render_contact_detail_preview(by_id.get(str(selected_contact_id or "")))
            else:
                st.caption("Select a customer to choose a contact.")

            st.markdown("#### Job #")
            if has_job_number_column and selected_job:
                st.text_input("Job #", value=str(current_value("job_number") or ""), disabled=True, help="Assigned when the job was created.", key="job_form_job_number")
            elif has_job_number_column and mode == "add":
                suggested_jn = next_job_number()
                st.caption("Suggested job number is prefilled. You can override it.")
                st.caption(f"Suggested: **{suggested_jn}**")
                if "job_number_manual_input" not in st.session_state:
                    st.session_state["job_number_manual_input"] = suggested_jn
                st.text_input("Job #", key="job_number_manual_input", help="Leave the suggested value or type a custom job number.", label_visibility="collapsed")

            location = str(current_value("location") or "").strip()

            if use_job_tabs and selected_job:
                st.markdown("#### Status")
            else:
                st.markdown("#### Status & linked estimate")
                if mode == "add":
                    st.caption("*Linked estimate* is optional — leave the first row selected for a job with no quote.")

            status_options = list(JOB_STATUSES)
            current_status = str(current_value("status", "Draft") or "Draft").strip() or "Draft"
            if current_status not in status_options:
                status_options = status_options + [current_status]
            status_idx = status_options.index(current_status)

            if use_job_tabs and selected_job:
                status = st.selectbox("Status", status_options, index=status_idx, disabled=_ro, key="job_form_status")
            else:
                c5, c6 = st.columns(2, gap="small")
                status = c5.selectbox("Status", status_options, index=status_idx, disabled=_ro, key="job_form_status")
                estimate_labels = [""] + [k for k in estimate_options.keys() if k]
                current_estimate_label = ""
                if selected_job and selected_job.get("estimate_id"):
                    _seid = str(selected_job["estimate_id"])
                    current_estimate_label = estimate_label_map.get(_seid, "")
                    if not current_estimate_label:
                        for lab, eid_opt in estimate_options.items():
                            if lab and str(eid_opt) == _seid:
                                current_estimate_label = lab
                                break
                _link_lbl = "Linked estimate (optional)" if mode == "add" else "Linked estimate"
                linked_estimate = c6.selectbox(
                    _link_lbl,
                    estimate_labels,
                    index=estimate_labels.index(current_estimate_label) if current_estimate_label in estimate_labels else 0,
                    disabled=_ro,
                    key="job_form_linked_estimate",
                    help="Leave blank for a standalone job. Pick a row only if attaching to an existing estimate.",
                )

            st.markdown("#### Awarded amount")
            awarded_amount = st.number_input("Awarded Amount", min_value=0.0, value=float(current_value("awarded_amount", 0) or 0), step=100.0, format="%.2f", disabled=_ro, key="job_form_awarded_amount")

            st.markdown("#### Notes")
            notes = st.text_area("Notes", value=current_value("notes"), disabled=_ro, height=80, key="job_form_notes")

            if not can_edit:
                if mode == "add":
                    st.info("Only office roles can create jobs.")
                    return
                st.caption("View only — contact the office to change job details.")

            b1, b2 = st.columns(2, gap="small")
            if mode == "add":
                if b1.button("Create Job", type="primary", use_container_width=True, disabled=_ro, key="job_form_create"):
                    if not customer_name:
                        st.error("Customer required")
                        st.stop()
                    if not job_name.strip():
                        st.error("Job Name required")
                        st.stop()
                    linked_eid = _linked_estimate_id(estimate_options, linked_estimate)
                    payload: dict[str, Any] = {
                        "customer_id": customer_options[customer_name],
                        "customer_contact_id": selected_contact_id,
                        "job_name": job_name.strip(),
                        "location": location.strip(),
                        "status": status,
                        "estimate_id": linked_eid,
                        "awarded_amount": float(awarded_amount or 0),
                        "notes": notes.strip(),
                    }
                    if has_customer_location_column:
                        payload["customer_location_id"] = selected_customer_location_id
                    if has_job_number_column:
                        final_job_number = str(st.session_state.get("job_number_manual_input") or "").strip()
                        if not final_job_number:
                            st.error("Enter a job number.")
                            st.stop()
                        try:
                            dup = fetch_by_match_admin("jobs", {"job_number": final_job_number}, columns="id,job_number", limit=1)
                        except Exception:
                            dup = fetch_by_match("jobs", {"job_number": final_job_number}, columns="id,job_number", limit=1)
                        if dup:
                            st.error("Job number already exists.")
                            st.stop()
                        payload["job_number"] = final_job_number
                    insert_row_admin("jobs", payload)
                    try:
                        from data_cache import clear_session_table_cache
                    except ImportError:
                        from app.data_cache import clear_session_table_cache  # type: ignore
                    clear_session_table_cache()
                    bump_data_version()
                    clear_job_mode()
                    st.success("Job created.")
                    st.rerun()
            else:
                if b1.button("Update Job", type="primary", use_container_width=True, disabled=_ro, key="job_form_update"):
                    if not selected_job:
                        st.error("Select a job first.")
                        st.stop()
                    if not customer_name:
                        st.error("Customer required")
                        st.stop()
                    if not job_name.strip():
                        st.error("Job Name required")
                        st.stop()
                    linked_eid = _linked_estimate_id(estimate_options, linked_estimate)
                    payload = {
                        "customer_id": customer_options[customer_name],
                        "customer_contact_id": selected_contact_id,
                        "job_name": job_name.strip(),
                        "location": location.strip(),
                        "status": status,
                        "estimate_id": linked_eid,
                        "awarded_amount": float(awarded_amount or 0),
                        "notes": notes.strip(),
                    }
                    if has_customer_location_column:
                        payload["customer_location_id"] = selected_customer_location_id
                    update_rows_admin("jobs", payload, {"id": selected_job["id"]})
                    try:
                        from data_cache import clear_session_table_cache
                    except ImportError:
                        from app.data_cache import clear_session_table_cache  # type: ignore
                    clear_session_table_cache()
                    bump_data_version()
                    clear_job_mode()
                    st.success("Job updated.")
                    st.rerun()

            if b2.button("Cancel", use_container_width=True, key="job_form_cancel"):
                clear_job_mode()
                st.rerun()

            if mode == "edit" and selected_job:
                _render_email_settings_expander(selected_job=selected_job, can_edit=can_edit)
                _render_weekly_timesheets_expander(selected_job=selected_job, can_edit=can_edit)
