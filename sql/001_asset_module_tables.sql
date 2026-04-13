create extension if not exists pgcrypto;

create table if not exists public.assets (
    id uuid primary key default gen_random_uuid(),
    asset_id text unique not null,
    asset_name text not null,
    asset_type text default '',
    manufacturer text default '',
    model text default '',
    serial_number text default '',
    year text default '',
    category text default '',
    subcategory text default '',
    status text default 'Available',
    condition text default '',
    location text default '',
    yard_location text default '',
    assigned_employee text default '',
    assigned_job_id uuid null,
    department text default '',
    purchase_date date null,
    purchase_cost numeric(12,2) default 0,
    current_value numeric(12,2) default 0,
    hour_meter numeric(12,2) default 0,
    mileage numeric(12,2) default 0,
    license_plate text default '',
    vin text default '',
    qr_code_value text default '',
    photo_path text default '',
    notes text default '',
    is_active boolean default true,
    created_by uuid null,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists idx_assets_asset_id on public.assets(asset_id);
create index if not exists idx_assets_serial_number on public.assets(serial_number);
create index if not exists idx_assets_status on public.assets(status);
create index if not exists idx_assets_asset_type on public.assets(asset_type);

create table if not exists public.asset_photos (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets(id) on delete cascade,
    file_name text not null,
    file_path text not null,
    photo_type text default 'overview',
    uploaded_by uuid null,
    created_at timestamptz default now()
);

create table if not exists public.asset_documents (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets(id) on delete cascade,
    document_type text default '',
    file_name text not null,
    file_path text not null,
    expiration_date date null,
    notes text default '',
    uploaded_by uuid null,
    created_at timestamptz default now()
);

create table if not exists public.asset_assignments (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets(id) on delete cascade,
    assigned_to text default '',
    assigned_job_id uuid null,
    assigned_location text default '',
    check_out_at timestamptz null,
    check_in_at timestamptz null,
    notes text default '',
    created_by uuid null,
    created_at timestamptz default now()
);

create table if not exists public.asset_maintenance (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets(id) on delete cascade,
    service_type text not null,
    service_date date not null,
    hour_meter numeric(12,2) default 0,
    mileage numeric(12,2) default 0,
    vendor text default '',
    cost numeric(12,2) default 0,
    po_number text default '',
    performed_by text default '',
    notes text default '',
    next_service_date date null,
    next_service_hours numeric(12,2) default 0,
    next_service_mileage numeric(12,2) default 0,
    created_by uuid null,
    created_at timestamptz default now()
);

create table if not exists public.asset_inspections (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid not null references public.assets(id) on delete cascade,
    inspection_type text not null,
    inspection_date date not null,
    inspector text default '',
    status text default 'Pass',
    issues_found text default '',
    corrective_action text default '',
    photo_path text default '',
    created_by uuid null,
    created_at timestamptz default now()
);

create table if not exists public.asset_service_rules (
    id uuid primary key default gen_random_uuid(),
    asset_type text not null unique,
    default_service_type text default 'PM',
    interval_days integer default 0,
    interval_hours numeric(12,2) default 0,
    interval_miles numeric(12,2) default 0,
    is_active boolean default true,
    created_at timestamptz default now()
);
