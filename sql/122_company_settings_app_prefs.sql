-- Application preferences for Admin / Settings → Application Settings (NP-003)

alter table public.company_settings
    add column if not exists default_landing_page text not null default 'Dashboard',
    add column if not exists date_format text not null default 'MM/DD/YYYY',
    add column if not exists email_notifications_enabled boolean not null default true;

comment on column public.company_settings.default_landing_page is 'Default nav slug label after sign-in (Dashboard, Jobs, Timekeeping).';
comment on column public.company_settings.date_format is 'Display date format preference for the app.';
comment on column public.company_settings.email_notifications_enabled is 'Master toggle for outbound email notifications.';
