from __future__ import annotations

import re

_JOB_LEGACY = re.compile(r"^JOB-(\d+)$", re.IGNORECASE)


def job_display_label(job_number, job_name) -> str:
    """
    Human label for a job relationship: ``J00001 – Job name``.

    Accepts raw DB values (including legacy ``JOB-nnnn``) and falls back so linked records
    are never blank.
    """
    jn = str(job_number or "").strip()
    name = str(job_name or "").strip()
    if jn:
        m = _JOB_LEGACY.match(jn)
        if m:
            jn = f"J{int(m.group(1)):05d}"

    if jn and name:
        return f"{jn} – {name}"
    if name:
        return name
    return jn

