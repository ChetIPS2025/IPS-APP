-- =============================================================================
-- 090_catalog_relationships.sql — Pricing Guide / Inventory / Assets separation
-- Master catalog: pricing_guide_items
-- Stock: inventory_items (consumables only)
-- Fleet: assets (reusable tools/equipment)
-- Safe to re-run.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- pricing_guide_items — extended master catalog fields
-- -----------------------------------------------------------------------------
alter table if exists public.pricing_guide_items
    add column if not exists item_class text not null default 'Non-Inventory',
    add column if not exists item_number text not null default '',
    add column if not exists model_number text not null default '',
    add column if not exists sku text not null default '',
    add column if not exists markup_percent numeric(8, 4) not null default 0,
    add column if not exists sell_price numeric(14, 2) not null default 0,
    add column if not exists vendor text not null default '',
    add column if not exists image_url text not null default '',
    add column if not exists qr_code_url text not null default '',
    add column if not exists linked_inventory_id uuid references public.inventory_items (id) on delete set null,
    add column if not exists linked_asset_id uuid references public.assets (id) on delete set null,
    add column if not exists asset_recommended boolean not null default false;

create index if not exists idx_pricing_guide_items_item_class
    on public.pricing_guide_items (item_class);
create index if not exists idx_pricing_guide_items_item_number
    on public.pricing_guide_items (item_number);
create index if not exists idx_pricing_guide_items_model_number
    on public.pricing_guide_items (model_number);
create index if not exists idx_pricing_guide_items_sku
    on public.pricing_guide_items (sku);
create index if not exists idx_pricing_guide_items_linked_inventory
    on public.pricing_guide_items (linked_inventory_id);
create index if not exists idx_pricing_guide_items_linked_asset
    on public.pricing_guide_items (linked_asset_id);

-- Mirror legacy link columns into linked_* aliases
update public.pricing_guide_items
set linked_inventory_id = coalesce(linked_inventory_id, inventory_item_id),
    linked_asset_id = coalesce(linked_asset_id, asset_id),
    sku = coalesce(nullif(sku, ''), nullif(item_code, '')),
    item_number = coalesce(nullif(item_number, ''), nullif(item_code, '')),
    markup_percent = coalesce(nullif(markup_percent, 0), default_markup_percent, 0),
    sell_price = coalesce(nullif(sell_price, 0), default_sell_price, 0)
where true;

-- Infer item_class from existing links when blank/default
update public.pricing_guide_items
set item_class = case
    when linked_inventory_id is not null or inventory_item_id is not null then 'Inventory'
    when linked_asset_id is not null or asset_id is not null then 'Asset'
    when item_type in ('Labor', 'Travel', 'Subcontractor', 'Service') then 'Non-Inventory'
    when item_type in ('Inventory', 'Material', 'Consumable') and coalesce(linked_inventory_id, inventory_item_id) is not null then 'Inventory'
    when item_type in ('Equipment', 'Rental') and coalesce(linked_asset_id, asset_id) is not null then 'Asset'
    else coalesce(nullif(item_class, ''), 'Non-Inventory')
end
where coalesce(item_class, 'Non-Inventory') = 'Non-Inventory';

-- -----------------------------------------------------------------------------
-- inventory_items — stock consumables linked to pricing guide
-- -----------------------------------------------------------------------------
alter table if exists public.inventory_items
    add column if not exists pricing_guide_id uuid references public.pricing_guide_items (id) on delete set null,
    add column if not exists sku text not null default '',
    add column if not exists barcode text not null default '',
    add column if not exists stock_location text not null default '',
    add column if not exists last_purchase_cost numeric(14, 2),
    add column if not exists average_cost numeric(14, 2),
    add column if not exists quantity_allocated numeric not null default 0,
    add column if not exists quantity_available numeric generated always as (
        greatest(coalesce(quantity_on_hand, 0) - coalesce(quantity_allocated, 0), 0)
    ) stored;

create index if not exists idx_inventory_items_pricing_guide
    on public.inventory_items (pricing_guide_id);
create index if not exists idx_inventory_items_sku
    on public.inventory_items (sku);
create index if not exists idx_inventory_items_barcode
    on public.inventory_items (barcode);

update public.inventory_items
set pricing_guide_id = coalesce(pricing_guide_id, pricing_item_id),
    stock_location = coalesce(nullif(stock_location, ''), nullif(storage_location, ''), ''),
    sku = coalesce(nullif(sku, ''), '')
where true;

-- -----------------------------------------------------------------------------
-- assets — reusable property linked to pricing guide
-- -----------------------------------------------------------------------------
alter table if exists public.assets
    add column if not exists pricing_guide_id uuid references public.pricing_guide_items (id) on delete set null,
    add column if not exists asset_number text not null default '',
    add column if not exists assigned_trailer_id uuid references public.assets (id) on delete set null,
    add column if not exists service_due date,
    add column if not exists inspection_due date,
    add column if not exists manuals text not null default '',
    add column if not exists certifications text not null default '';

create index if not exists idx_assets_pricing_guide
    on public.assets (pricing_guide_id);
create index if not exists idx_assets_asset_number
    on public.assets (asset_number);
create index if not exists idx_assets_assigned_trailer
    on public.assets (assigned_trailer_id);

update public.assets
set pricing_guide_id = coalesce(pricing_guide_id, pricing_item_id),
    asset_number = coalesce(nullif(asset_number, ''), nullif(asset_id, ''), '')
where true;

-- -----------------------------------------------------------------------------
-- tool_trailer_kits — supervisor-owned mobile tool kits / trailers
-- -----------------------------------------------------------------------------
create table if not exists public.tool_trailer_kits (
    id uuid primary key default gen_random_uuid(),
    trailer_name text not null default '',
    supervisor text not null default '',
    qr_code text not null default '',
    location text not null default '',
    assigned_job_id uuid references public.jobs (id) on delete set null,
    parent_asset_id uuid references public.assets (id) on delete set null,
    notes text not null default '',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_tool_trailer_kits_supervisor
    on public.tool_trailer_kits (supervisor);
create index if not exists idx_tool_trailer_kits_parent_asset
    on public.tool_trailer_kits (parent_asset_id);

alter table public.tool_trailer_kits enable row level security;
drop policy if exists tool_trailer_kits_all on public.tool_trailer_kits;
create policy tool_trailer_kits_all
    on public.tool_trailer_kits
    for all
    to authenticated
    using (true)
    with check (true);

comment on table public.tool_trailer_kits is
    'Named tool trailer / kit containers (Electrical Trailer, Welding Trailer, etc.).';

comment on column public.pricing_guide_items.item_class is
    'Inventory | Asset | Non-Inventory — controls whether stock/asset records are created.';
