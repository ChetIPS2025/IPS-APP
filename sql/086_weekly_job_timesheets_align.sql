-- Align weekly_job_timesheets schema with customer-facing export workflow.
-- Run after sql/085_weekly_job_timesheets.sql.

-- Header extensions
alter table public.weekly_job_timesheets
    add column if not exists customer_location_id uuid null,
    add column if not exists customer_contact_id uuid null,
    add column if not exists approved_by_name text not null default '',
    add column if not exists approved_by_title text not null default '',
    add column if not exists approved_at timestamptz null,
    add column if not exists signature_path text not null default '',
    add column if not exists pdf_path text not null default '',
    add column if not exists pdf_url text not null default '',
    add column if not exists excel_path text not null default '',
    add column if not exists excel_url text not null default '';

-- Backfill new name/url columns from legacy fields
update public.weekly_job_timesheets
set approved_by_name = approved_by
where coalesce(approved_by_name, '') = '' and coalesce(approved_by, '') <> '';

update public.weekly_job_timesheets
set approved_at = signed_at
where approved_at is null and signed_at is not null;

update public.weekly_job_timesheets
set pdf_path = pdf_file_url
where coalesce(pdf_path, '') = '' and coalesce(pdf_file_url, '') <> '';

update public.weekly_job_timesheets
set pdf_url = pdf_file_url
where coalesce(pdf_url, '') = '' and coalesce(pdf_file_url, '') <> '';

update public.weekly_job_timesheets
set signature_path = signature_data
where coalesce(signature_path, '') = '' and coalesce(signature_data, '') <> '';

-- Expand status values (keep Rejected for legacy rows)
alter table public.weekly_job_timesheets
    drop constraint if exists weekly_job_timesheets_status_check;

alter table public.weekly_job_timesheets
    add constraint weekly_job_timesheets_status_check
    check (status in ('Draft', 'Generated', 'Sent', 'Approved', 'Signed', 'Voided', 'Rejected'));

-- Line extensions (ST/OT/DT per day + cost fields)
alter table public.weekly_job_timesheet_lines
    add column if not exists employee_id uuid null,
    add column if not exists asset_id uuid null,
    add column if not exists inventory_item_id uuid null,
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
    add column if not exists notes text not null default '';

-- Mirror legacy day totals into monday_st..sunday_st when new columns are empty
update public.weekly_job_timesheet_lines
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
where line_type in ('labor', 'equipment')
  and total_hours = 0
  and (hours_mon + hours_tue + hours_wed + hours_thu + hours_fri + hours_sat + hours_sun) <> 0;

update public.weekly_job_timesheet_lines
set quantity = qty, total_cost = cost
where line_type in ('material', 'expense')
  and quantity = 0
  and qty <> 0;

comment on column public.weekly_job_timesheets.excel_path is 'Storage path for generated TIMESHEET WEEKLY.xlsx export.';
comment on column public.weekly_job_timesheets.pdf_path is 'Storage path for generated customer PDF export.';
