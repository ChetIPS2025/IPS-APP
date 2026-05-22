"""
Jobs module — Supabase reads/writes.

Schema assumptions: table ``jobs`` with columns job_number, job_name, customer_id,
status, start_date, target_completion_date, notes, supervisor (optional).
"""

from __future__ import annotations

from app.services.phase2_modules_service import (
    delete_job,
    list_jobs,
    normalize_job,
    save_job,
)

__all__ = ["delete_job", "list_jobs", "normalize_job", "save_job"]
