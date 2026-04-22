-- Customer-facing weekly timesheets per job with signature workflow.
-- Run after sql/009_time_entries.sql and after jobs/customers/customer_locations/customer_contacts exist.
--
-- NOTE: unsigned_pdf_url / signed_pdf_url store storage object paths (use create_signed_url in app).

create extension if not exists pgcrypto;

create table if not exists public.job_weekly_timesheets (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,
    week_start date not null,
    week_end date not null,
    customer_id uuid null references public.customers (id) on delete set null,
    customer_location_id uuid null references public.customer_locations (id) on delete set null,
    customer_contact_id uuid null references public.customer_contacts (id) on delete set null,
    unsigned_pdf_url text default '',
    signed_pdf_url text default '',
    status text not null default 'Draft' check (status in ('Draft', 'Sent', 'Signed', 'Rejected')),
    sent_at timestamptz null,
    signed_at timestamptz null,
    signed_by_name text default '',
    signed_by_email text default '',
    signature_data text default '',
    signed_by_user_agent text default '',
    signed_by_device_label text default '',
    notes text default '',
    sign_token uuid not null default gen_random_uuid(),
    created_at timestamptz not null default now()
);

create unique index if not exists uq_job_weekly_timesheets_job_week
    on public.job_weekly_timesheets (job_id, week_start);

create unique index if not exists uq_job_weekly_timesheets_sign_token
    on public.job_weekly_timesheets (sign_token);

comment on table public.job_weekly_timesheets is 'Customer weekly timesheets generated from time_entries; signed via token link.';
comment on column public.job_weekly_timesheets.unsigned_pdf_url is 'Storage object path for unsigned PDF (use create_signed_url).';
comment on column public.job_weekly_timesheets.signed_pdf_url is 'Storage object path for signed PDF (use create_signed_url).';
comment on column public.job_weekly_timesheets.signature_data is 'Signature image (PNG) base64 or data URL (stored for audit).';
comment on column public.job_weekly_timesheets.sign_token is 'Secure token for customer signing link (no login required).';

alter table if exists public.job_weekly_timesheets enable row level security;

drop policy if exists "Allow read access" on public.job_weekly_timesheets;
create policy "Allow read access" on public.job_weekly_timesheets for select to authenticated using (true);

drop policy if exists "Allow insert access" on public.job_weekly_timesheets;
create policy "Allow insert access" on public.job_weekly_timesheets for insert to authenticated with check (true);

drop policy if exists "Allow update access" on public.job_weekly_timesheets;
create policy "Allow update access" on public.job_weekly_timesheets for update to authenticated using (true) with check (true);

drop policy if exists "Allow delete access" on public.job_weekly_timesheets;
create policy "Allow delete access" on public.job_weekly_timesheets for delete to authenticated using (true);
