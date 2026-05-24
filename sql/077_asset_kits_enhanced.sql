-- Asset Kits / Tool Trailers enhancement (parent asset flags + kit audits/transactions).
-- Safe to re-run. Uses inventory_items (not legacy inventory table).

-- Parent asset kit fields
alter table public.assets
    add column if not exists is_kit boolean not null default false,
    add column if not exists kit_type text,
    add column if not exists assigned_to_employee_id uuid null,
    add column if not exists assigned_to_name text,
    add column if not exists assigned_to_phone text,
    add column if not exists assigned_job_id uuid null references public.jobs (id) on delete set null,
    add column if not exists total_kit_value numeric default 0,
    add column if not exists last_kit_audit_at timestamptz,
    add column if not exists kit_status text default 'Active';

create index if not exists idx_assets_is_kit on public.assets (is_kit) where is_kit = true;
create index if not exists idx_assets_assigned_job on public.assets (assigned_job_id) where assigned_job_id is not null;

comment on column public.assets.is_kit is 'True when asset is a container kit (tool trailer, gang box, etc.).';
comment on column public.assets.total_kit_value is 'Sum of active kit item values; maintained by app.';

-- Extend asset_kit_items (038 / 044 may already exist)
alter table public.asset_kit_items
    add column if not exists child_asset_id uuid null references public.assets (id) on delete set null,
    add column if not exists item_type text default 'Tool',
    add column if not exists description text default '',
    add column if not exists quantity_expected numeric default 1,
    add column if not exists quantity_actual numeric default 1,
    add column if not exists unit text default 'EA',
    add column if not exists condition text default 'Good',
    add column if not exists status text default 'Present',
    add column if not exists serial_number text default '',
    add column if not exists qr_token text,
    add column if not exists qr_value text,
    add column if not exists assigned_to_employee_id uuid null,
    add column if not exists assigned_to_name text,
    add column if not exists updated_at timestamptz not null default now();

-- Backfill from legacy columns when present
update public.asset_kit_items
set quantity_expected = coalesce(quantity_expected, quantity, 1),
    quantity_actual = coalesce(quantity_actual, quantity_on_hand, quantity, 1)
where quantity_expected is null or quantity_actual is null;

create index if not exists asset_kit_items_child_asset_idx
    on public.asset_kit_items (child_asset_id) where child_asset_id is not null;
create index if not exists asset_kit_items_status_idx on public.asset_kit_items (status);

-- Kit audits (unified model; distinct from legacy tool_trailer_audits)
create table if not exists public.asset_kit_audits (
    id uuid primary key default gen_random_uuid(),
    parent_asset_id uuid not null references public.assets (id) on delete cascade,
    audit_date timestamptz not null default now(),
    performed_by_user_id uuid null,
    performed_by_employee_id uuid null,
    performed_by_name text,
    performed_by_phone text,
    assigned_supervisor_id uuid null,
    assigned_supervisor_name text,
    job_id uuid null references public.jobs (id) on delete set null,
    expected_item_count numeric default 0,
    present_item_count numeric default 0,
    missing_item_count numeric default 0,
    damaged_item_count numeric default 0,
    expected_value numeric default 0,
    missing_value numeric default 0,
    damaged_value numeric default 0,
    status text default 'Completed',
    notes text,
    created_at timestamptz not null default now()
);

create index if not exists asset_kit_audits_parent_idx
    on public.asset_kit_audits (parent_asset_id, audit_date desc);

alter table public.asset_kit_audits enable row level security;
drop policy if exists "asset_kit_audits_all" on public.asset_kit_audits;
create policy "asset_kit_audits_all"
    on public.asset_kit_audits for all to authenticated using (true) with check (true);

create table if not exists public.asset_kit_audit_items (
    id uuid primary key default gen_random_uuid(),
    audit_id uuid not null references public.asset_kit_audits (id) on delete cascade,
    kit_item_id uuid not null references public.asset_kit_items (id) on delete cascade,
    expected_quantity numeric default 1,
    actual_quantity numeric default 1,
    condition text,
    status text,
    missing_quantity numeric default 0,
    damaged_quantity numeric default 0,
    notes text,
    created_at timestamptz not null default now()
);

create index if not exists asset_kit_audit_items_audit_idx
    on public.asset_kit_audit_items (audit_id);

alter table public.asset_kit_audit_items enable row level security;
drop policy if exists "asset_kit_audit_items_all" on public.asset_kit_audit_items;
create policy "asset_kit_audit_items_all"
    on public.asset_kit_audit_items for all to authenticated using (true) with check (true);

create table if not exists public.asset_kit_transactions (
    id uuid primary key default gen_random_uuid(),
    parent_asset_id uuid not null references public.assets (id) on delete cascade,
    kit_item_id uuid null references public.asset_kit_items (id) on delete set null,
    job_id uuid null references public.jobs (id) on delete set null,
    transaction_type text not null,
    quantity numeric default 1,
    performed_by_user_id uuid null,
    performed_by_employee_id uuid null,
    performed_by_name text,
    performed_by_phone text,
    assigned_to_employee_id uuid null,
    assigned_to_name text,
    previous_status text,
    new_status text,
    notes text,
    created_at timestamptz not null default now()
);

create index if not exists asset_kit_txn_parent_idx
    on public.asset_kit_transactions (parent_asset_id, created_at desc);

alter table public.asset_kit_transactions enable row level security;
drop policy if exists "asset_kit_transactions_all" on public.asset_kit_transactions;
create policy "asset_kit_transactions_all"
    on public.asset_kit_transactions for all to authenticated using (true) with check (true);
