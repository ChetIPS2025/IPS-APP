-- Application preferences for Admin / Settings → Application Settings (NP-003)
-- Safe to re-run. Creates company_settings when missing (legacy DBs may not have 001_core.sql).

-- -----------------------------------------------------------------------------
-- company_settings (create full table if absent)
-- -----------------------------------------------------------------------------
create table if not exists public.company_settings (
    id uuid primary key default gen_random_uuid(),
    company_name text not null default 'Industrial Plant Solutions',
    logo_storage_path text not null default '',
    timezone text not null default 'America/Chicago',
    default_landing_page text not null default 'Dashboard',
    date_format text not null default 'MM/DD/YYYY',
    email_notifications_enabled boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Additive columns when table existed from 001_core.sql without app prefs
alter table public.company_settings
    add column if not exists default_landing_page text not null default 'Dashboard',
    add column if not exists date_format text not null default 'MM/DD/YYYY',
    add column if not exists email_notifications_enabled boolean not null default true;

insert into public.company_settings (company_name)
select 'Industrial Plant Solutions'
where not exists (select 1 from public.company_settings limit 1);

drop trigger if exists trg_company_settings_updated_at on public.company_settings;
do $$
begin
    if exists (
        select 1 from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public' and p.proname = 'ips_set_updated_at'
    ) then
        create trigger trg_company_settings_updated_at
            before update on public.company_settings
            for each row execute function public.ips_set_updated_at();
    end if;
exception when others then
    null;
end $$;

alter table public.company_settings enable row level security;

drop policy if exists company_settings_select on public.company_settings;
create policy company_settings_select on public.company_settings
    for select to authenticated using (true);

drop policy if exists company_settings_write on public.company_settings;
do $$
begin
    if exists (
        select 1 from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public' and p.proname = 'ips_is_admin'
    ) then
        execute $pol$
            create policy company_settings_write on public.company_settings
                for all to authenticated
                using (public.ips_is_admin())
                with check (public.ips_is_admin())
        $pol$;
    else
        execute $pol$
            create policy company_settings_write on public.company_settings
                for all to authenticated
                using (true)
                with check (true)
        $pol$;
    end if;
end $$;

comment on table public.company_settings is 'Single-row company profile and application preferences (Admin / Settings).';
comment on column public.company_settings.default_landing_page is 'Default nav slug label after sign-in (Dashboard, Jobs, Timekeeping).';
comment on column public.company_settings.date_format is 'Display date format preference for the app.';
comment on column public.company_settings.email_notifications_enabled is 'Master toggle for outbound email notifications.';
