-- Unified Pricing Guide: master estimating database.
-- Safe to re-run (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

-- -----------------------------------------------------------------------------
-- pricing_guide_items
-- -----------------------------------------------------------------------------
create table if not exists public.pricing_guide_items (
    id uuid primary key default gen_random_uuid(),
    item_code text not null default '',
    item_type text not null default 'Material',
    description text not null default '',
    category text not null default '',
    subcategory text not null default '',
    unit text not null default 'EA',
    default_cost numeric not null default 0,
    default_markup_percent numeric not null default 0,
    default_sell_price numeric not null default 0,
    taxable boolean not null default true,
    is_active boolean not null default true,
    inventory_item_id uuid references public.inventory_items (id) on delete set null,
    asset_id uuid references public.assets (id) on delete set null,
    vendor_id uuid,
    labor_role text,
    equipment_type text,
    travel_type text,
    notes text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint pricing_guide_items_item_code_unique unique (item_code)
);

create index if not exists idx_pricing_guide_items_type
    on public.pricing_guide_items (item_type);
create index if not exists idx_pricing_guide_items_category
    on public.pricing_guide_items (category);
create index if not exists idx_pricing_guide_items_active
    on public.pricing_guide_items (is_active);
create index if not exists idx_pricing_guide_items_inventory
    on public.pricing_guide_items (inventory_item_id);
create index if not exists idx_pricing_guide_items_asset
    on public.pricing_guide_items (asset_id);
create index if not exists idx_pricing_guide_items_vendor
    on public.pricing_guide_items (vendor_id);

comment on table public.pricing_guide_items is
    'Master estimating price list: inventory-linked, labor, equipment, travel, subcontractor, and other billable items.';

drop trigger if exists trg_pricing_guide_items_updated_at on public.pricing_guide_items;
do $$
begin
    if exists (
        select 1 from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public' and p.proname = 'ips_set_updated_at'
    ) then
        create trigger trg_pricing_guide_items_updated_at
            before update on public.pricing_guide_items
            for each row execute function public.ips_set_updated_at();
    end if;
exception when others then
    null;
end $$;

-- -----------------------------------------------------------------------------
-- pricing_guide_price_history
-- -----------------------------------------------------------------------------
create table if not exists public.pricing_guide_price_history (
    id uuid primary key default gen_random_uuid(),
    pricing_item_id uuid not null references public.pricing_guide_items (id) on delete cascade,
    old_cost numeric not null default 0,
    new_cost numeric not null default 0,
    changed_by text not null default '',
    changed_at timestamptz not null default now(),
    notes text not null default ''
);

create index if not exists idx_pricing_guide_price_history_item
    on public.pricing_guide_price_history (pricing_item_id, changed_at desc);

-- -----------------------------------------------------------------------------
-- pricing_guide_assembly_items (TODO-ready; not fully implemented in UI)
-- -----------------------------------------------------------------------------
create table if not exists public.pricing_guide_assembly_items (
    id uuid primary key default gen_random_uuid(),
    assembly_id uuid not null references public.pricing_guide_items (id) on delete cascade,
    component_id uuid not null references public.pricing_guide_items (id) on delete cascade,
    quantity numeric not null default 1,
    sort_order int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_pricing_guide_assembly_parent
    on public.pricing_guide_assembly_items (assembly_id, sort_order);

-- -----------------------------------------------------------------------------
-- Reverse links: inventory + assets → pricing guide
-- -----------------------------------------------------------------------------
alter table if exists public.inventory_items
    add column if not exists pricing_item_id uuid references public.pricing_guide_items (id) on delete set null;

alter table if exists public.inventory_items
    add column if not exists sync_cost_to_pricing boolean not null default false;

create index if not exists idx_inventory_items_pricing_item
    on public.inventory_items (pricing_item_id);

alter table if exists public.assets
    add column if not exists pricing_item_id uuid references public.pricing_guide_items (id) on delete set null;

create index if not exists idx_assets_pricing_item
    on public.assets (pricing_item_id);

-- -----------------------------------------------------------------------------
-- estimate_line_items — pricing item snapshot link
-- -----------------------------------------------------------------------------
alter table if exists public.estimate_line_items
    add column if not exists pricing_item_id uuid references public.pricing_guide_items (id) on delete set null;

create index if not exists idx_estimate_line_items_pricing_item
    on public.estimate_line_items (pricing_item_id);

-- -----------------------------------------------------------------------------
-- Migrate legacy estimate_materials → pricing_guide_items
-- -----------------------------------------------------------------------------
insert into public.pricing_guide_items (
    item_code,
    item_type,
    description,
    category,
    subcategory,
    unit,
    default_cost,
    default_markup_percent,
    default_sell_price,
    taxable,
    is_active,
    inventory_item_id,
    notes,
    created_at,
    updated_at
)
select
    em.item_key,
    case when em.inventory_ref_id is not null then 'Inventory' else 'Material' end,
    coalesce(nullif(trim(em.description), ''), em.item_key),
    coalesce(nullif(trim(em.category), ''), 'Pricing Guide'),
    coalesce(nullif(trim(em.subgroup), ''), ''),
    coalesce(nullif(trim(em.unit), ''), 'EA'),
    coalesce(em.purchase_price, 0),
    case
        when coalesce(em.purchase_price, 0) > 0
             and coalesce(em.sell_price, 0) > coalesce(em.purchase_price, 0)
            then round(((em.sell_price - em.purchase_price) / em.purchase_price) * 100.0, 4)
        else 25
    end,
    coalesce(
        em.sell_price,
        round(coalesce(em.purchase_price, 0) * 1.25, 2)
    ),
    true,
    coalesce(em.is_active, true),
    em.inventory_ref_id,
    '',
    coalesce(em.created_at, now()),
    coalesce(em.updated_at, now())
from public.estimate_materials em
where coalesce(trim(em.item_key), '') <> ''
  and not exists (
      select 1
      from public.pricing_guide_items p
      where lower(trim(p.item_code)) = lower(trim(em.item_key))
  );

-- Back-link inventory rows from migrated pricing items
update public.inventory_items ii
set pricing_item_id = p.id
from public.pricing_guide_items p
where p.inventory_item_id = ii.id
  and ii.pricing_item_id is null;

-- Seed labor rates into pricing guide (when not already present)
insert into public.pricing_guide_items (
    item_code,
    item_type,
    description,
    category,
    unit,
    default_cost,
    default_markup_percent,
    default_sell_price,
    labor_role,
    is_active
)
select
    'LABOR-' || upper(regexp_replace(coalesce(nullif(trim(lr.classification), ''), 'Labor'), '[^A-Za-z0-9]+', '-', 'g')),
    'Labor',
    coalesce(nullif(trim(lr.classification), ''), 'Labor'),
    'Labor',
    'HR',
    coalesce(lr.st_rate, 0),
    0,
    coalesce(lr.st_rate, 0),
    coalesce(nullif(trim(lr.classification), ''), 'Labor'),
    coalesce(lr.is_active, true)
from public.labor_rates lr
where nullif(trim(lr.classification), '') is not null
  and not exists (
      select 1
      from public.pricing_guide_items p
      where p.item_type = 'Labor'
        and lower(trim(p.labor_role)) = lower(trim(coalesce(nullif(trim(lr.classification), ''), 'Labor')))
  );

-- Seed equipment-linked pricing from assets with rates
insert into public.pricing_guide_items (
    item_code,
    item_type,
    description,
    category,
    unit,
    default_cost,
    default_markup_percent,
    default_sell_price,
    asset_id,
    equipment_type,
    is_active
)
select
    'EQ-' || upper(regexp_replace(coalesce(a.asset_number, left(a.id::text, 8)), '[^A-Za-z0-9]+', '-', 'g')),
    'Equipment',
    coalesce(nullif(trim(a.asset_name), ''), 'Equipment'),
    coalesce(nullif(trim(a.category), ''), 'Equipment'),
    'HR',
    coalesce(
        nullif(a.hourly_rate, 0),
        nullif(a.daily_rate, 0) / 8.0,
        nullif(a.rental_daily_rate, 0) / 8.0,
        0
    ),
    0,
    coalesce(
        nullif(a.hourly_rate, 0),
        nullif(a.daily_rate, 0) / 8.0,
        nullif(a.rental_daily_rate, 0) / 8.0,
        0
    ),
    a.id,
    coalesce(nullif(trim(a.category), ''), nullif(trim(a.asset_type), ''), ''),
    coalesce(a.is_active, true)
from public.assets a
where coalesce(
        nullif(a.hourly_rate, 0),
        nullif(a.daily_rate, 0),
        nullif(a.rental_daily_rate, 0),
        0
    ) > 0
  and a.pricing_item_id is null
  and not exists (
      select 1 from public.pricing_guide_items p where p.asset_id = a.id
  );

update public.assets a
set pricing_item_id = p.id
from public.pricing_guide_items p
where p.asset_id = a.id
  and a.pricing_item_id is null;

-- Optional FK to vendors when that table exists
do $$
begin
    if exists (
        select 1 from information_schema.tables
        where table_schema = 'public' and table_name = 'vendors'
    ) and not exists (
        select 1 from information_schema.table_constraints
        where constraint_schema = 'public'
          and table_name = 'pricing_guide_items'
          and constraint_name = 'pricing_guide_items_vendor_id_fkey'
    ) then
        alter table public.pricing_guide_items
            add constraint pricing_guide_items_vendor_id_fkey
            foreign key (vendor_id) references public.vendors (id) on delete set null;
    end if;
exception when others then
    null;
end $$;
