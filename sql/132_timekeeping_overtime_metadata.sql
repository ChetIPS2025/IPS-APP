-- Overtime calculation metadata for employee_timekeeping_days allocation rows.

alter table public.employee_timekeeping_days
    add column if not exists calculated_time_type text,
    add column if not exists final_time_type text,
    add column if not exists overtime_override boolean default false,
    add column if not exists overtime_override_by uuid references public.profiles(id),
    add column if not exists overtime_override_at timestamptz,
    add column if not exists overtime_override_reason text;

alter table public.company_settings
    add column if not exists timekeeping_weekend_counts_toward_40 boolean default false;
