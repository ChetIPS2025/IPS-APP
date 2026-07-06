-- Add inventory status/department columns expected by save_inventory_item (011_phase3_schema_align).
-- Safe to run multiple times.

alter table public.inventory_items
    add column if not exists status text not null default 'In Stock';

alter table public.inventory_items
    add column if not exists department text not null default '';

comment on column public.inventory_items.status is 'Stock status label (In Stock, Low Stock, Out of Stock, Discontinued).';
comment on column public.inventory_items.department is 'Optional owning department for reporting.';
