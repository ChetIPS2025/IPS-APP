-- =============================================================================
-- 002_jobs.sql — Jobs module
-- Depends on: 001_core.sql (customers, customer_locations, employees, estimates ref)
-- =============================================================================

create table if not exists public.jobs (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid references public.customers (id) on delete set null,
    location_id uuid references public.customer_locations (id) on delete set null,
    estimate_id uuid,
    job_number text,
    job_name text not null default '',
    customer_name text not null default '',
    location text not null default '',
    status text not null default 'Planning',
    project_manager text not null default '',
    supervisor text not null default '',
    supervisor_id uuid references public.employees (id) on delete set null,
    start_date date,
    end_date date,
    target_completion_date date,
    completed_date date,
    percent_complete int not null default 0,
    awarded_amount numeric(14, 2),
    scope_of_work text not null default '',
    notes text not null default '',
    source_type text not null default 'standalone',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_jobs_customer_id on public.jobs (customer_id);
create index if not exists idx_jobs_status on public.jobs (status);
create index if not exists idx_jobs_supervisor_id on public.jobs (supervisor_id);
create index if not exists idx_jobs_start_date on public.jobs (start_date);
create unique index if not exists uq_jobs_job_number
    on public.jobs (job_number)
    where job_number is not null and trim(job_number) <> '';

drop trigger if exists trg_jobs_updated_at on public.jobs;
create trigger trg_jobs_updated_at
    before update on public.jobs
    for each row execute function public.ips_set_updated_at();

-- -----------------------------------------------------------------------------
-- job_notes
-- -----------------------------------------------------------------------------
create table if not exists public.job_notes (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    note_text text not null,
    created_by uuid references public.profiles (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_job_notes_job_id on public.job_notes (job_id, created_at desc);

-- -----------------------------------------------------------------------------
-- job_daily_updates (field supervisor)
-- -----------------------------------------------------------------------------
create table if not exists public.job_daily_updates (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    update_date date not null default current_date,
    summary text not null default '',
    weather text not null default '',
    crew_count int,
    created_by uuid references public.profiles (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_job_daily_updates_job on public.job_daily_updates (job_id, update_date desc);

-- -----------------------------------------------------------------------------
-- job_activity_log
-- -----------------------------------------------------------------------------
create table if not exists public.job_activity_log (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    activity_type text not null default 'note',
    description text not null default '',
    created_by uuid references public.profiles (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_job_activity_job on public.job_activity_log (job_id, created_at desc);

-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------
alter table public.jobs enable row level security;
alter table public.job_notes enable row level security;
alter table public.job_daily_updates enable row level security;
alter table public.job_activity_log enable row level security;

drop policy if exists jobs_select on public.jobs;
create policy jobs_select on public.jobs for select to authenticated using (true);
drop policy if exists jobs_write on public.jobs;
create policy jobs_write on public.jobs for all to authenticated using (true) with check (true);

drop policy if exists job_notes_all on public.job_notes;
create policy job_notes_all on public.job_notes for all to authenticated using (true) with check (true);

drop policy if exists job_daily_updates_all on public.job_daily_updates;
create policy job_daily_updates_all on public.job_daily_updates for all to authenticated using (true) with check (true);

drop policy if exists job_activity_log_all on public.job_activity_log;
create policy job_activity_log_all on public.job_activity_log for all to authenticated using (true) with check (true);

comment on table public.jobs is 'Active projects / work orders (IPS Jobs module).';
comment on column public.jobs.notes is 'App maps to job description / scope notes.';
comment on column public.jobs.customer_name is 'Denormalized for list views; sync from customers optional.';
