from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.db import fetch_table

from app.estimate.calculations import _D0, _dec, money

from app.services.phase2_modules_service import asset_is_rentable
def _truthy_rental(val) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "t")


def _safe_rate(val) -> Decimal:
    try:
        if val is None or val == "":
            return _D0
        return _dec(val)
    except Exception:
        return _D0


def load_estimate_equipment_from_assets() -> list[dict]:
    """
    Single source of truth for estimate equipment: ``assets`` with **category** = Equipment (case-insensitive).

    Shapes rows for :func:`compute_totals` (``equipment_item``, ``daily_rate``, …) plus ``asset_id`` and ``notes``
    for linking and display. Legacy ``equipment_catalog`` table is not used.
    """
    raw = fetch_table("assets", limit=5000, order_by="asset_name")
    out: list[dict] = []
    for a in raw:
        if str(a.get("category") or "").strip().lower() != "equipment":
            continue
        name = str(a.get("asset_name") or "").strip()
        if not name:
            continue
        rn = str(a.get("rental_notes") or "").strip()
        gn = str(a.get("notes") or "").strip()
        notes = rn if rn else gn
        aid = str(a.get("id") or "").strip()
        out.append(
            {
                "equipment_item": name,
                "daily_rate": _safe_rate(a.get("rental_daily_rate")),
                "weekly_rate": _safe_rate(a.get("rental_weekly_rate")),
                "monthly_rate": _safe_rate(a.get("rental_monthly_rate")),
                "is_rental": asset_is_rentable(a),
                "is_rentable": asset_is_rentable(a),
                "asset_id": aid,
                "notes": notes,
                "manufacturer": str(a.get("manufacturer") or "").strip(),
                "model": str(a.get("model") or "").strip(),
                "serial_number": str(a.get("serial_number") or "").strip(),
            }
        )
    return out


def _equipment_search_haystack(r: dict) -> str:
    return " ".join(
        [
            str(r.get("equipment_item") or ""),
            str(r.get("manufacturer") or ""),
            str(r.get("model") or ""),
            str(r.get("serial_number") or ""),
        ]
    ).lower()


def _equipment_matches_search(r: dict, search_q: str) -> bool:
    q = (search_q or "").strip().lower()
    if not q:
        return True
    hay = _equipment_search_haystack(r)
    for token in q.split():
        if token and token not in hay:
            return False
    return True


def _format_equipment_picker_label(r: dict, *, duplicate_name: bool) -> str:
    name = r["equipment_item"]
    rental_badge = " [RENTAL]" if (r.get("is_rentable") or r.get("is_rental")) else ""
    d, w, m = r["daily_rate"], r["weekly_rate"], r["monthly_rate"]
    rates = f"D {money(d)} · W {money(w)} · M {money(m)}"
    mfg = str(r.get("manufacturer") or "").strip()
    mod = str(r.get("model") or "").strip()
    ser = str(r.get("serial_number") or "").strip()
    tail_bits = [x for x in [mfg, mod, ser] if x]
    tail = f" · {' · '.join(tail_bits)}" if tail_bits else ""
    base = f"{name}{rental_badge} — {rates}{tail}"
    if duplicate_name:
        aid = str(r.get("asset_id") or "").strip()
        if len(aid) >= 8:
            base = f"{base} — id:{aid[:8]}"
    return base


