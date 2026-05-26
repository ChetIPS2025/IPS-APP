from __future__ import annotations

"""
PHASE 1 — Job Costing (plug-and-play)

Schema assumptions (see ``sql/023_job_costing_materials_equipment.sql``):
- ``public.time_entries``: ``job_id``, ``employee_id``, ``work_date``, ``hours`` (labor hours; do not alter time tracking).
- ``public.job_materials``: ``job_id``, ``item_name``, ``quantity``, ``unit_cost``, ``line_total`` (optional ``inventory_item_id``).
- ``public.job_equipment``: ``job_id``, ``asset_label``, ``usage_hours``, ``usage_days``, ``rate_per_hour``, ``rate_per_day``, ``line_total``.

The UI also accepts optional column aliases if you add them later (``material_name`` / ``qty`` / ``total_cost``, etc.).

Core rule: **Estimate = quote**, **Job = costing** — all costing rows use ``job_id`` only.
"""

from contextlib import contextmanager
from typing import Any
import html

import pandas as pd
import streamlit as st

from auth import current_role

from db import fetch_one, fetch_table, fetch_table_admin, insert_row, insert_row_admin


# --- helpers (Phase 1; keep small and local) ---


def job_display_label(job_row: dict) -> str:
    """Readable label for selectors, e.g. ``J26025 – Fireline Repair`` (IPS job number rules)."""
    try:
        from app.utils.formatters import job_display_label as _fmt_label
    except ImportError:
        from utils.formatters import job_display_label as _fmt_label  # type: ignore

    out = _fmt_label(job_row.get("job_number"), job_row.get("job_name"))
    s = str(out).strip()
    return s if s else "(unnamed job)"


def _safe_float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _money_str(value: float) -> str:
    return f"${_safe_float(value):,.2f}"


def _job_costing_admin_read() -> bool:
    return current_role() in {"admin", "manager"}


def _sort_jobs(jobs: list[dict]) -> list[dict]:
    try:
        from services.job_service import sort_jobs_by_number_then_name
    except ImportError:
        from app.services.job_service import sort_jobs_by_number_then_name  # type: ignore

    return sort_jobs_by_number_then_name(jobs)


def _fetch_table_graceful(
    table: str,
    *,
    limit: int = 20000,
    order_by: str | None = "created_at",
) -> tuple[list[dict], str | None]:
    """Return ``(rows, error_message)``. ``error_message`` is set if the table is missing or unreadable."""
    admin = _job_costing_admin_read()
    fn = fetch_table_admin if admin else fetch_table
    for ob in (order_by, None):
        try:
            rows = fn(table, limit=limit, order_by=ob) if ob else fn(table, limit=limit, order_by=None)
            return list(rows or []), None
        except Exception as exc:
            err = str(exc).lower()
            if "relation" in err and "does not exist" in err:
                return [], f"The database table `{table}` was not found. Run sql/023_job_costing_materials_equipment.sql in Supabase."
            if ob is None:
                return [], f"Could not load `{table}`: {exc!r}"
    return [], "unreachable"


def _insert_row_resilient(table: str, payload: dict[str, Any]) -> None:
    """Prefer anon insert (RLS); fall back to service role when configured (same pattern as other pages)."""
    try:
        insert_row(table, payload)
    except Exception:
        insert_row_admin(table, payload)


def _estimate_amount_for_job(job: dict, estimate_by_id: dict[Any, dict]) -> float | None:
    """``proposal_total`` then ``final_bid``; ``None`` if no linked estimate."""
    eid = job.get("estimate_id")
    if not eid:
        return None
    est = estimate_by_id.get(eid) or {}
    for key in ("proposal_total", "final_bid"):
        raw = est.get(key)
        if raw is not None and str(raw).strip() != "":
            v = _safe_float(raw)
            if v != 0 or key == "proposal_total":
                return v
    return None


def _material_display_name(row: dict) -> str:
    return str(row.get("material_name") or row.get("item_name") or "").strip() or "—"


def _material_qty(row: dict) -> float:
    return _safe_float(row.get("qty") if row.get("qty") is not None else row.get("quantity"))


