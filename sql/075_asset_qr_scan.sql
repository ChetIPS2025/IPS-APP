-- Asset mobile QR scan: tokens, extended inspections, issues, document URL support.
-- Run after sql/074_add_asset_images.sql.

alter table public.assets
    add column if not exists qr_token text,
    add column if not exists qr_value text;

create unique index if not exists idx_assets_qr_token_unique
    on public.assets (qr_token)
    where qr_token is not null and length(trim(qr_token)) > 0;

comment on column public.assets.qr_token is 'Secret token for mobile asset QR deep links; validated on scan.';
comment on column public.assets.qr_value is 'Cached mobile scan URL (?scan=asset&asset_id=…&token=…).';

-- Extend legacy asset_inspections for field QR inspections (non-breaking adds).
alter table public.asset_inspections
    add column if not exists inspector_user_id uuid,
    add column if not exists inspector_employee_id uuid,
    add column if not exists inspector_name text,
    add column if not exists inspector_phone text,
    add column if not exists condition text default 'Good',
    add column if not exists hours_miles numeric,
    add column if not exists location text,
    add column if not exists visual_damage boolean default false,
    add column if not exists safety_guards_ok boolean default true,
    add column if not exists leaks_present boolean default false,
    add column if not exists tires_wheels_ok boolean default true,
    add column if not exists controls_working boolean default true,
    add column if not exists emergency_stop_working boolean default true,
    add column if not exists labels_present boolean default true,
    add column if not exists clean_usable boolean default true,
    add column if not exists notes text,
    add column if not exists photo_url text;

create index if not exists idx_asset_inspections_asset_id
    on public.asset_inspections (asset_id);

create index if not exists idx_asset_inspections_date
    on public.asset_inspections (inspection_date desc);

alter table public.asset_inspections enable row level security;

drop policy if exists "asset_inspections_all" on public.asset_inspections;
create policy "asset_inspections_all"
    on public.asset_inspections
    for all
    to authenticated
    using (true)
    with check (true);

-- TODO: add limited insert policy for unauthenticated QR inspections when public scanning is enabled.

create table if not exists public.asset_issues (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets (id) on delete cascade,
    severity text default 'Medium',
    description text not null,
    reported_by_name text,
    reported_by_phone text,
    photo_path text,
    photo_url text,
    status text default 'Open',
    created_at timestamptz not null default now()
);

create index if not exists idx_asset_issues_asset_id
    on public.asset_issues (asset_id);

create index if not exists idx_asset_issues_created_at
    on public.asset_issues (created_at desc);

alter table public.asset_issues enable row level security;

drop policy if exists "asset_issues_all" on public.asset_issues;
create policy "asset_issues_all"
    on public.asset_issues
    for all
    to authenticated
    using (true)
    with check (true);

-- documents_hub extras (safe if table already has columns from 008/062).
alter table public.documents_hub
    add column if not exists file_url text;

comment on column public.documents_hub.file_url is 'Optional public HTTPS URL for document preview/download.';
