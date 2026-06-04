-- Fitting catalog metadata on pricing_guide_items (threaded unions, adapters, etc.).

alter table if exists public.pricing_guide_items
    add column if not exists product_type text not null default '',
    add column if not exists connection_type text not null default '',
    add column if not exists pipe_size text not null default '',
    add column if not exists dash_size text not null default '',
    add column if not exists pressure_class text not null default '',
    add column if not exists body_shape text not null default '',
    add column if not exists material_grade text not null default '',
    add column if not exists max_pressure_temp text not null default '',
    add column if not exists max_steam_pressure_temp text not null default '';

create index if not exists idx_pricing_guide_items_fitting_category
    on public.pricing_guide_items (category, subcategory)
    where category = 'Unions';

create index if not exists idx_pricing_guide_items_fitting_connection
    on public.pricing_guide_items (connection_type, material_grade)
    where connection_type <> '';

comment on column public.pricing_guide_items.dash_size is
    'Fitting dash size (string, e.g. 02, 04) — leading zeros preserved.';
comment on column public.pricing_guide_items.material_grade is
    'Material option label (e.g. 304 Stainless Steel, 316 Stainless Steel).';
