-- Supervisor daily field reports: one row per job per calendar day (upsert in app).
-- Run after public.jobs exists.

create table if not exists public.supervisor_daily_reports (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    report_date date not null,
    supervisor_name text not null default '',
    crew_size integer not null default 0 check (crew_size >= 0 and crew_size <= 500),
    main_goal text not null default '',
    midday_on_track boolean not null default true,
    midday_reason text not null default '',
    completed_today text not null default '',
    not_completed text not null default '',
    not_completed_reason text not null default '',
    delay_waiting_material boolean not null default false,
    delay_waiting_tools boolean not null default false,
    delay_waiting_direction boolean not null default false,
    delay_too_many_on_task boolean not null default false,
    delay_rework boolean not null default false,
    delay_equipment boolean not null default false,
    delay_customer boolean not null default false,
    delay_safety boolean not null default false,
    delay_other boolean not null default false,
    delay_other_notes text not null default '',
    tomorrows_plan text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by uuid null
);

create unique index if not exists uq_supervisor_daily_reports_job_date
    on public.supervisor_daily_reports (job_id, report_date);

create index if not exists idx_supervisor_daily_reports_report_date
    on public.supervisor_daily_reports (report_date desc);

comment on table public.supervisor_daily_reports is 'End-of-day supervisor report for a job (field workflow).';

create table if not exists public.supervisor_daily_report_crew (
    id uuid primary key default gen_random_uuid(),
    report_id uuid not null references public.supervisor_daily_reports (id) on delete cascade,
    employee_name text not null default '',
    task text not null default '',
    hours numeric(8, 2) not null default 0 check (hours >= 0 and hours <= 999.99),
    notes text not null default '',
    sort_order integer not null default 0
);

create index if not exists idx_supervisor_daily_report_crew_report_id
    on public.supervisor_daily_report_crew (report_id, sort_order);

create table if not exists public.supervisor_daily_report_photos (
    id uuid primary key default gen_random_uuid(),
    report_id uuid not null references public.supervisor_daily_reports (id) on delete cascade,
    storage_path text not null,
    file_name text not null default '',
    content_type text not null default 'application/octet-stream',
    created_at timestamptz not null default now()
);

create index if not exists idx_supervisor_daily_report_photos_report_id
    on public.supervisor_daily_report_photos (report_id);

-- RLS (same posture as sql/019_rls_authenticated_crud.sql)
alter table if exists public.supervisor_daily_reports enable row level security;
drop policy if exists "Allow read access" on public.supervisor_daily_reports;
create policy "Allow read access" on public.supervisor_daily_reports for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_daily_reports;
create policy "Allow insert access" on public.supervisor_daily_reports for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_daily_reports;
create policy "Allow update access" on public.supervisor_daily_reports for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_daily_reports;
create policy "Allow delete access" on public.supervisor_daily_reports for delete to authenticated using (true);

alter table if exists public.supervisor_daily_report_crew enable row level security;
drop policy if exists "Allow read access" on public.supervisor_daily_report_crew;
create policy "Allow read access" on public.supervisor_daily_report_crew for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_daily_report_crew;
create policy "Allow insert access" on public.supervisor_daily_report_crew for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_daily_report_crew;
create policy "Allow update access" on public.supervisor_daily_report_crew for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_daily_report_crew;
create policy "Allow delete access" on public.supervisor_daily_report_crew for delete to authenticated using (true);

alter table if exists public.supervisor_daily_report_photos enable row level security;
drop policy if exists "Allow read access" on public.supervisor_daily_report_photos;
create policy "Allow read access" on public.supervisor_daily_report_photos for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.supervisor_daily_report_photos;
create policy "Allow insert access" on public.supervisor_daily_report_photos for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.supervisor_daily_report_photos;
create policy "Allow update access" on public.supervisor_daily_report_photos for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.supervisor_daily_report_photos;
create policy "Allow delete access" on public.supervisor_daily_report_photos for delete to authenticated using (true);
