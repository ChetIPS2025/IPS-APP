-- Quote / estimate material catalog (separate from inventory stock).
-- Run in Supabase after inventory_items (015) exists.

create table if not exists public.estimate_materials (
    id uuid primary key default gen_random_uuid(),
    item_key text not null,
    description text not null default '',
    category text not null default 'Quote Catalog',
    subgroup text not null default '',
    unit text not null default 'EA',
    purchase_price numeric,
    sell_price numeric,
    vendor_item_number text not null default '',
    is_active boolean not null default true,
    inventory_ref_id uuid null references public.inventory_items (id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint estimate_materials_item_key_unique unique (item_key)
);

create index if not exists idx_estimate_materials_inventory_ref
    on public.estimate_materials (inventory_ref_id);
create index if not exists idx_estimate_materials_category
    on public.estimate_materials (category);
create index if not exists idx_estimate_materials_active
    on public.estimate_materials (is_active);

comment on table public.estimate_materials is
    'Catalog lines for estimates and proposals (pricing, markup). Optional link to stocked inventory_items.';

comment on column public.estimate_materials.inventory_ref_id is
    'When set, this quote line was copied from or syncs pricing with inventory_items.id.';
