-- Separate straight-time vs. overtime lines per employee / job / calendar day.
-- Run in Supabase SQL editor after prior time_entries migrations.

alter table public.time_entries add column if not exists time_type text;

update public.time_entries
set time_type = 'ST'
where time_type is null or trim(time_type) = '';

alter table public.time_entries alter column time_type set default 'ST';

alter table public.time_entries alter column time_type set not null;

alter table public.time_entries drop constraint if exists time_entries_time_type_check;

alter table public.time_entries
    add constraint time_entries_time_type_check check (time_type in ('ST', 'OT'));

-- Legacy uniqueness: one row per employee × job × day (no time type).
drop index if exists public.uq_time_entries_employee_job_day;

-- Job rows: allow ST and OT on the same job/day.
create unique index if not exists uq_time_entries_emp_job_date_ttype
    on public.time_entries (employee_id, job_id, work_date, time_type)
    where job_id is not null;

-- Non-job rows (optional): same employee/day/category split by ST/OT.
create unique index if not exists uq_time_entries_emp_nj_date_ttype
    on public.time_entries (employee_id, non_job_code, work_date, time_type)
    where job_id is null and coalesce(trim(non_job_code), '') <> '';

comment on column public.time_entries.time_type is 'Straight time (ST) or overtime (OT); pairs with hours for the same job and day.';
