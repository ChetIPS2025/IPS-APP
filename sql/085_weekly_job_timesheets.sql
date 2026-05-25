-- Weekly job timesheets (customer-facing printable form + approval workflow).
-- Run after sql/004_weekly_timesheets.sql, sql/031_job_weekly_timesheets.sql, sql/002_jobs.sql.

create extension if not exists pgcrypto;

create table if not exists public.weekly_job_timesheets (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    customer_id uuid null references public.customers (id) on delete set null,
    week_start date not null,
    week_end date not null,
    job_number text not null default '',
    client_name text not null default '',
    job_name text not null default '',
    po_number text not null default '',
    sheet_date date null,
    approved_by text not null default '',
    work_performed text not null default '',
    status text not null default 'Draft'
        check (status in ('Draft', 'Sent', 'Approved', 'Signed', 'Rejected')),
    signature_data text not null default '',
    signature_url text not null default '',
    signed_at timestamptz null,
    signed_by_name text not null default '',
    signed_by_email text not null default '',
    unsigned_pdf_url text not null default '',
    pdf_file_url text not null default '',
    locked_snapshot jsonb null,
    locked_at timestamptz null,
    sign_token uuid not null default gen_random_uuid(),
    sign_token_expires_at timestamptz null,
    created_by uuid null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_weekly_job_timesheets_job_week
    on public.weekly_job_timesheets (job_id, week_start);

create unique index if not exists uq_weekly_job_timesheets_sign_token
    on public.weekly_job_timesheets (sign_token);

create table if not exists public.weekly_job_timesheet_lines (
    id uuid primary key default gen_random_uuid(),
    timesheet_id uuid not null references public.weekly_job_timesheets (id) on delete cascade,
    line_type text not null default 'labor'
        check (line_type in ('labor', 'equipment', 'material', 'expense')),
    sort_order int not null default 0,
    description text not null default '',
    class_name text not null default '',
    hours_mon numeric(12, 2) not null default 0,
    hours_tue numeric(12, 2) not null default 0,
    hours_wed numeric(12, 2) not null default 0,
    hours_thu numeric(12, 2) not null default 0,
    hours_fri numeric(12, 2) not null default 0,
    hours_sat numeric(12, 2) not null default 0,
    hours_sun numeric(12, 2) not null default 0,
    st_hours numeric(12, 2) not null default 0,
    ot_hours numeric(12, 2) not null default 0,
    dt_hours numeric(12, 2) not null default 0,
    qty numeric(14, 4) not null default 0,
    cost numeric(14, 2) not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_weekly_job_ts_lines_sheet
    on public.weekly_job_timesheet_lines (timesheet_id, sort_order);

comment on table public.weekly_job_timesheets is 'Per-job weekly customer timesheet with printable PDF and sign-off.';
comment on table public.weekly_job_timesheet_lines is 'Labor/equipment/material lines for weekly_job_timesheets.';

alter table public.weekly_job_timesheets enable row level security;
alter table public.weekly_job_timesheet_lines enable row level security;

drop policy if exists weekly_job_timesheets_select on public.weekly_job_timesheets;
create policy weekly_job_timesheets_select on public.weekly_job_timesheets
    for select to authenticated using (true);

drop policy if exists weekly_job_timesheets_write on public.weekly_job_timesheets;
create policy weekly_job_timesheets_write on public.weekly_job_timesheets
    for all to authenticated using (true) with check (true);

drop policy if exists weekly_job_timesheet_lines_select on public.weekly_job_timesheet_lines;
create policy weekly_job_timesheet_lines_select on public.weekly_job_timesheet_lines
    for select to authenticated using (true);

drop policy if exists weekly_job_timesheet_lines_write on public.weekly_job_timesheet_lines;
create policy weekly_job_timesheet_lines_write on public.weekly_job_timesheet_lines
    for all to authenticated using (true) with check (true);
