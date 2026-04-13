from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def score_duplicate(candidate: dict, asset: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    candidate_serial = _norm(candidate.get("serial_number"))
    asset_serial = _norm(asset.get("serial_number"))
    if candidate_serial and asset_serial and candidate_serial == asset_serial:
        score += 100
        reasons.append("exact serial number match")

    candidate_manufacturer = _norm(candidate.get("manufacturer"))
    asset_manufacturer = _norm(asset.get("manufacturer"))
    candidate_model = _norm(candidate.get("model"))
    asset_model = _norm(asset.get("model"))
    if candidate_manufacturer and candidate_model and candidate_manufacturer == asset_manufacturer and candidate_model == asset_model:
        score += 45
        reasons.append("manufacturer + model match")

    candidate_name = _norm(candidate.get("asset_name"))
    asset_name = _norm(asset.get("asset_name"))
    if candidate_name and asset_name and candidate_name == asset_name:
        score += 35
        reasons.append("asset name match")

    candidate_asset_id = _norm(candidate.get("asset_id"))
    asset_asset_id = _norm(asset.get("asset_id"))
    if candidate_asset_id and asset_asset_id and candidate_asset_id == asset_asset_id:
        score += 100
        reasons.append("asset id match")

    return score, reasons


def find_possible_duplicates(candidate: dict, assets: list[dict], threshold: int = 35) -> list[dict]:
    matches: list[dict] = []
    for asset in assets:
        score, reasons = score_duplicate(candidate, asset)
        if score >= threshold:
            enriched = dict(asset)
            enriched["_duplicate_score"] = score
            enriched["_duplicate_reasons"] = reasons
            matches.append(enriched)

    return sorted(matches, key=lambda x: x["_duplicate_score"], reverse=True)
