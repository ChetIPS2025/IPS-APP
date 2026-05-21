"""Read-only Job Detail view for Job Database (``job_view_mode`` == ``view``)."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from auth import current_role

try:
    from app.db import create_signed_url
except ImportError:
    from db import create_signed_url  # type: ignore

try:
    from db import fetch_by_match, fetch_by_match_admin, fetch_table, fetch_table_admin
except ImportError:
    from app.db import fetch_by_match, fetch_by_match_admin, fetch_table, fetch_table_admin  # type: ignore

try:
    from services.delete_safety import delete_job_row_if_no_costing
except ImportError:
    from app.services.delete_safety import delete_job_row_if_no_costing  # type: ignore

try:
    from services.job_service import job_row_select_label
except ImportError:
    from app.services.job_service import job_row_select_label  # type: ignore

try:
    from table_actions import TABLE_KEY_JOBS, clear_selected_ids
except ImportError:
    from app.table_actions import (  # type: ignore
        TABLE_KEY_JOBS,
        clear_selected_ids,
    )

try:
    from app.pages import job_costing as _jc
except ImportError:
    import pages.job_costing as _jc  # type: ignore

try:
    from app.pages.job_database_job_tasks import render_job_cost_tab, render_job_tasks_tab
except ImportError:
    from pages.job_database_job_tasks import render_job_cost_tab, render_job_tasks_tab  # type: ignore

try:
    from app.services import job_reference_attachments as _jra_svc
except ImportError:
    import services.job_reference_attachments as _jra_svc  # type: ignore

try:
    from services.customer_locations import location_display_name_city_state
except ImportError:
    from app.services.customer_locations import location_display_name_city_state  # type: ignore


_JOB_STATUS_COLORS: dict[str, str] = {
    "complete": "#16a34a",
    "completed": "#16a34a",
    "closed": "#16a34a",
    "in progress": "#f59e0b",
    "scheduled": "#f59e0b",
    "awarded": "#f59e0b",
    "blocked": "#dc2626",
    "on hold": "#dc2626",
    "not started": "#64748b",
    "draft": "#64748b",
    "quoted": "#64748b",
    "submitted": "#64748b",
    "approved": "#22c55e",
    "duplicate": "#64748b",
    "waiting on customer": "#0891b2",
}


def _status_badge(status: Any) -> str:
    label = str(status or "").strip() or "—"
    color = _JOB_STATUS_COLORS.get(label.lower(), "#64748b")
    return (
        '<span class="ips-status-badge" '
        f'style="--ips-status-color:{html.escape(color)};">{html.escape(label)}</span>'
    )


def _money(v: Any) -> str:
    try:
        if v is None or str(v).strip() == "":
            return "—"
        return f"${float(v):,.2f}"
    except Exception:
        return "—"


def _disp(v: Any) -> str:
    s = str(v or "").strip()
    return s if s else "—"


def _job_num_display(row: dict[str, Any], *, has_job_number_column: bool) -> str:
    if has_job_number_column:
        jn = str(row.get("job_number") or "").strip()
        if jn:
            return jn
    for k in ("job_id", "id"):
        v = str(row.get(k) or "").strip()
        if v:
            return v
    return ""


def _fetch_tasks_simple(job_id: str, *, admin_read: bool) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    try:
        return list(fn("job_tasks", {"job_id": str(job_id).strip()}, limit=800) or [])
    except Exception:
        return []


def _task_progress_pct(tasks: list[dict[str, Any]]) -> float:
    if not tasks:
        return 0.0
    done = 0
    for t in tasks:
        if not isinstance(t, dict):
            continue
        s = str(t.get("status") or "").strip().lower()
        if s in ("complete", "completed", "closed"):
            done += 1
    return round(100.0 * done / len(tasks), 1)


def _sum_job_expenses(job_id: str, *, admin_read: bool) -> tuple[float, list[dict[str, Any]]]:
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    try:
        rows = list(fn("job_expenses", {"job_id": str(job_id).strip()}, limit=5000) or [])
    except Exception:
        return 0.0, []
    total = 0.0
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            total += float(r.get("amount") or 0)
        except Exception:
            pass
    return total, rows


def _contact_row_for_detail(contact_id: str, *, admin_read: bool) -> dict[str, Any] | None:
    cid = str(contact_id or "").strip()
    if not cid:
        return None
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    try:
        rows = list(fn("customer_contacts", {"id": cid}, limit=1) or [])
        return rows[0] if rows else None
    except Exception:
        return None


def render_job_database_detail_view_page(
    *,
    job_row: dict[str, Any],
    has_job_number_column: bool,
    has_customer_location_column: bool,
    customers: list[dict[str, Any]],
    customer_name_by_id: dict[str, str],
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    estimate_detail: dict[str, Any] | None,
    location_by_id: dict[str, dict[str, Any]],
    contact_label_by_id: dict[str, str],
    can_edit: bool,
    admin_read: bool,
    on_clear_view: Any,
    on_sync_edit: Any,
) -> None:
    """Full-width read-only job portal; mutates session for Back / Edit / Delete only."""
    jid = str(job_row.get("id") or "").strip()
    if not jid:
        st.error("Invalid job.")
        return

    try:
        from app.ui.field_light_theme import inject_field_light_theme as _ift
    except ImportError:
        from ui.field_light_theme import inject_field_light_theme as _ift  # type: ignore

    _ift()

    _on_clear_view = on_clear_view
    _on_sync_edit = on_sync_edit

    jn = _job_num_display(job_row, has_job_number_column=has_job_number_column)
    jname = _disp(job_row.get("job_name"))
    cust = _disp(job_row.get("customer_name") or customer_name_by_id.get(str(job_row.get("customer_id") or ""), ""))
    status = job_row.get("status")
    awarded = job_row.get("awarded_amount")
    quote_cell = str(job_row.get("Quote (estimate)") or job_row.get("quote_number") or "").strip()

    loc_txt = ""
    if has_customer_location_column:
        clid = str(job_row.get("customer_location_id") or "").strip()
        if clid and clid in location_by_id:
            loc_txt = location_display_name_city_state(location_by_id[clid])
    if not loc_txt:
        loc_txt = str(job_row.get("location") or job_row.get("Location") or "").strip()

    contact_txt = str(job_row.get("Contact") or "").strip()
    ccid = str(job_row.get("customer_contact_id") or "").strip()
    if not contact_txt and ccid and ccid in contact_label_by_id:
        contact_txt = contact_label_by_id[ccid]

    tasks = _fetch_tasks_simple(jid, admin_read=admin_read)
    pct = _task_progress_pct(tasks)

    employees: list[dict[str, Any]] = []
    try:
        if admin_read:
            employees = list(fetch_table_admin("employees", limit=5000, order_by="name") or [])
        else:
            employees = list(fetch_table("employees", limit=5000, order_by="name") or [])
    except Exception:
        employees = []
    emp_by_id = {str(e.get("id")): e for e in employees if e.get("id")}

    grid_rows: list[dict[str, Any]] = []
    try:
        fn_te = fetch_table_admin if admin_read else fetch_table
        for ob in ("work_date", None):
            try:
                grid_rows = list(
                    fn_te("time_entries", limit=50000, order_by=ob) if ob else fn_te("time_entries", limit=50000) or []
                )
                break
            except Exception:
                grid_rows = []
    except Exception:
        grid_rows = []

    labor_rows = _jc._labor_rows_time_entries(grid_rows, jid, emp_by_id)
    labor_total = _jc._labor_total_from_rows(labor_rows)
    jm_rows, _jm_err = _jc._fetch_table_graceful("job_materials", limit=50000, order_by="created_at")
    je_rows, _je_err = _jc._fetch_table_graceful("job_equipment", limit=50000, order_by="created_at")
    mats = _jc._materials_for_job(jm_rows, jid)
    equip = _jc._equipment_for_job(je_rows, jid)
    mat_total = _jc._material_total(mats)
    eq_total = _jc._equipment_total(equip)
    po_total, po_rows = _sum_job_expenses(jid, admin_read=admin_read)
    direct_total = labor_total + mat_total + eq_total + po_total

    aw_f = 0.0
    try:
        if awarded is not None and str(awarded).strip() != "":
            aw_f = float(awarded)
    except Exception:
        aw_f = 0.0
    profit = aw_f - direct_total if aw_f else None
    margin_pct = (100.0 * profit / aw_f) if (aw_f and profit is not None) else None

    uniq_emp: dict[str, str] = {}
    for r in labor_rows:
        nm = str(r.get("Employee") or "").strip()
        if nm and nm != "—":
            uniq_emp[nm] = nm

    assets_on_job: list[dict[str, Any]] = []
    try:
        fn_a = fetch_by_match_admin if admin_read else fetch_by_match
        assets_on_job = list(fn_a("assets", {"assigned_job_id": jid}, limit=200) or [])
    except Exception:
        assets_on_job = []

    ref_rows: list[dict[str, Any]] = []
    try:
        fn_r = fetch_by_match_admin if admin_read else fetch_by_match
        ref_rows = list(fn_r("job_reference_attachments", {"job_id": jid}, limit=300) or [])
    except Exception:
        ref_rows = []

    st.markdown('<span class="ips-job-detail-sticky-host"></span>', unsafe_allow_html=True)
    top1, top2, top3 = st.columns([1.1, 1.0, 1.0], gap="small")
    with top1:
        if st.button("← Back to Jobs", key="job_detail_back", use_container_width=True):
            _on_clear_view()
            st.rerun()
    with top2:
        if st.button(
            "Edit Job",
            type="primary",
            key="job_detail_edit",
            use_container_width=True,
            disabled=not (can_edit or current_role() == "employee"),
        ):
            _on_sync_edit(jid)
            st.rerun()
    with top3:
        del_help = "Only admin or manager can delete jobs." if not can_edit else "Delete this job (blocked if costing exists)."
        if st.button("Delete Job", type="secondary", key="job_detail_del", disabled=not can_edit, help=del_help):
            st.session_state["job_db_detail_delete_confirm"] = jid
            st.rerun()

    conf = str(st.session_state.get("job_db_detail_delete_confirm") or "").strip()
    if conf == jid:
        st.warning("Delete this job permanently? Jobs with labor, materials, equipment, or PO expenses cannot be deleted.")
        d1, d2 = st.columns(2, gap="small")
        with d1:
            if st.button("Confirm delete", type="primary", key="job_detail_del_y", use_container_width=True):
                try:
                    delete_job_row_if_no_costing(jid, admin_read=admin_read)
                    st.session_state.pop("job_db_detail_delete_confirm", None)
                    _on_clear_view()
                    clear_selected_ids(TABLE_KEY_JOBS)
                    st.success("Job deleted.")
                    st.rerun()
                except RuntimeError as re:
                    st.error(str(re))
                except Exception as exc:
                    st.error(f"Could not delete: {exc}")
        with d2:
            if st.button("Cancel", key="job_detail_del_n", use_container_width=True):
                st.session_state.pop("job_db_detail_delete_confirm", None)
                st.rerun()

    hero_inner = (
        f'<div class="ips-job-detail-hero">'
        f'<h1>{html.escape(jname)}</h1>'
        f'<p class="ips-job-detail-meta"><strong>Job #</strong> {html.escape(jn or "—")} &nbsp;·&nbsp; '
        f"<strong>Customer</strong> {html.escape(cust)}</p>"
        f'<div style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;margin:0.5rem 0;">'
        f"{_status_badge(status)}"
        f'<span style="color:#64748b;font-weight:600;">Progress {pct:g}%</span></div>'
        f'<div class="ips-job-detail-meta" style="margin-top:0.35rem;">'
        f"<strong>Awarded</strong> {_money(awarded)} &nbsp;·&nbsp; <strong>Quote / PO</strong> {html.escape(quote_cell or '—')}<br/>"
        f"<strong>Location</strong> {html.escape(loc_txt or '—')} &nbsp;·&nbsp; <strong>Contact</strong> {html.escape(contact_txt or '—')}"
        f"</div></div>"
    )
    st.markdown(hero_inner, unsafe_allow_html=True)

    try:
        from app.ui.activity import render_activity_panel
        from app.ui.page_shell import render_card
    except ImportError:
        from ui.activity import render_activity_panel  # type: ignore
        from ui.page_shell import render_card  # type: ignore

    with render_card(title="Activity"):
        render_activity_panel(
            title="Job activity",
            created_at=job_row.get("created_at"),
            updated_at=job_row.get("updated_at"),
            status=status,
            extra_lines=[
                ("Job #", jn or "—"),
                ("Customer", cust),
            ],
        )

    with render_card(title="Job information"):
        st.markdown('<p class="ips-job-detail-section-title">Job information</p>', unsafe_allow_html=True)
        desc = str(job_row.get("description") or job_row.get("scope") or "").strip()
        st.markdown(f"**Description**  \n{html.escape(desc) if desc else '—'}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Start date", _disp(job_row.get("start_date")))
        c2.metric("Due / target", _disp(job_row.get("target_completion_date") or job_row.get("due_date")))
        c3.metric("Source", _disp(job_row.get("source_type") or job_row.get("Source")))
        le = str(job_row.get("Linked estimate") or estimate_label_map.get(str(job_row.get("estimate_id") or ""), ""))
        st.markdown(f"**Linked estimate**  \n{html.escape(le) if le.strip() else '—'}")
        notes = str(job_row.get("notes") or "").strip()
        with st.expander("Notes", expanded=bool(notes)):
            st.text(notes or "—")

    with render_card(title="Customer information"):
        st.markdown('<p class="ips-job-detail-section-title">Customer information</p>', unsafe_allow_html=True)
        phone = email = "—"
        if ccid:
            crow = _contact_row_for_detail(ccid, admin_read=admin_read)
            if crow:
                phone = _disp(crow.get("phone") or crow.get("mobile"))
                email = _disp(crow.get("email"))
        st.markdown(f"**Customer**  \n{html.escape(cust)}")
        st.markdown(f"**Contact**  \n{html.escape(contact_txt or '—')}")
        st.markdown(f"**Phone**  \n{html.escape(phone)}")
        st.markdown(f"**Email**  \n{html.escape(email)}")
        st.markdown(f"**Site / location**  \n{html.escape(loc_txt or '—')}")

    with render_card(title="Financial summary"):
        st.markdown('<p class="ips-job-detail-section-title">Financial summary</p>', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Awarded", _money(awarded))
        m2.metric("Labor cost", _jc._money_str(labor_total))
        m3.metric("Material cost", _jc._money_str(mat_total))
        m4.metric("Equipment cost", _jc._money_str(eq_total))
        m5, m6, m7, m8 = st.columns(4)
        m5.metric("PO / job expenses", _jc._money_str(po_total))
        m6.metric("Total direct cost", _jc._money_str(direct_total))
        m7.metric("Profit (awarded − cost)", _jc._money_str(profit) if profit is not None else "—")
        m8.metric("Margin %", f"{margin_pct:.1f}%" if margin_pct is not None else "—")

    with render_card(title="Assigned employees"):
        st.markdown('<p class="ips-job-detail-section-title">Assigned employees (from time entries)</p>', unsafe_allow_html=True)
        if uniq_emp:
            for nm in sorted(uniq_emp.keys()):
                st.markdown(f"- **{html.escape(nm)}**")
        else:
            st.caption("No time booked to this job yet.")

    with render_card(title="Assigned assets"):
        st.markdown('<p class="ips-job-detail-section-title">Assigned assets / equipment</p>', unsafe_allow_html=True)
        if not assets_on_job:
            st.caption("No assets are assigned to this job.")
        else:
            for a in assets_on_job[:40]:
                aid = str(a.get("asset_id") or "").strip()
                an = str(a.get("asset_name") or "").strip()
                st.markdown(f"- **{html.escape(aid or '—')}** — {html.escape(an or '—')}")

    with render_card(title="Tasks"):
        st.markdown('<p class="ips-job-detail-section-title">Tasks</p>', unsafe_allow_html=True)
        jl = job_row_select_label(job_row)
        render_job_tasks_tab(job_id=jid, job_label=jl, can_edit_tasks=False, admin_read=admin_read)

    with render_card(title="Costing & estimates"):
        st.markdown('<p class="ips-job-detail-section-title">Costing & estimates</p>', unsafe_allow_html=True)
        render_job_cost_tab(job_id=jid, job_row=job_row)

    with render_card(title="Files & references"):
        st.markdown('<p class="ips-job-detail-section-title">Uploaded files & references</p>', unsafe_allow_html=True)
        if not ref_rows:
            st.caption("No reference attachments on this job yet. Add files from **Edit Job → Tasks**.")
        else:
            bucket = _jra_svc.reference_bucket()
            for r in ref_rows[:24]:
                fnm = str(r.get("file_name") or r.get("display_name") or "file").strip()
                sp = str(r.get("storage_path") or "").strip()
                st.markdown(f"**{html.escape(fnm)}**")
                if not sp:
                    st.caption("—")
                    continue
                url = create_signed_url(sp, expires_in=3600) if not sp.startswith("http") else sp
                ext = fnm.rsplit(".", 1)[-1].lower() if "." in fnm else ""
                rid = str(r.get("id") or "").strip() or fnm
                load_key = f"jdv_ref_preview_loaded_{jid}_{rid}"
                if ext in ("jpg", "jpeg", "png", "webp") and url:
                    if not st.session_state.get(load_key):
                        st.caption("Image preview not loaded (faster page).")
                        if st.button("Load preview", key=f"jdv_load_img_{jid}_{rid}", use_container_width=True):
                            st.session_state[load_key] = True
                            st.rerun()
                    else:
                        try:
                            st.image(url, use_container_width=True)
                        except Exception:
                            st.link_button("Open image", url)
                elif ext == "pdf" and url:
                    if not st.session_state.get(load_key):
                        st.caption("PDF preview not loaded (faster page).")
                        if st.button("Load preview", key=f"jdv_load_pdf_{jid}_{rid}", use_container_width=True):
                            st.session_state[load_key] = True
                            st.rerun()
                    else:
                        try:
                            components.iframe(url, height=520, scrolling=True)
                        except Exception:
                            st.link_button("Open PDF", url, use_container_width=True)
                else:
                    st.link_button(f"Download / open {ext or 'file'}", url, use_container_width=True)

    try:
        from app.ui.field_components import render_job_photos_panel, render_job_timeline_panel
    except ImportError:
        from ui.field_components import render_job_photos_panel, render_job_timeline_panel  # type: ignore

    render_job_timeline_panel(job_id=jid, admin_read=admin_read)
    render_job_photos_panel(job_id=jid, admin_read=admin_read, compact=True)

    try:
        from app.pages.supervisor_daily_reports import render_daily_reports_for_job
    except ImportError:
        from pages.supervisor_daily_reports import render_daily_reports_for_job  # type: ignore

    render_daily_reports_for_job(
        job_id=jid,
        job_label=job_row_select_label(job_row),
        admin_read=admin_read,
        show_title=True,
    )

    with st.expander("Activity snapshot (from tasks)", expanded=False):
        dated: list[tuple[str, str]] = []
        for t in tasks:
            if not isinstance(t, dict):
                continue
            ts = str(t.get("updated_at") or t.get("created_at") or "")[:19]
            tno = str(t.get("task_number") or t.get("id") or "")[:12]
            stt = str(t.get("status") or "")
            dated.append((ts, f"Task {tno} — {stt}"))
        dated.sort(reverse=True)
        for ts, line in dated[:40]:
            st.caption(f"{ts} — {line}" if ts else line)
