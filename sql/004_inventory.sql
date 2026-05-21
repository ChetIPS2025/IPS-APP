-- =============================================================================
-- 004_inventory.sql — Inventory module
-- Depends on: 001_core.sql (vendors optional)
-- =============================================================================

create table if not exists public.inventory_items (
    id uuid primary key default gen_random_uuid(),
    vendor_id uuid references public.vendors (id) on delete set null,
    item_name text not null,
    sku text not null default '',
    item_number text generated always as (sku) stored,
    category text not null default '',
    unit text not null default 'EA',
    quantity_on_hand numeric not null default 0,
    qty_on_hand numeric generated always as (quantity_on_hand) stored,
    reorder_point numeric not null default 0,
    reorder_quantity numeric not null default 0,
    unit_cost numeric,
    total_value numeric generated always as (quantity_on_hand * coalesce(unit_cost, 0)) stored,
    vendor text not null default '',
    storage_location text not null default '',
    location text generated always as (storage_location) stored,
    department text not null default '',
    barcode text not null default '',
    external_purchase_url text not null default '',
    status text not null default 'In Stock',
    notes text not null default '',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_inventory_items_category on public.inventory_items (category);
create index if not exists idx_inventory_items_status on public.inventory_items (status);
create index if not exists idx_inventory_items_active on public.inventory_items (is_active);
create index if not exists idx_inventory_items_name on public.inventory_items (item_name);
create index if not exists idx_inventory_items_sku on public.inventory_items (sku);
create unique index if not exists uq_inventory_items_sku
    on public.inventory_items (sku)
    where sku is not null and trim(sku) <> '';

drop trigger if exists trg_inventory_items_updated_at on public.inventory_items;
create trigger trg_inventory_items_updated_at
    before update on public.inventory_items
    for each row execute function public.ips_set_updated_at();

-- FK from estimate_line_items → inventory (optional)
do $$
begin
    if exists (
        select 1 from information_schema.tables
        where table_schema = 'public' and table_name = 'estimate_line_items'
    ) then
        alter table public.estimate_line_items
            drop constraint if exists estimate_line_items_inventory_item_id_fkey;
        alter table public.estimate_line_items
            add constraint estimate_line_items_inventory_item_id_fkey
            foreign key (inventory_item_id) references public.inventory_items (id) on delete set null;
    end if;
exception when others then
    null;
end $$;

-- -----------------------------------------------------------------------------
-- inventory_transactions
-- -----------------------------------------------------------------------------
create table if not exists public.inventory_transactions (
    id uuid primary key default gen_random_uuid(),
    inventory_item_id uuid not null references public.inventory_items (id) on delete cascade,
    transaction_type text not null default 'adjustment',
    quantity_delta numeric not null default 0,
    quantity_after numeric,
    unit_cost numeric,
    reference text not null default '',
    job_id uuid references public.jobs (id) on delete set null,
    notes text not null default '',
    created_by uuid references public.profiles (id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_inventory_txn_item
    on public.inventory_transactions (inventory_item_id, created_at desc);
create index if not exists idx_inventory_txn_type
    on public.inventory_transactions (transaction_type);

-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------
alter table public.inventory_items enable row level security;
alter table public.inventory_transactions enable row level security;

drop policy if exists inventory_items_select on public.inventory_items;
create policy inventory_items_select on public.inventory_items for select to authenticated using (true);
drop policy if exists inventory_items_write on public.inventory_items;
create policy inventory_items_write on public.inventory_items for all to authenticated using (true) with check (true);

drop policy if exists inventory_transactions_select on public.inventory_transactions;
create policy inventory_transactions_select on public.inventory_transactions for select to authenticated using (true);
drop policy if exists inventory_transactions_write on public.inventory_transactions;
create policy inventory_transactions_write on public.inventory_transactions for all to authenticated using (true) with check (true);

comment on table public.inventory_items is 'Stocked supplies (IPS Inventory module).';
comment on table public.inventory_transactions is 'Stock adjustments and usage history.';
