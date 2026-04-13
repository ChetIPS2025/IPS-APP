-- 010_pm_matrix_time_tracking.sql
-- Idempotent migration: employees + time_entries for PM matrix time tracking.
-- Safe to re-run: creates missing tables/columns/indexes only; does not drop data.
--
-- Prerequisites: public.jobs must exist (005_jobs_job_number.sql or equivalent).
-- Legacy: weekly_timesheets / employee_time_entries (if any) are left untouched.
--
-- If CREATE UNIQUE INDEX uq_time_entries_employee_job_day fails due to duplicate
-- (employee_id, job_id, work_date) rows, deduplicate in SQL first, then re-run.

-- =============================================================================
-- public.employees
-- =============================================================================
create table if not exists public.employees (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    role text default ''::text,
    trade text,
    hourly_rate numeric(12, 2) not null default 0,
    overtime_rate numeric(12, 2),
    is_active boolean not null default true,
    notes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

alter table public.employees add column if not exists name text;
alter table public.employees add column if not exists role text;
alter table public.employees add column if not exists trade text;
alter table public.employees add column if not exists hourly_rate numeric(12, 2);
alter table public.employees add column if not exists overtime_rate numeric(12, 2);
alter table public.employees add column if not exists is_active boolean;
alter table public.employees add column if not exists notes text;
alter table public.employees add column if not exists created_at timestamptz;
alter table public.employees add column if not exists updated_at timestamptz;

-- Defaults for legacy rows (additive only)
alter table public.employees alter column hourly_rate set default 0;
alter table public.employees alter column is_active set default true;

create index if not exists idx_employees_is_active on public.employees(is_active);
create index if not exists idx_employees_name_lower on public.employees(lower(name));

comment on table public.employees is 'Workforce master for PM matrix time entry and labor costing.';

-- =============================================================================
-- public.time_entries  (PM calendar: one row per employee × job × calendar day)
-- =============================================================================
create table if not exists public.time_entries (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees(id) on delete cascade,
    job_id uuid not null references public.jobs(id) on delete cascade,
    work_date date not null,
    hours numeric(8, 2) not null default 0,
    notes text default ''::text,
    created_by uuid null,
    updated_at timestamptz not null default now()
);

alter table public.time_entries add column if not exists employee_id uuid;
alter table public.time_entries add column if not exists job_id uuid;
alter table public.time_entries add column if not exists work_date date;
alter table public.time_entries add column if not exists hours numeric(8, 2);
alter table public.time_entries add column if not exists notes text;
alter table public.time_entries add column if not exists created_by uuid;
alter table public.time_entries add column if not exists updated_at timestamptz;

alter table public.time_entries alter column hours set default 0;
alter table public.time_entries alter column updated_at set default now();

-- Do not add FK constraints on pre-existing time_entries tables with bad IDs;
-- new installs get FKs from CREATE TABLE. To attach FKs on legacy DBs after cleanup:
--   alter table public.time_entries
--     add constraint time_entries_employee_id_fkey
--     foreign key (employee_id) references public.employees(id) on delete cascade;
-- (Run only when data validates.)

create unique index if not exists uq_time_entries_employee_job_day
    on public.time_entries(employee_id, job_id, work_date);

create index if not exists idx_time_entries_work_date on public.time_entries(work_date);
create index if not exists idx_time_entries_employee_date on public.time_entries(employee_id, work_date);

comment on table public.time_entries is 'PM weekly matrix: one row per employee, job, and calendar day; unique (employee_id, job_id, work_date).';
