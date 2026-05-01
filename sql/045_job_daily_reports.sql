-- Supervisor Daily Reports per job.
-- Run after jobs, employees, profiles, and storage setup migrations.

create extension if not exists pgcrypto;

create table if not exists public.job_daily_reports (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    report_date date not null,
    supervisor_name text not null default '',
    crew_size integer not null default 0 check (crew_size >= 0),
    main_goal text not null default '',
    midday_on_track boolean not null default true,
    midday_reason text not null default '',
    completed_today text not null default '',
    not_completed text not null default '',
    not_completed_reason text not null default '',
    delay_reasons text[] not null default '{}',
    delay_other text not null default '',
    tomorrow_plan text not null default '',
    submitted_by uuid null references public.profiles (id) on delete set null,
    submitted_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_job_daily_reports_job_date
    on public.job_daily_reports (job_id, report_date);
create index if not exists idx_job_daily_reports_report_date
    on public.job_daily_reports (report_date);
create index if not exists idx_job_daily_reports_job_id
    on public.job_daily_reports (job_id);

create table if not exists public.job_daily_report_crew (
    id uuid primary key default gen_random_uuid(),
    report_id uuid not null references public.job_daily_reports (id) on delete cascade,
    job_id uuid not null references public.jobs (id) on delete cascade,
    employee_id uuid null references public.employees (id) on delete set null,
    employee_name text not null default '',
    task text not null default '',
    hours numeric(8, 2) not null default 0 check (hours >= 0),
    notes text not null default '',
    sort_order integer not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_job_daily_report_crew_report_id
    on public.job_daily_report_crew (report_id);

create table if not exists public.job_daily_report_photos (
    id uuid primary key default gen_random_uuid(),
    report_id uuid not null references public.job_daily_reports (id) on delete cascade,
    job_id uuid not null references public.jobs (id) on delete cascade,
    report_date date not null,
    file_path text not null default '',
    file_name text not null default '',
    content_type text not null default '',
    uploaded_at timestamptz not null default now()
);

create index if not exists idx_job_daily_report_photos_report_id
    on public.job_daily_report_photos (report_id);

comment on table public.job_daily_reports is 'Supervisor daily production report per job and report date.';
comment on table public.job_daily_report_crew is 'Crew assignments captured on a supervisor daily report.';
comment on table public.job_daily_report_photos is 'Storage object paths for photos uploaded to supervisor daily reports.';

alter table if exists public.job_daily_reports enable row level security;
alter table if exists public.job_daily_report_crew enable row level security;
alter table if exists public.job_daily_report_photos enable row level security;

drop policy if exists "Allow read access" on public.job_daily_reports;
create policy "Allow read access" on public.job_daily_reports for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_daily_reports;
create policy "Allow insert access" on public.job_daily_reports for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_daily_reports;
create policy "Allow update access" on public.job_daily_reports for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_daily_reports;
create policy "Allow delete access" on public.job_daily_reports for delete to authenticated using (true);

drop policy if exists "Allow read access" on public.job_daily_report_crew;
create policy "Allow read access" on public.job_daily_report_crew for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_daily_report_crew;
create policy "Allow insert access" on public.job_daily_report_crew for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_daily_report_crew;
create policy "Allow update access" on public.job_daily_report_crew for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_daily_report_crew;
create policy "Allow delete access" on public.job_daily_report_crew for delete to authenticated using (true);

drop policy if exists "Allow read access" on public.job_daily_report_photos;
create policy "Allow read access" on public.job_daily_report_photos for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_daily_report_photos;
create policy "Allow insert access" on public.job_daily_report_photos for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_daily_report_photos;
create policy "Allow update access" on public.job_daily_report_photos for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_daily_report_photos;
create policy "Allow delete access" on public.job_daily_report_photos for delete to authenticated using (true);
