-- =============================================================================
-- 006_timekeeping.sql — Timekeeping module
-- Depends on: 001_core.sql (employees), 002_jobs.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- time_entries (PM matrix / daily job hours)
-- -----------------------------------------------------------------------------
create table if not exists public.time_entries (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    job_id uuid not null references public.jobs (id) on delete cascade,
    work_date date not null,
    hours numeric(8, 2) not null default 0,
    time_type text not null default 'ST',
    notes text not null default '',
    approved boolean not null default false,
    created_by uuid references public.profiles (id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint time_entries_type_check check (time_type in ('ST', 'OT', 'DT'))
);

create unique index if not exists uq_time_entries_employee_job_day_type
    on public.time_entries (employee_id, job_id, work_date, time_type);

create index if not exists idx_time_entries_work_date on public.time_entries (work_date);
create index if not exists idx_time_entries_employee on public.time_entries (employee_id, work_date);

drop trigger if exists trg_time_entries_updated_at on public.time_entries;
create trigger trg_time_entries_updated_at
    before update on public.time_entries
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- employee_timekeeping_weeks (weekly summary / approval)
-- -----------------------------------------------------------------------------
create table if not exists public.employee_timekeeping_weeks (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    week_start date not null,
    st_total numeric not null default 0,
    ot_total numeric not null default 0,
    dt_total numeric not null default 0,
    status text not null default 'Pending',
    approved_by uuid references public.profiles (id) on delete set null,
    approved_at timestamptz,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint employee_timekeeping_weeks_unique unique (employee_id, week_start),
    constraint employee_timekeeping_weeks_status_check
        check (status in ('Pending', 'Approved', 'Rejected'))
);

create index if not exists idx_timekeeping_weeks_employee
    on public.employee_timekeeping_weeks (employee_id, week_start desc);

drop trigger if exists trg_timekeeping_weeks_updated_at on public.employee_timekeeping_weeks;
create trigger trg_timekeeping_weeks_updated_at
    before update on public.employee_timekeeping_weeks
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- employee_timekeeping_days (editable weekly grid)
-- -----------------------------------------------------------------------------
create table if not exists public.employee_timekeeping_days (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    week_start date not null,
    work_date date not null,
    job_id uuid references public.jobs (id) on delete set null,
    job_label text not null default '',
    st_hours numeric not null default 0,
    ot_hours numeric not null default 0,
    dt_hours numeric not null default 0,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint employee_timekeeping_days_unique unique (employee_id, work_date, job_id)
);

create index if not exists idx_timekeeping_days_employee_week
    on public.employee_timekeeping_days (employee_id, week_start);

-- -----------------------------------------------------------------------------
-- weekly_timesheets (export / customer sign-off token — optional)
-- -----------------------------------------------------------------------------
create table if not exists public.weekly_timesheets (
    id uuid primary key default gen_random_uuid(),
    employee_id uuid not null references public.employees (id) on delete cascade,
    week_start date not null,
    status text not null default 'draft',
    sign_token uuid default gen_random_uuid(),
    signed_at timestamptz,
    created_at timestamptz not null default now(),
    constraint weekly_timesheets_unique unique (employee_id, week_start)
);

create index if not exists idx_weekly_timesheets_token on public.weekly_timesheets (sign_token);

-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------
alter table public.time_entries enable row level security;
alter table public.employee_timekeeping_weeks enable row level security;
alter table public.employee_timekeeping_days enable row level security;
alter table public.weekly_timesheets enable row level security;

drop policy if exists time_entries_select on public.time_entries;
create policy time_entries_select on public.time_entries for select to authenticated using (true);
drop policy if exists time_entries_write on public.time_entries;
create policy time_entries_write on public.time_entries for all to authenticated using (true) with check (true);

drop policy if exists timekeeping_weeks_select on public.employee_timekeeping_weeks;
create policy timekeeping_weeks_select on public.employee_timekeeping_weeks for select to authenticated using (true);
drop policy if exists timekeeping_weeks_write on public.employee_timekeeping_weeks;
create policy timekeeping_weeks_write on public.employee_timekeeping_weeks for all to authenticated using (true) with check (true);

drop policy if exists timekeeping_days_select on public.employee_timekeeping_days;
create policy timekeeping_days_select on public.employee_timekeeping_days for select to authenticated using (true);
drop policy if exists timekeeping_days_write on public.employee_timekeeping_days;
create policy timekeeping_days_write on public.employee_timekeeping_days for all to authenticated using (true) with check (true);

drop policy if exists weekly_timesheets_select on public.weekly_timesheets;
create policy weekly_timesheets_select on public.weekly_timesheets for select to authenticated using (true);
drop policy if exists weekly_timesheets_write on public.weekly_timesheets;
create policy weekly_timesheets_write on public.weekly_timesheets for all to authenticated using (true) with check (true);

comment on table public.employee_timekeeping_weeks is 'Weekly approval summary (IPS Timekeeping module).';
comment on table public.employee_timekeeping_days is 'Per-day ST/OT/DT grid rows.';
