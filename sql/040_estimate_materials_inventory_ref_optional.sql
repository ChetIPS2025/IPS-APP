-- Optional follow-up to 039: ensure inventory_ref_id exists on older deployments.
-- No-op when the column is already present (PostgreSQL 11+).

alter table if exists public.estimate_materials
    add column if not exists inventory_ref_id uuid null
    references public.inventory_items (id) on delete set null;

create index if not exists idx_estimate_materials_inventory_ref
    on public.estimate_materials (inventory_ref_id);