def _material_unit_cost(row: dict) -> float:
    return _safe_float(row.get("unit_cost"))


def _material_line_total(row: dict) -> float:
    for key in ("total_cost", "line_total"):
        if row.get(key) is not None and str(row.get(key)).strip() != "":
            return _safe_float(row.get(key))
    return _material_qty(row) * _material_unit_cost(row)


def _equipment_display_name(row: dict) -> str:
    return str(row.get("equipment_name") or row.get("asset_label") or "").strip() or "—"


def _equipment_qty(row: dict) -> float:
    if row.get("qty") is not None:
        return _safe_float(row.get("qty"))
    # Legacy rows: treat days or hours as billable qty depending on which is set
    d, h = _safe_float(row.get("usage_days")), _safe_float(row.get("usage_hours"))
    if d and not h:
        return d
    if h and not d:
        return h
    return d + h


def _equipment_rate(row: dict) -> float:
    if row.get("rate") is not None:
        return _safe_float(row.get("rate"))
    d, h = _safe_float(row.get("usage_days")), _safe_float(row.get("usage_hours"))
    if d and not h:
        return _safe_float(row.get("rate_per_day"))
    if h and not d:
        return _safe_float(row.get("rate_per_hour"))
    return max(_safe_float(row.get("rate_per_day")), _safe_float(row.get("rate_per_hour")))


def _equipment_basis(row: dict) -> str:
    notes = str(row.get("notes") or "")
    if "Basis: Week" in notes:
        return "Week"
    if "Basis: Day" in notes:
        return "Day"
    if "Basis: Hour" in notes:
        return "Hour"
    b = str(row.get("basis") or "").strip()
    if b:
        return b
    d, h = _safe_float(row.get("usage_days")), _safe_float(row.get("usage_hours"))
    if d and not h:
        return "Day"
    if h and not d:
        return "Hour"
    if d and h:
        return "Mixed"
    return "—"


def _equipment_line_total(row: dict) -> float:
    for key in ("total_cost", "line_total"):
        if row.get(key) is not None and str(row.get(key)).strip() != "":
            return _safe_float(row.get(key))
    return _equipment_qty(row) * _equipment_rate(row)


def _labor_rows_time_entries(
    grid_rows: list[dict],
    job_id: Any,
    employees_by_id: dict[str, dict],
) -> list[dict[str, Any]]:
    """Read-only labor lines from ``time_entries`` only (Phase 1)."""
    out: list[dict[str, Any]] = []
    for te in grid_rows:
        if not te.get("job_id"):
            continue
        if str(te.get("job_id")) != str(job_id):
            continue
        eid = str(te.get("employee_id") or "")
        emp = employees_by_id.get(eid)
        name = str(emp.get("name") or "").strip() if emp else "—"
        hours = _safe_float(te.get("hours"))
        rate = _safe_float(emp.get("hourly_rate")) if emp else 0.0
        line = hours * rate
        out.append(
            {
                "Employee": name,
                "Date": str(te.get("work_date") or "")[:10],
                "Hours": hours,
                "Rate": rate,
                "Total cost": line,
            }
        )
    return out


def _labor_total_from_rows(rows: list[dict]) -> float:
    return sum(_safe_float(r.get("Total cost")) for r in rows)


def _materials_for_job(rows: list[dict], job_id: Any) -> list[dict]:
    return [r for r in rows if str(r.get("job_id")) == str(job_id)]


def _material_total(rows: list[dict]) -> float:
    return sum(_material_line_total(r) for r in rows)


def _equipment_for_job(rows: list[dict], job_id: Any) -> list[dict]:
    return [r for r in rows if str(r.get("job_id")) == str(job_id)]


def _equipment_total(rows: list[dict]) -> float:
    return sum(_equipment_line_total(r) for r in rows)


def _render_bordered_section(title: str):
    """Flat section title matching the Phase 2 page shell."""
    return _section_card(title=title)


