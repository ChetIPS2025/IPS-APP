-- Estimate builder predetermined pricing: labor_rates lookup + asset hourly/daily/weekly rates.

create table if not exists public.labor_rates (
    id uuid primary key default gen_random_uuid(),
    role_name text,
    classification text not null default '',
    st_rate numeric not null default 0,
    ot_rate numeric,
    dt_rate numeric,
    ot_multiplier numeric not null default 1.5,
    dt_multiplier numeric not null default 2.0,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Backfill role_name from classification when present (labor module uses classification).
update public.labor_rates
set role_name = classification
where coalesce(role_name, '') = '' and coalesce(classification, '') <> '';

alter table public.labor_rates
    add column if not exists role_name text,
    add column if not exists ot_multiplier numeric default 1.5,
    add column if not exists dt_multiplier numeric default 2.0,
    add column if not exists is_active boolean default true;

alter table public.assets
    add column if not exists hourly_rate numeric default 0,
    add column if not exists daily_rate numeric default 0,
    add column if not exists weekly_rate numeric default 0;

comment on table public.labor_rates is 'Default labor ST/OT/DT rates for estimates and costing.';
comment on column public.assets.hourly_rate is 'Optional explicit hourly equipment rate for estimates.';
comment on column public.assets.daily_rate is 'Optional explicit daily equipment rate for estimates.';
comment on column public.assets.weekly_rate is 'Optional explicit weekly equipment rate for estimates.';
