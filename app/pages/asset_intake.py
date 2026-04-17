from __future__ import annotations

import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.branding import render_header
    from app.db import fetch_table
    from app.ui import IPS_NAV_PENDING_KEY
    from app.services.asset_constants import ASSET_CONDITIONS, ASSET_STATUSES, ASSET_TYPES
    from app.services.asset_photo_autofill import extract_asset_from_photos
    from app.services.asset_service import find_duplicates_for_asset, optional_numeric, save_asset
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_table  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore
    from services.asset_constants import ASSET_CONDITIONS, ASSET_STATUSES, ASSET_TYPES  # type: ignore
    from services.asset_photo_autofill import extract_asset_from_photos  # type: ignore
    from services.asset_service import find_duplicates_for_asset, optional_numeric, save_asset  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore


def _init_intake_widgets() -> None:
    defaults: dict[str, object] = {
        "intake_asset_id": "",
        "intake_asset_name": "",
        "intake_manufacturer": "",
        "intake_model": "",
        "intake_serial_number": "",
        "intake_year": "",
        "intake_asset_type": ASSET_TYPES[0],
        "intake_condition": ASSET_CONDITIONS[1] if len(ASSET_CONDITIONS) > 1 else ASSET_CONDITIONS[0],
        "intake_status": ASSET_STATUSES[0],
        "intake_location": "",
        "intake_yard_location": "",
        "intake_assigned_employee": "",
        "intake_department": "",
        "intake_hour_meter": 0.0,
        "intake_mileage": 0.0,
        "intake_purchase_cost": 0.0,
        "intake_current_value": 0.0,
        "intake_notes": "",
        "intake_category": "",
        "intake_subcategory": "",
        "intake_is_rental": False,
        "intake_rental_daily": 0.0,
        "intake_rental_weekly": 0.0,
        "intake_rental_monthly": 0.0,
        "intake_rental_notes": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if "intake_assigned_job" not in st.session_state:
        st.session_state["intake_assigned_job"] = ""
    if "intake_purchase_date" not in st.session_state:
        st.session_state["intake_purchase_date"] = None


def _apply_ai_to_widgets(result: dict) -> None:
    st.session_state["intake_asset_name"] = str(result.get("asset_name", "") or "").strip()
    st.session_state["intake_manufacturer"] = str(result.get("manufacturer", "") or "").strip()
    st.session_state["intake_model"] = str(result.get("model", "") or "").strip()
    st.session_state["intake_serial_number"] = str(result.get("serial_number", "") or "").strip()
    st.session_state["intake_location"] = str(result.get("location", "") or "").strip()
    st.session_state["intake_notes"] = str(result.get("notes", "") or "").strip()
    at = str(result.get("asset_type", "") or "").strip()
    st.session_state["intake_asset_type"] = at if at in ASSET_TYPES else "Other"
    cd = str(result.get("condition", "") or "").strip()
    st.session_state["intake_condition"] = cd if cd in ASSET_CONDITIONS else "Good"
    try:
        st.session_state["intake_hour_meter"] = float(result.get("hour_meter", 0) or 0)
    except (TypeError, ValueError):
        st.session_state["intake_hour_meter"] = 0.0
    try:
        st.session_state["intake_mileage"] = float(result.get("mileage", 0) or 0)
    except (TypeError, ValueError):
        st.session_state["intake_mileage"] = 0.0


# Per-field AI hints shown in the review expander (keys match asset_photo_autofill field_confidence / field_review_flags)
_INTAKE_AI_REVIEW_FIELDS: tuple[tuple[str, str], ...] = (
    ("manufacturer", "Manufacturer"),
    ("model", "Model"),
    ("serial_number", "Serial number"),
    ("condition", "Condition"),
    ("hour_meter", "Hour meter"),
    ("mileage", "Mileage"),
)


def _render_ai_extracted_summary(ai: dict) -> None:
    """Show key extracted fields after autofill, before user edits / save."""
    name = str(ai.get("asset_name") or "").strip() or "—"
    mfr = str(ai.get("manufacturer") or "").strip() or "—"
    model = str(ai.get("model") or "").strip() or "—"
    serial = str(ai.get("serial_number") or "").strip() or "—"

    with st.container(border=True):
        st.markdown("##### Extracted equipment (AI)")
        st.caption("These values are loaded into **Asset details** below — review and edit before saving.")

        a, b = st.columns(2)
        a.markdown(f"**Equipment name**  \n{name}")
        a.markdown(f"**Manufacturer**  \n{mfr}")
        b.markdown(f"**Model**  \n{model}")
        b.markdown(f"**Serial number**  \n{serial}")

        specs: dict[str, object] = {
            "asset_type": ai.get("asset_type"),
            "condition": ai.get("condition"),
            "location": str(ai.get("location") or "").strip() or None,
            "hour_meter": ai.get("hour_meter"),
            "mileage": ai.get("mileage"),
            "per_image_role": ai.get("per_image_role"),
        }
        notes = str(ai.get("notes") or "").strip()
        if notes:
            specs["notes"] = notes

        st.markdown("**Detected specs**")
        st.json(specs)

        with st.expander("Full AI extraction (raw JSON)", expanded=False):
            st.json(ai)


def _build_intake_payload(job_options: dict[str, str | None]) -> dict:
    pd = st.session_state.get("intake_purchase_date")
    payload = {
        "asset_id": str(st.session_state.get("intake_asset_id", "") or "").strip(),
        "asset_name": str(st.session_state.get("intake_asset_name", "") or "").strip(),
        "asset_type": st.session_state.get("intake_asset_type"),
        "manufacturer": str(st.session_state.get("intake_manufacturer", "") or "").strip(),
        "model": str(st.session_state.get("intake_model", "") or "").strip(),
        "serial_number": str(st.session_state.get("intake_serial_number", "") or "").strip(),
        "year": str(st.session_state.get("intake_year", "") or "").strip(),
        "status": st.session_state.get("intake_status"),
        "condition": st.session_state.get("intake_condition"),
        "location": str(st.session_state.get("intake_location", "") or "").strip(),
        "yard_location": str(st.session_state.get("intake_yard_location", "") or "").strip(),
        "assigned_employee": str(st.session_state.get("intake_assigned_employee", "") or "").strip(),
        "assigned_job_id": job_options.get(str(st.session_state.get("intake_assigned_job") or "")),
        "department": str(st.session_state.get("intake_department", "") or "").strip(),
        "hour_meter": float(st.session_state.get("intake_hour_meter") or 0),
        "mileage": float(st.session_state.get("intake_mileage") or 0),
        "purchase_cost": float(st.session_state.get("intake_purchase_cost") or 0),
        "current_value": float(st.session_state.get("intake_current_value") or 0),
        "purchase_date": pd.isoformat() if pd else None,
        "notes": str(st.session_state.get("intake_notes", "") or "").strip(),
        "category": str(st.session_state.get("intake_category", "") or "").strip(),
        "subcategory": str(st.session_state.get("intake_subcategory", "") or "").strip(),
        "is_rental": bool(st.session_state.get("intake_is_rental", False)),
        "rental_notes": str(st.session_state.get("intake_rental_notes", "") or "").strip(),
    }
    if payload["is_rental"]:
        payload["rental_daily_rate"] = optional_numeric(st.session_state.get("intake_rental_daily"))
        payload["rental_weekly_rate"] = optional_numeric(st.session_state.get("intake_rental_weekly"))
        payload["rental_monthly_rate"] = optional_numeric(st.session_state.get("intake_rental_monthly"))
    return payload


def _collect_intake_photo_files(save_photos: list | None) -> list[dict]:
    photo_files: list[dict] = []
    if save_photos:
        for photo in save_photos:
            photo_files.append(
                {
                    "file_name": photo.name,
                    "file_bytes": photo.getvalue(),
                    "photo_type": "overview",
                }
            )
    elif st.session_state.get("asset_intake_photo_meta"):
        photo_files = list(st.session_state["asset_intake_photo_meta"])
    return photo_files


def _finalize_intake_after_save(asset_row: dict) -> None:
    st.session_state["asset_detail_id"] = asset_row.get("id")
    st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
    st.session_state["asset_detail_flash"] = (
        f"Success: Asset saved ({asset_row.get('asset_id')} — {asset_row.get('asset_name')}). "
        "Photos are attached; review the profile below."
    )
    st.session_state.pop("asset_intake_ai", None)
    st.session_state.pop("asset_intake_photo_meta", None)
    st.session_state.pop("asset_intake_pending_save", None)
    _keep_uploaders = {"intake_ai_photos", "intake_save_photos"}
    for k in list(st.session_state.keys()):
        if k.startswith("intake_") and k not in _keep_uploaders:
            del st.session_state[k]
    _init_intake_widgets()
    st.session_state.pop("asset_db_add_mode", None)


def _run_intake_save(
    job_options: dict[str, str | None],
    *,
    save_photos: list | None,
    show_duplicate_panel: bool,
) -> None:
    payload = _build_intake_payload(job_options)
    if show_duplicate_panel:
        duplicates = find_duplicates_for_asset(payload)
        if duplicates:
            st.warning("Possible duplicate assets found. Review before saving.")
            for match in duplicates[:5]:
                st.write(
                    f"**{match.get('asset_id')} - {match.get('asset_name')}** | "
                    f"Score: {match.get('_duplicate_score')} | "
                    f"Reasons: {', '.join(match.get('_duplicate_reasons', []))}"
                )

    photo_files = _collect_intake_photo_files(save_photos)
    asset_row = save_asset(payload, photo_files=photo_files, created_by=current_profile().get("id"))
    _finalize_intake_after_save(asset_row)
    st.rerun()


def _render_intake_ai_field_review(ai: dict) -> None:
    fc = ai.get("field_confidence") or {}
    fr = ai.get("field_review_flags") or {}
    rows: list[dict[str, str]] = []
    for key, label in _INTAKE_AI_REVIEW_FIELDS:
        raw_c = fc.get(key)
        try:
            conf_str = f"{float(raw_c) * 100:.0f}%" if raw_c is not None else "—"
        except (TypeError, ValueError):
            conf_str = "—"
        flags = fr.get(key)
        if isinstance(flags, list) and flags:
            flags_str = "; ".join(str(x) for x in flags)
        else:
            flags_str = "—"
        rows.append({"Field": label, "Confidence": conf_str, "Review flags": flags_str})
    with st.expander("AI field review (confidence & flags)", expanded=False):
        st.dataframe(rows, hide_index=True, use_container_width=True)


def render_asset_intake_form() -> None:
    """Add-asset flow (AI, duplicates, save). Caller must enforce admin/estimator."""
    _init_intake_widgets()
    default_cat = st.session_state.pop("intake_category_default", None)
    if default_cat is not None:
        st.session_state["intake_category"] = str(default_cat)

    jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000, order_by="job_number"))
    job_options: dict[str, str | None] = {"": None}
    for job in jobs:
        label = job_row_select_label(job)
        if label and label != "—":
            job_options[label] = job.get("id")
    job_name_list = list(job_options.keys())

    st.caption("Upload photos and run AI to pre-fill key fields, then review and save.")

    st.subheader("AI autofill")
    ai_photos = st.file_uploader(
        "Equipment photos & documents (one or more)",
        type=["pdf", "heic", "jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="intake_ai_photos",
        help="Supported: PDF, HEIC, JPG, JPEG, PNG, WEBP. PDFs use rendered pages; HEIC is converted for analysis.",
    )

    ac1, ac2, ac3 = st.columns([1, 1, 2])
    with ac1:
        run_ai = st.button("Extract fields with AI", use_container_width=True, type="primary")
    with ac2:
        clear_ai = st.button("Clear AI suggestions", use_container_width=True)

    if clear_ai:
        st.session_state.pop("asset_intake_ai", None)
        st.session_state.pop("asset_intake_photo_meta", None)
        st.rerun()

    if run_ai:
        if not ai_photos:
            st.error("Upload at least one photo before running AI extraction.")
        else:
            try:
                with st.spinner("Analyzing uploads…"):
                    batch = [(f.getvalue(), f.name) for f in ai_photos]
                    result = extract_asset_from_photos(batch)
                st.session_state["asset_intake_ai"] = result
                st.session_state["asset_intake_photo_meta"] = [
                    {"file_name": f.name, "file_bytes": f.getvalue(), "photo_type": "overview"}
                    for f in ai_photos
                ]
                _apply_ai_to_widgets(result)
                st.success("Fields updated from AI — review and edit below before saving.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"AI extraction failed: {exc}")

    ai = st.session_state.get("asset_intake_ai")
    if ai:
        _render_ai_extracted_summary(ai)
        conf = float(ai.get("confidence", 0) or 0)
        m1, m2 = st.columns(2)
        m1.metric("AI confidence", f"{conf * 100:.0f}%")
        flags = ai.get("review_flags") or []
        if flags:
            m2.warning("Review flags: " + "; ".join(str(f) for f in flags))
        else:
            m2.caption("No review flags.")
        _render_intake_ai_field_review(ai)
        if st.button("Save Asset", type="primary", use_container_width=True, key="intake_save_asset"):
            st.session_state["asset_intake_pending_save"] = True
            st.rerun()

    st.divider()
    st.subheader("Asset details")

    c1, c2 = st.columns(2)
    c1.text_input("Asset ID (blank = auto)", key="intake_asset_id")
    c2.text_input("Asset Name", key="intake_asset_name")

    c3, c4, c5 = st.columns(3)
    c3.selectbox("Asset Type", ASSET_TYPES, key="intake_asset_type")
    c4.text_input("Manufacturer", key="intake_manufacturer")
    c5.text_input("Model", key="intake_model")

    c6, c7, c8 = st.columns(3)
    c6.text_input("Serial Number", key="intake_serial_number")
    c7.text_input("Year", key="intake_year")
    c8.selectbox("Condition", ASSET_CONDITIONS, key="intake_condition")

    c9, c10, c11 = st.columns(3)
    c9.selectbox("Status", ASSET_STATUSES, key="intake_status")
    c10.text_input("Location", key="intake_location")
    c11.text_input("Yard / Bay", key="intake_yard_location")

    c12, c13, c14 = st.columns(3)
    c12.text_input("Assigned Employee", key="intake_assigned_employee")
    c13.selectbox("Assigned Job", job_name_list, key="intake_assigned_job")
    c14.text_input("Department", key="intake_department")

    c15, c16, c17 = st.columns(3)
    c15.number_input("Hour Meter", min_value=0.0, step=1.0, key="intake_hour_meter")
    c16.number_input("Mileage", min_value=0.0, step=1.0, key="intake_mileage")
    c17.number_input("Purchase Cost", min_value=0.0, step=100.0, key="intake_purchase_cost")

    c18, c19 = st.columns(2)
    c18.number_input("Current Value", min_value=0.0, step=100.0, key="intake_current_value")
    c19.date_input("Purchase Date", key="intake_purchase_date")

    ic1, ic2 = st.columns(2)
    ic1.text_input("Category", key="intake_category")
    ic2.text_input("Subcategory", key="intake_subcategory")

    st.checkbox("Rent to Customer", key="intake_is_rental")
    if st.session_state.get("intake_is_rental"):
        ir1, ir2, ir3 = st.columns(3, gap="small")
        ir1.number_input("Daily rate", min_value=0.0, step=1.0, format="%.2f", key="intake_rental_daily")
        ir2.number_input("Weekly rate", min_value=0.0, step=1.0, format="%.2f", key="intake_rental_weekly")
        ir3.number_input("Monthly rate", min_value=0.0, step=1.0, format="%.2f", key="intake_rental_monthly")
        st.text_area("Rental notes", key="intake_rental_notes", height=72)

    st.text_area("Notes", key="intake_notes", height=96)

    st.subheader("Photos to save")
    save_photos = st.file_uploader(
        "Attach photos stored with this asset (optional; defaults to photos used for AI if any)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="intake_save_photos",
    )

    if st.session_state.pop("asset_intake_pending_save", False):
        try:
            _run_intake_save(job_options, save_photos=save_photos, show_duplicate_panel=True)
        except Exception as exc:
            st.error(f"Save failed: {exc}")

    if st.button("Check duplicate / Save", type="primary", use_container_width=True, key="intake_chk_save"):
        try:
            _run_intake_save(job_options, save_photos=save_photos, show_duplicate_panel=True)
        except Exception as exc:
            st.error(f"Save failed: {exc}")


def render() -> None:
    render_header("Asset Intake")

    if current_role() not in {"admin", "estimator"}:
        st.info("Only admin or estimator users can add assets.")
        return

    render_asset_intake_form()
