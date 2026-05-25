-- =============================================================================
-- 088_create_job_daily_updates.sql — Job-specific daily field updates for Weekly Timesheets
-- Depends on: public.jobs, public.employees
-- Not related to public.company_updates (company announcements).
-- =============================================================================

alter table public.jobs
    add column if not exists po_number text;

-- Legacy table from 002_jobs.sql may only have summary/weather/crew_count.
create table if not exists public.job_daily_updates (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    update_date date not null default current_date,
    employee_id uuid null references public.employees (id) on delete set null,
    employee_name text,
    supervisor_id uuid null references public.employees (id) on delete set null,
    supervisor_name text,
    work_performed text,
    notes text,
    delays text,
    safety_notes text,
    weather text,
    created_by uuid null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.job_daily_updates
    add column if not exists employee_id uuid references public.employees (id) on delete set null,
    add column if not exists employee_name text,
    add column if not exists supervisor_id uuid references public.employees (id) on delete set null,
    add column if not exists supervisor_name text,
    add column if not exists work_performed text,
    add column if not exists notes text,
    add column if not exists delays text,
    add column if not exists safety_notes text,
    add column if not exists weather text,
    add column if not exists created_by uuid,
    add column if not exists updated_at timestamptz not null default now();

-- Legacy 002_jobs.sql column
alter table public.job_daily_updates
    add column if not exists summary text;

update public.job_daily_updates
set work_performed = coalesce(nullif(trim(work_performed), ''), nullif(trim(summary), ''))
where coalesce(trim(work_performed), '') = ''
  and coalesce(trim(summary), '') <> '';

create index if not exists idx_job_daily_updates_job_id
    on public.job_daily_updates (job_id);

create index if not exists idx_job_daily_updates_update_date
    on public.job_daily_updates (update_date);

create index if not exists idx_job_daily_updates_job_date
    on public.job_daily_updates (job_id, update_date);

drop trigger if exists trg_job_daily_updates_updated_at on public.job_daily_updates;
create trigger trg_job_daily_updates_updated_at
    before update on public.job_daily_updates
    for each row execute function public.ips_set_updated_at();

alter table public.job_daily_updates enable row level security;

drop policy if exists "job_daily_updates_all" on public.job_daily_updates;
create policy "job_daily_updates_all"
    on public.job_daily_updates
    for all
    to authenticated
    using (true)
    with check (true);

comment on table public.job_daily_updates is 'Job-specific daily field work reports (not company announcements).';
