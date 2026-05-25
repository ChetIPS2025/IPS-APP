-- Standardize weekly timesheet tables on public.weekly_timesheets / weekly_timesheet_lines.
-- Safe to run when sql/004_weekly_timesheets.sql already created the base tables.
-- Does not create duplicate weekly_job_timesheets tables.

create extension if not exists pgcrypto;

create table if not exists public.weekly_timesheets (
    id uuid primary key default gen_random_uuid(),
    job_id uuid references public.jobs (id) on delete cascade,
    customer_id uuid null references public.customers (id) on delete set null,
    week_start date not null,
    week_end date,
    job_number text default '',
    client_name text default '',
    job_name text default '',
    po_number text default '',
    sheet_date date,
    work_performed text default '',
    approved_by text default '',
    approved_by_name text default '',
    approved_by_title text default '',
    approved_at timestamptz,
    signature_data text default '',
    signature_path text default '',
    signature_url text default '',
    signature_png_base64 text,
    status text default 'Draft',
    pdf_path text default '',
    pdf_url text default '',
    pdf_file_url text default '',
    unsigned_pdf_url text default '',
    excel_path text default '',
    excel_url text default '',
    signed_at timestamptz,
    signed_by_name text default '',
    signed_by_email text default '',
    locked_snapshot jsonb,
    locked_at timestamptz,
    sign_token uuid default gen_random_uuid(),
    sign_token_expires_at timestamptz,
    created_by uuid null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.weekly_timesheets
    add column if not exists customer_id uuid null references public.customers (id) on delete set null,
    add column if not exists week_end date,
    add column if not exists work_performed text default '',
    add column if not exists approved_by text default '',
    add column if not exists approved_by_name text default '',
    add column if not exists approved_by_title text default '',
    add column if not exists approved_at timestamptz,
    add column if not exists signature_data text default '',
    add column if not exists signature_path text default '',
    add column if not exists signature_url text default '',
    add column if not exists status text default 'Draft',
    add column if not exists pdf_path text default '',
    add column if not exists pdf_url text default '',
    add column if not exists pdf_file_url text default '',
    add column if not exists unsigned_pdf_url text default '',
    add column if not exists excel_path text default '',
    add column if not exists excel_url text default '',
    add column if not exists signed_at timestamptz,
    add column if not exists signed_by_name text default '',
    add column if not exists signed_by_email text default '',
    add column if not exists locked_snapshot jsonb,
    add column if not exists locked_at timestamptz,
    add column if not exists sign_token uuid default gen_random_uuid(),
    add column if not exists sign_token_expires_at timestamptz,
    add column if not exists created_by uuid null,
    add column if not exists updated_at timestamptz default now();

update public.weekly_timesheets
set week_end = week_start + interval '6 days'
where week_end is null and week_start is not null;

update public.weekly_timesheets
set approved_by_name = approved_by
where coalesce(approved_by_name, '') = '' and coalesce(approved_by, '') <> '';

update public.weekly_timesheets
set signature_path = coalesce(signature_data, signature_png_base64, '')
where coalesce(signature_path, '') = '' and coalesce(signature_data, signature_png_base64, '') <> '';

update public.weekly_timesheets
set pdf_path = coalesce(pdf_file_url, unsigned_pdf_url, '')
where coalesce(pdf_path, '') = '' and coalesce(pdf_file_url, unsigned_pdf_url, '') <> '';

update public.weekly_timesheets
set pdf_url = coalesce(pdf_path, pdf_file_url, '')
where coalesce(pdf_url, '') = '' and coalesce(pdf_path, pdf_file_url, '') <> '';

alter table public.weekly_timesheets drop constraint if exists weekly_timesheets_status_check;
alter table public.weekly_timesheets
    add constraint weekly_timesheets_status_check
    check (status in ('Draft', 'Generated', 'Sent', 'Approved', 'Signed', 'Voided', 'Rejected'));

create unique index if not exists weekly_timesheets_job_week_uidx
    on public.weekly_timesheets (job_id, week_start)
    where job_id is not null;

create unique index if not exists uq_weekly_timesheets_sign_token
    on public.weekly_timesheets (sign_token);

create table if not exists public.weekly_timesheet_lines (
    id uuid primary key default gen_random_uuid(),
    timesheet_id uuid not null references public.weekly_timesheets (id) on delete cascade,
    line_type text not null default 'labor',
    description text default '',
    class_name text default '',
    employee_equipment text default '',
    employee_id uuid null,
    asset_id uuid null,
    inventory_item_id uuid null,
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
    monday_st numeric(12, 2) not null default 0,
    monday_ot numeric(12, 2) not null default 0,
    monday_dt numeric(12, 2) not null default 0,
    tuesday_st numeric(12, 2) not null default 0,
    tuesday_ot numeric(12, 2) not null default 0,
    tuesday_dt numeric(12, 2) not null default 0,
    wednesday_st numeric(12, 2) not null default 0,
    wednesday_ot numeric(12, 2) not null default 0,
    wednesday_dt numeric(12, 2) not null default 0,
    thursday_st numeric(12, 2) not null default 0,
    thursday_ot numeric(12, 2) not null default 0,
    thursday_dt numeric(12, 2) not null default 0,
    friday_st numeric(12, 2) not null default 0,
    friday_ot numeric(12, 2) not null default 0,
    friday_dt numeric(12, 2) not null default 0,
    saturday_st numeric(12, 2) not null default 0,
    saturday_ot numeric(12, 2) not null default 0,
    saturday_dt numeric(12, 2) not null default 0,
    sunday_st numeric(12, 2) not null default 0,
    sunday_ot numeric(12, 2) not null default 0,
    sunday_dt numeric(12, 2) not null default 0,
    total_st numeric(12, 2) not null default 0,
    total_ot numeric(12, 2) not null default 0,
    total_dt numeric(12, 2) not null default 0,
    total_hours numeric(12, 2) not null default 0,
    qty numeric(14, 4) not null default 0,
    quantity numeric(14, 4) not null default 0,
    cost numeric(14, 2) not null default 0,
    unit_cost numeric(14, 2) not null default 0,
    total_cost numeric(14, 2) not null default 0,
    sort_order int not null default 0,
    notes text default '',
    created_at timestamptz not null default now()
);

alter table public.weekly_timesheet_lines
    add column if not exists line_type text not null default 'labor',
    add column if not exists description text default '',
    add column if not exists st_hours numeric(12, 2) not null default 0,
    add column if not exists ot_hours numeric(12, 2) not null default 0,
    add column if not exists dt_hours numeric(12, 2) not null default 0,
    add column if not exists monday_st numeric(12, 2) not null default 0,
    add column if not exists monday_ot numeric(12, 2) not null default 0,
    add column if not exists monday_dt numeric(12, 2) not null default 0,
    add column if not exists tuesday_st numeric(12, 2) not null default 0,
    add column if not exists tuesday_ot numeric(12, 2) not null default 0,
    add column if not exists tuesday_dt numeric(12, 2) not null default 0,
    add column if not exists wednesday_st numeric(12, 2) not null default 0,
    add column if not exists wednesday_ot numeric(12, 2) not null default 0,
    add column if not exists wednesday_dt numeric(12, 2) not null default 0,
    add column if not exists thursday_st numeric(12, 2) not null default 0,
    add column if not exists thursday_ot numeric(12, 2) not null default 0,
    add column if not exists thursday_dt numeric(12, 2) not null default 0,
    add column if not exists friday_st numeric(12, 2) not null default 0,
    add column if not exists friday_ot numeric(12, 2) not null default 0,
    add column if not exists friday_dt numeric(12, 2) not null default 0,
    add column if not exists saturday_st numeric(12, 2) not null default 0,
    add column if not exists saturday_ot numeric(12, 2) not null default 0,
    add column if not exists saturday_dt numeric(12, 2) not null default 0,
    add column if not exists sunday_st numeric(12, 2) not null default 0,
    add column if not exists sunday_ot numeric(12, 2) not null default 0,
    add column if not exists sunday_dt numeric(12, 2) not null default 0,
    add column if not exists total_st numeric(12, 2) not null default 0,
    add column if not exists total_ot numeric(12, 2) not null default 0,
    add column if not exists total_dt numeric(12, 2) not null default 0,
    add column if not exists total_hours numeric(12, 2) not null default 0,
    add column if not exists quantity numeric(14, 4) not null default 0,
    add column if not exists unit_cost numeric(14, 2) not null default 0,
    add column if not exists total_cost numeric(14, 2) not null default 0,
    add column if not exists notes text default '';

update public.weekly_timesheet_lines
set description = employee_equipment
where coalesce(description, '') = '' and coalesce(employee_equipment, '') <> '';

update public.weekly_timesheet_lines
set
    monday_st = hours_mon,
    tuesday_st = hours_tue,
    wednesday_st = hours_wed,
    thursday_st = hours_thu,
    friday_st = hours_fri,
    saturday_st = hours_sat,
    sunday_st = hours_sun,
    total_st = st_hours,
    total_ot = ot_hours,
    total_dt = dt_hours,
    total_hours = st_hours + ot_hours + dt_hours,
    quantity = qty,
    total_cost = cost
where coalesce(total_hours, 0) = 0
  and (hours_mon + hours_tue + hours_wed + hours_thu + hours_fri + hours_sat + hours_sun) <> 0;

create index if not exists idx_weekly_timesheet_lines_sheet
    on public.weekly_timesheet_lines (timesheet_id, sort_order);

alter table public.weekly_timesheets enable row level security;
alter table public.weekly_timesheet_lines enable row level security;

drop policy if exists "weekly_timesheets_all" on public.weekly_timesheets;
create policy "weekly_timesheets_all"
    on public.weekly_timesheets
    for all
    to authenticated
    using (true)
    with check (true);

drop policy if exists "weekly_timesheet_lines_all" on public.weekly_timesheet_lines;
create policy "weekly_timesheet_lines_all"
    on public.weekly_timesheet_lines
    for all
    to authenticated
    using (true)
    with check (true);

comment on table public.weekly_timesheets is 'Per-job weekly customer timesheet with printable PDF/Excel export and sign-off.';
comment on table public.weekly_timesheet_lines is 'Labor/equipment/material lines for weekly_timesheets.';
