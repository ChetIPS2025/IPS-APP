from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from branding import render_header

from auth import current_profile, current_role
from db import (
    create_signed_url,
    fetch_by_match,
    fetch_by_match_admin,
    fetch_one,
    fetch_table,
    fetch_table_admin,
    fetch_table_with_order_fallback,
    insert_row_admin,
    next_quote_number,
    update_rows_admin,
    upload_bytes,
)
from proposal import try_convert_proposal_docx_to_pdf

try:
    from services.job_service import job_number_display, job_row_select_label
except ImportError:
    from app.services.job_service import job_number_display, job_row_select_label  # type: ignore

from app.estimate.calculations import (
    _D0,
    _dec,
    _is_missing_number,
    _num0,
    _q2,
    compute_totals,
    money,
    money_db,
    money_str,
)
from app.estimate.customer_job import (
    create_or_get_job_by_name,
    resolve_estimate_linked_job,
    _customer_dropdown_labels,
    _fetch_contacts_for_estimate_editor,
    _fetch_customer_row_by_id_for_editor,
    _fetch_customers_for_editor,
    _norm_name_key,
    _top_matches,
)
from app.estimate.defaults import (
    FINAL_STATUSES,
    _estimate_table_column_names,
    _fetch_prepared_by_choices,
    _normalize_prepared_by_id_value,
    _payload_prepared_by_for_db,
    blank_estimate,
    coalesce_imported_estimate,
    ensure_numeric_defaults,
    merge_estimate_row_scalar_fields_into_editor,
    parse_estimate_json_bytes,
)
from app.estimate.equipment import (
    build_equipment_picker_maps,
    enrich_equipment_rows_from_assets,
    load_estimate_equipment_from_assets,
    _equipment_core_with_picker_labels,
    _equipment_rows_core_for_editor,
)
from app.estimate.persistence import (
    _duplicate_quote_message,
    attach_pending_pdf_import_source,
    insert_imported_estimate,
    persist_estimate,
    upload_generated_export,
    validate_import_customer_id,
)
from app.estimate.proposal_exports import (
    PROPOSAL_PDF_UNAVAILABLE_SHORT,
    _build_proposal_docx_and_vals,
    _inject_proposal_preview_styles,
    _proposal_export_kwargs,
    _render_proposal_preview_html,
    proposal_preview_html,
)


def _materials_rows_for_editor(rows: list | None, *, materials_options: list[str]) -> list[dict]:
    """
    Build rows with only ``item`` + ``qty`` for ``st.data_editor``.

    Imports and legacy JSON often add ``quantity``, ``unit_price``, ``description``, etc.
    Those extra keys became extra dataframe columns, so users had to fill Qty twice
    (or fight duplicate-looking columns).
    """
    out: list[dict] = []
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        item = raw.get("item") if raw.get("item") is not None else raw.get("item_key")
        item_s = str(item or "").strip()
        q = raw.get("qty")
        if _is_missing_number(q) and not _is_missing_number(raw.get("quantity")):
            try:
                q = float(raw.get("quantity") or 0)
            except (TypeError, ValueError):
                q = 0.0
        try:
            qf = float(q or 0)
        except (TypeError, ValueError):
            qf = 0.0
        out.append({"item": item_s, "qty": qf})
    if not out and materials_options:
        return [{"item": materials_options[0], "qty": 0.0}]
    if not out:
        return [{"item": "", "qty": 0.0}]
    return out


def _labor_rows_for_editor(rows: list | None, *, labor_options: list[str]) -> list[dict]:
    """
    Build rows with only the five labor editor columns.

    Legacy rows may include a single ``hours`` field or other keys that created
    extra columns next to ST/OT hrs per day.
    """
    keys_num = ("headcount", "st_hours_per_day", "ot_hours_per_day", "days")
    out: list[dict] = []
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        d = {k: _num0(raw.get(k)) for k in keys_num}
        d["classification"] = str(raw.get("classification") or "").strip()
        if (
            d["headcount"] == 0.0
            and d["st_hours_per_day"] == 0.0
            and d["ot_hours_per_day"] == 0.0
            and d["days"] == 0.0
            and not _is_missing_number(raw.get("hours"))
        ):
            try:
                h = float(raw.get("hours") or 0)
            except (TypeError, ValueError):
                h = 0.0
            if h > 0.0:
                d["headcount"] = 1.0
                d["st_hours_per_day"] = h
                d["days"] = 1.0
        out.append(d)
    if not out and labor_options:
        return [
            {
                "classification": labor_options[0],
                "headcount": 0.0,
                "st_hours_per_day": 0.0,
                "ot_hours_per_day": 0.0,
                "days": 0.0,
            }
        ]
    if not out:
        return [
            {
                "classification": "",
                "headcount": 0.0,
                "st_hours_per_day": 0.0,
                "ot_hours_per_day": 0.0,
                "days": 0.0,
            }
        ]
    return out

def ensure_state():
    st.session_state.setdefault("estimate_editor_state", blank_estimate())
    st.session_state.setdefault("loaded_estimate_id", None)
    st.session_state.setdefault("estimate_editor_quote_ready", False)
    st.session_state.setdefault("est_eq_rental_only", True)
    # Editing indices for line-item row-card forms (avoid re-entry / widget resets)
    st.session_state.setdefault("est_material_edit_idx", None)
    st.session_state.setdefault("est_labor_edit_idx", None)
    st.session_state.setdefault("est_equipment_edit_idx", None)
    st.session_state.setdefault("est_travel_edit_kind", None)
    # Quick-add defaults (remember last used)
    st.session_state.setdefault("est_material_last_category", "All")
    st.session_state.setdefault("est_material_last_item", "")
    st.session_state.setdefault("est_material_last_qty", 1.0)
    st.session_state.setdefault("est_labor_last_classification", "")
    st.session_state.setdefault("est_labor_last_headcount", 1.0)
    st.session_state.setdefault("est_labor_last_st_hours", 8.0)
    st.session_state.setdefault("est_labor_last_ot_hours", 0.0)
    st.session_state.setdefault("est_labor_last_days", 1.0)
    st.session_state.setdefault("est_equipment_last_item", "")
    st.session_state.setdefault("est_equipment_last_qty", 1.0)
    st.session_state.setdefault("est_equipment_last_basis", "Day")
    st.session_state.setdefault("est_equipment_last_duration", 1.0)
    st.session_state.setdefault("est_travel_last_kind", "Mileage")
    st.session_state.setdefault("est_travel_last_amount", 0.0)
    st.session_state.setdefault("est_travel_last_miles", 0.0)
    st.session_state.setdefault("est_travel_last_mileage_rate", 0.0)
    st.session_state.setdefault("est_travel_last_hotel_nights", 0.0)
    st.session_state.setdefault("est_travel_last_hotel_rate", 0.0)
    # Pending uploads (kept stable across reruns; uploaded on Save)
    st.session_state.setdefault("est_pending_quote_attachments", [])
    st.session_state.setdefault("est_pending_po_attachment", None)
    st.session_state.setdefault("est_revision_note", "")
    est0 = st.session_state["estimate_editor_state"]
    # Legacy widget keys from the old free-text customer field (avoid stale session state).
    st.session_state.pop("est_customer_query", None)
    st.session_state.pop("est_customer_match_pick", None)
    if st.session_state.pop("est_embed_pdf_preview", None):
        st.session_state["est_embed_proposal_preview"] = True
    st.session_state.pop("ips_proposal_template_bytes", None)
    # Defensive defaults: some imported legacy payloads may omit keys or set them to null.
    est0.setdefault("materials", [])
    est0.setdefault("labor", [])
    est0.setdefault("equipment", [])
    est0.setdefault("travel", {})
    est0.setdefault("controls", {})
    ensure_numeric_defaults(est0)
    est0.setdefault("prepared_by_id", "")
    est0.setdefault("prepared_by_name", "")
    est0.setdefault("contact_name", "")
    est0["prepared_by_id"] = _normalize_prepared_by_id_value(str(est0.get("prepared_by_id") or ""))
    # Quote numbers must never change on rerun. We only allocate a new number at commit time
    # (Save / Submit / Approve / Award) for brand-new estimates when quote_number is blank.
    qn = str(est0.get("quote_number", "") or "").strip()
    st.session_state["estimate_editor_quote_ready"] = bool(qn)


_PREP_NONE = "__prep_none__"
_LEGACY_UNLISTED = "__legacy_unlisted__"


def _render_estimate_prepared_by_field(est: dict, *, is_locked: bool) -> None:
    """Compact select for **Estimate Prepared By** (profiles + employees)."""
    roster = _fetch_prepared_by_choices()
    label_by_key: dict[str, str] = {_PREP_NONE: "—"}
    for k, lab in roster:
        label_by_key[k] = lab
    keys: list[str] = [_PREP_NONE] + [k for k, _ in roster]

    cur_id = _normalize_prepared_by_id_value(str(est.get("prepared_by_id") or "").strip())
    cur_name = str(est.get("prepared_by_name") or "").strip()

    if cur_id and cur_id not in label_by_key:
        keys.insert(1, cur_id)
        label_by_key[cur_id] = cur_name or cur_id or "(saved preparer)"
    if not cur_id and cur_name:
        keys.insert(1, _LEGACY_UNLISTED)
        label_by_key[_LEGACY_UNLISTED] = cur_name

    if cur_id and cur_id in label_by_key:
        sel = cur_id
    elif cur_id:
        sel = cur_id
    elif cur_name:
        sel = _LEGACY_UNLISTED
    else:
        sel = _PREP_NONE

    try:
        default_idx = keys.index(sel)
    except ValueError:
        default_idx = 0

    chosen = st.selectbox(
        "Estimate Prepared By",
        options=keys,
        index=min(default_idx, len(keys) - 1),
        format_func=lambda k: label_by_key.get(k, k),
        disabled=is_locked,
        key="est_prepared_by_select_main",
        help="Shown on proposals and reports. Pulled from Users (profiles) and Employees.",
    )
    if chosen == _PREP_NONE:
        est["prepared_by_id"] = ""
        est["prepared_by_name"] = ""
    elif chosen == _LEGACY_UNLISTED:
        est["prepared_by_id"] = ""
        est["prepared_by_name"] = cur_name
    else:
        est["prepared_by_id"] = chosen
        est["prepared_by_name"] = str(label_by_key.get(chosen, "") or "").strip()


def _imported_estimate_missing_customer(est: dict, *, pending_pdf_import: bool) -> bool:
    """True when editor state is an import that still needs a real ``customer_id``."""
    if est.get("customer_id"):
        return False
    if pending_pdf_import:
        return True
    meta = est.get("import_meta") if isinstance(est.get("import_meta"), dict) else {}
    if meta.get("vendor_quote"):
        return True
    return False

