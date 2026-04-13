-- Weekly timesheet header + line items (run in Supabase SQL editor)
-- Depends on public.jobs(id) existing.

create table if not exists public.weekly_timesheets (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.jobs (id) on delete set null,
  job_number text default '',
  client_name text default '',
  job_name text default '',
  po_number text default '',
  sheet_date date,
  week_start date not null,
  signature_png_base64 text,
  created_by uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists weekly_timesheets_job_week_uidx
  on public.weekly_timesheets (job_id, week_start)
  where job_id is not null;

create table if not exists public.weekly_timesheet_lines (
  id uuid primary key default gen_random_uuid(),
  timesheet_id uuid not null references public.weekly_timesheets (id) on delete cascade,
  sort_order int not null default 0,
  employee_equipment text default '',
  class_name text default '',
  hours_mon numeric(12, 2) not null default 0,
  hours_tue numeric(12, 2) not null default 0,
  hours_wed numeric(12, 2) not null default 0,
  hours_thu numeric(12, 2) not null default 0,
  hours_fri numeric(12, 2) not null default 0,
  hours_sat numeric(12, 2) not null default 0,
  hours_sun numeric(12, 2) not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_weekly_timesheet_lines_sheet
  on public.weekly_timesheet_lines (timesheet_id);
