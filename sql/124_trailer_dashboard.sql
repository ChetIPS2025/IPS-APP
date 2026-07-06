-- Tool Trailer Dashboard: spot audits with photos, tool requests, inspections, broken-tool reports.

alter table public.asset_kit_audits
    add column if not exists audit_type text default 'Full',
    add column if not exists photo_paths jsonb default '[]'::jsonb;

alter table public.asset_kit_audit_items
    add column if not exists photo_path text,
    add column if not exists photo_url text;

create table if not exists public.trailer_tool_requests (
    id uuid primary key default gen_random_uuid(),
    parent_asset_id uuid not null references public.assets (id) on delete cascade,
    kit_item_id uuid null references public.asset_kit_items (id) on delete set null,
    tool_name text not null default '',
    quantity numeric not null default 1,
    priority text not null default 'Normal',
    reason text not null default '',
    job_id uuid null references public.jobs (id) on delete set null,
    requested_by_user_id uuid null,
    requested_by_employee_id uuid null,
    requested_by_name text,
    requested_by_phone text,
    status text not null default 'Open',
    created_at timestamptz not null default now()
);

create index if not exists trailer_tool_requests_parent_idx
    on public.trailer_tool_requests (parent_asset_id, created_at desc);

alter table public.trailer_tool_requests enable row level security;
drop policy if exists trailer_tool_requests_all on public.trailer_tool_requests;
create policy trailer_tool_requests_all
    on public.trailer_tool_requests for all to authenticated using (true) with check (true);

create table if not exists public.trailer_broken_tool_reports (
    id uuid primary key default gen_random_uuid(),
    parent_asset_id uuid not null references public.assets (id) on delete cascade,
    kit_item_id uuid null references public.asset_kit_items (id) on delete set null,
    child_asset_id uuid null references public.assets (id) on delete set null,
    tool_name text not null default '',
    problem text not null default '',
    notes text not null default '',
    photo_path text,
    photo_url text,
    maintenance_issue_id uuid null,
    reported_by_user_id uuid null,
    reported_by_employee_id uuid null,
    reported_by_name text,
    reported_by_phone text,
    status text not null default 'Open',
    created_at timestamptz not null default now()
);

create index if not exists trailer_broken_tool_reports_parent_idx
    on public.trailer_broken_tool_reports (parent_asset_id, created_at desc);

alter table public.trailer_broken_tool_reports enable row level security;
drop policy if exists trailer_broken_tool_reports_all on public.trailer_broken_tool_reports;
create policy trailer_broken_tool_reports_all
    on public.trailer_broken_tool_reports for all to authenticated using (true) with check (true);

create table if not exists public.trailer_inspections (
    id uuid primary key default gen_random_uuid(),
    parent_asset_id uuid not null references public.assets (id) on delete cascade,
    job_id uuid null references public.jobs (id) on delete set null,
    performed_by_user_id uuid null,
    performed_by_employee_id uuid null,
    performed_by_name text,
    performed_by_phone text,
    tires_ok boolean not null default false,
    lights_ok boolean not null default false,
    jack_ok boolean not null default false,
    chains_ok boolean not null default false,
    fire_extinguisher_ok boolean not null default false,
    first_aid_ok boolean not null default false,
    locks_ok boolean not null default false,
    registration_ok boolean not null default false,
    photo_path text,
    photo_url text,
    notes text,
    created_at timestamptz not null default now()
);

create index if not exists trailer_inspections_parent_idx
    on public.trailer_inspections (parent_asset_id, created_at desc);

alter table public.trailer_inspections enable row level security;
drop policy if exists trailer_inspections_all on public.trailer_inspections;
create policy trailer_inspections_all
    on public.trailer_inspections for all to authenticated using (true) with check (true);

create table if not exists public.trailer_photos (
    id uuid primary key default gen_random_uuid(),
    parent_asset_id uuid not null references public.assets (id) on delete cascade,
    photo_path text,
    photo_url text,
    caption text,
    uploaded_by_user_id uuid null,
    uploaded_by_name text,
    created_at timestamptz not null default now()
);

create index if not exists trailer_photos_parent_idx
    on public.trailer_photos (parent_asset_id, created_at desc);

alter table public.trailer_photos enable row level security;
drop policy if exists trailer_photos_all on public.trailer_photos;
create policy trailer_photos_all
    on public.trailer_photos for all to authenticated using (true) with check (true);