def render_estimate_editor(*, embedded: bool = False) -> None:
    ensure_state()
    est = st.session_state["estimate_editor_state"]

    customers = _fetch_customers_for_editor()
    cur_cust_id = str(est.get("customer_id") or "").strip()
    ids_have = {str(c["id"]) for c in customers if c.get("id")}
    if cur_cust_id and cur_cust_id not in ids_have:
        extra = _fetch_customer_row_by_id_for_editor(cur_cust_id)
        if extra and extra.get("id"):
            customers = [extra] + list(customers)
        elif cur_cust_id:
            customers = [
                {"id": cur_cust_id, "customer_name": "[Customer not found — check Customers tab]"},
            ] + list(customers)

    jobs = fetch_table("jobs", columns="id,job_name,customer_id,job_number", limit=1000, order_by="job_number")
    materials_catalog = fetch_table("materials_catalog", limit=3000, order_by="item_key")
    labor_rates = fetch_table("labor_rates", limit=1000, order_by="classification")
    equipment_pricing = load_estimate_equipment_from_assets()
    existing_estimates = fetch_table("estimates", columns="id,quote_number,status,updated_at,revision_number", limit=1000, order_by="updated_at")

    customer_name_by_id = {str(c["id"]): str(c.get("customer_name") or "").strip() for c in customers if c.get("id")}
    jobs_by_customer = {}
    for j in jobs:
        jobs_by_customer.setdefault(j.get("customer_id"), []).append(j)
    materials_options = [m["item_key"] for m in materials_catalog]
    labor_options = [r["classification"] for r in labor_rates]

    if not embedded:
        render_header("Estimate Editor")
        st.caption(
            "Supabase-backed estimator logic with proposal export and approval workflow."
        )
    else:
        # Estimates page already called render_header; avoid duplicate logo/title.
        st.caption("Tabs below · list on the Estimates page opens other quotes.")
        st.markdown('<span class="ips-estimate-editor-root"></span>', unsafe_allow_html=True)

    current_status = est.get("status", "draft")
    is_locked = current_status in FINAL_STATUSES and current_role() != "admin"
    if is_locked:
        st.warning(f"This estimate is locked because status is '{current_status}'. Admin can still edit it.")

    if not embedded:
        open_col, new_col, gen_col = st.columns([2, 1, 1])
        with open_col:
            choices = ["-- New Estimate --"] + [f'{e["quote_number"]} | {e.get("status","")} | rev {e.get("revision_number",0)}' for e in existing_estimates]
            selected_quote = st.selectbox("Open Existing Estimate", choices)
            if selected_quote != "-- New Estimate --" and st.button("Load Selected Estimate", use_container_width=True):
                selected_id = next(e["id"] for e in existing_estimates if f'{e["quote_number"]} | {e.get("status","")} | rev {e.get("revision_number",0)}' == selected_quote)
                row = fetch_one("estimates", {"id": selected_id})
                if row:
                    loaded = row.get("estimate_json") or {}
                    loaded.update({
                        "quote_number": row.get("quote_number", ""),
                        "customer_id": row.get("customer_id"),
                        "customer_contact_id": row.get("customer_contact_id"),
                        "job_id": row.get("job_id"),
                        "status": row.get("status", "draft"),
                        "scope_of_work": row.get("scope_of_work", ""),
                        "exclusions": row.get("exclusions", ""),
                        "additional_charges": row.get("additional_charges", ""),
                        "customer_responsibilities": row.get("customer_responsibilities", ""),
                        "job_received": row.get("job_received", False),
                        "po_number": row.get("po_number", ""),
                        "po_date": str(row.get("po_date") or ""),
                        "po_amount": float(row.get("po_amount", 0) or 0),
                    })
                    merge_estimate_row_scalar_fields_into_editor(row, loaded)
                    ensure_numeric_defaults(loaded)
                    st.session_state["estimate_editor_state"] = loaded
                    st.session_state["loaded_estimate_id"] = selected_id
                    st.session_state["estimate_editor_quote_ready"] = True
                    st.rerun()
        with new_col:
            if st.button("New Blank Estimate", use_container_width=True):
                st.session_state["estimate_editor_state"] = ensure_numeric_defaults(blank_estimate())
                st.session_state["loaded_estimate_id"] = None
                st.session_state["estimate_editor_quote_ready"] = False
                st.rerun()
        with gen_col:
            can_generate_qn = not st.session_state.get("loaded_estimate_id") and not str(
                est.get("quote_number", "") or ""
            ).strip()
            if st.button("Generate Quote Number", use_container_width=True, disabled=not can_generate_qn):
                est["quote_number"] = next_quote_number()
                st.rerun()
    else:
        if st.session_state.get("estimate_pending_import_pdf"):
            st.info(
                "PDF import — edit **Materials**, **Labor**, and **Equipment** in the tabs below, "
                "then **Review / Save → Save Estimate**."
            )
        sug = st.session_state.get("estimate_pdf_suggestions") or {}
        if sug:
            st.markdown("##### PDF import — customer & job suggestions")
            st.caption(
                "Fuzzy matches from your PDF text. Nothing is saved until you **Accept** a suggestion "
                "or choose a **Customer** / **Job** below, then **Save Estimate**."
            )
            g1, g2 = st.columns(2)
            with g1:
                st.text_input(
                    "Extracted customer (from PDF)",
                    value=str(sug.get("customer_guess") or ""),
                    disabled=True,
                    key="est_pdf_guess_cust",
                )
                sid = sug.get("suggested_customer_id")
                if sid and not sug.get("customer_dismissed"):
                    st.markdown(
                        f"**Suggested customer:** {sug.get('suggested_customer_name') or ''}  \n"
                        f"{sug.get('customer_note') or ''}"
                    )
                    ac1, ac2 = st.columns(2)
                    if ac1.button("Accept customer", key="est_pdf_accept_customer"):
                        est["customer_id"] = sid
                        ns = dict(sug)
                        ns["customer_applied"] = True
                        st.session_state["estimate_pdf_suggestions"] = ns
                        st.rerun()
                    if ac2.button("Dismiss suggestion", key="est_pdf_dismiss_customer"):
                        ns = dict(sug)
                        ns["customer_dismissed"] = True
                        st.session_state["estimate_pdf_suggestions"] = ns
                        st.rerun()
                elif sid and sug.get("customer_dismissed"):
                    st.caption("Customer suggestion dismissed — use the **Customer** field below.")
                elif not sid:
                    st.caption(sug.get("customer_note") or "No customer match.")
            with g2:
                st.text_input(
                    "Extracted job / project (from PDF)",
                    value=str(sug.get("job_guess") or ""),
                    disabled=True,
                    key="est_pdf_guess_job",
                )
                jid = sug.get("suggested_job_id")
                if jid and not sug.get("job_dismissed"):
                    st.markdown(
                        f"**Suggested job:** {sug.get('suggested_job_name') or ''}  \n"
                        f"{sug.get('job_note') or ''}"
                    )
                    aj1, aj2 = st.columns(2)
                    if aj1.button("Accept job", key="est_pdf_accept_job"):
                        est["job_id"] = jid
                        ns = dict(sug)
                        ns["job_applied"] = True
                        st.session_state["estimate_pdf_suggestions"] = ns
                        st.rerun()
                    if aj2.button("Dismiss job suggestion", key="est_pdf_dismiss_job"):
                        ns = dict(sug)
                        ns["job_dismissed"] = True
                        st.session_state["estimate_pdf_suggestions"] = ns
                        st.rerun()
                elif jid and sug.get("job_dismissed"):
                    st.caption("Job suggestion dismissed — use the **Job** field below.")
                elif not jid:
                    st.caption(sug.get("job_note") or "No job match.")
        g1, g2 = st.columns([4, 1])
        with g2:
            can_generate_qn = not st.session_state.get("loaded_estimate_id") and not str(
                est.get("quote_number", "") or ""
            ).strip()
            if st.button(
                "Generate Quote Number",
                use_container_width=True,
                key="est_embed_gen_qn",
                disabled=not can_generate_qn,
            ):
                est["quote_number"] = next_quote_number()
                st.rerun()

    totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
    with st.container(border=True):
        st.markdown('<span class="ips-estimate-metrics-strip"></span>', unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5, gap="small")
        m1.metric("Materials", money(totals["material_sell_basis"]))
        m2.metric("Labor", money(totals["labor_total"]))
        m3.metric("Equipment", money(totals["equipment_total"]))
        m4.metric("Travel", money(totals["travel_total"]))
        m5.metric("Proposal", money(totals["proposal_total"]))

    if embedded:
        _pe = _proposal_export_kwargs(est, customer_name_by_id, jobs)
        vals, embed_docx, embed_docx_err = _build_proposal_docx_and_vals(est, totals, _pe)

        _, _emb_actions, _ = st.columns([0.2, 1.0, 0.2])
        eb1, eb2, eb3 = _emb_actions.columns([1, 1, 1], gap="small")
        with eb1:
            if st.button("Preview", use_container_width=True, key="est_embed_preview_btn"):
                st.session_state["est_embed_proposal_preview"] = True
        with eb2:
            if embed_docx is not None:
                st.download_button(
                    "Download Proposal (Word)",
                    data=embed_docx,
                    file_name=f"{est.get('quote_number') or 'proposal'}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary",
                    key="est_embed_dl_docx_main",
                )
        with eb3:
            if embed_docx is not None:
                if st.button("Export PDF", use_container_width=True, key="est_embed_export_btn"):
                    eid = st.session_state.get("loaded_estimate_id")
                    if not eid:
                        st.caption("Save the estimate first to store the PDF on this quote.")
                    else:
                        embed_pdf, _conv = try_convert_proposal_docx_to_pdf(embed_docx)
                        if embed_pdf is None:
                            st.caption(PROPOSAL_PDF_UNAVAILABLE_SHORT)
                        else:
                            upload_generated_export(
                                str(eid),
                                f"{est.get('quote_number') or 'proposal'}.pdf",
                                embed_pdf,
                                "application/pdf",
                                "generated_pdf",
                            )
                            st.success("PDF saved to storage and linked to this estimate.")

        if embed_docx_err and embed_docx is None:
            st.error(embed_docx_err)
        if st.session_state.get("est_embed_proposal_preview"):
            with st.expander("Proposal preview", expanded=True):
                if embed_docx is not None:
                    preview_html = proposal_preview_html(embed_docx, fallback_vals=vals)
                    _render_proposal_preview_html(
                        preview_html,
                        caption="From the generated Word document (same bytes as **Download Proposal (Word)**).",
                    )
                else:
                    st.caption("Build the Word proposal first to enable preview.")
            if st.button("Hide preview", use_container_width=True, key="est_embed_hide_preview"):
                st.session_state["est_embed_proposal_preview"] = False
                st.rerun()

    if _imported_estimate_missing_customer(
        est,
        pending_pdf_import=bool(st.session_state.get("estimate_pending_import_pdf")),
    ):
        st.warning(
            "This imported estimate is not linked to a customer yet. "
            "Select a saved customer from the list below (add one in the **Customers** tab if needed), then save."
        )

    # Row 1: Quote | Status | Customer — single compact row (no full-width fields).
    q_col, stat_col, cust_col = st.columns([1, 1, 2.2], gap="small")
    quote_locked_after_save = bool(
        str(st.session_state.get("loaded_estimate_id") or "").strip()
        and str(est.get("quote_number", "") or "").strip()
    )
    with q_col:
        est["quote_number"] = st.text_input(
            "Quote Number",
            value=est.get("quote_number", ""),
            disabled=(is_locked or quote_locked_after_save),
        )
        if quote_locked_after_save and not is_locked:
            st.caption("Locked after first save.")

    with stat_col:
        statuses = ["draft", "submitted", "approved", "awarded"]
        est["status"] = st.selectbox(
            "Status",
            statuses,
            index=statuses.index(est.get("status", "draft")) if est.get("status", "draft") in statuses else 0,
            disabled=is_locked,
        )

    with cust_col:
        _EMPTY_CUSTOMER = "__est_no_customer__"
        rows_for_ui = [r for r in customers if r.get("id")]
        if not rows_for_ui:
            st.warning(
                "No customers in the database. Add a customer from the **Customers** tab, then return here and select it."
            )
            if not is_locked:
                est["customer_id"] = None
        else:
            ordered_ids, id_to_label = _customer_dropdown_labels(rows_for_ui)
            options = [_EMPTY_CUSTOMER] + ordered_ids

            def _fmt_customer(cid: str) -> str:
                if cid == _EMPTY_CUSTOMER:
                    return "— Select customer —"
                return id_to_label.get(cid, cid)

            cur_sel = str(est.get("customer_id") or "").strip()
            default_idx = options.index(cur_sel) if cur_sel in options else 0
            sel = st.selectbox(
                "Customer",
                options=options,
                index=default_idx,
                format_func=_fmt_customer,
                disabled=is_locked,
                key="est_customer_select_id",
                help="Only saved customers from the Customers tab. Add new companies there first.",
            )
            if sel == _EMPTY_CUSTOMER:
                if not is_locked:
                    est["customer_id"] = None
                    est["customer_contact_id"] = None
                    est["contact_name"] = ""
            else:
                est["customer_id"] = sel

    # After customer is chosen: clear contact when customer changes (same run as the selectbox).
    prev_cust = st.session_state.get("_est_prev_customer_id")
    cur_cust = est.get("customer_id")
    if prev_cust is not None and cur_cust != prev_cust:
        est["customer_contact_id"] = None
        est["contact_name"] = ""
    st.session_state["_est_prev_customer_id"] = cur_cust

    matching_jobs = jobs_by_customer.get(est.get("customer_id"), []) if est.get("customer_id") else jobs
    job_names = [str(j.get("job_name") or "").strip() for j in matching_jobs if str(j.get("job_name") or "").strip()]
    job_id_by_norm: dict[str, str] = {}
    for j in matching_jobs:
        nm = str(j.get("job_name") or "").strip()
        if not nm:
            continue
        job_id_by_norm[_norm_name_key(nm)] = str(j.get("id") or "")

    # Row 2: Contact | Job | Prepared by — second compact row.
    row2_contact, row2_job, row2_prep = st.columns([1, 1, 1], gap="small")
    est.setdefault("customer_contact_id", None)
    with row2_contact:
        if est.get("customer_id"):
            try:
                from services.customer_contacts import (
                    contact_none_option_label,
                    contact_option_label,
                    inject_contact_picker_styles,
                    render_contact_detail_preview,
                    render_contact_quick_add_when_empty,
                )
            except ImportError:
                from app.services.customer_contacts import (  # type: ignore
                    contact_none_option_label,
                    contact_option_label,
                    inject_contact_picker_styles,
                    render_contact_detail_preview,
                    render_contact_quick_add_when_empty,
                )

            inject_contact_picker_styles()
            cid_key = str(est.get("customer_id") or "").strip()
            contacts = _fetch_contacts_for_estimate_editor(cid_key)
            if not contacts:
                st.caption("No contacts found for this customer.")
                st.selectbox(
                    "Contact",
                    options=[0],
                    index=0,
                    format_func=lambda _: contact_none_option_label(),
                    disabled=is_locked,
                    key=f"est_contact_sel_empty_{cid_key}",
                    help="Optional: add contacts for this customer on the Customers tab.",
                )
                est["customer_contact_id"] = None
                est["contact_name"] = ""
                render_contact_quick_add_when_empty(
                    customer_id=cid_key,
                    key_prefix="est",
                    disabled=is_locked,
                )
            else:
                cur = str(est.get("customer_contact_id") or "").strip()
                by_id = {str(c.get("id") or ""): c for c in contacts}
                chosen_id: str | None = cur if cur in by_id else None
                if chosen_id is None:
                    primary = next((c for c in contacts if c.get("is_primary")), None)
                    if primary and primary.get("id"):
                        chosen_id = str(primary["id"])
                    elif len(contacts) == 1 and contacts[0].get("id"):
                        chosen_id = str(contacts[0]["id"])

                labels = [contact_none_option_label()] + [contact_option_label(c) for c in contacts]
                ids: list[str | None] = [None] + [str(c["id"]) for c in contacts]
                try:
                    idx = ids.index(chosen_id) if chosen_id is not None else 0
                except ValueError:
                    idx = 0
                idx = min(max(idx, 0), len(labels) - 1)
                ci = st.selectbox(
                    "Contact",
                    options=list(range(len(labels))),
                    index=idx,
                    format_func=lambda i: labels[i],
                    disabled=is_locked,
                    key=f"est_contact_sel_{cid_key}",
                    help="Only contacts linked to the selected customer. Optional for this quote.",
                )
                est["customer_contact_id"] = ids[int(ci)]
                _sel_cid = est["customer_contact_id"]
                if _sel_cid:
                    _row = by_id.get(str(_sel_cid))
                    est["contact_name"] = (
                        str(_row.get("contact_name") or "").strip() if _row else ""
                    )
                else:
                    est["contact_name"] = ""

                render_contact_detail_preview(by_id.get(str(est.get("customer_contact_id") or "")))
        else:
            st.caption("Select a customer to choose a contact.")
            est["customer_contact_id"] = None
            est["contact_name"] = ""

    with row2_job:
        selected_job_name = next(
            (str(j.get("job_name") or "").strip() for j in matching_jobs if j.get("id") == est.get("job_id")), ""
        )
        job_initial = selected_job_name or str(st.session_state.get("est_job_query") or "")
        job_query = st.text_input(
            "Job",
            value=job_initial,
            disabled=is_locked,
            key="est_job_query",
            placeholder="Search or type a new job…",
            help=(
                "Type to search within the selected customer (when set). "
                "Jobs are **not** created during estimate save; create jobs only from explicit conversion actions "
                "(e.g. **Job Received** / **Create Job from Estimate**)."
            ),
        )
        job_norm = _norm_name_key(job_query)
        job_exact_id = job_id_by_norm.get(job_norm) if job_norm else None
        if job_exact_id:
            est["job_id"] = job_exact_id
            st.caption("Matched existing job.")
        elif job_norm:
            est["job_id"] = None
            st.caption("No exact match. Jobs are created only by explicit conversion actions.")

        job_matches = _top_matches(job_query, job_names, limit=7)
        if job_matches and not job_exact_id:
            job_pick = st.selectbox(
                "Close matches",
                [""] + job_matches,
                index=0,
                disabled=is_locked,
                key="est_job_match_pick",
                help="Pick an existing job to avoid creating a duplicate.",
            )
            if job_pick:
                st.session_state["est_job_query"] = job_pick
                st.rerun()

    with row2_prep:
        _render_estimate_prepared_by_field(est, is_locked=is_locked)

    try:
        from table_actions import inject_table_action_styles
    except ImportError:
        from app.table_actions import inject_table_action_styles  # type: ignore

    inject_table_action_styles()

    _loaded_eid = str(st.session_state.get("loaded_estimate_id") or "").strip() or None
    linked_job_id, linked_job_row = resolve_estimate_linked_job(est, jobs, _loaded_eid)
    if linked_job_id and linked_job_row is None:
        linked_job_row = fetch_one("jobs", {"id": linked_job_id}, columns="id,job_number,job_name")

    if linked_job_id:
        _jn = job_number_display((linked_job_row or {}).get("job_number"))
        _jnm = str((linked_job_row or {}).get("job_name") or "").strip()
        with st.container(border=True):
            st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
            _parts = ["**Linked job**"]
            if _jn:
                _parts.append(f"**{_jn}**")
            if _jnm:
                _parts.append(_jnm)
            st.markdown(" · ".join(_parts), unsafe_allow_html=True)

    tabs = st.tabs(["Materials", "Labor", "Equipment", "Travel", "Job Scope", "Attachments / P.O.", "Proposal", "Review / Save"])

    with tabs[0]:
        # Materials row cards + form-based add/edit to avoid "enter twice" UX.
        est.setdefault("materials", [])
        controls = est.get("controls", {}) or {}
        material_markup_dec = _dec(controls.get("material_markup_pct", 0) or 0)
        material_map = {m.get("item_key"): m for m in materials_catalog if isinstance(m, dict) and m.get("item_key")}

        # Optional category filter (resilient to schema differences).
        categories = sorted(
            {
                str(m.get("category") or "").strip()
                for m in materials_catalog
                if isinstance(m, dict) and str(m.get("category") or "").strip()
            }
        )
        cat_options = ["All"] + categories if categories else ["All"]

        st.caption("Category (narrow) → material → qty → add.")

        with st.form(key="est_material_add_form", clear_on_submit=True):
            # Remember last-used category when available.
            last_cat = str(st.session_state.get("est_material_last_category") or "All")
            cat_index = cat_options.index(last_cat) if last_cat in cat_options else 0
            ma1, ma2, ma3, ma4 = st.columns([0.65, 2.35, 0.4, 0.45], gap="small")
            with ma1:
                selected_cat = st.selectbox(
                    "Category",
                    options=cat_options,
                    index=cat_index,
                    disabled=is_locked,
                    key="est_material_add_category",
                    help="Optional filter. If your materials table has no category column, this stays as All.",
                )

            if selected_cat != "All":
                filtered_items = [
                    str(m.get("item_key") or "").strip()
                    for m in materials_catalog
                    if isinstance(m, dict)
                    and str(m.get("item_key") or "").strip()
                    and str(m.get("category") or "").strip() == selected_cat
                ]
            else:
                filtered_items = materials_options
            filtered_items = [x for x in filtered_items if x]
            if not filtered_items:
                filtered_items = [""]

            last_item = str(st.session_state.get("est_material_last_item") or "").strip()
            item_index = filtered_items.index(last_item) if last_item in filtered_items else 0
            with ma2:
                mat_add_item = st.selectbox(
                    "Material",
                    options=filtered_items,
                    index=item_index,
                    disabled=is_locked,
                    key="est_material_add_item",
                )
            with ma3:
                mat_add_qty = st.number_input(
                    "Qty",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_material_last_qty") or 1.0),
                    key="est_material_add_qty",
                )
            with ma4:
                st.markdown("")
                mat_add_submit = st.form_submit_button("Add", disabled=is_locked)

            if mat_add_submit:
                if not str(mat_add_item or "").strip():
                    st.error("Select a Material.")
                    st.stop()
                st.session_state["est_material_last_category"] = str(selected_cat)
                st.session_state["est_material_last_item"] = str(mat_add_item).strip()
                st.session_state["est_material_last_qty"] = float(mat_add_qty or 0.0) or 1.0
                est["materials"] = (est.get("materials") or []) + [{"item": str(mat_add_item).strip(), "qty": float(mat_add_qty or 0.0)}]
                st.session_state["est_material_edit_idx"] = None
                st.rerun()

        # Edit form (only one row at a time)
        mat_edit_idx = st.session_state.get("est_material_edit_idx")
        if mat_edit_idx is not None:
            try:
                mat_edit_idx = int(mat_edit_idx)
            except Exception:
                mat_edit_idx = None
            if mat_edit_idx is None or mat_edit_idx < 0 or mat_edit_idx >= len(est.get("materials") or []):
                st.session_state["est_material_edit_idx"] = None
            else:
                cur = (est.get("materials") or [])[mat_edit_idx] or {}
                cur_item = str(cur.get("item") or "").strip()
                cur_qty = float(cur.get("qty", 0) or 0)
                with st.form(key=f"est_material_edit_form_{mat_edit_idx}", clear_on_submit=True):
                    st.caption(f"Editing material line #{mat_edit_idx + 1}")
                    me1, me2, me3, me4 = st.columns([2.0, 0.42, 0.55, 0.55], gap="small")
                    with me1:
                        mat_edit_item = st.selectbox(
                            "Material",
                            options=materials_options if materials_options else [""],
                            index=(materials_options.index(cur_item) if cur_item in materials_options else 0),
                            disabled=is_locked,
                            key=f"est_material_edit_item_{mat_edit_idx}",
                        )
                    with me2:
                        mat_edit_qty = st.number_input(
                            "Qty",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_qty,
                            key=f"est_material_edit_qty_{mat_edit_idx}",
                        )
                    with me3:
                        mat_edit_submit = st.form_submit_button(
                            "Save", disabled=is_locked, key=f"est_material_edit_save_{mat_edit_idx}"
                        )
                    with me4:
                        mat_edit_cancel = st.form_submit_button(
                            "Cancel", disabled=is_locked, key=f"est_material_edit_cancel_{mat_edit_idx}"
                        )
                    if mat_edit_cancel:
                        st.session_state["est_material_edit_idx"] = None
                        st.rerun()
                    if mat_edit_submit:
                        if not str(mat_edit_item or "").strip():
                            st.error("Select a Material.")
                            st.stop()
                        est["materials"][mat_edit_idx] = {"item": str(mat_edit_item).strip(), "qty": float(mat_edit_qty or 0.0)}
                        st.session_state["est_material_edit_idx"] = None
                        st.rerun()

        # Render existing lines
        mat_lines = est.get("materials") or []
        if not mat_lines:
            st.info("No materials added yet.")
        else:
            for idx, line in enumerate(mat_lines):
                if not isinstance(line, dict):
                    continue
                item_key = str(line.get("item") or "").strip()
                qty_d = _dec(line.get("qty", 0) or 0)
                m = material_map.get(item_key)
                purchase_d = _dec((m or {}).get("purchase_price", 0) or 0)
                sell_d = _dec((m or {}).get("sell_price", 0) or 0)
                base_sell = sell_d if sell_d > _D0 else purchase_d * (Decimal("1") + material_markup_dec)
                subtotal = _q2(qty_d * base_sell)

                with st.container(border=True):
                    left, right = st.columns([1.65, 1], gap="small")
                    with left:
                        st.markdown(f"**{item_key or 'Unknown material'}**")
                        st.caption(f"Qty: {money_str(qty_d)}")
                    with right:
                        st.metric(label="Line subtotal", value=money(subtotal))
                    c_edit, c_rem = st.columns([1, 1], gap="small")
                    with c_edit:
                        if st.button(
                            "Edit",
                            disabled=is_locked,
                            use_container_width=True,
                            key=f"est_material_edit_btn_{idx}",
                        ):
                            st.session_state["est_material_edit_idx"] = idx
                            st.rerun()
                    with c_rem:
                        if st.button(
                            "Remove",
                            disabled=is_locked,
                            use_container_width=True,
                            key=f"est_material_remove_btn_{idx}",
                        ):
                            est["materials"] = [x for j, x in enumerate(mat_lines) if j != idx]
                            if st.session_state.get("est_material_edit_idx") == idx:
                                st.session_state["est_material_edit_idx"] = None
                            st.rerun()

    with tabs[1]:
        # Labor row cards + form-based add/edit to avoid "enter twice" UX.
        est.setdefault("labor", [])
        labor_map = {r.get("classification"): r for r in labor_rates if isinstance(r, dict) and r.get("classification")}

        st.caption("Quick add: classification + rates — last-used values are remembered.")

        with st.form(key="est_labor_add_form", clear_on_submit=True):
            last_class = str(st.session_state.get("est_labor_last_classification") or "").strip()
            class_opts = labor_options if labor_options else [""]
            class_index = class_opts.index(last_class) if last_class in class_opts else 0
            la1, la2, la3, la4, la5, la6 = st.columns([1.35, 0.62, 0.62, 0.62, 0.62, 0.52], gap="small")
            with la1:
                labor_add_class = st.selectbox(
                    "Class",
                    options=class_opts,
                    index=class_index,
                    disabled=is_locked,
                    key="est_labor_add_class",
                )
            with la2:
                labor_add_headcount = st.number_input(
                    "Headcount",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_labor_last_headcount") or 1.0),
                    key="est_labor_add_headcount",
                )
            with la3:
                labor_add_st_hrs = st.number_input(
                    "ST Hrs/Day",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_labor_last_st_hours") or 8.0),
                    key="est_labor_add_st_hours",
                )
            with la4:
                labor_add_ot_hrs = st.number_input(
                    "OT Hrs/Day",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_labor_last_ot_hours") or 0.0),
                    key="est_labor_add_ot_hours",
                )
            with la5:
                labor_add_days = st.number_input(
                    "Days",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_labor_last_days") or 1.0),
                    key="est_labor_add_days",
                )
            with la6:
                st.markdown("")
                labor_add_submit = st.form_submit_button("Add", disabled=is_locked)

            if labor_add_submit:
                if not str(labor_add_class or "").strip():
                    st.error("Select a Labor Classification.")
                    st.stop()
                st.session_state["est_labor_last_classification"] = str(labor_add_class).strip()
                st.session_state["est_labor_last_headcount"] = float(labor_add_headcount or 0.0) or 1.0
                st.session_state["est_labor_last_st_hours"] = float(labor_add_st_hrs or 0.0) or 8.0
                st.session_state["est_labor_last_ot_hours"] = float(labor_add_ot_hrs or 0.0)
                st.session_state["est_labor_last_days"] = float(labor_add_days or 0.0) or 1.0
                est["labor"] = (est.get("labor") or []) + [
                    {
                        "classification": str(labor_add_class).strip(),
                        "headcount": float(labor_add_headcount or 0.0),
                        "st_hours_per_day": float(labor_add_st_hrs or 0.0),
                        "ot_hours_per_day": float(labor_add_ot_hrs or 0.0),
                        "days": float(labor_add_days or 0.0),
                    }
                ]
                st.session_state["est_labor_edit_idx"] = None
                st.rerun()

        labor_edit_idx = st.session_state.get("est_labor_edit_idx")
        if labor_edit_idx is not None:
            try:
                labor_edit_idx = int(labor_edit_idx)
            except Exception:
                labor_edit_idx = None
            if labor_edit_idx is None or labor_edit_idx < 0 or labor_edit_idx >= len(est.get("labor") or []):
                st.session_state["est_labor_edit_idx"] = None
            else:
                cur = (est.get("labor") or [])[labor_edit_idx] or {}
                cur_class = str(cur.get("classification") or "").strip()
                cur_headcount = float(cur.get("headcount", 0) or 0)
                cur_st = float(cur.get("st_hours_per_day", 0) or 0)
                cur_ot = float(cur.get("ot_hours_per_day", 0) or 0)
                cur_days = float(cur.get("days", 0) or 0)
                with st.form(key=f"est_labor_edit_form_{labor_edit_idx}", clear_on_submit=True):
                    st.caption(f"Editing labor line #{labor_edit_idx + 1}")
                    le1, le2, le3, le4, le5 = st.columns([1.4, 0.62, 0.62, 0.62, 0.62], gap="small")
                    with le1:
                        labor_edit_class = st.selectbox(
                            "Class",
                            options=labor_options if labor_options else [""],
                            index=(labor_options.index(cur_class) if cur_class in labor_options else 0),
                            disabled=is_locked,
                            key=f"est_labor_edit_class_{labor_edit_idx}",
                        )
                    with le2:
                        labor_edit_headcount = st.number_input(
                            "Headcount",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_headcount,
                            key=f"est_labor_edit_headcount_{labor_edit_idx}",
                        )
                    with le3:
                        labor_edit_st = st.number_input(
                            "ST Hrs/Day",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_st,
                            key=f"est_labor_edit_st_hours_{labor_edit_idx}",
                        )
                    with le4:
                        labor_edit_ot = st.number_input(
                            "OT Hrs/Day",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_ot,
                            key=f"est_labor_edit_ot_hours_{labor_edit_idx}",
                        )
                    with le5:
                        labor_edit_days = st.number_input(
                            "Days",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_days,
                            key=f"est_labor_edit_days_{labor_edit_idx}",
                        )
                    leb1, leb2 = st.columns([1, 1], gap="small")
                    with leb1:
                        labor_edit_submit = st.form_submit_button(
                            "Save", disabled=is_locked, key=f"est_labor_edit_save_{labor_edit_idx}"
                        )
                    with leb2:
                        labor_edit_cancel = st.form_submit_button(
                            "Cancel", disabled=is_locked, key=f"est_labor_edit_cancel_{labor_edit_idx}"
                        )
                    if labor_edit_cancel:
                        st.session_state["est_labor_edit_idx"] = None
                        st.rerun()
                    if labor_edit_submit:
                        if not str(labor_edit_class or "").strip():
                            st.error("Select a Labor Classification.")
                            st.stop()
                        est["labor"][labor_edit_idx] = {
                            "classification": str(labor_edit_class).strip(),
                            "headcount": float(labor_edit_headcount or 0.0),
                            "st_hours_per_day": float(labor_edit_st or 0.0),
                            "ot_hours_per_day": float(labor_edit_ot or 0.0),
                            "days": float(labor_edit_days or 0.0),
                        }
                        st.session_state["est_labor_edit_idx"] = None
                        st.rerun()

        labor_lines = est.get("labor") or []
        if not labor_lines:
            st.info("No labor lines added yet.")
        else:
            for idx, line in enumerate(labor_lines):
                if not isinstance(line, dict):
                    continue
                classification = str(line.get("classification") or "").strip()
                headcount = _dec(line.get("headcount", 0) or 0)
                st_hrs = _dec(line.get("st_hours_per_day", 0) or 0)
                ot_hrs = _dec(line.get("ot_hours_per_day", 0) or 0)
                days = _dec(line.get("days", 0) or 0)
                lr = labor_map.get(classification)
                st_rate = _dec((lr or {}).get("st_rate", 0) or 0)
                ot_rate = _dec((lr or {}).get("ot_rate", 0) or 0)
                subtotal = _q2(headcount * days * ((st_hrs * st_rate) + (ot_hrs * ot_rate)))

                with st.container(border=True):
                    left, right = st.columns([1.65, 1], gap="small")
                    with left:
                        st.markdown(f"**{classification or 'Unknown labor'}**")
                        st.caption(f"Headcount: {headcount:.2f} · Days: {days:.2f} · ST {st_hrs:.2f}h/Day · OT {ot_hrs:.2f}h/Day")
                    with right:
                        st.metric(label="Line subtotal", value=money(subtotal))
                    c_edit, c_rem = st.columns([1, 1], gap="small")
                    with c_edit:
                        if st.button(
                            "Edit",
                            disabled=is_locked,
                            use_container_width=True,
                            key=f"est_labor_edit_btn_{idx}",
                        ):
                            st.session_state["est_labor_edit_idx"] = idx
                            st.rerun()
                    with c_rem:
                        if st.button(
                            "Remove",
                            disabled=is_locked,
                            use_container_width=True,
                            key=f"est_labor_remove_btn_{idx}",
                        ):
                            est["labor"] = [x for j, x in enumerate(labor_lines) if j != idx]
                            if st.session_state.get("est_labor_edit_idx") == idx:
                                st.session_state["est_labor_edit_idx"] = None
                            st.rerun()

    with tabs[2]:
        st.caption("Search → pick equipment → qty / basis / duration → add. Edit or remove from cards below.")
        eq_top1, eq_top2 = st.columns([3.0, 0.95], gap="small")
        with eq_top1:
            eq_search = st.text_input(
                "Search equipment",
                key="est_eq_equipment_search",
                placeholder="Name, manufacturer, model, serial…",
                disabled=is_locked,
                help="Matches every word you type (case-insensitive). Lines already on this estimate stay available even if filtered.",
            )
        with eq_top2:
            st.checkbox(
                "Rent-to-customer only",
                key="est_eq_rental_only",
                help="When checked, the picker lists only assets marked Rent to Customer. "
                "Uncheck to list all Equipment assets (rates may be zero).",
            )
        rental_only = st.session_state.get("est_eq_rental_only", True)

        option_labels, label_to_name, _name_to_label, _asset_id_to_label = build_equipment_picker_maps(
            equipment_pricing,
            rental_only=rental_only,
            search_query=eq_search,
            estimate_equipment_rows=est.get("equipment", []),
        )
        eq_opts = option_labels if option_labels else [""]
        equipment_map = {e["equipment_item"]: e for e in equipment_pricing}

        if not option_labels:
            st.warning(
                "No equipment assets match this filter. Add **Equipment** assets in the Asset Database, "
                "adjust search, or turn off “rent-to-customer only”."
            )

        est.setdefault("equipment", [])

        with st.form(key="est_equipment_add_form", clear_on_submit=True):
            last_item = str(st.session_state.get("est_equipment_last_item") or "").strip()
            item_index = eq_opts.index(last_item) if last_item in eq_opts else 0
            ea0, ea1, ea2, ea3, ea4 = st.columns([1.85, 0.48, 0.52, 0.52, 0.42], gap="small")
            with ea0:
                eq_add_item = st.selectbox(
                    "Equipment",
                    options=eq_opts,
                    index=item_index,
                    disabled=is_locked,
                    key="est_equipment_add_item",
                    help="Items include rate preview. Choose an asset-based equipment item when possible.",
                )
            basis_opts = ["Day", "Week", "Month"]
            last_basis = str(st.session_state.get("est_equipment_last_basis") or "Day")
            basis_index = basis_opts.index(last_basis) if last_basis in basis_opts else 0
            with ea1:
                eq_add_qty = st.number_input(
                    "Qty",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_equipment_last_qty") or 1.0),
                    key="est_equipment_add_qty",
                )
            with ea2:
                eq_add_basis = st.selectbox(
                    "Basis",
                    options=basis_opts,
                    index=basis_index,
                    disabled=is_locked,
                    key="est_equipment_add_basis",
                )
            with ea3:
                eq_add_duration = st.number_input(
                    "Dur.",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_equipment_last_duration") or 1.0),
                    key="est_equipment_add_duration",
                    help="Duration in selected basis (days/weeks/months).",
                )
            with ea4:
                st.markdown("")
                eq_add_submit = st.form_submit_button("Add", disabled=is_locked)
            if eq_add_submit:
                if not str(eq_add_item or "").strip():
                    st.error("Select an equipment item.")
                    st.stop()
                st.session_state["est_equipment_last_item"] = str(eq_add_item).strip()
                st.session_state["est_equipment_last_qty"] = float(eq_add_qty or 0.0) or 1.0
                st.session_state["est_equipment_last_basis"] = str(eq_add_basis)
                st.session_state["est_equipment_last_duration"] = float(eq_add_duration or 0.0) or 1.0

                new_row = {
                    "equipment_item": str(eq_add_item).strip(),
                    "qty": float(eq_add_qty or 0.0),
                    "basis": str(eq_add_basis),
                    "duration": float(eq_add_duration or 0.0),
                }
                # Normalize picker label → canonical asset name and attach metadata.
                enriched = enrich_equipment_rows_from_assets([new_row], equipment_pricing, picker_label_to_name=label_to_name)
                est["equipment"] = (est.get("equipment") or []) + enriched
                st.session_state["est_equipment_edit_idx"] = None
                st.rerun()

        eq_edit_idx = st.session_state.get("est_equipment_edit_idx")
        if eq_edit_idx is not None:
            try:
                eq_edit_idx = int(eq_edit_idx)
            except Exception:
                eq_edit_idx = None
            if eq_edit_idx is None or eq_edit_idx < 0 or eq_edit_idx >= len(est.get("equipment") or []):
                st.session_state["est_equipment_edit_idx"] = None
            else:
                cur = (est.get("equipment") or [])[eq_edit_idx] or {}
                cur_name = str(cur.get("equipment_item") or "").strip()
                cur_qty = float(cur.get("qty", 0) or 0.0)
                cur_basis = str(cur.get("basis") or "Day")
                cur_duration = float(cur.get("duration", 0) or 0.0)

                # Try to map canonical name → a current picker option label.
                cur_pick = next((lab for lab, nm in label_to_name.items() if nm == cur_name), cur_name)
                if cur_pick not in eq_opts and eq_opts:
                    cur_pick = eq_opts[0]
                with st.form(key=f"est_equipment_edit_form_{eq_edit_idx}", clear_on_submit=True):
                    st.caption(f"Editing equipment line #{eq_edit_idx + 1}")
                    ee0, ee1, ee2, ee3 = st.columns([1.75, 0.48, 0.52, 0.52], gap="small")
                    with ee0:
                        eq_edit_item = st.selectbox(
                            "Equipment",
                            options=eq_opts,
                            index=(eq_opts.index(cur_pick) if cur_pick in eq_opts else 0),
                            disabled=is_locked,
                            key=f"est_equipment_edit_item_{eq_edit_idx}",
                        )
                    with ee1:
                        eq_edit_qty = st.number_input(
                            "Qty",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_qty,
                            key=f"est_equipment_edit_qty_{eq_edit_idx}",
                        )
                    with ee2:
                        eq_edit_basis = st.selectbox(
                            "Basis",
                            options=basis_opts,
                            index=(basis_opts.index(cur_basis) if cur_basis in basis_opts else 0),
                            disabled=is_locked,
                            key=f"est_equipment_edit_basis_{eq_edit_idx}",
                        )
                    with ee3:
                        eq_edit_duration = st.number_input(
                            "Dur.",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_duration,
                            key=f"est_equipment_edit_duration_{eq_edit_idx}",
                        )
                    eeb1, eeb2 = st.columns(2, gap="small")
                    with eeb1:
                        eq_edit_submit = st.form_submit_button(
                            "Save", disabled=is_locked, key=f"est_equipment_edit_save_{eq_edit_idx}"
                        )
                    with eeb2:
                        eq_edit_cancel = st.form_submit_button(
                            "Cancel", disabled=is_locked, key=f"est_equipment_edit_cancel_{eq_edit_idx}"
                        )
                    if eq_edit_cancel:
                        st.session_state["est_equipment_edit_idx"] = None
                        st.rerun()
                    if eq_edit_submit:
                        if not str(eq_edit_item or "").strip():
                            st.error("Select an equipment item.")
                            st.stop()
                        new_row = {
                            "equipment_item": str(eq_edit_item).strip(),
                            "qty": float(eq_edit_qty or 0.0),
                            "basis": str(eq_edit_basis),
                            "duration": float(eq_edit_duration or 0.0),
                        }
                        enriched = enrich_equipment_rows_from_assets([new_row], equipment_pricing, picker_label_to_name=label_to_name)[0]
                        # Preserve any stored notes/asset_id if still valid (enricher will drop if no match).
                        est["equipment"][eq_edit_idx] = {**cur, **enriched}
                        st.session_state["est_equipment_edit_idx"] = None
                        st.rerun()

        eq_lines = est.get("equipment") or []
        if not eq_lines:
            st.info("No equipment lines added yet.")
        else:
            for idx, line in enumerate(eq_lines):
                if not isinstance(line, dict):
                    continue
                name = str(line.get("equipment_item") or "").strip()
                qty_d = _dec(line.get("qty", 0) or 0)
                basis = str(line.get("basis") or "Day")
                duration_d = _dec(line.get("duration", 0) or 0)
                meta = equipment_map.get(name) or {}
                rate = {
                    "Day": _dec(meta.get("daily_rate", 0) or 0),
                    "Week": _dec(meta.get("weekly_rate", 0) or 0),
                    "Month": _dec(meta.get("monthly_rate", 0) or 0),
                }.get(basis, _D0)
                subtotal = _q2(qty_d * duration_d * rate)
                with st.container(border=True):
                    left, right = st.columns([1.65, 1], gap="small")
                    with left:
                        st.markdown(f"**{name or 'Unknown equipment'}**")
                        st.caption(
                            f"Qty: {money_str(qty_d)} · Basis: {basis} · Duration: {money_str(duration_d)} · Rate: {money(rate)}"
                        )
                    with right:
                        st.metric(label="Line subtotal", value=money(subtotal))
                    c_edit, c_rem = st.columns([1, 1], gap="small")
                    with c_edit:
                        if st.button(
                            "Edit",
                            disabled=is_locked,
                            use_container_width=True,
                            key=f"est_equipment_edit_btn_{idx}",
                        ):
                            st.session_state["est_equipment_edit_idx"] = idx
                            st.rerun()
                    with c_rem:
                        if st.button(
                            "Remove",
                            disabled=is_locked,
                            use_container_width=True,
                            key=f"est_equipment_remove_btn_{idx}",
                        ):
                            est["equipment"] = [x for j, x in enumerate(eq_lines) if j != idx]
                            if st.session_state.get("est_equipment_edit_idx") == idx:
                                st.session_state["est_equipment_edit_idx"] = None
                            st.rerun()

        with st.expander("Rental rates (reference for lines above)", expanded=False):
            ref_rows = []
            for row in est.get("equipment", []) or []:
                name = str(row.get("equipment_item") or "").strip()
                if not name:
                    continue
                m = next((x for x in equipment_pricing if x["equipment_item"] == name), None)
                if m:
                    ref_rows.append(
                        {
                            "Equipment": name,
                            "Day": money(m["daily_rate"]),
                            "Week": money(m["weekly_rate"]),
                            "Month": money(m["monthly_rate"]),
                            "Rent to customer": "Yes" if m.get("is_rental") else "No",
                        }
                    )
            if ref_rows:
                st.dataframe(pd.DataFrame(ref_rows), hide_index=True, use_container_width=True)
            else:
                st.caption("Select equipment with a name that matches an Asset Database **Equipment** row to see rates.")

    with tabs[3]:
        st.caption("Quick add travel charges, then edit/remove from cards below.")
        travel = est.get("travel", {}) or {}
        est["travel"] = travel

        TRAVEL_KINDS = ["Mileage", "Per diem", "Hotel", "Airfare", "Rental car", "Fuel", "Override"]

        with st.form(key="est_travel_add_form", clear_on_submit=True):
            last_kind = str(st.session_state.get("est_travel_last_kind") or "Mileage")
            kind_index = TRAVEL_KINDS.index(last_kind) if last_kind in TRAVEL_KINDS else 0
            tk_type, tk_vals = st.columns([0.85, 2.65], gap="small")
            with tk_type:
                kind = st.selectbox(
                    "Type",
                    options=TRAVEL_KINDS,
                    index=kind_index,
                    disabled=is_locked,
                    key="est_travel_add_kind",
                )
            with tk_vals:
                if kind == "Mileage":
                    c1, c2 = st.columns(2, gap="small")
                    miles = c1.number_input(
                        "Round Trip Miles",
                        min_value=0.0,
                        step=10.0,
                        disabled=is_locked,
                        value=float(st.session_state.get("est_travel_last_miles") or _num0(travel.get("round_trip_miles"))),
                        key="est_travel_add_miles",
                    )
                    rate = c2.number_input(
                        "Mileage Rate",
                        min_value=0.0,
                        step=0.1,
                        format="%.2f",
                        disabled=is_locked,
                        value=float(
                            st.session_state.get("est_travel_last_mileage_rate") or _num0(travel.get("mileage_rate"))
                        ),
                        key="est_travel_add_mileage_rate",
                    )
                elif kind == "Hotel":
                    c1, c2 = st.columns(2, gap="small")
                    nights = c1.number_input(
                        "Hotel Nights",
                        min_value=0.0,
                        step=1.0,
                        disabled=is_locked,
                        value=float(
                            st.session_state.get("est_travel_last_hotel_nights") or _num0(travel.get("hotel_nights"))
                        ),
                        key="est_travel_add_hotel_nights",
                    )
                    nightly = c2.number_input(
                        "Hotel Rate / Night",
                        min_value=0.0,
                        step=10.0,
                        format="%.2f",
                        disabled=is_locked,
                        value=float(
                            st.session_state.get("est_travel_last_hotel_rate")
                            or _num0(travel.get("hotel_rate_per_room_per_night"))
                        ),
                        key="est_travel_add_hotel_rate",
                    )
                else:
                    ta1, ta2 = st.columns([0.9, 1.1], gap="small")
                    with ta1:
                        amt = st.number_input(
                            "Amount",
                            min_value=0.0,
                            step=25.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=float(st.session_state.get("est_travel_last_amount") or 0.0),
                            key="est_travel_add_amount",
                        )

            subc, _ = st.columns([0.75, 3.25])
            with subc:
                submit = st.form_submit_button("Apply", disabled=is_locked)
            if submit:
                st.session_state["est_travel_last_kind"] = str(kind)
                if kind == "Mileage":
                    travel["round_trip_miles"] = float(miles or 0.0)
                    travel["mileage_rate"] = float(rate or 0.0)
                    st.session_state["est_travel_last_miles"] = float(miles or 0.0)
                    st.session_state["est_travel_last_mileage_rate"] = float(rate or 0.0)
                elif kind == "Per diem":
                    travel["per_diem_per_person_per_day"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                elif kind == "Hotel":
                    travel["hotel_nights"] = float(nights or 0.0)
                    travel["hotel_rate_per_room_per_night"] = float(nightly or 0.0)
                    st.session_state["est_travel_last_hotel_nights"] = float(nights or 0.0)
                    st.session_state["est_travel_last_hotel_rate"] = float(nightly or 0.0)
                elif kind == "Airfare":
                    travel["airfare"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                elif kind == "Rental car":
                    travel["rental_car"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                elif kind == "Fuel":
                    travel["fuel"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                elif kind == "Override":
                    travel["line_total"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                est["travel"] = travel
                st.rerun()

        # Draft cards (edit/remove)
        def _travel_cards() -> list[tuple[str, str, Decimal]]:
            miles_total = _dec(travel.get("round_trip_miles")) * _dec(travel.get("mileage_rate"))
            hotel_total = _dec(travel.get("hotel_nights")) * _dec(travel.get("hotel_rate_per_room_per_night"))
            items: list[tuple[str, str, Decimal]] = [
                ("Mileage", f'{_num0(travel.get("round_trip_miles")):.2f} mi × {money(_dec(travel.get("mileage_rate")))}', miles_total),
                ("Per diem", "", _dec(travel.get("per_diem_per_person_per_day"))),
                ("Hotel", f'{_num0(travel.get("hotel_nights")):.2f} nights × {money(_dec(travel.get("hotel_rate_per_room_per_night")))}', hotel_total),
                ("Airfare", "", _dec(travel.get("airfare"))),
                ("Rental car", "", _dec(travel.get("rental_car"))),
                ("Fuel", "", _dec(travel.get("fuel"))),
                ("Override", "If set (>0) and computed travel is 0, totals use this.", _dec(travel.get("line_total"))),
            ]
            # Show only non-zero-ish items (but always show mileage/hotel if either field is set).
            out: list[tuple[str, str, Decimal]] = []
            for k, d, v in items:
                if k in ("Mileage", "Hotel"):
                    if _num0(travel.get("round_trip_miles")) > 0 or _num0(travel.get("mileage_rate")) > 0 or k == "Hotel" and (_num0(travel.get("hotel_nights")) > 0 or _num0(travel.get("hotel_rate_per_room_per_night")) > 0):
                        out.append((k, d, v))
                else:
                    if _q2(v) != _D0:
                        out.append((k, d, _q2(v)))
            return out

        cards = _travel_cards()
        if not cards:
            st.info("No travel charges set yet.")
        else:
            for k, detail, val in cards:
                with st.container(border=True):
                    left, right = st.columns([1.65, 1], gap="small")
                    with left:
                        st.markdown(f"**{k}**")
                        if detail:
                            st.caption(detail)
                    with right:
                        st.metric(label="Amount", value=money(val))
                    c1, c2 = st.columns([1, 1], gap="small")
                    with c1:
                        if st.button(
                            "Edit",
                            disabled=is_locked,
                            use_container_width=True,
                            key=f"est_travel_edit_{k}",
                        ):
                            st.session_state["est_travel_last_kind"] = k
                            st.rerun()
                    with c2:
                        if st.button(
                            "Remove",
                            disabled=is_locked,
                            use_container_width=True,
                            key=f"est_travel_remove_{k}",
                        ):
                            if k == "Mileage":
                                travel["round_trip_miles"] = 0.0
                                travel["mileage_rate"] = 0.0
                            elif k == "Per diem":
                                travel["per_diem_per_person_per_day"] = 0.0
                            elif k == "Hotel":
                                travel["hotel_nights"] = 0.0
                                travel["hotel_rate_per_room_per_night"] = 0.0
                            elif k == "Airfare":
                                travel["airfare"] = 0.0
                            elif k == "Rental car":
                                travel["rental_car"] = 0.0
                            elif k == "Fuel":
                                travel["fuel"] = 0.0
                            elif k == "Override":
                                travel["line_total"] = 0.0
                            est["travel"] = travel
                            st.rerun()

        st.markdown("---")
        st.caption("Estimate controls (markup, overhead, profit, contingency, tax) — submit once.")
        controls = est.get("controls", {}) or {}
        with st.form(key="est_controls_form", clear_on_submit=False):
            pc1, pc2, pc3, pc4, pc5 = st.columns(5, gap="small")
            material_markup_pct = pc1.number_input(
                "Material Markup %",
                min_value=0.0,
                value=_num0(controls.get("material_markup_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_material_markup_pct",
            )
            overhead_pct = pc2.number_input(
                "Overhead %",
                min_value=0.0,
                value=_num0(controls.get("overhead_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_overhead_pct",
            )
            profit_pct = pc3.number_input(
                "Profit %",
                min_value=0.0,
                value=_num0(controls.get("profit_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_profit_pct",
            )
            contingency_pct = pc4.number_input(
                "Contingency %",
                min_value=0.0,
                value=_num0(controls.get("contingency_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_contingency_pct",
            )
            sales_tax_pct = pc5.number_input(
                "Sales Tax %",
                min_value=0.0,
                value=_num0(controls.get("sales_tax_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_sales_tax_pct",
            )
            if st.form_submit_button("Save controls", disabled=is_locked):
                est["controls"] = {
                    **controls,
                    "material_markup_pct": float(material_markup_pct or 0.0),
                    "overhead_pct": float(overhead_pct or 0.0),
                    "profit_pct": float(profit_pct or 0.0),
                    "contingency_pct": float(contingency_pct or 0.0),
                    "sales_tax_pct": float(sales_tax_pct or 0.0),
                }
                st.rerun()

    with tabs[4]:
        st.caption(
            "Edit **Scope of Work** and **Customer Responsibilities** in one submit to avoid rerun/reset issues."
        )
        with st.form(key="est_scope_form", clear_on_submit=False):
            scope_of_work = st.text_area(
                "Scope of Work",
                value=str(est.get("scope_of_work") or ""),
                height=112,
                disabled=is_locked,
                key="est_scope_scope_of_work",
            )
            customer_responsibilities = st.text_area(
                "Customer Responsibilities",
                value=str(est.get("customer_responsibilities") or ""),
                height=112,
                disabled=is_locked,
                key="est_scope_customer_responsibilities",
            )
            if st.form_submit_button("Save scope sections", disabled=is_locked):
                est["scope_of_work"] = str(scope_of_work or "")
                est["customer_responsibilities"] = str(customer_responsibilities or "")
                st.rerun()

    with tabs[5]:
        st.caption("Add attachments to the draft (they upload when you Save/Submit/Approve/Award).")

        # Quote attachments (pending)
        pending_quotes: list[dict] = list(st.session_state.get("est_pending_quote_attachments") or [])
        with st.form(key="est_quote_attach_add_form", clear_on_submit=True):
            up_files = st.file_uploader(
                "Quote Attachments",
                type=["pdf", "jpg", "jpeg", "png"],
                accept_multiple_files=True,
                disabled=is_locked,
                key="est_quote_attach_uploader",
                help="Files are staged in the draft until you Save.",
            )
            if st.form_submit_button("Add attachment(s) to draft", disabled=is_locked):
                if not up_files:
                    st.warning("Choose one or more files first.")
                    st.stop()
                for f in up_files:
                    pending_quotes.append(
                        {
                            "file_name": f.name,
                            "bytes": f.getvalue(),
                            "content_type": f.type or "application/octet-stream",
                        }
                    )
                st.session_state["est_pending_quote_attachments"] = pending_quotes
                st.rerun()

        if pending_quotes:
            st.markdown("**Pending quote attachments**")
            for i, f in enumerate(pending_quotes):
                nm = str(f.get("file_name") or "file")
                with st.container(border=True):
                    st.markdown(f"**{nm}**")
                    if st.button(
                        "Remove",
                        disabled=is_locked,
                        use_container_width=True,
                        key=f"est_quote_attach_remove_{i}",
                    ):
                        st.session_state["est_pending_quote_attachments"] = [
                            x for j, x in enumerate(pending_quotes) if j != i
                        ]
                        st.rerun()
        else:
            st.caption("No pending quote attachments.")

        st.markdown("---")
        with st.form(key="est_po_form", clear_on_submit=False):
            job_received = st.checkbox(
                "Job Received / Awarded",
                value=bool(est.get("job_received", False)),
                disabled=is_locked,
                key="est_po_job_received",
            )
            pc1, pc2, pc3 = st.columns(3)
            po_number = pc1.text_input(
                "PO Number", value=str(est.get("po_number") or ""), disabled=is_locked, key="est_po_number"
            )
            po_date = pc2.text_input(
                "PO Date", value=str(est.get("po_date") or ""), disabled=is_locked, key="est_po_date"
            )
            po_amount = pc3.number_input(
                "PO Amount",
                min_value=0.0,
                value=float(est.get("po_amount", 0) or 0),
                step=100.0,
                disabled=is_locked,
                key="est_po_amount",
            )
            po_file = st.file_uploader(
                "PO Attachment",
                type=["pdf", "jpg", "jpeg", "png"],
                key="est_po_file_uploader",
                disabled=is_locked,
                help="Staged in the draft until you Save.",
            )
            if st.form_submit_button("Save P.O. fields to draft", disabled=is_locked):
                est["job_received"] = bool(job_received)
                est["po_number"] = str(po_number or "")
                est["po_date"] = str(po_date or "")
                est["po_amount"] = float(po_amount or 0.0)
                if po_file is not None:
                    st.session_state["est_pending_po_attachment"] = {
                        "file_name": po_file.name,
                        "bytes": po_file.getvalue(),
                        "content_type": po_file.type or "application/octet-stream",
                    }
                st.rerun()

        if st.session_state.get("est_pending_po_attachment"):
            po = st.session_state["est_pending_po_attachment"] or {}
            st.markdown("**Pending PO attachment**")
            with st.container(border=True):
                st.markdown(f"**{po.get('file_name') or 'po'}**")
                if st.button(
                    "Remove PO attachment",
                    disabled=is_locked,
                    use_container_width=True,
                    key="est_po_remove_pending",
                ):
                    st.session_state["est_pending_po_attachment"] = None
                    st.rerun()

    with tabs[6]:
        _pe = _proposal_export_kwargs(est, customer_name_by_id, jobs)
        vals, docx_bytes, word_build_error = _build_proposal_docx_and_vals(est, totals, _pe)
        st.caption(
            "Standard Word template **estimate_template_autofill_logo_updated.docx** — placeholders from this "
            "estimate; optional **company_logo.png** in **assets/** is merged when present."
        )

        pdf_bytes: bytes | None = None
        if docx_bytes is not None:
            pdf_bytes, _conv_note = try_convert_proposal_docx_to_pdf(docx_bytes)

        with st.container(border=True):
            st.markdown('<span class="ips-proposal-doc-surface"></span>', unsafe_allow_html=True)
            st.caption("Exports reflect the draft on screen. Open Word for exact pagination.")
            if word_build_error:
                st.error(word_build_error)
            elif pdf_bytes is None and docx_bytes is not None:
                st.caption(PROPOSAL_PDF_UNAVAILABLE_SHORT)

            if docx_bytes is None:
                st.caption("Ensure **assets/estimate_template_autofill_logo_updated.docx** exists in the app bundle.")

            _, _dl_mid, _ = st.columns([0.15, 1.0, 0.15])
            dc1, dc2 = _dl_mid.columns([1, 1], gap="small")
            with dc1:
                st.download_button(
                    "Download Proposal (Word)",
                    data=docx_bytes if docx_bytes is not None else b"",
                    file_name=f"{est.get('quote_number') or 'proposal'}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary",
                    disabled=docx_bytes is None,
                    key="est_proposal_dl_docx",
                )
            with dc2:
                if pdf_bytes is not None:
                    st.download_button(
                        "Download PDF Proposal",
                        data=pdf_bytes,
                        file_name=f"{est.get('quote_number') or 'proposal'}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="est_proposal_dl_pdf",
                    )

            if st.session_state.get("loaded_estimate_id"):
                _, _sv_mid, _ = st.columns([0.15, 1.0, 0.15])
                sc1, sc2 = _sv_mid.columns([1, 1], gap="small")
                if sc1.button("Save Word to Supabase", use_container_width=True, key="est_save_word_export"):
                    if docx_bytes is None:
                        st.caption("Build the Word proposal first (check the standard template file).")
                    else:
                        upload_generated_export(
                            st.session_state["loaded_estimate_id"],
                            f"{est.get('quote_number') or 'proposal'}.docx",
                            docx_bytes,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "generated_docx",
                        )
                        st.success("Word proposal saved to Supabase Storage.")
                if pdf_bytes is not None:
                    if sc2.button("Save PDF to Supabase", use_container_width=True, key="est_save_pdf_export"):
                        upload_generated_export(
                            st.session_state["loaded_estimate_id"],
                            f"{est.get('quote_number') or 'proposal'}.pdf",
                            pdf_bytes,
                            "application/pdf",
                            "generated_pdf",
                        )
                        st.success("PDF proposal saved to Supabase Storage.")
            else:
                st.caption("Save the estimate first to store exports in Supabase.")

        if docx_bytes is not None:
            preview_html = proposal_preview_html(docx_bytes, fallback_vals=vals)
            with st.expander("Proposal preview (read-only)", expanded=True):
                _render_proposal_preview_html(
                    preview_html,
                    caption="HTML preview of the same filled document — use Word for print layout.",
                )

    with tabs[7]:
        totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
        with st.container(border=True):
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Final Bid", money(totals["final_bid"]))
            rc2.metric("Overhead", money(totals["overhead_total"]))
            rc3.metric("Profit", money(totals["profit_total"]))
            rc4.metric("Sales Tax", money(totals["sales_tax_total"]))

            with st.form(key="est_revision_note_form", clear_on_submit=False):
                revision_note = st.text_input(
                    "Revision Note",
                    value=str(st.session_state.get("est_revision_note") or ""),
                    key="est_revision_note_input",
                )
                if st.form_submit_button("Update revision note"):
                    st.session_state["est_revision_note"] = str(revision_note or "")
                    st.rerun()

        customer_name = customer_name_by_id.get(str(est.get("customer_id") or "").strip(), "")
        loaded_id = st.session_state.get("loaded_estimate_id")
        qn_now = str(est.get("quote_number", "") or "").strip()
        if not qn_now:
            if loaded_id:
                st.warning("This estimate is missing a Quote Number.")
            else:
                st.info("Quote Number will be assigned on first save if left blank.")
        elif not customer_name:
            st.warning("Select a customer before saving.")

        save_cols = st.columns(4, gap="small")
        can_save = bool(
            bool(est.get("customer_id"))
            and (qn_now or not loaded_id)
        )

        def _resolve_customer_job_on_commit() -> list[str]:
            msgs: list[str] = []
            # IMPORTANT: Do not create jobs during estimate save.
            # Jobs are created only from explicit conversion actions (e.g. Estimates list / Job Database workflow).
            job_typed = " ".join(str(st.session_state.get("est_job_query") or "").strip().split())
            if job_typed:
                # The UI above will set est["job_id"] when an exact match exists.
                # If the user typed a new name (no exact match), keep the estimate unlinked and provide guidance.
                if not est.get("job_id"):
                    msgs.append(
                        "Job was not linked: no exact match found, and jobs are not created during estimate save. "
                        "Use **Job Received** / **Create Job from Estimate** to convert after customer approval."
                    )
            return msgs

        if save_cols[0].button("Save Estimate", use_container_width=True, disabled=(is_locked or not can_save)):
            # Allocate quote number only for brand-new estimates when blank.
            loaded_id = st.session_state.get("loaded_estimate_id")
            if not loaded_id and not str(est.get("quote_number", "") or "").strip():
                est["quote_number"] = next_quote_number()

            dup_msg = _duplicate_quote_message(str(est.get("quote_number", "") or "").strip(), loaded_id)
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": str(est.get("quote_number", "") or "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": est.get("status", "draft"),
                    "proposal_total": money_db(totals["proposal_total"]),
                    "final_bid": money_db(totals["final_bid"]),
                    "material_sell_basis": money_db(totals["material_sell_basis"]),
                    "labor_total": money_db(totals["labor_total"]),
                    "equipment_total": money_db(totals["equipment_total"]),
                    "travel_total": money_db(totals["travel_total"]),
                    "overhead_total": money_db(totals["overhead_total"]),
                    "profit_total": money_db(totals["profit_total"]),
                    "contingency_total": money_db(totals["contingency_total"]),
                    "sales_tax_total": money_db(totals["sales_tax_total"]),
                    "scope_of_work": est.get("scope_of_work", ""),
                    "exclusions": est.get("exclusions", ""),
                    "additional_charges": est.get("additional_charges", ""),
                    "customer_responsibilities": est.get("customer_responsibilities", ""),
                    "job_received": bool(est.get("job_received", False)),
                    "po_number": est.get("po_number", ""),
                    "po_date": est.get("po_date") or None,
                    "po_amount": float(est.get("po_amount", 0) or 0),
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                estimate_id = persist_estimate(payload, est, str(st.session_state.get("est_revision_note") or ""))
                attach_pending_pdf_import_source(estimate_id)
                pending_quotes = list(st.session_state.get("est_pending_quote_attachments") or [])
                for f in pending_quotes:
                    fn = str(f.get("file_name") or "file")
                    storage_path = f"quotes/{estimate_id}/attachments/{Path(fn).name}"
                    upload_bytes(storage_path, f.get("bytes") or b"", f.get("content_type") or "application/octet-stream")
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": estimate_id,
                            "category": "quote_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(f.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                pending_po = st.session_state.get("est_pending_po_attachment")
                if isinstance(pending_po, dict) and pending_po.get("bytes") is not None:
                    fn = str(pending_po.get("file_name") or "po")
                    storage_path = f"quotes/{estimate_id}/po/{Path(fn).name}"
                    upload_bytes(
                        storage_path,
                        pending_po.get("bytes") or b"",
                        pending_po.get("content_type") or "application/octet-stream",
                    )
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": estimate_id,
                            "category": "po_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(pending_po.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                # Clear pending uploads after commit so reruns don't re-upload.
                st.session_state["est_pending_quote_attachments"] = []
                st.session_state["est_pending_po_attachment"] = None
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate saved to Supabase.")
                st.session_state.pop("estimate_pdf_suggestions", None)

        if save_cols[1].button("Submit for Approval", use_container_width=True, disabled=(is_locked or not can_save)):
            loaded_id = st.session_state.get("loaded_estimate_id")
            if not loaded_id and not str(est.get("quote_number", "") or "").strip():
                est["quote_number"] = next_quote_number()

            dup_msg = _duplicate_quote_message(str(est.get("quote_number", "") or "").strip(), loaded_id)
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": str(est.get("quote_number", "") or "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "submitted",
                    "proposal_total": money_db(totals["proposal_total"]),
                    "final_bid": money_db(totals["final_bid"]),
                    "material_sell_basis": money_db(totals["material_sell_basis"]),
                    "labor_total": money_db(totals["labor_total"]),
                    "equipment_total": money_db(totals["equipment_total"]),
                    "travel_total": money_db(totals["travel_total"]),
                    "overhead_total": money_db(totals["overhead_total"]),
                    "profit_total": money_db(totals["profit_total"]),
                    "contingency_total": money_db(totals["contingency_total"]),
                    "sales_tax_total": money_db(totals["sales_tax_total"]),
                    "scope_of_work": est.get("scope_of_work", ""),
                    "exclusions": est.get("exclusions", ""),
                    "additional_charges": est.get("additional_charges", ""),
                    "customer_responsibilities": est.get("customer_responsibilities", ""),
                    "job_received": bool(est.get("job_received", False)),
                    "po_number": est.get("po_number", ""),
                    "po_date": est.get("po_date") or None,
                    "po_amount": float(est.get("po_amount", 0) or 0),
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                est["status"] = "submitted"
                eid = persist_estimate(payload, est, "Submitted for approval")
                attach_pending_pdf_import_source(eid)
                pending_quotes = list(st.session_state.get("est_pending_quote_attachments") or [])
                for f in pending_quotes:
                    fn = str(f.get("file_name") or "file")
                    storage_path = f"quotes/{eid}/attachments/{Path(fn).name}"
                    upload_bytes(storage_path, f.get("bytes") or b"", f.get("content_type") or "application/octet-stream")
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "quote_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(f.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                pending_po = st.session_state.get("est_pending_po_attachment")
                if isinstance(pending_po, dict) and pending_po.get("bytes") is not None:
                    fn = str(pending_po.get("file_name") or "po")
                    storage_path = f"quotes/{eid}/po/{Path(fn).name}"
                    upload_bytes(
                        storage_path,
                        pending_po.get("bytes") or b"",
                        pending_po.get("content_type") or "application/octet-stream",
                    )
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "po_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(pending_po.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                st.session_state["est_pending_quote_attachments"] = []
                st.session_state["est_pending_po_attachment"] = None
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate submitted for approval.")
                st.session_state.pop("estimate_pdf_suggestions", None)
                st.rerun()

        if save_cols[2].button("Approve", use_container_width=True, disabled=(current_role() != "admin" or not can_save)):
            loaded_id = st.session_state.get("loaded_estimate_id")
            if not loaded_id and not str(est.get("quote_number", "") or "").strip():
                est["quote_number"] = next_quote_number()

            dup_msg = _duplicate_quote_message(str(est.get("quote_number", "") or "").strip(), loaded_id)
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": str(est.get("quote_number", "") or "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "approved",
                    "proposal_total": money_db(totals["proposal_total"]),
                    "final_bid": money_db(totals["final_bid"]),
                    "material_sell_basis": money_db(totals["material_sell_basis"]),
                    "labor_total": money_db(totals["labor_total"]),
                    "equipment_total": money_db(totals["equipment_total"]),
                    "travel_total": money_db(totals["travel_total"]),
                    "overhead_total": money_db(totals["overhead_total"]),
                    "profit_total": money_db(totals["profit_total"]),
                    "contingency_total": money_db(totals["contingency_total"]),
                    "sales_tax_total": money_db(totals["sales_tax_total"]),
                    "scope_of_work": est.get("scope_of_work", ""),
                    "exclusions": est.get("exclusions", ""),
                    "additional_charges": est.get("additional_charges", ""),
                    "customer_responsibilities": est.get("customer_responsibilities", ""),
                    "job_received": bool(est.get("job_received", False)),
                    "po_number": est.get("po_number", ""),
                    "po_date": est.get("po_date") or None,
                    "po_amount": float(est.get("po_amount", 0) or 0),
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                est["status"] = "approved"
                eid = persist_estimate(payload, est, "Approved")
                attach_pending_pdf_import_source(eid)
                pending_quotes = list(st.session_state.get("est_pending_quote_attachments") or [])
                for f in pending_quotes:
                    fn = str(f.get("file_name") or "file")
                    storage_path = f"quotes/{eid}/attachments/{Path(fn).name}"
                    upload_bytes(storage_path, f.get("bytes") or b"", f.get("content_type") or "application/octet-stream")
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "quote_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(f.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                pending_po = st.session_state.get("est_pending_po_attachment")
                if isinstance(pending_po, dict) and pending_po.get("bytes") is not None:
                    fn = str(pending_po.get("file_name") or "po")
                    storage_path = f"quotes/{eid}/po/{Path(fn).name}"
                    upload_bytes(
                        storage_path,
                        pending_po.get("bytes") or b"",
                        pending_po.get("content_type") or "application/octet-stream",
                    )
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "po_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(pending_po.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                st.session_state["est_pending_quote_attachments"] = []
                st.session_state["est_pending_po_attachment"] = None
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate approved and locked.")
                st.session_state.pop("estimate_pdf_suggestions", None)
                st.rerun()

        if save_cols[3].button("Mark Awarded", use_container_width=True, disabled=(current_role() != "admin" or not can_save)):
            loaded_id = st.session_state.get("loaded_estimate_id")
            if not loaded_id and not str(est.get("quote_number", "") or "").strip():
                est["quote_number"] = next_quote_number()

            dup_msg = _duplicate_quote_message(str(est.get("quote_number", "") or "").strip(), loaded_id)
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": str(est.get("quote_number", "") or "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "awarded",
                    "proposal_total": money_db(totals["proposal_total"]),
                    "final_bid": money_db(totals["final_bid"]),
                    "material_sell_basis": money_db(totals["material_sell_basis"]),
                    "labor_total": money_db(totals["labor_total"]),
                    "equipment_total": money_db(totals["equipment_total"]),
                    "travel_total": money_db(totals["travel_total"]),
                    "overhead_total": money_db(totals["overhead_total"]),
                    "profit_total": money_db(totals["profit_total"]),
                    "contingency_total": money_db(totals["contingency_total"]),
                    "sales_tax_total": money_db(totals["sales_tax_total"]),
                    "scope_of_work": est.get("scope_of_work", ""),
                    "exclusions": est.get("exclusions", ""),
                    "additional_charges": est.get("additional_charges", ""),
                    "customer_responsibilities": est.get("customer_responsibilities", ""),
                    "job_received": True,
                    "po_number": est.get("po_number", ""),
                    "po_date": est.get("po_date") or None,
                    "po_amount": float(est.get("po_amount", 0) or 0),
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                est["status"] = "awarded"
                est["job_received"] = True
                eid = persist_estimate(payload, est, "Marked awarded")
                attach_pending_pdf_import_source(eid)
                pending_quotes = list(st.session_state.get("est_pending_quote_attachments") or [])
                for f in pending_quotes:
                    fn = str(f.get("file_name") or "file")
                    storage_path = f"quotes/{eid}/attachments/{Path(fn).name}"
                    upload_bytes(storage_path, f.get("bytes") or b"", f.get("content_type") or "application/octet-stream")
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "quote_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(f.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                pending_po = st.session_state.get("est_pending_po_attachment")
                if isinstance(pending_po, dict) and pending_po.get("bytes") is not None:
                    fn = str(pending_po.get("file_name") or "po")
                    storage_path = f"quotes/{eid}/po/{Path(fn).name}"
                    upload_bytes(
                        storage_path,
                        pending_po.get("bytes") or b"",
                        pending_po.get("content_type") or "application/octet-stream",
                    )
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "po_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(pending_po.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                st.session_state["est_pending_quote_attachments"] = []
                st.session_state["est_pending_po_attachment"] = None
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate marked awarded.")
                st.session_state.pop("estimate_pdf_suggestions", None)
                st.rerun()

        if st.session_state.get("loaded_estimate_id"):
            attachments = fetch_by_match("attachments", {"estimate_id": st.session_state["loaded_estimate_id"]}, columns="category,file_name,storage_path,uploaded_at", limit=200)
            if attachments:
                st.markdown("### Saved Files")
                for att in attachments:
                    signed = create_signed_url(att["storage_path"])
                    if signed:
                        st.markdown(f'- **{att["category"]}**: [{att["file_name"]}]({signed})')

    # Persistent estimate summary/totals panel (stays visible while editing).
    # This is intentionally rendered outside the tab bodies so it runs regardless of
    # which editor tab is active.
    try:
        totals_preview = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
    except Exception as exc:
        totals_preview = None
        st.sidebar.error(
            "Could not compute totals for the current draft. "
            "Check your line items and try again."
        )
        st.sidebar.caption(str(exc))

    with st.sidebar:
        st.markdown("### Estimate Summary")
        st.caption(
            f"Quote: {est.get('quote_number') or '—'} · Status: {est.get('status') or 'draft'}"
        )
        customer_name = customer_name_by_id.get(str(est.get("customer_id") or "").strip(), "") if "customer_name_by_id" in locals() else ""
        if customer_name:
            st.caption(f"Customer: {customer_name}")

        if totals_preview:
            st.metric("Final Bid", money(totals_preview.get("final_bid", 0.0)))
            st.metric("Proposal Total", money(totals_preview.get("proposal_total", 0.0)))
            st.metric("Overhead", money(totals_preview.get("overhead_total", 0.0)))
            st.metric("Profit", money(totals_preview.get("profit_total", 0.0)))
            st.metric("Sales Tax", money(totals_preview.get("sales_tax_total", 0.0)))

            st.caption(
                "Breakdown: "
                f"Materials {money(totals_preview.get('material_sell_basis', 0))} · "
                f"Labor {money(totals_preview.get('labor_total', 0))} · "
                f"Equipment {money(totals_preview.get('equipment_total', 0))} · "
                f"Travel {money(totals_preview.get('travel_total', 0))}"
            )

        # Line-item counts for quick context (no inputs).
        mats_n = len(est.get("materials", []) or [])
        labor_n = len(est.get("labor", []) or [])
        eq_n = len(est.get("equipment", []) or [])
        st.caption(f"Lines: Materials {mats_n} · Labor {labor_n} · Equipment {eq_n}")


def render() -> None:
    """Streamlit page entry for the standalone Estimate Editor route."""
    render_estimate_editor(embedded=False)
