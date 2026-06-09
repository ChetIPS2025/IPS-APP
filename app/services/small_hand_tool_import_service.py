"""CSV bulk import for quantity-based small hand tools."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

try:
    from app.services.repository import ServiceResult, clear_all_data_caches
    from app.services.small_hand_tool_service import (
        HAND_TOOL_CATEGORIES,
        HAND_TOOL_CONDITIONS,
        HAND_TOOL_STATUSES,
        import_hand_tool_row,
    )
except ImportError:
    from services.repository import ServiceResult, clear_all_data_caches  # type: ignore
    from services.small_hand_tool_service import (  # type: ignore
        HAND_TOOL_CATEGORIES,
        HAND_TOOL_CONDITIONS,
        HAND_TOOL_STATUSES,
        import_hand_tool_row,
    )

_TEMPLATE_HEADERS = (
    "tool_name",
    "category",
    "model_number",
    "serial_number",
    "expected_qty",
    "actual_qty",
    "location",
    "trailer",
    "job",
    "status",
    "condition",
    "notes",
)

_TEMPLATE_SAMPLE = (
    "Channel-lock Pliers 10in",
    "Pliers",
    "440",
    "",
    "2",
    "2",
    "Shop tool crib",
    "",
    "",
    "Available",
    "Good",
    "Example row — delete before import",
)

_IMPORT_ALIASES: dict[str, str] = {
    "tool_name": "tool_name",
    "name": "tool_name",
    "tool": "tool_name",
    "category": "category",
    "model_number": "model_number",
    "model": "model_number",
    "model_no": "model_number",
    "serial_number": "serial_number",
    "serial": "serial_number",
    "serial_no": "serial_number",
    "expected_qty": "expected_qty",
    "expected": "expected_qty",
    "quantity_expected": "expected_qty",
    "qty_expected": "expected_qty",
    "actual_qty": "actual_qty",
    "actual": "actual_qty",
    "quantity_on_hand": "actual_qty",
    "qty": "actual_qty",
    "quantity": "actual_qty",
    "location": "location",
    "storage_location": "location",
    "trailer": "trailer",
    "trailer_asset_number": "trailer",
    "tool_trailer": "trailer",
    "job": "job",
    "job_number": "job",
    "assigned_job": "job",
    "status": "status",
    "condition": "condition",
    "notes": "notes",
    "note": "notes",
}


def _clean(raw: object) -> str:
    return str(raw or "").strip()


def _norm_col(name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().casefold()).strip("_")
    return _IMPORT_ALIASES.get(key, key)


def _parse_qty(raw: object) -> float | None:
    if raw is None or (isinstance(raw, str) and not str(raw).strip()):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def hand_tool_csv_template_bytes() -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_TEMPLATE_HEADERS)
    writer.writerow(_TEMPLATE_SAMPLE)
    return buf.getvalue().encode("utf-8-sig")


def parse_hand_tool_csv(data: bytes, filename: str = "") -> list[dict[str, Any]]:
    """Parse CSV or XLSX into normalized import row dicts."""
    name = _clean(filename).casefold()
    raw_rows: list[dict[str, Any]]

    if name.endswith((".xlsx", ".xls")):
        import pandas as pd

        df = pd.read_excel(io.BytesIO(data))
        raw_rows = df.to_dict(orient="records")
    else:
        text = data.decode("utf-8-sig", errors="replace")
        raw_rows = list(csv.DictReader(io.StringIO(text)))

    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        norm: dict[str, Any] = {"_source_row": len(rows) + 2}
        empty = True
        for col, val in raw.items():
            if val is None or (isinstance(val, float) and val != val):
                continue
            text_val = _clean(val)
            if not text_val:
                continue
            key = _norm_col(str(col))
            if key:
                norm[key] = val
                empty = False
        if not empty:
            rows.append(norm)
    return rows


def _map_category(raw: object) -> str:
    text = _clean(raw)
    if not text:
        return "Other"
    for cat in HAND_TOOL_CATEGORIES:
        if text.casefold() == cat.casefold():
            return cat
    return text if text in HAND_TOOL_CATEGORIES else "Other"


def _normalize_status(raw: object) -> str:
    text = _clean(raw) or "Available"
    for status in HAND_TOOL_STATUSES:
        if text.casefold() == status.casefold():
            return status
    return "Available"


def _normalize_condition(raw: object) -> str:
    text = _clean(raw) or "Good"
    for cond in HAND_TOOL_CONDITIONS:
        if text.casefold() == cond.casefold():
            return cond
    return "Good"


def _resolve_trailer_id(trailer_ref: str, *, assets_by_number: dict[str, str], assets_by_label: dict[str, str]) -> str:
    ref = _clean(trailer_ref)
    if not ref:
        return ""
    key = ref.casefold()
    if key in assets_by_number:
        return assets_by_number[key]
    if key in assets_by_label:
        return assets_by_label[key]
    if " · " in ref:
        number = ref.split(" · ", 1)[0].strip().casefold()
        if number in assets_by_number:
            return assets_by_number[number]
    return ""


def _resolve_job_id(job_ref: str, *, jobs_by_number: dict[str, str], jobs_by_label: dict[str, str]) -> str:
    ref = _clean(job_ref)
    if not ref:
        return ""
    key = ref.casefold()
    if key in jobs_by_number:
        return jobs_by_number[key]
    if key in jobs_by_label:
        return jobs_by_label[key]
    if " · " in ref:
        number = ref.split(" · ", 1)[0].strip().casefold()
        if number in jobs_by_number:
            return jobs_by_number[number]
    return ""


def _build_lookup_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    trailer_by_number: dict[str, str] = {}
    trailer_by_label: dict[str, str] = {}
    job_by_number: dict[str, str] = {}
    job_by_label: dict[str, str] = {}

    try:
        from app.services.asset_kits_service import get_tool_trailers
    except ImportError:
        from services.asset_kits_service import get_tool_trailers  # type: ignore

    for trailer in get_tool_trailers():
        tid = _clean(trailer.get("id"))
        if not tid:
            continue
        number = _clean(trailer.get("asset_number") or trailer.get("asset_id"))
        name = _clean(trailer.get("asset_name") or trailer.get("name") or "Trailer")
        if number:
            trailer_by_number[number.casefold()] = tid
            trailer_by_number[_clean(trailer.get("asset_id")).casefold()] = tid
        label = f"{number} · {name}" if number else name
        trailer_by_label[label.casefold()] = tid
        if name:
            trailer_by_label[name.casefold()] = tid

    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore

    for job in load_jobs():
        jid = _clean(job.get("id"))
        if not jid:
            continue
        number = _clean(job.get("job_number"))
        name = _clean(job.get("job_name") or job.get("name"))
        if number:
            job_by_number[number.casefold()] = jid
        label = f"{number} · {name}" if number and name else (number or name or jid[:8])
        job_by_label[label.casefold()] = jid
        if name:
            job_by_label[name.casefold()] = jid

    return trailer_by_number, trailer_by_label, job_by_number, job_by_label


def validate_hand_tool_import_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Split parsed CSV rows into valid import payloads and invalid rows with reasons.

    Required: tool_name, expected_qty.
    """
    trailer_by_number, trailer_by_label, job_by_number, job_by_label = _build_lookup_maps()
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        row_num = int(row.get("_source_row") or idx + 1)
        name = _clean(row.get("tool_name"))
        expected_raw = row.get("expected_qty")
        expected = _parse_qty(expected_raw)

        errors: list[str] = []
        if not name:
            errors.append("tool_name is required")
        if expected is None:
            errors.append("expected_qty is required and must be a number")
        elif expected < 0:
            errors.append("expected_qty must be 0 or greater")

        trailer_ref = _clean(row.get("trailer"))
        job_ref = _clean(row.get("job"))
        trailer_id = _resolve_trailer_id(
            trailer_ref,
            assets_by_number=trailer_by_number,
            assets_by_label=trailer_by_label,
        )
        job_id = _resolve_job_id(
            job_ref,
            jobs_by_number=job_by_number,
            jobs_by_label=job_by_label,
        )
        if trailer_ref and not trailer_id:
            errors.append(f"trailer not found: {trailer_ref}")
        if job_ref and not job_id:
            errors.append(f"job not found: {job_ref}")

        preview = {
            "Row": row_num,
            "Tool": name or "—",
            "Model #": _clean(row.get("model_number")),
            "Serial": _clean(row.get("serial_number")),
            "Expected": expected if expected is not None else "—",
            "Actual": _parse_qty(row.get("actual_qty")),
            "Location": _clean(row.get("location")),
            "Trailer": trailer_ref or "—",
            "Job": job_ref or "—",
        }

        if errors:
            invalid.append({**preview, "Issues": "; ".join(errors)})
            continue

        actual = _parse_qty(row.get("actual_qty"))
        if actual is None:
            actual = expected
        preview["Actual"] = actual if actual is not None else "—"

        storage_type = "Tool Trailer" if trailer_id else "Warehouse"
        valid.append(
            {
                "_row_num": row_num,
                "_preview": preview,
                "tool_name": name,
                "category": _map_category(row.get("category")),
                "model_number": _clean(row.get("model_number")),
                "serial_number": _clean(row.get("serial_number")),
                "quantity_expected": expected,
                "quantity_on_hand": max(0.0, actual or 0.0),
                "storage_location": _clean(row.get("location")),
                "storage_type": storage_type,
                "container_asset_id": trailer_id or None,
                "assigned_job_id": job_id or None,
                "status": _normalize_status(row.get("status")),
                "condition": _normalize_condition(row.get("condition")),
                "notes": _clean(row.get("notes")),
            }
        )

    return valid, invalid


def bulk_import_hand_tools(rows: list[dict[str, Any]]) -> ServiceResult:
    """Import validated hand-tool payloads; rows should come from validate_hand_tool_import_rows."""
    created = 0
    errors: list[str] = []

    for row in rows:
        row_num = row.get("_row_num") or "?"
        payload = {k: v for k, v in row.items() if not str(k).startswith("_")}
        result = import_hand_tool_row(payload)
        if result.ok:
            created += 1
        else:
            errors.append(f"Row {row_num}: {result.error or 'failed'}")

    clear_all_data_caches()
    if created == 0 and errors:
        return ServiceResult(
            ok=False,
            error=errors[0] if len(errors) == 1 else "; ".join(errors[:5]),
            data={"created": 0, "errors": errors},
        )

    message = f"Imported {created} small hand tool(s)."
    if errors:
        message += f" {len(errors)} row(s) failed."
    return ServiceResult(
        ok=True,
        data={"created": created, "errors": errors, "message": message},
    )


__all__ = [
    "bulk_import_hand_tools",
    "hand_tool_csv_template_bytes",
    "parse_hand_tool_csv",
    "validate_hand_tool_import_rows",
]
