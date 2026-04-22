-- Extend job_weekly_timesheets with expiring sign tokens + signer title + audit hints.
-- Run after sql/031_job_weekly_timesheets.sql.

alter table public.job_weekly_timesheets
    add column if not exists sign_token_expires_at timestamptz null;

alter table public.job_weekly_timesheets
    add column if not exists signed_by_title text default '';

alter table public.job_weekly_timesheets
    add column if not exists signed_by_ip text default '';

comment on column public.job_weekly_timesheets.sign_token_expires_at is 'If set, signing link is invalid after this UTC timestamp.';
comment on column public.job_weekly_timesheets.signed_by_title is 'Optional signer title/role (e.g. Supervisor).';
comment on column public.job_weekly_timesheets.signed_by_ip is 'Best-effort requester IP at signing time (may be blank behind proxies).';

