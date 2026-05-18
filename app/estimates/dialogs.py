"""Import dialogs and workflow action wrappers for the Estimating module.

render_import_page()   Renders the full import page (PDF vendor + JSON).
render_json_import()   JSON-only import section.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# JSON import section
# ---------------------------------------------------------------------------

def render_json_import() -> None:
    """Render the JSON estimate import section."""
    try:
        try:
            from services.estimate_import_customer_match import (
                PLACEHOLDER,
                build_sorted_customer_names,
                classify_import_customer_matches,
                name_to_customer_id_map,
                resolve_picked_customer_id,
            )
        except ImportError:
            from app.services.estimate_import_customer_match import (  # type: ignore
                PLACEHOLDER,
                build_sorted_customer_names,
                classify_import_customer_matches,
                name_to_customer_id_map,
                resolve_picked_customer_id,
            )
    except Exception as e:
        st.error(f"Import helpers unavailable: {e}")
        return

    try:
        from pages.estimate_editor import (
            coalesce_imported_estimate,
            insert_imported_estimate,
            parse_estimate_json_bytes,
        )
    except ImportError:
        try:
            from app.pages.estimate_editor import (  # type: ignore
                coalesce_imported_estimate,
                insert_imported_estimate,
                parse_estimate_json_bytes,
            )
        except ImportError:
            st.error("JSON import helpers could not be loaded.")
            return

    from app.estimates.queries import fetch_customers_for_estimates

    st.markdown("### JSON estimate import")
    st.caption(
        "Upload **JSON** exports (same shape as Review / Save). "
        "Each file is matched to your **customer directory**. "
        "Confirm the customer below, then click **Import JSON file(s) to database**."
    )

    uploaded = st.file_uploader(
        "Upload JSON",
        type=["json"],
        accept_multiple_files=True,
        key="est_import_json_upload",
    )

    if not uploaded:
        st.caption("Upload one or more JSON estimate files above to preview and import.")
        return

    sig = tuple((i, f.name, len(f.getvalue())) for i, f in enumerate(uploaded))
    if st.session_state.get("estimates_import_sig") != sig:
        for k in list(st.session_state.keys()):
            if str(k).startswith("est_import_cust_"):
                st.session_state.pop(k, None)
        st.session_state["estimates_import_sig"] = sig
        cust_rows = fetch_customers_for_estimates()
        cached: list[dict] = []
        for f in uploaded:
            raw = f.getvalue()
            try:
                parsed = parse_estimate_json_bytes(raw)
                merged = coalesce_imported_estimate(parsed)
                qn = str(merged.get("quote_number", "") or "").strip()
                cls = classify_import_customer_matches(merged, cust_rows)
                cid = merged.get("customer_id")
                row_has_id = bool(cid) and cls.get("resolution") == "valid_existing"
                cached.append({
                    "file": f.name,
                    "kind": "json",
                    "merged": merged,
                    "error": None,
                    "quote_number": qn or "(will assign)",
                    "has_customer_id": "yes" if row_has_id else "needs confirmation",
                    "customer_classify": cls,
                    "customer_status": _import_customer_status_short(cls),
                })
            except Exception as exc:
                cached.append({
                    "file": f.name,
                    "kind": "json",
                    "merged": None,
                    "error": str(exc),
                    "quote_number": "—",
                    "has_customer_id": f"Error: {exc}",
                    "customer_classify": None,
                    "customer_status": "—",
                })
        st.session_state["estimates_import_cache"] = cached

    rows: list[dict] = st.session_state["estimates_import_cache"]
    cust_rows = fetch_customers_for_estimates()
    name_map = name_to_customer_id_map(cust_rows)
    all_names = build_sorted_customer_names(cust_rows)
    select_options = [PLACEHOLDER] + all_names

    preview_df = pd.DataFrame([
        {
            "file": r["file"],
            "kind": r["kind"],
            "quote_number": r["quote_number"],
            "customer": r.get("customer_status", "—"),
        }
        for r in rows
    ])
    st.dataframe(preview_df, use_container_width=True, hide_index=True)

    json_ready = [
        (i, r)
        for i, r in enumerate(rows)
        if r.get("kind") == "json" and r.get("merged") is not None and not r.get("error")
    ]

    if not json_ready:
        return

    st.markdown("##### Customer for each JSON file")
    st.caption(
        "Imports must be saved against a **real customer record**. "
        f"You cannot import while **{PLACEHOLDER}** is selected."
    )
    for i, r in json_ready:
        cls = r.get("customer_classify") or classify_import_customer_matches(r["merged"], cust_rows)
        st.markdown(f"**{r['file']}**")
        if cls.get("message"):
            st.info(str(cls["message"]))
        key = f"est_import_cust_{i}"
        if key not in st.session_state:
            default_name: str | None = None
            if cls.get("resolution") in ("valid_existing", "auto_single") and cls.get("customer_id"):
                cid0 = str(cls["customer_id"])
                default_name = next((n for n, cid in name_map.items() if cid == cid0), None)
            st.session_state[key] = default_name if default_name else PLACEHOLDER
        st.selectbox(
            "Customer directory",
            select_options,
            key=key,
            help="Pick the customer this estimate belongs to.",
        )

    st.markdown("##### JSON Import (direct)")
    if st.button(
        "Import JSON file(s) to database",
        type="secondary",
        use_container_width=True,
        key="est_import_json_run",
    ):
        errors: list[str] = []
        ok = 0
        notes: list[str] = []
        nm = name_to_customer_id_map(fetch_customers_for_estimates())
        for i, r in json_ready:
            f = uploaded[i]
            merged = r.get("merged")
            if merged is None:
                errors.append(f"{f.name}: nothing to import")
                continue
            chosen = st.session_state.get(f"est_import_cust_{i}")
            cid = resolve_picked_customer_id(chosen_label=chosen, name_to_id=nm)
            if not cid:
                errors.append(
                    f"{f.name}: choose a customer before importing "
                    f"(cannot save on {PLACEHOLDER!r})."
                )
                continue
            try:
                raw = f.getvalue()
                merged_save = dict(merged)
                merged_save["customer_id"] = cid
                _, suffix = insert_imported_estimate(
                    merged_save, f.name, raw, source_content_type="application/json"
                )
                ok += 1
                if suffix:
                    notes.append(f"{f.name}:{suffix}")
            except Exception as exc:
                errors.append(f"{f.name}: {exc}")

        for n in notes:
            st.info(n)
        for e in errors:
            st.error(e)
        if ok:
            from app.estimates.services import bump_estimates_cache
            bump_estimates_cache()
            st.success(f"Imported {ok} JSON estimate(s). Returning to list.")
            st.session_state["estimates_view"] = "list"
            st.rerun()


def _import_customer_status_short(cls: dict[str, Any] | None) -> str:
    if not cls:
        return "—"
    res = cls.get("resolution")
    if res == "valid_existing":
        return "ID in file (ok)"
    if res == "auto_single":
        return "Auto-matched"
    if res == "choose_ambiguous":
        return "Pick customer (multi)"
    if res in ("choose_open", "choose_required"):
        return "Pick customer"
    return "—"


# ---------------------------------------------------------------------------
# Full import page
# ---------------------------------------------------------------------------

def render_import_page() -> None:
    """Render the complete import page: PDF vendor quotes + JSON estimates."""
    try:
        try:
            from services.pdf_quote_import import render_vendor_pdf_quote_section
        except ImportError:
            from app.services.pdf_quote_import import render_vendor_pdf_quote_section  # type: ignore
        st.markdown("### PDF vendor quotes")
        render_vendor_pdf_quote_section()
    except Exception as e:
        st.warning(f"PDF vendor quote import unavailable: {e}")

    st.markdown("---")
    render_json_import()