def build_equipment_picker_maps(
    pricing_rows: list[dict],
    *,
    rental_only: bool,
    search_query: str,
    estimate_equipment_rows: list | None,
) -> tuple[list[str], dict[str, str], dict[str, str], dict[str, str]]:
    """
    Build rich picker labels and lookups for the equipment grid.

    Returns:
        option_labels — sorted selectbox options (display strings)
        label_to_name — maps each option to canonical ``equipment_item`` (asset name)
        name_to_label — maps asset name → display label when the name is unique in the filtered set
        asset_id_to_label — maps asset id → display label (stable when names collide)
    """
    active_names: set[str] = set()
    for row in estimate_equipment_rows or []:
        ei = str(row.get("equipment_item") or "").strip()
        if ei:
            active_names.add(ei)

    filtered: list[dict] = []
    for r in pricing_rows:
        name = str(r.get("equipment_item") or "").strip()
        passes_rental = (not rental_only) or bool(r.get("is_rentable") or r.get("is_rental"))
        keep_for_line = name in active_names
        if not passes_rental and not keep_for_line:
            continue
        if not _equipment_matches_search(r, search_query) and not keep_for_line:
            continue
        filtered.append(r)

    counts = Counter(str(r.get("equipment_item") or "") for r in filtered)
    label_to_name: dict[str, str] = {}
    name_to_label: dict[str, str] = {}
    asset_id_to_label: dict[str, str] = {}
    labels: list[str] = []

    for r in filtered:
        dup = counts[str(r.get("equipment_item") or "")] > 1
        label = _format_equipment_picker_label(r, duplicate_name=dup)
        base = label
        n = 0
        while label in label_to_name:
            n += 1
            label = f"{base} ({n})"
        labels.append(label)
        label_to_name[label] = r["equipment_item"]
        aid = str(r.get("asset_id") or "").strip()
        if aid:
            asset_id_to_label[aid] = label
        nm = str(r.get("equipment_item") or "").strip()
        if nm and counts[nm] == 1:
            name_to_label[nm] = label

    seen_names = set(label_to_name.values())
    for row in estimate_equipment_rows or []:
        ei = str(row.get("equipment_item") or "").strip()
        if ei and ei not in seen_names:
            labels.append(ei)
            label_to_name[ei] = ei
            seen_names.add(ei)

    labels_sorted = sorted(labels, key=str.casefold)
    return labels_sorted, label_to_name, name_to_label, asset_id_to_label


def enrich_equipment_rows_from_assets(
    rows: list[dict],
    pricing_rows: list[dict],
    *,
    picker_label_to_name: dict[str, str] | None = None,
) -> list[dict]:
    """
    Attach ``asset_id`` and ``equipment_notes`` when the line's ``equipment_item`` matches an Equipment asset name.
    Legacy text-only lines (no match) keep stored text; ``asset_id`` is omitted if unknown.

    ``picker_label_to_name`` maps grid cell values (rich labels) to canonical asset names when present.
    """
    by_name = {r["equipment_item"]: r for r in pricing_rows}
    lmap = picker_label_to_name or {}
    out: list[dict] = []
    for row in rows:
        r = dict(row)
        raw_cell = str(r.get("equipment_item") or "").strip()
        name = lmap.get(raw_cell, raw_cell)
        r["equipment_item"] = name
        meta = by_name.get(name)
        if meta and meta.get("asset_id"):
            r["asset_id"] = str(meta["asset_id"])
        else:
            r.pop("asset_id", None)
        if meta and meta.get("notes"):
            r["equipment_notes"] = str(meta["notes"])[:2000]
        else:
            r.pop("equipment_notes", None)
        out.append(r)
    return out


def _equipment_rows_core_for_editor(rows: list[dict] | None) -> list[dict]:
    """Only columns edited in the grid (metadata added back after save)."""
    keys = ("equipment_item", "qty", "basis", "duration")
    if not rows:
        return []
    return [{k: row.get(k) for k in keys} for row in rows]


def _equipment_core_with_picker_labels(
    rows_raw: list[dict],
    rows_core: list[dict],
    *,
    label_to_name: dict[str, str],
    name_to_label: dict[str, str],
    asset_id_to_label: dict[str, str],
) -> list[dict]:
    """Map stored canonical names / asset ids to rich selectbox labels for the current picker."""
    out: list[dict] = []
    for i, rc in enumerate(rows_core):
        rc = dict(rc)
        meta = rows_raw[i] if i < len(rows_raw) else {}
        ei = str(rc.get("equipment_item") or "").strip()
        aid = str(meta.get("asset_id") or "").strip()
        if aid and aid in asset_id_to_label:
            rc["equipment_item"] = asset_id_to_label[aid]
        elif ei in label_to_name:
            rc["equipment_item"] = ei
        elif ei in name_to_label:
            rc["equipment_item"] = name_to_label[ei]
        else:
            match = next((lab for lab, nm in label_to_name.items() if nm == ei), None)
            rc["equipment_item"] = match if match is not None else ei
        out.append(rc)
    return out

