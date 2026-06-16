-- Global and per-category default markup columns for estimates (067 partial apply fix).

alter table public.estimates
    add column if not exists default_material_markup_pct numeric(8, 4) not null default 0;

alter table public.estimates
    add column if not exists default_labor_markup_pct numeric(8, 4) not null default 0;

alter table public.estimates
    add column if not exists default_equipment_markup_pct numeric(8, 4) not null default 0;

alter table public.estimates
    add column if not exists default_subcontractor_markup_pct numeric(8, 4) not null default 0;

alter table public.estimates
    add column if not exists global_markup_pct numeric(8, 4) not null default 0;

comment on column public.estimates.global_markup_pct is
    'Default markup % applied to new Cost Builder lines; Customer Price = Cost + (Cost × Markup %).';
