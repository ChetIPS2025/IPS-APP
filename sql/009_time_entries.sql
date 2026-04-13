-- Weekly grid time entries (PM calendar). Requires public.employees and public.jobs.

create table if not exists public.time_entries (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees(id) on delete cascade,
    job_id uuid not null references public.jobs(id) on delete cascade,
    work_date date not null,
    hours numeric(8,2) not null default 0 check (hours >= 0),
    notes text default '',
    created_by uuid null,
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_time_entries_employee_job_day
    on public.time_entries(employee_id, job_id, work_date);

create index if not exists idx_time_entries_work_date on public.time_entries(work_date);
create index if not exists idx_time_entries_employee_date on public.time_entries(employee_id, work_date);

comment on table public.time_entries is 'PM weekly calendar: one row per employee, job, and calendar day.';