@contextmanager
def _section_card(*, title: str | None = None):
    st.markdown('<span class="ips-content-card-anchor ips-surface-soft"></span>', unsafe_allow_html=True)
    if title:
        st.markdown(f'<p class="ips-section-title">{html.escape(title)}</p>', unsafe_allow_html=True)
    yield


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("job_costing"):
        return
    st.markdown(
        '<span class="ips-job-costing-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    try:
        from app.components.headers import render_page_brand_header
    except ImportError:
        from components.headers import render_page_brand_header  # type: ignore
    render_page_brand_header(
        "Job Costing",
        "Costing by job — labor, materials, equipment, and estimate comparison.",
    )

    admin = _job_costing_admin_read()
    jobs: list[dict] = []
    estimates: list[dict] = []
    try:
        if admin:
            jobs = fetch_table_admin("jobs", limit=5000, order_by="job_number")
            estimates = fetch_table_admin("estimates", limit=5000, order_by="quote_number")
        else:
            jobs = fetch_table("jobs", limit=5000, order_by="job_number")
            estimates = fetch_table("estimates", limit=5000, order_by="quote_number")
    except Exception:
        try:
            jobs = fetch_table("jobs", limit=5000, order_by="job_number")
            estimates = fetch_table("estimates", limit=5000, order_by="quote_number")
        except Exception as exc:
            st.error(f"Could not load jobs or estimates: {exc!r}")
            return

    jobs = [j for j in (jobs or []) if j.get("id")]
    jobs_sorted = _sort_jobs(jobs)
    if not jobs_sorted:
        st.info("No jobs found.")
        return

    focus_jid = str(st.session_state.pop("jc_focus_job_id", "") or "").strip()
    if focus_jid:
        for i, j in enumerate(jobs_sorted):
            if str(j.get("id") or "").strip() == focus_jid:
                st.session_state["jc_selected_job_ix"] = i
                break

    estimate_by_id = {e.get("id"): e for e in (estimates or []) if e.get("id")}

    try:
        employees = fetch_table("employees", limit=5000, order_by="name")
    except Exception:
        employees = []
    employees_by_id = {str(e.get("id")): e for e in employees if e.get("id")}

    time_err: str | None = None
    grid_rows: list[dict] = []
    try:
        fn = fetch_table_admin if admin else fetch_table
        for ob in ("work_date", None):
            try:
                grid_rows = fn("time_entries", limit=50000, order_by=ob) if ob else fn("time_entries", limit=50000)
                grid_rows = list(grid_rows or [])
                break
            except Exception as exc:
                time_err = str(exc)
                if ob is None:
                    grid_rows = []
    except Exception as exc:
        time_err = str(exc)

    job_materials, jm_err = _fetch_table_graceful("job_materials", limit=50000, order_by="created_at")
    job_equipment, je_err = _fetch_table_graceful("job_equipment", limit=50000, order_by="created_at")

    # --- Job selector ---
    labels = [job_display_label(j) for j in jobs_sorted]
    if len(labels) != len(set(labels)):
        # Rare duplicate labels — disambiguate with id suffix for stable UX
        labels = [f"{job_display_label(j)} [{str(j.get('id'))[:8]}]" for j in jobs_sorted]

    if "jc_selected_job_ix" not in st.session_state:
        st.session_state.jc_selected_job_ix = 0
    if st.session_state.jc_selected_job_ix >= len(jobs_sorted):
        st.session_state.jc_selected_job_ix = 0
    ix = st.selectbox(
        "Job",
        list(range(len(jobs_sorted))),
        format_func=lambda i: labels[i],
        key="jc_selected_job_ix",
    )
    job = jobs_sorted[ix]
    job_id = job.get("id")

    try:
        from app.services.customer_locations import location_display_name_city_state
    except ImportError:
        from services.customer_locations import location_display_name_city_state  # type: ignore

    loc_hdr = ""
    clid = str(job.get("customer_location_id") or "").strip()
    if clid:
        loc_row = fetch_one("customer_locations", {"id": clid})
        if loc_row:
            loc_hdr = location_display_name_city_state(loc_row)
    if not loc_hdr:
        loc_hdr = str(job.get("location") or "").strip()
    if loc_hdr:
        st.caption(f"Location: {loc_hdr}")

    try:
        from app.services.delete_safety import job_costing_block_reason
    except ImportError:
        from services.delete_safety import job_costing_block_reason  # type: ignore

    _del_block = job_costing_block_reason(str(job_id), admin_read=admin)
    if _del_block:
        st.caption(f"⚠ {_del_block} — this job cannot be removed from Job Database until costing rows are cleared.")

    if time_err and not grid_rows:
        st.warning(f"Could not load **time_entries** for labor: {time_err}")

    if jm_err:
        st.warning(jm_err)
    if je_err:
        st.warning(je_err)

    # Linked quote (small)
    if job.get("estimate_id"):
        est = estimate_by_id.get(job.get("estimate_id"))
        qn = str(est.get("quote_number") or "").strip() if est else ""
        st.caption(
            f"Linked **estimate** (quote): `{qn or job.get('estimate_id')}` — "
            "estimate is the proposal; this page is the job costing record."
        )

    labor_rows = _labor_rows_time_entries(grid_rows, job_id, employees_by_id)
    labor_total = _labor_total_from_rows(labor_rows)

    mats_job = _materials_for_job(job_materials, job_id)
    equip_job = _equipment_for_job(job_equipment, job_id)
    material_total = _material_total(mats_job)
    equipment_total = _equipment_total(equip_job)

    total_job_cost = labor_total + material_total + equipment_total
    est_amt = _estimate_amount_for_job(job, estimate_by_id)
    variance = (est_amt - total_job_cost) if est_amt is not None else None

    # --- Summary cards ---
    with _section_card(title="Summary"):
        st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Labor cost", _money_str(labor_total))
        c2.metric("Material cost", _money_str(material_total))
        c3.metric("Equipment cost", _money_str(equipment_total))
        c4.metric("Total job cost", _money_str(total_job_cost))
        c5.metric("Estimate amount", _money_str(est_amt) if est_amt is not None else "—")
        c6.metric("Variance / margin", _money_str(variance) if variance is not None else "—")

    # --- Labor (read-only) ---
    lab_c = _render_bordered_section("Labor")
    with lab_c:
        st.caption("Source: **time_entries** for this ``job_id`` (hours × employee hourly rate).")
        if labor_rows:
            df = pd.DataFrame(labor_rows)
            show = df.copy()
            show["Rate"] = show["Rate"].map(_money_str)
            show["Total cost"] = show["Total cost"].map(_money_str)
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.info("No **time_entries** rows for this job yet.")
        st.markdown(f"**Labor total:** {_money_str(labor_total)}")

    can_edit = current_role() in {"admin", "pm"}

    # --- Materials ---
    mat_c = _render_bordered_section("Materials")
    with mat_c:
        if jm_err:
            st.error("Cannot add materials until **job_materials** exists.")
        elif can_edit:
            with st.form("jc_material_add", clear_on_submit=True):
                mn = st.text_input("Material name", key=f"jc_mn_{job_id}")
                q = st.number_input("Qty", min_value=0.0, value=1.0, step=0.25, key=f"jc_mq_{job_id}")
                uc = st.number_input("Unit cost", min_value=0.0, value=0.0, step=0.01, key=f"jc_muc_{job_id}")
                if st.form_submit_button("Add material"):
                    if not mn.strip():
                        st.error("Material name is required.")
                    elif q <= 0:
                        st.error("Qty must be greater than zero.")
                    else:
                        line = q * uc
                        payload = {
                            "job_id": str(job_id),
                            "item_name": mn.strip(),
                            "quantity": float(q),
                            "unit_cost": float(uc),
                            "line_total": round(line, 2),
                            "notes": "",
                        }
                        try:
                            _insert_row_resilient("job_materials", payload)
                            st.success("Material added.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Insert failed: {exc!r}")
        else:
            st.caption("Read-only: admin or pm can add materials.")

        if mats_job:
            view = pd.DataFrame(
                [
                    {
                        "Material": _material_display_name(r),
                        "Qty": _material_qty(r),
                        "Unit cost": _material_unit_cost(r),
                        "Total cost": _material_line_total(r),
                    }
                    for r in mats_job
                ]
            )
            vc = view.copy()
            vc["Unit cost"] = vc["Unit cost"].map(_money_str)
            vc["Total cost"] = vc["Total cost"].map(_money_str)
            st.dataframe(vc, use_container_width=True, hide_index=True)
        else:
            st.caption("No material lines for this job.")
        st.markdown(f"**Materials total:** {_money_str(material_total)}")

    # --- Equipment ---
    eq_c = _render_bordered_section("Equipment")
    with eq_c:
        if je_err:
            st.error("Cannot add equipment until **job_equipment** exists.")
        elif can_edit:
            with st.form("jc_equipment_add", clear_on_submit=True):
                en = st.text_input("Equipment name", key=f"jc_en_{job_id}")
                q = st.number_input("Qty", min_value=0.0, value=1.0, step=0.25, key=f"jc_eq_{job_id}")
                rate = st.number_input("Rate", min_value=0.0, value=0.0, step=0.01, key=f"jc_er_{job_id}")
                basis = st.selectbox("Basis", ["Day", "Hour", "Week"], key=f"jc_eb_{job_id}")
                if st.form_submit_button("Add equipment"):
                    if not en.strip():
                        st.error("Equipment name is required.")
                    elif q <= 0:
                        st.error("Qty must be greater than zero.")
                    else:
                        line = q * rate
                        usage_days = float(q) if basis == "Day" else 0.0
                        rate_per_day = float(rate) if basis == "Day" else 0.0
                        usage_hours = float(q) if basis == "Hour" else 0.0
                        rate_per_hour = float(rate) if basis == "Hour" else 0.0
                        if basis == "Week":
                            # Store weeks in usage_days + rate in rate_per_day for stable display;
                            # line_total remains qty × rate (see _equipment_basis notes check).
                            usage_days = float(q)
                            rate_per_day = float(rate)
                            usage_hours = 0.0
                            rate_per_hour = 0.0
                        payload = {
                            "job_id": str(job_id),
                            "asset_id": None,
                            "asset_label": en.strip(),
                            "usage_hours": usage_hours,
                            "usage_days": usage_days,
                            "rate_per_hour": rate_per_hour,
                            "rate_per_day": rate_per_day,
                            "line_total": round(line, 2),
                            "notes": f"Basis: {basis}",
                        }
                        try:
                            _insert_row_resilient("job_equipment", payload)
                            st.success("Equipment line added.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Insert failed: {exc!r}")
        else:
            st.caption("Read-only: admin or pm can add equipment.")

        if equip_job:
            view = pd.DataFrame(
                [
                    {
                        "Equipment": _equipment_display_name(r),
                        "Qty": _equipment_qty(r),
                        "Rate": _equipment_rate(r),
                        "Basis": _equipment_basis(r),
                        "Total cost": _equipment_line_total(r),
                    }
                    for r in equip_job
                ]
            )
            vc = view.copy()
            vc["Rate"] = vc["Rate"].map(_money_str)
            vc["Total cost"] = vc["Total cost"].map(_money_str)
            st.dataframe(vc, use_container_width=True, hide_index=True)
        else:
            st.caption("No equipment lines for this job.")
        st.markdown(f"**Equipment total:** {_money_str(equipment_total)}")

    # --- Variance recap (compact) ---
    with _section_card(title="Totals & variance"):
        st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
        recap = pd.DataFrame(
            {
                "Item": [
                    "Labor",
                    "Materials",
                    "Equipment",
                    "Total job cost",
                    "Estimate",
                    "Variance",
                ],
                "Amount": [
                    _money_str(labor_total),
                    _money_str(material_total),
                    _money_str(equipment_total),
                    _money_str(total_job_cost),
                    _money_str(est_amt) if est_amt is not None else "—",
                    _money_str(variance) if variance is not None else "—",
                ],
            }
        )
        st.dataframe(recap, use_container_width=True, hide_index=True)
