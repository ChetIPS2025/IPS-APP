-- Email notifications + per-job email settings.
-- Run after public.jobs exists.

create table if not exists public.job_email_settings (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references public.jobs (id) on delete cascade,

    -- recipients (array of emails)
    customer_recipients text[] not null default '{}',
    internal_recipients text[] not null default '{}',
    cc_recipients text[] not null default '{}',

    -- per-job toggles
    enable_daily_update_emails boolean not null default false,
    enable_weekly_friday_update_emails boolean not null default false,
    enable_safety_item_update_emails boolean not null default false,
    enable_budget_po_alerts boolean not null default false,

    -- basic controls
    is_active boolean not null default true,
    notes text not null default '',

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_job_email_settings_job_id
    on public.job_email_settings (job_id);

comment on table public.job_email_settings is 'Per-job email recipients and notification toggles.';


-- Outbox / audit trail. (This is NOT a queue worker; runner scripts read settings and write rows here.)
create table if not exists public.email_notifications (
    id uuid primary key default gen_random_uuid(),

    notification_type text not null default '',
    job_id uuid null references public.jobs (id) on delete set null,

    to_emails text[] not null default '{}',
    cc_emails text[] not null default '{}',
    bcc_emails text[] not null default '{}',

    subject text not null default '',
    text_body text not null default '',
    html_body text not null default '',
    meta jsonb not null default '{}'::jsonb,

    status text not null default 'pending', -- pending|sent|failed|skipped
    provider text not null default '',
    provider_message_id text not null default '',
    error_message text not null default '',

    created_at timestamptz not null default now(),
    sent_at timestamptz null
);

create index if not exists idx_email_notifications_created_at
    on public.email_notifications (created_at desc);
create index if not exists idx_email_notifications_job_id
    on public.email_notifications (job_id);
create index if not exists idx_email_notifications_type
    on public.email_notifications (notification_type);

comment on table public.email_notifications is 'Email send audit log / outbox. Rows created by automation runner.';


-- RLS: align with sql/019_rls_authenticated_crud.sql posture.
alter table if exists public.job_email_settings enable row level security;
drop policy if exists "Allow read access" on public.job_email_settings;
create policy "Allow read access" on public.job_email_settings for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.job_email_settings;
create policy "Allow insert access" on public.job_email_settings for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.job_email_settings;
create policy "Allow update access" on public.job_email_settings for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.job_email_settings;
create policy "Allow delete access" on public.job_email_settings for delete to authenticated using (true);

alter table if exists public.email_notifications enable row level security;
drop policy if exists "Allow read access" on public.email_notifications;
create policy "Allow read access" on public.email_notifications for select to authenticated using (true);
drop policy if exists "Allow insert access" on public.email_notifications;
create policy "Allow insert access" on public.email_notifications for insert to authenticated with check (true);
drop policy if exists "Allow update access" on public.email_notifications;
create policy "Allow update access" on public.email_notifications for update to authenticated using (true) with check (true);
drop policy if exists "Allow delete access" on public.email_notifications;
create policy "Allow delete access" on public.email_notifications for delete to authenticated using (true);

