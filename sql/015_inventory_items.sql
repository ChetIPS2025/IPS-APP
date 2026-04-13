-- Inventory / Supplies: stocked consumables (separate from individually tracked assets).
-- Run in Supabase SQL editor after prior migrations.

create table if not exists public.inventory_items (
    id uuid primary key default gen_random_uuid(),
    item_name text not null,
    category text not null default '',
    unit text not null default 'EA',
    quantity_on_hand numeric not null default 0,
    reorder_point numeric not null default 0,
    unit_cost numeric,
    vendor text not null default '',
    storage_location text not null default '',
    notes text not null default '',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_inventory_items_category on public.inventory_items (category);
create index if not exists idx_inventory_items_active on public.inventory_items (is_active);
create index if not exists idx_inventory_items_name on public.inventory_items (item_name);

comment on table public.inventory_items is 'IPS stocked supplies and consumables; not serialized assets.';
comment on column public.inventory_items.quantity_on_hand is 'Current quantity in stock.';
comment on column public.inventory_items.reorder_point is 'Alert threshold for replenishment.';
comment on column public.inventory_items.unit_cost is 'Last known cost per unit (optional).';
