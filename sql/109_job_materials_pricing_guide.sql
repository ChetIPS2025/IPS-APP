-- Link job costing material lines to Pricing Guide catalog items.

alter table if exists public.job_materials
    add column if not exists pricing_guide_id uuid null references public.pricing_guide_items (id) on delete set null;

create index if not exists idx_job_materials_pricing_guide_id on public.job_materials (pricing_guide_id);

comment on column public.job_materials.pricing_guide_id is 'Pricing Guide catalog item — costing only; does not move inventory.';
comment on column public.job_materials.usage_source is 'pricing_guide | qr_scan | manual_inventory | manual_entry';
